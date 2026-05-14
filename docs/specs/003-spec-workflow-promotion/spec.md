---
status: DRAFT
skill: spec-workflow
---

# Spec 003: spec-workflow promotion

## Overview

Promote the `spec-workflow` skill from `disable-model-invocation: true` stub to a real, auto-triggering Tier 0 skill. Codify the workflow we've been running by hand for the entire jig project (11+ slices across specs 001 and 002).

The workflow has stabilized — same shape every slice — so it's time to make the SKILL.md actually drive it rather than describe it.

## Why now

- Slice 002-04 deferred its behavioral activation pending this promotion ("encode now, activate later").
- The status board has drifted from spec.md files multiple times during dogfooding (see refinement-todo entries that mention "status board updates"). A `status-board` regen command would fix this.
- Every state transition has been hand-edited in both `spec.md` and `docs/specs/README.md`. Easy to forget one. A `transition` command eliminates that class of bug.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | Happy-path automation vs. parallel paths (bug-fix workflow)? | Bug-fix workflow → out of scope for this spec |
| I — Interface | One helper script + SKILL.md vs. separate skills per state? | One helper, one skill (consistent with scaffold.py / memory.py pattern) |
| D — Data | Single-spec view vs. multi-spec status board? | Both; bundled into one slice (they share file parsing) |
| R — Rules | Anti-horizontal-phasing check enforced or surfaced? | Surfaced (warn-only) — see slice 003-02 (out of scope here) |
| S — Spike | None required — workflow is well-understood from dogfooding. | — |

## Slice 003-01 — lifecycle-helper

**STATUS: DONE**

**Goal:** `workflow.py` helper with deterministic state transitions and status-board sync, plus SKILL.md promoted from stub to active (auto-triggering).

**DoR:** No prior slice dependency. `spec-workflow` SKILL.md exists in stub form. ✅

**Acceptance Criteria:**
1. `workflow.py transition <spec.md> <slice-name> <new-status>` updates the `**STATUS: <old>**` line for the named slice in the spec file. Refuses invalid status names. Refuses if the slice name doesn't match a slice heading.
2. `workflow.py status-board <project-dir>` walks `docs/specs/*/spec.md`, extracts each slice's name and current status, and rewrites `docs/specs/README.md` with the current table. Idempotent (re-running on already-current board is a no-op).
3. `skills/spec-workflow/SKILL.md` no longer has `disable-model-invocation: true`. Description rewritten to auto-trigger on relevant prompts (creating a spec, transitioning state, reconciling a slice).
4. SKILL.md body is restructured from "when implemented" framing to active instructions: how to author a spec, how to transition through the lifecycle, when to invoke helpers, when to spawn reviewer subagents.
5. Existing IntegrationTests (slice 002-04) still pass — the reconciliation checklist and memory-sync gate must remain intact.
6. SKILL.md still appears in `/` menu for explicit invocation; auto-triggering doesn't require the user to remember the slash command.

**DoD:** Same as 001-01. All checked.
- [x] All ACs pass (16 workflow tests, all green; 23 memory + 19 hook + 62 scaffold tests all green = 120 total, no regressions)
- [x] Implementer test coverage including a real-world fragment-matching test (`001-01` → `## Slice 001-01 — greenfield-scaffold`)
- [x] Reviewed by `reviewer` subagent (verdict: pass with 3 watch-notes — 2 captured as SKILL.md gotchas, 1 deferred to refinement-todo)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ End-to-end: user describes new work → SKILL.md guides them through the lifecycle → workflow.py automates the deterministic state mutations → real value delivered start to finish.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Dogfood-driven course corrections:**

1. **Convention drift caught by dogfooding.** First run of `workflow.py status-board` against jig itself reported "9 slices across 2 specs" — spec 003's slices were missing. Root cause: spec 003 used `**Slice 003-NN — name**` bold paragraphs instead of `## Slice 003-NN — name` H2 headings (the format used by specs 001 and 002). Reformatted spec 003 to match. **The dogfooding immediately surfaced a convention inconsistency that hand-edits had let slide.** This is exactly the value the slice was supposed to deliver — encoding the convention in tooling reveals where the convention drifted.

2. **Notes-preservation feature added beyond the plan.** Initial regen wiped curated Notes ("47 tests green; reviewed + reconciled", "Tasks at [...]") — a real loss of value. Added a `parse_existing_notes` step that builds a `(spec_dir, slice_label) → notes` map from the existing table and re-emits notes in the regenerated table. Added `test_status_board_preserves_existing_notes` regression test. **AC #2's idempotency now depends on this behavior** — without it, re-running on a curated board would change content (wipe notes) and break the idempotency contract.

**Reviewer-flagged improvements applied:**

3. **Pipe-in-Notes edge case documented.** `parse_existing_notes` regex always anchors to the last `|` on each line, so a Notes cell containing a raw `|` (markdown link `[a|b](url)` or code span `` `a|b` ``) would truncate the cell during preservation. Added a SKILL.md gotcha advising `&#124;` or rephrasing.

4. **`## Spike` headers are intentionally excluded from lifecycle transitions.** `find_slice_section` matches only `## Slice ...` headers. Spikes are research artifacts, not lifecycle-managed work items, and have no `**STATUS:**` marker the helper could transition. Added a SKILL.md gotcha making this exclusion explicit (so future spike authors don't try `transition` and get a confusing "not found").

**Reviewer notes deferred to refinement-todo.md:**

5. **Atomic writes across all helper scripts.** `workflow.py`, `scaffold.py`, and `memory.py` all use `Path.write_text()` directly — non-atomic. Probability of torn writes is low (single-call CLIs in milliseconds) but the impact is "lose state." Added a unified refinement-todo entry suggesting a shared `atomic_write_text(path, content)` helper using `os.replace()` for POSIX-atomic same-FS rename. Resolution trigger: "first report of a torn-write incident, OR before jig ships outside personal-dev use."

**Forward-leaning additions:**

- Status board preamble in `docs/specs/README.md` now self-documents the regen behavior ("Maintained by `workflow.py status-board` — re-run any time...").

**Doc updates from this slice:**

- `skills/spec-workflow/SKILL.md`: full rewrite from stub to active. Frontmatter `disable-model-invocation: true` removed. Body restructured into "Creating a new spec / Picking up a slice / After implementation / Reconciliation / Closing the slice" sections with concrete `workflow.py` invocations at each phase.
- `docs/refinement-todo.md`: new entry for atomic writes across all helpers.
- `docs/specs/README.md`: preamble updated, Notes column re-curated.
- No `architecture.md` changes (no new module boundaries — workflow.py is colocated with its skill, same pattern as scaffold.py / memory.py).
- No ADR required (the helper architecture mirrors precedent).
- No new `learnings.md` entry — the convention-drift dogfood signal (item #1) is captured here in the deviation log; if it recurs across multiple slices a generalizable lesson is worth elevating.

---

## Slice 003-02 — anti-horizontal-phasing-check

**STATUS: DRAFT** _(deferred; not part of this session)_

**Goal:** `workflow.py check <spec.md>` parses each slice and warns if it appears to be horizontal phasing (no user-facing layer touched).

Deferred because the detection heuristic (what counts as "user-facing layer touched"?) needs more dogfooding signal before encoding.

---

## Slice 003-03 — new-spec-scaffolding

**STATUS: DRAFT** _(deferred)_

**Goal:** `workflow.py new-spec <number> <name>` creates `docs/specs/NNN-name/` with `spec.md`, `plan.md`, `tasks.md` skeleton files pre-filled with the conventional structure.

Deferred — the current manual `mkdir` + `Write` flow works; this is convenience, not necessity.

---

## Slice 003-04 — auto-tick-review-passed-on-transition

**STATUS: DONE**

**Goal:** Extend `workflow.py transition` so that the two review-passed
DoD checkboxes — `"Implementation review passed"` and
`"Reconciliation review passed"` — are ticked automatically by the
appropriate lifecycle transition, never by the implementer. The
implementer never manually edits those two boxes; running the
transition IS the tick. This makes the pre-tick anti-pattern that
recurred across slices 007-01, 008-03, and 011-02
([inbox 2026-05-13, DoD pre-tick anti-pattern](../../inbox.md))
structurally impossible: there's no manual edit window in which to
get the ticking out of order.

### Why now

- **Three slices in a row hit the anti-pattern.** Each one logged it
  as a deviation. The lesson clearly isn't sticking via
  retrospective notes — durable fix needed.
- **The transition helper already exists** (slice 003-01,
  `workflow.py transition`). Adding box-ticking on specific
  transitions is a small extension, not a new helper.
- **The two relevant transitions have unambiguous semantics.** A
  slice transitions to `REVIEWED` only after implementation review
  passes; it transitions to `RECONCILED` only after reconciliation
  review passes. Coupling each box to its gating transition is
  natural — there's no other point in the lifecycle when those
  ticks are correct.

### DoR

- ✅ Slice 003-01 (`workflow.py transition`) is DONE.
- ✅ The pre-tick recurrence is documented across three slices'
  deviation logs (007-01 §X, 008-03 §8, 011-02 §10).
- ✅ The inbox entry [2026-05-13 DoD pre-tick anti-pattern](../../inbox.md)
  lists candidate (a) (artifact-evidence check) and explicitly
  flags (b) (move to close-out) as breaking the lifecycle. This
  slice picks neither (a) nor (b); it picks a simpler third
  option: auto-tick on transition.
- ✅ No new dependencies — `workflow.py` is pure Python, no
  external libraries.

### Anti-horizontal-phasing check

This slice is vertical: the *user* is the slice implementer; the
user-observable outcome is that after running
`workflow.py transition <spec> <slice> REVIEWED` (or `RECONCILED`),
the corresponding DoD box is ticked in the spec file without any
additional action. The transition helper IS the user-facing surface
that delivers the change end-to-end — no separate UI / skill / hook.

### Acceptance Criteria

1. **Transition IN_PROGRESS → REVIEWED auto-ticks
   "Implementation review passed".** The helper finds the slice's
   DoD section, locates a checkbox whose label matches (case-
   insensitive) the substring "implementation review passed", and
   flips `- [ ]` to `- [x]`. If no matching line exists, the
   transition still succeeds — auto-tick is best-effort, not a
   gate. If the box is already ticked, no-op (idempotent).

2. **Transition REVIEWED → RECONCILED auto-ticks
   "Reconciliation review passed".** Same shape as AC #1, with the
   label substring "reconciliation review passed".

3. **Other transitions do NOT auto-tick.** `DRAFT →
   READY_FOR_REVIEW`, `READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION`,
   `READY_FOR_IMPLEMENTATION → IN_PROGRESS`, `RECONCILED → DONE`,
   and any backwards transitions (e.g. `RECONCILED → REVIEWED`)
   leave checkboxes alone. The auto-tick fires only on the two
   forward transitions that gate on a review verdict.

4. **Auto-tick is scoped to the target slice's DoD section.** If
   the spec has multiple slices, only the named slice's checkboxes
   are touched. Box-text-matching looks for the checkbox between
   the `## Slice <name>` heading and the next `## ` heading (or
   EOF). The `### Close-out (post-DONE)` subsection inside the
   slice is skipped (already-skipped by slice-land's check_dod
   convention; auto-tick honors it too).

5. **Multiple matching boxes in the same DoD trigger a warning, not
   silent multi-tick.** If a slice's DoD has more than one box
   matching "implementation review passed" (case-insensitive
   substring), the helper emits a stderr warning naming the spec
   and slice, ticks none of them, and the transition still
   succeeds. This avoids accidentally flipping boxes in
   non-canonical DoDs.

6. **Tests cover the happy path, idempotency, scoping, and the
   no-matching-line case.** At least 6 new tests in
   `test_workflow.py`:
   - `test_transition_to_REVIEWED_auto_ticks_implementation_review`
   - `test_transition_to_RECONCILED_auto_ticks_reconciliation_review`
   - `test_other_transitions_leave_checkboxes_alone`
   - `test_auto_tick_is_idempotent`
   - `test_auto_tick_skips_close_out_subsection`
   - `test_auto_tick_warns_on_multiple_matches_and_skips`
   - `test_auto_tick_noop_when_label_absent`

7. **Existing `transition` behavior is unchanged.** The `STATUS:
   <new>` marker flip continues to work exactly as before; the
   16 existing workflow tests stay green. Auto-tick is an
   additional side effect, not a replacement.

8. **CLAUDE.md `Skills in this repo` table and
   `agents/implementer.md` DoD discipline section are updated** to
   reflect that "Implementation review passed" and
   "Reconciliation review passed" are now auto-ticked. The
   implementer no longer manually edits those two boxes.

### Definition of Done

- [x] AC #1 — IN_PROGRESS → REVIEWED auto-ticks "Implementation
  review passed".
- [x] AC #2 — REVIEWED → RECONCILED auto-ticks "Reconciliation
  review passed".
- [x] AC #3 — other transitions leave checkboxes alone.
- [x] AC #4 — auto-tick scoped to the target slice's DoD,
  excluding Close-out subsection.
- [x] AC #5 — multiple matches warn + skip + still transition.
- [x] AC #6 — 9 new tests in `test_workflow.py`, all green (AC said "at least 6"; landed 9).
- [x] AC #7 — existing 16 workflow tests still green.
- [x] AC #8 — CLAUDE.md skills table + `agents/implementer.md`
  DoD discipline updated.
- [x] Full test suite green (current baseline 362).
- [x] Implementation review passed (auto-ticked by transition).
- [x] Deviation log written under "### Deviation log (003-04)".
- [x] Reconciliation review passed (auto-ticked by transition).

### Deviation log (003-04)

**1. First slice to dogfood the auto-tick on its own DoD.** When I
transitioned `003-04` from IN_PROGRESS → REVIEWED via
`python3 workflow.py transition`, the helper auto-ticked
"Implementation review passed (auto-ticked by transition)" at
spec.md:236 without any manual edit on my part — the load-bearing
behavior change works end-to-end against a real slice. The
reconciliation box will get auto-ticked when this slice transitions
REVIEWED → RECONCILED at the close of this reconciliation pass.

**2. Implementation review caught an under-spec'd warning surface.**
First review pass returned `needs-changes` with three findings:
(a) AC #5's stderr warning must "name the spec and slice," but the
initial implementation only named the label substring; (b) the
companion test under-verified AC #5 — it asserted only that
"multiple ... implementation review passed" appeared in stderr,
not that the spec basename and slice fragment did; (c) a typo
("the only tickerstops") in `agents/implementer.md:52`. All three
fixed in the same pass:
- The warning is now composed in `transition()` with full context:
  `warning: <spec.md path>: slice <slice-name>: multiple matches
  for 'implementation review passed' in slice DoD; ...` —
  see `workflow.py:120-126`.
- The test now asserts `"spec.md"` and `"009-99"` both appear in
  stderr alongside the original "multiple" + label match.
- The typo became "the sole ticker stops" — same meaning,
  parseable English.

**3. Scope discipline — went 50% over AC #6's minimum on tests.**
AC #6 listed 6 expected test names plus an implicit "at least 6";
the slice landed with **9 new tests** in
`AutoTickReviewPassedTests`:
   - happy path for each of the two gating transitions (2),
   - other-transitions and RECONCILED-→-DONE no-re-tick (2),
   - idempotency (1),
   - Close-out exclusion + cross-slice scoping (2),
   - multiple-matches warn behavior (1),
   - no-matching-label no-op (1).
The two extras (RECONCILED → DONE no-re-tick + cross-slice
scoping) probe two specific edge cases the spec hinted at without
naming. Kept because they're cheap and pin specific failure modes
the implementation could regress into. Spec text wasn't updated to
match — the AC #6 wording said "at least 6," which 9 satisfies.

**4. `_auto_tick_review_box` is "best-effort" by design.**
A slice whose DoD doesn't include the canonical "Implementation
review passed" / "Reconciliation review passed" label still
transitions cleanly — the auto-tick simply finds nothing and
returns the section unchanged. This is the right behavior for
historical slices that pre-date the convention and for non-canonical
DoDs in external projects. Tests cover the no-op case
(`test_auto_tick_noop_when_label_absent`).

**5. `_CLOSE_OUT_RE` is duplicated, not extracted.** The Close-out
regex pattern is now defined in BOTH `workflow.py:39` AND
`skills/slice-land/land.py:112`. ADR-0003's three-callers-then-
extract trigger isn't met yet (still only two callers); the inline
comment in workflow.py reminds future readers to keep the two in
sync. When a third caller needs the same pattern, extract to
`_common/parsing.py` then.

**6. Test suite green at 371.** Pre-003-04 baseline: 362.
Net change: +9 (all in `AutoTickReviewPassedTests`). Total: 371.
No regressions in the existing 16 spec-workflow tests (AC #7
verified by running the full discover).

**7. Spec was skipped through DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION
in one move.** I authored 003-04 directly at `READY_FOR_IMPLEMENTATION`
without a separate spec-review pass, then transitioned to
`IN_PROGRESS`. The lifecycle states `READY_FOR_REVIEW` were skipped
entirely. Defensible for a small extension to an existing helper
with a clear precedent (mirrors how slice 011-01 ran), but worth
naming so reviewers don't have to reconstruct it.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache `Active specs` block updated.
- [x] Inbox entry [2026-05-13 DoD pre-tick anti-pattern] marked
  RESOLVED with a reference back to this slice.
