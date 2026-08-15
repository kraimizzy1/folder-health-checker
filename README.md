# Folder Health Checker

[中文说明](README.zh-CN.md)

A small Windows tool I made for getting a clearer picture of a large, messy folder before sorting it by hand. It scans only the folder you choose and writes an HTML and CSV report; it does not delete, move, rename, or upload your files.

## Use it

### Windows EXE (no Python needed)

Download `FolderHealthChecker-v0.2.0-windows-x64.exe`, then either drag a folder onto it or double-click it and paste a folder path. The reports are saved beside the EXE in `reports`.

### From source

Python 3.10+ is required. Drag a folder onto `run.bat`, or run:

```text
py -3 src\folder_health_checker.py "D:\folder-to-check"
```

Reports are written to `reports/report.html` and `reports/report.csv`. A new scan replaces the previous pair of reports.

## What is in the report

- File and folder counts, total size, extension breakdown, and the 50 largest files
- Exact duplicate groups (full SHA-256), old files, and empty folders
- Basic PNG/JPEG/GIF/BMP dimensions
- Video metadata when `ffprobe` is already installed
- Items that could not be read during the scan

The report contains full file paths and metadata, so check it before sharing it.

## Tests

```text
py -3 -m unittest discover -s tests -v
```

`scripts/create_example.py` makes sample data only under `work/example_data` and writes example reports under `reports`.

To build the Windows EXE, run `scripts\build_exe.bat`. The resulting file is `dist\FolderHealthChecker.exe`.

## Copyright and components

The code in this repository is released under the [MIT License](LICENSE). Copyright (c) 2026 kraimizzy1.

This project currently has no required third-party Python dependencies. `ffprobe` is an optional external tool: it is not bundled or distributed with this project. If third-party code or tools are used in the future, their own license terms will apply.
