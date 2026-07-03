"""
Sort and reshape CSV exports: pick columns per file, merge each row into one cell.

Usage examples:
  python data_sorter.py -i orders.csv --list-columns
  python data_sorter.py -i orders.csv -o out.csv --keep "Phone,Billing City"
  python data_sorter.py -i orders.csv -o out.csv --pick 20,21,19,22,24,25,28
  python data_sorter.py --config presets/sticky_orders.json
  python data_sorter.py -i orders.csv -o out.csv --interactive
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Documented misalignment in sticky_orders_ecom.csv (header label -> actual data).
MISALIGNED_HEADERS = {
    "Date/Time Stamp": "Duplicate Order ID (not a timestamp)",
    "Customer Name": "Line quantity",
    "Customer Email": "Customer full name",
    "Product Name": "Customer email",
    "Amount": "Product name",
    "Qty": "Order amount",
    "Shipping Type": "Campaign / funnel name",
    "Status": "Shipping type",
}


def read_header(input_path: Path) -> list[str]:
    with input_path.open("r", encoding="utf-8", errors="replace", newline="") as infile:
        return next(csv.reader(infile))


def print_columns(header: list[str], input_path: Path) -> None:
    print(f"Columns in {input_path.name} ({len(header)} total):\n")
    for index, name in enumerate(header, start=1):
        note = ""
        if name in MISALIGNED_HEADERS:
            note = f"  <- header misaligned: {MISALIGNED_HEADERS[name]}"
        print(f"  {index:>2}. {name}{note}")
    print("\nPick by name:  --keep \"Column A,Column B\"")
    print("Pick by number: --pick 1,3,5   or   --pick 1-5,8")


def parse_pick_expression(expression: str, column_count: int) -> list[int]:
    """Parse 1-based index expressions like '1,3,5-7' into sorted unique indices."""
    indices: set[int] = set()
    for part in expression.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if start > end:
                start, end = end, start
            indices.update(range(start, end + 1))
        else:
            indices.add(int(part))

    invalid = sorted(index for index in indices if index < 1 or index > column_count)
    if invalid:
        raise ValueError(
            f"Invalid column number(s): {', '.join(map(str, invalid))}. "
            f"Use 1-{column_count}."
        )
    return sorted(indices)


def parse_keep_names(expression: str) -> list[str]:
    return [name.strip() for name in expression.split(",") if name.strip()]


def resolve_columns_by_name(header: list[str], keep_names: list[str]) -> list[str]:
    header_lookup = {name.casefold(): name for name in header}
    resolved: list[str] = []
    missing: list[str] = []

    for name in keep_names:
        match = header_lookup.get(name.casefold())
        if match:
            resolved.append(match)
        else:
            missing.append(name)

    if missing:
        suggestions = suggest_columns(header, missing)
        detail = f" Unknown column(s): {', '.join(missing)}."
        if suggestions:
            detail += f" Did you mean: {', '.join(suggestions)}?"
        raise ValueError(detail.strip())

    return resolved


def suggest_columns(header: list[str], missing: list[str], limit: int = 3) -> list[str]:
    suggestions: list[str] = []
    for name in missing:
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        matches = [column for column in header if pattern.search(column)]
        suggestions.extend(matches[:limit])
    return suggestions


def resolve_keep_columns(
    header: list[str],
    keep_names: list[str] | None = None,
    pick_expression: str | None = None,
) -> list[str]:
    if keep_names and pick_expression:
        raise ValueError("Use either --keep or --pick, not both.")

    if pick_expression:
        indices = parse_pick_expression(pick_expression, len(header))
        return [header[index - 1] for index in indices]

    if keep_names:
        return resolve_columns_by_name(header, keep_names)

    raise ValueError("Choose columns with --keep, --pick, --config, or --interactive.")


def merge_row(values: list[str], skip_empty: bool = True) -> str:
    if skip_empty:
        values = [value.strip() for value in values if value.strip()]
    else:
        values = [value.strip() for value in values]
    return ", ".join(values)


def column_info(header: list[str]) -> list[dict[str, str | int | bool]]:
    return [
        {
            "index": index,
            "name": name,
            "misaligned": name in MISALIGNED_HEADERS,
            "misaligned_note": MISALIGNED_HEADERS.get(name, ""),
        }
        for index, name in enumerate(header, start=1)
    ]


@dataclass
class ProcessResult:
    input_rows: int
    output_rows: int
    duplicates_removed: int
    keep_columns: list[str]
    removed_column_count: int
    files_processed: int = 1


@dataclass
class ProgressUpdate:
    input_rows: int
    output_rows: int
    duplicates_removed: int
    progress_percent: int
    message: str


PROGRESS_ROW_INTERVAL = 50_000
SQLITE_COMMIT_INTERVAL = 100_000


def row_key_hash(selected: list[str]) -> str:
    payload = "\x1f".join(selected).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def open_dedup_database(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-200000")
    connection.execute("CREATE TABLE IF NOT EXISTS seen (key_hash TEXT PRIMARY KEY)")
    return connection


def is_duplicate(connection: sqlite3.Connection, key_hash: str) -> bool:
    cursor = connection.execute("INSERT OR IGNORE INTO seen (key_hash) VALUES (?)", (key_hash,))
    return cursor.rowcount == 0


def process_csv(
    input_path: Path,
    output_path: Path,
    keep_columns: list[str],
    skip_empty: bool = True,
    remove_duplicates: bool = False,
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    dedup_db_path: Path | None = None,
) -> ProcessResult:
    if not keep_columns:
        raise ValueError("Select at least one column to keep.")

    dedup_connection: sqlite3.Connection | None = None
    if remove_duplicates:
        db_path = dedup_db_path or output_path.with_suffix(".dedup.sqlite")
        dedup_connection = open_dedup_database(db_path)

    def emit_progress(message: str, force: bool = False) -> None:
        if not progress_callback:
            return
        if not force and input_rows % PROGRESS_ROW_INTERVAL != 0:
            return
        percent = 0
        if input_path.stat().st_size > 0:
            try:
                current_pos = infile.tell()
                percent = min(99, int((current_pos / input_path.stat().st_size) * 100))
            except (OSError, ValueError):
                percent = 0
        progress_callback(
            ProgressUpdate(
                input_rows=input_rows,
                output_rows=output_rows,
                duplicates_removed=duplicates_removed,
                progress_percent=percent,
                message=message,
            )
        )

    input_rows = 0
    output_rows = 0
    duplicates_removed = 0
    removed_column_count = 0

    try:
        with input_path.open("r", encoding="utf-8", errors="replace", newline="") as infile:
            reader = csv.reader(infile)
            header = next(reader)
            removed_column_count = len(header) - len(keep_columns)

            missing = [name for name in keep_columns if name not in header]
            if missing:
                raise ValueError(f"Input file is missing expected columns: {', '.join(missing)}")

            indices = [header.index(name) for name in keep_columns]
            merged_header = merge_row(keep_columns, skip_empty=False)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8", newline="") as outfile:
                writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
                writer.writerow([merged_header])

                emit_progress("Processing rows...", force=True)

                for row in reader:
                    if not row or all(not cell.strip() for cell in row):
                        continue

                    input_rows += 1
                    selected = [row[i].strip() if i < len(row) else "" for i in indices]

                    if dedup_connection is not None:
                        if is_duplicate(dedup_connection, row_key_hash(selected)):
                            duplicates_removed += 1
                            if input_rows % SQLITE_COMMIT_INTERVAL == 0:
                                dedup_connection.commit()
                            emit_progress("Processing rows...")
                            continue

                    writer.writerow([merge_row(selected, skip_empty=skip_empty)])
                    output_rows += 1

                    if dedup_connection is not None and input_rows % SQLITE_COMMIT_INTERVAL == 0:
                        dedup_connection.commit()

                    emit_progress("Processing rows...")

                if dedup_connection is not None:
                    dedup_connection.commit()
    finally:
        if dedup_connection is not None:
            dedup_connection.close()

    if progress_callback:
        progress_callback(
            ProgressUpdate(
                input_rows=input_rows,
                output_rows=output_rows,
                duplicates_removed=duplicates_removed,
                progress_percent=100,
                message="Finalizing output...",
            )
        )

    return ProcessResult(
        input_rows=input_rows,
        output_rows=output_rows,
        duplicates_removed=duplicates_removed,
        keep_columns=keep_columns,
        removed_column_count=len(header) - len(keep_columns),
        files_processed=1,
    )


def process_multiple_csv(
    input_paths: list[Path],
    output_path: Path,
    keep_columns: list[str],
    skip_empty: bool = True,
    remove_duplicates: bool = True,
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
    dedup_db_path: Path | None = None,
) -> ProcessResult:
    if not input_paths:
        raise ValueError("Select at least one CSV file.")
    if not keep_columns:
        raise ValueError("Select at least one column to keep.")

    dedup_connection: sqlite3.Connection | None = None
    if remove_duplicates:
        db_path = dedup_db_path or output_path.with_suffix(".dedup.sqlite")
        dedup_connection = open_dedup_database(db_path)

    total_bytes = sum(path.stat().st_size for path in input_paths if path.is_file())
    bytes_read = 0
    input_rows = 0
    output_rows = 0
    duplicates_removed = 0
    removed_column_count = 0
    merged_header = merge_row(keep_columns, skip_empty=False)

    def emit_progress(message: str, force: bool = False) -> None:
        if not progress_callback:
            return
        if not force and input_rows % PROGRESS_ROW_INTERVAL != 0:
            return
        percent = 0
        if total_bytes > 0:
            percent = min(99, int((bytes_read / total_bytes) * 100))
        progress_callback(
            ProgressUpdate(
                input_rows=input_rows,
                output_rows=output_rows,
                duplicates_removed=duplicates_removed,
                progress_percent=percent,
                message=message,
            )
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
            writer.writerow([merged_header])
            emit_progress("Processing files...", force=True)

            for file_index, input_path in enumerate(input_paths, start=1):
                emit_progress(
                    f"Processing file {file_index} of {len(input_paths)}: {input_path.name}",
                    force=True,
                )

                with input_path.open("r", encoding="utf-8", errors="replace", newline="") as infile:
                    reader = csv.reader(infile)
                    header = next(reader)
                    removed_column_count = len(header) - len(keep_columns)

                    missing = [name for name in keep_columns if name not in header]
                    if missing:
                        raise ValueError(
                            f"{input_path.name} is missing expected columns: {', '.join(missing)}"
                        )

                    indices = [header.index(name) for name in keep_columns]

                    for row in reader:
                        if not row or all(not cell.strip() for cell in row):
                            continue

                        input_rows += 1
                        selected = [row[i].strip() if i < len(row) else "" for i in indices]

                        if dedup_connection is not None:
                            if is_duplicate(dedup_connection, row_key_hash(selected)):
                                duplicates_removed += 1
                                if input_rows % SQLITE_COMMIT_INTERVAL == 0:
                                    dedup_connection.commit()
                                emit_progress(
                                    f"Processing file {file_index} of {len(input_paths)}: {input_path.name}"
                                )
                                continue

                        writer.writerow([merge_row(selected, skip_empty=skip_empty)])
                        output_rows += 1

                        if dedup_connection is not None and input_rows % SQLITE_COMMIT_INTERVAL == 0:
                            dedup_connection.commit()

                        emit_progress(
                            f"Processing file {file_index} of {len(input_paths)}: {input_path.name}"
                        )

                    bytes_read += input_path.stat().st_size

            if dedup_connection is not None:
                dedup_connection.commit()
    finally:
        if dedup_connection is not None:
            dedup_connection.close()

    if progress_callback:
        progress_callback(
            ProgressUpdate(
                input_rows=input_rows,
                output_rows=output_rows,
                duplicates_removed=duplicates_removed,
                progress_percent=100,
                message="Finalizing output...",
            )
        )

    return ProcessResult(
        input_rows=input_rows,
        output_rows=output_rows,
        duplicates_removed=duplicates_removed,
        keep_columns=keep_columns,
        removed_column_count=removed_column_count,
        files_processed=len(input_paths),
    )


def sort_csv(
    input_path: Path,
    output_path: Path,
    keep_columns: list[str],
    skip_empty: bool = True,
) -> int:
    result = process_csv(
        input_path,
        output_path,
        keep_columns,
        skip_empty=skip_empty,
        remove_duplicates=False,
    )
    return result.output_rows


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    required = {"input", "keep_columns"}
    missing_keys = required - data.keys()
    if missing_keys:
        raise ValueError(
            f"Config {config_path} is missing required key(s): {', '.join(sorted(missing_keys))}"
        )

    if not isinstance(data["keep_columns"], list) or not data["keep_columns"]:
        raise ValueError("Config 'keep_columns' must be a non-empty list of column names.")

    return data


def interactive_pick(header: list[str], input_path: Path) -> list[str]:
    print_columns(header, input_path)
    print("\nInteractive mode")
    print("Enter column numbers (example: 1,3,5-7) or column names separated by commas.")
    print("Press Enter without input to cancel.\n")

    if not sys.stdin.isatty():
        raise ValueError("Interactive mode requires a terminal. Use --keep or --pick instead.")

    while True:
        choice = input("Columns to keep: ").strip()
        if not choice:
            raise ValueError("No columns selected.")

        if re.fullmatch(r"[\d,\-\s]+", choice):
            indices = parse_pick_expression(choice, len(header))
            selected = [header[index - 1] for index in indices]
        else:
            selected = resolve_columns_by_name(header, parse_keep_names(choice))

        print("\nSelected columns:")
        for index, name in enumerate(selected, start=1):
            print(f"  {index}. {name}")

        confirm = input("\nUse these columns? [Y/n]: ").strip().casefold()
        if confirm in {"", "y", "yes"}:
            return selected

        print("Let's try again.\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pick CSV columns per file and merge each row into one cell."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Source CSV file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output CSV file (default: <input>_sorted.csv)",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="JSON config with input, output, and keep_columns",
    )
    parser.add_argument(
        "--keep",
        metavar="NAMES",
        help='Column names to keep, comma-separated (example: "Phone,Billing City")',
    )
    parser.add_argument(
        "--pick",
        metavar="NUMBERS",
        help="Column numbers to keep, 1-based (example: 20,21,19 or 1-5,8)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Choose columns interactively from a numbered list",
    )
    parser.add_argument(
        "--list-columns",
        action="store_true",
        help="Show available columns for the input file and exit",
    )
    parser.add_argument(
        "--keep-empty",
        action="store_true",
        help="Include empty fields in the merged cell (default: skip empty values)",
    )
    parser.add_argument(
        "--remove-duplicates",
        action="store_true",
        help="Remove duplicate rows based on selected column values (keep first)",
    )
    parser.add_argument(
        "--show-header-issues",
        action="store_true",
        help="Print known sticky-order header misalignment notes and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.show_header_issues:
        print("Known misaligned headers in sticky order exports:\n")
        for header, actual in MISALIGNED_HEADERS.items():
            print(f"  {header}: actually contains '{actual}'")
        print("\nUse --list-columns to inspect any CSV before choosing columns.")
        return

    input_path = args.input
    output_path = args.output
    keep_names: list[str] | None = None
    pick_expression = args.pick
    skip_empty = not args.keep_empty

    if args.config:
        config = load_config(args.config)
        input_path = Path(config["input"])
        output_path = Path(config.get("output", f"{input_path.stem}_sorted.csv"))
        keep_names = [str(name) for name in config["keep_columns"]]
        skip_empty = not config.get("keep_empty", False)
        pick_expression = None

    if input_path is None:
        raise SystemExit("Provide --input or --config.")

    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    header = read_header(input_path)

    if args.list_columns:
        print_columns(header, input_path)
        return

    if args.interactive:
        keep_columns = interactive_pick(header, input_path)
    else:
        if args.keep:
            keep_names = parse_keep_names(args.keep)
        keep_columns = resolve_keep_columns(header, keep_names, pick_expression)

    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_sorted.csv")

    result = process_csv(
        input_path,
        output_path,
        keep_columns,
        skip_empty=skip_empty,
        remove_duplicates=args.remove_duplicates,
    )

    print(f"Processed {result.output_rows:,} rows from {result.input_rows:,} input rows")
    if result.duplicates_removed:
        print(f"Removed {result.duplicates_removed:,} duplicate row(s)")
    print(f"Kept {len(keep_columns)} column(s): {', '.join(keep_columns)}")
    print(f"Removed {result.removed_column_count} column(s) from each row")
    print(f"Output written to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
