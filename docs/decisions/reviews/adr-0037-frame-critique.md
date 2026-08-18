---
adr: 0037
pass: frame-critique
verdict: pass
reviewer: jig:reviewer subagent (4 independent passes)
reviewed_at: 2026-08-18T21:32:33Z
prompt_source: review.py frame-critique docs/decisions/adr-0037-bug-fix-repository-closure-evidence.md
---

Frame-critique of ADR-0037 (bug-fix repository closure evidence), run
pre-implementation against the ADR and the spec 091 slice it seeds.

**Verdict: pass** — conceded on the fourth independent pass, after three
earlier passes returned `needs-changes` and the ADR was strengthened against
each. Each reviewer read only the artifacts (no implementation exists yet).

## Load-bearing assumption identified

Convergent-logic misses are caused by *thin or absent* search rather than by
*diligent but blind* search — i.e. recording the search and making it
challengeable changes discovery outcomes. The ADR now states this bet plainly
in `## Assumptions` and explicitly disowns the stronger claim that the parser
gate proves closure.

## What the earlier passes forced (all folded into the ADR)

1. **The overclaim.** Pass 1 showed the ADR read as if a prose presence-gate
   would surface unknown-unknown omissions, citing jig's own bug 005 (the
   diagnose gate "green-lighting for the wrong reason"). The Recommended
   Decision now separates the ADR-0011-lineage *deliberateness* gate from
   `bug-review` as the discovery-quality backstop, and engages bug 005 directly.
2. **Ungrounded backstop.** Pass 2 accepted the reframe but held that
   "`bug-review` owns the completeness judgment" was itself unproven — a
   reviewer has no superior search power and less context. The ADR now grounds
   the backstop on ADR-0052's already-accepted burden shift (an empty search is
   ungrounded until you show what closes the set,
   `skills/bug-fix/SKILL.md:224-226`), disclaims any superior-discovery
   assertion, and delineates the real overlap with ADR-0052.
3. **An internal contradiction.** Pass 3 found the sharpest defect: the
   equivalent-logic prompt is definitionally in ADR-0052's *unclosable* class,
   for which ADR-0052 licenses "record it as an assumption" — yet slice AC6 (as
   drafted during this critique cycle) declared exactly that answer
   non-satisfying. That gate would have been unsatisfiable, driving authors to
   boilerplate or `*_GATE=0` bypass. Resolved by restating the prompt as an
   **effort-and-protocol standard, not a completeness standard**: the assumption
   disposition is accepted for the *claim*, but does not discharge the
   *protocol* (terms tried, history inspected, sibling paths checked). A bare
   "none found" fails; a protocol-bearing assumption passes. AC6 was corrected
   to match and now requires tests for both directions.
4. **Falsifiability.** Pass 3 also showed the kill criterion was lagging and
   detection-dependent. A vacuity leading indicator was added; pass 4 noted that
   vacuity measures effort while the bet is about effect, so a paired
   effect-side indicator was added (how often an inventory actually changed the
   fix).

## Residual exposure, accepted knowingly

- The name-based baseline is weakest precisely against differently-named
  convergent logic — the motivating case. The ADR now states plainly that it
  **reduces** but does not **close** that class, and that closing it is a
  discovery-capability problem (Option C) deliberately not mandated, to avoid
  excluding offline and public users.
- The substantive quality judgment still runs at `bug-review`, i.e. after the
  fix; what genuinely moves earlier is the recorded search and the reuse
  decision. The Option A con was tightened to stop overstating that contrast.
- Evidence base is N=1 and external (Mystique PR 3417), unverifiable from this
  repo. The ADR routes validation to forward usage under the kill criteria
  rather than to retrospective replay, which cannot fail. Flagged here so
  reconciliation records it.

## Disposition

The frame survives. The remaining pass-4 findings were refinements, not frame
defects, and both were folded in before acceptance.
