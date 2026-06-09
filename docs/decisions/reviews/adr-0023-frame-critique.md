---
adr: 0023
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-09T21:47:43Z
prompt_source: review.py frame-critique docs/decisions/adr-0023-lifecycle-family-spine.md
---

## VERDICT
pass

## REASONING
The single highest-risk load-bearing assumption — "the three lifecycles share a genuine spine, not a superficial resemblance" — is grounded, not asserted: ADR-0016 and ADR-0019 each explicitly state they mirror workflow.py's gate architecture (ADR-0014), reuse _common/, inherit ADR-0011's trust boundary and ADR-0015/049 reservation, de-escalate trivial work, and name an escape seam; ADR-0019 calls itself "same architecture, different backbone." Every contract clause C1–C7 maps to a real, cited source (C5's source ADR-0022 is honestly flagged PARKED / design-intent). The convergence rule's load-bearing fact — that only one of three `transition` implementations exists, so extraction is not yet triggered — verified on disk (workflow.py present; no bug.py / refactor.py / _common/lifecycle.py). The strongest attack (the corroborating rule-of-three is one shipped instance plus two unbuilt designs deliberately written to rhyme, risking over-fit per ADR-0003) is one the author explicitly raises, rules out by choosing contract-only over code, and bounds with kill criteria giving a cheap reversal — so the frame survives.

## SPECIFIC ISSUES
- Residual risk (noted, not a frame defect): "recording the C1–C7 contract now prevents expensive drift, even though 2 of the 3 members (bug.py / refactor.py) are unbuilt designs and ADR-0019 was consciously modeled on ADR-0016." A contract abstracted from one real implementation plus two papers-of-itself could codify author-written resemblance rather than a spine the work independently demanded — ADR-0003's wrong-abstraction trap. Why it does not sink the frame: the ADR explicitly concedes this (Option B con; Assumptions; the "1 concrete → extraction not triggered" posture), ships a prose contract rather than _common/lifecycle.py to avoid it, and the kill criteria ("C1/C2 don't generalize → demote to documented similarity"; "engine fights members at extraction → keep inline-mirroring") give a bounded, cheap exit. If wrong, a governance document is demoted; no code is unwound.
