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

**STATUS: DONE**

**Goal:** Agent follows the hot cache → `docs/memory/` → ask-user → persist lookup pattern automatically, without explicit invocation.

**DoR:** Slice 002-01 STATUS: DONE (write path established). ✅

**Acceptance Criteria:**
1. Unknown term encountered → hot cache (`CLAUDE.md`) checked first.
2. Cache miss → `docs/memory/glossary.md` checked.
3. Glossary miss → agent asks once during current response.
4. Answer persisted: hot cache if term has appeared ≥3 times; glossary otherwise.
5. On subsequent encounters, term resolves without asking.
6. Persistence decision is logged (one-liner) to `docs/memory/learnings.md`.

**DoD:** Same as 002-01. All checked.
- [x] All ACs pass (21 tests, all green — 7 new lookup tests + 1 bare-dir edge case)
- [x] Implementer test coverage including round-trip (add → lookup) and hot-cache-wins-when-both regression
- [x] Reviewed by `reviewer` subagent (verdict: pass with cosmetic notes only)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Full round-trip: unknown → asked → persisted → resolved next time.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **`lookup` subcommand structure.** Output split across stdout (definition + source) and exit code (0=hit, 2=miss) — composable from SKILL.md / Claude's perspective. Makes "Did the lookup hit?" a single shell check, which is more reliable than parsing stdout.

2. **Hot cache wins over glossary when a term is in both.** Hot cache is the user's explicitly elevated terminology; glossary is the auto-collected backlog. The user's elevation is more authoritative. Regression test covers this.

3. **Lookup is loose-on-read, strict-on-write.** The hot-cache extraction regex `[—\-:]?\s*` accepts em-dash, hyphen, or colon as the separator between term and definition. Write paths (`promote`) only ever emit em-dash. This means manually-edited entries (which may use different punctuation) still resolve correctly, while the canonical written form stays consistent.

**AC #6 interpretation (accepted as deviation):**

4. **AC #6 says "Persistence decision is logged (one-liner) to `docs/memory/learnings.md`."** Implementing this literally would pollute `learnings.md` (whose template purpose is "dead ends and gotchas") with routine glossary adds. **The deviation is to interpret "logged" as the helper's existing stdout one-liner** ("glossary: added 'X'", "hot cache: promoted 'Y'"). This is captured by the `jig-telemetry.sh` hook into `.claude/skill-usage.jsonl` whenever invoked via Task. If a stronger audit trail proves necessary later, a separate gitignored `docs/memory/.audit.log` is cleaner than mixing audit data into learnings.md. **Plan.md documents this rationale in advance**, so this is a planned interpretation rather than a post-hoc justification.

**Doc updates from this slice:**

- SKILL.md gains a "Lookup-pattern flow" section with the explicit decision tree and a "do not ask twice" guidance paragraph.
- No `architecture.md` changes (lookup is a read-only addition to an existing module).
- No ADR required.
- No `learnings.md` entry — the deviation is logged in this deviation-log, which is the right home for design rationale (vs. anti-patterns).

---

## Slice 002-03 — auto-detect-hooks

**STATUS: DONE**

**Goal:** `jig-memory-scan` (UserPromptSubmit) and `jig-task-capture` (Stop) work reliably in practice.

**DoR:** Slice 002-02 STATUS: DONE. ✅

**Acceptance Criteria:**
1. `jig-memory-scan` catches capitalized references not in hot cache or glossary, surfaces them in `additionalContext` for the current turn.
2. `jig-task-capture` catches task-capture language patterns, surfaces triage options at the start of the next turn via `additionalContext`.
3. Both hooks are non-blocking (exit 0 always).
4. Verify `additionalContext` format is correct for both `UserPromptSubmit` and `Stop` events (empirical test — see `docs/refinement-todo.md`).
5. Dogfooding health check: after one week, `jig-memory-scan` firing rate should be 10–40% of prompts. Outside this range → tune heuristic and document in `docs/memory/learnings.md`.

**DoD:** Same as 002-01. All checked.
- [x] All ACs pass (19 hook tests, all green)
- [x] Implementer test coverage: both hooks tested for silence/firing/JSON format/exit-0 + heuristic-strip regressions
- [x] Reviewed by `reviewer` subagent (verdict: pass with 3 low-priority watch-notes; none blocking)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ End-to-end with real sessions.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **AC #5 firing-rate health check is a deferred measurement, not a slice-time test.** We have no telemetry data yet — the hooks have been firing on every session since slice 001-01 committed, but their output has never been captured. The 10–40% target requires real session traffic. Plan documents this; refinement-todo.md captures the resolution trigger ("~2 weeks of real session traffic") and a mitigation idea (lightweight `.claude/hook-firing.jsonl` counter file).

2. **Heuristic strips are deterministic, not statistical.** Slice tightened `jig-memory-scan.sh` to strip:
   - Fenced code blocks (` ```...``` `)
   - Inline code spans (`` `...` ``)
   - URLs (`https?://\S+`)
   - Absolute paths (`/word/word/...`)
   Plus an expanded COMMON acronym skiplist (~30 entries) so AI projects don't get spam on `API`, `JSON`, `CLI`, `SDK`, `MCP`, `LLM`, `TDD`, `BDD`, `ADR`, etc.

**Reviewer-flagged watch-notes (folded into refinement-todo's firing-rate entry):**

3. **Schemeless URLs would leak.** `example.com/FooBar` doesn't match `https?://\S+`. Real-world impact is low (most URLs in prompts have schemes); folded into the firing-rate watch-list.

4. **Nested triple-backticks leak middle content.** Non-greedy `.*?` pairs the outermost backticks. Inner content is typically lowercase code anyway, so unlikely to fire false positives.

5. **`CSS` in COMMON skiplist.** Harmless today — the camelCase regex `[A-Z][a-z]+(?:[A-Z][a-z]+)+` requires multi-segment caps, so single-word `CSS` wouldn't fire even without the skiplist. Worth watching as the COMMON set grows.

**AC #4 partial verification (logged as deviation):**

6. **`additionalContext` JSON format is verified at well-formedness level only.** Both hooks emit `{"continue": true, "additionalContext": "..."}`. Tests assert the JSON is parseable and has the expected keys. **Runtime verification — does Claude Code actually inject the context? — is empirical and not testable in CI.** This is consistent with the deviation pattern from slice 002-02's AC #6 (where "log" was interpreted permissively). Documented in plan.md.

**Doc updates from this slice:**

- `docs/refinement-todo.md` gains the firing-rate measurement entry with watch-list.
- No `architecture.md` changes (hooks were architecturally placed back in the starting move; this slice tightens them).
- No ADR required.
- No `learnings.md` entry — the heuristic improvements aren't generalizable lessons, they're slice-specific tuning.

---

## Slice 002-04 — reconciliation-integration

**STATUS: DONE**

**Goal:** Reconciliation phase includes a memory-sync step.

**DoR:** Slice 002-01 STATUS: DONE. ✅ spec-workflow skill must be implemented — ⚠️ partial deferral, see deviation #1 below.

**Acceptance Criteria:**
1. `spec-workflow` reconciliation checklist includes a memory-sync step.
2. `agents/reviewer.md` system prompt explicitly states: "Do not write to docs/memory/ — defining the glossary is not your job."
3. During reconciliation of any spec, new domain terms that emerged during implementation are surfaced for memory-sync.

**DoD:** Same as 002-01. All checked.
- [x] All ACs pass (23 tests, all green — 2 new `IntegrationTests`)
- [x] Implementer test coverage: section-anchored regex confirms memory-sync is *inside* the reconciliation section, not just anywhere
- [x] Reviewed by `reviewer` subagent (verdict: pass with 2 watch-notes; both addressed)
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ Enhances an existing full-stack flow.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **DoR partial deferral: "spec-workflow skill must be implemented" → "encode now, activate later."** The DoR literally required spec-workflow to be a real skill, but it remains a `disable-model-invocation: true` stub (planned for spec 003+). Strict adherence would have blocked 002-04 indefinitely. Instead, the slice embeds the Reconciliation checklist content (including the memory-sync gate item) directly in the stub's SKILL.md. When spec-workflow is later promoted to a real skill, the integration is already specified — no rework. Behavior gated on promotion; content lives now.

2. **AC #1 behavioral verification is deferred.** The test confirms memory-sync is *mentioned inside the reconciliation section* of SKILL.md, but does NOT confirm Claude actually runs memory-sync when reconciling — that requires spec-workflow to be active, which is deferral #1. Analogous to slice 002-03 AC #4 (JSON well-formedness verified; runtime injection deferred).

**Reviewer-flagged improvements applied:**

3. **Test defensiveness tightened.** Original test asserted "reconcil" and "memory-sync" each appear anywhere in the file — a future edit could move memory-sync out of the reconciliation section without failing. Rewrote to locate the reconciliation H2 explicitly and assert memory-sync appears *inside* that section (bounded by the next H2 or EOF). First-attempt regex used the `s` DOTALL flag, which made `.*reconcil` greedy across multiple H2 headers — caught by the test run. Fixed via a two-step approach: `re.search` for the header line, then slice from end-of-header to the next H2.

4. **Reviewer prohibition strengthened with rationale.** Original was a terse "Do not write to docs/memory/". Now reads: "Do not write to docs/memory/ — defining the glossary, capturing learnings, or modifying the hot cache are jobs for the memory-sync skill, run during the reconciliation phase (not review). You may *read* from memory to ground your evaluation in established terminology, but writes are out of scope." Why-driven, not just don't-driven.

**Reviewer notes accepted as design-consistent:**

5. **Reviewer prohibition regex is path-permissive** (matches "docs/memory|memory layer|memory/"). The "memory/" alternative could false-positive on unrelated content. Currently no false positives; cost-of-tightening exceeds cost-of-watching. Acceptable.

**Doc updates from this slice:**

- `agents/reviewer.md`: prohibition expanded with why.
- `skills/spec-workflow/SKILL.md`: new Reconciliation checklist H2 section with **7 gate items** (deviation log, architecture impact, conventions impact, inbox triage, memory-sync, reconciliation review, commit).
- No `architecture.md` changes (this is a content/process integration, not structural).
- No ADR required.
- No `learnings.md` entry — the "encode now, activate later" pattern is already documented from earlier slices.
