VERDICT: needs-changes

REASONING:
The reviewed 119-02 implementation supports AC1–4 and AC6: finite rooted read/hash validation, pinned run links, unchanged-pass refusal at REVIEWED/DONE, and explicit trusted-local limits. The root-NUL fix rejects controls before resolution, with meaningful recording/reuse regressions covering actionable refusal and preservation of the previous pass. The inspected evidence supports the 72-command mutation/restoration trace and additional already-DONE checks without evaluator calls. AC5 genuine changed-build renewal remains the sole acceptance blocker identified; restoration, synthetic renewal and frozen 6cc evidence do not satisfy it.

SPECIFIC ISSUES:
- `docs/specs/119-mixed-design-evidence-attestation/slice-02-reject-stale-delivery.md:99` — **High confidence — acceptance blocker:** genuine build-B evaluation and fresh attestation remain `not-run`. Supply an authoritative overall PASS under the same frozen evaluation definition, matching subordinate run/digest evidence, independently selected PRE-RESULT delivery context, and fresh independent attestation demonstrating normal completion.

RECONCILIATION NOTES:
No additional architectural deviation identified. Preserve the controlled-mirror/synthetic-prerequisite disclosures, original frozen evidence and root-NUL correction history. The authorized IN_PROGRESS draft checkpoint is appropriate, but whole-slice PASS/DONE remains unavailable until AC5 and the subsequently required ordered reviews/reconciliation clear.
