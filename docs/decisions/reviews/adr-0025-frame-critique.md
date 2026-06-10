---
adr: 0025
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-10T17:38:39Z
prompt_source: review.py frame-critique docs/decisions/adr-0025-use-cases-breadth-layer.md (re-run after addressing needs-changes)
---

VERDICT: pass

REASONING:
Re-run on the corrected ADR by a fresh independent reviewer (no memory of the
prior pass). The single most load-bearing assumption is A1 — breadth-divergence
on behavior-dense projects is real and recurs at a justifying rate — and the
author names it, concedes it is unverified (one user / one Android app / not
measured), draws the precise line between the *verified gap* and the *assumed harm
rate*, and attaches a kill criterion. The three concrete grounding claims the
frame leans on were re-verified and all hold: the vision template/wizard carry no
use-case/behavior concept (§A1 gap); `parsing.py` supports list-valued frontmatter
via `_parse_flow_list` (§A3); and §A4 is accurate — `build_reconciliation_prompt`
is per-slice + deviation-log-scoped (no project-wide vision view) and
`analyze/SKILL.md` states cross-spec input is "explicitly NOT supported by the
MVP." The two prior needs-changes findings are resolved (A4 corrected + grounded;
the kill criterion now measures divergence-prevention, held explicitly distinct
from uptake/link-existence). The deeper unflagged risk available — that divergence
is a property of depth-first agent authoring under context pressure, so a
populated use-case section yields trace links without binding framing-convergence
regardless of grain — lands squarely on the existing §A2 kill criterion, and the
wrong-frame cost is bounded by the overridable-default + advisory-not-gate +
Option-C-deferred scoping. The frame survives the strongest attack.

SPECIFIC ISSUES:
- Primary (already flagged, accept) — A1: divergence is real and recurs at a
  justifying rate. Thin evidence; if wrong, the init capture step is pure ceremony
  on behavior-dense projects. Conceded verbatim, gap-vs-harm-rate distinguished,
  scoped as an overridable Tier-1 default (skip → zero cost), watched by the "low
  uptake / friction-without-payoff → drop" kill criterion. Downside bounded and
  cheaply discoverable post-ship — the frame holds despite thin evidence.
- Secondary (now flagged via §A2) — causal attribution: that divergence is caused
  by the *absence of a breadth artifact*, fixable by *adding one agents read as
  framing* (B3). The alternative reading: feed-forward-by-reading may not bind
  regardless of grain (a vision already holds Target users + Scope, yet divergence
  is the stated problem). Genuinely load-bearing, but caught by the existing §A2
  kill criterion ("trace-linked specs show no less contradiction/overlap on shared
  behaviors → drop it"), which is instrumented for exactly this failure mode and
  held distinct from link-existence — so it does not sink the frame.

Note: prior verdict was needs-changes (A4 over-claim + kill-criterion blind spot);
both addressed in the corrected ADR, which this fresh pass confirms.
