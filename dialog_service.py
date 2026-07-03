"""Run native file/folder dialogs via a separate GUI process."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Literal

DialogMode = Literal["file", "files", "directory"]

_PICKER_SCRIPT = Path(__file__).with_name("native_picker.py")
_dialog_lock = threading.Lock()


def _gui_python_executable() -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.is_file():
            return str(pythonw)
    return str(exe)


def _run_picker(mode: DialogMode) -> list[str]:
    if not _PICKER_SCRIPT.is_file():
        raise RuntimeError(f"Missing picker script: {_PICKER_SCRIPT}")

    fd, result_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        cmd = [
            _gui_python_executable(),
            str(_PICKER_SCRIPT),
            "--mode",
            mode,
            "--result",
            result_path,
        ]

        run_kwargs: dict = {"timeout": 600}
        if sys.platform == "win32":
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        with _dialog_lock:
            completed = subprocess.run(cmd, **run_kwargs)

        if not os.path.isfile(result_path):
            raise RuntimeError(
                "File picker closed without returning a result. "
                "Check that no other picker window is already open."
            )

        payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(payload.get("error") or "File picker failed.")

        if completed.returncode not in (0, 1):
            raise RuntimeError(f"File picker exited with code {completed.returncode}.")

        paths = payload.get("paths") or []
        return [str(path) for path in paths if str(path).strip()]
    finally:
        try:
            os.unlink(result_path)
        except OSError:
            pass


def browse_csv_file() -> str | None:
    paths = _run_picker("file")
    return paths[0] if paths else None


def browse_csv_files() -> list[str]:
    return _run_picker("files")


def browse_output_directory() -> str | None:
    paths = _run_picker("directory")
    return paths[0] if paths else None
