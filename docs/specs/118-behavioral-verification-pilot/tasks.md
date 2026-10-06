# Tasks: 118-01

- [x] Independent spec review and readiness transitions.
- [x] Red tests for optional template sections and authoring/clarify guidance.
- [x] Red tests for compliance-only prompt guidance and absent-section behavior.
- [x] Implement source/template changes; witness targeted green.
- [x] Add and execute the worked example against the real CLI.
- [x] Document proportional workflow and regenerate all host packages.
- [x] Run full validation and fresh compliance/craft reviews.
- [x] Record runtime evidence, deviation log, and reconciliation sweep.
- [ ] Run reconciliation review and gated close-out.
- [ ] Check status board/package drift and commit local deliverables.

## First paused close-out

The worked example is packaged, but direct execution and writing its per-step
evidence were denied. Review-file writes were also denied. The repository suite
was stopped after the scenario-execution denial; no full-suite pass is claimed.
Fresh read-only compliance and craft reviews ran, but no gated verdict artifact
has been written. Resume the remaining tasks only after authorization; do not
bypass the evidence gates or mark this slice DONE.

The initial two TDD loops have contemporaneous logs in this session's artifact
directory: `118-rules-red.txt`, `118-rules-green.txt`,
`118-scenarios-red.txt`, and `118-targeted-green.txt`.
Later runtime-manifest refinements initially had only static/source-test coverage.

## Authorized resumption

The owner explicitly selected complete local ceremony authorization on
2026-10-05. The updated example now executes successfully, with progress counts
and unchanged-file observations in [scenario.json](verification/scenario.json).
All 347 targeted tests passed. The full suite ran 5065 tests with 5 failures,
26 errors, and 8 skips; pyright passed. The inherited
`safe.bareRepository=explicit` setting prevents existing bare-Git fixtures from
executing their Git commands. That restriction was reproduced, not overridden.

The owner subsequently approved the process-only fixture setting with "Do it".
All 56 fixture selectors and then the complete 5065-test suite passed
(8 skipped); pyright is clean. Persistent settings were unchanged.
The late runtime-manifest guard remains explicitly recorded as an AC8
sequencing deviation for independent review, not retroactive test-first history.
Compliance recovery and fresh craft review passed, with the AC8 sequencing
exception explicitly recorded and independently accepted rather than claiming
retroactive chronology. Reconciliation review and gated close-out remain pending.
No push/merge/PR or evidence-gate bypass is authorized.
