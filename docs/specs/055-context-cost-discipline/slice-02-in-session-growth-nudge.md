---
status: READY_FOR_REVIEW
dependencies: [055-01]
last_verified:
---

## Slice 055-02 — In-session context-growth nudge

**Goal:** Give the developer a timely, soft, non-blocking signal *mid-session*
when accumulated orchestrator context has grown past the dumb-zone line, so
they compact or delegate the next read-heavy step before the context
balloons. Directly attacks the ×turns multiplier (the $540 session ran 985
turns with 1 reset, context climbing to 840K).

**DoR:**
- ✅ 055-01 landed (the discipline section + principle the nudge points at).
- ✅ Signal design decided (spec Decisions §2/§3 + Clarifications): extend
  `jig-context-check.sh` to `UserPromptSubmit`, transcript-tail read,
  dumb-zone threshold, per-band rate-limit with re-arm-on-drop, scaffolded
  into target projects.

**Acceptance Criteria:**

1. **`hooks/scripts/jig-context-check.sh` is extended to also fire on
   `UserPromptSubmit`** (one script for both the `SessionStart` baseline and
   the in-session growth check — per Clarification Q2). On each user turn,
   when the current context-size estimate crosses a configurable threshold, it
   emits a soft `additionalContext` nudge recommending `/compact` or
   delegating the next read-heavy step. It **never blocks** (always exits 0,
   never sets `continue: false`).
2. The estimate is read **cheaply from the transcript tail** — the last
   assistant record's `cache_read_input_tokens` — **without scanning the
   whole file**.
3. The threshold defaults to **0.40 of the model context window** (the
   "dumb zone" line), configurable via the existing `JIG_CONTEXT_*`
   convention (reuse `JIG_CONTEXT_WINDOW_BYTES`; add a fraction var with the
   same out-of-range fallback behavior as `JIG_CONTEXT_SOFT_WARN_PCT`).
4. The nudge fires **at most once per threshold band** per session
   (40 → 60 → 80%), tracked in a per-session state file (e.g. under `$TMPDIR`
   keyed by session id). Re-crossing the same band is silent. **The band
   re-arms when the estimate drops back below it** (e.g. after `/compact`), so
   a subsequent climb past it nudges again (Clarification Q3).
5. **Silent and safe** when there is no assistant turn yet, or the transcript
   is missing/unreadable/malformed (never throws, never blocks). Reuses
   `hooks/scripts/lib/context_fill.py` where applicable.
6. The nudge text references the `docs/workflow.md` "Context-cost discipline"
   section from 055-01.
7. **The `UserPromptSubmit` registration is wired into both the plugin's hook
   config and scaffold-init's generated `settings.json`** (Clarification Q1),
   so scaffolded target projects receive the nudge, not just the jig repo.

**DoD:**
- [ ] All ACs pass; full test suite green.
- [ ] Coverage via **synthetic transcript JSONL fixtures** fed to the hook
      script (mirroring `test_jig_context_check.py`, per Clarification Q4):
      below-threshold ⇒ silent; first crossing of a band ⇒ exactly one nudge;
      re-firing of the same band ⇒ silent; **drop-then-reclimb ⇒ re-armed
      nudge**; crossing a higher band ⇒ nudge; no-assistant-turn / malformed
      transcript ⇒ silent (never throws, never blocks).
- [ ] A scaffold-mode test asserts the `UserPromptSubmit` hook lands in the
      generated `settings.json`.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice a developer in a long
session — in the jig repo *or* a scaffolded project — is prompted to compact
or delegate *before* the context balloons, at the start of each turn.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; thresholds/env-var names recorded in
      the Notes column.
- [ ] CLAUDE.md hygiene per spec 025-01 rule.
