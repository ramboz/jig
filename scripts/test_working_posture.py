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


class CorpusReconcileGuidanceTests(unittest.TestCase):
    """Spec 110-02 — the corpus-reconcile disposition guidance is present in
    docs/workflow.md, and the spec 102 amendment brake is provably NOT softened."""

    WORKFLOW = REPO_ROOT / "docs" / "workflow.md"
    SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"

    def test_workflow_carries_reconcile_not_refuse_guidance(self):
        norm = _norm(self.WORKFLOW.read_text(encoding="utf-8"))
        # disposition, not tone: context-to-reconcile-against, not ammunition
        self.assertIn("reconcile against", norm.lower())
        self.assertRegex(norm, r"(?i)not ammunition to")
        # the named failure mode: reconcile-then-block
        self.assertRegex(norm, r"(?i)reconcile-then-block")
        # the hard exception is explicit
        self.assertRegex(norm, r"(?i)spec 102 amendment guardrail stays hard")

    def test_spec_102_amend_brake_lead_unchanged(self):
        """AC2/AC4: the prose-only spec-102 brake keeps its hard 'stop' lead —
        this slice must not soften it (A2)."""
        norm = _norm(self.SPEC_WORKFLOW_SKILL.read_text(encoding="utf-8"))
        self.assertRegex(norm, r"(?i)surface the conflict and\s+stop")
        # the load-bearing clauses remain
        self.assertRegex(norm, r"(?i)explicit owner approval")
        self.assertRegex(norm, r"(?i)never write the resolution in the same turn")


class ToolOwnedRefusalTests(unittest.TestCase):
    """Spec 110-03 — the review-heavy SKILL bodies keep refusals attributed to
    the tooling (not the agent), and preserve the invoke-the-gate obligation.

    The A2 classification found the bodies already tool-attribute their refusals
    (`the gate refuses`, `workflow.py transition refuses`, `the → FIXING gate
    refuses`); this guard prevents a regression where a future edit re-narrates a
    refusal as the *agent's* job or drops the run-the-helper imperative."""

    def test_no_agent_owned_refusal_narration(self):
        """AC1/AC2: no orchestrator-read prose casts the AGENT as the refuser."""
        for skill in REVIEW_HEAVY_SKILLS:
            norm = _norm(skill.read_text(encoding="utf-8"))
            with self.subTest(skill=skill.parent.name):
                # the agent must not be told it personally refuses/blocks advances
                self.assertNotRegex(
                    norm,
                    r"(?i)you (refuse|must not advance|block the|reject the)"
                    r"\s+(to )?(advance|transition|proceed)",
                )

    def test_invoke_the_gate_imperative_preserved(self):
        """AC4: the run-the-helper obligation survives (gates are
        invocation-conditional — an un-invoked gate never fires)."""
        for skill in REVIEW_HEAVY_SKILLS:
            text = skill.read_text(encoding="utf-8")
            with self.subTest(skill=skill.parent.name):
                # each review-heavy body still tells the agent to run a helper
                self.assertRegex(
                    text, r"(?i)(workflow|bug|review)\.py|run[- ]tests|status-board"
                )

    def test_posture_pointer_present(self):
        """110-01 consistency: the collaborative posture pointer stays at the top
        of each review-heavy body (110-03's tone rests on it)."""
        for skill in REVIEW_HEAVY_SKILLS:
            norm = _norm(skill.read_text(encoding="utf-8"))
            with self.subTest(skill=skill.parent.name):
                self.assertRegex(norm, r"(?i)working posture")


if __name__ == "__main__":
    unittest.main()
