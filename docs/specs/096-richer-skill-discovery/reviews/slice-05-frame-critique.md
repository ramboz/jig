---
slice: 096-05 — anomaly-record-and-consumers
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer subagent (frame-critique pass)
reviewed_at: 2026-07-28T02:10:00Z
prompt_source: review.py frame-critique
---

Frame-critique of 096-05 returned **needs-changes**.

**Primary.** AC1/AC2 rest on the assumption that "the candidate set the
orchestrator was **actually shown and declined**" has a trustworthy producer.
The slice never names one, and only two exist — both of which break its purpose:

- **Orchestrator self-report.** Every evidence-artifact field is a hand-supplied
  flag on `record-review` (`review.py:1667-1693` — `--verdict`, `--reviewer`,
  `--prompt-source` are all orchestrator-typed), and `record-review` is a
  *separate process invocation* from `review.py <pass> --richer-skill …`, so
  nothing carries the candidate set across. The watchdog's input is then
  controlled by the watched party — the agent ADR-0039:330-331 names as having
  "a standing spec-057 cost incentive to choose the cheaper rubric." AC5
  ("absence of data is not evidence of an anomaly") plus AC3 (never blocks)
  makes *omission* a sanctioned, zero-cost escape: pass `--richer-skill none`,
  leave the candidate fields empty, get a clean `verdict: pass` artifact that is
  byte-identical to a machine with nothing installed — precisely the distinction
  AC1 says the record exists to make. The AC is self-defeating under its own
  backward-compat rule.
- **A Python precision filter over the nomination list.** AC2 forbids the raw
  list, so this must be a calibrated subset — but **no slice builds a precision
  matcher.** `slice-03:36-39` is explicitly recall-only; `slice-03:65-67` hands
  the gap forward as prose. ADR-0039:304-307 acknowledges the requirement
  ("Matcher precision therefore still matters … precision governs the
  false-positive rate of this ADR's only observability surface") but spec.md's
  Decomposition table allocates it to no slice. Building it would resurrect the
  deterministic matcher the owner overrode as "overfit by construction"
  (`adr-0039:339-350`), now as the sole calibration authority.

Consequence: this anomaly is the only instrument for the kill criterion
ADR-0039:489-498 calls "most likely to fire". Under self-report it under-reports
exactly when the orchestrator is being cheap — the same condition that produces
the failure — so an empty anomaly log reads as "Option D is working." A false
negative, not a missing signal, licensing further investment in the zero-config
layer on evidence that measures orchestrator diligence rather than deferral
correctness.

Note: AC6's documented blind spot (enumeration nominates nothing) is a
*different* failure from this one, where enumeration succeeds, candidates exist,
and the record suppresses the anomaly anyway. So this is not an accepted risk.

Closing move: make the producer explicit and non-orchestrator — have the
`review.py <pass> --richer-skill …` prompt-build call (which already computes
enumeration and knows the pick) write the candidate set to a sidecar keyed to
(slice, pass), and have `record-review` merge it rather than accept it as a
flag. AC5 then needs to distinguish "artifact predates this slice" from "sidecar
existed and was not merged."
