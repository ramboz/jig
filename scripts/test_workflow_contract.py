"""
Guard tests for slice 045-04 (workflow-contract-alignment).

These pin the honesty fix that closes the framing-vs-enforcement gap
ADR-0014 identified: the user-facing process must match what slices
045-01..03 made the tooling actually enforce.

Specifically:

- `docs/workflow.md` must NOT claim a `Stop` hook blocks completion when
  reconciliation hasn't happened (the only `Stop` hook,
  `jig-task-capture.sh`, blocks nothing — ADR-0014 §6). It must instead
  name the deterministic `workflow.py transition` review-evidence gate as
  the real mechanism, and describe the evidence artifacts +
  `record-review` recording step.
- `agents/implementer.md` must NOT tell the implementer to set `REVIEWED`
  directly (the gate now refuses without recorded passing evidence — AC2),
  while keeping the load-bearing "Report the deliverable paths" phrase.
- The scaffold-generated `templates/docs/workflow.md.template` must
  inherit the same honest framing (AC4) — no false Stop-hook gate claim.

Run:
    python3 scripts/test_workflow_contract.py
    # or from repo root:
    python3 -m unittest scripts.test_workflow_contract
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
IMPLEMENTER = REPO_ROOT / "agents" / "implementer.md"
SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
INDEP_REVIEW_SKILL = REPO_ROOT / "skills" / "independent-review" / "SKILL.md"
WORKFLOW_TEMPLATE = REPO_ROOT / "templates" / "docs" / "workflow.md.template"

# The retired false claim: a Stop hook gating completion on reconciliation.
# Matches "Stop hook blocks completion" allowing intervening words/newlines
# (the original wrapped "The Stop\nhook blocks completion if reconciliation
# hasn't happened.").
STOP_HOOK_GATE_RE = re.compile(
    r"stop\s+hook\s+blocks\s+completion", re.IGNORECASE | re.DOTALL
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class WorkflowMdHonestHookClaim(unittest.TestCase):
    """AC3: workflow.md no longer claims a Stop hook blocks completion."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW_MD)

    def test_no_stop_hook_gate_claim(self) -> None:
        self.assertNotRegex(
            self.text, STOP_HOOK_GATE_RE,
            "docs/workflow.md must not claim a Stop hook blocks completion "
            "(the only Stop hook, jig-task-capture.sh, blocks nothing — "
            "ADR-0014 §6). Name the workflow.py transition gate instead.",
        )

    def test_names_the_transition_gate(self) -> None:
        lower = self.text.lower()
        self.assertIn(
            "transition", lower,
            "workflow.md must name workflow.py transition as the enforcement "
            "mechanism for the review/reconciliation evidence gate",
        )
        self.assertIn(
            "gate", lower,
            "workflow.md must describe the review-evidence gate",
        )


class WorkflowMdDescribesEnforcedPath(unittest.TestCase):
    """AC1: workflow.md describes the evidence artifacts + recording step."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW_MD)

    def test_mentions_record_review(self) -> None:
        self.assertIn(
            "record-review", self.text,
            "workflow.md must describe recording verdict evidence via "
            "review.py record-review (ADR-0014 §1)",
        )

    def test_mentions_evidence_artifacts(self) -> None:
        self.assertIn(
            "reviews/", self.text,
            "workflow.md must point at the docs/specs/NNN-slug/reviews/ "
            "evidence artifacts the gate checks",
        )

    def test_mentions_failed_review_recovery(self) -> None:
        # The recovery path (re-review → re-record → retry the gate) must be
        # described so a contributor knows how to clear a blocked transition.
        lower = self.text.lower()
        self.assertTrue(
            "re-record" in lower
            or "record again" in lower
            or "overwrite" in lower
            or "re-review" in lower,
            "workflow.md must describe failed-review recovery (address "
            "findings → re-review → record-review again → retry the gated "
            "transition)",
        )


class ImplementerStopsOverClaiming(unittest.TestCase):
    """AC2: implementer.md no longer sets REVIEWED directly."""

    def setUp(self) -> None:
        self.text = _read(IMPLEMENTER)

    def test_no_direct_reviewed_instruction(self) -> None:
        # The retired instruction: "Update spec status to `REVIEWED`".
        self.assertNotIn(
            "Update spec status to `REVIEWED`", self.text,
            "agents/implementer.md must not tell the implementer to set "
            "REVIEWED directly — the evidence gate refuses without recorded "
            "passing review evidence (AC2 / ADR-0014 §5)",
        )

    def test_keeps_report_deliverable_paths(self) -> None:
        # Load-bearing phrase asserted by test_review_queue_cleanup too.
        self.assertIn(
            "Report the deliverable paths", self.text,
            "agents/implementer.md must keep the 'Report the deliverable "
            "paths' instruction",
        )


class SkillsDescribeGatedLifecycle(unittest.TestCase):
    """AC1: both SKILL.md files describe record → gated transition → recovery."""

    def test_spec_workflow_skill_names_gate_and_recorder(self) -> None:
        text = _read(SPEC_WORKFLOW_SKILL)
        self.assertIn("record-review", text)
        self.assertIn("JIG_REVIEW_EVIDENCE_GATE", text)

    def test_independent_review_skill_names_record_and_check(self) -> None:
        text = _read(INDEP_REVIEW_SKILL)
        self.assertIn("record-review", text)
        self.assertIn("check-reviews", text)


class ScaffoldTemplateInheritsHonestFraming(unittest.TestCase):
    """AC4: the scaffold-generated workflow doc inherits the honest framing."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW_TEMPLATE)

    def test_no_stop_hook_gate_claim(self) -> None:
        self.assertNotRegex(
            self.text, STOP_HOOK_GATE_RE,
            "templates/docs/workflow.md.template must not claim a Stop hook "
            "blocks completion (AC4 — generated docs inherit the flow)",
        )

    def test_points_at_the_transition_gate(self) -> None:
        # The generated doc must point at a command that exists in that
        # install shape — workflow.py transition is the gate.
        self.assertIn(
            "transition", self.text.lower(),
            "the scaffold workflow template must point at the workflow.py "
            "transition gate that exists in the scaffolded install shape",
        )


if __name__ == "__main__":
    unittest.main()
