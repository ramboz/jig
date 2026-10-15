---
slice: 119-03 — legacy-and-opt-in
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (gpt-6.1-sol; fresh overall-authority framing review)
reviewed_at: 2026-10-15T00:26:51Z
prompt_source: review.py frame-critique docs/specs/119-mixed-design-evidence-attestation/spec.md 119-03 docs/decisions/adr-0065-attest-external-policy-verdict-delivered-revision.md
---

VERDICT: pass

REASONING:
The load-bearing assumption is that a legacy threshold-only producer can supply renewed delivery-bound evidence without Jig inventing provenance or interpreting component success as overall success. The draft makes owner acceptance of that compatibility cost explicit and requires the selected legacy verdict to cover the installed policy, while rejecting namespace confusion and rich-required downgrade (`docs/specs/119-mixed-design-evidence-attestation/slice-03-legacy-and-opt-in.md:15-22,26-45`). Historical/unflagged behavior and independent compliance remain protected; an unavailable genuine legacy path blocks that positive path rather than earning a waiver.

RECONCILIATION NOTES:
No implementation deviations assessed. Legacy producer capability and the compatibility-cost decision remain openly unresolved, not completed commitments.
