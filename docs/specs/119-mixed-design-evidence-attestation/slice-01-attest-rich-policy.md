---
status: DRAFT
dependencies: [071-01, 104-02, adr-0065]
last_verified:
arch_review: true
frame_review: true
---

## Slice 119-01 — attest-rich-policy

**Goal:** A developer can use genuine frozen mixed-policy evidence to clear
the existing design-review rail, while a high average with a required failure,
component success with overall quality failure, or incomplete evidence cannot
earn completion.

**DoR:**
- [ ] ADR-0065 accepted in a later authorized phase; independent framing and
  spec-readiness reviews pass.
- [ ] C0 aligns the Vellum approval reference, installed overall
  Servo gate authority/policy, separate input/envelope/gate-payload/design-eval
  versions, exact serialization/digest domains/test vectors, explicit required
  matrix, subordinate run/digest references and current/served/delivered-build
  closure predicates. Concrete tolerance/transport choices need owner approval.
- [ ] C1 source/input checkpoint identifies approved normal/open inputs while
  Vellum 013-01 remains IN_PROGRESS. Producer invocation/capture protocol is
  defined; runnable consumer code, full driven-state integration and passing
  pilot evidence are not prerequisites to start implementation.
- [ ] Existing source surfaces read at the spec's pinned main anchor:
  `build_design_review_prompt`, `record-review`, `validate_evidence` and the
  REVIEWED/DONE required-pass composition. Scope is this design-review rail.

**Acceptance Criteria:**

1. **Producer-owned predicate in the generated prompt.** `review.py
   design-review` requests the spec's full rich attestation predicate, reads
   the pinned installed overall gate-payload policy verdict and every required
   condition. It treats design component evidence as run/digest-bound subordinate
   support, not the completion authority, and records separately named
   contract versions, gate/component run references, digests and reasons.
   It explicitly forbids
   evaluator execution, rescoring, new thresholds and replacement of compliance.
   Deterministic and mixed evidence are both allowed under the producer contract.
2. **Genuine positive path through completion.** Read the actual preserved
   overall-gate baseline produced during implementation, with approved design,
   effective policy/config, gate/component run/digest references and app/delivery
   identities matching. The installed overall gate's required and quality
   conditions must pass. A fresh read-only reviewer attests it; `record-review`
   writes the existing design-review path and standard verdict envelope.
   A flagged fixture clears REVIEWED and DONE only with all the other normally
   required reviews, reconciliation and dependencies satisfied.
3. **Required failure cannot be averaged away.** A genuine producer run whose
   composite exceeds its own threshold but whose required condition fails
   receives a non-passing attestation. Recording that verdict causes the
   existing REVIEWED/DONE rail to refuse with the responsible condition/run
   reference. It never produces a replacement composite. An explicit overall
   gate pass conflicting with a required failure is also non-clearing.
4. **Missing and inconclusive are not success.** Required condition missing,
   unknown, not-run, inconclusive, environment-error, unreadable records,
   unsupported namespaced contract version, absent explicit overall gate
   verdict or missing/mismatched subordinate run/digest reference each
   yield a non-passing record and lifecycle refusal with an actionable reason.
   Required coverage is checked against the policy inventory, not result rows.
   Optional outcomes are treated exactly as the approved producer policy says.
5. **Bounded integration.** No new pass/stage, runtime import/invocation or
   auto-discovery dependency is needed. Only flagged design-review evidence
   requires the rich semantics when the slice selects that contract.
   Compliance/craft/reconciliation are independently required as before.
   Update directly related live guidance and regenerate all host packages in
   the future implementation; do not amend closed specs or conventions.
6. **Component pass is not overall pass.** Execute a genuine control run in
   which the deterministic design-evidence component succeeds and its required
   observations pass, but the installed gate's quality requirement fails.
   The reviewer records non-pass and REVIEWED/DONE refuse, citing the preserved
   overall quality failure rather than treating component-envelope `pass` as
   completion. An overall-pass record contradicting that quality failure is
   non-clearing; no reviewer rerun or re-scoring repairs the contradiction.
   A component-envelope v1 label must not select legacy gate-payload v1.

### Behavioral rules

| Rule | Operation | Actor | Precondition | Outcome | Rationale | AC |
|------|-----------|-------|--------------|---------|-----------|----|
| BR-1 | Attest and record | Read-only reviewer | Installed overall gate passes; required outcomes and component/delivery bindings valid | Pass may clear existing rail | Overall installed policy is authoritative | 1, 2 |
| BR-2 | Attest and record | Read-only reviewer | Composite high, required failure or contradiction | Non-pass; completion refused | Required conditions are not averages | 3 |
| BR-3 | Attest and record | Read-only reviewer | Required evidence missing or inconclusive | Non-pass with reason | Unknown is not pass | 4 |
| BR-4 | Attest and record | Read-only reviewer | Deterministic component passes; overall quality fails | Non-pass; completion refused | Component success does not satisfy overall policy | 6 |

### Verification scenario

**Preconditions:** Produce frozen pilot captures during implementation using
actual producer commands, aligned namespaced versions and complete identities.
The preserved overall gate references its design evidence by run and digest.
Use an isolated Jig
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
| Deterministic component passes, overall quality fails | 1, 6 | Non-pass; REVIEWED/DONE refuse despite component pass | Not executed | not-run | Genuine installed overall-gate control with linked component evidence, pending |

**DoD:**
- [ ] All ACs verified with witnessed red-to-green tests and producer-backed
  overall-gate/component scenario evidence, including genuine served-build
  binding and the component-pass/quality-fail control; no not-run step credited
  as success.
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

Servo and Vellum's aligned authority/approval contracts can support genuine
preserved overall-gate/component pilot runs and binding proof during
implementation. These are spec A1/A2 assumptions, not already shipped evidence.

### Deviation log (after reconciliation)

Not implemented; no deviations claimed.

### Reconciliation sweep

Pending implementation and independent reconciliation.
