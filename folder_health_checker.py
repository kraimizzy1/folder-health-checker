#!/usr/bin/env python3
"""文件夹体检器：只读扫描目录并生成中文 HTML/CSV 报告。"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
import shutil
import struct
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".mpeg", ".mpg"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
TWO_YEARS_SECONDS = 365.2425 * 2 * 24 * 3600


def human_size(value: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:.0f} {unit}" if unit == "B" else f"{number:.2f} {unit}"
        number /= 1024
    return f"{value} B"


def iso_time(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


@dataclass
class ScanResult:
    root: str
    started: str
    finished: str = ""
    file_count: int = 0
    folder_count: int = 0
    total_size: int = 0
    extensions: dict[str, dict[str, int]] = field(default_factory=dict)
    largest: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    old_files: list[dict[str, Any]] = field(default_factory=list)
    empty_folders: list[str] = field(default_factory=list)
    images: list[dict[str, Any]] = field(default_factory=list)
    videos: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    ffprobe_available: bool = False


def add_error(result: ScanResult, operation: str, path: os.PathLike[str] | str, exc: BaseException) -> None:
    result.errors.append({"操作": operation, "路径": str(path), "错误": f"{type(exc).__name__}: {exc}"})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def image_dimensions(path: Path) -> tuple[int, int] | None:
    """用标准库读取 PNG/GIF/BMP/JPEG 宽高，不解码图像内容。"""
    with path.open("rb") as stream:
        head = stream.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and len(head) >= 24:
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a") and len(head) >= 10:
            return struct.unpack("<HH", head[6:10])
        if head.startswith(b"BM") and len(head) >= 26:
            width, height = struct.unpack("<ii", head[18:26])
            return abs(width), abs(height)
        if head.startswith(b"\xff\xd8"):
            stream.seek(2)
            while True:
                marker_start = stream.read(1)
                if not marker_start:
                    return None
                if marker_start != b"\xff":
                    continue
                marker = stream.read(1)
                while marker == b"\xff":
                    marker = stream.read(1)
                if not marker or marker in (b"\xd8", b"\xd9"):
                    continue
                length_data = stream.read(2)
                if len(length_data) != 2:
                    return None
                length = struct.unpack(">H", length_data)[0]
                if marker[0] in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    data = stream.read(5)
                    if len(data) == 5:
                        height, width = struct.unpack(">HH", data[1:5])
                        return width, height
                    return None
                stream.seek(max(0, length - 2), os.SEEK_CUR)
    return None


def probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    command = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name:format=duration",
        "-of", "json", str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=True)
    data = json.loads(completed.stdout)
    stream = (data.get("streams") or [{}])[0]
    duration = (data.get("format") or {}).get("duration")
    return {
        "路径": str(path), "时长（秒）": round(float(duration), 3) if duration else "",
        "宽": stream.get("width", ""), "高": stream.get("height", ""),
        "编码": stream.get("codec_name", ""),
    }


def scan_folder(root: Path, now: float | None = None) -> ScanResult:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(f"不是文件夹：{root}")
    result = ScanResult(root=str(root), started=dt.datetime.now().astimezone().isoformat(timespec="seconds"))
    files: list[dict[str, Any]] = []
    by_size: dict[int, list[Path]] = defaultdict(list)
    ext_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"数量": 0, "字节": 0})
    ffprobe = shutil.which("ffprobe")
    result.ffprobe_available = bool(ffprobe)
    cutoff = (now if now is not None else dt.datetime.now().timestamp()) - TWO_YEARS_SECONDS

    def walk(folder: Path) -> None:
        try:
            with os.scandir(folder) as iterator:
                entries = list(iterator)
        except OSError as exc:
            add_error(result, "读取文件夹", folder, exc)
            return
        if not entries:
            result.empty_folders.append(str(folder))
        for entry in entries:
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    result.folder_count += 1
                    walk(path)
                elif entry.is_file(follow_symlinks=False):
                    stat = entry.stat(follow_symlinks=False)
                    size = stat.st_size
                    suffix = path.suffix.lower() or "（无扩展名）"
                    record = {"路径": str(path), "字节": size, "大小": human_size(size), "修改时间": iso_time(stat.st_mtime), "类型": suffix}
                    result.file_count += 1
                    result.total_size += size
                    ext_stats[suffix]["数量"] += 1
                    ext_stats[suffix]["字节"] += size
                    files.append(record)
                    by_size[size].append(path)
                    if stat.st_mtime < cutoff:
                        result.old_files.append(record)
                    if suffix in IMAGE_EXTENSIONS:
                        try:
                            dimensions = image_dimensions(path)
                            if dimensions:
                                result.images.append({"路径": str(path), "宽": dimensions[0], "高": dimensions[1], "类型": suffix})
                        except (OSError, ValueError, struct.error) as exc:
                            add_error(result, "读取图片信息", path, exc)
                    if ffprobe and suffix in VIDEO_EXTENSIONS:
                        try:
                            result.videos.append(probe_video(path, ffprobe))
                        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
                            add_error(result, "读取视频信息", path, exc)
            except OSError as exc:
                add_error(result, "读取文件信息", path, exc)

    walk(root)
    result.extensions = dict(sorted(ext_stats.items(), key=lambda item: item[1]["字节"], reverse=True))
    result.largest = sorted(files, key=lambda item: item["字节"], reverse=True)[:50]
    result.old_files.sort(key=lambda item: item["修改时间"])

    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        hashes: dict[str, list[str]] = defaultdict(list)
        for path in paths:
            try:
                hashes[sha256_file(path)].append(str(path))
            except OSError as exc:
                add_error(result, "计算 SHA-256", path, exc)
        for digest, matching in hashes.items():
            if len(matching) > 1:
                result.duplicates.append({"SHA-256": digest, "单文件字节": size, "文件数": len(matching), "路径": matching})
    result.duplicates.sort(key=lambda item: item["单文件字节"] * (item["文件数"] - 1), reverse=True)
    result.finished = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return result


def table(title: str, headers: list[str], rows: list[list[Any]]) -> str:
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    heads = "".join(f'<th onclick="sortTable(this)">{html.escape(header)} ↕</th>' for header in headers)
    empty = '<tr><td colspan="99" class="empty">无</td></tr>' if not rows else ""
    return f"<section><h2>{html.escape(title)}</h2><div class='table-wrap'><table><thead><tr>{heads}</tr></thead><tbody>{body}{empty}</tbody></table></div></section>"


def write_reports(result: ScanResult, report_dir: Path, basename: str = "report") -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    html_path, csv_path = report_dir / f"{basename}.html", report_dir / f"{basename}.csv"
    ext_rows = [[ext, value["数量"], value["字节"], human_size(value["字节"])] for ext, value in result.extensions.items()]
    dup_rows = [[item["SHA-256"], item["单文件字节"], item["文件数"], "\n".join(item["路径"])] for item in result.duplicates]
    content = [
        table("按扩展名统计", ["扩展名", "文件数", "字节", "大小"], ext_rows),
        table("最大的 50 个文件", ["路径", "字节", "大小", "修改时间", "类型"], [[x[k] for k in ("路径", "字节", "大小", "修改时间", "类型")] for x in result.largest]),
        table("重复文件（完整 SHA-256）", ["SHA-256", "单文件字节", "文件数", "路径"], dup_rows),
        table("超过 2 年未修改", ["路径", "字节", "大小", "修改时间", "类型"], [[x[k] for k in ("路径", "字节", "大小", "修改时间", "类型")] for x in result.old_files]),
        table("空文件夹", ["路径"], [[x] for x in result.empty_folders]),
        table("图片信息", ["路径", "宽", "高", "类型"], [[x[k] for k in ("路径", "宽", "高", "类型")] for x in result.images]),
        table("视频信息", ["路径", "时长（秒）", "宽", "高", "编码"], [[x[k] for k in ("路径", "时长（秒）", "宽", "高", "编码")] for x in result.videos]),
        table("扫描错误", ["操作", "路径", "错误"], [[x[k] for k in ("操作", "路径", "错误")] for x in result.errors]),
    ]
    template = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>文件夹体检报告</title><style>
:root{color-scheme:light;--blue:#1769aa;--bg:#f4f7fa}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:#24313d;font:14px/1.55 "Segoe UI","Microsoft YaHei",sans-serif}
header{padding:32px max(4vw,24px);color:white;background:linear-gradient(125deg,#125b91,#1c8a8a)}h1{margin:0 0 8px}.meta{opacity:.9}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;padding:20px max(4vw,24px)}
.card,section{background:white;border-radius:10px;box-shadow:0 2px 12px #172b4d16}.card{padding:18px}.value{font-size:25px;font-weight:700;color:var(--blue)}main{padding:0 max(4vw,24px) 40px}section{margin:0 0 18px;padding:18px}h2{font-size:18px;margin:0 0 12px}
.table-wrap{overflow:auto;max-height:560px}table{width:100%;border-collapse:collapse}th{position:sticky;top:0;background:#eaf1f7;cursor:pointer;text-align:left}th,td{padding:9px 11px;border-bottom:1px solid #e2e8ee;vertical-align:top;white-space:pre-wrap}tr:hover{background:#f7fbff}.empty{text-align:center;color:#718096}
</style></head><body><header><h1>文件夹体检报告</h1><div class="meta">扫描目录：ROOT<br>开始：START　完成：FINISH　ffprobe：FFPROBE</div></header>
<div class="cards"><div class="card"><div>文件</div><div class="value">FILES</div></div><div class="card"><div>文件夹</div><div class="value">FOLDERS</div></div><div class="card"><div>总大小</div><div class="value">SIZE</div></div><div class="card"><div>重复组</div><div class="value">DUPS</div></div><div class="card"><div>错误</div><div class="value">ERRORS</div></div></div>
<main>CONTENT</main><script>
function sortTable(th){const t=th.closest("table"),b=t.tBodies[0],i=[...th.parentNode.children].indexOf(th),asc=th.dataset.asc!=="1";th.dataset.asc=asc?"1":"0";[...b.rows].sort((a,c)=>{let x=a.cells[i]?.innerText??"",y=c.cells[i]?.innerText??"";let nx=Number(x),ny=Number(y);let v=(!isNaN(nx)&&!isNaN(ny))?nx-ny:x.localeCompare(y,"zh-CN");return asc?v:-v}).forEach(r=>b.appendChild(r))}
</script></body></html>"""
    replacements = {
        "ROOT": html.escape(result.root), "START": result.started, "FINISH": result.finished,
        "FFPROBE": "可用" if result.ffprobe_available else "未找到（已跳过视频元数据）",
        "FILES": str(result.file_count), "FOLDERS": str(result.folder_count), "SIZE": human_size(result.total_size),
        "DUPS": str(len(result.duplicates)), "ERRORS": str(len(result.errors)), "CONTENT": "".join(content),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    html_path.write_text(template, encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["类别", "路径/扩展名", "文件数", "字节", "大小/信息", "修改时间/SHA-256"])
        writer.writerow(["汇总", result.root, result.file_count, result.total_size, human_size(result.total_size), result.finished])
        writer.writerow(["汇总-文件夹", result.root, result.folder_count, "", "", ""])
        for ext, values in result.extensions.items():
            writer.writerow(["扩展名", ext, values["数量"], values["字节"], human_size(values["字节"]), ""])
        for item in result.largest:
            writer.writerow(["大文件", item["路径"], "", item["字节"], item["大小"], item["修改时间"]])
        for item in result.duplicates:
            for path in item["路径"]:
                writer.writerow(["重复文件", path, item["文件数"], item["单文件字节"], "", item["SHA-256"]])
        for item in result.old_files:
            writer.writerow(["旧文件", item["路径"], "", item["字节"], item["大小"], item["修改时间"]])
        for path in result.empty_folders:
            writer.writerow(["空文件夹", path, "", "", "", ""])
        for item in result.images:
            writer.writerow(["图片", item["路径"], "", "", f'{item["宽"]}×{item["高"]} {item["类型"]}', ""])
        for item in result.videos:
            writer.writerow(["视频", item["路径"], "", "", f'{item["宽"]}×{item["高"]} {item["编码"]} {item["时长（秒）"]}秒', ""])
        for item in result.errors:
            writer.writerow(["错误", item["路径"], "", "", item["操作"], item["错误"]])
    return html_path, csv_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只读扫描文件夹并生成中文体检报告")
    parser.add_argument("folder", help="要扫描的文件夹")
    parser.add_argument("--reports", default=str(Path(__file__).parent / "reports"), help="报告输出目录")
    args = parser.parse_args(argv)
    try:
        result = scan_folder(Path(args.folder))
        html_path, csv_path = write_reports(result, Path(args.reports))
    except (OSError, ValueError) as exc:
        print(f"无法开始扫描：{exc}", file=sys.stderr)
        return 2
    print(f"扫描完成：{result.file_count} 个文件，{result.folder_count} 个文件夹，{len(result.errors)} 个错误")
    print(f"HTML：{html_path}")
    print(f"CSV ：{csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
