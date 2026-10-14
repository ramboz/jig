---
slice: 119-03 — legacy-and-opt-in
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (gpt-6.1-sol; independent pre-implementation critique)
reviewed_at: 2026-10-14T23:58:15Z
prompt_source: review.py frame-critique docs/specs/119-mixed-design-evidence-attestation/spec.md 119-03 docs/decisions/adr-0065-attest-external-policy-verdict-delivered-revision.md
---

VERDICT: pass

REASONING:
WEAKEST ASSUMPTION: a supported legacy producer can furnish renewed, delivery-bound evidence without a Jig-owned adapter (`docs/specs/119-mixed-design-evidence-attestation/spec.md:192-194`). COUNTER-ARGUMENT: historical scalar ledgers may lack that provenance, making the positive compatibility path unavailable; the draft explicitly blocks that path pending genuine producer support rather than fabricating identities or silently downgrading rich requirements (`docs/specs/119-mixed-design-evidence-attestation/slice-03-legacy-and-opt-in.md:15-20,31-40,94-98`). WHAT WOULD CHANGE MY MIND: accepting field absence as version selection, weakening independent compliance, or claiming unbound historical evidence proves current delivery. RECOMMENDED ACTION: retain the genuine legacy sample prerequisite and explicit contract selection; unflagged preservation is grounded in the existing required-pass composition (`skills/_common/review_evidence.py:282-292`).

RECONCILIATION NOTES:
No implementation deviations assessed; legacy capability remains an honest prerequisite, not an established interface fact.
