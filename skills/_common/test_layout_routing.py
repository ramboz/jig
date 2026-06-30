"""Cross-cutting routing tests for slice 084-02 — the jig helpers honor a
configured `layout.docs_root` (ADR-0033) and resolve project-root *discovery*
via the sentinel, never structure.

Two guard tests back the rewiring:
  - `NoStrayDocsLiteralTests` — AST scan of the rewired modules: no `X / "docs"`
    path-join survives (allowlist: template-source paths + push-mode worktree
    reconstruction).
  - `DiscoveryBleedTests` — both discovery categories resolve a nested
    subproject to itself, never the enclosing repo.

Run from the repo root:
    python3 skills/_common/test_layout_routing.py
"""

import ast
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills"))
for _d in ("spec-workflow", "adr-workflow", "independent-review", "bug-fix",
           "memory-sync", "scaffold-init"):
    sys.path.insert(0, str(REPO_ROOT / "skills" / _d))

import adr  # noqa: E402
import decisions  # noqa: E402
import memory  # noqa: E402
import review  # noqa: E402
import stocktake  # noqa: E402
import workflow  # noqa: E402
from _common import (
    lexicon,  # noqa: E402
    scaffold_state,  # noqa: E402
    team_signal,  # noqa: E402
)
from _common import project_layout as pl  # noqa: E402


def _mk_dotroot_project() -> Path:
    """A scaffolded project whose scaffold.json sets docs_root='.'."""
    tmp = Path(tempfile.mkdtemp(prefix="jig-route-")).resolve()
    (tmp / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
    return tmp


_MIN_SPEC = (
    "---\nstatus: DONE\ndependencies: []\nlast_verified: 2026-06-29\n---\n\n"
    "# Spec 001 — demo\n\n## Overview\n\nDemo.\n\n"
    "## Slice 001-01 — demo\n\n**STATUS: DONE**\n"
)


class StatusBoardLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = _mk_dotroot_project()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_status_board_writes_collapsed_path(self):
        # docs_root="." → board at <project>/specs/README.md, NOT docs/specs/.
        spec = self.tmp / "specs" / "001-demo" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(_MIN_SPEC)
        # regenerate_status_board updates an existing board — seed the skeleton
        # at the collapsed path it must resolve to.
        (self.tmp / "specs" / "README.md").write_text(
            "# Status board\n\n| Spec | Slice | Status | Notes |\n"
            "| --- | --- | --- | --- |\n"
        )
        workflow.regenerate_status_board(self.tmp)
        board = (self.tmp / "specs" / "README.md").read_text()
        self.assertIn("001-01", board)  # row rebuilt from the collapsed specs dir
        self.assertFalse((self.tmp / "docs" / "specs" / "README.md").exists())


class ScaffoldStateRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = _mk_dotroot_project()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_classified_scaffolded_and_helpers_collapse(self):
        # AC5: sentinel present → scaffolded; every helper resolves collapsed.
        self.assertEqual(scaffold_state.classify_scaffold_state(self.tmp), "scaffolded")
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "specs")
        self.assertEqual(pl.decisions_dir(self.tmp), self.tmp / "decisions")
        self.assertEqual(pl.memory_dir(self.tmp), self.tmp / "memory")


class WriterLayoutTests(unittest.TestCase):
    """The newly-inventoried artifact writers land under the collapsed root."""

    def setUp(self):
        self.tmp = _mk_dotroot_project()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_memory_writers_collapse(self):
        self.assertEqual(memory._glossary_path(self.tmp), self.tmp / "memory" / "glossary.md")
        self.assertEqual(memory._inbox_path(self.tmp), self.tmp / "inbox.md")
        # _ensure_file side effect: they create under the collapsed root.
        self.assertTrue((self.tmp / "memory" / "glossary.md").is_file())
        self.assertTrue((self.tmp / "inbox.md").is_file())
        self.assertFalse((self.tmp / "docs").exists())

    def test_people_md_path_collapses(self):
        self.assertEqual(team_signal.people_md_path(self.tmp), self.tmp / "memory" / "people.md")

    def test_lightweight_path_collapses(self):
        self.assertEqual(
            decisions.lightweight_path(self.tmp),
            self.tmp / "decisions" / "lightweight-decisions.md",
        )

    def test_stocktake_reads_collapsed_specs(self):
        spec = self.tmp / "specs" / "001-demo" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(_MIN_SPEC)
        self.assertEqual(stocktake.count_reconciled_slices(self.tmp), 1)

    def test_lexicon_overlay_honors_dot_root(self):
        # lexicon stays stdlib-only (hook-safe) and CANNOT import project_layout,
        # so it duplicates docs_root resolution in `_memory_dir`. Guard that
        # forced duplication behaviorally: a docs_root="." project's glossary
        # overlay must resolve to <project>/memory/glossary.md (the AST literal
        # guard cannot catch wrong-root *logic*).
        self.assertEqual(lexicon._memory_dir(self.tmp), self.tmp / "memory")
        gloss = self.tmp / "memory" / "glossary.md"
        gloss.parent.mkdir(parents=True)
        gloss.write_text("# Glossary\n\n## Frobnicator\n\nA project-only term.\n")
        merged = lexicon.load(self.tmp)
        self.assertIn("frobnicator", merged)
        self.assertFalse((self.tmp / "docs").exists())


class AdrIndexLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = _mk_dotroot_project()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_index_works_on_collapsed_decisions(self):
        # AC4: `adr index <dir>` works for the collapsed decisions dir.
        dec = pl.decisions_dir(self.tmp)
        dec.mkdir(parents=True)
        (dec / "adr-0001-demo.md").write_text(
            "---\nstatus: Accepted\n---\n\n# ADR-0001: Demo\n\n## Status\n\nAccepted\n"
        )
        # cmd_index regenerates an existing `## Index` section — seed it.
        (dec / "README.md").write_text("# Decisions\n\n## Index\n\n")
        out = adr.cmd_index(dec)
        self.assertEqual(out, dec / "README.md")
        self.assertIn("0001", out.read_text())


class DefaultLayoutUnchangedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-route-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_no_scaffold_uses_docs(self):
        # No scaffold.json → default "docs". Identical to legacy.
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "docs" / "specs")
        self.assertEqual(memory._glossary_path.__module__, "memory")  # sanity
        # team_signal default path under docs/.
        self.assertEqual(
            team_signal.people_md_path(self.tmp),
            self.tmp / "docs" / "memory" / "people.md",
        )


class DiscoveryBleedTests(unittest.TestCase):
    """AC7 — both discovery categories resolve a nested subproject to itself."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-route-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _nested(self):
        repo = self.tmp / "monorepo"
        (repo / ".git").mkdir(parents=True)
        (repo / "docs").mkdir()
        (repo / "docs" / "architecture.md").write_text("# repo arch")
        sub = repo / "cwv"
        sub.mkdir()
        (sub / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
        spec = sub / "specs" / "001-x" / "spec.md"
        spec.parent.mkdir(parents=True)
        spec.write_text("# spec")
        return repo, sub, spec

    def test_depth_arithmetic_discovery_resolves_subproject(self):
        # workflow._project_root_for_spec must return the sentinel-bearing
        # subproject, NOT the enclosing repo (legacy parents[3]).
        repo, sub, spec = self._nested()
        self.assertEqual(spec.resolve().parents[3], repo)  # the trap
        self.assertEqual(workflow._project_root_for_spec(spec), sub)

    def test_marker_up_walk_discovery_resolves_subproject(self):
        # review._find_project_root must return the subproject, never the
        # ancestor that has docs/architecture.md.
        repo, sub, spec = self._nested()
        self.assertEqual(review._find_project_root(spec), sub)

    def test_find_project_root_none_when_no_project(self):
        orphan = self.tmp / "orphan" / "spec.md"
        orphan.parent.mkdir(parents=True)
        orphan.write_text("# spec")
        self.assertIsNone(review._find_project_root(orphan))


class NoStrayDocsLiteralTests(unittest.TestCase):
    """AC6 — no `X / "docs"` path-join survives in the rewired modules.

    Allowlist (legitimately keep a "docs" literal): template-SOURCE paths
    (a join chain containing "templates") and push-mode detached-worktree
    reconstruction (`wt / "docs" / ...`, default-layout push, refused in a
    subtree by 084-03). Pre-sentinel detectors (scaffold_state, scaffold.py,
    migrate.py) are NOT in the scanned set. AST-based: matches a Constant
    equal to "docs" used as an operand of a `/` (Div) BinOp.
    """

    REWIRED = [
        "skills/spec-workflow/workflow.py",
        "skills/adr-workflow/adr.py",
        "skills/independent-review/review.py",
        "skills/bug-fix/bug.py",
        "skills/memory-sync/decisions.py",
        "skills/memory-sync/memory.py",
        "skills/_common/team_signal.py",
        "skills/scaffold-init/stocktake.py",
        "skills/_common/lexicon.py",
    ]

    @staticmethod
    def _is_allowed(segment: str) -> bool:
        seg = (segment or "").strip()
        return "templates" in seg or seg.startswith("wt ") or "wt /" in seg

    def test_no_stray_docs_path_join(self):
        violations = []
        for rel in self.REWIRED:
            src = (REPO_ROOT / rel).read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
                    continue
                operands = [node.left, node.right]
                if not any(
                    isinstance(o, ast.Constant) and o.value == "docs"
                    for o in operands
                ):
                    continue
                segment = ast.get_source_segment(src, node) or ""
                if self._is_allowed(segment):
                    continue
                violations.append(f"{rel}:{node.lineno}: {segment!r}")
        self.assertEqual(violations, [], "stray docs path-joins:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
