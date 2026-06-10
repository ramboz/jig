---
adr: 0024
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (opus 4.8)
reviewed_at: 2026-06-10T00:59:49Z
prompt_source: review.py frame-critique docs/decisions/adr-0024-reference-reframe.md (round 4, post-coverage-gate fix)
---

VERDICT: pass

REASONING:
The single load-bearing assumption — that the motivating failure was a missing re-baseline primitive over the corpus (no operation elevates a moved reference to authoritative + routes the fallout), not merely a vocabulary/authority/prompting gap — is the right diagnosis to attack, and the author has both named it and pre-emptively hardened the actual soft spot underneath it. The frame correctly relocates the real risk from "does reframe re-baseline?" to ENUMERATION COMPLETENESS over settled ground (§2/§4, Assumptions §4), concedes it is the binding risk, refuses to assume it away, and makes it visible and human-gated (coverage statement confirmed at accept) with a first-use un-park trigger (T1). Both probed claims check out against code/ADRs (adr.py:887/936 _gate_frame_critique enforces the Proposed->Accepted gate; ADR-0023 §4 genuinely admits the non-member "capability over the spine" category). The frame survives the strongest attack because its most vulnerable point is already owned, gated, and trigger-backed — not asserted.

SPECIFIC ISSUES:
- Load-bearing assumption: the motivating failure was an ABSENCE-OF-RE-BASELINE-PRIMITIVE problem (corrective = named operation + keystone-ADR authority + disposition discipline) rather than an AGENT-READ / instruction-following problem a named skill won't fix. Strongest counter-reading: the team did drop the design in and did intend a retrofit, yet the agent kept patching — at least as consistent with "the agent under-weighted a non-authoritative file and was never instructed to re-anchor" as with "no operation existed." If the true cause is the READ (the model won't reliably re-anchor even given a keystone ADR + manifest, because the dead premise is woven through prose it treats as settled), the §6 "session executes" step inherits the same failure one layer down — sound drafts, but execution still patches. NOT FATAL: the ADR's correctness rests on corpus-read completeness (§2, Assumptions §4), which it owns and makes visible/gated; and the execution-drift risk is named as the Option-B graduation kill-criterion ("reframes drift even with good drafts in hand -> graduate to a gated member") — so the alternative framing is enumerated and trigger-wired, not ignored. Residual exposure is bounded (n=1, soft skill, parked detection, first-use T1) and cheap to discover post-ship — the n=1 posture ADR-0002/0003 endorses. The frame would only fail if it claimed the skill SOLVES re-baselining; it claims it makes re-baselining EXPRESSIBLE and HUMAN-GATED and parks the hard half honestly — so it passes.

Reviewer: jig:reviewer (opus 4.8). Round 4, post-coverage-gate fix (supersedes round 3; PASS).
