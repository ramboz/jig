---
status: DRAFT
skill: memory-sync
---

# Spec 002: memory-layer

## Overview

The memory layer provides cross-session continuity via a three-tier lookup/persist pattern: hot cache (`CLAUDE.md`), deep storage (`docs/memory/`), and capture (`docs/inbox.md`). It is independent of `scaffold-init` — the `memory-sync` skill self-heals missing memory structure.

Borrows the three-layer architecture from Anthropic's Productivity plugin (May 2026), dropping the task-management framing (jig already has specs for that).

## Explicit non-scope

- No `TASKS.md` flat task list — specs are the source of truth for project work
- No `dashboard.html` Kanban — specs have their own status board
- No external integrations (Asana, Linear, Notion)
- No deep scan of emails / calendar / chats

## SPIDR Analysis

| Technique | Question | Outcome |
|---|---|---|
| P — Path | Explicit sync → auto-trigger → auto-detect? | 3 slices in order |
| D — Data | Hot cache only vs. full docs/memory/ depth? | Covered in 002-02 |
| I — Interface | Batched-at-end vs. mid-response unknowns? | Dogfooding in 002-03 |
| R — Rules | What qualifies as memory-worthy? | Part of 002-02 |
| S — Spike | None required — lookup pattern well-understood | — |

---

## Slice 002-01 — explicit-sync

**STATUS: DONE**

**Goal:** `/jig:memory-sync` works on explicit invocation. User says "remember this" or invokes the skill directly.

**DoR:**
- No prior slice dependency.
- Note: if `docs/memory/` or `docs/inbox.md` don't exist, THIS SLICE CREATES THEM as part of its own execution (self-healing, not a manual prereq).

**Acceptance Criteria:**
1. Invoking `/jig:memory-sync` produces a summary of what was added/changed in memory files.
2. New glossary terms written to `docs/memory/glossary.md`.
3. New learnings written to `docs/memory/learnings.md`.
4. High-frequency terms (≥3 references in a session) promoted to `CLAUDE.md` hot cache.
5. Unresolved items park in `docs/inbox.md`, not in memory files.
6. If `docs/memory/` doesn't exist, the skill creates it before writing.

**DoD:** Same as 001-01. All checked.
- [x] All ACs pass (14 tests, all green)
- [x] Implementer test coverage covering each command + self-healing + regressions
- [x] Reviewed by `reviewer` subagent (verdict: pass with 4 flagged items — 3 fixed, 1 documented as design)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Full round-trip: invoke → files update → summary returned.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **AC #4 "≥3 references" is Claude's judgment, not a helper-tracked counter.** A session-level reference counter would need persistent state across invocations, which is heavier machinery than the value warrants. SKILL.md explicitly tells Claude this is its call.

2. **LIFO bullet order in `promote`.** New Hot Cache entries are inserted right after `### Key terms`, so the most recently promoted term appears first. Intentional: most recently promoted = most likely referenced next. Documented as a SKILL.md gotcha for future revisitation if alphabetical/chronological order proves preferable.

3. **Memory templates are coupled to `summary()` H2 counting.** The glossary/learnings templates use blockquote prose (not H2) for instructional content, so `summary()` can count `^## ` headings as user-added entries. This is a real coupling between template structure and parser logic. Captured in `docs/memory/learnings.md` so future template edits don't silently break the summary.

**Reviewer-flagged fixes applied:**

4. **Unquoted CLI examples in SKILL.md.** Showed unquoted `<name>`, `<definition>` etc. — Claude following the example with content containing spaces or shell metachars would mis-parse or shell-inject. All examples now use double-quotes consistently with an explicit "always quote" note.

5. **`promote` idempotency false-positive risk.** Original check was `f"- **{term}**" in text`, which would falsely match if another bullet's definition prose mentioned the marker (e.g., "see also - **FOO**"). Tightened to a line-anchored regex (`(?m)^- \*\*<term>\*\*`). Added regression test `test_promote_not_fooled_by_prose_mention`.

6. **`add-learning` with empty body succeeded silently.** Now emits a stderr warning when both `--body` and stdin are empty/missing, naming the title that will become a stub.

**Reviewer notes accepted as-is:**

7. **AC #4 verification depth.** The threshold logic isn't tested because it lives in Claude's judgment. `test_promote_writes_to_hot_cache` verifies the write path; the threshold is documented as Claude's call. Consistent with the plan.

**Forward-leaning additions:**

- `summary` command returns counts (not just changes-in-this-invocation) — useful for ad-hoc inspection beyond the AC's "summary of what was added" wording.

**Doc updates from this slice:**

- `docs/memory/learnings.md` extended (template-coupling lesson).
- `templates/docs/memory/glossary.md.template` and `learnings.md.template` rewritten to keep how-to content out of H2 (paragraph-only intros).
- No `architecture.md` changes (memory-sync is a new helper but doesn't redefine module boundaries).
- No ADR required.

---

## Slice 002-02 — lookup-pattern

**STATUS: DRAFT**

**Goal:** Agent follows the hot cache → `docs/memory/` → ask-user → persist lookup pattern automatically, without explicit invocation.

**DoR:** Slice 002-01 STATUS: DONE (write path established).

**Acceptance Criteria:**
1. Unknown term encountered → hot cache (`CLAUDE.md`) checked first.
2. Cache miss → `docs/memory/glossary.md` checked.
3. Glossary miss → agent asks once during current response.
4. Answer persisted: hot cache if term has appeared ≥3 times; glossary otherwise.
5. On subsequent encounters, term resolves without asking.
6. Persistence decision is logged (one-liner) to `docs/memory/learnings.md`.

**DoD:** Same as 002-01.

**Anti-horizontal-phasing check:** ✅ Full round-trip: unknown → asked → persisted → resolved next time.

---

## Slice 002-03 — auto-detect-hooks

**STATUS: DRAFT**

**Goal:** `jig-memory-scan` (UserPromptSubmit) and `jig-task-capture` (Stop) work reliably in practice.

**DoR:** Slice 002-02 STATUS: DONE.

**Acceptance Criteria:**
1. `jig-memory-scan` catches capitalized references not in hot cache or glossary, surfaces them in `additionalContext` for the current turn.
2. `jig-task-capture` catches task-capture language patterns, surfaces triage options at the start of the next turn via `additionalContext`.
3. Both hooks are non-blocking (exit 0 always).
4. Verify `additionalContext` format is correct for both `UserPromptSubmit` and `Stop` events (empirical test — see `docs/refinement-todo.md`).
5. Dogfooding health check: after one week, `jig-memory-scan` firing rate should be 10–40% of prompts. Outside this range → tune heuristic and document in `docs/memory/learnings.md`.

**DoD:** Same as 002-01.

**Anti-horizontal-phasing check:** ✅ End-to-end with real sessions.

---

## Slice 002-04 — reconciliation-integration

**STATUS: DRAFT**

**Goal:** Reconciliation phase includes a memory-sync step.

**DoR:** Slice 002-01 STATUS: DONE. spec-workflow skill must be implemented.

**Acceptance Criteria:**
1. `spec-workflow` reconciliation checklist includes a memory-sync step.
2. `agents/reviewer.md` system prompt explicitly states: "Do not write to docs/memory/ — defining the glossary is not your job."
3. During reconciliation of any spec, new domain terms that emerged during implementation are surfaced for memory-sync.

**DoD:** Same as 002-01.

**Anti-horizontal-phasing check:** ✅ Enhances an existing full-stack flow.
