"""
AC verification tests for spec 058 (bug-fix helper).

Run from the repo root:
    python3 -m unittest discover -s skills/bug-fix -p 'test_*.py'
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BUG_PY = REPO_ROOT / "skills" / "bug-fix" / "bug.py"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The three existing readers of the `.jig/spec-ref` marker (slice 098-04 AC3).
# A bug-shaped marker must stay invisible to all three.
from hooks.scripts.lib.read_attribution import (  # noqa: E402
    read_spec_ref as _ra_read_spec_ref,
)
from scripts.usage import read_spec_ref_marker as _usage_read_spec_ref  # noqa: E402
from skills._common.gate_telemetry import (  # noqa: E402
    read_spec_ref as _gt_read_spec_ref,
)
from skills._common.parsing import parse_frontmatter  # noqa: E402
from skills._common.test_reservation import (  # noqa: E402
    CAPTURED_GH006,
    CAPTURED_GH013,
)


def load_bug_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bug_module_058", BUG_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            "main_repro_checked_at",
            "main_repro_ref",
            "main_repro_result",
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

    def test_status_board_default_preamble_links_spec_board(self):
        write(self._bug("001-alpha.md"), (
            "---\n"
            "status: REPORTED\n"
            "severity: high\n"
            "tier: standard\n"
            "claimed_by:\n"
            "regression_test:\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class:\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))
        board = self.root / "docs" / "bugs" / "README.md"
        self.assertFalse(board.exists(), "test setup should exercise default preamble")

        r = run_bug("status-board", "--project-dir", str(self.root))

        self.assertEqual(r.returncode, 0, r.stderr)
        text = board.read_text()
        preamble = text.split("| ID |", 1)[0]
        self.assertIn("../specs/README.md", preamble)
        self.assertIn("Spec Status Board", preamble)

    def test_status_board_counts_main_recheck_as_reproducing(self):
        write(self._bug("001-alpha.md"), (
            "---\n"
            "status: ROOT_CAUSED\n"
            "severity: high\n"
            "tier: standard\n"
            "claimed_by: wt-alpha\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "main_repro_checked_at: 2026-06-29\n"
            "main_repro_ref: origin/main@abc123\n"
            "main_repro_result: reproduces\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class: local_patch\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))
        r = run_bug("status-board", "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.root / "docs" / "bugs" / "README.md").read_text()
        self.assertIn("| 001 | alpha | high | standard | ROOT_CAUSED | yes |", text)

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
                   hypotheses: str = "- [ ] cache race\n- [x] parser bug\n",
                   security_surface: str = "false",
                   main_repro_result: str = "reproduces") -> Path:
        return write(self._bug(), (
            "---\n"
            f"status: {status}\n"
            "severity: high\n"
            f"tier: {tier}\n"
            "claimed_by: wt-alpha\n"
            f"regression_test: {regression_test}\n"
            f"main_repro_checked_at: {'2026-06-29' if main_repro_result else ''}\n"
            f"main_repro_ref: {'origin/main@abc123' if main_repro_result else ''}\n"
            f"main_repro_result: {main_repro_result}\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            f"fix_class: {fix_class}\n"
            f"security_surface: {security_surface}\n"
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

    def _write_review(self, pass_name: str, verdict: str = "pass") -> Path:
        return write(
            self.root / "docs" / "bugs" / "reviews" / f"bug-001-{pass_name}.md",
            "---\n"
            "bug: 001\n"
            f"pass: {pass_name}\n"
            f"verdict: {verdict}\n"
            "reviewer: reviewer\n"
            "reviewed_at: 2026-06-23T00:00:00Z\n"
            "prompt_source: test\n"
            "---\n\n"
            "VERDICT body\n",
        )

    def _write_required_reviews(self, *extra_passes: str) -> None:
        self._write_review("bug-review")
        self._write_review("craft")
        for pass_name in extra_passes:
            self._write_review(pass_name)

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

    def test_fixing_requires_main_recheck_after_root_caused(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("main recheck required", r.stderr)
        self.assertIn("main_repro_result", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_main_check_reproduces_stamps_fields_and_allows_fixing(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "main-check", "001", "--result", "reproduces",
            "--ref", "origin/main@def456",
            "--evidence", "original reported repro still fails",
            "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields = self._fm()
        self.assertEqual(fields["status"], "ROOT_CAUSED")
        self.assertEqual(fields["main_repro_ref"], "origin/main@def456")
        self.assertEqual(fields["main_repro_result"], "reproduces")
        self.assertRegex(fields["main_repro_checked_at"], r"\d{4}-\d{2}-\d{2}")
        self.assertIn("original reported repro still fails", self._bug().read_text())

        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd(1))},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_main_check_requires_evidence_note(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "main-check", "001", "--result", "reproduces",
            "--ref", "origin/main@def456",
            "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("required", r.stderr)
        self.assertIn("--evidence", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_main_check_resolved_on_main_marks_terminal_status(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "main-check", "001", "--result", "resolved-on-main",
            "--ref", "origin/main@def456",
            "--evidence", "original reported repro no longer fails",
            "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields = self._fm()
        self.assertEqual(fields["status"], "RESOLVED_ON_MAIN")
        self.assertEqual(fields["main_repro_result"], "resolved_on_main")
        self.assertIn("original reported repro no longer fails", self._bug().read_text())

    def test_direct_transition_cannot_mark_resolved_on_main_without_check(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "transition", "001", "RESOLVED_ON_MAIN",
            "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid transition", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_main_recheck_gate_bypass_allows_fixing_without_stamp(self):
        self._write_bug(
            status="ROOT_CAUSED",
            fix_class="local_patch",
            main_repro_result="",
        )
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={
                "JIG_BUG_MAIN_CHECK_GATE": "0",
                "JIG_TDD_HELPER": str(self._fake_tdd(1)),
            },
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

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
        self._write_required_reviews()
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
        self._write_required_reviews()
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
        self._write_required_reviews()
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0", "JIG_TDD_HELPER": str(self.root / "missing.py")},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def test_reviewed_refuses_missing_bug_review_evidence(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0"},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bug-review", r.stderr)
        self.assertIn("record-review", r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_reviewed_refuses_failing_bug_review_evidence(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        self._write_review("bug-review", verdict="needs-changes")
        self._write_review("craft")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0"},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("needs-changes", r.stderr)
        self.assertIn("bug-review", r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_reviewed_refuses_missing_craft_evidence_after_bug_review(self):
        self._write_bug(status="FIXING", fix_class="local_patch")
        self._write_review("bug-review")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0"},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr)
        self.assertIn("record-review", r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_reviewed_requires_security_when_security_surface_truthy(self):
        self._write_bug(
            status="FIXING", fix_class="local_patch", security_surface="YES",
        )
        self._write_required_reviews()
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0"},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("security", r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

        self._write_review("security")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_BUG_TEST_GATE": "0"},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def _write_learning(self, text: str = "- Bug 001: learned the cache race pattern.\n") -> Path:
        return write(self.root / "docs" / "memory" / "learnings.md", text)

    def test_done_refuses_missing_learning_even_with_review_evidence(self):
        self._write_bug(status="REVIEWED", fix_class="local_patch")
        self._write_required_reviews()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("learning", r.stderr.lower())
        self.assertIn("docs/memory/learnings.md", r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def test_done_revalidates_review_evidence(self):
        self._write_bug(status="REVIEWED", fix_class="local_patch")
        self._write_learning()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("review evidence", r.stderr.lower())
        self.assertIn("bug-review", r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def test_standard_reviewed_can_close_done_with_reviews_and_learning(self):
        self._write_bug(status="REVIEWED", fix_class="local_patch", tier="standard")
        self._write_required_reviews()
        self._write_learning()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "DONE")

    def test_gnarly_bug_requires_verified_before_done(self):
        self._write_bug(status="REVIEWED", fix_class="local_patch", tier="gnarly")
        self._write_required_reviews()
        self._write_learning()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("VERIFIED", r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def test_security_surface_requires_verified_before_done(self):
        self._write_bug(
            status="REVIEWED", fix_class="local_patch",
            tier="standard", security_surface="yes",
        )
        self._write_required_reviews("security")
        self._write_learning()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("VERIFIED", r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

    def test_verified_requires_original_repro_attestation_in_proof(self):
        self._write_bug(status="REVIEWED", fix_class="local_patch", tier="gnarly")
        r = run_bug(
            "transition", "001", "VERIFIED", "--project-dir", str(self.root),
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("original reported repro", r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")

        text = self._bug().read_text()
        text = text.replace(
            "## Proof\n\n",
            "## Proof\n\nAttested re-run of original reported repro on 2026-06-23.\n\n",
        )
        self._bug().write_text(text)
        r = run_bug(
            "transition", "001", "VERIFIED", "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "VERIFIED")

    def test_verified_gnarly_can_close_done_with_reviews_and_learning(self):
        self._write_bug(status="VERIFIED", fix_class="local_patch", tier="gnarly")
        self._write_required_reviews()
        self._write_learning()
        r = run_bug(
            "transition", "001", "DONE", "--project-dir", str(self.root),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "DONE")


class BugEscalationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self) -> Path:
        return self.root / "docs" / "bugs" / "001-alpha.md"

    def test_escalate_opens_spec_links_both_directions_and_parks_bug(self):
        write(self._bug(), (
            "---\n"
            "status: ROOT_CAUSED\n"
            "severity: high\n"
            "tier: gnarly\n"
            "claimed_by: wt-alpha\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class: structural_fix\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "# Bug 001: alpha\n\n"
            "## Symptom\n\nDesign gap.\n"
        ))
        fake_workflow = self.root / "fake_workflow.py"
        spec_dir = self.root / "docs" / "specs" / "123-alpha"
        spec_path = spec_dir / "spec.md"
        fake_workflow.write_text(
            "from pathlib import Path\n"
            "import sys\n"
            f"p = Path({str(spec_path)!r})\n"
            "p.parent.mkdir(parents=True, exist_ok=True)\n"
            "p.write_text('---\\nstatus: DRAFT\\n---\\n\\n# Spec 123\\n')\n"
            "print('reserved 123-alpha')\n"
            "print(p)\n"
        )
        r = run_bug(
            "escalate", "001", "--project-dir", str(self.root),
            env={"JIG_WORKFLOW_HELPER": str(fake_workflow)},
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        fields, _ = parse_frontmatter(self._bug().read_text())
        self.assertEqual(fields["status"], "ESCALATED")
        self.assertEqual(fields["escalated_to"], "123")
        spec_text = spec_path.read_text()
        spec_fields, _ = parse_frontmatter(spec_text)
        self.assertEqual(spec_fields["originated_from_bug"], "001")
        self.assertIn("originated from bug 001", spec_text.lower())


class BugReservationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_push_reservation_race_cleans_ephemeral_worktree(self):
        module = load_bug_module()
        calls: list[tuple[list[str], Path]] = []

        def fake_run(argv, cwd):
            argv = list(argv)
            cwd = Path(cwd)
            calls.append((argv, cwd))
            if argv[:3] == ["git", "worktree", "add"]:
                Path(argv[4]).mkdir(parents=True, exist_ok=True)
                return 0, "", ""
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return 0, "abc123\n", ""
            if argv[:2] == ["git", "push"]:
                return 1, "", "rejected non-fast-forward"
            return 0, "", ""

        with patch.object(module, "_run", side_effect=fake_run):
            with self.assertRaises(module.BugError) as cm:
                module.reserve_bug_on_origin(self.root, "alpha", pr_mode=False)

        self.assertIn("race-on-push", str(cm.exception))
        self.assertTrue(
            any(c[0][:3] == ["git", "worktree", "remove"] for c in calls),
            "race path must remove the ephemeral worktree",
        )

    def _fake_run_factory(self, calls, main_push_rc, main_push_err):
        """Build a fake _run that drives reservation to either a direct
        main push (main_push_rc) or, on refusal, the PR-fallback branch."""
        def fake_run(argv, cwd):
            argv = list(argv)
            calls.append((argv, Path(cwd)))
            if argv[:3] == ["git", "worktree", "add"]:
                Path(argv[4]).mkdir(parents=True, exist_ok=True)
                return 0, "", ""
            if argv[:3] == ["git", "rev-parse", "HEAD"]:
                return 0, "abc123\n", ""
            if argv[:4] == ["git", "config", "--get", "remote.origin.url"]:
                return 0, "https://github.com/u/r.git\n", ""
            if argv[:2] == ["git", "push"]:
                # argv[3] is the refspec sha:refs/heads/<dest>
                if argv[3].endswith(":refs/heads/main"):
                    return main_push_rc, "", main_push_err
                return 0, "", ""  # PR-fallback branch push
            if argv[:2] == ["gh", "pr"]:
                return 0, "https://github.com/u/r/pull/42\n", ""
            return 0, "", ""
        return fake_run

    def test_pr_mode_reserves_via_branch_and_opens_pr(self):
        module = load_bug_module()
        calls: list[tuple[list[str], Path]] = []
        fake_run = self._fake_run_factory(calls, main_push_rc=0, main_push_err="")

        with patch.object(module, "_run", side_effect=fake_run), \
                patch.object(module.shutil, "which", return_value="/usr/bin/gh"):
            number, slug = module.reserve_bug_on_origin(
                self.root, "alpha", pr_mode=True)

        self.assertEqual((number, slug), ("001", "alpha"))
        # --pr never pushes straight to main; it pushes the reserve branch.
        self.assertFalse(
            any(c[0][:2] == ["git", "push"]
                and c[0][3].endswith(":refs/heads/main") for c in calls),
            "--pr mode must not push directly to main",
        )
        self.assertTrue(
            any(c[0][:2] == ["git", "push"]
                and c[0][3].endswith(":refs/heads/reserve/bug-001-alpha")
                for c in calls),
            "--pr mode must push the reserve/bug-* branch",
        )
        self.assertTrue(
            any(c[0][:2] == ["gh", "pr"] for c in calls),
            "--pr mode must open a PR via gh",
        )
        self.assertTrue(
            any(c[0][:3] == ["git", "worktree", "remove"] for c in calls),
            "--pr path must remove the ephemeral worktree",
        )

    def test_protected_branch_push_falls_back_to_pr(self):
        module = load_bug_module()
        calls: list[tuple[list[str], Path]] = []
        # Direct push to main refused by branch protection (GH006). The stderr
        # is the CAPTURED multi-line refusal, including the ` ! [remote
        # rejected]` line that made the old classifier read this as a race.
        fake_run = self._fake_run_factory(
            calls, main_push_rc=1,
            main_push_err=CAPTURED_GH006)

        with patch.object(module, "_run", side_effect=fake_run), \
                patch.object(module.shutil, "which", return_value="/usr/bin/gh"):
            number, slug = module.reserve_bug_on_origin(
                self.root, "alpha", pr_mode=False)

        self.assertEqual((number, slug), ("001", "alpha"))
        # It must attempt the direct main push first, then fall back.
        self.assertTrue(
            any(c[0][:2] == ["git", "push"]
                and c[0][3].endswith(":refs/heads/main") for c in calls),
            "protection path must attempt the direct main push first",
        )
        self.assertTrue(
            any(c[0][:2] == ["git", "push"]
                and c[0][3].endswith(":refs/heads/reserve/bug-001-alpha")
                for c in calls),
            "protection fallback must push the reserve/bug-* branch",
        )
        self.assertTrue(
            any(c[0][:2] == ["gh", "pr"] for c in calls),
            "protection fallback must open a PR via gh",
        )
        self.assertTrue(
            any(c[0][:3] == ["git", "worktree", "remove"] for c in calls),
            "protection fallback must remove the ephemeral worktree",
        )

    def test_ruleset_gh013_push_falls_back_to_pr(self):
        # issue #147 gap 1 — a repository-rulesets refusal (GH013) must route to
        # the PR fallback the same way a classic GH006 does. Its trailer is
        # `push declined due to repository rule violations`, which no older
        # protection signal matched.
        module = load_bug_module()
        calls: list[tuple[list[str], Path]] = []
        fake_run = self._fake_run_factory(
            calls, main_push_rc=1, main_push_err=CAPTURED_GH013)

        with patch.object(module, "_run", side_effect=fake_run), \
                patch.object(module.shutil, "which", return_value="/usr/bin/gh"):
            number, slug = module.reserve_bug_on_origin(
                self.root, "alpha", pr_mode=False)

        self.assertEqual((number, slug), ("001", "alpha"))
        self.assertTrue(
            any(c[0][:2] == ["git", "push"]
                and c[0][3].endswith(":refs/heads/reserve/bug-001-alpha")
                for c in calls),
            "GH013 fallback must push the reserve/bug-* branch",
        )
        self.assertTrue(
            any(c[0][:2] == ["gh", "pr"] for c in calls),
            "GH013 fallback must open a PR via gh",
        )

    def test_pr_fallback_refuses_when_gh_missing(self):
        module = load_bug_module()
        calls: list[tuple[list[str], Path]] = []
        fake_run = self._fake_run_factory(calls, main_push_rc=0, main_push_err="")

        with patch.object(module, "_run", side_effect=fake_run), \
                patch.object(module.shutil, "which", return_value=None):
            with self.assertRaises(module.BugError) as cm:
                module.reserve_bug_on_origin(self.root, "alpha", pr_mode=True)

        self.assertIn("gh", str(cm.exception).lower())
        self.assertTrue(
            any(c[0][:3] == ["git", "worktree", "remove"] for c in calls),
            "gh-missing refusal must still remove the ephemeral worktree",
        )


class TerminalSegregationTests(unittest.TestCase):
    """Bug 004 (issue #76): the status board must segregate terminal
    non-DONE rows (ESCALATED / RESOLVED_ON_MAIN) into a dedicated section,
    mirroring the spec board's `## Deferred slices` / `## Abandoned slices`
    split, so closure is legible at a glance. DONE stays in the active table
    (terminal-success, never the confusing case)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self, rel: str) -> Path:
        return self.root / "docs" / "bugs" / rel

    def _write_bug(self, rel: str, *, status: str, slug: str,
                   escalated_to: str = "", severity: str = "medium",
                   tier: str = "standard") -> None:
        write(self._bug(rel), (
            "---\n"
            f"status: {status}\n"
            f"severity: {severity}\n"
            f"tier: {tier}\n"
            "claimed_by:\n"
            "regression_test:\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class:\n"
            "security_surface: false\n"
            f"escalated_to: {escalated_to}\n"
            "---\n\n"
            f"# Bug: {slug}\n\n## Symptom\n"
        ))

    def _board_text(self) -> str:
        r = run_bug("status-board", "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        return (self.root / "docs" / "bugs" / "README.md").read_text()

    def test_escalated_bug_rendered_under_terminal_section(self):
        self._write_bug("001-alpha.md", status="REPORTED", slug="alpha")
        self._write_bug("002-beta.md", status="ESCALATED", slug="beta",
                        escalated_to="099")
        text = self._board_text()

        self.assertIn("## Terminal", text,
                      "escalated bug must produce a Terminal section heading")
        heading_at = text.index("## Terminal")
        active_at = text.index("| 001 | alpha |")
        terminal_at = text.index("| 002 | beta |")
        self.assertLess(active_at, heading_at,
                        "active REPORTED row must stay above the Terminal heading")
        self.assertLess(heading_at, terminal_at,
                        "ESCALATED row must appear below the Terminal heading")
        # escalated_to context stays visible on the segregated row
        self.assertRegex(text[heading_at:], r"\| 002 \| beta \|[^\n]*\| 099 \|")

    def test_resolved_on_main_bug_segregated(self):
        self._write_bug("001-gamma.md", status="RESOLVED_ON_MAIN", slug="gamma")
        text = self._board_text()

        self.assertIn("## Terminal", text)
        self.assertLess(text.index("## Terminal"), text.index("| 001 | gamma |"),
                        "RESOLVED_ON_MAIN row must appear below the Terminal heading")

    def test_no_terminal_section_when_all_active_or_done(self):
        # DONE is terminal-success, NOT a terminal-non-DONE row: it stays in
        # the active table and must not trigger the Terminal section.
        self._write_bug("001-alpha.md", status="REPORTED", slug="alpha")
        self._write_bug("002-delta.md", status="DONE", slug="delta")
        text = self._board_text()

        self.assertNotIn("## Terminal", text,
                         "no Terminal section when every bug is active or DONE")
        self.assertIn("| 002 | delta |", text,
                      "DONE row stays in the active table")

    def test_all_terminal_renders_empty_active_table(self):
        # Edge: every bug is terminal-non-DONE. The active table still renders
        # its header+separator (zero rows) and the Terminal section carries the
        # rows — valid markdown, no crash, header always present.
        self._write_bug("001-alpha.md", status="ESCALATED", slug="alpha",
                        escalated_to="099")
        text = self._board_text()

        self.assertIn("## Terminal", text)
        header_line = ("| ID | slug | severity | tier | status | reproduces? | "
                       "regression test | claimed_by | escalated_to | Notes |")
        self.assertIn(header_line, text, "active header stays present")
        # The only data row lives below the Terminal heading, not above it.
        self.assertLess(text.index("## Terminal"), text.index("| 001 | alpha |"))
        active_region = text[:text.index("## Terminal")]
        self.assertNotIn("| 001 | alpha |", active_region,
                         "no data row in the (empty) active table")

    def test_terminal_row_note_preserved_across_regen(self):
        # A curated Note on an escalated row, seeded inline in a flat legacy
        # board, must survive regeneration into the Terminal section.
        self._write_bug("001-beta.md", status="ESCALATED", slug="beta",
                        escalated_to="099")
        board = self.root / "docs" / "bugs" / "README.md"
        write(board, (
            "# Bug Status Board\n\n"
            "| ID | slug | severity | tier | status | reproduces? | "
            "regression test | claimed_by | escalated_to | Notes |\n"
            "|----|------|----------|------|--------|-------------|"
            "-----------------|------------|--------------|-------|\n"
            "| 001 | beta | medium | standard | ESCALATED | no | "
            " |  | 099 | keep me |\n"
        ))
        text = self._board_text()

        self.assertIn("## Terminal", text)
        self.assertIn("keep me", text,
                      "curated Note must survive migration into Terminal section")


class DiagnoseGateListShapeTests(unittest.TestCase):
    """Regression coverage for bug 005 / issue 80: the diagnose gate must
    count candidate hypotheses across every Markdown list marker and must
    count only *top-level* items, so numbered lists are visible and nested
    confirm/falsify sub-bullets are not mistaken for hypotheses."""

    def setUp(self):
        self.mod = load_bug_module()

    def _gaps(self, hypotheses: str, evidence: str = "some evidence") -> list:
        text = (
            f"## Evidence\n\n{evidence}\n\n"
            f"## Hypotheses\n\n{hypotheses}\n\n"
            "## Root cause\n\n"
        )
        return self.mod._diagnosis_gaps(text)

    def test_numbered_list_hypotheses_count(self):
        """False negative: `1.`/`2.` ordered lists must count toward >=2."""
        gaps = self._gaps(
            "1. [ ] H1: an alternative explanation\n"
            "2. [x] H2 (leading): the leading explanation\n"
        )
        self.assertNotIn(
            "at least two candidate hypotheses",
            "\n".join(gaps),
            "numbered-list hypotheses must be counted",
        )

    def test_star_and_plus_bullets_count(self):
        """`*` and `+` are valid Markdown bullets and must count."""
        gaps = self._gaps("* [ ] H1: alt\n+ [x] H2 (leading): main\n")
        self.assertNotIn("at least two candidate hypotheses", "\n".join(gaps))

    def test_nested_subbullets_do_not_count_as_hypotheses(self):
        """False positive: nested `- Confirm:`/`- Falsify:` sub-bullets under a
        single hypothesis must NOT satisfy the >=2 check on their own."""
        gaps = self._gaps(
            "1. [x] H1 (leading): the only real hypothesis\n"
            "   - Confirm: do X\n"
            "   - Falsify: do Y\n"
        )
        self.assertIn(
            "at least two candidate hypotheses",
            "\n".join(gaps),
            "indented sub-bullets must not be counted as top-level hypotheses",
        )

    def test_parenthetical_leading_marker_satisfies_leading(self):
        """SKILL.md says 'mark the leading one'; `**(leading)**` must satisfy
        the leading check, not only `[x]` / `Leading:`."""
        gaps = self._gaps("- H1: alt explanation\n- **(leading)** H2: main\n")
        self.assertNotIn("a leading hypothesis", "\n".join(gaps))

    def test_dash_bullet_hypotheses_still_count(self):
        """Backward compatibility: the original `- [x]` shape keeps working."""
        gaps = self._gaps("- [ ] H1: alt\n- [x] H2 (leading): main\n")
        joined = "\n".join(gaps)
        self.assertNotIn("at least two candidate hypotheses", joined)
        self.assertNotIn("a leading hypothesis", joined)

    def test_gap_messages_name_the_expected_shape(self):
        """The gap strings (surfaced in the warning and the gnarly error) must
        name the list-item shape and the leading marker, not just the gap."""
        gaps = self._gaps("", evidence="")
        joined = "\n".join(gaps)
        self.assertIn("list item", joined, "must name the list-item shape")
        self.assertIn("[x]", joined, "must name the leading marker shape")


class Slice098BugMarkerTests(unittest.TestCase):
    """Spec 098-04 — a bug fix opened the prescribed way leaves the SAME
    working-tree lifecycle marker (`.jig/spec-ref`) a spec slice does, so the
    entry gate (098-01) reads one signal for both lifecycles."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.marker = self.root / ".jig" / "spec-ref"

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self, rel: str = "001-alpha.md") -> Path:
        return self.root / "docs" / "bugs" / rel

    def _status(self) -> str:
        fields, _ = parse_frontmatter(self._bug().read_text())
        return str(fields.get("status") or "").strip()

    def _claimed_by(self) -> str:
        fields, _ = parse_frontmatter(self._bug().read_text())
        return str(fields.get("claimed_by") or "").strip()

    def _write_record(self, *, status: str = "REPORTED", claimed_by: str = "",
                      fix_class: str = "") -> Path:
        return write(self._bug(), (
            "---\n"
            f"status: {status}\n"
            "severity: high\n"
            "tier: standard\n"
            f"claimed_by: {claimed_by}\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "main_repro_checked_at:\n"
            "main_repro_ref:\n"
            "main_repro_result:\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            f"fix_class: {fix_class}\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n"
        ))

    def _seed_marker(self, body: str) -> None:
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(body)

    # ---- AC1: pickup stamps a bug-shaped marker ----
    def test_pickup_stamps_bug_marker(self):
        self._write_record(status="REPORTED")
        r = run_bug("pickup", "001", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-me"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.marker.is_file())
        self.assertEqual(self.marker.read_text().strip(), "bug=001")

    def test_pickup_after_push_reservation_stamps_marker(self):
        # new_bug(push=True) commits to origin/main and returns None — nothing
        # lands locally. Before `pickup`, the record is fetched from origin/main
        # into the working tree (bug-fix/SKILL.md §1) ALREADY claimed_by the
        # reserving checkout. Re-picking it up here (existing == owner) is the
        # distinct path this test exercises: the marker is stamped even when the
        # claim field is unchanged. This is the case the gate's bug arm exists for.
        self._write_record(status="REPORTED", claimed_by="wt-me")
        r = run_bug("pickup", "001", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-me"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._claimed_by(), "wt-me")
        self.assertEqual(self.marker.read_text().strip(), "bug=001")

    # ---- AC2: transition into a working status stamps ----
    def test_working_status_set_is_derived_from_open_statuses(self):
        """AC2 — the stamping set is exactly OPEN_STATUSES - {REPORTED},
        derived from the constant so a future status cannot silently fall
        outside the gate's notion of 'working'."""
        mod = load_bug_module()
        self.assertEqual(mod._BUG_WORKING_STATUSES,
                         set(mod.OPEN_STATUSES) - {"REPORTED"})
        self.assertNotIn("REPORTED", mod._BUG_WORKING_STATUSES)
        # Every working status is a valid, open, non-terminal status.
        for status in mod._BUG_WORKING_STATUSES:
            self.assertIn(status, mod.OPEN_STATUSES)

    def test_transition_into_working_stamps_without_prior_pickup(self):
        # No prior pickup: the record is unclaimed, and a resumed session that
        # transitions it straight into a working status is still 'inside'.
        self._write_record(status="REPORTED", claimed_by="")
        r = run_bug("transition", "001", "DIAGNOSING",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._status(), "DIAGNOSING")
        self.assertEqual(self.marker.read_text().strip(), "bug=001")

    def test_transition_into_fixing_stamps_marker(self):
        self._write_record(status="ROOT_CAUSED", fix_class="local_patch")
        r = run_bug("transition", "001", "FIXING",
                    "--project-dir", str(self.root),
                    env={"JIG_BUG_MAIN_CHECK_GATE": "0",
                         "JIG_BUG_TEST_GATE": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.marker.read_text().strip(), "bug=001")

    def test_transition_to_reported_never_stamps(self):
        # REPORTED is deliberately excluded (AC2): a bug can sit reported with
        # nobody on it. There is no transition INTO REPORTED, so the guard is
        # that a same-status no-op transition does not stamp either.
        self._write_record(status="REPORTED")
        r = run_bug("transition", "001", "REPORTED",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.marker.exists())

    # ---- AC3: compatibility + no cross-talk ----
    def test_spec_shaped_marker_read_identically_by_all_three(self):
        self._seed_marker("spec=098\nslice=098-04\n")
        self.assertEqual(_ra_read_spec_ref(self.root), ("098", "098-04"))
        self.assertEqual(_gt_read_spec_ref(self.root), "098")
        self.assertEqual(_usage_read_spec_ref(self.root), "098")

    def test_bug_shaped_marker_invisible_to_spec_readers(self):
        self._seed_marker("bug=001\n")
        self.assertEqual(_ra_read_spec_ref(self.root), ("", ""))
        self.assertEqual(_gt_read_spec_ref(self.root), "")
        self.assertIsNone(_usage_read_spec_ref(self.root))

    # ---- AC5: release clears the marker (only when it names this bug) ----
    def test_release_clears_marker(self):
        self._write_record(status="DIAGNOSING", claimed_by="wt-me")
        self._seed_marker("bug=001\n")
        r = run_bug("pickup", "001", "--release", "--reason", "stepping away",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.marker.exists())

    def test_release_leaves_foreign_marker_untouched(self):
        # Releasing bug 001 must not clobber a marker that names a spec slice
        # (or a different bug) — the session may still be inside that item.
        self._write_record(status="DIAGNOSING", claimed_by="wt-me")
        self._seed_marker("spec=055\nslice=055-01\n")
        r = run_bug("pickup", "001", "--release", "--reason", "x",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.marker.read_text(), "spec=055\nslice=055-01\n")

    def test_release_leaves_a_different_bugs_marker_untouched(self):
        # The clear must key on THIS bug's number: a marker naming bug 002 is
        # left alone when bug 001 is released (the '002' != '001' branch).
        self._write_record(status="DIAGNOSING", claimed_by="wt-me")
        self._seed_marker("bug=002\n")
        r = run_bug("pickup", "001", "--release", "--reason", "x",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.marker.read_text().strip(), "bug=002")

    def test_marker_names_bug_is_lenient_and_normalizes(self):
        # The regex tolerates surrounding whitespace and zero-pads the number.
        mod = load_bug_module()
        self.assertEqual(mod._marker_names_bug("  bug = 1 \n"), "001")
        self.assertEqual(mod._marker_names_bug("bug=027\n"), "027")
        self.assertEqual(mod._marker_names_bug("spec=098\nslice=098-04\n"), "")
        self.assertEqual(mod._marker_names_bug(""), "")

    # ---- AC6: terminal statuses clear the marker ----
    def test_main_check_resolved_on_main_clears_marker(self):
        self._write_record(status="ROOT_CAUSED")
        self._seed_marker("bug=001\n")
        r = run_bug("main-check", "001", "--result", "resolved-on-main",
                    "--ref", "origin/main@abc123",
                    "--evidence", "ran the repro on fresh main; gone",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._status(), "RESOLVED_ON_MAIN")
        self.assertFalse(self.marker.exists())

    def test_transition_to_done_clears_marker(self):
        mod = load_bug_module()
        self._write_record(status="REVIEWED", fix_class="local_patch")
        self._seed_marker("bug=001\n")
        # Isolate the marker wiring from the (separately tested) DONE evidence
        # and learning gates.
        with patch.object(mod._evidence, "validate_bug_evidence",
                          return_value=[]), \
                patch.object(mod, "_learning_recorded", return_value=True):
            mod.transition_bug(self.root, "001", "DONE")
        self.assertEqual(self._status(), "DONE")
        self.assertFalse(self.marker.exists())

    def test_escalate_clears_marker(self):
        mod = load_bug_module()
        self._write_record(status="ROOT_CAUSED")
        self._seed_marker("bug=001\n")
        spec_dir = self.root / "docs" / "specs" / "099-x"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("---\nstatus: DRAFT\n---\n# Spec 099\n")
        fake = subprocess.CompletedProcess(
            [], 0, stdout=f"reserved 099-x\n{spec_md}\n", stderr="")
        with patch.object(mod.subprocess, "run", return_value=fake):
            mod.escalate_bug(self.root, "001")
        self.assertEqual(self._status(), "ESCALATED")
        self.assertFalse(self.marker.exists())

    # ---- AC4: best-effort, never blocking ----
    def test_marker_write_failure_does_not_break_pickup(self):
        self._write_record(status="REPORTED")
        # Occupy .jig with a regular file so the marker write cannot succeed.
        (self.root / ".jig").write_text("not a directory")
        r = run_bug("pickup", "001", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-me"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._claimed_by(), "wt-me")

    def test_marker_write_failure_does_not_break_transition(self):
        self._write_record(status="REPORTED")
        (self.root / ".jig").write_text("not a directory")
        r = run_bug("transition", "001", "DIAGNOSING",
                    "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._status(), "DIAGNOSING")

    def test_failed_status_write_leaves_no_marker(self):
        # Ordering (AC2): the marker is stamped only AFTER the status write
        # succeeds. Fail ONLY the bug-record write (the *.md path), letting the
        # marker write succeed if reached — so this fails loudly if the stamp
        # were ever placed BEFORE the status write.
        mod = load_bug_module()
        self._write_record(status="REPORTED")
        self.assertFalse(self.marker.exists())
        real_awt = mod.atomic_write_text

        def only_record_fails(path, text):
            if str(path).endswith(".md"):
                raise OSError("disk full")
            return real_awt(path, text)

        with patch.object(mod, "atomic_write_text",
                          side_effect=only_record_fails):
            with self.assertRaises(OSError):
                mod.transition_bug(self.root, "001", "DIAGNOSING")
        self.assertFalse(self.marker.exists())


class CheckBoardTests(unittest.TestCase):
    """`bug.py check-board` — the read-only guard that lets the board stop
    being hand-merged (issue #149).

    The board is a derived file: every parallel PR appends a row at the same
    end-of-table position, so every parallel PR conflicts on it. Silencing that
    conflict is only safe if something else catches what the conflict marker
    was accidentally catching — a **duplicate bug id**, which `_render_board`
    otherwise renders as two rows without complaint. This subcommand is that
    something else, plus a drift check that the committed board still matches
    what the records say. Read-only by contract: CI must be able to run it
    against a checkout without mutating the tree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self, rel: str) -> Path:
        return self.root / "docs" / "bugs" / rel

    def _record(self, num: str, slug: str, **fields: str) -> Path:
        base = {"status": "REPORTED", "severity": "low", "tier": "standard",
                "claimed_by": "", "regression_test": "", "red_confirmed_at": "",
                "green_confirmed_at": "", "fix_class": "",
                "security_surface": "false", "escalated_to": ""}
        base.update(fields)
        fm = "".join(f"{k}: {v}\n" for k, v in base.items())
        return write(self._bug(f"{num}-{slug}.md"),
                     f"---\n{fm}---\n\n## Symptom\n")

    def _sync_board(self) -> Path:
        r = run_bug("status-board", "--project-dir", str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        return self._bug("README.md")

    def test_clean_project_passes(self):
        self._record("001", "alpha")
        self._record("002", "beta")
        self._sync_board()

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertEqual(r.returncode, 0, r.stderr)

    def test_duplicate_id_fails_and_names_both_records(self):
        """The core guard. Two records claiming 017 is exactly what a parallel
        reservation produces once the conflict marker stops being shown."""
        self._record("017", "alpha")
        self._sync_board()
        self._record("017", "beta")
        self._sync_board()

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertNotEqual(r.returncode, 0)
        combined = r.stdout + r.stderr
        self.assertIn("017", combined)
        self.assertIn("017-alpha.md", combined, "must name the colliding files")
        self.assertIn("017-beta.md", combined, "must name the colliding files")

    def test_drifted_board_fails_and_names_the_file(self):
        self._record("001", "alpha")
        board = self._sync_board()
        self._record("002", "beta")  # board now stale — row 002 missing

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertNotEqual(r.returncode, 0)
        combined = r.stdout + r.stderr
        self.assertIn("README.md", combined)
        self.assertIn("status-board", combined,
                      "must name the command that fixes the drift")
        self.assertEqual(board.read_text().count("| 002 |"), 0,
                         "check-board must not repair the drift itself")

    def test_is_read_only(self):
        """CI runs this against a checkout; it must leave the tree untouched
        even when it fails."""
        self._record("001", "alpha")
        board = self._sync_board()
        before = board.read_text()
        self._record("002", "beta")

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertEqual(r.returncode, 1,
                         "expected a real check failure, not an argparse usage "
                         f"error: {r.stderr}")
        self.assertEqual(board.read_text(), before)

    def test_curated_notes_do_not_read_as_drift(self):
        """Notes live only in the board and are preserved across regen, so a
        hand-written Note must not be reported as the board having drifted."""
        self._record("001", "alpha")
        board = self._sync_board()
        board.write_text(board.read_text().replace(
            "|  |\n", "| curated note |\n", 1))

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_board_fails_cleanly(self):
        self._record("001", "alpha")

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertNotEqual(r.returncode, 0)
        self.assertIn("README.md", r.stdout + r.stderr)

    def test_terminal_section_rows_are_checked_too(self):
        """`_render_board` splits ESCALATED / RESOLVED_ON_MAIN into a second
        table. A duplicate id spanning the two tables must still be caught."""
        self._record("017", "alpha")
        self._record("017", "beta", status="ESCALATED", escalated_to="spec 099")
        self._sync_board()

        r = run_bug("check-board", "--project-dir", str(self.root))

        self.assertNotEqual(r.returncode, 0)
        self.assertIn("017", r.stdout + r.stderr)


class Spec091ClosureTemplateTests(unittest.TestCase):
    """AC1: new records carry the closure sections + creation-time marker."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _fields_and_body(self):
        path = self.root / "docs" / "bugs" / "001-auth-crash.md"
        text = path.read_text()
        fields, _ = parse_frontmatter(text)
        return fields, text

    def test_new_stamps_closure_schema_marker(self):
        r = run_bug("new", "auth-crash", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-alpha"})
        self.assertEqual(r.returncode, 0, r.stderr)
        fields, _ = self._fields_and_body()
        self.assertEqual(str(fields["closure_schema"]).strip(), "1")

    def test_new_emits_all_five_closure_prompts(self):
        r = run_bug("new", "auth-crash", "--project-dir", str(self.root),
                    env={"JIG_CLAIM_ID": "wt-alpha"})
        self.assertEqual(r.returncode, 0, r.stderr)
        _, body = self._fields_and_body()
        for marker in (
            "## Repository closure inventory",
            "**Equivalent / convergent logic searched:**",
            "**Relevant history inspected:**",
            "**Affected call sites:**",
            "**Reuse decision:**",
            "## Call-site closure",
            "**Disposition per affected site:**",
        ):
            self.assertIn(marker, body)


class Spec091ClosureGateHelperTests(unittest.TestCase):
    """Unit-level coverage of the closure gate parsing (AC2/AC3/AC6)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_bug_module()

    def _inventory(self, equivalent="grep foo/bar; git log -S; searched `urlId`",
                   history="git blame shows helper added in a1b2c3",
                   sites="callers: a(), b()", reuse="reuse existing helper"):
        return (
            "## Repository closure inventory\n\n"
            f"**Equivalent / convergent logic searched:** {equivalent}\n\n"
            f"**Relevant history inspected:** {history}\n\n"
            f"**Affected call sites:** {sites}\n\n"
            f"**Reuse decision:** {reuse}\n\n"
            "## Fix class\n"
        )

    def test_fully_answered_inventory_has_no_gaps(self):
        self.assertEqual(self.mod._closure_inventory_gaps(self._inventory()), [])

    def test_missing_inventory_section_is_a_gap(self):
        gaps = self.mod._closure_inventory_gaps("## Root cause\n\nx\n")
        self.assertTrue(gaps)
        self.assertIn("Repository closure inventory", gaps[0])

    def test_empty_prompt_is_a_gap(self):
        gaps = self.mod._closure_inventory_gaps(self._inventory(reuse=""))
        self.assertTrue(any("Reuse decision" in g for g in gaps))

    def test_comment_only_section_is_not_substantive(self):
        # A record that carries only the shipped HTML comment (unedited) must
        # still gate — the comment is not an answer.
        section = (
            "## Repository closure inventory\n\n"
            "<!-- Spec 091 / ADR-0037: pre-fix repository closure. -->\n\n"
            "**Equivalent / convergent logic searched:**\n\n"
            "**Relevant history inspected:**\n\n"
            "**Affected call sites:**\n\n"
            "**Reuse decision:**\n\n"
            "## Fix class\n"
        )
        self.assertTrue(self.mod._closure_inventory_gaps(section))

    def test_protocol_bearing_assumption_answer_passes(self):
        # AC6: an honest "not closable by name search" WITH protocol passes.
        answer = (
            "searched `urlId`, `canonicalUrl`, `identity`; `git log -S` and "
            "`git blame` on the touched surface returned only this path; the "
            "set is not closable by name search — recorded as an assumption."
        )
        gaps = self.mod._closure_inventory_gaps(self._inventory(equivalent=answer))
        self.assertEqual(gaps, [])

    def test_bare_none_found_fails(self):
        # AC6: a bare negative verdict with no protocol does not satisfy it.
        for bare in ("none", "None found.", "n/a", "nothing found", "no"):
            with self.subTest(bare=bare):
                gaps = self.mod._closure_inventory_gaps(
                    self._inventory(equivalent=bare)
                )
                self.assertTrue(
                    any("bare verdict" in g for g in gaps),
                    f"{bare!r} should fail the protocol floor: {gaps}",
                )

    def test_decorated_bare_verdict_still_fails(self):
        for bare in ("none!", "None found…", "nothing.", "N/A?"):
            with self.subTest(bare=bare):
                gaps = self.mod._closure_inventory_gaps(
                    self._inventory(equivalent=bare)
                )
                self.assertTrue(any("bare verdict" in g for g in gaps))

    def test_inner_bold_label_does_not_false_gap(self):
        # An author who writes an inner `**Note:**` inside a real answer must
        # not trip a false "missing prompt" gap — the required label still owns
        # non-empty content before the inner label.
        answer = "searched `foo`; git log -S clean **Note:** see PR 12"
        gaps = self.mod._closure_inventory_gaps(self._inventory(reuse=answer))
        self.assertEqual(gaps, [])

    def test_call_site_closure_gaps(self):
        self.assertTrue(self.mod._call_site_closure_gaps("## Fix\n\nx\n"))
        ok = (
            "## Call-site closure\n\n"
            "**Disposition per affected site:** a() changed; b() left as-is "
            "(different contract)\n\n"
            "## Already tried\n"
        )
        self.assertEqual(self.mod._call_site_closure_gaps(ok), [])

    def test_marker_presence_detects_new_vs_legacy(self):
        self.assertTrue(self.mod._is_closure_schema_record({"closure_schema": "1"}))
        self.assertFalse(self.mod._is_closure_schema_record({}))
        self.assertFalse(self.mod._is_closure_schema_record({"closure_schema": ""}))


class Spec091ClosureTransitionGateTests(unittest.TestCase):
    """AC2/AC3 end-to-end via the CLI, with the marker driving new-vs-legacy."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self):
        return self.root / "docs" / "bugs" / "001-alpha.md"

    def _fake_tdd(self, code: int) -> Path:
        script = self.root / f"fake_tdd_{code}.py"
        script.write_text(
            "import sys\nprint('fake tdd')\nraise SystemExit("
            f"{code})\n"
        )
        return script

    def _write(self, *, status="ROOT_CAUSED", tier="standard", marked=True,
               inventory=True, closure=False, fix_class="local_patch"):
        inv = (
            "## Repository closure inventory\n\n"
            "**Equivalent / convergent logic searched:** grep `foo`; git log -S\n\n"
            "**Relevant history inspected:** git blame -> a1b2c3\n\n"
            "**Affected call sites:** a(), b()\n\n"
            "**Reuse decision:** reuse existing helper\n\n"
        ) if inventory else "## Repository closure inventory\n\n"
        cls = (
            "## Call-site closure\n\n"
            "**Disposition per affected site:** a() changed; b() left as-is\n\n"
        ) if closure else "## Call-site closure\n\n"
        marker = "closure_schema: 1\n" if marked else ""
        return write(self._bug(), (
            "---\n"
            f"status: {status}\n"
            "severity: high\n"
            f"tier: {tier}\n"
            "claimed_by: wt-alpha\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "main_repro_checked_at: 2026-08-18\n"
            "main_repro_ref: origin/main@abc123\n"
            "main_repro_result: reproduces\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            f"fix_class: {fix_class}\n"
            "security_surface: false\n"
            "escalated_to:\n"
            f"{marker}"
            "---\n\n"
            "## Symptom\n\n## Repro\n\n## Evidence\n\ntrace\n\n"
            "## Hypotheses\n\n- [ ] a\n- [x] b (leading)\n\n"
            "## Root cause\n\nrc\n\n"
            f"{inv}"
            "## Fix class\n\n## Fix\n\n"
            f"{cls}"
            "## Already tried\n\n## Regression test\n\n## Proof\n\n## Learning\n"
        ))

    def _fm(self):
        fields, _ = parse_frontmatter(self._bug().read_text())
        return fields

    def test_marked_record_blocks_fixing_without_inventory(self):
        self._write(marked=True, inventory=False)
        r = run_bug("transition", "001", "FIXING", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(1))})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("repository-closure inventory", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")

    def test_marked_record_with_inventory_reaches_fixing(self):
        self._write(marked=True, inventory=True)
        r = run_bug("transition", "001", "FIXING", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(1))})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_legacy_unmarked_record_is_exempt(self):
        # A pre-091 record has no marker and no inventory — it must still
        # transition (compatibility path), never blocked by the closure gate.
        self._write(marked=False, inventory=False)
        r = run_bug("transition", "001", "FIXING", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(1))})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_trivial_tier_marked_record_is_exempt(self):
        self._write(marked=True, inventory=False, tier="trivial")
        r = run_bug("transition", "001", "FIXING", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(1))})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_closure_gate_bypass_env_disables_it(self):
        self._write(marked=True, inventory=False)
        r = run_bug("transition", "001", "FIXING", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(1)),
                         "JIG_BUG_CLOSURE_GATE": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "FIXING")

    def test_marked_record_blocks_reviewed_without_call_site_closure(self):
        self._write(status="FIXING", marked=True, inventory=True, closure=False)
        r = run_bug("transition", "001", "REVIEWED", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(0)),
                         "JIG_REVIEW_EVIDENCE_GATE": "0"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("call-site closure", r.stderr)

    def test_legacy_record_reviewed_exempt_from_call_site_closure(self):
        self._write(status="FIXING", marked=False, inventory=False, closure=False)
        r = run_bug("transition", "001", "REVIEWED", "--project-dir", str(self.root),
                    env={"JIG_TDD_HELPER": str(self._fake_tdd(0)),
                         "JIG_REVIEW_EVIDENCE_GATE": "0"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._fm()["status"], "REVIEWED")


class Spec091VacuitySamplingTests(unittest.TestCase):
    """AC7: the recorded inventory is machine-samplable — a leading kill
    indicator (vacuity) can be computed from records, keyed on the marker so a
    legacy record is never mistaken for a vacuous new one."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_bug_module()

    def _record(self, *, marked, equivalent):
        marker = "closure_schema: 1\n" if marked else ""
        return (
            "---\n"
            "status: FIXING\n"
            f"{marker}"
            "---\n\n"
            "## Repository closure inventory\n\n"
            f"**Equivalent / convergent logic searched:** {equivalent}\n\n"
            "**Relevant history inspected:** x\n\n"
            "**Affected call sites:** y\n\n"
            "**Reuse decision:** z\n\n"
            "## Fix class\n"
        )

    def test_marker_keyed_vacuity_classification(self):
        mod = self.mod
        corpus = {
            "legacy": self._record(marked=False, equivalent="none"),
            "vacuous_new": self._record(marked=True, equivalent="none found"),
            "protocol_new": self._record(
                marked=True,
                equivalent="grep `foo`; git log -S; not closable — assumption",
            ),
        }
        # A sampler built only from exposed helpers.
        def classify(text):
            fields, _ = parse_frontmatter(text)
            if not mod._is_closure_schema_record(fields):
                return "legacy-exempt"
            section = mod._section(text, "Repository closure inventory")
            eq = mod._labeled_blocks(section).get(
                "Equivalent / convergent logic searched", ""
            )
            return "vacuous" if mod._is_bare_negative(eq) else "protocol"

        self.assertEqual(classify(corpus["legacy"]), "legacy-exempt")
        self.assertEqual(classify(corpus["vacuous_new"]), "vacuous")
        self.assertEqual(classify(corpus["protocol_new"]), "protocol")


class Spec091SingleSourceEnumerationTests(unittest.TestCase):
    """AC6: the ADR-0052 enumeration rule has one home; the closure guidance
    cross-references it rather than restating a weaker variant."""

    SKILL = REPO_ROOT / "skills" / "bug-fix" / "SKILL.md"

    def test_enumeration_rule_lives_in_exactly_one_place(self):
        text = self.SKILL.read_text()
        # Distinctive phrases from the diagnose grounding block (ADR-0052).
        self.assertEqual(text.count("returns the *complete* set"), 1)
        self.assertEqual(text.count("One true example says nothing"), 1)

    def test_closure_guidance_cross_references_rather_than_restates(self):
        text = self.SKILL.read_text()
        self.assertIn("same enumeration standard as", text)
        self.assertIn("adr-0052", text.lower())


class Spec091BugReviewPromptTests(unittest.TestCase):
    """AC4: the bug-review prompt judges repository closure, not just the
    local regression test."""

    @classmethod
    def setUpClass(cls):
        import importlib.util
        review_py = REPO_ROOT / "skills" / "independent-review" / "review.py"
        spec = importlib.util.spec_from_file_location("review_091", review_py)
        cls.review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.review)

    def test_prompt_checks_closure_reuse_history_and_disposition(self):
        prompt = self.review.build_bug_review_prompt(
            Path("docs/bugs/001-x.md"), ["skills/bug-fix/bug.py"]
        )
        lowered = prompt.lower()
        self.assertIn("repository closure", lowered)
        self.assertIn("convergent", lowered)
        self.assertIn("adr-0052", lowered)
        self.assertIn("call site", lowered)
        self.assertIn("none found", lowered)


class Bug021GateSurfacesTargetingRefusalTests(unittest.TestCase):
    """Bug 021: when tdd.py cannot run the *named* test as asked (exit 2 —
    e.g. a custom command with no {test} placeholder, or an unresolved
    selector), the transition gates must surface tdd.py's own report instead
    of a bare exit code, so the refusal is actionable and never mistaken for
    evidence about the named test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bug(self) -> Path:
        return self.root / "docs" / "bugs" / "001-alpha.md"

    def _fm(self) -> dict:
        fields, _ = parse_frontmatter(self._bug().read_text())
        return fields

    def _write_bug(self, *, status: str) -> Path:
        return write(self._bug(), (
            "---\n"
            f"status: {status}\n"
            "severity: high\n"
            "tier: standard\n"
            "regression_test: tests/test_alpha.py::test_bug\n"
            "main_repro_checked_at: 2026-08-31\n"
            "main_repro_ref: origin/main@abc123\n"
            "main_repro_result: reproduces\n"
            "red_confirmed_at:\n"
            "green_confirmed_at:\n"
            "fix_class: local_patch\n"
            "security_surface: false\n"
            "escalated_to:\n"
            "---\n\n"
            "## Symptom\n\n"
            "## Repro\n\n"
            "## Evidence\n\ntrace: log line 7\n\n"
            "## Hypotheses\n\n- [ ] cache race\n- [x] parser bug\n\n"
            "## Root cause\n\n"
            "## Fix\n\n"
            "## Already tried\n\n"
            "## Regression test\n\n"
            "## Proof\n\n"
            "## Learning\n"
        ))

    def _fake_tdd_refusing(self, message: str, code: int = 2) -> Path:
        script = self.root / "fake_tdd_refusing.py"
        script.write_text(
            "import sys\n"
            f"sys.stderr.write({message!r} + '\\n')\n"
            f"raise SystemExit({code})\n"
        )
        return script

    def test_fixing_exit_2_surfaces_tdd_report_and_stamps_no_red(self):
        self._write_bug(status="ROOT_CAUSED")
        refusal = (
            "custom test command does not accept a test selector "
            "(no {test} placeholder in .jig/test-command)"
        )
        r = run_bug(
            "transition", "001", "FIXING", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd_refusing(refusal))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not accept a test selector", r.stderr)
        self.assertEqual(self._fm()["status"], "ROOT_CAUSED")
        self.assertEqual(str(self._fm().get("red_confirmed_at") or ""), "")

    def test_reviewed_green_failure_surfaces_tdd_report(self):
        self._write_bug(status="FIXING")
        r = run_bug(
            "transition", "001", "REVIEWED", "--project-dir", str(self.root),
            env={"JIG_TDD_HELPER": str(self._fake_tdd_refusing(
                "unresolved selector: tests/test_alpha.py::test_bug"))},
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unresolved selector", r.stderr)
        # The failed attempt is carried forward as evidence, with the report.
        self.assertEqual(self._fm()["status"], "DIAGNOSING")
        self.assertIn("unresolved selector", self._bug().read_text())


if __name__ == "__main__":
    unittest.main()
