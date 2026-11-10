---
bug: 041
pass: bug-review
verdict: pass
reviewer: reviewer subagent (fresh, round 5 on the final design)
reviewed_at: 2026-11-10T19:40:50Z
prompt_source: review.py bug-review
---

VERDICT: pass

REASONING:
The fix covers all three documented root causes rather than masking the symptom. Orient's positive description no longer claims "next" (the only "next" is in the "Do not use" clause); the exclusion covers every bare "what's next?" and says to give the short answer, then offer the full orientation; a scope check before the headline command runs the full skill without asking on an explicit /jig:orient, and on "what's next?" gives the short answer then asks — no stops, yes runs the full orientation. This matches the owner's last revision exactly. Red evidence holds (3 failures + 8 errors across the 11 surface tests against the old SKILL.md; the score-based routing test closes the gap the rate-floor gate leaves), and the 101-01 AC8 / 088-02 AC3 interactions are disclosed honestly.

ROUND HISTORY (final design, fresh reviewer each round):
- Round 1, needs-changes: "what should I pick up next?" not named in the scope check (and could fall into the explicit-whole-project case); board showed DONE while the record was FIXING; red evidence described an earlier test class; first-design docstring wording; no no-plan fallback in the description.
- Round 2, needs-changes (record only): stale "reclassified as project-level" note; contradictory 3→1 vs 3→3 rank claims; Fix 2 quoted a stale draft; wrap leftovers.
- Round 3, needs-changes (cosmetic): wrap leftovers in SKILL.md, the test docstring and the record; optional sub-heading wording.
- Round 4, needs-changes: the record's Evidence/H3/Root cause wrongly said the pre-fix body had no early scope statement — the 088-02 paragraph existed but was as narrow as the description and gave no stop instruction.
- Round 5, pass (this verdict).
(Earlier designs — infer-from-context, then ask-first — were invalidated by the reopen and the second owner revision; the first design's own bug-review needed two rounds.)

SPECIFIC ISSUES (round 5, nits):
- learnings.md still said "the body had no scope check".
- Record quote of the 088-02 paragraph stopped before "— not to re-survey the whole project"; "can't be acted on" overstated it.
- Two wrap leftovers in the record.
- Proof "recorded below" had nothing below it yet (filled after the → REVIEWED gate).

RECONCILIATION NOTES:
- 101-01 AC8 not amended: the live Judgment line now carries "In a full orientation" and "re-ask for orientation"; spec 101's re-ask and session-start cases run the collaboration survey only after a yes. Owner-accepted; recorded as a deviation from the closed AC8 wording.
- 088-02 AC3 not amended: every bare "what's next?" now gets a short answer plus an offer.
- Description wording: "release plans" → "release scope" in the survey list; output-format clause → "recommend where to start". No AC or test pins either.
- First owner-less negatives in evals/cases/; they pass on alphabetical tie-break; the real guard is Bug041OrientNextStepRoutingTests.

DISPOSITION (implementer, after round 5):
- learnings.md now says the body's only early scope note was as narrow and never said to stop.
- Record quotes the full 088-02 clause and qualifies the claim to the between-steps case; Root cause 3 heading now "too narrow".
- Wraps fixed; the description-wording deviation added to Spec interactions.
- Proof's final green is appended after the → REVIEWED gate run.
