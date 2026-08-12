---
slice: 110-03 — put the "no" on the tooling; tone-pass the review bodies
pass: craft
verdict: pass
reviewer: reviewer subagent (fresh context)
reviewed_at: 2026-08-12T03:10:35Z
prompt_source: pr-review skill craft pass (--richer-skill none)
substrate: non-interactive
---

PASS (re-review after fixing the round-1 [blocker]). Both guards non-vacuous: agent-owned refusal narration turns test_no_agent_owned_refusal_narration red; stripping every runnable helper example turns test_invoke_the_gate_imperative_preserved red. Negative-refusal regex well-scoped (subject + refuse/reject/block + advance/proceed/transition, sentence-bounded) and correctly excludes tool-attributed subjects. Nits addressed: invoke-test docstring softened to reflect it is a coarse "some runnable helper example survives" guard (AC5 concedes the suite can't verify invocation); deviation #5 corrected (posture pointer guarded by WorkingPostureSkillPointerTests, not duplicated here).
