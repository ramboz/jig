---
slice: 096-01 — config-precedence
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (frame-critique, reshaped onto ADR-0040)
reviewed_at: 2026-07-28T14:57:55Z
prompt_source: review.py frame-critique
---

Frame-critique of reshaped 096-01 (onto ADR-0040) — **pass**. The load-bearing
assumption (config presence is a faithful proxy for "configured skill applied",
AC6 → substrate: config) holds as a deliberate, ADR-0040-disclosed blind spot;
096-01 is the guaranteed floor, the prose-compliance risk lives in 096-03/04.
Grounding verified in-tree. Observations folded in pre-implementation: the
096-01/02 resolution seam is now named (096-01 does not ship admin/plugin-scope
name resolution ahead of 096-02's reviewer-read probe); AC3's code-health path is
net-new wiring (not symmetric with pr/arch), disclosed via the ADR-0010 docstring
correction owed in 096-02. Non-misdirecting; frame survives.
