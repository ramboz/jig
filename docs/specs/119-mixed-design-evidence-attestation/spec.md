---
status: IN_PROGRESS
skill: spec-workflow
use_cases: [UC-4, UC-7, UC-20]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 119: Mixed design-evidence attestation

> Follow-on to DONE specs [071](../071-design-review-pass/spec.md) and
> [104](../104-design-fidelity-routing/spec.md), proposing
> [ADR-0065](../../decisions/adr-0065-attest-external-policy-verdict-delivered-revision.md).
> Implementation checkpoint: ADR-0065/C0 are accepted; 119-01 passed
> independent framing and spec-readiness reviews. See [plan.md](plan.md).
> 119-02/03 remain DRAFT. Completion still requires genuine current evidence.
>
> Allocated on 2026-10-14 by installed `workflow.py new --no-push`.
> Number 119 is provisional on this proposal branch because main requires a PR.

## Overview

A developer opting into `design_review` should be able to complete a slice from
fresh, externally produced design evidence, and should get a clear refusal
when a required condition failed or the evidence belongs to a different app.
Jig will attest the installed producer gate's overall policy verdict and
recorded bindings rather than infer mixed-policy success from an average
score or a successful design component.

The main tradeoff is evidence discipline: runs need a link to the approved
design input, frozen policy/config and actual delivered implementation.
Legacy records missing that provenance need renewed evidence. Jig does not
run the evaluator, invent thresholds, measure the UI, or replace independent
compliance review.

### Current state (verified 2026-10-14)

Source anchor: main `e3fb1283a75131e4bc80e3aaf0bd019389d5a3df`, fetched before
authoring; HEAD and origin/main agreed at that point.

| Surface | Bounded observation |
|---------|---------------------|
| [`review.py:1437-1530`](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/independent-review/review.py#L1437-L1530) | The design-review prompt asks whether an external non-deterministic eval ran, its frozen config/threshold is unchanged, and its composite meets its own threshold. |
| [`review_evidence.py:255-295`](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/_common/review_evidence.py#L255-L295) | The optional design-review pass joins compliance/craft at REVIEWED and is part of DONE revalidation. |
| [`review_evidence.py:519-587`](https://github.com/ramboz/jig/blob/e3fb1283a75131e4bc80e3aaf0bd019389d5a3df/skills/_common/review_evidence.py#L519-L587) | The validator reads verdict shape/status and review-back-edge freshness; this function does not compare evaluated build identity with delivery. |
| [ADR-0049](../../decisions/adr-0049-design-fidelity-routing-to-originating-spec.md), [spec 104](../104-design-fidelity-routing/spec.md) | Visual fidelity remains spec-shaped work; the hard fidelity rail is graduated/opt-in. |

These claims come from reading the named function bodies and complete owning
criteria blocks. They do not assert cross-repo capabilities are already built.
The bug board was read before drafting; this proposal introduces a richer
evidence consumer, not a second owner for a reported tracked defect.

### Ownership and non-goals

Vellum owns grounding, source snapshots and approval of the design-input
contract. Servo owns implementation observation, evaluation policy, required
conditions, scoring/judgment, the installed overall gate-payload and subordinate
design component envelope. Jig owns independent
delivery review and attestation. Interface labels below describe semantic
requirements, not proposed JSON keys or a second producer schema.

No new lifecycle state, review pass, default design gate, generic oracle
registry, Servo runtime dependency or reviewer rerun/rescore is proposed.
ADR-0022's broader binding stays PARKED. ADR-0059's proposed
contract-completeness/reward-hacking pass remains orthogonal; this spec does
not adopt its claim that the oracle replaces compliance. General staleness
checks for other review passes, record signing and hostile-agent enforcement
are outside this spec. Closed records and `docs/conventions.md` stay untouched.

### Revised attestation predicate

For an explicitly selected, supported installed overall gate policy:

```text
attest_pass =
  readable_supported_pinned_installed_gate_and_contracts
  AND identified_completed_honest_run
  AND approved_source_and_target_match
  AND frozen_effective_policy_and_config_match
  AND evaluated_implementation_equals_current_delivery
  AND installed_overall_gate_payload_policy_verdict_is_pass
  AND subordinate_design_evidence_matches_gate_run_and_content_digest
  AND every_policy_required_condition_is_present_and_conclusive_pass
  AND preserved_records_are_consistent
```

**Verdict authority is the installed overall gate-payload under its pinned
effective policy**, including required evidence and quality. Servo 036's
design-evidence-envelope `pass` says the deterministic design component
succeeded; it does not assert Servo 035's overall gate passed. The component
evidence is subordinate support, referenced by run identity and content digest
from the preserved overall gate record. Matching a component's bytes to a
different gate run, or promoting its success to the overall verdict, is
non-clearing. A genuine run where the deterministic component passes but the
quality result fails must leave completion blocked.

The required inventory comes from the pinned installed producer policy, not from
whichever rows happen to appear in a result. Unknown outcomes, required
not-run/inconclusive/environment-error, missing rows, mismatched identities,
unsupported versions or an overall policy-pass contradicting a required or
quality failure
cannot clear. Composite and threshold can be quoted as supporting evidence;
they are not a sufficient rich-policy predicate. Optional outcomes remain
governed by the producer's policy, not a new Jig veto.

Pin each version namespace separately; neither a bare "v1/v2" label nor missing
fields selects a contract:

| Namespace | Owner and authority | Reported proposal, not an accepted interface |
|-----------|---------------------|---------------------------------------------|
| Approved design-input contract | Vellum; source facts, approval, constraints and mapping | Revision to align under Vellum 013. |
| Design-evidence-envelope | Servo 036; deterministic component observations/outcome | Component envelope v1; `pass` means this component succeeded. |
| Installed overall gate-payload | Servo 035; authoritative installed-policy verdict including quality | Opt-in schema v2 proposed; default gate-payload v1/exit 0/1/2 retained. |
| Design-eval configuration, when used | Servo design-eval; frozen quality/judge definition | Pin its own supported configuration revision independently. |

Shared checkpoint C0 sets supported combinations and run/digest references,
not a competing Jig producer schema. The reviewer reads the
preserved overall result; it does not invoke an installed gate or recompute
its quality/required-condition combination.

The reviewer reads preserved artifacts and records its references, reasons
and identity comparisons at the existing design-review verdict path. At
REVIEWED and DONE, the existing design-review evidence validation checks reuse
against the current declared delivery and preserved evidence identities.
It may read/hash artifacts; it must not execute the evaluator or derive its
score. Changes require new producer evidence and a fresh independent
attestation, not a new lifecycle gate.

### Identity and trust requirements

The producer/build-owner defines exact input serialization, namespaced versions,
digest domains/test vectors, explicit required matrix and canonical
current/served/delivered-build closure predicates at shared contract checkpoint
C0. Genuine proof that the
observer evaluated the served build is required during implementation, not
assumed from that definition or demanded before the integration can start.
Jig must explicitly validate all three comparisons:

| Binding | Required comparison |
|---------|---------------------|
| Approved design | Vellum source snapshot, approved target/contract revision and content identity in the run versus the currently approved target reference. |
| Eval definition | Installed overall gate/effective policy and separately pinned input/envelope/gate-payload/design-eval revisions in the run versus the approved configuration, including required inventory, threshold/aggregation rules and judge settings when applicable. |
| Implementation/delivery | Run's source revision and dirty-input digest, effective build/runtime inputs/config/assets/dependencies and evaluated/served build identity versus the current build-owner delivery record and referenced bytes. |

The current delivery reference must be independent of the result being
attested: comparing a result only to its own run manifest is circular.
A Git commit does not identify uncommitted inputs or prove what a server
served; a URL or timestamp is not a build identity. A documentation-only
commit can preserve the application identities when the declared input
closure supports that conclusion. Unknown input closure, inaccessible
artifacts or no credible served-build binding leaves the requirement unmet.

Preserve the overall gate run ID, separately named contract revisions,
subordinate design evidence run/digest references, referenced paths/digests
and comparison results in the attestation. Exact evidence-record encoding is
aligned with the producer before implementation, within existing review
artifact conventions rather than new slice frontmatter fields.

Local unsigned evidence is not forgery-proof: matching hashes do not establish
honest execution when an actor can rewrite both artifacts and claims. This
proposal addresses consistency/staleness in the initial trusted-local pilot,
not signatures, server-side verification or malicious-author isolation.

### Compatibility

Unflagged slices retain their current behavior. Existing closed evidence is
historical and is not rewritten. New attestations use one procedure with an
explicit pinned external contract variant:

- A rich/mixed contract requires the full predicate; absent rich fields never
  select a scalar fallback.
- An explicitly legacy, threshold-only policy retains its original
  higher-is-better composite/own-threshold semantics plus honest execution
  and the same source/config/build binding. Its selected verdict is authoritative
  for the installed threshold-only policy, not a component of a larger gate.
  Component-envelope v1 alone is not evidence of legacy gate-payload v1.
  It cannot discharge a slice that
  requires richer mandatory outcomes. Old evidence lacking binding is
  non-clearing for a new delivery until the producer renews it.
- Unsupported/ambiguous contract identity and contradictory records are
  non-clearing with an actionable reason. No automatic migration or Jig-owned
  producer-format adapter is assumed.

**Intentional compatibility cost for owner decision:** newly requested legacy
attestations need appropriate delivery provenance and may require renewed
producer evidence. Historical/unflagged behavior stays untouched, with no
default migration. The owner must accept this cost before ADR acceptance;
absence of provenance must not silently weaken a rich-required contract.

### Cross-repo prerequisites and pilot boundary

The table records proposal-era ownership, with draft-owner labels retained
as historical references. Accepted C0 and the published, independently read
C1/producer contract pins are now in [plan.md](plan.md); only the genuine
final-current proof obligations remain outstanding for 119-01.

| Owner | Shared checkpoint / implementation responsibility | Reported draft owner |
|-------|---------------------------------------------------|----------------------|
| Vellum (`PinkException/vellum`) | C1 in 013-01 IN_PROGRESS prepares approved normal/open source captures/inputs and mapping; it unblocks downstream observer/consumer use without claiming driven-state handoff DONE or 013-02 completion. | ADR-0011 and [spec 013](https://github.com/PinkException/vellum/blob/vellum-oracle-contract/docs/specs/013-design-to-oracle-handoff/spec.md). |
| Servo (`ramboz/servo`) | 035-01 standalone overall policy first; 036-01 then implements observation and proves served-build binding against C1 input. Pin distinct gate/envelope/config revisions at C0. | ADR-0044, [composition spec 035](https://github.com/ramboz/servo/blob/servo-required-design-evidence/docs/specs/035-required-evidence-alongside-quality-scores/spec.md) and [envelope spec 036](https://github.com/ramboz/servo/blob/servo-required-design-evidence/docs/specs/036-deterministic-design-evidence/spec.md). |
| Pilot/build owner (parent-coordinated) | Define current/served/delivered-build input closure predicates and independent delivery reference at C0; execute genuine baseline/failure, substitution/replay and binding scenarios during implementation. | Small self-contained fixture planned; no real-world app supplied. |
| Jig | ADR acceptance/readiness authority and C0 authority/identity contracts precede implementation; genuine producer-backed completion/refusal proof is in each slice's AC/DoD, using C1 inputs. | Accepted ADR-0065/C0; 119-01 passed separate readiness and is IN_PROGRESS. 119-02/03 remain DRAFT. |

At proposal authoring, sibling links were coordinator-reported draft references,
not independent verification of publication or alignment. The implementation
checkpoint now pins the actual published references separately. The proposed
acyclic start order is **Servo 035-01 standalone -> Vellum 013-01 IN_PROGRESS
C1 source/input checkpoint -> Servo 036-01 real observer/served-build proof ->
Jig 119-01/02 attestation -> Vellum 013-01 closes and 013-02 state integration**.
These are named coordination checkpoints, not dependencies on entire sibling
specs being DONE. **C0** means accepted/aligned decisions, exact input
serialization/version/digest domains/test vectors, explicit required matrix
and served/current/delivered-build closure predicates, with no demand for
runnable consumer code. The owner's accepted ADR/C0 grant now approves the
bounded pilot choices, not future completion evidence. Runtime scenarios,
substitution/replay proof and genuine
frozen captures are produced and verified during the owning implementation
AC/DoD, not a demand for finished integration before starting. C1's preparation
of an open-state source capture is not 013-02's driven-state integration.
This order remains parent-coordinated.

The shared fixture starts from the requested 240px card, 44px dark band, 20px
title, 12px subtitle and state-change control. These are proposed pilot goals,
not approved constraints or new Jig UI requirements. Vellum must distinguish
source facts, owner-approved constraints, residual intent/coverage and confirmed
app mapping, and approve the precise goals and normal/open-state captures before
Servo evaluates. The coordinator reports the old `card.render.png` is a solid
240x140 dimension-test image, not a design reference; an open-state reference
is still to be captured. Do not elevate that old PNG, its frame height or old
typography metadata into canonical targets.

Use planted visual, required-condition, state and stale-build failures.
Preserve results from the actual producer commands, not just handwritten
envelope fixtures. Mutation fixtures may supplement genuine captures for
malformed/version/consistency rejection and must be labelled. No real-world
oracle accuracy is claimed from this fixture. Figma is deferred and is not a
DoR prerequisite.

**Reported Servo vocabulary (assumption pending alignment):** proposed opt-in
overall gate-payload schema v2 separates policy from its subordinate
design-evidence-envelope v1/raw observations, uses overall evaluation status
`pass/fail/env_error`, required status `pass/fail/unknown`, typed reasons, and
retains default v1 and exit-code 0/1/2 behavior. An observed missing required
`#title`/contradiction is required fail with evaluation fail/exit 1; absent,
stale, unbound or unsupported evidence is required unknown with environment
error/exit 2. Complete bound required passes are necessary but not sufficient:
the installed overall gate must also meet its quality policy. A deterministic
component pass alone cannot clear. Jig reads the preserved overall gate-payload
and run/digest-linked component evidence rather than exit codes from a live
invocation; both
negative classes map to a non-clearing review verdict with their distinct
producer reasons retained. These are not new Jig schema definitions.

## Assumptions

- **A1:** The evolving installed Servo gate-payload can express the authoritative
  overall verdict and link complete subordinate evidence without Jig
  reconstructing evaluation policy. Parent must align separately named
  input/envelope/gate-payload/design-eval versions and replace reported
  branch links with published immutable proposal references before readiness.
- **A2:** Vellum and the pilot build owner can provide the independently
  comparable design approval and application source/config/served-build
  identities. Input closure and canonicalization remain unverified here.
- **A3:** Trusted-local frozen artifacts are sufficient for the pilot's threat
  model; they cannot prove authenticity against an actor controlling all files.
- **A4:** A documented legacy producer path can provide renewed delivery-bound
  evidence without a new Jig compatibility shim. Confirm with a genuine sample;
  otherwise that path remains non-clearing, not waived.

## Decomposition

**SPIDR ([vertical-slice splitting](../../memory/glossary.md)) by Rules, Path,
then Data.** No Spike: unknown interfaces are explicit prerequisites, not a
research phase disguised as a deliverable.

1. **Rules (119-01):** a developer can record a genuine rich-policy pass and
   see a high-composite required failure, component-pass/quality-fail control
   or inconclusive evidence refused on the existing review/completion rail.
2. **Path (119-02):** a previously valid pass cannot complete a changed app;
   freshness checks and renewed evidence work through final completion.
3. **Data (119-03):** a developer can finish with supported legacy
   threshold-only evidence or get a precise upgrade/provenance refusal;
   unflagged projects retain their ordinary workflow.

Each slice includes consumption, recorded verdict, observable lifecycle result,
documentation and a producer-backed scenario, not a parser-only phase.

## Slices

- [119-01 — attest-rich-policy](slice-01-attest-rich-policy.md)
- [119-02 — reject-stale-delivery](slice-02-reject-stale-delivery.md)
- [119-03 — legacy-and-opt-in](slice-03-legacy-and-opt-in.md)

## Historical authoring review and implementation stop

The paragraph below records the proposal-era stop. The accepted ADR and
2026-10-15 [implementation checkpoint](plan.md) now govern 119-01 readiness;
this does not credit its unexecuted acceptance scenarios.

All slices stay DRAFT; no DoD item is represented as complete. Independent
frame-critique evidence belongs in `reviews/` and the ADR's sibling review
directory. A passing framing verdict is not acceptance or implementation
readiness. Before readiness, resolve installed overall verdict authority,
version namespaces and identity closure/encoding at C0 and obtain later-phase
ADR/readiness authority. C1 supplies approved source inputs without requiring
013-01 DONE. Genuine overall
gate/component captures and binding proof are implementation AC/DoD work,
not a requirement that the whole integration already be complete.
