---
slice: 061-03 - host-package drift guard
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-05T22:21:45Z
prompt_source: review.py implementation <slice> 061-03 <deliverables>
---

All five ACs met with meaningful tests. build_all regenerates both packages (AC1); --check/check_drift rebuilds into a scratch tempdir, diffs against committed hosts/, exits non-zero naming each stale path + regenerate command, never mutates the committed tree (AC2, asserted by test_check_does_not_mutate_committed_tree); ci.yml runs --check as a dedicated step (AC3); determinism test asserts byte-identical re-build (AC4); docs/workflow.md documents edit->regenerate->commit + the guard (AC5). Both edge cases (version-only bump into BOTH manifests; partial tree fully replaced) tested. Builders rmtree+recreate so partial-replacement is real. No principle violations. Deviation log now filled.
