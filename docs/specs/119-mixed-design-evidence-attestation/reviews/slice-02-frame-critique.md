---
slice: 119-02 — reject-stale-delivery
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (gpt-6.1-sol; independent pre-implementation critique)
reviewed_at: 2026-10-14T23:58:15Z
prompt_source: review.py frame-critique docs/specs/119-mixed-design-evidence-attestation/spec.md 119-02 docs/decisions/adr-0065-attest-external-policy-verdict-delivered-revision.md
---

VERDICT: pass

REASONING:
WEAKEST ASSUMPTION: read-only revalidation can obtain an authoritative current delivery identity rather than repeatedly hashing an obsolete delivery declaration (`docs/specs/119-mixed-design-evidence-attestation/slice-02-reject-stale-delivery.md:14-22`). COUNTER-ARGUMENT: a stale declaration could leave A's evidence apparently valid after B is deployed, but the draft requires independently determined served-build binding, referenced-byte comparisons and refusal when input closure is unknown (`:26-50`). WHAT WOULD CHANGE MY MIND: a delivery protocol unable to distinguish that situation without evaluator execution, or verification that changes only the declaration rather than genuinely delivering B. RECOMMENDED ACTION: resolve that protocol through the listed DoR and exercise actual A/B delivery; existing DONE composition already calls REVIEWED validation without needing a back-edge (`skills/spec-workflow/workflow.py:941-946`), so the proposed extension has a grounded lifecycle attachment point.

RECONCILIATION NOTES:
No implementation deviations assessed; identity encoding and delivery authority remain deferred alignment work.
