---
status: DONE
tier: gnarly
severity: medium
claimed_by: claude/issue-130-jig-bugfix-57198e
regression_test: skills/spec-workflow/test_workflow.py::Bug013WidenedClaimTests
main_repro_checked_at: 2026-07-24
main_repro_ref: origin/main@fd7115a
main_repro_result: reproduces
red_confirmed_at: 2026-07-24
green_confirmed_at: 2026-07-24
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 013: slice-claim-covers-only-in-progress

Reported as [issue #130](https://github.com/ramboz/jig/issues/130) (jig 2.8.0).

## Symptom

`claimed_by:` is jig's only machine-readable "someone is working here" signal.
It is stamped **only** on `→ IN_PROGRESS` and actively **cleared** on
`→ REVIEWED`, `→ READY_FOR_IMPLEMENTATION`, and `→ DRAFT`
(`_CLAIM_CLEARING_STATUSES`, `skills/spec-workflow/workflow.py:3725`).

Every pickup surface that reads slice state — `workflow.py orient`, the spec
status board, and the `spec-workflow` SKILL.md pickup flow — therefore reports
a slice under active spec-level work (drafting, frame-critique, re-grounding,
spec review, or **reconciliation**) as carrying no owner, with nothing marking
the limit of what the claim covers.

The damage is not a git conflict. It is that **absence of a claim is read as
evidence of absence of work**, by humans and agents alike, and jig currently
offers nothing to contradict that reading. Because `claimed_by` *does* work for
`IN_PROGRESS`, a reader reasonably generalises it to "jig tracks who is working
on what" — it tracks who is *implementing*.

The sharpest case is `REVIEWED → RECONCILED`: reconciliation is one of the
heaviest write phases in the lifecycle (deviation log, sweep table, DoD ticks,
plus sweeping edits to architecture / refinement-todo / primers), and the claim
is *deliberately cleared* on entry to `REVIEWED`. The phase that rewrites the
most is the phase with the least ownership signal.

Reported incident (bouge, 2026-07-24): two Claude Code sessions, one repo,
separate worktrees. Session A closed a slice, surveyed frontmatter, found
`002-05` at `READY_FOR_REVIEW` with no `claimed_by:`, and twice recommended it
as *"unblocked, unclaimed"*. Session B was actively working it. Session A's
reasoning was sound; the data was structurally incapable of carrying the fact.

## Repro

Mechanically reproduced against this worktree's `workflow.py` in a scratch
project (`docs/specs/900-demo/`, two frontmatter slices):

```
$ python3 skills/spec-workflow/workflow.py orient --project-dir .
jig hint: Scaffolded jig project · active specs: 900 IN_PROGRESS · focus: 900-02 IN_PROGRESS (claimed by session-b)

$ JIG_REVIEW_EVIDENCE_GATE=0 python3 skills/spec-workflow/workflow.py \
    transition docs/specs/900-demo/spec.md 900-02 REVIEWED
transitioned 900-02 — beta: IN_PROGRESS → REVIEWED

$ head -4 docs/specs/900-demo/slice-02-beta.md
---
slice: 900-02
status: REVIEWED
---                       # claimed_by: session-b is GONE

$ python3 skills/spec-workflow/workflow.py orient --project-dir .
jig hint: Scaffolded jig project · active specs: 900 IN_PROGRESS · focus: 900-02 REVIEWED
```

The slice is now entering its heaviest write phase and `orient` names it as the
project focus with no ownership marker and no caveat. A second session reading
this output has no way to tell it apart from a genuinely idle slice.

Same shape for a slice sitting at `READY_FOR_REVIEW` under frame-critique: the
claim was never stamped at all.

## Evidence

1. **Stamp is `IN_PROGRESS`-only** — `workflow.py:1267`:
   `if has_frontmatter and new_status == IN_PROGRESS_STATUS and not release:`
   and the write at `:1374`.
2. **Clear list** — `workflow.py:3725`:
   `_CLAIM_CLEARING_STATUSES = ("REVIEWED", "READY_FOR_IMPLEMENTATION", "DRAFT")`.
3. **Collision guard needs both ends `IN_PROGRESS`** — `workflow.py:1271`
   (local, on-disk) and `_refuse_start_collision` / `:1293` (origin/main,
   spec 051-04). Neither can fire for a non-`IN_PROGRESS` target.
4. **Reader surfaces state no coverage limit:**
   - `orient` (`_focus_summary`, `workflow.py:1662`) appends
     `(claimed by X)` when `claimed_by` is non-empty and says **nothing**
     otherwise — silence is indistinguishable from "free".
   - `collect_slices` docstring (`workflow.py:1747`) documents the field as
     `""` when **"unclaimed"** — the exact over-reading, in jig's own source.
   - `render_status_table` surfaces the claim as a suffix on `IN_PROGRESS`
     status cells only.
   - `spec-workflow/SKILL.md:314–325` and `docs/workflow.md:110–121` describe
     the claim as stopping parallel worktrees "both picking up the same slice"
     without stating that this holds for `IN_PROGRESS` only.
5. **The narrow scope is DELIBERATE, not an oversight** —
   [spec 049 Non-goals](../specs/049-slice-claim-on-in-progress/spec.md):
   *"No claim on `READY_FOR_IMPLEMENTATION` slices. Claiming requires
   committing to start the work. Browsing the board doesn't reserve anything."*
   and *"the field is a runtime claim, not a planning artifact."*
6. **A neighbouring gap is already parked** — [refinement-todo](../refinement-todo.md)
   "push-by-default `IN_PROGRESS` claim + `session-plan` claim-check report"
   (from issue 81) covers a *local-only claim invisible to another worktree*.
   That is a different axis (visibility of an existing claim); this bug is
   about states where no claim exists at all. Related, not duplicate.

## Hypotheses

- [~] H1: The claim field is simply under-scoped — it should be stamped in
  every non-terminal state, and `_CLAIM_CLEARING_STATUSES` is a coding error.
  Falsify by reading spec 049's Non-goals for deliberate scoping.
  → **FALSIFIED AS DIAGNOSIS, ADOPTED AS REMEDY.** Evidence 5 falsifies the
  *causal* claim: the narrow scope is stated design intent (`IN_PROGRESS` =
  "committed to start the work"), reaffirmed by spec 051-04, so
  `_CLAIM_CLEARING_STATUSES` was not a coding error and nothing here was
  "simply" wrong. But widening the field is nonetheless the **fix that
  shipped** — chosen by the maintainer as a deliberate reversal of that
  decision, recorded in [ADR-0043](../decisions/adr-0043-slice-claim-covers-active-lifecycle.md)
  with a spec 049 `## Amendments` entry. The distinction is load-bearing: a
  falsified diagnosis fixed silently is drift; a decision reversed on the
  record is a decision. Its acknowledged cost — conflating "I am implementing
  this" with "I am editing this spec", which can legitimately be concurrent —
  is why the hard refusal was deliberately NOT widened alongside the marker.
- [ ] H3: The clear on `→ REVIEWED` specifically is the defect; the claim
  should survive into reconciliation. Falsify by checking whether AC1 names
  that clear explicitly. → **FALSIFIED**: spec 049 AC1 names
  `IN_PROGRESS → REVIEWED` as an explicit clearing edge (AC4 is the clearing
  criterion; AC1 is the stamp), and 049-01 shipped it as written. This is the designed semantics, not a slip.
- [x] H2 (leading): The defect is on the **reader** side, not the writer side.
  `claimed_by` correctly and honestly means "who is implementing"; every
  surface that consumes it presents slice state as a *complete* availability
  signal without disclosing that ownership data covers exactly one of nine
  states. Confirm by auditing those surfaces for any statement of coverage.
  → **CONFIRMED** by Evidence 4: none of the four reader surfaces states the
  limit, and jig's own `collect_slices` docstring calls an empty field
  "unclaimed".

## Root cause

**jig routes work by slice state and asserts more availability than its data
can support.**

Two design facts are individually correct and jointly produce the failure:

1. `claimed_by` is scoped, by explicit decision (spec 049), to *implementation*
   ownership — a runtime claim taken when a session commits to build.
2. jig's pickup path (`orient`, the status board, `spec-workflow` SKILL.md, and
   the same surfaces mirrored into `compass` / `jig:orient`) instructs a reader
   to choose work by reading slice state, and renders that state as though it
   answered "is anyone here?".

Nothing anywhere states that (1) is narrower than (2) assumes. The result is a
signal that is *reliable right up until it silently isn't* — worse than no
signal, because the working cases teach the wrong generalisation. Applying the
diagnostic question: the bad pickup recommendation is the **output**; the
**process** that produced it is jig's own guidance telling a reader that
unclaimed slice state means free work.

This is the same defect class jig has fixed twice before — slice 045-04
(retiring the false "Stop hook blocks completion" claim) and 078-02 (reframing
a bypass counter that could not answer the question its output implied). In
both, the fix was to make the shipped surface state honestly what it does and
does not cover.

The **minimum** fix for the diagnosed defect is therefore prose: state the
coverage limit where the reader is. That is issue option 3, and it alone would
have prevented the reported incident, since the recommendation was wrong not
because the collision was unavoidable but because absence of a claim was
reported as *"unclaimed"* with unearned confidence.

**What actually shipped is more than the minimum.** The maintainer chose issue
option 1 — widen the marker so the data can carry spec-level presence — and the
honest-prose fix rides along with it (see `## Fix`, reader-side items 6–8).
Widening reverses a recorded decision rather than correcting a slip, so it is
recorded as [ADR-0043](../decisions/adr-0043-slice-claim-covers-active-lifecycle.md)
+ a spec 049 amendment. Options 2 (a separate expiring lease field) and 4 (a
touched-on-another-branch advisory) remain unbuilt and are logged as ADR-0043
open questions; option 4 in particular catches a case no claim field can see —
plain `Edit`-tool writes that never reach `transition`.

## Fix class

`structural_fix`. The remedy changes what the data itself can express, at the
source, rather than papering over the reader. `claimed_by:` stops meaning "who
is implementing" and starts meaning **"which session is working this slice
right now"**, across the whole working lifecycle.

This deliberately reverses spec 049's `IN_PROGRESS`-only Non-goal, so it is
recorded as a decision ([ADR-0043](../decisions/adr-0043-slice-claim-covers-active-lifecycle.md))
with a spec 049 `## Amendments` entry, not slipped in as a bare code change
(ADR-0010).

## Fix

Chosen from issue #130's option 1 (widen the claim) by the maintainer, over the
lighter option 3 (fix the inference in prose only).

**Writer side** (`skills/spec-workflow/workflow.py`):

1. `_CLAIM_WORKING_STATUSES` — the four **working** states
   (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`) — replaces
   the `IN_PROGRESS`-only stamp condition. A session is doing something in each
   of these, so a transition into one stamps its identifier.
2. `_CLAIM_RELEASE_STATUSES` becomes the **release points**: the two
   pickup-queue states (`DRAFT` / `READY_FOR_IMPLEMENTATION`) plus the three
   terminal ones (`DONE` / `DEFERRED` / `ABANDONED`). Entering a queue state is
   semantically a release — "I am done here; it is available". `--release` still
   force-clears anywhere with a logged reason. The two sets partition
   `VALID_STATUSES`, pinned by test so a future status cannot land in neither.

   The queue-state exclusion is the load-bearing correction: `spec-workflow`'s
   pickup step tells a reader to choose the next slice from
   `READY_FOR_IMPLEMENTATION` (or `DRAFT`), so stamping those would leave the
   spec author's branch on a slice that is now free — inverting this bug rather
   than fixing it. See `## Already tried` entry 3.
3. The hard refusal is UNCHANGED: still only when a foreign claim holds a slice
   that is already `IN_PROGRESS`. Two sessions *building* the same slice stays
   an outright refusal (spec 049 AC3 / spec 051-04); two sessions *editing* one
   spec can be legitimate, so widening the block would have manufactured a new
   class of false refusal.
4. **New, non-blocking warnings** for every foreign claim the block does not
   cover **on a working-state transition** — three of them, because there are
   three places a foreign claim can be found. (A transition to a *release point*
   clears a foreign claim without notice, deliberately: the slice is being handed
   back to the queue, which is what a release means. That silence is asserted —
   not merely implied — by `test_pickup_queue_states_are_not_stamped`, which
   captures stderr and requires it empty.) The three: (a) on the caller's own copy in `transition`; (b) on the `origin/main`
   copy when `--push`/`--pr` is about to *replace* it in
   `_reserve_claim_on_main`; (c) on the `origin/main` copy at start-of-build in
   `_refuse_start_collision`, for a working state other than `IN_PROGRESS`. Each
   names the holder and the state; (a) and (b) also name the `--release` escape,
   and a single transition never prints two near-identical warnings about the
   same holder — the start-guard takes the already-warned identifier and stays
   quiet. (b) and (c) were
   added after review: without (b) the reservation silently overwrote another
   session's trunk claim — a state newly reachable because of this change —
   and without (c) `--push` would have published a trunk field that nothing
   reads, making "so other worktrees see it" true only after a merge.
5. `--push` / `--pr` reservation on `origin/main` widens to the same working
   states, so a session can make its claim visible to parallel worktrees at any
   phase — not only when it starts building. **First cut shipped this broken and
   all three review passes caught it** (see `## Already tried`): the call site
   was widened without touching `_reserve_claim_on_main`, which hardcoded
   `status: IN_PROGRESS`. Corrected: the target state is threaded in, and the
   reservation publishes `status:` to the trunk copy **only** for an
   `IN_PROGRESS` target — that one write is load-bearing because
   `_refuse_start_collision` reads exactly `status: IN_PROGRESS` + a foreign
   claim off `origin/main`. For every other working state the reservation
   publishes the **claim alone** and leaves trunk `status:` untouched: trunk
   lifecycle state is owned by the landing flow, not by a feature branch's
   in-flight transitions. The idempotent-re-claim short-circuit is re-keyed on
   what the reservation would actually write.

**Reader side:**

6. `render_status_table` renders `<STATUS> (<claimed_by>)` for every **working**
   state, not `IN_PROGRESS` only, so the board can show spec-level presence —
   while pickup-queue rows stay plain, so the board still answers "what is
   free" correctly.
7. `collect_slices`' docstring stops calling an empty field "unclaimed".
8. `docs/workflow.md` + `spec-workflow/SKILL.md` restate what the claim covers
   and, critically, what it still does not (see Residual risk).

**Residual risks, stated rather than hidden.**

1. **A claim is still LOCAL by default.** Across two worktrees on unpushed
   branches, session A cannot see session B's claim regardless of which states
   carry it — the separate, already-parked
   [refinement-todo](../refinement-todo.md) item (push-by-default claims, from
   issue 81). **The reported incident is exactly this shape**, so coverage alone
   does not close it; see [ADR-0043](../decisions/adr-0043-slice-claim-covers-active-lifecycle.md)
   Context, which says so outright. This fix makes the data *capable* of carrying
   presence, makes `--push` usable at every working state, and gives a pushed
   claim a consumer; it does not make local claims telepathic.
2. **A claim is an entry event, not live presence.** It names the session that
   last *moved* the slice into a working state. A session that picks up a slice
   someone else transitioned does not appear until its own next transition, so
   the field can name a session that has already left. jig has no better hook —
   it cannot observe plain `Edit`-tool writes at all (spec 049 non-goal, still
   standing). Documented as a presence *hint*, not a lock.
3. **The trunk claim is advisory outside `IN_PROGRESS`, deliberately.** Both
   `origin/main` read paths only warn there: the start-of-build guard warns on a
   foreign trunk claim at `READY_FOR_REVIEW` / `REVIEWED` / `RECONCILED`, and the
   trunk hard-refusal is both-ends-`IN_PROGRESS`, matching the local path —
   gating it that way was itself a review finding (`## Already tried` entry 5).
   A refusal outside that case is the false-block class this fix avoids. Two
   sessions can therefore take turns overwriting a non-enforced trunk claim.
   **One case is NOT merely advisory, and is now handled:** a trunk copy at
   `status: IN_PROGRESS` under a foreign claim is *enforced* —
   `_refuse_start_collision` hard-blocks on exactly that pair — so a claim-only
   reservation must not replace it. Doing so would transfer a live lock and get
   the original builder refused, naming the reviewer: the same false-block class,
   reached sideways. The reservation now warns and **skips the trunk write**; the
   local transition still proceeds, so `--push` at a working state is
   **best-effort** — it can warn, push nothing, and exit 0. The condition takes
   **two** tests, not one: the trunk `status:` is what makes a lock *enforceable*,
   and a *different* holder (or none) is what makes replacing it *harmful*. So an
   **unclaimed** `IN_PROGRESS` trunk copy is equally off-limits, while our **own**
   claim falls through to a silent no-op. Both halves were got wrong in turn — see
   `## Already tried` entries 5 and 7 — and all three conjuncts are now
   mutation-checked. Pinned by
   `test_push_at_working_state_does_not_refuse_on_foreign_in_progress_trunk`,
   `test_push_skips_an_unclaimed_in_progress_trunk_copy`,
   `test_push_at_working_state_is_silent_about_our_own_in_progress_trunk_claim`,
   and `test_push_to_in_progress_claims_an_unclaimed_in_progress_trunk_copy`.
   Logged as ADR-0043 open question 4.
4. **`READY_FOR_REVIEW` is classified as a working state on judgment, not
   measurement.** Its name is queue-shaped; it is treated as working because it
   is the reported incident's state and because in jig practice the author
   transitions into it and runs the review in the same session. ADR-0043 kill
   criterion 1 watches for the counter-evidence.
5. **`orient`'s focus line was NOT changed.** Of the four reader surfaces named
   in Evidence 4, three were fixed (board render, `collect_slices` docstring,
   the prose surfaces). `_focus_summary` already appended `(claimed by X)`
   whenever the field was non-empty, so it inherits the widened coverage for
   free — but it still prints nothing when a working-state slice has no claim,
   i.e. it does not itself say "unknown, not free". The prose surfaces carry
   that caveat instead.
6. **A pushed trunk claim is never released.** `--release` and the release-point
   clear both write locally only, so a claim published to `origin/main` persists
   there until the slice lands. Pre-existing from spec 049, not introduced here —
   but widening `--push` to four working states increases how many trunk claims
   can be in that state at once. Flagged by the round-7 craft pass as worth
   tracking rather than fixing in a bug.
7. **The warning has few opportunities to fire until claims are pushed by
   default.** Claim identity is the branch name, so same-branch sessions never
   look foreign to each other, and cross-branch sessions cannot read the field
   without `--push`. ADR-0043 open question 6 states this rather than counting
   the warning as delivered value.

## Already tried

**First cut of the widening was over-broad in two places; both were caught, one
by the existing suite and one by review. Neither is a wrong diagnosis — both are
the difference between widening a *marker* and widening the *machinery around
it*, which are separate decisions.**

1. **Widened the hard refusal by accident.** Replacing the
   `new_status == IN_PROGRESS` stamp condition with "any active state" also
   widened the block that shares that condition, so a session could no longer
   move *its own* slice out of `IN_PROGRESS` — the refusal fired on
   `IN_PROGRESS → REVIEWED` whenever the claim identifier differed. Three
   pre-existing `SliceClaimTests` failed immediately and correctly. Fixed by
   requiring **both** ends to be `IN_PROGRESS`, which is what the pre-widening
   code meant implicitly (it was only ever reached for an `IN_PROGRESS`
   target). Lesson recorded in `docs/memory/learnings.md`.
2. **Widened the trunk reservation call site but not the callee.**
   `_reserve_claim_on_main` hardcoded `set_frontmatter_field(content, "status",
   "IN_PROGRESS")`, so `transition … RECONCILED --push` would have pushed
   `status: IN_PROGRESS` to `origin/main`. Two harms, not one: it regresses the
   shared trunk's view of the slice, and it *fabricates* the foreign-
   `IN_PROGRESS` state that `_refuse_start_collision` hard-blocks on — i.e. it
   would have manufactured precisely the false-refusal class ADR-0043 claims to
   avoid. It had **zero test coverage**, which is why it survived to review;
   all three passes flagged it independently. Fixed as described in `## Fix`
   item 5, with `test_push_at_non_in_progress_state_does_not_rewrite_trunk_status`
   and two siblings now asserting the *content* written to the ephemeral claim
   worktree rather than only the git argv. The first draft of that test passed
   vacuously by matching on content instead of path (it captured the caller's
   own slice write); it filters on the `jig-claim-` temp path now.
3. **Stamped the pickup queue, inverting the bug.** The first two cuts stamped
   all six non-terminal states, including `DRAFT` and
   `READY_FOR_IMPLEMENTATION`. Those are precisely the two states
   `spec-workflow/SKILL.md` tells a reader to pick work from, so the spec
   author's `→ READY_FOR_IMPLEMENTATION` left their branch name on a slice that
   was now free. Reproduced before narrowing: the board rendered
   `READY_FOR_IMPLEMENTATION (author-branch)` for an available slice, and the
   implementer's first `→ IN_PROGRESS` printed "another session may be working
   it right now" — deterministically, on the most routine path in jig. That is
   bug 013 with the sign flipped: "blank reads as free" became "residue reads as
   occupied", on the same surface, and a warning that fires on every pickup
   trains readers to ignore warnings. Caught by the frame-critique pass, which
   also observed that spec 049's Non-goal made two claims and the first
   amendment had rebutted only one of them ("browsing doesn't reserve" — but the
   real objection is that *the actor is not the future worker*). Fixed by
   splitting the lifecycle on meaning rather than terminality: working states
   stamp, queue states release. Spec 049's `READY_FOR_IMPLEMENTATION` Non-goal is
   preserved, and two of AC4's three clearing edges revert to unchanged — the
   reversal is now materially smaller than the first draft claimed.
   `test_author_to_implementer_handoff_is_silent` and
   `test_pickup_queue_states_are_not_stamped` pin it.
4. **Silently overwrote a foreign claim on the shared trunk.** Having correctly
   decided not to publish trunk `status:` outside `IN_PROGRESS` (entry 2), the
   reservation still wrote trunk `claimed_by:` over another session's claim with
   no notice — at states where such a claim could not previously exist, so the
   hole was newly opened by this change. That contradicted the fix's own headline
   promise of a warning for every foreign claim the block does not cover. Flagged
   independently by the craft and bug-review passes. Fixed by warning in
   `_reserve_claim_on_main` before the replace, and — symmetrically — by teaching
   `_refuse_start_collision` to warn on a foreign trunk claim at a
   non-`IN_PROGRESS` working state, without which the widened `--push` wrote a
   field nothing consumed.
5. **Widened a hard refusal on the trunk path without noticing.** Same shape as
   entry 1, one layer down. `_reserve_claim_on_main`'s foreign-claim refusal
   tested only the *trunk* copy's status, which was sufficient while the callee
   could only ever be reached for an `IN_PROGRESS` target. Widening the call site
   made it reachable for `REVIEWED --push` against a trunk copy the implementer
   is still building — so a reviewer worktree recording a verdict would have been
   refused outright, verbatim the false-block class ADR-0043 claims to avoid. It
   was also asserted *not* to happen in five separate prose surfaces. Fixed by
   gating the refusal on the target being `IN_PROGRESS` (both ends, matching the
   local path) and letting the new warning carry every other case;
   `test_push_at_working_state_does_not_refuse_on_foreign_in_progress_trunk` and
   `test_push_to_in_progress_still_refuses_on_foreign_in_progress_trunk` pin both
   directions. Flagged independently by the bug-review and craft passes.

   **The pattern across entries 1, 4 and 5:** widening a marker, widening the
   blocking that shares its condition, and widening the machinery that consumes
   it are three separate decisions. Each time only the first was intended.
6. **Recorded two regression tests that were never written.** Entry 5's fix was
   logged here as pinned by
   `test_push_at_working_state_does_not_refuse_on_foreign_in_progress_trunk` and
   `test_push_to_in_progress_still_refuses_on_foreign_in_progress_trunk`.
   Neither existed: the edit script that added them asserted on a *later*
   substitution and raised before its single `write_text`, so every earlier
   substitution in that script was discarded — while its per-step progress output
   had already printed `ok: trunk refusal tests`. That printed line was treated as
   confirmation of a write that never happened. **Mechanism, not carelessness:**
   a multi-step edit script that batches N substitutions and writes once is
   all-or-nothing, but its logging is per-step, so partial-failure output is
   indistinguishable from success. Caught by the round-4 bug-review and craft
   passes, both of which grepped for the names.

   Worse than the bookkeeping error: the behaviour really was unguarded, on
   **both** paths. Dropping `target_is_in_progress` from the trunk refusal, or
   `new_status == IN_PROGRESS_STATUS` from the local one, left the entire suite
   green — so the false-refusal case ADR-0043 names as the thing it avoids had no
   regression guard at all. Now pinned by five tests, and each conjunct was
   **mutation-checked** (removed, suite re-run under `python3 -B`, confirmed red,
   restored) rather than assumed to discriminate.

   The general fix for this class: verify an edit landed by grepping for the
   artifact, never by trusting the edit script's own echo. Recorded in
   `docs/memory/learnings.md`.
7. **Over-corrected the enforced-lock condition, then under-corrected it.** Entry
   5's guard keyed on a *non-empty* trunk claim, which left an unclaimed
   `IN_PROGRESS` trunk copy stampable (round-5 bug-review). Dropping the claim
   test closed that hole — and swept in the session's **own** claim, so the
   documented `IN_PROGRESS --push` → `REVIEWED --push` sequence warned a session
   about its own live lock and advised force-releasing it (round-6 bug-review +
   craft, independently). A false alarm on this fix's flagship path: the same
   "warnings that fire on routine work get ignored" failure as entry 3.

   The distinction that was flattened, twice, in opposite directions: **what makes
   a lock *enforceable* (the trunk `status:`) and what makes replacing it *harmful*
   (it belongs to someone else) are two different tests, and both are required.**
   Final condition: `not target_is_in_progress and existing != identifier and
   origin_status == IN_PROGRESS`. An empty `existing` still trips it (hole stays
   closed); an own claim falls through to the benign idempotent no-op. Both
   directions are now mutation-checked — re-adding `existing and` reddens the
   suite, and removing `existing != identifier` reddens it too.

**Six of the seven entries above are the same mistake:** a condition, a block,
a condition, a block, or a consumer that was correct only because of a narrower
context it no longer sits in. Widening anything in this machinery means
re-deriving every condition that was silently relying on the old scope — not
adjusting the one you meant to change.


## Regression test

`skills/spec-workflow/test_workflow.py::Bug013WidenedClaimTests` — 28 test
methods (several parameterized over the state sets via `subTest`).
Witnessed **red** before the fix — `red_confirmed_at` stamped by the `bug.py`
`→ FIXING` gate shelling to `tdd.py`. `green_confirmed_at` is stamped by the
`→ REVIEWED` gate and is therefore still pending at the time of writing; the
suite is green locally (see `## Proof`), but the machine attestation lands with
that transition.

What it pins, and why each matters:

- `test_claim_survives_transition_to_reviewed` — **the headline.** The reported
  failure minimized: a claimed `IN_PROGRESS` slice moved to `REVIEWED` used to
  lose its owner on the way into reconciliation, the heaviest write phase. Fails
  outright pre-fix.
- `test_claim_stamped_on_every_working_state` /
  `test_claim_cleared_on_queue_and_terminal_states` — the coverage rule in both
  directions: the four working states stamp; the two pickup-queue states and the
  three terminal states release.
- `test_claim_states_partition_the_lifecycle` — pins the stamp/clear split as a
  total partition of `VALID_STATUSES`, so a tenth status cannot silently land in
  neither set. The split *is* the semantic core of the fix.
- `test_pickup_queue_states_are_not_stamped` /
  `test_status_board_never_labels_a_pickup_queue_row_with_an_owner` /
  `test_author_to_implementer_handoff_is_silent` — **the anti-inversion guards.**
  A free slice must read as free, on the board and at pickup, and jig's most
  routine handoff must be silent. See `## Already tried` entry 3 for what these
  exist to prevent.
- `test_foreign_claim_outside_in_progress_warns_and_proceeds` /
  `test_no_warning_when_claim_is_own` — the new signal fires when you walk into
  another session's work, and stays silent on ordinary sequential work (the
  false-positive guard).
- `test_in_progress_collision_still_hard_blocks` — **anti-regression on the
  relaxation.** Two sessions *building* one slice must still be refused; this
  test is what stops a future edit from quietly turning the block into a
  warning.
- `test_push_at_non_in_progress_state_does_not_rewrite_trunk_status` /
  `…_in_progress_still_publishes_status_to_trunk` /
  `…_is_idempotent_when_already_ours` — the trunk-reservation contract, asserting
  the *content* written to the ephemeral claim worktree (filtered by the
  `jig-claim-` path). These exist because the first cut shipped this branch
  broken with no coverage at all.
- `test_reservation_warns_before_replacing_a_foreign_trunk_claim` /
  `test_start_guard_warns_on_foreign_trunk_claim_at_a_working_state` /
  `test_start_guard_silent_when_trunk_claim_is_at_a_queue_state` — the two
  `origin/main` notice paths added in review, plus the silence case.
- `test_local_foreign_in_progress_claim_does_not_block_a_working_target` /
  `test_push_at_working_state_does_not_refuse_on_foreign_in_progress_trunk` /
  `test_push_to_in_progress_still_refuses_on_foreign_in_progress_trunk` — **the
  false-refusal guards**, on the local and trunk paths respectively, plus the
  anti-regression on the relaxation. These pin the case ADR-0043 names as the
  false block it avoids (a reviewer worktree recording a verdict on a slice the
  implementer still holds) and, on the trunk path, that an *enforced* claim is
  skipped rather than transferred. They exist because `## Already tried` entry 6
  found the behaviour completely unguarded.
- `test_one_transition_never_warns_twice_about_the_same_holder` /
  `test_dedup_does_not_hide_a_different_trunk_holder` /
  `test_reservation_warning_is_deduped_against_the_on_disk_warning` — the
  `already_warned` dedup on both consumers (start-guard and reservation), plus
  the guard that a *different* holder is still reported.
- `test_push_skips_an_unclaimed_in_progress_trunk_copy` /
  `test_push_at_working_state_is_silent_about_our_own_in_progress_trunk_claim` —
  the enforced-lock condition from both sides: an *unclaimed* IN_PROGRESS trunk
  copy is equally off-limits, while our *own* trunk claim must stay silent. Each
  direction is mutation-checked; see `## Already tried` entry 7.
- `test_status_board_renders_claim_for_working_non_in_progress_states` — the
  reader surface that reported "unclaimed".
- `test_prose_only_slice_is_still_a_no_op` /
  `test_push_on_prose_only_slice_refuses_at_any_active_state` — legacy
  prose-only slices still carry no claim and no synthesized `---` block.

**Two** pre-existing tests had their assertions **inverted**, not deleted,
because they pinned the reversed edge: `SliceClaimTests.test_claim_carried_into_reviewed`
(renamed from `…_cleared_on_reviewed`) and
`StatusBoardClaimRenderTests.test_active_states_surface_claim_terminal_states_do_not`.
Each carries an in-place `AMENDED by ADR-0043` note. Note the count *fell* from
four to two once the design was narrowed: `test_claim_cleared_on_back_to_ready`
and `…_on_back_to_draft` were inverted by the over-wide first cut and have been
restored to their original spec 049 assertions, which is the clearest signal that
the narrowing shrank the reversal. The surviving half of spec
049 AC2 ("byte-identical render when unclaimed") is still pinned, by the new
`test_unclaimed_active_states_render_plain`.

## Proof

- **Mutation-checked, not assumed.** Every conjunct that gates a refusal or a
  decline was removed, the suite re-run under `python3 -B` (no stale bytecode),
  confirmed **red**, and restored. Five checks in total:
  - `new_status == IN_PROGRESS_STATUS` on the **local** refusal — without it a
    session cannot move its own slice out of `IN_PROGRESS`.
  - `target_is_in_progress` on the **trunk** refusal — without it a reviewer
    worktree is refused on `REVIEWED --push`.
  - `existing and` re-added to the **decline** — reopens the unclaimed-trunk hole.
  - `existing != identifier` removed from the **decline** — warns a session about
    its own claim on the routine `--push` path.
  - `not target_is_in_progress` removed from the **decline** — a start-of-build
    claim can no longer be re-taken on a slice the session itself released.

  Before these were added, the first two and the last three each left the suite
  fully green when deleted.
- **Full suite:** 3526 tests, `OK (skipped=4)`, exit 0. (`scripts/run_tests.py`
  also prints a `committed host packages are stale` line — that is stdout from a
  *passing* test, `test_build_host_packages.test_check_flag_wires_to_check_drift`,
  which deliberately corrupts a temp fixture to exercise the drift guard's error
  path. `build_host_packages.py --check` reports in sync.)
- **Original repro re-run green** (`## Repro` fixture, same commands): the claim
  now survives `IN_PROGRESS → REVIEWED`, and `orient` reports
  `focus: 900-02 REVIEWED (claimed by session-b)` where it previously printed
  `focus: 900-02 REVIEWED` with no owner. The board renders the incident's exact
  shape — a `READY_FOR_REVIEW` slice — as `READY_FOR_REVIEW (session-c)` instead
  of bare `READY_FOR_REVIEW`.
- **Warning verified live:** a foreign session transitioning another's
  `READY_FOR_REVIEW` slice gets the named-holder warning and **exit 0**
  (non-blocking).
- **Refusal verified live:** two sessions targeting `IN_PROGRESS` on one slice
  still fails with **exit 2** and names the holder.
- **Terminal release verified live:** `→ DEFERRED` clears `claimed_by:`.
- **Host packages rebuilt** (`scripts/build_host_packages.py`) so both mirrors
  carry the change.

### Verification — the original reported repro (gnarly tier)

Gnarly tier re-runs the **originally reported** scenario, not just the proxy test.
Issue #130's repro is two worktrees on one repo, two branches, with session B
working slice `002-05` at `READY_FOR_REVIEW` and never reaching `IN_PROGRESS`.
Built for real — bare `origin.git`, `main` plus a `session-b` linked worktree,
the incident's own slice number and slug — and run against both trees:

**Pre-fix (`origin/main@fd7115a`), session B transitions to `READY_FOR_REVIEW`:**

```
transitioned 002-05 — waking-hours-window: READY_FOR_REVIEW → READY_FOR_REVIEW
---
slice: 002-05
status: READY_FOR_REVIEW      # no claimed_by — the field cannot carry it here
---
jig hint: … focus: 002-05 READY_FOR_REVIEW
```

The surveying session sees a live slice with no owner and no caveat. That is the
reported failure: *"unblocked, unclaimed"*, twice recommended.

**Post-fix, same scenario, session B using `--push`:**

```
claimed 002-05 — waking-hours-window on origin/main as 'session-b'
---
slice: 002-05
status: READY_FOR_REVIEW
claimed_by: session-b
---
```

and session A, after `git fetch` + fast-forward:

```
jig hint: … focus: 002-05 READY_FOR_REVIEW (claimed by session-b)
| [002-window](002-window/spec.md) | 002-05 — waking-hours-window | READY_FOR_REVIEW (session-b) |
```

Both pickup surfaces now name the holder on the exact slice and state from the
incident.

**Attested honestly — what this run does and does not prove.** It proves the
reported *state* can now carry and render presence, which it structurally could
not before. It does **not** prove the incident is impossible: session B had to
opt in with `--push`, and session A had to integrate `origin/main`. Without both,
A's local copy still shows blank — the visibility axis, parked as push-by-default
in [refinement-todo](../refinement-todo.md) and named in
[ADR-0043](../decisions/adr-0043-slice-claim-covers-active-lifecycle.md) OQ1,
which also records that publication alone is insufficient because the surveying
surfaces read the local copy. Residual risks 1 and 7 state the same limit.

## Learning

Recorded in [docs/memory/learnings.md](../memory/learnings.md) as *"Bug 013: a
partial signal teaches a total inference"*: a mechanism that answers a narrow
question reliably gets read as answering the broad one, and the working cases are
what make the misreading stick. Coverage limits must be documented where the
*reader* is, not only where the writer is; the heaviest-write phase deserves the
strongest marker and lifecycle machinery tends to give it the weakest; and
"absence of record" must be stated as such, out loud, because jig's own docstring
calling an empty field "unclaimed" was the whole bug in miniature. Process
half: widening a marker and widening the machinery around it are separate
decisions — conflating them produced both regressions in `## Already tried`.

## Main recheck

- 2026-07-24 - `origin/main@fd7115a` -> reproduces: Ran the issue-130 repro against a detached worktree at origin/main@fd7115a: a slice with claimed_by: session-b at IN_PROGRESS transitioned to REVIEWED loses claimed_by entirely, and 'workflow.py orient' then names 900-02 REVIEWED as project focus with no ownership marker and no caveat — indistinguishable from an idle slice.
