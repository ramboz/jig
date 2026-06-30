"""Tests for the shared project-layout helper (slice 084-01).

`skills/_common/project_layout.py` maps a `project_dir` to its artifact paths
through the configured (or default) `docs_root` read from
`<project_dir>/scaffold.json`, with a hardened path-escape validator and the
sentinel-anchored `project_root_for` discovery resolver (ADR-0033 §3/§5a).

Run from the repo root:
    python3 skills/_common/test_project_layout.py
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

from _common import project_layout as pl  # noqa: E402


def _write_scaffold(project_dir: Path, payload) -> None:
    """Write scaffold.json. `payload` is a dict (JSON-dumped) or a raw string
    (written verbatim, for the unparseable-JSON case)."""
    p = project_dir / "scaffold.json"
    if isinstance(payload, str):
        p.write_text(payload, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload), encoding="utf-8")


class DocsRootResolveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_absent_scaffold_defaults_to_docs(self):
        self.assertEqual(pl.docs_root(self.tmp), "docs")

    def test_scaffold_without_layout_defaults_to_docs(self):
        _write_scaffold(self.tmp, {"version": "1.0"})
        self.assertEqual(pl.docs_root(self.tmp), "docs")

    def test_layout_without_docs_root_defaults_to_docs(self):
        _write_scaffold(self.tmp, {"layout": {}})
        self.assertEqual(pl.docs_root(self.tmp), "docs")

    def test_empty_string_docs_root_defaults_to_docs(self):
        _write_scaffold(self.tmp, {"layout": {"docs_root": ""}})
        self.assertEqual(pl.docs_root(self.tmp), "docs")

    def test_dot_docs_root_returned_as_is(self):
        _write_scaffold(self.tmp, {"layout": {"docs_root": "."}})
        self.assertEqual(pl.docs_root(self.tmp), ".")

    def test_explicit_docs(self):
        _write_scaffold(self.tmp, {"layout": {"docs_root": "docs"}})
        self.assertEqual(pl.docs_root(self.tmp), "docs")

    def test_nested_non_default(self):
        _write_scaffold(self.tmp, {"layout": {"docs_root": "docs/internal"}})
        self.assertEqual(pl.docs_root(self.tmp), "docs/internal")

    def test_foo_dotdot_normalizes_to_dot(self):
        # "foo/.." normalizes to "." (project_dir itself) — accepted.
        _write_scaffold(self.tmp, {"layout": {"docs_root": "foo/.."}})
        self.assertEqual(pl.docs_root(self.tmp), ".")


class EscapeRejectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _set(self, value):
        _write_scaffold(self.tmp, {"layout": {"docs_root": value}})

    def test_absolute_path_rejected(self):
        self._set("/etc")
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_parent_escape_rejected(self):
        self._set("../docs")
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_sneaky_escape_rejected(self):
        self._set("a/../../x")
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_layout_error_is_value_error(self):
        self.assertTrue(issubclass(pl.LayoutError, ValueError))


class MalformedConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_unparseable_json_raises(self):
        _write_scaffold(self.tmp, "{ not valid json")
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_layout_wrong_type_raises(self):
        _write_scaffold(self.tmp, {"layout": "nope"})
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_docs_root_wrong_type_raises(self):
        _write_scaffold(self.tmp, {"layout": {"docs_root": 5}})
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_top_level_not_object_raises(self):
        _write_scaffold(self.tmp, "[1, 2, 3]")
        with self.assertRaises(pl.LayoutError):
            pl.docs_root(self.tmp)

    def test_escape_vs_malformed_same_type_distinct_message(self):
        # Same type (LayoutError), distinguishable by message only (AC4).
        _write_scaffold(self.tmp, {"layout": {"docs_root": "../escape"}})
        with self.assertRaises(pl.LayoutError) as esc:
            pl.docs_root(self.tmp)
        _write_scaffold(self.tmp, {"layout": {"docs_root": 5}})
        with self.assertRaises(pl.LayoutError) as mal:
            pl.docs_root(self.tmp)
        self.assertNotEqual(str(esc.exception), str(mal.exception))


class DerivedPathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _set(self, value):
        _write_scaffold(self.tmp, {"layout": {"docs_root": value}})

    def test_default_layout_matches_legacy(self):
        # No scaffold.json → default "docs". Identical to today's
        # project_dir / "docs" / <suffix>.
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "docs" / "specs")
        self.assertEqual(pl.decisions_dir(self.tmp), self.tmp / "docs" / "decisions")
        self.assertEqual(pl.workflow_path(self.tmp), self.tmp / "docs" / "workflow.md")
        self.assertEqual(pl.architecture_path(self.tmp), self.tmp / "docs" / "architecture.md")
        self.assertEqual(pl.memory_dir(self.tmp), self.tmp / "docs" / "memory")
        self.assertEqual(
            pl.refinement_todo_path(self.tmp),
            self.tmp / "docs" / "refinement-todo.md",
        )

    def test_dot_layout_collapses(self):
        self._set(".")
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "specs")
        self.assertEqual(pl.decisions_dir(self.tmp), self.tmp / "decisions")
        self.assertEqual(pl.workflow_path(self.tmp), self.tmp / "workflow.md")
        self.assertEqual(pl.architecture_path(self.tmp), self.tmp / "architecture.md")
        self.assertEqual(pl.memory_dir(self.tmp), self.tmp / "memory")
        self.assertEqual(pl.refinement_todo_path(self.tmp), self.tmp / "refinement-todo.md")
        # No "./" segment / no doubled separators.
        self.assertNotIn("/./", str(pl.specs_dir(self.tmp)))

    def test_nested_layout(self):
        self._set("docs/internal")
        self.assertEqual(pl.specs_dir(self.tmp), self.tmp / "docs" / "internal" / "specs")


class ProjectRootForTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    @staticmethod
    def _boom(_p):
        raise AssertionError("fallback should not have been called")

    def test_sentinel_at_self(self):
        (self.tmp / "scaffold.json").write_text("{}")
        self.assertEqual(
            pl.project_root_for(self.tmp, fallback=self._boom), self.tmp
        )

    def test_sentinel_at_ancestor(self):
        (self.tmp / "scaffold.json").write_text("{}")
        deep = self.tmp / "specs" / "001-x"
        deep.mkdir(parents=True)
        spec_md = deep / "spec.md"
        spec_md.write_text("# spec")
        self.assertEqual(
            pl.project_root_for(spec_md, fallback=self._boom), self.tmp
        )

    def test_no_sentinel_calls_fallback_with_path(self):
        target = self.tmp / "a" / "b" / "c.md"
        target.parent.mkdir(parents=True)
        target.write_text("x")
        seen = {}

        def fb(p):
            seen["p"] = p
            return self.tmp / "FALLBACK"

        result = pl.project_root_for(target, fallback=fb)
        self.assertEqual(result, self.tmp / "FALLBACK")
        self.assertEqual(Path(seen["p"]), target)

    def test_fallback_exception_propagates(self):
        target = self.tmp / "x.md"
        target.write_text("x")

        def fb(_p):
            raise RuntimeError("legacy boom")

        with self.assertRaises(RuntimeError):
            pl.project_root_for(target, fallback=fb)

    def test_nested_subproject_wins_over_ancestor(self):
        # Enclosing repo: has .git AND a docs/ tree. Subproject (docs_root="."):
        # carries the sentinel. A spec at <sub>/specs/<dir>/spec.md must resolve
        # to the subproject, never the enclosing repo (cross-project-bleed
        # guard). The resolver is depth-agnostic; the subproject sits one level
        # under the repo here so the legacy parents[3] arithmetic resolves
        # EXACTLY to the enclosing repo — the precise trap §5a describes.
        repo = self.tmp / "monorepo"
        (repo / ".git").mkdir(parents=True)
        (repo / "docs").mkdir()
        (repo / "docs" / "architecture.md").write_text("# repo arch")
        sub = repo / "cwv"
        sub.mkdir(parents=True)
        (sub / "scaffold.json").write_text(json.dumps({"layout": {"docs_root": "."}}))
        spec_md = sub / "specs" / "001-x" / "spec.md"
        spec_md.parent.mkdir(parents=True)
        spec_md.write_text("# spec")

        # The legacy depth-arithmetic fallback returns parents[3] (= the
        # enclosing repo) — the wrong root. Assert the sentinel walk overrides it.
        def legacy(p):
            return Path(p).resolve().parents[3]

        self.assertEqual(legacy(spec_md), repo)  # confirm the trap exists
        self.assertEqual(
            pl.project_root_for(spec_md, fallback=legacy), sub
        )


class KnownLimitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-layout-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_symlink_escape_not_caught_documented_limit(self):
        # docs_root that lexically stays inside project_dir but is a symlink
        # pointing outside is NOT caught (lexical normalization). This pins the
        # documented limitation (ADR-0033 §3 known-limit), not a feature.
        outside = Path(tempfile.mkdtemp(prefix="jig-outside-")).resolve()
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        link = self.tmp / "docs"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unsupported on this platform")
        _write_scaffold(self.tmp, {"layout": {"docs_root": "docs"}})
        # Accepted (no raise) — the lexical validator cannot see the symlink.
        self.assertEqual(pl.docs_root(self.tmp), "docs")


class ImportDisciplineTests(unittest.TestCase):
    def test_module_imports_only_stdlib_or_common(self):
        src = Path(pl.__file__).read_text()
        tree = ast.parse(src)
        offenders = []
        stdlib_ok = {
            "json", "os", "sys", "pathlib", "typing", "__future__",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in stdlib_ok and top != "_common":
                        offenders.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                top = (node.module or "").split(".")[0]
                if node.level == 0 and top and top not in stdlib_ok and top != "_common":
                    offenders.append(node.module)
        self.assertEqual(offenders, [], f"non-leaf imports: {offenders}")


if __name__ == "__main__":
    unittest.main()
