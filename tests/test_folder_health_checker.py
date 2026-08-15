import os
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from folder_health_checker import image_dimensions, scan_folder, write_reports


class FolderHealthCheckerTests(unittest.TestCase):
    def setUp(self):
        test_work_dir = Path(__file__).parent.parent / "work"
        test_work_dir.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_work_dir)
        self.root = Path(self.temp.name) / "sample"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_scan_counts_duplicates_old_and_empty(self):
        (self.root / "empty").mkdir()
        (self.root / "sub").mkdir()
        (self.root / "a.txt").write_bytes(b"same")
        (self.root / "sub" / "b.txt").write_bytes(b"same")
        (self.root / "other.bin").write_bytes(b"different")
        old = self.root / "old.log"
        old.write_bytes(b"old")
        old_time = time.time() - 3 * 365 * 24 * 3600
        os.utime(old, (old_time, old_time))

        result = scan_folder(self.root)
        self.assertEqual(result.file_count, 4)
        self.assertEqual(result.folder_count, 2)
        self.assertEqual(result.total_size, 20)
        self.assertEqual(len(result.duplicates), 1)
        self.assertEqual(result.duplicates[0]["文件数"], 2)
        self.assertEqual(len(result.duplicates[0]["SHA-256"]), 64)
        self.assertIn(str(self.root / "empty"), result.empty_folders)
        self.assertEqual([x["路径"] for x in result.old_files], [str(old)])

    def test_png_dimensions_and_reports(self):
        png = self.root / "tiny.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + struct.pack(">II", 13, 7) + b"\0" * 8)
        self.assertEqual(image_dimensions(png), (13, 7))
        result = scan_folder(self.root)
        output = Path(self.temp.name) / "reports"
        html_path, csv_path = write_reports(result, output)
        self.assertIn("文件夹体检报告", html_path.read_text(encoding="utf-8"))
        self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertIn("13×7", csv_path.read_text(encoding="utf-8-sig"))

    def test_does_not_follow_symlink_when_supported(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("do not scan", encoding="utf-8")
        link = self.root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("当前环境不允许创建目录链接")
        result = scan_folder(self.root)
        self.assertEqual(result.file_count, 0)
        self.assertEqual(result.folder_count, 0)

    def test_inaccessible_folder_is_recorded_instead_of_crashing(self):
        blocked = self.root / "blocked"
        blocked.mkdir()
        real_scandir = os.scandir

        def controlled_scandir(path):
            if Path(path) == blocked:
                raise PermissionError("模拟无权访问")
            return real_scandir(path)

        with patch("folder_health_checker.os.scandir", side_effect=controlled_scandir):
            result = scan_folder(self.root)
        self.assertEqual(result.folder_count, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]["操作"], "读取文件夹")
        self.assertIn(str(blocked), result.errors[0]["路径"])


if __name__ == "__main__":
    unittest.main()
