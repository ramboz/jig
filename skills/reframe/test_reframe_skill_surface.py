"""Surface tests for skills/reframe/SKILL.md (slices 067-01 + 067-02).

Slice 067-02 adds `RetrofitSpecDraftTests` (the per-`retrofit` `workflow.py new`
drafting surface). The AC index below is 067-01's; 067-02's four ACs are pinned
by that class.

Pure-file inspection — no subprocess, no runner. Mirrors the surface-test
pattern from skills/explain/test_explain_skill_surface.py and
skills/clarify/test_clarify_skill_surface.py.

Pins the structural, unit-testable ACs of slice 067-01. The plain-language
*quality* of the corpus read (AC2) and the honesty of a given coverage floor
(the substance of AC5) are judgment, not unit-testable — the accepted gap for a
judgment-only jig skill (recorded in the spec's testability note); the slice's
pre-implementation `frame_review` pass pressure-tests that framing instead.

  AC #1 — registered + discoverable: SKILL.md exists with active frontmatter
          (name: reframe, user-invocable: true, NO disable-model-invocation);
          the description names the operation + both invocation styles; the
          skill is in jig's per-tier inventory + the two restated mirror tables;
          and /jig:reframe stays discoverable in the root CLAUDE.md primer
          (post-spec-076: a named mention, not a per-skill table row).
  AC #2 — corpus read documented: reads the accepted corpus; explicitly NOT a
          `## Assumptions` sweep and NOT a built corpus-walker (parked).
  AC #3 — keystone reframe-ADR via the real ADR lifecycle (`adr.py new`), so it
          inherits the frame-critique `accept` gate.
  AC #4 — the manifest assigns every affected artifact a disposition (no TBD),
          the full 6-term vocabulary, retire-draft first, `## Emergent work`.
  AC #5 — the two-level coverage floor: L1 (top-level classes, each
          scanned/excused) + L2 (artifact-level within touched classes);
          reduces-and-surfaces, not eliminates.
  AC #6 — judgment-only, no helper: no reframe.py; body states no `.py` helper.
  AC #7 — defers to a richer installed re-baselining / reference-migration skill
          and does NOT defer to the generic built-in.
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
            f"skills/reframe/SKILL.md must exist at {SKILL_MD}",
        )

    def test_has_frontmatter_block(self):
        self.assertTrue(
            _frontmatter(self.text),
            "SKILL.md must start with a YAML frontmatter block",
        )

    def test_name_field(self):
        self.assertRegex(_frontmatter(self.text), r"(?m)^name:\s*reframe\s*$")

    def test_user_invocable_true(self):
        self.assertRegex(_frontmatter(self.text), r"(?m)^user-invocable:\s*true\s*$")

    def test_no_disable_model_invocation(self):
        # AC #1: this skill auto-triggers (auto + explicit invocation styles).
        self.assertNotIn("disable-model-invocation: true", _frontmatter(self.text))


class DescriptionTests(unittest.TestCase):
    """AC #1 / #7 — description names the operation, both invocation styles,
    auto-trigger phrases, the deferral clause, and a Do-not-use-for block."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        )

    def test_names_the_operation(self):
        # AC #1 — re-baselines the corpus onto a moved load-bearing reference.
        self.assertIn("re-baseline", self.normalized)
        self.assertIn("moved load-bearing reference", self.normalized)

    def test_declares_both_invocation_styles(self):
        # AC #1 — auto (trigger phrases) + explicit (`/jig:reframe`).
        self.assertIn("/jig:reframe", self.normalized)
        self.assertIn("auto-triggers when you say", self.normalized)

    def test_has_auto_trigger_phrases(self):
        phrases = [
            "reframe onto this",
            "we changed direction",
            "the design moved",
            "re-baseline the project",
        ]
        for phrase in phrases:
            self.assertIn(
                phrase, self.normalized,
                f"description missing trigger phrase: {phrase!r}",
            )

    def test_defers_to_richer_installed_skill(self):
        # AC #7 — defers to a richer installed re-baselining / reference-migration
        # skill.
        self.assertIn("defers to any other installed skill", self.normalized)
        self.assertIn("project re-baselining", self.normalized)
        self.assertIn("migrating onto a new reference", self.normalized)

    def test_does_not_defer_to_generic_builtin(self):
        # AC #7 — explicit "does not defer to the generic built-in".
        self.assertIn("does not defer to the generic built-in", self.normalized)

    def test_do_not_use_clause(self):
        # AC #7 — the confusable-sibling boundaries.
        self.assertIn("do not use for", self.normalized)
        self.assertIn("use `/jig:migrate`", self.normalized)
        self.assertIn("`jig:refactor`", self.normalized)
        self.assertIn("`adr.py supersede`", self.normalized)
        self.assertIn("use `/jig:analyze`", self.normalized)


class DescriptionBoundsTests(unittest.TestCase):
    """AC #7 (anti-greediness / honesty) — the description does not over-claim in
    a way that would shadow a richer installed skill or promise a detector."""

    @classmethod
    def setUpClass(cls):
        cls.normalized = _normalize(
            _frontmatter(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        )

    def test_no_over_claiming_phrases(self):
        forbidden = [
            "comprehensive",
            "fully automatic",
            "fully automated",
            "expert-level",
            "guarantees",
            "detects every",
            "automatically detects",
        ]
        for phrase in forbidden:
            self.assertNotIn(
                phrase, self.normalized,
                f"description over-claims with phrase: {phrase!r}",
            )


class BodyTests(unittest.TestCase):
    """AC #2/#3/#4/#5/#6 — required body sections + their load-bearing content."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_norm = _normalize(cls.body)

    def _h2_positions(self):
        body = _strip_fenced_blocks(self.body)
        return [(m.group(1).lower(), m.start())
                for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body)]

    def test_has_required_sections(self):
        headings = [h for h, _ in self._h2_positions()]

        def present(needle):
            return any(needle in h for h in headings)

        for needle in [
            "what this skill does",
            "when to use vs. when to defer",
            "inputs",
            "the corpus read",
            "the keystone reframe-adr",
            "the re-baselining manifest",
            "the two-level coverage floor",
        ]:
            self.assertTrue(present(needle), f"missing H2 section: {needle!r}")

    # ---- AC #2 — corpus read -------------------------------------------------
    def test_corpus_read_not_assumptions_sweep(self):
        self.assertIn("accepted corpus", self.body_norm)
        self.assertIn("not a `## assumptions` sweep", self.body_norm)

    def test_corpus_read_not_built_walker(self):
        self.assertIn("not a built corpus-walker", self.body_norm)
        self.assertIn("parked", self.body_norm)

    # ---- AC #3 — keystone ADR via adr.py new ---------------------------------
    def test_keystone_adr_via_adr_py_new(self):
        self.assertIn("keystone", self.body_norm)
        self.assertIn("adr.py", self.body_norm)
        # frame-critique-gated accept flow inherited by riding the ADR lifecycle.
        self.assertIn("frame-critique", self.body_norm)
        self.assertTrue(
            "authoritative as of" in self.body_norm,
            "keystone ADR must declare the new reference authoritative as of a date",
        )

    # ---- AC #4 — the manifest + disposition vocabulary -----------------------
    def test_manifest_no_tbd_and_retire_draft_first(self):
        self.assertIn("no `tbd`", self.body_norm)
        # retire-draft surfaced first.
        self.assertTrue(
            "retire-draft` items are surfaced" in self.body_norm
            or "retire-draft items are surfaced" in self.body_norm,
            "retire-draft items must be surfaced first",
        )

    def test_full_disposition_vocabulary(self):
        for disp in ["reaffirm", "amend", "supersede", "retire-draft",
                     "retrofit", "rewrite"]:
            self.assertIn(
                disp, self.body_norm,
                f"disposition vocabulary missing: {disp!r}",
            )

    def test_emergent_work_section_named(self):
        self.assertIn("emergent work", self.body_norm)

    # ---- AC #5 — the two-level coverage floor --------------------------------
    def test_two_level_coverage_floor(self):
        self.assertIn("two-level coverage floor", self.body_norm)
        self.assertIn("level 1", self.body_norm)
        self.assertIn("level 2", self.body_norm)

    def test_l1_names_top_level_classes(self):
        # The fixed, unit-tested class list is what makes a whole-class drop
        # impossible to hide (the frame-critique-defeating property).
        for cls_name in ["docs/decisions/", "docs/specs/", "skills/*/skill.md",
                         "readme"]:
            self.assertIn(
                cls_name, self.body_norm,
                f"L1 coverage floor must name top-level class: {cls_name!r}",
            )

    def test_l2_within_touched_classes(self):
        self.assertIn("artifact-level", self.body_norm)
        self.assertTrue(
            "class the reference actually touches" in self.body_norm
            or "within touched classes" in self.body_norm,
            "L2 must be scoped to the classes the reference touches",
        )

    def test_floor_reduces_not_eliminates(self):
        self.assertIn("reduces and surfaces", self.body_norm)
        # honest: does not eliminate; T1 backstop.
        self.assertIn("does **not** eliminate", self.body_norm)
        self.assertIn("t1", self.body_norm)

    def test_l1_staleness_note_present(self):
        # The 067-01 frame-critique non-blocking note, folded in: the L1 class
        # list is jig-corpus-shaped and must be revisited if a downstream corpus
        # grows a new top-level class.
        self.assertIn("jig-corpus-shaped", self.body_norm)

    # ---- AC #6 — no helper ---------------------------------------------------
    def test_no_helper_documented(self):
        self.assertIn("no `.py` helper", self.body_norm)


class NoPyHelperTests(unittest.TestCase):
    """AC #6 — skills/reframe/ does NOT gain a reframe.py helper."""

    def test_no_reframe_py(self):
        py_file = SKILL_DIR / "reframe.py"
        self.assertFalse(
            py_file.is_file(),
            f"AC #6: skills/reframe/reframe.py must not exist (found at {py_file})",
        )


class TierRegistrationTests(unittest.TestCase):
    """AC #1 — the skill is registered in jig's per-tier inventory (the single
    source of truth) and in the two restated mirror tables, so the plugin install
    contract carries it."""

    def test_in_scaffold_tier_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
        import scaffold  # noqa: E402
        all_skills = {s for skills in scaffold._TIER_SKILLS.values() for s in skills}
        self.assertIn(
            "reframe", all_skills,
            "reframe must be registered in scaffold._TIER_SKILLS (source of truth)",
        )

    def test_reframe_is_tier_1(self):
        sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
        import scaffold  # noqa: E402
        self.assertIn("reframe", scaffold._TIER_SKILLS["tier-1"])

    def test_in_install_contract_expected_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import install_contract  # noqa: E402
        self.assertIn("reframe", install_contract.EXPECTED_SKILLS)

    def test_in_scaffold_contract_tier_skills(self):
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import scaffold_contract  # noqa: E402
        all_skills = {
            s for skills in scaffold_contract._TIER_SKILLS.values() for s in skills
        }
        self.assertIn("reframe", all_skills)


class ClaudeMdDiscoverabilityTests(unittest.TestCase):
    """AC #1 / DoD — /jig:reframe stays discoverable from the root CLAUDE.md
    primer. Spec 076-01 (lean primer) replaced the heavy per-skill 'Skills in
    this repo' table with a short pointer + hot-cache index, so discoverability
    is a NAMED MENTION, not a table row (see slice 067-01 AC1)."""

    @classmethod
    def setUpClass(cls):
        cls.text = ROOT_CLAUDE_MD.read_text() if ROOT_CLAUDE_MD.is_file() else ""

    def test_claude_md_exists(self):
        self.assertTrue(ROOT_CLAUDE_MD.is_file(), f"missing {ROOT_CLAUDE_MD}")

    def test_reframe_discoverable(self):
        self.assertIn(
            "eframe", self.text,  # matches "Reframe" / "reframe" / "/jig:reframe"
            "root CLAUDE.md must keep reframe discoverable (spec 076-01 named "
            "mention, not a table row)",
        )

    def test_claude_md_under_line_budget(self):
        # The named mention must not blow the spec 076 lean-primer line budget.
        n = self.text.count("\n") + (0 if self.text.endswith("\n") else 1)
        self.assertLessEqual(
            n, 70,
            f"CLAUDE.md has {n} lines; spec 076 budget is 70 — add reframe by "
            f"extending an existing line, not a new one",
        )


class RetrofitSpecDraftTests(unittest.TestCase):
    """Slice 067-02 — the SKILL.md specifies that each `retrofit` disposition
    mints a retrofit spec draft via `workflow.py new`, reference-anchored, with a
    complete + linked mapping back to the manifest. (The content quality of a
    generated draft is judgment, like 067-01 — not unit-tested.)"""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.body_norm = _normalize(cls.body)

    def _h2_positions(self):
        body = _strip_fenced_blocks(self.body)
        return [(m.group(1).lower(), m.start())
                for m in re.finditer(r"(?m)^##\s+(.+?)\s*$", body)]

    def test_has_retrofit_spec_drafts_section(self):
        self.assertTrue(
            any("retrofit spec drafts" in h for h, _ in self._h2_positions()),
            "missing 'Retrofit spec drafts' H2 section (067-02)",
        )

    def test_per_retrofit_workflow_new_flow(self):
        # AC1 — one retrofit spec per `retrofit` disposition, via workflow.py new.
        self.assertIn("workflow.py", self.body_norm)
        self.assertIn("every `retrofit` disposition", self.body_norm)

    def test_goal_anchored_on_reference(self):
        # AC2 — the draft is goaled "bring <artifact/code> in line with <reference>".
        # Pin the full template (not just "in line with") so the assertion can't
        # pass on unrelated prose (067-02 craft nit).
        self.assertIn(
            "bring `<artifact/code>` in line with `<reference>`", self.body_norm,
            "AC2: retrofit draft goal must use the reference-anchored template",
        )

    def test_assumptions_anchored_on_reference(self):
        # AC3 — the retrofit spec's `## Assumptions` cite the new reference.
        self.assertIn("anchor `## assumptions`", self.body_norm)

    def test_complete_and_visible_mapping(self):
        # AC4 — no retrofit disposition silently dropped; manifest links each
        # retrofit row to its drafted spec number.
        self.assertIn("no `retrofit` disposition silently dropped", self.body_norm)
        self.assertIn("explicitly-recorded reason", self.body_norm)
        self.assertTrue(
            "link each `retrofit` row to its drafted spec number" in self.body_norm,
            "manifest must link each retrofit row to its drafted spec number "
            "(complete + visible mapping)",
        )


if __name__ == "__main__":
    unittest.main()
