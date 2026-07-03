"""Native file/folder picker — runs in its own GUI process (pythonw on Windows)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def pick(mode: str) -> list[str]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    root.update_idletasks()
    root.lift()
    root.focus_force()
    root.update()

    filetypes = [("CSV files", "*.csv"), ("All files", "*.*")]

    try:
        if mode == "file":
            picked = filedialog.askopenfilename(
                parent=root,
                title="Select CSV file",
                filetypes=filetypes,
            )
            return [picked] if picked else []

        if mode == "files":
            picked = filedialog.askopenfilenames(
                parent=root,
                title="Select multiple CSV files (Ctrl+click each file)",
                filetypes=filetypes,
            )
            if isinstance(picked, str):
                return [picked] if picked else []
            return list(picked) if picked else []

        picked = filedialog.askdirectory(
            parent=root,
            title="Select output folder",
        )
        return [picked] if picked else []
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["file", "files", "directory"], required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    payload: dict = {"ok": True, "paths": [], "error": None}

    try:
        payload["paths"] = pick(args.mode)
    except Exception as exc:
        payload["ok"] = False
        payload["error"] = str(exc)

    Path(args.result).write_text(json.dumps(payload), encoding="utf-8")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
