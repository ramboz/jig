---
slice: 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:48:43Z
prompt_source: review.py arch docs/specs/067-reframe/spec.md 067-01 <deliverables>
---

VERDICT: pass

REASONING:
Adds one new public external surface (the /jig:reframe skill) and preserves every documented
module boundary: no `.py` helper (verified no reframe.py), no `transition`, no state machine
— a judgment-only capability over the spine (ADR-0023 §4), consistent with the architecture
doc. The new skills tier-registration public contract is updated in the same change-set
across all canonical surfaces + every pinned-tier guard (no drift, the 065-03 failure mode).
Cross-module calls (adr.py new, workflow.py new) match real argparse/invocation forms and
correctly inherit the frame-critique accept gate. Failure modes handled honestly.

SPECIFIC ISSUES:
- [strength] Front-matter positions reframe as a capability over the spine (no transition/
  state machine), refusing the rejected Option-B reframe.py.
- [strength] New external surface registered consistently across source-of-truth + both
  mirror contracts + all pinned-tier guards — registration-drift fully closed.
- [strength] adr.py new / workflow.py new calls match the real contracts; keystone genuinely
  inherits the frame-critique accept gate.
- [strength] L1 maintenance note discloses the jig-corpus-shaped / configurable-docs-root
  (ADR-0033) seam rather than leaving it silent.
- [nit] L1 class list enumerates the docs/prose corpus; a reframe onto a test-infra/vendor
  reference could touch non-doc boundaries (hooks/, templates/, agents/, scripts/). Scoping
  is defensible (code changes route through retrofit specs), but SKILL.md never states it —
  add a one-line clarification that L1 covers the AUTHORITY-BEARING CORPUS, not the code tree.
- [nit] Forward-references slices 067-02/067-03 (unbuilt) — consistent with jig cross-slice
  linking; log-only.

RECONCILIATION NOTES:
- Both nits land in the deviation log, not blocking REVIEWED. Fold in the L1-scoping one-liner.
- No blockers. The enumeration-completeness concern is by-design owned in ADR-0024 + pressure-
  tested by the separate frame_review pass — out of scope for arch.
