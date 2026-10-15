# Plan: mixed design-evidence attestation

## 119-01 implementation checkpoint (2026-10-15)

The owner accepted ADR-0065 and C0. This implementation is stacked on
`jig-mixed-evidence-attestation` at
`dcfcbc5eb8bfaac8f3cf11405a5e6b6f254d5c98` (proposal PR #242); the initial
worktree and both proposal refs matched that exact commit. The authoring plan
below is historical, not an instruction to undo acceptance.

### Concrete consumer boundary

Implement 119-01 in `build_design_review_prompt` and its existing output
envelope, tests and live guidance. The slice selects its supported external
contract and points to the preserved evidence plus **separately selected**
approval, frozen policy/config and current delivery context in its body or
deliverables. Do not add slice frontmatter, a new pass, an evaluator import,
an executable producer adapter, automatic discovery or a second scorer.
The reviewer reads the contract and evidence; the orchestrator may supply
a preserved pure read/hash audit with its invocation and digest domains.
An unsupported or unauditable contract is non-clearing, not a guessed mapping.

`record-review`, `validate_evidence` and REVIEWED/DONE composition remain the
existing verdict rail in this slice. The recorded design-review body preserves
the references, versions, comparisons and refusal reasons. 119-02 owns automatic
revalidation of a previously recorded pass against changed delivery; this
checkpoint does not claim that follow-on behavior.

Source was re-read against main anchor `e3fb1283`: `review.py` is byte-identical
(`bf3cd8be3b903a9d4625f8d7d7d7021474be2d3b7a4b4cd31e37d8ef641fcdde`);
`review_evidence.py` has no diff from that anchor. The complete owning
119-01 criteria and the existing design-review round-trip tests were read.

### Pinned producer evidence contract

Servo's producer-owned [036 plan at 5440b634](https://github.com/ramboz/servo/blob/5440b63458bf862d4fe0b19e274db18c38c170aa/docs/specs/036-deterministic-design-evidence/plan.md)
defines the ordinary command output seam and candidate/delivery proof:

| Namespace / binding | Supported pilot shape |
|---|---|
| Vellum input | `vellum-design-input/0.1-pilot`; independently approved normal/open packages |
| Installed overall result | `kind: gate_result`, integer `schema_version: 2`; explicit overall `status`, `exit_code`, `reason`, `policy_hash`, required inventory/results and quality |
| Required component | `kind: required_component_result`, integer version 1; same gate `run_id`, frozen config/evaluator/source bindings |
| Command output refs | `kind: command_result_artifacts`, integer version 1; declared run-scoped root, manifest and complete sorted artifact inventory |
| Design envelope | `kind: design_evidence`, integer version 1; subordinate component status, constraints, source/policy/evaluator/build/current-delivery identities |
| Design-eval config | Separately pinned revision 2 where used; never inferred from the other versions |

The overall gate's `components[].result.{path,hash}` binds exact component
bytes; each component's raw `evidence[].result_artifact` binds the envelope
and complete capture tree. References use raw-byte SHA-256, not reserialized
JSON. Semantic identities use the producer's separate named domains and
canonicalization. No component-envelope v1 selects legacy overall-gate v1.
Required inventory comes from `.servo/required-policy.json` and its installed
pin, with approved checks/config/evaluator bindings, not result rows alone.
Preserved acquisition claim/receipt, served response/output closure and
independent delivery enumeration establish the runtime comparison; a URL,
repository HEAD or envelope's own `current_delivery` assertion does not.

Vellum C1 is published at
`55dd18007cd5664be17c1e7c4666fd1f00dd93d6`, under
`plugin/skills/build-to-redline/fixtures/approved-card/c1/release-r3/`.
Its raw normal/open/release/approval hashes are respectively
`b894ed7590cf7678af832071b657085cf9316bb1cd4c4dfde2f4f9be53ec0303`,
`5d3ac7de4780ab4cc21802e8e9cd3d5aae7572a3050312f7608ab4e7b839f4fb`,
`5aeea5e302038656d17ad881052a0f63d47bb297370f1c0c5d04e0a1339b6313`,
`d4322d16444bba75f6e4384430284595ecf2b203f4278c3ac0fda9564f8c4c5b`.
Approval is fixture-scoped agent source approval, not an authenticated human
signature or candidate-delivery acceptance.

### Execution and honest stop

1. Run an independent readiness review of this plan plus the full slice,
   separately from the already-passing frame critique; use normal transitions.
2. Implement with witnessed failing prompt/rail tests first. Preserve old
   unflagged behavior; do not implement 119-02/03 wholesale.
3. Generate the actual prompt and run a fresh read-only attester against
   genuine producer records and an independently selected delivery context.
   Record the actual verdict and exercise REVIEWED/DONE in isolated fixtures
   with other prerequisites satisfied. Label disposable mutation controls.
4. Run compliance, craft and arch reviews and record their actual verdicts.
   Reconcile guidance and regenerate all three host packages officially.
5. If any genuine current-epoch AC proof is unavailable, preserve IN_PROGRESS
   and publish a stacked draft checkpoint. A compliance refusal is evidence,
   not permission to invent a pass or remove an AC.

The producer handoff `036-01-current-control-handoff.json` has raw SHA-256
`e1f27950e91c4dbbcb91a766eb7c01eb5987d17e8c931913b26d580124a6c42c`.
It preserves genuine overall-pass run `545a9dd5-805f-4f79-a695-bc9ff6faf63f`
from a **prior helper epoch** and component-pass/quality-fail run
`01ec10a8-62fe-448a-81d7-25c06a0e45a7` (`0.5120652827881754 < 0.8`).
Neither is silently relabelled as a current completion baseline. Current
producer records and independently selected current delivery remain required
for completion; whole Servo 036 DONE is not a start prerequisite.

**Later checkpoint:** implementation and fresh attestations are now recorded
in [verification/checkpoint.md](verification/checkpoint.md). The newer genuine
`b6e14da1` baseline also received a nonpassing attestation for incomplete
read/hash closure coverage. The producer subsequently identified an unfrozen
scalar-quality execution wrapper and is sealing exact final `oracle.sh`
bytes through its existing artifact closure and staged reapproval. Treat
both inspected baseline/control records as historical interoperability, not
final-current completion. Current whole-slice compliance is needs-changes;
supporting craft/arch passes do not advance lifecycle.

## Authoring phase (historical proposal)

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
