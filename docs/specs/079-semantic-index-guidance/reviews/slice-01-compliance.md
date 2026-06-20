---
slice: 079-01 — workflow.md index guidance
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-20T15:38:00Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All four ACs are met. The "### Reach for a semantic/code index" subsection sits inside `## Context-cost discipline` and covers when (turn-count / search-round-trip threshold), which (portable options centered — IDE/LSP, local symbol indexer, Glean/Kythe — with Adobe-internal tools demoted to "if available"), and the detect-installed-else-recommend / install-nothing stance. Install-nothing framing ("jig never vendors or auto-installs"), honest-about-limits ("not a savings guarantee" / "context isn't free"), and the docs-only constraint (CLAUDE.md carries no such section) are all present. The test asserts each load-bearing claim per AC including section placement and the negative CLAUDE.md check; honors design principle 5 (BYO depth / jig provides the floor); adds no skill/hook/subagent/MCP.

SPECIFIC ISSUES:
- docs/workflow.md — (Low, ADDRESSED post-review) `ctags` was grouped under a "tree-sitter-based" label though it uses its own parser; reworded to "A local symbol indexer (`ctags`, or tree-sitter-based tooling / a local code-search MCP)".

RECONCILIATION NOTES:
- 079-02 (scaffold nudge) remains correctly deferred/conditional per the spec. When 079-02 is DEFERRED and this slice closes the spec, run the close-out (status-board regen; CLAUDE.md active-specs already "none" so no compression needed).
- The implementation note about `migrate copy-machinery` flowing the section is moot: migrate copies a project's OWN workflow.md, not jig's. Record in the deviation log.
