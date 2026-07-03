"""Background job runner with on-disk status for large CSV processing."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from data_sorter import ProgressUpdate, process_csv, process_multiple_csv, read_header, resolve_columns_by_name

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "jobs"
OUTPUT_DIR = BASE_DIR / "outputs"

JOBS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

_lock = threading.Lock()
_active_jobs: dict[str, threading.Thread] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def save_job(job_id: str, payload: dict) -> None:
    payload["updated_at"] = _utc_now()
    _job_path(job_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_job(job_id: str) -> dict | None:
    path = _job_path(job_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def create_job(
    keep_columns: list[str],
    skip_empty: bool,
    remove_duplicates: bool,
    output_path: Path,
    input_path: Path | None = None,
    input_paths: list[Path] | None = None,
) -> str:
    if input_path is None and not input_paths:
        raise ValueError("Provide an input file or input file list.")
    if input_path is not None and input_paths:
        raise ValueError("Use either one input file or multiple input files.")

    job_id = uuid.uuid4().hex
    multi_mode = bool(input_paths)

    save_job(
        job_id,
        {
            "job_id": job_id,
            "status": "queued",
            "created_at": _utc_now(),
            "mode": "multi" if multi_mode else "single",
            "input_path": str(input_path) if input_path else None,
            "input_paths": [str(path) for path in input_paths] if input_paths else [],
            "output_path": str(output_path),
            "output_name": output_path.name,
            "keep_columns": keep_columns,
            "skip_empty": skip_empty,
            "remove_duplicates": remove_duplicates,
            "input_rows": 0,
            "output_rows": 0,
            "duplicates_removed": 0,
            "files_processed": len(input_paths) if input_paths else 1,
            "progress_percent": 0,
            "message": "Waiting to start...",
            "error": None,
        },
    )

    worker = threading.Thread(
        target=_run_job,
        args=(job_id, input_path, input_paths, output_path, keep_columns, skip_empty, remove_duplicates),
        daemon=True,
    )

    with _lock:
        _active_jobs[job_id] = worker

    worker.start()
    return job_id


def _run_job(
    job_id: str,
    input_path: Path | None,
    input_paths: list[Path] | None,
    output_path: Path,
    keep_columns: list[str],
    skip_empty: bool,
    remove_duplicates: bool,
) -> None:
    dedup_db_path = JOBS_DIR / f"{job_id}_dedup.sqlite"

    def on_progress(update: ProgressUpdate) -> None:
        job = load_job(job_id) or {}
        job.update(
            {
                "status": "running",
                "input_rows": update.input_rows,
                "output_rows": update.output_rows,
                "duplicates_removed": update.duplicates_removed,
                "progress_percent": update.progress_percent,
                "message": update.message,
            }
        )
        save_job(job_id, job)

    try:
        on_progress(
            ProgressUpdate(
                input_rows=0,
                output_rows=0,
                duplicates_removed=0,
                progress_percent=0,
                message="Starting...",
            )
        )

        if input_paths:
            header = read_header(input_paths[0])
            resolved_columns = resolve_columns_by_name(header, keep_columns)
            result = process_multiple_csv(
                input_paths,
                output_path,
                resolved_columns,
                skip_empty=skip_empty,
                remove_duplicates=True,
                progress_callback=on_progress,
                dedup_db_path=dedup_db_path,
            )
        else:
            assert input_path is not None
            header = read_header(input_path)
            resolved_columns = resolve_columns_by_name(header, keep_columns)
            result = process_csv(
                input_path,
                output_path,
                resolved_columns,
                skip_empty=skip_empty,
                remove_duplicates=remove_duplicates,
                progress_callback=on_progress,
                dedup_db_path=dedup_db_path if remove_duplicates else None,
            )

        save_job(
            job_id,
            {
                **(load_job(job_id) or {}),
                "status": "completed",
                "input_rows": result.input_rows,
                "output_rows": result.output_rows,
                "duplicates_removed": result.duplicates_removed,
                "kept_columns": result.keep_columns,
                "removed_column_count": result.removed_column_count,
                "files_processed": result.files_processed,
                "progress_percent": 100,
                "message": f"Saved to {output_path}",
                "output_path": str(output_path),
                "error": None,
            },
        )
    except Exception as exc:
        save_job(
            job_id,
            {
                **(load_job(job_id) or {}),
                "status": "failed",
                "progress_percent": 0,
                "message": "Processing failed.",
                "error": str(exc),
            },
        )
        if output_path.exists():
            output_path.unlink(missing_ok=True)
    finally:
        dedup_db_path.unlink(missing_ok=True)
        with _lock:
            _active_jobs.pop(job_id, None)


def get_job(job_id: str) -> dict | None:
    return load_job(job_id)
