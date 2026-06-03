---
status: DONE
dependencies: [055-04]
last_verified: 2026-06-03
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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Coverage: doc-presence tests for the workflow.md section and the
      `agents/*.md` return-envelope convention.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (None deferred.)

**Anti-horizontal-phasing check:** After this slice, the orchestration guidance
and agent prompts actively keep emitted tokens (delegation prompts + returned
summaries) lean — observable in the conventions, and measurable as a lower
output share via the 056 tracker.

### Deviation log

- **AC #1 — workflow.md section.** Added `### Keep emitted output lean —
  concise prompts, tight return envelopes` under `## Context-cost discipline`
  in `docs/workflow.md`, placed as the last `###` subsection before the
  `### Worked example: the "$540 session"` — i.e. a sibling to the
  `### Keep verbose command output out of the orchestrator` (055-04) section
  and the `### Run thin` (057-01) section, as the slice directs. Covers:
  point the subagent at files/paths to read rather than pasting contents;
  state the deliverable + return envelope, not background prose; prefer a
  prompt *file* over inlining a large prompt; soft/non-blocking (ADR-0011).
- **AC #2 — agent return convention.** Added a `## Return a tight envelope,
  not a transcript` section to **both** `agents/implementer.md` (after its
  existing "Surface results, not logs" section; also tightened the trailing
  "Output format" to frame the report as the envelope) and `agents/reviewer.md`
  (immediately before its required VERDICT output-format block). Both state the
  subagent returns a tight envelope (verdict / summary / changed-files), not
  full logs or transcripts — explicitly framed as the return-side of 055-04's
  results-not-logs rule and spec 057's output-volume lever.
- **AC #3 — soft / non-blocking.** No gate, hook, or enforcement added. Docs +
  agent-prompt conventions only, as specified.
- **Tests.** Added two doc-presence test classes to
  `skills/spec-workflow/test_workflow.py` (alongside the 057-01
  `SessionPlanDocTests`): `OutputDisciplineDocTests` (workflow.md section
  present + covers scoped prompts / return envelope / prompt file) and
  `AgentReturnEnvelopeDocTests` (envelope convention present in both
  `agents/implementer.md` and `agents/reviewer.md`). All 4 green.
- **No decisions deferred** → `docs/refinement-todo.md` untouched.
- **Post-review reconciliation fix (craft nit).** The craft pass found that
  `test_output_discipline_section_present`'s heading regex (`^###\s+.*output`)
  also matched the pre-existing 055-04 heading "Keep verbose command output out
  of the orchestrator", so it would stay green even if the new 057-03 section
  were deleted (the sibling content test backstopped it, but the heading test
  was looser than its intent). Tightened the regex to pin the 057-03 heading
  (`emitted output` / `output lean`); all 4 tests re-run green. No prose change.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the
      output-volume lever + the 055-04 lineage (row marked **Closes spec 057**).
- [x] `CLAUDE.md` hygiene per spec 025-01 (covered by the shared spec-057
      "Thin-orchestrator discipline" Key-terms entry; Active-specs was "(none)").
