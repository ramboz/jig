---
slice: 083-06 — Widen the load-bearing-decision judgment prompt in BOTH session-end surfaces
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-26T19:45:29Z
prompt_source: review.py implementation/pr-review 083-05+06 (paired), read-only jig:reviewer
---

Compliance pass (jig:reviewer, Opus, read-only). Slice 083-06: implementation PASS on all four ACs — both reconcile checklists (docs/workflow.md, spec-workflow/SKILL.md) and the memory-sync prompt carry verbatim ADR_TRIGGER with correct judgment/escape-hatch framing; four-site drift test green; host copies match. The reviewer's sole needs-changes was a sequencing gap: slice DoR/DoD require ADR-0031 Accepted while it was still Proposed. RESOLVED: ADR-0031 transitioned Proposed→Accepted (2026-06-26) after its frame-critique passed; gate cleared. Reviewer also correctly noted NOT to compress spec 083's Active-specs entry — 083-07/083-08 remain.
