"""Hook script tests for slice 027-01 (jig-post-edit-verify.sh).

Tests the PostToolUse hook by piping mock hook payloads in via stdin and
asserting on stdout JSON, stderr, and exit code. Mirrors the pattern used by
`skills/memory-sync/test_hooks.py`.

Run from the repo root:
    python3 scripts/test_post_edit_verify.py
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-post-edit-verify.sh"


def run_hook(payload: dict, *, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Drop the opt-out by default so tests pin the on-by-default behavior.
    env.pop("JIG_POST_EDIT_VERIFY", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


def parse(result: subprocess.CompletedProcess):
    """Assert exit 0, return parsed stdout dict or None if no output."""
    assert result.returncode == 0, (
        f"hook should never block (got {result.returncode}); "
        f"stderr={result.stderr!r}"
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


class EditVerificationTests(unittest.TestCase):
    """AC #2 — Edit verification: new_string present in file after edit."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-edit-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _file(self, name: str, content: str) -> Path:
        p = Path(self.tmpdir) / name
        p.write_text(content)
        return p

    def test_edit_with_new_string_present_is_silent(self):
        f = self._file("a.txt", "hello brave new world")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "hello",
                "new_string": "hello brave",
            },
        }))
        self.assertIsNone(out, "new_string present → no warning expected")

    def test_edit_with_new_string_missing_warns(self):
        # File on disk does not contain the claimed new_string → silent no-op
        # edit. Hook should warn.
        f = self._file("a.txt", "this file has unrelated content")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "foo",
                "new_string": "BRAND_NEW_SUBSTRING_NOT_IN_FILE",
            },
        }))
        self.assertIsNotNone(out, "missing new_string should warn")
        self.assertTrue(out.get("continue"))
        self.assertIn("BRAND_NEW_SUBSTRING_NOT_IN_FILE", out["additionalContext"])
        self.assertIn("Re-read and retry", out["additionalContext"])

    def test_edit_deletion_with_old_string_gone_is_silent(self):
        f = self._file("a.txt", "after deletion: rest of file")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "TO_BE_DELETED",
                "new_string": "",
            },
        }))
        self.assertIsNone(out, "deletion: old_string absent → no warning")

    def test_edit_deletion_with_old_string_still_present_warns(self):
        # File still contains old_string → deletion didn't take.
        f = self._file("a.txt", "this STILL_HERE was supposed to be deleted")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "STILL_HERE",
                "new_string": "",
            },
        }))
        self.assertIsNotNone(out)
        self.assertIn("STILL_HERE", out["additionalContext"])
        self.assertIn("deletion", out["additionalContext"].lower())


class WriteVerificationTests(unittest.TestCase):
    """AC #3 — Write verification: first 200 bytes of file match requested."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-write-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _file(self, name: str, content: str) -> Path:
        p = Path(self.tmpdir) / name
        p.write_text(content)
        return p

    def test_write_with_matching_prefix_is_silent(self):
        content = "first line\nsecond line\nthird line\n"
        f = self._file("a.txt", content)
        out = parse(run_hook({
            "tool_name": "Write",
            "tool_input": {"file_path": str(f), "content": content},
        }))
        self.assertIsNone(out, "matching content → no warning")

    def test_write_with_drifted_prefix_warns(self):
        # File contents differ from what Write claimed it wrote.
        f = self._file("a.txt", "ACTUAL FILE CONTENTS — drifted from claim")
        out = parse(run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(f),
                "content": "CLAIMED CONTENT — not what's on disk",
            },
        }))
        self.assertIsNotNone(out, "prefix mismatch should warn")
        self.assertIn("post-write check failed", out["additionalContext"])

    def test_write_only_checks_first_200_bytes(self):
        # Beyond byte 200, contents may differ without warning.
        prefix = "X" * 200
        f = self._file("a.txt", prefix + "ACTUAL_TAIL")
        out = parse(run_hook({
            "tool_name": "Write",
            "tool_input": {"file_path": str(f), "content": prefix + "CLAIMED_TAIL"},
        }))
        self.assertIsNone(out, "tail beyond 200 bytes is not checked")


class MultiEditVerificationTests(unittest.TestCase):
    """AC #4 — MultiEdit: each edit verified individually."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-multi-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _file(self, name: str, content: str) -> Path:
        p = Path(self.tmpdir) / name
        p.write_text(content)
        return p

    def test_multiedit_all_present_is_silent(self):
        f = self._file("a.txt", "alpha beta gamma delta")
        out = parse(run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(f),
                "edits": [
                    {"old_string": "x", "new_string": "alpha"},
                    {"old_string": "y", "new_string": "gamma"},
                ],
            },
        }))
        self.assertIsNone(out, "all edits present → no warning")

    def test_multiedit_one_missing_warns_with_index(self):
        f = self._file("a.txt", "alpha beta gamma")
        out = parse(run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(f),
                "edits": [
                    {"old_string": "x", "new_string": "alpha"},
                    {"old_string": "y", "new_string": "MISSING_FROM_FILE"},
                ],
            },
        }))
        self.assertIsNotNone(out)
        self.assertIn("MISSING_FROM_FILE", out["additionalContext"])
        # Index marker (edit 2/2) helps the agent pinpoint which one drifted.
        self.assertIn("(edit 2/2)", out["additionalContext"])

    def test_multiedit_deletion_check(self):
        f = self._file("a.txt", "STILL_THERE plus other content")
        out = parse(run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(f),
                "edits": [
                    {"old_string": "STILL_THERE", "new_string": ""},
                ],
            },
        }))
        self.assertIsNotNone(out)
        self.assertIn("STILL_THERE", out["additionalContext"])


class SoftWarningShapeTests(unittest.TestCase):
    """AC #5 — output is {"continue": true, "additionalContext": ...}."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-shape-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_warning_payload_shape(self):
        f = Path(self.tmpdir) / "a.txt"
        f.write_text("unrelated")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f), "old_string": "x", "new_string": "WONT_FIND",
            },
        }))
        self.assertIsNotNone(out)
        self.assertIs(out.get("continue"), True,
                      "must never set continue:false — soft warning only")
        self.assertIsInstance(out.get("additionalContext"), str)
        self.assertGreater(len(out["additionalContext"]), 0)


class OptOutTests(unittest.TestCase):
    """AC #6 — JIG_POST_EDIT_VERIFY=0 disables the hook entirely."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-optout-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_opt_out_silences_warning(self):
        f = Path(self.tmpdir) / "a.txt"
        f.write_text("unrelated")
        result = run_hook(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(f),
                    "old_string": "x",
                    "new_string": "WOULD_OTHERWISE_WARN",
                },
            },
            env_overrides={"JIG_POST_EDIT_VERIFY": "0"},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "",
                         "opt-out should produce no output")

    def test_default_on_warns(self):
        # Symmetric assertion: with the env var unset, the same payload warns.
        f = Path(self.tmpdir) / "a.txt"
        f.write_text("unrelated")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "x",
                "new_string": "WOULD_OTHERWISE_WARN",
            },
        }))
        self.assertIsNotNone(out, "default-on should warn")


class BoundedReadTests(unittest.TestCase):
    """AC #7 — Hook never reads more than 64KB from any file."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-bounded-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_10mb_file_with_edit_beyond_64kb_exits_silently(self):
        """If the substring lives past the 64KB read budget on a 10MB file,
        the hook returns silently (best-effort) rather than false-warning or
        full-file-reading."""
        f = Path(self.tmpdir) / "big.txt"
        # 10MB of filler, with the "edit target" planted at offset ~1MB.
        filler_head = b"a" * (1024 * 1024)
        needle = b"\nNEEDLE_AT_1MB_OFFSET\n"
        filler_tail = b"b" * (10 * 1024 * 1024 - len(filler_head) - len(needle))
        f.write_bytes(filler_head + needle + filler_tail)

        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "ignored",
                "new_string": "NEEDLE_AT_1MB_OFFSET",
            },
        }))
        # Best-effort: file is larger than the 64KB budget and the needle
        # isn't in the head. Hook cannot confirm a miss, so it stays silent.
        self.assertIsNone(out,
                          "file > 64KB with needle past head → silent (best-effort)")

    def test_10mb_file_with_needle_in_head_finds_it(self):
        """Sanity check the inverse: if the needle IS within the first 64KB
        of a 10MB file, the hook finds it and doesn't warn."""
        f = Path(self.tmpdir) / "big.txt"
        head = b"HEAD_NEEDLE_HERE " + (b"x" * 1024)
        tail = b"y" * (10 * 1024 * 1024 - len(head))
        f.write_bytes(head + tail)

        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "ignored",
                "new_string": "HEAD_NEEDLE_HERE",
            },
        }))
        self.assertIsNone(out, "needle in first 64KB → no warning")

    def test_small_file_with_missing_needle_warns(self):
        """Symmetric: small files (fully read) still warn on a real miss."""
        f = Path(self.tmpdir) / "small.txt"
        f.write_text("small file with unrelated content")
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "ignored",
                "new_string": "DEFINITELY_NOT_THERE",
            },
        }))
        self.assertIsNotNone(out,
                             "small file with missing needle → warning")


class RobustnessTests(unittest.TestCase):
    """AC #8 + general robustness: missing files, garbage payloads, unknown
    tool names — never block."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-027-robust-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_file_exits_silently(self):
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(Path(self.tmpdir) / "does-not-exist.txt"),
                "old_string": "x", "new_string": "y",
            },
        }))
        self.assertIsNone(out, "missing file → silent, never blocks")

    def test_empty_file_path_exits_silently(self):
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {"old_string": "x", "new_string": "y"},
        }))
        self.assertIsNone(out)

    def test_unknown_tool_name_exits_silently(self):
        out = parse(run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
        }))
        self.assertIsNone(out)

    def test_garbage_payload_exits_silently(self):
        result = run_hook({"completely": "unexpected", "shape": True})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_invalid_stdin_json_exits_zero(self):
        env = os.environ.copy()
        env.pop("JIG_POST_EDIT_VERIFY", None)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="not even json",
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0,
                         "invalid JSON must not block")


if __name__ == "__main__":
    unittest.main()
