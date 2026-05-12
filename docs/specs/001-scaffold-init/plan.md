# Plan: Slice 001-04 — deferred-decisions

## Approach

Two parts:

1. **Format compliance verification** — assert via tests that scaffolded `refinement-todo.md` matches AC #1/#2. The current template already follows the pattern: 3 H2 categories (Architecture, Conventions, Operations) with H3 `### Decision: <name>` entries containing `**Deferred:**` and `**Resolution trigger:**` lines. The AC #1 wording suggests H2 for decisions; we use H3 under category H2 (cleaner doc structure). Log this interpretation in deviation.

2. **Stocktake helper** — a small Python script that:
   - Counts slices in `STATUS: DONE` or `STATUS: RECONCILED` across `docs/specs/*/spec.md`
   - Parses deferred items from `docs/refinement-todo.md`
   - Prints a markdown report
   - When count ≥3, surfaces an "review for promotion" suggestion

Stocktake is **invoked manually** by the user. It is not a hook (per AC #3: "skill, not hook"). It lives in `skills/scaffold-init/` since it's part of the scaffold-init concern (post-scaffold operational tool). A standalone skill wrapper is deferred — `memory-sync` (spec 002) is the natural future home.

## "Spec" vs "slice" interpretation

AC #3 says "after 3 reconciled specs". A jig "spec" is a directory `docs/specs/NNN-name/` containing one spec.md with multiple slices. Pragmatic interpretation: **count reconciled slices, not entire specs.** A whole-spec milestone is rare; slice-level milestones are the natural pulse. This is logged in the deviation log.

## Files to create

| Path | Purpose |
|---|---|
| `skills/scaffold-init/stocktake.py` | The helper script |

## Files to modify

| Path | Change |
|---|---|
| `templates/docs/workflow.md.template` | Add a Stocktake section with invocation hint |
| `skills/scaffold-init/test_scaffold.py` | New tests: format compliance + stocktake parsing + threshold behavior |
| `docs/specs/001-scaffold-init/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## Test strategy

`FormatComplianceTests`:
- assert ≥3 H3 `### Decision:` entries
- assert each entry has matching `**Deferred:**` and `**Resolution trigger:**` lines within its section
- assert each category (Architecture, Conventions, Operations) has ≥1 decision

`StocktakeTests`:
- bare scaffold (no DONE specs) → stocktake runs, count=0, no promotion suggestion
- fabricate 3 fake spec.md files with `**STATUS: DONE**` → stocktake count=3, suggestion appears
- stocktake correctly parses deferred items (count + names) from refinement-todo.md
- stocktake handles missing refinement-todo.md gracefully (returns 0 items, runs cleanly)

## Out of scope

- A separate skill wrapper for stocktake → deferred (memory-sync slice 002 is the natural home).
- Auto-running stocktake on a schedule → user invokes manually.
- "Promotion" actually moving items from refinement-todo to spec backlog → stocktake only suggests.
