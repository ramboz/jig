---
slice: 086-01 — routing-eval harness (collision + trigger + ratchet)
pass: frame-critique
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-07-08T19:02:29Z
prompt_source: review.py frame-critique 086-01 (cycle 3)
---

Adversarial frame-critique (rung-1 fresh-context subagent, general-purpose, Opus-class). Third cycle; PASS.

The frame survives its strongest attack. The highest-risk load-bearing premise
is Assumption 1's deeper form — that lexical TF-IDF overlap on the stripped
positive surface tracks semantic routing fitness (gradient not anti-aligned).
It is honestly conceded as un-probed until the Tier-3 eval, with a manual kill
criterion. The frame survives because the eval's teeth and the action they drive
are robust to that premise being imperfect:

- the trigger top_k hard gate's remediation ("add the missing vocabulary") helps
  the real model router regardless of whether the lexical proxy is aligned; and
- the collision hard gate is nearly inert at the current baseline (max pair 0.22
  vs COLLISION_ERROR 0.75, ~3.4x headroom; the 0.50 WARN is report-only), so it
  exerts no anti-aligned "push the surfaces apart" pressure today.

The residual guarantee (catch a future edit that strips vocabulary a pinned case
encodes, in jig's raise-only-floor gate culture) is narrow but real and cheap.

Known-limitation notes (explicitly NON-blocking per the reviewer):
1. Assumptions 1 and 2 are in tension — Assumption 2's "paraphrase, don't copy
   the description" guard suppresses the case-description lexical overlap that
   Assumption 1's rank-1 mechanism needs for teeth, so a pinned positive's rank
   can ride on one or two tokens against a coarse ~19-doc IDF (brittle both
   ways). This bounds the canary's resolution; it does not invalidate it.
2. Both kill criteria route through a mis-route detector that does not exist
   (.claude/skill-usage.jsonl logs only which skill fired, not the prompt or
   correctness). The spec labels this honestly ("manual, not automatic") and
   does not over-claim; acceptable given the small blast radius.

Prior cycles: cycle 1 raised the boilerplate-in-vector flaw (fixed via
routing_surface) + the self-consistency concern; cycle 2 raised the Overview
overclaim + self-contradictory Assumption 2 + inoperable kill criterion
(addressed by scoping the Overview and restating the assumption honestly).
