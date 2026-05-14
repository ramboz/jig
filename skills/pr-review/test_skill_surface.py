"""Surface tests for skills/pr-review/SKILL.md.

Covers AC #1 (frontmatter shape), AC #2 (body sections), AC #3 (description
trigger phrases + anti-greediness bounds + body refs + worked example), and
the deferral-language requirement from spec 012-01.

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
    """Match the normalization pattern from slice 006-01 design choice #7:
    YAML folded scalars insert newlines in raw bytes but parse to
    single-space-collapsed strings. Normalize so substring assertions match
    the parsed shape, not the raw bytes."""
    return " ".join(s.lower().split())


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(SKILL_MD.is_file(),
                        f"skills/pr-review/SKILL.md must exist at {SKILL_MD}")

    def test_has_frontmatter_block(self):
        fm = _frontmatter(self.text)
        self.assertTrue(fm, "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        fm = _frontmatter(self.text)
        self.assertRegex(fm, r"(?m)^name:\s*pr-review\s*$")

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
    """AC #3 — description contains the six trigger phrases + deferral hint
    + a "Do not use for" clause naming spec-compliance review."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_one_sentence_summary(self):
        # Post-012-01 hot-patch: description opens with the team-baseline
        # framing (was: "lightweight default pr review for jig projects").
        self.assertIn(
            "team baseline for pr and code review",
            self.normalized,
        )

    def test_six_trigger_phrases(self):
        phrases = [
            "review this pr",
            "check this diff",
            "review these changes",
            "pre-review before i share",
            "what do you think of this pr",
            "review the diff on this branch",
        ]
        for phrase in phrases:
            self.assertIn(phrase, self.normalized,
                          f"description missing trigger phrase: {phrase!r}")

    def test_deferral_hint_present(self):
        # Post-012-01 hot-patch: deferral is now category-based, not
        # name-specific (was: "if you have another `pr-review` skill
        # installed"). The new phrasing tells the router to defer to any
        # other installed skill whose description claims PR/code/diff
        # review.
        self.assertIn(
            "defers to any other installed skill whose description "
            "identifies it as handling pr review, code review, or "
            "diff review",
            self.normalized,
        )

    def test_excludes_bundled_review_skill_from_deferral(self):
        # Post-012-01 hot-patch: the description carves out the bundled
        # `review` skill explicitly so the deferral chain doesn't collapse
        # downward to the catch-all fallback.
        self.assertIn(
            "does not defer to the generic built-in `review` skill",
            self.normalized,
        )

    def test_do_not_use_clause_names_independent_review(self):
        self.assertRegex(self.normalized, r"do not use")
        self.assertIn("spec-compliance review", self.normalized)
        self.assertIn("/jig:independent-review", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """AC #3 (anti-greediness) — the normalized description does NOT contain
    over-claiming phrases that would shadow a richer user skill."""

    @classmethod
    def setUpClass(cls):
        cls.fm = _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.normalized = _normalize(cls.fm)

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive review",
            "deep code analysis",
            "expert-level",
            "multi-persona",
            "full audit",
            "security review",
            "architecture review",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, self.normalized,
                             f"description over-claims with phrase: {phrase!r}")


class BodyTests(unittest.TestCase):
    """AC #2 — body has the six H2 sections in order."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def _h2_positions(self, body: str):
        """Return list of (heading_text_lower, char_offset) for every H2."""
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
        self.assertTrue(any(h.strip() == "inputs" for h, _ in positions),
                        "missing 'Inputs' H2")

    def test_has_review_structure(self):
        positions = self._h2_positions(self.body)
        self.assertTrue(
            any("review structure" in h for h, _ in positions),
            "missing 'Review structure' H2",
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
    """Body explicitly references `~/.claude/skills/pr-review` as the
    deferral target — discoverable to users reading the SKILL.md body, not
    just the frontmatter description."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_body_references_user_skill_path(self):
        self.assertIn("~/.claude/skills/pr-review", self.body)

    def test_body_distinguishes_independent_review(self):
        # AC #2 — body must tell /jig:independent-review apart from this skill.
        self.assertIn("/jig:independent-review", self.body)

    def test_body_distinguishes_reviewer_subagent(self):
        # AC #2 — body must address the agents/reviewer.md neighborhood.
        self.assertIn("agents/reviewer.md", self.body)


class WorkedExampleTests(unittest.TestCase):
    """AC #10 — body contains one minimal worked example: a diff fragment
    and the corresponding four-section review (scope/blockers/nits/strengths)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_lower = cls.body.lower()

    def test_has_diff_fragment(self):
        # Look for diff-style markers (a fenced ``` block containing +/- lines)
        # in the body. We don't enforce a specific language; we just want
        # *some* diff-shaped content.
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
            "body must contain at least one fenced block with diff-style +/- lines",
        )

    def test_has_four_section_review_in_example(self):
        # The worked example should demonstrate the four output sections.
        # We assert all four labels appear in the body (case-insensitive).
        for label in ["scope", "blockers", "nits", "strengths"]:
            self.assertIn(label, self.body_lower,
                          f"worked example missing label: {label!r}")


if __name__ == "__main__":
    unittest.main()
