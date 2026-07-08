---
slice: 078-02 — gate-stats digest
pass: frame-critique
verdict: pass
reviewer: Explore (jig frame-critique)
reviewed_at: 2026-07-08T21:14:35Z
prompt_source: review.py frame-critique
---

Adversarial frame-critique of spec 078 / slice 078-02 (gate-stats digest), run retroactively during the shipped-ahead-of-slicing reconciliation ceremony (2026-07-08). Three rounds.

**Round 1 → needs-changes.** Found a real over-claim: slice-02's Goal and the shipped `gate_stats` output stated the per-gate bypass count answers "is this gate deadweight? / is the gate catching anything?". That is a numerator (bypasses) with no denominator (respected gate fires) — a category error. A count of 0 is ambiguous (a golden gate nobody bypasses vs. a gate that never fires), so bypass frequency alone cannot support a keep/retire verdict, yet the tool's own closing line told the maintainer it does.

**Remediation.** Reframed the claim to an *override-frequency audit trail* (matching the spec Overview + EngTip #19 "silent heroics"), explicitly disclaiming the deadweight verdict, across five sites: spec Overview, spec Clarifications (gates-in-scope), spec Decomposition bullet, slice-02 Goal + anti-phasing check + impl note, and the shipped `gate_stats` output (workflow.py ~2204). The respected-fire denominator was deferred to docs/refinement-todo.md with a resolution trigger. Round 2 caught that the first pass missed the spec Overview + Clarifications; those were then fixed too.

**Round 3 → pass.** All five sites plus the deferral entry are mutually consistent; the numerator/denominator gap is named inline at every site that could mislead; the audit-trail value stands independent of the missing denominator.

VERDICT: pass

Findings:
- [strength] Numerator/denominator gap named inline at all five sites and cross-linked to a correctly-reasoned deferral entry (including the count=0 ambiguity).
- [nit] Overview's verb "informs" (whether a gate earns its keep) is a generous but adequately-caveated verb ("cannot by itself settle") — no change required.
