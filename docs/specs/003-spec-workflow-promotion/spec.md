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
