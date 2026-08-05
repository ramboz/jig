"""Surface tests for skills/spec-workflow/SKILL.md — spec 068-02 contract prose.

Slice 068-02 adds two pieces of spec-author contract prose to SKILL.md
(ADR-0025 / the use-case breadth layer):

  AC1 — *read use cases as framing.* Before drafting a spec, the author reads
        the vision `## Use cases` section as framing context.
  AC5 — *grow-on-discovery, mechanical trigger.* When a spec reaches
        draft/framing with an empty/absent/unresolvable `use_cases:` (the
        deterministic `classify` signal — NOT a voluntary self-report), the
        author is prompted with three one-step paths:
          (a) cite an existing UC,
          (b) grow the vision additively (reuse the capture loop, seeded with
              existing entries → normalize → confirm → assign the next UC-N),
              guarding grow quality (goal-level grain + near-duplicate →
              route-to-cite),
          (c) decline (no-op).
        CRITICAL: when there is NO `## Use cases` section (layer not adopted —
        e.g. jig's own repo) the trigger is silent — nothing prompts or errors.

These are pure-file inspections (no subprocess, no runner), run under the same
`python3 scripts/run_tests.py` invocation as every other jig skill surface test.
Mirrors skills/analyze/test_analyze_skill_surface.py.
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL_MD = SKILL_DIR / "SKILL.md"


def _body(text: str) -> str:
    m = re.match(r"^---\n.*?\n---\n(.*)$", text, re.DOTALL)
    return m.group(1) if m else text


class UseCasesFramingContractTests(unittest.TestCase):
    """068-02 AC1 — spec drafting reads the vision `## Use cases` section as
    framing context before drafting."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.lower = cls.body.lower()

    def test_instructs_reading_use_cases_section(self):
        # The contract must name the `## Use cases` vision section explicitly.
        self.assertIn(
            "## use cases", self.lower,
            "SKILL.md must instruct reading the vision `## Use cases` section "
            "(068-02 AC1)",
        )

    def test_frames_use_cases_as_framing_before_drafting(self):
        # The instruction must position it as framing read *before* drafting.
        self.assertIn(
            "framing", self.lower,
            "SKILL.md must position the use-cases read as framing (068-02 AC1)",
        )
        self.assertTrue(
            "before drafting" in self.lower
            or "before you draft" in self.lower
            or "before authoring" in self.lower,
            "the framing read must be positioned *before* drafting (068-02 AC1)",
        )


class GrowOnDiscoveryContractTests(unittest.TestCase):
    """068-02 AC4/AC5 — the mechanical grow trigger + the 3-path prompt, with
    the grow-quality guard and the no-section no-op carve-out."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        cls.lower = cls.body.lower()

    def test_documents_use_cases_trace_field(self):
        # The author records the trace link in `use_cases:` frontmatter.
        self.assertIn(
            "use_cases:", self.body,
            "SKILL.md must document the `use_cases:` trace field (068-02 AC2)",
        )

    def test_trigger_is_the_mechanical_empty_or_unresolvable_state(self):
        # AC5: the trigger is the deterministic empty/absent/unresolvable
        # state — NOT a voluntary self-report.
        self.assertTrue(
            "empty" in self.lower and "unresolvable" in self.lower,
            "the grow trigger must fire on an empty/absent/unresolvable "
            "`use_cases:` (068-02 AC5)",
        )
        # It must be framed as mechanical / deterministic, not opt-in.
        self.assertTrue(
            "mechanical" in self.lower or "deterministic" in self.lower,
            "the trigger must be framed as a mechanical/deterministic signal, "
            "not a voluntary self-report (068-02 AC5)",
        )

    def test_documents_three_paths(self):
        # AC5: cite / grow / decline — all three present.
        self.assertTrue(
            "cite" in self.lower,
            "path (a) must let the author cite an existing use case (068-02 AC5)",
        )
        self.assertTrue(
            "grow" in self.lower,
            "path (b) must let the author grow the vision (068-02 AC5)",
        )
        self.assertTrue(
            "decline" in self.lower,
            "path (c) must let the author decline (068-02 AC5)",
        )

    def test_grow_path_reuses_capture_loop_seeded_with_existing(self):
        # AC5(b): reuse vision-elicitation's capture loop, seeded with the
        # existing entries → normalize → confirm → write additively.
        self.assertTrue(
            "capture loop" in self.lower or "vision-elicitation" in self.lower,
            "the grow path must reuse vision-elicitation's capture loop "
            "(068-02 AC5b)",
        )
        self.assertTrue(
            "additive" in self.lower or "additively" in self.lower,
            "the grow path must write additively (never discard-and-replace) "
            "(068-02 AC5b)",
        )
        self.assertTrue(
            "seeded" in self.lower or "existing entries" in self.lower,
            "the capture loop must be seeded with the existing entries "
            "(068-02 AC5b)",
        )

    def test_grow_path_assigns_next_uc_n(self):
        # AC5(b): a new entry gets the next free UC-N.
        self.assertRegex(
            self.body, r"UC-N|next free|next.{0,12}id",
            "the grow path must assign the next free UC-N id (068-02 AC5b)",
        )

    def test_grow_quality_guard_grain_and_dedup(self):
        # AC5(b)(i)+(ii): confirm step guards grow quality — goal-level grain
        # (reject spec-shaped phrasing) + near-duplicate → route back to cite.
        self.assertIn(
            "goal-level", self.lower,
            "the confirm step must enforce goal-level grain (068-02 AC5b-i)",
        )
        self.assertTrue(
            "near-duplicate" in self.lower or "duplicate" in self.lower,
            "the confirm step must run a near-duplicate check (068-02 AC5b-ii)",
        )

    def test_soft_never_blocks(self):
        # AC4: empty/absent use_cases never errors or blocks a transition.
        self.assertTrue(
            "never block" in self.lower or "does not block" in self.lower
            or "not blocked" in self.lower or "never blocks" in self.lower,
            "the discipline must be soft — never blocks drafting/transition "
            "(068-02 AC4)",
        )

    def test_no_section_is_a_silent_no_op(self):
        # CRITICAL (AC5): no `## Use cases` section (layer not adopted) ⇒
        # nothing prompts or errors.
        self.assertTrue(
            "no_section" in self.lower or "no `## use cases`" in self.lower
            or "no use-case section" in self.lower
            or "not adopted" in self.lower,
            "the contract must name the no-section / layer-not-adopted state "
            "(068-02 AC5)",
        )
        self.assertTrue(
            "silent" in self.lower or "no-op" in self.lower
            or "nothing prompts" in self.lower or "suppressed" in self.lower,
            "the no-section state must be a silent no-op — nothing prompts or "
            "errors (068-02 AC5)",
        )

    def test_names_the_classify_predicate_helper(self):
        # The mechanical trigger is the `use_cases.py` classify_spec predicate —
        # name the EXACT symbol so the orchestrator knows what computes the
        # signal and the prose can't drift from the function name.
        self.assertTrue(
            "classify_spec" in self.lower,
            "the contract should name the deterministic classify_spec predicate "
            "that computes the trigger signal (068-02 AC5)",
        )


class SliceAuthoringReferenceAnchorTests(unittest.TestCase):
    """Bug 027 (GitHub issue 173) — the slice-authoring guidance must point at
    the in-project scaffolded worked example, not an unanchored template path.

    `templates/docs/specs/slice-template.md` is a bare, unanchored relative path
    that (a) names no root and (b) is mislocated post-ship: scaffold copies
    `templates/` to `<project>/.claude/templates/`, so the project-root path
    the wording implies does not exist inside a scaffolded repo. The authoritative
    structural reference is the scaffolded first spec `docs/specs/001-adopt-jig/`,
    which lands at project root (host-agnostic) and is named "the worked example
    to imitate" by the scaffolded `CLAUDE.md`."""

    @classmethod
    def setUpClass(cls):
        cls.body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")

    def test_no_unanchored_slice_template_path(self):
        # The bare, unanchored, post-ship-mislocated path must not appear as an
        # authoring instruction. Authors get a well-formed starter slice via
        # `workflow.py new`; the raw template location is host-dependent and
        # must not be cited by hand.
        self.assertNotIn(
            "templates/docs/specs/slice-template.md", self.body,
            "SKILL.md must not send slice authors to the unanchored / "
            "post-ship-mislocated `templates/docs/specs/slice-template.md` "
            "path (bug 027 / issue 173)",
        )

    def test_cites_in_project_worked_example(self):
        # The in-project, host-agnostic worked example is the structural
        # reference authors should mirror.
        self.assertIn(
            "001-adopt-jig", self.body,
            "SKILL.md slice-authoring guidance must cite the in-project "
            "scaffolded worked example `docs/specs/001-adopt-jig/` as the "
            "structural reference (bug 027 / issue 173)",
        )


class FailedReviewRetractionSweepTests(unittest.TestCase):
    """Bug 032 / issue #133 — the "Recovering from a failed review" path must
    direct a corpus-wide sweep for a retracted claim before re-recording, so a
    content-shaped finding surviving in a sibling artifact is caught in one
    pass instead of round-by-round.

    Scoped to the recovery section (not the whole body) so the wiring is
    asserted to land *in that path*, where the author actually is when a
    review fails."""

    @classmethod
    def setUpClass(cls):
        body = _body(SKILL_MD.read_text() if SKILL_MD.is_file() else "")
        # Isolate the recovery *prose*: from its bold lead to the
        # review-sequence bash block (```bash) or the next `##`/`###` heading,
        # whichever comes first. Anchoring on the ```bash fence specifically —
        # not any fence — keeps the assertions on the paragraphs (not the
        # ~95-line bash block below) while staying robust if a future edit adds
        # an inline example fence to the recovery prose above the review block.
        start = body.find("Recovering from a failed review")
        tail = body[start:] if start != -1 else ""
        end = re.search(r"\n```bash|\n#{2,3} ", tail)
        cls.section = (tail[: end.start()] if end else tail)
        cls.lower = cls.section.lower()

    def test_recovery_section_exists(self):
        self.assertTrue(
            self.section, "SKILL.md must retain the 'Recovering from a failed "
            "review' section (bug 032)",
        )

    def test_wires_in_analyze_for_the_corpus_sweep(self):
        # Maintainer direction on #133: leverage the existing /jig:analyze.
        self.assertIn(
            "jig:analyze", self.lower,
            "the recovery path must wire in `/jig:analyze` for the "
            "cross-artifact sweep (bug 032 / issue #133)",
        )

    def test_names_the_retracted_claim_as_content_that_propagates(self):
        # The gap is treating a finding as living in exactly one file. The fix
        # must name the retracted claim and that it propagates beyond the
        # reviewed artifact.
        self.assertIn(
            "retract", self.lower,
            "the recovery path must name the retracted claim (bug 032)",
        )
        self.assertTrue(
            "propagat" in self.lower or "sibling" in self.lower
            or "corpus" in self.lower or "other artifact" in self.lower,
            "the recovery path must state a retracted claim propagates beyond "
            "the reviewed deliverable (bug 032)",
        )

    def test_directs_a_sweep_before_re_recording(self):
        # A corpus-wide sweep (grep / analyze) for the retracted phrasing,
        # positioned *before* re-recording the verdict.
        self.assertTrue(
            "sweep" in self.lower or "grep" in self.lower
            or "search" in self.lower,
            "the recovery path must direct a corpus-wide sweep for the "
            "retracted phrasing (bug 032)",
        )
        self.assertIn(
            "before", self.lower,
            "the sweep must be positioned before re-recording the verdict "
            "(bug 032)",
        )

    def test_distinguishes_surviving_assertions_from_explicit_retractions(self):
        # A surviving copy must be fixed; an explicit, labelled retraction in a
        # changelog/history is fine — the sweep must not treat them alike.
        self.assertIn(
            "surviving", self.lower,
            "the recovery path must distinguish surviving assertions (must "
            "fix) from explicit retractions (fine) (bug 032)",
        )


if __name__ == "__main__":
    unittest.main()
