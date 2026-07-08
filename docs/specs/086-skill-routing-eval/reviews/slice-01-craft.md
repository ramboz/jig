---
slice: 086-01 — routing-eval harness (collision + trigger + ratchet)
pass: craft
verdict: pass
reviewer: pr-review skill (general-purpose subagent)
reviewed_at: 2026-07-08T19:13:12Z
prompt_source: review.py pr-review 086-01 (re-review)
---

Craft pass (pr-review methodology, fresh-context general-purpose subagent;
re-review after the test-coverage + nit fixes). PASS — no blockers. All
documented baselines reproduced on a live run (19 skills, top collision 0.22,
57/57 positives in top_k, 95% rank-1, 100% negative route-away, 28 tests OK,
ratchet trips at 1.01).

Strengths:
- [strength] routing_surface() dropping the negative-disambiguation tail before
  vectorizing — sharp, well-reasoned response to the frame-critique; effect real
  and verified (top collision 0.22).
- [strength] print_report returns the exact tally main() and the CI gate consume
  — human report and pass/fail decision can't drift apart.
- [strength] test_no_routable_skill_resolves_empty re-walks the skill dirs
  instead of trusting load_descriptions() (which pre-filters empties) — closes
  the vacuous-check trap.
- [strength] "Known limitations / why this is a canary" doc is unusually honest
  (self-authored closed loop, lexical≠semantic, length bias) with deferred fixes.

Nits (→ deviation log):
- [nit] some positive prompts (bug-fix, tdd-loop, vision-elicitation) echo their
  description's auto-trigger phrases near-verbatim — the self-consistency
  limitation the README warns about; reseed toward real user speech in a future
  pass.
- [nit] MIN_RANK1_RATE 0.85 / MIN_NEG_ROUTE_AWAY 0.90 sit ~10pp under the live
  baseline (95%/100%) though the comment says "just below"; reword the comment
  to match (conservative anti-gaming slack) — raise-only ratchet keeps risk low.
- [nit] "(prototype)" / "routing-eval spike" labels remain in evals/README.md
  and test_skill_routing.py docstrings for a check that now gates CI; drop them.
- [nit] evaluate_case reads case["skill_name"] raw (opaque KeyError on a
  malformed case file) while trigger is .get()-guarded; minor, author-controlled.
