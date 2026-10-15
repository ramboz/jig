---
status: IN_PROGRESS
dependencies: [071-01, 104-02, adr-0065]
last_verified:
arch_review: true
frame_review: true
claimed_by: jig-producer-backed-attestation
---

## Slice 119-01 — attest-rich-policy

**Goal:** A developer can use genuine frozen mixed-policy evidence to clear
the existing design-review rail, while a high average with a required failure,
component success with overall quality failure, or incomplete evidence cannot
earn completion.

**DoR:**
- [x] ADR-0065 accepted in a later authorized phase; independent framing and
  spec-readiness reviews pass.
- [x] C0 aligns the Vellum approval reference, installed overall
  Servo gate authority/policy, separate input/envelope/gate-payload/design-eval
  versions, exact serialization/digest domains/test vectors, explicit required
  matrix, subordinate run/digest references and current/served/delivered-build
  closure predicates. Concrete tolerance/transport choices need owner approval.
- [x] C1 source/input checkpoint identifies approved normal/open inputs while
  Vellum 013-01 remains IN_PROGRESS. Producer invocation/capture protocol is
  defined; runnable consumer code, full driven-state integration and passing
  pilot evidence are not prerequisites to start implementation.
- [x] Existing source surfaces read at the spec's pinned main anchor:
  `build_design_review_prompt`, `record-review`, `validate_evidence` and the
  REVIEWED/DONE required-pass composition. Scope is this design-review rail.

Readiness evidence: accepted ADR-0065, the independently checked pins and
concrete boundary in [plan.md](plan.md), existing
[frame critique](reviews/slice-01-frame-critique.md) and separate
[spec-readiness review](reviews/slice-01-readiness.md). Current producer
completion proof remains an implementation obligation.

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

**Code revision / dirty-change identity:** The implemented source cut, actual
historical producer references, independently selected context, read/hash
limits and observed CLI refusals are recorded in
[verification/checkpoint.md](verification/checkpoint.md). Final-current
completion proof remains pending; no historical run is relabelled.

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| Baseline attestation and completion | 1, 2 | Pass record; existing rail clears | Genuine baseline attester returned needs-changes; recorded verdict refused REVIEWED/DONE | fail (non-clearing, correctly preserved) | [Checkpoint](verification/checkpoint.md); renewed final-current pass/completion pending |
| Required failure with high composite | 3 | Non-pass; refusal names required failure | Not executed | not-run | Required genuine planted-failure run, pending |
| Inconclusive or missing evidence | 4 | Non-pass; refusal names missing/inconclusive evidence | Not executed | not-run | Genuine inconclusive capture plus labelled deletion fixture, pending |
| Deterministic component passes, overall quality fails | 1, 6 | Non-pass; REVIEWED/DONE refuse despite component pass | Historical genuine control attester fail; both transitions refused | pass for historical refusal only; final-current not-run | [Actual attestation](verification/quality-fail-attestation.md), [CLI checkpoint](verification/checkpoint.md) |

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

Partial implementation checkpoint, not completed reconciliation:
the existing prompt/output envelope now describes the rich predicate and
namespaced producer bindings. Existing record/validator/lifecycle composition
is unchanged; automatic persisted freshness is 119-02. Source/guidance/tests
and all three generated packages are implemented. Genuine current acceptance
proof is incomplete: the actual baseline attester refused incomplete
raw-checks/nested-runtime audit coverage; a later producer execution-wrapper
closure gap requires renewed sealed-driver records. The genuine quality-fail
attester's nonpass and actual CLI refusals are retained as historical evidence.
No AC was removed or waived; no score was recomputed.

Compliance is needs-changes; supporting craft and arch reviews pass.
The craft redundancy nit is nonblocking and explicitly retained as synthetic
verdict-rail support, not producer semantic coverage. No new production
parser, pass, state, frontmatter, runtime dependency or scoring mechanism.
Closed 071/104, Accepted ADRs and conventions are untouched.

### Reconciliation sweep

Checkpoint sweep only; no RECONCILED claim. Scope is this worktree's changes
above exact proposal base `dcfcbc5eb8bfaac8f3cf11405a5e6b6f254d5c98`,
not the generated main-based changed-file list. The five inherited proposal/
reservation/acceptance commits (including ADR-0065 and its framing artifacts)
are excluded from this implementation sweep; no-op below means no change
in this checkpoint, not absence from the entire stacked branch.

| Surface | Disposition | Reason |
|---------|-------------|--------|
| `skills/independent-review/review.py`, tests and SKILL.md | updated | Full prompt predicate, output references and explicitly synthetic rail tests |
| `docs/workflow.md` | updated | Read-only overall authority, input/delivery binding and 119-02 boundary |
| Three `hosts/` packages | updated | Official generator; drift check passes |
| 119 spec/plan/tasks/slice/verification and status board | updated | Actual accepted/readiness status, IN_PROGRESS, nonpassing compliance, genuine refusal limits; proposal-era claims marked historical |
| 119 readiness/compliance/craft/arch/reconciliation review records | updated | Actual independent verdicts; readiness and supporting code-cut craft/arch pass, whole-slice compliance/reconciliation needs-changes |
| `docs/architecture.md`, ADRs, conventions | no-op | Existing approved boundary reused; no new module/API or decision |
| Inbox/primers/closed records | no-op | No item resolved, spec not closed, no amendment authorized |
| 119-02/03 and other repositories | deferred | Separate owners/scope; final producer context must arrive from parent |
| `docs/memory/learnings.md` | updated | Raw manifest hashes do not establish independently pinned transitive closure; helper summary/team check completed |
