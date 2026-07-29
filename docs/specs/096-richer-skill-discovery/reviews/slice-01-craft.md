---
slice: 096-01 — config-precedence
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (craft pass / pr-review)
reviewed_at: 2026-07-29T01:32:01Z
prompt_source: review.py pr-review
---

## VERDICT
pass

## REASONING
A clean, well-scoped realization of config-first precedence.
`review_config.configured_skill` is a stdlib-only leaf mirroring
`project_layout`, with a disciplined loud-structural-error /
quiet-baseline-fallback split. The three builders route through
`_resolve_richer_skill` (config wins, legacy retained per AC4); `record-review`
derives `substrate: config` without amending the ADR-0014 gate; the four
SKILL.md prose notes accurately state the orchestrated-pass-only limitation.
Tests are hermetic and cover the AC edge matrix. Only minor doc-drift and a
slightly over-promising field name — none blocks REVIEWED.

## SPECIFIC ISSUES
- [nit][impl] review.py — module header + `build_pr_review_prompt` /
  `build_arch_review_prompt` docstrings still describe dispatch as
  `detect_richer_skill()`-only, omitting the config-first `_resolve_richer_skill`
  precedence; the code-health docstring WAS updated, so the three are now
  inconsistent. → reconciliation fix.
- [nit][impl] review.py — `_config_substrate_lines` re-derives `applied_skill`
  from config presence, independent of what the reviewer actually did; the field
  name reads as "what was applied" rather than "what was configured". → add a
  caveat / record the configured identifier.
- [strength][impl] review_config.py — the loud-vs-quiet contract is exemplary
  (structural authoring mistakes raise; broken/unrelated scaffold.json and
  unresolvable-but-well-formed names both degrade to None).
- [strength][impl] test_review.py — explicit regression guard that a
  substrate-bearing artifact still parses with `verdict:` intact + all canonical
  fields, directly protecting the ADR-0014 gate from silent amendment.

## RECONCILIATION NOTES
- Host-parity scope seam: bare-name config resolves Claude-only (`~/.claude`);
  Codex bare-name arrives with 096-02's multi-scope resolver. AC5 tension is a
  documented 096-01→096-02 boundary, not a defect — log it.
- AC6 literal ("when key present") vs implementation (stamps only when it
  resolves) — config-present-but-unresolvable audit deferred to 096-05.
