"""
AC verification tests for spec 058-02 (bug-fix core helper).

Run from the repo root:
    python3 -m unittest discover -s skills/bug-fix -p 'test_*.py'
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUG_PY = REPO_ROOT / "skills" / "bug-fix" / "bug.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from skills._common.parsing import parse_frontmatter  # noqa: E402


def run_bug(*args: str, cwd: Path | None = None,
            env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(BUG_PY), *args],
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        capture_output=True,
        text=True,
    )


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class BugCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self, rel: str) -> Path:
        return self.root / "docs" / "bugs" / rel

    def _fm(self, rel: str) -> dict:
        fields, _ = parse_frontmatter(self._bug(rel).read_text())
        return fields

    def test_new_allocates_local_number_and_schema(self):
        r = run_bug("new", "auth-crash", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-alpha"})
        self.assertEqual(r.returncode, 0, r.stderr)
        path = self._bug("001-auth-crash.md")
        self.assertTrue(path.is_file())
        fields = self._fm("001-auth-crash.md")
        self.assertEqual(fields["status"], "REPORTED")
        self.assertEqual(fields["claimed_by"], "wt-alpha")
        self.assertEqual(fields["security_surface"], "false")
        for key in (
            "tier",
            "severity",
            "regression_test",
            "red_confirmed_at",
            "green_confirmed_at",
            "fix_class",
            "escalated_to",
        ):
            self.assertIn(key, fields)
        body = path.read_text()
        for heading in (
            "## Symptom",
            "## Repro",
            "## Evidence",
            "## Hypotheses",
            "## Root cause",
            "## Fix class",
            "## Fix",
            "## Already tried",
            "## Regression test",
            "## Proof",
            "## Learning",
        ):
            self.assertIn(heading, body)

    def test_new_scans_existing_bug_numbers_locally(self):
        write(self._bug("001-old.md"), "---\nstatus: REPORTED\n---\n")
        r = run_bug("new", "second", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-alpha"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self._bug("002-second.md").is_file())

    def test_triage_persists_standard_tier_and_severity(self):
        run_bug("new", "wrong-total", "--project-dir", str(self.root),
                env={"JIG_CLAIM_ID": "wt-alpha"})
        r = run_bug(
            "triage", "001", "--tier", "standard", "--severity", "high",
            "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields = self._fm("001-wrong-total.md")
        self.assertEqual(fields["tier"], "standard")
        self.assertEqual(fields["severity"], "high")

    def test_triage_trivial_deescalates_and_removes_record(self):
        run_bug("new", "typo", "--project-dir", str(self.root),
                env={"JIG_CLAIM_ID": "wt-alpha"})
        r = run_bug(
            "triage", "001", "--tier", "trivial",
            "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        msg = r.stdout + r.stderr
        self.assertIn("tdd-loop", msg)
        self.assertIn("no bug record needed", msg)
        self.assertFalse(self._bug("001-typo.md").exists())

    def test_triage_refuses_direct_path_outside_docs_bugs(self):
        (self.root / "docs" / "bugs").mkdir(parents=True)
        outside = write(self.root / "docs" / "notes.md", "---\nstatus: x\n---\n")
        r = run_bug(
            "triage", str(outside), "--tier", "trivial",
            "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(outside.exists())
        self.assertIn("docs/bugs", r.stderr)

    def test_triage_refuses_direct_path_to_board_file(self):
        board = write(self.root / "docs" / "bugs" / "README.md", "# Bugs\n")
        r = run_bug(
            "triage", str(board), "--tier", "trivial",
            "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(board.exists())
        self.assertIn("NNN-slug.md", r.stderr)

    def test_triage_refuses_bare_board_filename(self):
        board = write(self.root / "docs" / "bugs" / "README.md", "# Bugs\n")
        r = run_bug(
            "triage", "README.md", "--tier", "trivial",
            "--project-dir", str(self.root),
            cwd=self.root,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(board.exists())
        self.assertIn("bug not found", r.stderr)

    def test_status_board_regenerates_and_preserves_notes(self):
        write(self._bug("001-alpha.md"), (
            "---\n"
            "status: REPORTED\n"
            "severity: high\n"
            "tier: standard\n"
            "claimed_by: wt-alpha\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class:\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))
        board = self.root / "docs" / "bugs" / "README.md"
        board.write_text(
            "# Bug Status Board\n\n"
            "| ID | slug | severity | tier | status | reproduces? | "
            "regression test | claimed_by | escalated_to | Notes |\n"
            "|----|------|----------|------|--------|-------------|"
            "-----------------|------------|--------------|-------|\n"
            "| 001 | alpha | high | standard | REPORTED | no | "
            "tests/test_alpha.py::test_bug | wt-alpha |  | keep me |\n"
        )
        r = run_bug("status-board", "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        text = board.read_text()
        self.assertIn("| ID | slug | severity | tier | status | reproduces? |", text)
        self.assertIn("| 001 | alpha | high | standard | REPORTED | no |", text)
        self.assertIn("tests/test_alpha.py::test_bug", text)
        self.assertIn("keep me", text)

    def test_pickup_refuses_foreign_open_claim(self):
        write(self._bug("001-alpha.md"), (
            "---\n"
            "status: REPORTED\n"
            "severity:\n"
            "tier:\n"
            "claimed_by: wt-other\n"
            "regression_test:\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class:\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))
        r = run_bug("pickup", "001", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-me"})
        self.assertNotEqual(r.returncode, 0)
        msg = r.stdout + r.stderr
        self.assertIn("wt-other", msg)
        self.assertIn("--release", msg)
        self.assertEqual(self._fm("001-alpha.md")["claimed_by"], "wt-other")

    def test_release_clears_claim_and_appends_reason(self):
        write(self._bug("001-alpha.md"), (
            "---\n"
            "status: REPORTED\n"
            "severity:\n"
            "tier:\n"
            "claimed_by: wt-other\n"
            "regression_test:\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class:\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))
        r = run_bug(
            "pickup", "001", "--release", "--reason", "worktree abandoned",
            "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        text = self._bug("001-alpha.md").read_text()
        fields = self._fm("001-alpha.md")
        self.assertNotIn("claimed_by", fields)
        self.assertIn("## Release log", text)
        self.assertIn("worktree abandoned", text)
        self.assertIn("wt-other", text)


if __name__ == "__main__":
    unittest.main()
