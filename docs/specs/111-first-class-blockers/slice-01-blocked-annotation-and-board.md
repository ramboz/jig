---
status: DONE
dependencies: [adr-0057]
last_verified: 2026-08-15
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
   empty (treated as unset). The `collect_slices` row also carries the extracted
   `**Blocked:**` body line (as the tuple already carries `abandonment_reason`),
   so `render_blocked_table` has both the frontmatter value and the body-line
   prose without re-reading the file.

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
   idempotency. A raw `|` in a rendered "Blocked on" cell is **actively escaped**
   (to `&#124;`) so it cannot corrupt or glue table rows. (This is a deliberate
   improvement on the Deferred/Abandoned tables, which rely on an author-side
   `&#124;` convention rather than escaping — `blocked_by:` is free text and far
   more likely to contain a literal `|`, so the render path escapes it itself.)

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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one fixture; the
      edge cases above are covered explicitly.
- [x] Each new test shown to fail when its feature is removed (mutate → red →
      restore).
- [x] An explicit test asserts the empty-project byte-identity of the board (AC5).
- [x] An explicit test asserts a `blocked_by:` on a non-actionable slice is NOT
      rendered (AC4).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred (the typed
      `blocked_by:` vocabulary is already deferred in ADR-0057 — record here if a
      new deferral emerges).

**Non-goals:** the `spec_lint` validation of misfiled `blocked_by:` (slice
111-02); a typed `blocked_by:` vocabulary (deferred, ADR-0057); a
`workflow.py`-level `blocked` query subcommand (the board section is the v1
consumer; add a query only if a consumer needs it); auto-clearing the annotation
on transition (clearing is manual per ADR-0057).

### Deviation log

Original ACs preserved above. Notes:

- **Frame-critique refined two ACs before implementation (pre-impl pass).** The
  adversarial frame-critique of 111-01 caught that AC6's original "the same pipe
  caveat the board already documents" mis-framed the sibling tables (Deferred/
  Abandoned rely on an author-side `&#124;` convention, they do **not** escape),
  and that the `**Blocked:**` body-line plumbing into `render_blocked_table` was
  unstated. Both were fixed in the ACs: AC6 now mandates **active** `|`→`&#124;`
  escaping in the render path (a deliberate improvement, since `blocked_by:` is
  free text), and AC1 states the `collect_slices` row carries the extracted body
  line. Verdict recorded at `reviews/slice-01-frame-critique.md`.
- **`collect_slices` row grew 7→9 (`+blocked_by, +blocked_line`).** The one
  strict-arity unpack consumer (`_focus_summary`) was fixed with `*_rest` + an
  explanatory comment; `_active_spec_summary` already used `*_rest`;
  `collect_slices` has no external consumers. Every `render_*_table` reads its
  columns index-guarded.
- **Sibling tables intentionally NOT retrofitted.** The Deferred/Abandoned tables
  were left on the author-side `&#124;` convention; only the new Blocked path
  actively escapes. Retrofitting them is out of this slice's scope (noted by the
  compliance reviewer).
- **Craft-review nits addressed.** (1) The stale tuple-width docstrings in
  `render_status_table` / `render_abandoned_table` were updated to name the
  9-tuple. (2) The "9-wide positional tuple → `NamedTuple`/dataclass" future
  refactor was recorded as a deferred decision in `docs/refinement-todo.md`
  (trigger: a 10th field, or a positional-index bug). Verdicts at
  `reviews/slice-01-{compliance,craft}.md`.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/spec-workflow/workflow.py` | `updated` | `BLOCKED_FIELD`, `_extract_blocked`, 9-tuple `collect_slices`, `_BLOCKER_ACTIONABLE_STATUSES`, `render_blocked_table` (active `|` escaping), `_compose_board` wiring; two docstrings refreshed. |
| `skills/spec-workflow/test_workflow.py` | `updated` | New `BlockedSlicesBoardTests` (19 tests) covering every AC + edge case; red→green witnessed. |
| `hosts/claude/**` + `hosts/codex/**` | `updated` | Regenerated by `build_host_packages.py`; `--check` reports in sync (AC7). |
| `docs/refinement-todo.md` | `updated` | Recorded the deferred `NamedTuple` refactor of the `collect_slices` row. |
| `docs/specs/README.md` | `deferred` | Regenerated at close-out (post-DONE step below). |
| `docs/architecture.md` | `no-op` | No module boundary / public-contract change — reuses the existing `collect_slices`/`render_*_table` pattern additively. |
| `docs/conventions.md` | `no-op` | No authoring rule changed (the `blocked_by:` convention is documented in ADR-0057 + the spec, not conventions.md). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Spec 111 still in flight (111-02 open) — no close-out compression due yet. |
| `docs/decisions/` (ADR-0057) | `no-op` | Already Accepted + indexed in the shaping phase. |
| `docs/memory/**` + glossary | `deferred` | The "blocker = annotation on an actionable slice" lesson + a **first-class blocker** glossary entry — folded into `/jig:memory-sync` at spec close-out. |
| `docs/inbox.md` | `no-op` | Nothing resolved or added. |

_Excluded by design: the shaping-phase artifacts (ADR-0057 + its frame-critique,
the rewritten `spec.md`, slice 111-02's planning doc) and this slice's own
review-evidence files (`reviews/slice-01-*.md`) are not implementation drift — the
ADR-0057 `no-op` row accounts for the decision artifact. A `git diff main...HEAD`
on this checkout also surfaces already-merged 096-05 / 107 files because the local
`main` ref lags `origin/main` (onto which this branch was rebased); those are not
changes on this branch._

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] Glossary/primer: add a one-line **first-class blocker** entry pointing at
      ADR-0057 if this closes the spec.
