---
status: Proposed
dependencies: []
last_verified:
frame_review: true
---

# ADR-0069: Owner review: a human-attested pass in the REVIEWED evidence set

## Status

Proposed (2026-11-20)

## Context

GitHub issue 254 (`ramboz/jig`) reports a slice that implemented three UX
decisions taken on paper. It passed the compliance, craft and reconciliation
reviews. The owner's first check on a real device then rejected all three.
The slice went `RECONCILED → IN_PROGRESS`, and every review verdict, the
deviation log, the reconciliation sweep and the decision records written
during reconciliation had to be redone.

The lifecycle has no slot for the owner's hands-on check. Projects put it in
the slice's Definition of Done (DoD), which `transition` enforces only at
`DONE`, after `RECONCILED`. That order is fine when the check confirms what
review already approved. It is wrong when the check is the first real test of
a decision, because reconciliation then records behaviour nobody has tried.

Three things already in the code shape the answer (read on 2026-11-20):

- The `REVIEWED` evidence set is built from frontmatter flags.
  `required_passes` in `skills/_common/review_evidence.py` adds `arch`,
  `code-health` and `design-review` when the slice sets `arch_review`,
  `code_health_review` or `design_review`. `workflow.py transition` refuses
  `REVIEWED` until every required pass has a recorded `verdict: pass`, and
  re-checks the same set at `DONE`.
- The `design-review` pass (spec 071) has this structural shape, but a
  read-only reviewer subagent attests a frozen score from an external design
  eval. It checks fidelity to a design. It does not ask whether the owner
  tried the feature, so it would not have caught the reported case.
- [ADR-0023](adr-0023-lifecycle-family-spine.md) keeps spec-workflow, bug-fix
  and refactor on one gated-evidence spine with a shared set of states.

Every existing pass is written by a reviewer subagent. The owner's check is
the first pass whose author is a person.

## Decision Options Considered

### Option A: a new `ACCEPTED` state between `REVIEWED` and `RECONCILED`
- **Pros:** the step is visible on the status board; matches the issue's
  first suggestion.
- **Cons:** it puts the owner after the automated reviews, in series, so
  the owner's rejection always arrives after a full review round has been
  paid for. A new state also touches every
  consumer of the state list (claims, cross-ref checks, the status board,
  `slice-land`, the bug-fix and refactor lifecycles that share the spine),
  for a step most slices do not need.

### Option B: an evidence gate whose flag is derived
The issue's second suggestion: derive the flag the way `frame_review` is
derived, true when the slice implements decisions not yet tried.
- **Pros:** the owner does not have to remember to set it.
- **Cons:** "a decision nobody has tried yet" is not readable from the
  files. `frame_review` derives from a section the author writes
  (`## Assumptions`); there is no equivalent record of what the owner has
  tried. A wrong `true` is expensive here in a way it is not for
  `frame_review`: it creates a gate only a person can clear, so a false
  positive stalls the slice on someone's time.

### Option C: stretch `design-review` to cover the owner's check
- **Pros:** no new pass.
- **Cons:** it merges two different claims, "the build matches the design"
  (a frozen external score, attested) and "the owner tried it and accepts
  it". A slice can need either without the other, and the design-review
  record's freshness rules would not fit a person's answer.

### Option D: an optional human pass in the `REVIEWED` batch, set by an explicit flag (chosen)
- **Pros:** reuses the flag, gate, verdict file and `session-plan`
  machinery; the owner checks while the automated reviews run; a rejection
  lands before any reconciliation document exists; slices without the flag
  are unaffected.
- **Cons:** the owner must opt in per slice, so a slice that needed the
  check can still miss it (mitigated by asking at authoring time, decision 7);
  the evidence is a file an agent can write (decision 3).

### Option E: documentation only
Tell projects to do the owner's check before reconciling, with no gate.
- **Pros:** no code.
- **Cons:** the convention that failed was also documentation. Nothing
  would stop `REVIEWED` when the check was skipped.

## Recommended Decision

Option D. The owner chose this shape when triaging issue 254; this ADR
records it and settles the details.

1. **A new pass, `owner-review`, in the `REVIEWED` evidence set.** It is
   required iff the slice's frontmatter sets `owner_review: true`. It uses
   the existing verdict file (`reviews/slice-NN-owner-review.md`), the
   existing gate rule (only `verdict: pass` clears, ADR-0014 §3), the
   existing re-check at `DONE`, and the existing rule that a verdict not
   newer than the slice's `review_reopened_at` stamp no longer clears
   (bug 039). There is no new lifecycle state and no separate gate.

2. **The verdict is the owner's, in the owner's words.** The record keeps
   the six frontmatter fields of ADR-0014 §2; `reviewer:` names the person.
   The body must carry three labelled parts: `TRIED:` (what the owner did),
   `SURFACE:` (the device, browser, build or other surface they used) and
   `OWNER SAID:` (their answer, quoted). `record-review` builds the body
   from three required arguments and refuses the record when one is empty.
   The gate re-checks that the three parts are present, so a hand-written
   file without them does not clear.

3. **This is a deliberateness gate, not proof.** Per
   [ADR-0011](adr-0011-spec-gate-model.md), the gate sits inside the
   agent's trust boundary. An agent can write the verdict file, and jig
   cannot verify that a person tried anything. What the gate does is make
   skipping the check a deliberate act that leaves a record: a quoted
   answer that the owner can read in the diff and contradict. Real
   enforcement, where a project needs it, is out of band (review of the
   pull request by the owner).

4. **The agent asks and quotes; it never infers.** `review.py owner-review`
   prints what to ask: what to try (from the slice's acceptance criteria)
   and the question to put to the owner. The agent records a verdict only
   from the owner's reply to that question in the current conversation.
   Silence, an earlier general approval, a reply about something else, and
   the agent's own run of the feature are not answers. A device check can
   outlast the session that asked: a later session may record the owner's
   reply to the standing question, but only from the owner's own message
   in that session, never from an agent's notes about what the owner said.
   With no person to ask (an unattended run), nothing is recorded and the
   slice waits; `record-review` refuses `--non-interactive` for this pass.
   After recording, the agent shows the owner the recorded file, and the
   record is part of the diff the owner reviews before the slice lands;
   those are the two moments a wrong quote can be caught.

5. **The pass runs in parallel with the automated reviews, and a rejection
   goes back to `IN_PROGRESS` before reconciliation.** `workflow.py
   session-plan` lists `owner-review` straight after `implement`, marked as
   waiting on the owner, so the question goes out once the build is
   finished (not mid-build) and while the reviewer subagents run. A
   `needs-changes` (or `fail`) verdict blocks `REVIEWED`, so the slice is
   still `IN_PROGRESS` and no deviation log, sweep or decision record has
   been written.

6. **Any rejection in the batch reopens the whole batch.** The passes are
   not independent: a fix made for one of them changes the build the others
   judged. In particular, an owner `pass` given before an automated
   reviewer asked for changes describes a build that no longer exists, and
   re-asking costs the owner's time, so an agent would be tempted to keep
   it. On an `owner_review: true` slice, `record-review` therefore stamps
   the slice's `review_reopened_at` whenever it records a non-`pass`
   verdict for a `REVIEWED`-stage pass, whoever the reviewer is. Every
   verdict recorded up to that moment stops clearing: the automated passes
   are re-run and the owner is asked again, with a summary of what changed.
   The owner may answer that they do not need to try it again; that is
   their call and is recorded in their words. This rule is limited to
   flagged slices; other slices keep today's behaviour (re-run only the
   pass that failed). It does not catch a change made without any
   non-`pass` verdict (general code-staleness stays deferred, ADR-0014
   Scope); the ask and the docs state the rule for that case: if what the
   owner tried changes after their answer, ask again.

7. **The flag is explicit, and jig asks for it.** `owner_review` has three
   readings: `true` (required), `false` (the owner said no) and absent (not
   yet asked). When a slice looks UI-related and the flag is absent, jig
   asks the owner whether they want to try the slice themselves before it
   is reconciled, and writes `true` or `false` from the answer. The trigger
   is the absent flag on a UI-related slice, which is the state a careless
   author leaves behind; it does not depend on the author volunteering
   anything. "UI-related" is a stated word list matched against the slice
   text, or `design_review: true`. The prompt is given at authoring time
   and repeated as a non-blocking note on the slice's forward transitions
   and in `session-plan` until the flag has a value.

8. **`design_review: true` recommends yes; it does not set the flag.** A
   slice with a design-fidelity gate ships a screen, so the question
   suggests yes. The owner still answers, because the flag creates a gate
   that only they can clear.

## Consequences

**Becomes easier:**
- Getting the owner's first real test before reconciliation, at the cost of
  one question when the slice is written. The re-loop is shortened, not
  removed: implementation and a review round are still spent before the
  first real test of a paper decision.
- Seeing that a slice is waiting on a person: `session-plan` says so.
- Auditing: the owner's quoted answer sits beside the other verdicts.

**Becomes harder:**
- An `owner_review: true` slice cannot reach `REVIEWED` in an unattended
  run. That is intended, and the autonomy layer has to treat it as a wait
  on a person, not as a failure to retry.
- One more pass name for every consumer of `PASSES`.
- On a flagged slice, one failing pass means re-running the whole review
  batch and asking the owner again (decision 6).
- The word list gives false positives (one question, answered once with
  `owner_review: false`) and false negatives (the owner can still set the
  flag by hand).

## Assumptions

- **A1 (unverified).** A quoted answer in a file the owner reviews is
  enough of a deterrent to an agent inventing the check. Nothing measures
  this yet; kill criterion 1 watches for it.
- **A2 (unverified).** A word list catches most UI slices in real
  projects. It was chosen for being cheap and readable, not measured.

Probed facts (2026-11-20): `required_passes`, `validate_evidence` and the
`DONE` re-check behave as described in Context (read in
`skills/_common/review_evidence.py` and `_gate_evidence` in
`skills/spec-workflow/workflow.py`); `session_plan` emits the conditional
review phases after `craft` (read in `workflow.py`); `review_reopened_at`
is stamped today only on a transition out of `REVIEWED` / `RECONCILED` /
`DONE` (read in `workflow.py transition`), so without decision 6 a slice
that never left `IN_PROGRESS` would carry no stamp.

## Kill criteria

1. An `owner-review` record turns up whose quote the owner did not say.
   The agent-writable record is then not a usable deliberateness signal,
   and the pass needs an out-of-band channel or should be withdrawn.
2. Owners routinely answer the authoring question with yes and then wave
   the check through without trying anything. The pass is then ceremony
   and should become documentation only.
3. A third lifecycle (bug-fix or refactor) needs the same human pass. That
   is the ADR-0023 trigger to move it into the shared spine instead of
   copying it.

## Open questions

- **A change with no failing verdict.** Decision 6 keys on a recorded
  non-`pass` verdict. A change made after the owner's answer without one
  (a nit fixed after a `pass`, say) is covered only by the stated rule.
  Binding the owner's verdict to a commit and comparing at the gate would
  close it, at the cost of defining "the deliverable" for every project;
  deferred until a real miss.
- **The bug lifecycle.** `bug.py` has its own `REVIEWED` gate and no owner
  pass. Not needed for issue 254; see kill criterion 3.
