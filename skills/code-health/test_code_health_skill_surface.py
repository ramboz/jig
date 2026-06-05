"""Surface tests for skills/code-health/SKILL.md (slice 060-01).

Pure-file inspection — no subprocess, no runner. Mirrors the surface-test
pattern from skills/security-review/test_security_review_skill_surface.py
and skills/pr-review/test_skill_surface.py.

Pins AC #5:
  - active frontmatter (name: code-health, user-invocable: true, NO
    disable-model-invocation — this slice ships it active);
  - a verb-led description with auto-trigger phrases, a "defers to a richer
    installed skill" clause, and a "Do NOT use for…" block;
  - a body bash recipe that calls health.py;
  - the required H2 structure.
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
    """YAML folded scalars insert newlines in raw bytes but parse to
    single-space-collapsed strings — normalize so substring assertions match
    the parsed shape (slice 012-01 design choice, reused across jig)."""
    return " ".join(s.lower().split())


_FENCED_BLOCK_RE = re.compile(r"(?ms)^```.*?^```[ \t]*$")


def _strip_fenced_blocks(text: str) -> str:
    return _FENCED_BLOCK_RE.sub("", text)


class FrontmatterTests(unittest.TestCase):
    """AC #5 — active frontmatter."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(SKILL_MD.is_file(),
                        f"skills/code-health/SKILL.md must exist at {SKILL_MD}")

    def test_has_frontmatter_block(self):
        self.assertTrue(_frontmatter(self.text),
                        "SKILL.md must start with a YAML frontmatter block")

    def test_name_field(self):
        self.assertRegex(_frontmatter(self.text),
                         r"(?m)^name:\s*code-health\s*$")

    def test_user_invocable_true(self):
        self.assertRegex(_frontmatter(self.text),
                         r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #5 — this slice ships the skill active.
        self.assertNotIn("disable-model-invocation: true",
                         _frontmatter(self.text))


class DescriptionTests(unittest.TestCase):
    """AC #5 — verb-led description with trigger phrases, deferral clause,
    and a do-not-use-for block."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else ""))

    def test_trigger_phrases(self):
        phrases = [
            "lint this",
            "check code health",
            "run the linter",
            "is this code clean",
            "any lint issues",
            "static analysis",
        ]
        for phrase in phrases:
            self.assertIn(phrase, self.normalized,
                          f"description missing trigger phrase: {phrase!r}")

    def test_defers_to_richer_skill(self):
        # AC #5 — a "defers to a richer installed skill" clause.
        self.assertIn("defers to", self.normalized)

    def test_do_not_use_block(self):
        # AC #5 — a "Do NOT use for…" carve-out.
        self.assertRegex(self.normalized, r"do not use")

    def test_mentions_ruff(self):
        # Python + ruff is this slice's scope.
        self.assertIn("ruff", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """Anti-greediness — the description does not over-claim in a way that
    would shadow a richer installed skill (mirrors security-review bounds)."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else ""))

    def test_no_over_claiming(self):
        forbidden = [
            "comprehensive static analysis",
            "guarantees clean code",
            "full code audit",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, self.normalized,
                             f"description over-claims: {phrase!r}")


class BodyTests(unittest.TestCase):
    """AC #5 — required H2 sections + a health.py bash recipe."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""
        cls.body = _body(cls.text)
        cls.body_lower = cls.body.lower()

    def _h2_positions(self, body: str):
        body = _strip_fenced_blocks(body)
        return [(m.group(1).lower(), m.start())
                for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body)]

    def test_has_what_this_skill_does(self):
        self.assertTrue(
            any("what this skill does" in h for h, _ in self._h2_positions(self.body)),
            "missing 'What this skill does' H2")

    def test_has_when_not_to_use(self):
        self.assertTrue(
            any("when not to use" in h for h, _ in self._h2_positions(self.body)),
            "missing 'When NOT to use' H2")

    def test_has_helper_invocation_recipe(self):
        # A bash recipe calling `health.py … check` must be present. The path
        # is quoted in the recipe (`…/health.py" check`), so match the helper
        # name and the `check` subcommand independently rather than as one
        # contiguous string.
        self.assertIn("health.py", self.text)
        self.assertRegex(self.text, r'health\.py"?\s+check')
        self.assertIn("```bash", self.text)

    def test_documents_exit_codes(self):
        # AC #2 — 0 / 1 / 2 normalized exit codes documented in the surface.
        for code in ("0", "1", "2"):
            self.assertIn(code, self.body)
        self.assertIn("clean", self.body_lower)
        self.assertIn("findings", self.body_lower)

    def test_documents_override(self):
        # AC #4 — the .jig/lint-command override is documented.
        self.assertIn(".jig/lint-command", self.text)

    def test_documents_graceful_degradation(self):
        # AC #3 — the no-linter recommendation path is documented.
        self.assertTrue(
            "no python linter" in self.body_lower
            or "degrade" in self.body_lower,
            "body must document graceful degradation when no linter is found")


class NoExtraneousTests(unittest.TestCase):
    """code-health DOES ship a .py helper (unlike pr-review). Assert health.py
    is the helper alongside SKILL.md."""

    def test_health_py_exists(self):
        self.assertTrue((SKILL_DIR / "health.py").is_file(),
                        "code-health ships a deterministic health.py helper")


if __name__ == "__main__":
    unittest.main()
