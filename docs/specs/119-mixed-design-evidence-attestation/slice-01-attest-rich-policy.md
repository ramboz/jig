---
status: DRAFT
dependencies: [071-01, 104-02, adr-0065]
last_verified:
arch_review: true
frame_review: true
---

## Slice 119-01 — attest-rich-policy

**Goal:** A developer can use genuine frozen mixed-policy evidence to clear
the existing design-review rail, while a high average with a required failure
or incomplete evidence cannot earn completion.

**DoR:**
- [ ] ADR-0065 accepted in a later authorized phase; independent framing and
  spec-readiness reviews pass.
- [ ] Parent aligns the Vellum approval reference and Servo producer
  contract/version, complete required inventory and outcome vocabulary.
- [ ] Genuine frozen evaluator baseline and planted required-failure captures
  exist for the card app, with producer command/version, run IDs and
  source/config/evaluated-build/delivery binding; no forged passing ledger.
- [ ] Existing source surfaces read at the spec's pinned main anchor:
  `build_design_review_prompt`, `record-review`, `validate_evidence` and the
  REVIEWED/DONE required-pass composition. Scope is this design-review rail.

**Acceptance Criteria:**

1. **Producer-owned predicate in the generated prompt.** `review.py
   design-review` requests the spec's full rich attestation predicate, reads
   the pinned producer policy verdict and every required condition, and records
   evidence/run/contract references and reasons. It explicitly forbids
   evaluator execution, rescoring, new thresholds and replacement of compliance.
   Deterministic and mixed evidence are both allowed under the producer contract.
2. **Genuine positive path through completion.** Read the actual preserved
   baseline with approved design, effective policy/config and app/delivery
   identities matching. A fresh read-only reviewer attests it; `record-review`
   writes the existing design-review path and standard verdict envelope.
   A flagged fixture clears REVIEWED and DONE only with all the other normally
   required reviews, reconciliation and dependencies satisfied.
3. **Required failure cannot be averaged away.** A genuine producer run whose
   composite exceeds its own threshold but whose required condition fails
   receives a non-passing attestation. Recording that verdict causes the
   existing REVIEWED/DONE rail to refuse with the responsible condition/run
   reference. It never produces a replacement composite. An explicit producer
   pass conflicting with a required failure is also non-clearing.
4. **Missing and inconclusive are not success.** Required condition missing,
   unknown, not-run, inconclusive, environment-error, unreadable records,
   unsupported contract version and absent explicit rich policy verdict each
   yield a non-passing record and lifecycle refusal with an actionable reason.
   Required coverage is checked against the policy inventory, not result rows.
   Optional outcomes are treated exactly as the approved producer policy says.
5. **Bounded integration.** No new pass/stage, runtime import/invocation or
   auto-discovery dependency is needed. Only flagged design-review evidence
   requires the rich semantics when the slice selects that contract.
   Compliance/craft/reconciliation are independently required as before.
   Update directly related live guidance and regenerate all host packages in
   the future implementation; do not amend closed specs or conventions.

### Behavioral rules

| Rule | Operation | Actor | Precondition | Outcome | Rationale | AC |
|------|-----------|-------|--------------|---------|-----------|----|
| BR-1 | Attest and record | Read-only reviewer | Rich producer pass, all required outcomes and bindings valid | Pass may clear existing rail | Producer owns policy | 1, 2 |
| BR-2 | Attest and record | Read-only reviewer | Composite high, required failure or contradiction | Non-pass; completion refused | Required conditions are not averages | 3 |
| BR-3 | Attest and record | Read-only reviewer | Required evidence missing or inconclusive | Non-pass with reason | Unknown is not pass | 4 |

### Verification scenario

**Preconditions:** Parent-provided frozen pilot captures with actual producer
commands, aligned versions and complete identities. Use an isolated Jig
fixture, no live installation edits. Presatisfy unrelated review/dependency
requirements so refusal is attributable to design evidence.

**Invocation:** Generate the design-review prompt; run a fresh read-only
reviewer against each genuine capture; record its actual verdict using
`record-review`; exercise existing `check-reviews` and `transition` commands
at REVIEWED and DONE. Publish exact runnable fixture commands at implementation.

**Preserved behavior:** Separate compliance/craft/reconciliation, opt-in gate
and no producer invocation from review.

**Code revision / dirty-change identity:** Record the Jig revision plus pilot
application source/dirty-input, config, evaluated build and delivery identities;
preserve evaluator artifacts and CLI observations under a durable verification
path. They do not exist yet.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Baseline attestation and completion | 1, 2 | Pass record; existing rail clears | Not executed | not-run | Required genuine baseline and CLI trace, pending |
| Required failure with high composite | 3 | Non-pass; refusal names required failure | Not executed | not-run | Required genuine planted-failure run, pending |
| Inconclusive or missing evidence | 4 | Non-pass; refusal names missing/inconclusive evidence | Not executed | not-run | Genuine inconclusive capture plus labelled deletion fixture, pending |

**DoD:**
- [ ] All ACs verified with witnessed red-to-green tests and producer-backed
  scenario evidence; no not-run step credited as success.
- [ ] Targeted review/workflow tests and affected host-package checks pass.
- [ ] Independent compliance, craft and arch reviews recorded and clear.
- [ ] Deviation log, reconciliation sweep and reconciliation review recorded.
- [ ] Live guidance describes the new predicate without changing closed records.

### Close-out (post-DONE)

- [ ] Regenerate/audit status board; move load-bearing invariants into Notes.
- [ ] If this closes the spec, compress active-spec primer entries.

**Anti-horizontal-phasing check:** The developer can consume an actual producer
run, record an honest attestation and observe completion clear or refuse.

## Assumptions

Servo and Vellum's aligned producer/approval contracts and genuine preserved
pilot runs will satisfy the spec's A1/A2 prerequisites. None is asserted shipped.

### Deviation log (after reconciliation)

Not implemented; no deviations claimed.

### Reconciliation sweep

Pending implementation and independent reconciliation.
