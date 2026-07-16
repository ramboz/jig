---
bug: 012
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent (independent, read-only)
reviewed_at: 2026-07-16T20:38:40Z
prompt_source: review.py bug-review
---

Independent reviewer subagent (read-only), prompt built by `review.py bug-review`.

**Round 1 — needs-changes.** Five issues. The material one: the fix's template
resolution (`CLAUDE_PLUGIN_ROOT`, else `parents[2]/templates/`) is unreachable in
**Claude scaffold mode**, which copies `skills/` but not `templates/` — so
`add-lightweight` fails there with `template not found`, "mode 1 in a new costume,
with no remedy named", for exactly the population the bug names. Plus: the CLI seeded
before validating input (a rejected call left a file behind with no signal); the new
messages used the hardcoded `_LIGHTWEIGHT_REL` while the write routed through
`project_layout` (misreports under spec-084 `docs_root: "."`); `dedup` ran before the
`## Entries` gate (a foreign file with a matching heading returned a silent "already
recorded"); and `--docs-root .` was untested.

**Response.** The scaffold-mode gap was reproduced (`env -u CLAUDE_PLUGIN_ROOT`
against a copied helper) and confirmed as **not a regression** (that mode failed
before) and **inherited** (`adr.py:73-81` is identical). It is deliberately NOT closed
here: the fix is a design fork with blast radius across both helpers and every
scaffolded `.claude/` — deferred to the maintainer, asked on #109, parked in
`refinement-todo.md`, recorded under `## Remaining risk`, `fix_class` qualified as
"structural for plugin-mode installs", and mitigated by an error naming two
verified-working remedies (`UnreachableTemplateTests`). The other four were fixed,
each with a test that was red first.

**Round 2 — pass.** Re-verified all five in the code rather than on trust; confirmed
the `CodexCopyMachineryTests` anchor claim is real and not decorative; confirmed the
hosts trees are re-synced. Judged finding 1's handling as "the way I'd want an
inherited, out-of-scope gap handled: confirmed rather than argued away".

Three non-blocking residuals raised in round 2, all since addressed: the record's
"asked on #109" was past-tense-but-unposted at read time (the comment is now posted
and linked); `_foreign_format_error` still hardcoded the path on the *error* path
(fixed — `test_error_names_the_real_path_under_track_local_docs_root`); and
`migrate.py`'s bare "template not found" was asymmetric with `decisions.py`'s
(fixed). Its reconciliation notes drove the `refinement-todo.md` entry for the design
fork and the `docs/inbox.md` entry for the `bug.py new` number collision.
