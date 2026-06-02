---
status: DONE
dependencies: [055-01]
last_verified: 2026-06-01
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
- [x] All ACs pass; full test suite green. 1683 tests, OK (3 skipped).
- [x] Coverage via **synthetic transcript JSONL fixtures** fed to the hook
      script (mirroring `test_jig_context_check.py`, per Clarification Q4):
      below-threshold ⇒ silent; first crossing of a band ⇒ exactly one nudge;
      re-firing of the same band ⇒ silent; **drop-then-reclimb ⇒ re-armed
      nudge**; crossing a higher band ⇒ nudge; no-assistant-turn / malformed
      transcript ⇒ silent (never throws, never blocks).
- [x] A scaffold-mode test asserts the `UserPromptSubmit` hook lands in the
      generated `settings.json`.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed (4 nits → 1 fixed, 2 documented, 1 cosmetic logged; none blocking).
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred (n/a — no formal deferrals).

**Anti-horizontal-phasing check:** After this slice a developer in a long
session — in the jig repo *or* a scaffolded project — is prompted to compact
or delegate *before* the context balloons, at the start of each turn.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; env-var (`JIG_CONTEXT_GROWTH_WARN_PCT`)
      + band design recorded in the Notes column.
- [x] CLAUDE.md hygiene per spec 025-01 rule (n/a — 055-02 does not close the
      spec; 055-03 / 055-04 remain).

### Deviation log (after reconciliation)

The spec above is preserved. Implementation notes:

1. **What shipped.** Implemented via the `jig:implementer` subagent (strict
   TDD). `jig-context-check.sh` now branches on `hook_event_name`:
   `UserPromptSubmit` runs the new in-session growth nudge; `SessionStart` runs
   the existing baseline check unchanged (pinned by
   `SessionStartNoRegressionTests`). The growth logic lives as pure,
   unit-tested functions in `hooks/scripts/lib/context_fill.py`
   (`read_tail_cache_read_tokens`, `evaluate_growth`, `growth_nudge_for_turn`,
   `growth_nudge_text`); the new env var is **`JIG_CONTEXT_GROWTH_WARN_PCT`**
   (default 0.40, same out-of-range fallback as `JIG_CONTEXT_SOFT_WARN_PCT`).
   Registered under `UserPromptSubmit` in `hooks/hooks.json`; scaffold
   propagation is automatic via `scaffold.py`'s `_build_jig_hook_entries`
   (asserted by a new scaffold-mode test). Suite: 1683 tests, OK (3 skipped).

2. **Dogfooding note.** The implementation (~100K tokens) and all three review
   passes ran in isolated subagents; the orchestrator kept only summaries.

3. **Design resolution (spec Open questions).** The escalation bands are
   **40 / 60 / 80%**; only the **first** band is configurable (via
   `JIG_CONTEXT_GROWTH_WARN_PCT`) — 0.60 / 0.80 are fixed offsets. This
   resolves the spec's "40/60/80 vs. a single threshold" + env-var-name open
   questions. Recorded in the status-board Notes column per Close-out.

4. **Review findings folded in** (compliance + craft both `pass`; evidence in
   `reviews/slice-02-{compliance,craft}.md`):
   - *Fixed (craft nit)* — removed the `0.40` duplication between
     `DEFAULT_GROWTH_THRESHOLD` and `GROWTH_BANDS[0]` (now
     `GROWTH_BANDS = (DEFAULT_GROWTH_THRESHOLD, 0.60, 0.80)`; value unchanged,
     `test_growth_bands_are_40_60_80` still green).
   - *Documented (craft nits)* — added an in-code note on the two
     deferred-by-design choices: the per-session `$TMPDIR` state file is left
     to the OS tmp-reaper (not self-cleaned), and the state read-modify-write
     is unguarded but safe because `UserPromptSubmit` turns are serial within a
     session.

5. **Findings logged, not changed** (non-blocking): the nudge text's `:.0f`
   rounding can read "~40% … past the 40% mark" just over a band (cosmetic).

6. **Plan adherence / impact.** Followed the planned shape; the implementer
   split the logic into `evaluate_growth` (pure) + `growth_nudge_for_turn`
   (I/O) — within the spec's "(your call)" latitude. No conventions impact.
   Architecture: a new hook *event* registration extending spec 026's
   context-fill seam — no module-boundary or public-contract change, so no ADR
   (consistent with `arch_review: false`). Inbox: nothing to park.
