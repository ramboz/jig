---
status: RECONCILED
dependencies: []
last_verified: 2026-07-03
frame_review: true
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
- [x] All ACs pass; full test suite green (no regressions). **3173 tests,
      `OK (skipped=9)` — verified independently twice (once immediately
      post-implementation, once after the craft-review nit fixes).**
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
      **`AbandonedLifecycleTests` — 17 tests, one or more per AC
      (transition matrix across every pre-DONE state, DONE-refusal,
      outbound-restriction refusal, board rendering with/without reason
      and omitted-when-empty, all 3 rollup permutations, session-plan
      skip, auto-tick no-op, dependents warning present/absent/DONE-dependent-excluded).**
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. **Compliance + craft passes, both `pass`; recorded at
      `docs/specs/085-abandoned-state/reviews/slice-01-{compliance,craft}.md`.**
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. **No new deferral from this slice;
      added a disambiguating cross-reference to the pre-existing
      `unreserve` entry (see deviation log §7).**

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

**1. Pre-implementation frame-critique took five rounds, not one.** The
spec's own Overview and Assumptions sections already document the four
substantive findings and their resolutions in detail (`DONE → ABANDONED`
reachability, the cascade-to-dependents analogy, the `compute_spec_status`
return-type widening audit, and the `DEFERRED`+`ABANDONED` rollup
decision) — not repeated here to avoid duplicating a durable record with
itself. Recorded verdicts: `docs/specs/085-abandoned-state/reviews/slice-01-frame-critique.md`.

**2. `_DEFERRED_ALLOWED_NEXT` gained `"ABANDONED"`.** Not called out
explicitly in the slice text, but required by AC1's own transition list
("reachable ... from DRAFT, ..., and DEFERRED"): the pre-existing
FROM-`DEFERRED` outbound restriction would otherwise block
`DEFERRED → ABANDONED`. A parked slice can now be permanently dropped
directly, without first re-opening to `DRAFT`.

**3. `collect_slices`'s row tuple grew from 6 to 7 elements** (added
`abandonment_reason` at index 6), mirroring the earlier 3→4→5→6-tuple
growth history for `resolution_trigger` / `kind` / `claimed_by`. All
existing consumers (`render_status_table`, `render_deferred_table`,
`parse_existing_notes`) access positionally with `len(row) >= N` guards,
so the new element is additive and non-breaking — confirmed by the full
test suite (3173 tests, no regressions).

**4. `_find_live_dependents` returns `"<spec_dir> <label> (<status>)"`
strings**, not a structured type. AC8 named the requirement (warn, name
the fragment) but not an exact output shape; this format was chosen for
human-readability in a stderr warning, matching `_branch_freshness_warning`'s
plain-text style rather than a machine-parseable one (this warning has no
programmatic consumer).

**5. `session_plan`'s "no slices to plan" message updated** from "every
slice is DEFERRED" to "every slice is DEFERRED or ABANDONED" — a small
accuracy fix directly adjacent to the AC5 edit (the function's skip
condition), not separately specced but necessary so the message stays true.

**6. Two craft-review nits fixed post-review, pre-RECONCILED:**
`_find_live_dependents`'s unused `abandoned_spec_md` parameter was dropped
(only `abandoned_slice_path` was ever read), and a vacuous test assertion
(`assertNotEqual(dependent_md, None)`, which could never fail since
`_write_spec` never returns `None`) was removed from
`test_transition_to_abandoned_warns_about_live_dependent`. Neither changed
behavior; both improved code clarity. Full suite re-run green after the fix
(3173 tests); host packages regenerated and re-confirmed in sync.

**7. Doc updates from this slice (beyond the code):**

- `skills/spec-workflow/workflow.py` — see compliance review
  (`docs/specs/085-abandoned-state/reviews/slice-01-compliance.md`) for the
  full call-site list. Net +~195 lines after the nit cleanup.
- `skills/spec-workflow/test_workflow.py` — new `AbandonedLifecycleTests`
  class, 17 tests.
- `skills/spec-workflow/SKILL.md` — new "ABANDONED state" subsection
  (mirrors "DEFERRED state"); the lifecycle diagram and the
  spec-level-rollup paragraph updated to describe the 4th `compute_spec_status`
  return value (**closed-spec drift fix, live prose — corrected inline
  per ADR-0010**, not an amendment, since SKILL.md is live not a closed
  record).
- `docs/workflow.md` — lifecycle mermaid diagram gained the
  `ABANDONED ⇄ DRAFT` sidetrack; the `session-plan` description corrected
  to say "non-DEFERRED, non-ABANDONED" (same live-prose-fix rationale).
- `docs/memory/glossary.md` — new `## ABANDONED` entry, placed directly
  after `## DEFERRED`.
- `docs/refinement-todo.md` — the existing `unreserve <NNN>` deferred
  decision gained a one-line cross-reference distinguishing it from this
  slice's mechanism (never-drafted-stub deletion vs. permanently-dropped
  specced work) — no scope or resolution-trigger change, just a
  disambiguation note for future readers.
- `docs/specs/036-closed-spec-drift/spec.md` — **closed-spec drift, ADR-0010
  Amendments route** (this is a `DONE` record, not live prose): a dated
  `## Amendments` entry closes the loop on Q3's "specs whose entire scope
  was abandoned" case, which that spec's answer never actually resolved.
- No `docs/conventions.md` change (explicit Non-goal — requires
  `JIG_CONVENTIONS_APPROVED=1` / human approval; a symmetrical `ABANDONED`
  rule belongs there eventually but is out of scope here).
- No `docs/architecture.md` change (internal lifecycle-state extension,
  no module-boundary or public-contract change).
- No new ADR — same precedent slice 015-02 set when introducing `DEFERRED`
  ("lifecycle extension, not a directional architecture choice"). The four
  load-bearing judgment calls this slice made are durably recorded in the
  spec's own Assumptions section and the frame-critique review file, which
  is discoverable the same way an ADR would be (linked from the status
  board), so a dedicated ADR would duplicate rather than add information.
- `docs/roadmap.md` — no-op (dev-infrastructure spec, not a
  milestone-tracked feature — same precedent as spec 051).
- `docs/inbox.md` — checked, nothing to triage (no items referenced this
  gap).
- `CLAUDE.md` — checked; no hot-cache entry added. `DEFERRED` itself has
  no Key-terms bullet despite being a comparably-sized lifecycle addition,
  so adding one for its sibling `ABANDONED` would be inconsistent bloat —
  the full definition lives in `SKILL.md` + `docs/workflow.md` +
  the glossary, which is exactly where `DEFERRED`'s lives.

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door doesn't enumerate lifecycle states; unaffected. |
| `docs/specs/README.md` | `updated` | Regenerated via `workflow.py status-board`; spec 085 now listed, rollup computed. |
| `docs/product-vision.md` | `no-op` | Internal dev-workflow mechanism, not a product-facing behavior or use case. |
| `docs/architecture.md` | `no-op` | No module-boundary or public-contract change — internal lifecycle-state extension inside `workflow.py`. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | Checked; no hot-cache entry warranted (see deviation log §7 — `DEFERRED` itself has none, for consistency). No `AGENTS.md` or scaffold templates reference lifecycle states directly. |
| `docs/inbox.md` | `no-op` | Checked — no entries referenced this gap. |
| `docs/refinement-todo.md` | `updated` | Added a one-line cross-reference distinguishing the existing `unreserve` deferred decision from this slice's mechanism — no scope change. |
| `docs/memory/**` | `updated` | New `## ABANDONED` glossary entry. Broader memory-sync (learnings, MEMORY.md index) runs as a separate post-reconciliation step. |
| `docs/decisions/README.md` / ADR index | `no-op` | No new ADR — see deviation log §7 for the precedent-consistent reasoning (mirrors slice 015-02's DEFERRED introduction, which also skipped an ADR). |
| Additional live prose / generated templates touched by this slice | `updated` | `skills/spec-workflow/SKILL.md` (new "ABANDONED state" subsection + corrected lifecycle-rollup prose) and `docs/workflow.md` (mermaid diagram + `session-plan` description) — both live prose, corrected inline per ADR-0010. `docs/specs/036-closed-spec-drift/spec.md` (a `DONE` record) got a dated `## Amendments` entry instead, per the same ADR's records-vs-live-prose split. |
