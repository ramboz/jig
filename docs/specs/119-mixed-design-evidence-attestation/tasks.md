# Tasks: mixed design-evidence attestation

This is a work plan, not an implementation completion checklist.
Authoring review evidence is in the ADR and slice `reviews/` directories.
The 2026-10-15 implementation checkpoints in `plan.md` supersede proposal-era
pending claims below. This worktree implements only 119-02, stacked on the
completed 119-01 parent. 119-03 remains DRAFT and outside this implementation.

## Before readiness

- [x] Parent aligns durable Vellum/Servo proposal links, installed overall verdict
  authority, separate version namespaces and subordinate run/digest references.
- [x] Approve source/target approval and policy/config binding semantics.
- [x] Define app input closure, dirty-input digest and independently observed
  delivered-build identity with exact C0 serialization/digest domains/test
  vectors and explicit required matrix; approve concrete tolerance/transport.
- [x] Select existing-artifact identity encoding (named body references and
  comparisons); persisted reuse checks remain 119-02.
- [x] Define producer capture/renewal protocol and C1 approved-source checkpoint;
  preserve genuine captures and prove runtime binding during implementation.
- [x] Owner accepts the intentional new-legacy-attestation provenance cost,
  with historical/unflagged/default behavior unchanged.
- [x] Obtain later-phase ADR acceptance and readiness review authority.
- [x] Obtain independent spec-readiness verdict (not the framing verdict).

## 119-01 — rich verdict through completion

- [x] Write failing overall-authority/required-failure/incomplete-evidence and
  deterministic-component-pass/overall-quality-fail tests.
- [x] Consume authoritative installed overall-gate policy/outcomes and subordinate
  run/digest-bound design evidence in the existing prompt/attestation path.
- [x] Produce genuine passing, required-failure and component-pass/quality-fail
  overall/component captures; prove served-build binding, then exercise
  independent review, recording, existing review checks and completion.
- [x] Document, validate, review, reconcile and close the vertical slice.

Historical492checkpoint: source/guidance/tests/host packages are implemented, but genuine
current completion proof remains open. Actual positive attester needs-changes
and quality-fail attester fail are preserved under `verification/`; existing
record/check/REVIEWED/DONE refusal was exercised. Compliance needs-changes,
craft/arch supporting code-cut pass; lifecycle stays IN_PROGRESS.

Later sealed6cc759e evidence now supplies all actual producer-backed
scenarios, independent full closure and124CLI observations; see
`verification/sealed-proof.md`. Final passing implementation reviews are
recorded in `reviews/`; reconciliation and gated closure follow the live
slice record. Old nonpassing records are preserved; no119-02/03
implementation is claimed.

119-01 closed through normal REVIEWED, RECONCILED and DONE evidence/dependency
gates. At that checkpoint119-02/03 were DRAFT. Current119-02 state is in its
own record;119-03 remains DRAFT, so no compress-on-spec-close primer change
applies.

## 119-02 — freshness through final delivery

- [x] Verify exact selected parent locally/remotely and all three source pins.
- [x] Pass independent framing/spec-readiness and claim through normal helpers.
- [x] Write failing tests for changed app with unchanged eval definition and
  reuse of a previously passing review at DONE without a back-edge.
- [x] Narrowly add source/target, effective policy/config and app/delivery
  reference/digest checks to existing design-review evidence validation.
- [x] Exercise genuine A/B/renewed runs and dirty/config/approval changes;
  preserve documentation-only application identity.
- [ ] Record trust limits, validate, review, reconcile and close the slice.

Current checkpoint: 25new/173affectedtests and normal selected-old-PASS
read/hash reuse proof pass. Twelvecopied changes yield36specific refusals in
72actualCLIobservations with unchanged pass/GitHEAD/size/mtime; restoration and
outside-closure documentation change clear. All3887currentexternalruntime
files and39copiedoutputfiles rehashed. Genuine changed-build renewal, not
restoration, is now separately proved by the actual44a A/B sequence in
`verification/slice-02-actual-renewal.md`; the old checkpoint gap is preserved
as history, not waived.
The compliance-discovered root-NUL diagnostic bug is fixed with witnessed
red/green recording/reuse regressions; final genuine mutation proof was
repeated on that exact guard source. Fresh full ordered reviews now judge all
completed acceptance evidence before actual11902 closure.

## 119-03 — bounded legacy and opt-in preservation

- [ ] Write failing downgrade, missing-provenance and preservation tests.
- [ ] Exercise genuine bound legacy threshold-only completion and renewed
  evidence refusal; no guessed schema or provenance.
- [ ] Verify unflagged workflow and independent compliance remain unchanged.
- [ ] Update existing guidance; regenerate/validate all host packages.
- [ ] Review, reconcile and close; regenerate/audit board and compress primers.
