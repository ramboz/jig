---
status: DONE
tier: standard
severity: low
claimed_by: claude/issue-133-0edb78
regression_test: skills/spec-workflow/test_spec_workflow_skill_surface.py::FailedReviewRetractionSweepTests
main_repro_checked_at: 2026-07-31
main_repro_ref: origin/main@4cb68a1
main_repro_result: reproduces
red_confirmed_at: 2026-07-31
green_confirmed_at: 2026-07-31
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 032: review-recovery-no-retraction-sweep

Reported as [issue #133](https://github.com/ramboz/jig/issues/133).

## Symptom

A reconciliation/independent review falsifies a specific *claim* in the
deliverable under review. The author corrects that one document, re-runs the
pass — and it fails again, because the same retracted claim is still standing,
word for word, in sibling artifacts that cross-reference the corrected file
(CHANGELOG.md, the slice record, the inbox, another doc). This repeats across
rounds; a round-3 reviewer note (verbatim in #133) diagnosed it:

> The pattern across three rounds is consistent: the author corrects the
> document under review but leaves the same assertion standing in sibling
> documents — the fix here is a grep for the retracted claim across `docs/`
> and `CHANGELOG.md`, not another rewrite of `architecture.md`, which is now
> clean.

The *stale* copy is frequently the one a future session reads first (the
project's own rules make CHANGELOG.md a read-before-you-fix record), so the
retracted version stays authoritative where it does the most damage.

## Repro

1. Write a claim into two artifacts, one citing the other as its source
   (e.g. an assertion in `architecture.md`, echoed in `CHANGELOG.md`).
2. Run an independent/reconciliation review that falsifies the claim.
3. Follow the current "Recovering from a failed review" path
   (`skills/spec-workflow/SKILL.md`): address the finding in the reviewed
   deliverable only, re-record, re-run `transition … REVIEWED`.
4. Observe: the review fails again on the surviving copy in the sibling
   artifact. The recovery path never directed a corpus-wide sweep.

## Evidence

- `skills/spec-workflow/SKILL.md` § "Recovering from a failed review"
  (currently at line 487) reads: *"address the findings, re-run the pass
  against the updated deliverable, `record-review` the new verdict, then
  re-run `transition … REVIEWED`."* Every noun is singular — "the updated
  deliverable" — encoding the one-file assumption.
- `/jig:analyze` already owns cross-artifact consistency + terminology drift,
  but nothing in the recovery path invokes it. The capability exists; the
  wiring does not.
- Maintainer direction on #133: *"I think leveraging the existing
  `/jig:analyze` is the right call."*

## Hypotheses

- [ ] H1: `/jig:analyze` fails to detect the surviving duplicate, so even an
      author who ran it would not be pointed at the sibling artifact. Falsify
      by confirming analyze's scope covers cross-artifact duplication /
      terminology drift (its own description asserts this) — the tool detects
      it; the gap is that nobody is told to run it.
- [x] H2 (leading): the recovery-path prose treats a review finding as living
      in exactly one file ("the updated deliverable"), so it never prompts a
      corpus-wide sweep for the retracted *claim*. A falsified assertion is
      **content, and content propagates**; fixing only the reviewed artifact
      leaves the retracted version authoritative elsewhere. Confirm by reading
      the section — the fix is guidance (wire in the sweep), not code.

## Root cause

The "Recovering from a failed review" guidance is written for **code-shaped
findings**, which are local to a file/function. It does not distinguish those
from **content-shaped findings** — a retracted claim, which is often copied by
design into the changelog, slice record, inbox, and cross-referenced docs.
Because the prose says "re-run the pass against the updated deliverable"
(singular), the author's correction stops at the reviewed artifact and the
corpus stays internally contradictory, re-failing the next round on the
surviving copy. The missing step is a corpus-wide sweep for the retracted
phrasing before re-recording — a plain grep across the docs root and
`CHANGELOG.md`, with `/jig:analyze` as a structured *within-spec* complement
(it audits one spec + a fixed doc whitelist and does **not** read the
changelog; see `## Already tried`).

## Fix class

`guardrail` — adds a defensive step to the recovery *process* so a retracted
claim surviving in a sibling artifact is surfaced before re-recording, rather
than being rediscovered round-by-round. It does not patch any single output;
it closes the class of "corpus left internally contradictory after a review."

## Fix

Add a step to `skills/spec-workflow/SKILL.md` § "Recovering from a failed
review": **when a review retracts a claim, sweep the corpus before
re-recording.** The step names that a content-shaped finding propagates into
sibling artifacts (changelog, slice record, inbox, cross-referenced docs),
makes the **plain grep across the docs root + `CHANGELOG.md`** the corpus-wide
mechanism, positions it *before* `record-review`, and distinguishes
**surviving** assertions (must fix) from **explicit** retractions (fine).

`/jig:analyze` is wired in per maintainer direction on #133, but as the
**structured within-spec complement**, not the corpus sweep — its Duplication
and Terminology-Drift categories catch a retracted claim across the spec's own
slice files and its fixed cross-reference set (`product-vision`, ADRs,
glossary, `architecture.md`). It audits one spec plus that set, **not**
`CHANGELOG.md` or the inbox (`skills/analyze/SKILL.md` § Inputs — "MVP scans
one spec at a time"; cross-spec explicitly unsupported), so it sharpens the
grep rather than replacing it. Framing analyze as the primary mechanism would
miss the exact artifact (`CHANGELOG.md`) in this bug's repro — the craft pass
caught that overclaim; see `## Already tried`.

Prose-only change to the skill contract; no `.py` behaviour changes.

## Already tried

- First draft named `/jig:analyze` as the *primary* corpus-sweep mechanism
  ("catches exactly this propagation" into `CHANGELOG.md`/inbox). The **craft
  review (round 1) failed it**: analyze's own contract limits inputs to one
  spec's files + a fixed whitelist that excludes `CHANGELOG.md` and the inbox
  — the very artifact in this bug's repro. Corrected: grep is the corpus-wide
  mechanism; analyze is the structured within-spec complement. This refines
  H1 — analyze detects duplicates *within its scope*, but that scope does not
  reach the changelog, so the plain grep is load-bearing, not a fallback.
- Root cause itself was reachable by reading the section (H2 confirmed on
  first pass; the recovery prose was singular/code-shaped).

## Regression test

`skills/spec-workflow/test_spec_workflow_skill_surface.py::FailedReviewRetractionSweepTests`
— five test methods scoped to the recovery prose (stopping at the first code
fence, not the whole body): the
section survives; it wires in `/jig:analyze`; it names the retracted claim as
content that propagates to siblings/corpus; it directs a sweep positioned
before re-recording; it distinguishes surviving assertions from explicit
retractions. Follows the project's skill-surface idiom (spec 068-02 tested
this same file the same way); it is a suite contract test, not a
transition-blocking lexical gate.

## Proof

- red: 4/5 assertions failed against the pre-fix section (only
  `test_recovery_section_exists` passed). Witnessed by the `→ FIXING` gate
  (`red_confirmed_at: 2026-07-31`).
- green: all 5 pass after the fix; the full 16-test skill-surface file stays
  green (068-02 tests unaffected). Witnessed by the `→ REVIEWED` gate.

## Learning

A review finding about **content propagates**; a recovery path written for
code-shaped findings silently assumes one-file locality and re-fails
round-by-round on the untouched sibling copy. The durable fix is a corpus-wide
sweep *before* re-recording. Second, sharper lesson: **verify a named tool's
documented scope before wiring it in as the mechanism.** The maintainer's
"leverage `/jig:analyze`" was right in spirit, but analyze's MVP audits one
spec + a fixed whitelist — not `CHANGELOG.md` or the inbox, the exact artifact
in this bug's repro. The craft pass caught the overclaim only because it read
`skills/analyze/SKILL.md` § Inputs instead of trusting the tool's tagline. See
[`docs/memory/learnings.md`](../memory/learnings.md).

## Main recheck

- 2026-07-31 - `origin/main@4cb68a1` -> reproduces: git show origin/main:skills/spec-workflow/SKILL.md § 'Recovering from a failed review' (lines 487-495) still directs fixing only 'the updated deliverable' (singular); grep for retract|corpus|jig:analyze|sibling in the recovery path returns nothing.
