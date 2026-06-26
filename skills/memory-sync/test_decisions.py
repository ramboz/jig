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


if __name__ == "__main__":
    unittest.main()
