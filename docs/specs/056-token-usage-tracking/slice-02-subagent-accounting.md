---
status: READY_FOR_REVIEW
dependencies: [056-01]
last_verified:
---

## Slice 056-02 — Subagent accounting (toolUseResult proxy) + orchestrator/subagent split

**Goal:** Extend the report to include delegated-subagent usage — which the
transcripts under-record — using a documented proxy, and split the report into
**orchestrator** vs **subagent** so the ~90/10 cost shape is visible per spec.

**DoR:**
- ✅ 056-01 landed (the report + attribution it extends).
- ✅ Subagent-proxy factor decided (spec Open question — 0.5 / 0.7 / 1.0).

**Acceptance Criteria:**

1. The report parses `Agent`-tool `toolUseResult` records in the attributed
   sessions and estimates each subagent call's cumulative usage as
   `usage.cache_read_input_tokens × totalToolUseCount × <factor>` (factor
   configurable; default per the resolved Open question), summed across calls.
2. Output **splits orchestrator (measured, from `message.usage`) vs subagent
   (estimated, from `toolUseResult`)** token + $ totals, and **labels the
   subagent figure an estimate** — explicitly noting the `toolUseResult`
   records only the subagent's final turn.
3. Subagent totals broken down **by `subagent_type`** (e.g. `jig:reviewer`,
   `jig:implementer`, `general-purpose`, `Explore`).
4. The raw (final-turn-only) `toolUseResult` token sum is also shown alongside
   the proxy, so the reader sees both the lower bound and the estimate.

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Coverage via fixtures with `Agent` `toolUseResult` records: the proxy
      math; the orchestrator-vs-subagent split; per-`subagent_type` breakdown;
      the estimate labeling; a session with no subagents (subagent total 0).
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice the per-spec report shows
the true cost shape (orchestrator vs subagent), closing the measurement gap the
055-motivating analysis exposed — observable in the report output.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the proxy
      formula + factor + the "subagent = estimate" caveat.
- [ ] CLAUDE.md hygiene per spec 025-01 rule.
