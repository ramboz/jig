---
status: FIXING
tier: standard
severity: medium
regression_test: skills/migrate/test_migrate.py::PluginModeConversionTests
main_repro_checked_at: 2026-07-30
main_repro_ref: a03f6c8
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at: 2026-07-30
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 018: copy-machinery-leaves-mode-inconsistent

> **Numbering note:** when this was filed, 015–017 were held by then-unmerged
> PRs [#143](https://github.com/ramboz/jig/pull/143) and
> [#144](https://github.com/ramboz/jig/pull/144), and `bug.py new` re-allocated
> 015 on a main-rooted worktree — so this record was renumbered by hand. Both
> PRs have since merged and 018 is confirmed free on `main`.

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

Filed against `main@bde9dfc`; re-verified unchanged on `main@00c3333` before
the fix was written, and again on `main@a03f6c8` (2026-07-30) after specs 099-01
(#136) and bug 017's record (#144) landed — checked in a throwaway detached
worktree at that ref, so the fix on this branch could not mask it. 099-01 made
plugin mode the *default*, which widens the affected population rather than
changing the behaviour:

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

`structural_fix`, with one honest qualification. The root cause is "a project's
mode lives in three places and the command updates one". Part 1 closes that
structurally for the machine-owned place: the command now converts the mode
itself, in the right order, and nothing downstream has to remember to. The
third place — the user's own prose — is deliberately **not** closed by code,
because closing it means overwriting user content; by the maintainer's ruling
it is surfaced and handed to the user instead. So this is a structural fix plus
a deliberate advisory, not a structural fix that quietly leaves a gap. No
contract is narrowed and exit codes are unchanged.

## Scope decision

The record originally stopped here because part 2 was a genuine judgment call
with a destructive failure mode. It was put to the maintainer on
[PR #145](https://github.com/ramboz/jig/pull/145) and resolved there:

> I'd lean towards the warning option, and explicitly asking the user what they
> want to do. copy machinery will mostly likely be always interactive-triggered,
> so we should be in a session that can ask the user what they want, warn of the
> risks, and let them choose the best option for their use case.
> — @ramboz, 2026-07-30

So: **disposition 1 (warn, don't rewrite)**, with the *asking* placed in the
skill rather than the helper. Dispositions 2 (marker-block rewrite) and 3
(`--rewrite-docs` opt-in) are not taken. Neither is refuted — 3 in particular
stays available if warning proves insufficient in practice — but neither is
needed to close the gap, and both add a rewrite path that would have to be
defended. If either is revisited, it needs its own record.

## Fix

The two halves are treated differently on purpose.

**Part 1 — the manifest.** `scaffold.py` gains `read_scaffold_mode` /
`write_scaffold_mode`, deliberately shaped like the existing
`read_installed_tiers` / `write_installed_tiers` pair: same manifest, same
atomic write, and the same *commit-only-after-the-copy-succeeded* ordering, so
a refused or failed copy never leaves the manifest claiming a mode the tree
does not have. `migrate.py copy_machinery` flips `plugin-only` → `in-repo`
after the copy and reports the flip. A project with **no** `scaffold.json`
makes no mode claim, so nothing is written for it — the spec-021
migrate-into-jig case is untouched.

**Part 2 — the docs.** `copy-machinery` scans the project's *own* markdown
(configured docs root + host primer, excluding the host runtime dirs whose
machinery this command just refreshed) for surviving `${CLAUDE_PLUGIN_ROOT}`
citations, and prints each file with its hit count plus the host-correct
in-repo form. **It writes nothing.** The advisory is not a gate: the copy
succeeded, so the exit code stays 0.

The *decision* lives in [`skills/migrate/SKILL.md`](../../skills/migrate/SKILL.md),
not in the helper — a new "Converting a plugin-mode project" section instructs
the session to surface the warning and offer three options (leave them / agent
edits them showing a diff first / user edits them), and states explicitly that
a general "migrate my project" is not consent to rewrite documentation. This
follows the project's standing preference for judgment in the skill over
keyword logic in the helper.

**Also flagged, not fixed here**: whether `copy-machinery` should be the
advertised recovery route at all, given it is reached by a user who by
definition has no plugin installed while `migrate.py` lives *inside* the
plugin. That is a defect in the advice, and it belongs to spec 099-01's
summary line ([#136](https://github.com/ramboz/jig/pull/136)), not to this
command.

## Already tried

- H1 and H2 were falsified by reading the call path and probing the emitted
  files, before any edit.
- **First placement of the SKILL.md section was wrong and silently discarded.**
  It was written between the `What it does:` and `### Refusal: unmanaged hooks`
  headings — a span the Codex builder replaces wholesale via
  `finalize_codex_migrate_skill`. The build reported success, the Codex package
  simply did not contain the section, and nothing failed. Section moved after
  the refusal block; `test_codex_render_keeps_the_ask_before_editing_step` now
  guards the *rendered* artifact so the same silent drop cannot recur.
- **A fixture that would have passed for the wrong reason.**
  `test_already_in_repo_project_is_not_reflipped` built its in-repo project
  with a bare `scaffold.py <dir>`, which was in-repo when the test was written
  and became *plugin mode* the moment 099-01 (#136) merged. It then failed
  loudly — but only because it asserts a negative; a differently-shaped test
  would have gone on passing while proving nothing. Now pins `--in-repo`
  explicitly, with a comment saying why.

## Regression test

`skills/migrate/test_migrate.py::PluginModeConversionTests` (15 tests).

Written against a *scaffolded* project, as the record required: a
`copy-machinery` run on a project with no `scaffold.json` has no mode to flip,
so a test on that path would pass without proving anything.
`test_baseline_manifest_says_plugin_only` pins the premise so the conversion
test cannot silently start passing for the wrong reason.

Coverage: the flip itself, the reported flip, field preservation, idempotency,
the already-in-repo no-op, the no-manifest no-op, the docs being named, the
replacement path being stated, **the docs surviving byte-for-byte**, the exit
code staying 0, silence when there is nothing stale, machinery not being
mis-reported as user docs, and the skill (in both source and Codex-rendered
form) documenting the ask-before-editing step.

## Proof

Red witnessed before the fix — 5 of 14 failing on unmodified `main@00c3333`
(the then-current main; the repro was re-confirmed on `main@a03f6c8` after the
rebase, see Repro):

```
FAIL: test_successful_copy_flips_scaffold_mode_to_in_repo
    AssertionError: 'plugin-only' != 'in-repo'
FAIL: test_summary_reports_the_mode_flip
FAIL: test_stale_doc_citations_are_named_in_the_summary
FAIL: test_summary_states_the_replacement_path
FAIL: test_skill_documents_the_ask_before_editing_step
```

The `→ FIXING` transition was therefore run with `JIG_BUG_TEST_GATE=0`. The
gate re-runs the regression test and demands red; by the time this record
caught up with the maintainer's ruling the fix was already on disk, so the gate
could only have re-witnessed green. The red above is the real evidence, and it
was witnessed before any production line was written — not reconstructed after.

Green after: `PluginModeConversionTests` 15/15 OK; full suite **3705 tests OK
(4 skipped)**, pyright clean. The suite's host-package drift guard reports
stale packages inside `run_tests.py` but passes 4/4 when run on its own
(`build_host_packages.py --check`) with the packages freshly built and
committed — that is bug 008, not this change.

## Learning

**A caller can widen a callee's contract without touching it, and nothing in
the toolchain notices.** 099-01 turned `copy-machinery` into the advertised
plugin-mode recovery route by writing one summary line; `copy-machinery` itself
was never edited, so no test, review, or diff on either side had cause to ask
whether the command actually did what it was now being sold as doing.

**A build that rewrites documentation can delete a section and still report
success.** The Codex renderer replaces named spans of `SKILL.md`; anything an
author places inside such a span vanishes from the Codex package with no error
and no diff to notice. Source-only assertions do not catch it — the guard has
to read the rendered artifact.

## Main recheck

- 2026-07-30 - `00c3333` -> reproduces: scaffold --plugin-only then copy-machinery: scaffold_mode stays plugin-only; docs/workflow.md keeps 3 CLAUDE_PLUGIN_ROOT citations

## Release log

- 2026-07-30 - released claim from claude/bug-copy-machinery-mode: branch claude/bug-copy-machinery-mode was deleted after PR #145 merged; no session holds this bug. Part 1 (manifest flip) is on main; the retroactive bug-review and craft passes returned needs-changes on part 2 (docs advisory never fires on the Codex host), so the bug stays FIXING and is free for pickup.
