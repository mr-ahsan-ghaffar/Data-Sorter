from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from data_sorter import column_info, read_header, resolve_columns_by_name
from file_io import SUPPORTED_INPUT_LABEL, file_type_label, validate_input_file
from job_manager import create_job, get_job
from file_dialog import browse_csv_file, browse_csv_files, browse_output_directory
from path_utils import make_file_ref, resolve_input_file, resolve_output_csv

APP_PORT = 5055
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PRESETS_DIR = BASE_DIR / "presets"

OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)


def format_file_size(size_bytes: int) -> str:
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.2f} GB"
    if size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def resolve_file_ref(file_ref: str) -> Path:
    if not file_ref.startswith("path:"):
        raise ValueError("Invalid file reference.")
    path = Path(file_ref.removeprefix("path:")).resolve()
    validate_input_file(path)
    return path


def analyze_file(path: Path) -> dict:
    header = read_header(path)
    return {
        "file_ref": make_file_ref(path),
        "file_path": str(path),
        "filename": path.name,
        "file_type": file_type_label(path),
        "file_size": path.stat().st_size,
        "file_size_label": format_file_size(path.stat().st_size),
        "column_count": len(header),
        "columns": column_info(header),
        "default_output_dir": str(path.parent),
    }


@app.get("/")
def index():
    return render_template("index.html")


def analyze_files(paths: list[Path]) -> dict:
    if not paths:
        raise ValueError(f"Select at least one input file ({SUPPORTED_INPUT_LABEL}).")

    first = analyze_file(paths[0])
    total_size = sum(path.stat().st_size for path in paths)
    file_items = [
        {
            "file_path": str(path),
            "filename": path.name,
            "file_size_label": format_file_size(path.stat().st_size),
        }
        for path in paths
    ]

    return {
        **first,
        "file_count": len(paths),
        "file_paths": [str(path) for path in paths],
        "files": file_items,
        "total_size_label": format_file_size(total_size),
        "default_output_dir": str(paths[0].parent),
    }


@app.post("/api/browse-files")
def browse_files():
    try:
        selected = browse_csv_files()
        if not selected:
            return jsonify({"cancelled": True, "paths": []})
        return jsonify({"cancelled": False, "paths": selected})
    except Exception as exc:
        return jsonify({"error": f"Could not open file picker: {exc}"}), 500


@app.post("/api/open-paths")
def open_paths_files():
    data = request.get_json(silent=True) or {}
    raw_paths = data.get("file_paths") or []
    if isinstance(raw_paths, str):
        raw_paths = [line.strip() for line in raw_paths.splitlines() if line.strip()]

    if not raw_paths:
        return jsonify({"error": f"Add at least one input file ({SUPPORTED_INPUT_LABEL})."}), 400

    try:
        resolved: list[Path] = []
        seen: set[str] = set()
        for raw_path in raw_paths:
            path = resolve_input_file(str(raw_path).strip())
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(path)

        if len(resolved) < 2:
            return jsonify({"error": "Add at least 2 input files for multi-file duplicate removal."}), 400

        return jsonify(analyze_files(resolved))
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not open files: {exc}"}), 400


@app.post("/api/browse-file")
def browse_file():
    try:
        selected = browse_csv_file()
        if not selected:
            return jsonify({"cancelled": True, "path": None})
        return jsonify({"cancelled": False, "path": selected})
    except Exception as exc:
        return jsonify({"error": f"Could not open file picker: {exc}"}), 500


@app.post("/api/browse-directory")
def browse_directory():
    try:
        selected = browse_output_directory()
        if not selected:
            return jsonify({"cancelled": True, "path": None})
        return jsonify({"cancelled": False, "path": selected})
    except Exception as exc:
        return jsonify({"error": f"Could not open folder picker: {exc}"}), 500


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "browse_supported": True, "multi_browse_supported": True, "port": APP_PORT})


@app.post("/api/open-path")
def open_path_file():
    data = request.get_json(silent=True) or {}
    file_path = str(data.get("file_path", "")).strip()
    if not file_path:
        return jsonify({"error": f"Enter the full path to an input file ({SUPPORTED_INPUT_LABEL})."}), 400

    try:
        source_path = resolve_input_file(file_path)
        return jsonify(analyze_file(source_path))
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not open file: {exc}"}), 400


@app.get("/api/presets")
def presets():
    preset_files = sorted(PRESETS_DIR.glob("*.json"))
    items = []
    for path in preset_files:
        with path.open("r", encoding="utf-8") as preset_file:
            preset_data = json.load(preset_file)
        items.append(
            {
                "id": path.stem,
                "name": path.stem.replace("_", " ").title(),
                "keep_columns": preset_data.get("keep_columns", []),
            }
        )
    return jsonify({"presets": items})


@app.post("/api/jobs")
def start_job():
    data = request.get_json(silent=True) or {}
    file_ref = str(data.get("file_ref", "")).strip()
    input_paths_raw = data.get("input_paths") or []
    keep_columns = data.get("keep_columns") or []
    skip_empty = bool(data.get("skip_empty", True))
    remove_duplicates = bool(data.get("remove_duplicates", False))
    output_name = str(data.get("output_name", "sorted_output.csv")).strip() or "sorted_output.csv"
    output_dir = str(data.get("output_dir", "")).strip()
    multi_mode = bool(data.get("multi_mode", False))

    if multi_mode:
        if not input_paths_raw:
            return jsonify({"error": "Load at least 2 input files first."}), 400
        if len(input_paths_raw) < 2:
            return jsonify({"error": "Multi-file mode needs at least 2 input files."}), 400
    elif not file_ref:
        return jsonify({"error": "Load an input file first."}), 400

    if not keep_columns:
        return jsonify({"error": "Select at least one column to keep."}), 400
    if not output_dir:
        return jsonify({"error": "Enter an output directory."}), 400

    try:
        output_path = resolve_output_csv(output_dir, output_name)

        if multi_mode:
            input_paths = [resolve_input_file(str(path)) for path in input_paths_raw]
            header = read_header(input_paths[0])
            resolved_columns = resolve_columns_by_name(header, [str(name) for name in keep_columns])
            job_id = create_job(
                resolved_columns,
                skip_empty,
                True,
                output_path,
                input_paths=input_paths,
            )
        else:
            input_path = resolve_file_ref(file_ref)
            header = read_header(input_path)
            resolved_columns = resolve_columns_by_name(header, [str(name) for name in keep_columns])
            job_id = create_job(
                resolved_columns,
                skip_empty,
                remove_duplicates,
                output_path,
                input_path=input_path,
            )

        return jsonify({"job_id": job_id, "status": "queued", "output_path": str(output_path)})
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Could not start job: {exc}"}), 500


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(job)


@app.get("/api/jobs/<job_id>/download")
def download_job_output(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404
    if job.get("status") != "completed":
        return jsonify({"error": "Job is not completed yet."}), 400

    output_path = Path(str(job.get("output_path", "")))
    if not output_path.is_file():
        return jsonify({"error": "Output file not found on disk."}), 404

    return send_file(output_path, as_attachment=True, download_name=output_path.name)


if __name__ == "__main__":
    url = f"http://127.0.0.1:{APP_PORT}"
    print(f"Data Sorter running at {url}")
    print(f"Supported input: {SUPPORTED_INPUT_LABEL}")
    print("Click 'Choose file' in the browser to pick a file from anywhere on your PC.")
    app.run(debug=False, host="127.0.0.1", port=APP_PORT, threaded=True)
