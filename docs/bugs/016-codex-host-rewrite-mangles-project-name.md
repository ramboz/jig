---
status: REPORTED
tier:
severity: low
claimed_by:
regression_test:
main_repro_checked_at: 2026-07-29
main_repro_ref: bde9dfc
main_repro_result: reproduces
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
---

# Bug 016: codex-host-rewrite-mangles-project-name

## Symptom

On the Codex host, a project whose directory name contains `Claude` is
**renamed** in its own generated documents. A project at `Claude-Tools/` gets
an `AGENTS.md` headed `# Codex-Tools`.

The project's real name is user data. The scaffold rewrites it.

## Repro

```bash
mkdir -p /tmp/Claude-Tools
python3 skills/scaffold-init/scaffold.py /tmp/Claude-Tools --host codex --solo
head -1 /tmp/Claude-Tools/AGENTS.md      # => "# Codex-Tools"  (expected "# Claude-Tools")
```

Reproduces on unmodified `main@bde9dfc`. Case-sensitive: a lowercase
`claude-tools` survives, because the transform replaces `Claude`, not `claude`.

## Evidence

Found while fixing [bug 015](015-codex-brief-seed-claude-md-leak.md) — the same
ordering fault, in different files. 015 fixed `brief.md` and the seed spec by
applying the host transform *before* substitution; this record covers the paths
that still apply it *after*.

- `copy_template` renders substitutions first, then `post_render`.
- `scaffold()` passes `doc_rewrite` as `post_render` for the primer and for the
  whole `docs/` tree.
- `CodexScaffoldRenderer.rewrite_skill_md_paths` ends with a blanket
  `out.replace("Claude", "Codex")`.
- `PROJECT_NAME` is `target.name` — user-derived — and is substituted before
  that replacement runs.

Every rendered doc interpolating `PROJECT_NAME` is therefore exposed, not only
the primer. The blast radius is **not yet enumerated**; the primer is simply the
one that was probed.

## Hypotheses

- [ ] H1: the blanket `Claude` → `Codex` replacement is too broad in general and
  should be narrowed to specific phrases (`Claude Code`, `CLAUDE.md`). Falsify
  by checking whether narrowing still catches the prose occurrences the Codex
  docs legitimately need translated — if it misses some, the breadth is wanted
  and the ordering is the real fault.
- [x] H2 (leading): the transform is applied at the wrong point, not written too
  broadly — substituted values should never reach a prose transform. Confirm by
  moving the primer/`docs/` renders onto the `pre_render` hook bug 015 added and
  checking output is otherwise byte-identical.

## Root cause

Not yet confirmed — see H2. Leading explanation: the host transform runs
post-substitution on these paths, so it is shown user data it should never see.

## Fix class

## Fix

Not fixed. Deliberately deferred out of bug 015: that bug's repro grep searched
only for `CLAUDE.md`, and widening its fix to the primer and the entire `docs/`
tree changes already-shipped output for every Codex project — which deserves its
own before/after diff and its own review rather than riding along inside a fix
for a different symptom.

**Likely small:** move those `copy_template` calls from `post_render=` to
`pre_render=` for the host half, exactly as `_emit_seed_spec` now does. The
`pre_render` hook already exists (added by 015).

## Already tried

Nothing — deferred before any attempt.

## Regression test

None yet. Note that bug 015's
`CodexScaffoldAdapterTests::test_codex_host_rewrite_does_not_mangle_project_name`
covers **only** `brief.md` and the seed spec. The primer and `docs/` tree are
uncovered, which is why this needs a record rather than a comment.

## Proof

## Learning
