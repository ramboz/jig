"""Surface tests for skills/analyze/SKILL.md (slice 024-01).

Mirrors the surface-test pattern from skills/clarify/test_clarify_skill_surface.py
and skills/contracts/test_contracts_skill_surface.py. Pins every AC for
slice 024-01:

  AC #1 — frontmatter is active (no disable-model-invocation; standalone
          baseline framing; six trigger phrases; do-not-use-for clause
          with three exclusions)
  AC #2 — body has the required H2 sections in order
  AC #3 — six finding categories section with exact category names
          and "what triggers a finding" bullet lists (3+ bullets each)
  AC #4 — output format (header → findings table → coverage summary →
          next steps) documented in body
  AC #5 — this file IS the surface-pinning test class set; six classes
          (Frontmatter / Description / DescriptionBounds / Body /
          FindingCategory / WorkedExample)
  AC #7 — two worked-example sibling files exist with the canonical
          sections (input excerpt / findings table / coverage summary)

These tests are pure-file inspections — no subprocess, no runner. They
run under the same `python3 scripts/run_tests.py` invocation used for
every other jig skill.

Per user direction on 2026-05-18, the description does NOT include a
category-based deferral hint to spec-kit's `/speckit.analyze`. Jig's
analyze ships as a standalone baseline.
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


_FENCED_BLOCK_RE = re.compile(r"(?ms)^```.*?^```[ \t]*$")


def _strip_fenced_blocks(text: str) -> str:
    """Remove fenced ```...``` regions so H2/H3-shaped lines inside code
    examples don't trip the `_h2_positions` / `_h3_blocks` regex helpers.
    Offsets refer to the returned (stripped) body, not the source."""
    return _FENCED_BLOCK_RE.sub("", text)


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(
            SKILL_MD.is_file(),
            f"skills/analyze/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*analyze\s*$")

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
            "cross-artifact consistency report for jig specs",
            self.normalized,
        )
        self.assertIn(
            "a non-destructive six-category audit at "
            "critical/high/medium/low severity",
            self.normalized,
        )
        for category in [
            "duplication",
            "ambiguity",
            "underspecification",
            "principle violations",
            "coverage gaps",
            "terminology drift",
        ]:
            self.assertIn(
                category, self.normalized,
                f"description summary missing category: {category!r}",
            )

    def test_six_trigger_phrases(self):
        phrases = [
            "analyze this spec",
            "check for inconsistencies",
            "audit adr vs spec drift",
            "cross-artifact alignment",
            "find drift in this spec",
            "audit this spec for principle violations",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_do_not_use_clause_three_exclusions(self):
        # AC #1 — three exclusions in this exact order with this exact phrasing.
        self.assertRegex(self.normalized, r"do not use for")
        # (a) pre-DRAFT ambiguity scanning routes to /jig:clarify.
        self.assertIn(
            "pre-draft ambiguity scanning",
            self.normalized,
        )
        self.assertIn("use `/jig:clarify` instead", self.normalized)
        # (b) structural frontmatter / slice-numbering routes to spec_lint.py.
        self.assertIn(
            "structural frontmatter or slice-numbering validation",
            self.normalized,
        )
        self.assertIn("use `spec_lint.py` instead", self.normalized)
        # (c) spec-compliance review routes to /jig:independent-review.
        self.assertIn(
            "spec-compliance review of a finished slice",
            self.normalized,
        )
        self.assertIn("use `/jig:independent-review` instead", self.normalized)

    def test_alternatives_referenced(self):
        # AC #5 (DescriptionTests sub-clause): clarify, spec_lint.py,
        # independent-review all named as explicit alternatives.
        for slash in (
            "/jig:clarify",
            "spec_lint.py",
            "/jig:independent-review",
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
            "comprehensive analysis",
            "deep dive",
            "expert review",
            "full audit",
            "writes findings to disk",
            "fixes the findings",
            "automated remediation",
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
        self.assertTrue(
            any(h.strip() == "inputs" for h, _ in positions),
            "missing 'Inputs' H2",
        )

    def test_has_six_finding_categories(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("six finding categories" in h for h, _ in positions),
            "missing 'Six finding categories' H2",
        )

    def test_has_severity_scoring(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("severity scoring" in h for h, _ in positions),
            "missing 'Severity scoring' H2",
        )

    def test_has_output_format(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("output format" in h for h, _ in positions),
            "missing 'Output format' H2",
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
            "six finding categories",
            "severity scoring",
            "output format",
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
            "/jig:clarify",
            "spec_lint.py",
            "/jig:independent-review",
            "/jig:pr-review",
        ):
            self.assertIn(
                slash, body_lower,
                f"body must reference neighbor skill: {slash!r}",
            )

    def test_what_this_skill_does_emphasizes_reporter_only(self):
        # AC #2 — opening paragraph emphasizes "reporter only, no file writes"
        # up front.
        body_lower = self.body.lower()
        self.assertTrue(
            "reporter only" in body_lower or "no file writes" in body_lower
            or "non-destructive" in body_lower,
            "first H2 must frame skill as reporter-only / non-destructive",
        )

    def test_inputs_section_lists_required_sources(self):
        # AC #2 — Inputs lists the four read-only secondary inputs.
        body_lower = self.body.lower()
        self.assertIn("docs/product-vision.md", body_lower)
        self.assertIn("docs/decisions/", body_lower)
        self.assertIn("docs/memory/glossary.md", body_lower)
        self.assertIn("docs/architecture.md", body_lower)

    def test_gotchas_covers_four_explicit_notes(self):
        # AC #2 — Gotchas covers (a) non-destructive, (b) one-spec-at-a-time,
        # (c) severity table subject to judgment, (d) no .py helper for
        # analyze itself.
        body_lower = self.body.lower()
        # (a) non-destructive — skill never writes
        self.assertTrue(
            "non-destructive" in body_lower or "never writes" in body_lower,
            "Gotchas must cover non-destructive / never writes",
        )
        # (b) one-spec-at-a-time scope
        self.assertIn("one-spec-at-a-time", body_lower)
        # (c) principle-violation severity table subject to judgment
        self.assertIn("judgment", body_lower)
        # (d) no .py helper — reviewer-prompt principles-check is separate
        self.assertTrue(
            "no .py helper" in body_lower or "no helper" in body_lower,
            "Gotchas must call out the no-helper choice",
        )


class FindingCategoryTests(unittest.TestCase):
    """AC #3 — all six category names present in the body as H3 headings;
    each H3 followed by at least one bullet list with three or more items."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    EXPECTED_CATEGORIES = [
        "Duplication",
        "Ambiguity",
        "Underspecification",
        "Principle Violations",
        "Coverage Gaps",
        "Terminology Drift",
    ]

    def _h3_blocks(self, body: str):
        """Return [(heading_text, block_text), ...] for every H3 in the body.
        block_text is everything from the H3 line up to (but not including)
        the next H2 or H3 heading."""
        body = _strip_fenced_blocks(body)
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
                f"finding categories missing H3 for: {category!r}; "
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
                f"at least 3 'what triggers a finding' bullets, found "
                f"{len(bullets)}",
            )


class OutputFormatTests(unittest.TestCase):
    """AC #4 — output format documented in body with the four-section
    shape (header / findings table / coverage summary / next steps)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_documents_findings_table_columns(self):
        # AC #4 — findings table columns: # / Severity / Category /
        # Location / Finding.
        body_lower = self.body.lower()
        for col in ("severity", "category", "location", "finding"):
            self.assertIn(
                col, body_lower,
                f"output format must document findings-table column: {col!r}",
            )

    def test_documents_coverage_summary(self):
        body_lower = self.body.lower()
        self.assertIn("coverage summary", body_lower)

    def test_documents_next_steps(self):
        body_lower = self.body.lower()
        self.assertIn("next steps", body_lower)

    def test_documents_severity_levels(self):
        body_lower = self.body.lower()
        for level in ("critical", "high", "medium", "low"):
            self.assertIn(
                level, body_lower,
                f"output format must document severity level: {level!r}",
            )

    def test_documents_max_50_findings(self):
        body_lower = self.body.lower()
        self.assertIn("50", body_lower)
        self.assertTrue(
            "truncated" in body_lower,
            "output format must mention truncation behavior at 50 findings",
        )


class WorkedExampleTests(unittest.TestCase):
    """AC #7 — the two worked-example sibling files exist, each with the
    canonical sections (input excerpt / findings table / coverage
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
        # Input excerpt section
        self.assertTrue(
            "input" in text_lower or "spec excerpt" in text_lower
            or "draft" in text_lower,
            f"{label}: missing 'input excerpt' section",
        )
        # Findings table — must include at least one row with a severity
        # token (CRITICAL / HIGH / MEDIUM / LOW). Tolerate the markdown
        # table shape; just require both 'findings' and at least one
        # severity word.
        self.assertIn(
            "findings", text_lower,
            f"{label}: missing 'findings' section",
        )
        self.assertTrue(
            any(level in text for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")),
            f"{label}: findings must include at least one severity token",
        )
        # Coverage summary table — must include the word "coverage"
        # along with the six category names.
        self.assertIn(
            "coverage summary", text_lower,
            f"{label}: missing 'coverage summary' section",
        )
        for category in [
            "duplication",
            "ambiguity",
            "underspecification",
            "principle violations",
            "coverage gaps",
            "terminology drift",
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
        # AC #7 — first worked example targets a real jig spec with known
        # drift. Spec 017 (vision-elicitation) during its mid-reshape
        # window is the lean candidate per spec body.
        if not self.jig_exists:
            self.skipTest("worked-example-jig.md missing")
        text_lower = self.jig_text.lower()
        self.assertTrue(
            "017" in text_lower or "vision-elicitation" in text_lower,
            "jig worked example must target spec 017-vision-elicitation "
            "(mid-reshape drift candidate)",
        )

    def test_saas_worked_example_targets_oauth(self):
        # AC #7 — second worked example is a non-jig hypothetical with
        # deliberate drift (OAuth-login spec).
        if not self.saas_exists:
            self.skipTest("worked-example-saas.md missing")
        self.assertIn("oauth", self.saas_text.lower())

    def test_jig_worked_example_spans_four_plus_categories(self):
        # Spec body, AC #7: "4-6 findings spanning at least 4 of the 6
        # categories with documented severities".
        if not self.jig_exists:
            self.skipTest("worked-example-jig.md missing")
        text_lower = self.jig_text.lower()
        present = sum(
            1
            for category in [
                "duplication",
                "ambiguity",
                "underspecification",
                "principle violations",
                "coverage gaps",
                "terminology drift",
            ]
            if category in text_lower
        )
        self.assertGreaterEqual(
            present, 4,
            f"jig worked example must reference at least 4 of 6 categories; "
            f"found {present}",
        )


class NoPyHelperTests(unittest.TestCase):
    """Spec Non-goals — skills/analyze/ does NOT gain an analyze.py
    helper. SKILL.md only (judgment-skill archetype)."""

    def test_no_analyze_py(self):
        py_file = SKILL_DIR / "analyze.py"
        self.assertFalse(
            py_file.is_file(),
            f"spec Non-goals: skills/analyze/analyze.py must not exist "
            f"(found at {py_file})",
        )


class SpecLintReferenceShapeTests(unittest.TestCase):
    """Spec 075-02 — every `scripts/spec_lint.py` reference in SKILL.md must
    be the resolvable plugin-root form (`${CLAUDE_PLUGIN_ROOT}/scripts/...`),
    never the bare relative `scripts/spec_lint.py` that does not resolve from
    a consuming project's CWD. The bare *tool name* `spec_lint.py` (no path)
    is allowed for purely descriptive mentions. This is the file-local guard
    against a regression to the bad relative path (the slice's AC4 grep is the
    cross-surface backstop; this pins the analyze SKILL specifically)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_no_bare_relative_scripts_path(self):
        bare = self.text.count("scripts/spec_lint.py")
        plugin_root = self.text.count("${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py")
        self.assertEqual(
            bare, plugin_root,
            "every `scripts/spec_lint.py` in SKILL.md must be the plugin-root "
            f"form; found {bare} occurrence(s) of `scripts/spec_lint.py` but "
            f"only {plugin_root} carry the ${{CLAUDE_PLUGIN_ROOT}} prefix — a "
            "bare relative path would not resolve in a consuming project",
        )


if __name__ == "__main__":
    unittest.main()
