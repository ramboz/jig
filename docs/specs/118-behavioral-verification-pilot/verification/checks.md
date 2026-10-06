# Verification: 118-01

Executed source revision: `7a04ff595769a86bcb51ba3dc5bd96c1969ff971`.
Runtime sources were unchanged when these checks ran.

| Check | Invocation | Observation |
|-------|------------|-------------|
| Fixture CLI and preservation | Python block from `skills/spec-workflow/worked-example-behavioral-verification.md`, source repository as `JIG_ROOT` | Both steps pass; UC-1 reports `1/2 slices done`, exit 0, fixture paths/bytes unchanged. See [scenario.json](scenario.json). |
| Targeted regressions | `python3 scripts/run_tests.py skills/spec-workflow/test_behavioral_verification.py skills/spec-workflow/test_spec_workflow_skill_surface.py skills/clarify/test_clarify_skill_surface.py skills/independent-review/test_review.py` | 347 tests in 29.042s, `OK`, exit 0. Full-log SHA-256: `97920b52a4d4edf8385617c08b8a8ea0532ab32d615879897734267571a4d594`. |
| Three-host parity | `python3 scripts/build_host_packages.py --check` | Committed host packages match source, exit 0. |
| Spec structure | `python3 scripts/spec_lint.py docs/specs/118-behavioral-verification-pilot/spec.md` | No AC contradictions, exit 0. |
| Board audit | `python3 skills/spec-workflow/workflow.py check-board .` | `spec board: clean`, exit 0. |
| Remote baseline | `git fetch --quiet origin`; `git rev-list --count HEAD..origin/main` | Fetch succeeds; count 0. No remote write. |
| Initial repository suite | `python3 scripts/run_tests.py` | 5065 tests in 501.756s; 5 failures, 26 errors, 8 skipped, exit 1. Environment failure, retained below. |
| Approved fixture-compatible suite | Same runner with the owner-approved process-only `safe.bareRepository=all` environment entry | 5065 tests in 526.371s; `OK (skipped=8)`, exit 0. Full-log SHA-256: `e7295ace940811d88f334974d0b1040d2c613891cc705ffbfb5c672a25744a47`. |
| Type-check gate within suite | Existing runner's pyright step | `pyright: clean`. |

## Full-suite environment blocker

The failed cases concern existing bare-Git fixtures in claim-ref, reservation,
decision promotion, and git-freshness tests. A direct isolated probe reproduced
the restriction without changing configuration: `git init --bare` succeeds,
but `git config core.hookspath hooks` inside that fixture exits 128 with
`fatal: not in a git directory`. `git config --show-origin --get
safe.bareRepository` reports the inherited command-line value `explicit`.

The owner subsequently approved the test-process-only `safe.bareRepository=all`
setting with "Do it". The runner appends that single entry to a copy of the
inherited environment and preserves all other settings. No global/repository
configuration or file-protocol policy was changed. The parent process still
reports `safe.bareRepository=explicit`.

All 56 selectors covering the previously failing fixture groups passed in
44.579s under that approved setting; full-log SHA-256:
`ea91314be9552e3ee44ee087b9d624381d6a0939df31c519f07c58052f3c64e2`.
The complete suite subsequently passed with the same scoped setting: 5065
tests, 8 skipped, and clean pyright. The passing output remains in session
artifact `118-full-suite-approved-fixtures.txt`. The initial raw output remains
in `118-full-suite-authorized.txt`; its failures are retained rather than erased.

## TDD evidence and limits

[tdd.txt](tdd.txt) preserves contemporaneous output excerpts and full-log hashes:
rules tests first reported three failures, then three passes; scenario/prompt
tests reported seven failures, then the combined 346-test selection passed.
The authorized retry includes the later identity refinement and reports 347 passes.

The later runtime-manifest refinement was added after the original red loops;
no fresh pre-change red chronology is claimed for that refinement. Its executed
test independently computes the expected per-file and aggregate hashes. The
non-compliance-pass exclusion is a preservation control that correctly passes
before and after the compliance-only feature.

The supplemental identity-sensitivity experiment initially was denied. After
the owner relaxed permissions, it ran in a disposable copy of the runtime:
editing `_common/use_cases.py` changed the runtime identity without breaking the
scenario, and replacing per-file digests with a constant caused the existing
example assertion to fail (exit 1). Actual observations are in
[identity-mutations.json](identity-mutations.json). Repository source was not
modified. This establishes non-vacuous assertions, not retroactive test-first
chronology for the late refinement.

This is fixture CLI evidence, not live hook firing, UI authentication, or
measured improvement in escaped-defect rates.

## AC8 process deviation disposition

The orchestrator accepts the single late supplemental runtime-manifest guard
as an explicitly recorded sequencing deviation, subject to independent review
and reconciliation. The originally planned authoring/scenario implementation has
contemporaneous red/green evidence; the late refinement has executed independent
digest assertions and observed mutant rejection. Its pre-implementation
chronology is not claimed or rewritten. This exception weakens no functional
AC, removes no test, creates no bypass, and does not change the future test-first
policy. The original acceptance criterion remains above in the slice record
rather than being silently rewritten to match history.

The independent compliance recovery accepted this historical process exception
and returned pass after inspecting the recovered evidence. This disposition
does not claim perfect original chronology or change future policy.

## Craft-note resolution

The craft reviewer returned pass and reported a nonblocking omission of
`project_layout.py`, `parsing.py`, and `review_evidence.py` from the saved
manifest. A direct audit found all three present and independently matched all
19 per-file digests and the aggregate identity to current source bytes; the
reported omission is not an actual evidence gap. No JSON was rewritten.

Its section-localization suggestion is accepted as nonblocking: current
authoring guidance is on the correct creation hot path. No test was weakened,
and no new scope was introduced to satisfy a nit.
