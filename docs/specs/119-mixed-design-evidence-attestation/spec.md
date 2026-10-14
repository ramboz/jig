---
status: DRAFT
skill: spec-workflow
use_cases: [UC-4, UC-7, UC-20]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 119: Mixed design-evidence attestation

> Follow-on to DONE specs [071](../071-design-review-pass/spec.md) and
> [104](../104-design-fidelity-routing/spec.md), proposing
> [ADR-0065](../../decisions/adr-0065-attest-external-policy-verdict-delivered-revision.md).
> DRAFT only: source implementation has not started.
>
> Allocated on 2026-10-14 by installed `workflow.py new --no-push`.
> Number 119 is provisional on this proposal branch because main requires a PR.

## Overview

A developer opting into `design_review` should be able to complete a slice from
fresh, externally produced design evidence, and should get a clear refusal
when a required condition failed or the evidence belongs to a different app.
Jig will attest the producer's policy verdict and recorded bindings rather
than infer mixed-policy success from an average score.

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
conditions, scoring/judgment and the result envelope. Jig owns independent
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

For an explicitly selected, supported rich producer contract:

```text
attest_pass =
  readable_supported_pinned_contract
  AND identified_completed_honest_run
  AND approved_source_and_target_match
  AND frozen_effective_policy_and_config_match
  AND evaluated_implementation_equals_current_delivery
  AND explicit_producer_policy_verdict_is_pass
  AND every_policy_required_condition_is_present_and_conclusive_pass
  AND preserved_records_are_consistent
```

The required inventory comes from the pinned producer policy, not from
whichever rows happen to appear in a result. Unknown outcomes, required
not-run/inconclusive/environment-error, missing rows, mismatched identities,
unsupported versions or a policy-pass contradicting a required failure
cannot clear. Composite and threshold can be quoted as supporting evidence;
they are not a sufficient rich-policy predicate. Optional outcomes remain
governed by the producer's policy, not a new Jig veto.

The reviewer reads preserved artifacts and records its references, reasons
and identity comparisons at the existing design-review verdict path. At
REVIEWED and DONE, the existing design-review evidence validation checks reuse
against the current declared delivery and preserved evidence identities.
It may read/hash artifacts; it must not execute the evaluator or derive its
score. Changes require new producer evidence and a fresh independent
attestation, not a new lifecycle gate.

### Identity and trust requirements

The producer/build-owner must define canonical input closure and digest rules.
Jig must explicitly validate all three comparisons:

| Binding | Required comparison |
|---------|---------------------|
| Approved design | Vellum source snapshot, approved target/contract revision and content identity in the run versus the currently approved target reference. |
| Eval definition | Run's effective policy/config identity versus the frozen approved policy/config, including required inventory, threshold/aggregation rules and judge settings when applicable. |
| Implementation/delivery | Run's source revision and dirty-input digest, effective build/runtime inputs/config/assets/dependencies and evaluated/served build identity versus the current build-owner delivery record and referenced bytes. |

The current delivery reference must be independent of the result being
attested: comparing a result only to its own run manifest is circular.
A Git commit does not identify uncommitted inputs or prove what a server
served; a URL or timestamp is not a build identity. A documentation-only
commit can preserve the application identities when the declared input
closure supports that conclusion. Unknown input closure, inaccessible
artifacts or no credible served-build binding leaves the requirement unmet.

Preserve the run ID, producer contract revision, referenced paths/digests and
comparison results in the attestation. Exact evidence-record encoding is
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
  and the same source/config/build binding. It cannot discharge a slice that
  requires richer mandatory outcomes. Old evidence lacking binding is
  non-clearing for a new delivery until the producer renews it.
- Unsupported/ambiguous contract identity and contradictory records are
  non-clearing with an actionable reason. No automatic migration or Jig-owned
  producer-format adapter is assumed.

### Cross-repo prerequisites and pilot boundary

| Owner | Prerequisite before implementation readiness | Present status |
|-------|---------------------------------------------|----------------|
| Vellum (`PinkException/vellum`) | Approved Claude Design-first source/target contract, immutable snapshot and approval reference; any identifier mapping owned there. | Coordinator reports ADR-0011 and [spec 013](https://github.com/PinkException/vellum/blob/vellum-oracle-contract/docs/specs/013-design-to-oracle-handoff/spec.md); branch publication pending, link prospective. |
| Servo (`ramboz/servo`) | Pinned mixed/deterministic result-envelope version with explicit policy verdict, required outcomes and honest execution/build binding; preservation and genuine evaluator commands. | Coordinator reports ADR-0044, [composition spec 035](https://github.com/ramboz/servo/blob/servo-required-design-evidence/docs/specs/035-required-evidence-alongside-quality-scores/spec.md) and [envelope spec 036](https://github.com/ramboz/servo/blob/servo-required-design-evidence/docs/specs/036-deterministic-design-evidence/spec.md); publication pending, links prospective. |
| Pilot/build owner (parent-coordinated) | Small app, build-input closure, independent delivery identity and genuine frozen baseline/failure captures. | Planned, not executed; no real-world app supplied. |
| Jig | ADR-0065 accepted in a later authorized phase; framing/readiness review and all external prerequisites satisfied. | This turn remains Proposed/DRAFT. |

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
output v2 separates raw observations from policy, uses evaluation status
`pass/fail/env_error`, required status `pass/fail/unknown`, typed reasons, and
retains default v1 and exit-code 0/1/2 behavior. An observed missing required
`#title`/contradiction is required fail with evaluation fail/exit 1; absent,
stale, unbound or unsupported evidence is required unknown with environment
error/exit 2. Only complete bound required passes can permit evaluation pass.
Jig reads these records rather than exit codes from a live invocation; both
negative classes map to a non-clearing review verdict with their distinct
producer reasons retained. These are not new Jig schema definitions.

## Assumptions

- **A1:** The evolving Servo producer envelope can express the predicate and
  complete required inventory without Jig reconstructing evaluation policy.
  Parent must align the reported vocabulary/versioning and replace prospective
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
   see a high-composite required failure or inconclusive evidence refused on
   the existing review/completion rail.
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

## Authoring review and implementation stop

All slices stay DRAFT; no DoD item is represented as complete. Independent
frame-critique evidence belongs in `reviews/` and the ADR's sibling review
directory. A passing framing verdict is not acceptance or implementation
readiness. Before any readiness transition, resolve the cross-repo contracts,
publish genuine preserved evaluator samples, settle the identity comparison
encoding and obtain the later-phase ADR/readiness authority.
