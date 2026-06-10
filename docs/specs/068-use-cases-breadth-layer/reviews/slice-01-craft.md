---
slice: 068-01 — capture-and-vision-section
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-10T22:23:14Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
This is a well-crafted, judgment-only capture-seed slice. The new `## Use cases` template section (goal-level guidance, `[actor] can [goal]` form, concrete example, explicit goal-vs-spec caution) and the SKILL.md "Use cases capture" four-step contract (any-shape/loop-to-exhaustion, single confirm-gated normalize pass, edit round-trip, hard no-silent-inference rule) are clear, internally consistent, and faithfully scoped to seed-not-grow. The YarnFinder worked example demonstrates all four steps end-to-end (bulk+incremental capture, dedupe, edit-then-reconfirm, a no-infer question that is declined and correctly not folded in), and the new tests pin the contract on substance rather than superficially. On the specific count-consistency check: the three numbers measure three distinct things and remain coherent — 10 vision H2s, of which 7 come from Q&A (5+2), Stack has no producer, and Use cases comes from the capture loop (explicitly flagged as not-Q&A); the "12-section walk-through" counts the numbered Q&A sections (1-12) actually walked, unchanged by inserting the non-numbered Use cases block. No contradiction was introduced.

SPECIFIC ISSUES:
- [nit] skills/vision-elicitation/worked-example-rerun.md:14 — Stale H2 count: "now has all 9 H2 sections marked `status: filled`". The template now carries 10 H2s (Use cases added by 068-01), so a re-run after a 068-aware first run sees 10 filled sections. Made stale by this slice's template change.
- [nit] skills/vision-elicitation/worked-example-yarnfinder.md:26-44 — The "Concept-to-template mapping" table (header says YarnFinder "names 9 sections") and the prose at line 24 ("These map to the template's 10 H2s") describe a 9-concept→template mapping that does not enumerate the new Use cases H2 as a mapped row. The Use cases demonstration is added below as its own block (correct), but the top-of-file mapping table is now an incomplete inventory. Cosmetic.
- [strength] skills/vision-elicitation/test_vision_elicitation_skill_surface.py — The 068-01 tests pin the contract meaningfully: normalize ops (dedupe/split/goal-level), confirm-gate phrasing ("nothing is written"/"before any write"), edit round-trip, the no-infer triad (never + infer/auto-add + question + explicit-yes), AND the seed-not-grow / 068-02 boundary — so the prose can't drift without breaking a test.
- [strength] skills/vision-elicitation/SKILL.md:37-62 — The implementer kept the delicate 10-vision-H2 vs 13-Q&A-section vs capture-loop relationship explicit and correct (flags Use cases as a distinct conversational loop, not Q&A; keeps the 5+5+1+2=13 arithmetic intact), which is exactly where a contradiction would otherwise have crept in.

RECONCILIATION NOTES:
- Two stale pre-068 H2 counts in sibling worked examples (`worked-example-rerun.md:14`; `worked-example-yarnfinder.md:24-44` mapping table) should be corrected to 10 during reconciliation, or explicitly logged as a deferred follow-up. Neither blocks REVIEWED — documentation-currency nits, not contract/correctness defects. Matches the learnings.md "mid-implementation reshape leaves stale neighbor prose" pattern; the worked-example files are outside the SkillMdStalenessRegressionTests surface set.
