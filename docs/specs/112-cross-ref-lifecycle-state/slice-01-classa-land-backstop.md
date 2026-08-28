---
status: DONE
dependencies: [adr-0058]
last_verified: 2026-08-27
arch_review: true
frame_review: true
---

## Slice 112-01 — classa-land-backstop

**Goal:** Introduce the shared cross-ref lifecycle-state primitive and wire its
first consumer — a Class-A blocker in `land.py prepare` that refuses GO when the
slice/ADR being landed is already `DONE`/`Accepted` on `origin/main` (or a merged
ancestor). Delivers, end-to-end, a false-positive-free stop against re-landing
already-integrated work.

**DoR:**
- ✅ ADR-0058 Accepted (done).
- ✅ Access to `origin/main` for the read (best-effort; the gate degrades to a
  non-blocking warning when the base ref is unreachable).

**Acceptance Criteria:**

1. **New primitive `identifier_state_on_ref(identifier, ref)`** (home:
   `skills/_common/`) returns the lifecycle marker (`DONE`/`Accepted`/… or
   `absent`) for a slice (`NNN-MM`) or ADR (`NNNN`) on a given git ref, matching
   on the **number**, not the filename (survives a renamed slug). Reads via
   `git show <ref>:<path>`; returns `absent` when the file is not on that ref.
2. **`land.py prepare` gains a fifth blocker.** When the slice under land (or its
   linked ADR) is already `DONE`/`Accepted` on `origin/main`, `prepare` reports a
   Class-A blocker and exits non-zero (GO refused), naming the ref and the
   integrated state. Folded into the existing `has_blocker` computation.
3. **False-positive guard:** the gate does **not** fire on the normal case where
   the identifier is absent from `origin/main` or is at an equal/earlier state.
   The one legitimate `DONE`-on-main case (sanctioned re-open / supersession) is
   passable via the deliberateness bypass (AC5).
4. **Best-effort:** when `origin/main` cannot be resolved/read (offline, no
   remote), the check emits a non-blocking warning and does not fail `prepare`
   — consistent with `_branch_freshness_warning`'s posture.
5. **Bypass:** `JIG_CROSSREF_GATE=0` (also `false`/`off`/`no`) skips the Class-A
   blocker, logged like jig's other gate bypasses (ADR-0011). Exact env name may
   be reconciled with existing `JIG_*` naming during implementation.
6. **Host-package parity:** `land.py` and any new `_common` helper are vendored
   into `hosts/`; the slice regenerates host copies so CI drift stays green.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Tests exercise: integrated-DONE → refuse; absent → pass; equal/earlier →
      pass; unreachable-base → warn-not-fail; bypass set → pass. Number-match
      across a renamed slug covered.
- [x] Each new test shown to fail when its feature is removed.
- [x] Reviewed by `reviewer` subagent (compliance + craft; arch pass — this
      slice introduces a shared primitive and extends the land-gate contract).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a developer running
`land.py prepare` on a branch that duplicates already-integrated work gets an
explicit refusal instead of a GO — an observable, end-to-end behavior change at a
real command, not internal scaffolding.

### Deviation log (after reconciliation)

1. **ADR-arm rescope (review blocker → fixed).** The first implementation keyed
   the Class-A ADR arm on the slice's `dependencies:` frontmatter, which
   false-positived: depending on an already-`Accepted` governing ADR is the
   normal precondition, so it blocked nearly every slice with an ADR dependency
   (this one included). Compliance + craft both caught it independently. Rescoped
   to `_introduced_adr_identifiers` — ADRs *added by this branch*
   (`git diff --diff-filter=A origin/main...HEAD` on the decisions dir) — blocking
   only when an introduced ADR's number is already `Accepted` on `origin/main`
   (the actual duplicate-ADR incident). Best-effort: unresolvable diff → warning,
   not a block. **Limitation:** detection is commit-based, so an *uncommitted*
   new ADR file is not seen — consistent with landing committed work + AC4.
2. **`parsing.py` extraction (structural, beyond the literal ACs).** Extracted
   `status_marker_from_section` out of `land.py` into `skills/_common/parsing.py`
   so `cross_ref_state.py` could reuse the exact status parser without a circular
   import (`cross_ref_state` → `land.py`). `land.check_status` now delegates;
   behavior preserved byte-for-byte. Arch review confirmed this the correct
   boundary move.
3. **Craft nit applied:** `kind_label` ternary → `_CROSSREF_KIND_LABEL` dict.
   **Deferred nit:** a shared `_frontmatter_of_section` helper (duplicated
   section-frontmatter fallback) — only 2 callers, deferred per rule-of-three.
4. **Pre-existing flaky test (not this slice).**
   `test_codex_semantic_index_internal_overlay_fixture_activates_scout`
   (scaffold-init / scout-daemon activation) fails non-deterministically — it
   failed then passed on byte-identical code, and this slice's diff touches only
   `land.py`/`parsing.py`/`cross_ref_state.py` (+ their host copies), not scout
   logic. Logged as a flake, not a regression.
5. **Status-reader precedence divergence** (opposite precedence vs
   `workflow.py::_slice_status_from_section`) recorded as a deferred item in
   `docs/refinement-todo.md` (arch-review nit).

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door untouched — internal land-gate change. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | No behavior/scope drift; principles preserved (deterministic gate, ADR-0011 bypass). |
| `docs/architecture.md` | `updated` | Added `cross_ref_state.py` to the `skills/_common/` roster (arch-review nit). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Spec 112 in flight (other slices DRAFT); no primer compression yet. |
| `docs/inbox.md` | `no-op` | No inbox items resolved by this slice. |
| `docs/refinement-todo.md` | `updated` | Added the status-reader precedence-divergence deferred item. |
| `docs/memory/**` | `no-op` | No new domain term/learning warranting memory-sync (the flake + precedence notes live in the deviation log + refinement-todo). |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR added/changed by this slice (ADR-0058 already indexed). |
| `skills/slice-land/SKILL.md` | `updated` | This slice adds a fifth land readiness check; corrected the "four checks" prose + exit-0 clause + example output to include the Class-A cross-ref backstop (reconciliation-review note). |
| `hosts/**` (vendored copies) | `updated` | Regenerated via `build_host_packages.py`; `--check` in sync. |
