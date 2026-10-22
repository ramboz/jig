---
status: Accepted
dependencies: []
last_verified: 2026-10-22
frame_review: true
---

# ADR-0066: Component-agnostic design attestation

## Status

Accepted (2026-10-22)

## Context

Jig needs reusable design attestation without shipping an application's proof
of concept. The owner explicitly selected retirement of the unmerged pilot
interfaces and clean product-only replacements on 2026-10-22.

The original effort union at `43fcc30216cafc8caa8ee01b1688d6f86dff2666`
contains reusable strict reading and static result checks
(`skills/_common/design_bindings.py:133–274`,
`static_design_bindings.py:282–854`), wired into the existing review recorder,
checker and lifecycle validator (`review_evidence.py:523–529,586–595`).
It also accepts the pilot's `vellum-design-input/0.1-pilot` protocol
(`design_bindings.py:14–28,292–340`). The clean main base does not contain
that unmerged runtime or its ADR-0065/spec 119 records. This decision is new
prospective scope; none of those historical records is amended.

Plain-language outcome: external tools keep measuring and deciding whether
the whole policy passed. Jig checks their preserved verdict and whether the
approved source, runtime and delivered build still match. This is reusable
across components within one finite supported profile, not a universal
evidence adapter.

## Decision Options Considered

### Option A: Keep pilot compatibility in the product
- **Pros:** Old selections could still be reused.
- **Cons:** Ships a bespoke public validator and live preparation lane;
  contradicts the owner's explicit retirement decision.

### Option B: Bounded generic static readback on the existing rail
- **Pros:** Component facts are data; native authority, strict identities and
  independent current delivery remain enforceable without a new evaluator.
- **Cons:** Unsupported producers/build recipes refuse; retiring selections
  requires new producer evidence and independent attestation.

### Option C: General provider registry or query language
- **Pros:** Could accommodate more unrelated evidence shapes.
- **Cons:** Speculative execution/semantic surface and extra architecture with
  no current caller; exceeds this owner-directed replacement.

## Recommended Decision

Choose B. Keep the existing design-review pass and record/check/lifecycle
integration. A selected `jig/static-design-freshness/1` supports the existing
`vellum-confirmed-source/0.2`, `static-css-subset/1`,
`static-source-contract-app/1` and native `gate_result/2` meanings.
Separately pinned producer namespaces never select one another.

The native overall verdict is authority, including required-condition and
quality policy when that supported profile declares it. Missing, FAIL,
UNKNOWN, stale, contradictory or unbound evidence cannot clear. Component
scores never replace overall authority. Raw hashes, complete inventories,
independent approval/current build/delivery, live original source freshness,
runtime closure, run IDs, acquisition nonces and served-response links remain
required. Jig reads/hashes evidence; it does not import/call producers,
evaluate the interface or recompute scores. Live original-root Git identity
uses a fixed local HEAD metadata probe with no shell, user-supplied argv,
network or writes. Inherited Git repository/worktree/config redirection is
removed. A non-Git root has explicit null identity; probe execution failures
are errors, not null success. This bounded metadata subprocess is not a
claim of filesystem-only validation.

Retire `jig/design-freshness/1` and `vellum-design-input/0.1-pilot` selections
with actionable renewal/refusal, never automatic migration, schema aliasing
or scalar downgrade. Unselected pre-existing scalar design-review and
unflagged slices keep their behavior. Old frozen epochs remain historical,
not newly approved epochs for extracted runtime bytes.

Vellum's source primitives move to `design_input.py`; Servo's static observer
uses `evidence_io.py` / `evidence_runtime.py`. Jig validates actual selected
runtime files rather than pinning old card helpers or assigning approval to
renamed code. Component IDs, roles, goals, environment and resources stay
input data. Restricting the supported producer/profile is deliberate; no
arbitrary-provider/build framework, registry, query language, new pass or
lifecycle is introduced.

## Consequences

**Becomes easier:**
- Reuse across different non-card interfaces without shipping their fixtures.
- Audit current approval, runtime and delivery on the same review rail.

**Becomes harder:**
- Old pilot selections must renew evidence, not relabel approvals.
- A genuinely different producer meaning requires an explicit future decision.

## Assumptions

None. The decision constrains future implementation; it does not claim that
the extracted runtime has already been independently approved for a real app.

## Kill criteria

If extracting the generic helpers changes producer semantics rather than
runtime identity alone, stop and obtain a new explicit contract/approval
decision before changing wire-version meanings.

## Open questions

None about scope. Successor runtime inventory is supplied by its producer
before coupling changes; it must not be guessed or replaced with old tooling.
