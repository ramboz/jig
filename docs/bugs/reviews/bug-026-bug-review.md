---
bug: 026
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-02T03:23:17Z
prompt_source: review.py bug-review docs/bugs/026-grounding-rule-misses-reconciliation.md skills/spec-workflow/SKILL.md skills/spec-workflow/test_workflow.py
---

Independent bug-review pass (read-only reviewer subagent, fresh self-contained
prompt built by `review.py bug-review`).

VERDICT: pass

The fix addresses the documented root cause — ADR-0020 §1's grounding rule was
wired only into spec-authoring step 6 and never reached the reconciliation
checklist — by extending the reconciliation "Architecture impact" item with the
same probe-or-`file:line` grounding requirement, cross-referencing ADR-0020 §1
and step 6. `fix_class: guardrail` is honestly labelled: preventive-discipline
extension plus a drift/presence regression test, no runtime logic, no symptom
patch.

The regression test is correctly scoped: `_reconciliation_section` slices from
`## Reconciliation checklist` (SKILL.md:686) to the next `##` heading, which
structurally excludes spec-authoring step 6 (SKILL.md:254); the pinned clause
"executed probe or a `file:line` citation" is absent on origin/main (grep → 0),
so it is genuinely red-before / green-after. Host mirrors are correctly
byte-identical. Both self-citations verified against source (ADR-0020 §1 →
adr-0020:77; step 6 → SKILL.md:254).

Item raised and ADDRESSED after the pass: the record's `## Proof`, `## Learning`,
and `green_confirmed_at` were empty at review time (status FIXING) — now filled
(`## Proof` red/green evidence; `## Learning`; the green stamp lands on the
`→ REVIEWED` transition).

Reconciliation notes (non-blocking): (1) the clause is a verbatim restatement of
step 6's rule rather than single-sourced like the adjacent ADR-0031 "Load-bearing
decision" item — a deliberate deferral to keep PR #164's maintainer-approved
wording faithful, disclosed in the record's "Already tried"; (2) the presence
test pins prose, so a meaning-preserving reword would turn it red — acceptable
and intended for a canonical-wording drift guard (now called out in a test
comment).
