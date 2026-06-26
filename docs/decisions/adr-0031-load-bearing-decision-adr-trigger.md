---
status: Accepted
dependencies: []
last_verified: 2026-06-26
frame_review: true
---

# ADR-0031: Load-bearing-decision ADR trigger, single-sourced

## Status

Accepted (2026-06-26)

## Context

[Spec 083](../specs/083-lightweight-decision-records/spec.md) (Phase 2) captures
decisions settled mid-session. Its frame-critique surfaced a structural gap: a
**lexical scan** (slice 083-04) is biased to catch *lightweight* decisions and
miss *load-bearing* ones — the more load-bearing a decision, the less likely it
carries a stock trigger phrase. So the load-bearing case cannot be owned by the
scan; it is owned by **judgment prompts** at the two session-end surfaces that
exist: **reconciliation** (in-spec slices) and **session-end memory-sync**
(out-of-spec work, which has no reconciliation phase).

Two slices then need the *same* trigger wording:

- **083-05** — the routing rubric's ADR-branch criterion (where a triaged
  candidate lands: ADR vs lightweight record vs refinement-todo vs drop).
- **083-06** — the widened judgment clause in **both** reconcile checklists
  (`docs/workflow.md`, `skills/spec-workflow/SKILL.md`) and the memory-sync
  session-end prompt (`skills/memory-sync/SKILL.md`).

If each site phrases the trigger independently, they drift — and a drifted
trigger silently changes *when an ADR is required*, which is a load-bearing
lifecycle policy. The existing Phase-1 wording in `lightweight-decisions.md`
("ADR if it changes a module boundary, public contract, or cross-cutting
policy") under-fires for the spec's founding case: an off-spec ADR-worthy design
choice that changed **no** boundary but **does** have rejected alternatives a
future agent would undo without knowing. The trigger must widen to cover it, and
the widening must land identically in every consumer.

This is a hard-to-reverse, cross-cutting policy change (when an ADR is required)
touching four maintained sites — it warrants its own ADR, and the ADR is the
natural **single canonical source** for the trigger sentence.

## Decision Options Considered

### Option A: Each site phrases the trigger in its own words
- **Pros:** No coupling; each surface reads naturally in context.
- **Cons:** Four independent phrasings drift over time; a future edit to one
  silently diverges the ADR-required policy across surfaces with nothing to catch
  it. The frame-critique flagged this as the residual risk.

### Option B: Single canonical sentence, quoted verbatim by all four sites, drift-checked in CI
- **Pros:** One authority; every consumer quotes the *exact* string; a unit test
  asserts the string appears in all four sites, so divergence fails CI rather
  than accumulating silently. The ADR holds the canonical text.
- **Cons:** Slightly less idiomatic phrasing at each site (a quoted sentence
  inside a checklist item); requires a mechanical test and a code-level constant
  to anchor the comparison.

## Recommended Decision

**Option B.** The canonical load-bearing-decision ADR trigger is this single
sentence (the **canonical string**):

> A load-bearing design choice with rejected alternatives — one a future agent would need to know about to avoid undoing it — warrants an ADR even when it changes no module boundary or public contract.

**Single-sourcing mechanism.** The sentence is mirrored as a code constant,
`ADR_TRIGGER` in `skills/memory-sync/decisions.py` (the tier-0 helper home — see
below), which is the programmatic authority the drift test compares against. Four consumer sites quote the exact
string:

1. the **routing rubric** (ADR-branch criterion) in
   `docs/decisions/lightweight-decisions.md`;
2. the **reconciliation checklist** in `docs/workflow.md`;
3. the **reconciliation checklist** in `skills/spec-workflow/SKILL.md`;
4. the **session-end memory-sync prompt** in `skills/memory-sync/SKILL.md`.

`skills/memory-sync/test_decisions.py` asserts `ADR_TRIGGER` appears verbatim in
all four sites (and that this ADR's prose carries it), so any future drift fails
CI. This ADR's own prose is the human-readable canonical source; the constant is
its machine mirror.

**Helper home — tier-0, not tier-1.** `decisions.py` lives in the **tier-0**
`memory-sync` skill rather than alongside `adr.py` in the **tier-1**
`adr-workflow` skill, even though cohesion would favour the latter. The
always-scaffolded surfaces that reference the helper (the memory-sync prompt and
`lightweight-decisions.md`) would otherwise fail the scaffold **helper-closure**
check, which requires every referenced `${CLAUDE_PLUGIN_ROOT}/skills/.../*.py`
path to resolve in the scaffolded (default tier-0) set. A tier-1 helper
referenced from always-scaffolded tier-0 surfaces is a broken local-helper path.

The trigger is **judgment**, not lexical — it is added to the two judgment
surfaces (reconciliation + memory-sync) precisely because no regex can see a
trigger-phrase-free design choice. It widens the Phase-1 boundary/contract test
with an **escape hatch** ("a future agent would need to know about to avoid
undoing it") so it fires on the founding out-of-spec case.

### Scope of the claim — consistency, not capture (frame-critique correction)

**This ADR is a policy-*consistency* mechanism, not a capture-rate
improvement.** It guarantees that the four surfaces agree on *when an ADR is
required*; it does **not** claim that the widened wording makes an agent more
likely to *attend* to a load-bearing decision at session end. That capture
question is the spec's, and [spec 083](../specs/083-lightweight-decision-records/spec.md)
scopes it honestly: the discursive out-of-spec load-bearing decision remains
**recall-reduced-not-eliminated**, owned by the memory-sync session-end escape
hatch — an *attention* prompt, not deterministic capture. ADR-0031 changes the
*wording* of that prompt and unifies it across surfaces; it does **not** change
the attention failure mode the spec admits it cannot close (the deterministic
floor for that is 083-04's scan + 083-07's in-flight capture, not this ADR).
So the "named owner" win below is a **consistency** win — every surface now asks
the same question — not evidence that more decisions get caught.

The **drift test is deliberately lexical** (verbatim-substring presence): it
catches a *diverged copy* of the canonical sentence, which is the single failure
mode this ADR exists to prevent. It does **not** police *semantic* drift — a site
could quote the sentence verbatim yet surround it with contradicting prose, and
the test would stay green. That residual is accepted: semantic coherence of the
four surfaces is a review-time concern (the reconciliation reviewer reads the
sites), not something a string check can or should enforce.

## Consequences

**Becomes easier:**
- The ADR-required policy is stated once and enforced; the four surfaces can no
  longer disagree about when an ADR is warranted (a **consistency** guarantee).
- The spec's founding case (off-spec, ADR-worthy, no boundary change) gets a
  single, uniform owner-question at the only session-end surface it reaches
  (memory-sync) — closing a *policy* gap, not the *attention* gap (see Scope).

**Becomes harder:**
- Editing the trigger means editing the canonical sentence (here + the constant)
  and re-syncing all four quotes — by design; the drift test forces it.
- A quoted sentence inside a checklist item reads slightly less fluidly than
  bespoke prose per site, and risks being skimmed as boilerplate; the
  reconciliation reviewer is the backstop for "quoted but ignored."

## Assumptions

- **Load-bearing, and explicitly NOT claimed here: that the widened judgment
  prompt lifts capture rate over the Phase-1 nudge.** This ADR does not rest on
  it — its scope is policy *consistency* (see Scope above), which holds
  independent of capture efficacy. The capture-efficacy question is unevidenced
  (no replay of the food-log founding decision shows the new wording changes the
  outcome) and is owned by the spec's deterministic mechanisms (083-04/083-07),
  not by this trigger sentence. Recorded here so the ADR does not silently
  over-claim a capture win.
- The four consumer paths are existing maintained files (probed:
  `docs/workflow.md`, `skills/spec-workflow/SKILL.md`, `skills/memory-sync/SKILL.md`
  all exist and carry the surfaces named above; `docs/decisions/lightweight-decisions.md`
  ships the Phase-1 routing heuristic this widens).

## Kill criteria

- If a future host or workflow drops one of the two session-end surfaces
  (reconciliation or memory-sync), the "both surfaces" guarantee no longer holds
  and the owner map must be revisited.
- If the drift test proves too brittle (e.g. legitimate per-site rephrasing is
  repeatedly wanted), revisit single-sourcing in favor of a looser semantic check.
- If a later eval/replay shows the widened wording demonstrably does **not**
  change capture outcomes AND the four-site maintenance ceremony is judged not
  worth the consistency guarantee alone, revert to bespoke per-site wording.

## Open questions

None.
