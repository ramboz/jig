---
dependencies: []
last_verified:
---

# ADR-0007: scaffold.json gains per-skill install list

## Status

Accepted (2026-05-15)

## Context

The `scaffold.json` install-state manifest currently tracks granularity at the tier level only.

```json
{
  "installed_tiers": ["tier-0", "tier-1"],
  "scaffold_signals": { ... }
}
```

Slice 006-01 AC #5 hit the resulting gap during the `tdd-loop` skill's
landing: the brief.md narrative said "Tier 1 `tdd-loop` and friends
auto-installed," but `scaffold.json` had no field that named
`tdd-loop` specifically. The slice's deviation log parked the question
in the inbox with an explicit trigger:

> When a third Tier 1 skill arrives, this gap will need a real answer:
> either expand the schema to `tier_1_skills: ["tdd-loop", ...]` or
> commit to tier-granularity tracking forever.

That trigger has fired. Tier 1 now ships five active skills:
`adr-workflow`, `tdd-loop`, `slice-land`, `pr-review`, `arch-review`.
Tier 0 ships four active skills + one deliberate stub + one sibling
(`migrate`). The tier-granularity field can no longer answer:

- Is `pr-review` specifically installed (vs. a downstream fork that
  swapped it for a richer alternative)?
- Does `verify_install` need to walk the filesystem, or can it read
  the manifest?
- What's the install-time intent vs. the on-disk state today?

Spec 016-03's flip to default-on `--with-machinery` further sharpens
the question: every skill now lands in `.claude/skills/jig-*/` by
default, so the filesystem IS the runtime source of truth — but the
manifest still purports to declare install state.

## Decision Options Considered

### Option A: Per-skill list ALONGSIDE `installed_tiers` (additive)

Add `installed_skills` as a flat list of `<tier>/<skill>` strings:

```json
{
  "installed_tiers": ["tier-0", "tier-1"],
  "installed_skills": [
    "tier-0/scaffold-init", "tier-0/memory-sync",
    "tier-0/spec-workflow", "tier-0/independent-review",
    "tier-0/migrate",
    "tier-1/adr-workflow", "tier-1/tdd-loop", "tier-1/slice-land",
    "tier-1/pr-review", "tier-1/arch-review"
  ],
  ...
}
```

- **Pros:**
  - Additive — old `scaffold.json` files (without `installed_skills`)
    are still valid; readers treat missing as "fall back to
    filesystem inspection."
  - Preserves the tier narrative in brief.md ("Tier 1
    auto-installed") without splitting the schema.
  - Single source of truth at fine granularity for any future
    consumer that needs it (e.g. `verify_install --against-manifest`,
    `migrate.py report` reading intent vs. disk state).
- **Cons:**
  - Two fields where one might do; readers must know which to
    prefer (tier list for narrative, skill list for granular checks).
  - Future drift risk: `installed_tiers` and `installed_skills` can
    disagree if someone hand-edits one. Mitigated by writing the
    invariant down: `installed_tiers` is derivable from
    `installed_skills` (`{s.split("/")[0] for s in installed_skills}`).

### Option B: Replace `installed_tiers` with `installed_skills` entirely

- **Pros:**
  - Cleaner. One source of truth.
  - Tier membership becomes a derived view.
- **Cons:**
  - Breaks every existing `scaffold.json` consumer (4 production
    call-sites in `scaffold.py`; 5 tests). All need a migration.
  - The tier abstraction has narrative value in brief.md ("Tier 0:
    always; Tier 1: signal-gated; Tier 2: offered"). Forcing readers
    to recompute tier membership from a 10-element list undermines
    that.

### Option C: Keep tier-only granularity (status quo)

- **Pros:** Zero work; zero schema churn.
- **Cons:**
  - Forces every downstream caller that needs per-skill state to
    walk the filesystem. `verify_install.py` and `migrate.py` already
    do, with subtle inconsistencies (different glob patterns, jig-
    prefix handling).
  - Forfeits any chance of a manifest-driven install-vs-disk
    reconciliation tool.
  - Pushes the inbox entry off forever — the trigger has fired and
    the cost of "do nothing" keeps growing.

### Option D: Push the schema into per-skill manifest files

A `.claude/skills/jig-<name>/install.json` per skill, owned by that
skill.

- **Pros:** Maximally decoupled; each skill carries its own
  metadata.
- **Cons:**
  - 10× the files for the same information.
  - No single read for "what's installed here?" — every consumer
    must glob.
  - Out of step with `scaffold.json`'s explicit role as the
    central install-state manifest (per ADR-0001 and the original
    Spike 001a brief).

## Recommended Decision

**Option A.** Add `installed_skills` as an additive field next to
`installed_tiers` in `scaffold.json`. The field is a list of
`"<tier>/<skill>"` strings (e.g. `"tier-1/tdd-loop"`); the tier
prefix is redundant with the existing `installed_tiers` list but
keeps each entry self-describing.

Schema invariant: `set(s.split("/")[0] for s in installed_skills) ==
set(installed_tiers)`. Stated, not enforced — `scaffold.py` writes
both fields consistently; hand-edits that violate the invariant are
the editor's problem.

Backwards compatibility: existing `scaffold.json` files without
`installed_skills` remain valid. Readers default to "field absent
= fall back to filesystem inspection" (already the de-facto
behaviour for `verify_install.py` and `migrate.py`). No migration
script needed; the next time `scaffold.py` rewrites a manifest
(e.g. `--force` re-scaffold), the field gets populated.

## Consequences

**Becomes easier:**

- `verify_install --against-manifest` becomes a one-read check
  (`is "tier-1/tdd-loop" in manifest["installed_skills"]?`)
  instead of a filesystem walk + jig-prefix re-derivation.
- Future divergence between install intent and on-disk state
  (e.g. someone deletes a skill dir manually) becomes detectable
  without a separate "intent" file.
- The inbox entry resolves cleanly with a known
  forward-compatible answer instead of remaining a perpetual
  follow-up.

**Becomes harder:**

- Two fields to keep in sync. The invariant is written down; tests
  pin it; hand-edits are still possible. A future
  `validate_manifest --check-invariants` mode could enforce it.
- Slightly larger `scaffold.json` (10 strings ≈ 250 bytes). Not a
  real cost.

**Implementation status:**

- This ADR lands alongside the schema change. The follow-up commit
  in the same PR:
  - Adds `installed_skills` to `templates/scaffold.json.template`
    (empty list placeholder).
  - Updates `scaffold.py:_select_tiers` (or a new `_enumerate_skills`
    helper) to compute the per-skill list from the same signal set
    that produced `installed_tiers`.
  - Writes `manifest["installed_skills"] = installed_skills` in
    `scaffold()`.
  - Adds 2-3 tests pinning (a) field presence, (b) tier-derivability
    invariant, (c) backwards-compat (an old manifest without the
    field still loads).
- No downstream caller depends on the new field today. Consumers
  may opt in over time; the path is clear.

## Open questions

None. The schema is additive; the invariant is stated; old manifests
keep working without migration. Future opt-in consumers (e.g.
`verify_install --against-manifest`) get a clean lookup.
