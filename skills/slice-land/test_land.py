"""
AC verification tests for slice 007-01 (land-prepare).

Run from the repo root:
    python3 -m unittest skills.slice-land.test_land
Or from the skill dir:
    python3 -m unittest test_land
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAND_PY = REPO_ROOT / "skills" / "slice-land" / "land.py"
SKILL_MD = REPO_ROOT / "skills" / "slice-land" / "SKILL.md"
TDD_PY = REPO_ROOT / "skills" / "tdd-loop" / "tdd.py"


def _pytest_available() -> bool:
    """Mirror tdd-loop's skip pattern — only run tests that need a green
    pytest result when pytest is importable."""
    try:
        import pytest  # noqa: F401
        return True
    except ImportError:
        return False


def run_land(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    """Invoke land.py as a subprocess.

    `cwd` lets tests control what dir tdd.py runs against.
    """
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(LAND_PY), *args],
        capture_output=True, text=True, env=env,
        cwd=str(cwd) if cwd else None,
    )


def _spec_with_slice(slice_label: str, status: str,
                     dod_ticked: bool = True,
                     dod_count: int = 4,
                     dod_unticked: int = 0,
                     include_deviation_log: bool = True,
                     extra_dev_text: str = "") -> str:
    """Generate a synthetic spec.md for a given slice in a given state."""
    dod_lines = []
    if dod_ticked:
        for _ in range(dod_count):
            dod_lines.append("- [x] Some DoD item complete.")
    else:
        for _ in range(dod_count - dod_unticked):
            dod_lines.append("- [x] Some DoD item complete.")
        for _ in range(dod_unticked):
            dod_lines.append("- [ ] Some DoD item NOT complete.")
    dod_block = "\n".join(dod_lines)

    deviation_block = ""
    if include_deviation_log:
        deviation_block = (
            "\n### Deviation log (after reconciliation)\n\n"
            "The original spec is preserved above.\n\n"
            "**Design choices logged:**\n\n"
            f"1. **Some design decision recorded.** "
            f"{extra_dev_text or 'Body text describing what changed and why.'}\n\n"
            "**Doc updates from this slice:**\n\n"
            "- `skills/foo/SKILL.md`: net-new file.\n"
            "- `CLAUDE.md`: hot-cache updated.\n"
        )

    return (
        "---\n"
        "status: DRAFT\n"
        "skill: foo\n"
        "tier: 1\n"
        "---\n\n"
        "# Spec X: foo\n\n"
        "## Overview\n\n"
        "Synthetic spec for tests.\n\n"
        f"## Slice {slice_label}\n\n"
        f"**STATUS: {status}**\n\n"
        "**Goal:** A synthetic goal sentence.\n\n"
        "**DoR:**\n"
        "- Test prerequisite met.\n\n"
        "**Acceptance Criteria:**\n\n"
        "1. **`foo cmd`** does one thing.\n"
        "2. **`foo other-cmd`** does another thing.\n"
        "3. Exit code is 0 on success.\n\n"
        "**DoD** (same shape as 003-01 / 004-01):\n"
        f"{dod_block}\n\n"
        "**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice.\n"
        f"{deviation_block}"
    )


# -------------------- PrepareReportTests --------------------


class PrepareReportTests(unittest.TestCase):
    """AC #1 & #3 — four readiness sections + exit codes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-land-")
        self.spec = Path(self.tmpdir) / "spec.md"
        # No test signals in the tmpdir — tdd.py will return exit 2 (no
        # runner detected) → maps to "warn" in land.py → not a blocker.
        # This keeps the readiness tests independent of pytest install
        # state. The green-tests path is exercised separately (skipped
        # when pytest is absent).

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _all_green_spec(self):
        self.spec.write_text(_spec_with_slice("007-01 — land-prepare", "DONE"))

    def test_all_green_exit_zero(self):
        """When STATUS=DONE, deviation log present, all DoD ticked, and
        tests do not block (warn or green) → exit 0 with all required
        items ticked. The Tests row is [x] when pytest is available,
        [?] otherwise — both are non-blockers."""
        self._all_green_spec()
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        out = result.stdout
        self.assertIn("Landing readiness", out)
        # Three readiness items must be ticked; tests row is non-blocking
        self.assertIn("[x] Status", out)
        self.assertIn("[x] Deviation log", out)
        self.assertIn("[x] DoD", out)
        # Tests row: green OR warn — both acceptable
        self.assertRegex(out, r"(?m)^- \[[x?]\] Tests")

    @unittest.skipUnless(_pytest_available(),
                         "pytest not importable in this env")
    def test_all_green_exit_zero_with_real_pytest(self):
        """When pytest IS installed, a clean pytest target produces an
        explicit [x] Tests row (not [?]). This pins the green path."""
        (Path(self.tmpdir) / "test_dummy.py").write_text(
            "def test_one():\n    assert 1 + 1 == 2\n"
        )
        self._all_green_spec()
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        self.assertIn("[x] Tests", result.stdout)

    def test_status_not_done_blocks(self):
        """STATUS=REVIEWED (not DONE) → exit 1, status check fails."""
        self.spec.write_text(_spec_with_slice("007-01 — land-prepare", "REVIEWED"))
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 1)
        out = result.stdout
        self.assertIn("[ ] Status", out)
        # Names the actual status
        self.assertIn("REVIEWED", out)

    def test_missing_deviation_log_blocks(self):
        """No Deviation log subsection → exit 1, blocker names the gap."""
        self.spec.write_text(_spec_with_slice(
            "007-01 — land-prepare", "DONE",
            include_deviation_log=False))
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 1)
        out = result.stdout
        self.assertIn("[ ] Deviation log", out)

    def test_dod_unticked_blocks(self):
        """2 of 8 DoD boxes unchecked → exit 1; report shows count."""
        self.spec.write_text(_spec_with_slice(
            "007-01 — land-prepare", "DONE",
            dod_ticked=False, dod_count=8, dod_unticked=2))
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 1)
        out = result.stdout
        self.assertIn("[ ] DoD", out)
        # Reports counts: e.g. "6/8 boxes ticked"
        self.assertIn("6/8", out)

    def test_test_check_no_runner_warns_not_blocks(self):
        """If tdd.py returns exit 2 (no runner detected), surface as
        warning — not a hard block. Slice can still land if no tests."""
        self.spec.write_text(_spec_with_slice(
            "007-01 — land-prepare", "DONE"))
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        # tmpdir has no test signals → tdd.py exits 2 → land.py warns
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        out = result.stdout
        # Warning marker — `[?]` (not [x], not [ ])
        self.assertRegex(out, r"(?m)^- \[\?\] Tests")


# -------------------- ModeTests --------------------


class ModeTests(unittest.TestCase):
    """AC #2 — --mode direct / --mode pr / default next-steps."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-land-mode-")
        self.spec = Path(self.tmpdir) / "spec.md"
        # No test signals → tdd.py warns (not blocker)
        self.spec.write_text(_spec_with_slice("007-01 — land-prepare", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_no_next_steps(self):
        """No --mode flag → no Next steps section."""
        result = run_land("prepare", str(self.spec), "007-01",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        self.assertNotIn("Next steps", result.stdout)

    def test_mode_direct_emits_four_git_commands(self):
        """--mode direct → Next steps has the four-line git workflow."""
        result = run_land("prepare", str(self.spec), "007-01",
                          "--mode", "direct",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        out = result.stdout
        self.assertIn("Next steps", out)
        self.assertIn("git checkout main", out)
        self.assertIn("git merge", out)
        self.assertIn("git push origin main", out)
        # worktree-remove is suggested (even if as a comment)
        self.assertIn("git worktree remove", out)

    def test_mode_pr_emits_push_and_gh_create(self):
        """--mode pr → push + gh pr create, plus body file path."""
        result = run_land("prepare", str(self.spec), "007-01",
                          "--mode", "pr",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        out = result.stdout
        self.assertIn("Next steps", out)
        self.assertIn("git push -u origin", out)
        self.assertIn("gh pr create", out)
        # Body file path referenced
        self.assertIn("jig-slice-", out)
        self.assertIn("-pr-body.md", out)

    def test_mode_direct_substitutes_branch(self):
        """direct-mode merge command names the actual current branch."""
        result = run_land("prepare", str(self.spec), "007-01",
                          "--mode", "direct",
                          cwd=Path(self.tmpdir))
        out = result.stdout
        # Branch detection runs against the test cwd which is a tmp dir,
        # NOT a git repo. So branch detection should degrade gracefully
        # to a placeholder. Either way, the merge command must appear.
        self.assertRegex(out, r"git merge \S+\s+--ff-only")


# -------------------- PrBodyTests --------------------


class PrBodyTests(unittest.TestCase):
    """AC #2 (pr-mode body) — PR body file is written with required fields."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-land-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        # No test signals → tdd.py warns (not blocker)
        self.spec.write_text(_spec_with_slice(
            "007-01 — land-prepare", "DONE",
            extra_dev_text="A specific deviation-log paragraph that should appear "
                           "in the PR body excerpt."))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        # Cleanup the well-known PR body file too if created
        for p in Path(tempfile.gettempdir()).glob("jig-slice-*-pr-body.md"):
            try:
                p.unlink()
            except Exception:
                pass

    def _read_pr_body(self) -> str:
        """Locate the PR body file written by --mode pr."""
        candidates = list(Path(tempfile.gettempdir()).glob(
            "jig-slice-*-pr-body.md"))
        self.assertEqual(len(candidates), 1,
                         f"expected exactly one PR body file, got {candidates}")
        return candidates[0].read_text()

    def test_pr_body_file_exists_at_predictable_path(self):
        """--mode pr writes a file at /tmp/jig-slice-<NNN-NN>-pr-body.md."""
        result = run_land("prepare", str(self.spec), "007-01",
                          "--mode", "pr",
                          cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        # The path printed in the report should match a real file
        m = re.search(r"(\S*jig-slice-\d{3}-\d{2}-pr-body\.md)", result.stdout)
        self.assertIsNotNone(m, f"no PR body path in output:\n{result.stdout}")
        body_path = Path(m.group(1))
        self.assertTrue(body_path.is_file(),
                        f"expected PR body file at {body_path}")

    def test_pr_body_contains_slice_label(self):
        run_land("prepare", str(self.spec), "007-01",
                 "--mode", "pr", cwd=Path(self.tmpdir))
        body = self._read_pr_body()
        # Slice label
        self.assertIn("007-01", body)
        self.assertIn("land-prepare", body)

    def test_pr_body_contains_spec_link(self):
        run_land("prepare", str(self.spec), "007-01",
                 "--mode", "pr", cwd=Path(self.tmpdir))
        body = self._read_pr_body()
        # Spec file referenced
        self.assertIn("spec.md", body)

    def test_pr_body_contains_ac_items(self):
        """Numbered AC items from the spec must appear in the body."""
        run_land("prepare", str(self.spec), "007-01",
                 "--mode", "pr", cwd=Path(self.tmpdir))
        body = self._read_pr_body()
        # The synthetic ACs include `foo cmd` and `foo other-cmd` titles
        self.assertIn("foo cmd", body)
        self.assertIn("foo other-cmd", body)

    def test_pr_body_contains_deviation_log_excerpt(self):
        """First-N chars of deviation log appear in body."""
        run_land("prepare", str(self.spec), "007-01",
                 "--mode", "pr", cwd=Path(self.tmpdir))
        body = self._read_pr_body()
        self.assertIn("specific deviation-log paragraph", body)

    def test_pr_body_deviation_log_bounded(self):
        """Deviation log excerpt is capped at ~500 chars to keep PR readable."""
        # Build a spec with a very long deviation log
        long_text = "X" * 2000
        self.spec.write_text(_spec_with_slice(
            "007-01 — land-prepare", "DONE",
            extra_dev_text=long_text))
        run_land("prepare", str(self.spec), "007-01",
                 "--mode", "pr", cwd=Path(self.tmpdir))
        body = self._read_pr_body()
        # No more than ~600 chars of X in the body (allows for ellipsis +
        # surrounding sections)
        x_run = re.search(r"X+", body)
        if x_run is not None:
            self.assertLess(len(x_run.group(0)), 600,
                            "deviation log excerpt exceeded 500-char bound")


# -------------------- ErrorTests --------------------


class ErrorTests(unittest.TestCase):
    """AC #3 — exit 2 on user errors."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-land-err-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_spec(self):
        bogus = Path(self.tmpdir) / "nonexistent.md"
        result = run_land("prepare", str(bogus), "001-01")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_ambiguous_fragment(self):
        spec = Path(self.tmpdir) / "spec.md"
        spec.write_text(
            "## Slice 001-01 alpha\n\n**STATUS: DONE**\n\n"
            "## Slice 001-01 beta\n\n**STATUS: DONE**\n"
        )
        result = run_land("prepare", str(spec), "001-01")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambig", result.stderr.lower())

    def test_no_matching_fragment(self):
        spec = Path(self.tmpdir) / "spec.md"
        spec.write_text("## Slice 001-01 alpha\n\n**STATUS: DONE**\n")
        result = run_land("prepare", str(spec), "999-99")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_invalid_mode(self):
        spec = Path(self.tmpdir) / "spec.md"
        spec.write_text(
            _spec_with_slice("007-01 — land-prepare", "DONE"))
        result = run_land("prepare", str(spec), "007-01",
                          "--mode", "foo")
        self.assertEqual(result.returncode, 2)
        # argparse error mentions invalid choice
        self.assertRegex(result.stderr.lower(), r"invalid|choose from")


# -------------------- SafetyTests --------------------


class SafetyTests(unittest.TestCase):
    """AC #4 — no destructive git/gh subprocess calls in the helper source.

    Read-only `git rev-parse` IS allowed (per spec clarification).
    Forbidden patterns: subprocess invocations of `git checkout`,
    `git merge`, `git push`, `git worktree remove`, `gh pr create`.
    """

    def setUp(self):
        self.source = LAND_PY.read_text()

    def test_no_git_checkout(self):
        # Forbidden: subprocess.run(...) argv containing "checkout" as a literal.
        # (The string "checkout" may legitimately appear in comments / docstrings
        # / the suggested-commands output template — those are not invocations.)
        self.assertNotRegex(
            self.source,
            r'subprocess\.\w+\([^)]*[\'"]checkout[\'"]',
        )

    def test_no_git_merge(self):
        self.assertNotRegex(
            self.source,
            r'subprocess\.\w+\([^)]*[\'"]merge[\'"]',
        )

    def test_no_git_push(self):
        self.assertNotRegex(
            self.source,
            r'subprocess\.\w+\([^)]*[\'"]push[\'"]',
        )

    def test_no_git_worktree_remove(self):
        self.assertNotRegex(
            self.source,
            r'subprocess\.\w+\([^)]*[\'"]worktree[\'"][^)]*[\'"]remove[\'"]',
        )

    def test_no_gh_pr_create(self):
        self.assertNotRegex(
            self.source,
            r'subprocess\.\w+\([^)]*[\'"]gh[\'"]',
        )

    def test_rev_parse_is_allowed(self):
        """Read-only `git rev-parse` for branch detection is permitted —
        spec clarification on AC #4. This test pins that allowance: at
        least one subprocess call to `git rev-parse` should exist (or
        the source should not call git at all)."""
        # Either no git subprocess invocations at all, OR every git call
        # is to "rev-parse" (read-only).
        git_calls = re.findall(
            r'subprocess\.\w+\([^)]*[\'"]git[\'"][^)]*\)',
            self.source,
            re.DOTALL,
        )
        for call in git_calls:
            # Each git call must be rev-parse — no checkout/merge/push/etc.
            self.assertIn("rev-parse", call,
                          f"non-rev-parse git subprocess call: {call}")


# -------------------- SkillSurfaceTests --------------------


class SkillSurfaceTests(unittest.TestCase):
    """AC #5 — SKILL.md surface."""

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text()

    def test_frontmatter_active(self):
        """No `disable-model-invocation` line in the frontmatter."""
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have YAML frontmatter")
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "slice-land must auto-trigger (frontmatter active)")

    def test_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        self.assertNotIn("user-invocable: false", fm)

    def test_description_has_all_six_trigger_phrases(self):
        """AC #5 enumerates six trigger phrases — all must appear in
        the description."""
        # Normalize whitespace because YAML folded scalars (`>`) collapse
        # newlines to spaces.
        normalized = " ".join(self.skill.lower().split())
        triggers = [
            "land this slice",
            "merge back to main",
            "ready to ship",
            "create a pr for this slice",
            "close out the slice",
            "slice is done",
        ]
        for trigger in triggers:
            self.assertIn(trigger, normalized,
                          f"missing trigger phrase: {trigger!r}")

    def test_body_references_land_py_prepare(self):
        self.assertIn("land.py prepare", self.skill,
                      "SKILL.md must reference `land.py prepare`")

    def test_body_references_mode_flag(self):
        self.assertIn("--mode", self.skill,
                      "SKILL.md must document the --mode flag")


if __name__ == "__main__":
    unittest.main()
