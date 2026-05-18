"""Surface tests for skills/clarify/SKILL.md (slice 023-01).

Mirrors the surface-test pattern from skills/pr-review/test_skill_surface.py
and skills/contracts/test_contracts_skill_surface.py. Pins every AC for
slice 023-01:

  AC #1 — frontmatter is active (no disable-model-invocation; team-baseline
          framing; six trigger phrases; do-not-use-for clause with
          spec-compliance / cross-artifact / project-vision carve-outs)
  AC #2 — body has the required H2 sections in order
  AC #3 — six-category taxonomy section with the exact category names
          and "what to check" bullet lists (3+ bullets each)
  AC #4 — output format (`## Clarifications` section shape) documented in
          body
  AC #5 — this file IS the surface-pinning test class set; six classes
          (Frontmatter / Description / DescriptionBounds / Body /
          TaxonomyCoverage / WorkedExample)
  AC #6 — two worked-example sibling files exist with the canonical
          three-section shape (input excerpt / Q&A trace / coverage
          summary)
  AC #7 — no clarify.py exists in skills/clarify/

These tests are pure-file inspections — no subprocess, no runner. They
run under the same `python3 scripts/run_tests.py` invocation used for
every other jig skill.

Per user direction on 2026-05-18, the description does NOT include a
category-based deferral hint to spec-kit's `/speckit.clarify`. Jig's
clarify ships as a standalone baseline.
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"
WORKED_JIG = SKILL_DIR / "worked-example-jig.md"
WORKED_SAAS = SKILL_DIR / "worked-example-saas.md"


def _frontmatter(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else ""


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


def _normalize(s: str) -> str:
    """Match the normalization pattern used across jig skill surface tests
    (slice 012-01 design choice #7): YAML folded scalars insert newlines
    in raw bytes but parse to single-space-collapsed strings. Normalize
    so substring assertions match the parsed shape, not the raw bytes."""
    return " ".join(s.lower().split())


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(
            SKILL_MD.is_file(),
            f"skills/clarify/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*clarify\s*$")

    def test_user_invocable_true(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1: this skill auto-triggers. The standalone-baseline framing
        # (per user direction 2026-05-18) does not invert this default.
        fm = _frontmatter(self.text)
        self.assertNotIn("disable-model-invocation: true", fm)


class DescriptionTests(unittest.TestCase):
    """AC #1 — description contains the one-sentence purpose, six trigger
    phrases, and the Do-not-use-for clause naming three exclusions."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_one_sentence_summary_exact_phrasing(self):
        # AC #1 specifies the exact phrasing of the opening sentence.
        self.assertIn(
            "lightweight spec clarification scan for jig projects",
            self.normalized,
        )
        self.assertIn(
            "a six-category ambiguity audit that asks up to five "
            "prioritized questions and appends them to the spec's "
            "`## clarifications` section",
            self.normalized,
        )

    def test_six_trigger_phrases(self):
        phrases = [
            "clarify this spec",
            "audit this spec for ambiguities",
            "is this spec ready for review",
            "find unknowns in this scope",
            "scan for unanswered questions",
            "what's missing from this spec",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_do_not_use_clause_three_exclusions(self):
        # AC #1 — three exclusions in this exact order with this exact phrasing.
        self.assertRegex(self.normalized, r"do not use for")
        # (a) spec-compliance review carve-out routes to /jig:independent-review.
        self.assertIn("spec-compliance review of a finished slice", self.normalized)
        self.assertIn("use `/jig:independent-review` instead", self.normalized)
        # (b) cross-artifact consistency analysis routes to /jig:analyze.
        self.assertIn(
            "cross-artifact consistency analysis or drift detection",
            self.normalized,
        )
        self.assertIn("use `/jig:analyze` instead", self.normalized)
        # (c) project-vision or architecture elicitation routes to vision-elicitation.
        self.assertIn(
            "project-vision or architecture elicitation",
            self.normalized,
        )
        self.assertIn("use `/jig:vision-elicitation` instead", self.normalized)

    def test_alternatives_referenced(self):
        # AC #5 (DescriptionTests sub-clause): independent-review, analyze,
        # vision-elicitation all named as explicit alternatives.
        for slash in (
            "/jig:independent-review",
            "/jig:analyze",
            "/jig:vision-elicitation",
        ):
            self.assertIn(
                slash, self.normalized,
                f"description missing alternative reference: {slash!r}",
            )


class DescriptionBoundsTests(unittest.TestCase):
    """AC #5 (anti-greediness) — the normalized description does NOT
    contain over-claiming phrases that would shadow a richer downstream
    or sibling skill. Same pattern as 012-01's DescriptionBoundsTests."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive review",
            "deep analysis",
            "expert-level",
            "full audit",
            "specification author",
            "writes the spec for you",
            "interprets your requirements",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.normalized,
                f"description over-claims with phrase: {phrase!r}",
            )


class BodyTests(unittest.TestCase):
    """AC #2 — body has the required H2 sections in order."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def _h2_positions(self, body: str):
        results = []
        for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body):
            results.append((m.group(1).lower(), m.start()))
        return results

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
        self.assertTrue(
            any(h.strip() == "inputs" for h, _ in positions),
            "missing 'Inputs' H2",
        )

    def test_has_taxonomy(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("six-category taxonomy" in h for h, _ in positions),
            "missing 'Six-category taxonomy' H2",
        )

    def test_has_question_loop(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("question-asking loop" in h for h, _ in positions),
            "missing 'Question-asking loop' H2",
        )

    def test_has_output_section(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any(
                "output" in h and "clarifications" in h
                for h, _ in positions
            ),
            "missing 'Output: the `## Clarifications` section' H2",
        )

    def test_has_gotchas(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("gotchas" in h for h, _ in positions),
            "missing 'Gotchas' H2",
        )

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
            "six-category taxonomy",
            "question-asking loop",
            "output:",
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

    def test_body_references_four_neighbors(self):
        # AC #2 — "When to use vs. when to defer" distinguishes from four
        # neighbor skills.
        body_lower = self.body.lower()
        for slash in (
            "/jig:spec-workflow",
            "/jig:analyze",
            "/jig:vision-elicitation",
            "/jig:independent-review",
        ):
            self.assertIn(
                slash, body_lower,
                f"body must reference neighbor skill: {slash!r}",
            )

    def test_gotchas_covers_verbatim_advisory_one_doc_no_helper(self):
        # AC #2 — Gotchas section covers the four explicit notes (a)-(d).
        body_lower = self.body.lower()
        # (a) verbatim-answer rule
        self.assertIn("verbatim", body_lower)
        # (b) advisory-not-gate
        self.assertIn("advisory", body_lower)
        # (c) one-doc-at-a-time scope
        self.assertIn("one-doc-at-a-time", body_lower)
        # (d) no .py helper — section surgery via Read + Edit
        self.assertIn("read + edit", body_lower)


class TaxonomyCoverageTests(unittest.TestCase):
    """AC #3 — all six category names present in the body as H3 headings;
    each H3 followed by at least one bullet list with three or more items."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    EXPECTED_CATEGORIES = [
        "Scope & Boundaries",
        "Acceptance Criteria Testability",
        "Dependencies & Blockers",
        "Non-functional Requirements",
        "Edge Cases & Failure Modes",
        "Terminology Consistency",
    ]

    def _h3_blocks(self, body: str):
        """Return [(heading_text, block_text), ...] for every H3 in the body.
        block_text is everything from the H3 line up to (but not including)
        the next H2 or H3 heading."""
        blocks = []
        positions = []
        for m in re.finditer(r"(?m)^###\s+(.+?)\s*$", body):
            positions.append((m.group(1), m.start(), m.end()))
        # Also collect H2 positions so an H3 block ends at the next H2 too.
        h2_starts = [m.start() for m in re.finditer(r"(?m)^##\s+", body)]
        for i, (heading, start, end) in enumerate(positions):
            next_h3_start = (
                positions[i + 1][1] if i + 1 < len(positions) else len(body)
            )
            # First H2 after this H3 (must come after `end`).
            next_h2_starts = [s for s in h2_starts if s > end]
            next_h2_start = (
                next_h2_starts[0] if next_h2_starts else len(body)
            )
            block_end = min(next_h3_start, next_h2_start)
            blocks.append((heading, body[start:block_end]))
        return blocks

    def test_all_six_categories_present_as_h3(self):
        blocks = self._h3_blocks(self.body)
        headings = [h for h, _ in blocks]
        for category in self.EXPECTED_CATEGORIES:
            self.assertTrue(
                any(category.lower() in h.lower() for h in headings),
                f"taxonomy missing H3 for category: {category!r}; "
                f"found H3s: {headings}",
            )

    def test_each_category_has_three_plus_bullets(self):
        blocks = self._h3_blocks(self.body)
        for category in self.EXPECTED_CATEGORIES:
            matching = [
                (h, b) for h, b in blocks if category.lower() in h.lower()
            ]
            self.assertTrue(
                matching,
                f"no H3 block found for category: {category!r}",
            )
            heading, block = matching[0]
            # Count bullet lines starting with `- ` or `* ` at the start of
            # a line (after the heading). The heading itself isn't a bullet.
            bullets = re.findall(r"(?m)^[-*]\s+\S", block)
            self.assertGreaterEqual(
                len(bullets), 3,
                f"category {category!r} (H3 heading {heading!r}) must have "
                f"at least 3 'what to check' bullets, found {len(bullets)}",
            )


class WorkedExampleTests(unittest.TestCase):
    """AC #6 — the two worked-example sibling files exist, each with the
    canonical three-section shape (input excerpt / Q&A trace / coverage
    summary)."""

    @classmethod
    def setUpClass(cls):
        cls.jig_exists = WORKED_JIG.is_file()
        cls.saas_exists = WORKED_SAAS.is_file()
        cls.jig_text = WORKED_JIG.read_text() if cls.jig_exists else ""
        cls.saas_text = WORKED_SAAS.read_text() if cls.saas_exists else ""

    def test_jig_worked_example_exists(self):
        self.assertTrue(
            self.jig_exists,
            f"worked-example-jig.md must exist at {WORKED_JIG}",
        )

    def test_saas_worked_example_exists(self):
        self.assertTrue(
            self.saas_exists,
            f"worked-example-saas.md must exist at {WORKED_SAAS}",
        )

    def _check_three_sections(self, text: str, label: str) -> None:
        text_lower = text.lower()
        # The three canonical sections: input excerpt / Q&A trace /
        # coverage summary. We match on the conceptual tokens, allowing
        # variation in exact H2 wording.
        self.assertTrue(
            "input" in text_lower or "spec excerpt" in text_lower
            or "draft" in text_lower,
            f"{label}: missing 'input excerpt' section",
        )
        # Q&A trace — must show at least one question + answer pair.
        # Use the per-entry shape: Q1, Q2, etc.
        self.assertRegex(
            text, r"(?m)^###\s*Q\d",
            f"{label}: missing Q&A entries shaped as `### Q<n>`",
        )
        # Coverage summary table — must include the word "coverage"
        # along with the six category names.
        self.assertIn(
            "coverage summary", text_lower,
            f"{label}: missing 'coverage summary' section",
        )
        for category in [
            "scope & boundaries",
            "acceptance criteria testability",
            "dependencies & blockers",
            "non-functional requirements",
            "edge cases & failure modes",
            "terminology consistency",
        ]:
            self.assertIn(
                category, text_lower,
                f"{label}: coverage summary missing category: {category!r}",
            )

    def test_jig_worked_example_three_sections(self):
        if not self.jig_exists:
            self.skipTest("worked-example-jig.md missing — see file_exists test")
        self._check_three_sections(self.jig_text, "worked-example-jig.md")

    def test_saas_worked_example_three_sections(self):
        if not self.saas_exists:
            self.skipTest("worked-example-saas.md missing — see file_exists test")
        self._check_three_sections(self.saas_text, "worked-example-saas.md")

    def test_jig_worked_example_targets_real_jig_spec(self):
        # AC #6 — first worked example pulls from a real DRAFT-state jig
        # spec (per spec body: candidate is spec 018-slice-per-file or
        # spec 022-contracts).
        if not self.jig_exists:
            self.skipTest("worked-example-jig.md missing")
        text_lower = self.jig_text.lower()
        self.assertTrue(
            "018" in text_lower or "022" in text_lower
            or "slice-per-file" in text_lower or "contracts" in text_lower,
            "jig worked example must target a real jig spec "
            "(018-slice-per-file or 022-contracts)",
        )

    def test_saas_worked_example_targets_oauth(self):
        # AC #6 — second worked example is "add OAuth login to a SaaS app".
        if not self.saas_exists:
            self.skipTest("worked-example-saas.md missing")
        self.assertIn("oauth", self.saas_text.lower())


class NoPyHelperTests(unittest.TestCase):
    """AC #7 — skills/clarify/ does NOT gain a clarify.py helper."""

    def test_no_clarify_py(self):
        py_file = SKILL_DIR / "clarify.py"
        self.assertFalse(
            py_file.is_file(),
            f"AC #7: skills/clarify/clarify.py must not exist (found at {py_file})",
        )


if __name__ == "__main__":
    unittest.main()
