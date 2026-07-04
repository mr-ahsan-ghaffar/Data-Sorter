# Setup Guide — Data Sorter

This guide walks you through installing and running **Data Sorter** on a new Windows PC.

## What this tool does

- Select columns from **CSV, TXT, or Excel** and merge each row into one cell
- Remove duplicate rows (works on very large files)
- Process one file or many files together
- Read and write using full disk paths (your files stay where they are)

**Supported input:** CSV, TXT, Excel (`.xlsx`, `.xls` — max 100,000 rows and 25 MB for Excel)

---

## Requirements

| Item | Details |
|------|---------|
| OS | Windows 10 or 11 |
| Python | 3.10 or newer |
| Network | Internet on first setup only (to install Flask) |

---

## Step 1: Get the project

### Option A — Git

```bat
git clone https://github.com/mr-ahsan-ghaffar/Data-Sorter.git
cd Data-Sorter
```

### Option B — Download ZIP

1. Open the GitHub repo page
2. Click **Code** → **Download ZIP**
3. Extract to a folder, e.g. `C:\Tools\Data-Sorter\`

---

## Step 2: Install Python

Skip this if Python is already installed.

1. Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. Download and run the installer
3. **Important:** on the first screen, check **Add python.exe to PATH**
4. Click **Install Now**
5. Verify in Command Prompt:

   ```bat
   python --version
   ```

---

## Step 3: First-time setup (run once)

Open the project folder and double-click:

```
setup.bat
```

This installs Flask and creates runtime folders. Wait until you see **Setup complete.**

Or run manually:

```bat
cd C:\Tools\Data-Sorter
python -m pip install -r requirements.txt
```

---

## Step 4: Start the app

Double-click:

```
start_server.bat
```

- A console window opens (keep it open while using the app)
- Your browser opens at **http://127.0.0.1:5055**

To stop the app, close the console window.

---

## Step 5: Using the web UI

### Single file mode

1. Click **Choose file** or paste a full CSV path (e.g. `D:\Data\orders.csv`)
2. Click **Load file**
3. Check the columns you want to keep; drag to reorder
4. Set **Output folder** and **Output filename**
5. Optional: enable **Remove duplicate rows**
6. Click **Start processing**

### Multiple files mode

1. Click the **Multiple files** tab
2. Click **Choose files** — hold **Ctrl** and click each CSV
3. Click **Open**, then **Load files**
4. Select columns and start processing

Duplicates are removed **across all loaded files** into one output CSV.

---

## Tips

- The file picker may open **behind** the browser — check the Windows taskbar
- Press **Ctrl+F5** in the browser if buttons look outdated after an update
- Output is saved to the folder you pick, not copied into the app folder
- Large files (millions of rows) run in the background with a progress bar

---

## Troubleshooting

### "Python is not installed or not on PATH"

Reinstall Python and enable **Add python.exe to PATH**, then run `setup.bat` again.

### "Failed to install dependencies"

Open Command Prompt in the project folder:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Port 5055 already in use

Close any other **start_server.bat** windows, then start again. The batch file tries to free the port automatically.

### Choose file does nothing

1. Close and restart **start_server.bat**
2. Press **Ctrl+F5** in the browser
3. Look for the picker window behind other windows

### File not found when pasting a path

Use the full path including drive letter, e.g. `D:\Exports\orders.csv`. Paths are case-insensitive on Windows.

---

## Updating the app

If you cloned with Git:

```bat
git pull
```

Then restart **start_server.bat** and press **Ctrl+F5** in the browser.

---

## Folder reference

| Path | Purpose |
|------|---------|
| `setup.bat` | First-time install |
| `start_server.bat` | Launch the web app |
| `app.py` | Web server entry point |
| `data_sorter.py` | CSV engine |
| `presets/` | Saved column presets |
| `jobs/` | Job progress (auto-created) |
| `outputs/` | Temporary job downloads (auto-created) |
