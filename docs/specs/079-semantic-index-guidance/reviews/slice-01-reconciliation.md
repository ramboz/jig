---
slice: 079-01 — workflow.md index guidance
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T15:40:25Z
prompt_source: review.py reconciliation
---

VERDICT: pass

REASONING:
Every deviation-log claim checks out against the files. The ctags reword is present verbatim in docs/workflow.md; the test uses the distinctive "lsp" token (not bare "ide") and scopes the "when" assertion to the new subsection via the _subsection() helper; templates/docs/workflow.md.template has no `## Context-cost discipline` section; and migrate.py inventories a project's own docs/workflow.md rather than copying jig's. All three prior review verdicts pass, scope is docs-only with nothing added to the hot cache, and the deferred usage.py A/B is honestly disclosed. No design-principle violations.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- usage.py A/B turn/token-delta measurement parked in docs/inbox.md (loose end), so the deviation log is no longer its only home.
- The "does the lever reach scaffolded projects" question is parked under conditional slice 079-02, which is transitioned DEFERRED with the resolution trigger "079-01 guidance shown insufficient in practice" and reflected on the status board.
