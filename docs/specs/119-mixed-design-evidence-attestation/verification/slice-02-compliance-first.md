VERDICT: needs-changes

REASONING:
Against parent `15c7af924b8d484d8664f4a0db1ff2455a112855`, AC1–AC3 are supported by independently selected context, pinned run/digest links, meaningful negative tests and the preserved 72-command trace: 36 refusals with the same recorded pass. AC4 correctly reuses existing recording/REVIEWED/DONE validation without evaluator calls or workflow changes, but malformed-root handling has the diagnostic defect below. AC5 demonstrates documentation-only preservation, but genuine changed-build B renewal under the same frozen definition, independent PRE-RESULT context and fresh attestation remains unverified; restoration and synthetic renewal do not satisfy it. AC6's guidance accurately limits the claim to trusted-local consistency, but the outstanding acceptance gap prevents whole-slice DoD clearance.

SPECIFIC ISSUES:
- `docs/specs/119-mixed-design-evidence-attestation/slice-02-reject-stale-delivery.md:99` — **High confidence, acceptance blocker:** genuine B evaluation/attestation is explicitly `not-run`. Supply the required authoritative overall PASS, matching subordinate evidence, independent delivery context and fresh attestation, then demonstrate normal completion; the frozen 6cc baseline cannot substitute.
- `skills/_common/design_bindings.py:145–146` — **High confidence, robustness:** a JSON root containing escaped `\u0000` reaches `Path.resolve()`, which raises `ValueError` on the supported Python 3.9 runtime. Neither this handler nor `freshness_problem` catches it, so recording/checking returns an internal error instead of the required named freshness/renewal diagnostic. Reject control characters before resolution and add a regression covering recording and reuse.

RECONCILIATION NOTES:
Preserve the existing honest AC5 deferral and disposable-mirror/synthetic-prerequisite disclosures. Do not credit byte restoration as renewal or attribute later capture-helper fixes to frozen 6cc evidence. No additional architectural deviation identified; ordered reviews and reconciliation remain pending.
