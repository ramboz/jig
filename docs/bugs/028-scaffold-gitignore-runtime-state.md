---
status: DONE
tier: standard
severity: medium
claimed_by: claude/bug-028-gitignore-runtime-state
regression_test: skills/scaffold-init/test_scaffold.py::Bug028RuntimeStateGitignoreTests::test_fresh_scaffold_ignores_runtime_state_paths
main_repro_checked_at: 2026-08-01
main_repro_ref: origin/main@80110ba
main_repro_result: reproduces
red_confirmed_at: 2026-08-02
green_confirmed_at: 2026-08-02
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 028: scaffold-gitignore-runtime-state

Reported as [GitHub issue 107](https://github.com/ramboz/jig/issues/107).

## Symptom

Every project jig scaffolds ends up **tracking jig's own per-checkout runtime
state** — hook telemetry (`.claude/skill-usage.jsonl`,
`.claude/context-growth-read-events.jsonl`), queues/locks
(`.claude/review-queue.json`, `.claude/scheduled_tasks.lock`), the per-user
settings overlay (`.claude/settings.local.json`), and per-checkout markers
(`.jig/spec-ref`, `.jig/decision-scratch/`, `.jig/decision-suppressions.log`).
These churn on every session and, for the per-checkout markers, collide at
merge/rebase time. Observed on jig 2.7.0; still present on 2.9.0.

## Repro

```bash
tmp=$(mktemp -d)
CLAUDE_PLUGIN_ROOT="$PWD" python3 skills/scaffold-init/scaffold.py "$tmp/demo"
grep -c '.claude/skill-usage.jsonl' "$tmp/demo/.gitignore"   # -> 0 (absent)
```

The scaffolded `.gitignore` contains only the secret-ignore block; none of the
`.claude/*` runtime-state paths nor `.jig/spec-ref` / decision-capture paths are
present, so a first `git add -A` tracks them.

## Evidence

- jig's own `.gitignore` git-ignores these paths (with comments stating the rule
  explicitly, e.g. `.jig/spec-ref`: "Per-checkout state — must NOT be tracked or
  travel across branches"). That knowledge lives only in the maintainers'
  working copy.
- The scaffolder's only `.gitignore` writer is
  `_write_gitignore_secret_block()` / `_render_gitignore_block()` in
  `skills/scaffold-init/scaffold.py` (slice 052-02, ADR-0013), whose payload is
  `_GITIGNORE_SECRET_PATTERNS` — **secret files only**. A later change folded the
  local-runtime `.jig/semantic-index-*` and `.jig/servo-hint-shown` files *into*
  the secret block (spec 080 / slice 072-02), but the `.claude/*` telemetry +
  queues + settings overlay and `.jig/spec-ref` / decision-capture paths were
  never propagated.
- No `.gitignore` template ships in the plugin tree at all — the block is fully
  code-generated, so the gap is entirely in `_GITIGNORE_SECRET_PATTERNS`'s scope.
- Downstream report ([#107](https://github.com/ramboz/jig/issues/107)): one
  project accrued 19 churn commits of pure telemetry noise, a tracked
  hook-rewritten file blocked `git merge --ff-only`, and `.jig/spec-ref` produced
  a real merge conflict between two worktrees.
- Collaborator follow-up on #107 added two more paths from the decision-capture
  feature (`.jig/decision-scratch/`, `.jig/decision-suppressions.log`) — same
  failure mode.

## Hypotheses

- [ ] H1: The scaffolder *does* ship a runtime-state `.gitignore` but writes it
  to the wrong place / under a template not copied in plugin mode. Falsify by
  grepping the plugin tree for any gitignore template and by reading the only
  gitignore writer — if the payload is secret-only, H1 is dead.
- [x] H2 (leading): The scaffolder has exactly one `.gitignore` writer whose
  payload (`_GITIGNORE_SECRET_PATTERNS`) is scoped to secret files; jig's
  runtime-state ignore list is maintained only in jig's own repo `.gitignore`
  and was never propagated into the scaffolder. Confirm by reading
  `_render_gitignore_block` / `_GITIGNORE_SECRET_PATTERNS` and by running the
  repro above (runtime paths absent from a fresh scaffold).

## Root cause

Confirmed H2. `skills/scaffold-init/scaffold.py` generates the project
`.gitignore` from a single marker-delimited block, `_render_gitignore_block()`,
whose payload `_GITIGNORE_SECRET_PATTERNS` is deliberately scoped to
secret-carrying files (ADR-0013 security floor). jig's knowledge of *which
runtime files are per-checkout local state* lives only in jig's own repo
`.gitignore` and is never emitted by the scaffolder. This is a **missing
propagation** defect — a process problem (the maintained ignore list has no
path into scaffolded projects), not a wrong value. Fixing it means giving the
scaffolder a second managed block that carries the runtime-state list, written
by the same idempotent `_upsert_marked_block` mechanic on every path that
already writes the secret block (`scaffold()`, `--plugin-only`, and
`copy_machinery`).

## Fix class

structural_fix — add the missing runtime-state managed block to the scaffolder's
`.gitignore` generator (the durable source), not a one-off patch of a single
project's `.gitignore`.

## Fix

In `skills/scaffold-init/scaffold.py`:

1. Add `_GITIGNORE_RUNTIME_BEGIN` / `_GITIGNORE_RUNTIME_END` markers,
   `_GITIGNORE_RUNTIME_PATTERNS` (the `.claude/*` runtime paths + `.jig/spec-ref`
   + `.jig/decision-scratch/` + `.jig/decision-suppressions.log`; **not** the
   semantic-index / servo-hint files, which already ride in the secret block —
   avoid duplication), and `_render_gitignore_runtime_block()`.
   **Deliberately excluded:** the review-queue.json runtime file, even though it
   is in jig's own `.gitignore`. It is a removed feature (spec 039); jig keeps
   the self-ignore only defensively, and a guard test
   (`test_review_queue_cleanup`) forbids live-code references to that path
   literal. Scaffolded projects have no review-queue writer, so propagating it
   would be dead noise — do not blind-copy jig's self-ignore list.
2. Replace `_write_gitignore_secret_block` with
   `_write_gitignore_managed_blocks`, which upserts **both** blocks in a single
   read + atomic write, and update the three call sites (`scaffold()` main path,
   `--plugin-only`, `copy_machinery`) plus the one unit-test reference.
3. Include a one-line `git rm --cached` hint in the rendered runtime block so the
   migration wrinkle (a `.gitignore` entry is a no-op on an already-tracked file)
   is documented in the most-discoverable place, reaching both new and
   `copy-machinery`-migrated projects.

## Already tried

- Initial implementation was done in the shared primary worktree, where a
  concurrent session's `git stash` discarded the uncommitted work; re-done in an
  isolated worktree off `origin/main` to avoid the contended tree (learning
  recorded).
- First REVIEWED green check failed (`tdd.py exit 1`) — the full suite caught
  `test_review_queue_cleanup::test_no_live_runtime_references_to_review_queue`:
  the initial runtime list blind-copied `.claude/review-queue.json` from jig's
  own `.gitignore`, but that path is a removed feature guarded against live-code
  references. Fixed by excluding it (see Fix) and referring to it only by bare
  filename in comments/tests. This is why witnessing the fix against the FULL
  suite — not just the targeted class — mattered.

## Regression test

`skills/scaffold-init/test_scaffold.py::Bug028RuntimeStateGitignoreTests` — a
fresh scaffold's `.gitignore` must contain the runtime-state block markers and
every runtime path, in `--plugin-only` mode too, idempotent across re-runs, and
without duplicating the semantic-index/servo-hint entries that already live in
the secret block. Fails on trunk (paths absent); passes with the fix.

## Proof

- **Red** (fix stashed, tests present): the FIXING gate ran the full suite via
  `.jig/test-command` and witnessed red; `red_confirmed_at` stamped.
- **Green** (fix applied): full suite green (`Ran 3893 tests … pyright: clean`)
  after excluding the review-queue path; REVIEWED gate re-confirms and stamps
  `green_confirmed_at`.
- Reviews: `bug-review` pass + `craft` pass (see `docs/bugs/reviews/`),
  re-confirmed after the review-queue exclusion.
- Reconciliation: rebuilt committed host packages via
  `scripts/build_host_packages.py` (`--check` in sync); corrected renamed-function
  references in live prose (`adr-0041` 105/257, `docs/specs/README.md:230`) per
  ADR-0010, leaving closed spec/review records historical.

## Learning

See `docs/memory/learnings.md` — "Bug 028: a list the source repo maintains for
itself won't reach generated projects unless the generator emits it" (plus the
don't-blind-copy corollary — the review-queue path had to be filtered out — and
the shared-primary-worktree concurrency gotcha).

## Main recheck

- 2026-08-01 - `origin/main@80110ba` -> reproduces: CLAUDE_PLUGIN_ROOT=$PWD python3 skills/scaffold-init/scaffold.py <tmp>/demo; grep -c '.claude/skill-usage.jsonl' <tmp>/demo/.gitignore -> 0 (review-queue.json, .jig/spec-ref, .jig/decision-scratch/ also absent); secret block present.
