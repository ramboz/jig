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


if __name__ == "__main__":
    unittest.main()
