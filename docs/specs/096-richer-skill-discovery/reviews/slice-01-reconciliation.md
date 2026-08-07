---
slice: 096-01 — config-precedence
pass: reconciliation
verdict: pass
reviewer: jig:reviewer subagent (reconciliation pass)
reviewed_at: 2026-07-29T01:39:38Z
prompt_source: review.py reconciliation
---

## VERDICT
pass

## REASONING
The deviation log's five claims + two scope-seam notes all match the code:
`review_config.configured_value` returns the raw identifier and
`_config_substrate_lines` records it (portable-identifier switch is real);
`_config_substrate_lines` swallows `ReviewConfigError` while
`_resolve_richer_skill` propagates it; the module header + pr/arch docstrings are
config-first; `code_health` gained net-new dispatch; the AC6-narrowing to
"resolves on this machine" is faithfully implemented; the four AC7 SKILL.md notes
exist and propagated to host packages. Two doc-hygiene nits were caught and fixed
in reconciliation (see below). No misrepresentation of what was built.

## SPECIFIC ISSUES
- [nit][impl] review.py record-review main() comment said "resolved
  applied_skill", contradicting the portable-identifier change → FIXED in
  reconciliation (comment now says PORTABLE configured identifier).
- [nit][impl] slice close-out box for the AC7 SKILL.md notes was unchecked though
  the notes already existed → FIXED (checked, noted done-in-implementation).

## RECONCILIATION NOTES
- Portability guarantee is bare-name-scoped: an explicit absolute path a user
  writes in scaffold.json is recorded verbatim (their own committed value, not
  jig-injected). Clarified in the deviation log so "portable identifier" is not
  read as universal.
