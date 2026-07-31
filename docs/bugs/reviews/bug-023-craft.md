---
bug: 023
pass: craft
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-07-30T22:44:50Z
prompt_source: pr-review skill craft pass (9 rounds; verdict from the final pass)
---

Craft pass via this project's baseline `skills/pr-review/SKILL.md`
methodology. Re-review after eight rounds; the previous craft pass returned
`pass` and its remaining items are applied.

**The change.** `read_host_renderer` in `skills/scaffold-init/scaffold.py`
sits with its siblings `read_scaffold_mode` / `read_installed_tiers` and
keeps their contract exactly: every unusable manifest shape — absent,
unreadable, field missing, wrong-typed, unrecognised host — collapses to
`None`, so callers need one fallback branch. The `isinstance` guard correctly
precedes the `in _HOST_RENDERERS` membership test, so a hand-edited list-
valued field cannot raise on an unhashable key. `renderer_for_host` becomes a
dict lookup over the same registry — one structure, two readers.
`migrate.copy_machinery` gains two lines and a comment naming why its two
host arguments are deliberately different.

**Test integrity.** All 12 methods in `CrossHostAdvisoryTests` were traced
against the pre-fix expression. The four the record claims as red fail for
their stated reasons; the two accessor tests error on the missing symbol; the
remaining five (two premise guards, three degrade paths) pass pre-fix and are
labelled as such rather than claimed as red. Each degrade test still pins a
distinct production line — `or resolved_host`, the `try/except`, and the
membership check that keeps an unknown host from silently becoming Claude.
`test_stale_docs_are_still_not_rewritten_across_hosts` carries the
"advisory fired" precondition that bug 018's craft pass demanded, so it
cannot pass on a buggy build for the wrong reason.

`test_stale_docs_are_still_not_rewritten_across_hosts` uses `startswith`
rather than `assertEqual` deliberately: `copy-machinery` legitimately appends
managed convention blocks to `docs/workflow.md` (see
`CopyMachinerySelfDefiningConventionTests`), so `assertEqual` would fail.

**`host_specific_spellings()`.** The AST walk is correct — `ast.Attribute`
named `replace`, two string-literal args, both sides collected. Filters are
principled: empty right-hand sides of deletions and literals with interior
newlines are dropped, with no length cap (an earlier version capped at 32
characters, which `${CLAUDE_PLUGIN_ROOT}/templates/` hits exactly — a
silent-drop path one character away). It bans nothing legitimate in the
guarded section today. Parsing another module's AST from a test is a real
coupling, and the right trade here: the failure mode is loud (empty set →
explicit assertion) where the hand-written list it replaced failed silently,
three times. A back-reference comment in the builder names both the total and
partial restructure risks.

**Prose weight.** The call-site comment is down from 22 lines to the
asymmetry it protects; the reasoning lives in `_stale_docs_warning`'s own
docstring, so a callee's contract no longer requires reading one caller's
inline comment. `read_host_renderer`'s docstring lost the two navigation
paragraphs its remote placement had needed. The guard test's docstring defers
its version history to the record rather than restating it — which is what
the restatement drift across six sites cost to learn.

**Mirrors.** `hosts/claude/**` and `hosts/codex/**` are byte-identical to
their sources at every changed line, and the advisory section renders
identically in both — which is the property the guard asserts.

**Claims match code.** The four-attempt guard history now agrees across
`## Fix`, `## Proof`, the mutation-checked paragraph, `## Deviations`,
`docs/memory/learnings.md`, and both test docstrings. The append rationale
matches the code in both record sites and the test comment: case-insensitivity
comes from `.lower()` on both sides; the bare host names are a floor against a
partial builder restructure. The scope statement names what is and is not
mechanically enforced, including the delegate-rewritten paths section identity
cannot see when their rewrite is prefix-gated.

Full suite 3847 tests, OK (skipped=7), exit 0. Host packages rebuilt and in
sync.

No defects.
