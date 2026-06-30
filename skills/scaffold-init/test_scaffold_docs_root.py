"""Tests for scaffold-init `--docs-root` (slice 084-03).

Covers: default byte-unchanged (no layout block / no caveat), `--docs-root .`
end-to-end collapse + manifest + helper round-trip, layout-aware primer links
on the plugin-only (doc_rewrite=None) path, CLI escape rejection with no partial
scaffold, the git_toplevel/subtree push-refusal, and the pinned brief caveat.

Run from the repo root:
    python3 skills/scaffold-init/test_scaffold_docs_root.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
sys.path.insert(0, str(REPO_ROOT / "skills"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "spec-workflow"))
sys.path.insert(0, str(REPO_ROOT / "skills" / "adr-workflow"))

import adr  # noqa: E402
import scaffold  # noqa: E402
import workflow  # noqa: E402
from _common import project_layout as pl  # noqa: E402
from _common import scaffold_state  # noqa: E402


def run_scaffold(target: Path, *extra: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target), *extra],
        capture_output=True, text=True, env=env,
    )


class DefaultUnchangedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-dr-")) / "proj"
        self.tmp.mkdir(parents=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(
            self.tmp.parent, ignore_errors=True))

    def test_default_writes_no_layout_block_and_no_caveat(self):
        # AC1: default scaffold → no `layout` block, no caveat, docs under docs/.
        r = run_scaffold(self.tmp, "--plugin-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        manifest = json.loads((self.tmp / "scaffold.json").read_text())
        self.assertNotIn("layout", manifest)
        self.assertTrue((self.tmp / "docs" / "architecture.md").is_file())
        brief = (self.tmp / "brief.md").read_text()
        self.assertNotIn("whole-repo dirty check", brief)


class DotRootEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-dr-")) / "cwv"
        self.tmp.mkdir(parents=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(
            self.tmp.parent, ignore_errors=True))

    def test_dot_root_collapses_and_round_trips(self):
        # AC2: `--docs-root .` → collapsed tree, layout block, scaffolded,
        # helpers resolve track-local, seed present.
        r = run_scaffold(self.tmp, "--docs-root", ".", "--plugin-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        # Collapsed: artifacts directly under the project dir, no docs/ layer.
        self.assertTrue((self.tmp / "architecture.md").is_file())
        self.assertTrue((self.tmp / "workflow.md").is_file())
        self.assertFalse((self.tmp / "docs").exists())
        # Manifest carries the layout block.
        manifest = json.loads((self.tmp / "scaffold.json").read_text())
        self.assertEqual(manifest["layout"], {"docs_root": "."})
        # Classifies scaffolded; helpers resolve collapsed.
        self.assertEqual(scaffold_state.classify_scaffold_state(self.tmp), "scaffolded")
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "specs")
        # Seed landed under the collapsed specs dir (AC2 end-to-end).
        self.assertTrue((self.tmp / "specs" / "001-adopt-jig" / "spec.md").is_file())
        self.assertTrue((self.tmp / "specs" / "README.md").is_file())

    def test_dot_root_primer_links_rewritten_plugin_only(self):
        # AC3: on the plugin-only path (doc_rewrite=None) the layout rewrite
        # still applies — CLAUDE.md `docs/specs/...` links collapse to `specs/...`.
        r = run_scaffold(self.tmp, "--docs-root", ".", "--plugin-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        claude_md = (self.tmp / "CLAUDE.md").read_text()
        self.assertIn("specs/", claude_md)
        self.assertNotIn("docs/specs/", claude_md)
        self.assertNotIn("docs/decisions/", claude_md)

    def test_dot_root_brief_has_pinned_caveat(self):
        # AC6: non-default layout → brief.md carries the pinned phrase.
        r = run_scaffold(self.tmp, "--docs-root", ".", "--plugin-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("whole-repo dirty check", (self.tmp / "brief.md").read_text())

    def test_status_board_command_round_trip(self):
        # AC2 (strongest form): a real 084-02 command (status-board) resolves
        # the collapsed paths end-to-end on the scaffolded project — not just a
        # bare helper call.
        r = run_scaffold(self.tmp, "--docs-root", ".", "--plugin-only")
        self.assertEqual(r.returncode, 0, r.stderr)
        workflow.regenerate_status_board(self.tmp)
        board = (self.tmp / "specs" / "README.md").read_text()
        self.assertIn("001-adopt-jig", board)  # seed rows on the collapsed board
        self.assertFalse((self.tmp / "docs" / "specs").exists())


class EscapeRejectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-dr-")) / "proj"
        self.tmp.mkdir(parents=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(
            self.tmp.parent, ignore_errors=True))

    def test_escape_rejected_leaves_no_partial(self):
        # AC4: `../x` is rejected before any write — no partial scaffold.
        r = run_scaffold(self.tmp, "--docs-root", "../evil", "--plugin-only")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.tmp / "scaffold.json").exists())
        self.assertFalse((self.tmp / "CLAUDE.md").exists())
        self.assertFalse((self.tmp / "docs").exists())

    def test_absolute_rejected(self):
        r = run_scaffold(self.tmp, "--docs-root", "/etc", "--plugin-only")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.tmp / "scaffold.json").exists())


class ComposeRewriteUnitTests(unittest.TestCase):
    def test_compose_applies_layout_on_machinery_path(self):
        # AC3 machinery path: layout rewrite composes onto a non-None existing
        # transform (both apply).
        existing = lambda t: t.replace("PLUG", "ok")  # noqa: E731
        fn = scaffold._compose_layout_rewrite(existing, ".")
        self.assertEqual(fn("PLUG [x](docs/specs/y)"), "ok [x](specs/y)")

    def test_compose_default_is_passthrough(self):
        existing = object()
        self.assertIs(scaffold._compose_layout_rewrite(existing, "docs"), existing)


class SubtreePushRefusalTests(unittest.TestCase):
    """AC5 — git_toplevel/subtree push-refusal."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-dr-")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(
            self.tmp, ignore_errors=True))
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)

    def test_refuses_for_subtree(self):
        # Subproject with scaffold.json nested under the git repo root.
        sub = self.tmp / "docs" / "opportunities" / "cwv"
        sub.mkdir(parents=True)
        (sub / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow._refuse_push_in_subtree(sub)
        self.assertIn("subtree push-mode unsupported", str(ctx.exception))

    def test_allows_repo_root_project(self):
        # scaffold.json at the git toplevel → NOT a subtree → no refusal.
        (self.tmp / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
        workflow._refuse_push_in_subtree(self.tmp)  # must not raise

    def test_git_toplevel_none_outside_repo(self):
        outside = Path(tempfile.mkdtemp(prefix="jig-nogit-")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        self.assertIsNone(workflow.git_toplevel(outside))
        # No git repo → nothing to refuse.
        workflow._refuse_push_in_subtree(outside)  # must not raise

    def test_adr_reserve_refuses_in_subtree(self):
        # Parity fix (arch review): `adr new --push` must also refuse in a
        # subtree (same shared-main failure as `new`). Shared detection in
        # _common.subtree; adr door raises AdrError.
        sub = self.tmp / "docs" / "opportunities" / "cwv"
        sub.mkdir(parents=True)
        (sub / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
        with self.assertRaises(adr.AdrError) as ctx:
            adr.reserve_adr("demo-slug", sub, no_push=False)
        self.assertIn("subtree push-mode unsupported", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
