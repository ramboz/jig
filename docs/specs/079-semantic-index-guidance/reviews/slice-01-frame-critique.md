---
slice: 079-01 — workflow.md index guidance
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T15:34:40Z
prompt_source: review.py frame-critique
---

VERDICT: pass

REASONING:
The single highest-risk load-bearing assumption is that passive prose in docs/workflow.md will shift the agent's runtime grep-vs-index behavior at the moment it matters — every sibling lever in this section (run-thin, delegate-reading, read-lean) carries an active limb (session-plan dispatch, a PreToolUse Read-hook nudge) while this one is read-only prose with no actuation. The frame is not exposed by this: the spec pre-registers exactly this risk and gates the 079-02 scaffold nudge on "the passive guidance proving insufficient"; the slice delivers observable, uptake-independent doc value; the "indexes cut turns" claim is cited to EngTip #26 not re-derived; the limits caveat is honest; and the install-nothing / detect-else-recommend stance matches the established contracts/code-health pattern. The audience scoping is internally coherent — the spec's end-state is jig's OWN docs/workflow.md, and the slim wizard template has no Context-cost section at all, so "does it reach scaffolded projects" is a pre-existing structural gap, not a regression introduced here.

SPECIFIC ISSUES:
- Assumption "standing prose guidance suffices to shift runtime behavior" — could be wrong (an agent mid-grep does not re-read workflow.md; unlike the other levers there is no hook/dispatch actuation), but the impact is bounded and already owned: 079-02 is conditioned on this proving insufficient and the implementation note proposes a usage.py A/B. Load-bearing but conceded by design, not a defect. Frame survives.

RECONCILIATION NOTES (fold into deviation log):
- The guidance lands ONLY in jig's docs/workflow.md; templates/docs/workflow.md.template (scaffold source) has no Context-cost section, so scaffolded projects receive none of this lever — consistent with the spec end-state + 079-02 deferral, but record that the reach-to-scaffolded-projects question is parked under 079-02, not silently met.
- The slice-01 implementation note ("confirm the section flows via migrate copy-machinery") is moot: migrate.py copies a project's OWN workflow.md, not jig's. Note it so a future reader doesn't re-open it as a gap.

PROVENANCE: frame-critique cleared on round 1 (fresh reviewer); frame-review-needed=true for this slice.
