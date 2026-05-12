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


if __name__ == "__main__":
    unittest.main()
