"""Surface tests for skills/explain/SKILL.md (slice 065-03).

Pure-file inspection — no subprocess, no runner. Mirrors the surface-test
pattern from skills/clarify/test_clarify_skill_surface.py and
skills/code-health/test_code_health_skill_surface.py.

Pins the structural, unit-testable ACs of slice 065-03 (the plain-language
*quality* of ACs 2/3 is judgment, not unit-testable — the accepted gap for a
judgment-only jig skill, recorded in the spec coverage summary):

  AC #1 — the skill is registered + discoverable: SKILL.md exists with active
          frontmatter (name: explain, user-invocable: true, NO
          disable-model-invocation); the description declares both invocation
          styles (auto + explicit) and the two modes; AND the skill is listed
          in jig's per-tier inventory + the root CLAUDE.md skills table.
  AC #2 — term mode is documented (merged-lexicon def + example + see-also;
          absent term flagged, not invented).
  AC #3 — artifact mode is documented with the fixed six-block shape and the
          auto-pull-linked-refs behavior.
  AC #4 — the ephemeral contract is stated (writes nothing; no --save; no
          appended section).
  AC #5 — judgment-only, no helper: no explain.py exists; the body says lookups
          run inline via Read + the 065-01 loader.
  AC #6 — defers to a richer installed skill (plain-language explanation /
          onboarding / artifact walkthroughs) and does NOT defer to the generic
          built-in.
"""

import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REPO_ROOT = SKILL_DIR.parent.parent
ROOT_CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


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
    """Remove fenced ```...``` regions so H2/H3-shaped lines inside code
    examples don't trip the heading regex helpers."""
    return _FENCED_BLOCK_RE.sub("", text)


class FrontmatterTests(unittest.TestCase):
    """AC #1 — active frontmatter (name + user-invocable + no disable)."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text() if SKILL_MD.is_file() else ""

    def test_file_exists(self):
        self.assertTrue(
            SKILL_MD.is_file(),
            f"skills/explain/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        self.assertTrue(
            _frontmatter(self.text),
            "SKILL.md must start with a YAML frontmatter block",
        )

    def test_name_field(self):
        self.assertRegex(_frontmatter(self.text), r"(?m)^name:\s*explain\s*$")

    def test_user_invocable_true(self):
        self.assertRegex(_frontmatter(self.text), r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1: this skill auto-triggers (auto + explicit invocation styles).
        self.assertNotIn("disable-model-invocation: true", _frontmatter(self.text))


class DescriptionTests(unittest.TestCase):
    """AC #1 / #6 — description declares both modes, both invocation styles,
    auto-trigger phrases, the deferral clause, and a Do-not-use-for block."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        )

    def test_declares_both_modes(self):
        # AC #1 — the two modes are named in the description.
        self.assertIn("term mode", self.normalized)
        self.assertIn("artifact mode", self.normalized)

    def test_declares_both_invocation_styles(self):
        # AC #1 — auto (trigger phrases) + explicit (`/jig:explain`).
        self.assertIn("/jig:explain", self.normalized)
        self.assertIn("auto-triggers when you say", self.normalized)

    def test_has_auto_trigger_phrases(self):
        # A handful of natural-language trigger phrases for auto-invocation.
        phrases = [
            "explain this term",
            "walk me through this spec",
            "explain this adr",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_states_ephemeral_in_description(self):
        # AC #4 surfaced at the description level too — "chat-only".
        self.assertIn("ephemeral", self.normalized)
        self.assertIn("chat-only", self.normalized)

    def test_defers_to_richer_installed_skill(self):
        # AC #6 — defers to a richer installed skill identified as handling
        # plain-language explanation / onboarding / artifact walkthroughs.
        self.assertIn("defers to any other installed skill", self.normalized)
        self.assertIn("plain-language explanation", self.normalized)
        self.assertIn("onboarding", self.normalized)
        self.assertIn("artifact walkthroughs", self.normalized)

    def test_does_not_defer_to_generic_builtin(self):
        # AC #6 — explicit "does not defer to the generic built-in".
        self.assertIn("does not defer to the generic built-in", self.normalized)

    def test_do_not_use_clause(self):
        self.assertIn("do not use for", self.normalized)
        self.assertIn("use `/jig:independent-review` instead", self.normalized)
        self.assertIn("use `/jig:analyze` instead", self.normalized)
        self.assertIn("use `/jig:memory-sync` instead", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """AC #6 (anti-greediness) — the description does not over-claim in a way
    that would shadow a richer installed onboarding/explanation skill."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        )

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive",
            "deep analysis",
            "expert-level",
            "guarantees understanding",
            "certifies understanding",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.normalized,
                f"description over-claims with phrase: {phrase!r}",
            )


class BodyTests(unittest.TestCase):
    """AC #2/#3/#4/#5 — required body sections + their load-bearing content."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_norm = _normalize(cls.body)

    def _h2_positions(self):
        body = _strip_fenced_blocks(self.body)
        return [(m.group(1).lower(), m.start())
                for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body)]

    def test_has_what_this_skill_does(self):
        self.assertTrue(
            any("what this skill does" in h for h, _ in self._h2_positions()),
            "missing 'What this skill does' H2",
        )

    def test_has_term_mode_section(self):
        self.assertTrue(
            any(h.strip().startswith("term mode") for h, _ in self._h2_positions()),
            "missing 'Term mode' H2",
        )

    def test_has_artifact_mode_section(self):
        self.assertTrue(
            any("artifact mode" in h for h, _ in self._h2_positions()),
            "missing 'Artifact mode' H2",
        )

    def test_term_mode_uses_merged_lexicon_and_flags_absent(self):
        # AC #2 — def from the merged lexicon, with example + see-also, and an
        # absent term flagged (not invented).
        self.assertIn("merged lexicon", self.body_norm)
        self.assertIn("example", self.body_norm)
        self.assertIn("see-also", self.body_norm)
        # "never invent" for an absent term.
        self.assertTrue(
            "not invent" in self.body_norm
            or "never invent" in self.body_norm
            or "do not fabricate" in self.body_norm,
            "term mode must state it flags an absent term rather than inventing one",
        )

    def test_artifact_mode_fixed_six_block_shape(self):
        # AC #3 — the fixed walkthrough shape: all six block labels present.
        for label in [
            "in one sentence",
            "why it exists",
            "words you'll need",
            "walkthrough",
            "the decisions & why",
            "if you had to work on this",
        ]:
            self.assertIn(
                label, self.body_norm,
                f"artifact-mode walkthrough missing block: {label!r}",
            )

    def test_artifact_mode_auto_pulls_linked_refs(self):
        # AC #3 — auto-pulls the linked ADRs/specs.
        self.assertTrue(
            "auto-pull" in self.body_norm or "auto pull" in self.body_norm,
            "artifact mode must document auto-pulling linked refs",
        )

    def test_ephemeral_contract(self):
        # AC #4 — writes nothing; no --save; no appended section.
        self.assertIn("ephemeral", self.body_norm)
        self.assertIn("writes nothing", self.body_norm)
        self.assertIn("--save", self.body)  # the literal flag name, not normalized

    def test_no_helper_documented(self):
        # AC #5 — body states no .py helper; lookups run inline via Read + the
        # 065-01 loader.
        self.assertIn("no `.py` helper", self.body_norm)
        self.assertIn("lexicon.py", self.body_norm)


class NoPyHelperTests(unittest.TestCase):
    """AC #5 — skills/explain/ does NOT gain an explain.py helper."""

    def test_no_explain_py(self):
        py_file = SKILL_DIR / "explain.py"
        self.assertFalse(
            py_file.is_file(),
            f"AC #5: skills/explain/explain.py must not exist (found at {py_file})",
        )


class TierRegistrationTests(unittest.TestCase):
    """AC #1 — the skill is registered in jig's per-tier inventory (the
    single source of truth) and in the two restated mirror tables, so the
    plugin install contract carries it."""

    def test_in_scaffold_tier_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
        import scaffold  # noqa: E402
        all_skills = {s for skills in scaffold._TIER_SKILLS.values() for s in skills}
        self.assertIn(
            "explain", all_skills,
            "explain must be registered in scaffold._TIER_SKILLS (source of truth)",
        )

    def test_in_install_contract_expected_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import install_contract  # noqa: E402
        self.assertIn("explain", install_contract.EXPECTED_SKILLS)

    def test_in_scaffold_contract_tier_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import scaffold_contract  # noqa: E402
        all_skills = {
            s for skills in scaffold_contract._TIER_SKILLS.values() for s in skills
        }
        self.assertIn("explain", all_skills)


class ClaudeMdRowTests(unittest.TestCase):
    """AC #1 / DoD — the root CLAUDE.md 'Skills in this repo' table carries a
    row for /jig:explain."""

    @classmethod
    def setUpClass(cls):
        cls.text = ROOT_CLAUDE_MD.read_text() if ROOT_CLAUDE_MD.is_file() else ""

    def test_claude_md_exists(self):
        self.assertTrue(ROOT_CLAUDE_MD.is_file(), f"missing {ROOT_CLAUDE_MD}")

    def test_explain_row_present(self):
        # A table row begins `| `/jig:explain` |` — match the skill cell.
        self.assertRegex(
            self.text,
            r"\|\s*`/jig:explain`\s*\|",
            "root CLAUDE.md 'Skills in this repo' table must have a /jig:explain row",
        )


if __name__ == "__main__":
    unittest.main()
