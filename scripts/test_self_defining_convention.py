"""
Docs-lint for the self-defining-vocabulary authoring convention (spec 065-04).

The convention is jig's "stop the dense-jargon pile from growing" rule: when
authoring a spec/slice, expand each acronym on first use and link the term to
the glossary/lexicon. It is soft, forward-only, and explicitly NOT a gate
(clarify Q4). This test pins:

  AC1 — jig's own `docs/workflow.md` carries the "Self-defining vocabulary"
        section (dogfood), with its load-bearing phrasing.
  AC2(a) — the slice template `templates/docs/specs/slice-template.md` carries
        the one-line authoring reminder pointing at the convention + glossary.
        (AC2(b) — the workflow.py renderers — is pinned in
        skills/spec-workflow/test_workflow.py::SelfDefiningReminderInRenderersTests.)
  AC4 — the convention text states the soft / forward-only / no-gate intent,
        and NO lint/gate enforcing undefined-acronym blocking was added.

The managed-block FLOW (AC3 — injection into a project's docs/workflow.md by
scaffold() + copy_machinery()) is pinned in skills/scaffold-init/test_scaffold.py
and skills/migrate/test_migrate.py, next to the .gitignore-floor tests it mirrors.

Mirrors the existing doc-presence tests (e.g. test_context_cost_discipline.py).

Run:
    python3 -m unittest scripts.test_self_defining_convention
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / "docs" / "workflow.md"
SLICE_TEMPLATE = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"

HEADING = "Self-defining vocabulary"
BLOCK_BEGIN = "<!-- >>> jig self-defining-vocabulary >>> -->"
BLOCK_END = "<!-- <<< jig self-defining-vocabulary <<< -->"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class WorkflowSectionExists(unittest.TestCase):
    """AC1 — docs/workflow.md gains the 'Self-defining vocabulary' section."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(WORKFLOW)

    def test_section_heading_present(self):
        self.assertRegex(
            self.text, rf"(?m)^#+\s+{HEADING}\b",
            "docs/workflow.md must have a 'Self-defining vocabulary' heading "
            "(spec 065-04 AC1)",
        )

    def test_managed_block_markers_present(self):
        # jig dogfoods the exact managed block the helper writes.
        self.assertIn(BLOCK_BEGIN, self.text)
        self.assertIn(BLOCK_END, self.text)

    def test_states_expand_and_link_rule(self):
        body = self.text.lower()
        self.assertIn("expand each acronym on first use", body)
        self.assertIn("glossary", body)

    def test_points_at_explain_escape_hatch(self):
        self.assertIn("/jig:explain", self.text)


class SoftForwardOnlyNoGate(unittest.TestCase):
    """AC4 — the convention is soft, forward-only, and NOT a gate."""

    @classmethod
    def setUpClass(cls):
        cls.body = _read(WORKFLOW).lower()

    def test_states_not_a_gate(self):
        self.assertIn("not a gate", self.body)

    def test_states_nothing_blocks_a_transition(self):
        self.assertTrue(
            "nothing lints or blocks a transition" in self.body,
            "the convention must state that nothing lints/blocks a transition "
            "on an undefined acronym (clarify Q4)",
        )

    def test_states_forward_only(self):
        self.assertTrue(
            "forward-only" in self.body or "does not retrofit" in self.body
            or "not** retrofit" in self.body,
            "the convention must state it is forward-only (existing specs "
            "untouched)",
        )


class SliceTemplateReminder(unittest.TestCase):
    """AC2(a) — the slice template carries the authoring reminder."""

    @classmethod
    def setUpClass(cls):
        cls.text = _read(SLICE_TEMPLATE)

    def test_reminder_present(self):
        low = self.text.lower()
        self.assertIn("jig self-defining vocabulary", low)
        self.assertIn("expand each acronym on", low)
        self.assertIn("glossary.md", low)

    def test_reminder_is_a_comment_not_body(self):
        # The reminder is an HTML comment so it never renders into the authored
        # slice body — it nudges the author, it isn't content.
        self.assertRegex(
            self.text,
            r"<!--[^>]*self-defining vocabulary",
            "the reminder must be an HTML comment, not rendered body text",
        )


class DogfoodBlockMatchesHelper(unittest.TestCase):
    """Drift guard (arch-pass nit; 050 people.md byte-identity precedent):
    jig's own docs/workflow.md hand-carries the managed block, but the single
    source of truth is `_render_self_defining_block()`. Assert the dogfooded
    block region is byte-identical to the helper's render, so the two cannot
    silently diverge (helper edited, dogfood copy not — or vice versa)."""

    def test_dogfood_block_is_byte_identical_to_render(self):
        sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
        import importlib
        scaffold = importlib.import_module("scaffold")
        rendered = scaffold._render_self_defining_block().rstrip("\n")

        doc = _read(WORKFLOW)
        begin = doc.find(BLOCK_BEGIN)
        end = doc.find(BLOCK_END)
        self.assertNotEqual(begin, -1, "docs/workflow.md missing block begin marker")
        self.assertNotEqual(end, -1, "docs/workflow.md missing block end marker")
        region = doc[begin:end + len(BLOCK_END)]
        self.assertEqual(
            region, rendered,
            "docs/workflow.md's dogfooded block has drifted from "
            "_render_self_defining_block(); regenerate it via "
            "_ensure_self_defining_convention_block (single source of truth)",
        )


if __name__ == "__main__":
    unittest.main()
