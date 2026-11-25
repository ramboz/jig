"""Spec 124 / ADR-0069: the docs put the owner's hands-on check in the
review batch, before reconciliation.

Run from the repo root:
    python3 skills/spec-workflow/test_owner_review_docs.py
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
SPEC_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
REVIEW_SKILL = REPO_ROOT / "skills" / "independent-review" / "SKILL.md"


def flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text())


class OwnerReviewPassDocsTests(unittest.TestCase):
    """124-01 AC9."""

    def check_common(self, text):
        self.assertIn("owner_review: true", text)
        self.assertIn("review.py owner-review", text)
        self.assertIn("ADR-0069", text)
        low = text.lower()
        # Where the owner's check belongs.
        self.assertIn("not in the dod after `reconciled`", low)
        self.assertIn("before reconciliation", low)
        # Deliberateness, not proof.
        self.assertIn("deliberateness", low)
        self.assertIn("not proof", low)
        # The agent asks and quotes.
        self.assertIn("never infer", low)
        # The re-ask rule.
        self.assertIn("ask again", low)

    def test_workflow_md(self):
        text = flat(WORKFLOW_MD)
        self.check_common(text)
        section = text[text.index("## Post-implementation review"):
                       text.index("## Reconciliation rules")]
        self.assertIn("Owner-review pass", section)
        self.assertIn("in parallel", section)
        self.assertIn("`owner-review`", section)
        self.assertIn("review_reopened_at", section)
        self.assertIn("stays `IN_PROGRESS`", section)

    def test_spec_workflow_skill(self):
        text = flat(SPEC_SKILL)
        self.check_common(text)
        section = text[text.index("### After implementation"):
                       text.index("### Reconciliation (REVIEWED → RECONCILED)")]
        self.assertIn("Owner-review pass", section)
        self.assertIn("workflow.py owner-review-needed", section)
        self.assertIn("in parallel", section)
        self.assertIn("--owner-quote", section)
        self.assertIn("review_reopened_at", section)

    def test_independent_review_skill(self):
        text = flat(REVIEW_SKILL)
        self.check_common(text)
        self.assertIn("### Owner-review", REVIEW_SKILL.read_text())
        for arg in ("--tried", "--surface", "--owner-quote"):
            self.assertIn(arg, text)
        self.assertIn("--non-interactive", text)


if __name__ == "__main__":
    unittest.main()
