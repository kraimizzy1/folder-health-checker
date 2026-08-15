# Folder Health Checker

[简体中文](README.zh-CN.md)

A small, read-only Windows folder analyzer that helps you understand what is taking up space without deleting or modifying anything.

It scans only the folder you explicitly choose, works offline, and generates local HTML and CSV reports.

## Features

- Total file count, folder count, and size
- Storage usage grouped by file extension
- 50 largest files
- Duplicate detection using size pre-filtering plus full SHA-256 verification
- Files not modified for roughly two years
- Empty folders
- PNG, JPEG, GIF, and BMP dimensions using only the Python standard library
- Optional video metadata (duration, resolution, codec) when `ffprobe` is already installed
- Scan errors are recorded in the report instead of aborting the entire scan
- Sortable HTML tables and CSV output

## Safety and privacy

Folder Health Checker is intentionally conservative:

- Read-only: it does not delete, move, rename, or modify scanned files
- Offline: it does not make network requests
- Scope-limited: it scans only the folder you explicitly select
- Symbolic links are skipped to avoid unintentionally traversing outside the selected folder
- Reports are written only to the project's local `reports` directory

Reports contain full file paths, sizes, timestamps, and SHA-256 hashes for detected duplicates. Review reports before sharing them publicly.

## Requirements

- Windows 10 or Windows 11
- Python 3.10+
- Optional: `ffprobe` for video metadata

There are no required third-party Python packages.

## Quick start

### Option 1: drag and drop

Drag the folder you want to inspect onto `run.bat`.

### Option 2: double-click

Double-click `run.bat`, paste a folder path, and press Enter.

### Option 3: command line

```text
py -3 folder_health_checker.py "D:\Folder\To\Inspect"
```

When the scan finishes, open:

```text
reports\report.html
```

or use `reports\report.csv` with Excel or another spreadsheet tool.

Each normal run overwrites the previous `report.html` and `report.csv` inside this project. It never writes into the scanned folder.

## Tests

```text
py -3 -m unittest discover -s tests -v
```

The test suite creates its own temporary data under `work/` and cleans it up afterward.

## Create sample data locally

```text
py -3 create_example.py
```

This creates synthetic files under `work/example_data` and generates local example reports. Both `work/` and `reports/` are ignored by Git so local paths are not accidentally committed.

## Known limitations

- Very large folders can take time because duplicate candidates require full-file SHA-256 reads.
- Files blocked by permissions, exclusive locks, or Windows path policies may not be readable; those failures are reported instead of crashing the scan.
- Windows junction/reparse-point behavior has not yet been broadly tested across different storage and cloud-sync setups. Symbolic links are explicitly skipped.
- Video metadata is skipped when `ffprobe` is unavailable.

## Project structure

- `folder_health_checker.py` — scanner and report generator
- `run.bat` — Windows launcher
- `tests/` — automated tests
- `create_example.py` — creates synthetic local sample data
- `requirements.txt` — dependency note

## License

MIT License. See [LICENSE](LICENSE).
