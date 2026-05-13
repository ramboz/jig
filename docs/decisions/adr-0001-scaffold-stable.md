# ADR-0001: scaffold-stable trigger

## Status

Accepted (2026-05-12)

## Context

scaffold-init generates docs with `Status: Draft (wizard-generated)` markers at the top. The original design (see [docs/research/00-starter-prompt.md](../research/00-starter-prompt.md) and slice 001-04 deviation log) stated:

> After 3–5 stable specs, scaffolding stability gets marked via a `scaffold-stable` ADR; the `Draft` markers flip to `Stable`.

This ADR resolves the deferred decision recorded in `docs/refinement-todo.md` under "scaffold-stable ADR trigger". The trigger was flagged automatically by jig's own stocktake (`skills/scaffold-init/stocktake.py`) once jig itself crossed the 3-reconciled-slice threshold during slice 001-04 reconciliation.

## Decision Options Considered

### Option A: Fixed threshold (3 reconciled slices)
- **Pros:** Deterministic, easy to detect, matches stocktake's existing logic.
- **Cons:** 3 slices is a low bar — could fire prematurely if early slices are trivial.

### Option B: Fixed threshold (5 reconciled slices)
- **Pros:** More conservative; gives the scaffold more validation before locking in.
- **Cons:** Slower to surface; for small projects with <5 slices total, never fires.

### Option C: Adaptive (≥3 reconciled slices AND ≥1 reconciled doc-touching slice)
- **Pros:** Heuristic — fires only when the docs themselves have been exercised, not just when slice count crosses a threshold.
- **Cons:** More complex to implement; "doc-touching" is a fuzzy classification.

### Option D: Manual (no automatic trigger; user runs a command when ready)
- **Pros:** Simplest. Avoids premature flipping.
- **Cons:** Yet another thing to remember. Defeats the "stocktake surfaces it for you" model.

## Recommended Decision

**Option A** — fixed threshold of **3 reconciled slices**.

- Aligns with the existing stocktake threshold (already implemented in slice 001-04).
- Simple to detect: `count_reconciled_slices(target) >= 3` (the function already exists).
- The flip from `Draft (wizard-generated)` → `Stable` is performed by a one-shot script (`stabilize.py`, deferred to a follow-on slice — see Consequences) or manually by a human invoking find/sed. The mechanism is small enough that a dedicated slice is not warranted unless usage shows it.
- Documentation says "3–5"; we pick the lower bound deliberately so the signal arrives sooner. Users can defer the actual flip if they want more confidence.

## Consequences

**Becomes easier:**
- The stocktake's existing promotion suggestion now has a concrete next step ("when you act on this, flip the Draft markers to Stable").
- Future ADRs that supersede this one can change the threshold without a code change (the threshold is a project decision, not a code constant — `PROMOTION_THRESHOLD` in stocktake.py stays at 3).

**Becomes harder:**
- Locking in scaffolded docs as Stable means later edits become "real changes" worth ADRs of their own. This is intentional.

**Implementation status:**
- The threshold is implemented (stocktake.py:18 — `PROMOTION_THRESHOLD = 3`).
- The actual Draft → Stable rewrite is **not yet automated**. Manual flip: `grep -rl "Status: Draft (wizard-generated)" docs/ CLAUDE.md | xargs sed -i '' 's/Status: Draft (wizard-generated)/Status: Stable/g'`. A `stabilize.py` helper is a candidate for a future slice if real users find the manual step annoying.

## Open questions

None. (If we later find that 3 is too low, supersede with a new ADR rather than editing this one.)
