"""Tests for skills/_common/lexicon.py and skills/_common/lexicon.json.

Covers spec slice 065-01 — the shipped lexicon + project-glossary overlay
loader. Plain-`python3`-runnable like the other _common tests; uses tmp dirs
for fixtures. Stdlib-only.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lexicon  # noqa: E402

COMMON_DIR = Path(__file__).resolve().parent
LEXICON_JSON = COMMON_DIR / "lexicon.json"
LEXICON_PY = COMMON_DIR / "lexicon.py"


def _write_glossary(project_dir: Path, body: str) -> None:
    """Write `body` to <project_dir>/docs/memory/glossary.md."""
    gloss = project_dir / "docs" / "memory" / "glossary.md"
    gloss.parent.mkdir(parents=True, exist_ok=True)
    gloss.write_text(body)


class LexiconSchemaTests(unittest.TestCase):
    """AC1 — the shipped lexicon exists, valid JSON, required shape."""

    def setUp(self):
        self.data = json.loads(LEXICON_JSON.read_text())

    def test_lexicon_json_is_object_keyed_by_term(self):
        self.assertIsInstance(self.data, dict)
        self.assertGreater(len(self.data), 0, "lexicon.json is empty")

    def test_every_entry_has_short_and_plain(self):
        for term, entry in self.data.items():
            self.assertIsInstance(entry, dict, f"{term!r} entry is not an object")
            self.assertIn("short", entry, f"{term!r} missing required 'short'")
            self.assertIn("plain", entry, f"{term!r} missing required 'plain'")
            self.assertIsInstance(entry["short"], str)
            self.assertIsInstance(entry["plain"], str)
            self.assertTrue(entry["short"].strip(), f"{term!r} 'short' is blank")
            self.assertTrue(entry["plain"].strip(), f"{term!r} 'plain' is blank")

    def test_optional_fields_have_right_types(self):
        for term, entry in self.data.items():
            if "example" in entry:
                self.assertIsInstance(
                    entry["example"], str, f"{term!r} 'example' must be a string"
                )
            if "see_also" in entry:
                self.assertIsInstance(
                    entry["see_also"], list, f"{term!r} 'see_also' must be a list"
                )

    def test_see_also_keys_resolve(self):
        keys = set(self.data.keys())
        for term, entry in self.data.items():
            for ref in entry.get("see_also", []):
                self.assertIn(
                    ref, keys,
                    f"{term!r} see_also -> {ref!r} does not resolve to a key",
                )

    def test_seed_terms_present(self):
        # A representative sample the slice spec calls out explicitly.
        keys = set(self.data.keys())
        for expected in ("spidr", "adr", "vertical slice", "reconciliation",
                         "deviation log", "dor", "ac", "dod", "frontmatter"):
            self.assertIn(expected, keys, f"expected seed term {expected!r} missing")


class LexiconLoadOverlayTests(unittest.TestCase):
    """AC2 — load() merges shipped + project overlay, project wins."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-065-01-"))
        self.shipped = lexicon.load_shipped()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_shipped_only_when_no_glossary(self):
        # No docs/memory/glossary.md at all.
        merged = lexicon.load(self.tmp)
        self.assertEqual(merged, self.shipped)

    def test_project_overlay_overrides_shipped_term(self):
        # spidr is a shipped term; project redefines it.
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "## SPIDR\n\n"
            "In this project SPIDR means our custom splitting playbook.\n"
        ))
        merged = lexicon.load(self.tmp)
        self.assertIn("spidr", merged)
        self.assertIn("custom splitting playbook", merged["spidr"]["plain"])
        # Shipped wording must be gone for the overridden term.
        self.assertNotEqual(
            merged["spidr"]["plain"], self.shipped["spidr"]["plain"]
        )

    def test_compound_heading_overrides_not_duplicates(self):
        # Regression (065-01 arch review): a shipped seed key must equal the
        # _term_key() of jig's own canonical glossary heading, so a compound
        # multi-word heading OVERRIDES the shipped entry rather than adding a
        # parallel key. Guards the dogfood invariant that jig's committed
        # glossary idempotently overlays its lexicon.
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "## Tier 0 / Tier 1 / Tier 2\n\n"
            "Project-specific tier meaning.\n"
        ))
        merged = lexicon.load(self.tmp)
        self.assertIn("tier 0 / tier 1 / tier 2", merged)
        self.assertIn(
            "Project-specific tier meaning",
            merged["tier 0 / tier 1 / tier 2"]["plain"],
        )
        # No parallel key under the old compact spelling.
        self.assertNotIn("tier 0/1/2", merged)

    def test_project_only_term_is_added(self):
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "## Frobnicator\n\n"
            "Our internal widget pipeline.\n"
        ))
        merged = lexicon.load(self.tmp)
        self.assertIn("frobnicator", merged)
        self.assertIn("widget pipeline", merged["frobnicator"]["plain"])

    def test_shipped_term_survives_when_not_overridden(self):
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "## Frobnicator\n\n"
            "Our internal widget pipeline.\n"
        ))
        merged = lexicon.load(self.tmp)
        # An untouched shipped term keeps its shipped definition.
        self.assertEqual(merged["adr"], self.shipped["adr"])

    def test_h3_heading_is_ignored_no_false_override(self):
        # Negative: H3 (### ) must contribute NO override.
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "### SPIDR\n\n"
            "This H3 must NOT override the shipped definition.\n"
        ))
        merged = lexicon.load(self.tmp)
        self.assertEqual(merged["spidr"], self.shipped["spidr"])

    def test_first_paragraph_only_is_taken_as_definition(self):
        _write_glossary(self.tmp, (
            "# Glossary\n\n"
            "## Widget\n\n"
            "First paragraph is the definition.\n\n"
            "Second paragraph should be ignored.\n"
        ))
        merged = lexicon.load(self.tmp)
        self.assertIn("First paragraph is the definition.",
                      merged["widget"]["plain"])
        self.assertNotIn("Second paragraph", merged["widget"]["plain"])


class LexiconFailSoftTests(unittest.TestCase):
    """AC3 — missing / malformed project glossary is fail-soft."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-065-01-fs-"))
        self.shipped = lexicon.load_shipped()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_glossary_returns_shipped_unchanged(self):
        self.assertEqual(lexicon.load(self.tmp), self.shipped)

    def test_missing_project_dir_returns_shipped_unchanged(self):
        missing = self.tmp / "does-not-exist"
        self.assertEqual(lexicon.load(missing), self.shipped)

    def test_garbage_glossary_degrades_to_shipped_only(self):
        # No headings at all — unparseable as an overlay; must not raise.
        _write_glossary(self.tmp, "\x00\x01 not markdown at all >>>> \n#### ## #\n")
        try:
            merged = lexicon.load(self.tmp)
        except Exception as exc:  # noqa: BLE001 — the whole point is no raise
            self.fail(f"load() raised on garbage glossary: {exc!r}")
        # No H2 headings -> no overrides -> exactly the shipped lexicon.
        self.assertEqual(merged, self.shipped)

    def test_empty_glossary_returns_shipped_unchanged(self):
        _write_glossary(self.tmp, "")
        self.assertEqual(lexicon.load(self.tmp), self.shipped)


class LexiconHookSafeTests(unittest.TestCase):
    """AC4 — stdlib-only, importable from a `python3 -c` hook context."""

    def test_stdlib_only_no_third_party_imports(self):
        # Parse the source and assert every top-level import is stdlib.
        import ast

        src = LEXICON_PY.read_text()
        tree = ast.parse(src)
        stdlib_ok = {"json", "pathlib", "re", "os", "sys", "io", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.assertIn(root, stdlib_ok,
                                  f"non-stdlib import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    root = node.module.split(".")[0]
                    self.assertIn(root, stdlib_ok,
                                  f"non-stdlib import-from: {node.module}")

    def test_loadable_and_callable_like_a_hook(self):
        # A hook runs `python3 -c "..."` with an arbitrary CWD and no package
        # root. Emulate: spawn a subprocess from a foreign CWD that imports
        # lexicon by file path and calls load().
        tmp = Path(tempfile.mkdtemp(prefix="jig-065-01-hook-"))
        try:
            code = (
                "import importlib.util, sys, json\n"
                f"spec = importlib.util.spec_from_file_location('lex', {str(LEXICON_PY)!r})\n"
                "m = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(m)\n"
                f"d = m.load({str(tmp)!r})\n"
                "print(json.dumps(sorted(d)[:1]))\n"
            )
            r = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(tmp), capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0, f"hook-style call failed: {r.stderr}")
            self.assertTrue(r.stdout.strip(), "no output from hook-style call")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_by_file_path_resolves_shipped_json(self):
        # Loading the module by file path (not via sys.path) must still find
        # lexicon.json relative to __file__.
        spec = importlib.util.spec_from_file_location("lex_fp", str(LEXICON_PY))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        tmp = Path(tempfile.mkdtemp(prefix="jig-065-01-fp-"))
        try:
            d = mod.load(tmp)
            self.assertIn("adr", d)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class LexiconTravelsAsMachineryTests(unittest.TestCase):
    """AC5 — lexicon.json + lexicon.py live under skills/_common/ and are
    copied by the scaffold/migrate `_copy_skill_dir` (which mirrors every
    non-test file under a `_`-prefixed shared module verbatim)."""

    def test_files_live_in_common(self):
        self.assertTrue(LEXICON_JSON.is_file(), "lexicon.json missing in _common")
        self.assertTrue(LEXICON_PY.is_file(), "lexicon.py missing in _common")

    def test_copy_skill_dir_includes_lexicon_excludes_test(self):
        # Drive the real copy routine used by scaffold-init / copy-machinery
        # for `_`-prefixed shared modules, and confirm the lexicon assets land
        # in the copied set while the test file does not.
        repo_root = COMMON_DIR.parent.parent  # skills/_common -> repo root
        sys.path.insert(0, str(repo_root / "skills" / "scaffold-init"))
        sys.path.insert(0, str(repo_root / "skills"))
        from scaffold import _copy_skill_dir

        dst = Path(tempfile.mkdtemp(prefix="jig-065-01-machinery-")) / "_common"
        try:
            _copy_skill_dir(COMMON_DIR, dst)
            self.assertTrue((dst / "lexicon.json").is_file(),
                            "lexicon.json not copied as machinery")
            self.assertTrue((dst / "lexicon.py").is_file(),
                            "lexicon.py not copied as machinery")
            # test files are excluded from the copied set
            self.assertFalse((dst / "test_lexicon.py").exists(),
                             "test_lexicon.py should not travel as machinery")
        finally:
            shutil.rmtree(dst.parent, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
