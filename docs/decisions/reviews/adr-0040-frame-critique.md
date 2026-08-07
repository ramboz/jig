---
adr: 0040
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (frame-critique pass, rev6 of 6)
reviewed_at: 2026-07-28T14:43:45Z
prompt_source: review.py frame-critique
---

Frame-critique of ADR-0040 — **pass** on revision 6, after five prior revisions
each driven by a `needs-changes` from an independent frame-critique. The frame
survived the reviewer's strongest attack on D3's load-bearing assumption (that
`record-review` can derive a trustworthy `substrate:` from observable state,
giving the anomaly a producer that is not the audited agent). Every factual
citation was verified in-tree by the reviewer.

Revision history recorded inside the ADR itself (deliberately, not dropped):
- rev1: prompt-build call wrote sidecar from its own enumeration → recorded a
  re-enumeration, not an act of showing.
- rev2: treated sidecar *absence* as the skipped-step signal → fired precisely
  when config was working (absence had three legitimate producers).
- rev3: placed enforcement in the prompt-build call, claimed "a skipped step
  cannot produce an artifact" → false, `record-review` writes independently and
  bug-fix already calls it without a builder. Chokepoint moved to `record-review`.
- rev4: printing a precision-filtered list made the regex the pick gate,
  reversing ADR-0039's recall-not-precision split → fixed by tiered output
  (high-confidence + speculative; anomaly fires only on high-confidence tier).
- rev5: builder-exists was a *mechanical* membership test; `design_review` is an
  ADR-0022 attest-only gate that refuses deferral → excluded from the extensible
  set, which narrows to three (pr_review, arch_review, code_health).

Fixes applied under the pass verdict (reviewer flagged, orchestrator verified):
- PRIMARY: `substrate:` computation scoped by `(category ∈ three) AND (keying
  mode == slice)`, not category alone — `craft` is a shared pass token and
  bug-fix runs it in-category, so a category-only scope would stamp `not-shown`
  on every bug fixed.
- `config` named as a third blind spot (derived from presence, modal once 096-01
  ships, anomaly-blind where the guaranteed layer lives).
- Tiering print format made load-bearing: descriptions for high-confidence,
  names-only for speculative — bounds the context re-injection cost (spec 055/057).
- Off-list pick explicitly handled (reject → baseline + record), not left open.
- Second inline ADR-0010 correction owed: code-health builder docstring
  (`review.py:887-890`) is stale live prose.
- D2 grounds restated on the real invariant ("unprefixed ⇒ no SKILL.md", holds
  for both unprefixed writers incl. the Codex alias); OQ3 re-aimed at it.

Decisions D1–D3 supersede ADR-0039 on the three falsified premises; everything
else in ADR-0039 is carried forward unchanged.
