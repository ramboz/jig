---
status: Accepted
dependencies: []
last_verified: 2026-07-24
frame_review: true
---

# ADR-0045: Slice Claim Covers Active Lifecycle

## Status

Accepted (2026-07-24)

Amends [spec 049](../specs/049-slice-claim-on-in-progress/spec.md) — its
`IN_PROGRESS`-only stamp scoping, **but not** its Non-goal on
`READY_FOR_IMPLEMENTATION`, which is preserved (see Recommended Decision).

Does not supersede [ADR-0015](adr-0015-worktree-aware-reservation.md): the
reservation *shape* (fetch → read trunk copy → ephemeral detached worktree →
push by SHA → PR fallback) is untouched. It does **narrow the reservation's
payload** — `_reserve_claim_on_main` now takes the transition's target state and
publishes trunk `status:` only for `IN_PROGRESS` — and adds a warning before it
replaces a foreign trunk claim. Both are recorded under Recommended Decision
rather than left in code comments.

## Context

`claimed_by:` is jig's only machine-readable "a session is working here"
signal. Spec 049 scoped it deliberately to *implementation* ownership: it is
stamped on `→ IN_PROGRESS` and cleared on `→ REVIEWED` /
`READY_FOR_IMPLEMENTATION` / `DRAFT`, with the stated Non-goal *"Claiming
requires committing to start the work. Browsing the board doesn't reserve
anything."*

That scoping was coherent on its own terms. It collides with a second jig
design fact: **jig routes agent sessions to work by reading slice state.**
`workflow.py orient`, the spec status board, and the `spec-workflow` pickup
flow all instruct a reader to choose the next slice from lifecycle state, and
they render that state as though it answered "is anyone here?".

It does not. Ownership data covers one of nine states. Every other active
state — `DRAFT` (authoring ACs, SPIDR split), `READY_FOR_REVIEW` (spec review,
frame-critique, re-grounding), `READY_FOR_IMPLEMENTATION`, and above all
`REVIEWED → RECONCILED` (deviation log, sweep table, DoD ticks, plus sweeping
edits across architecture / refinement-todo / primers) — is unmarked. The
phase that rewrites the most is the phase with the least ownership signal,
because the claim is *deliberately cleared* on entry to `REVIEWED`.

Humans coordinate out-of-band. Agent sessions have only the repo. So absence
of a claim reads as evidence of absence of work, and jig offers nothing to
contradict it. Worse, because the mechanism *does* work for `IN_PROGRESS`, it
teaches the wrong generalisation: a reader concludes "jig tracks who is working
on what" when it tracks who is *implementing*. A signal that is reliable right
up until it silently isn't is worse than no signal.

Reported as [issue #130](https://github.com/ramboz/jig/issues/130) with a real
incident (bouge, 2026-07-24): one session surveyed slice frontmatter, found a
`READY_FOR_REVIEW` slice with no `claimed_by:`, and twice recommended it as
*"unblocked, unclaimed"* while a second session was actively working it.
Diagnosed as [bug 013](../bugs/013-slice-claim-covers-only-in-progress.md).

**Two axes, and this decision moves only one of them.** Stated plainly, because
the frame-critique pass was right to attack it: the reported incident was two
worktrees on **separate branches**. A claim is a frontmatter field on the branch
you are standing on, and it is local unless `--push`ed, so a claim stamped by
Session B would still have been unreadable from Session A's worktree. **This
decision does not, by itself, prevent the incident that motivated it.** It fixes
*coverage* — whether a claim exists at all during spec-level phases — while the
incident also turns on *visibility* — whether an existing claim can be read from
another worktree. Visibility is separately parked as the push-by-default item in
[refinement-todo](../refinement-todo.md) (from issue 81), and widening coverage
raises its value without settling it. The mechanical repro in bug 013 is
single-tree: it proves the coverage gap is real, not that coverage was the
binding constraint in the incident. Both axes must move before the reported
failure class is closed; this is the one the maintainer chose to move first.

## Decision Options Considered

### Option A: Widen the claim to every active (non-terminal) state — REJECTED (refined into A′)
Stamp `claimed_by:` on transition into any of the six non-terminal states;
clear only on the terminal three (`DONE` / `DEFERRED` / `ABANDONED`) and on
`--release`.
- **Pros:** Makes the data structurally capable of carrying the fact at all,
  which no amount of prose can. Reuses the shipped field, identifier resolution,
  release path, audit log, and `--push`/`--pr` reservation — no new vocabulary,
  no second field for a reader to learn. The `RECONCILED` and `REVIEWED` phases, the highest-damage
  cases, are covered by the same rule as the rest.
- **Cons:** Conflates "I am implementing this" with "I am editing this spec",
  which can legitimately be concurrent. Reverses a recorded Non-goal.
  **Fatally: it stamps the pickup-queue states, which inverts the bug** — see
  Option A′ for the mechanism and how it was caught. That is why plain A was
  implemented, tested green, and then narrowed rather than shipped.

### Option A′: Widen to the WORKING states only, preserving the pickup queue — CHOSEN (refinement of A)
Stamp `claimed_by:` on `READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` /
`RECONCILED`; treat `DRAFT` and `READY_FOR_IMPLEMENTATION` as release points
alongside the terminal three.
- **Pros:** Delivers everything Option A was chosen for — the reported
  incident's state (`READY_FOR_REVIEW`) and the highest-damage phase
  (`REVIEWED → RECONCILED`) both covered — while keeping spec 049's Non-goal on
  `READY_FOR_IMPLEMENTATION` intact. The rule is not arbitrary: those two states
  are exactly the ones `spec-workflow/SKILL.md` step 2 tells a reader to choose
  work from, so they *are* the pickup queue. Reduces the size of the reversal:
  two of spec 049 AC4's three clearing edges survive unchanged.
- **Cons:** The stamp/clear split is now a semantic judgment ("working" vs
  "queued") rather than a syntactic one ("non-terminal" vs "terminal"), so a
  future tenth status needs a deliberate classification. Mitigated by a test
  pinning that the two sets partition `VALID_STATUSES`.
- **Why plain Option A was wrong:** stamping the queue states INVERTS this bug.
  The spec author's `→ READY_FOR_IMPLEMENTATION` leaves their branch name on a
  slice that is now free, so the board labels every ready slice with a departed
  owner and the implementer's first `→ IN_PROGRESS` warns on the routine path.
  "Blank reads as free" becomes "residue reads as occupied" — the same defect
  with the sign flipped, on the same surface. Found by the frame-critique pass
  and reproduced before narrowing; the six-state version was implemented, tested
  green, and then narrowed.

### Option A″: Stop clearing on `→ REVIEWED`, change nothing else — REJECTED (too narrow)
Remove `REVIEWED` from the clearing list and leave the stamp on `IN_PROGRESS`
only. **Not quite the one-line change an earlier draft called it**, per the
round-7 frame-critique: spec 049's clear list carried no terminal states, so
dropping `REVIEWED` would let an `IN_PROGRESS` claim survive
`REVIEWED → RECONCILED → DONE` and land on a finished slice with nothing
releasing it. A″ therefore also needs terminal clearing added — the classification
question re-enters, in smaller form.
- **Pros:** Covers the self-declared highest-damage phase
  (`REVIEWED → RECONCILED` reconciliation) at the smallest possible cost. Needs
  no working/queue partition, no reservation payload rule, and does not depend on
  the uncertain `READY_FOR_REVIEW` classification (OQ3). Reverses exactly one
  recorded edge.
- **Cons:** Leaves `READY_FOR_REVIEW` — **the reported incident's own state** —
  permanently unmarked, so the concrete failure that prompted this work stays
  structurally unexpressible. Also produces a stranger rule than A′ ("the claim
  survives one specific forward edge") which is harder to reason about than
  "working states carry a claim", and gives no basis for classifying a future
  state.
- **Why rejected — and the cost accounting, honestly.** An earlier draft of this
  ADR claimed A′ "costs one extra tuple and a partition test" over A″. That was
  wrong, and contradicted this document's own Consequences three lines later; the
  round-6 frame-critique caught it. Because A″ keeps the stamp `IN_PROGRESS`-only,
  `_reserve_claim_on_main` is never called with a non-`IN_PROGRESS` target, so A″
  avoids **all** of: the payload rule, the decline-to-write invariant, the
  `--push` best-effort downgrade, and the silent claim-transfer consequence. A″ is
  several times cheaper, not marginally.

  A′ is chosen anyway for one reason: it covers `READY_FOR_REVIEW`, the reported
  incident's own state, and A″ leaves it permanently unmarkable. That benefit is
  **contingent on the same parked visibility item** as everything else here (OQ1)
  — Context already concedes A′ does not prevent the incident on its own — so a
  reader should understand the A′-over-A″ choice as buying optionality on the
  incident's state at a real, immediate cost, not as a cheap strict improvement.
  If push-by-default is never built, A″ would have been the better trade.

### Option B: A separate lightweight `active_session:` lease field with a timestamp
Orthogonal to `claimed_by`, refreshed by any transition or slice edit;
expresses presence rather than ownership.
- **Pros:** Keeps ownership and presence as distinct concepts, which they
  genuinely are. A timestamp allows staleness to expire on its own, so an
  abandoned session does not park a slice indefinitely.
- **Cons:** A second concurrency field every reader, renderer, board, and skill
  must learn, plus lease-expiry semantics (how long is stale? who refreshes?
  what refreshes it, given jig cannot see plain `Edit`-tool writes?) — a spec's
  worth of design, for a problem whose damage is a wrong pickup recommendation.
  Two overlapping signals also reintroduce the same misgeneralisation risk on a
  new axis.

### Option C: Leave the mechanism; fix the inference in prose only
Teach `orient`, the status board, and the pickup guidance to state that claim
data covers `IN_PROGRESS` only and is not evidence a slice is free.
- **Pros:** Cheapest, reverses nothing, and alone would have prevented the
  reported incident — the recommendation was wrong because it was stated with
  unearned confidence, not because the collision was unavoidable.
- **Cons:** Leaves jig unable to *ever* express spec-level presence; the honest
  answer becomes a permanent "we can't tell you". Every future reader surface
  must remember to repeat the caveat, and prose caveats decay (jig has had to
  retire two over-claiming statements already — slice 045-04, slice 078-02).

### Option D: A pre-edit "recently touched on another branch" advisory
Non-blocking warning when a slice's file was modified on another branch
recently.
- **Pros:** Catches presence that no claim field can see, including plain
  `Edit`-tool writes that bypass the helper entirely.
- **Cons:** Needs cross-branch git inspection on a hot path; "recently" is a
  tunable with no obvious value; noisy on healthy sequential work. Orthogonal
  to this decision — it could be added later on top of any option here.

## Recommended Decision

**Option A′** — Option A's widening, restricted to the working states — with
the refusal semantics deliberately held narrow.

The lifecycle splits two ways for ownership. **Working states**
(`READY_FOR_REVIEW`, `IN_PROGRESS`, `REVIEWED`, `RECONCILED`) mean a session is
doing something, and stamp. **Release points** — the pickup-queue states
`DRAFT` and `READY_FOR_IMPLEMENTATION`, plus the terminal `DONE` / `DEFERRED` /
`ABANDONED` — mean the slice is waiting for whoever comes next, and clear.
Entering a queue state is semantically a *release*: "I am done here; it is
available."

**On `orient`'s ranking, which looks like a second pickup queue and is not.**
`_ORIENT_FOCUS_ORDER` ranks `IN_PROGRESS` → `REVIEWED` → `RECONCILED` →
`READY_FOR_IMPLEMENTATION` → `READY_FOR_REVIEW` → `DRAFT`, so `orient` surfaces a
`REVIEWED` slice *ahead* of a `READY_FOR_IMPLEMENTATION` one and appends
`(claimed by …)` to whichever it picks. A round-5 frame-critique read that as a
broader pickup queue and argued A′ therefore puts departed-owner residue at the
top of it — the same inversion that disqualified Option A. The distinction that
defuses it: `IN_PROGRESS` ranks **first** in that order, and nobody would call a
slice someone is actively building "available", so the ordering is
*most-in-flight-first* (what needs attention), not *most-available-first* (what
is free to take). A claim on a `REVIEWED` row is therefore informative — it says
who owns the in-flight work — where a claim on a `READY_FOR_IMPLEMENTATION` row
would be a false occupancy signal on a genuinely free slice. Recorded because a
careful reader independently misread it; if the misreading is common, the fix is
`orient`-side wording, not the state partition. Note also that the reviewer's
supporting claim — that `REVIEWED` is dual-meaning and `REVIEWED →
READY_FOR_IMPLEMENTATION` is a spec-level park point — does not hold: the
lifecycle has no such edge (`docs/workflow.md`), and `REVIEWED` is reachable only
from `IN_PROGRESS`. One caveat on that defence, per the round-7 pass: that is the
*documented* lifecycle, not an enforced invariant — only `DEFERRED` and
`ABANDONED` have restricted outbound edges, so any state can in fact be
transitioned straight to `REVIEWED` and take a stamp. The residue argument rests
on convention, which is worth knowing if the convention slips.

**`DRAFT` authoring presence is knowingly given up.** Context names `DRAFT`
(authoring ACs, SPIDR-splitting) among the unmarked states that constitute the
bug, and A′ leaves it unmarked. This is a **tradeoff, not an impossibility** —
an earlier draft of this ADR claimed `DRAFT` was "structurally unmarkable", which
was wrong and the round-5 frame-critique caught it: entry to `DRAFT` fires like
any other entry (`DEFERRED → DRAFT`, `ABANDONED → DRAFT`, any back-edge), so
moving `"DRAFT"` between the two tuples *would* mark those sessions. The real
tradeoff is the one A′ resolves against marking: `DRAFT` is a pickup-queue state,
so a claim there produces false occupancy on the board for every parked draft —
and jig carries long-lived ones (spec 034's slices have sat at `DRAFT` for
months). Two genuinely structural gaps remain either way: a *newly created* slice
gets `status: DRAFT` written straight into frontmatter with no transition at all,
and within-state authoring after entry is invisible to an entry-triggered stamp.
So do not read the fix as guarding `DRAFT` collisions — but do read the exclusion
as revisable if the board cost ever looks smaller than the collision cost.

Two narrowings of the reservation path ride along, both discovered in review:
`_reserve_claim_on_main` publishes trunk `status:` only for an `IN_PROGRESS`
target (that write exists solely to feed `_refuse_start_collision`; publishing
any other state would regress the trunk's lifecycle view, which the landing flow
owns), and it warns before replacing a foreign trunk claim. Symmetrically,
`_refuse_start_collision` now *warns* on a foreign trunk claim at a non-
`IN_PROGRESS` working state — without that read, `--push` would publish a trunk
field nothing consults.

`claimed_by:` is redefined as *"the session that last moved this slice into a
working state"* — stamped on entry to a working state, cleared at a release
point (or by `--release`). That wording is deliberate and
narrower than "who is here now": the stamp is an entry event, so it is a strong
presence *hint*, not a live lock (see Assumptions). It is what jig can honestly
observe, given it cannot see plain `Edit`-tool writes at all.

The **hard block stays exactly where it was**: a transition is refused only
when a foreign claim holds a slice that is already `IN_PROGRESS`. Two sessions
*building* the same slice remains an outright refusal (spec 049 AC3, spec
051-04). Two sessions *editing* one spec is Option A's real cost, and turning
that into a refusal would manufacture a new class of false blocks — for
instance a reviewer worktree unable to record a verdict on a slice the
implementer still holds. Instead, a foreign claim in any other active state
produces a **loud, non-blocking warning** naming the holder, the state, and the
`--release` escape. That warning is the signal that previously did not exist at
all; the block is not what was missing — though see Consequences for how
rarely it can fire before claims are pushed by default.

Options B and D are not rejected on merit, only on sequencing: both are
additive on top of this decision, and neither is needed to make the current
reader surfaces honest.

## Consequences

**Becomes easier:**
- Every existing pickup surface (`orient` focus line, status board,
  `session-plan`, `compass` / `jig:orient`) *can* report spec-level presence,
  because the underlying field can now carry it — where before it was
  structurally unable to.
- **Not claimed: that this retires the need for a caveat.** It does not; it
  changes the caveat's shape, from "ownership data covers `IN_PROGRESS` only" to
  "a claim may exist on a branch you cannot see". So the honest-prose work
  Option C would have done is still required and ships alongside this decision
  (`docs/workflow.md`, `spec-workflow/SKILL.md`, and the `collect_slices`
  docstring all now state that blank means *no claim recorded*, never *free*).
  Option C was rejected as **insufficient**, not as unnecessary.
- Reconciliation and spec-review phases — previously the least protected — are
  marked by the same rule as implementation.
- `--push` / `--pr` now works at any working state, so a session can make its
  claim visible to parallel worktrees before it starts building — and, because
  `_refuse_start_collision` now reads a trunk claim at any working state, that
  published claim is actually *consumed* (as a warning) rather than written and
  ignored. Without that read the "so other worktrees see it" promise would have
  been true only after a merge.

**Becomes harder:**
- Concurrent, legitimate spec-level work by two sessions now surfaces a warning
  that is sometimes noise. Accepted: a warning that occasionally fires on
  healthy work is a better failure mode than silence on colliding work. Note the
  *routine* paths are deliberately silent — restricting the stamp to working
  states is what keeps the author→implementer handoff quiet, and a test pins
  that (`test_author_to_implementer_handoff_is_silent`).
- **The new warning has few opportunities to fire until push-by-default lands
  (OQ6), so do not count it as delivered value.** Claim identity is the branch
  name: two sessions on the *same* branch stamp and read an identical identifier,
  so no claim ever looks foreign; two sessions on *different* branches cannot
  read the field at all without `--push`, which is not the default. Day one, this
  decision's practical output is closer to Option C's — honest prose plus a board
  suffix on the claiming branch's own tree — while its costs are paid now. It is
  still the necessary first half (push-by-default cannot surface a
  `READY_FOR_REVIEW` slice that carries no claim to begin with), but the
  Recommended Decision's "that warning is the signal that previously did not
  exist at all" describes a *capability*, not yet a frequently-exercised path.
- **A non-`IN_PROGRESS` transition TRANSFERS a foreign claim to the
  transitioning session** — the stamp is unconditional once the warning is
  emitted. A reviewer worktree recording `REVIEWED` therefore reassigns the
  implementer's claim to itself. This is the direct consequence of holding the
  block narrow (a refusal would be the alternative), and it means the field
  answers "who last moved this slice", which is a presence *hint*, not a lock.
  The warning is the only notice the previous holder's identifier is being
  overwritten, and the previous holder does not learn of it at all.
- Stale claims are somewhat more likely, since a claim now persists through
  `READY_FOR_REVIEW` and `REVIEWED`, which can sit for a while. Bounded by the
  queue-state exclusion: the two states a slice actually *parks* in for long
  stretches (`DRAFT`, `READY_FOR_IMPLEMENTATION`) release the claim, so the
  long-lived-residue case that plain Option A would have created does not arise.
  `--release --reason` (already shipped, already logged to `## Release log`)
  remains the escape.
- **One residue channel the parking argument does not cover:** a branch merged
  while its slice sits at `READY_FOR_REVIEW` or `REVIEWED` lands a `claimed_by:`
  naming a now-deleted branch onto trunk, where the board renders it and every
  later transition on that slice reads it as foreign. This is "residue reads as
  occupied" arriving by *merge* rather than by transition — the disqualifier
  applied to Option A, through a channel the working/queue split does not gate.
  Rare in jig's land flow (implementation slices reach `DONE` before merge and
  spec PRs merge at `READY_FOR_IMPLEMENTATION`, both of which release), so it is
  a noise cost with `--release` as the escape rather than a design fault — but it
  is not bounded by the parking argument above. Raised by the round-6
  frame-critique pass.
- The stamp/clear split is now a **semantic** classification, not a syntactic
  one. A future tenth lifecycle status must be deliberately sorted into working
  vs release; `test_claim_states_partition_the_lifecycle` fails if one is added
  to neither set, so the classification cannot be skipped silently.
- Reserve-on-main gained **three** invariants where it had none: the payload
  rule (`status:` published only for an `IN_PROGRESS` target), warn-before-
  replace, and decline-to-write when the target is *not* `IN_PROGRESS` and the
  trunk copy is at `status: IN_PROGRESS` under a different identifier or none
  (OQ4 — our own trunk claim is a silent no-op). The third makes `--push` at a
  working state other than `IN_PROGRESS` **best-effort** — it can warn, push
  nothing, and exit 0 — a weaker contract than the flag had before this decision,
  which the CLI cannot signal through the exit code.
- Separately, and NOT part of those three: the reservation's pre-existing hard
  failures (trunk copy already `DONE`, origin unreachable, slice absent from
  trunk) are now reachable from three more states, where they abort the whole
  local transition rather than only the push. Low impact — opt-in flag, clear
  message, local file untouched, drop `--push` to recover — but it is the same
  "condition correct only in its old, narrower context" class this change hit
  repeatedly. Raised by the round-8 bug-review pass.

## Assumptions

- **Verified by probe (2026-07-24):** the `IN_PROGRESS`-only stamp, the
  three-state clear list, and the both-ends-`IN_PROGRESS` refusal are as
  described — read directly at `skills/spec-workflow/workflow.py:1267`,
  `:3725`, `:1271`, and reproduced end-to-end against a detached worktree at
  `origin/main@fd7115a` (bug 013 `## Repro`).
- **Verified by probe:** spec 049's Non-goals do state the `IN_PROGRESS`-only
  scoping as intent, so this ADR reverses a decision rather than fixing a slip.
- **Assumed, not verified:** that warning-not-blocking is the right default
  for a foreign claim outside `IN_PROGRESS`. jig has no telemetry here. Note the
  frame-critique pass correctly caught an apparent contradiction in an earlier
  draft, which claimed both that review/reconciliation is "ordinarily performed
  by the session that holds the slice" *and* that a separate reviewer worktree
  on the implementer's slice is "the everyday case". Resolved: **both shapes
  occur**, and the design is deliberately chosen to be tolerable under either —
  same-session continuation (common) makes the claim accurate and the warning
  silent, while cross-session handoff (also common, e.g. a dedicated review
  worktree) is exactly why a refusal would be wrong. The design does not depend
  on which is more frequent; only the *usefulness* of the resulting claim value
  does, and that is Kill criterion 1.
- **Assumed, not verified — and the sharper of the two:** that a
  transition-triggered stamp is a good enough proxy for presence. Presence is a
  property *within* a state; the stamp is an *entry* event. A session that
  frame-critiques a `READY_FOR_REVIEW` slice, or reconciles a `REVIEWED` one,
  often did not perform the transition that put it there — so the claim can name
  the session that **left**. jig has no better hook: it cannot observe plain
  `Edit`-tool writes at all (spec 049's standing non-goal), so entry events are
  the only signal available. Accepted with the semantics stated honestly as
  "who last moved this slice" rather than "who is here now"; the mitigation is
  that the arriving session takes the claim over at its next transition, and the
  highest-damage case (`REVIEWED → RECONCILED`) is ordinarily the same session
  that recorded the verdicts. Option B's expiring lease is the real answer if
  this proves insufficient.

- **Assumed, not argued: that Options B and D are additive on top of this
  decision rather than replacements for it.** Everything above prices A′ as the
  necessary first half of a two-part fix whose second half (push-by-default, OQ1)
  is parked and undated. That holds for OQ1 itself — a pushed claim cannot surface
  a slice that carries no claim, which I take as settled. It does **not** clearly
  hold for the other two: Option B's `active_session:` lease would *replace*
  presence-signalling rather than layer on it (this ADR's own Con on B is that two
  overlapping signals reintroduce the misgeneralisation risk — which a widened
  `claimed_by` plus a lease would be), and Option D reads git history and needs no
  claim field at all. So if the visibility gap is eventually closed by B or D
  instead of by push-by-default, A′'s partition and its three reservation
  invariants are stranded cost, not paid-forward groundwork. This tension is
  visible in the document: "B and D are additive" (Recommended Decision) versus
  "Option B's expiring lease is the real answer if this proves insufficient"
  (Assumptions) cannot both be fully true. Cheap to discover late — the field and
  the partition test survive either way — which is why it is recorded as an
  assumption rather than treated as disqualifying. Raised by the round-6
  frame-critique pass.

## Kill criteria

- **Retired by the narrowing:** the earlier draft's kill criterion "the warning
  fires routinely on healthy sequential work" was satisfiable by inspection —
  the author→implementer handoff tripped it on every new slice. That is now a
  pinned-silent path, not a monitoring commitment. Its replacement: the warning
  fires routinely on the `READY_FOR_REVIEW` → external-reviewer handoff, which
  would mean `READY_FOR_REVIEW` is a queue state too and belongs on the release
  side.
- **Most likely to fire:** a parallel-session collision recurs of the reported
  shape (two worktrees, separate branches) — which this decision does not
  prevent, as stated in Context. That does not falsify the coverage fix, but it
  does mean *visibility* was the binding constraint, and push-by-default should
  then be treated as triggered rather than merely parked. Do not read a
  recurrence as evidence this decision was wrong; read it as the second half of
  the work coming due.
- A claim is repeatedly found naming a session that has already finished (the
  transition-event-vs-presence gap above) badly enough to mislead a reader — at
  which point the stamp trigger, not its coverage, is the thing to change, and
  Option B's expiring lease becomes the right shape.
- **The A′-over-A″ premium never pays off.** Trigger: the next change to this
  claim machinery finds OQ1 (push-by-default) still unbuilt and undated. At that
  point the working/queue partition and the three reservation invariants have been
  carried for a warning that still cannot fire, and A″ — `IN_PROGRESS`-only stamp
  plus terminal clearing — should be reconsidered as the resting state. Recorded
  because the round-7 frame-critique correctly observed that Kill criterion 2
  otherwise insulates this choice from the only evidence that would test it: it
  tells the reader to treat a recurrence as "the second half coming due", which
  can absorb any amount of delay. This criterion is the counterweight. Two limits
  on it, stated so it is not over-trusted: the trigger is event-conditioned, so if
  nobody touches this machinery it never evaluates; and "OQ1 built" is the wrong
  test — see OQ1 on why publication alone leaves the incident class open. Evaluate
  it against the class being closed.
- Stale claims on long-lived `READY_FOR_REVIEW` / `REVIEWED` slices become the
  dominant cause of `--release` calls, indicating that presence genuinely needs
  Option B's expiring lease rather than a persistent claim.

## Open questions

1. **Publication is not the whole of the visibility half.** Should `--push`
   become the default for claims now that they span every working state? Deliberately left open — it is the existing parked
   [refinement-todo](../refinement-todo.md) item from issue 81, and widening
   coverage does not settle it. Widening does raise its value, since a
   local-only claim is now unread for longer, and the trunk read path added here
   means a pushed claim finally has a consumer.

   **But push-by-default alone would not close the reported incident**, and this
   ADR should not be read as promising it does. That incident's mechanism was a
   *survey-and-recommend*, and the surfaces that produced the bad recommendation
   (`orient`'s focus line, the status board) read the **local** copy. The only
   consumers of a *trunk* claim are `_refuse_start_collision` (reached only for an
   `IN_PROGRESS` target) and `_reserve_claim_on_main` (only under `--push`) — both
   at transition time, i.e. *after* the recommendation is made. A third piece is
   therefore needed: a reader-side trunk consult on the pickup path. The parked
   [refinement-todo](../refinement-todo.md) item does include a `session-plan`
   claim-check that supplies part of it; earlier drafts of this ADR reduced that
   item to "should `--push` be the default", which undersold it. Raised by the
   round-8 frame-critique pass.
2. Should a claim carry the state it was taken in, so a reader can distinguish
   "claimed while reviewing" from "claimed while building"? Not built: the
   slice's own `status:` already sits beside the claim, so the pair is
   readable without a second field.
3. **Is `READY_FOR_REVIEW` genuinely a working state?** It is treated as one
   here, because it is the reported incident's state and because in jig practice
   the author transitions into it and then runs the spec review in the same
   session. But its *name* is queue-shaped, and if review is routinely performed
   by a different worktree than the one that requested it, the same residue
   argument that excluded `READY_FOR_IMPLEMENTATION` would apply. Kill criterion
   1 watches exactly this.
4. **Both origin/main claim reads are warnings, never blocks, outside
   `IN_PROGRESS`.** The `--push` reservation warns before replacing a foreign
   trunk claim, and the hard refusal there is both-ends-`IN_PROGRESS`, matching
   the local path. **One exception, resolved rather than left open:** a trunk copy
   at `status: IN_PROGRESS` is off-limits to a claim-only reservation, whether or
   not it carries a claim. `_refuse_start_collision` hard-blocks on `IN_PROGRESS`
   **plus a foreign claim**, so a *claimed* trunk copy is already enforced and
   must not have its holder swapped; an *unclaimed* one is not blocked yet, and
   stamping a claim onto it is exactly what would create the enforced pair. Either
   way a claim-only reservation warns and **skips** the trunk write: replacing a
   holder would transfer a live lock and get the original builder refused naming
   the reviewer, and stamping an unclaimed copy would refuse everyone. Our own
   claim is excluded — that is a silent no-op, not a decline. What remains genuinely open is that a
   *non-enforced* trunk claim can be overwritten repeatedly, with nothing
   arbitrating. So a trunk claim at `REVIEWED` is noticed but never enforced,
   and the `--push` reservation replaces a foreign trunk claim after warning
   rather than refusing. Deliberate — a refusal there is the false-block class
   this decision avoids — but it means the trunk claim is advisory data, and
   nothing prevents two sessions from taking turns overwriting it.
5. Option D (the touched-on-another-branch advisory) remains unaddressed and
   catches a case no claim field can — plain `Edit`-tool writes that never go
   through `transition`. Left for its own decision.
6. **How often can the new warning actually fire before push-by-default lands?**
   Rarely — and that should not be over-counted as shipped value. Claim identity
   is the branch name, so two sessions on the *same* branch stamp and read an
   identical identifier and no claim ever looks foreign; two sessions on
   *different* branches cannot read each other's field at all without `--push`,
   which is not the default (OQ1). The set of readers who can both see the
   widened claim and recognise it as someone else's is therefore
   post-merge-or-opt-in only. Coverage remains a strict prerequisite for the
   visibility half — push-by-default cannot surface a `READY_FOR_REVIEW` slice
   that carries no claim to begin with — but until it lands, this decision's
   day-to-day output is closer to Option C's (honest prose plus a board suffix on
   the claiming branch's own tree) while its costs are paid now. Raised by the
   round-3 frame-critique pass.
