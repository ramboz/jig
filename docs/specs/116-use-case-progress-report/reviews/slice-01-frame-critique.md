---
slice: 116-01 — progress-rollup
pass: frame-critique
verdict: pass
reviewer: reviewer
reviewed_at: 2026-10-03T17:34:01Z
prompt_source: review.py frame-critique docs/specs/116-use-case-progress-report/spec.md 116-01
---

**Round 1 — needs-changes.** Highest-risk assumption: the report shows drift — Unanchored plus the per-use-case listing as "the rabbit-hole signal". On jig's corpus and authoring flow an off-goal spec gets anchored by construction (use cases fitted to the existing specs on 2026-10-03; step 2a's cite/grow prompt; only deliberate infra declines land in Unanchored); lifetime totals answer "how much is done", not "where is current work heading"; the full tree (~150 lines) contradicts "on one screen"; the mis-mapping safeguard needs familiarity the owner lacks. Counting rule itself confirmed grounded (`compute_spec_status` excludes DEFERRED/ABANDONED). Secondary: ADR-0064 claimed the vision wording was approved ahead of AC9.

**Fixes applied:** the in-flight-first alternative was offered to the owner, who kept the full tree (AC1 unchanged) with a narrowed claim (2026-10-03). Spec Overview drops "rabbit-hole signal" and adds "What it is not" (progress view, not drift detector — ADR-0064 bound 5); Assumptions rewritten with a false-anchoring known limit; slice Goal drops "on one screen"; ADR's vision sentence now defers to AC9 (owner approved the wording on 2026-10-03); parked signals in refinement-todo.

**Round 2 — pass.** The frame is now honest and survives the strongest attack; no new likely-wrong assumption. Nits applied: ADR main assumption "drift signal" → "progress view"; "serve" → "cite" in the spec summary and Goal; ledger intro no longer says "Both entries".
