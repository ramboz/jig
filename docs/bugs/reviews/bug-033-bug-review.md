---
bug: 033
pass: bug-review
verdict: pass
reviewer: reviewer subagent (read-only, fresh context)
reviewed_at: 2026-08-12T01:18:51Z
prompt_source: review.py bug-review builder
---

Fix addresses the documented root cause (unconditional adversarial mandate with no grounding-aware off-ramp), not a symptom: the new "Before you block — reconcile first" block supplies all three off-ramps (reconcile-against-linked-accepted-ADR → known residual; wrong-vs-under-documented → cite the grounding; no-absence-claim-without-citation), and the person-directed sentence is re-pointed at the artifact with no residual affect prose. Adversarial depth preserved per ADR-0020. Regression tests bind (AC1/2/3/5 fail on revert; AC4 is a deliberate depth-retention guard). Blast radius clean; VERDICT envelope correctly unchanged; stays within structural_fix. No specific issues.
