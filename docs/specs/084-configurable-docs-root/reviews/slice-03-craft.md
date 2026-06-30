---
slice: 084-03 — scaffold-init `--docs-root` flag + layout-aware output
pass: craft
verdict: pass
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-30T15:24:27Z
prompt_source: review.py craft (084-03); jig:reviewer subagent
---

VERDICT: pass

Craft is clean and consistent. docs_root validated once at the top of scaffold()
then threaded as a normalized string; `_compose_layout_rewrite` handles both the
machinery (existing non-None) and plugin-only (None) paths with correct ordering
(machinery transform first, layout collapse second). The `(?<![\w/])docs/` regex
is the right tool for rendered link text and correctly anchored. git_toplevel /
subtree guard placement, and the CLI-subprocess + real-git-init tests, are sound.
No blockers.

Resolved in reconciliation:
- [FIXED] the `target if docs_root=="." else target/docs_root` base, previously
  inlined at 4 sites, is now a single `_scaffold_docs_base(target, docs_root)`
  helper (project_layout.docs_base can't be reused — the sentinel isn't on disk
  yet during render).

Deferred (logged): test_compose_default_is_passthrough's object() sentinel is
slightly obscure (cosmetic); verify_install doc-link deferral noted above.
