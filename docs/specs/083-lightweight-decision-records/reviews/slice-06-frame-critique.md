---
slice: 083-06 — Widen the load-bearing-decision judgment prompt in BOTH session-end surfaces
pass: frame-critique
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-26T19:39:21Z
prompt_source: review.py frame-critique (ADR-0031 + spec 083 + slices 05/06); jig:reviewer subagent; 2 rounds
---

Adversarial frame-critique of ADR-0031 + the paired 083-05/06 design (all carry frame_review: true; the slices' flag derives from spec-level Assumptions about the 083-04 Stop-hook payload, already shipped — the substantive framing under critique is the ADR's).

Round 1 — needs-changes: the ADR conflated policy *consistency* (what the single-sourcing apparatus delivers) with capture-rate *improvement* (unevidenced). The memory-sync escape hatch is the same session-end attention prompt the spec already concedes cannot close recall-dependence; widening its wording is a naming win, not a capture win. Secondary: the drift test guards lexical identity only, blind to semantic drift (verbatim sentence surrounded by contradicting prose).

Resolution: ADR reframed to scope itself explicitly as a policy-CONSISTENCY mechanism, NOT a capture-rate improvement; "### Scope of the claim — consistency, not capture" added; `## Assumptions` now declares the capture-efficacy bet as load-bearing-but-not-claimed-here (was the false "None load-bearing"); drift test's lexical-only scope stated honestly with the reconciliation reviewer assigned as semantic backstop; third kill criterion tied to a capture-outcome eval. Stale test docstring path corrected.

Round 2 — pass: both load-bearing issues resolved at the frame level, not papered over. The ADR now claims exactly what it can defend (consistency) and cedes what it cannot (capture efficacy → spec 083-04/083-07; semantic coherence → reconciliation reviewer). Single-sourcing confirmed genuinely wired: ADR_TRIGGER matches the ADR prose verbatim (incl. U+2014 em-dashes) and test_decisions.py asserts presence in all four consumer sites + the ADR.
