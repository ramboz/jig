---
status: RECONCILED
dependencies: [adr-0069]
last_verified: 2026-11-20
kind: feature
arch_review: true
claimed_by: claude/elegant-chaplygin-fa1375
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 124-01 — owner-review pass

**Goal:** A slice that sets `owner_review: true` cannot reach `REVIEWED`
until the owner's own verdict is recorded, the owner is asked while the
automated reviews run, and a rejection keeps the slice `IN_PROGRESS` before
any reconciliation document is written.

**DoR:**
- ✅ [ADR-0069](../../decisions/adr-0069-owner-review-human-attested-evidence.md)
  drafted (accepted before this slice reaches `DONE`).
- ✅ The existing flag-gated passes were read: `required_passes` /
  `validate_evidence` in `skills/_common/review_evidence.py`,
  `_gate_evidence` / `session_plan` / `slice_needs_*` in
  `skills/spec-workflow/workflow.py`, `record_review` in
  `skills/independent-review/review.py`.

**Acceptance Criteria:**

1. **The flag adds the pass to the `REVIEWED` set.** With
   `owner_review: true` in a slice's frontmatter, `workflow.py transition
   <spec> <slice> REVIEWED` exits non-zero until
   `reviews/slice-NN-owner-review.md` exists with `verdict: pass`; the
   refusal names the `owner-review` pass. `review.py check-reviews --stage
   REVIEWED` reports the same. `transition … DONE` re-checks it. A slice
   without the flag (absent or `false`) transitions exactly as before.
2. **`workflow.py owner-review-needed <spec> <slice>`** prints `true` iff the
   flag is truthy, else `false` (same contract as `design-review-needed`).
3. **`review.py owner-review <spec> <slice>` prints the ask.** The output
   contains the slice's text (so the acceptance criteria to try are in front
   of the agent), the question to put to the owner, the `record-review`
   command, and the rules: ask and wait; record only the owner's reply to
   this question, quoted; never infer a verdict from silence, an earlier
   approval or the agent's own run; with no person to ask, record nothing.
4. **`record-review --pass owner-review` takes the owner's answer.** It
   requires non-blank `--tried`, `--surface` and `--owner-quote`, and writes
   a body with `TRIED:`, `SURFACE:` and `OWNER SAID:` parts (the quote as a
   blockquote). `--summary-file` is optional for this pass and is appended
   as notes. A missing or blank argument exits 2 and writes no file.
   `--non-interactive` with this pass exits 2. The three arguments given
   with any other pass exit 2.
5. **The gate re-checks the body.** An `owner-review` file with
   `verdict: pass` but without a non-empty `TRIED:`, `SURFACE:` or
   `OWNER SAID:` part does not clear `REVIEWED`; the diagnostic names the
   missing part.
6. **A rejection says what to do.** With a recorded `needs-changes` or
   `fail` owner verdict, the `REVIEWED` refusal says the owner asked for
   changes, the slice stays `IN_PROGRESS`, reconciliation must not start,
   and after the fix the owner is asked again and the automated passes are
   re-run. `record-review` prints the same notice when it records a
   non-`pass` owner verdict.
7. **Any rejection reopens the batch on a flagged slice.** On an
   `owner_review: true` slice, `record-review` with a non-`pass` verdict
   for any `REVIEWED`-stage pass (`compliance`, `craft`, `arch`,
   `code-health`, `design-review`, `owner-review`) stamps
   `review_reopened_at` in the slice frontmatter and says so, naming the
   passes to re-run and that the owner must be asked again. An owner
   `pass` recorded before that stamp no longer clears `REVIEWED`. A `pass`
   verdict, a `reconciliation` verdict, and any verdict on an unflagged
   slice stamp nothing. `review.py owner-review` on a flagged slice stamps
   `owner_review_asked_at`; once a reopen stamp exists, an owner `pass`
   clears only if the owner was asked again after it, so a late reply to
   the earlier ask does not clear. Whenever an ask stamp exists, an owner
   verdict recorded before it does not clear (re-running the ask means a
   new answer is pending). With no ask stamp there is no ask-time
   requirement.
8. **`workflow.py session-plan` shows the pass as waiting on the owner.**
   For a flagged slice the plan lists `owner-review` directly after
   `implement` and before `compliance`, marked as a question for the owner
   that runs in parallel with the automated passes. An unflagged slice's
   plan is unchanged.
9. **The docs put the owner's check in the review batch.**
   `docs/workflow.md` (post-implementation review, recording, recovering)
   and `skills/spec-workflow/SKILL.md` and
   `skills/independent-review/SKILL.md` describe the pass, state that an
   owner check belongs with the review batch before reconciliation and not
   in the DoD after `RECONCILED`, state that the record is a
   deliberateness signal, not proof, and state the re-ask rule: if what the
   owner tried changes after their answer, ask again.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`) and
      `--check` clean.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01 rule (this slice does not close the
      spec).

**Anti-horizontal-phasing check:** after this slice an owner who sets
`owner_review: true` gets asked during review and can stop the slice before
reconciliation; nothing waits on slice 02.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Ask-time binding added (frame-critique rounds 2–3, AC7 extended).**
   The planned reopen stamp alone let two stale owner answers clear: a late
   reply about the pre-fix build recorded after the reopen, and an old
   reply recorded before the ask was re-run. `review.py owner-review` now
   stamps `owner_review_asked_at`, and the gate requires
   `review_reopened_at` < `owner_review_asked_at` <= `reviewed_at`
   (`owner_ask_stale_problem`, `owner_answer_predates_ask_problem`). AC7
   was extended in the slice text to say so. Consequence: the ask command
   writes the slice file each time it runs (a frontmatter diff per ask);
   its help text says so.
2. **Escalated arch verdicts do not reopen the batch** (craft finding). A
   spec-122 escalation waits on a person's decision, not a fix, so the
   reopen notice would have contradicted the "do not fix" notice.
3. **The reopen notice names the passes** (`reviewed_passes_for`), per AC7.
4. **`REVIEWED_STAGE_PASSES` is derived** from `required_passes` with every
   flag on, so a new REVIEWED pass cannot be missed by the reopen rule.
5. **Public flag reader** `review_evidence.owner_review_required` for
   `review.py`, instead of reaching into the private reader.
6. **Session-plan label.** The owner phase renders "WAITING ON THE OWNER
   (ask now; a person answers)" with no `runs {skill}`, since no skill or
   subagent runs.
7. **Closed-record guard touched.** `test_design_fidelity_authoring_nudge.py`
   pins spec 104-02 AC4 ("no new `slice_needs_*_review` deriver"). The pin
   now admits `slice_needs_owner_review`, which is a human pass and not a
   design-fidelity mechanism; 104-02's record itself is not amended
   (ADR-0010 / spec 102).
8. **Not done, deferred** to `docs/refinement-todo.md` ("bind the owner's
   verdict to a build"): changes with no recorded rejection, an ask run
   before the fix exists, and a parallel automated `pass` returning after
   another pass's rejection. ADR-0069 decision 6 names these limits.
9. **Same-second strictness.** The ask must be strictly later than the
   reopen stamp (one-second resolution), so an ask run in the same second
   as the reopen is refused; this fails closed and the remedy is to ask
   again.
10. **Reviews.** Compliance round 1 `needs-changes` (the re-ask hole, fixed
   above), round 2 `pass`; craft `pass` and arch `pass` with nits, folded in as items 2–6.
   ADR frame-critique ran four rounds; rounds 1–3 drove decision 6.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Front door lists skills, not review passes. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | UC-4 / UC-7 unchanged; the pass serves them. |
| `docs/architecture.md` | `updated` | Owner-review named as the one subagent-less pass; `review.py` frontmatter writes recorded. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | `CLAUDE.md` key-terms index gains the owner-review entry; scaffold template change is slice 02's. |
| `docs/workflow.md` | `updated` | Post-implementation review: owner-review pass, where the owner's check belongs, rejection/re-ask rules. |
| `skills/spec-workflow/SKILL.md`, `skills/independent-review/SKILL.md` | `updated` | Pass, recording, rejection and batch-reopen rules. |
| `docs/inbox.md` | `no-op` | No item resolved by this slice. |
| `docs/refinement-todo.md` | `updated` | Build-binding and bug-lifecycle entries added. |
| `docs/memory/**` | `updated` | Glossary review-evidence entry names owner-review. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0069 indexed as Proposed (`adr.py index`); `adr.py accept` + re-index run when the owner accepts it, before DONE. |
| `docs/decisions/adr-0069-…md` + `docs/decisions/reviews/adr-0069-frame-critique.md` | `updated` | Drafted, Proposed; four frame-critique rounds, the last `pass`. |
| `hosts/` | `updated` | Regenerated; `build_host_packages.py --check` clean. |

