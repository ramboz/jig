"""Surface tests for slice 104-02 (authoring-nudge) — ADR-0049.

Slice 104-02 adds a design-fidelity **authoring nudge** to the spec-workflow
"Creating a new spec" flow, plus an enriched `design_review:` comment in the
slice template. No new mechanism is introduced: enforcement stays anchored to
the existing `design_review` flag / `slice_needs_design_review` deriver
(spec 071). This test file covers:

  AC1 — the authoring nudge is present on the numbered "Creating a new spec"
        hot-path: extract design values into checkable ACs; when fidelity
        must gate, set `design_review: true` + wire a servo `design-eval`;
        cites spec 071 + ADR-0049.
  AC2 — the guidance is graduated, not mandatory: both tiers named
        (low-stakes visual polish -> design-values-in-ACs + attest-by-eyeball,
        no servo required; a hard fidelity gate -> servo design-eval +
        design_review), and jig "offers, never forces" servo.
  AC3 — the slice-template `design_review:` comment is enriched to name the
        authoring action (extract design values into ACs; wire a servo
        design-eval), not just "set true when ...".
  AC4 — no new mechanism: `workflow.py` still defines exactly the same three
        `slice_needs_*_review` derivers (arch, code_health, design) and no
        new design-fidelity / visual-detector deriver was added.

Mirrors skills/spec-workflow/test_spec_workflow_skill_surface.py in style
(read_text, normalized/lowercased haystack, assertIn/assertTrue).
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"
WORKFLOW_PY = SKILL_DIR / "workflow.py"
REPO_ROOT = SKILL_DIR.parent.parent
SLICE_TEMPLATE = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


class DesignFidelityAuthoringNudgeTests(unittest.TestCase):
    """104-02 AC1/AC2 — the SKILL.md "Creating a new spec" flow carries the
    design-fidelity authoring nudge, graduated across two tiers."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""
        cls.body = _body(cls.text)
        cls.lower = cls.body.lower()

    def test_creating_a_new_spec_flow_present(self):
        self.assertIn(
            "### Creating a new spec", self.body,
            "sanity: the numbered 'Creating a new spec' flow must exist",
        )

    def test_nudge_directs_extracting_design_values_into_acs(self):
        self.assertIn(
            "design value", self.lower,
            "the nudge must direct extracting design values (colours, "
            "spacing, sizes, layout rules) into checkable ACs (104-02 AC1)",
        )
        self.assertTrue(
            "checkable ac" in self.lower or "checkable acceptance" in self.lower,
            "the design values must be extracted into checkable ACs "
            "(104-02 AC1)",
        )

    def test_nudge_directs_design_review_flag_and_servo_design_eval(self):
        self.assertIn(
            "design_review", self.body,
            "the nudge must direct setting `design_review: true` when "
            "fidelity must gate (104-02 AC1)",
        )
        self.assertIn(
            "design-eval", self.lower,
            "the nudge must direct wiring a servo `design-eval` as the "
            "done-condition (104-02 AC1)",
        )
        self.assertIn(
            "servo", self.lower,
            "the nudge must name servo as the eval provider (104-02 AC1)",
        )

    def test_nudge_cites_spec_071_and_adr_0049(self):
        self.assertTrue(
            "spec 071" in self.lower or "071-design-review-pass" in self.lower,
            "the nudge must cite spec 071 (the design_review pass) "
            "(104-02 AC1)",
        )
        self.assertIn(
            "adr-0049", self.lower,
            "the nudge must cite ADR-0049 (104-02 AC1)",
        )

    def test_nudge_is_on_the_numbered_authoring_hot_path(self):
        # Observable: the step lives in the numbered "Creating a new spec"
        # flow body, not a footnote elsewhere in the file.
        creating_idx = self.body.find("### Creating a new spec")
        picking_idx = self.body.find("### Picking up a slice")
        self.assertNotEqual(creating_idx, -1)
        self.assertNotEqual(picking_idx, -1)
        flow_section = self.body[creating_idx:picking_idx].lower()
        self.assertIn(
            "design value", flow_section,
            "the design-fidelity nudge must live inside the numbered "
            "'Creating a new spec' flow, not elsewhere in SKILL.md "
            "(104-02 AC1)",
        )
        self.assertIn(
            "design-eval", flow_section,
            "the servo design-eval pointer must live inside the numbered "
            "'Creating a new spec' flow (104-02 AC1)",
        )

    def test_guidance_is_graduated_two_tiers_named(self):
        # AC2: both tiers named explicitly.
        self.assertTrue(
            "low-stakes" in self.lower,
            "the low-stakes visual-polish tier must be named (104-02 AC2)",
        )
        self.assertIn(
            "attest-by-eyeball", self.lower,
            "the low-stakes tier's resolution (attest-by-eyeball, no servo "
            "required) must be named (104-02 AC2)",
        )
        self.assertTrue(
            "hard fidelity gate" in self.lower or "hard gate" in self.lower,
            "the hard-fidelity-gate tier must be named (104-02 AC2)",
        )

    def test_jig_offers_never_forces_servo(self):
        # AC2: jig "offers, never forces" servo.
        self.assertTrue(
            "offers, never forces" in self.lower
            or ("offers" in self.lower and "never forces" in self.lower),
            "the nudge must state jig offers, never forces, servo "
            "(104-02 AC2)",
        )


class SliceTemplateDesignReviewCommentTests(unittest.TestCase):
    """104-02 AC3 — the slice-template `design_review:` comment names the
    authoring action, not just "set true when ..."."""

    @classmethod
    def setUpClass(cls):
        cls.text = (
            SLICE_TEMPLATE.read_text() if SLICE_TEMPLATE.is_file() else ""
        )
        cls.lower = cls.text.lower()

    def test_template_has_design_review_field(self):
        self.assertIn(
            "design_review: true", self.text,
            "sanity: the slice template must still carry the "
            "`design_review: true` frontmatter comment",
        )

    def test_comment_names_extracting_design_values(self):
        self.assertIn(
            "design value", self.lower,
            "the template's `design_review:` comment must name extracting "
            "design values into ACs as the authoring action (104-02 AC3)",
        )

    def test_comment_names_servo_design_eval(self):
        self.assertIn(
            "design-eval", self.lower,
            "the template's `design_review:` comment must name wiring a "
            "servo `design-eval` (104-02 AC3)",
        )

    def test_comment_cites_adr_0049(self):
        self.assertIn(
            "adr-0049", self.lower,
            "the template's `design_review:` comment must cite ADR-0049 "
            "(104-02 AC3)",
        )


class NoNewDesignFidelityMechanismTests(unittest.TestCase):
    """104-02 AC4 — teeth stay anchored to the existing `design_review`
    flag; no new frontmatter flag, deriver, or keyword/visual-design
    auto-detector is introduced in workflow.py."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW_PY.read_text() if WORKFLOW_PY.is_file() else ""

    def test_slice_needs_design_review_unchanged(self):
        self.assertIn(
            "def slice_needs_design_review(spec_path, slice_fragment: str)"
            " -> bool:",
            self.text,
            "the existing `slice_needs_design_review` deriver signature "
            "must be unchanged (104-02 AC4)",
        )
        self.assertIn(
            'frontmatter_flag_truthy(fields.get("design_review", ""))',
            self.text,
            "`slice_needs_design_review` must still read the plain "
            "`design_review` frontmatter flag via the shared truthy "
            "predicate — no new mechanism (104-02 AC4)",
        )

    def test_review_flag_deriver_set_unchanged(self):
        # Exactly the three existing `slice_needs_*_review` derivers
        # (arch, code_health, design) — no fourth was added.
        derivers = re.findall(
            r"^def (slice_needs_\w+_review)\(", self.text, re.MULTILINE
        )
        self.assertEqual(
            sorted(derivers),
            ["slice_needs_arch_review", "slice_needs_code_health_review",
             "slice_needs_design_review"],
            "no new `slice_needs_*_review` deriver may be added — teeth "
            "stay anchored to the existing three flags (104-02 AC4)",
        )

    def test_no_visual_design_keyword_detector_added(self):
        # No new keyword/visual-design auto-detector function.
        detectors = re.findall(
            r"^def (\w*(?:visual|fidelity)\w*)\(", self.text, re.MULTILINE
        )
        self.assertEqual(
            detectors, [],
            "no new keyword/visual-design auto-detector function may be "
            "added to workflow.py (104-02 AC4): found "
            f"{detectors}",
        )


if __name__ == "__main__":
    unittest.main()
