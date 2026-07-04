---
status: IN_PROGRESS
dependencies: []
last_verified:
frame_review: true
claimed_by: claude/eloquent-heisenberg-ec4ef3
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 085-01 — abandoned-as-lifecycle-state

**Goal:** Add `ABANDONED` as a terminal-adjacent lifecycle state for
slices/specs that are permanently dropped, distinct from `DEFERRED`
(parked, resumable via a stated trigger). Mirrors how `DEFERRED` itself
was introduced in slice 015-02: same FROM-state transition restriction,
same rollup-exclusion mechanism, same status-board section pattern.

**DoR:**
- ✅ Precedent slice 015-02 (DONE) — `docs/specs/015-structured-lifecycle-metadata/spec.md`
  — is the exact pattern to mirror, including its deviation log.
- ✅ `VALID_STATUSES` enum in `skills/spec-workflow/workflow.py` is the
  single point of change for accepted status values.
- ✅ The `**Resolution trigger:**` extraction convention
  (`_extract_resolution_trigger` / `_RESOLUTION_TRIGGER_RE`) is the
  template to mirror for a new `**Abandonment reason:**` line — same
  regex shape, different label.

**Acceptance Criteria:**

1. **`ABANDONED` is a valid status, reachable only from pre-`DONE` states.**
   `workflow.py transition X ABANDONED` succeeds from `DRAFT`,
   `READY_FOR_REVIEW`, `READY_FOR_IMPLEMENTATION`, `IN_PROGRESS`,
   `REVIEWED`, `RECONCILED`, and `DEFERRED`. `ABANDONED → ABANDONED` is
   idempotent (no error on re-run). **`DONE → ABANDONED` is refused** —
   frame-critique review found no case for collapsing "never attempted"
   and "shipped, then deliberately removed" into one bucket (see spec
   Non-goals); marking already-shipped work abandoned is out of scope for
   this slice. The refusal error names the reason (not just "invalid
   transition") so an author who hits it understands why, e.g. "cannot
   transition DONE → ABANDONED: marking already-shipped work as abandoned
   is out of scope (see spec 085 Non-goals)."
2. **`ABANDONED` has the same restricted outbound edges as `DEFERRED`.**
   `ABANDONED → DRAFT` (re-open) succeeds. Every other outbound transition
   from `ABANDONED` is refused, with an error message shaped like the
   existing `DEFERRED` refusal ("invalid transition: ABANDONED → X. From
   ABANDONED, only DRAFT (re-open) is allowed.").
3. **Status board renders a dedicated `## Abandoned slices` section.**
   `workflow.py status-board` emits a third table (after the active table
   and the existing `## Deferred slices` table) listing slices in
   `ABANDONED` with `Spec | Slice | Abandonment reason` columns.
   Abandonment reason is extracted from a `**Abandonment reason:**` line
   in the slice body (same convention shape as `**Resolution trigger:**`).
   The section is omitted entirely (not rendered with an empty table) when
   no slice is `ABANDONED` — mirroring `render_deferred_table`'s existing
   omission behavior.
4. **Spec-level rollup excludes `ABANDONED` the same way it excludes
   `DEFERRED`, plus resolves the wholly-abandoned case.**
   `compute_spec_status`: a spec with a mix of `DONE` + `ABANDONED` slices
   (no other live states) rolls up to `DONE` — same as a mix of `DONE` +
   `DEFERRED` today. A spec where **every** slice is `ABANDONED` rolls up
   to `ABANDONED` (not `DRAFT`) — this is the case
   [spec 036 Q3](../036-closed-spec-drift/spec.md) left open ("specs whose
   entire scope was abandoned"). A spec with a mix of `DEFERRED` and
   `ABANDONED` slices and nothing else still rolls up to `DRAFT` —
   settled, not merely assumed, by frame-critique round 4: this is
   consistency with the existing (unchanged) all-`DEFERRED` → `DRAFT`
   behavior, on the reasoning that both cases need the same human action
   (reopen the resumable part, or close it out entirely) and neither
   loses detail, since the individual slice rows stay fully visible
   regardless of the coarse spec-level rollup (see spec Assumptions for
   the full reasoning + resolution trigger).
   This widens `compute_spec_status`'s return type from three documented
   values to four; update its docstring to document `ABANDONED` as the
   fourth (frame-critique round 3 audited every consumer of the return
   value — see spec Assumptions — and found none branch on a closed
   three-value set, so this is a safe widening, not a breaking change).
5. **`session_plan` skips `ABANDONED` slices**, the same way it already
   skips `DEFERRED` — abandoned work never appears in the orchestrator's
   dispatch plan.
6. **Auto-tick stays correct.** The existing auto-tick rules apply only to
   `→ REVIEWED` / `→ RECONCILED`. `→ ABANDONED` and `ABANDONED → DRAFT`
   tick nothing — no regressions in existing auto-tick tests.
7. **Tests green.** New tests cover: transition to `ABANDONED` from each
   pre-`DONE` state, `DONE → ABANDONED` refused, invalid outbound
   transition from `ABANDONED` refused, status-board renders the
   Abandoned section (with/without reason, omitted when empty), rollup
   (mixed `DONE`+`ABANDONED` → `DONE`; unanimous `ABANDONED` →
   `ABANDONED`; mixed `DEFERRED`+`ABANDONED` only → `DRAFT`),
   `session_plan` omits `ABANDONED` slices. Full suite green,
   no regressions.
8. **Transitioning to `ABANDONED` warns about live dependents, once,
   non-blocking.** Frame-critique round 2 found that `ABANDONED` is a
   hard, permanent dead end for `_validate_dependencies`'s exact
   `"DONE"` check — unlike the spike-Outcome precedent, where a
   `DONE` spike slice with `Outcome: abandoned` never trips that check.
   A live dependent (any other slice, anywhere in the project, whose
   `dependencies:` list names this slice's fragment AND whose own
   status is not already `DONE`/`ABANDONED`) would otherwise fail its
   own `→ DONE` transition later with no context on why. So: when
   `transition X ABANDONED` succeeds, print a warning to stderr
   (mirroring the existing `_branch_freshness_warning` pattern on
   `REVIEWED`/`RECONCILED`) naming each live dependent found, or print
   nothing when there are none. **Advisory only** — does not block the
   transition, does not modify the dependent, does not cascade. This is
   the one place this spec deliberately narrows the spike-precedent
   analogy the Non-goals section otherwise leans on (see spec's Non-goals
   / Assumptions for the reasoning).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** After this slice lands, a user can run
`workflow.py transition <spec> <slice> ABANDONED` on a specced-but-dropped
slice, regenerate the status board, and see it surfaced in its own
`## Abandoned slices` section with its reason — end-to-end observable
value in one slice, no follow-up slice required to make it visible.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO — filled during reconciliation._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO_ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
