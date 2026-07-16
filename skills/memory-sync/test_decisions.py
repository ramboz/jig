"""
AC verification tests for slice 083-05 (routing rubric + decisions.py
add-lightweight) and the single-source drift guard co-owned with 083-06.

Run from the repo root:
    python3 skills/memory-sync/test_decisions.py
"""

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISIONS_PY = REPO_ROOT / "skills" / "memory-sync" / "decisions.py"
TEMPLATE = (
    REPO_ROOT / "templates" / "docs" / "decisions"
    / "lightweight-decisions.md.template"
)
TODAY = date.today().isoformat()

# The four consumer sites that must quote the canonical ADR-trigger sentence
# verbatim, plus ADR-0031 (the human-readable canonical source).
RUBRIC = REPO_ROOT / "docs" / "decisions" / "lightweight-decisions.md"
WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
MEMORY_SYNC_SKILL = REPO_ROOT / "skills" / "memory-sync" / "SKILL.md"
ADR_0031 = (
    REPO_ROOT / "docs" / "decisions"
    / "adr-0031-load-bearing-decision-adr-trigger.md"
)

_SEED = """# Lightweight Decisions

Some intro prose.

## Entries

> _Illustrative only._

### 2026-01-15 — Example entry

**Decision:** something.
"""


def _import_decisions():
    spec = importlib.util.spec_from_file_location("decisions", DECISIONS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


decisions = _import_decisions()


class AddLightweightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        target = decisions.lightweight_path(self.project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_SEED, encoding="utf-8")
        self.target = target

    def tearDown(self):
        self._tmp.cleanup()

    # AC1 — appends a well-formed entry
    def test_append_wellformed_entry(self):
        appended = decisions.add_lightweight(
            self.project, "Button copy", "Use 'Get started'",
            "User testing", "Onboarding CTA", commit="abc123", date="2026-06-26")
        self.assertTrue(appended)
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("### 2026-06-26 — Button copy", text)
        self.assertIn("**Decision:** Use 'Get started'", text)
        self.assertIn("**Context:** User testing", text)
        self.assertIn("**Scope:** Onboarding CTA", text)
        self.assertIn("**Commit:** abc123", text)
        # the seeded example entry is preserved
        self.assertIn("### 2026-01-15 — Example entry", text)

    def test_date_defaults_to_today(self):
        decisions.add_lightweight(
            self.project, "No date given", "decided", "ctx", "scope")
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("### %s — No date given" % TODAY, text)

    def test_commit_optional(self):
        decisions.add_lightweight(
            self.project, "No commit", "decided", "ctx", "scope",
            date="2026-06-26")
        text = self.target.read_text(encoding="utf-8")
        self.assertNotIn("**Commit:**", text.split("No commit", 1)[1])

    # AC2 — idempotent
    def test_idempotent_same_title_date(self):
        first = decisions.add_lightweight(
            self.project, "Dupe", "d", "c", "s", date="2026-06-26")
        before = self.target.read_text(encoding="utf-8")
        second = decisions.add_lightweight(
            self.project, "  dupe  ", "d2", "c2", "s2", date="2026-06-26")
        after = self.target.read_text(encoding="utf-8")
        self.assertTrue(first)
        self.assertFalse(second)  # normalized title match → no-op
        self.assertEqual(before, after)

    def test_same_title_different_date_appends(self):
        decisions.add_lightweight(
            self.project, "Recur", "d", "c", "s", date="2026-06-26")
        appended = decisions.add_lightweight(
            self.project, "Recur", "d", "c", "s", date="2026-06-27")
        self.assertTrue(appended)

    # AC1/AC2 — malformed input
    def test_missing_title_raises(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "", "d", "c", "s")

    def test_missing_decision_raises(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "", "c", "s")

    def test_no_file_raises(self):
        empty = Path(tempfile.mkdtemp())
        try:
            with self.assertRaises(FileNotFoundError):
                decisions.add_lightweight(empty, "t", "d", "c", "s")
        finally:
            import shutil
            shutil.rmtree(empty)

    def test_missing_entries_heading_raises(self):
        self.target.write_text("# Lightweight Decisions\n\nNo entries heading.\n",
                               encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "d", "c", "s")


class SingleSourceDriftTests(unittest.TestCase):
    """083-05 AC4 / 083-06 AC3 — the canonical ADR_TRIGGER sentence must appear
    verbatim in all four consumer sites (and in ADR-0031's prose)."""

    def _assert_contains_trigger(self, path: Path):
        self.assertTrue(path.exists(), "missing consumer site: %s" % path)
        self.assertIn(
            decisions.ADR_TRIGGER, path.read_text(encoding="utf-8"),
            "canonical ADR_TRIGGER sentence not found verbatim in %s" % path.name)

    def test_rubric_site(self):
        self._assert_contains_trigger(RUBRIC)

    def test_workflow_reconcile_checklist_site(self):
        self._assert_contains_trigger(WORKFLOW_MD)

    def test_spec_workflow_reconcile_checklist_site(self):
        self._assert_contains_trigger(SPEC_WORKFLOW_SKILL)

    def test_memory_sync_prompt_site(self):
        self._assert_contains_trigger(MEMORY_SYNC_SKILL)

    def test_adr0031_canonical_source(self):
        self._assert_contains_trigger(ADR_0031)


class EntriesPlaceholderTests(unittest.TestCase):
    """The template seeds `## Entries` with a "_No entries yet._" placeholder,
    and `add_lightweight` appends at end-of-file without clearing it — so the
    moment a real decision is recorded, the file says "No entries yet"
    directly above the entries it lists. Affects every jig project, since
    scaffold-init seeds this same template.

    These start from the shipped template verbatim, which is exactly what a
    scaffolded project's file looks like before its first entry.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(TEMPLATE.read_text(encoding="utf-8"),
                               encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _text(self) -> str:
        return self.target.read_text(encoding="utf-8")

    def test_placeholder_is_dropped_when_the_first_entry_lands(self):
        decisions.add_lightweight(self.project, "Knob fill", "Use var(--surface)",
                                  "mockup hex rejected", "Home settings",
                                  date="2026-07-16")
        text = self._text()
        self.assertNotIn("_No entries yet.", text)
        self.assertIn("### 2026-07-16 — Knob fill", text)

    def test_entries_heading_survives_the_drop(self):
        """Strip the placeholder, not the section it sits in."""
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        self.assertEqual(self._text().count("## Entries"), 1)

    def test_placeholder_kept_while_the_file_has_no_entries(self):
        """It is useful copy for an empty file — the defect is only that it
        outlives the first entry. A no-op append must not strip it either."""
        self.assertIn("_No entries yet.", self._text())
        decisions.add_lightweight(self.project, "Dupe", "d", "c", "s",
                                  date="2026-07-16")
        before = self._text()
        appended = decisions.add_lightweight(self.project, "Dupe", "d2", "c2",
                                             "s2", date="2026-07-16")
        self.assertFalse(appended)
        self.assertEqual(self._text(), before, "no-op must not rewrite")

    def test_second_entry_appends_normally(self):
        decisions.add_lightweight(self.project, "One", "d", "c", "s",
                                  date="2026-07-16")
        decisions.add_lightweight(self.project, "Two", "d", "c", "s",
                                  date="2026-07-17")
        text = self._text()
        self.assertIn("### 2026-07-16 — One", text)
        self.assertIn("### 2026-07-17 — Two", text)
        self.assertNotIn("_No entries yet.", text)
        self.assertEqual(text.count("## Entries"), 1)

    def test_template_fence_example_heading_survives(self):
        """`_existing_keys` deliberately scans every `### ` heading, including
        the `### [Date] — [Short title]` line inside the `## Template` fence.
        Stripping the placeholder must not disturb it."""
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        self.assertIn("### [Date] — [Short title]", self._text())

    def test_unrelated_italics_are_not_stripped(self):
        """Only the placeholder goes — not any italic line that happens to sit
        under `## Entries` (e.g. a project's own illustrative note)."""
        self.target.write_text(_SEED, encoding="utf-8")
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        text = self._text()
        self.assertIn("> _Illustrative only._", text)
        self.assertIn("### 2026-01-15 — Example entry", text)

    def test_template_still_ships_the_placeholder_we_strip(self):
        """Drift guard: the matcher keys off the template's own wording. If the
        template's copy is reworded, the strip silently stops working and the
        defect returns with no test failing anywhere else."""
        self.assertRegex(TEMPLATE.read_text(encoding="utf-8"),
                         decisions._ENTRIES_PLACEHOLDER_RE)


if __name__ == "__main__":
    unittest.main()
