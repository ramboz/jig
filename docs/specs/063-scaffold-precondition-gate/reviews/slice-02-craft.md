---
slice: 063-02 — skill-step0-precondition
pass: craft
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-09T00:09:37Z
prompt_source: review.py pr-review
---

VERDICT: pass

REASONING:
This is a tightly-scoped documentation change (a "Step 0: confirm the project is scaffolded"
precondition in skills/spec-workflow/SKILL.md, lines 109-134) plus two guard/parity tests, and
the craft is solid. The prose is clear, correctly ordered before the reserve step, names both
routing targets and the anti-pattern, and points at the workflow.py new helper without duplicating
its heuristic; the bypass env var (JIG_SCAFFOLD_PRECONDITION) and the /jig:scaffold-init and
/jig:migrate routing strings match the 063-01 implementation exactly, so prose and code agree by
construction. The tests follow existing conventions, the section-isolation in the contract test is
a robust touch, and the full suite is green (no regressions). Findings are nice-to-haves only.

SPECIFIC ISSUES:
- [strength] scripts/test_workflow_contract.py — SpecWorkflowStep0Precondition.setUp isolates the
  `### Creating a new spec` section before asserting, so a stray mention elsewhere in SKILL.md can't
  produce a false pass.
- [strength] scripts/test_workflow_contract.py — the negative assertion that the prose does NOT
  restate the trigger heuristic (`3-of-4` variants) directly pins AC2's "point at the helper, no
  duplicated logic" intent, guarding the most likely regression.
- [strength] skills/spec-workflow/SKILL.md:120-127 — prose explicitly tells the orchestrator it
  "doesn't have to decide the state yourself" and to "run the helper and let it route," making the
  deterministic gate the source of truth and the prose a thin pointer.
- [nit] test_scaffold_mode.py vs test_workflow_contract.py — the parity test and the contract test
  assert the same substring vocabulary (step 0, /jig:scaffold-init, /jig:migrate, slices/) against
  two surfaces (live source vs scaffold copy). Intentional and defensible (distinct files, distinct
  regressions), but a future reword must satisfy both suites — worth a discoverability note.
- [nit] scripts/test_workflow_contract.py — assertions match lowercase substrings anywhere within
  the isolated section rather than anchoring to the `0.` list item, so within-section structural
  drift isn't fully pinned. Low risk for a prose guard; acceptable as-is.

RECONCILIATION NOTES:
No blockers. Both nits are test-coupling/robustness observations, appropriate to log in the
deviation log rather than block REVIEWED. The three strengths (section-isolation, the AC2
negative-assertion guard, the helper-is-source-of-truth prose framing) are patterns worth repeating.
