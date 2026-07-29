---
slice: 096-03 — enumerate-and-select
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (compliance pass)
reviewed_at: 2026-07-29T22:08:00Z
prompt_source: review.py implementation
---

## VERDICT
pass

## REASONING
All 9 ACs met with filesystem-backed tests (no mocks). `enumerate_candidates`
tiers via a recall-oriented matcher that never picks (AC1); `candidates` writes
the sidecar in the same call that prints (AC2); `--richer-skill` required on all
three passes (AC3); picks validated against the shown tiers, off-list/`none`
→ baseline without erroring (AC4/AC5); missing-sidecar fail-fast with a
`--non-interactive` escape (AC6); config→pick→baseline chain with
`detect_richer_skill` fully removed (AC7); the spec-workflow recipe instructs the
orchestrator for all three passes incl. multiple-candidates + config-override
framing (AC8); the consume-on-read sidecar's lifetime/absence/staleness/
concurrency are defined + tested (AC9). Both named DoD regression tests exist and
are meaningful. No principle violations.

## SPECIFIC ISSUES
- [nit][impl] `_validate_pick_against_sidecar` re-resolved the pick by directory
  name while the shown/picked name is the frontmatter name — a divergence would
  silently fall to baseline. → FIXED: now uses the sidecar's stored `path` for
  the matched shown candidate (re-checking existence + non-baseline); regression
  test `test_pick_resolves_via_stored_path_when_name_diverges_from_dir` added.

## RECONCILIATION NOTES
- The candidate-channel machinery ships in both host packages; Codex's
  config-only posture (spec Assumptions) is enforced by which recipe steps the
  orchestrator runs, not by a code path disabling Codex enumeration — the
  intended 096-04 outcome, recorded in the deviation log.
- docs/skill-routing-verification.md still references the removed
  detect_richer_skill — tracked as a Close-out (post-DONE) item.
