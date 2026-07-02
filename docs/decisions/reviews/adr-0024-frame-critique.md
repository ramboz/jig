---
adr: 0024
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T16:27:36Z
prompt_source: review.py frame-critique docs/decisions/adr-0024-reference-reframe.md (round 3)
---

VERDICT: pass  (round 3 — after the two-level coverage floor + two-pronged T1 + n=1 leverage-assumption fixes)

REASONING:
The single load-bearing assumption is enumeration completeness over *settled* ground —
that a model's corpus read, floored by the two-level coverage walk, finds the artifacts
encoding the dead premise. It is genuinely load-bearing and genuinely exposed, BUT the
ADR does not assert it: Assumptions §4 names it verbatim as "reduced and surfaced, NOT
fully owned," grounds the reduction in a concrete mechanism (L1 per-class visible fates
catch the servo whole-class `skills/` drop; L2 intra-class artifact-level read confronts
the motivating Android-design shape), enumerates the three residuals it does NOT close
(untouched-class misscoping, within-touched-class miss, rubber-stamped `excused`), and
backstops each with T1's two-pronged evidence incl. post-reframe discovery. The secondary
bet — correction-over-noticing ordering — is flagged as an n=1 assumption with a matching
kill criterion, and being wrong about it is recoverable (parked detection is additive; the
correction machinery is needed regardless of ordering). The frame survives the strongest
attack: every load-bearing assumption is one the ADR already owns and honestly bounds.

SPECIFIC ISSUES:
- (Primary, conceded-and-backstopped, NOT a gap) "A model's single-pass corpus read,
  floored by the two-level coverage walk, is complete enough that the manifest catches the
  dead-premise artifacts." If wrong, a partial manifest buries a surviving dead premise
  under fresh keystone authority — worse than the inert file. But Assumptions §4 names it,
  disclaims completeness, grounds the floor's reduction in mechanism (L1/L2), and hands the
  residual to T1(a)/(b). Conceded-and-backstopped, not unowned → no needs-changes.

RECONCILIATION NOTES:
- No deviations from linked ADRs. ADR-0023 §4 admits the "capability over the spine, not a
  member" category (go-live is a consuming gate vs reframe an orchestrating capability — a
  flavor difference, but §5 applies §4's actual criterion: no distinct intake→DONE backbone,
  no own transition — categorization holds). ADR-0020's ledger is genuinely risk-gated/
  default-off (blind to settled premises, as claimed). amend/supersede/rewrite route
  correctly per ADR-0010; the inline edits to this still-Proposed ADR (emergent-work,
  rewrite, and these frame-critique fixes) are consistent with ADR-0010 (amendments apply
  to CLOSED records; a Proposed ADR is edited inline).
