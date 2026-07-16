---
bug: 012
pass: craft
verdict: pass
reviewer: jig:reviewer subagent (independent, read-only)
reviewed_at: 2026-07-16T20:41:35Z
prompt_source: pr-review skill craft pass
---

Independent reviewer subagent (read-only), running the `pr-review` skill's
diff-shaped methodology (no `review.py pr-review` builder exists for bugs — that
builder requires a spec + slice; recorded per bugs 001–003 precedent).

**Round 1 — needs-changes.** Nine issues. The material one, and the best catch of
this session: the new Stop-nudge emitted
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/memory-sync/decisions.py"` — the **only**
`${CLAUDE_PLUGIN_ROOT}/skills/…` literal in all of `hooks/` — which resolves in Claude
*plugin* mode alone. In Claude scaffold mode `CLAUDE_PLUGIN_ROOT` is unset and it
expands to `python3 "/skills/memory-sync/decisions.py"`; the Codex rewrite maps it to
a root the plugin package doesn't use. Every sibling hook resolves both modes at
runtime via `SCRIPT_DIR` precisely because both exist. As the reviewer put it:
shipping an agent-facing command that fails in 2 of 3 install modes is this bug's own
failure shape — "jig tells an agent where to write but never what shape" — one surface
later. Verified and fixed: the nudge now names the command, not a path, guarded by
`test_summary_command_is_host_neutral` (red before).

Also round 1: `_foreign_format_error` still hardcoded `_LIGHTWEIGHT_REL` while
`_display_path` existed for exactly that reason — the spec-084 fix was **half-applied**
to the success path only, so the *error* path named a file that doesn't exist under
`docs_root: "."` (both passes caught this independently); a `%`-format call in an
f-string file; a comment restating the user-facing string beneath it; docstrings
arguing the change to a PR reader rather than stating constraints; a test helper
defined after use; and `_display_path`'s fallback returning a guaranteed-wrong path.
All fixed. One nit (double `seed_lightweight`/`_require_entry_fields`) was argued and
knowingly kept — the reviewer agreed on re-review that keeping `add_lightweight ->
bool` is the right call.

**Round 2 — pass.** Verified all nine against the source rather than the summary,
including that the new `assertNotIn` guard is load-bearing (an `assertIn` alone would
pass on the buggy substring). Caught one real defect in the *record*: `## Proof` still
claimed 3342/+21 from before the follow-up tests, contradicting the 3350/+29 run it
cited — corrected, along with three stale per-file counts. Its note that
`green_confirmed_at` was unset was withdrawn as a workflow-ordering misread (the
`→ REVIEWED` gate stamps it).
