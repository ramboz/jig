---
slice: 096-03 — enumerate-and-select
pass: arch
verdict: pass
reviewer: jig:reviewer subagent (arch pass)
reviewed_at: 2026-07-29T18:46:20Z
prompt_source: review.py arch-review
---

## VERDICT
pass

## REASONING
The seam split is architecturally correct: discovery/tiering
(`enumerate_candidates` + `_classify_for_category`) sits with the 096-02
resolution primitives in `skill_discovery.py`; durable state is isolated in the
new leaf `candidate_sidecar.py` (stdlib + atomic_io only); the CLI/resolver
composition lives in `review.py`. No layering inversion, leaf discipline
preserved. The precedence chain (config → validated-pick → baseline),
off-list→baseline-not-error, fail-fast (AC6), and tiering-never-picks are all
faithfully implemented. Documented in architecture.md + the spec-workflow recipe.

## SPECIFIC ISSUES
- [strength][impl] both new modules hold the LEAF invariant; state + discovery
  seams stay independently testable, no CLI coupling into _common.
- [strength][impl] the matcher governs tiering only; pick validation checks
  membership in EITHER tier, so an incidental-demotion miss only demotes, never
  blocks a legitimate pick.
- [strength][impl] a single resolver (`_resolve_richer_for_pass`) is the sole
  precedence authority for all three builders; structural ReviewConfigError
  propagates while off-list/none degrade to baseline.
- [nit][spec] consume-on-read guarantee is an end-state property — the consuming
  half ships in 096-05. → FIXED: deviation log + docstring softened to
  "prevented by always-run-candidates + atomic overwrite in the 096-03 window;
  impossible-by-construction once 096-05 wires consume".
- [nit][impl] the transient sidecar under reviews/.candidates/ stores a
  machine-specific applied_path in the committed evidence tree. → FIXED:
  reviews/.candidates/ is now .gitignore'd.
- [nit][impl] `candidates` took category + --pass orthogonally (mismatch keys
  the sidecar wrong). → FIXED: coherence check refuses a mismatch (exit 2),
  regression test added.
- [nit][impl] `_PASS_CATEGORY` mirrors `review_config.PASS_TO_CATEGORY` (a
  self-documented CLI-local mirror) — accepted small drift risk.

## RECONCILIATION NOTES
- Whether 096-03 should declare a dependency on 096-05: kept separate — the
  write/record halves are complete + tested here; consume is 096-05's to wire,
  and the interim staleness protection is documented.
- docs/skill-routing-verification.md still references the removed
  detect_richer_skill — tracked as a Close-out (post-DONE) item.
