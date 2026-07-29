---
slice: 096-01 — config-precedence
pass: compliance
verdict: pass
reviewer: jig:reviewer subagent (compliance pass)
reviewed_at: 2026-07-29T01:32:01Z
prompt_source: review.py implementation
---

## VERDICT
pass

## REASONING
All seven ACs for slice 096-01 are met with hermetic tests exercising each.
`review_config.configured_skill` resolves the three categories with the AC1
name/path + user-scope seam; AC2's loud-on-structural / quiet-on-runtime-absence
split is correct and tested; the three builders wire config-first resolution via
`_resolve_richer_skill` (config wins over the retained legacy
`detect_richer_skill`, AC4); `record-review` derives `substrate: config` +
`applied_skill` from observable config state without amending the ADR-0014 gate
(AC6, verified: gate reduces to `verdict == pass`, extra keys tolerated); all
four SKILL.mds carry the AC7 orchestrated-pass-only caveat. No correctness bugs.

## SPECIFIC ISSUES
- [nit][impl] review.py — `applied_skill` is stamped as an absolute,
  machine-specific path in committed evidence (ADR-0014 audit trail); a
  teammate's recording would differ. → reconciliation fix (record the configured
  identifier, not the resolved absolute path).
- [nit][impl] review_config.py — bare-name config resolves against `~/.claude`
  only; on Codex a bare name never resolves until 096-02 adds multi-scope. The
  documented AC1/AC5 scope seam, not a bug. → reconciliation log.

## RECONCILIATION NOTES
- AC6 stamps `substrate: config` only when the configured skill actually
  RESOLVES on this machine (not merely when the key is present) — the honest
  "record what was applied" reading; the config-present-but-unresolvable audit
  case is deferred to 096-05 per AC6's "minimum viable half". Log it.
- `_config_substrate_lines` swallows `ReviewConfigError` (returns "") whereas
  `_resolve_richer_skill` propagates it — intentional (the structural error
  already surfaced loudly at prompt-build time). Note in deviation log.
- Post-DONE close-out items pending: Spec 053 `## Amendments`, status-board regen.
