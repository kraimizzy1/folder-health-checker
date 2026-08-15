# Folder Health Checker / 文件夹体检器

A small Windows tool I made for getting a clearer picture of a large, messy folder before sorting it by hand. It scans only the folder you choose and writes an HTML and CSV report; it does not delete, move, rename, or upload your files.

## Use it

### Windows EXE (no Python needed)

Download `FolderHealthChecker-v0.2.0-windows-x64.exe`, then either drag a folder onto it or double-click it and paste a folder path. The reports are saved beside the EXE in `reports`.

### From source

Python 3.10+ is required. Drag a folder onto `run.bat`, or run:

```text
py -3 folder_health_checker.py "D:\folder-to-check"
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

`create_example.py` makes sample data only under `work/example_data` and writes example reports under `reports`.

## Copyright and components / 版权与组件

The code in this repository is released under the [MIT License](LICENSE). Copyright (c) 2026 kraimizzy1.

This project currently has no required third-party Python dependencies. `ffprobe` is an optional external tool: it is not bundled or distributed with this project. If third-party code or tools are used in the future, their own license terms will apply.

---

这是我为整理大而杂的文件夹写的小工具。它只扫描你选择的文件夹，并生成 HTML 和 CSV 报告；不会删除、移动、重命名、上传其中的文件。

## 怎么用

### Windows EXE（不需要安装 Python）

下载 `FolderHealthChecker-v0.2.0-windows-x64.exe` 后，把文件夹拖到 EXE 上；也可以双击 EXE，再粘贴要扫描的路径。报告会保存在 EXE 同级的 `reports` 文件夹里。

### 源码运行

需要 Python 3.10+。把文件夹拖到 `run.bat` 上，或运行：

```text
py -3 folder_health_checker.py "D:\要检查的文件夹"
```

报告会写入 `reports/report.html` 和 `reports/report.csv`。每次扫描会覆盖上一份报告，不会改动被扫描目录。

## 报告会告诉你

- 文件数、文件夹数、总大小、扩展名统计和最大的 50 个文件
- 完整 SHA-256 确认的重复文件、旧文件和空文件夹
- PNG/JPEG/GIF/BMP 图片尺寸
- 系统已安装 `ffprobe` 时的视频信息
- 扫描中读不到的文件或文件夹

报告含有完整路径和文件元数据，分享前请先确认其中没有敏感信息。

## 测试

```text
py -3 -m unittest discover -s tests -v
```

`create_example.py` 只会在 `work/example_data` 创建模拟数据，并把示例报告写入 `reports`。

## 版权与组件声明

## Third-party components

Any third-party tools or components used with this project remain subject to their own licenses and terms.

`ffprobe` is optional and is not bundled with this project.
