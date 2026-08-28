---
status: DRAFT
dependencies: [adr-0058]
last_verified:
kind: spike
frame_review: true
---

## Slice 112-04 — refclaims-cas-spike

**Goal:** Resolve ADR-0058 Assumption A1 before the Class-B remote path is built:
determine whether git hosts permit a custom `refs/claims/*` namespace pushed as a
compare-and-swap lock, and confirm the local-worktree mechanics.

**Question:** Can jig use `git push --force-with-lease=refs/claims/<N>: origin
HEAD:refs/claims/<N>` as a create-if-absent distributed mutex on the hosts jig
targets (GitHub personal + EMU at minimum), and does the same-machine
`git update-ref refs/claims/<N> HEAD ""` behave as an atomic local mutex visible
across linked worktrees (A2)?

**Time-box:** 4 hours.

**DoR:**
- ✅ ADR-0058 Accepted; A1/A2 identified as the load-bearing unknowns.

**Findings:** _Filled during the spike. Probe: push a `refs/claims/*` ref to a
scratch remote; attempt a racing second create; confirm rejection semantics.
Test `update-ref` create-if-absent across two linked worktrees. Record which
hosts allow the namespace and whether branch-protection/EMU policy interferes._

**Outcome:** _One of `spec 112-05 unblocked` (A1 holds; ref-CAS path viable) /
`spec 112-05 reshaped onto ADR-0053 reservation-branch fallback` (A1 fails) /
`ADR-NNNN created` (if the finding is load-bearing enough to record). Set at DONE._

**DoD:**
- [ ] Question answered with evidence (commands run + observed host behavior).
- [ ] Outcome recorded; 112-05 DoR updated to reflect the chosen claim surface.
- [ ] Findings captured under this slice heading.

**Anti-horizontal-phasing check:** Spike — delivers a decision (which claim
surface Class-B uses), not shippable behavior; nested in this spec per the
always-nested rule.

### Deviation log (after reconciliation)

_N/A until the spike closes._

### Reconciliation sweep

_N/A — spike._
