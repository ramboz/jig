---
slice: 123-02 — dead-end-policy-recipe
pass: frame-critique
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-11-20T21:59:12Z
prompt_source: review.py frame-critique docs/specs/123-custom-test-command-contract/spec.md dead-end docs/specs/123-custom-test-command-contract/slice-02-dead-end-policy-recipe.md
---

VERDICT: pass

REASONING:
Round 3 (rounds 1 and 2 returned needs-changes; their findings were folded into the slice before this round). The slice rests on one assumption: guidance printed at the no-runner dead end reaches the actor and is enough to get them to a sound command, with the Gradle recipe failing closed wherever its unprobed reading of Gradle is wrong. The reachable half is grounded in source and the disclosed Gradle residual could not be made to fail open. Read-only review: nothing was run, and the Gradle points are from the reviewer's knowledge of Gradle, not a probe.

SPECIFIC ISSUES:
- Primary — "the last stderr line reaches the bug-fix gate whole, and the recipe document reaches a consuming project's agent" holds: `bug.py` quotes the last non-blank stderr line up to 300 characters; `tdd.py` writes the hint last on both `detect` and `run`; `test-command-recipes.md` is present under all three host packages and `skills/bug-fix/SKILL.md` links it. Residual: at the gate the agent sees only the bare filename, so reachability from an installed plugin depends on the bug-fix SKILL.md link (acceptable).
- Disclosed Gradle residual ("deleting reports forces a re-run; if not, exit 2") — correct as far as it could be attacked: up-to-date skip, unmatched filter, compile failure, wrong `RESULTS` directory all end in no report, so exit 2.
- Secondary, undisclosed fail-open path — the wrapper decided red with `grep` for `<failure`/`<error` over the whole report file, which also holds the tests' captured output as CDATA; a passing test that prints such text would be a false red. Fix: disclose, or decide from the `<testsuite ... failures= errors=>` header attributes.
- Note — ADR-0068 is still `status: Proposed`; accept it before DONE.
- Note — the recipes document linked the ADR by a repository-relative path that does not ship in the host packages.

Orchestrator follow-up after this verdict (not seen by the reviewer): the wrapper now reads the `<testsuite>` header counts (`tests=`, `failures=`, `errors=`) and a stub case with failure-looking text in captured output pins it green; the recipes document now cites ADR-0068 by its GitHub URL.
