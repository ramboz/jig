---
status: DRAFT
dependencies: [119-02, adr-0065]
last_verified:
frame_review: true
---

## Slice 119-03 — legacy-and-opt-in

**Goal:** A developer can use a supported legacy threshold-only producer without
silent rich-policy downgrade, while unflagged projects retain their workflow.

**DoR:**
- [ ] 119-02 DONE; ADR-0065 accepted and readiness review passes.
- [ ] The owner accepts the intentional provenance cost for newly requested
  legacy attestations; historical/unflagged behavior and defaults stay unchanged.
- [ ] Identify the authoritative installed legacy threshold-only policy and
  capture/renewal protocol at C0. Confirm spec A4
  during implementation with genuine evidence; no handcrafted passing surrogate.
- [ ] Parent aligns how a slice explicitly names its pinned producer contract
  in its existing evidence pointer; absence of rich fields is not version
  selection. Lower-is-better legacy scoring remains outside this proposal.

**Acceptance Criteria:**

1. **Legacy completion without a competing schema.** An explicitly pinned,
   supported legacy threshold-only contract can clear design-review with an
   actual honest run, original composite at least its own frozen threshold
   and all current source/config/build bindings. The selected verdict must
   cover the installed legacy policy, not only a component in a larger gate;
   design-evidence-envelope v1 does not imply legacy gate-payload v1.
   Record separately named legacy contracts
   and exact scope of the attestation; do not claim it satisfied richer
   required-condition policies. The existing record/check/transition path
   reaches DONE when ordinary reviews/dependencies also clear.
2. **No silent downgrade.** Missing or unsupported rich verdict/required
   outcomes, ambiguous/version-namespace-confused contract identity, or a slice
   requiring rich evidence with only a legacy scalar result receives non-pass
   and an actionable
   contract/evidence diagnostic, even with a high composite. No auto-adapter,
   guessed default version or format selection by missing fields.
3. **No invented old provenance.** Genuine legacy evidence without source,
   effective config or delivered-build binding cannot clear a new
   attestation/DONE. The diagnostic asks for renewed producer evidence.
   Historical closed review files are not rewritten or invalidated as records;
   they are not reusable proof of a different current delivery.
4. **Opt-in and review preservation.** A fixture with no `design_review` flag
   still needs ordinary compliance/craft/reconciliation and no external design
   evidence, plugin or identity data. Flagged fixtures still require independent
   compliance, including deterministic visual acceptance criteria when written,
   even when the external design verdict passes.
5. **One documented workflow across hosts.** Update the existing independent
   review/spec-workflow live guidance and examples to explain rich versus
   explicitly legacy evidence and renewal, regenerate all three host packages,
   and show equivalent prompt/record/refusal behavior. No changes to conventions,
   Accepted ADRs, closed specs, installed plugins or default gate selection.

### Verification scenario

**Preconditions:** Genuine legacy capture, explicit frozen contract and
aligned binding references; isolated flagged/unflagged fixtures with ordinary
review/dependency prerequisites satisfied. Missing-binding examples are
labelled negative fixtures, not manufactured successes.

**Invocation:** Prompt and independently attest the genuine legacy sample;
record and check its verdict through DONE. Repeat with absent provenance and
rich-required/legacy-only mismatch. Exercise unflagged completion with no Servo
installation. Record exact commands during implementation.

**Preserved behavior:** Legacy threshold semantics within their explicit scope,
separate compliance, unflagged workflow and closed historical records.

**Code revision / dirty-change identity:** Preserve producer version, original
run and policy/config, evaluated app/delivery identities and exercised Jig
revision. State unavailable identity as unavailable, not an empty passing field.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Genuine bound legacy result | 1 | Scoped legacy pass can clear DONE | Not executed | not-run | Genuine legacy capture and CLI trace, pending |
| Missing binding or rich-required mismatch | 2, 3 | Non-pass and precise renewal/contract reason | Not executed | not-run | Legacy negative fixtures and trace, pending |
| Unflagged ordinary completion | 4 | No design evidence dependency; normal reviews remain | Not executed | not-run | Isolated workflow preservation trace, pending |
| Rendered host review surfaces | 5 | Same semantics and record/refusal paths | Not executed | not-run | Future generated-package checks, pending |

**DoD:**
- [ ] Each AC verified with witnessed test coverage and genuine producer-backed
  compatibility scenario produced during implementation, not just literal
  prompt assertions or a component-only success promoted to overall pass.
- [ ] Targeted review/workflow and host-rendering checks pass.
- [ ] Independent compliance and craft reviews recorded and clear.
- [ ] Deviation log, reconciliation sweep and reconciliation review recorded.
- [ ] Memory-sync/primer hygiene considered without treating proposals as shipped.

### Close-out (post-DONE)

- [ ] Regenerate/audit status board and record compatibility boundaries in Notes.
- [ ] Compress active-spec primer entries when this spec closes.

**Anti-horizontal-phasing check:** A developer gets an honest legacy completion
or a concrete renewal/refusal path while ordinary unflagged work remains usable.

## Assumptions

Spec A4's supported legacy producer can supply genuine, delivery-bound renewed
evidence without Jig translating a second schema. If that capability is absent,
the positive path is blocked pending producer support, not relaxed.

### Deviation log (after reconciliation)

Not implemented; no deviations claimed.

### Reconciliation sweep

Pending implementation and independent reconciliation.
