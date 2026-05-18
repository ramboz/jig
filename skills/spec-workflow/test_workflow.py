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
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_workflow(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
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
    def test_new_refuses_on_non_main_branch(self):
        self._mkspec("001-existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/something\n")
        from unittest.mock import patch
        with patch.object(_workflow, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_workflow.WorkflowError) as ctx:
                _workflow.reserve_spec(
                    "myslug", project_dir=self.target,
                    no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("main", msg.lower())
        # Refused BEFORE any mutation: spec dir not created
        self.assertFalse(any((self.target / "docs/specs").glob("*-myslug")))

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
        spec_before = self.spec.read_text()
        result = run_workflow(
            "transition", str(self.spec), "018-01", "IN_PROGRESS",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Slice file's frontmatter updated
        slice_after = self.slice_file.read_text()
        self.assertIn("status: IN_PROGRESS", slice_after)
        # spec.md UNCHANGED — the write must go to loc.path, not blindly spec_md
        self.assertEqual(self.spec.read_text(), spec_before)

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


if __name__ == "__main__":
    unittest.main()
