---
status: DONE
tier: standard
severity: low
claimed_by: claude/fervent-shannon-da9219
regression_test: skills/bug-fix/test_bug.py::TerminalSegregationTests::test_escalated_bug_rendered_under_terminal_section
main_repro_checked_at: 2026-07-06
main_repro_ref: origin/main@6cee6d1
main_repro_result: reproduces
red_confirmed_at: 2026-07-06
green_confirmed_at: 2026-07-06
fix_class: observability
security_surface: false
escalated_to:
---

# Bug 004: terminal-status-legibility

Reported as [issue #76](https://github.com/ramboz/jig/issues/76).

## Symptom

A bug in a terminal non-`DONE` state (`ESCALATED` — correctly escalated to a
spec that then shipped; or `RESOLVED_ON_MAIN`) is repeatedly misread — across
separate sessions — as "stale: never got flipped to `DONE`." The escalation
worked exactly as designed and the record is closed, but nothing in the
surfaced artifacts signals closure, so it keeps looking like open work someone
forgot to finish. An agent (or a human skimming) pattern-matches "status is
not `DONE`" → "needs to become `DONE`," when `ESCALATED`/`RESOLVED_ON_MAIN`
are in fact terminal.

## Repro

1. Escalate a bug: `bug.py escalate NNN` → record goes `ESCALATED`, board
   regenerated.
2. Open `docs/bugs/README.md`. The escalated row sits inline in the single
   flat table among active `REPORTED`/`DIAGNOSING` rows, with blank
   `reproduces?` / `regression test` columns.
3. Ask "is this bug done or still open?" — unanswerable at a glance; the only
   strong signal is one word in the `status` column.

Contrast: `docs/specs/README.md` splits terminal-but-not-DONE slices into
`## Deferred slices` / `## Abandoned slices` sections — closure is legible
there.

## Evidence

- `skills/bug-fix/bug.py:857` `_render_board` emits one flat table for **all**
  rows; it never branches on status class.
- `skills/bug-fix/bug.py:53` `OPEN_STATUSES` already exists (the six active
  states) — the machine-readable seam for "open vs closed" is present but the
  renderer ignores it.
- `skills/spec-workflow/workflow.py:1678` (`_DEFERRED_HEADING`) / `:1715`
  (`_ABANDONED_HEADING`) / `:1750` (`regenerate_status_board`) — the spec
  board already segregates terminal-non-DONE rows into dedicated sections.
  This is the parity precedent.
- `skills/bug-fix/SKILL.md` `## Gotchas` — bullets exist for the `→ FIXING`
  gate, `tdd.py` exit codes, bypass env vars, "escalate don't grind," and
  "never spawns subagents"; **none** states that `ESCALATED`/
  `RESOLVED_ON_MAIN` are terminal. The lifecycle diagram implies it; nothing
  says it where a reader second-guessing a record's state would look.
- `skills/bug-fix/bug.py:809` — escalation *does* stamp `escalated_to: NNN`,
  and the board has an `escalated_to` column. So an `ESCALATED` row is not
  byte-identical to a `REPORTED` one — but that lone populated cell is easy to
  overlook, and `RESOLVED_ON_MAIN` populates nothing distinguishing.

## Hypotheses

- [x] **(leading) Structural — the renderer:** `_render_board` predates/omits
  the terminal-segregation pattern the spec board established, so
  terminal-non-DONE rows render inline among active rows with no visual class
  marker. *Confirm:* `_render_board` has no status branching; the spec board
  does (`_DEFERRED_HEADING`/`_ABANDONED_HEADING`). *Falsify:* if the board
  already emitted a terminal section, the symptom couldn't arise. → Confirmed
  by the evidence above.
- [ ] **(rejected) Blank columns:** the confusion is really about the *blank
  fix/test columns* being ambiguous — so the fix would be to populate/annotate
  those columns rather than re-position the rows. *Falsify:* `escalated_to`
  IS populated on escalation (`bug.py:809`), yet the misread still recurred
  across sessions per the report — so column *content* is not the lever;
  row *position/labeling* (does this row belong to "open work"?) is. An
  `ESCALATED` row with every column filled still pattern-matches as
  in-progress while it sits in the active table.
- [ ] **Docs half (independent):** even a perfectly-segregated board doesn't
  help a reader reasoning about a single record in isolation. The
  `## Gotchas` section is where that reader looks, and it never encoded the
  terminal invariant. *Confirm:* grep `## Gotchas` — no terminal bullet
  (confirmed).

## Root cause

Two coordinated omissions, both in the *process that produces the artifacts*,
not in any one bad row:

1. **Renderer:** `_render_board` never grew the terminal-state segregation
   that `workflow.py`'s spec board has. The `OPEN_STATUSES` seam that would
   drive the split already exists but the renderer doesn't consult it, so
   `ESCALATED`/`RESOLVED_ON_MAIN` rows are visually indistinguishable from
   active work.
2. **Docs:** `skills/bug-fix/SKILL.md` `## Gotchas` never stated the invariant
   that `ESCALATED`/`RESOLVED_ON_MAIN` are terminal (closed, not unfinished),
   so a reader second-guessing a record has no authoritative one-liner to
   consult.

Neither is a symptom-patch: the board fix teaches the renderer the
open/closed distinction it already half-knows via `OPEN_STATUSES`, and the
docs fix encodes a standing invariant.

## Fix class

`observability` — the fix surfaces already-correct state legibly. It changes
no bug-fixing behaviour and adds no runtime guard; it teaches the renderer the
open/closed distinction it already half-knows (`OPEN_STATUSES`) and encodes the
terminal invariant in the docs.

## Fix

Two coordinated changes, mirroring the spec board's precedent:

1. **`skills/bug-fix/bug.py` — `_render_board`:** add
   `TERMINAL_NON_DONE_STATUSES = {"ESCALATED", "RESOLVED_ON_MAIN"}` and split
   rows into active (everything else, including `DONE`) vs terminal-non-DONE.
   Render the active table as today; when any terminal-non-DONE rows exist,
   append a `## Terminal — closed (not fixed as bugs)` section with an
   explanatory blockquote and a **same-shape** table (identical 10 columns).
   Same shape keeps `_parse_existing_notes` working unchanged (its regex scans
   the whole file for 7-inner-column rows, so notes survive in either table)
   and preserves severity/tier/escalated_to at a glance. When there are no
   terminal-non-DONE rows the section is fully omitted (no empty heading) —
   parity with `render_deferred_table`/`render_abandoned_table`. `DONE` stays
   in the active table (terminal-*success*, never the confusing case), matching
   how the spec board keeps `DONE` inline and only splits `DEFERRED`/
   `ABANDONED`.

2. **`skills/bug-fix/SKILL.md` — `## Gotchas`:** add a one-line bullet stating
   that `ESCALATED`/`RESOLVED_ON_MAIN` are terminal — a bug in a terminal
   non-`DONE` state is closed, not unfinished; its blank fix/test columns are
   expected; don't flag it stale or advance it to `DONE`.

## Already tried

## Regression test

`skills/bug-fix/test_bug.py::TerminalSegregationTests` — asserts (a) an
`ESCALATED` bug renders under a `## Terminal` heading, positioned *after* the
active table, while an active `REPORTED` bug stays above it; (b) a
`RESOLVED_ON_MAIN` bug is likewise segregated; (c) with only active bugs, no
`## Terminal` heading is emitted; (d) a curated Note on a terminal row survives
regeneration (migrated from a flat inline row into the terminal section). Fails
red on trunk (flat single-table renderer emits no terminal heading).

## Proof

- `TerminalSegregationTests` (5 tests) green; the named regression test is red
  on trunk (`## Terminal` heading absent from the flat renderer) and green
  after — `red_confirmed_at` stamped by the `→ FIXING` gate, `green_confirmed_at`
  by `→ REVIEWED`.
- Full jig suite green: `Ran 3369 tests … OK (skipped=6)`, `pyright: clean`.
- `uvx ruff check .` clean; host-package drift regenerated (`SKILL.md` + `bug.py`
  mirrors into `hosts/claude` + `hosts/codex`) and back in sync.
- Visual smoke of a mixed board confirmed: active table (REPORTED + DONE
  inline), then a `## Terminal` section with the explanatory blockquote and the
  ESCALATED/RESOLVED_ON_MAIN rows, curated Note preserved.

## Deviations

- Record prose (Fix §1) described the status set as a plain `{...}` literal; the
  implementation uses `frozenset({...})` (immutability strengthening, no
  behavioral change). Flagged by the bug-review pass.
- Added `test_all_terminal_renders_empty_active_table` after the craft pass
  noted the all-terminal → empty-active-table edge was unasserted. Non-blocking
  coverage strengthening.

## Learning

A terminal-but-not-success lifecycle state needs its surfaced artifact (the
status board) to make closure legible — a distinct status *value* isn't enough
when blank columns pattern-match as open work. The spec board already had the
pattern (`Deferred`/`Abandoned` split); the bug board should have inherited it.
Recorded in [docs/memory/learnings.md](../memory/learnings.md). Tooling note:
the `.jig/test-command` runner ignores the appended selector and runs the full
suite + `uvx pyright`, so the red→green gate here is repo-wide.

## Main recheck

- 2026-07-06 - `origin/main@6cee6d1` -> reproduces: origin/main _render_board (bug.py:857) is a single flat loop with no status branching; SKILL.md ## Gotchas has no ESCALATED/RESOLVED_ON_MAIN terminal bullet. Both defect surfaces present on trunk.
