---
adr: 0026
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (opus, fresh re-critique)
reviewed_at: 2026-06-15T16:30:20Z
prompt_source: review.py frame-critique docs/decisions/adr-0026-adr-status-frontmatter.md
---

VERDICT: pass

REASONING:
This ADR's four load-bearing factual claims are not asserted but genuinely grounded — I verified each against the code (_lookup_adr_accepted/_lookup_slice_status in workflow.py:694-740, _classify_status/cmd_supersede in adr.py:997-1109) and the corpus (the only superseded ADRs are 0002/0008; no slice depends on either). The single remaining load-bearing element is honestly identified by the author as a value judgment ("uniformity now > a bounded sync tax + being mildly ahead of demand"), not a factual claim, and its cheaper alternative (Option C: reader-only, prose-canonical, fixes the only concrete bug with zero format change) is enumerated in full and explicitly rejected with reasons — not hidden. Per the frame-critique standard, an honestly-stated value judgment whose alternative is weighed and rejected is a defensible frame even where a reviewer might personally prefer the cheaper option, so it survives.

SPECIFIC ISSUES:
- Primary load-bearing assumption — the value judgment that "completing the uniform frontmatter data-model is worth the dual-write tax + being admittedly ahead of demand," chosen over the cheaper Option C. The strongest attack is the project's own "don't build ahead of demand" norm (cited in the ADR itself: the PARKED pluggable-oracle boundary, ADR-0019's trigger). By that norm Option C is the conventional jig call: it fixes the only concrete bug in the reader alone, no format change, no dual-write, and is explicitly not inert. If no consumer ever reads status: from ADR frontmatter, the dual-write tax was paid purely for symmetry. However this does NOT sink the frame: (a) it is correctly labeled a value judgment, not a forced factual conclusion; (b) the cheaper alternative is fully enumerated and rejected on stated grounds, not skipped or strawmanned; (c) the cost is honestly bounded and the over-build is hedged with a kill criterion. A contestable-but-honest value judgment with its alternative weighed and an exit ramp defined is a defensible frame. No factual assumption about reality is likely-wrong and no alternative was hidden — pass, not needs-changes.
