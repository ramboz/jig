---
status: Proposed
dependencies: []
last_verified:
frame_review: true
---

# ADR-0065: Attest the external policy verdict for the delivered revision

## Status

Proposed (2026-10-14)

**Proposal only.** No decision is accepted and no source implementation has
started. Number allocated by `adr.py new --no-push`: provisional on this
proposal branch, not reserved on `origin/main` (main requires a PR).

Plain-language summary: a good average score must not hide a required failure,
and evidence for yesterday's app must not complete today's delivery. Jig should
attest the installed external gate's overall policy verdict and its recorded
identities, not a component's success, without becoming an evaluator. The
tradeoff is stricter evidence requirements for projects that opt into
`design_review`, including legacy runs without build provenance.

## Context

Jig's design-review pass currently attests a thresholded external score.

**Current state, read at main
`e3fb1283a75131e4bc80e3aaf0bd019389d5a3df` on 2026-10-14:**

- [`build_design_review_prompt`, lines 1437-1530](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/independent-review/review.py#L1437-L1530)
  describes a non-deterministic fidelity eval. Its three attestation conditions
  are execution, unchanged frozen config/threshold, and composite at least the
  evaluator's own threshold. That enumerates this function's explicit
  conditions, not every possible external producer.
- [`required_passes`, lines 255-295](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/_common/review_evidence.py#L255-L295)
  keeps design-review opt-in at REVIEWED; DONE reuses that evidence set.
  [`validate_evidence`, lines 519-587](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/_common/review_evidence.py#L519-L587)
  checks recorded verdicts and review-back-edge freshness, rather than comparing
  an evaluated app's identity to the delivery. This is a bounded source
  observation, not a claim that all review staleness is solved here.
- [Spec 071](../specs/071-design-review-pass/spec.md) owns the shipped,
  attest-only pass. [ADR-0049](adr-0049-design-fidelity-routing-to-originating-spec.md)
  and [spec 104](../specs/104-design-fidelity-routing/spec.md) own fidelity
  routing and graduated opt-in. Their closed records are not edited.
- [ADR-0022](adr-0022-pluggable-oracle-boundary.md)'s broader runtime binding
  remains PARKED. [ADR-0059](adr-0059-servo-delivered-work-design-review-gate.md)
  is a separate Proposed contract-completeness/reward-hacking review. This
  decision does not adopt its replacement of compliance or its new trigger.

The requested Vellum/Servo/Jig composition introduces a concrete consumer:
Vellum grounds and obtains approval for the design input; Servo observes the
implementation and owns deterministic/mixed evaluation policy and results;
Jig attests delivery evidence. A policy can require individual conditions
alongside an aggregate score. A high composite with a failed required
condition, or an old run with an unchanged eval definition but a different app
build, must not earn completion. A deterministic design component can succeed
while the installed overall policy fails its quality requirement; that component
pass must not clear Jig's design-review attestation.

The first integration target is an explicitly limited, self-contained web-app
fixture using Vellum's card design and planted failures. Claude Design is the
first design source; Figma is deferred, not a prerequisite. This fixture is
not evidence of broad real-world design-oracle quality.

**Sibling proposals reported by the coordinator, not accepted contracts:**
Servo ADR-0044 and specs 035/036 on `servo-required-design-evidence` own required
constraint composition and the output envelope. Vellum ADR-0011/spec 013 on
`vellum-oracle-contract` own the approved input contract. These reported draft
references and their alignment are not independently verified here. The
coordinator's framing review identifies Servo 036's design-evidence-envelope
v1 `pass` as component success, whereas Servo 035's installed overall gate
also requires quality. The follow-on spec keeps those authorities and version
namespaces distinct; no sibling implementation is claimed.

## Decision Options Considered

### Option A: Keep composite-at-least-threshold as the sufficient verdict
- **Pros:** preserves the current narrow review instructions.
- **Cons:** cannot express a producer's mandatory-condition policy; freshness
  of an eval definition alone does not bind the verdict to the delivered app.

### Option B: Make Jig run or independently reconstruct the mixed evaluator
- **Pros:** Jig could produce its own measurements.
- **Cons:** duplicates Servo's role and policy, violates the attest-only rail,
  and risks a second scoring implementation disagreeing with the producer.

### Option C: Attest the installed overall gate verdict and delivery binding (recommended)
- **Pros:** required failures remain failures; freshness includes the delivered
  build; reuses the existing design-review pass and independent reviews.
- **Cons:** requires an aligned producer-owned evidence contract and accessible
  identity records. Some old records cannot meet the stronger evidence bar.

### Option D: Introduce a universal oracle runtime and a new completion gate
- **Pros:** could generalize future integrations.
- **Cons:** activates the parked ADR-0022 boundary without that demand, adds
  coupling and a new gate for a consumer already served by spec 071.

## Recommended Decision

**Propose Option C, implemented by
[spec 119](../specs/119-mixed-design-evidence-attestation/spec.md).**

1. **Keep the rail.** `design_review` remains opt-in; record at the existing
   `reviews/slice-NN-design-review.md` path and revalidate through the existing
   REVIEWED/DONE evidence checks. Compliance, craft, conditional specialist
   reviews, and reconciliation keep their own jobs. No evaluator invocation,
   runtime import, automatic Servo discovery, new pass, or new lifecycle state.
2. **Use the installed overall gate's approved policy verdict.**
   For rich evidence, attestation is `pass` only when all of these hold:
   the installed overall gate identity, effective policy and pinned gate-payload
   contract are supported and readable; an identifiable run actually completed
   without required evidence errors; it binds to the currently
   approved source/target and frozen effective policy/config; it binds to the
   evaluated and currently delivered implementation; the preserved overall
   gate-payload explicitly says its installed policy passed, including quality;
   and every condition required by that pinned policy is present with a
   conclusive pass outcome. Referenced design component evidence is subordinate
   support bound to that gate run by run identity and content digest. Its `pass`
   never substitutes for the overall verdict. A component pass with overall
   quality failure is non-clearing. Missing, unknown, inconclusive, not-run,
   environment-error, stale, or contradictory records are non-passing. An
   overall pass contradicting preserved required or quality failure is
   inconsistent evidence, not permission for Jig to recompute the result.
3. **Keep ownership and version namespaces explicit.** Servo owns the overall
   gate-payload, design component envelope and evaluation policy semantics;
   Vellum owns source/target provenance and approval semantics. Jig records
   the run reference, external contract
   revision, identity comparisons, required-outcome references, producer
   overall verdict, subordinate evidence digest, and attestation reason.
   Vellum input-contract revision, Servo design-evidence-envelope version,
   overall gate-payload version and design-eval configuration version (when
   used) are separately pinned and checked in their own namespaces. Reported
   component-envelope v1 is not legacy gate-payload v1, and gate-payload v2
   does not imply input/envelope/design-eval v2. This is a consumer requirement,
   not a competing producer schema. Exact keys, supported version combinations
   and canonicalization rules remain assumptions until sibling alignment.
4. **Validate three distinct bindings.** Compare source snapshot and approved
   target identity; effective evaluator policy/config identity; and app
   source revision plus dirty-input identity, build inputs/config/assets and
   evaluated/served build identity against the current delivery. Use
   producer/build-owner defined, content-addressed input manifests; a Git SHA
   alone, a URL, a timestamp, or comparison only to the run's own manifest is
   insufficient. The current expected delivery must be independently
   identified from the project/build-owner's delivery inputs, not copied from
   the eval result. Fail closed when the necessary comparison cannot be made.
5. **Do not let a recorded pass outlive that binding.** Extend only the
   existing design-review evidence validation to compare the attestation's
   recorded references/digests with the current declared delivery and
   preserved run evidence at REVIEWED and DONE. Reading identities and
   hashing referenced bytes is not rerunning or rescoring the evaluator.
   A changed app with an unchanged eval definition invalidates reuse.
   Request a new producer run and a fresh independent attestation. Identical
   application input/build identities may survive a documentation-only
   commit; do not treat the containing repository's HEAD as the build.
6. **Compatibility is bounded, not silent downgrade.** Preserve unflagged
   slices and historical evidence. New attestations of an explicitly pinned
   legacy threshold-only contract may use its original higher-is-better
   composite/own-threshold rule, provided execution and all source/config/build
   bindings are evidenced. The selected verdict must be authoritative for
   that installed threshold-only policy, not one component of a larger gate.
   Legacy evidence without those bindings needs renewed producer evidence;
   never fabricate provenance. A contract requiring
   rich outcomes cannot fall back to scalar comparison because fields are
   missing. This is one review procedure consuming explicit external contract
   variants, not a new Jig compatibility layer or dual conventions.
   This cost is an explicit owner decision before acceptance: newly requested
   legacy attestations can be refused until provenance is renewed. Do not
   migrate historical/default behavior or relax rich requirements silently.
7. **Bound the trust claim.** Digests detect accidental mismatch and replay
   against the compared inputs, not honest producer execution by themselves.
   Unsigned local manifests and verdicts can be altered together; Jig's
   bypassable review mechanism is not forgery-proof or a hostile-agent
   security boundary. Signing, remote witnessing, trusted CI and merge
   authority separation are separate governance work, not smuggled into this
   consumer update.

## Consequences

**Becomes easier:**
- A developer can see why completion was denied: required failure, absent
  evidence, wrong target/policy, or different delivered implementation.
- Mixed deterministic and judgment-based evidence uses the same attest-only
  rail without converting a judge's opinion into Jig-generated measurements.

**Becomes harder:**
- Producers must preserve traceable results and build/source/config identities.
  Legacy runs without that provenance cannot support a new passing attestation.
- C0 contract/identity alignment is an entry checkpoint, not a demand for an
  already completed cross-repo integration or runnable consumer code. C1 is
  Vellum's source/input preparation while 013-01 remains IN_PROGRESS, not
  driven-state handoff completion. Genuine frozen overall gate and
  subordinate evaluator evidence is produced and checked during implementation
  under acceptance criteria and Definition of Done; handcrafted passing
  examples alone do not suffice.

## Assumptions

- **A1 — proposed producer capability:** Servo's installed overall gate will
  preserve an authoritative gate-payload verdict, required-condition outcomes,
  quality result and run/digest-bound subordinate design evidence sufficient
  for the consumer predicate. The reported overall gate-payload candidate is
  opt-in schema v2 with evaluation status
  `pass/fail/env_error`, `required_status: pass/fail/unknown`, typed reasons and
  separate raw observations. An observed required absence/contradiction is
  fail; unavailable/stale/unbound/unsupported evidence is unknown/env_error.
  Jig maps either to a non-clearing attestation, not a new evaluator outcome.
  Reported design-evidence-envelope v1 has its own component-success semantics;
  design-eval and Vellum input versions are separate. Names, supported
  combinations and binding keys are pending reconciliation, not accepted or
  source-verified here; parent coordinates the sibling proposal.
- **A2 — proposed provenance:** Vellum and the pilot build owner will supply
  an approved source/target snapshot and a content-addressed delivery-input
  manifest with a credible link to the actually observed/served build.
  Input serialization, version/digest domains, test vectors, required matrix,
  current/served/delivered-build closure predicates and approval rules are
  defined at shared checkpoint C0; genuine binding proof is a later
  implementation acceptance requirement, not a circular readiness prerequisite.
- **A3 — bounded deployment:** the initial trust setting permits reading these
  local preserved artifacts. Their authenticity is an assumption, not a
  property established by hashes or a read-only reviewer.

## Kill criteria

- If the agreed contracts cannot distinguish missing evidence from failure/pass
  or define evaluated-build binding, resolve that contract gap at C0 before
  readiness; do not substitute Jig scoring or guessed identities. Missing
  runtime proof is implementation AC/DoD work, not evidence that C0 needs an
  already-built consumer.
- If the consumer needs imports, subprocess evaluation, a global oracle
  registry or a new gate to work, re-scope and obtain a separate decision
  rather than accidentally unpark ADR-0022.
- If hostile-record resistance is a prerequisite, this local attestation
  design alone is insufficient; separate trusted-production governance first.

## Open questions

1. Which exact input/envelope/gate-payload/design-eval revisions and supported
   combinations are approved, including the installed overall verdict authority,
   subordinate run/digest binding and inconsistent-record handling?
2. Which Vellum approval artifact and source/target digests are authoritative,
   and how are superseded approvals distinguished?
3. Which build-owner manifest covers dirty source, dependencies, assets and
   effective runtime/build config, and proves the served build was evaluated?
4. Which genuine legacy producer sample supports the bounded compatibility
   path? If none has delivery binding, require renewed evidence, not a waiver.
   Will the owner accept that intentional cost for newly requested legacy
   attestations, without a surprise migration of historical/default behavior?
