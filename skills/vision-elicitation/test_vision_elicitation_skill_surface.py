"""Surface tests for skills/vision-elicitation/.

Covers slice 017-02 ACs:
- AC #1 — frontmatter + description shape (3 trigger phrases + template
          reference + category-based deferral hint)
- AC #2 — questions.md exists with the Appendix A sections verbatim (12 from
          spec 017-02 + Section 13 added by spec 022-02 = 13 total)
- AC #3 — both worked-example transcripts exist with required structure
- AC #4 — jig worked example produces template-shaped output (the 9
          H2s from templates/docs/product-vision.md.template), with
          explicit acknowledgment of the divergence from the hand-
          seeded docs/product-vision.md (reword recorded in slice
          017-02 deviation log §1)
- AC #5 — YarnFinder worked example produces template-shaped output
          (same 9 H2s as AC #4 — the skill is template-driven), with
          YarnFinder's bespoke concepts (Data sourcing / Recommended
          slice order / prioritized backlog) mapped to template slots
- AC #6 / #7 — first-run rendered output transitions markers correctly
          (verified via worked-example shape, since the skill is judgment-
          only — no behavioral runtime to test directly)
- AC #8 — surface tests pin frontmatter / description / questions / SKILL.md
          per-section flow markers + anti-greediness DescriptionBoundsTests
          class

AC #9 (routing dogfood) is a post-merge close-out item; not asserted here.

Pattern follows pr-review (slice 012-01) and arch-review (slice 014-01).
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"
QUESTIONS_MD = SKILL_DIR / "questions.md"
WORKED_JIG = SKILL_DIR / "worked-example-jig.md"
WORKED_YARN = SKILL_DIR / "worked-example-yarnfinder.md"

REPO_ROOT = SKILL_DIR.parent.parent
SPEC_MD = REPO_ROOT / "docs" / "specs" / "017-vision-elicitation" / "spec.md"
VISION_MD = REPO_ROOT / "docs" / "product-vision.md"
VISION_TEMPLATE = REPO_ROOT / "templates" / "docs" / "product-vision.md.template"

# Template H2s — the source-of-truth for elicitation output shape.
# Per AC #4 reword (deviation §1 of slice 017-02), the worked examples
# must match the *template* H2 structure, not the hand-seeded
# docs/product-vision.md (which predates the template and uses bespoke
# H2 names).
EXPECTED_TEMPLATE_H2S = [
    "Identity",
    "Target users",
    "Core problem",
    "Competitive landscape",
    "Scope",
    "Stack",
    "Design principles & constraints",
    "How new work enters",
    "Open questions",
]


def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def _normalize(s: str) -> str:
    """YAML folded scalars insert newlines that parse to single spaces.
    Normalize for substring assertions (same helper as pr-review/arch-review)."""
    return " ".join(s.lower().split())


# ----------------------------------------------------------------------------
# AC #1: SKILL.md frontmatter shape
# ----------------------------------------------------------------------------


class FrontmatterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(SKILL_MD.is_file(),
                        f"skills/vision-elicitation/SKILL.md must exist at {SKILL_MD}")

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*vision-elicitation\s*$")

    def test_user_invocable_true(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1 — auto-triggers. AC #9 fallback would invert this in a
        # follow-up commit if the routing dogfood ever fails.
        fm = _frontmatter(self.text)
        self.assertNotIn("disable-model-invocation: true", fm)


# ----------------------------------------------------------------------------
# AC #1: Description must contain (a) trigger phrases (b) template reference
#        (c) category-based deferral hint
# ----------------------------------------------------------------------------


class DescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    # AC #1(a) — three trigger phrases (per spec)
    def test_trigger_phrase_set_up_project_vision(self):
        self.assertIn("set up project vision", self.normalized,
                      "Description must include trigger phrase 'set up project vision'")

    def test_trigger_phrase_elicit_architecture(self):
        self.assertIn("elicit architecture", self.normalized,
                      "Description must include trigger phrase 'elicit architecture'")

    def test_trigger_phrase_define_what_were_building(self):
        # YAML folded; word boundaries collapse. Match either form.
        self.assertIn("define what we're building", self.normalized,
                      "Description must include trigger phrase 'define what we're building'")

    # AC #1(b) — explicit reference to the 017-01 templates as output shape
    def test_references_product_vision_template(self):
        self.assertIn("product-vision.md", self.normalized,
                      "Description must reference docs/product-vision.md as output shape")

    def test_references_architecture_template(self):
        self.assertIn("architecture.md", self.normalized,
                      "Description must reference architecture.md slots as output shape")

    # AC #1(c) — category-based deferral hint
    def test_deferral_hint_category_based(self):
        # Same shape as pr-review / arch-review: "defers to … skill whose
        # description identifies it as handling …"
        self.assertIn("defers to", self.normalized,
                      "Description must include category-based deferral language")
        self.assertIn("vision elicitation", self.normalized,
                      "Deferral hint must name the 'vision elicitation' category")
        # Two of three discovery-category phrases per AC #1(c)
        present = [phrase for phrase in
                   ("product discovery", "project framing", "product scope")
                   if phrase in self.normalized]
        self.assertGreaterEqual(
            len(present), 2,
            "Deferral hint must name at least two of {product discovery, "
            "project framing, product scope} alongside 'vision elicitation' — "
            f"got {present}")


# ----------------------------------------------------------------------------
# AC #8: Anti-greediness bounds — same pattern as pr-review's
# DescriptionBoundsTests / arch-review's equivalent.
# ----------------------------------------------------------------------------


class DescriptionBoundsTests(unittest.TestCase):
    """Pin the description against over-claim phrases per AC #8."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        )

    def test_does_not_claim_best(self):
        self.assertNotIn("best vision", self.normalized,
                         "Description must not claim to be the 'best' anything (AC #8)")
        self.assertNotIn("the best", self.normalized,
                         "Description must not use 'the best' superlatives (AC #8)")

    def test_does_not_claim_comprehensive(self):
        self.assertNotIn("comprehensive product discovery", self.normalized,
                         "Description must not claim 'comprehensive' anything (AC #8)")
        self.assertNotIn("comprehensive vision", self.normalized,
                         "Description must not claim 'comprehensive vision' (AC #8)")

    def test_does_not_claim_complete(self):
        self.assertNotIn("complete vision elicitation", self.normalized,
                         "Description must not claim 'complete' elicitation (AC #8)")

    def test_does_not_claim_definitive(self):
        self.assertNotIn("definitive", self.normalized,
                         "Description must not use 'definitive' phrasing (AC #8)")

    def test_baseline_acknowledged(self):
        # Positive bound: description should signal this is a baseline (matches
        # pr-review's "slim baseline" / arch-review's "lightweight baseline"
        # pattern). One of {baseline, slim, lightweight, default} must appear.
        markers = ("baseline", "slim", "lightweight", "default")
        present = [m for m in markers if m in self.normalized]
        self.assertTrue(
            present,
            f"Description must signal baseline scope using one of {markers}; "
            f"got none",
        )


# ----------------------------------------------------------------------------
# AC #2: questions.md exists with the Appendix A sections verbatim (12 from
# spec 017-02 + Section 13 added by spec 022-02 = 13 total).
# ----------------------------------------------------------------------------


# Sections must match Appendix A in spec.md exactly (slice 017-01 reshape
# fixed the heading names; this list is the post-reshape source of truth).
EXPECTED_QUESTION_SECTIONS = [
    "Identity",
    "Target users",
    "Core problem",
    "Competitive landscape",
    "Scope",
    "Repository structure",
    "Tech stack",
    "Module boundaries",
    "Data model",
    "Design principles & constraints",
    "How new work enters",
    "Open questions",
    "Contract surfaces",  # added by spec 022-02 (slice 022-02 AC #1)
]


class QuestionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = QUESTIONS_MD.read_text() if QUESTIONS_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(QUESTIONS_MD.is_file(),
                        f"questions.md must exist at {QUESTIONS_MD}")

    def test_has_13_sections(self):
        # Sections are H3 headings of the form "### Section N — <name>".
        # 12 from spec 017 + 1 (Contract surfaces) added by spec 022-02.
        headings = re.findall(r"^## Section \d+ — (.+?)\s*(?:\*\(|$)",
                              self.text, flags=re.MULTILINE)
        self.assertEqual(
            len(headings), 13,
            f"questions.md must have exactly 13 sections (AC #2 from 017-02 "
            f"+ AC #1 from 022-02); got {len(headings)}",
        )

    def test_section_names_match_appendix_a(self):
        headings = re.findall(r"^## Section \d+ — (.+?)\s*(?:\*\(|$)",
                              self.text, flags=re.MULTILINE)
        # Strip trailing markdown emphasis / parentheticals; compare to
        # the canonical names.
        cleaned = [h.split("*")[0].strip() for h in headings]
        self.assertEqual(
            cleaned, EXPECTED_QUESTION_SECTIONS,
            f"questions.md section names must match Appendix A; "
            f"got {cleaned}",
        )

    def test_each_section_has_at_least_one_question(self):
        # Each section body must contain at least one **Qn.x:** prompt
        for section in EXPECTED_QUESTION_SECTIONS:
            pattern = re.compile(
                rf"^## Section \d+ — {re.escape(section)}.*?(?=^## Section|\Z)",
                flags=re.MULTILINE | re.DOTALL,
            )
            match = pattern.search(self.text)
            self.assertIsNotNone(
                match,
                f"questions.md must contain section '{section}'",
            )
            self.assertRegex(
                match.group(0), r"\*\*Q\d+\.\d+:?\*\*",
                f"section '{section}' must contain at least one Qn.x question",
            )


# ----------------------------------------------------------------------------
# AC #3 / #4 / #5: Worked-example transcripts exist + structural match
# ----------------------------------------------------------------------------


class WorkedExampleJigTests(unittest.TestCase):
    """AC #3 + AC #4 — jig worked example shape + structural-match dogfood
    against the vision template (post-AC #4 reword in slice 017-02
    deviation §1)."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKED_JIG.read_text() if WORKED_JIG.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(WORKED_JIG.is_file(),
                        f"worked-example-jig.md must exist at {WORKED_JIG}")

    def test_walks_through_sections_with_qa_pairs(self):
        # AC #3: shows question → answer → rendered section heading + body.
        # Pin: at least 8 of the (now 13, originally 12) sections appear
        # with a Q/A pair (allow skipped sections to be elided in the
        # worked example). The worked-example file documents the original
        # 12-section walk-through; Section 13 (Contract surfaces, added
        # by spec 022-02) is intentionally not walked here.
        present = sum(1 for sec in EXPECTED_QUESTION_SECTIONS
                      if sec in self.text)
        self.assertGreaterEqual(
            present, 8,
            f"worked-example-jig.md must walk through ≥8 of the question "
            f"sections with Q/A pairs; got {present}",
        )

    def test_references_real_vision_md(self):
        # AC #4: must reference the hand-seeded docs/product-vision.md to
        # acknowledge the H2-name divergence (template uses "Identity";
        # hand-seeded uses "Vision statement"; etc.).
        self.assertIn("docs/product-vision.md", self.text,
                      "worked-example-jig.md must reference "
                      "docs/product-vision.md to acknowledge the H2-name "
                      "divergence with the template (AC #4)")

    def test_output_matches_vision_template_h2s(self):
        # AC #4 (post-reword): output H2 structure matches the
        # vision *template*'s 9 H2s (not the hand-seeded vision.md's
        # bespoke H2 names). Each template H2 must appear in the
        # worked example as a rendered output marker.
        for h2 in EXPECTED_TEMPLATE_H2S:
            self.assertIn(
                h2, self.text,
                f"worked-example-jig.md must show rendered output with "
                f"H2 '{h2}' from the vision template (AC #4)",
            )


class WorkedExampleYarnFinderTests(unittest.TestCase):
    """AC #3 + AC #5 — YarnFinder worked example shape + structural-match
    against /Users/ramboz/Projects/CLAUDE.md's prescribed sections."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKED_YARN.read_text() if WORKED_YARN.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(WORKED_YARN.is_file(),
                        f"worked-example-yarnfinder.md must exist at {WORKED_YARN}")

    def test_references_yarnfinder(self):
        self.assertIn(
            "YarnFinder", self.text,
            "worked-example-yarnfinder.md must reference the YarnFinder project")

    def test_references_user_claude_md(self):
        # AC #5: must reference the source of the YarnFinder pitch.
        # Either spelling is acceptable (the CLAUDE.md path is sensitive)
        self.assertIn(
            "CLAUDE.md", self.text,
            "worked-example-yarnfinder.md must reference the source "
            "CLAUDE.md (AC #5)")

    def test_walks_through_sections_with_qa_pairs(self):
        # AC #3: shows question → answer pattern.
        # Pin: at least 8 of the question sections have Q/A coverage.
        # (Originally 12; spec 022-02 added Section 13 which the
        # worked example intentionally doesn't walk.)
        present = sum(1 for sec in EXPECTED_QUESTION_SECTIONS
                      if sec in self.text)
        self.assertGreaterEqual(
            present, 8,
            f"worked-example-yarnfinder.md must walk through ≥8 of the "
            f"question sections; got {present}",
        )

    def test_yarnfinder_concepts_mapped_to_template_slots(self):
        # AC #5: YarnFinder's bespoke concepts (Data sourcing, Recommended
        # slice order, prioritized backlog) must be explicitly addressed —
        # whether mapped to template slots or noted as out-of-shape.
        # The post-017-01-reshape template is canonical: the worked example
        # MUST acknowledge how YarnFinder's content fits the template.
        yarnfinder_concepts = ("Data sourcing", "slice order", "prioritized")
        present = [c for c in yarnfinder_concepts if c in self.text]
        self.assertGreaterEqual(
            len(present), 2,
            f"worked-example-yarnfinder.md must address ≥2 of the YarnFinder-"
            f"bespoke concepts {yarnfinder_concepts}; got {present}",
        )


# ----------------------------------------------------------------------------
# AC #8: SKILL.md body has per-section flow markers
# ----------------------------------------------------------------------------


class BodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_documents_per_section_flow(self):
        # AC #8 — per-section flow markers must appear in the SKILL.md body
        self.assertRegex(
            self.body, r"(?i)per-section",
            "SKILL.md body must document per-section flow (AC #8)",
        )

    def test_documents_three_marker_states(self):
        # Body must reference the unfilled/filled/skipped marker state
        # convention (slice 017-01) so the elicitation skill's behavior
        # is anchored to the convention.
        for state in ("unfilled", "filled", "skipped"):
            self.assertIn(
                state, self.body,
                f"SKILL.md body must reference marker state '{state}'",
            )

    def test_documents_no_paraphrase_rule(self):
        # The "skill does not paraphrase user words" rule (Appendix A
        # "Question-set vs. user-words boundary") must be enforced in
        # the SKILL.md body.
        self.assertRegex(
            self.body, r"(?i)(no\s+paraphras|don't\s+paraphras|does not paraphras|"
                      r"writes the user's words|user's own words)",
            "SKILL.md body must document the no-paraphrase rule",
        )

    def test_references_questions_file(self):
        # Progressive disclosure: SKILL.md body must point to questions.md
        # rather than inlining the full question set (12 sections originally
        # per spec 017-02; 13 since Section 13 added by spec 022-02).
        self.assertIn(
            "questions.md", self.body,
            "SKILL.md body must reference questions.md for the question set",
        )

    def test_references_worked_examples(self):
        self.assertIn(
            "worked-example-jig.md", self.body,
            "SKILL.md body must reference worked-example-jig.md",
        )
        self.assertIn(
            "worked-example-yarnfinder.md", self.body,
            "SKILL.md body must reference worked-example-yarnfinder.md",
        )

    def test_worked_examples_section_acknowledges_template_shape(self):
        # Implementation-reviewer-driven regression pin (deviation §2):
        # the AC #4/#5 reword to "template-shaped output" must hold across
        # all SKILL.md prose. An earlier draft had a stale "matches the
        # hand-seeded docs/product-vision.md byte-for-byte" claim that
        # contradicted the reworded AC. Pin both directions: the worked-
        # examples section must mention "template", AND must NOT claim
        # byte-for-byte match with the hand-seeded file.
        worked_match = re.search(
            r"## Worked examples\n(.*?)(?=^## |\Z)",
            self.body, flags=re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(
            worked_match,
            "SKILL.md must have a '## Worked examples' section",
        )
        worked_body = worked_match.group(1)
        self.assertIn(
            "template", worked_body.lower(),
            "Worked-examples section must describe output as 'template'-"
            "shaped — pinning against recurrence of the pre-reword stale "
            "claim (slice 017-02 reviewer-driven regression pin)",
        )
        self.assertNotIn(
            "byte-for-byte", worked_body,
            "Worked-examples section must NOT claim byte-for-byte match "
            "with the hand-seeded docs/product-vision.md — that contradicts "
            "the AC #4 reword to template-shape output",
        )


# ----------------------------------------------------------------------------
# AC #1(c): Deferral language — same shape as pr-review / arch-review
# ----------------------------------------------------------------------------


class DeferralLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_body_has_deferral_section(self):
        # Same shape as pr-review's "When to use vs. when to defer"
        self.assertRegex(
            self.body, r"(?i)(when to defer|when not to use|defer to)",
            "SKILL.md body must have a 'when to defer' discussion",
        )


# ----------------------------------------------------------------------------
# Slice 017-03: Re-run protocol + hash field + per-section refresh
# ----------------------------------------------------------------------------


WORKED_RERUN = SKILL_DIR / "worked-example-rerun.md"
CONVENTIONS_MD = REPO_ROOT / "docs" / "conventions.md"


class RerunProtocolBodyTests(unittest.TestCase):
    """AC #1 (017-03) — SKILL.md body contains a 'Re-run protocol'
    section documenting the four-step flow + AC #5 (017-03) per-section
    refresh."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_has_rerun_protocol_section(self):
        # The body must have a section that names the re-run protocol
        # (either as an H2 / H3 heading or as a bolded paragraph header).
        self.assertRegex(
            self.body, r"(?im)^#+\s+Re-run protocol|^\*\*Re-run protocol\*\*",
            "SKILL.md body must contain a 'Re-run protocol' section "
            "(slice 017-03 AC #1)",
        )

    def test_documents_four_step_flow(self):
        # Four steps: read marker → compute hash → compare → surface
        # decision. Pin the four step verbs.
        body_lower = self.body.lower()
        for verb in ("read", "compute hash", "compare", "surface"):
            self.assertIn(
                verb, body_lower,
                f"SKILL.md body must mention '{verb}' as part of the "
                f"re-run four-step flow (017-03 AC #1)",
            )

    def test_documents_three_choice_surface(self):
        # AC #4 (017-03): warning offers refresh / skip / diff.
        body_lower = self.body.lower()
        for choice in ("refresh", "skip", "diff"):
            self.assertIn(
                choice, body_lower,
                f"SKILL.md body must mention the '{choice}' choice for "
                f"per-section divergence handling (017-03 AC #4)",
            )

    def test_documents_per_section_refresh(self):
        # AC #5 (017-03): per-section refresh is documented.
        self.assertRegex(
            self.body, r"--section",
            "SKILL.md body must document `--section` per-section refresh "
            "(017-03 AC #5)",
        )

    def test_references_rerun_worked_example(self):
        # AC #6 (017-03): worked-example transcript referenced from SKILL.md
        self.assertIn(
            "worked-example-rerun.md", self.body,
            "SKILL.md body must reference worked-example-rerun.md "
            "(017-03 AC #6)",
        )


class ConventionsHashFieldTests(unittest.TestCase):
    """AC #2 (017-03) — docs/conventions.md marker convention specifies
    the hash field format for filled sections."""

    @classmethod
    def setUpClass(cls):
        cls.body = CONVENTIONS_MD.read_text() if CONVENTIONS_MD.is_file() else ""

    def test_hash_field_documented(self):
        # The "Elicitation slots" rule must now document the hash field.
        rule_match = re.search(
            r"\*\*Rule:\*\* Elicitation slots.*?(?=\*\*Rule:\*\*|\Z)",
            self.body, flags=re.DOTALL,
        )
        self.assertIsNotNone(
            rule_match,
            "docs/conventions.md must contain the 'Elicitation slots' rule",
        )
        rule_body = rule_match.group(0)
        # Hash field name + format.
        self.assertIn(
            "hash:", rule_body,
            "The 'Elicitation slots' rule must document the `hash:` field "
            "for filled sections (017-03 AC #2)",
        )

    def test_hash_format_specified(self):
        # AC #2 (017-03): hash format is sha256:<first-12-hex>.
        rule_match = re.search(
            r"\*\*Rule:\*\* Elicitation slots.*?(?=\*\*Rule:\*\*|\Z)",
            self.body, flags=re.DOTALL,
        )
        rule_body = rule_match.group(0) if rule_match else ""
        self.assertRegex(
            rule_body, r"sha256",
            "The 'Elicitation slots' rule must specify 'sha256' as the "
            "hash algorithm (017-03 AC #2)",
        )
        self.assertRegex(
            rule_body, r"12.{0,10}hex",
            "The 'Elicitation slots' rule must specify the hash prefix "
            "length ('12 hex' chars) (017-03 AC #2)",
        )

    def test_017_03_hash_field_no_longer_says_added_in_017_03(self):
        # Pre-017-03 convention rule said "hash field added in 017-03".
        # After 017-03 lands, that future-tense phrasing should be gone.
        rule_match = re.search(
            r"\*\*Rule:\*\* Elicitation slots.*?(?=\*\*Rule:\*\*|\Z)",
            self.body, flags=re.DOTALL,
        )
        rule_body = rule_match.group(0) if rule_match else ""
        self.assertNotIn(
            "added in 017-03", rule_body,
            "The 'Elicitation slots' rule must no longer say "
            "'added in 017-03' — that's the pre-017-03 deferral note. "
            "After 017-03 lands, the hash field is documented directly.",
        )


class SkillMdStalenessRegressionTests(unittest.TestCase):
    """Slice 017-03 reviewer-driven regression pin (per learnings.md
    "Mid-implementation reshape leaves stale future-tense prose"). Each
    landing of a deferred slice should not leave behind sentences that
    describe the now-shipped behavior as deferred.

    Scope extended (reconciliation reviewer §7): test sweeps both
    SKILL.md AND docs/conventions.md, because the first reconciliation
    pass found a stale "017-03's re-run mechanics will detect" in
    conventions.md that the SKILL.md-only test missed."""

    STALE_PHRASES = [
        "once that ships",
        "Once slice 017-03 ships",
        "Today (017-02) the skill is first-run only",
        "Re-runs are 017-03's job",
        "017-03 will detect",
        "017-03 will add",
        "017-03 adds re-run mechanics",
        "added in 017-03",
    ]

    SURFACES = {
        "SKILL.md": SKILL_MD,
        "docs/conventions.md": CONVENTIONS_MD,
    }

    def test_no_017_03_future_tense_phrasing(self):
        for label, path in self.SURFACES.items():
            text = path.read_text() if path.is_file() else ""
            for phrase in self.STALE_PHRASES:
                self.assertNotIn(
                    phrase, text,
                    f"{label} must not contain pre-017-03 future-tense "
                    f"phrasing '{phrase}' — pattern documented in "
                    f"docs/memory/learnings.md 'Mid-implementation reshape "
                    f"leaves stale future-tense prose'",
                )

    def test_describes_rerun_as_shipped(self):
        # Positive bound: SKILL.md must describe the re-run protocol as
        # part of the skill's current behavior (not future work).
        skill_text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""
        self.assertIn(
            "re-run protocol", skill_text.lower(),
            "SKILL.md must describe the Re-run protocol as current behavior",
        )


class WorkedExampleRerunTests(unittest.TestCase):
    """AC #6 (017-03) — worked-example transcript demonstrates divergence
    detection end-to-end."""

    @classmethod
    def setUpClass(cls):
        cls.text = WORKED_RERUN.read_text() if WORKED_RERUN.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(
            WORKED_RERUN.is_file(),
            f"worked-example-rerun.md must exist at {WORKED_RERUN} "
            "(017-03 AC #6)",
        )

    def test_shows_divergence_detection(self):
        text_lower = self.text.lower()
        # The transcript must show: a section gets manually edited;
        # the skill detects divergence; the skill warns; the user
        # chooses refresh / skip / diff; the section is refreshed
        # or kept; the hash updates.
        for cue in ("hash", "diverge", "manual edit", "warn"):
            self.assertIn(
                cue, text_lower,
                f"worked-example-rerun.md must demonstrate '{cue}' "
                f"as part of the divergence detection flow (017-03 AC #6)",
            )

    def test_shows_three_choice_resolution(self):
        text_lower = self.text.lower()
        for choice in ("refresh", "skip", "diff"):
            self.assertIn(
                choice, text_lower,
                f"worked-example-rerun.md must show the '{choice}' choice "
                f"(017-03 AC #6)",
            )

    def test_shows_hash_update_after_refresh(self):
        # After refresh, the marker's hash should change. The worked
        # example must show this end-to-end.
        text_lower = self.text.lower()
        self.assertRegex(
            text_lower, r"hash.{0,200}(?:updat|new|chang)",
            "worked-example-rerun.md must show hash update after refresh "
            "(017-03 AC #6)",
        )


if __name__ == "__main__":
    unittest.main()
