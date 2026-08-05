"""
Tests for slice 058-06 — `jig:bug-fix` skill + plugin wiring + workflow.md
routing. One fixture per acceptance criterion:

  - AC #1: skills/bug-fix/SKILL.md exists with the bug-fix name, a
    trigger-rich description, and the orchestration content (lifecycle +
    teeth gates, diagnose vs diagnose_and_fix modes, the borrowed
    diagnostic question, the tier model, de-escalation), owning its
    orchestration (defers only pr-review + security-review).
  - AC #2: bug-fix is registered in the tier table (scaffold._TIER_SKILLS)
    and the restated install contract (install_contract.EXPECTED_SKILLS),
    and verify_install treats it as a contract skill requiring a SKILL.md.
  - AC #3: docs/workflow.md carries the bug-shaped vs spec-shaped routing
    rule pointing at jig:bug-fix and spec-workflow.
  - AC #4: cross-references name the real skill — spec-workflow's bookend
    no longer points at the non-existent debug-workflow, and the project
    CLAUDE.md helper roster lists bug-fix (bug.py).

Slice 104-01 (design-fidelity triage disambiguation, ADR-0049) adds
`DesignFidelityTriageTests` — the gnarly "design-gap" tier is disambiguated
into malfunction (bug) vs. fidelity gap (spec spine), with both routing
branches, the ambiguous-case tie-breaker, and the fidelity-vs-refinement
test present and self-consistent across the whole surface — plus
`BugPyUnchangedTests`, which guards that this stays prose/judgment routing
(no new tier token in bug.py).
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install_contract  # noqa: E402
import verify_install  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "skills" / "bug-fix" / "SKILL.md"
BUG_PY = REPO_ROOT / "skills" / "bug-fix" / "bug.py"


class BugFixSkillContentTests(unittest.TestCase):
    """AC #1 — the skill exists and owns its orchestration."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text()
        cls.lower = cls.text.lower()

    def test_skill_md_exists(self):
        self.assertTrue(SKILL_MD.is_file(), f"missing {SKILL_MD}")

    def test_name_resolves_to_bug_fix(self):
        # Bare `name:` per the repo convention (the host prefixes `jig:`);
        # surfaced as jig:bug-fix.
        self.assertIn("name: bug-fix", self.text)
        self.assertIn("user-invocable: true", self.text)

    def test_description_is_trigger_rich(self):
        for trigger in (
            "fix this bug",
            "debug this",
            "root-cause this",
            "regress",
        ):
            self.assertIn(
                trigger, self.lower, f"description missing trigger: {trigger!r}"
            )

    def test_modes_documented(self):
        self.assertIn("diagnose_and_fix", self.text)
        self.assertIn("diagnose", self.text)

    def test_borrowed_diagnostic_question(self):
        # The "output vs the process that created it" question (ADR-0016 §9).
        self.assertIn("process that created", self.lower)
        self.assertIn("treadmill", self.lower)

    def test_tier_model_present(self):
        for tier in ("trivial", "standard", "gnarly"):
            self.assertIn(tier, self.lower, f"tier model missing: {tier}")

    def test_de_escalation_guidance(self):
        self.assertIn("de-escalation", self.lower)

    def test_teeth_gates_present(self):
        # The two distinctive gates + the lifecycle states.
        self.assertIn("ROOT_CAUSED", self.text)
        self.assertIn("red", self.lower)
        self.assertIn("green", self.lower)
        self.assertIn("hypothes", self.lower)

    def test_owns_orchestration_defers_only_reused_steps(self):
        # It must NOT defer wholesale; only pr-review (craft) and
        # security-review (conditional security) defer to a richer skill.
        self.assertIn("pr-review", self.lower)
        self.assertIn("security-review", self.lower)
        self.assertIn("owns its orchestration", self.lower)


class BugFixWiringTests(unittest.TestCase):
    """AC #2 — registered in the tier table + install contract; a contract
    skill verify_install requires a SKILL.md for."""

    def test_in_expected_skills(self):
        self.assertIn("bug-fix", install_contract.EXPECTED_SKILLS)

    def test_in_tier_one(self):
        scaffold_dir = str(REPO_ROOT / "skills" / "scaffold-init")
        sys.path.insert(0, scaffold_dir)
        try:
            import scaffold  # noqa: E402

            self.assertIn("bug-fix", scaffold._TIER_SKILLS["tier-1"])
        finally:
            if scaffold_dir in sys.path:
                sys.path.remove(scaffold_dir)

    def test_verify_install_requires_bug_fix_skill_md(self):
        # verify_install asserts every contract skill has a SKILL.md under
        # skills/. With bug-fix in EXPECTED_SKILLS, that assertion now covers
        # this skill against the real repo tree.
        ok, msg = verify_install.check_active_skills_present(REPO_ROOT)
        self.assertTrue(ok, msg)


class WorkflowRoutingTests(unittest.TestCase):
    """AC #3 — docs/workflow.md routing rule."""

    @classmethod
    def setUpClass(cls):
        cls.text = (REPO_ROOT / "docs" / "workflow.md").read_text()

    def test_routing_section_present(self):
        self.assertIn("Routing", self.text)

    def test_routes_bug_shaped_to_bug_fix(self):
        self.assertIn("jig:bug-fix", self.text)

    def test_routes_spec_shaped_to_spec_workflow(self):
        self.assertIn("spec-workflow", self.text)

    def test_trivial_skips_to_tdd_loop(self):
        self.assertIn("tdd-loop", self.text)


class CrossReferenceTests(unittest.TestCase):
    """AC #4 — cross-references name the real skill."""

    def test_spec_workflow_bookend_updated(self):
        text = (REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md").read_text()
        self.assertNotIn("debug-workflow", text)
        self.assertIn("jig:bug-fix", text)

    def test_claude_md_helper_roster(self):
        text = (REPO_ROOT / "CLAUDE.md").read_text()
        self.assertIn("`bug-fix` (`bug.py`)", text)


class DesignFidelityTriageTests(unittest.TestCase):
    """Slice 104-01 — design-gap tier disambiguation + triage rule
    (ADR-0049). One fixture per acceptance criterion."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text()
        # Normalize whitespace (incl. markdown line-wraps) so a multi-word
        # phrase assertion isn't brittle to where prose happens to wrap.
        cls.lower = re.sub(r"\s+", " ", cls.text.lower())

    def test_malfunction_vs_fidelity_distinction_present(self):
        # AC1: the gnarly-tier "design-gap" entry must name both the
        # malfunction case and the pure visual fidelity-gap case, and their
        # different routes.
        self.assertIn("malfunction", self.lower)
        self.assertIn("fidelity gap", self.lower)
        self.assertIn("spec spine", self.lower)

    def test_routing_branches_present(self):
        # AC2: both routing branches so a mockup-first rebuild is not
        # dead-ended — originating spec exists vs. no originating spec.
        self.assertIn("originating spec", self.lower)
        self.assertIn("no originating spec", self.lower)
        self.assertIn("new spec", self.lower)

    def test_malfunction_test_stated(self):
        # AC2: the canonical triage test in prose.
        self.assertIn("only when the ui", self.lower)
        self.assertIn("malfunctions", self.lower)

    def test_ambiguous_case_tie_breaker_present(self):
        # AC3: ADR-0049 §2's tie-breaker for the ambiguous-but-functional
        # case (behaves correctly, only looks off) defaults to the spine.
        self.assertIn("ambiguous", self.lower)
        self.assertIn("behaves correctly", self.lower)

    def test_fidelity_vs_refinement_target_change_test_present(self):
        # AC3: ADR-0049 §3's operative test — does the visual target change?
        self.assertIn("target", self.lower)
        self.assertIn("refinement", self.lower)
        self.assertIn("carry", self.lower)

    def test_pointers_to_spec_workflow_and_adr(self):
        # AC2: the triage SECTION (not just the file) names spec-workflow and
        # links ADR-0049 — scoped so the assertion can't be satisfied by the
        # word "spec-workflow" appearing elsewhere in the SKILL. Anchor on the
        # `###` heading (not the earlier description mention of the section).
        self.assertIn("### design-fidelity triage", self.lower)
        section = self.lower.split("### design-fidelity triage", 1)[-1][:2500]
        self.assertIn("spec-workflow", section)
        self.assertIn(
            "adr-0049-design-fidelity-routing-to-originating-spec.md", section
        )

    def test_no_undifferentiated_design_gap_surface(self):
        # AC5: self-consistency across the WHOLE bug-fix surface — after the
        # disambiguation, no read-surface may still carry the undifferentiated
        # "design-gap" term that routes a pure visual fidelity gap into
        # bug-fix. (The de-escalation bullet was a second surface beyond the
        # tier table; this guards against that whole class of miss.)
        self.assertNotIn("design-gap", self.lower)

    def test_description_boundary_names_fidelity_as_spec_shaped(self):
        # AC5: self-consistency — the description's "Do not use for
        # spec-shaped work" boundary agrees with the new triage text.
        self.assertIn("do not use for spec-shaped work", self.lower)
        self.assertIn("design-fidelity", self.lower)


class BugPyUnchangedTests(unittest.TestCase):
    """AC4 — the routing is prose/judgment only: no new tier token,
    classifier branch, or CLI behaviour added to bug.py."""

    @classmethod
    def setUpClass(cls):
        cls.text = BUG_PY.read_text()
        cls.lower = cls.text.lower()

    def test_valid_tiers_unchanged(self):
        sys.path.insert(0, str((REPO_ROOT / "skills" / "bug-fix")))
        try:
            import bug  # noqa: E402

            self.assertEqual(bug.VALID_TIERS, ("trivial", "standard", "gnarly"))
        finally:
            if str((REPO_ROOT / "skills" / "bug-fix")) in sys.path:
                sys.path.remove(str((REPO_ROOT / "skills" / "bug-fix")))

    def test_no_new_design_fidelity_tier_token(self):
        for token in ("design-gap", "fidelity", "mockup", "design-fidelity"):
            self.assertNotIn(
                token,
                self.lower,
                f"bug.py must not gain a new design/fidelity tier token: {token!r}",
            )


if __name__ == "__main__":
    unittest.main()
