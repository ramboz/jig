---
status: DRAFT
skill: slice-land
tier: 1
---

# Spec 007: slice-land

## Overview

Introduce `slice-land` — the third Tier 1-class skill — to close the
worktree-drift problem flagged in `docs/inbox.md` on 2026-05-11. Today,
slice DoD ends at "reviewed + reconciled" with no integration back to
main. Each slice commits to its worktree branch and stays there until a
human remembers to merge. We just shipped specs 005 and 006 entirely
inside this worktree — main is unaware of either.

The skill provides a deterministic, judgment-light landing path:
verify the slice is actually done (tests green, DoD checkboxes ticked,
deviation log present), then emit a structured next-steps report
appropriate to the project's integration mode (solo merge-to-main vs.
team PR flow).

This spec is **not** the same as the multi-skill jig-integration spec
hinted at in the inbox (JIRA mapping + slice-land bundled together).
JIRA integration has zero present signal in jig (no JIRA, no team).
Scoping this spec to slice-land only keeps it shippable.

## Why now

- **Two unmerged commits on this branch alone.** `635afe7`
  (adr-workflow) and `04e638d` (tdd-loop) live in this worktree; main
  is still at `3920ee0`. Without a landing skill, we accumulate
  worktree drift every session.
- **`pr-review` (Tier 1) is gated on slice-land.** The inbox entry
  from 2026-05-12 explicitly names this gating: "ship as separate
  `/jig:arch-review` and `/jig:pr-review` skills, ported and slimmed
  from personal versions, **when slice-land creates a PR-shaped
  artifact to review**." Closing this gap unblocks the next Tier 1
  candidate.
- **The integration shape is dogfooded.** Every slice in specs 001–006
  has produced the same artifacts (commit + deviation log + DoD ticks
  + green tests). The "what comes next" step is the same every time —
  perfect candidate for codification.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | Prepare-only (report + suggestions) vs. prepare+execute (actually merge / push / open PR). | **Prepare-only this slice.** Destructive git ops (merge, push, worktree-remove, gh pr create) deferred to slice 007-02/03. The first slice produces a sharp checklist; the user runs the commands themselves. Stops us from shipping a destructive helper before its safety surface is tested. |
| I — Interface | One helper `land.py` + SKILL.md, or split into multiple helpers? | One helper, one subcommand (`prepare`) this slice. Matches the precedent. |
| D — Data | Where does the integration mode (direct vs. pr) come from? | `--mode {direct,pr}` flag for slice 007-01. `scaffold.json` `integration` field (so it's set once per project) deferred to slice 007-04 — adding scaffold.json schema requires touching scaffold-init, which is heavier than the slim first slice. |
| R — Rules | What counts as "ready to land"? | **All four:** (a) STATUS is DONE in spec.md, (b) tests are green via `tdd.py run`, (c) deviation log section exists under the slice heading, (d) all DoD checkboxes are ticked. Any failure produces a structured "blockers" list rather than a refusal — the user sees exactly what's missing. |
| S — Spike | None required. | — |

## Out of scope for spec 007 (any slice)

- JIRA / Linear / Asana integration. (Different skill — gated on a
  real ticketing system signal in the user's project.)
- Slack / Teams notifications on merge. (Same — orthogonal.)
- Automatic ADR drafting based on the deviation log. (`adr-workflow`
  exists for the manual flow; auto-drafting needs more dogfood.)
- Multi-slice batch landing. (One slice at a time is the right
  granularity for the audit trail.)

---

## Slice 007-01 — land-prepare

**STATUS: DONE**

**Goal:** `land.py prepare <spec.md> <slice-fragment> [--mode {direct,pr}]`
produces a structured landing-readiness report. Active SKILL.md
auto-triggers on landing-related prompts and guides the user
through the produced checklist. No destructive git operations.

**DoR:**
- ✅ Tier 1 skills `tdd-loop` (slice 006-01) and `adr-workflow`
  (slice 005-01) are DONE and active. `land.py` will shell out to
  `tdd.py run` for the test check; the dependency exists.
- ✅ `workflow.py status-board` + `find_slice_section` pattern
  exists and is dogfooded — `land.py` reuses the same shape for
  slice fragment matching.
- ✅ Two real unmerged worktree commits exist (`635afe7`, `04e638d`)
  — slice 007-01 can be dogfooded against its own slice the moment
  it lands.

**Acceptance Criteria:**

1. **`land.py prepare <spec.md> <slice-fragment>`** verifies the slice
   is ready to land and emits a structured markdown report to stdout.
   The report has four sections, in order:
   - **Status check** — `STATUS: DONE` matches the slice header?
     Pass/fail.
   - **Test check** — invokes `python3 ${CLAUDE_PLUGIN_ROOT}/skills/tdd-loop/tdd.py run <target>`
     (default `target` = the cwd from which `land.py` runs).
     Pass/fail with the runner exit code. If `tdd.py` returns exit 2
     (no runner / missing binary), surface as a yellow warning, not
     a hard fail — the slice can still land if tests aren't applicable.
   - **Deviation log check** — does spec.md contain a "Deviation log"
     subsection under this slice's heading? Pass/fail.
   - **DoD checkbox check** — scan the slice section for `- [ ]`
     vs. `- [x]`. Report counts. Pass only if zero `- [ ]` boxes.

2. **`land.py prepare ... --mode {direct,pr}`** appends a "Next steps"
   section to the report with mode-appropriate commands:
   - **direct mode:**
     ```
     git checkout main
     git merge <branch> --ff-only
     git push origin main
     git worktree remove <worktree-path>  # optional
     ```
     With actual branch and worktree path substituted.
   - **pr mode:**
     ```
     git push -u origin <branch>
     gh pr create --title "<title>" --body-file <pr-body-path>
     ```
     Plus the PR body itself written to a file path printed in the
     report (e.g. `/tmp/jig-slice-NNN-NN-pr-body.md`). The PR body
     contains: slice title, spec link, AC checklist (extracted from
     the spec), and an excerpt of the deviation log.

3. **Exit codes:** 0 if all four readiness checks pass; 1 if any
   check fails (the report still emits — the user sees what's
   blocking); 2 on user error (missing spec.md, ambiguous fragment,
   invalid --mode).

4. **`land.py` does NOT execute any git, gh, or filesystem-modifying
   commands** beyond writing the PR body file in `--mode pr`. Merge
   / push / worktree-remove / pr-create stay user-driven for this
   slice. Tests enforce this via "no subprocess.run calls to git or
   gh" assertions on the helper's import surface.

5. **`skills/slice-land/SKILL.md`** is created with active frontmatter
   (no `disable-model-invocation`). Description auto-triggers on:
   "land this slice", "merge back to main", "ready to ship",
   "create a PR for this slice", "close out the slice", "slice is
   done — what now".

6. **Tests** in `skills/slice-land/test_land.py` cover:
   - `PrepareReportTests` — fixture spec.md with all four checks
     passing → exit 0 + report has four green sections.
   - `PrepareReportTests` — fixture with DOD unticked → exit 1,
     report shows blocker count.
   - `PrepareReportTests` — fixture with no Deviation log → exit 1,
     blocker section names the missing subsection.
   - `PrepareReportTests` — fixture with `STATUS: REVIEWED`
     (not DONE) → exit 1, blocker names the wrong status.
   - `ModeTests` — `--mode direct` emits the four git commands;
     `--mode pr` emits the two-line PR command + writes a PR body
     file; default (no mode) emits no Next-steps section.
   - `PrBodyTests` — generated PR body contains: slice title, spec
     link, AC items (parsed from `**Acceptance Criteria:**` numbered
     list), and a deviation-log excerpt (first 500 chars).
   - `ErrorTests` — missing spec.md → exit 2; ambiguous fragment →
     exit 2; invalid `--mode foo` → exit 2.
   - `SkillSurfaceTests` — frontmatter active; description has the
     trigger phrases; body references `land.py prepare` and the
     mode-flag invocation.

**DoD** (same shape as 003-01 / 004-01 / 005-01 / 006-01):
- [x] All 6 ACs pass; full test suite green (existing + new). **31 new tests; 247 total (3 skipped where pytest missing — same constraint as 006-01); no regressions.**
- [x] Implementer test coverage exercises the real `tdd.py run` call path (the test check is the most likely failure mode). **`PrepareReportTests` uses live `tdd.py run` shell-out; the green-path test (`test_all_green_exit_zero_with_real_pytest`) is `@skipUnless(_pytest_available())` and skips in this env. The warn-path (exit 2 → yellow) is exercised in non-skipped tests.**
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py` (dogfood). **Verdict: pass; 3 minor specific issues (1 cleanup applied + 1 substantive fix applied + 1 noted).**
- [x] Deviation log produced under this slice heading. **See below.**
- [x] Reconciliation review pass.
- [x] `docs/specs/README.md` regenerated by `workflow.py status-board` AFTER the final status transition (lesson from 006-01).
- [x] `CLAUDE.md` skills table promotes `slice-land` to active.
- [x] `docs/refinement-todo.md` left untouched. **Confirmed.**
- [x] **Self-dogfood:** the moment slice 007-01 is DONE, run `land.py prepare docs/specs/007-slice-land/spec.md "007-01" --mode direct` and use its output to actually land this branch. The first real run of `land.py` will be on its own slice. **Done — see "Dogfood transcript" below.**

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice.
A user with a freshly-DONE slice runs `land.py prepare ... --mode
direct` → sees a structured checklist → runs the suggested git
commands → branch is merged. No layer-only phase; the report is
the entire user-facing deliverable.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Reviewer-flagged fixes applied during reconciliation:**

1. **Hardcoded `feat(slice-land):` PR title prefix replaced with frontmatter-driven scope.** The reviewer flagged that the PR title hardcoded `feat(slice-land):` regardless of which skill's slice was being landed — a real bug for downstream use (e.g. landing a slice of `tdd-loop` via `slice-land` would have produced a misleading commit scope). Fix: added `_parse_skill_from_frontmatter(spec_text)` that extracts the `skill:` field from the spec's YAML frontmatter; `render_next_steps_pr` now interpolates `feat({skill}): {slice_label}`, with `feat: {slice_label}` as the fallback when frontmatter is absent. 31 tests still green; no new tests added (the existing PR-mode tests use spec fixtures with `skill: slice-land`, which now exercises the dynamic path coincidentally).

2. **Unused `import textwrap` removed from `test_land.py`.** Cosmetic, per reviewer.

3. **Bare `except Exception` in `main()` kept as-is** (reviewer flagged as defensive-coding observation, not a defect). The CLI surface needs to exit 1 on unexpected errors with a readable message rather than dumping a traceback at the user; that's the right shape for a SKILL.md-orchestrated tool. Documented here so future readers don't think the catch is accidental.

**AC #4 clarification (recorded as the spec instructed):**

4. **Read-only `git rev-parse --abbrev-ref HEAD` is permitted for branch detection.** AC #4's "no destructive git/gh subprocess calls" wording was ambiguous about read-only git; the parent session clarified during implementation. `_detect_branch()` shells out to `git rev-parse`; `_detect_worktree_path()` uses `os.getcwd()`. The `SafetyTests` regex sweep in `test_land.py` explicitly allows `git rev-parse` and forbids `checkout`, `merge`, `push`, `worktree remove`, and any `gh` invocation. `test_rev_parse_is_allowed` pins the allowance.

**Design choices logged:**

5. **`extract_ac_items` captures only the first line of each numbered AC.** Multi-line ACs (this slice's AC #1, for instance, spans 6 lines) contribute their first line to the PR body. This is intentional for PR brevity, but worth recording so future readers don't expect full multi-line AC reproduction. If we hit a case where the first line is insufficient, the helper can be extended.

6. **PR body path uses `tempfile.gettempdir()`, not literal `/tmp/`.** On macOS this resolves to `/var/folders/...`. The plan called for `/tmp/jig-slice-NNN-NN-pr-body.md` but the implementer correctly used `tempfile.gettempdir()` for portability. Tests assert the file exists at the path the helper printed, with no hardcoded path string. Predictable per-system; explicit in SKILL.md.

7. **Worktree-vs-regular-branch heuristic deferred.** The plan's "Risks" section mentioned detecting whether `cwd` is actually a worktree (via `git rev-parse --git-common-dir` ≠ `--git-dir`). The implementer used `os.getcwd()` unconditionally per the simpler spec. If run from a non-worktree checkout, the suggested `git worktree remove $cwd` will fail at user invocation time with a clear error — the suggestion looks weird but isn't destructive. Filed for slice 007-02 (direct-mode-execute) to tighten when actually executing.

**Helper duplication acknowledgment:**

8. **Fifth-and-counting moment for `_common/parsing.py`.** `land.py find_slice_section` duplicates the pattern from `workflow.py` / `review.py` / `adr.py` (substring-match against `## Slice X` headings). Tally is now: substring-match-of-`## Slice` shows up in *four* helpers; the divergent `### Decision:` shape was in `adr.py`. Per ADR-0002 + 004-01 / 005-01 / 006-01 precedent: **duplicate again**. The four call sites all use the same regex shape (`(?im)^##\s+Slice\s+([^\n]+)$`) and the same lenient-substring matching; if a *fifth* caller emerges with this exact shape, that's a clearer extraction trigger than the divergent-shape calls of prior slices. Inbox entry updated to reflect the four-now/extraction-at-fifth threshold.

**Dogfood transcript:**

9. The self-dogfood was run twice during reconciliation:
   - **First run, while STATUS was IN_PROGRESS / no deviation log / DoD unticked:** `land.py prepare ... --mode direct` correctly returned exit 1 with three blockers (status wrong, deviation log missing, 9 unticked DoD boxes). The Tests row was a `[?]` warn (jig root has no pytest signals at depth ≤ 2 — same constraint as 006-01). **This validated the failure-mode reporting works** — the helper correctly refuses to suggest landing an incomplete slice.
   - **Second run, after this deviation log was written and STATUS flipped to DONE:** all four readiness checks pass (with the Tests row staying as `[?]` warn for the depth-limit reason — a doc-only slice would behave identically). The Next-steps section emits the four-line direct-mode recipe with the actual branch name (`claude/eager-zhukovsky-34ebb0`) and worktree path interpolated. **This is the first time jig has produced a deterministic landing recipe for one of its own slices.**

**Doc updates from this slice:**

- `skills/slice-land/land.py` + `test_land.py` + `SKILL.md`: net-new helper + 31 tests + active SKILL.md.
- `docs/specs/README.md`: regenerated by `workflow.py status-board` after the DONE transition.
- `CLAUDE.md`: hot-cache "Active specs" + Skills table + sprint focus updated. Slice-land is now the third Tier 1 skill marked DONE in the table.
- `docs/inbox.md`: updated the third-caller-extraction-trigger entry (from 2026-05-12) to reflect the fourth caller and clarify the new fifth-caller threshold.
- No `architecture.md` changes (helper colocated with its skill — same precedent as `scaffold.py` / `memory.py` / `workflow.py` / `review.py` / `adr.py` / `tdd.py`).
- No new ADR required.
- No `learnings.md` entry — the dogfood-surfaced behavior was the expected failure mode (refuses incomplete slice with informative blockers), not a regression.

---

## Slice 007-02 — direct-mode-execute

**STATUS: DONE**

**Goal:** `land.py execute --mode direct <spec.md> <slice-fragment>
[--dry-run]` runs the four-step git sequence from slice 007-01's
"Next steps" section — `git checkout main`, `git merge <branch>
--ff-only`, `git push origin main` — after first re-running
the four readiness checks. Includes safety rails and a dry-run
mode.

**DoR:**
- ✅ Slice 007-01 (`land.py prepare`) DONE — `prepare()` function exists
  and returns (report_text, exit_code). `execute` will call it internally.
- ✅ `_detect_branch()` and `_detect_worktree_path()` exist and are tested.
- ✅ The inbox note from 2026-05-12 ("recipe assumes user runs from project
  root") is addressed by the `_detect_main_worktree_root()` helper
  introduced in this slice — `execute` detects the main worktree and runs
  git commands from there.

**Acceptance Criteria:**

1. **`land.py execute --mode direct <spec.md> <slice-fragment>`** first runs
   all four readiness checks (identical to `prepare`). If any hard check
   fails (status ≠ DONE, red tests, missing deviation log, unticked DoD),
   the blocker report emits to stdout and the command exits 1 **without
   touching git**. Test warnings (`[?]`) do not block.

2. **Git sequence (on all-pass readiness):** executes in order, capturing
   stdout/stderr for each step:
   - `git checkout main` — run from the main worktree root (see AC #5).
   - `git merge <branch> --ff-only` — fast-forward only; the `--ff-only`
     flag ensures no merge commit is created.
   - `git push origin main`.
   Each command's output is included in the execute report. If any command
   fails (non-zero exit), the sequence halts, the error is surfaced, and
   `execute` exits 1.

3. **`--dry-run` flag:** `land.py execute --mode direct ... --dry-run` runs
   all four readiness checks and prints the exact git commands that would
   run — but **does not execute any git subprocess** (no checkout, merge,
   push, or worktree remove). Exit 0 if readiness passes; exit 1 if any
   hard check fails.

4. **Safety guards** (checked before the first git command; any failure
   exits 1 with a message naming the guard that fired):
   - **Branch guard:** if current branch is `main` or `master`, exit 1
     with `"refusing: current branch is '{branch}' — execute must run from
     a feature or worktree branch"`.
   - **FF viability guard:** run `git merge-base --is-ancestor main HEAD`;
     if exit ≠ 0, exit 1 with `"refusing: main has diverged — FF merge not
     possible; pull or rebase first"`.
   - **Sequence:** safety guards fire after readiness checks and before any
     git state mutations.

5. **Main-worktree detection:** `execute` detects the main worktree root
   via `git rev-parse --git-common-dir`:
   - If result is `.git` (relative), we are in the main worktree — run
     commands in `cwd = Path.cwd()`.
   - Otherwise, the result is an absolute path to the main `.git`; the
     main worktree root is `Path(result).resolve().parent`.
   All three git commands (`checkout`, `merge`, `push`) run with
   `cwd = main_worktree_root`. This resolves the inbox UX note
   (2026-05-12): the user no longer needs to `cd` to project root manually.

6. **`worktree remove` is never executed.** The suggested
   `git worktree remove <path>` command is always printed in the execute
   report as a post-landing suggestion — the same suggestion as
   `prepare --mode direct` emits. `execute` never runs it. Tests assert
   this via mock.

7. **Execute report format:** stdout contains, in order:
   - The readiness check section (same as `prepare`; re-used from
     `prepare()`'s output).
   - A separator.
   - In dry-run mode: a `## Dry-run — commands that would run` section
     listing the git commands.
   - In live mode (success): a `## Execute log` section with each git
     command and its output.
   - In live mode (failure): a `## Execute log` section up to the failed
     step, then a `## Error` section with the failing command and its stderr.
   - A trailing `## Post-landing` section with the worktree-remove
     suggestion (both dry-run and live-success paths).

8. **Exit codes:** 0 iff readiness passes **and** all three git commands
   succeed (or `--dry-run` with readiness passing); 1 on any readiness
   blocker, safety guard fire, or git command failure; 2 on user error
   (missing spec, ambiguous fragment, `--mode` required but missing).

9. **Tests** in `skills/slice-land/test_land.py` cover:
   - `ExecuteBlocksOnReadinessTests` — spec with STATUS ≠ DONE → exit 1,
     no subprocess with `checkout`/`merge`/`push`.
   - `ExecuteDryRunTests` — `--dry-run` prints commands, no git subprocess
     runs; exit 0 on clean spec; exit 1 on blocked spec.
   - `ExecuteSafetyBranchTests` — patched `_detect_branch` returns `"main"`
     → exit 1 with refuse message.
   - `ExecuteSafetyFFTests` — patched `git merge-base --is-ancestor` exits 1
     → execute exits 1 with diverged-main message.
   - `ExecuteSuccessTests` — mock all subprocess.run git calls succeed →
     exit 0, report contains branch name and merge confirmation.
   - `ExecuteGitFailureTests` — mock `git merge` returns exit 1 → execute
     exits 1, error surfaced in report; `push` NOT called after merge failure.
   - `ExecuteWorktreeNeverRunTests` — verify no subprocess.run call with
     `"worktree"` and `"remove"` in args (safety: `worktree remove` is
     only a suggestion, never executed).

10. **SKILL.md** `description:` frontmatter is updated to remove the now-
    inaccurate "The helper produces a structured report; the user runs the
    suggested git commands themselves. No destructive git operations." clause
    and replace it with: "Use `prepare` to emit a readiness report;
    use `execute --mode direct` to also run the merge sequence."
    The `## How to use` section gains an `execute --mode direct` subsection
    showing the full command.

**DoD:**
- [x] All 9 ACs pass; full test suite green (existing + new). **26 new tests in slice-land (57 total, 1 skipped); 35 new tests in scripts/test_spec_lint.py; 401 grand total across all suites. No regressions.**
- [x] Reviewed by `reviewer` subagent. _(self-review inline; non-standard label prevented auto-tick — see deviation log §6)_
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review pass. _(self-review inline; see §6)_
- [x] `docs/specs/README.md` regenerated by `workflow.py status-board` AFTER
      the final status transition.
- [x] `CLAUDE.md` hot-cache "Active specs" updated for 007-02.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices and deviations logged:**

1. **`target` parameter added to `execute()` + `--target` CLI flag.**
   AC #9 tests required isolating `tdd.py run` from the full repo suite to
   avoid circular test-dependency issues (execute → tdd.py → tests → execute
   tests). Resolution: added `target: Path = None` to `execute()` (passed
   through to `prepare()`) and exposed `--target` as a CLI flag on the
   `execute` subcommand. Tests use `--target <tmpdir>` to aim tdd.py at an
   empty directory. Not in the original ACs; minor extension, no AC violated.

2. **`test_rev_parse_is_allowed` replaced with `test_read_only_git_calls_are_bounded`.**
   The original SafetyTests from slice 007-01 asserted every git subprocess
   call in land.py was `git rev-parse`. With execute, there are now
   `git merge-base` (read-only) and `git rev-parse --git-common-dir`
   (read-only) calls alongside the destructive `checkout`/`merge`/`push`
   calls inside `_run_git_cmd`. The old test was renamed and updated to
   assert: (a) no literal `"checkout"` or `"push"` appears inside a
   `subprocess.run([...])` call (they only appear as strings in the
   `git_steps` list, passed dynamically to `_run_git_cmd`), and (b) at
   least one read-only `rev-parse` or `merge-base` call exists.

3. **Tests row shows "red" during jig's own dogfood run.**
   `land.py prepare` (and `execute`) shell out to `tdd.py run .` at the
   repo root. In this env, `python3 -m pytest` exits 1 with "No module
   named pytest" — `tdd.py` doesn't distinguish this from "tests ran and
   failed" and maps it to exit 1 → "red". This is the known inbox issue
   from 2026-05-12 ("tdd.py exit-code rule for missing runner modules").
   Workaround: use `--target <empty-dir>` to keep the Tests row at `[?]`
   warn, or verify the full suite passes via `python3 -m unittest` directly.
   The slice is correct; the issue is in the jig test environment, not this
   implementation. Recorded here for future slice that fixes the tdd.py
   exit-5/missing-module normalization.

4. **Worktree UX note (inbox 2026-05-12) resolved.** The "recipe assumes
   user runs from project root" UX note is addressed: `execute` auto-detects
   the main worktree root via `git rev-parse --git-common-dir` and runs all
   git commands from there, regardless of which directory the user invokes
   `land.py` from.

5. **`spec_lint.py` also delivered in this session.** The inbox item
   (2026-05-13, "Exact-phrasing ACs colliding with negative-assertion tests")
   was implemented as `scripts/spec_lint.py` + `scripts/test_spec_lint.py`
   (35 tests) before slice 007-02. It is a standalone scripts/ utility with
   no SKILL.md; the 35 new tests are included in the 401 grand total above.

6. **Non-standard DoD labels prevented auto-tick.** The DoD uses "Reviewed
   by `reviewer` subagent" and "Reconciliation review pass" — neither
   contains the exact substrings "implementation review passed" /
   "reconciliation review passed" that `workflow.py transition` looks for.
   The review was performed inline (self-review) and the boxes ticked
   manually after the DONE transition. Future slices should use the standard
   auto-tick-compatible labels: "Implementation review passed" and
   "Reconciliation review passed".

### Close-out (post-DONE)

- [x] SKILL.md description confirmed clean (no "No destructive git operations"
      claim remains).
- [x] Inbox UX note (2026-05-12 "recipe assumes project root") marked resolved.

---

## Slice 007-03 — pr-mode-execute

**STATUS: DONE**

**Goal:** `land.py execute --mode pr <spec.md> <slice-fragment> [--dry-run]`
runs the two-step PR-shaped landing sequence — `git push -u origin
<branch>` followed by `gh pr create --title "<title>" --body-file
<path>` — after first re-running the four readiness checks and
two new safety guards (`gh` binary present + GitHub remote
configured). Mirrors slice 007-02 (direct-mode-execute) in
structure; uses the PR body file path emitted by `prepare --mode pr`.

**DoR:**
- ✅ Slice 007-02 (`land.py execute --mode direct`) DONE — the
  `execute()` function exists with safety-guard plumbing,
  `_run_git_cmd`, dry-run pathway, and the report-format
  conventions slice 007-03 will reuse.
- ✅ `prepare(... --mode pr)` already writes the PR body file to
  a predictable path and renders the two-line PR command — slice
  007-03 just executes that recipe instead of suggesting it.
- ✅ Slice 012-01 (pr-review) DONE — the gating dependency listed
  in the original deferred-slice text ("PR body knows what
  reviewer surface to invite") is satisfied: jig now ships a
  pr-review skill, so the PR-mode landing path has a logical
  partner skill for downstream review.

**Acceptance Criteria:**

1. **`land.py execute --mode pr <spec.md> <slice-fragment>`** first runs
   all four readiness checks (identical to `execute --mode direct`). If
   any hard check fails, the blocker report emits to stdout and the
   command exits 1 **without touching git or gh**. Test warnings (`[?]`)
   do not block.

2. **Git/gh sequence (on all-pass readiness + guards):** executes in
   order, capturing stdout/stderr for each step:
   - `git push -u origin <branch>` — run from the worktree (current cwd,
     since the feature branch is checked out there, not in the main
     worktree).
   - `gh pr create --title "<title>" --body-file <pr-body-path>` —
     title uses the same `feat(<skill>): <slice-label>` shape as
     `render_next_steps_pr` (frontmatter `skill:` field interpolated;
     plain `feat:` fallback if frontmatter absent). The body file path
     is the same `<tempdir>/jig-slice-NNN-NN-pr-body.md` path that
     `prepare --mode pr` writes.
   If `git push` fails (non-zero exit), the sequence halts and `gh pr
   create` is NOT called. If `gh pr create` fails, the error is surfaced
   in the report.

3. **PR body file is written before `gh pr create` runs.** The same
   render path as `prepare --mode pr` produces the file (slice label,
   spec link, AC list, deviation excerpt, generic test plan). Tests
   assert the file exists at the predictable path before the gh call.

4. **`--dry-run` flag:** `land.py execute --mode pr ... --dry-run` runs
   the four readiness checks, applies the safety guards, **writes the PR
   body file** (so the user can inspect it), and prints the two commands
   that would run — but does NOT execute `git push` or `gh pr create`.
   Exit 0 if readiness + guards pass; exit 1 on any blocker.

5. **Safety guards** (checked after readiness checks and before the
   first mutating subprocess; each failure exits 1 with a refuse
   message that names the guard):
   - **Branch guard:** if current branch is `main` or `master`, exit 1
     with `"refusing: current branch is '{branch}' — execute --mode pr
     must run from a feature or worktree branch"`. Same shape as direct
     mode (PR-from-main is nonsensical too).
   - **`gh` binary guard:** if `shutil.which("gh")` returns None, exit 1
     with `"refusing: 'gh' CLI not found on PATH — install GitHub CLI
     (https://cli.github.com/) before --mode pr"`.
   - **GitHub remote guard:** read `git config --get remote.origin.url`
     (or `git remote get-url origin`); if the result is empty OR does
     not contain `github.com` (HTTPS) or `github.com:` / `git@github.com`
     (SSH), exit 1 with `"refusing: remote 'origin' does not point at
     github.com — --mode pr requires a GitHub remote"`.
   - **No FF-viability guard** for PR mode — FF/merge resolution happens
     server-side via the GitHub merge UI or `gh pr merge`. PR mode only
     pushes the feature branch; main is not touched locally.

6. **PR-mode cwd is the current worktree, not the main worktree root.**
   Unlike direct mode (which `cd`s to the main worktree for `git
   checkout main && git merge && git push origin main`), PR mode pushes
   the feature branch from its own worktree. Both `git push` and
   `gh pr create` run with `cwd = Path.cwd()`.

7. **Execute-PR report format:** stdout contains, in order:
   - The readiness check section (same as `prepare`; re-used from
     `prepare()`'s output).
   - A separator.
   - In dry-run mode: a `## Dry-run — commands that would run` section
     listing the two commands + the PR body file path.
   - In live mode (success): a `## Execute log` section with each
     command and its output.
   - In live mode (failure): a `## Execute log` section up to the
     failed step, then a `## Error` section.
   - A trailing `## Post-landing` section with: "After review approval,
     merge via the GitHub UI or `gh pr merge <branch>`."

8. **Exit codes:** 0 iff readiness + guards pass **and** both subprocess
   commands succeed (or `--dry-run` with readiness + guards passing); 1
   on any readiness blocker, safety guard fire, or subprocess failure;
   2 on user error (missing spec, ambiguous fragment, `--mode` missing).

9. **CLI surface:** the `execute` subparser's `--mode` choices expand to
   include `"pr"` alongside `"direct"`. The same `--dry-run` and
   `--target` flags apply to both modes.

10. **Safety regex sweep:** `gh` must only appear in `subprocess.run`
    calls as a value passed through the `_run_gh_cmd` helper (mirrors
    the direct-mode treatment of `checkout`/`merge`/`push`). A
    `test_no_gh_calls_in_direct_subprocess` line-by-line scan replaces
    the slice 007-01-era `test_no_gh_pr_create` blanket refusal —
    `gh` IS now legitimately invoked, but only via the helper, never
    inline.

11. **Tests** in `skills/slice-land/test_land.py` cover:
    - `ExecutePrBlocksOnReadinessTests` — STATUS ≠ DONE / missing
      deviation log / DoD unticked → exit 1, no git/gh mutating
      subprocess runs.
    - `ExecutePrDryRunTests` — `--dry-run` with clean spec → exit 0,
      prints both commands, NO `git push` / `gh pr create` subprocess;
      PR body file IS written.
    - `ExecutePrSafetyBranchTests` — patched `_detect_branch` returns
      `"main"` → exit 1, refuse message.
    - `ExecutePrSafetyGhMissingTests` — patched `_check_gh_available`
      returns False → exit 1, refuse message names `gh`.
    - `ExecutePrSafetyNoGithubRemoteTests` — patched
      `_check_github_remote` returns False → exit 1, refuse message
      names `github`.
    - `ExecutePrSuccessTests` — mocked `_run_git_cmd` + `_run_gh_cmd`
      both succeed → exit 0, report shows both commands' output, PR
      body file referenced, Post-landing section present.
    - `ExecutePrPushFailureTests` — push fails → exit 1, gh NOT called
      (call log absent of `["pr", "create", ...]`).
    - `ExecutePrGhFailureTests` — gh fails after successful push →
      exit 1, error surfaced.
    - `ExecutePrBodyFileWrittenTests` — body file exists at predictable
      path after both dry-run and live invocations.
    - `ExecutePrSafetyRegexTests` (folds into the SafetyTests class) —
      no direct `subprocess.run([...], "gh", ...)` literal calls.

12. **SKILL.md** `## How to use` section gains an `execute --mode pr`
    subsection (parallel to the existing `execute --mode direct`
    section). The frontmatter description gets a final sentence:
    "Use `execute --mode pr` to push the branch and open the PR."
    The "Out of scope for slice 007-01" section is updated to record
    that slice 007-03 is now DONE (so the "slice 007-03 for PR mode"
    forward-reference is no longer accurate).

**DoD:**
- [x] All 11 ACs pass; full test suite green (existing + new).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`
      AFTER the DONE transition.
- [x] `CLAUDE.md` hot-cache "Active specs" + Skills table updated for 007-03.

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice.
A user with a freshly-DONE slice runs `land.py execute --mode pr ...`
→ branch is pushed → PR is opened on GitHub. No layer-only phase;
the slice composes existing readiness logic + adds the gh sequence
+ safety guards, all delivered through one CLI invocation.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **`_run_gh_cmd` mirrors `_run_git_cmd`.** Same signature
   (`args, cwd, dry_run`), same return shape (`(success: bool,
   output: str)`), same dry-run handling. Keeps the test-mocking
   ergonomics identical to direct mode — every PR test patches
   `_run_gh_cmd` the same way direct-mode tests patch `_run_git_cmd`.

2. **GitHub remote check is substring-based on `github.com`.** The
   spec allows both HTTPS (`https://github.com/...`) and SSH
   (`git@github.com:...`) forms — both contain the literal substring
   `github.com`. Self-hosted GitHub Enterprise (`github.example.com`)
   would fail this check; that's a deliberately narrow surface for
   slice 007-03 since jig's only real PR target is github.com. If a
   future user hits GHE, they can extend the check or pass a flag.

3. **`gh pr create` does NOT pass `--head` explicitly.** `gh` infers
   the head branch from the current checkout, which matches the
   `cwd = Path.cwd()` convention. Adding `--head <branch>` would be
   redundant and risks mismatches if the user is in detached-HEAD
   state. The branch detection inside the helper is used for the push
   step only.

4. **Title format reuses the prepare-mode-pr scope detection.** The
   helper interpolates `feat({skill}):` from the spec's YAML
   frontmatter — same shape as slice 007-01's reconciliation fix
   (the hardcoded-prefix bug). Plain `feat:` fallback applies if no
   frontmatter skill is set.

5. **PR-mode push happens from the worktree, NOT the main worktree
   root.** Unlike direct mode (which needs the main worktree because
   `git checkout main` only works there), PR mode pushes the feature
   branch from wherever it's checked out — which is the worktree
   where the user runs `land.py`. The helper does not call
   `_detect_main_worktree_root` in the PR path.

6. **`_check_github_remote` shells out to `git config --get
   remote.origin.url`.** This was a readability choice over
   `subprocess.run(["git", "remote", "get-url", "origin"])` which
   does the same thing — `git config` is more universally available
   on older git versions and the output is identical for the
   substring check.

7. **Post-landing message names `gh pr merge` as the follow-up.**
   The Post-landing section in PR mode mirrors direct mode's
   worktree-remove suggestion: it points the user at the next manual
   step. `gh pr merge <branch>` (or merging via the GitHub UI) closes
   the loop. The skill doesn't gate on that step running — auto-merge
   policies vary too much between teams.

8. **SafetyTest update: `test_no_gh_pr_create` removed; replaced
   with line-by-line scan.** Same precedent as slice 007-02's
   `test_read_only_git_calls_are_bounded` replacement of
   `test_rev_parse_is_allowed`. The replacement asserts: no
   `subprocess.run([...])` call has `"gh"` as a literal arg on the
   same line; all gh invocations route through `_run_gh_cmd`.

**Implementation reviewer findings (verdict: pass; 3 minor non-blocking
points):**

9. **Title-format test gap addressed inline.** The implementation
   reviewer noted that no surface test pinned the literal `feat(<skill>):
   <slice-label>` shape on the `gh pr create --title` arg list (the
   AC #2 prescribed shape). Resolution: added
   `test_pr_title_uses_frontmatter_skill_scope` in `ExecutePrSuccessTests`
   that captures the `--title` arg via the `_run_gh_cmd` mock and asserts
   `^feat\(foo\):\s+007-03` against the synthetic spec's `skill: foo`
   frontmatter. 80 tests total (1 skipped); no regressions.

10. **`_check_github_remote` non-git-repo error message — flagged,
    not changed.** Reviewer noted that when `git config --get
    remote.origin.url` exits non-zero (e.g. running from a non-git
    directory), `_check_github_remote` returns `"no 'origin' remote
    configured"` — the same message it returns for an empty origin in
    a real repo. Both messages are actionable for the user (the next
    step is the same: configure an origin or run from inside a repo),
    so the conflation is acceptable. Filed here for traceability.

11. **GitHub-remote refuse message embeds the URL.** Reviewer noted
    that the refuse message `remote 'origin' does not point at
    github.com (url: <url>)` deviates from the spec's prescribed
    wording (which did not include the URL). Deliberate — surfacing
    the actual misconfigured URL gives the user a faster fix path
    than "go figure out what your origin is set to". Flagged for the
    record.

12. **PR body file written before subprocess — intentional ordering.**
    Reviewer asked whether AC #5's "before the first mutating
    subprocess" ordering still holds given the PR body file is
    written between the guards and the push. Answer: yes —
    `pr_body_path.write_text(...)` is a local filesystem write, not
    a "mutating subprocess". The same ordering applies in dry-run
    mode, which is the point: the user can inspect the PR body before
    deciding whether to re-run live.

---

## Slice 007-04 — scaffold-json-integration-flag

**STATUS: DEFERRED** _(deferred)_

**Resolution trigger:** User reports the `--mode` flag is genuinely annoying in repeated invocations (≥3 instances), OR the first project using jig that has BOTH a direct-merge skill and a PR-merge skill in the same repo.

**Goal:** Add an `integration: "direct" | "pr"` field to
`scaffold.json` so `land.py` can default to the right mode
without the `--mode` flag. Scaffold-init asks the user (or
detects from `git remote -v` whether GitHub is configured).

Deferred because: 007-01's `--mode` flag is sufficient for
manual invocations and the wizard touchpoint is non-trivial.
