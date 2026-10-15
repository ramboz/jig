# Plan: mixed design-evidence attestation

## Authoring phase (this proposal)

Keep ADR-0065 Proposed and all slices DRAFT. Reserve through installed helpers,
review framing independently, record actual verdicts, regenerate/audit the
indexes and open one draft proposal PR. No source, convention, closed-record
or installed-plugin changes; no acceptance or merge.

Main is PR-protected. The documented `--no-push` path allocated ADR-0065 and
spec 119 provisionally; this PR carries those reservations. Existing open
PR #230's provisional ADR-0062/0063 and specs 114/115 remain untouched.

## C0 readiness contract (parent-owned alignment)

1. Link the Vellum and Servo draft owners after all sibling proposals exist.
   Pin installed overall gate-payload verdict authority, subordinate component
   run/digest links, complete required inventory and inconsistent-record rules.
   Keep input-contract, design-evidence-envelope, gate-payload and design-eval
   versions separate; component-envelope v1 is not legacy gate-payload v1.
   These are consumer needs, not a competing producer schema.
2. Pin the source/target approval authority and effective policy/config identity.
   Set the build-owner input closure, canonical digest rules, dirty-input
   handling and independent delivery/observed-build binding.
   Define exact input serialization/version/digest domains/test vectors and
   explicit required matrix. Concrete tolerance/transport choices are not yet
   owner-approved; no runnable consumer code is demanded at C0.
3. Define capture/invocation protocol and producer checkpoints. During
   implementation, produce genuine baseline, high-composite required-failure,
   deterministic-component-pass/overall-quality-fail, inconclusive, changed-app,
   renewed and legacy captures, with run/digest links and actual binding proof.
   Completed integration is not a readiness prerequisite. Label mutation
   fixtures separately. Claude Design first; Figma not required.
4. Settle the narrow encoding of identity references in existing design-review
   artifacts and how current-delivery identity is obtained. Keep schemas
   producer-owned and gate validation limited to evidence consistency.
5. Obtain later-phase ADR acceptance and spec readiness authority, then follow
   the normal gated transitions. A passing authoring review alone is not enough.
   Obtain the owner's explicit choice on the intentional legacy provenance
   cost; do not silently change historical/default behavior or weaken rich policy.

## Cross-repo start order (parent-coordinated)

Servo 035-01 standalone -> Vellum 013-01 IN_PROGRESS C1 source/input checkpoint
(prepare/approve normal/open references without claiming driven-state handoff
DONE) -> Servo 036-01 real observer/served-build proof -> Jig 119-01/02
attestation -> Vellum 013-01 closes and 013-02 state integration.

C0 defines accepted/aligned decisions, installed verdict authority, exact input
serialization, separate versions, digest domains/test vectors, explicit required
matrix and current/served/delivered-build closure predicates. C1 prepares and
approves actual normal/open card source captures, typography/frame goals and
mapping while 013-01 is IN_PROGRESS; open capture preparation is not 013-02
completion. The old dimension-test PNG/redline is not an approved design goal.
Runtime binding, substitution/replay and integration proof are AC/DoD outputs
of the owning implementations, not dependencies on whole sibling specs being
DONE or runnable consumer code at C0.

## Future implementation sequence

1. **119-01:** TDD the rich evidence attestation workflow through actual
   prompt/reviewer/record/check/transition use. Use genuine baseline and
   high-composite-required-failure captures and the deterministic-component-pass/
   overall-quality-fail control, then negative evidence variants. Bind
   subordinate evidence to the authoritative installed gate run/digest.
   First delivery must be end-to-end, not a parser scaffold.
2. **119-02:** TDD and exercise stale delivery at initial review and reuse at
   DONE without a manual back-edge. Use independently identified builds A/B,
   dirty input/config/source changes and renewed evaluator evidence. Narrowly
   extend existing design-review validation; do not grow general staleness
   infrastructure. Keep documentation-only changes outside app input closure.
3. **119-03:** Exercise bound legacy threshold-only completion, missing
   provenance refusal, rich-required downgrade refusal and unflagged completion.
   No format auto-adapter or default new gate.
4. For each slice: update directly related live guidance; regenerate all host
   packages when source changes; run affected scoped tests/checks; run fresh
   independent compliance/craft and conditional arch reviews; reconcile,
   record reconciliation evidence and close through the existing gates.

## Validation scope

Authoring: scoped `spec_lint.py`, frame-review derivation, ADR index and board
regeneration/audits, diff whitespace and documentation link checks. No unrelated
full suites or claims about runtime behavior.

Future implementation: affected independent-review/workflow/review-evidence
selectors, manifest/rendering checks where touched and three-host drift check.
The orchestrator executes producer-backed scenarios before read-only review;
the reviewer only reads the frozen evidence. Record observed outcomes and
Jig/application/dirty-input/config/build identities. Fixture success demonstrates
integration behavior, not broad real-world oracle quality.
