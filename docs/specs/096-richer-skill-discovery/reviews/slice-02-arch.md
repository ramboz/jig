---
slice: 096-02 — baseline-exclusion-and-resolve
pass: arch
verdict: pass
reviewer: jig:reviewer subagent (arch pass, re-review after blocker fix)
reviewed_at: 2026-07-29T04:22:59Z
prompt_source: review.py arch-review
---

## VERDICT
pass

## REASONING
Module boundary is clean + consistent with jig's `_common` convention:
skill_discovery is a stdlib-only leaf; review_config takes a single
one-directional, acyclic dependency on it (same intra-_common pattern as
team_signal→project_layout, review_evidence→parsing), and its docstring was
honestly downgraded from "stdlib only" to "near-leaf". The anchored exclusion
(plugins/ ancestor + exact `jig` segment on skill_dir.parent.parts) is a real,
well-tested improvement over the scope-blind bug. No blockers.

## SPECIFIC ISSUES
- [strength][impl] exclusion invariant asserted against the real scaffold writer.
- [strength][impl] anchoring on skill_dir.parent.parts avoids misclassifying a
  non-jig plugin shipping a skill literally named `jig`; exact-segment `in` avoids
  `jig-tools`.
- [nit][impl] skill_discovery module docstring "mirrors ... review_config" was
  stale (review_config now imports it) → fixed.

## RECONCILIATION NOTES
- OQ4 path test couples to the host's plugin-cache dir shape (jig doesn't own it)
  and fails OPEN; recorded as a known risk for 096-03, not a settled fact.
- Codex admin-scope exclusion unproven (every plugin test uses a Claude-style
  path); AC5 "every scope both hosts" is proven for Claude + project scope, a
  096-03 obligation for Codex admin. Both recorded in the deviation log.
- Module boundary consistent with precedent; architecture.md _common list
  refreshed; no ADR/boundary-doc change warranted (ADR-0040 governs).
