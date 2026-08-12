"""Spec 110 (ADR-0055, adversarial-register quarantine) — lexical-presence guards
for the orchestrator-facing collaborative-posture surfaces. Removing a guarded
statement turns these red; none asserts behaviour.

- 110-01: the Working-posture boundary on the scaffold primer templates + the
  review-heavy SKILL bodies (adversarial review is a named, bounded operation;
  default collaborative).
- 110-02: the corpus-reconcile disposition guidance in docs/workflow.md, and the
  spec-102 amendment brake left provably unchanged.
- 110-03: refusals in the review-heavy SKILL bodies stay tool-attributed (no
  agent-owned refusal narration) and the invoke-the-gate imperative survives."""

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
        """AC1/AC2: no orchestrator-read prose casts the AGENT (or, third-person,
        the reviewer/orchestrator) as the one who refuses to advance work — that
        register belongs on the tooling."""
        # "you refuse", "you must refuse", "the reviewer refuses to advance", …
        agent_refusal = re.compile(
            r"(?i)\b(you|the (agent|orchestrator|reviewer))\b[^.]{0,40}?"
            r"\b(refuses?|rejects?|blocks?)\b[^.]{0,20}?"
            r"\b(advance|advancing|proceed|transition|the move)\b"
        )
        for skill in REVIEW_HEAVY_SKILLS:
            norm = _norm(skill.read_text(encoding="utf-8"))
            with self.subTest(skill=skill.parent.name):
                self.assertNotRegex(norm, agent_refusal)

    def test_invoke_the_gate_imperative_preserved(self):
        """AC4 (coarse guard). Gates are invocation-conditional (an un-invoked
        gate never fires), so each review-heavy body must keep at least one
        concrete helper INVOCATION example — the `${CLAUDE_PLUGIN_ROOT}/skills/.../X.py`
        form appears only in runnable command examples, never in refusal
        *narration* ("the gate refuses"). This guards that the bodies keep their
        runnable-command register at all; it does NOT single out the
        gate-specific `transition`/`bug.py` imperative (AC4 itself concedes the
        suite can't verify invocation — that stays an inspection check)."""
        invocation = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/\S+?\.py")
        for skill in REVIEW_HEAVY_SKILLS:
            text = skill.read_text(encoding="utf-8")
            with self.subTest(skill=skill.parent.name):
                self.assertRegex(text, invocation)


if __name__ == "__main__":
    unittest.main()
