---
status: ROOT_CAUSED
tier: standard
severity: medium
claimed_by: claude/bug-copy-machinery-mode
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

# Bug 018: copy-machinery-leaves-mode-inconsistent

> **Numbering note:** 015–017 are taken by unmerged PRs
> [#143](https://github.com/ramboz/jig/pull/143) and
> [#144](https://github.com/ramboz/jig/pull/144). `bug.py new` re-allocated 015
> on a main-rooted worktree, so this record was renumbered by hand.

## Symptom

`migrate.py copy-machinery` converts a plugin-mode project to in-repo, but the
project's **own records still describe plugin mode afterwards**:

- `scaffold.json`'s `scaffold_mode` stays `"plugin-only"`.
- `docs/workflow.md` still cites `${CLAUDE_PLUGIN_ROOT}/skills/…` — the variable
  that is unset for the plugin-less population this route exists to rescue.

So a "recovered" project has working machinery under `.claude/skills/` and a
manifest and workflow doc that both contradict it.

This matters more than it used to: spec 099-01's plugin-mode summary line names
`migrate.py copy-machinery` as **the** recovery route for a project scaffolded
without a plugin, so the command is now advertised on the default path.

## Repro

On unmodified `main@bde9dfc`:

```bash
mkdir -p /tmp/cmprobe
python3 skills/scaffold-init/scaffold.py /tmp/cmprobe --plugin-only --solo
python3 -c "import json;print(json.load(open('/tmp/cmprobe/scaffold.json'))['scaffold_mode'])"
#   -> plugin-only                                   (correct so far)

python3 skills/migrate/migrate.py copy-machinery /tmp/cmprobe
#   -> copied machinery into /tmp/cmprobe/.claude    (exit 0)

ls /tmp/cmprobe/.claude/skills | wc -l
#   -> 8                                             machinery IS there
python3 -c "import json;print(json.load(open('/tmp/cmprobe/scaffold.json'))['scaffold_mode'])"
#   -> plugin-only                                   <-- still, after conversion
grep -c 'CLAUDE_PLUGIN_ROOT' /tmp/cmprobe/docs/workflow.md
#   -> 3                                             <-- docs still point at the plugin
```

## Evidence

`copy_machinery` in `skills/migrate/migrate.py` calls
`scaffold_mod.copy_machinery(...)` to place the files, then commits **only** the
tier set:

```python
# Commit the raised tier set only after the delta skills copied cleanly.
if commit_tiers is not None:
    scaffold_mod.write_installed_tiers(project_dir, commit_tiers)
```

No `scaffold_mode` write exists anywhere on the path, and no doc render — the
function's whole contract is "copy files + record tiers".

That is coherent for the job it was **originally** built for. Slice 021-01
introduced `copy-machinery` for *migrating an existing project into jig* and for
*tier upgrades* — cases with no prior `scaffold_mode` claim to contradict. It
was never a mode-conversion command. Spec 099-01 then pointed users at it as
one, without changing it.

So this is not a regression in `migrate.py`. It is a **contract widened by a
caller in a different slice, without the callee being told.**

## Hypotheses

- [ ] H1: `copy_machinery` writes `scaffold_mode` but something later overwrites
  it. Falsify by grepping the call path for `scaffold_mode` writes — there are
  none; only `write_installed_tiers` touches the manifest. **Falsified.**
- [ ] H2: the docs are re-rendered, and plugin-root citations are correct in
  in-repo mode anyway. Falsify by reading the emitted file: `docs/workflow.md`
  is byte-unchanged by the command, and in-repo docs are supposed to cite
  `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-…` (what a `--in-repo` scaffold
  produces). **Falsified.**
- [x] H3 (leading): `copy-machinery` was built to copy files and record tiers,
  never to convert a mode, and 099-01 advertised it as a mode converter without
  widening it. **Confirmed** by the call path and by 021-01's stated scope.

## Root cause

`migrate.py copy-machinery`'s contract is "place machinery, record tiers". A
project's *mode* is expressed in three places — the files on disk, the
`scaffold_mode` manifest field, and the paths the rendered docs cite — and the
command updates only the first.

## Fix class

## Fix

Not yet fixed. **A scope decision is needed first, and it is not obvious**, so
this is recorded rather than guessed at.

**Part 1 — the manifest — is unambiguous.** After a successful copy the project
*is* in-repo, so `scaffold_mode` should say so. Safe, mechanical, no user data
involved.

**Part 2 — the docs — is not**, and is why this record does not simply ship a
fix. Re-rendering `docs/workflow.md` would silently **overwrite a file the user
is expected to edit**. Scaffolded docs ship as `Status: Draft
(wizard-generated)` and the workflow invites the project to make them its own;
by the time anyone runs `copy-machinery`, those docs may carry real project
content. A conversion command that eats them is a worse bug than the one it
fixes.

Three candidate dispositions for part 2:

1. **Warn, don't rewrite.** Emit a note naming the files that still cite the
   plugin root and what to change. Cheap, safe, honest — the user keeps their
   edits and knows what is stale. *Current preference.*
2. **Rewrite only jig-owned marker blocks.** The scaffold already uses delimited
   blocks elsewhere (`>>> jig secret-ignore >>>`), so a bounded rewrite is
   conceivable — but `docs/workflow.md`'s plugin-root citations sit in ordinary
   prose, not inside a marker, so this needs the blocks to exist first.
3. **`--rewrite-docs` as an explicit opt-in**, default off, refusing when the
   file has diverged from its rendered template.

**Also worth deciding**: whether `copy-machinery` should own mode conversion at
all. The command is reached by a user who by definition has **no plugin
installed** — and `migrate.py` lives *inside the plugin*. The advertised
recovery route may not be runnable by the population it targets, which is a
defect in the advice rather than in the command, and belongs to spec 099-01's
summary line rather than here.

## Already tried

Nothing discarded. H1 and H2 were falsified by reading the call path and probing
the emitted files, before any edit.

## Regression test

None yet. Once scoped, the manifest half is straightforward: scaffold
`--plugin-only`, run `copy-machinery`, assert `scaffold_mode == "in-repo"`.

It must be written against a *scaffolded* project. `copy-machinery` on a project
with no `scaffold.json` legitimately has no mode to flip, so a test taking that
path would pass without proving anything.

## Proof

## Learning
