"""Native file/folder picker for the local web app (Windows)."""

from __future__ import annotations

import argparse
import json
import tkinter as tk
from tkinter import filedialog


def pick_file() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()
    path = filedialog.askopenfilename(
        title="Select CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
    )
    root.destroy()
    return path or ""


def pick_directory() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update_idletasks()
    path = filedialog.askdirectory(title="Select output folder")
    root.destroy()
    return path or ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["file", "directory"], required=True)
    args = parser.parse_args()

    if args.mode == "file":
        selected = pick_file()
    else:
        selected = pick_directory()

    print(json.dumps({"path": selected}))


if __name__ == "__main__":
    main()
