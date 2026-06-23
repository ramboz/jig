"""
AC verification tests for spec 058 (bug-fix helper).

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


class BugTransitionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self, rel: str = "001-alpha.md") -> Path:
        return self.root / "docs" / "bugs" / rel

    def _write_bug(self, *, status: str = "REPORTED", tier: str = "standard",
                   fix_class: str = "", regression_test: str = "tests/test_alpha.py::test_bug",
                   evidence: str = "trace: log line 7",
                   hypotheses: str = "- [ ] cache race\n- [x] parser bug\n") -> Path:
        return write(self._bug(), (
            "---\n"
            f"status: {status}\n"
            "severity: high\n"
            f"tier: {tier}\n"
            "claimed_by: wt-alpha\n"
            f"regression_test: {regression_test}\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            f"fix_class: {fix_class}\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n\n"
            "## Repro\n\n"
            f"## Evidence\n\n{evidence}\n\n"
            f"## Hypotheses\n\n{hypotheses}\n"
            "## Root cause\n\n"
            "## Fix class\n\n"
            "## Fix\n\n"
            "## Already tried\n\n"
            "## Regression test\n\n"
            "## Proof\n\n"
            "## Learning\n"
        ))

    def _fm(self) -> dict:
        fields, _ = parse_frontmatter(self._bug().read_text())
        return fields

    def _fake_tdd(self, code: int) -> Path:
        script = self.root / f"fake_tdd_{code}.py"
        script.write_text(
            "import sys\n"
            "print('fake tdd', ' '.join(sys.argv[1:]))\n"
            f"raise SystemExit({code})\n"
        )
        return script

    def test_transition_reported_to_diagnosing_sets_status(self):
        self._write_bug(status="REPORTED")
        r = run_bug(
            "transition", "001", "DIAGNOSING", "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "DIAGNOSING")

    def test_transition_refuses_invalid_status_membership(self):
        self._write_bug(status="REPORTED")
        r = run_bug(
            "transition", "001", "BOGUS", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid status", r.stderr)
        self.assertEqual(self._fm()["status"], "REPORTED")

    def test_transition_refuses_illegal_ordering(self):
        self._write_bug(status="REPORTED")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid transition", r.stderr)
        self.assertEqual(self._fm()["status"], "REPORTED")

    def test_gnarly_root_caused_requires_diagnosis_evidence(self):
        self._write_bug(
            status="DIAGNOSING", tier="gnarly", evidence="", hypotheses="- [x] one\n",
        )
        r = run_bug(
            "transition", "001", "ROOT_CAUSED", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("hypotheses", r.stderr)
        self.assertIn("evidence", r.stderr)
        self.assertEqual(self._fm()["status"], "DIAGNOSING")

    def test_standard_root_caused_warns_but_does_not_block(self):
        self._write_bug(
            status="DIAGNOSING", tier="standard", evidence="", hypotheses="- [x] one\n",
        )
        r = run_bug(
            "transition", "001", "ROOT_CAUSED", "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warning", r.stderr.lower())
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_diagnose_gate_bypass_allows_incomplete_gnarly_diagnosis(self):
        self._write_bug(
            status="DIAGNOSING", tier="gnarly", evidence="", hypotheses="- [x] one\n",
        )
        r = run_bug(
            "transition", "001", "ROOT_CAUSED", "--project-dir", str(self.root),
            env={"JIG_BUG_DIAGNOSE_GATE": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_fixing_requires_declared_fix_class(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fix_class", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_fixing_refuses_unknown_fix_class(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="big_rewrite")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("fix_class", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_fixing_red_gate_stamps_red_confirmed_at(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields = self._fm()
        self.assertEqual(fields["status"], "FIXING")
        self.assertRegex(fields["red_confirmed_at"], r"\d{4}-\d{2}-\d{2}")

    def test_fixing_exit_zero_refuses_test_that_already_passes(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(0))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("passes without a fix", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_fixing_exit_two_fails_closed_as_environment_error(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(2))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("environment error", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_reviewed_green_gate_stamps_green_confirmed_at(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(0))},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields = self._fm()
        self.assertEqual(fields["status"], "REVIEWED")
        self.assertRegex(fields["green_confirmed_at"], r"\d{4}-\d{2}-\d{2}")

    def test_failed_green_check_routes_back_to_diagnosing_and_logs_attempt(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self._fm()["status"], "DIAGNOSING")
        text = self._bug().read_text()
        self.assertIn("## Already tried", text)
        self.assertIn("green check failed", text)

    def test_red_test_gate_bypass_skips_tdd_and_transitions_to_fixing(self):
        self._write_bug(status="ROOT_CAUSED", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0", "JIG_TDD_HELPER": str(self.root / "missing.py")},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_green_test_gate_bypass_skips_tdd_and_transitions_to_reviewed(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0", "JIG_TDD_HELPER": str(self.root / "missing.py")},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")


if __name__ == "__main__":
    unittest.main()
