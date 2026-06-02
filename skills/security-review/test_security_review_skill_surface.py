"""Surface tests for skills/security-review/SKILL.md (slice 052-05).

Mirrors the surface-test pattern established by
`skills/pr-review/test_skill_surface.py` (slice 012-01) and reused by
`skills/arch-review/` and `skills/analyze/`. Pins every AC for slice
052-05:

  AC #1 — the skill exists and auto-triggers (active frontmatter, no
          disable-model-invocation, user-invocable, six trigger phrasings).
  AC #2 — defers to richer installed skills via a CATEGORY-based deferral
          hint (security review / SAST / vulnerability analysis), not a
          name-based one; plus do-not-use-for carve-outs.
  AC #3 / AC #7 — orchestrates installed scanners (scanner-PRESENT path
          names ≥3 of semgrep/bandit/gosec/npm audit/osv-scanner) AND
          degrades gracefully (scanner-ABSENT heuristic-only path), both
          described in the body.
  AC #4 — heuristic baseline floor: the eight named categories + the
          four-bucket verdict envelope (summary / blockers / nits /
          strengths).
  AC #5 — honest framing: best-effort heuristic baseline, not a guarantee,
          not a substitute for CI scanning / dedicated review / richer
          installed skill; real controls out-of-band.

These tests are pure-file inspections — no subprocess, no runner. They
run under the same `python3 scripts/run_tests.py` invocation used for
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
    """Match the normalization pattern used across jig skill surface tests
    (slice 012-01 design choice #7): YAML folded scalars insert newlines
    in raw bytes but parse to single-space-collapsed strings. Normalize
    so substring assertions match the parsed shape, not the raw bytes."""
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
        self.assertTrue(
            SKILL_MD.is_file(),
            f"skills/security-review/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*security-review\s*$")

    def test_user_invocable_true(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1: this skill auto-triggers. Per ADR-0013 the baseline ships
        # active (no fallback inversion at ship time).
        fm = _frontmatter(self.text)
        self.assertNotIn("disable-model-invocation: true", fm)


class DescriptionTests(unittest.TestCase):
    """AC #1 / AC #2 — description carries the standalone-baseline framing,
    six trigger phrasings, the category-based deferral hint, and the
    do-not-use-for carve-outs."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_standalone_baseline_framing(self):
        # AC #1 — team-baseline / best-effort heuristic framing in the opener.
        self.assertIn("team baseline", self.normalized)
        self.assertIn("best-effort heuristic security pass", self.normalized)

    def test_six_trigger_phrases(self):
        phrases = [
            "review this for security",
            "any vulnerabilities here",
            "security pass on this diff",
            "is this code secure",
            "check this for security issues",
            "security review this",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_category_based_deferral_hint_present(self):
        # AC #2 — the deferral is CATEGORY-based (security review / SAST /
        # vulnerability analysis), mirroring pr-review's wording; NOT a
        # name match against `security-review`.
        self.assertIn(
            "defers to any other installed skill whose description "
            "identifies it as handling security review, sast, or "
            "vulnerability analysis",
            self.normalized,
        )

    def test_deferral_hint_names_router_resolved_examples(self):
        # AC #2 — names the user's own / Adobe's adobe-security-* family /
        # a built-in security-review as the routes the router may resolve,
        # while keeping the hint category-based.
        self.assertIn("adobe-security-", self.normalized)
        self.assertIn("prefer it over this slim baseline", self.normalized)

    def test_do_not_use_carve_outs(self):
        # AC #2 — three carve-outs: spec-compliance → independent-review;
        # general PR craft → pr-review; secret prevention is the hook.
        self.assertRegex(self.normalized, r"do not use")
        self.assertIn("spec-compliance review", self.normalized)
        self.assertIn("/jig:independent-review", self.normalized)
        self.assertIn("/jig:pr-review", self.normalized)
        self.assertIn("jig-secret-scan", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """AC #1 / AC #5 (anti-greediness) — the normalized description does NOT
    contain over-claiming phrases that would shadow a richer user skill.

    Intentional asymmetry (mirrors arch-review's bounds test): the category
    names "security review", "sast", and "vulnerability analysis" are NOT
    forbidden because AC #2 mandates them in the deferral hint. The bounds
    test fires on depth-claims and guarantee-claims, not category names."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive security",
            "deep security analysis",
            "expert-level",
            "full audit",
            "penetration test",
            "guarantees",
            "sast engine",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.normalized,
                f"description over-claims with phrase: {phrase!r}",
            )


class BodyTests(unittest.TestCase):
    """AC #1 / AC #3 / AC #4 — body has the required H2 sections in order."""

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

    def test_has_orchestrate_installed_scanners(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("orchestrate installed scanners" in h for h, _ in positions),
            "missing 'Orchestrate installed scanners' H2",
        )

    def test_has_heuristic_baseline_categories(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("heuristic baseline categories" in h for h, _ in positions),
            "missing 'Heuristic baseline categories' H2",
        )

    def test_has_review_structure(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("review structure" in h or "output" in h for h, _ in positions),
            "missing 'Review structure / output' H2",
        )

    def test_has_honest_framing(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("honest framing" in h for h, _ in positions),
            "missing 'Honest framing' H2",
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
        """H2 section *headings* must appear in the spec-mandated order.

        Match against `_h2_positions` (real headings, fenced blocks
        stripped) rather than raw `body.find`: this SKILL.md uses inline
        cross-references (e.g. `[Honest framing](#honest-framing)`) and
        category prose that would make a naive substring search match
        body text before its heading."""
        expected_order = [
            "what this skill does",
            "when to use",
            "orchestrate installed scanners",
            "heuristic baseline categories",
            "review structure",
            "honest framing",
            "gotchas",
            "relationship to other skills",
        ]
        h2s = self._h2_positions(self.body)
        positions = []
        for phrase in expected_order:
            matches = [off for heading, off in h2s if phrase in heading]
            self.assertTrue(
                matches, f"section heading {phrase!r} not found among H2s",
            )
            positions.append(matches[0])
        self.assertEqual(
            positions, sorted(positions),
            f"section order wrong; got positions {positions} for {expected_order}",
        )


class CategoryTests(unittest.TestCase):
    """AC #4 — all eight heuristic-baseline category names present in body."""

    @classmethod
    def setUpClass(cls):
        cls.body_lower = (
            _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        ).lower()

    EXPECTED_CATEGORIES = [
        "secrets",
        "injection",
        "authn/authz",
        "crypto misuse",
        "input validation",
        "unsafe deserialization",
        "dangerous functions",
        "dependency risk",
    ]

    def test_all_eight_categories_present(self):
        for category in self.EXPECTED_CATEGORIES:
            self.assertIn(
                category, self.body_lower,
                f"heuristic baseline missing category: {category!r}",
            )


class OrchestrationPathsTests(unittest.TestCase):
    """AC #3 / AC #7 — both orchestration paths documented: scanner-PRESENT
    (names the scanners + runs the ones on PATH) and scanner-ABSENT (graceful
    degradation to heuristic-only). 'Never bundle / install nothing.'"""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    SCANNERS = ["semgrep", "bandit", "gosec", "npm audit", "osv-scanner"]

    def test_scanner_present_path_names_three_plus_scanners(self):
        present = sum(1 for s in self.SCANNERS if s in self.body_lower)
        self.assertGreaterEqual(
            present, 3,
            f"scanner-present path must name at least 3 of "
            f"{self.SCANNERS}; found {present}",
        )

    def test_detects_on_path(self):
        # AC #3 — detect scanners on PATH and run the ones present.
        self.assertIn("path", self.body_lower)

    def test_install_nothing(self):
        # AC #3 — never bundle; install nothing.
        self.assertTrue(
            "install nothing" in self.body_lower
            or "installs nothing" in self.body_lower
            or "never bundle" in self.body_lower,
            "body must state it installs nothing / never bundles scanners",
        )

    def test_scanner_absent_graceful_degradation(self):
        # AC #3 / AC #7 — degrade gracefully to heuristic-only when none
        # is present.
        self.assertTrue(
            "heuristic-only" in self.body_lower
            or "degrade gracefully" in self.body_lower
            or "degrades gracefully" in self.body_lower,
            "body must describe graceful degradation to heuristic-only "
            "when no scanner is present",
        )

    def test_both_paths_explicitly_described(self):
        # AC #7 — BOTH the scanner-present and scanner-absent paths are
        # described, not merely the union of keywords.
        self.assertIn("when present", self.body_lower)
        self.assertTrue(
            "when none" in self.body_lower or "if none" in self.body_lower
            or "no scanner" in self.body_lower,
            "body must describe the no-scanner path explicitly",
        )


class ReviewEnvelopeTests(unittest.TestCase):
    """AC #4 — the four-bucket verdict envelope (summary / blockers / nits /
    strengths), the shape jig's other review skills use, with file:line
    citations."""

    @classmethod
    def setUpClass(cls):
        cls.body_lower = (
            _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        ).lower()

    def test_four_bucket_envelope_present(self):
        for label in ["summary", "blockers", "nits", "strengths"]:
            self.assertIn(
                label, self.body_lower,
                f"review envelope missing bucket: {label!r}",
            )

    def test_file_line_citation_documented(self):
        # AC #4 — blockers/nits cite file:line (matches pr-review's shape).
        self.assertIn("file:line", self.body_lower)


class HonestFramingTests(unittest.TestCase):
    """AC #5 — honest framing present: best-effort heuristic baseline, not a
    guarantee, not a substitute for CI scanning / a dedicated review / a
    richer installed skill; real controls out-of-band."""

    @classmethod
    def setUpClass(cls):
        cls.body_lower = (
            _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        ).lower()

    def test_not_a_guarantee(self):
        self.assertIn("not a guarantee", self.body_lower)

    def test_not_a_substitute(self):
        self.assertIn("not a substitute", self.body_lower)

    def test_out_of_band_controls(self):
        # AC #5 — real controls are out-of-band (CI SAST / secret-scanning /
        # dependency monitoring / branch protection).
        self.assertIn("out-of-band", self.body_lower)
        self.assertTrue(
            "ci" in self.body_lower,
            "honest framing must point to CI security scanning as the "
            "real control",
        )

    def test_secret_scan_is_prevention_this_is_review(self):
        # AC #5 — the jig-secret-scan hook covers prevention; this skill
        # covers review.
        self.assertIn("jig-secret-scan", self.body_lower)
        self.assertIn("prevention", self.body_lower)


class DeferralLanguageTests(unittest.TestCase):
    """AC #2 — body names the richer-skill routes (the user's own /
    adobe-security-* / built-in security-review) and the sibling jig skills
    a reader should disambiguate from."""

    @classmethod
    def setUpClass(cls):
        cls.body_lower = (
            _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        ).lower()

    def test_body_names_adobe_security_family(self):
        self.assertIn("adobe-security-", self.body_lower)

    def test_body_distinguishes_pr_review(self):
        self.assertIn("/jig:pr-review", self.body_lower)

    def test_body_distinguishes_independent_review(self):
        self.assertIn("/jig:independent-review", self.body_lower)

    def test_body_distinguishes_secret_scan_hook(self):
        self.assertIn("jig-secret-scan", self.body_lower)


class WorkedExampleTests(unittest.TestCase):
    """AC #4 — body contains a worked example: a diff fragment and the
    corresponding four-bucket review (summary / blockers / nits /
    strengths)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    def test_has_diff_fragment(self):
        in_block = False
        has_diff_line = False
        for line in self.body.splitlines():
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block and (line.startswith("+") or line.startswith("-")) \
                    and not line.startswith(("+++", "---")):
                has_diff_line = True
                break
        self.assertTrue(
            has_diff_line,
            "body must contain at least one fenced block with diff-style "
            "+/- lines for the worked example",
        )

    def test_has_four_bucket_review_in_example(self):
        for label in ["summary", "blockers", "nits", "strengths"]:
            self.assertIn(
                label, self.body_lower,
                f"worked example missing label: {label!r}",
            )


class NoPyHelperTests(unittest.TestCase):
    """ADR-0013 / spec — security-review is a judgment skill. SKILL.md only,
    no `.py` helper (like pr-review / arch-review)."""

    def test_no_security_review_py(self):
        py_file = SKILL_DIR / "security_review.py"
        self.assertFalse(
            py_file.is_file(),
            f"security-review is a judgment skill: "
            f"{py_file} must not exist",
        )


if __name__ == "__main__":
    unittest.main()
