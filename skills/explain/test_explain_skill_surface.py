"""Surface tests for skills/explain/SKILL.md (slices 065-03 + 065-05).

Slice 065-05 adds the third "passage" mode and an explicit mode-precedence
rule with two carve-outs (term-mode honesty; path-shaped-but-unresolvable →
ask). Its structural ACs are pinned by `DescriptionTests` (passage mode +
trigger phrases declared) and `PassageModeTests` (section present, precedence
+ both carve-outs documented, no-jig-vocabulary → generic, best-effort/
no-fabricate provenance, never-invent extends to passage, no hard term cap,
dead-end removed, two existing modes intact). The plain-language *quality* of
a passage explanation stays a judgment, not unit-tested — the accepted gap
inherited from 065-03.

Original 065-03 scope:

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

    def test_declares_passage_mode(self):
        # 065-05 AC #1 — the third mode is named in the description.
        self.assertIn("three modes", self.normalized)
        self.assertIn("passage mode", self.normalized)

    def test_passage_trigger_phrases(self):
        # 065-05 — passage-mode auto-trigger phrases.
        for phrase in ("what does this output mean", "explain this snippet"):
            self.assertIn(
                phrase, self.normalized,
                f"description missing passage-mode trigger phrase: {phrase!r}",
            )

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
    """AC #1 / DoD — the root CLAUDE.md keeps /jig:explain discoverable.

    Spec 076-01 (lean primer) replaced the heavy per-skill 'Skills in this
    repo' table with a short pointer (the host already surfaces every skill
    with its description each session). The original DoD asserted a table row;
    post-076 the surviving, still-true invariant is that the primer still names
    /jig:explain in its skills pointer, so the on-demand explainer stays
    discoverable from the always-loaded file."""

    @classmethod
    def setUpClass(cls):
        cls.text = ROOT_CLAUDE_MD.read_text() if ROOT_CLAUDE_MD.is_file() else ""

    def test_claude_md_exists(self):
        self.assertTrue(ROOT_CLAUDE_MD.is_file(), f"missing {ROOT_CLAUDE_MD}")

    def test_explain_discoverable(self):
        # Post-076 the table is gone; /jig:explain must still be named in the
        # primer's 'Skills in this repo' pointer.
        self.assertIn(
            "/jig:explain", self.text,
            "root CLAUDE.md must keep /jig:explain discoverable (spec 076-01)",
        )


class PassageModeTests(unittest.TestCase):
    """Slice 065-05 — the third mode and its precedence carve-outs are
    documented at the SKILL.md surface (the quality of a passage explanation is
    judgment, not unit-tested — the accepted gap inherited from 065-03)."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_norm = _normalize(cls.body)

    def _h2_positions(self):
        body = _strip_fenced_blocks(self.body)
        return [(m.group(1).lower(), m.start())
                for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body)]

    def test_has_passage_mode_section(self):
        # AC #1 — a "Passage mode" H2 section exists.
        self.assertTrue(
            any("passage mode" in h for h, _ in self._h2_positions()),
            "missing 'Passage mode' H2 section",
        )

    def test_existing_two_modes_still_present(self):
        # AC #6 — term + artifact sections survive the third-mode addition.
        positions = self._h2_positions()
        self.assertTrue(
            any(h.strip().startswith("term mode") for h, _ in positions),
            "Term mode section must still be present",
        )
        self.assertTrue(
            any("artifact mode" in h for h, _ in positions),
            "Artifact mode section must still be present",
        )

    def test_mode_precedence_documented(self):
        # AC #2 — the resolution order is documented in one place.
        self.assertIn("path", self.body_norm)
        self.assertIn("artifact mode", self.body_norm)
        self.assertIn("term mode", self.body_norm)
        self.assertIn("passage mode", self.body_norm)
        # The ordered form: path -> artifact ; key -> term ; otherwise -> passage.
        self.assertTrue(
            "exact / normalized lexicon key" in self.body_norm
            or "normalized lexicon key" in self.body_norm,
            "mode precedence must name the lexicon-key -> term-mode rule",
        )

    def test_term_honesty_carveout(self):
        # AC #2 — an unknown single term still routes to term mode, not swallowed
        # by passage mode. Pin the negation phrase itself (not a trivially-true
        # `"not" in body` conjunct) so the assertion enforces the adjacency.
        # Pin "silently absorbed into a passage-mode guess" — the phrase only
        # appears inside the negated sentence ("is **not** silently absorbed…"),
        # so it enforces the carve-out without tripping on the `**not**` bold
        # markers `_normalize` leaves in place.
        self.assertIn(
            "silently absorbed into a passage-mode guess", self.body_norm,
            "must document that an unknown short query is NOT absorbed into a "
            "passage-mode guess (term-mode honesty carve-out)",
        )

    def test_path_disambiguation_carveout(self):
        # AC #2 / clarify Q1 — a path-shaped-but-unresolvable argument asks the
        # user rather than falling through to passage mode.
        self.assertIn(
            "looks like a repo file path", self.body_norm,
            "must document the path-shaped-but-unresolvable case",
        )
        self.assertIn(
            "ask the user", self.body_norm,
            "path-shaped-but-unresolvable input must ASK the user (clarify Q1), "
            "not silently route to passage mode",
        )

    def test_no_jig_vocabulary_explains_generically(self):
        # AC #1 / clarify Q2 — a passage with no jig terms is explained
        # generically rather than declined.
        self.assertTrue(
            "no jig vocabulary" in self.body_norm
            or "no recognizable jig terms" in self.body_norm
            or "no jig vocabulary at all" in self.body_norm,
            "must document the no-jig-vocabulary case",
        )
        self.assertIn("generic", self.body_norm)

    def test_provenance_best_effort_never_fabricated(self):
        # AC #3 — best-effort source identification, never fabricated.
        self.assertTrue(
            "best-effort" in self.body_norm or "best effort" in self.body_norm,
            "provenance must be framed as best-effort",
        )
        self.assertTrue(
            "do not invent a source" in self.body_norm
            or "never fabricated" in self.body_norm
            or "not invent a source" in self.body_norm,
            "must state the source is never fabricated",
        )

    def test_never_invent_extends_to_passage(self):
        # AC #4 — the never-invent rule extends to unrecognized tokens in a
        # passage.
        self.assertIn("never-invent", self.body_norm)
        self.assertTrue(
            "flagged as unrecognized" in self.body_norm,
            "unrecognized jig-shaped tokens in a passage must be flagged, not "
            "given a fabricated meaning",
        )

    def test_no_silent_dead_end(self):
        # AC #6 — the old bare "ambiguous -> say what you tried and stop"
        # dead-end no longer stands alone; it is replaced by the passage route.
        # Negative: the original dead-end phrasing (removed in 065-05) is gone.
        self.assertNotIn(
            "say what you tried (term lookup found nothing; no file at that "
            "path) rather than guessing",
            self.body_norm,
        )
        # Positive: the replacement is documented — there is explicitly no
        # silent give-up branch any more.
        self.assertTrue(
            "no silent" in self.body_norm and "dead-end" in self.body_norm,
            "must document that the ambiguous-argument dead-end is replaced by "
            "the passage route (no silent give-up)",
        )

    def test_no_hard_term_cap(self):
        # clarify Q4 — passage mode does not impose a hard cap on inline term
        # definitions; it is "not capped at the 065-02 hook's per-prompt N".
        # (The literal "no hard cap" phrasing was refined out by the
        # conventions output-shape pass, which now forbids that wording — see
        # docs/conventions.md — but the no-cap decision itself is preserved.)
        self.assertIn("not capped", self.body_norm)


if __name__ == "__main__":
    unittest.main()
