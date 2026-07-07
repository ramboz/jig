---
bug: 004
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-07T05:04:37Z
prompt_source: pr-review skill craft pass
---

VERDICT: pass

REASONING:
The fix cleanly implements terminal-row segregation in `_render_board` with a
well-factored `_render_row` helper and shared `_BOARD_HEADER`/`_BOARD_SEPARATOR`/
blurb constants, faithfully mirroring the spec board's `render_deferred_table`/
`render_abandoned_table` precedent (empty-set omission, same-shape table so
`_parse_existing_notes` keeps working). The `TerminalSegregationTests`
assertions genuinely pin behavior — position via index ordering,
DONE-stays-active omission, and note migration from a legacy flat board —
rather than trivially passing. The Gotchas bullet is accurate and well-worded,
and all four host mirrors are byte-faithful to source.

SPECIFIC ISSUES:
- skills/bug-fix/bug.py — when every bug is terminal, the active table renders
  a bare header+separator with zero rows. Valid markdown, but the edge was not
  asserted. ADDRESSED post-review by adding
  `test_all_terminal_renders_empty_active_table`.

RECONCILIATION NOTES:
- No spec deviations; fix scoped to bug 004's two surfaces (renderer + Gotchas).
  `fix_class: observability` honestly labelled.
- The double list comprehension over `rows` is acceptable at bug-board scale;
  no simplification warranted.
