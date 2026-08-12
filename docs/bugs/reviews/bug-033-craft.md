---
bug: 033
pass: craft
verdict: pass
reviewer: reviewer subagent (read-only, fresh context)
reviewed_at: 2026-08-12T01:18:51Z
prompt_source: pr-review skill craft pass
---

Craft: the new reconcile block matches surrounding voice (bold lead-ins, em-dashes, imperative markdown) and preserves ADR-0020 depth (closing "does not soften the pass … a genuinely ungrounded assumption still blocks"). De-person-ified sentence retains "strongest attack" and drops the affect phrases (present only as negative test assertions). Test assertions run against normalize_ws(); AC1/2/3/5 fail on revert; AC4 is a legitimate depth-retention guard. No blast radius on sibling FrameCritiquePromptTests / InvestigationGuidanceTests. Minor: record originally overstated the edit surface (named _FRAME_CRITIQUE_OUTPUT_FORMAT) — corrected to build_frame_critique_prompt only. Verdict: pass.
