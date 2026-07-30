---
dependencies: []
last_verified: 2026-06-15
frame_review: true
status: Superseded
---

# ADR-0026: Frontmatter is the canonical home for ADR status

## Status

Accepted (2026-06-15)
Superseded by [ADR-0046](./adr-0046-adr-status-frontmatter-authority.md) (2026-07-29)

## Context

ADR status lives only in prose; slice status lives in frontmatter. The
dependency check in `workflow.py` inherits that split: `_lookup_adr_accepted`
scans only the ADR's prose `## Status` section for an `^Accepted` line and
never reads frontmatter, while its sibling `_lookup_slice_status` reads the
slice's frontmatter `status:` first and falls back to the prose marker only
when frontmatter is absent.

Two consequences of this asymmetry:

1. **Surprise / non-uniformity.** The two readers take status from
   different places for the two artifact types, so a maintainer reasonably
   expects the ADR reader to honor frontmatter too and is caught out when it
   doesn't. ADR lifecycle state is the one piece of ADR metadata still
   locked in prose — `dependencies`, `last_verified`, and `frame_review` are
   already structured frontmatter fields.
2. **A real reader/writer mismatch on superseded ADRs.** `adr.py supersede`
   leaves the `Accepted (date)` prose line in place and only *appends* a
   `Superseded by …` line. Because `_lookup_adr_accepted` matches
   `^Accepted`, a dependency on a **superseded** ADR is currently reported
   as satisfied — even though `adr.py`'s own `_classify_status` already
   treats "Superseded wins over Accepted." The dependency reader is out of
   step with the writer's own status model.

These two problems have **different cost profiles**, and the fixes span a
range (see Options). Problem 2 is a concrete bug fixable in the reader
alone; problem 1 is a uniformity/data-model gap that only a format change
addresses.

Today **no** ADR carries a `status:` field in frontmatter (verified across
all 25 existing ADRs), and **no current consumer reads ADR status from
frontmatter** (verified: `_lookup_adr_accepted` and `_classify_status` both
operate on prose). Status lives entirely in prose, written and flipped by
`adr.py new` / `accept` / `supersede`.

Audit of blast radius: the genuinely-superseded ADRs are **0002 and 0008**;
no slice declares a dependency on either (slice deps point only at
0014/0017/0020/0022/0024/0025, all current). So changing how superseded
ADRs resolve has no effect on any existing transition.

## Decision Options Considered

### Option A: Keep prose canonical; document the asymmetry, leave the bug
- **Pros:** No format change, no dual source of truth, zero migration. The
  asymmetry is arguably *correct* — each artifact has one status home (slice
  = frontmatter, ADR = prose) and each reader parses where its writer
  writes.
- **Cons:** Leaves problem 2 (superseded reads as accepted) unfixed. The two
  readers stay mechanically different.

### Option B: Reader-only — make `_lookup_adr_accepted` frontmatter-first with prose fallback
- **Pros:** Tiny change; structurally mirrors `_lookup_slice_status`.
- **Cons:** **Inert today** — no ADR populates frontmatter status, so the new
  branch never executes. Adds a dead branch and fixes nothing, including
  problem 2.

### Option C: Reader-only, prose-canonical — teach the reader to recognize `Superseded`
- **What:** Keep prose as the single source of truth, but fix problem 2 in
  the reader: have `_lookup_adr_accepted` reuse `adr.py`'s existing prose
  classifier `_classify_status` (which already returns
  Proposed/Accepted/**Superseded**, "Superseded wins") — lifting it to
  `_common` so both skills share it — or, minimally, check for a
  `Superseded by` line before the `^Accepted` check.
- **Pros:** Fixes problem 2 — the *only concrete bug* — at the smallest
  possible blast radius. Prose stays the single source of truth: **no
  frontmatter, no dual-write, no format change, no migration.** Aligns with
  jig's "don't build ahead of demand" norm (cf. the PARKED pluggable-oracle
  boundary, ADR-0019's trigger). Unlike Option B, it is **not inert**.
- **Cons:** Does nothing for problem 1 — the reader/writer *mechanism* stays
  asymmetric with slices, and ADR status remains prose-only, not queryable
  as structured data alongside `dependencies` / `last_verified` /
  `frame_review`. Leaves the uniform-frontmatter-metadata direction
  incomplete.

### Option D: Full alignment — frontmatter is canonical, writer + reader (CHOSEN)
- **What:** `adr.py` stamps a `status:` frontmatter field (Proposed →
  Accepted → Superseded) in lockstep with the prose; the reader reads
  frontmatter first, prose as the legacy fallback.
- **Pros:** Completes the frontmatter data-model — status joins the other
  lifecycle metadata and becomes uniform with slices and queryable as
  structured data. Reader and writer agree. Fixes problem 2 as a side
  effect (supersede stamps `Superseded`, reader honors it). Legacy ADRs
  grandfather through the prose fallback — no forced backfill.
- **Cons:** Status now lives in two places (frontmatter + prose
  `## Status`), so the writer must update both atomically or they drift.
  Touches the ADR artifact format (template + three `adr.py` write paths).
  **Mildly ahead of demand** — no consumer needs frontmatter ADR status
  today.

## Recommended Decision

Adopt **Option D**, with eyes open to its cost.

**Why not the cheaper Option C.** Option C is genuinely cheaper and *does*
fix the only concrete bug (problem 2) with no format change — it is the
right call if problem 2 is the *only* thing worth solving. We choose D
instead because we judge problem 1 worth solving too: ADR status is the
last lifecycle attribute still trapped in prose while every other ADR
metadata field (`dependencies`, `last_verified`, `frame_review`) is already
structured frontmatter. Completing that data-model — one uniform status
model across ADRs *and* slices, status readable as data rather than scraped
from prose — is the actual goal here, and Option C explicitly does not
deliver it.

We accept two honest costs for that:

- **It is mildly ahead of demand.** No consumer reads ADR frontmatter status
  today. We judge the one-time cost of establishing the field now — versus
  retrofitting `status:` across the ADR corpus later *and* carrying the
  prose/frontmatter asymmetry indefinitely — as the better trade. This is a
  deliberate exception to "don't build ahead of demand," not an oversight.
- **The dual-write tax is real but bounded.** Prose `## Status` must exist
  regardless (Nygard convention, human-readable dates, supersession links
  that `adr.py supersede` parses), so the frontmatter field is a *mirror*,
  not net-new surface. All status mutations already funnel through three
  co-located `adr.py` commands, so "keep them in sync" is three writes in
  one module, locked by a test — not an open-ended hazard.

Concretely, Option D means:

1. **Frontmatter `status:` is canonical; prose `## Status` is a synchronized
   human-readable mirror and the fallback for legacy ADRs.**
   `_lookup_adr_accepted` reads frontmatter `status:` first; when absent
   (every ADR authored before this change), it falls back to the existing
   prose scan. Grandfathers all existing ADRs with no backfill — the same
   default-off / forward-only pattern used for `frame_review` (spec 064-05).

2. **The writer keeps both representations in sync in a single atomic write:**
   - `adr.py new` stamps `status: Proposed` (next to `frame_review: true`)
     and writes the `Proposed (date)` prose line.
   - `adr.py accept` sets frontmatter `status: Accepted` in the same write
     that flips the prose to `Accepted (date)`.
   - `adr.py supersede` sets the old ADR's frontmatter `status: Superseded`
     in the same write that appends the prose `Superseded by …` line.

3. **`Superseded` is not `Accepted` for dependency purposes.** Once an ADR's
   frontmatter says `Superseded`, `_lookup_adr_accepted` returns
   not-satisfied with a reason naming the superseder. This aligns the
   dependency reader with `adr.py`'s `_classify_status`. No slice depends on
   a superseded ADR today, so this tightening changes no existing
   transition.

Frontmatter wins on disagreement; the synchronized-write rule (point 2)
keeps disagreement from arising. The implementing spec **must** include a
test that locks the supersede → frontmatter sync so prose and frontmatter
cannot silently diverge. Status values mirror the three prose lifecycle
states: `Proposed`, `Accepted`, `Superseded` (exact, case-sensitive match).

This decision **refines the Nygard `## Status` convention** carried by the
ADR template (`templates/docs/decisions/adr-0000-template.md`) and **extends
the `frame_review` precedent** (a managed frontmatter field on ADRs, spec
064-05 / ADR-0020). It does **not** touch
[ADR-0004](./adr-0004-decisions-folder-naming.md) (folder/filename naming).
Per [ADR-0006](./adr-0006-adr-accept-then-index-ordering.md), frontmatter
`status:` is — like the prose Status line — the one mutable surface on an
otherwise immutable ADR; flipping it via `accept` / `supersede` is not a
decision-content edit.

## Consequences

**Becomes easier:**
- A maintainer (and any future frontmatter-parsing tooling) can read an
  ADR's lifecycle state from frontmatter alone, uniformly with slices.
- The dependency reader and `adr.py`'s status model agree; a dependency on a
  superseded ADR is caught instead of silently passing.

**Becomes harder:**
- The writer must update two representations atomically *forever*; a future
  code path that touches one without the other reintroduces drift.
  Mitigated by the sync-locking test and by keeping all status writes inside
  `adr.py`.
- A slice that legitimately wants to depend on a superseded ADR (rare) can
  no longer express that as a passing dependency — it must depend on the
  superseder instead (arguably the correct expression anyway).
- We take on a maintenance surface ahead of a consuming need; if that need
  never materializes, the sync tax was paid for uniformity alone (see Kill
  criteria).

## Assumptions

The load-bearing factual claims here were **verified by inspection, not
assumed** (recorded for the reviewer's grounding):

- No ADR carries a frontmatter `status:` field today, and no current
  consumer reads ADR status from frontmatter — scanned every frontmatter
  block under `docs/decisions/` and confirmed `_lookup_adr_accepted` /
  `_classify_status` operate on prose. The reader's prose fallback therefore
  covers every legacy ADR.
- `adr.py supersede` preserves the `Accepted (date)` prose line and only
  appends `Superseded by …` — confirmed in the supersede helper and on the
  two live superseded ADRs (0002, 0008). This is why today's prose-only
  reader treats a superseded ADR as accepted, and why `_classify_status`
  exists to disambiguate.
- No slice's `dependencies:` references a currently-superseded ADR — so the
  `Superseded ≠ Accepted` tightening has no current blast radius.

No unverified load-bearing assumptions remain. The chosen frame's exposure
is a *value judgment* (uniformity now is worth a bounded sync tax and being
mildly ahead of demand), not an unverified factual claim — and the cheaper
single-source alternative (Option C) is enumerated and explicitly rejected
above rather than skipped.

## Kill criteria

- If a uniform frontmatter status model never acquires a consumer (no
  tooling ever reads `status:` from ADR frontmatter) *and* the sync proves
  even mildly error-prone, the trade was wrong — revert to Option C's
  single-source prose reader and drop the frontmatter field.
- If keeping frontmatter and prose synchronized ships a drift bug despite
  the locking test, reconsider collapsing to a single representation.
- If a real need emerges to treat a superseded ADR as a satisfied
  dependency, revisit the `Superseded ≠ Accepted` ruling.

## Open questions

- **Backfill of existing ADRs.** Existing ADRs are grandfathered via the
  prose fallback, so no backfill is required for correctness. A later
  cosmetic pass could stamp `status:` into the ~25 existing ADRs for
  uniformity, but that is out of scope here — recommend leaving it to a
  separate optional migration.
