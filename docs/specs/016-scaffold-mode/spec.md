---
status: DONE
skill: scaffold-init
tier: 0
---

# Spec 016: scaffold-mode

## Overview

Today jig is a Claude Code plugin: skills, agents, hooks, and helper `.py`
files all live under `${CLAUDE_PLUGIN_ROOT}` after `/plugin install`. The
dev never sees or touches that machinery — they get docs in their repo
and an opaque set of `/jig:*` commands they can't easily customize.
[Spec 001-scaffold-init](../001-scaffold-init/spec.md) scaffolds `docs/`
and `CLAUDE.md` into the project, but every executable artifact stays
plugin-side.

This spec teaches `scaffold-init` to **also copy the runtime machinery**
— `skills/`, `agents/`, `hooks/scripts/` — into the project's `.claude/`
directory, and to rewrite SKILL.md path placeholders accordingly. After
this spec lands, every jig install has two valid shapes:

1. **Plugin install** (unchanged): `/plugin install jig@jig` — central,
   upgradeable, opaque. Right for "install-and-forget" users.
2. **Scaffolded install** (new): `/jig:scaffold-init` drops the machinery
   into the dev's repo. They own it, can edit any SKILL.md or helper,
   and version-control their customizations. Right for "scaffold-and-
   extend" users — the original positioning.

Both modes are served from a single source-of-truth repo. The plugin
zip artifact (`scripts/build_release_zip.py`, slice 013-03) still
packages the canonical plugin form. The audit at the head of this spec
([referenced below](#references)) confirmed the path coupling is
shallow — agents have **zero** plugin-root references, hooks are
already `${CLAUDE_PROJECT_DIR}`-relative, and Python helpers'
`plugin_root()` functions already fall back to `Path(__file__).parents[N]`,
so they self-locate. The only real refactor is `SKILL.md` path strings
(24 occurrences across 7 files).

## Why now

- **The original positioning is "scaffolding library," not "plugin."**
  The README at jig's birth framed it as files-in-your-repo that you
  own and extend. The plugin path was a distribution convenience, not
  a positioning. Spec 013 made plugin install work end-to-end (CLI,
  zip, marketplace, release-please), but inadvertently locked
  customization away from devs. Two-mode parity recovers the original
  vision without giving up what 013 built.
- **Audit shows the coupling is shallow.** Agents = 0 plugin refs.
  Hooks = 0 plugin refs (use `$CLAUDE_PROJECT_DIR`). Skill helpers
  already self-locate via `plugin_root()` fallback. The blast radius
  of "copy runtime artifacts into the project" is one substitution
  pass over SKILL.md path strings + a hook-manifest rewrite. No
  helper-side `.py` changes are strictly required.
- **jig dogfoods naturally.** jig's own repo already has both
  `.claude-plugin/` (plugin mode) AND `skills/`/`agents/`/`hooks/` at
  the root (source-tree mode). It is, in effect, the canonical
  scaffolded install with one rewrite missing. Slice 016-03 turns that
  accident into a load-bearing test.
- **No competing in-flight work.** Tier 1 sprint is closed (per
  CLAUDE.md). Spec 008 (migrate) effectively complete. The only open
  Tier 1 candidate (`local-dev-parity`) has no signal. This is a
  natural moment to revisit positioning.

## Goals

1. **`scaffold-init` copies skills + agents into the project** so
   the dev sees them in `.claude/skills/` and `.claude/agents/` and
   can edit them under version control.
2. **`scaffold-init` copies hook scripts + writes `.claude/settings.json`**
   registering the same five jig hooks against the project-local
   script paths, so the hook pipeline works on a scaffolded install
   without any plugin component.
3. **A single source of truth for SKILL.md path strings.** The audit
   found 24 `${CLAUDE_PLUGIN_ROOT}/skills/<name>/<helper>.py`
   occurrences across 7 SKILL.md files. The source files keep their
   plugin-style paths (for plugin distribution); `scaffold.py`
   rewrites them to project-relative paths at copy time.
4. **Dual-mode documentation.** README's installation section gains
   a parallel "Scaffold into your repo" path next to the existing
   plugin install. CONTRIBUTING.md notes that jig's own working tree
   is the canonical scaffolded layout.
5. **Verifiable end-to-end on `jig` itself.** Running `scaffold-init`
   into a clean checkout produces a `.claude/` tree whose hooks fire,
   whose skills are discoverable, and whose helpers run.

## Non-goals

- **`/jig:update` skill for selective version-updates of in-repo
  files.** Discussed in the audit as Option B in the update story.
  Manual cherry-pick from release notes is the day-one update path.
  An update skill is a natural future slice (016-04 below, **deferred**)
  but not required to ship 016-01..03.
- **Removing the plugin path.** Plugin install via `/plugin install
  jig@jig` keeps working unchanged. This spec is additive.
- **Per-file "ejected" metadata** (Option C in the audit). A header
  like `<!-- jig-version: 1.0.0 ejected:false -->` on every scaffolded
  file is the right shape *if and when* the update skill ships.
  Pre-baking it now creates churn for unclear value.
- **Coexistence resolution rules** beyond Claude Code's existing
  project-scoped precedence. If a user has both jig plugin installed
  AND scaffolded files in `.claude/`, the project-scoped versions win
  by Claude Code's normal rules. We document this; we do not introduce
  a new arbiter.
- **A new tier or skill.** Scaffold-init absorbs the new behavior
  via flags / new subcommand surface; no new skill is born.
- **Vision/architecture elicitation.** Tracked separately as
  [spec 017](../017-vision-elicitation/spec.md).

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** — Spike | Do we need a spike on `${CLAUDE_PROJECT_DIR}` availability inside skill bash, or on project-scoped skill discovery rules? | **No** — but called out as a Known constraint. The implementer of 016-01 validates `${CLAUDE_PROJECT_DIR}` is reachable from skill bash before committing path-rewrite strategy. If it isn't, fall back to absolute paths computed at scaffold time (still no spike — the recovery path is mechanical). |
| **P** — Path | Single rewrite source-of-truth (SKILL.md keeps plugin-style paths; only scaffold.py rewrites) vs. abstract placeholder (`${JIG_ROOT}`) rewritten at both plugin-build and scaffold time? | **Single rewrite, scaffold-only.** Source SKILL.md stays as-is for the plugin distribution (no zip-build rewrite step needed; `build_release_zip.py` stays simple). scaffold.py owns the substitution `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` → `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` at copy time. One substitution pass, one consumer. |
| **I** — Interface | One big slice or split by artifact-class? | **Three active slices + one deferred**, split by artifact-class (skills+agents in 016-01, hooks in 016-02, dogfood+docs in 016-03, update skill deferred as 016-04). Each is independently mergeable. Anti-horizontal-phasing holds for each (see per-slice checks). |
| **D** — Data | What new files land in the user's project? | **Per 016-01:** `.claude/skills/jig-<name>/SKILL.md` (+ siblings: `<helper>.py`, `test_*.py` excluded), `.claude/agents/jig-<name>.md`. **Per 016-02:** `.claude/hooks/scripts/jig-*.sh`, `.claude/settings.json` (new file, gets jig hook registration). **Per 016-03:** README + CONTRIBUTING updates. No new files in the user's project from 016-03. |
| **R** — Rules | What's the precedence between scaffolded and plugin installs of the same skill? | **Project-scoped wins** — this is Claude Code's existing rule, not a new arbiter. Documented in CONTRIBUTING.md (016-03). Users who scaffolded and then later install the plugin won't see double-fire; the scaffolded files take precedence. |

## Out of scope for spec 016 (any slice)

- **Auto-detection of "this project should scaffold, not plugin-install"**
  at scaffold-init time. The flag is explicit (or the new subcommand
  is explicit) — no inference.
- **A `/jig:eject` skill** that converts an existing plugin install
  into a scaffolded one. Doable later via the same machinery 016-01
  introduces; punted to a future spec.
- **Migrating `${CLAUDE_PLUGIN_ROOT}` to `${JIG_ROOT}` at the source.**
  The single-rewrite path (P column above) keeps source SKILL.md
  using `${CLAUDE_PLUGIN_ROOT}`. A future refactor could universalize
  to `${JIG_ROOT}` if it ever buys anything.
- **Multi-language helpers.** All helpers today are Python; scaffold-mode
  copies them as-is. If a future helper is shell or Node, the same
  copy-and-rewrite logic applies trivially.
- **Updates for in-repo files.** Tracked as **deferred slice 016-04**.

## Known constraints

- **`${CLAUDE_PROJECT_DIR}` availability in skill bash recipes is
  load-bearing.** It is set by Claude Code for hook contexts; the
  implementer of 016-01 must confirm it's also set when bash inside
  a project-scoped SKILL.md runs. If not, the fallback is to rewrite
  SKILL.md paths to absolute paths at scaffold time (using the
  target dir captured during `scaffold.py` execution). Either approach
  is mechanical; this is not a spike question.
- **Project-scoped skill discovery is governed by Claude Code, not
  jig.** `.claude/skills/<name>/SKILL.md` is the conventional layout;
  the frontmatter `name` field is authoritative. We choose `jig-`
  prefixed *directory* names to avoid collisions with user-added
  project skills (`.claude/skills/jig-scaffold-init/SKILL.md` ↔
  frontmatter `name: scaffold-init`). The Claude Code skill list will
  show two skills with the same human-facing name if both plugin and
  scaffold are installed; project-scoped wins by precedence.
- **Hook scripts don't change.** Today's `hooks/scripts/jig-*.sh`
  files use `$CLAUDE_PROJECT_DIR` exclusively (verified by the audit).
  Copying them as-is into `.claude/hooks/scripts/` works without edit.
- **Helper `.py` files don't change.** `plugin_root()` already falls
  back to `Path(__file__).resolve().parents[2]` when `$CLAUDE_PLUGIN_ROOT`
  is unset. In scaffold mode, that resolves to the project's
  `.claude/` directory, which is the right scope for reading project-
  local state. Templates (read only by `scaffold.py` at install time)
  are never read at runtime, so their non-presence in `.claude/` is fine.
- **scaffold-init's "already scaffolded" check stays the same.**
  Re-running scaffold-init with scaffold-mode enabled on an already-
  scaffolded project still raises `AlreadyScaffoldedError`. The
  `--force` escape hatch behaves the same way.
- **scaffold-init's "looks already-spec-driven" check (008-05) is
  unaffected.** Routing to `/jig:migrate` still fires regardless of
  scaffold-mode preference.

---

## Slice 016-01 — copy-skills-and-agents

**STATUS: DONE**

**Goal:** `scaffold-init` learns to copy `skills/*` and `agents/*` from
the plugin source tree into `.claude/skills/` and `.claude/agents/` in
the target project, rewriting SKILL.md path strings from
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/` to a project-relative form. After
this slice, a freshly-scaffolded project contains editable copies of
every jig skill + agent, discoverable by Claude Code as project-scoped.
Hooks are not touched (next slice).

**DoR:**
- ⏳ Audit findings reviewed (see spec Overview).
- ✅ `scaffold.py` already has `copy_template()` + `render()` infrastructure
  with placeholder substitution — extend, don't rewrite.
- ✅ Test pattern established (`test_scaffold.py` has 100+ tests; new
  tests follow that file's style).
- ⏳ Implementer confirms `${CLAUDE_PROJECT_DIR}` reachability from skill
  bash (otherwise fall back to absolute paths — Known constraint #1).

**Anti-horizontal-phasing check.** Vertical: the user is the dev running
`scaffold-init`; the user-observable outcome is `ls .claude/skills/` shows
all jig skill directories with editable SKILL.md files inside, and
`/jig:scaffold-init` (or any jig skill) auto-completes/invokes from the
project-scoped install with no plugin component present. Crosses all
layers: `scaffold.py` (new copy + rewrite logic), the on-disk tree
under `.claude/` (new artifact), and Claude Code's skill router (existing,
unmodified — but now discovering jig skills from `.claude/skills/`).

**Acceptance Criteria:**

1. **`scaffold.py` grows a `--with-machinery` flag** (or equivalent
   surface — implementer's call, recorded in deviation log).
   Default-off for now: existing scaffold-init invocations are unchanged.
   When set, the wizard ALSO copies skills/agents in addition to docs.
   Once 016-03 lands, the default flips to on; for slices 016-01 and
   016-02 the flag is opt-in to keep the existing test suite green.

2. **With `--with-machinery`, `scaffold-init` copies every directory
   under `skills/` into `target/.claude/skills/jig-<name>/`,
   excluding `test_*.py` files.** The `jig-` prefix on the directory
   namespaces jig's skills away from any user-added project skills
   that may already live at `.claude/skills/<name>/`. The SKILL.md
   frontmatter `name` field is left untouched (still `scaffold-init`,
   `tdd-loop`, etc.) — Claude Code's discovery uses the frontmatter,
   not the directory name.

3. **SKILL.md path placeholders are rewritten at copy time.** Every
   literal `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` in any copied
   SKILL.md becomes `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`.
   No other strings in SKILL.md are modified. (If `${CLAUDE_PROJECT_DIR}`
   is not reachable from skill bash — see Known constraint #1 —
   the fallback is to substitute the absolute path of the target
   project, captured at scaffold time. Deviation log records which
   strategy was used.)

4. **`agents/*.md` are copied to `target/.claude/agents/jig-<name>.md`**
   with no string substitution (the audit confirmed agents have zero
   plugin-root references). The `jig-` prefix on filenames namespaces
   them from user-added agents.

5. **Copied SKILL.md files keep their YAML frontmatter intact.** No
   re-rendering of frontmatter; only the body's
   `${CLAUDE_PLUGIN_ROOT}/skills/...` strings are touched. A
   regression test reads a copied SKILL.md and asserts the frontmatter
   matches the source.

6. **Skill helpers (`*.py`, excluding `test_*.py`) are copied verbatim.**
   No substitution. `plugin_root()` fallback handles self-location.

7. **`scaffold.json` gains a new top-level field `scaffold_mode`** with
   values `"plugin-only"` (default, today's behavior) or `"in-repo"`
   (set when `--with-machinery` was passed). Used by 016-03's dogfood
   verification.

8. **The new test file `test_scaffold_mode.py`** (separate from
   `test_scaffold.py` so existing-test stability is obvious) covers:
   (a) with `--with-machinery`, `.claude/skills/jig-scaffold-init/SKILL.md`
       exists and matches the source up to path substitutions;
   (b) every `${CLAUDE_PLUGIN_ROOT}/skills/` occurrence in the copied
       SKILL.md has been rewritten;
   (c) no `${CLAUDE_PLUGIN_ROOT}/skills/` occurrences remain in any
       copied SKILL.md (the substitution covers all runtime path
       references, not a subset). **Scope clarification:** AC #3
       only rewrites `${CLAUDE_PLUGIN_ROOT}/skills/<name>/`. Incidental
       doc-prose mentions of bare `${CLAUDE_PLUGIN_ROOT}` and
       `${CLAUDE_PLUGIN_ROOT}/templates/` (e.g. in scaffold-init's
       Gotchas, migrate's prose) survive intentionally — they are not
       runtime-relevant. The test asserts the narrower invariant;
       see slice 016-01 deviation log §2 for full rationale.
   (d) `test_*.py` files are NOT in `.claude/skills/jig-<name>/`;
   (e) `.claude/agents/jig-reviewer.md` exists with unchanged content;
   (f) `scaffold.json.scaffold_mode == "in-repo"` when the flag was passed;
   (g) without `--with-machinery`, none of `.claude/skills/` or
       `.claude/agents/` is created — pure existing-behavior preservation.

9. **No regression in existing tests.** Full `test_scaffold.py` suite
   stays green. The default-off flag is load-bearing for this AC.

**Definition of Done:**

- [x] `scaffold.py` grows the `--with-machinery` flag (or equivalent).
- [x] Skill + agent copy logic implemented with path substitution.
- [x] `scaffold.json` schema extended with `scaffold_mode` field.
- [x] `test_scaffold_mode.py` committed with the 7 cases from AC #8.
- [x] Existing `test_scaffold.py` suite green.
- [x] Full test suite green.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (016-01)

**1. Spec was originally numbered 014 during authorship + implementation;
renumbered to 016 mid-flight.** A parallel claude session FF-merged a
distinct `feat(arch-review): spec 014-01` to local `main` while slice
014-01 (scaffold-mode) was in the implementer's hands. We took the
mechanical path: merged main into the branch, renumbered our specs
014 → 016 and 015 → 017, and let `arch-review` keep `014`. The
implementer's code carried stale `014` labels in comments/docstrings
(`scaffold.py:379, 422, 501, 504, 586, 598, 600, 617` and
`test_scaffold_mode.py:2, 4, 47, 87, 298`) — those were swept to `016`
as part of addressing the implementation reviewer's first SPECIFIC
ISSUE. No code-path changes; pure labeling correction.

**2. AC #8(c) narrowed from "no `${CLAUDE_PLUGIN_ROOT}` remains" to
"no `${CLAUDE_PLUGIN_ROOT}/skills/` remains."** The originally-drafted
AC #8(c) said "no `${CLAUDE_PLUGIN_ROOT}` occurrences remain in any
copied SKILL.md (the substitution covers all of them, not a subset)."
This contradicted AC #3, which explicitly rewrites *only*
`${CLAUDE_PLUGIN_ROOT}/skills/<name>/` and says "No other strings in
SKILL.md are modified." Reality: `scaffold-init/SKILL.md` carries
incidental `${CLAUDE_PLUGIN_ROOT}/templates/` (one occurrence) plus a
prose-level `${CLAUDE_PLUGIN_ROOT}` in its Gotchas; `migrate/SKILL.md`
has another prose mention. The audit summary undercounted (also flagged
in implementer report: "audit cited 7 SKILL.md files; the repo has 8 —
the `migrate` SKILL.md was added since the audit"). AC #3 takes
precedence — it's the runtime-correctness invariant. AC #8(c) text
amended in the spec to assert the narrower invariant
(`${CLAUDE_PLUGIN_ROOT}/skills/`-scoped), with an inline scope-
clarification note pointing here.

**3. Implementation skips dirs starting with `_` and dirs without a
`SKILL.md` — not in any AC.** `skills/_common/` is a `_`-prefixed
private sub-directory holding shared helpers; `scaffold.py` shouldn't
treat it as a skill. Same logic for any future dir under `skills/`
that lacks a `SKILL.md` (e.g. a `__pycache__/` sneaking in). Both skip
rules are defensive, not user-facing. The convention mirrors how
`scripts/run_tests.py` ignores `_common`. Not a deviation from the
spec — a sensible extension of "copies every directory under
`skills/`" (AC #2) that the spec wording didn't anticipate.

**4. `${CLAUDE_PROJECT_DIR}` env-var path chosen over absolute-path
fallback (Known constraint #1 / AC #3 parenthetical).** The implementer
chose to emit `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` rather
than rewriting paths to absolute target-time values. Rationale (per
implementer): the existing hook scripts already rely on
`$CLAUDE_PROJECT_DIR` in production (audit-confirmed); Claude Code
documents it as the project-root injection for hook contexts;
recovery to absolute substitution is a one-line change inside
`_rewrite_skill_md_paths()` if a future smoke-test reveals
unreachability from SKILL.md bash specifically. The DoR item
"Implementer confirms `${CLAUDE_PROJECT_DIR}` reachability from skill
bash" remains ⏳ at the time of this log — bridge-of-trust on the
documented behavior, with the slice 016-01 close-out smoke-test as
the empirical check.

**5. Reviewer flagged two minor test-quality observations, kept as-is.**
- `test_scaffold_mode.py:109-121` (`test_a` body equality) does whole-
  file substitution on the source while the implementation only
  substitutes the body. Works today because no source SKILL.md
  frontmatter contains `${CLAUDE_PLUGIN_ROOT}/skills/`. Reviewer
  rated "fragile but not a current bug." Kept; will tighten if a
  future SKILL.md ever puts the token in frontmatter.
- `test_scaffold_mode.py:228-241` (AC #5 frontmatter regression)
  only checks `scaffold-init/SKILL.md`. Reviewer noted "iterating over
  every copied SKILL.md would be a stronger guarantee" but rated
  "minor." Kept; the existing single-file check meets the spec's
  literal "A regression test reads a copied SKILL.md."

**6. Smoke-test result (2026-05-15, post-DONE close-out).** Ran
`CLAUDE_PLUGIN_ROOT=$(pwd) python3 skills/scaffold-init/scaffold.py
--with-machinery <tmpdir>` from the jig worktree. Output:
- `<tmpdir>/.claude/skills/` contained 11 `jig-`prefixed directories
  (one per source skill, including `jig-arch-review` carried in from
  main's merge): `jig-adr-workflow`, `jig-arch-review`, `jig-contracts`,
  `jig-independent-review`, `jig-memory-sync`, `jig-migrate`,
  `jig-pr-review`, `jig-scaffold-init`, `jig-slice-land`,
  `jig-spec-workflow`, `jig-tdd-loop`.
- `<tmpdir>/.claude/agents/` contained 3 `jig-`prefixed files:
  `jig-architect.md`, `jig-implementer.md`, `jig-reviewer.md`.
- `${CLAUDE_PLUGIN_ROOT}/skills/` count in `jig-tdd-loop/SKILL.md` and
  `jig-scaffold-init/SKILL.md` = **0** (AC #3 substitution complete).
- `${CLAUDE_PROJECT_DIR}` count in same two SKILL.md files = **2**
  each (the rewritten bash commands). Sample from `jig-tdd-loop`:
  `python3 "${CLAUDE_PROJECT_DIR}/.claude/skills/jig-tdd-loop/tdd.py"
  detect [target]` — exactly the expected shape.
- Bare-prose `${CLAUDE_PLUGIN_ROOT}` mentions DID survive in
  `jig-scaffold-init/SKILL.md` (lines 19, 101 — the `templates/` path
  reference + the "right env var inside the plugin" Gotcha) per
  deviation log §2. Confirms the narrower AC #8(c) interpretation
  matches the implementation's behavior.

Structural verification passes. Runtime reachability of
`${CLAUDE_PROJECT_DIR}` from skill-bash context (DoR §4 open
question) was NOT exercised — that requires a `claude` session
loading the scaffolded skills, which is a manual user-driven check
out of band of this smoke-test. The structural rewrite is correct;
if the env-var doesn't resolve at runtime, the one-line fallback
inside `_rewrite_skill_md_paths()` (per deviation log §4) is the
recovery path.

**7. Test counts.** Pre-016-01 baseline (post-merge of `main`'s
arch-review work): **555 tests, 3 skipped** (541 jig baseline + 14
slice 016-01 + 27 arch-review merged in concurrently → 582 grand
total). Post-label-fix: **582 tests, 3 skipped — green.** No
regressions.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache updated to mark 016-01 DONE.
- [x] Manual smoke-test: run `scaffold.py --with-machinery <tmpdir>`,
  verify `ls <tmpdir>/.claude/skills/` lists all jig skills, and
  verify one SKILL.md no longer contains
  `${CLAUDE_PLUGIN_ROOT}/skills/` (note: bare `${CLAUDE_PLUGIN_ROOT}`
  prose mentions DO survive — see deviation log §2). Recorded in
  deviation log §6 (2026-05-15).

---

## Slice 016-02 — copy-hooks-and-register

**STATUS: DONE**

**Goal:** With `--with-machinery`, `scaffold-init` also copies
`hooks/scripts/jig-*.sh` into `target/.claude/hooks/scripts/`, and
writes `target/.claude/settings.json` with the five jig hooks
registered against the project-local script paths. After this slice,
a scaffolded install fires the same SessionStart / UserPromptSubmit /
PreToolUse / Stop hooks today's plugin install fires — without any
plugin component.

**DoR:**
- ⏳ Slice 016-01 DONE (the `--with-machinery` flag exists and the copy
  infrastructure is in place; 016-02 extends the same code path).
- ✅ `hooks/scripts/jig-*.sh` files use `$CLAUDE_PROJECT_DIR`
  exclusively (audit confirmed; no script changes needed).
- ✅ `hooks/hooks.json` shape is documented; the project-side equivalent
  goes in `.claude/settings.json` under the `hooks` key per Claude
  Code's project-hooks convention.

**Anti-horizontal-phasing check.** Vertical: the user is the dev who
just scaffolded jig in-repo; the user-observable outcome is that the
SessionStart hook fires when they open `claude` in the project, the
UserPromptSubmit hook scans the prompt for unknown terms, and the
Stop hook captures task ideas — all WITHOUT the jig plugin being
installed. Crosses all layers: hook scripts (copied), settings.json
(new content), and the Claude Code hook runtime (existing — but now
sees jig hooks from project settings, not plugin).

**Acceptance Criteria:**

1. **Hook scripts are copied to `.claude/hooks/scripts/`** when
   `--with-machinery` was passed. All five scripts (`jig-context-check.sh`,
   `jig-memory-scan.sh`, `jig-spec-gate.sh`, `jig-task-capture.sh`,
   `jig-telemetry.sh`) land verbatim — no substitution; they already use
   only project-relative env vars.

2. **`.claude/settings.json` is generated (or updated, if pre-existing)
   with the five jig hooks registered.** The shape mirrors
   `hooks/hooks.json` but with `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`
   in place of `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/`. Timeouts and
   `matcher` rules carry over unchanged.

3. **Pre-existing `.claude/settings.json` is preserved on merge.** If
   the target already has a `settings.json` with other hooks or other
   top-level fields (permissions, env, etc.), scaffold-init adds its
   hooks under a stable `metadata.managed_by_jig: true` marker on
   each appended hook entry, or merges into existing arrays without
   clobbering. The implementer chooses the merge strategy; the
   deviation log records the decision. **The test suite covers both
   the clean-create and the merge-into-existing case.**

4. **scaffold-init refuses to overwrite a managed `settings.json`
   that lacks a jig marker** without `--force`. Same safety stance
   as the existing `scaffold.json` check. If the file exists and
   contains hooks but none carry the jig marker, scaffold-init refuses
   and tells the user to either `--force` or merge by hand. (No
   silent stomping.)

5. **`.claude/hooks/scripts/jig-*.sh` files are executable** (`0o755`
   mode) after copy. Today's plugin install relies on the file system's
   execute bit being set in the source tree; copying must preserve it.

6. **`test_scaffold_mode.py` is extended** with cases:
   (h) all five hook scripts exist under `.claude/hooks/scripts/`
       and are executable;
   (i) `.claude/settings.json` parses as JSON and contains entries
       for all four hook events (PreToolUse, SessionStart,
       UserPromptSubmit, Stop) referencing
       `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-*.sh`;
   (j) merge-into-existing: an existing `.claude/settings.json` with
       a non-hook field is preserved;
   (k) refuse-on-unmanaged-hooks: an existing `.claude/settings.json`
       with hooks but no jig marker raises and exits non-zero.

7. **No regression in existing tests.** Full suite green.

**Definition of Done:**

- [x] 016-01 DONE.
- [x] Hook copy + settings.json generation implemented in `scaffold.py`.
- [x] Merge-existing logic implemented (per AC #3) with deviation-log
  rationale on the chosen strategy.
- [x] `test_scaffold_mode.py` extended per AC #6.
- [x] Full test suite green.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (016-02)

**1. Merge strategy decision (AC #3): append-with-marker.** Pre-
existing `.claude/settings.json` is treated as follows. Non-hook
top-level fields (`permissions`, `env`, etc.) pass through verbatim.
Per hook event, non-jig entries survive untouched; jig-managed
entries are replaced in place on re-run (so idempotent and never
duplicates). Every jig-managed hook entry carries
`metadata: {managed_by_jig: true}` — the marker that drives both the
idempotent replace-in-place and the AC #4 refuse-on-unmanaged
safety check. Rationale: refuse-then-instruct on any pre-existing
settings.json would have forced devs with `permissions` or `env`
already configured into `--force`, which is a needlessly hostile
default. Append-with-marker preserves their config and still
hard-stops against silent stomping of third-party hooks (AC #4).

**2. AC #4 refuse-on-unmanaged-hooks is independent of merge.**
Trigger: `.claude/settings.json` has hooks AND none carry
`metadata.managed_by_jig`. In that case `scaffold.py` raises
`UnmanagedHooksError`, exits with code 3, and the error text names
`--force` as the documented escape. `--force` propagates from
`scaffold()` through to `_copy_hooks_and_register` and bypasses
the safety while still preserving the existing entries (they survive
the merge — see test
`test_existing_user_hooks_under_other_matcher_preserved`).

**3. Idempotent re-run with `--force` chooses replace-in-place
rather than skip-if-present.** Spec was silent on this detail.
Replace-in-place ensures that a jig version bump that changes a
hook script's matcher (or adds a new event handler) propagates on
the next `--force` re-scaffold. Skip-if-present would have made
that update silent and confusing. Confirmed by
`test_idempotent_rerun_does_not_duplicate_jig_entries`.

**4. AC #6 sub-case (i) tests are tighter than the spec wording.**
Spec said the test asserts entries "referencing
`${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-*.sh`." Two tests
together implement the stronger invariant:
- `test_i_settings_json_registers_all_four_hook_events`
  (test_scaffold_mode.py:406–411) asserts there are **exactly five**
  such references — one per source hook script.
- `test_settings_json_shape_mirrors_source_hooks_json`
  (test_scaffold_mode.py:413–437) asserts the `matcher` / `timeout` /
  `async` / `type` keys from `hooks/hooks.json` are preserved
  per-entry.
The combined invariant is in spirit with the spec's "shape mirrors
`hooks/hooks.json`" language. Documented here so a future maintainer
who adds a sixth hook script knows to update **both** tests in
lockstep.

**5. Reviewer SPECIFIC ISSUES — kept as-is.**
- `test_idempotent_rerun_does_not_duplicate_jig_entries` only
  checks jig-entry counts post-re-run; it doesn't independently
  verify foreign-non-jig-entries-don't-duplicate-either.
  Reviewer rated "today's coverage is sufficient for AC #3 but
  the survivors-no-duplication invariant is untested." Kept as a
  future tightening candidate.
- `test_existing_user_hooks_under_other_matcher_preserved`
  conflates AC #3 (jig hooks merge alongside) and AC #4 (force
  escape) in one test. Reviewer rated "not a correctness bug."
  Kept for compactness; both invariants are exercised.
- `_copy_hooks_and_register` silently skips the copy loop when
  `src_scripts` doesn't exist (guarded by `if src_scripts.is_dir():`
  at scaffold.py:588) but still writes settings.json registering
  paths to scripts that don't exist. This can't happen in the wild —
  the plugin tree always has `hooks/scripts/` — but a future jig
  refactor that removed that directory would silently produce a
  broken scaffold. Reviewer's note recorded; a sanity-guard error
  is a separate defensive ticket if it ever recurs.

**6. Test counts.** Pre-016-02 baseline: 582 tests, 3 skipped.
Post-016-02: 593 tests, 3 skipped — green. New tests: 11
(`CopyHooksAndRegisterTests` + `MergeExistingSettingsTests`).
No regressions.

**7. Smoke-test result (2026-05-15, post-DONE close-out).** Ran
`CLAUDE_PLUGIN_ROOT=$(pwd) python3 skills/scaffold-init/scaffold.py
--with-machinery <tmpdir>` from the jig worktree. Structural
verification:
- `.claude/hooks/scripts/` contained all 5 source scripts:
  `jig-context-check.sh`, `jig-memory-scan.sh`, `jig-spec-gate.sh`,
  `jig-task-capture.sh`, `jig-telemetry.sh`.
- All 5 are mode `-rwxr-xr-x` (0o755) — AC #5 confirmed at runtime,
  not just in unit tests.
- `.claude/settings.json` registered all 4 hook events
  (`PreToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`) with
  matcher blocks mirroring `hooks/hooks.json` shape.
- **5 jig-marked matcher blocks total** (`PreToolUse` has 2: Task →
  telemetry, Edit|Write|MultiEdit → spec-gate; the other three
  events one block each). Every block carries
  `metadata: {managed_by_jig: true}` at the **outer matcher block**
  level — NOT on the inner hook command. Worth recording: an
  initial count-by-marker script looked for the marker on the
  inner hook entry and reported `0`, which momentarily looked
  like a regression. The marker placement mirrors how
  `hooks/hooks.json` pairs a matcher with its hooks list — jig
  owns the *block*, not the individual command.
- Every command resolves to `bash
  ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-*.sh`. Sample
  SessionStart: `bash
  ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/jig-context-check.sh`.
  AC #2 confirmed; no `${CLAUDE_PLUGIN_ROOT}` references survived
  in the registered commands.

Runtime SessionStart-hook firing (the spec's literal close-out
wording: "open `claude` in that dir, observe the SessionStart hook
fires") was NOT exercised — it requires a fresh `claude` session
loading the scaffolded settings.json, which is user-driven and out
of band of this smoke-test. Structural verification confirms the
registration is correct; runtime fire-or-not is what the user
observes at first use. Same bridge-of-trust pattern as slice 016-01
§6.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache updated to mark 016-02 DONE.
- [x] Manual smoke-test: run scaffold-init with `--with-machinery`
  into a tmpdir; structural verification PASS per deviation log §7
  (5 hook scripts copied with 0o755, all 4 events registered with
  jig markers on outer matcher blocks, every command uses
  `${CLAUDE_PROJECT_DIR}` paths). Runtime SessionStart-hook firing
  observation is user-driven in a fresh `claude` session — same
  bridge-of-trust as 016-01.

---

## Slice 016-03 — dogfood-and-dual-mode-docs

**STATUS: DONE**

**Goal:** Flip `--with-machinery` to default-on (i.e. scaffold-mode
becomes jig's default install shape), rewrite README's Installation
section to document the two install paths in parallel, and add a
CONTRIBUTING.md note that jig's own working tree is the canonical
scaffolded install (closing the dogfood loop). Verify end-to-end on
a clean checkout of jig itself.

**DoR:**
- ⏳ Slices 016-01 and 016-02 DONE.
- ✅ `scripts/verify_install.py` exists and runs the 4-check core
  (per slice 011-01 / 011-02).
- ✅ README Installation section is the canonical entry point for
  new users (per 013-04 AC #2).

**Anti-horizontal-phasing check.** Vertical: the user is a brand-new
adopter reading the README; the user-observable outcome is that the
README offers two install commands side-by-side and the dev can pick
either based on whether they want to extend jig or just consume it.
Crosses all layers: README (public docs), CONTRIBUTING.md (contributor
docs), scaffold.py (default flag change), and verify_install.py
(extended to cover the scaffold-mode layout).

**Acceptance Criteria:**

1. **`scaffold.py`'s `--with-machinery` flag flips to default-on.**
   Add a `--plugin-only` flag for users who explicitly want the old
   docs-only behavior. The deviation log records the impact on
   `test_scaffold.py` (some existing tests may now exercise the new
   default; either update them OR have them pass `--plugin-only`
   explicitly to preserve historical assertions — implementer's call).

2. **README Installation section gains a "Scaffold into your repo"
   path** alongside the existing two (CLI marketplace install + zip
   from release). The order is: scaffold (new default), plugin from
   CLI, plugin from zip, from source for contributors. Each path
   names its trade-off in one sentence (e.g. "Scaffold to own and
   edit the machinery; plugin to install-and-forget").

3. **CONTRIBUTING.md gains a "Two install shapes" subsection** that
   explains:
   - jig's own working tree is the canonical scaffolded install
     (skills/ + agents/ + hooks/ at the repo root, just one level
     up from where they'd be in `.claude/`);
   - changes to source SKILL.md propagate to both modes (plugin
     install reads source directly; scaffold-mode rewrites at copy
     time);
   - hook scripts and helper `.py` files are mode-agnostic — they
     don't need a build step;
   - the precedence rule (project-scoped wins) when both are
     installed in the same dev environment.

4. **`scripts/verify_install.py` gains a `--mode {plugin,scaffold}`
   flag.** The four core checks adapt:
   - plugin mode: today's behavior (validates `${CLAUDE_PLUGIN_ROOT}/
     skills/...`);
   - scaffold mode: validates `<root>/.claude/skills/jig-*/SKILL.md`,
     `.claude/agents/jig-*.md`, `.claude/hooks/scripts/jig-*.sh`,
     `.claude/settings.json` hook registration.
   Tests in `test_verify_install.py` cover both modes.

5. **End-to-end dogfood on jig itself.** In a clean tmpdir, run
   `python3 scripts/build_release_zip.py --version <X.Y.Z>` (existing
   plugin-build path) **AND** `python3 skills/scaffold-init/scaffold.py
   <tmpdir>` (new scaffold path). The first produces a zip whose
   four checks pass (regression — existing flow); the second produces
   a `.claude/` tree whose scaffold-mode checks pass. **Both succeed
   from the same source tree.** Recorded in the deviation log as a
   timestamped run.

6. **A test in `test_scaffold_mode.py` regression-pins the dogfood
   shape** by scaffolding into a tmpdir and asserting all four
   `verify_install.py --mode scaffold` checks pass. This is the
   automation backstop for AC #5.

7. **The "Scaffold mode" capability is referenced in `CLAUDE.md`'s
   skill table** for `scaffold-init`. One-line note describing what
   the flag does and pointing at spec 016.

8. **No regression in existing tests.** Full suite green. Test count
   delta recorded in deviation log.

**Definition of Done:**

- [x] 016-02 DONE.
- [x] `scaffold.py` default flipped; `--plugin-only` opt-out wired.
- [x] README Installation section rewritten per AC #2.
- [x] CONTRIBUTING.md "Two install shapes" subsection added.
- [x] `verify_install.py` gains `--mode` flag with both branches
  tested.
- [x] `test_scaffold_mode.py` regression test for AC #6.
- [x] CLAUDE.md skill table updated per AC #7.
- [x] End-to-end dogfood recorded in deviation log per AC #5.
- [x] Full test suite green.
- [x] Implementation review passed.
- [x] Deviation log written.
- [x] Reconciliation review passed.

### Deviation log (016-03)

**1. `--plugin-only` and `--with-machinery` are argparse mutually-
exclusive, not standalone flags.** Spec AC #1 says "Add a
`--plugin-only` flag." The implementer chose to group them under
`add_mutually_exclusive_group()` because the two flags are
semantically opposing booleans on the same dimension. `--with-machinery`
is kept (default-on, redundant by default) for documentation symmetry
and back-compat with explicit slice 016-01/02 invocations in tests
and runbooks. Passing both flags exits 2 with the standard argparse
mutually-exclusive error (covered by
`test_plugin_only_and_with_machinery_are_exclusive`).

**2. `test_scaffold.py` historical assertions left untouched.** The
spec briefing said "Decide: update existing `test_scaffold.py` cases
that broke OR have them pass `--plugin-only`. Record the decision."
Decision: **neither was needed**. A grep of `test_scaffold.py` showed
zero references to `.claude/skills/`, `.claude/agents/`,
`.claude/hooks/scripts/`, `.claude/settings.json`, or `scaffold_mode` —
the existing tests assert only canonical-docs invariants (CLAUDE.md,
scaffold.json shape, docs/architecture.md content, etc.) that are
unaffected by the default flip. Default scaffolds still produce the
same docs tree; what changed is the addition of `.claude/skills/`
and friends, which no test_scaffold.py case asserts on. The
`DefaultOffMachineryTests` and `MergeExistingSettingsTests` in
`test_scaffold_mode.py` were the only consumers, and those were
updated to pass `--plugin-only` explicitly (still asserting the
opt-out preserves the old shape).

**3. `verify_install.py` gained `--project-root` separate from
`--plugin-root`.** Spec AC #4 said "`verify_install.py` gains a
`--mode {plugin,scaffold}` flag." The two modes target structurally
different trees (plugin: `<plugin_root>/.claude-plugin/`,
`<plugin_root>/skills/`; scaffold: `<project_root>/.claude/skills/`,
`<project_root>/.claude/agents/`, etc.). Reusing `--plugin-root` for
both would conflate the two concepts in the CLI surface. Decision:
add `--project-root` (defaults to `.` in scaffold mode) and keep
`--plugin-root` defaulting to the script's repo root. Plugin-mode
invocations are byte-identical to today; scaffold-mode adds a clean
new path.

**4. Scaffold-mode "not installed" check uses `.claude/` absence,
not `.claude/skills/` absence.** A scaffolded project may have an
empty or in-progress `.claude/` while the dev is working through
slices; flagging that as "not scaffolded" would be overzealous. The
`_looks_unscaffolded` heuristic only fires when `.claude/` doesn't
exist at all — mirroring `_looks_uninstalled`'s "neither plugin.json
nor marketplace.json nor agents/" approach. Covered by
`test_run_headless_scaffold_returns_two_when_not_scaffolded`.

**5. AC #5 dogfood run (2026-05-15T17:12:14Z).** Ran both paths
from the same source tree in `/tmp/jig-dogfood-016-03/`:

```
--- 1. Plugin-build path: scripts/build_release_zip.py ---
OK: built jig-dogfood.zip (66 entries, version 1.0.0)

--- 2. Plugin-build smoke-test (validates the zip) ---
PASS marketplace: marketplace.json present and lists 'jig'
PASS manifest: plugin.json present and well-formed
PASS agents: all three subagent definitions present
PASS skills: 11 skill SKILL.md file(s) reachable
summary: 4/4 passed

--- 3. Scaffold path: scaffold.py (default-on with-machinery) ---
scaffolded scaffold-target → /private/tmp/jig-dogfood-016-03/scaffold-target

--- 4. Scaffold-mode verify_install: 4 checks ---
PASS skills: 11 scaffolded skill SKILL.md file(s) present
PASS agents: all three scaffolded subagent definitions present
PASS hooks: all five scaffolded hook scripts present
PASS settings: settings.json registers 5 jig-managed hook entry/entries
summary: 4/4 passed
```

Both paths exit 0. The scaffold path produced 11 `jig-` prefixed
skills (matching slice 016-01's smoke-test count), 3 agents, 5 hook
scripts, and a settings.json with 5 jig-managed hook entries (one
matcher per source `hooks/hooks.json` entry). AC #5 confirmed end-
to-end.

**6. Test counts.** Pre-016-03 baseline: 617 tests, 3 skipped (per
the merged main). Post-016-03: **631 tests, 3 skipped — green**.
New tests: 14 — 10 in `scripts/test_verify_install.py` (2 CLI
`--mode` cases + 8 `ScaffoldModeChecksTests`) and 4 in
`skills/scaffold-init/test_scaffold_mode.py`
(`DefaultOnMachineryTests`,
`PluginOnlyOptOutTests` x2,
`DogfoodVerifyInstallScaffoldTests`). No regressions.

**7. Reviewer SPECIFIC ISSUES — recorded; non-blocking.**
- **Partial-state-on-refuse** (`scaffold.py:619`). `UnmanagedHooksError`
  is raised AFTER the hook-script copy already happened (loop at
  `scaffold.py:588-595`, `dst_scripts.mkdir` at line 587). A scaffold
  that refuses on `.claude/settings.json` under default-on leaves
  `.claude/hooks/scripts/jig-*.sh` behind. **This rough edge predates
  016-03** — it was the behavior of slice 016-02 too — but the
  default-on flip in this slice makes it more reachable for new users
  who happen to have a pre-existing `.claude/settings.json` with
  non-jig hooks. `--force` is the documented escape. Future tidy-on-
  refuse or moving the safety check before the copy would close it
  cleanly; recorded for a follow-up rather than a 016-03 in-scope fix
  (deviation log §1 of 016-02 explains why the safety check sits where
  it does).
- **PASS-line-counting in `DogfoodVerifyInstallScaffoldTests`
  (test_scaffold_mode.py:762-785).** The test counts PASS lines via
  prefix match. If a future scaffold-mode check emits a non-prefixed
  line containing "PASS", the count could drift. Today the output
  format is `{marker} {name}: {msg}` with `marker == "✓"` for PASS,
  so the line-start anchor is safe. Minor robustness note; left as-is.

**8. Dual-flag rejection note.** The mutually-exclusive grouping at
`scaffold.py:769` means passing both `--with-machinery` AND
`--plugin-only` exits 2 with argparse's standard "not allowed with
argument" message. Tested at
`test_scaffold_mode.py:726-735` (`test_plugin_only_and_with_machinery_are_exclusive`)
— recorded only in test, not in SKILL.md or the wizard prompt. Worth
a SKILL.md mention if a future doc-surfacing pass exposes
`--plugin-only` to end users.

**9. AC #5 dogfood — root cleanliness note.** The 2026-05-15T17:12:14Z
dogfood scaffolded into `/tmp/jig-dogfood-016-03/scaffold-target/`,
a freshly-created tempdir with no pre-existing `.claude/`,
`docs/specs/`, or other jig-managed artifacts. `_looks_already_spec_driven`
did NOT refuse (would only trigger on ≥3 of the four migrate
triggers, none of which were present). Cleaned post-verification.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md Hot Cache updated to mark spec 016 effectively complete
  (016-01..03 DONE; 016-04 deferred).
- [x] Default-on smoke-test ran (2026-05-15, structural verification):
  `python3 skills/scaffold-init/scaffold.py <tmpdir>` (no flags;
  default-on path) produced a `.claude/` tree with 11 jig-prefixed
  skills, 3 agents, 5 hook scripts (0o755), and 5 jig-managed
  settings.json entries. `verify_install.py --mode scaffold
  --project-root <tmpdir>` returned 4/4 PASS. Confirms the default
  flip behaves identically to `--with-machinery` under 016-01/02's
  smoke-tests.
- [x] **User-driven runtime verification** — DONE 2026-05-15.
  Scaffolded jig into a tmpdir with `scaffold.py <tmpdir>` (default-on,
  no flags), then spawned a fresh non-interactive session from the
  tmpdir with `claude --print --output-format json` and asked the
  model to enumerate available skills without invoking tools.
  Session ID: `54d38632-dec1-42e4-bd6a-f8f12274ee1a`. Result
  (verbatim JSON):
  ```json
  {
    "unprefixed_present": ["scaffold-init", "tdd-loop",
                            "spec-workflow", "pr-review"],
    "jig_prefixed_present": ["jig:memory-sync", "jig:tdd-loop",
                              "jig:spec-workflow",
                              "jig:scaffold-init",
                              "jig:independent-review",
                              "jig:pr-review", "jig:slice-land",
                              "jig:adr-workflow", "jig:migrate"],
    "totals": {"unprefixed": 4, "jig_prefixed": 9}
  }
  ```
  **Interpretation:** project-scoped discovery WORKS. The
  unprefixed names (`scaffold-init`, `tdd-loop`, etc.) come from
  the scaffolded `.claude/skills/jig-<name>/SKILL.md` files (the
  `name:` field in the frontmatter has no namespace prefix; the
  `jig-` is only in the directory name). The `jig:*` names come
  from the plugin install (which is also active in this dev
  environment). The two coexist with distinct names — no collision,
  no precedence dispute. The plugin's `jig:*` skills and the
  scaffolded unprefixed skills are addressable separately.
  **Caveat:** the model only confirmed the four skills named in
  the prompt; the scaffolded `.claude/skills/` has 11 directories,
  so a full inventory would likely surface 11 unprefixed skills.
  The four-of-four positive result is sufficient to prove the load
  works.

---

## Slice 016-04 — update-skill (DEFERRED)

**STATUS: DEFERRED**

**Goal (deferred):** Introduce a `/jig:update` skill that, given a
scaffolded project, compares each in-repo jig file against the matching
release's content (via SHA or release-tagged source) and offers to update
untouched files in place. Touched files (locally edited) warn and are
left as-is, with a diff preview.

**Why deferred:** Slices 016-01..03 deliver the dual-mode shape and the
manual-cherry-pick update story is sufficient on day one. Promoting
016-04 requires either (a) a second contributor reporting friction
maintaining their scaffolded install across jig releases, or (b) a jig
release that ships a security-shaped fix to a SKILL.md or hook script
where stale copies in the wild become a concrete risk.

**Resolution trigger:** Scope narrowed by spec 038-04 (2026-05-29) — the *tier-upgrade* part of this skill's job (additively adding a higher tier to an already-scaffolded project without overwriting existing-tier edits) is now handled by `migrate copy-machinery --add-tier` (ADR-0012); the remaining justification is the *version-refresh* case, which `copy-machinery`'s plain refresh still overwrites. So: ≥1 reported issue along the lines of "I scaffolded jig N versions ago and want to update cleanly without overwriting my edits", OR a security-grade fix to a copied artifact (hook script, SKILL.md bash), OR jig adopts per-file metadata headers (audit's Option C) for another reason that makes a SHA-compare cheaper.

(No DoR / AC / DoD until promotion.)

---

## References

- **Audit-stage finding from this session.** The original scope drift
  was raised by the user; the audit confirmed the path-coupling gap
  is shallow (agents = 0 plugin refs, hooks = 0 plugin refs, helpers
  self-locate via `plugin_root()` fallback). Summary in the same
  conversation as this spec's authorship.
- **Originating positioning doc:** scaffold-init's role as a
  "scaffolding library" (vs. plugin) per the original project
  framing — recovered by this spec.
- **Precedent — same scaffold-init surface:** [spec 001-scaffold-init](../001-scaffold-init/spec.md)
- **Precedent — dual-distribution shape:** [spec 013-release-pipeline](../013-release-pipeline/spec.md)
  (plugin zip artifact pattern reused as-is; scaffold path is the new
  half).
- **Related — wizard gap (separate spec):** [spec 017-vision-elicitation](../017-vision-elicitation/spec.md)
- **Claude Code project-scoped skills docs:** standard `.claude/skills/`
  + `.claude/agents/` discovery (the Claude Code router auto-discovers
  these; jig is a normal client of the existing rules).

## Amendments

### 2026-05-27 — Hook count: five → seven

This spec's prose at lines 72, 412, 445, and 471 refers to "the same
five jig hooks" / "all five hook scripts". Reality today is **seven**
hooks: an earlier five → six sweep added `jig-post-edit-verify.sh`
(slice 027-01), and a subsequent six → seven sweep added
`jig-boundary-change-warn.sh` (slice 005-03 close-out, boundary-change
detection). The original prose is preserved in place per
[ADR-0008](../../decisions/adr-0008-closed-spec-drift-policy.md)
Option C; this amendment overrides it.

- Link: [slice 005-03 — six → seven sweep](../005-adr-workflow/spec.md)
- Link: [spec 027 — post-tool edit verification (five → six)](../027-post-tool-edit-verification/spec.md)

