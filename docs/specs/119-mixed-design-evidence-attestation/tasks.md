# Tasks: mixed design-evidence attestation

This is a DRAFT work plan, not an implementation completion checklist.
Authoring review evidence is in the ADR and slice `reviews/` directories.

## Before readiness

- [ ] Parent aligns durable Vellum/Servo proposal links and contract versions.
- [ ] Approve source/target approval and policy/config binding semantics.
- [ ] Define app input closure, dirty-input digest and independently observed
  delivered-build identity.
- [ ] Select existing-artifact identity encoding and read-only reuse checks.
- [ ] Preserve genuine pilot captures and a supported legacy sample.
- [ ] Obtain later-phase ADR acceptance and readiness review authority.

## 119-01 — rich verdict through completion

- [ ] Write failing rich-policy/required-failure/incomplete-evidence tests.
- [ ] Consume producer-owned policy/outcomes and bind evidence in the prompt
  and existing recorded attestation path.
- [ ] Exercise genuine passing and high-composite required-failure runs through
  independent review, recording, existing review checks and completion.
- [ ] Document, validate, review, reconcile and close the vertical slice.

## 119-02 — freshness through final delivery

- [ ] Write failing tests for changed app with unchanged eval definition and
  reuse of a previously passing review at DONE without a back-edge.
- [ ] Narrowly add source/target, effective policy/config and app/delivery
  reference/digest checks to existing design-review evidence validation.
- [ ] Exercise genuine A/B/renewed runs and dirty/config/approval changes;
  preserve documentation-only application identity.
- [ ] Record trust limits, validate, review, reconcile and close the slice.

## 119-03 — bounded legacy and opt-in preservation

- [ ] Write failing downgrade, missing-provenance and preservation tests.
- [ ] Exercise genuine bound legacy threshold-only completion and renewed
  evidence refusal; no guessed schema or provenance.
- [ ] Verify unflagged workflow and independent compliance remain unchanged.
- [ ] Update existing guidance; regenerate/validate all host packages.
- [ ] Review, reconcile and close; regenerate/audit board and compress primers.
