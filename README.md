# Data Sorter

A local web app for cleaning and merging tabular data. Pick columns, merge each row into one comma-separated cell, remove duplicates, and process large files using full disk paths — your data never leaves your PC.

**Input:** CSV, TXT, Excel (`.xlsx`, `.xls` — small files up to 100k rows / 25 MB)  
**Output:** CSV

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-green)

**Repository:** [github.com/mr-ahsan-ghaffar/Data-Sorter](https://github.com/mr-ahsan-ghaffar/Data-Sorter)

## Features

- **Column picker** — choose which columns to keep and set their order
- **Row merge** — combine selected columns into a single output cell per row
- **Duplicate removal** — disk-based SQLite deduplication for large files (millions of rows)
- **Multiple input formats** — CSV and TXT for large files; Excel for small spreadsheets
- **Single or multiple files** — deduplicate across several input files in one run
- **Native file picker** — browse files anywhere on your PC (no upload/copy into the app folder)
- **Presets** — save and reuse column selections (example preset included)

## Requirements

- Windows 10 or 11
- Python 3.10 or newer
- Internet (first setup only, to install Flask)

## Quick start

1. **Clone this repo** (or download as ZIP)
2. **Install Python** from [python.org](https://www.python.org/downloads/) — check **Add python.exe to PATH**
3. Run **`setup.bat`** once
4. Run **`start_server.bat`**
5. Open **http://127.0.0.1:5055** in your browser

See **[SETUP.md](SETUP.md)** for the full setup guide and troubleshooting.

## Usage

### Single file

1. Click **Choose file** or paste a full CSV path
2. Click **Load file**
3. Select columns and drag to reorder
4. Choose output folder and filename
5. Click **Start processing**

### Multiple files

1. Open the **Multiple files** tab
2. Click **Choose files** (Ctrl+click to select several CSVs)
3. Click **Load files**
4. Select columns, then **Start processing**

Output is written directly to the folder you choose.

## Project structure

```
app.py              Flask web server
data_sorter.py      CSV processing and deduplication engine
job_manager.py      Background jobs and progress tracking
dialog_service.py   Native Windows file/folder picker
native_picker.py    Picker helper process
path_utils.py       Path validation helpers
start_server.bat    Start the app
setup.bat           First-time dependency install
templates/          Web UI
static/             CSS and JavaScript
presets/            Column preset JSON files
jobs/               Job status (created at runtime)
outputs/            Temporary downloads (created at runtime)
```

## CLI (optional)

You can also run the sorter from the command line:

```bat
python data_sorter.py input.csv --pick --remove-duplicates -o output.csv
```

Run `python data_sorter.py --help` for all options.

## License

Use freely within your organization. No warranty provided.
