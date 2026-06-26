---
status: DONE
dependencies: [083-01, adr-0031]
last_verified: 2026-06-26
frame_review: true  # spec-level ## Assumptions are real (064-04 deriver);
#                   # covered by the ADR-0031 frame-critique pass (shared design).
---

## Slice 083-05 — Routing rubric + `decisions.py add-lightweight` helper

**Goal:** Give triage a deterministic where-does-this-land step. Ship the
four-route routing rubric (ADR / lightweight record / refinement-todo / drop) in
the browsable `lightweight-decisions.md` home, and a `decisions.py add-lightweight`
CLI that idempotently appends a recorded decision in the template format — so
Phase 1's nudge-only file gains the helper-backed determinism the rest of jig
has. The rubric's ADR-branch criterion quotes the **single canonical** trigger
sentence from [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md).

**DoR:**
- ✅ [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)
  reserved (Proposed) — defines the canonical ADR-trigger sentence + the
  single-sourcing mechanism (constant `ADR_TRIGGER` + drift test).
- ✅ Helper home grounded: `decisions.py` lives in the **tier-0** `memory-sync`
  skill (alongside `memory.py`), **not** tier-1 `adr-workflow` — the
  always-scaffolded surfaces that reference it (memory-sync prompt +
  `lightweight-decisions.md`) must keep their scaffold helper-closure, which only
  resolves tier-0 helpers (a tier-1 helper referenced from tier-0 surfaces fails
  the closure check). Self-contained (no cross-tree import) so host packaging
  copies the skill whole. Append idempotency modeled on `memory.py`'s helpers.
- ✅ Routing home grounded: `docs/decisions/lightweight-decisions.md` already
  carries a Phase-1 "When to write here vs. an ADR" heuristic — this slice
  expands it to the full four-route rubric.

**Acceptance Criteria:**

1. **`decisions.py add-lightweight` appends a well-formed entry.** Given a title,
   decision, context, and scope, the CLI appends an entry under `## Entries` in
   `docs/decisions/lightweight-decisions.md` matching the template shape
   (`### [Date] — [title]` + `**Decision:**` / `**Context:**` / `**Scope:**` /
   optional `**Commit:**`), with today's date. Observable via the mutated file +
   exit 0.
2. **Idempotent.** Re-running `add-lightweight` with the same title (date-scoped)
   does not append a duplicate entry — it is a no-op (exit 0, file unchanged) and
   says so. Title match is normalized (case/whitespace-insensitive).
3. **Routing rubric present + ADR-branch single-sourced.** The four-route rubric
   (ADR / lightweight record / refinement-todo / drop) is documented in
   `lightweight-decisions.md`, and its ADR-branch criterion contains the **exact
   canonical string** `decisions.ADR_TRIGGER` (verbatim quote of ADR-0031's
   sentence).
4. **Single-source drift guard (co-owned with 083-06).** `test_decisions.py`
   asserts `ADR_TRIGGER` appears verbatim in all four consumer sites — the rubric
   (this slice) plus the two reconcile checklists and the memory-sync prompt
   (083-06) — and in ADR-0031's prose. The full four-site assertion goes green
   only once 083-06's edits land (the two slices ship in one PR).

**DoD:**
- [x] All ACs pass; full suite green (2978 tests OK, pyright clean); `uvx ruff check .` clean.
- [x] Test coverage exercises append, idempotency, malformed input (missing
      title/decision/file/`## Entries`), and the single-source drift guard (14 tests).
- [x] Reviewed by `reviewer` subagent (frame-critique + compliance + craft).
- [x] Deviation log + reconciliation sweep under this slice heading.
- [x] Host packages rebuilt; `build_host_packages.py --check` green.

### Deviation log

- **Helper home moved tier-1 → tier-0 (load-bearing).** First placed at
  `skills/adr-workflow/decisions.py` (cohesion with `adr.py`, the `docs/decisions/`
  tooling). That broke the scaffold **helper-closure** invariant: the
  always-scaffolded memory-sync prompt + `lightweight-decisions.md` reference the
  helper, but `adr-workflow` is **tier-1** (not in the default tier-0 scaffold) —
  surfacing as ~237 cascading test errors (scaffold-verify exit 4). Relocated to
  **tier-0 `skills/memory-sync/decisions.py`** (alongside `memory.py`). Recorded
  in [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md)
  "Helper home — tier-0, not tier-1".
- **Self-contained, non-atomic write (DoR constraint).** `decisions.py` does not
  import `_common.atomic_io` (cross-tree import would break whole-skill host
  packaging), so `add-lightweight` uses a plain write — acceptable for an
  owner-gated, single-writer doc; commented inline.
- **Craft nits addressed inline** (logged, non-blocking): `## Template` code-block
  re-spaced to match `render_entry` output (live file + scaffold template);
  `ADR_TRIGGER` split-literal grep note added; `_existing_keys` scan-breadth
  documented; a missing-`## Entries` ValueError test added.
- **AC4 co-owned with 083-06.** The four-site drift guard ships in this slice's
  `test_decisions.py` but is only fully green once 083-06's three surface edits
  land — both slices ship in one PR.

### Reconciliation sweep

- `skills/memory-sync/decisions.py` + `test_decisions.py` — **updated** (new
  helper + tests, tier-0 home).
- `docs/decisions/lightweight-decisions.md` (rubric + template spacing) and
  `templates/docs/decisions/lightweight-decisions.md.template` — **updated**.
- `skills/memory-sync/SKILL.md` — **updated** (helper-invocation prose repointed
  from manual Edit/Write to `decisions.py add-lightweight`).
- `hosts/claude/**`, `hosts/codex/**` — **updated** (rebuilt; `--check` green).
- [ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md) —
  **updated** (canonical source; Accepted 2026-06-26).
- `CLAUDE.md` primer / `docs/specs/README.md` status board — **deferred**: board
  regenerated at close-out; primer Active-specs entry stays (spec 083 still open
  via 083-07/083-08), so no compress-on-close per spec 025.
- `docs/architecture.md` — **no-op** (no module boundary / public contract change;
  a new tier-0 helper file is within existing skill structure).
