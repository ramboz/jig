"""Tests for skills/_common/atomic_io.py — slice 032-01.

Covers AC #2 cases (a–e):
  (a) happy path overwrites an existing file with new content;
  (b) happy path creates a new file when the destination doesn't exist;
  (c) the tmp file is in `path.parent` (verified by monkey-patching
      `tempfile.NamedTemporaryFile` to capture the `dir=` argument);
  (d) an exception during the `os.replace` call cleans up the tmp file;
  (e) unicode content round-trips correctly (utf-8 encoding).
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomic_io import atomic_write_text


class AtomicWriteTextTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_overwrites_existing_file(self):
        """(a) happy path overwrites an existing file with new content."""
        target = self.tmpdir / "existing.txt"
        target.write_text("old content")

        atomic_write_text(target, "new content")

        self.assertEqual(target.read_text(), "new content")

    def test_creates_new_file_when_destination_absent(self):
        """(b) happy path creates a new file when the destination doesn't
        exist."""
        target = self.tmpdir / "fresh.txt"
        self.assertFalse(target.exists())

        atomic_write_text(target, "hello")

        self.assertTrue(target.exists())
        self.assertEqual(target.read_text(), "hello")

    def test_tmp_file_lives_in_path_parent(self):
        """(c) the tmp file is in `path.parent` (verified by monkey-patching
        `tempfile.NamedTemporaryFile` to capture the `dir=` argument)."""
        target = self.tmpdir / "subdir" / "out.txt"
        target.parent.mkdir(parents=True, exist_ok=True)

        captured = {}
        real_named_temp_file = tempfile.NamedTemporaryFile

        def spy(*args, **kwargs):
            captured["dir"] = kwargs.get("dir")
            captured["delete"] = kwargs.get("delete")
            captured["suffix"] = kwargs.get("suffix")
            return real_named_temp_file(*args, **kwargs)

        with mock.patch("atomic_io.tempfile.NamedTemporaryFile", side_effect=spy):
            atomic_write_text(target, "data")

        self.assertEqual(Path(captured["dir"]), target.parent)
        self.assertFalse(captured["delete"])
        self.assertEqual(captured["suffix"], ".tmp")

    def test_replace_exception_cleans_up_tmp(self):
        """(d) an exception during the `os.replace` call cleans up the tmp
        file (mock `os.replace` to raise; assert no leftover `.tmp` in
        `path.parent`)."""
        target = self.tmpdir / "target.txt"

        with mock.patch(
            "atomic_io.os.replace",
            side_effect=OSError("simulated replace failure"),
        ):
            with self.assertRaises(OSError):
                atomic_write_text(target, "payload")

        leftover = list(self.tmpdir.glob("*.tmp"))
        self.assertEqual(
            leftover,
            [],
            f"expected no .tmp leftovers, found {leftover}",
        )
        self.assertFalse(target.exists())

    def test_unicode_roundtrip_utf8(self):
        """(e) unicode content round-trips correctly (utf-8 encoding)."""
        target = self.tmpdir / "unicode.txt"
        content = "héllo — 世界 🌍 ✨"

        atomic_write_text(target, content)

        self.assertEqual(target.read_text(encoding="utf-8"), content)
        # And the on-disk bytes should be the utf-8 encoding.
        self.assertEqual(target.read_bytes(), content.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
