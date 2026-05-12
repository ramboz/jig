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

**STATUS: DRAFT** _(deferred)_

**Goal:** `land.py execute --mode direct` actually runs the four
git commands from slice 007-01's "Next steps" section. Includes
safety rails: refuse if branch isn't merged-cleanly to main,
refuse if main has diverged, dry-run flag, prompt-before-destroy
for `worktree remove`.

Deferred because: destructive git operations need their own
safety review pass, and the "prepare" output already gives the
user copy-pasteable commands. Activating execute prematurely
risks losing work.

**Resolution trigger:** First time a real user runs `prepare`
twice in a row because they forgot to run the suggested commands.

---

## Slice 007-03 — pr-mode-execute

**STATUS: DRAFT** _(deferred)_

**Goal:** `land.py execute --mode pr` actually runs `git push` +
`gh pr create` with the pre-generated body. Includes detection
of a `gh` binary, refusal if no GitHub remote, and a confirm-
before-push prompt.

Deferred because: requires `gh` binary on PATH (not a jig dev
dependency) and depends on `pr-review` being designed (so the
PR body knows what reviewer surface to invite).

---

## Slice 007-04 — scaffold-json-integration-flag

**STATUS: DRAFT** _(deferred)_

**Goal:** Add an `integration: "direct" | "pr"` field to
`scaffold.json` so `land.py` can default to the right mode
without the `--mode` flag. Scaffold-init asks the user (or
detects from `git remote -v` whether GitHub is configured).

Deferred because: 007-01's `--mode` flag is sufficient for
manual invocations and the wizard touchpoint is non-trivial.
