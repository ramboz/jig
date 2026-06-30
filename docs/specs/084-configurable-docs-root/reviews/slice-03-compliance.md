---
slice: 084-03 — scaffold-init `--docs-root` flag + layout-aware output
pass: compliance
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T15:24:27Z
prompt_source: review.py compliance (084-03); jig:reviewer subagent
---

VERDICT: pass

All six ACs met. Default (docs_root="docs") is byte-preserving: no `layout`
block, no brief caveat, `_compose_layout_rewrite` returns the existing transform
unchanged, docs tree stays under target/docs. `--docs-root .` collapses the layer
end-to-end, validates before any write (AC4 no-partial), threads every
docs-writing site (seed, convention block, brief, manifest, copy_machinery), and
the `(?<![\w/])docs/` rewrite rule is correctly anchored. The subtree push-refusal
branches on the sentinel-resolved subproject root vs git_toplevel, placed before
mode routing.

Resolved in reconciliation:
- [FIXED] brief.md `people.md` prose line is now layout-aware (was naming
  docs/memory/people.md regardless of docs_root).
- [FIXED] AC2 strengthened with a real status-board command round-trip test
  (test_status_board_command_round_trip), not just a bare helper call.

Documented deferral (acceptable): verify_install's doc-link smoke check is
skipped for non-default layout (scaffold_contract.scaffold_doc_problems is
docs/-shaped); rewritten links covered by scaffold-init's own tests.
