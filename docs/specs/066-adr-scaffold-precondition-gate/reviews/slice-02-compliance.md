---
slice: 066-02 — adr-skill-step0-precondition
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T18:06:16Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All five ACs are met. The adr-workflow SKILL.md "Author a new ADR" section (lines 43-69) gains a
Step 0 precondition that confirms scaffold state before reserving/drafting, routes
greenfield->/jig:scaffold-init and adoptable->/jig:migrate, points at adr.py new's own
classify-and-route (066-01) without restating the heuristic, names the docs/decisions/-skeleton
anti-pattern with "never invent the structure by hand," and notes the JIG_SCAFFOLD_PRECONDITION=0
bypass — a faithful mirror of the shipped 063-02. The guard test (test_workflow_contract.py
AdrWorkflowStep0Precondition) and the scaffold-parity test (test_scaffold_mode.py) both pass
against the real files, isolate the correct section, and exercise each AC; the full contract suite
and WithMachineryTests are green with no regressions. The central AC2 invariant — prose and
deterministic gate "agree by construction" — is verified: 066-01 is DONE and adr.py:686-702
implements exactly the greenfield/adoptable/scaffolded routing the prose describes.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- No code/approach deviation: the implementation follows the spec's stated approach (SKILL.md Step 0
  + guard test + scaffold parity) exactly; the deviation log can record "no deviations" beyond the
  by-design anti-pattern noun (docs/decisions/ skeleton vs 063-02's slices/).
- Minor (mirrors 063-02 by design, not a defect): AC2's negative assertion only forbids the literal
  "3-of-4 / three of four" phrasings, so a differently-worded future heuristic restatement wouldn't
  trip it; the positive assertions carry the real weight.
- Close-out housekeeping: spec.md Decomposition still shows both slices DRAFT — refreshes when the
  status board regenerates at close-out.
