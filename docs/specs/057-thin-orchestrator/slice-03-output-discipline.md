---
status: READY_FOR_REVIEW
dependencies: [055-04]
last_verified:
---

## Slice 057-03 — Output discipline (concise delegation prompts + summaries)

**Goal:** Bound the size of what the orchestrator *emits* — the delegation
prompts it writes to subagents and the summaries subagents return — since
output is ~22% of cost-equivalent spend (5×-priced, larger than folklore) per
the 2026-06-03 deep-dive. The **output-volume** lever, sibling to 055-04's
"surface results, not logs" (which kept verbose *Bash* output out of the
orchestrator; this extends the principle to the orchestrator↔subagent boundary).
Added at clarify (2026-06-03, Q4).

**DoR:**
- ✅ 055-04 landed (verbose-Bash containment — the kin mechanism).
- ✅ Deep-dive recorded output at ~22% of cost-equivalent spend (the rationale).

**Acceptance Criteria:**

1. **`docs/workflow.md` gains output-discipline guidance.** Delegation prompts
   are scoped and concise: point the subagent at files/paths to read rather than
   pasting their contents; state the deliverable + the expected return envelope,
   not background prose; prefer pointing a subagent at a prompt *file* over
   inlining a large prompt. A doc-presence test asserts the section.
2. **The subagent return convention is codified.** Reviewers/implementers return
   a tight envelope (verdict / summary / changed-files), not full logs or
   transcripts — extending 055-04's results-not-logs rule to what subagents emit
   back. Captured in the relevant `agents/*.md` guidance.
3. **Soft / non-blocking.** Guidance + agent-prompt conventions only; nothing is
   enforced or gated.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Coverage: doc-presence tests for the workflow.md section and the
      `agents/*.md` return-envelope convention.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, the orchestration guidance
and agent prompts actively keep emitted tokens (delegation prompts + returned
summaries) lean — observable in the conventions, and measurable as a lower
output share via the 056 tracker.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the
      output-volume lever + the 055-04 lineage.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (if this slice closes the spec,
      compress the Active-specs entry).
