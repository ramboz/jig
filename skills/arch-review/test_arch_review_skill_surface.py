"""Surface tests for skills/arch-review/SKILL.md.

Covers AC #1 (frontmatter shape), AC #2 (body sections), AC #3 (description
trigger phrases + anti-greediness bounds + body refs + worked example), and
the deferral-language requirement from spec 014-01.

Structurally mirrors `skills/pr-review/test_skill_surface.py` (the
precedent established by slice 012-01). The arch-review variant differs in:
seven trigger phrases (vs. pr-review's six), four sibling-skill names (vs.
pr-review's three), and a four-section review output of summary / strengths
/ concerns / open questions (vs. pr-review's scope / blockers / nits /
strengths).

These tests are pure-file inspections — no subprocess, no runner. They run
under the same `python3 -m unittest discover skills/` invocation used for
every other jig skill.
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def _normalize(s: str) -> str:
    """Match the normalization pattern from slice 006-01 design choice #7,
    reused by 012-01: YAML folded scalars insert newlines in raw bytes but
    parse to single-space-collapsed strings. Normalize so substring
    assertions match the parsed shape, not the raw bytes."""
    return " ".join(s.lower().split())


_FENCED_BLOCK_RE = re.compile(r"(?ms)^```.*?^```[ \t]*$")


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced ```...``` regions so H2/H3-shaped lines inside code
    examples don't trip the `_h2_positions` regex helper.
    Offsets refer to the returned (stripped) body, not the source."""
    return _FENCED_BLOCK_RE.sub("", text)


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(SKILL_MD.is_file(),
                        f"skills/arch-review/SKILL.md must exist at {SKILL_MD}")

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*arch-review\s*$")

    def test_user_invocable_true(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1: this skill auto-triggers. If AC #9 fallback fires, this test
        # is intentionally inverted in a follow-up commit; for the default
        # (auto-triggering) path, absent or false is required.
        fm = _frontmatter(self.text)
        self.assertNotIn("disable-model-invocation: true", fm)


class DescriptionTests(unittest.TestCase):
    """AC #3 — description contains the one-sentence summary, the seven
    trigger phrases, the category-based deferral hint, the bundled-review
    carve-out, and a Do-not-use-for clause naming the three sibling skills."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_one_sentence_summary(self):
        # AC #1 mandated phrasing for the opener.
        self.assertIn(
            "team baseline for architecture, design-doc, and rfc review",
            self.normalized,
        )

    def test_seven_trigger_phrases(self):
        phrases = [
            "review this design",
            "review this architecture",
            "review this proposal",
            "review my rfc",
            "poke holes in this proposal",
            "is this design sound",
            "critique this tech spec",
        ]
        for phrase in phrases:
            self.assertIn(phrase, self.normalized,
                          f"description missing trigger phrase: {phrase!r}")

    def test_category_based_deferral_hint_present(self):
        # AC #1 mandated category-based deferral hint (matches the post-
        # reconciliation pattern from 012-01).
        self.assertIn(
            "defers to any other installed skill whose description "
            "identifies it as handling architecture review, design "
            "review, rfc review, or technical-design review",
            self.normalized,
        )

    def test_excludes_bundled_review_skill_from_deferral(self):
        # AC #1 mandated carve-out so the deferral chain doesn't collapse
        # downward to the generic built-in `review` skill.
        self.assertIn(
            "does not defer to the generic built-in `review` skill",
            self.normalized,
        )

    def test_do_not_use_clause_names_pr_review(self):
        self.assertRegex(self.normalized, r"do not use")
        # AC #1 sub-clause (a) — PR/diff review goes to /jig:pr-review.
        self.assertIn("pr/diff review", self.normalized)
        self.assertIn("/jig:pr-review", self.normalized)

    def test_do_not_use_clause_names_independent_review(self):
        # AC #1 sub-clause (b) — spec-compliance review goes to
        # /jig:independent-review.
        self.assertIn("spec-compliance review", self.normalized)
        self.assertIn("/jig:independent-review", self.normalized)

    def test_do_not_use_clause_names_adr_workflow(self):
        # AC #1 sub-clause (c) — ADR authorship/scaffolding goes to
        # /jig:adr-workflow; this skill reviews ADR drafts but does not
        # create them.
        self.assertIn("adr authorship or scaffolding", self.normalized)
        self.assertIn("/jig:adr-workflow", self.normalized)

    def test_do_not_use_clause_exclusions_in_spec_mandated_order(self):
        # AC #1 mandates the three exclusions appear in this exact order:
        # PR/diff review → spec-compliance → ADR authorship. Filed as inbox
        # `clarify/test/exclusion-ordering` (2026-05-18, observation extends
        # to arch-review) — substring presence alone doesn't catch drift.
        a = self.normalized.find("pr/diff review")
        b = self.normalized.find("spec-compliance review of a finished slice")
        c = self.normalized.find("adr authorship or scaffolding")
        self.assertNotEqual(a, -1, "missing exclusion (a) PR/diff review")
        self.assertNotEqual(b, -1, "missing exclusion (b) spec-compliance")
        self.assertNotEqual(c, -1, "missing exclusion (c) ADR authorship")
        self.assertLess(a, b, "exclusion (a) must precede (b) in spec-mandated order")
        self.assertLess(b, c, "exclusion (b) must precede (c) in spec-mandated order")


class DescriptionBoundsTests(unittest.TestCase):
    """AC #3 (anti-greediness) — the normalized description does NOT contain
    over-claiming phrases that would shadow a richer user skill.

    Intentional asymmetry (per spec 014-01 AC #3): the category names
    "architecture review" and "design review" are NOT in the forbidden list
    because both appear in the AC #1 deferral hint. The bounds test fires on
    depth-claims and persona-claims, not on category names. Do not add
    "architecture review" or "design review" to the forbidden list without
    first amending AC #1's mandated deferral-hint phrasing.
    """

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive review",
            "deep design analysis",
            "expert-level",
            "multi-persona",
            "seven perspectives",
            "full audit",
            "security review",
            "scalability review",
            "reliability review",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, self.normalized,
                             f"description over-claims with phrase: {phrase!r}")

    def test_intentional_asymmetry_rationale_pinned(self):
        # The category names that are *intentionally* allowed in the
        # description (because AC #1 mandates them in the deferral hint).
        # This test pins the rationale documented in AC #3: removing these
        # from the description would break the deferral hint, so they must
        # remain present.
        for phrase in ["architecture review", "design review"]:
            self.assertIn(
                phrase, self.normalized,
                f"description missing category-name phrase: {phrase!r} "
                "(see AC #3 intentional-asymmetry rationale)",
            )


class BodyTests(unittest.TestCase):
    """AC #2 — body has the six H2 sections in order."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def _h2_positions(self, body: str):
        """Return list of (heading_text_lower, char_offset) for every H2."""
        body = _strip_fenced_blocks(body)
        results = []
        for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body):
            results.append((m.group(1).lower(), m.start()))
        return results

    def test_fenced_block_h2_h3_are_ignored(self):
        synthetic = (
            "## Real H2\n"
            "Text.\n"
            "```\n"
            "## Fake H2 in code block\n"
            "### Fake H3 in code block\n"
            "```\n"
            "### Real H3\n"
        )
        headings = [h for h, _ in self._h2_positions(synthetic)]
        self.assertIn("real h2", headings)
        self.assertNotIn("fake h2 in code block", headings)

    def test_has_what_this_skill_does(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("what this skill does" in h for h, _ in positions),
            f"missing 'What this skill does' H2; found: {[h for h, _ in positions]}",
        )

    def test_has_when_to_use_vs_defer(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("when to use" in h and "defer" in h for h, _ in positions),
            "missing 'When to use vs. when to defer' H2",
        )

    def test_has_inputs(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(any(h.strip() == "inputs" for h, _ in positions),
                        "missing 'Inputs' H2")

    def test_has_review_structure(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("review structure" in h for h, _ in positions),
            "missing 'Review structure' H2",
        )

    def test_concerns_bucket_carries_leanness_lens(self):
        """Spec 109-01 AC #2 — the Concerns bucket must direct the reviewer
        to raise over-engineering / premature abstraction / a simpler
        architecture, anchored to still satisfying the acceptance criteria.
        Guards the SKILL.md baseline against silently regressing the lens."""
        # Collapse whitespace so line-wrapped multi-word terms still match.
        body_norm = re.sub(r"\s+", " ", _strip_fenced_blocks(self.body).lower())
        for term in ("simpler architecture", "over-engineering",
                     "premature abstraction", "speculative generality"):
            self.assertIn(
                term, body_norm,
                f"Concerns bucket must name '{term}' as a leanness concern "
                f"(spec 109-01 AC #2)",
            )
        self.assertRegex(
            body_norm,
            r"simpler architecture.{0,300}acceptance criteria",
            "the leanness lens must be anchored to satisfying the acceptance "
            "criteria, not stripping required behavior (109-01 AC #2)",
        )

    def test_has_gotchas(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(any("gotchas" in h for h, _ in positions),
                        "missing 'Gotchas' H2")

    def test_has_relationship_to_other_skills(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("relationship to other skills" in h for h, _ in positions),
            "missing 'Relationship to other skills' H2",
        )

    def test_sections_in_order(self):
        """Sections must appear in the order specified by AC #2."""
        body_lower = self.body.lower()
        expected_order = [
            "what this skill does",
            "when to use",
            "inputs",
            "review structure",
            "gotchas",
            "relationship to other skills",
        ]
        positions = []
        for phrase in expected_order:
            idx = body_lower.find(phrase)
            self.assertGreater(
                idx, -1, f"section header {phrase!r} not found in body",
            )
            positions.append(idx)
        self.assertEqual(
            positions, sorted(positions),
            f"section order wrong; got positions {positions} for {expected_order}",
        )


class DeferralLanguageTests(unittest.TestCase):
    """AC #3 — body explicitly references `~/.claude/skills/arch-review` as
    the deferral target, and names the three sibling jig skills the reader
    should disambiguate from."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_body_references_user_skill_path(self):
        self.assertIn("~/.claude/skills/arch-review", self.body)

    def test_body_distinguishes_pr_review(self):
        # AC #2 — body must tell /jig:pr-review apart from this skill.
        self.assertIn("/jig:pr-review", self.body)

    def test_body_distinguishes_independent_review(self):
        # AC #2 — body must tell /jig:independent-review apart from this skill.
        self.assertIn("/jig:independent-review", self.body)

    def test_body_distinguishes_adr_workflow(self):
        # AC #2 — body must tell /jig:adr-workflow apart from this skill
        # (the review-vs-scaffold boundary).
        self.assertIn("/jig:adr-workflow", self.body)


class WorkedExampleTests(unittest.TestCase):
    """AC #10 — body contains one minimal worked example: a short design-doc
    fragment (~10-15 lines, at least one substantive choice worth reviewing)
    and the corresponding four-section review output (summary, one strength,
    one concern, one open question)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    def test_has_design_doc_or_diff_fragment(self):
        # Look for a fenced ``` block that contains either diff-style +/-
        # lines OR a short design-doc fragment (any fenced markdown block in
        # the body that is not a code-shape example wrapper). Either shape
        # counts as a "worked example fragment" per AC #10.
        in_block = False
        seen_block_content = False
        for line in self.body.splitlines():
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block and line.strip():
                seen_block_content = True
                break
        self.assertTrue(
            seen_block_content,
            "body must contain at least one fenced block with content "
            "(design-doc fragment or diff fragment for the worked example)",
        )

    def test_has_four_section_review_in_example(self):
        # The worked example should demonstrate the four output sections:
        # summary / strengths / concerns / open questions (the arch-review
        # variant; pr-review's labels are scope / blockers / nits /
        # strengths).
        for label in ["summary", "strengths", "concerns", "open questions"]:
            self.assertIn(label, self.body_lower,
                          f"worked example missing label: {label!r}")


if __name__ == "__main__":
    unittest.main()
