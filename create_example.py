"""在项目内创建模拟文件，并生成 reports/example_report.html/.csv。"""
import os
import shutil
import struct
import time
from pathlib import Path

from folder_health_checker import scan_folder, write_reports

BASE = Path(__file__).parent
SAMPLE = BASE / "work" / "example_data"


def create_sample() -> None:
    if SAMPLE.exists():
        shutil.rmtree(SAMPLE)
    (SAMPLE / "照片").mkdir(parents=True)
    (SAMPLE / "文档").mkdir()
    (SAMPLE / "空文件夹").mkdir()
    (SAMPLE / "文档" / "说明.txt").write_text("这是文件夹体检器的模拟文件。\n", encoding="utf-8")
    duplicate = "用于验证完整 SHA-256 的重复内容。\n".encode("utf-8")
    (SAMPLE / "文档" / "副本甲.txt").write_bytes(duplicate)
    (SAMPLE / "副本乙.txt").write_bytes(duplicate)
    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 640, 360) + b"\0" * 8
    (SAMPLE / "照片" / "示例.png").write_bytes(png)
    old = SAMPLE / "文档" / "旧记录.log"
    old.write_text("三年前的模拟记录", encoding="utf-8")
    timestamp = time.time() - 3 * 365 * 24 * 3600
    os.utime(old, (timestamp, timestamp))


if __name__ == "__main__":
    create_sample()
    html_path, csv_path = write_reports(scan_folder(SAMPLE), BASE / "reports", "example_report")
    print(f"已生成：{html_path}")
    print(f"已生成：{csv_path}")
