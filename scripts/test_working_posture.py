"""Spec 110-01 — the collaborative Working-posture boundary is present on the
orchestrator-facing surfaces (scaffold primer templates + the review-heavy SKILL
bodies). Lexical-presence guard: removing the statement turns these red.

ADR-0055 (adversarial-register quarantine): adversarial review is a named,
bounded operation; outside it the default posture is collaborative. This test
guards the *counter-anchor* surfaces (110-01); it does not assert behaviour."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _norm(text: str) -> str:
    """Strip blockquote markers and collapse all whitespace, so lexical checks
    survive Markdown line-wrapping."""
    return " ".join(re.sub(r"(?m)^\s*>\s?", " ", text).split())

TEMPLATES = [
    REPO_ROOT / "templates" / "CLAUDE.md.template",
    REPO_ROOT / "templates" / "AGENTS.md.template",
]
REVIEW_HEAVY_SKILLS = [
    REPO_ROOT / "skills" / "independent-review" / "SKILL.md",
    REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md",
    REPO_ROOT / "skills" / "bug-fix" / "SKILL.md",
]


class WorkingPostureTemplateTests(unittest.TestCase):
    """AC2: the scaffold primer templates carry a Working-posture section."""

    def test_templates_carry_working_posture_boundary(self):
        for tpl in TEMPLATES:
            text = tpl.read_text(encoding="utf-8")
            with self.subTest(template=tpl.name):
                self.assertIn("## Working posture", text)
                self.assertIn("named, bounded operation", text)
                self.assertRegex(text, r"(?i)collaborative and solution-forward")
                # posture, not a new gate — enforcement stays in tooling
                self.assertRegex(text, r"(?i)enforcement lives in tooling")


class WorkingPostureSkillPointerTests(unittest.TestCase):
    """AC3: the review-heavy SKILL bodies point to the same boundary + ADR."""

    def test_review_heavy_skills_point_to_boundary(self):
        for skill in REVIEW_HEAVY_SKILLS:
            norm = _norm(skill.read_text(encoding="utf-8"))
            with self.subTest(skill=skill.parent.name):
                self.assertRegex(norm, r"(?i)working posture")
                self.assertIn(
                    "](../../docs/decisions/adr-0055-", norm.lower()
                )
                self.assertIn("named, bounded operation", norm)
                self.assertIn(
                    "adversarial stance into ordinary conversation", norm
                )


if __name__ == "__main__":
    unittest.main()
