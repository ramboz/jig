---
status: DRAFT
dependencies: [119-01, adr-0065]
last_verified:
arch_review: true
frame_review: true
---

## Slice 119-02 — reject-stale-delivery

**Goal:** A developer cannot complete a changed delivery using an earlier valid
design-review pass, even when the evaluator definition is unchanged.

**DoR:**
- [ ] 119-01 DONE; ADR-0065 accepted and readiness review passes.
- [ ] Parent aligns build-owner input closure, canonical digests, dirty-input
  handling and the authoritative, independently determined current delivery
  reference at C0, including how the observer
  will link it to the served build.
- [ ] Baseline/change/renewal capture protocol and C1 source inputs are defined.
  Produce and prove genuine changed-app/renewed runs, with unchanged eval
  definition and an uncommitted-input variant, during this slice's AC/DoD;
  do not require already-finished integration to start.
- [ ] Settle the machine-readable binding references within the existing
  design-review artifact conventions; do not invent new slice frontmatter.

**Acceptance Criteria:**

1. **Explicit three-way freshness.** A design-review attestation compares
   approved source/target, effective frozen policy/config, and evaluated
   implementation to current delivery using the identities in the overview.
   Missing dirty-input/config/build identity, inaccessible bytes or unknown
   input closure is non-clearing. A result compared only to its own manifest,
   matching HEAD alone or the same app URL does not prove delivery freshness.
2. **Changed app, unchanged eval definition.** After a valid review of build A,
   deliver build B with an application input or asset/control change but the
   same target and eval policy/config. Reusing A's producer result in a new
   review yields non-pass. Reusing A's already recorded passing design-review
   artifact at REVIEWED or DONE also refuses without requiring a manual
   lifecycle back-edge first. The message names the changed binding and asks
   for fresh producer evidence/attestation, not a Jig evaluation.
3. **Other stale or inconsistent evidence.** Changing approved source/target,
   installed gate/policy/config, dirty inputs, effective runtime/build config or
   referenced overall/component run/result bytes invalidates reuse through the
   same rail. A component run/digest not linked to the pinned overall gate
   cannot support reuse. Pin the actual run reference rather than the last row
   of a mutable ledger; absence of the pinned run is non-clearing. Reject a build
   claim that disagrees with the independently identified delivery.
4. **Bounded deterministic revalidation.** Existing design-review evidence
   checks re-read/hash the declared references at REVIEWED and DONE, compare
   against the attested identities and current delivery, and return actionable
   diagnostics. They do not score, judge the UI, import/invoke Servo, validate
   every other pass's code freshness or add a new lifecycle gate. A recorded
   `pass` with incomplete comparison references cannot clear this contract.
5. **Renewed pass and honest preservation.** A genuine new producer run on
   build B, with authoritative overall-gate pass and matching subordinate
   component run/digest, followed by a new independent attestation through the
   existing helper, clears with the other ordinary requirements satisfied.
   A documentation-only commit outside the declared application input closure
   does not invalidate matching app/build evidence solely because HEAD changed.
   Missing closure evidence never receives that exception by guesswork.
6. **Truthful limits.** Attestation guidance and recorded reasons distinguish
   identity consistency from authenticity: unsigned local evidence is not
   forgery-proof. No signed-record claim or hostile-agent guarantee is introduced.

### Verification scenario

**Preconditions:** Aligned owner-defined input manifests and genuine captures
produced during implementation; isolated fixture with a previously passing
overall-gate attestation and
unrelated evidence/dependencies satisfied. Source/eval artifacts remain frozen.

**Invocation:** Deliver changed build B without changing the eval definition;
attempt `check-reviews`/REVIEWED and DONE with A's evidence. Repeat with a dirty
input, changed config/approval, then genuine renewed run/attestation on B.
Exercise documentation-only preservation separately. Publish exact commands
with the future fixture, not invented executable claims in this draft.

**Preserved behavior:** No rerun in review, no automatic back-edge requirement
to notice changed delivery, no blanket HEAD-based invalidation.

**Code revision / dirty-change identity:** Preserve Jig revision, application
revision plus dirty-input digest, full binding manifests and actual CLI outcomes.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Build B, unchanged definition, reuse A pass | 1, 2, 4 | Both review reuse and DONE refuse stale build | Not executed | not-run | Genuine A/B captures and gate trace, pending |
| Dirty/config/source/result mismatch | 1, 3, 4 | Precise refusal; no evaluator run | Not executed | not-run | Genuine changed-input runs and labelled corruption fixtures, pending |
| Fresh evaluation and attestation of B | 5 | Existing completion rail clears | Not executed | not-run | Genuine renewed run and CLI trace, pending |
| Documentation-only change | 5 | App identities unchanged; no HEAD-only refusal | Not executed | not-run | Scoped input-manifest comparison, pending |

**DoD:**
- [ ] All ACs verified; stale-result reuse shown red before the change and
  non-clearing afterward, with genuine A/B overall/component runs, demonstrated
  served-build binding, runtime substitution/replay refusal and declared
  fixture mutations.
- [ ] Affected review/workflow tests and host-package checks pass.
- [ ] Independent compliance, craft and arch reviews recorded and clear.
- [ ] Deviation log, reconciliation sweep and reconciliation review recorded.
- [ ] Live instructions cover current-delivery comparison and trust limitations.

### Close-out (post-DONE)

- [ ] Regenerate/audit status board; retain the stale-delivery invariant in Notes.
- [ ] If this closes the spec, compress active-spec primer entries.

**Anti-horizontal-phasing check:** A developer sees old evidence refused on an
actually changed app and can complete only after a genuine renewed attestation.

## Assumptions

The build owner can close and identify relevant application inputs and link the
served build independently of the result, as spec A2 proposes. The local trust
setting is spec A3, not proof against co-edited evidence.

### Deviation log (after reconciliation)

Not implemented; no deviations claimed.

### Reconciliation sweep

Pending implementation and independent reconciliation.
