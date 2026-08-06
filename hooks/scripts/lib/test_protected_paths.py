"""AC3 tests for slice 106-01 — protected-path soft nudge (ADR-0051).

Run from repo root:
    python3 -m unittest hooks/scripts/lib/test_protected_paths.py
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
if str(HERE) not in os.sys.path:
    os.sys.path.insert(0, str(HERE))

import protected_paths  # noqa: E402


class ProtectedPathsHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "scaffold.json").write_text(
            json.dumps({
                "protected_paths": [
                    "docs/conventions.md",
                    "docs/decisions/**",
                    ".github/workflows/**",
                    "CODEOWNERS",
                ],
            }),
            encoding="utf-8",
        )
        os.environ.pop("JIG_PROTECTED_PATHS", None)

    def tearDown(self):
        self.tmp.cleanup()

    def _payload(self, file_path, tool="Edit"):
        return {"tool_name": tool, "tool_input": {"file_path": file_path}}

    # --- read_protected_paths -------------------------------------------
    def test_read_returns_list(self):
        self.assertIn(
            "docs/conventions.md", protected_paths.read_protected_paths(self.root)
        )

    def test_read_missing_scaffold_json_returns_empty(self):
        empty = Path(tempfile.mkdtemp())
        self.assertEqual(protected_paths.read_protected_paths(empty), [])

    def test_read_broken_scaffold_json_returns_empty(self):
        (self.root / "scaffold.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(protected_paths.read_protected_paths(self.root), [])

    # --- match_protected_path -------------------------------------------
    def test_match_hits_protected_edit(self):
        self.assertEqual(
            protected_paths.match_protected_path(
                self.root, "docs/decisions/adr-0051.md"
            ),
            "docs/decisions/**",
        )

    def test_match_misses_non_protected(self):
        self.assertIsNone(
            protected_paths.match_protected_path(self.root, "src/app.py")
        )

    def test_match_absolute_path(self):
        abs_path = str(self.root / "CODEOWNERS")
        self.assertEqual(
            protected_paths.match_protected_path(self.root, abs_path), "CODEOWNERS"
        )

    # --- evaluate --------------------------------------------------------
    def test_evaluate_nudges_in_boundary(self):
        nudge = protected_paths.evaluate(
            self._payload("docs/conventions.md"), self.root
        )
        self.assertIsNotNone(nudge)
        self.assertIn("governance-protected", nudge)
        self.assertIn("102", nudge)

    def test_evaluate_silent_out_of_boundary(self):
        self.assertIsNone(
            protected_paths.evaluate(self._payload("src/app.py"), self.root)
        )

    def test_evaluate_ignores_non_edit_tools(self):
        self.assertIsNone(
            protected_paths.evaluate(
                self._payload("docs/conventions.md", tool="Read"), self.root
            )
        )

    def test_optout_silences(self):
        with patch.dict(os.environ, {"JIG_PROTECTED_PATHS": "0"}, clear=False):
            self.assertIsNone(
                protected_paths.evaluate(
                    self._payload("docs/conventions.md"), self.root
                )
            )

    def test_fail_open_on_broken_scaffold(self):
        (self.root / "scaffold.json").write_text("{broken", encoding="utf-8")
        self.assertIsNone(
            protected_paths.evaluate(
                self._payload("docs/conventions.md"), self.root
            )
        )

    def test_fail_open_on_missing_scaffold(self):
        empty = Path(tempfile.mkdtemp())
        self.assertIsNone(
            protected_paths.evaluate(self._payload("docs/conventions.md"), empty)
        )


class GlobMatcherParityTests(unittest.TestCase):
    """Pin the hook's INLINE `**`-aware matcher in behavioral sync with
    `governance.path_matches_glob` (the source-of-truth). Hooks cannot import
    the skill module, so the matcher is duplicated by necessity — this guards
    the two copies against silent drift (craft/arch review, slice 106-01)."""

    def setUp(self):
        # governance.py lives in the scaffold-init skill dir; add it for import.
        gov_dir = HERE.parents[2] / "skills" / "scaffold-init"
        if str(gov_dir) not in os.sys.path:
            os.sys.path.insert(0, str(gov_dir))
        import governance  # noqa: E402
        self.governance = governance

    def test_matchers_agree_across_representative_cases(self):
        globs = list(self.governance.PROTECTED_PATHS) + [
            "a/*.py", "x/**", "top/**/leaf.json",
        ]
        paths = [
            "docs/conventions.md", "docs/decisions/adr-0051.md", "docs/decisions",
            "oracle.sh", "CODEOWNERS", "README.md", "src/app.py",
            ".github/workflows/jig-governance.yml", ".github/workflows",
            ".servo/evals/config.json", ".servo/config.json",  # top-level: no match
            "a/b.py", "a/b/c.py", "x", "x/y/z", "top/mid/leaf.json", "top/leaf.json",
            "./docs/conventions.md",
        ]
        for g in globs:
            for p in paths:
                self.assertEqual(
                    protected_paths._path_matches_glob(p, g),
                    self.governance.path_matches_glob(p, g),
                    msg=f"matcher drift for path={p!r} glob={g!r}",
                )

    def test_servo_subdir_edge_is_intentional(self):
        # `.servo/**/config.json` matches a config under a subdir, not top-level.
        self.assertTrue(
            protected_paths._path_matches_glob(
                ".servo/evals/config.json", ".servo/**/config.json"))
        self.assertFalse(
            protected_paths._path_matches_glob(
                ".servo/config.json", ".servo/**/config.json"))

    def test_self_reference_paths_match(self):
        # The governance plane's own files are protected by construction.
        self.assertTrue(
            protected_paths._path_matches_glob(
                ".github/workflows/jig-governance.yml", ".github/workflows/**"))
        self.assertTrue(
            protected_paths._path_matches_glob("CODEOWNERS", "CODEOWNERS"))


if __name__ == "__main__":
    unittest.main()
