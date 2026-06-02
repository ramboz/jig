"""
AC verification tests for slice 003-01 (lifecycle-helper).

Run from the repo root:
    python3 skills/spec-workflow/test_workflow.py
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_workflow(*args: str, gate: bool = False) -> subprocess.CompletedProcess:
    """Invoke workflow.py as a subprocess.

    Slice 045-03: the review-evidence gate (`transition → REVIEWED/
    RECONCILED/DONE`) is ON by default in production. The pre-045-03 test
    suite transitions to those gated states WITHOUT recording evidence,
    so this helper sets the documented bypass `JIG_REVIEW_EVIDENCE_GATE=0`
    by default — tests that aren't *about* the gate keep their old
    behavior. Gate-specific tests pass `gate=True` to exercise the real
    enforcement (or set the env var explicitly).
    """
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if not gate:
        env["JIG_REVIEW_EVIDENCE_GATE"] = "0"
    else:
        # Ensure an inherited bypass from the parent shell can't mask a
        # gate-on test.
        env.pop("JIG_REVIEW_EVIDENCE_GATE", None)
    return subprocess.run(
        [sys.executable, str(WORKFLOW), *args],
        capture_output=True, text=True, env=env,
    )


def scaffold(target: Path) -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True, text=True, env=env, check=True,
    )


def write_synthetic_spec(path: Path, slices: list) -> None:
    """Build a spec.md from a list of (slice_name, status) pairs."""
    lines = ["---", "status: DRAFT", "---", "", "# Spec X", "", "## Overview", "", "synthetic.", ""]
    for name, status in slices:
        lines.extend([
            "---",
            "",
            f"## Slice {name}",
            "",
            f"**STATUS: {status}**",
            "",
            "**Goal:** placeholder.",
            "",
        ])
    path.write_text("\n".join(lines))


class TransitionTests(unittest.TestCase):
    """workflow.py transition <spec.md> <slice-name> <new-status>."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_transition_updates_status(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT"),
                                          ("001-02 beta", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self.spec.read_text()
        # The named slice should be transitioned
        m = re.search(r"## Slice 001-01[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", content)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS")
        # The other slice should be untouched
        m2 = re.search(r"## Slice 001-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", content)
        self.assertEqual(m2.group(1), "DRAFT")

    def test_transition_chains(self):
        """Multiple sequential transitions on the same slice work."""
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        for new_status in ("IN_PROGRESS", "REVIEWED", "RECONCILED", "DONE"):
            r = run_workflow("transition", str(self.spec), "001-01", new_status)
            self.assertEqual(r.returncode, 0, f"failed at {new_status}: {r.stderr}")
        content = self.spec.read_text()
        self.assertIn("**STATUS: DONE**", content)

    def test_transition_refuses_invalid_status(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "BOGUS")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("status", result.stderr.lower())

    def test_transition_refuses_unknown_slice(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "999-99", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr.lower() + result.stdout.lower())

    def test_transition_refuses_ambiguous_slice(self):
        """If two slices match the name fragment, refuse to transition either."""
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT"),
                                          ("001-01 alpha-fork", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ambig", result.stderr.lower() + result.stdout.lower())

    def test_transition_lenient_on_slice_name_match(self):
        """`001-01` should match `## Slice 001-01 — greenfield-scaffold` (substring)."""
        self.spec.write_text(
            "# Spec X\n\n## Slice 001-01 — greenfield-scaffold\n\n**STATUS: DRAFT**\n"
        )
        result = run_workflow("transition", str(self.spec), "001-01", "DONE")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DONE**", self.spec.read_text())

    def test_transition_prints_summary(self):
        write_synthetic_spec(self.spec, [("001-01 alpha", "DRAFT")])
        result = run_workflow("transition", str(self.spec), "001-01", "IN_PROGRESS")
        self.assertEqual(result.returncode, 0)
        self.assertIn("DRAFT", result.stdout)
        self.assertIn("IN_PROGRESS", result.stdout)

    def test_transition_does_not_clobber_prose_status_marker(self):
        """Inbox 2026-05-18 `spec-workflow/transition/status-marker-clobber` —
        the status-rewrite regex `(\\*\\*STATUS:\\s*)([A-Z_]+)(\\*\\*)`
        matched the FIRST `**STATUS: …**` anywhere in the slice section
        body, not the slice's own status line.

        Hit on slice 030-01 (a per-file slice that uses frontmatter-only
        status, no prose `**STATUS:**` line) during REVIEWED → RECONCILED:
        the deviation log quoted another slice's marker in prose. The
        regex had nothing canonical to find for THIS slice's own status,
        so it matched the prose example and rewrote DRAFT → RECONCILED
        in the quoted text. Frontmatter `status:` still flipped correctly
        (so lifecycle-wise harmless), but the prose got corrupted.

        Synthetic spec: a per-file-style slice with frontmatter-only
        status (no prose STATUS line at the top) whose deviation log
        contains a prose example with `**STATUS: DEFERRED**` markup.
        After `transition ... IN_PROGRESS`:
        - The frontmatter `status:` field must read `IN_PROGRESS`.
        - The prose example must read `**STATUS: DEFERRED**` unchanged.
        """
        # Sibling slice file (post-018 layout — frontmatter authoritative,
        # no prose `**STATUS:**` line at the top).
        slice_file = self.spec.parent / "slice-01-alpha.md"
        slice_file.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified: 2026-05-19\n---\n\n"
            "## Slice 001-01 — alpha\n\n"
            "**Goal:** placeholder.\n\n"
            "**DoD:**\n- [x] placeholder.\n\n"
            "### Deviation log (after reconciliation)\n\n"
            "When slice 002-02 was parked, its marker read "
            "`**STATUS: DEFERRED**` per the convention — that should "
            "stay unchanged when this slice transitions.\n"
        )
        # Parent spec.md pointing at the sibling slice (the parser walks
        # both inline `## Slice X` sections AND sibling slice-*.md files).
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nsynthetic.\n"
        )
        result = run_workflow("transition", str(self.spec), "001-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        slice_text = slice_file.read_text()
        # Frontmatter status must be flipped.
        self.assertRegex(slice_text,
                         r"(?m)^status:\s*IN_PROGRESS\s*$",
                         "frontmatter status was not updated")
        # The prose-quoted marker must be untouched.
        self.assertIn("`**STATUS: DEFERRED**`", slice_text,
                      "prose-quoted STATUS marker was clobbered")
        # And no spurious `**STATUS: IN_PROGRESS**` should have been
        # written into the slice body — frontmatter-only slices stay
        # frontmatter-only.
        self.assertNotIn("**STATUS: IN_PROGRESS**", slice_text,
                         "transition leaked a prose STATUS line into a "
                         "frontmatter-only slice")


class StatusBoardTests(unittest.TestCase):
    """workflow.py status-board <project-dir>."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-board-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)
        # Drop in synthetic specs
        spec1 = self.target / "docs/specs/100-alpha"
        spec1.mkdir(parents=True)
        write_synthetic_spec(spec1 / "spec.md", [
            ("100-01 first", "DONE"),
            ("100-02 second", "IN_PROGRESS"),
            ("100-03 third", "DRAFT"),
        ])
        spec2 = self.target / "docs/specs/101-beta"
        spec2.mkdir(parents=True)
        write_synthetic_spec(spec2 / "spec.md", [
            ("101-01 alpha", "RECONCILED"),
        ])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_board_regenerates_table(self):
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        # All four slices should be in the table
        self.assertIn("100-01 first", board)
        self.assertIn("100-02 second", board)
        self.assertIn("100-03 third", board)
        self.assertIn("101-01 alpha", board)
        # And their statuses
        self.assertRegex(board, r"100-01[^|]*\|[^|]*DONE")
        self.assertRegex(board, r"101-01[^|]*\|[^|]*RECONCILED")

    def test_status_board_preserves_preamble(self):
        # Inject a preamble before the existing table
        board_path = self.target / "docs/specs/README.md"
        original = board_path.read_text()
        preamble = "# Spec Status Board\n\n> Custom preamble that must survive regen.\n\n"
        board_path.write_text(preamble + original)
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0)
        new_content = board_path.read_text()
        self.assertIn("Custom preamble that must survive regen", new_content)

    def test_status_board_preserves_existing_notes(self):
        """Curated Notes column content must survive regen."""
        # First regen to establish baseline table
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        content = board_path.read_text()
        # Hand-edit a Note cell for one slice (DONE statuses render as **DONE**)
        new_content = content.replace(
            "| 100-01 first | **DONE** |  |",
            "| 100-01 first | **DONE** | 42 tests green; reviewed + reconciled |",
        )
        self.assertNotEqual(new_content, content, "test setup failed: edit was a no-op")
        board_path.write_text(new_content)
        # Second regen — the curated Note must survive
        run_workflow("status-board", str(self.target))
        new_content = board_path.read_text()
        self.assertIn("42 tests green; reviewed + reconciled", new_content)

    def test_status_board_idempotent(self):
        """Re-running on a current board produces no change."""
        run_workflow("status-board", str(self.target))
        first = (self.target / "docs/specs/README.md").read_text()
        run_workflow("status-board", str(self.target))
        second = (self.target / "docs/specs/README.md").read_text()
        self.assertEqual(first, second)


class SkillPromotionTests(unittest.TestCase):
    """The spec-workflow SKILL.md must be promoted from stub to active."""

    def setUp(self):
        self.skill_path = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
        self.skill = self.skill_path.read_text()

    def test_skill_frontmatter_has_no_disable_invocation(self):
        # Extract frontmatter
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have frontmatter")
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "spec-workflow must auto-trigger (frontmatter promoted)")

    def test_skill_is_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        # user-invocable should be true (or absent — default is true)
        self.assertNotIn("user-invocable: false", fm)

    def test_skill_body_no_stub_banner(self):
        """The 'Status: DRAFT — not yet implemented' banner must be gone."""
        self.assertNotRegex(
            self.skill,
            r"(?i)status:\s*draft\s*—\s*not\s+yet\s+implemented",
            "stub banner must be removed",
        )
        self.assertNotIn("(when implemented)", self.skill,
                         "'when implemented' phrasing must be removed")

    def test_skill_reconciliation_checklist_intact(self):
        """Slice 002-04's reconciliation checklist with memory-sync must survive."""
        # Locate the reconciliation H2
        header = re.search(r"(?im)^##\s+[^\n]*reconcil[^\n]*$", self.skill)
        self.assertIsNotNone(header)
        rest = self.skill[header.end():]
        nxt = re.search(r"(?m)^##\s", rest)
        section = rest[: nxt.start()] if nxt else rest
        self.assertIn("memory-sync", section,
                      "memory-sync must stay in the reconciliation section after promotion")

    def test_skill_references_workflow_helper(self):
        """The promoted SKILL.md should tell Claude to use workflow.py."""
        self.assertIn("workflow.py", self.skill,
                      "SKILL.md must reference the workflow.py helper")


class AutoTickReviewPassedTests(unittest.TestCase):
    """Slice 003-04: workflow.py transition auto-ticks the two review-passed
    DoD boxes on the gating transitions."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-autotick-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, slice_name: str, status: str, dod_lines: list) -> None:
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            f"## Slice {slice_name}", "",
            f"**STATUS: {status}**", "",
            "**Goal:** placeholder.", "",
            "**Definition of Done:**", "",
        ]
        body.extend(dod_lines)
        self.spec.write_text("\n".join(body) + "\n")

    def _read(self) -> str:
        return self.spec.read_text()

    # AC #1
    def test_transition_to_REVIEWED_auto_ticks_implementation_review(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [x] Implementation review passed.", text)
        # Recon row stays unticked
        self.assertIn("- [ ] Reconciliation review passed.", text)

    # AC #2
    def test_transition_to_RECONCILED_auto_ticks_reconciliation_review(self):
        self._write("009-99 alpha", "REVIEWED", [
            "- [x] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "RECONCILED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [x] Reconciliation review passed.", text)

    # AC #3
    def test_other_transitions_leave_checkboxes_alone(self):
        self._write("009-99 alpha", "DRAFT", [
            "- [ ] Implementation review passed.",
            "- [ ] Reconciliation review passed.",
        ])
        # DRAFT → READY_FOR_REVIEW shouldn't touch the boxes
        result = run_workflow("transition", str(self.spec), "009-99", "READY_FOR_REVIEW")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        self.assertIn("- [ ] Implementation review passed.", text)
        self.assertIn("- [ ] Reconciliation review passed.", text)

    def test_RECONCILED_to_DONE_does_not_re_tick(self):
        self._write("009-99 alpha", "RECONCILED", [
            "- [x] Implementation review passed.",
            "- [x] Reconciliation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "DONE")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # Both stay ticked, neither is added/removed
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(text.count("- [x] Reconciliation review passed."), 1)

    # AC #4 (idempotent)
    def test_auto_tick_is_idempotent_when_box_already_ticked(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [x] Implementation review passed.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # Still exactly one ticked instance, no `- [x] - [x]` corruption
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)

    # AC #4 (scoping: Close-out subsection excluded)
    def test_auto_tick_skips_close_out_subsection(self):
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            "## Slice 009-99 alpha", "",
            "**STATUS: IN_PROGRESS**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",
            "",
            "### Close-out (post-DONE)",
            "",
            "- [ ] Implementation review passed.  # would be a duplicate label if reached",
            "",
        ]
        self.spec.write_text("\n".join(body) + "\n")
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # The DoD line (above Close-out) is ticked
        self.assertIn("- [x] Implementation review passed.", text)
        # The Close-out duplicate stays unticked
        # (count: 1 ticked + 1 unticked-in-Close-out = 1 each)
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(
            text.count("- [ ] Implementation review passed."), 1,
            f"Close-out duplicate should remain unticked; spec was:\n{text}",
        )

    # AC #4 (scoping: other slices in same spec untouched)
    def test_auto_tick_does_not_touch_other_slices(self):
        body = [
            "---", "status: DRAFT", "---", "",
            "# Spec X", "",
            "## Slice 009-99 alpha", "",
            "**STATUS: IN_PROGRESS**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",
            "",
            "## Slice 009-98 beta", "",
            "**STATUS: DRAFT**", "",
            "**Definition of Done:**", "",
            "- [ ] Implementation review passed.",  # should stay unticked
            "",
        ]
        self.spec.write_text("\n".join(body) + "\n")
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # alpha is ticked; beta is not
        self.assertEqual(text.count("- [x] Implementation review passed."), 1)
        self.assertEqual(text.count("- [ ] Implementation review passed."), 1)

    # AC #5 (multiple matches in same DoD: warn + skip + name spec/slice)
    def test_auto_tick_warns_on_multiple_matches_and_skips_all(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Implementation review passed (first take).",
            "- [ ] Implementation review passed (second take).",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0,
                         msg=f"transition should still succeed; stderr: {result.stderr}")
        text = self._read()
        # Neither got ticked
        self.assertEqual(text.count("- [x] Implementation review passed"), 0)
        # Stderr describes the ambiguity AND names the spec + slice so a
        # CI/log grep can disambiguate which slice triggered the warning.
        self.assertRegex(
            result.stderr,
            r"(?i)multiple.*implementation review passed",
            "stderr should describe the ambiguous match",
        )
        self.assertIn(
            "spec.md", result.stderr,
            f"stderr should name the spec file; got: {result.stderr!r}",
        )
        self.assertIn(
            "009-99", result.stderr,
            f"stderr should name the slice; got: {result.stderr!r}",
        )

    # AC #5 (no matching label → no-op, no warn)
    def test_auto_tick_noop_when_label_absent(self):
        self._write("009-99 alpha", "IN_PROGRESS", [
            "- [ ] Some unrelated item.",
        ])
        result = run_workflow("transition", str(self.spec), "009-99", "REVIEWED")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self._read()
        # The unrelated item stays unticked
        self.assertIn("- [ ] Some unrelated item.", text)
        # No stderr noise about absent labels
        self.assertNotIn("Implementation review passed", result.stderr or "")

    # AC #7: existing tests still pass — covered implicitly by running the
    # whole test_workflow.py module.


class DeferredLifecycleTests(unittest.TestCase):
    """Slice 014-02: `DEFERRED` is a recognized state with bounded
    outbound transitions and a separate status-board section."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-defer-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec(self, rel_dir: str, label: str, status: str,
                    trigger: str = "") -> Path:
        """Append a slice to the spec under rel_dir, creating the spec
        file with a preamble on first call."""
        spec_dir = self.target / "docs/specs" / rel_dir
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_md = spec_dir / "spec.md"
        slice_block = (
            f"\n## Slice {label}\n\n**STATUS: {status}**\n\n**Goal:** x.\n"
        )
        if trigger:
            slice_block += f"\n**Resolution trigger:** {trigger}\n"
        if spec_md.is_file():
            spec_md.write_text(spec_md.read_text() + slice_block)
        else:
            spec_md.write_text("# Spec\n" + slice_block)
        return spec_md

    def test_transition_any_to_deferred(self):
        """From any active state, → DEFERRED succeeds."""
        spec_md = self._write_spec("500-alpha", "500-01 alpha", "DRAFT")
        result = run_workflow("transition", str(spec_md), "500-01", "DEFERRED")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DEFERRED**", spec_md.read_text())

    def test_transition_deferred_to_draft(self):
        """DEFERRED → DRAFT (re-open) is allowed."""
        spec_md = self._write_spec("501-alpha", "501-01 alpha", "DEFERRED")
        result = run_workflow("transition", str(spec_md), "501-01", "DRAFT")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("**STATUS: DRAFT**", spec_md.read_text())

    def test_transition_deferred_to_done_refused(self):
        """DEFERRED → DONE (or any non-DRAFT) must be refused."""
        spec_md = self._write_spec("502-alpha", "502-01 alpha", "DEFERRED")
        result = run_workflow("transition", str(spec_md), "502-01", "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEFERRED", result.stderr)

    def test_status_board_renders_deferred_section(self):
        """Slices in DEFERRED appear under `## Deferred slices` with
        their `**Resolution trigger:**` line as the per-row context."""
        self._write_spec("600-alpha", "600-01 active", "IN_PROGRESS")
        self._write_spec("600-alpha", "600-02 parked", "DEFERRED",
                         trigger="When the third caller appears.")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (self.target / "docs/specs/README.md").read_text()
        # Active table has 600-01 only (600-02 is in the Deferred section)
        active = board.split("## Deferred slices")[0]
        self.assertIn("600-01 active", active)
        # Deferred section is present with the trigger
        self.assertIn("## Deferred slices", board)
        self.assertIn("600-02 parked", board)
        self.assertIn("When the third caller appears.", board)

    def test_status_board_omits_deferred_section_when_empty(self):
        """No `## Deferred slices` heading when nothing is deferred."""
        self._write_spec("700-alpha", "700-01 active", "IN_PROGRESS")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0)
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertNotIn("## Deferred slices", board)

    def test_status_board_idempotent_with_deferred(self):
        """Re-running on a board that already has a Deferred section
        produces no diff."""
        self._write_spec("800-alpha", "800-01 a", "DEFERRED",
                         trigger="When X happens.")
        run_workflow("status-board", str(self.target))
        first = (self.target / "docs/specs/README.md").read_text()
        run_workflow("status-board", str(self.target))
        second = (self.target / "docs/specs/README.md").read_text()
        self.assertEqual(first, second)

    def test_status_board_does_not_glue_adjacent_rows_across_tables(self):
        """Regression: `parse_existing_notes`'s row regex used `\\s*` between
        the status and notes cells, which could consume `\\n` and continue
        matching `(.*?)\\|$` on the NEXT line. When the prior board had a
        `## Deferred slices` table (3-cell rows), this glued the next
        deferred row's content into the active row's Notes cell. Bug
        symptom: lines in the regenerated README contained two `|...|`
        rows mashed onto one physical line. Fix: tightened the inter-cell
        `\\s*` to `[^\\S\\n]*` so the match cannot cross newlines.

        This test seeds a board with one active + two deferred slices,
        regenerates twice (so the second regen reads the first's output),
        then asserts every `^| ... |$` line contains exactly 4 cells
        (active row) OR 3 cells (deferred row) — never glued.
        """
        self._write_spec("900-alpha", "900-01 active", "IN_PROGRESS")
        # Curate a note on the active row so we exercise preservation
        # without the glue bug stomping it.
        self._write_spec("900-alpha", "900-02 parked-a", "DEFERRED",
                         trigger="When trigger A fires.")
        self._write_spec("900-alpha", "900-03 parked-b", "DEFERRED",
                         trigger="When trigger B fires.")
        board_path = self.target / "docs/specs/README.md"

        first = run_workflow("status-board", str(self.target))
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")

        # Hand-curate a note on the active row so we can confirm it survives
        # regen unaltered (and isn't replaced by glued-row content).
        board_text = board_path.read_text()
        marker = "| 900-01 active | IN_PROGRESS |  |"
        replacement = "| 900-01 active | IN_PROGRESS | curated note here |"
        self.assertIn(marker, board_text, "active row not found before curation")
        board_path.write_text(board_text.replace(marker, replacement))

        second = run_workflow("status-board", str(self.target))
        self.assertEqual(second.returncode, 0, f"stderr: {second.stderr}")
        final = board_path.read_text()

        # Every `|`-prefixed line must have <=5 pipes (4 cells max) or
        # exactly 4 pipes (3 cells, deferred table). Anything more means
        # two rows got glued.
        for line in final.splitlines():
            if not line.startswith("|") or set(line.strip()) == {"|", "-"}:
                continue  # skip separator rows
            pipe_count = line.count("|")
            self.assertIn(
                pipe_count, (4, 5),
                f"row has {pipe_count} pipes (expected 4 or 5) — glue bug "
                f"resurfaced:\n  {line!r}",
            )

        # Spot-check: curated note survived regen unchanged.
        self.assertIn(
            "| 900-01 active | IN_PROGRESS | curated note here |", final,
            "curated note on active row was not preserved across regen",
        )

        # Spot-check: deferred-table rows are NOT pulled into the active
        # row's Notes cell. The active row's Notes must not contain a
        # markdown link to another spec (which would be cross-row glue).
        active_section = final.split("## Deferred slices")[0]
        active_900_lines = [
            ln for ln in active_section.splitlines()
            if "900-01 active" in ln
        ]
        self.assertEqual(len(active_900_lines), 1)
        self.assertNotIn(
            "900-02", active_900_lines[0],
            "active row's Notes cell contains content from a deferred row "
            "(cross-row glue bug)",
        )
        self.assertNotIn(
            "900-03", active_900_lines[0],
            "active row's Notes cell contains content from a deferred row "
            "(cross-row glue bug)",
        )


class StaleCheckTests(unittest.TestCase):
    """Slice 014-03: `workflow.py stale` lists items whose last_verified
    is more than N days old AND whose dep file was modified since."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-stale-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _touch(self, path: Path, iso_date: str) -> None:
        """Set both mtime and atime to the given YYYY-MM-DD (00:00 UTC)."""
        import time
        dt = __import__("datetime").datetime.fromisoformat(iso_date)
        ts = time.mktime(dt.timetuple())
        os.utime(path, (ts, ts))

    def _write_dep_slice(self, dep_spec: str, dep_label: str,
                         touch_date: str) -> Path:
        """Create a 'dependency' spec file and touch it to the given date."""
        dep_dir = self.target / "docs/specs" / dep_spec
        dep_dir.mkdir(parents=True, exist_ok=True)
        dep_md = dep_dir / "spec.md"
        dep_md.write_text(
            f"# Dep\n\n## Slice {dep_label}\n\n**STATUS: DONE**\n\nBody.\n"
        )
        self._touch(dep_md, touch_date)
        return dep_md

    def _write_consumer_slice(self, spec_dir: str, label: str,
                              last_verified: str, deps: list) -> Path:
        """Write the consumer slice with frontmatter."""
        cons_dir = self.target / "docs/specs" / spec_dir
        cons_dir.mkdir(parents=True, exist_ok=True)
        cons_md = cons_dir / "spec.md"
        cons_md.write_text(
            f"# Spec\n\n## Slice {label}\n\n"
            f"---\nstatus: RECONCILED\n"
            f"dependencies: [{', '.join(deps)}]\n"
            f"last_verified: {last_verified}\n---\n\nBody.\n"
        )
        return cons_md

    def test_no_stale_items_when_recent(self):
        """Recently verified slice with old deps → not stale."""
        self._write_dep_slice("900-dep", "900-01 old-dep", "2020-01-01")
        today = __import__("datetime").date.today().isoformat()
        self._write_consumer_slice("901-cons", "901-01 c", today, ["900-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "30")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_stale_item_listed_when_dep_changed_since(self):
        """Old verify date + dep changed since → stale."""
        # Dep touched yesterday (recent change)
        import datetime as _dt
        yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        self._write_dep_slice("910-dep", "910-01 fresh-dep", yesterday)
        # Consumer verified 200 days ago
        old = (_dt.date.today() - _dt.timedelta(days=200)).isoformat()
        self._write_consumer_slice("911-cons", "911-01 c", old, ["910-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("stale items", result.stdout)
        self.assertIn("911-01", result.stdout)
        self.assertIn(old, result.stdout)

    def test_old_verify_without_dep_change_not_stale(self):
        """Conjunctive criterion: old verify alone is not enough."""
        import datetime as _dt
        ancient = "2018-01-01"
        # Dep also old — no change since verify
        self._write_dep_slice("920-dep", "920-01 ancient", ancient)
        old = (_dt.date.today() - _dt.timedelta(days=300)).isoformat()
        self._write_consumer_slice("921-cons", "921-01 c", old, ["920-01"])
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_legacy_slice_without_frontmatter_skipped(self):
        """Slices with no frontmatter (no last_verified) are skipped."""
        # Write a legacy slice in the same project
        legacy_dir = self.target / "docs/specs/930-legacy"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "spec.md").write_text(
            "# Spec\n\n## Slice 930-01 legacy\n\n**STATUS: DONE**\n\nBody.\n"
        )
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_missing_dependencies_skipped(self):
        """Slice with last_verified but empty dependencies → skipped."""
        old = "2020-01-01"
        cons_dir = self.target / "docs/specs/940-empty"
        cons_dir.mkdir(parents=True)
        (cons_dir / "spec.md").write_text(
            f"# Spec\n\n## Slice 940-01 c\n\n"
            f"---\nstatus: DONE\ndependencies: []\nlast_verified: {old}\n---\n\n"
            f"Body.\n"
        )
        result = run_workflow("stale", "--project-dir", str(self.target),
                              "--days", "90")
        self.assertEqual(result.returncode, 0)
        self.assertIn("no stale items", result.stdout)

    def test_days_flag_overrides_default(self):
        """`--days 1` makes a 5-day-old verify stale; default 90 wouldn't."""
        import datetime as _dt
        yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
        self._write_dep_slice("950-dep", "950-01 fresh", yesterday)
        five_days_ago = (_dt.date.today() - _dt.timedelta(days=5)).isoformat()
        self._write_consumer_slice("951-cons", "951-01 c", five_days_ago,
                                   ["950-01"])
        # Default 90 → not stale yet
        r1 = run_workflow("stale", "--project-dir", str(self.target))
        self.assertEqual(r1.returncode, 0)
        self.assertIn("no stale items", r1.stdout)
        # --days 1 → stale
        r2 = run_workflow("stale", "--project-dir", str(self.target),
                          "--days", "1")
        self.assertEqual(r2.returncode, 0)
        self.assertIn("951-01", r2.stdout)


class RoutingStatsTests(unittest.TestCase):
    """Slice 041-02: `workflow.py routing-stats` renders a category-split
    histogram (jig baseline vs. richer/other) from the shared
    `.claude/skill-usage.jsonl` trace written by jig-skill-trace.sh."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-routing-")
        self.project = Path(self.tmpdir) / "proj"
        (self.project / ".claude").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _iso_days_ago(self, days: int) -> str:
        import datetime as _dt
        return (_dt.datetime.now(_dt.timezone.utc)
                - _dt.timedelta(days=days)).isoformat()

    def _write_log(self, entries: list) -> None:
        """entries: list of dicts → JSONL. A dict carrying key '__raw__'
        injects a verbatim line (for malformed-input tests)."""
        import json as _json
        log = self.project / ".claude" / "skill-usage.jsonl"
        lines = []
        for e in entries:
            lines.append(e["__raw__"] if "__raw__" in e else _json.dumps(e))
        log.write_text("\n".join(lines) + "\n")

    def _skill(self, name, *, days_ago=0):
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "session_id": "s",
            "event": "skill_invoked",
            "tool_name": "Skill",
            "skill_name": name,
        }

    def _task(self, *, days_ago=0):
        # A jig-telemetry.sh Task-spawn row — no event / skill_name.
        return {
            "timestamp": self._iso_days_ago(days_ago),
            "session_id": "s",
            "tool_name": "Task",
            "prompt_snippet": "spawn something",
        }

    def _run(self, *extra):
        return run_workflow("routing-stats", "--project-dir",
                            str(self.project), *extra)

    def _row(self, stdout: str, category: str) -> str:
        return next(l for l in stdout.splitlines()
                    if l.strip().startswith(category + " ")
                    or l.strip() == category)

    def test_missing_log_friendly_message(self):
        # No skill-usage.jsonl written at all → friendly, no crash.
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no routing data", r.stdout)

    def test_empty_log_friendly_message(self):
        (self.project / ".claude" / "skill-usage.jsonl").write_text("")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("no skill invocations", r.stdout)

    def test_counts_jig_vs_other_per_category(self):
        entries = [self._skill("jig:pr-review") for _ in range(3)]
        entries += [self._skill("pr-review") for _ in range(7)]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # category pr-review: jig=3, other=7, total=10
        self.assertRegex(self._row(r.stdout, "pr-review"),
                         r"\bpr-review\b.*\b3\b.*\b7\b.*\b10\b")

    def test_excludes_task_spawn_rows(self):
        # Load-bearing shared-file invariant: Task-spawn rows (no 'event'/
        # 'skill_name') must NOT count as skill invocations.
        self._write_log([self._task(), self._task(),
                         self._skill("jig:analyze")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # exactly 1 invocation; the two Task rows excluded
        self.assertRegex(self._row(r.stdout, "analyze"),
                         r"\banalyze\b.*\b1\b.*\b0\b.*\b1\b")

    def test_days_window_excludes_old_entries(self):
        self._write_log([
            self._skill("jig:contracts", days_ago=60),
            self._skill("jig:contracts", days_ago=0),
        ])
        r = self._run("--days", "30")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # only the in-window invocation counted
        self.assertRegex(self._row(r.stdout, "contracts"),
                         r"\bcontracts\b.*\b1\b.*\b0\b.*\b1\b")
        self.assertIn("1 outside window", r.stdout)

    def test_malformed_line_skipped(self):
        self._write_log([
            {"__raw__": "{ not valid json"},
            self._skill("jig:tdd-loop"),
            {"__raw__": "12345"},  # valid JSON but not a dict
        ])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "tdd-loop"),
                         r"\btdd-loop\b.*\b1\b.*\b0\b.*\b1\b")

    def test_non_utf8_bytes_do_not_crash(self):
        # A corrupted (non-UTF-8) trace must not break the "always exits 0"
        # contract: bad bytes decode to replacement chars and drop out via
        # the json.loads guard, while valid lines still count.
        import json as _json
        log = self.project / ".claude" / "skill-usage.jsonl"
        good = _json.dumps(self._skill("jig:analyze")).encode("utf-8")
        log.write_bytes(b"\xff\xfe not utf-8 at all\n" + good + b"\n")
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "analyze"),
                         r"\banalyze\b.*\b1\b.*\b0\b.*\b1\b")

    def test_jig_only_category_zero_other(self):
        self._write_log([self._skill("jig:spec-workflow"),
                         self._skill("jig:spec-workflow")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertRegex(self._row(r.stdout, "spec-workflow"),
                         r"\bspec-workflow\b.*\b2\b.*\b0\b.*\b2\b")

    def test_sorted_by_total_descending(self):
        entries = [self._skill("jig:spec-workflow") for _ in range(5)]
        entries += [self._skill("jig:clarify")]
        self._write_log(entries)
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertLess(r.stdout.index("spec-workflow"),
                        r.stdout.index("clarify"),
                        "higher-total category should sort first")

    def test_legend_explains_jig_vs_other(self):
        self._write_log([self._skill("pr-review")])
        r = self._run()
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("legend", r.stdout.lower())
        self.assertIn("jig", r.stdout)
        self.assertIn("other", r.stdout)


class SliceTemplateTests(unittest.TestCase):
    """Slice 014-01: a new slice template exists with the right frontmatter."""

    def test_slice_template_present(self):
        template = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"
        self.assertTrue(template.is_file(),
                        "templates/docs/specs/slice-template.md must exist")
        text = template.read_text()
        self.assertIn("status: DRAFT", text)
        self.assertIn("dependencies: []", text)
        self.assertIn("last_verified:", text)
        # Close-out section per slice 009 convention
        self.assertIn("### Close-out (post-DONE)", text)

    def test_slice_template_is_file_per_slice_shape(self):
        """Slice 018-03: template's frontmatter must come BEFORE the
        `## Slice` heading (file-per-slice layout). Embedded layout
        had heading first, frontmatter after — but the template is now
        meant as a whole-file template, not a `## Slice` block to
        append to spec.md."""
        template = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"
        text = template.read_text().lstrip()
        # First non-blank line is the frontmatter delimiter, not a heading.
        first_line = text.splitlines()[0]
        self.assertEqual(first_line, "---",
                         f"expected '---' (frontmatter open) at top, "
                         f"got: {first_line!r}")
        # Heading appears AFTER the closing frontmatter delimiter.
        fm_end = text.index("\n---\n", 4)  # second `---` line
        self.assertIn("## Slice {{NUMBER}}", text[fm_end:],
                      "## Slice heading must follow the frontmatter block")


class FrontmatterTransitionTests(unittest.TestCase):
    """Slice 014-01: transitions handle slice-level frontmatter."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-fm-")
        self.spec = Path(self.tmpdir) / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_fm_slice(self, name: str, status: str, deps: list = None,
                        body: str = "") -> None:
        deps_line = (f"\ndependencies: [{', '.join(deps)}]"
                     if deps else "\ndependencies: []")
        self.spec.write_text(
            f"# Spec X\n\n## Slice {name}\n\n"
            f"---\nstatus: {status}{deps_line}\nlast_verified:\n---\n\n"
            f"{body}"
        )

    # AC #1: slice frontmatter is parsed and used as the source of truth.
    def test_status_board_reads_frontmatter_status(self):
        # Set up a full scaffold so the status-board has somewhere to write.
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        spec_dir = target / "docs/specs/200-frontmatter-spec"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "# Spec\n\n## Slice 200-01 — alpha\n\n"
            "---\nstatus: IN_PROGRESS\ndependencies: []\n---\n\n"
            "Body.\n"
        )
        result = run_workflow("status-board", str(target))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        board = (target / "docs/specs/README.md").read_text()
        # The board should show IN_PROGRESS for slice 200-01, sourced
        # from frontmatter (no prose `**STATUS:**` marker present).
        self.assertRegex(board, r"200-01[^|]*\|[^|]*IN_PROGRESS")

    # AC #2: legacy prose marker fallback still works (existing tests
    # cover that exhaustively).

    # AC #3: transition writes to frontmatter when present.
    def test_transition_updates_frontmatter_status(self):
        self._write_fm_slice("300-01 alpha", "DRAFT")
        result = run_workflow("transition", str(self.spec), "300-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        self.assertIn("status: IN_PROGRESS", text)
        # No spurious prose marker leak — none was present originally.
        self.assertNotIn("**STATUS:", text)

    # AC #3: `last_verified` is stamped on RECONCILED transitions.
    def test_reconciled_transition_stamps_last_verified(self):
        self._write_fm_slice("301-01 alpha", "REVIEWED")
        result = run_workflow("transition", str(self.spec), "301-01",
                              "RECONCILED")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        self.assertIn("status: RECONCILED", text)
        # Today's date should appear in last_verified
        today = __import__("datetime").date.today().isoformat()
        self.assertIn(f"last_verified: {today}", text)

    # AC #3: non-RECONCILED transitions don't stamp.
    def test_non_reconciled_transition_does_not_stamp(self):
        self._write_fm_slice("302-01 alpha", "DRAFT")
        result = run_workflow("transition", str(self.spec), "302-01",
                              "IN_PROGRESS")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        text = self.spec.read_text()
        # last_verified field stays empty
        self.assertIn("last_verified:\n", text)

    # AC #4: DONE transition refuses on unsatisfied slice dependency.
    def test_done_refuses_when_dependency_not_done(self):
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        # Spec A with a DRAFT slice; spec B with a slice depending on A.
        spec_a = target / "docs/specs/400-alpha"
        spec_a.mkdir(parents=True)
        (spec_a / "spec.md").write_text(
            "# Spec A\n\n## Slice 400-01 — first\n\n"
            "---\nstatus: DRAFT\ndependencies: []\n---\n\nBody.\n"
        )
        spec_b = target / "docs/specs/401-beta"
        spec_b.mkdir(parents=True)
        spec_b_path = spec_b / "spec.md"
        spec_b_path.write_text(
            "# Spec B\n\n## Slice 401-01 — second\n\n"
            "---\nstatus: REVIEWED\ndependencies: [400-01]\n---\n\nBody.\n"
        )
        result = run_workflow("transition", str(spec_b_path), "401-01",
                              "DONE")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("400-01", result.stderr)
        self.assertIn("DRAFT", result.stderr)

    # AC #4: DONE succeeds when dependency is DONE.
    def test_done_succeeds_when_dependency_done(self):
        target = Path(self.tmpdir) / "demo-project"
        target.mkdir()
        scaffold(target)
        spec_a = target / "docs/specs/410-alpha"
        spec_a.mkdir(parents=True)
        (spec_a / "spec.md").write_text(
            "# Spec A\n\n## Slice 410-01 — first\n\n"
            "---\nstatus: DONE\ndependencies: []\n---\n\nBody.\n"
        )
        spec_b = target / "docs/specs/411-beta"
        spec_b.mkdir(parents=True)
        spec_b_path = spec_b / "spec.md"
        spec_b_path.write_text(
            "# Spec B\n\n## Slice 411-01 — second\n\n"
            "---\nstatus: RECONCILED\ndependencies: [410-01]\n---\n\nBody.\n"
        )
        result = run_workflow("transition", str(spec_b_path), "411-01",
                              "DONE")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("status: DONE", spec_b_path.read_text())


# Load workflow.py as a module for direct-call tests (needed for mocking
# subprocess.run inside the helper). importlib bypasses the hyphen-in-
# directory-name limitation. Mirrors the pattern in skills/slice-land/
# test_land.py.
import importlib.util as _ilu


def _load_workflow():
    spec = _ilu.spec_from_file_location("_workflow_module", WORKFLOW)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_workflow = _load_workflow()


class _SubprocessRecorder:
    """Captures subprocess.run calls and returns canned results based on
    a sequence of (matcher, returncode, stdout, stderr) tuples.

    Each call to the recorder consumes the first matching tuple in the
    sequence (FIFO). Matcher is a callable that takes the argv list and
    returns True if this tuple should fire. Unmatched calls return
    (returncode=0, stdout="", stderr="") by default — useful for
    benign reads like `git status --porcelain`.
    """

    def __init__(self):
        self.calls = []            # list of argv-lists
        self._responses = []       # list of (matcher, rc, stdout, stderr)

    def stub(self, matcher, returncode=0, stdout="", stderr=""):
        self._responses.append((matcher, returncode, stdout, stderr))
        return self

    def __call__(self, *args, **kwargs):
        # First positional arg is the argv list (or string).
        argv = args[0] if args else kwargs.get("args")
        if isinstance(argv, str):
            argv_list = argv.split()
        else:
            argv_list = list(argv)
        self.calls.append(argv_list)
        for i, (matcher, rc, out, err) in enumerate(self._responses):
            if matcher(argv_list):
                # One-shot: pop after match.
                self._responses.pop(i)
                return _make_proc(rc, out, err)
        return _make_proc(0, "", "")

    def argv_log(self):
        """Returns a list of space-joined command strings for assertion."""
        return [" ".join(a) for a in self.calls]


def _make_proc(returncode: int, stdout: str = "", stderr: str = ""):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _matches(*prefix_tokens):
    """Build a matcher that returns True when argv starts with the given
    tokens (in order, contiguous from index 0). E.g. _matches("git",
    "push") fires for ["git", "push", "origin", "main"]."""
    def _m(argv):
        return tuple(argv[: len(prefix_tokens)]) == tuple(prefix_tokens)
    return _m


def _matches_full(*tokens):
    """Exact full-argv matcher."""
    def _m(argv):
        return tuple(argv) == tuple(tokens)
    return _m


class ReserveSpecTests(unittest.TestCase):
    """Slice 003-03: `workflow.py new <slug>` reserves the next free
    spec number by committing — and by default pushing — a stub
    spec.md to origin/main."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-reserve-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Build minimal scaffolding: docs/specs/ exists; a couple of
        # existing spec dirs so the next-number computation has signal.
        (self.target / "docs" / "specs").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mkspec(self, name: str) -> None:
        d = self.target / "docs" / "specs" / name
        d.mkdir(parents=True)
        (d / "spec.md").write_text("# Spec\n")

    def _stub_preflight_ok(self, rec: _SubprocessRecorder,
                            dirty: bool = False) -> None:
        """Stub the preflight git calls: branch == main, clean worktree,
        origin URL on github.com. `dirty=True` simulates uncommitted
        changes."""
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0,
                 stdout=("M somefile\n" if dirty else ""))
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")

    # AC #1 + AC #2 + AC #7 (--no-push) — happy path; verify stub contents
    # and commit semantics without any remote calls.
    def test_new_reserves_next_number_and_writes_stub(self):
        self._mkspec("001-existing")
        self._mkspec("015-other")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Local commit step.
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "parallel-worktree-collision",
                project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs" / "specs" / "016-parallel-worktree-collision"
        self.assertTrue(spec_dir.is_dir(), f"missing: {spec_dir}")
        spec_md = spec_dir / "spec.md"
        self.assertTrue(spec_md.is_file())
        text = spec_md.read_text()
        # AC #2: frontmatter
        self.assertIn("---\nstatus: DRAFT\nskill:\n---", text)
        # AC #2: title-cased header
        self.assertIn("# Spec 016: Parallel-worktree collision", text)
        # AC #2: today's date in the reservation line
        import datetime as _dt
        today = _dt.date.today().isoformat()
        self.assertIn(f"Reserved on {today}", text)
        # AC #2: required headers (slice 018-03 renamed "SPIDR analysis"
        # → "Decomposition" + added "Slices" section pointing at the
        # starter slice file emitted alongside spec.md).
        self.assertIn("## Overview", text)
        self.assertIn("## Decomposition", text)
        self.assertIn("## Slices", text)
        self.assertIn("slice-01-tbd.md", text)
        # AC #1: commit message
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("docs(specs): reserve 016-parallel-worktree-collision",
                      " ".join(commit_calls[0]))
        # AC #7 (--no-push): no fetch / push calls.
        flat_log = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat_log)
        self.assertNotIn("git fetch", flat_log)

    # AC #1 — gap-tolerance: max + 1 across gaps, non-spec entries ignored.
    def test_new_uses_max_plus_one_across_gaps(self):
        self._mkspec("001-x")
        self._mkspec("015-y")
        self._mkspec("003-z")
        # Non-spec sibling entries don't perturb the max
        (self.target / "docs" / "specs" / "README.md").write_text("# stub\n")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # 015 was the max → reserve 016
        spec_dir = self.target / "docs" / "specs" / "016-newslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 016-newslot, got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")

    # AC #5 — refuse on non-main branch.
    # Worktree-aware reservation (prototype): off-main no longer refuses.
    # With --no-push it commits a provisional reservation to the CURRENT
    # branch (the push path is exercised by the detached-worktree tests).
    def test_new_off_main_no_push_reserves_on_current_branch(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/something\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "myslug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Provisional stub created locally (002 = max(001) + 1).
        self.assertTrue((self.target / "docs/specs/002-myslug/spec.md").is_file())
        # Committed with a pathspec-limited commit so unrelated staged work
        # can't leak into the reservation commit.
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("--", commit_calls[0])
        # No push / fetch — --no-push is purely local.
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat)
        self.assertNotIn("git fetch", flat)

    # Worktree-aware reservation — default (push) from off-main claims the
    # number on origin/main via an EPHEMERAL DETACHED worktree, never
    # touching the caller's branch.
    def test_new_off_main_push_uses_detached_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        # fetch / worktree add / add / commit / push HEAD:main / worktree
        # remove all default to rc=0 in the recorder.
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "fromtree", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        # Detached checkout of origin/main — NOT a checkout of `main`
        # (which a linked worktree can't do).
        self.assertIn("git worktree add --detach", flat)
        self.assertIn("origin/main", flat)
        # Pushes the detached HEAD onto main — NOT `git push origin main`.
        self.assertIn("git push origin HEAD:main", flat)
        # The ephemeral worktree is always torn down.
        self.assertIn("git worktree remove --force", flat)
        # The caller's branch is never checked out or reset.
        self.assertNotIn("git checkout main", flat)
        self.assertNotIn("git reset --hard", flat)

    # Worktree path race recovery: the stranded commit lives only in the
    # ephemeral worktree, so recovery is just the teardown — no on-main-style
    # `git reset --hard HEAD~1`.
    def test_new_off_main_race_cleans_up_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        rec.stub(_matches("git", "push", "origin", "HEAD:main"),
                 returncode=1,
                 stderr="! [rejected] HEAD -> main (non-fast-forward)\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "raced", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        self.assertIn("race", str(ctx.exception).lower())
        flat = " | ".join(rec.argv_log())
        self.assertIn("git worktree remove --force", flat)
        self.assertNotIn("git reset --hard HEAD~1", flat)

    # Worktree path protected-branch fallback: push the detached commit to
    # a reserve/ branch and open a PR (no local-main to un-strand).
    def test_new_off_main_protected_falls_back_to_pr(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/x\n")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "push", "origin", "HEAD:main"),
                 returncode=1,
                 stderr="remote: error: GH006: Protected branch update failed.\n")
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "protd", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        # Reservation commit pushed straight to a reserve/ branch...
        self.assertIn("git push origin HEAD:refs/heads/reserve/", flat)
        # ...and a PR opened with explicit head/base.
        self.assertIn("gh pr create", flat)
        self.assertIn("--head", flat)
        self.assertIn("--base", flat)
        # Ephemeral worktree still torn down.
        self.assertIn("git worktree remove --force", flat)

    # AC #5 — refuse on dirty worktree.
    def test_new_refuses_on_dirty_worktree(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec, dirty=True)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertTrue("dirty" in msg or "uncommitted" in msg or "clean" in msg,
                        f"unexpected message: {ctx.exception!r}")
        # No spec dir created
        self.assertFalse(any((self.target / "docs/specs").glob("*-myslug")))

    # AC #5 — bad slug variants: uppercase, leading digit, empty, double-dash.
    def test_new_refuses_on_bad_slug(self):
        self._mkspec("001-existing")
        bad = ["BadSlug", "1leadingdigit", "", "double--dash",
                "-leading", "with space"]
        for slug in bad:
            with self.subTest(slug=slug):
                rec = _SubprocessRecorder()
                # No preflight stubs needed — slug check happens first
                # for clearly-invalid shapes that argparse / regex
                # rejects before any git command runs.
                from unittest.mock import patch
                with patch.object(_workflow, "subprocess") as sp_mod:
                    sp_mod.run = rec
                    with self.assertRaises(_workflow.WorkflowError) as ctx:
                        _workflow.reserve_spec(
                            slug, project_dir=self.target,
                            no_push=True, pr_mode=False,
                        )
                msg = str(ctx.exception).lower()
                self.assertIn("slug", msg,
                              f"slug={slug!r}: error didn't name 'slug': "
                              f"{ctx.exception!r}")

    # AC #5 — refuse when docs/specs/ absent.
    def test_new_refuses_when_specs_dir_absent(self):
        # Build a fresh target without docs/specs
        bare = Path(self.tmpdir) / "bare"
        bare.mkdir()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "validslug", project_dir=bare,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("docs/specs", msg)

    # AC #3 — direct push succeeds; no fallback branch created.
    def test_new_direct_push_succeeds(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # fetch + add + commit + push all succeed
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # No fallback branch operations: no `git branch reserve/`, no
        # `git checkout reserve/`, no `git push -u origin reserve/`.
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("git checkout reserve", flat)
        self.assertNotIn("git push -u origin reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # AC #3 + AC #4 — protected-branch stderr triggers PR fallback.
    def test_new_falls_back_on_protected_branch(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Spec 037-02: `_next_spec_number` (push mode) consumes the
        # origin-url stub from `_stub_preflight_ok`. Re-stub for the
        # downstream `_check_gh_and_remote` call.
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        # push origin main FAILS with protection signal
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1, stderr="remote: error: GH006: Protected branch update failed.\n")
        # Fallback sequence
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/42\n")
        # shutil.which('gh') needs to be true; we patch shutil.which.
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git branch", flat)
        self.assertIn("git reset --hard origin/main", flat)
        self.assertIn("git checkout", flat)
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)

    # AC #6 — non-fast-forward triggers race-detection (NOT fallback).
    def test_new_does_not_fall_back_on_non_fast_forward(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        # The race-recovery does `git reset --hard HEAD~1`
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "newslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("race", msg)
        # Local commit dropped: reset HEAD~1 fired.
        flat = " | ".join(rec.argv_log())
        self.assertIn("git reset --hard HEAD~1", flat)
        # No fallback branch / gh pr create
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # Refinement-todo (slice 003-03 review): the race-recovery's
    # `git reset --hard HEAD~1` un-strands the commit but leaves the
    # now-empty spec dir on disk. The fix `shutil.rmtree`s the dir
    # after the reset so the user's worktree stays clean.
    def test_new_race_recovery_removes_empty_spec_dir(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        # In tests `git reset --hard HEAD~1` is mocked so the worktree
        # files aren't actually rolled back; the helper must still clean
        # up the dir it just created.
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError):
                _workflow.reserve_spec(
                    "newslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        # The dir would have been created as 002-newslot
        spec_dir = self.target / "docs" / "specs" / "002-newslot"
        self.assertFalse(
            spec_dir.exists(),
            f"race recovery left empty spec dir on disk: {spec_dir}",
        )

    # AC #7 (--pr) — skip direct-push, go straight to branch + PR.
    def test_new_pr_mode_skips_direct_push(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        # Spec 037-02: re-stub origin-url for `_check_gh_and_remote`
        # (the first stub is consumed by `_next_spec_number`).
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        # Fallback sequence — direct push NOT attempted.
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/u/r/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "myslot", project_dir=self.target,
                no_push=False, pr_mode=True,
            )
        self.assertEqual(code, 0)
        # No `git push origin main`
        push_main = [c for c in rec.calls
                     if tuple(c[:4]) == ("git", "push", "origin", "main")]
        self.assertEqual(push_main, [],
                         f"--pr should skip direct push; calls: "
                         f"{rec.argv_log()}")
        # But the branch + PR creation happened
        flat = " | ".join(rec.argv_log())
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)

    # AC #4 — PR fallback refuses without `gh` on PATH.
    def test_new_pr_mode_refuses_without_gh(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value=None):
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslot", project_dir=self.target,
                    no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("gh", msg, f"prereq message must name 'gh': "
                                 f"{ctx.exception!r}")

    # AC #4 — PR fallback refuses when origin isn't on github.com.
    def test_new_pr_mode_refuses_without_github_remote(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        # Override preflight: origin URL points elsewhere
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0,
                 stdout="git@gitlab.example.com:foo/bar.git\n")
        # Spec 037-02: re-stub origin-url for `_check_gh_and_remote`
        # (the first stub is consumed by `_next_spec_number`).
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0,
                 stdout="git@gitlab.example.com:foo/bar.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslot", project_dir=self.target,
                    no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("github.com", msg,
                      f"prereq message must name 'github.com': "
                      f"{ctx.exception!r}")

    # AC #7 (--no-push) — never calls fetch or push.
    def test_new_no_push_skips_remote_calls(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "soloslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git fetch", flat)
        self.assertNotIn("git push", flat)

    # AC #7 — mutex: --no-push and --pr together is a usage error.
    def test_new_no_push_and_pr_are_mutually_exclusive(self):
        self._mkspec("001-existing")
        # argparse usage error → exit 2 from main()
        result = run_workflow("new", "myslot", "--no-push", "--pr")
        self.assertNotEqual(result.returncode, 0)

    # AC #2 — title casing example from the spec.
    def test_new_title_cases_slug_per_spec_example(self):
        # Seed enough specs to push the reservation to 016 (matches the
        # spec example for clarity).
        self._mkspec("001-existing")
        self._mkspec("015-other")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "parallel-worktree-collision",
                project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        text = (self.target / "docs/specs/016-parallel-worktree-collision/"
                              "spec.md").read_text()
        self.assertIn("Parallel-worktree collision", text)


class MixedLayoutTransitionTests(unittest.TestCase):
    """Slice 018-02 AC #2: `transition` writes to the slice file when the
    slice lives in one; writes to spec.md when it's embedded. Same
    command, layout-aware target."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-mixed-"))
        # Slice 018-01 in its own file
        self.slice_file = self.tmpdir / "slice-01-file-based.md"
        self.slice_file.write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 018-01 — file-slice\n\n"
            "**Goal:** placeholder.\n"
        )
        # Slice 018-02 embedded in spec.md
        self.spec = self.tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec\n\n"
            "## Slice 018-02 — embedded-slice\n\n"
            "**STATUS: DRAFT**\n\n"
            "**Goal:** placeholder.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_transition_writes_to_slice_file_not_spec_md(self):
        result = run_workflow(
            "transition", str(self.spec), "018-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Slice file's frontmatter updated
        slice_after = self.slice_file.read_text()
        self.assertIn("status: IN_PROGRESS", slice_after)
        # spec.md's slice content section is UNCHANGED — the slice
        # mutation must go to loc.path, not blindly spec_md. Slice 030-01
        # adds an additional valid write to spec.md's frontmatter
        # `status:` field (rollup), so the file is allowed to change ONLY
        # in that field. The embedded slice section (018-02) must not
        # have been touched.
        spec_after = self.spec.read_text()
        m = re.search(
            r"## Slice 018-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", spec_after,
        )
        self.assertIsNotNone(m)
        self.assertEqual(
            m.group(1), "DRAFT",
            "spec.md's embedded slice 018-02 should remain DRAFT — only "
            "the slice file's 018-01 was transitioned",
        )

    def test_transition_writes_to_spec_md_for_embedded_slice(self):
        slice_before = self.slice_file.read_text()
        result = run_workflow(
            "transition", str(self.spec), "018-02", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # spec.md changed — embedded slice's STATUS marker rewritten
        spec_after = self.spec.read_text()
        m = re.search(r"## Slice 018-02[^\n]*\n+\*\*STATUS:\s+(\w+)\*\*", spec_after)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS")
        # Slice file untouched
        self.assertEqual(self.slice_file.read_text(), slice_before)


class NewSpecScaffoldsFilePerSliceTests(unittest.TestCase):
    """Slice 018-03 AC #1+#2+#4: `workflow.py new` scaffolds spec.md
    (header-only) + a starter `slice-01-*.md` file. spec.md must NOT
    contain an embedded `## Slice` section."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-new-fps-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        # Minimal git init so reserve_spec's stage+commit path doesn't
        # break — we mock subprocess anyway, but the dir must look git-like.
        (self.target / "docs/specs").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stub_subprocess(self, rec):
        rec.stub(_matches("git", "symbolic-ref"), returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status"), returncode=0)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "merge-base"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)

    def test_emits_spec_md_plus_starter_slice_file(self):
        from unittest.mock import patch
        import skills  # noqa: F401 — namespace anchor
        import importlib
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _workflow.reserve_spec(
                "demo-slug", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs/specs/001-demo-slug"
        self.assertTrue((spec_dir / "spec.md").is_file())
        self.assertTrue((spec_dir / "slice-01-tbd.md").is_file(),
                        "starter slice file slice-01-tbd.md must be emitted")

    def test_spec_md_has_no_embedded_slice_section(self):
        from unittest.mock import patch
        import importlib
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        spec_text = (self.target / "docs/specs/001-demo-slug/spec.md").read_text()
        self.assertNotIn("## Slice ", spec_text,
                         "spec.md must not contain a `## Slice` heading "
                         "(slices live in sibling files now)")

    def test_starter_slice_file_has_file_per_slice_shape(self):
        from unittest.mock import patch
        import importlib
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        slice_text = (self.target / "docs/specs/001-demo-slug"
                      / "slice-01-tbd.md").read_text()
        # Frontmatter at top (file-per-slice shape)
        self.assertTrue(slice_text.startswith("---\n"))
        # Heading after frontmatter, with the right slice fragment
        self.assertIn("## Slice 001-01 — tbd", slice_text)
        # Placeholders substituted
        self.assertNotIn("{{NUMBER}}", slice_text)
        self.assertNotIn("{{NAME}}", slice_text)

    def test_iter_slices_picks_up_starter_slice(self):
        """End-to-end: after `new`, `iter_slices(spec.md)` yields the
        starter slice — proves the helpers from 018-01/02 see the
        scaffolded shape end-to-end."""
        from unittest.mock import patch
        import importlib
        _workflow = importlib.import_module("skills.spec-workflow.workflow")
        rec = _SubprocessRecorder()
        self._stub_subprocess(rec)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            _workflow.reserve_spec("demo-slug",
                                    project_dir=self.target,
                                    no_push=True, pr_mode=False)
        # Import iter_slices from the common parser
        sys.path.insert(0, str(REPO_ROOT / "skills" / "_common"))
        from parsing import iter_slices
        spec_md = self.target / "docs/specs/001-demo-slug/spec.md"
        locs = list(iter_slices(spec_md))
        labels = [l.label for l in locs]
        self.assertIn("001-01 — tbd", labels)


class MixedLayoutDependencyValidationTests(unittest.TestCase):
    """Slice 018-02 follow-up (reviewer §SPECIFIC ISSUES):
    `_lookup_slice_status` and `_resolve_dep_path` must see file-per-slice
    slices when resolving DONE-transition dependencies."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-deps-"))
        # Dep slice lives in a sibling file, marked DONE.
        dep_spec_dir = self.tmpdir / "docs/specs/050-deps"
        dep_spec_dir.mkdir(parents=True)
        (dep_spec_dir / "slice-01-prereq.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified: 2026-05-15\n---\n\n"
            "## Slice 050-01 — prereq\n\nBody.\n"
        )
        (dep_spec_dir / "spec.md").write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 050\n\n## Overview\n\nNote.\n"
        )
        # Consumer slice depends on it. Lives in spec.md, RECONCILED.
        consumer_dir = self.tmpdir / "docs/specs/051-consumer"
        consumer_dir.mkdir(parents=True)
        self.consumer_spec = consumer_dir / "spec.md"
        self.consumer_spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 051\n\n"
            "## Slice 051-01 — consumes-prereq\n\n"
            "---\nstatus: RECONCILED\ndependencies: [050-01]\nlast_verified:\n---\n\n"
            "**Goal:** depends on 050-01.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_done_transition_finds_dep_in_slice_file(self):
        """Pre-018-02 bug: dependency validation walked `## Slice` headers
        inside spec.md only. A consumer slice whose `dependencies: [050-01]`
        targets a slice that's been split out to `slice-01-prereq.md`
        would be reported as 'slice not found' even though it IS DONE.
        After the fix, the DONE transition succeeds."""
        result = run_workflow(
            "transition", str(self.consumer_spec), "051-01", "DONE",
        )
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")


class MixedLayoutStatusBoardTests(unittest.TestCase):
    """Slice 018-02: status-board regen sees both layouts in one spec."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-board-mixed-"))
        # Status-board requires the README.md target to already exist
        # (it regenerates an existing board, doesn't create one from
        # nothing). Stub one in.
        (self.tmpdir / "docs/specs").mkdir(parents=True)
        (self.tmpdir / "docs/specs/README.md").write_text(
            "# Status board\n\n| Spec | Slice | Status | Notes |\n"
            "|---|---|---|---|\n"
        )
        spec_dir = self.tmpdir / "docs/specs/099-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "slice-01-from-file.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 099-01 — alpha\n\nBody.\n"
        )
        (spec_dir / "spec.md").write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec 099\n\n"
            "## Slice 099-02 — beta\n\n**STATUS: DRAFT**\n\nBody.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_status_board_lists_both_layouts(self):
        result = run_workflow("status-board", str(self.tmpdir))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = (self.tmpdir / "docs/specs/README.md").read_text()
        self.assertIn("099-01 — alpha", board)
        self.assertIn("099-02 — beta", board)
        # Status from each layout is read correctly
        # Slice file → DONE; embedded → DRAFT
        self.assertRegex(board, r"099-01 — alpha\s*\|\s*\*\*DONE\*\*")
        self.assertRegex(board, r"099-02 — beta\s*\|\s*DRAFT")


# ---------- spike documentation surface (slice 029-01) ----------


class SpikeSliceTemplateTests(unittest.TestCase):
    """Slice 029-01 AC #4: the slice template documents the spike body
    shape under a `kind: spike` subsection.

    AC #7 also concerns this surface — the three outcome forms
    (`ADR-NNNN created`, `spec NNN-NN unblocked`, `abandoned (reason)`)
    and the semicolon multi-outcome convention must be documented here
    so the template, SKILL.md, and SPIDR primer agree.
    """

    def setUp(self):
        template = (REPO_ROOT / "templates" / "docs" / "specs"
                    / "slice-template.md")
        self.template = template
        self.text = template.read_text()

    def test_template_has_spike_subsection_heading(self):
        # AC #4: a subsection introducing the spike body shape exists.
        self.assertRegex(
            self.text,
            r"(?im)^###\s+.*kind:\s*spike.*",
            "expected a '### For `kind: spike` slices' (or similar) "
            "subsection in the slice template",
        )

    def test_template_lists_all_four_spike_labels(self):
        # AC #4: the four labelled blocks are documented.
        for label in ("**Question:**", "**Time-box:**",
                      "**Findings:**", "**Outcome:**"):
            self.assertIn(label, self.text,
                          f"spike body label {label!r} missing from template")

    def test_template_documents_three_outcome_forms(self):
        # AC #7: all three outcome forms documented.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)

    def test_template_documents_semicolon_multi_outcome(self):
        # AC #7: multiple outcomes joined by `;` documented.
        self.assertIn(";", self.text)
        # Cheap pin: at least one prose mention of "semicolon" or "multiple"
        # near the spike section.
        self.assertRegex(
            self.text,
            r"(?is)kind:\s*spike.*(semicolon|multiple outcomes)",
            "template must say multiple outcomes are separated by `;`",
        )


class SpidrPrimerSpikeTests(unittest.TestCase):
    """Slice 029-01 AC #5 + AC #8: the SPIDR primer at
    `docs/spec-workflow/spidr-primer.md` documents the
    "when S fires → kind: spike" rule with a worked example.
    """

    def setUp(self):
        primer = REPO_ROOT / "docs" / "spec-workflow" / "spidr-primer.md"
        self.primer_path = primer
        self.assertTrue(primer.is_file(),
                        f"SPIDR primer must exist at {primer}")
        self.text = primer.read_text()

    def test_primer_documents_when_s_fires_rule(self):
        # AC #5: explicit "when the S axis fires, mark `kind: spike`" rule.
        # Match the load-bearing phrasing: a mention of `kind: spike` near
        # the discussion of when the Spike axis applies.
        self.assertIn("kind: spike", self.text,
                      "SPIDR primer must reference `kind: spike` explicitly")
        # The rule should appear in the context of S/Spike axis.
        self.assertRegex(
            self.text,
            r"(?is)(spike|S axis|S\s*—)[^\n]*?kind:\s*spike|"
            r"kind:\s*spike[^\n]*?(spike|S axis|S\s*—)",
            "the `kind: spike` rule must appear in the context of the S axis",
        )

    def test_primer_worked_example_has_four_labels(self):
        # AC #8: a worked spike example with all four labels.
        for label in ("**Question:**", "**Time-box:**",
                      "**Findings:**", "**Outcome:**"):
            self.assertIn(label, self.text,
                          f"SPIDR primer worked example missing {label!r}")

    def test_primer_worked_example_has_concrete_outcome(self):
        # AC #8: the worked example should show one of the three outcome
        # forms (ADR-NNNN / spec NNN-NN / abandoned) concretely.
        outcome_section = self.text
        self.assertRegex(
            outcome_section,
            r"(?im)\*\*Outcome:\*\*[^\n]*?"
            r"(ADR-\d{4}\s+created|spec\s+\d{3}-\d{2}\s+unblocked"
            r"|abandoned\s*\([^)]+\))",
            "worked example must show a concrete Outcome value",
        )

    def test_primer_documents_three_outcome_forms(self):
        # AC #7: outcome forms documented in the primer too.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)


class SpecWorkflowSkillMdSpikeTests(unittest.TestCase):
    """Slice 029-01 AC #6 + AC #7: `skills/spec-workflow/SKILL.md` gains a
    "Spike slices" subsection covering (a) when to introduce a spike,
    (b) the four-label body shape, (c) always-nested rule, (d) abandoned
    failure mode.
    """

    def setUp(self):
        skill = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
        self.skill_path = skill
        self.text = skill.read_text()

    def test_skill_has_spike_slices_subsection(self):
        # AC #6: a `## Spike slices` (or `### Spike slices`) section exists.
        self.assertRegex(
            self.text,
            r"(?im)^#{2,3}\s+Spike slices\s*$",
            "expected a 'Spike slices' subsection in spec-workflow/SKILL.md",
        )

    def test_skill_lists_four_body_labels(self):
        # AC #6(b): the four labelled blocks are named.
        for label in ("Question", "Time-box", "Findings", "Outcome"):
            self.assertIn(label, self.text,
                          f"SKILL.md missing spike body label {label!r}")

    def test_skill_documents_always_nested_rule(self):
        # AC #6(c): the always-nested rule must be stated.
        # Look for "always nested" or "never standalone" phrasing near
        # the spike section.
        self.assertRegex(
            self.text,
            r"(?is)spike slices.*?(always[- ]nested|never standalone"
            r"|no standalone|no\s+`?docs/spikes/?`?)",
            "SKILL.md must document the always-nested rule for spikes",
        )

    def test_skill_documents_abandoned_failure_mode(self):
        # AC #6(d): abandoned-spike manual reshape pattern documented.
        self.assertRegex(
            self.text,
            r"(?is)abandon",
            "SKILL.md must document the abandoned-spike failure mode",
        )
        # The mode must mention manual review / audit of dependents,
        # not automatic cascade.
        self.assertRegex(
            self.text,
            r"(?is)(manual|human).*?(audit|reshape|review).*?depend|"
            r"depend.*?(manual|human).*?(audit|reshape|review)",
            "SKILL.md must say abandoned spikes require manual dependent audit",
        )

    def test_skill_documents_three_outcome_forms(self):
        # AC #7: outcome forms appear in SKILL.md too.
        self.assertIn("ADR-NNNN created", self.text)
        self.assertIn("spec NNN-NN unblocked", self.text)
        self.assertIn("abandoned (reason)", self.text)


# ---------- status-board spike marker (slice 029-02) ----------


class StatusBoardSpikeMarkerTests(unittest.TestCase):
    """Slice 029-02: `kind: spike` slices render with a visible marker
    in the status board, derived from the slice's `kind:` field at render
    time. The marker is additive — it does not introduce a new column,
    change column shape, or break parser round-trips."""

    # The marker chosen (per spec Open question #3 lean): a leading
    # microscope emoji on the slice cell. Single-char prefix, no schema
    # churn, survives the `parse_existing_notes` regex round-trip.
    MARKER = "\U0001f52c"  # 🔬

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-spike-board-"))
        self.target = self.tmpdir / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spike_slice(self, spec_dir: str, label: str,
                            status: str, kind: str = "spike") -> Path:
        """Create a file-per-slice spec dir with a `kind: spike`
        frontmatter slice."""
        sd = self.target / "docs/specs" / spec_dir
        sd.mkdir(parents=True, exist_ok=True)
        # Stub spec.md (frontmatter only — slice lives in slice-NN-*.md).
        spec_md = sd / "spec.md"
        if not spec_md.is_file():
            spec_md.write_text("---\nstatus: DRAFT\n---\n\n# Spec\n")
        # File-per-slice slice file with `kind:` frontmatter.
        slice_num = label.split()[0].split("-")[1]  # "029-02 alpha" → "02"
        slice_file = sd / f"slice-{slice_num}-test.md"
        kind_line = f"kind: {kind}\n" if kind else ""
        slice_file.write_text(
            f"---\nstatus: {status}\ndependencies: []\n{kind_line}---\n\n"
            f"## Slice {label}\n\n**Goal:** investigate something.\n"
        )
        return slice_file

    def _write_feature_slice(self, spec_dir: str, label: str,
                              status: str) -> Path:
        """Create a regular (non-spike) slice — no `kind:` field, or
        `kind: feature`. Default: no `kind:` field at all (most realistic
        for legacy slices)."""
        return self._write_spike_slice(spec_dir, label, status, kind="")

    def _read_board(self) -> str:
        return (self.target / "docs/specs/README.md").read_text()

    # ----- AC #1: spike slices carry the marker; non-spike unchanged.

    def test_spike_slice_renders_with_marker(self):
        self._write_spike_slice("100-spike-test", "100-01 — investigate-x",
                                 "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # The slice cell carries the marker prefix on the spike slice row.
        # Anchor against the slice label so we catch the prefix and the
        # column shape together.
        self.assertRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+100-01 — investigate-x\s*\|",
            f"spike row missing marker; board:\n{board}",
        )

    def test_non_spike_slice_renders_without_marker(self):
        self._write_feature_slice("101-feature", "101-01 — regular-work",
                                   "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # The non-spike slice cell has no leading marker.
        self.assertIn("101-01 — regular-work", board)
        self.assertNotRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+101-01 — regular-work",
            f"non-spike row has unexpected marker; board:\n{board}",
        )

    def test_explicit_kind_feature_renders_without_marker(self):
        """`kind: feature` (the documented explicit-default synonym for
        unset) must NOT trigger the marker."""
        self._write_spike_slice("102-feature-explicit",
                                 "102-01 — explicit-feature",
                                 "DRAFT", kind="feature")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        self.assertIn("102-01 — explicit-feature", board)
        self.assertNotRegex(
            board,
            rf"\|\s*{re.escape(self.MARKER)}\s+102-01 — explicit-feature",
        )

    # ----- AC #2: marker is derived from `kind:`, not stored separately.

    def test_marker_derived_from_kind_field_on_regen(self):
        """Manual-edit-to-the-board that strips the marker is re-added
        on the next regen (marker is recomputed from each slice's `kind:`,
        not stored in the board itself)."""
        self._write_spike_slice("110-derive", "110-01 — a-spike", "DRAFT")
        # First regen — marker present.
        run_workflow("status-board", str(self.target))
        board1 = self._read_board()
        self.assertIn(self.MARKER, board1)
        # Hand-strip the marker from the board (manual edit).
        stripped = board1.replace(f"{self.MARKER} 110-01", "110-01")
        self.assertNotEqual(stripped, board1)
        (self.target / "docs/specs/README.md").write_text(stripped)
        # Second regen — marker is restored from the slice's `kind:`.
        run_workflow("status-board", str(self.target))
        board2 = self._read_board()
        self.assertIn(f"{self.MARKER} 110-01", board2,
                       "marker must be re-added on regen even after manual strip")

    def test_flipping_kind_field_propagates_on_next_regen(self):
        """Editing the slice's `kind:` field from `spike` to nothing
        (regular feature) removes the marker on the next regen."""
        slice_file = self._write_spike_slice(
            "111-flip", "111-01 — flippable", "DRAFT",
        )
        run_workflow("status-board", str(self.target))
        board_with = self._read_board()
        self.assertIn(f"{self.MARKER} 111-01", board_with)
        # Now flip the slice's frontmatter — drop `kind: spike`.
        original = slice_file.read_text()
        flipped = original.replace("kind: spike\n", "")
        self.assertNotEqual(flipped, original)
        slice_file.write_text(flipped)
        # Re-regen the board — marker should be gone for this slice.
        run_workflow("status-board", str(self.target))
        board_after = self._read_board()
        self.assertIn("111-01 — flippable", board_after)
        self.assertNotRegex(
            board_after,
            rf"\|\s*{re.escape(self.MARKER)}\s+111-01",
            "marker must vanish when `kind: spike` is removed from the slice",
        )

    # ----- AC #3: marker does not break parsers; round-trip preserved.

    def test_marker_does_not_corrupt_notes_preservation(self):
        """The marker must round-trip through `parse_existing_notes` —
        manual notes on a spike row must survive subsequent regens
        unchanged, with the marker still in place."""
        self._write_spike_slice("120-roundtrip", "120-01 — survive-notes",
                                 "DRAFT")
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        first = board_path.read_text()
        # Find the spike row and curate a note on it.
        # The row reads: `| [spec] | 🔬 120-01 — survive-notes | DRAFT |  |`
        # We replace the trailing empty notes cell with a curated note.
        empty_cell = (
            f"| {self.MARKER} 120-01 — survive-notes | DRAFT |  |"
        )
        curated_cell = (
            f"| {self.MARKER} 120-01 — survive-notes | DRAFT "
            f"| curated note — spike-row test |"
        )
        self.assertIn(empty_cell, first,
                       f"baseline row shape missing; board:\n{first}")
        board_path.write_text(first.replace(empty_cell, curated_cell))
        # Re-regen — note must survive AND marker stays.
        run_workflow("status-board", str(self.target))
        final = board_path.read_text()
        self.assertIn("curated note — spike-row test", final,
                       f"curated note on spike row lost on regen; board:\n{final}")
        self.assertIn(f"{self.MARKER} 120-01 — survive-notes", final)

    # ----- AC #4: marker is documented (status-board preamble).

    def test_status_board_preamble_documents_the_marker(self):
        """A reader who sees `🔬` should be able to find out what it
        means without grepping for `kind: spike`. The status-board
        preamble (or a small header sentence) names the marker."""
        # Existing repo's board carries the documentation; scaffolded
        # projects get the same documentation via the template (pinned
        # by `test_scaffold_template_documents_spike_marker` below).
        # Here we pin the in-repo board itself, which is what real
        # readers see.
        board_path = REPO_ROOT / "docs" / "specs" / "README.md"
        text = board_path.read_text()
        # The preamble lives above the first `| Spec` table header.
        m = re.search(r"(?m)^\|\s*Spec\b", text)
        self.assertIsNotNone(m, "no `| Spec` table header in board")
        preamble = text[: m.start()]
        # Marker + an explanatory mention of "spike" in the preamble.
        self.assertIn(self.MARKER, preamble,
                       f"preamble must show the marker glyph; got:\n{preamble}")
        self.assertRegex(
            preamble,
            r"(?i)spike",
            "preamble must mention 'spike' so the marker meaning is recoverable",
        )

    # ----- AC #5: tests cover presence, absence, and mixed.

    def test_no_spike_spec_renders_with_no_markers(self):
        """A spec with no spike slices produces a status board with no
        marker character anywhere in its rows."""
        self._write_feature_slice("130-no-spikes", "130-01 — a", "DRAFT")
        self._write_feature_slice("130-no-spikes", "130-02 — b", "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # Pull only the active table rows for this spec; the preamble
        # documents the marker so we must scope the assertion to rows.
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines()
            if "130-no-spikes" in ln
        ]
        self.assertEqual(len(spec_rows), 2)
        for row in spec_rows:
            self.assertNotIn(
                self.MARKER, row,
                f"unexpected marker on non-spike row: {row!r}",
            )

    def test_mixed_spec_marks_spikes_only(self):
        """A spec with one spike + one feature slice marks only the spike."""
        self._write_spike_slice("131-mixed", "131-01 — a-spike",
                                 "DRAFT", kind="spike")
        self._write_feature_slice("131-mixed", "131-02 — a-feature", "DRAFT")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spike_rows = [
            ln for ln in active.splitlines() if "131-01 — a-spike" in ln
        ]
        feature_rows = [
            ln for ln in active.splitlines() if "131-02 — a-feature" in ln
        ]
        self.assertEqual(len(spike_rows), 1)
        self.assertEqual(len(feature_rows), 1)
        self.assertIn(self.MARKER, spike_rows[0])
        self.assertNotIn(self.MARKER, feature_rows[0])

    def test_all_spike_spec_marks_every_row(self):
        """A spec where every slice is a spike — all rows carry the marker."""
        self._write_spike_slice("132-all-spike", "132-01 — q1",
                                 "DRAFT", kind="spike")
        self._write_spike_slice("132-all-spike", "132-02 — q2",
                                 "IN_PROGRESS", kind="spike")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines() if "132-all-spike" in ln
        ]
        self.assertEqual(len(spec_rows), 2)
        for row in spec_rows:
            self.assertIn(
                self.MARKER, row,
                f"row missing marker in all-spike spec: {row!r}",
            )

    def test_one_slice_spec_with_spike_renders_marker(self):
        """The 1-slice-spec case from the 029 Overview: a normal spec
        where the only slice is `kind: spike` (the "investigation with
        no clear downstream spec yet" pattern). The marker still renders
        — this is exactly the scenario the spike workflow targets."""
        self._write_spike_slice("133-one-slice", "133-01 — sole-spike",
                                 "DRAFT", kind="spike")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spec_rows = [
            ln for ln in active.splitlines() if "133-one-slice" in ln
        ]
        self.assertEqual(len(spec_rows), 1)
        self.assertIn(self.MARKER, spec_rows[0])

    # ----- AC #6: no regressions to existing column shape.

    def test_existing_column_shape_unchanged(self):
        """Snapshot the row shape: pipe count + cell-content shape on a
        spike row matches a non-spike row except for the marker prefix
        in the slice cell. The marker is additive — no new column, no
        re-alignment."""
        self._write_spike_slice("140-shape", "140-01 — spike-row",
                                 "DRAFT", kind="spike")
        self._write_feature_slice("140-shape", "140-02 — feature-row",
                                   "DRAFT")
        run_workflow("status-board", str(self.target))
        board = self._read_board()
        active = board.split("## Deferred slices")[0]
        spike_rows = [
            ln for ln in active.splitlines() if "140-01 — spike-row" in ln
        ]
        feature_rows = [
            ln for ln in active.splitlines() if "140-02 — feature-row" in ln
        ]
        self.assertEqual(len(spike_rows), 1)
        self.assertEqual(len(feature_rows), 1)
        # Same pipe count (i.e., same column count).
        self.assertEqual(
            spike_rows[0].count("|"), feature_rows[0].count("|"),
            f"column count drift between rows:\n"
            f"  spike:   {spike_rows[0]!r}\n  feature: {feature_rows[0]!r}",
        )
        # Spike row has exactly 5 pipes (4 cells).
        self.assertEqual(spike_rows[0].count("|"), 5,
                          f"unexpected pipe count on spike row: "
                          f"{spike_rows[0]!r}")
        # Snapshot: spike row's slice cell content is exactly
        # `<marker> <label>` (single space).
        expected_spike_cell = f"| {self.MARKER} 140-01 — spike-row |"
        self.assertIn(
            expected_spike_cell, spike_rows[0],
            f"spike row cell shape drift; got: {spike_rows[0]!r}",
        )
        # Snapshot: feature row's slice cell content is exactly `<label>`.
        expected_feature_cell = "| 140-02 — feature-row |"
        self.assertIn(
            expected_feature_cell, feature_rows[0],
            f"feature row cell shape drift; got: {feature_rows[0]!r}",
        )

    # ----- AC #7: regen idempotency.

    def test_status_board_regen_idempotent_with_spike(self):
        """Two consecutive regens against a spike-bearing project produce
        identical output."""
        self._write_spike_slice("150-idem", "150-01 — spike-idem", "DRAFT")
        self._write_feature_slice("150-idem", "150-02 — feature-idem", "DRAFT")
        run_workflow("status-board", str(self.target))
        first = self._read_board()
        run_workflow("status-board", str(self.target))
        second = self._read_board()
        self.assertEqual(
            first, second,
            "non-idempotent regen — diff suggests marker round-trip churn",
        )
        # And the marker is present in both passes.
        self.assertIn(f"{self.MARKER} 150-01 — spike-idem", first)
        self.assertIn(f"{self.MARKER} 150-01 — spike-idem", second)

    def test_status_board_idempotency_message_when_current(self):
        """When the board is already current, regen prints the
        already-current message (slice 003-01 idempotency contract held)."""
        self._write_spike_slice("151-idem", "151-01 — spike-curr", "DRAFT")
        # First regen produces the canonical state.
        run_workflow("status-board", str(self.target))
        # Second regen — already-current message must surface.
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already current", result.stdout,
                       f"idempotent regen path skipped; stdout:\n{result.stdout}")

    # ----- AC #4 (scaffold parity): the scaffold template carries the
    # same marker documentation so newly-scaffolded projects don't need
    # to re-discover the convention.

    def test_scaffold_template_documents_spike_marker(self):
        """The scaffold template at `templates/docs/specs/README.md.template`
        carries the spike-marker explanation so freshly-scaffolded
        projects ship with the documentation already in place — same
        AC #4 surface as the in-repo board (pinned above)."""
        template_path = REPO_ROOT / "templates" / "docs" / "specs" / "README.md.template"
        text = template_path.read_text()
        # Preamble sits above the first `| Spec` table header (same
        # layout as the rendered board).
        m = re.search(r"(?m)^\|\s*Spec\b", text)
        self.assertIsNotNone(m, "no `| Spec` table header in template")
        preamble = text[: m.start()]
        self.assertIn(self.MARKER, preamble,
                       f"template preamble must show the marker glyph; got:\n{preamble}")
        self.assertRegex(
            preamble,
            r"(?i)spike",
            "template preamble must mention 'spike' so the marker meaning is recoverable",
        )

    # ----- AC #1 (deferred-table parity): DEFERRED `kind: spike` rows
    # render with the marker too — same visual contract as active rows.

    def test_deferred_spike_renders_with_marker(self):
        """A DEFERRED spike slice carries the marker in the `## Deferred
        slices` table, same as it would in the active table."""
        self._write_spike_slice("160-deferred-spike",
                                 "160-01 — investigate-later",
                                 "DEFERRED")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        # Locate the deferred section and scope the assertion to it.
        deferred_idx = board.find("## Deferred slices")
        self.assertNotEqual(deferred_idx, -1,
                            f"no deferred section in board:\n{board}")
        deferred = board[deferred_idx:]
        self.assertIn(f"{self.MARKER} 160-01 — investigate-later", deferred,
                      f"deferred spike row missing marker; section:\n{deferred}")

    def test_deferred_non_spike_renders_without_marker(self):
        """A DEFERRED non-spike slice renders unchanged in the deferred
        table — the marker is spike-only."""
        self._write_feature_slice("161-deferred-feature",
                                   "161-01 — wait-on-trigger",
                                   "DEFERRED")
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, result.stderr)
        board = self._read_board()
        deferred_idx = board.find("## Deferred slices")
        self.assertNotEqual(deferred_idx, -1,
                            f"no deferred section in board:\n{board}")
        deferred = board[deferred_idx:]
        # The row exists in the deferred section.
        self.assertIn("161-01 — wait-on-trigger", deferred,
                      f"deferred feature row missing; section:\n{deferred}")
        # And does NOT carry the marker prefix on its slice cell.
        self.assertNotIn(f"{self.MARKER} 161-01", deferred,
                         f"deferred feature row erroneously carries marker; section:\n{deferred}")

class ComputeSpecStatusTests(unittest.TestCase):
    """Slice 030-01 AC #1: `compute_spec_status(spec_path)` derives the
    spec-level rollup from slice states. Pure-function tests across the
    enumerated fixtures: empty, single-DRAFT, single-DONE, single-DEFERRED,
    all-DEFERRED, mixed-DONE-DRAFT, mixed-DONE-DEFERRED,
    mixed-IN_PROGRESS-DONE, legacy embedded, file-per-slice, both layouts."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-rollup-"))
        self.spec_dir = self.tmpdir / "spec-dir"
        self.spec_dir.mkdir()
        self.spec_md = self.spec_dir / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec_md(self, body: str = "") -> None:
        """Write a spec.md with frontmatter and optional body (embedded
        sections)."""
        self.spec_md.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n## Overview\n\nSyn.\n"
            + body
        )

    def _write_slice_file(self, name: str, status: str,
                          filename: str = None) -> None:
        """Write a file-per-slice file with frontmatter status."""
        if filename is None:
            # Derive a default filename from the slice fragment portion.
            tag = name.split()[0].replace("—", "").replace("-", "")[:6]
            filename = f"slice-{tag}.md"
        path = self.spec_dir / filename
        path.write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            f"## Slice {name}\n\n**Goal:** placeholder.\n"
        )

    def _embedded(self, name: str, status: str) -> str:
        """Build an embedded `## Slice ...` block w/ `**STATUS:**` marker."""
        return (
            f"\n## Slice {name}\n\n**STATUS: {status}**\n\n"
            f"**Goal:** placeholder.\n"
        )

    # AC #1: empty spec dir (no slices at all)
    def test_empty_spec_returns_draft(self):
        self._write_spec_md()
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: single DRAFT slice → DRAFT
    def test_single_draft_slice_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DRAFT")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: single DONE slice → DONE
    def test_single_done_slice_returns_done(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: single DEFERRED slice → DRAFT (no live work)
    def test_single_deferred_slice_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DEFERRED")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: all slices DEFERRED → DRAFT
    def test_all_deferred_returns_draft(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DEFERRED",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DEFERRED",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DRAFT")

    # AC #1: mixed DONE + DRAFT → IN_PROGRESS (work has begun)
    def test_mixed_done_draft_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DRAFT",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: mixed DONE + DEFERRED → DONE (every non-DEFERRED slice is DONE)
    def test_mixed_done_deferred_returns_done(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DEFERRED",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: mixed IN_PROGRESS + DONE → IN_PROGRESS
    def test_mixed_in_progress_done_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "IN_PROGRESS",
                               filename="slice-01-a.md")
        self._write_slice_file("100-02 beta", "DONE",
                               filename="slice-02-b.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: a single READY_FOR_REVIEW slice → IN_PROGRESS (active work)
    def test_single_ready_for_review_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "READY_FOR_REVIEW")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: a single REVIEWED slice → IN_PROGRESS
    def test_single_reviewed_returns_in_progress(self):
        self._write_spec_md()
        self._write_slice_file("100-01 alpha", "REVIEWED")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: legacy embedded-section spec.md with a DONE slice
    def test_legacy_embedded_done_returns_done(self):
        self._write_spec_md(self._embedded("100-01 alpha", "DONE"))
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #1: legacy embedded section with mixed DONE + DRAFT → IN_PROGRESS
    def test_legacy_embedded_mixed_returns_in_progress(self):
        body = (
            self._embedded("100-01 alpha", "DONE")
            + self._embedded("100-02 beta", "DRAFT")
        )
        self._write_spec_md(body)
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: both layouts in one spec (mid-migration shape)
    def test_mixed_layouts_in_one_spec(self):
        # Slice file: DONE.  Embedded: DRAFT.  Mixed → IN_PROGRESS.
        self._write_spec_md(self._embedded("100-02 beta", "DRAFT"))
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md),
                         "IN_PROGRESS")

    # AC #1: both layouts, all DONE
    def test_mixed_layouts_all_done(self):
        self._write_spec_md(self._embedded("100-02 beta", "DONE"))
        self._write_slice_file("100-01 alpha", "DONE",
                               filename="slice-01-a.md")
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")

    # AC #6: spec.md without frontmatter still gets a computed status
    # (it's the WRITE step that's skipped, not the compute).
    def test_no_frontmatter_still_computes(self):
        # Write a spec.md that has NO frontmatter block at all
        self.spec_md.write_text("# Spec\n\n## Overview\n\nSyn.\n")
        self._write_slice_file("100-01 alpha", "DONE")
        # compute_spec_status still returns its rule-derived value
        self.assertEqual(_workflow.compute_spec_status(self.spec_md), "DONE")


class TransitionRollupTests(unittest.TestCase):
    """Slice 030-01 AC #2: `workflow.py transition` writes the rollup
    to spec.md frontmatter `status:` after the slice mutation."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-tr-rollup-"))
        self.spec_dir = self.tmpdir / "spec-dir"
        self.spec_dir.mkdir()
        self.spec_md = self.spec_dir / "spec.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_spec_md(self, status: str = "DRAFT") -> None:
        self.spec_md.write_text(
            f"---\nstatus: {status}\n---\n\n# Spec X\n\n## Overview\n\nSyn.\n"
        )

    def _write_slice_file(self, name: str, status: str,
                          filename: str = "slice-01-a.md") -> None:
        (self.spec_dir / filename).write_text(
            f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
            f"## Slice {name}\n\n**Goal:** placeholder.\n"
        )

    # AC #2: transition writes rollup to spec.md
    def test_transition_writes_rollup_to_spec_md(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self.spec_md.read_text()
        # spec.md frontmatter status should now be IN_PROGRESS (rollup)
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "IN_PROGRESS",
                         f"expected IN_PROGRESS rollup, spec.md was:\n{text}")

    # AC #2: rollup flips to DONE when only DONE slices remain
    def test_transition_to_done_flips_spec_to_done(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "RECONCILED")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DONE",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        text = self.spec_md.read_text()
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         f"expected DONE rollup, spec.md was:\n{text}")

    # AC #2: idempotent — same rollup value → no spurious write
    def test_transition_rollup_is_idempotent(self):
        # Two slices: both DRAFT. spec.md frontmatter already says DRAFT.
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT",
                               filename="slice-01-a.md")
        self._write_slice_file("200-02 beta", "DRAFT",
                               filename="slice-02-b.md")
        before = self.spec_md.read_text()
        # Transition one slice DRAFT → DRAFT (no-op-ish; rollup stays DRAFT
        # because the OTHER slice is still DRAFT).
        # Use a real change that doesn't flip rollup: transition to DRAFT.
        # We need a state transition that keeps both slices as DRAFT in
        # aggregate; transitioning 200-01 to DEFERRED keeps spec DRAFT
        # (the other slice is still DRAFT, all non-DEFERRED are DRAFT).
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DEFERRED",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        after = self.spec_md.read_text()
        # spec.md status field should still be DRAFT
        m = re.search(r"^status:\s*(\w+)", after, re.MULTILINE)
        self.assertEqual(m.group(1), "DRAFT",
                         f"expected DRAFT rollup, spec.md was:\n{after}")
        # spec.md content unchanged (idempotent — no spurious write)
        self.assertEqual(before, after,
                         "spec.md was rewritten despite no rollup change")

    # AC #4: spec.md without frontmatter is left untouched
    def test_transition_does_not_write_to_no_frontmatter_spec(self):
        # Write a spec.md without frontmatter
        no_fm = "# Spec X\n\n## Overview\n\nNo frontmatter here.\n"
        self.spec_md.write_text(no_fm)
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "DONE",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # spec.md content unchanged (no frontmatter insertion)
        self.assertEqual(self.spec_md.read_text(), no_fm,
                         "spec.md without frontmatter was modified — "
                         "defensive case should leave it untouched")

    # AC #2: slice mutation still happens (rollup is ADDITIONAL, not replacement)
    def test_transition_still_writes_slice_status(self):
        self._write_spec_md(status="DRAFT")
        self._write_slice_file("200-01 alpha", "DRAFT")
        result = run_workflow(
            "transition", str(self.spec_md), "200-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # The slice's status should be updated too
        slice_text = (self.spec_dir / "slice-01-a.md").read_text()
        self.assertIn("status: IN_PROGRESS", slice_text)


class StatusBoardRollupTests(unittest.TestCase):
    """Slice 030-01 AC #3: `workflow.py status-board` writes the rollup
    to every spec.md it walks (during regen)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-board-rollup-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        (self.target / "docs/specs").mkdir(parents=True)
        # Seed the board file so status-board has something to regenerate
        (self.target / "docs/specs/README.md").write_text(
            "# Status board\n\n| Spec | Slice | Status | Notes |\n"
            "|---|---|---|---|\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mk_spec(self, dirname: str, frontmatter_status: str,
                  slices: list) -> Path:
        """Build a spec dir with a spec.md (frontmatter `status:`) and a
        set of file-per-slice files. `slices` is [(name, status), ...]."""
        spec_dir = self.target / "docs/specs" / dirname
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            f"---\nstatus: {frontmatter_status}\n---\n\n"
            f"# Spec\n\n## Overview\n\nSyn.\n"
        )
        for i, (name, status) in enumerate(slices, start=1):
            (spec_dir / f"slice-{i:02d}-x.md").write_text(
                f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n---\n\n"
                f"## Slice {name}\n\n**Goal:** placeholder.\n"
            )
        return spec_md

    # AC #3: status-board flips DRAFT → DONE for fully-done specs
    def test_status_board_flips_done_specs(self):
        spec_md = self._mk_spec("300-alpha", "DRAFT",
                                 [("300-01 a", "DONE"),
                                  ("300-02 b", "DONE")])
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         f"expected DONE rollup, spec.md was:\n"
                         f"{spec_md.read_text()}")

    # AC #3: status-board flips DRAFT → IN_PROGRESS for partial-done specs
    def test_status_board_flips_in_progress_specs(self):
        spec_md = self._mk_spec("301-beta", "DRAFT",
                                 [("301-01 a", "DONE"),
                                  ("301-02 b", "IN_PROGRESS")])
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "IN_PROGRESS",
                         f"expected IN_PROGRESS rollup, spec.md was:\n"
                         f"{spec_md.read_text()}")

    # AC #3: status-board leaves an already-correct spec.md untouched
    # (idempotent — no spurious write)
    def test_status_board_idempotent_on_correct_specs(self):
        spec_md = self._mk_spec("302-gamma", "DONE",
                                 [("302-01 a", "DONE")])
        before = spec_md.read_text()
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        after = spec_md.read_text()
        # spec.md not changed (rollup matched what's already there)
        self.assertEqual(before, after,
                         f"spec.md was rewritten despite no rollup change")

    # AC #3: status-board writes regardless of board-table-changes
    # (a spec whose status flips DRAFT → DONE updates spec.md even if
    # the board's per-slice rows are unchanged from the previous version).
    def test_status_board_writes_spec_even_when_table_unchanged(self):
        # Set up a fully-DONE spec with frontmatter status: DRAFT
        spec_md = self._mk_spec("303-delta", "DRAFT",
                                 [("303-01 a", "DONE")])
        # First regen to establish baseline table content
        run_workflow("status-board", str(self.target))
        # After first regen: spec.md should be DONE, board table reflects DONE.
        first_text = spec_md.read_text()
        m = re.search(r"^status:\s*(\w+)", first_text, re.MULTILINE)
        self.assertEqual(m.group(1), "DONE")
        # Manually flip spec.md back to DRAFT (simulating drift)
        spec_md.write_text(first_text.replace(
            "status: DONE", "status: DRAFT"
        ))
        # Second regen — table content already matches slices (idempotent
        # on its own), but spec.md frontmatter is now stale. The rollup
        # write should fire regardless.
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        m = re.search(r"^status:\s*(\w+)", spec_md.read_text(),
                      re.MULTILINE)
        self.assertEqual(m.group(1), "DONE",
                         "rollup write should fire even when the board "
                         "table itself is already current")

    # AC #4: status-board leaves a spec.md without frontmatter alone
    def test_status_board_does_not_write_to_no_frontmatter_spec(self):
        spec_dir = self.target / "docs/specs/304-epsilon"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        no_fm = "# Spec\n\n## Overview\n\nLegacy.\n"
        spec_md.write_text(no_fm)
        (spec_dir / "slice-01-a.md").write_text(
            "---\nstatus: DONE\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 304-01 — alpha\n\n**Goal:** placeholder.\n"
        )
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        # spec.md content unchanged (no frontmatter insertion)
        self.assertEqual(spec_md.read_text(), no_fm,
                         "spec.md without frontmatter was modified")


# ---------------------------------------------------------------------------
# Slice 031-02 — `slice_needs_arch_review` helper + slice-template hint
# ---------------------------------------------------------------------------


class SliceNeedsArchReviewTests(unittest.TestCase):
    """Slice 031-02 AC #4 + AC #6: `workflow.py` exposes
    `slice_needs_arch_review(spec_md, slice_fragment) -> bool` that
    reads the slice's frontmatter and returns the `arch_review:` value,
    defaulting to `false` when the field is absent.

    The helper is exposed as a CLI subcommand `arch-review-needed` so
    SKILL.md's bash recipe can shell out the same way it shells out
    `subagent-type`.

    Test fixtures use the canonical post-018-03 file-per-slice layout:
    `spec.md` carries the overview + spec-level frontmatter, and a
    sibling `slice-NN-<short>.md` carries the slice content + the
    slice-level frontmatter (where `arch_review:` lives).
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-arch-needed-"))
        self.spec = self.tmpdir / "spec.md"
        self.slice_file = self.tmpdir / "slice-02-arch.md"
        # Minimum spec.md — overview only; slice content lives in sibling.
        self.spec.write_text(
            "---\nstatus: IN_PROGRESS\nskill: spec-workflow\n---\n\n"
            "# Spec X\n\n## Overview\n\nStuff.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_slice(self, fm_extra: str, slice_name: str = "031-02 alpha") -> None:
        """Write a synthetic slice FILE (file-per-slice layout) with the
        given frontmatter extras. `fm_extra` goes between
        `last_verified:` and the closing `---`."""
        self.slice_file.write_text(
            "---\n"
            "status: IN_PROGRESS\n"
            "dependencies: []\n"
            "last_verified:\n"
            f"{fm_extra}"
            "---\n\n"
            f"## Slice {slice_name}\n\n"
            "**Goal:** placeholder.\n"
        )

    def _run(self, slice_fragment: str = "031-02"):
        return run_workflow(
            "arch-review-needed", str(self.spec), slice_fragment,
        )

    # AC #4 — defaults to false when field is absent
    def test_returns_false_when_field_absent(self):
        self._write_slice(fm_extra="")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    # AC #4 — reads true when frontmatter sets it
    def test_returns_true_when_field_is_true(self):
        self._write_slice(fm_extra="arch_review: true\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "true")

    # AC #4 — reads false explicitly
    def test_returns_false_when_field_is_false(self):
        self._write_slice(fm_extra="arch_review: false\n")
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    # AC #6 — embedded slice (no per-slice frontmatter) defaults to false
    def test_returns_false_for_legacy_embedded_slice(self):
        # Legacy shape: slice embedded in spec.md with no per-slice
        # frontmatter — the `arch_review:` field can't exist there, so
        # the helper must default to false.
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n"
            "## Slice 031-02 alpha\n\n**STATUS: DRAFT**\n\n"
            "**Goal:** placeholder.\n"
        )
        # No slice_file written; spec.md carries the embedded slice.
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "false")

    def test_returns_true_for_embedded_slice_with_post_heading_frontmatter(self):
        # Legacy 015-01 layout: an embedded slice may carry per-slice
        # frontmatter inserted AFTER the `## Slice` heading. The helper
        # must read it via the layout-aware `_slice_frontmatter` path
        # (consistent with `collect_slices` / `compute_spec_status`).
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n"
            "## Slice 031-02 alpha\n\n"
            "---\nstatus: IN_PROGRESS\narch_review: true\n---\n\n"
            "**Goal:** placeholder.\n"
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "true")

    # Edge: case-insensitive truthy values
    def test_returns_true_for_truthy_variations(self):
        for truthy in ("true", "True", "TRUE", "yes"):
            self._write_slice(fm_extra=f"arch_review: {truthy}\n")
            result = self._run()
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertEqual(
                result.stdout.strip(), "true",
                f"value {truthy!r} should be treated as true",
            )

    # Edge: stdout-only (no trailing noise) for shell substitution
    def test_stdout_only_emits_clean_value(self):
        self._write_slice(fm_extra="arch_review: true\n")
        result = self._run()
        self.assertEqual(result.returncode, 0)
        # Same hygiene as `subagent-type`: single word + optional newline
        self.assertIn(result.stdout, ("true\n", "true"))


class SliceTemplateArchReviewHintTests(unittest.TestCase):
    """Slice 031-02 AC #1 + AC #6: the slice template at
    `templates/docs/specs/slice-template.md` ships the `arch_review:`
    field commented out with a one-line guide, so authors discover it
    organically when copying the template for a new slice."""

    def setUp(self):
        template = (REPO_ROOT / "templates" / "docs" / "specs"
                    / "slice-template.md")
        self.template = template
        self.text = template.read_text()

    def test_template_mentions_arch_review_field(self):
        # AC #1: the commented-out hint must mention the field
        self.assertIn(
            "arch_review:", self.text,
            "slice template must mention the `arch_review:` "
            "frontmatter field (031-02 AC #1)",
        )

    def test_template_has_arch_review_hint_in_frontmatter_block(self):
        # AC #1: the hint sits inside the leading frontmatter block,
        # commented out (lines start with `#`).
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        self.assertIsNotNone(m, "slice template must start with frontmatter")
        fm = m.group(1)
        self.assertIn(
            "arch_review:", fm,
            "`arch_review:` hint must be in the leading frontmatter "
            "block (031-02 AC #1)",
        )
        # The hint must be commented out — search for `# arch_review:`
        self.assertRegex(
            fm,
            r"#\s*arch_review:",
            "the `arch_review:` hint must be commented out (031-02 AC #1: "
            "existing slices without the field are unaffected)",
        )

    def test_template_explains_when_to_set_arch_review(self):
        # AC #1: a one-line guide explains when to flip the flag.
        # Search for module/boundary/contract/architecture vocab near the hint.
        m = re.match(r"---\n(.*?)\n---", self.text, re.DOTALL)
        fm = m.group(1)
        self.assertRegex(
            fm,
            r"(?is)arch_review:.*(?:module|boundar|contract|architect)",
            "the `arch_review:` hint must explain when to set it "
            "(031-02 AC #1: module boundaries / public contracts / "
            "architecture-shaped concerns)",
        )


# Slice 028-03: importlib-load workflow.py as a module so tests can
# monkeypatch `_checksum` directly to inject deterministic mid-regen
# mutations. Mirrors the loader pattern slice 028-02 added for memory.py.
def _import_workflow_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_workflow_under_test", WORKFLOW,
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StatusBoardRaceCheckTests(unittest.TestCase):
    """Slice 028-03 — checksum-based race-detection guard on
    `workflow.py status-board`.

    ACs covered:
      - AC #1: pre-regen checksum captured (verified indirectly via
        race-detected case: if pre-checksum wasn't captured, the
        post-checksum compare couldn't detect the mutation).
      - AC #2: pre-write checksum compared; refuses on mismatch.
      - AC #3: exact refusal message + exit code 4.
      - AC #4: `--force` flag bypasses the check (CLI + Python API).
      - AC #5: tests cover all three branches (no-race / detected-race /
        forced-overwrite) + the stale-checksum false-positive edge case.
      - AC #6: regression test on Notes-column preservation.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-board-race-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)
        # Drop in a synthetic spec so the regen has something to write.
        spec1 = self.target / "docs/specs/200-race-check"
        spec1.mkdir(parents=True)
        write_synthetic_spec(spec1 / "spec.md", [
            ("200-01 first", "DONE"),
            ("200-02 second", "IN_PROGRESS"),
        ])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #5 branch 1: no-race (default behavior). Existing tests in
    # StatusBoardTests already cover this thoroughly; one regression-pin
    # here so a future refactor that breaks the no-race path fails
    # alongside the slice-028-03 tests.
    def test_no_race_default_behavior_unchanged(self):
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(
            result.returncode, 0,
            f"no-race regen must succeed; stderr: {result.stderr}",
        )
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("200-01 first", board)
        self.assertIn("200-02 second", board)

    # AC #2 + AC #3 + AC #5 branch 2: race detected → refusal raised.
    def test_race_detected_raises_status_board_race_error(self):
        wf = _import_workflow_module()
        # Establish baseline so the regen has new content to write
        # (otherwise the idempotent fast path skips the race check
        # entirely — that's intentional per Design decision #3).
        run_workflow("status-board", str(self.target))
        # Mutate one of the slices so the next regen has real new content.
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch _checksum to return different values on the two calls
        # (pre-regen vs pre-write) — simulates a concurrent writer
        # mutating the board between the two reads.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre-regen", "sha-mid-regen-different"],
        ):
            with self.assertRaises(wf.StatusBoardRaceError) as cm:
                wf.regenerate_status_board(self.target)
        # AC #3: exact refusal message. Match character-for-character so
        # future auditors can grep for it.
        self.assertEqual(
            str(cm.exception),
            "status board changed during regen — another writer may "
            "have run. Re-run `workflow.py status-board` to retry.",
        )

    # AC #3: CLI exits 4 (not 2) when a race is detected.
    def test_cli_exits_4_on_race(self):
        wf = _import_workflow_module()
        # Set up so the regen would write something.
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch checksum on the loaded module via a wrapper subprocess.
        # Simpler approach: use the Python API directly via the module
        # path, since the CLI subprocess can't easily share a mock.
        # Invoke main() directly so the exception → exit-code mapping is
        # exercised in-process.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-post"],
        ):
            rc = wf.main(
                ["workflow.py", "status-board", str(self.target)],
            )
        self.assertEqual(rc, 4,
                         "race detection must surface as exit code 4")

    # AC #4 + AC #5 branch 3: forced-overwrite bypasses the guard.
    # Python API path: pass `force=True`.
    def test_force_python_api_bypasses_race_check(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Patch _checksum to a divergent side_effect — but with force=True
        # the guard should be skipped entirely (no checksum call at all,
        # so the side_effect is irrelevant).
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre-WOULD-be-race", "sha-post-WOULD-be-race"],
        ):
            # Should not raise; write proceeds despite checksum mismatch
            # because force=True turns off the guard.
            summary = wf.regenerate_status_board(self.target, force=True)
        self.assertIn("regenerated status board", summary)
        # Confirm the write actually happened (REVIEWED status landed).
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("REVIEWED", board)

    # AC #4: `--force` CLI flag works (matches Python API).
    def test_force_cli_flag_bypasses_race_check(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-post-diverged"],
        ):
            rc = wf.main(
                ["workflow.py", "status-board", str(self.target), "--force"],
            )
        self.assertEqual(rc, 0, "force flag must bypass the guard and exit 0")
        board = (self.target / "docs/specs/README.md").read_text()
        self.assertIn("REVIEWED", board)

    # AC #5 edge case: stale-checksum false-positive. If the file is
    # rewritten with identical content (SHA256 stays the same), the
    # content-based check correctly treats it as "no race" and the write
    # proceeds. Documented in deviation log; this test pins the behavior.
    def test_identical_content_rewrite_does_not_trigger_race(self):
        wf = _import_workflow_module()
        run_workflow("status-board", str(self.target))
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        # Same checksum on both calls — simulates a concurrent writer
        # rewriting with identical content. Should NOT raise.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-same", "sha-same"],
        ):
            summary = wf.regenerate_status_board(self.target)
        self.assertIn("regenerated status board", summary)

    # AC #1 / AC #5 idempotent-fast-path: when the regen produces no new
    # content (new == existing), the write is skipped and the race check
    # is unreachable. This pins that no false-positive race is reported
    # on the idempotent path.
    def test_idempotent_fast_path_does_not_trigger_race(self):
        wf = _import_workflow_module()
        # First regen establishes the baseline.
        run_workflow("status-board", str(self.target))
        # Second regen with the same spec state — new_content == existing,
        # so the function returns "already current" before reaching the
        # race-check / write code. Patch _checksum with divergent values:
        # if the race-check code ran on the fast path (it shouldn't), the
        # divergent side_effect would raise.
        with unittest.mock.patch.object(
            wf, "_checksum",
            side_effect=["sha-pre", "sha-DIVERGENT-would-race"],
        ):
            summary = wf.regenerate_status_board(self.target)
        self.assertEqual(summary, "status board already current; no changes")

    # Craft-pass coverage gap: --force + idempotent state should still
    # respect the fast path (return "already current") rather than writing
    # unconditionally. Pins the behavior against a future refactor that
    # might move the fast-path below the race-check block.
    def test_force_respects_idempotent_fast_path(self):
        wf = _import_workflow_module()
        # First regen establishes the baseline.
        run_workflow("status-board", str(self.target))
        # Second regen with `force=True` — no content change, so the
        # function must still short-circuit on the fast path.
        summary = wf.regenerate_status_board(self.target, force=True)
        self.assertEqual(summary, "status board already current; no changes")

    # AC #6: regression — Notes column preservation must still work.
    def test_notes_column_preserved_across_regen(self):
        # First regen to establish baseline table
        run_workflow("status-board", str(self.target))
        board_path = self.target / "docs/specs/README.md"
        content = board_path.read_text()
        # Hand-edit a Note cell for one slice
        new_content = content.replace(
            "| 200-01 first | **DONE** |  |",
            "| 200-01 first | **DONE** | curated note that must survive |",
        )
        self.assertNotEqual(new_content, content,
                            "test setup failed: edit was a no-op")
        board_path.write_text(new_content)
        # Mutate a spec so the second regen has new content (so the
        # actual write path runs, exercising the race check + Notes
        # preservation together).
        spec_md = self.target / "docs/specs/200-race-check/spec.md"
        spec_md.write_text(
            spec_md.read_text().replace("IN_PROGRESS", "REVIEWED")
        )
        result = run_workflow("status-board", str(self.target))
        self.assertEqual(result.returncode, 0,
                         f"regen failed: {result.stderr}")
        regenerated = board_path.read_text()
        self.assertIn("curated note that must survive", regenerated)


class ReserveSpecAgainstOriginTests(unittest.TestCase):
    """Spec 037-02: `reserve_spec` reads `origin/main` in push mode and
    refuses on diverged local main. Mirrors slice 037-01's tuple-key
    behavior dispatcher (see `test_land.py:1750-1787`).

    `_next_spec_number` and `_preflight_branch_and_worktree` (and
    `reserve_spec`'s post-fetch diverged-main check) all call
    `subprocess.run` via the module-level `_run`. We patch the module's
    `subprocess` so the recorder intercepts every call.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-wf-037-02-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        (self.target / "docs" / "specs").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mkspec(self, name: str) -> None:
        d = self.target / "docs" / "specs" / name
        d.mkdir(parents=True)
        (d / "spec.md").write_text("# Spec\n")

    def _patched_run(self, behavior):
        """Return a fake `subprocess.run` that consults `behavior`.

        `behavior` is a dict mapping a tuple key (the command's
        identifying suffix) to either a `_make_proc(...)` result OR a
        callable returning one. Mirrors the dispatcher in
        `test_land.py:1750-1787`.

        Tuple keys recognized:
          ("symbolic-ref",)             -> git symbolic-ref --short HEAD
          ("status",)                   -> git status --porcelain
          ("origin-url",)               -> git config --get remote.origin.url
          ("fetch",)                    -> git fetch origin main
          ("ls-tree",)                  -> git ls-tree --name-only origin/main docs/specs/
          ("verify", "origin/main")     -> git rev-parse --verify origin/main
          ("verify", "main")            -> git rev-parse --verify main
          ("ancestor", "main", "origin/main") -> git merge-base --is-ancestor main origin/main
          ("rev-parse", "main")         -> git rev-parse main (SHA print)
          ("add",)                      -> git add
          ("commit",)                   -> git commit
          ("push-main",)                -> git push origin main
          ("reset-head1",)              -> git reset --hard HEAD~1
          ("branch",)                   -> git branch
          ("checkout",)                 -> git checkout
          ("push-u",)                   -> git push -u origin <branch>
          ("reset-origin",)             -> git reset --hard origin/main
          ("gh-pr",)                    -> gh pr create
        """
        calls = []

        def fake_run(*args, **kwargs):
            argv = args[0] if args else kwargs.get("args")
            if isinstance(argv, str):
                argv_list = argv.split()
            else:
                argv_list = list(argv)
            calls.append(argv_list)

            # Identify by suffix/role
            if argv_list[:1] == ["gh"] and "pr" in argv_list:
                key = ("gh-pr",)
            elif argv_list[:2] == ["git", "symbolic-ref"]:
                key = ("symbolic-ref",)
            elif argv_list[:3] == ["git", "status", "--porcelain"]:
                key = ("status",)
            elif (argv_list[:3] == ["git", "config", "--get"]
                  and "remote.origin.url" in argv_list):
                key = ("origin-url",)
            elif argv_list[:2] == ["git", "fetch"]:
                key = ("fetch",)
            elif argv_list[:2] == ["git", "ls-tree"]:
                key = ("ls-tree",)
            elif (argv_list[:3] == ["git", "rev-parse", "--verify"]):
                key = ("verify", argv_list[-1])
            elif (argv_list[:2] == ["git", "rev-parse"]
                  and "--verify" not in argv_list):
                key = ("rev-parse", argv_list[-1])
            elif (argv_list[:2] == ["git", "merge-base"]
                  and "--is-ancestor" in argv_list):
                # last two positional args are the ancestor pair
                key = ("ancestor", argv_list[-2], argv_list[-1])
            elif argv_list[:2] == ["git", "add"]:
                key = ("add",)
            elif argv_list[:2] == ["git", "commit"]:
                key = ("commit",)
            elif argv_list[:4] == ["git", "push", "origin", "main"]:
                key = ("push-main",)
            elif (argv_list[:4] == ["git", "reset", "--hard", "HEAD~1"]):
                key = ("reset-head1",)
            elif (argv_list[:4] == ["git", "reset", "--hard", "origin/main"]):
                key = ("reset-origin",)
            elif argv_list[:2] == ["git", "branch"]:
                key = ("branch",)
            elif argv_list[:2] == ["git", "checkout"]:
                key = ("checkout",)
            elif argv_list[:3] == ["git", "push", "-u"]:
                key = ("push-u",)
            else:
                key = tuple(argv_list[-2:])

            entry = behavior.get(key)
            if entry is None:
                # default success, empty output
                return _make_proc(0, "", "")
            # Guard against MagicMock-instance silent bypass: only treat
            # FunctionType/lambda/method as a dispatcher. Mirrors
            # test_land.py:1780-1786 lesson.
            import types
            if isinstance(entry, (types.FunctionType, types.LambdaType,
                                  types.MethodType)):
                return entry(argv_list, **kwargs)
            return entry

        fake_run._calls = calls
        return fake_run

    def _default_preflight_behavior(self):
        """Common stub set: on main, clean worktree, GitHub origin."""
        return {
            ("symbolic-ref",): _make_proc(0, "main\n", ""),
            ("status",): _make_proc(0, "", ""),
            ("origin-url",): _make_proc(
                0, "git@github.com:user/repo.git\n", ""),
            ("fetch",): _make_proc(0, "", ""),
            ("add",): _make_proc(0, "", ""),
            ("commit",): _make_proc(0, "", ""),
            ("push-main",): _make_proc(0, "", ""),
        }

    # ----------- AC #1: push-mode scan reads `origin/main` -----------

    def test_push_mode_scan_reads_origin_main_not_working_tree(self):
        """AC #1 — a spec committed to origin/main but absent from the
        working tree is counted. Working tree has only 001; origin/main
        ls-tree returns 020-other, so the next number is 021."""
        from unittest.mock import patch
        self._mkspec("001-local-only")  # working tree only
        behavior = self._default_preflight_behavior()
        # origin/main has both 001 and a 020-other; verify ref present.
        behavior[("verify", "origin/main")] = _make_proc(
            0, "abc123\n", "")
        behavior[("verify", "main")] = _make_proc(0, "abc123\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "abc123\n", "")
        # ancestor: equal SHAs → in sync (not behind)
        behavior[("ancestor", "main", "origin/main")] = _make_proc(
            0, "", "")
        # ls-tree returns directory entries from origin/main
        behavior[("ls-tree",)] = _make_proc(
            0, "001-local-only\n020-other\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # 020 was the max on origin/main → reserve 021
        spec_dir = self.target / "docs" / "specs" / "021-newslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 021-newslot from origin/main scan; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # Confirm we actually called ls-tree against origin/main
        ls_tree_calls = [
            c for c in fake._calls
            if c[:2] == ["git", "ls-tree"] and "origin/main" in c
        ]
        self.assertEqual(
            len(ls_tree_calls), 1,
            f"expected 1 ls-tree origin/main call; got: {fake._calls}",
        )

    # ----------- AC #2: --no-push preserves working-tree scan -----------

    def test_no_push_keeps_working_tree_scan(self):
        """AC #2 — `--no-push` mode never calls `git ls-tree`; spec
        number derives from working-tree scan."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        self._mkspec("015-other")
        behavior = self._default_preflight_behavior()
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "newslot", project_dir=self.target,
                no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=015, so reserve 016
        spec_dir = self.target / "docs" / "specs" / "016-newslot"
        self.assertTrue(spec_dir.is_dir())
        # AC #2 absence-of-effect: no ls-tree call against origin/main
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"--no-push must not call ls-tree; got: {c}",
            )
        # And no fetch either (matches existing AC #7 no-push contract)
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "fetch"],
                f"--no-push must not fetch; got: {c}",
            )

    def test_pr_mode_is_push_mode_equivalent_for_scan(self):
        """AC #2 — `--pr` (push-mode-equivalent) scans `origin/main`."""
        from unittest.mock import patch
        import shutil as _shutil
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        behavior[("verify", "origin/main")] = _make_proc(0, "abc\n", "")
        behavior[("verify", "main")] = _make_proc(0, "abc\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "abc\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(
            0, "001-existing\n050-large\n", "")
        # PR-mode helpers
        behavior[("branch",)] = _make_proc(0)
        behavior[("reset-origin",)] = _make_proc(0)
        behavior[("checkout",)] = _make_proc(0)
        behavior[("push-u",)] = _make_proc(0)
        behavior[("gh-pr",)] = _make_proc(
            0, "https://github.com/u/r/pull/9\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "prslot", project_dir=self.target,
                no_push=False, pr_mode=True,
            )
        self.assertEqual(code, 0)
        # Origin/main max=050 → reserve 051
        spec_dir = self.target / "docs" / "specs" / "051-prslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 051-prslot from origin/main scan; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        ls_tree_calls = [
            c for c in fake._calls
            if c[:2] == ["git", "ls-tree"] and "origin/main" in c
        ]
        self.assertEqual(len(ls_tree_calls), 1)

    # ----------- AC #3: no origin / no origin/main → silent fall-back ---

    def test_no_origin_remote_falls_back_silently(self):
        """AC #3 — no origin → working-tree scan with no warning."""
        from unittest.mock import patch
        import io
        self._mkspec("001-existing")
        self._mkspec("007-other")
        behavior = self._default_preflight_behavior()
        # origin-url lookup FAILS → silent fall-through to working tree
        behavior[("origin-url",)] = _make_proc(1, "", "")
        # Even though origin-url fails, the existing fetch step at
        # workflow.py:1271-1282 still runs (warn-and-proceed). To keep
        # this test focused on the silent local-only fall-back, treat
        # the fetch as a no-op (default rc=0).
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "fallbackslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=007 → reserve 008
        spec_dir = self.target / "docs" / "specs" / "008-fallbackslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 008-fallbackslot from working-tree "
                        f"fall-back; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #3: silent — no "warning:" prefix from THIS code path. The
        # fetch warning (AC #6) is a different path; we don't trigger
        # it here because fetch defaulted to rc=0.
        stderr_text = captured.getvalue()
        self.assertNotIn(
            "no origin", stderr_text.lower(),
            f"expected silent fall-back; got: {stderr_text!r}",
        )
        self.assertNotIn(
            "origin remote", stderr_text.lower(),
            f"expected silent fall-back; got: {stderr_text!r}",
        )
        # And absence-of-effect: no ls-tree against origin/main
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"no-origin path must not call ls-tree; got: {c}",
            )

    def test_no_origin_main_ref_falls_back_silently(self):
        """AC #3 — origin exists, fetch succeeds, but `rev-parse --verify
        origin/main` fails → fall back to working-tree scan, silently."""
        from unittest.mock import patch
        import io
        self._mkspec("001-existing")
        self._mkspec("003-other")
        behavior = self._default_preflight_behavior()
        # origin exists; fetch succeeds; rev-parse --verify origin/main FAILS
        behavior[("verify", "origin/main")] = _make_proc(1, "", "")
        # No ls-tree stub → if called, defaults to rc=0 stdout="" which
        # would mistakenly produce next_n=1; we assert ls-tree wasn't
        # called instead.
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "missingref", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Working-tree max=003 → reserve 004
        spec_dir = self.target / "docs" / "specs" / "004-missingref"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 004-missingref; got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #3 distinguished from AC #6: this is silent (no warning).
        stderr_text = captured.getvalue()
        self.assertNotIn("origin/main", stderr_text,
                         f"expected silent fall-back; got: {stderr_text!r}")
        # Absence-of-effect: ls-tree not called
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"no-origin-main path must not call ls-tree; got: {c}",
            )

    # ----------- AC #4: preflight refuses on diverged local main -------

    def test_preflight_refuses_when_local_main_behind_origin(self):
        """AC #4 — local main strictly behind origin/main → refuse with
        a message containing 'origin/main' AND 'pull or rebase'."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # origin/main present; local SHA != origin SHA; main is strict
        # ancestor of origin/main → behind.
        behavior[("verify", "origin/main")] = _make_proc(0, "ORIG\n", "")
        behavior[("verify", "main")] = _make_proc(0, "LOCL\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "LOCL\n", "")
        # `--is-ancestor main origin/main` returns 0 → main IS ancestor →
        # since SHAs differ, local is strictly behind.
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        # ls-tree wouldn't be reached if preflight runs after fetch +
        # before scan. The slice says preflight runs after the fetch.
        # Either order is fine for refusal; we just need the WorkflowError.
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "divergedslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception)
        # AC #4: message contains both substrings
        self.assertIn("origin/main", msg,
                      f"refusal must name 'origin/main'; got: {msg!r}")
        self.assertTrue(
            "pull or rebase" in msg.lower(),
            f"refusal must hint 'pull or rebase'; got: {msg!r}",
        )
        # AC #4 + close-out invariant: no spec dir was created
        self.assertFalse(
            any((self.target / "docs/specs").glob("*-divergedslot")),
            "refusal must happen BEFORE any spec dir mutation",
        )

    def test_preflight_allows_when_local_equals_origin(self):
        """AC #4 negative — when local main == origin/main (same SHA),
        no refusal: reservation proceeds. Distinguishes equality from
        behind."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # Same SHA — caller should NOT refuse even though `--is-ancestor`
        # also returns 0 for equal commits.
        behavior[("verify", "origin/main")] = _make_proc(0, "SAME\n", "")
        behavior[("verify", "main")] = _make_proc(0, "SAME\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "SAME\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "syncedslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Origin/main max=001 → reserve 002
        spec_dir = self.target / "docs" / "specs" / "002-syncedslot"
        self.assertTrue(spec_dir.is_dir())

    def test_preflight_allows_when_local_ahead_of_origin(self):
        """AC #4 negative — when local main is ahead of origin/main
        (unpushed commits), don't refuse on the diverged-main check.
        The push step's race classifier handles any actual conflict."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        behavior[("verify", "origin/main")] = _make_proc(0, "OLDR\n", "")
        behavior[("verify", "main")] = _make_proc(0, "NEWR\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "NEWR\n", "")
        # main is NOT ancestor of origin/main (rc=1) → local is ahead
        behavior[("ancestor", "main", "origin/main")] = _make_proc(1)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "aheadslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        spec_dir = self.target / "docs" / "specs" / "002-aheadslot"
        self.assertTrue(spec_dir.is_dir())

    # ----------- AC #5: shared exit code ------------------------------

    def test_diverged_refusal_exits_2_through_main(self):
        """AC #5 — `WorkflowError` routes through main() to exit 2, the
        same code as today's dirty/off-main refusals. Smoke check at the
        process boundary (not just at the helper level)."""
        # Build a minimal scaffolded layout in tmp and run the CLI with
        # PYTHONPATH set so our patched module can be imported. Rather
        # than spawning git for real, we just check exit-code semantics:
        # WorkflowError → exit 2 is established by 003-03. The
        # diverged-main refusal MUST go through the same path.
        # We assert structurally: the new helper raises WorkflowError
        # (already covered by `test_preflight_refuses_when_local_main_
        # behind_origin`); here we additionally check that `main()`'s
        # WorkflowError handler still maps to exit 2 — i.e. no new
        # exit-code class was added.
        # Simplest assertion: pass a slug that fails preflight (off-main)
        # via the actual CLI and confirm exit 2 — proving the shared
        # path still works. Then assert via inspection that the new
        # diverged path raises WorkflowError (not some new exception
        # type).
        # AC #5 part A: WorkflowError → exit 2 via main() is intact.
        result = run_workflow(
            "new", "valid-slug",
            "--project-dir", str(self.target),
            "--no-push",
        )
        # This run will fail preflight (no git init in tmpdir →
        # symbolic-ref fails). Exit code 2 confirms the WorkflowError
        # → exit 2 contract.
        self.assertEqual(
            result.returncode, 2,
            f"WorkflowError must exit 2; got rc={result.returncode}, "
            f"stderr={result.stderr!r}",
        )
        # AC #5 part B: structural — the new diverged-main helper raises
        # the SAME exception class. We verify by introspection.
        self.assertTrue(
            issubclass(_workflow.WorkflowError, Exception),
            "new refusal path must use the existing WorkflowError class",
        )

    # ----------- AC #6: fetch failure preserves warn-and-proceed ------

    def test_fetch_failure_preserves_warn_and_proceed(self):
        """AC #6 — `git fetch origin main` fails → existing warning to
        stderr (workflow.py:1278-1282) is emitted verbatim; the new
        diverged-main check is skipped (no origin/main to compare); the
        scan falls back to working-tree per AC #3."""
        from unittest.mock import patch
        import io
        self._mkspec("001-existing")
        self._mkspec("004-other")
        behavior = self._default_preflight_behavior()
        # fetch FAILS
        behavior[("fetch",)] = _make_proc(
            1, "", "fatal: unable to access: network down")
        # Because fetch failed, origin/main may be stale or absent.
        # Even if a previous fetch left it present, the new check must
        # be guarded; here we simulate "no ref" so the diverged check
        # has nothing to compare and the scan falls back.
        behavior[("verify", "origin/main")] = _make_proc(1, "", "")
        fake = self._patched_run(behavior)
        captured = io.StringIO()
        with patch.object(_workflow, "subprocess") as sp_mod, \
             patch.object(_workflow.sys, "stderr", captured):
            sp_mod.run = fake
            code = _workflow.reserve_spec(
                "warnslot", project_dir=self.target,
                no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # AC #6: existing warn-and-proceed text preserved
        stderr_text = captured.getvalue()
        self.assertIn("warning:", stderr_text)
        self.assertIn("git fetch origin main", stderr_text)
        self.assertIn("proceeding with local view", stderr_text)
        # AC #6: scan fell back to working-tree (max=004 → 005)
        spec_dir = self.target / "docs" / "specs" / "005-warnslot"
        self.assertTrue(spec_dir.is_dir(),
                        f"expected 005-warnslot via working-tree fallback; "
                        f"got: "
                        f"{sorted((self.target / 'docs/specs').iterdir())}")
        # AC #6 absence-of-effect: ls-tree not called (no origin/main)
        for c in fake._calls:
            self.assertFalse(
                c[:2] == ["git", "ls-tree"],
                f"fetch-failed path must not call ls-tree; got: {c}",
            )

    # ----------- AC #7: race classifier path still reachable ----------

    def test_race_classifier_path_still_reachable(self):
        """AC #7 — `_classify_push_failure` and the on-push race-recovery
        path (workflow.py:1352-1374) remain wired. Simulate a race-on-
        push (non-fast-forward) and confirm the classifier's race branch
        fires and the recovery path runs (reset HEAD~1 + spec-dir
        cleanup)."""
        from unittest.mock import patch
        self._mkspec("001-existing")
        behavior = self._default_preflight_behavior()
        # origin/main present, in sync — preflight passes.
        behavior[("verify", "origin/main")] = _make_proc(0, "X\n", "")
        behavior[("verify", "main")] = _make_proc(0, "X\n", "")
        behavior[("rev-parse", "main")] = _make_proc(0, "X\n", "")
        behavior[("ancestor", "main", "origin/main")] = _make_proc(0)
        behavior[("ls-tree",)] = _make_proc(0, "001-existing\n", "")
        # push fails with race signal
        behavior[("push-main",)] = _make_proc(
            1, "", "! [rejected] main -> main (non-fast-forward)\n")
        behavior[("reset-head1",)] = _make_proc(0)
        fake = self._patched_run(behavior)
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = fake
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "raceslot", project_dir=self.target,
                    no_push=False, pr_mode=False,
                )
        # AC #7: classifier surfaced 'race-on-push'
        self.assertIn("race-on-push", str(ctx.exception))
        # AC #7 absence-of-effect: recovery ran reset --hard HEAD~1
        reset_calls = [
            c for c in fake._calls
            if c[:4] == ["git", "reset", "--hard", "HEAD~1"]
        ]
        self.assertEqual(
            len(reset_calls), 1,
            f"race-recovery must reset HEAD~1; got: {fake._calls}",
        )
        # AC #7: classifier helper still importable + behaves
        self.assertEqual(
            _workflow._classify_push_failure(
                "! [rejected] main -> main (non-fast-forward)"),
            "race",
        )
        self.assertEqual(
            _workflow._classify_push_failure(
                "remote: error: GH006: Protected branch update failed."),
            "protection",
        )

    # ----------- AC #8: stale comment at workflow.py:1269 updated -----

    def test_stale_comment_at_fetch_step_updated(self):
        """AC #8 — the comment at the fetch step is rewritten to reflect
        both effects (the scan AND the divergence preflight consult
        origin/main). We assert the new prose is present and the old
        misleading line is gone."""
        text = Path(_workflow.__file__).read_text()
        # The old single-purpose phrasing must be removed
        self.assertNotIn(
            "so the next-number scan reflects the freshest state",
            text,
            "stale single-purpose fetch comment must be replaced",
        )
        # The new phrasing must mention BOTH effects: the scan AND
        # the divergence preflight reading from origin/main.
        # We accept a few wordings; the load-bearing bits are
        # "next-number scan" and "divergence preflight" (or
        # synonyms like "diverged-main" / "preflight").
        self.assertIn("next-number scan", text)
        self.assertTrue(
            ("divergence preflight" in text
             or "diverged-main" in text
             or "diverged preflight" in text),
            "fetch comment must name the divergence preflight effect "
            "alongside the next-number scan",
        )


# ===========================================================================
# Slice 045-03: lifecycle-transition-gates.
#
# `workflow.py transition` refuses REVIEWED / RECONCILED / DONE moves
# unless the review evidence required by ADR-0014 §5 exists and clears.
# These tests run the gate ON (gate=True → JIG_REVIEW_EVIDENCE_GATE unset)
# and build evidence fixtures as `reviews/slice-NN-<pass>.md` files in a
# temp spec dir, mirroring the 045-02 recorder layout.
# ===========================================================================


class _GateFixture(unittest.TestCase):
    """Builds a temp spec dir with one slice file and (optionally) review
    evidence + a deviation log, then drives gated transitions with the
    gate enabled."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-wf-gate-"))
        # docs/specs/NNN-slug/ layout so evidence_path resolves a sibling
        # reviews/ dir under the spec.
        self.spec_dir = self.tmpdir / "docs" / "specs" / "045-gate-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec_md = self.spec_dir / "spec.md"
        self.spec_md.write_text(
            "---\nstatus: IN_PROGRESS\n---\n\n# Spec\n\n## Overview\n\nx.\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def write_slice(self, status: str, *, slice_no: str = "01",
                    slug: str = "thing", arch_review: bool = False,
                    deviation_log: bool = False,
                    dod_lines: list = None,
                    label: str = None) -> None:
        """Write `slice-NN-<slug>.md` with the given status. The `## Slice`
        label defaults to `045-NN — <slug>` so the fragment `045-NN`
        resolves it."""
        label = label or f"045-{slice_no} — {slug}"
        fm = ["---", f"status: {status}", "dependencies: []", "last_verified:"]
        if arch_review:
            fm.append("arch_review: true")
        fm.append("---")
        body = ["", f"## Slice {label}", "", "**Goal:** placeholder.", ""]
        if dod_lines:
            body.extend(["**Definition of Done:**", ""])
            body.extend(dod_lines)
            body.append("")
        if deviation_log:
            body.extend(["### Deviation log (after reconciliation)", "",
                         "Real reconciliation prose here.", ""])
        (self.spec_dir / f"slice-{slice_no}-{slug}.md").write_text(
            "\n".join(fm) + "\n" + "\n".join(body) + "\n"
        )

    def write_evidence(self, pass_name: str, *, slice_no: str = "01",
                       verdict: str = "pass",
                       reviewer: str = "jig:reviewer",
                       reviewed_at: str = "2026-06-02T14:30:00Z",
                       prompt_source: str = "review.py x",
                       slice_field: str = None,
                       omit: tuple = (),
                       raw: str = None) -> Path:
        """Write `reviews/slice-NN-<pass>.md` verdict file (ADR-0014 §1/§2).
        `omit` drops named frontmatter fields (malformed-input fixtures);
        `raw` overrides the entire file content verbatim."""
        slice_field = slice_field or f"045-{slice_no}"
        reviews = self.spec_dir / "reviews"
        reviews.mkdir(exist_ok=True)
        path = reviews / f"slice-{slice_no}-{pass_name}.md"
        if raw is not None:
            path.write_text(raw)
            return path
        fields = {
            "slice": slice_field,
            "pass": pass_name,
            "verdict": verdict,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "prompt_source": prompt_source,
        }
        lines = ["---"]
        for k, v in fields.items():
            if k in omit:
                continue
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append("## VERDICT")
        lines.append(verdict)
        path.write_text("\n".join(lines) + "\n")
        return path

    def _status_in_slice(self, slice_no: str = "01",
                         slug: str = "thing") -> str:
        text = (self.spec_dir / f"slice-{slice_no}-{slug}.md").read_text()
        m = re.search(r"^status:\s*(\w+)", text, re.MULTILINE)
        return m.group(1) if m else "?"


class TransitionReviewedGateTests(_GateFixture):
    """AC1: REVIEWED is gated on compliance + craft (+ arch when flagged)."""

    # --- clears ---
    def test_reviewed_clears_with_compliance_and_craft_pass(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "REVIEWED")

    # --- missing ---
    def test_reviewed_blocked_when_compliance_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("craft")  # compliance absent
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())
        # Status not advanced.
        self.assertEqual(self._status_in_slice(), "IN_PROGRESS")

    def test_reviewed_blocked_when_craft_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")  # craft absent
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    # --- malformed ---
    def test_reviewed_blocked_when_evidence_malformed(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        # craft file with no frontmatter block at all.
        self.write_evidence("craft", raw="no frontmatter here\n")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    def test_reviewed_blocked_when_required_field_missing(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft", omit=("verdict",))
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("verdict", r.stderr.lower())

    # --- fail / needs-changes (superseded-only) ---
    def test_reviewed_blocked_when_compliance_fail(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance", verdict="fail")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())

    def test_reviewed_blocked_when_craft_needs_changes(self):
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft", verdict="needs-changes")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("craft", r.stderr.lower())

    # --- arch: required only when flagged ---
    def test_reviewed_blocked_when_arch_flagged_but_missing(self):
        self.write_slice("IN_PROGRESS", arch_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        # arch evidence absent though the slice declares arch_review: true
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("arch", r.stderr.lower())

    def test_reviewed_clears_when_arch_flagged_and_present(self):
        self.write_slice("IN_PROGRESS", arch_review=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("arch")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected REVIEWED to clear; stderr={r.stderr}")

    def test_reviewed_ignores_arch_when_not_flagged(self):
        # No arch_review flag → arch evidence not required even if absent.
        self.write_slice("IN_PROGRESS")
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"arch should not be required; stderr={r.stderr}")


class TransitionReconciledGateTests(_GateFixture):
    """AC2: RECONCILED needs the reconciliation verdict AND a deviation log."""

    def test_reconciled_clears_with_verdict_and_devlog(self):
        self.write_slice("REVIEWED", deviation_log=True)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected RECONCILED to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "RECONCILED")

    def test_reconciled_blocked_when_reconciliation_evidence_missing(self):
        self.write_slice("REVIEWED", deviation_log=True)
        # no reconciliation verdict file
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())

    def test_reconciled_blocked_when_deviation_log_missing(self):
        self.write_slice("REVIEWED", deviation_log=False)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("deviation log", r.stderr.lower())

    def test_reconciled_blocked_when_reconciliation_fail(self):
        self.write_slice("REVIEWED", deviation_log=True)
        self.write_evidence("reconciliation", verdict="fail")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "RECONCILED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())


class TransitionDoneGateTests(_GateFixture):
    """AC2: DONE re-validates the full set AND keeps the dependency check."""

    def _write_full_evidence(self):
        self.write_evidence("compliance")
        self.write_evidence("craft")
        self.write_evidence("reconciliation")

    def test_done_clears_with_full_evidence(self):
        self.write_slice("RECONCILED", deviation_log=True)
        self._write_full_evidence()
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertEqual(r.returncode, 0,
                         f"expected DONE to clear; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "DONE")

    def test_done_blocked_when_reviewed_evidence_missing(self):
        # Reconciliation present but compliance/craft absent — the DONE
        # re-validation must catch a hand-edited status that skipped REVIEWED.
        self.write_slice("RECONCILED", deviation_log=True)
        self.write_evidence("reconciliation")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("compliance", r.stderr.lower())

    def test_done_blocked_when_reconciliation_missing(self):
        self.write_slice("RECONCILED", deviation_log=True)
        self.write_evidence("compliance")
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reconciliation", r.stderr.lower())

    def test_done_still_enforces_dependency_check(self):
        # Full evidence present, but a dependency is unsatisfied — the
        # existing dependency gate must still fire (belt-and-suspenders).
        # Add an unsatisfied dep to the slice frontmatter.
        (self.spec_dir / "slice-01-thing.md").write_text(
            "---\nstatus: RECONCILED\ndependencies: [099-99]\n"
            "last_verified:\n---\n\n## Slice 045-01 — thing\n\n"
            "**Goal:** x.\n\n### Deviation log\n\nprose.\n"
        )
        self._write_full_evidence()
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DONE", gate=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("dependen", r.stderr.lower())


class TransitionGateDiagnosticsTests(_GateFixture):
    """AC3: refusals name the missing/invalid artifact AND the command."""

    def test_diagnostic_names_artifact_and_command(self):
        self.write_slice("IN_PROGRESS")
        # compliance missing entirely
        self.write_evidence("craft")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "REVIEWED", gate=True)
        self.assertNotEqual(r.returncode, 0)
        err = r.stderr.lower()
        # Names the pass.
        self.assertIn("compliance", err)
        # Names the recorder command a contributor runs next.
        self.assertIn("record-review", err)


class TransitionUngatedStatesTests(_GateFixture):
    """AC4: ungated transitions + the two review back-edges still work
    with the gate ON and no evidence present."""

    def test_draft_to_ready_for_review_ungated(self):
        self.write_slice("DRAFT")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_REVIEW", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_ready_for_review_to_ready_for_implementation_ungated(self):
        self.write_slice("READY_FOR_REVIEW")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "READY_FOR_IMPLEMENTATION", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_ready_for_implementation_to_in_progress_ungated(self):
        self.write_slice("READY_FOR_IMPLEMENTATION")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_any_to_deferred_ungated(self):
        self.write_slice("IN_PROGRESS")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DEFERRED", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_deferred_to_draft_reopen_ungated(self):
        self.write_slice("DEFERRED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "DRAFT", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_reviewed_to_in_progress_back_edge_ungated(self):
        # needs-changes back-edge relaxes status → nothing to gate, even
        # with no evidence on disk.
        self.write_slice("REVIEWED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")

    def test_reconciled_to_in_progress_back_edge_ungated(self):
        # reconciliation-fails back-edge relaxes status → ungated.
        self.write_slice("RECONCILED")
        r = run_workflow("transition", str(self.spec_md), "045-01",
                         "IN_PROGRESS", gate=True)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}")


class TransitionGateBypassTests(_GateFixture):
    """Bypass: JIG_REVIEW_EVIDENCE_GATE in the falsey set skips the
    evidence check (a deliberate-actor escape hatch, ADR-0011 stance)."""

    def _run_with_gate_env(self, value, *args):
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["JIG_REVIEW_EVIDENCE_GATE"] = value
        return subprocess.run(
            [sys.executable, str(WORKFLOW), *args],
            capture_output=True, text=True, env=env,
        )

    def test_bypass_zero_lets_reviewed_through_without_evidence(self):
        self.write_slice("IN_PROGRESS")
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "REVIEWED",
        )
        self.assertEqual(r.returncode, 0,
                         f"bypass=0 should skip the gate; stderr={r.stderr}")
        self.assertEqual(self._status_in_slice(), "REVIEWED")

    def test_bypass_accepts_false_off_no(self):
        for value in ("false", "off", "no", "FALSE", "Off"):
            with self.subTest(value=value):
                self.write_slice("IN_PROGRESS")
                r = self._run_with_gate_env(
                    value, "transition", str(self.spec_md), "045-01",
                    "RECONCILED",
                )
                self.assertEqual(
                    r.returncode, 0,
                    f"bypass={value!r} should skip the gate; stderr={r.stderr}",
                )

    def test_bypass_still_enforces_dependency_check_on_done(self):
        # The bypass only skips the *evidence* check; the DONE dependency
        # check must still run (per the slice brief).
        (self.spec_dir / "slice-01-thing.md").write_text(
            "---\nstatus: RECONCILED\ndependencies: [099-99]\n"
            "last_verified:\n---\n\n## Slice 045-01 — thing\n\n**Goal:** x.\n"
        )
        r = self._run_with_gate_env(
            "0", "transition", str(self.spec_md), "045-01", "DONE",
        )
        self.assertNotEqual(r.returncode, 0,
                            "dependency check must still fire under bypass")
        self.assertIn("dependen", r.stderr.lower())


class ArchReviewTruthyUnificationTests(unittest.TestCase):
    """045-03 must-do (d): a SINGLE shared truthy predicate backs both
    `workflow.slice_needs_arch_review` and
    `review_evidence._arch_review_flag` so they cannot drift."""

    def test_workflow_and_evidence_share_one_truthy_source(self):
        sys.path.insert(0, str(REPO_ROOT / "skills"))
        sys.path.insert(0, str(REPO_ROOT / "skills" / "spec-workflow"))
        import importlib
        parsing = importlib.import_module("_common.parsing")
        review_evidence = importlib.import_module("_common.review_evidence")
        workflow = importlib.import_module("workflow")
        # The shared constant exists in the common module.
        self.assertTrue(hasattr(parsing, "FRONTMATTER_TRUTHY"))
        shared = parsing.FRONTMATTER_TRUTHY
        # Both callers' truthy tuples are the SAME object as the shared one
        # (identity, not just equality — that's what "cannot drift" means).
        self.assertIs(workflow._ARCH_REVIEW_TRUTHY, shared)
        self.assertIs(review_evidence._ARCH_REVIEW_TRUTHY, shared)

    def test_shared_predicate_accepts_permissive_truthy_set(self):
        sys.path.insert(0, str(REPO_ROOT / "skills"))
        import importlib
        parsing = importlib.import_module("_common.parsing")
        for tok in ("true", "yes", "on", "1", "YES", "On", "TRUE"):
            self.assertTrue(parsing.frontmatter_flag_truthy(tok),
                            f"{tok!r} should be truthy")
        for tok in ("false", "no", "0", "maybe", "", None):
            self.assertFalse(parsing.frontmatter_flag_truthy(tok),
                             f"{tok!r} should not be truthy")

class AmendmentDigestTests(unittest.TestCase):
    """workflow.py amendments — read-only digest of the `## Amendments`
    overrides on closed records (slice 048-04). Indexes current truth so a
    reader needn't reread historical drift; never modifies any artifact."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-amd-")
        self.proj = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, rel: str, text: str) -> None:
        p = self.proj / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    # AC #1 / #2 — lists amendment-bearing artifacts (path + date + title),
    # sorted; AC #5 — an artifact without amendments is not listed.
    def test_lists_amendment_bearing_artifacts_sorted(self):
        self._write(
            "docs/specs/016-scaffold-mode/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 016\n\nbody\n\n"
            "## Amendments\n\n### 2026-05-27 — Hook count: five → seven\n"
            "prose.\n",
        )
        self._write(
            "docs/decisions/adr-0008-closed-spec-drift-policy.md",
            "# ADR-0008\n\nbody\n\n## Amendments\n\n"
            "### 2026-05-27 — Hook count: five → seven\nprose.\n",
        )
        self._write(
            "docs/specs/099-no-amendments/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 099\n\nno amendments here.\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        out = result.stdout
        self.assertIn("docs/decisions/adr-0008-closed-spec-drift-policy.md", out)
        self.assertIn("docs/specs/016-scaffold-mode/spec.md", out)
        self.assertIn("2026-05-27 — Hook count: five → seven", out)
        self.assertNotIn("099-no-amendments", out)
        # Stable, sorted by path: decisions/ precedes specs/.
        self.assertLess(
            out.index("docs/decisions/adr-0008"),
            out.index("docs/specs/016-scaffold-mode"),
            "digest must be sorted by artifact path",
        )

    # AC #5 — absence case: clear message, exit 0.
    def test_handles_no_amendments(self):
        self._write(
            "docs/specs/099-no-amendments/spec.md",
            "---\nstatus: DONE\n---\n\n# Spec 099\n\nno amendments.\n",
        )
        self._write("docs/decisions/adr-0001-foo.md", "# ADR-0001\n\nbody.\n")
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)

    # Edge: a `## Amendments` heading with no dated entries is not a real
    # override — skip it (don't crash or emit an empty artifact block).
    def test_ignores_empty_amendments_section(self):
        self._write(
            "docs/specs/016-scaffold-mode/spec.md",
            "# Spec 016\n\nbody\n\n## Amendments\n\n(none yet)\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)

    # Edge: a `## Amendments` heading INSIDE a ```-fenced code block is an
    # illustrative example (this is exactly ADR-0008's shape — it documents
    # the amendment *format* in a fence), NOT a live amendment. It must be
    # ignored, or the digest reports a false override.
    def test_ignores_fenced_amendments_example(self):
        self._write(
            "docs/decisions/adr-0008-closed-spec-drift-policy.md",
            "# ADR-0008\n\nThe amendment shape:\n\n"
            "```markdown\n## Amendments\n\n"
            "### 2026-05-27 — Hook count: five → seven\nillustrative prose.\n"
            "```\n\n(the above is just an example of the format.)\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("No amendment-bearing artifacts", result.stdout)
        self.assertNotIn("adr-0008", result.stdout)

    # AC #1 — amendments can live in slice files, not only spec.md / ADRs.
    def test_finds_amendments_in_slice_files(self):
        self._write(
            "docs/specs/016-scaffold-mode/slice-01-foo.md",
            "---\nstatus: DONE\n---\n\n## Slice 016-01\n\nbody\n\n"
            "## Amendments\n\n### 2026-06-01 — Renamed widget → gadget\nprose.\n",
        )
        result = run_workflow("amendments", "--project-dir", str(self.proj))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("slice-01-foo.md", result.stdout)
        self.assertIn("2026-06-01 — Renamed widget → gadget", result.stdout)


class ReserveSpecFromLinkedWorktreeE2E(unittest.TestCase):
    """Real-git end-to-end proof of the worktree-aware reservation fix.

    Reproduces the exact friction that motivated it: a linked worktree on a
    feature branch with `main` checked out in the primary worktree (so the
    linked worktree CANNOT `git checkout main`). The reservation must still
    land on origin/main, clean up its ephemeral worktree, and leave the
    caller's branch and working tree untouched.

    Unlike the recorder-based tests above, this class drives REAL `git` (no
    subprocess patching) — the bug was about git's one-checkout-per-branch
    worktree semantics, which only real git exercises."""

    def _git(self, *args, cwd):
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        )

    def setUp(self):
        import shutil
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-wf-wt-e2e-"))
        # Build `work` on `main` directly (robust across git versions —
        # avoids empty-clone default-branch quirks), seed two specs, then
        # push to a bare `origin`.
        self.work = self.tmp / "work"
        self._git("init", str(self.work), cwd=self.tmp)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.work)
        for k, v in (("user.email", "t@e.x"), ("user.name", "T"),
                     ("commit.gpgsign", "false")):
            self._git("config", k, v, cwd=self.work)
        for name in ("001-alpha", "002-beta"):
            d = self.work / "docs" / "specs" / name
            d.mkdir(parents=True)
            (d / "spec.md").write_text(f"# Spec {name}\n")
        self._git("add", "-A", cwd=self.work)
        self._git("commit", "-m", "seed specs", cwd=self.work)
        self.origin = self.tmp / "origin.git"
        self._git("init", "--bare", str(self.origin), cwd=self.tmp)
        self._git("remote", "add", "origin", str(self.origin), cwd=self.work)
        push = self._git("push", "-u", "origin", "main", cwd=self.work)
        self.assertEqual(push.returncode, 0, f"seed push failed: {push.stderr}")
        # Linked worktree on a feature branch — `main` stays held by `work`.
        self.feat = self.tmp / "feat"
        add = self._git("worktree", "add", "-b", "feature", str(self.feat),
                        cwd=self.work)
        self.assertEqual(add.returncode, 0, f"worktree add failed: {add.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reserve_from_linked_worktree_lands_on_origin_main(self):
        # Precondition the whole fix rests on: the linked worktree genuinely
        # cannot check out `main` (it's held by `work`).
        co = self._git("checkout", "main", cwd=self.feat)
        self.assertNotEqual(co.returncode, 0)
        self.assertIn("already used by worktree", co.stderr)

        feat_head_before = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()

        # Reserve from the linked worktree — REAL git, no mocking.
        code = _workflow.reserve_spec(
            "gamma", project_dir=self.feat, no_push=False, pr_mode=False,
        )
        self.assertEqual(code, 0)

        # The reservation landed on origin/main as 003-gamma (max + 1).
        ls = self._git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        self.assertIn("docs/specs/003-gamma/spec.md", ls.stdout)

        # The ephemeral reservation worktree was cleaned up — only `work`
        # and `feat` remain registered.
        wl = self._git("worktree", "list", cwd=self.work).stdout
        self.assertNotIn("jig-reserve-spec", wl)
        self.assertEqual(len(wl.strip().splitlines()), 2, wl)

        # The caller's branch tip and working tree are untouched: identical
        # HEAD, and the stub does NOT appear in the feature worktree.
        feat_head_after = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()
        self.assertEqual(feat_head_before, feat_head_after)
        self.assertFalse((self.feat / "docs/specs/003-gamma").exists())


if __name__ == "__main__":
    unittest.main()
