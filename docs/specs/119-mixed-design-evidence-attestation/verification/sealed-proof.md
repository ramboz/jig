# Final sealed-epoch verification — 2026-10-15

This replaces the earlier **evidence gap**, not the historical records:
the old baseline refusal and quality failure remain preserved unchanged.
All four 119-01 scenarios now have actual producer-backed observations.
Whole-slice review/lifecycle evidence is recorded separately in `reviews/`.
This proof does not supply 119-02 automatic persisted-pass freshness.

## Code, contract and independently chosen context

Jig code under exercise is checkpoint
`492f128dc34823e356350dfd4cc521e355e1cf18`. The only subsequent executable
test change renews the expected producer pin; `review.py`, `record-review`,
`validate_evidence` and workflow transition behavior are unchanged from that
checkpoint. Live guidance is renewed to the sealed producer epoch and
officially regenerated across all three hosts.

Producer source:
`6cc759e807cab5411363b44c19c58e7a457b3715`; integrated readback
`6d5e5b66c7f3ed796c7cbbbafdb84012e2e29cb5` has identical producer core.
Producer contract remains separately versioned Vellum input
`vellum-design-input/0.1-pilot`, overall `gate_result`2, required component1,
command output-reference1, subordinate design envelope1 and quality config2.
The overall installed policy, including quality, is the authority.
No new producer schema or Jig evaluator/parser/import/discovery was added.

Parent independently selected source/dirty-input, approved C1 source/target,
RAW approved checks, final oracle wrapper, effective policy/config,
build/output/current-delivery and all3887nestedruntime files **before**
result envelopes existed. These are not envelope-derived expected values.
Raw files and separately named Servo LF / Vellum NUL semantic domains are
kept distinct; a URL, timestamp or Git SHA alone is not the app identity.

Proof root `P`:
`/Users/ramboz/.copilot/session-state/e33c1f8d-6be8-4fb4-8801-6cfe7838aa5c/files/final-proof-6cc759e`.
Parent independent contexts `I`:
`/Users/ramboz/.copilot/session-state/61f2e313-f28a-403a-9433-724268681e33/files`.
Jig session artifacts `J`:
`/Users/ramboz/.copilot/session-state/c049095e-5c63-4af4-9e9a-dfd233c5e669/files`.

| Actual scenario / target under P | Run | Parent PRE-RESULT context under I and raw SHA-256 |
|---|---|---|
| Matching baseline / baseline | cbe6b5b3-a60f-4dc1-abb9-23a8fd6f48a2 | `036-sealed-baseline-independent-context.json`, `a08b529026a3a81f1a2e414b87fb654a34ee7ab2a570b34fce15b5a79131b32d` |
| Component pass / quality fail / misalignment | 2de07bf5-fc61-482d-bcf8-1dbc11ec2d5e | `036-sealed-misalignment-independent-context.json`, `bd09affabe5e8e8853599389875939e64b67ce5d3a93903b04326bd14632b355` |
| High quality / required fail / required-failure | 78963609-9c1f-4602-aa41-3b7129c60476 | `036-sealed-required-failure-independent-context.json`, `72a95bd0d95f9ea82bb1c0b0c02eab08809c5ea27d2a0c7e371d6850eab2768b` |
| Genuine ambiguous acquisition / baseline | dc9e9733-67de-4b1a-ac53-5643c4d05318 | `P/nojudge-controls/genuine-ambiguous-binding-inconclusive-pre-context.json`, `fc356d976c174a0c529e8146bd456587f2f58027b1517bff740021ea8a982f05` |

The actual immutable index `P/proof-index.json`, raw
`45a2df047e05d1dab67982a4b4a0280607537cf78094ad71fcd70b217bb2b2fc`,
indexes678artifacts, including all actual native receipts, approvals,
captures, final-current and no-judge control records. Jig independently
rehashed every indexed artifact with zero mismatch.
`J/119-01-final-index-rehash.json` preserves that observation.
Each actual live batch has its own independent definition review and final
staged-driver review, ordinary final approval/install/reinstall and complete
full-oracle artifact seal; draft-driver review hashes are not confused with
the subsequently approved raw checks. The earlier unfrozen-wrapper gap is
not waived, patched in old records or hidden.

## Actual fresh attesters and lifecycle observations

| AC | Actual producer outcome | Actual fresh attester | Existing rail observed |
|---|---|---|---|
| 1,2 | Baseline overallpass0; all28requiredpass; genuine0.97/default0.8 | pass | Design alone refuses missing compliance/craft; REVIEWED clears after those preconditions; reconciliation missing refuses; RECONCILED/DONE clear only after reconciliation precondition |
| 3 | Genuine0.9675/default0.8 but normal/open-title-font-size20.01 versus20/tolerance0;26pass/2fail; overallfail1 | fail, required_constraints_failed | Record preserves both responsible IDs/run refs; REVIEWED/DONE refuse |
| 4 | Genuine ambiguous acquisition,6pass/10fail/12unknown, qualityunavailable; overallenv_error2 | needs-changes, required_evidence_unavailable | Recorded nonpass; REVIEWED/DONE refuse |
| 4 | Thirteen labelled copied-result variants | Actual per-case fail/needs-changes | Every recorded nonpass refuses REVIEWED/DONE |
| 1,6 | All28requiredpass/componentpass; genuine0.5278427304671842/default0.8; overallfail1 | fail, quality_below_threshold | REVIEWED/DONE refuse despite component success; overall-pass contradiction copy also refuses |

Actual reviewer records:
[complete sealed baseline](sealed-baseline-attestation-complete.md),
[quality/inconclusive/mutations](sealed-controls-attestation.md),
[genuine high-quality required failure](sealed-required-failure-attestation.md).
These retain contract namespaces, source/config/delivery comparisons,
gate/component/envelope raw digests, required outcomes and responsible reasons.
The reviewer used the standard verdict envelope; no orchestrator-invented
passing design judgment was substituted.

### Review recovery, without rewriting evidence

The first final compliance review returned needs-changes for two concrete
verification defects. The initial positive response did not retain all
identifiable contract/context/audit/inventory/delivery references in its own
recorded body. A narrower fresh read-only reviewer authored the complete
provenance addendum above; that actual response is preserved verbatim, raw
`257786782ee2bfe848186d47a02f4b17b67bf3ec8d9ecafa563a6c57a045f6b6`,
and recorded in a new isolated positive fixture. The standard recorder adds
its normal final newline; it does not rewrite the review text.
The initial generic positive reply remains in
[sealed-baseline-attestation.md](sealed-baseline-attestation.md).

The initial required-failure DONE trace also reported missing fixture
deviation-log/sweep subsections alongside design failure. Those unrelated
fixture prerequisites were completed, then the existing genuine verdict was
re-recorded and both refusals repeated with no such extra blockers. The
initial trace remains unchanged as `119-01-required-failure-rail.json`;
the corrected witness is `119-01-required-failure-rail-v2.json`.
These are fixture/evidence corrections, not producer reruns or scope changes.

The13copied-result controls cover required missing/unknown/not-run/inconclusive/
env_error, unsupported gate namespace, absent overall verdict, absent
subordinate reference, unreadable component, component digest/run mismatch,
overall-pass/required-failure contradiction and overall-pass/quality-failure
contradiction. Original bytes remain untouched. The as-reviewed manifest is
preserved; the one generic context-label correction is logged in the
actual control review. These copies supplement, not replace, genuine runs.
Pilot inventory has no optional conditions; no extra optional-outcome veto
was introduced or claimed to have been exercised.

All fixture compliance/craft/reconciliation prerequisites are explicitly
**synthetic harness preconditions**, per the owning scenario's instruction
to isolate design clearance/refusal. They do not claim actual app review.
The passing design attestation and all selected negative verdicts are actual
fresh read-only reviewer decisions. Positive fixture dependencies are empty
and satisfied; actual Jig119 dependencies are independently checked at its
own final lifecycle transition.

The final124CLI observations (positive-v2, controls and required-failure-v2)
comprise68recordings,18checks and38transitions:
35expected transition refusals (32negative controls plus3missing unrelated
review prerequisites) and3positive transitions. The positive isolated
fixture ends DONE; every negative fixture stays IN_PROGRESS.

## Read/hash audits and exact traces

Jig independently rehashed4112baseline comparisons including all3887runtime
files; separate control rechecks cover3941raw references each. Producer
full audits preserve4175comparisons per live run. Different counts represent
different enumerated comparison sets, not additional judgments; all have
zero mismatch. Own scripts import no producer and execute no subprocess.
Preserved native replies report claude-opus-5 through pinned Claude CLI2.1.300;
baselineclaims26–33, quality-fail34–41, required-fail42–49. This is runtime-
reported identity and trusted-local consistency, not provider authentication
or a human source-approval signature.

| J artifact | Raw SHA-256 |
|---|---|
| `119-01-sealed-context-audit.py` | `21c4c7f98782bab084dd8fa3767e31084d7eea2bc30f2fe44c1381f9b4fc492f` |
| `119-01-sealed-context-audit.json` | `8d1945d9f4e4867ab329d5b3395c45bbddd76509cb541ba998babb1a0ed5ee6c` |
| `119-01-sealed-misalignment-pins.json` | `eff93710c031f56df6483eeab61ff47e9784dd43159a74308b36bec3a218d60f` |
| `119-01-sealed-required-failure-pins.json` | `6a84b802fdf75c1ac67c999995b7d124e2d304d9ab9b427f9142f038377a6172` |
| `119-01-sealed-baseline-rail-v2.json` | `497110681437e73c6c44d37db62b14afa62e66f57e6f11c384da10913c6a2139` |
| `119-01-sealed-controls-rail.json` | `cb07e4b27ddb03f37d91bf17bdca907e2bf42aed3a8d0f9e04c0e8889e4720ac` |
| `119-01-required-failure-rail-v2.json` | `fc80b9a739622b554ec9d25ace2dfbd700c6af5a13f5a0c92f05e71647a6ece7` |
| `119-01-final-index-rehash.json` | `2ecf81ef771f290346570da1594402db23e4aa27aac514259d3eb8db9b427641` |

Each trace records exact argv, expected/actual exit, stdout/stderr and
producer_calls=0/judge_calls=0. Runnable current read-only checks:

```bash
J=/Users/ramboz/.copilot/session-state/c049095e-5c63-4af4-9e9a-dfd233c5e669/files
python3 skills/independent-review/review.py check-reviews "$J/119-01-fixture-sealed-baseline-complete/spec.md" 001-01 --stage REVIEWED
python3 skills/independent-review/review.py check-reviews "$J/119-01-fixture-sealed-required-failure/spec.md" 001-01 --stage REVIEWED
python3 skills/independent-review/review.py check-reviews "$J/119-01-sealed-refusal-fixtures/genuine-inconclusive/spec.md" 001-01 --stage REVIEWED
```

Expected exits are0,2,2. The first-run orchestration scripts corresponding
to each trace preserve the recorded fixture setup/record/check/transition
commands; do not rerun them over already-completed fixtures as if creating
fresh execution evidence.

## Validation and boundaries

Final full compliance, craft, architecture and reconciliation reviews are
actual passes recorded in `reviews/`; the real slice entered REVIEWED and
RECONCILED through their normal evidence gates. DONE revalidates that
evidence and dependencies through its own normal gate; the slice record
carries the authoritative lifecycle state.
The craft nit about redundant synthetic verdict-only test reasons is retained
as nonblocking; these tests are never credited as producer-semantic proof.

The producer-pin guidance test was witnessed red for missing6cc759e, then
green after renewing the immutable link. Current affected suites:
289independent-review,103review-evidence,30workflow and18host-package tests
pass; scoped Ruff, Python compilation and official three-host drift checks
pass. These are in addition to the actual producer-backed scenarios, not
proxies for them.

No producer, browser, CLI quality evaluator or judge was called by Jig.
No threshold, weighted score, source target or approved policy was changed.
No new pass/state/frontmatter/runtime adapter; compliance/craft/architecture/
reconciliation remain independently required for the actual slice.
No closed071/104, Accepted ADR, conventions or other repo edits.

**119-02 is still necessary:** the existing validator does not yet
automatically invalidate a previously recorded design pass when delivery
changes before DONE. The initial fresh attester's current-delivery check
and producer stale-input controls do not establish that capability.
119-02 must implement/test that narrow persisted-pass revalidation in a
separate stacked slice/PR. Broad legacy work remains119-03.
