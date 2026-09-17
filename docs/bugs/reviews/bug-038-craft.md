---
bug: 038
pass: craft
verdict: pass
reviewer: pr-review skill craft pass
reviewed_at: 2026-09-17T19:55:58Z
prompt_source: pr-review skill craft pass (diff-shaped; /tmp/craft038_prompt.txt)
---

Independent craft (pr-review methodology) pass (jig:reviewer subagent,
read-only, diff-shaped).

VERDICT: PASS

Verified correct: the new branch fires only for `status == "Proposed" and not
lv`; a Proposed ADR *with* last_verified falls through to the existing
conjunctive dep-change path (pinned by a scope-guard test). `age_days > days` is
the right boundary, consistent with `_stale_check`. Hoisting `rel` above the
skip is inert (pure path computation); reading `status` is side-effect-free; the
`stale()` renderer is category-agnostic and unchanged. The regex is
`^`-anchored per line, case-insensitive, with an optional `**Status:**` prefix,
and cannot match the frontmatter `status: Proposed`, a `## Proposed` heading, or
an `Accepted (...)` line; `last_verified` is never conflated with the proposal
date. Tests pin both detection and scope-guard behavior non-vacuously.

Non-blocking residuals (all documented): the `**Status:**`-prefixed regex
alternative and the `_file_modified_iso` fallback are untested; and because the
extractor uses document-wide `search`, a stray earlier `Proposed (date)` line
would win over the `## Status` line (low risk given the pattern's specificity).
No correctness blocker, broken invariant, or vacuous test found.
