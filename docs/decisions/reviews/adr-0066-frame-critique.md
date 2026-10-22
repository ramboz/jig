---
adr: 0066
pass: frame-critique
verdict: pass
reviewer: reviewer
reviewed_at: 2026-10-22T17:59:28Z
prompt_source: review.py frame-critique ADR-0066; final Git paragraph supplement
---

VERDICT: pass

REASONING:
The highest-risk assumption is that component-specific facts can become input
data without changing the supported producers' evidence meanings. The
strongest counterexample--extraction changing measurement or policy semantics--
is covered by the kill criterion; changed runtime bytes require a new approval
epoch. The finite frame survives, without establishing real-app approval.
The fixed local HEAD probe is technically authorized, isolated from Git
redirection, and does not execute a producer/evaluator/browser.

RECONCILIATION NOTES:
Prospective decision only. Implementation has not been assessed.

FINAL-REVISION SUPPLEMENT:
Independent narrow reviewer git-probe-framing returned VERDICT: pass after the
live-Git paragraph was added. It found a bounded local HEAD metadata probe,
no shell/user argv/network/writes, explicit inherited Git redirection isolation,
and explicit non-Git null versus execution failure. No contradictions with the
previously framed finite static policy. ADR remains Proposed.

Exact final proposed ADR raw SHA256:
68302a2df1ea492b79931f9a4d198a486cbaf2bb13ea18ed2acb79aebd87368f
