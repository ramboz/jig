---
status: IN_PROGRESS
dependencies: [119-01, adr-0065]
last_verified:
arch_review: true
frame_review: true
claimed_by: jig-delivery-freshness-guard
---

## Slice 119-02 — reject-stale-delivery

**Goal:** A developer cannot complete a changed delivery using an earlier valid
design-review pass, even when the evaluator definition is unchanged.

**DoR:**
- [x] 119-01 DONE; ADR-0065 accepted and readiness review passes.
- [x] Parent aligns build-owner input closure, canonical digests, dirty-input
  handling and the authoritative, independently determined current delivery
  reference at C0, including how the observer
  will link it to the served build.
- [x] Baseline/change/renewal capture protocol and C1 source inputs are defined.
  Produce and prove genuine changed-app/renewed runs, with unchanged eval
  definition and an uncommitted-input variant, during this slice's AC/DoD;
  do not require already-finished integration to start.
- [x] Settle the machine-readable binding references within the existing
  design-review artifact conventions; do not invent new slice frontmatter.

Readiness: the 119-02 checkpoint in [plan.md](plan.md) defines the bounded
encoding and proof obligations. Independent framing and spec-readiness both
pass; the actual response is preserved in
[verification/slice-02-readiness-response.md](verification/slice-02-readiness-response.md).
Genuine renewed-build acceptance remains an implementation obligation.

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

**Code revision / dirty-change identity:** Exact exercised source hashes, genuine
frozen6cc producer run, independent context, full rooted inventories and actual
CLI outcomes are preserved in
[verification/slice-02-freshness-proof.md](verification/slice-02-freshness-proof.md).
Synthetic transport Git HEAD is labelled separately from producer revision.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Changed declared current bytes, unchanged definition, reuse A pass | 1, 2, 4 | Both review reuse and DONE refuse stale build | Same actual recorded pass refuses copied candidate/build/delivery changes without back-edge; all bytes restored | pass | [72CLI trace and initial actual wrapper attestation](verification/slice-02-freshness-proof.md) |
| Dirty/config/source/result mismatch | 1, 3, 4 | Precise refusal; no evaluator run | 12copied source/config/policy/checks/oracle/runtime/capture/acquisition cases,36refusals; structural reference controls in tests | pass | [Exact mutation/refusal/restoration evidence](verification/slice-02-freshness-proof.md) |
| Fresh evaluation and attestation of B | 5 | Existing completion rail clears | Not executed | not-run | Genuine renewed run and CLI trace, pending |
| Documentation-only change | 5 | App identities unchanged; no HEAD-only refusal | Synthetic transport HEAD changes outside declared input closure; same pass clears normal fixture DONE | pass | [Scoped input-manifest/Git witness](verification/slice-02-freshness-proof.md) |

**DoD:**
- [ ] All ACs verified; stale-result reuse shown red before the change and
  non-clearing afterward, with genuine A/B overall/component runs, demonstrated
  served-build binding, runtime substitution/replay refusal and declared
  fixture mutations.
- [x] Affected review/workflow tests and host-package checks pass.
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

The existing design-review recorder and evidence validator now share a finite
read/hash consumer. Selection/context/bindings are JSON blocks in existing
bodies, not new frontmatter, states or passes. Exact named references and
closed inventories are reviewer-authored; the writer never silently discovers
or approves new comparison inputs. Historical unselected/unflagged workflows
are preserved; broad legacy work remains119-03.

The first served-link draft incorrectly assumed a separate raw response body
file. Actual producer records instead declare response hashes in observation
`loaded_resources`; a witnessed red and surgical fixed-field link now match
that supported contract without adding a programmable query language.
The first real wrapper attester found a missing installed runtime pin and an
incomplete actual-copy output audit; both were corrected before recording
the passing wrapper. Original producer records and earlier nonpasses remain
preserved. No score, approval, frozen policy or source epoch was rewritten.
The first whole-slice compliance review also found malformed root NUL bytes
escaping as a Python3.9 internal error. A witnessed red precedes the lexical
root preflight and recording/reuse regressions; final mutation and
already-DONE proofs were repeated on the corrected guard.

Code/tests/live guidance and all three official host packages are implemented.
Automatic old-pass refusal/restoration is proved with genuine preserved
producer verdicts and explicitly labelled copied mutation/transport fixtures,
including all3887currentexternalruntime files. Genuine same-frozen-definition
changed-build B renewal is still parent-owned and unverified here. Restoration
is not credited as renewal. No whole-slice PASS/DONE is claimed until AC5 and
the required ordered reviews/reconciliation clear.

### Reconciliation sweep

Prepared sweep, pending final independent reconciliation:

| Surface | Disposition | Reason |
|---------|-------------|--------|
| Source recorder/shared evidence validator/finite binding helper + tests | updated | Same read/hash check at recording and existing REVIEWED/DONE composition |
| Independent-review live instructions and finite encoding | updated | Explicit opt-in, current raw bytes/complete inventories, independent context and limits |
| `docs/workflow.md`, `docs/architecture.md` | updated | Existing approved consumer boundary; no new ADR decision or producer runtime |
| Three generated host packages | updated | Official builder and drift guard only; never hand-edited |
| 119plan/tasks/slice/verification/reviews and status board | updated | Exact parent/readiness/proof and honest remaining AC5; normal helpers own state |
| Inbox, primers, Accepted ADRs, conventions and closed records | no-op | No item resolved, spec remains open, no amendment/convention authority |
| Other repositories and installed/global plugins | no-op | External evidence/toolchain read-only; parent owns producer renewal/integration |
| Broad legacy migration and new provenance UX | deferred | 119-03 remains DRAFT |
| `docs/memory/learnings.md` | updated | Installed-vs-source runtime and actual served-response/copy-audit pitfalls; summary/team-check completed |
| Final reconciliation verdict | deferred | Required after AC5 and ordered reviews; no invented lifecycle pass |
