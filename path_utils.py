from __future__ import annotations

from pathlib import Path

from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs"


def clean_path_text(path_text: str) -> str:
    return path_text.strip().strip('"').strip("'")


def normalize_path(path_text: str) -> Path:
    cleaned = clean_path_text(path_text)
    if not cleaned:
        raise ValueError("Path is required.")
    return Path(cleaned).expanduser().resolve()


def resolve_input_csv(path_text: str) -> Path:
    path = normalize_path(path_text)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("Input file must be a .csv file.")
    return path


def resolve_output_csv(output_dir_text: str, output_name: str) -> Path:
    cleaned_dir = clean_path_text(output_dir_text)
    if cleaned_dir:
        output_dir = normalize_path(cleaned_dir)
    else:
        output_dir = DEFAULT_OUTPUT_DIR.resolve()

    if output_dir.is_file():
        raise ValueError("Output directory cannot be a file. Provide a folder path.")

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(output_name.strip()) or "sorted_output.csv"
    if not filename.lower().endswith(".csv"):
        filename = f"{filename}.csv"

    return output_dir / filename


def make_file_ref(path: Path) -> str:
    return f"path:{path.resolve()}"
