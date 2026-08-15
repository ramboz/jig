---
status: DRAFT
dependencies: [adr-0057]
last_verified:
frame_review: true
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 111-01 — blocked-annotation-and-board

**Goal:** An author marks an actionable slice as blocked with a `blocked_by:`
frontmatter field (and an optional `**Blocked:**` body line), and the status
board renders a `## Blocked slices` section listing every actionable-state slice
that is blocked — a clean, countable signal a portfolio dashboard (Gauge) can
read directly, instead of approximating from `DEFERRED` / `dependencies:` /
refinement-todo proxies.

**Decision:** [ADR-0057](../../decisions/adr-0057-first-class-blockers-are-annotations.md)
— a blocker is an annotation on an actionable slice, not a lifecycle state.

**DoR:**
- ✅ ADR-0057 Accepted (annotation-not-state; the "actionable" boundary =
  `READY_FOR_IMPLEMENTATION` + `_CLAIM_WORKING_STATUSES`).
- ✅ The rendering pattern to mirror exists and is probed:
  `render_deferred_table` / `render_abandoned_table`
  (`skills/spec-workflow/workflow.py:2231` / `:2271`) emit a
  `| Spec | Slice | <context> |` table appended after the active table;
  `collect_slices` (`:2063`) reads per-slice frontmatter (`claimed_by` via
  `CLAIM_FIELD`, `:2112`); `_extract_resolution_trigger` (`:1544`) is the
  body-line extractor shape.
- ✅ Actionable states grounded: `_CLAIM_WORKING_STATUSES`
  (`workflow.py:4204`) + `READY_FOR_IMPLEMENTATION`.

**Assumptions:** A1, A2 from [spec 111](./spec.md#assumptions) — A1 (no existing
`blocked_by` convention) grounded by enumeration; A2 (consumer wants
ready-but-stuck included) is an un-probed assumption with a kill condition in
ADR-0057.

**Acceptance Criteria:**

1. **`blocked_by:` is read from slice frontmatter.** `collect_slices` carries each
   slice's `blocked_by:` value (empty string when unset), read the same way
   `claimed_by` is (a module-level `BLOCKED_FIELD = "blocked_by"` constant, via
   `fm_fields.get(BLOCKED_FIELD)`). A whitespace-only value is normalized to
   empty (treated as unset).

2. **A `**Blocked:**` body-line extractor exists.** `_extract_blocked(section)`
   returns the prose after a `**Blocked:**` line (mirroring
   `_extract_resolution_trigger`), empty string when absent. This is the optional
   human-detail half of the convention.

3. **The board renders a `## Blocked slices` section.** A `render_blocked_table`
   helper emits a `| Spec | Slice | Blocked on |` table listing every
   **actionable-state** slice with a non-empty `blocked_by:`, in file order,
   appended after the active table alongside the Deferred/Abandoned sections. The
   "Blocked on" cell shows the `**Blocked:**` body line when present, otherwise
   the `blocked_by:` frontmatter value. A short intro line (mirroring the Deferred
   table's) states these are actionable slices stuck on a named thing.

4. **Only actionable-state slices count.** A slice is included only when its
   status is in `READY_FOR_IMPLEMENTATION` + `_CLAIM_WORKING_STATUSES`
   (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`). A
   `blocked_by:` on a `DRAFT` / `DONE` / `DEFERRED` / `ABANDONED` slice is **not**
   rendered in the Blocked section and does not count (that misfile is 111-02's
   lint warning, not a board entry).

5. **Omitted when empty.** When no actionable slice is blocked,
   `render_blocked_table` returns the empty string and no `## Blocked slices`
   heading appears — no noise for clean projects (same contract as
   `render_deferred_table`). A board regen on a project with zero blocked slices
   is byte-identical to the pre-slice output.

6. **Regen stays intact.** Adding the Blocked section does not disturb active-table
   Notes preservation, the Deferred/Abandoned sections, the race guard, or
   idempotency. A raw `|` in a `blocked_by:` value or `**Blocked:**` line is
   escaped/handled so it cannot corrupt or glue table rows (the same pipe caveat
   the board already documents).

7. **Host packages regenerated.** `scripts/build_host_packages.py` reproduces
   `hosts/claude/` and `hosts/codex/` with no diff; the committed mirrors carry
   the `blocked_by` reader + `render_blocked_table`.

**Edge cases to cover explicitly:**
- `blocked_by:` present but empty / whitespace-only → treated as unset, not blocked.
- `blocked_by:` on a `DONE` slice → ignored by the board (out of count).
- `blocked_by:` on a `READY_FOR_IMPLEMENTATION` slice → counted (the ready-but-stuck
  case A2 exists for).
- `blocked_by:` set with no `**Blocked:**` body line → "Blocked on" shows the
  frontmatter value.
- `blocked_by:` and a `**Blocked:**` line both present → "Blocked on" shows the
  body line.
- A `|` in the blocked value → escaped; adjacent rows not glued.
- Multiple blocked slices across specs → all listed, file order.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture; the
      edge cases above are covered explicitly.
- [ ] Each new test shown to fail when its feature is removed (mutate → red →
      restore).
- [ ] An explicit test asserts the empty-project byte-identity of the board (AC5).
- [ ] An explicit test asserts a `blocked_by:` on a non-actionable slice is NOT
      rendered (AC4).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred (the typed
      `blocked_by:` vocabulary is already deferred in ADR-0057 — record here if a
      new deferral emerges).

**Non-goals:** the `spec_lint` validation of misfiled `blocked_by:` (slice
111-02); a typed `blocked_by:` vocabulary (deferred, ADR-0057); a
`workflow.py`-level `blocked` query subcommand (the board section is the v1
consumer; add a query only if a consumer needs it); auto-clearing the annotation
on transition (clearing is manual per ADR-0057).

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Glossary/primer: add a one-line **first-class blocker** entry pointing at
      ADR-0057 if this closes the spec.
