---
status: DONE
tier: standard
severity: medium
claimed_by: claude/adversarial-review-leak-64bb2d
regression_test: skills/independent-review/test_review.py::Bug033FrameCritiqueGroundingAwareTests
main_repro_checked_at: 2026-08-11
main_repro_ref: origin/main@a642b66
main_repro_result: reproduces
red_confirmed_at: 2026-08-11
green_confirmed_at: 2026-08-11
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 033: frame-critique-false-positive-grounded

## Symptom

The frame-critique pass (`build_frame_critique_prompt` in
`skills/independent-review/review.py`) returns a blocking `needs-changes` on a
"load-bearing assumption" that is *actually grounded* — but grounded somewhere
the pre-implementation reviewer didn't read: a **linked accepted ADR**, or
**context outside the artifact** (a protocol, a prior decision, an external
tool's capability). A settled or bounded residual gets inflated into "the whole
frame is wrong," and the author spends multiple rounds re-litigating decided
work. The pass is doing its job *too indiscriminately*: it is built to always
produce an attack, and has no way to tell "this assumption is wrong" from "this
assumption is fine, I just can't see its grounding from here."

## Repro

1. Author a spec/slice/ADR with `frame_review: true` whose single load-bearing
   assumption is grounded in a **linked accepted ADR** or an **out-of-band
   protocol**, rather than restated inline in the artifact.
2. Run the frame-critique pass (`review.py frame-critique …` → reviewer
   subagent) per `independent-review/SKILL.md`.
3. Observe `VERDICT: needs-changes` attacking that assumption as "most likely to
   be wrong," with no acknowledgement that it may be grounded in the
   linked/external context and no verdict path for "known, accepted residual."

Concrete historical instance: PR #159 (spec 102), frame-critique ran 5 rounds.

## Evidence

- Prompt source — `review.py::build_frame_critique_prompt` (~1287–1335) +
  `_FRAME_CRITIQUE_OUTPUT_FORMAT` (~1222): "be the strongest skeptic they will
  face"; "Concede a `pass` only if the frame survives your strongest attack";
  "find the single load-bearing assumption … most likely to be **WRONG**." The
  "What to read" list mentions linked ADRs only as material to "verify whether
  the load-bearing claims are actually grounded" — with **no** instruction that
  a grounding found there is a *reason not to block*, no wrong-vs-underdocumented
  split, and no bar on asserting absence without a citation.
- PR #159 (spec 102 — derived-index-integrity; ADR-0047 + ADR-0048): 5 rounds,
  genuinely mixed. **Real gap caught (keep this behaviour):** a board-only note
  could be destroyed "green" — later fixed with a `check-board` detector.
  **False positive (this bug):** the ADR-0048 blocker rested on a cross-branch
  numbering collision already handled **out-of-band** by the
  reserve-and-push-immediately protocol (context not in the artifact); it also
  blocked on an `Assumptions: None load-bearing` overclaim.
- Reporter — issue #199 (Marie-Rose). A real frame-critique session
  self-diagnosed: the prompt "has no verdict for 'this is a known, ADR-accepted
  residual.'"

## Hypotheses

- [x] H1 (leading): The prompt structurally guarantees an attack ("strongest
      skeptic," "concede a `pass` only if the frame survives your strongest
      attack") **and** omits any reconcile-against-grounding step, so a
      sound-but-not-locally-restated assumption is reported as "most likely
      wrong." Confirm by reading the builder — the emitted prompt contains the
      attack mandate and contains **no** instruction to (a) reconcile against
      linked accepted ADRs, (b) distinguish false from grounded-elsewhere, or
      (c) cite where it looked before claiming absence. *(Confirmed by direct
      read of `review.py:1287–1335`.)*
- [ ] H2: The false positives are driven by weak/cheap model selection, not the
      prompt. Falsify by: ADR-0020 mandates equal-or-stronger-than-author and
      **forbids** downgrading this pass; PR #159 ran at full strength and still
      false-positived — so model tier is not the cause. *(Falsified: adversarial
      depth was present; the miss was grounding-blindness, not weakness.)*
- [ ] H3: The reviewer simply failed to read the linked ADRs it was pointed at
      (a diligence miss, not a prompt gap). Falsify by: even a reviewer that
      reads them has **no verdict path** for "grounded, accepted residual" —
      linked ADRs are listed only as claims to scrutinize, never as a reason to
      withhold a block. The gap is structural, not diligence.

## Root cause

`build_frame_critique_prompt` + `_FRAME_CRITIQUE_OUTPUT_FORMAT` encode an
**unconditional adversarial mandate with no grounding-aware off-ramp**. Three
specific omissions:

1. **No reconcile-before-block step.** The reviewer is never told to check
   whether the attacked assumption is settled in a linked accepted ADR (→ a
   known residual, a note not a block) before emitting `needs-changes`.
2. **No wrong-vs-underdocumented distinction.** "The assumption is false" and
   "the assumption may be grounded in context I can't see here" both currently
   land as `needs-changes`.
3. **No no-absence-without-citation bar.** The reviewer may assert a
   capability/fact "doesn't exist" without naming where it looked.

Compounding (issue #199's orchestrator-leak strand): the affect is
**person-directed** ("the strongest skeptic **they** will face," "save the
author"), which models the disposition on a person and is the seam through which
artifact-adversarial can bleed toward person-adversarial. Grounding-awareness
and de-person-ifying the affect are the **same edit surface**, so they land
together here.

This is a **process** defect (the prompt that generates the attack), not an
**output** defect — the fix reshapes the generating prompt, not any single
verdict. Per ADR-0020 the adversarial depth must **not** be weakened; the fix
makes the depth *grounding-aware* so it aims at real gaps instead of settled
ones.

**Enumeration (ADR-0052).** The claim "the frame-critique builder is the *only*
place this attack mandate is emitted to a model" is grounded by this session's
scaffold-wide register audit plus the reporter's own root-cause: the adversarial
disposition prose lives only in `review.py::build_frame_critique_prompt` /
`agents/reviewer.md`; everywhere else in the scaffold "adversarial" appears only
as a *pointer/label* to this pass, never as a directive to be adversarial. That
closes the set for the emitted-prompt surface. (The broader "recorded decisions
weaponised into refusal in plain conversation" strand is real but is
**out of scope** for this bug — deferred to a spec, per the routing split.)

## Fix class

`structural_fix` — reshapes the **generating prompt** so the adversarial mandate
carries a grounding-aware off-ramp, rather than patching any single verdict. Not
a `workaround` (root cause is addressed) and not a `guardrail` bolt-on (the
change is to the process that produces the attack).

## Fix

Edit `build_frame_critique_prompt` in `skills/independent-review/review.py`.
All four items land in the **builder body**; `_FRAME_CRITIQUE_OUTPUT_FORMAT`
(the verdict envelope) is deliberately left **unchanged** — mapping a grounded
residual to a *note* within the existing `pass | fail | needs-changes` verdicts
needs no new envelope value here. (Adding an explicit "accepted-residual"
verdict value, which reporter #199 names as absent, is **deferred to the
follow-up spec** per the routing split — recorded here for traceability.)

1. **Reconcile before you block** — instruct the reviewer, before emitting
   `needs-changes`, to check whether the attacked assumption is settled in a
   **linked accepted ADR**; if so, treat it as a **known residual** (a note, not
   a block).
2. **Separate *wrong* from *under-documented*** — "the assumption is false"
   blocks; "the assumption may be grounded in context I can't see here" asks the
   author to **cite the grounding**, it is not a fatal verdict.
3. **No absence-claim without a citation** — the reviewer must not assert a
   capability/fact is absent **without naming where it looked**.
4. **De-person-ify the affect** — replace "save the author" / "the strongest
   skeptic **they** will face" with artifact-directed phrasing; retain the
   **strongest attack** on the frame (ADR-0020: depth must not be weakened).

## Already tried


- 2026-08-11 - green check failed for `skills/independent-review/test_review.py::Bug033FrameCritiqueGroundingAwareTests` (tdd.py exit 1)
(none — first fix attempt)

## Regression test

`skills/independent-review/test_review.py::Bug033FrameCritiqueGroundingAwareTests`
— asserts the emitted frame-critique prompt carries the reconcile-before-block
step, the wrong-vs-under-documented distinction, and the
no-absence-without-citation bar; retains adversarial depth ("strongest attack",
"load-bearing assumption"); and no longer contains the person-directed affect.
Red before the prompt edit, green after.

## Proof

Red→green, witnessed both by the teeth gate and directly:

- **Red** — at `→ FIXING`, `review.py` was reverted to its `origin/main` state
  and the full suite ran (`.jig/test-command` → `scripts/run_tests.py`);
  `Bug033FrameCritiqueGroundingAwareTests` failed **4 of 5** (only the
  depth-retention guard AC4 passed, since the old prompt already carried
  "strongest attack"). The FIXING gate stamped `red_confirmed_at: 2026-08-11`.
- **Green** — with the fix restored, the class passes **5/5** directly
  (`python3 skills/independent-review/test_review.py
  Bug033FrameCritiqueGroundingAwareTests`), and the `→ REVIEWED` gate re-ran the
  full suite green (stamps `green_confirmed_at`).

## Learning

Frame-critique's adversarial mandate needs a **grounding-aware off-ramp**: a
load-bearing assumption grounded in a linked accepted ADR or out-of-band context
is a *known residual* (a note), not a fatal frame flaw. ADR-0020's "never weaken
this pass" is honoured by aiming the **strongest attack at genuinely-exposed**
assumptions — not by softening the verdict. The deeper principle — *recorded
decisions are context to reconcile against, not ammunition to refuse with* —
generalises past the review gate into plain conversation (issue #199's
orchestrator-leak strand) and is carried to a follow-up spec.

## Main recheck

- 2026-08-11 - `origin/main@a642b66` -> reproduces: git show origin/main:skills/independent-review/review.py — build_frame_critique_prompt still emits 'save the author' + 'strongest skeptic they will face' and carries NO reconcile-before-block / grounded-elsewhere / without-citation language. Regression test Bug033FrameCritiqueGroundingAwareTests runs RED on fresh main (4 of 5 fail).
