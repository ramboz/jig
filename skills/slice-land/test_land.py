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

    def test_close_out_boxes_excluded_from_dod_count(self):
        """Spec 009 / slice 009-01 — `### Close-out` subsection's
        checkboxes do NOT count toward the DoD. Without this, slices that
        include post-DONE items (status-board regen, CLAUDE.md updates)
        can never satisfy DoD before slice-land blesses them.

        Synthetic spec: 4 ticked DoD boxes, then a `### Close-out
        (post-DONE)` subsection with 2 unticked boxes. Without the fix,
        check_dod returns (False, 4, 6) and slice-land flags a blocker.
        With the fix, check_dod returns (True, 4, 4)."""
        spec_text = (
            "---\nstatus: DRAFT\nskill: foo\ntier: 1\n---\n\n"
            "# Spec X: foo\n\n## Overview\n\nSynthetic.\n\n"
            "## Slice 009-01 — close-out-test\n\n"
            "**STATUS: DONE**\n\n"
            "**Goal:** Synthetic goal.\n\n"
            "**Acceptance Criteria:**\n\n1. AC one.\n\n"
            "**DoD:**\n"
            "- [x] Item one.\n"
            "- [x] Item two.\n"
            "- [x] Item three.\n"
            "- [x] Item four.\n\n"
            "### Close-out (post-DONE)\n\n"
            "- [ ] Status-board regenerated AFTER DONE.\n"
            "- [ ] CLAUDE.md updates AFTER DONE.\n\n"
            "### Deviation log (after reconciliation)\n\n"
            "Synthetic log.\n"
        )
        self.spec.write_text(spec_text)
        result = run_land("prepare", str(self.spec), "009-01",
                          cwd=Path(self.tmpdir))
        # DoD should be 4/4 (the 2 close-out boxes are excluded), no
        # blocker for DoD. Tests row will still warn (`[?]`) because
        # tmpdir has no runner — that's not a blocker.
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")
        out = result.stdout
        # DoD row shows `[x] DoD: 4/4 boxes ticked` (NOT 4/6)
        self.assertRegex(out, r"(?m)^- \[x\] DoD: 4/4")
        self.assertNotIn("4/6", out,
                         "close-out boxes leaked into DoD count")

    def test_close_out_heading_is_case_insensitive(self):
        """Spec 009 / slice 009-01 — case variants of the close-out
        heading all delimit the boundary."""
        for heading in ("### Close-out", "### close-out",
                        "### Closeout", "### CLOSE-OUT (post-DONE)"):
            with self.subTest(heading=heading):
                spec_text = (
                    "---\nstatus: DRAFT\nskill: foo\ntier: 1\n---\n\n"
                    "# Spec X\n\n"
                    "## Slice 009-01 — close-out-case-test\n\n"
                    "**STATUS: DONE**\n\n"
                    "**Goal:** g\n\n"
                    "**Acceptance Criteria:**\n\n1. AC.\n\n"
                    "**DoD:**\n- [x] One.\n- [x] Two.\n\n"
                    f"{heading}\n\n- [ ] Post-DONE thing.\n"
                )
                spec = Path(self.tmpdir) / f"spec-{heading[4:8]}.md"
                spec.write_text(spec_text)
                result = run_land("prepare", str(spec), "009-01",
                                  cwd=Path(self.tmpdir))
                out = result.stdout
                self.assertRegex(
                    out, r"(?m)^- \[x\] DoD: 2/2",
                    f"heading {heading!r} not recognized: {out}",
                )


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

    def test_no_gh_calls_in_direct_subprocess(self):
        """Slice 007-03 — `gh` IS legitimately invoked (PR-mode execute),
        but only via the `_run_gh_cmd` helper.  Same precedent as
        slice 007-02's `test_read_only_git_calls_are_bounded`: the
        "gh" literal must NOT appear as an arg inside a
        `subprocess.run([...])` call on the same line.  The literal
        belongs in a local `cmd = ["gh"] + args` assignment that is
        then passed as a variable to subprocess.run."""
        for line in self.source.splitlines():
            stripped = line.strip()
            if re.search(r'subprocess\.\w+\s*\(\s*\[', stripped):
                self.assertNotRegex(
                    stripped,
                    r'"gh"',
                    f"direct gh subprocess call: {stripped!r}",
                )

    def test_read_only_git_calls_are_bounded(self):
        """Slice 007-01 AC #4 (updated for 007-02) — destructive git args
        (`checkout`, `push`) must not appear as literals inside direct
        `subprocess.run(["git", ...])` calls; they must only be passed
        dynamically through `_run_git_cmd`.

        Strategy: scan for direct subprocess calls where the first arg is
        "git" (as a string literal in the same parenthesized group). None
        of those should contain "checkout" or "push" as a literal arg.
        """
        # Collect each single-function-call block by finding
        # subprocess.run(["git", ...]) patterns (single-line list start).
        # We look at each line individually to avoid cross-call matching.
        for line in self.source.splitlines():
            stripped = line.strip()
            if re.search(r'subprocess\.\w+\s*\(\s*\[', stripped):
                # This line starts a subprocess call with a list arg.
                self.assertNotRegex(
                    stripped,
                    r'"(?:checkout|push)"',
                    f"destructive git arg in direct subprocess call: {stripped!r}",
                )
        # At least one read-only git call must exist.
        self.assertRegex(
            self.source,
            r'(?:rev-parse|merge-base)',
            "expected at least one read-only git call (rev-parse or merge-base)",
        )


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


# ==================== Execute subcommand tests (slice 007-02) ====================

import importlib.util as _ilu

# Load land.py as a module for direct-call tests (needed for mocking).
# importlib bypasses the hyphen-in-directory-name limitation.
def _load_land():
    spec = _ilu.spec_from_file_location("_land_module", LAND_PY)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_land = _load_land()


def _make_subprocess_mock(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Return a mock CompletedProcess-like object."""
    from unittest.mock import MagicMock
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


# -------------------- ExecuteBlocksOnReadinessTests --------------------


class ExecuteBlocksOnReadinessTests(unittest.TestCase):
    """AC #1 — blockers prevent any git command from running."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_not_done_blocks_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "IN_PROGRESS",
                             include_deviation_log=True)
        )
        result = run_land("execute", "--mode", "direct",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertEqual(result.returncode, 1)
        # No git sequence log should appear
        self.assertNotIn("Execute log", result.stdout)
        self.assertNotIn("Dry-run", result.stdout)

    def test_missing_dod_blocks_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE",
                             dod_ticked=False, dod_unticked=2,
                             include_deviation_log=True)
        )
        result = run_land("execute", "--mode", "direct",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Execute log", result.stdout)

    def test_missing_deviation_log_blocks_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE",
                             include_deviation_log=False)
        )
        result = run_land("execute", "--mode", "direct",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Execute log", result.stdout)


# -------------------- ExecuteDryRunTests --------------------


class ExecuteDryRunTests(unittest.TestCase):
    """AC #3 — dry-run prints commands, never calls git checkout/merge/push.

    These subprocess tests run from the repo root (no cwd override) so that:
      - git commands (rev-parse, merge-base) work correctly.
      - tdd.py runs against the repo root where tests can be detected.
    The spec path is passed as an absolute path.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dry_run_clean_spec_exits_zero(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE")
        )
        # --target <tmpdir> keeps tdd.py away from the full repo suite.
        result = run_land("execute", "--mode", "direct", "--dry-run",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertEqual(result.returncode, 0,
                         f"stdout: {result.stdout}\nstderr: {result.stderr}")

    def test_dry_run_output_contains_dry_run_section(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE")
        )
        result = run_land("execute", "--mode", "direct", "--dry-run",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        out = result.stdout
        self.assertIn("Dry-run", out)
        self.assertIn("git checkout main", out)
        self.assertIn("git merge", out)
        self.assertIn("git push origin main", out)

    def test_dry_run_does_not_contain_execute_log(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE")
        )
        result = run_land("execute", "--mode", "direct", "--dry-run",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertNotIn("Execute log", result.stdout)

    def test_dry_run_blocked_spec_exits_one(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "IN_PROGRESS",
                             include_deviation_log=True)
        )
        result = run_land("execute", "--mode", "direct", "--dry-run",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Dry-run", result.stdout)

    def test_dry_run_includes_worktree_suggestion(self):
        self.spec.write_text(
            _spec_with_slice("007-02 — test", "DONE")
        )
        result = run_land("execute", "--mode", "direct", "--dry-run",
                          "--target", self.tmpdir,
                          str(self.spec), "007-02")
        # worktree remove must appear as a suggestion, not a live command
        self.assertIn("worktree remove", result.stdout)


# -------------------- ExecuteSafetyTests (direct calls + mocking) --------------------


class ExecuteSafetyBranchTests(unittest.TestCase):
    """AC #4 branch guard — refuses when current branch is main/master."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-02 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _execute_with_branch(self, branch_name: str) -> tuple:
        from unittest.mock import patch, MagicMock
        with patch.object(_land, "_detect_branch", return_value=branch_name), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)):
            return _land.execute(self.spec, "007-02", target=Path(self.tmpdir))

    def test_main_branch_refused(self):
        report, code = self._execute_with_branch("main")
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)
        self.assertIn("main", report)

    def test_master_branch_refused(self):
        report, code = self._execute_with_branch("master")
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)

    def test_feature_branch_not_refused(self):
        from unittest.mock import patch, MagicMock
        with patch.object(_land, "_detect_branch", return_value="feat/my-slice"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")):
            report, code = _land.execute(self.spec, "007-02", target=Path(self.tmpdir))
        self.assertEqual(code, 0)
        self.assertNotIn("Refusing", report)


class ExecuteSafetyFFTests(unittest.TestCase):
    """AC #4 FF viability guard — refuses when main has diverged."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-02 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_diverged_main_refused(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_ff_viable",
                          return_value=(False, "main has diverged — FF merge not possible; pull or rebase first")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)):
            report, code = _land.execute(self.spec, "007-02", target=Path(self.tmpdir))
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)
        self.assertIn("diverged", report)


# -------------------- ExecuteSuccessTests --------------------


class ExecuteSuccessTests(unittest.TestCase):
    """AC #2 — happy path: all git commands succeed → exit 0."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-02 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_execute_success(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/my-slice"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")):
            return _land.execute(self.spec, "007-02", target=Path(self.tmpdir))

    def test_success_exit_zero(self):
        _, code = self._run_execute_success()
        self.assertEqual(code, 0)

    def test_success_report_contains_execute_log(self):
        report, _ = self._run_execute_success()
        self.assertIn("Execute log", report)

    def test_success_report_contains_branch_name(self):
        report, _ = self._run_execute_success()
        self.assertIn("feat/my-slice", report)

    def test_success_report_contains_post_landing_suggestion(self):
        report, _ = self._run_execute_success()
        self.assertIn("Post-landing", report)
        self.assertIn("worktree remove", report)


# -------------------- ExecuteGitFailureTests --------------------


class ExecuteGitFailureTests(unittest.TestCase):
    """AC #2 — if any git command fails, sequence halts and exits 1."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-02 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_merge_failure_exits_one(self):
        from unittest.mock import patch, call

        call_log = []

        def fake_git_cmd(args, cwd, dry_run=False):
            call_log.append(args[0])  # record subcommand
            if args[0] == "merge":
                return False, "CONFLICT (content): Merge conflict in foo.py"
            return True, "ok"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", side_effect=fake_git_cmd):
            report, code = _land.execute(self.spec, "007-02", target=Path(self.tmpdir))

        self.assertEqual(code, 1)
        self.assertIn("Error", report)
        # push must NOT have been called after merge failure
        self.assertNotIn("push", call_log)

    def test_checkout_failure_prevents_merge_and_push(self):
        from unittest.mock import patch

        call_log = []

        def fake_git_cmd(args, cwd, dry_run=False):
            call_log.append(args[0])
            if args[0] == "checkout":
                return False, "error: pathspec 'main' did not match"
            return True, "ok"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", side_effect=fake_git_cmd):
            _, code = _land.execute(self.spec, "007-02", target=Path(self.tmpdir))

        self.assertEqual(code, 1)
        self.assertNotIn("merge", call_log)
        self.assertNotIn("push", call_log)


# -------------------- ExecuteWorktreeNeverRunTests --------------------


class ExecuteWorktreeNeverRunTests(unittest.TestCase):
    """AC #6 — `git worktree remove` is NEVER executed, only suggested."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-02 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _collect_git_calls(self, dry_run: bool = False):
        """Run execute and return list of git subcommand arg-lists called."""
        from unittest.mock import patch

        calls = []

        def fake_git_cmd(args, cwd, dry_run=False):
            calls.append(list(args))
            return True, "ok"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", side_effect=fake_git_cmd):
            _land.execute(self.spec, "007-02", dry_run=dry_run,
                          target=Path(self.tmpdir))

        return calls

    def test_worktree_remove_not_in_live_calls(self):
        calls = self._collect_git_calls(dry_run=False)
        for args in calls:
            self.assertFalse(
                "worktree" in args and "remove" in args,
                f"git worktree remove was executed (must only be suggested): {args}"
            )

    def test_worktree_remove_not_in_dry_run_calls(self):
        calls = self._collect_git_calls(dry_run=True)
        # In dry-run mode _run_git_cmd is not called for git commands,
        # so the call list should be empty.
        for args in calls:
            self.assertFalse(
                "worktree" in args and "remove" in args,
                f"git worktree remove was unexpectedly invoked: {args}"
            )

    def test_worktree_suggestion_appears_in_output_success(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_ff_viable", return_value=(True, "")), \
             patch.object(_land, "_detect_main_worktree_root", return_value=Path(self.tmpdir)), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")):
            report, _ = _land.execute(self.spec, "007-02",
                                      target=Path(self.tmpdir))
        self.assertIn("worktree remove", report)


# -------------------- ExecuteCliSurfaceTests --------------------


class ExecuteCliSurfaceTests(unittest.TestCase):
    """AC #10 — SKILL.md updated to document execute --mode direct."""

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text()

    def test_skill_md_references_execute(self):
        self.assertIn("execute", self.skill.lower(),
                      "SKILL.md must document the execute subcommand")

    def test_skill_md_references_dry_run(self):
        self.assertIn("--dry-run", self.skill,
                      "SKILL.md must document the --dry-run flag")

    def test_skill_md_no_destructive_ops_claim_removed(self):
        """AC #10 requires the 'No destructive git operations' clause in the
        description frontmatter to be replaced once execute ships."""
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m)
        # The old description said "No destructive git operations." verbatim.
        # After 007-02 this must be gone.
        self.assertNotIn("No destructive git operations", m.group(1),
                         "SKILL.md description must be updated for execute")


# ==================== PR-mode execute tests (slice 007-03) ====================


# -------------------- ExecutePrBlocksOnReadinessTests --------------------


class ExecutePrBlocksOnReadinessTests(unittest.TestCase):
    """Slice 007-03 AC #1 — readiness blockers prevent any git/gh
    subprocess from running in PR mode."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_not_done_blocks_pr_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-03 — test", "IN_PROGRESS",
                             include_deviation_log=True)
        )
        result = run_land("execute", "--mode", "pr",
                          "--target", self.tmpdir,
                          str(self.spec), "007-03")
        self.assertEqual(result.returncode, 1)
        # No git or gh execute-log section should appear
        self.assertNotIn("Execute log", result.stdout)
        self.assertNotIn("Dry-run", result.stdout)

    def test_missing_dod_blocks_pr_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-03 — test", "DONE",
                             dod_ticked=False, dod_unticked=2,
                             include_deviation_log=True)
        )
        result = run_land("execute", "--mode", "pr",
                          "--target", self.tmpdir,
                          str(self.spec), "007-03")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Execute log", result.stdout)

    def test_missing_deviation_log_blocks_pr_execute(self):
        self.spec.write_text(
            _spec_with_slice("007-03 — test", "DONE",
                             include_deviation_log=False)
        )
        result = run_land("execute", "--mode", "pr",
                          "--target", self.tmpdir,
                          str(self.spec), "007-03")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Execute log", result.stdout)


# -------------------- ExecutePrDryRunTests --------------------


class ExecutePrDryRunTests(unittest.TestCase):
    """Slice 007-03 AC #4 — dry-run prints commands but never invokes
    git push or gh pr create.  PR body file IS written so the user
    can inspect it before live invocation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for p in Path(tempfile.gettempdir()).glob("jig-slice-*-pr-body.md"):
            try:
                p.unlink()
            except Exception:
                pass

    def _execute_pr_dry_run(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")):
            return _land.execute(self.spec, "007-03", mode="pr",
                                 dry_run=True, target=Path(self.tmpdir))

    def test_dry_run_clean_spec_exits_zero(self):
        _, code = self._execute_pr_dry_run()
        self.assertEqual(code, 0)

    def test_dry_run_output_contains_dry_run_section(self):
        report, _ = self._execute_pr_dry_run()
        self.assertIn("Dry-run", report)
        self.assertIn("git push", report)
        self.assertIn("gh pr create", report)

    def test_dry_run_writes_pr_body_file(self):
        report, _ = self._execute_pr_dry_run()
        # PR body file referenced in the report and on disk
        m = re.search(r"(\S*jig-slice-\d{3}-\d{2}-pr-body\.md)", report)
        self.assertIsNotNone(m, f"no PR body path in report:\n{report}")
        self.assertTrue(Path(m.group(1)).is_file(),
                        f"PR body file not written at {m.group(1)}")

    def test_dry_run_no_live_subprocess(self):
        """Dry-run must not call _run_git_cmd or _run_gh_cmd with
        dry_run=False (no live execution)."""
        from unittest.mock import patch, MagicMock
        # Wrap the helpers so we can inspect dry_run kwarg per-call
        git_calls = []
        gh_calls = []

        def fake_git(args, cwd, dry_run=False):
            git_calls.append((list(args), dry_run))
            return True, "[dry-run] git " + " ".join(args)

        def fake_gh(args, cwd, dry_run=False):
            gh_calls.append((list(args), dry_run))
            return True, "[dry-run] gh " + " ".join(args)

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd", side_effect=fake_git), \
             patch.object(_land, "_run_gh_cmd", side_effect=fake_gh):
            _land.execute(self.spec, "007-03", mode="pr",
                          dry_run=True, target=Path(self.tmpdir))

        # In dry-run mode, every call to git/gh must have dry_run=True
        for args, dr in git_calls:
            self.assertTrue(dr, f"git called live in dry-run: {args}")
        for args, dr in gh_calls:
            self.assertTrue(dr, f"gh called live in dry-run: {args}")

    def test_dry_run_blocked_spec_exits_one(self):
        self.spec.write_text(
            _spec_with_slice("007-03 — test", "IN_PROGRESS",
                             include_deviation_log=True)
        )
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")):
            report, code = _land.execute(self.spec, "007-03", mode="pr",
                                         dry_run=True,
                                         target=Path(self.tmpdir))
        self.assertEqual(code, 1)
        self.assertNotIn("Dry-run", report)


# -------------------- ExecutePrSafetyBranchTests --------------------


class ExecutePrSafetyBranchTests(unittest.TestCase):
    """Slice 007-03 AC #5 — refuses when current branch is main/master."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _execute_with_branch(self, branch_name: str):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value=branch_name), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")):
            return _land.execute(self.spec, "007-03", mode="pr",
                                 target=Path(self.tmpdir))

    def test_main_branch_refused(self):
        report, code = self._execute_with_branch("main")
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)
        self.assertIn("main", report)

    def test_master_branch_refused(self):
        report, code = self._execute_with_branch("master")
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)


# -------------------- ExecutePrSafetyGhMissingTests --------------------


class ExecutePrSafetyGhMissingTests(unittest.TestCase):
    """Slice 007-03 AC #5 — refuses when `gh` binary is not on PATH."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_gh_missing_refused(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available",
                          return_value=(False, "'gh' CLI not found on PATH")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")):
            report, code = _land.execute(self.spec, "007-03", mode="pr",
                                         target=Path(self.tmpdir))
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)
        self.assertIn("gh", report)


# -------------------- ExecutePrSafetyNoGithubRemoteTests --------------------


class ExecutePrSafetyNoGithubRemoteTests(unittest.TestCase):
    """Slice 007-03 AC #5 — refuses when origin doesn't point at github.com."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_no_github_remote_refused(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote",
                          return_value=(False, "remote 'origin' does not point at github.com")):
            report, code = _land.execute(self.spec, "007-03", mode="pr",
                                         target=Path(self.tmpdir))
        self.assertEqual(code, 1)
        self.assertIn("Refusing", report)
        self.assertIn("github", report.lower())


# -------------------- ExecutePrSuccessTests --------------------


class ExecutePrSuccessTests(unittest.TestCase):
    """Slice 007-03 AC #2 — happy path: push + gh pr create both succeed."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for p in Path(tempfile.gettempdir()).glob("jig-slice-*-pr-body.md"):
            try:
                p.unlink()
            except Exception:
                pass

    def _run_execute_pr_success(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/my-slice"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")), \
             patch.object(_land, "_run_gh_cmd",
                          return_value=(True, "https://github.com/org/repo/pull/42")):
            return _land.execute(self.spec, "007-03", mode="pr",
                                 target=Path(self.tmpdir))

    def test_success_exit_zero(self):
        _, code = self._run_execute_pr_success()
        self.assertEqual(code, 0)

    def test_success_report_contains_execute_log(self):
        report, _ = self._run_execute_pr_success()
        self.assertIn("Execute log", report)

    def test_success_report_contains_push_step(self):
        report, _ = self._run_execute_pr_success()
        self.assertIn("git push", report)

    def test_success_report_contains_gh_pr_create_step(self):
        report, _ = self._run_execute_pr_success()
        self.assertIn("gh pr create", report)

    def test_success_report_contains_post_landing(self):
        report, _ = self._run_execute_pr_success()
        self.assertIn("Post-landing", report)
        # PR mode mentions gh pr merge / GitHub UI as the close-out step
        self.assertRegex(report, r"(?i)gh pr merge|github\s*ui")

    def test_success_pr_body_file_written(self):
        self._run_execute_pr_success()
        candidates = list(Path(tempfile.gettempdir()).glob(
            "jig-slice-*-pr-body.md"))
        self.assertEqual(len(candidates), 1,
                         f"expected exactly one PR body file, got {candidates}")

    def test_pr_title_uses_frontmatter_skill_scope(self):
        """Slice 007-03 AC #2 — `gh pr create --title` arg must follow the
        `feat(<skill>): <slice-label>` shape, with `<skill>` pulled from
        the spec frontmatter (`foo` for the synthetic spec used here).
        Reviewer feedback (implementation review §1) pinned this as an
        explicit-surface gap on the success path."""
        from unittest.mock import patch
        title_seen = []

        def fake_gh(args, cwd, dry_run=False):
            for i, a in enumerate(args):
                if a == "--title" and i + 1 < len(args):
                    title_seen.append(args[i + 1])
            return True, "ok"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")), \
             patch.object(_land, "_run_gh_cmd", side_effect=fake_gh):
            _land.execute(self.spec, "007-03", mode="pr",
                          target=Path(self.tmpdir))

        self.assertEqual(len(title_seen), 1,
                         f"expected exactly one --title arg, got {title_seen}")
        title = title_seen[0]
        # Synthetic spec frontmatter is `skill: foo`
        self.assertRegex(title, r"^feat\(foo\):\s+007-03",
                         f"title shape mismatch: {title!r}")


# -------------------- ExecutePrPushFailureTests --------------------


class ExecutePrPushFailureTests(unittest.TestCase):
    """Slice 007-03 AC #2 — push failure halts the sequence; gh NOT called."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_push_failure_exits_one_and_skips_gh(self):
        from unittest.mock import patch
        gh_call_log = []

        def fake_gh(args, cwd, dry_run=False):
            gh_call_log.append(list(args))
            return True, "should not be called"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd",
                          return_value=(False, "error: failed to push some refs")), \
             patch.object(_land, "_run_gh_cmd", side_effect=fake_gh):
            report, code = _land.execute(self.spec, "007-03", mode="pr",
                                         target=Path(self.tmpdir))

        self.assertEqual(code, 1)
        self.assertIn("Error", report)
        # gh pr create must NOT have been called after push failure
        self.assertEqual(gh_call_log, [],
                         f"gh was invoked despite push failure: {gh_call_log}")


# -------------------- ExecutePrGhFailureTests --------------------


class ExecutePrGhFailureTests(unittest.TestCase):
    """Slice 007-03 AC #2 — gh pr create failure surfaces in the report."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_gh_failure_exits_one_after_successful_push(self):
        from unittest.mock import patch
        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "pushed")), \
             patch.object(_land, "_run_gh_cmd",
                          return_value=(False, "a pull request for branch already exists")):
            report, code = _land.execute(self.spec, "007-03", mode="pr",
                                         target=Path(self.tmpdir))

        self.assertEqual(code, 1)
        self.assertIn("Error", report)
        self.assertIn("already exists", report)


# -------------------- ExecutePrBodyFileWrittenTests --------------------


class ExecutePrBodyFileWrittenTests(unittest.TestCase):
    """Slice 007-03 AC #3 — PR body file is written before gh pr create."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-exec-pr-")
        self.spec = Path(self.tmpdir) / "spec.md"
        self.spec.write_text(_spec_with_slice("007-03 — test", "DONE"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for p in Path(tempfile.gettempdir()).glob("jig-slice-*-pr-body.md"):
            try:
                p.unlink()
            except Exception:
                pass

    def test_body_file_exists_before_gh_call_in_live_mode(self):
        """When gh is invoked, the body file path passed to gh must exist."""
        from unittest.mock import patch

        body_paths_seen = []

        def fake_gh(args, cwd, dry_run=False):
            # Extract the --body-file path from the args
            for i, a in enumerate(args):
                if a == "--body-file" and i + 1 < len(args):
                    body_paths_seen.append(args[i + 1])
            return True, "ok"

        with patch.object(_land, "_detect_branch", return_value="feat/test"), \
             patch.object(_land, "_check_gh_available", return_value=(True, "")), \
             patch.object(_land, "_check_github_remote", return_value=(True, "")), \
             patch.object(_land, "_run_git_cmd", return_value=(True, "ok")), \
             patch.object(_land, "_run_gh_cmd", side_effect=fake_gh):
            _land.execute(self.spec, "007-03", mode="pr",
                          target=Path(self.tmpdir))

        self.assertEqual(len(body_paths_seen), 1,
                         f"expected exactly one --body-file path, got {body_paths_seen}")
        body_path = Path(body_paths_seen[0])
        self.assertTrue(body_path.is_file(),
                        f"PR body file does not exist at {body_path}")


# -------------------- ExecutePrCliSurfaceTests --------------------


class ExecutePrCliSurfaceTests(unittest.TestCase):
    """Slice 007-03 AC #12 — SKILL.md documents --mode pr."""

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text()

    def test_skill_md_references_pr_mode_execute(self):
        """SKILL.md's How-to-use section must document `execute --mode pr`."""
        # Single search — either `--mode pr` appears in the body, or the
        # explicit `execute --mode pr` phrase does
        body = self.skill.lower()
        self.assertTrue(
            "--mode pr" in body or "execute --mode pr" in body,
            "SKILL.md must document `execute --mode pr`",
        )


if __name__ == "__main__":
    unittest.main()
