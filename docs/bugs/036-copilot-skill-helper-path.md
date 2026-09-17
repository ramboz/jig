---
status: DONE
tier: standard
severity: high
claimed_by: copilot-plugin-audit
regression_test: skills/scaffold-init/test_copilot_renderer.py::CopilotPluginModeHelperPathTests
main_repro_checked_at: 2026-09-17
main_repro_ref: origin/main@297465a
main_repro_result: reproduces
red_confirmed_at: 2026-09-17
green_confirmed_at: 2026-09-17
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 036: copilot-skill-helper-path

## Symptom

Every jig skill shipped in the **Copilot plugin package** documents its helper
invocation as a *project-relative* path, e.g.

    python3 ".github/skills/spec-workflow/workflow.py" new <slug>

In plugin mode (the default `scaffold_mode: plugin-only`) the scaffolded
project has no `.github/skills/` directory — the machinery lives in the
installed plugin. The documented command therefore resolves against the
project cwd and fails with `No such file or directory`.

Claude renders `${CLAUDE_PLUGIN_ROOT}/skills/...` and Codex renders
`${PLUGIN_ROOT}/skills/...`; both are absolute and correct. Copilot is the
only host whose own documented commands do not run.


## Repro

1. Scaffold a clean repo from the installed Copilot plugin (v2.15.2):
   `python3 ~/.copilot/installed-plugins/jig/jig/.github/skills/scaffold-init/scaffold.py .`
2. From the project root run the command the shipped SKILL.md documents:
   `python3 ".github/skills/spec-workflow/workflow.py" new demo-feature`

Observed: `can't open file '<proj>/.github/skills/spec-workflow/workflow.py':
[Errno 2] No such file or directory`.
Expected: the spec is reserved, as on Claude/Codex.


## Evidence

- `ls .github/` in a scaffolded project: only `workflows/` — no `skills/`.
- Live Copilot session asked to follow spec-workflow verbatim reported:
  *"There's no `.github/skills/spec-workflow/` in this project"* and only
  proceeded by **independently hunting** for the installed plugin path. The
  recovery is a model heuristic, not a contract.
- `env | grep -i plugin` inside a live Copilot session: **no plugin-root
  variable of any kind** is exported (no `COPILOT_PLUGIN_ROOT`).
- Once given the correct absolute path, every helper works:
  `workflow.py new` reserved `003-demo-feature`, `workflow.py orient` and
  `bug.py new` both succeeded. The helpers are sound; only the documented
  path is wrong.
- Hooks are unaffected: hook commands are executed *by the host* and do
  resolve against the plugin root, which is why the earlier live hook probes
  passed and masked this.
- Scope: 13 SKILL.md files, 88 occurrences of `python3 ".github/skills/...`.
- Host discloses the skill's absolute directory on invocation (verified live:
  a session reported `/Users/ramboz/.copilot/installed-plugins/jig/jig/.github/skills/tdd-loop`),
  so a deterministic plugin-mode spelling is achievable.


## Hypotheses

- [ ] H1: Copilot exports an undocumented plugin-root env var that the
  relative path implicitly relies on. **Falsified** — `env` in a live session
  shows no such variable.
- [ ] H2: Copilot resolves *all* plugin-authored relative paths against the
  plugin root, so the spelling is fine. **Falsified** — true only for
  host-executed hook commands; agent-issued bash runs with cwd = project, and
  the documented command fails there.
- [x] H3 (leading): the 113-04 AC4 rewrite generalized the *hook* path
  semantics to skill bodies, and the Copilot renderer never grew the
  plugin-mode/in-repo split that the Codex renderer has. **Confirmed** —
  `CopilotScaffoldRenderer.rewrite_doc_paths_plugin_mode` simply delegates to
  the in-repo `rewrite_skill_md_paths`.


## Root cause

`CopilotScaffoldRenderer` has **one** path rendering, the in-repo one
(`SKILL_PATH_REPLACEMENT = r".github/skills/\1/"`), and its plugin-mode entry
point is a pass-through:

    # skills/scaffold-init/scaffold.py:2267
    @classmethod
    def rewrite_doc_paths_plugin_mode(cls, body: str) -> str:
        return cls.rewrite_skill_md_paths(body)

`CodexScaffoldRenderer` solved exactly this with a mode-parameterized
`_rewrite_host_paths(body, plugin_mode=bool)` selecting between
`PLUGIN_SKILL_PATH_REPLACEMENT` (`${PLUGIN_ROOT}/skills/\1/`) and the
project-local replacement. The Copilot renderer was never given that split.

`scripts/build_copilot_plugin.py:263` then applies the **in-repo** rewrite
unconditionally while building the plugin package — a package that is
plugin-mode by definition — so the shipped skills document a path that only
exists in the `--in-repo` layout.

Compounding it, the renderer substitutes prose that *asserts the broken
behaviour is correct*: "Copilot does not expose a plugin-root environment
variable for skill-issued commands; use the packaged `.github/...` relative
paths shown above." The first clause is true; the conclusion does not follow.

Scope note (grounding, ADR-0052): the 88 sites were enumerated by matching the
single generated spelling `python3 ".github/skills/<skill>/<helper>.py"` across
`hosts/copilot/.github/skills/`. That set is closed because every one of those
strings is *emitted by* `SKILL_PATH_REPLACEMENT` — the generator is the only
writer, so regenerating fixes all of them by construction.


## Repository closure inventory

**Equivalent / convergent logic searched:** `grep -rn "rewrite_skill_md_paths"`
and `"rewrite_doc_paths_plugin_mode"` across the repo; `grep -n` for
`SKILL_PATH_REPLACEMENT` / `PLUGIN_SKILL_PATH_REPLACEMENT` / `PLUGIN_ROOT_PREFIX`
in `skills/scaffold-init/scaffold.py`. Found the convergent implementation:
`CodexScaffoldRenderer._rewrite_host_paths(plugin_mode=...)` (scaffold.py:1286)
already models the required mode split. This is a **reuse-the-pattern** case,
not a new mechanism.

**Relevant history inspected:** `git log -S rewrite_skill_md_paths` →
`dc8d453` (spec 113, introduced the Copilot renderer and the 113-04 AC4
rewrite) and `3e6faff` (bug 034, narrowed the `.claude/`→`.github/` rewrite).
Neither added a plugin-mode variant; 113-04's own comment claims the rewrite
targets "the plugin-root-relative Copilot spelling", which is the false premise.

**Affected call sites:**
- `skills/scaffold-init/scaffold.py:2267` — `rewrite_doc_paths_plugin_mode`
  pass-through (the defect).
- `skills/scaffold-init/scaffold.py:2242` — in-repo `rewrite_skill_md_paths`
  (correct for `--in-repo`; must keep working).
- `skills/scaffold-init/scaffold.py:2246-2255` — the prose substitution that
  documents the broken rule.
- `scripts/build_copilot_plugin.py:263` and `:867` — unconditional in-repo
  rewrite during plugin-package build.
- `skills/scaffold-init/scaffold.py:3784` — mode dispatch that already selects
  the right entry point; correct once the plugin-mode branch is real.
- Generated: 13 `hosts/copilot/.github/skills/*/SKILL.md` (88 occurrences),
  regenerated by `scripts/build_host_packages.py`.

**Reuse decision:** reuse the Codex `_rewrite_host_paths(plugin_mode=...)`
shape rather than adding a parallel mechanism, so the two hosts' mode handling
cannot drift. No duplication introduced.


## Fix class

## Fix

Gave `CopilotScaffoldRenderer` the mode split the Codex renderer already had,
and pointed the plugin builder at the plugin-mode entry point.

1. `CopilotScaffoldRenderer._rewrite_host_paths(body, *, plugin_mode)` — one
   body for the host-vocabulary rules, parameterized only on where the runtime
   lives. `rewrite_skill_md_paths` (in-repo) and `rewrite_doc_paths_plugin_mode`
   (plugin) are now thin callers, mirroring `CodexScaffoldRenderer`.
2. Plugin-mode root is `$JIG_ROOT`. The canonical source spells invocations
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/…"`, so substituting the prefix alone
   yields `python3 "$JIG_ROOT/skills/…"` — still inside the original quotes,
   so still space-safe.
3. `scripts/build_copilot_plugin.py` now renders SKILL.md bodies with
   `rewrite_doc_paths_plugin_mode` — the package *is* plugin mode.
4. `scripts/jig_root.py` — the fresh-shell locator, added to
   `COPILOT_INCLUDE_SCRIPT_FILES` so it ships at `.github/scripts/jig_root.py`.
   In-repo machinery wins; otherwise install roots are scanned for a
   `.plugin/plugin.json` naming `jig`, highest version first (the marketplace
   path segment is user-controlled, so the manifest is the only stable key).
5. `copilot_hook_adapter.py` publishes the root on `SessionStart` from exactly
   one carrier (`jig-project-orient.sh`), **merging** into that hook's own
   `additionalContext` so the orientation line survives. Fail-open: an
   unparseable or absent child body still yields a valid single JSON object.
6. `_ensure_root_note` injects the resolution note into every plugin-mode skill
   that references `$JIG_ROOT`, so a skill read in isolation defines the
   variable it uses. Idempotent.

Hook commands are deliberately untouched: they are executed by the host and
correctly resolve `.github/...` against the plugin root.


## Call-site closure

**Disposition per affected site:**

- `scaffold.py:rewrite_doc_paths_plugin_mode` — **changed** (was the
  pass-through defect; now a real plugin-mode branch).
- `scaffold.py:rewrite_skill_md_paths` — **changed shape, same behaviour**;
  still the in-repo transform, covered by
  `test_in_repo_mode_still_uses_project_relative_path`.
- `scaffold.py` prose substitution — **changed**: mode-specific note; the
  plugin-mode text no longer asserts that relative paths resolve.
- `build_copilot_plugin.py:263` (SKILL.md render) — **changed** to plugin mode.
- `build_copilot_plugin.py:867` (`.md.template` render) — **changed.** This was
  first recorded as "intentionally left alone" on the theory that `scaffold.py`
  re-renders templates per mode at scaffold time. That reasoning was wrong and a
  live scaffold falsified it: because the builder had *already* rewritten the
  template to the in-repo `.github/...` spelling, the scaffold-time mode
  dispatch had nothing left to act on, and a plugin-mode project emitted
  `python3 ".github/skills/memory-sync/decisions.py"` — the same unresolvable
  path this bug is about, in a second artifact. Both review passes flagged it
  independently. Fixed by shipping `.md.template` files **canonical**
  (`${CLAUDE_PLUGIN_ROOT}` intact), which restores the mode dispatch and matches
  the builder's own docstring. Verified live in both modes: plugin-mode renders
  `$JIG_ROOT/skills/memory-sync/decisions.py`, in-repo renders
  `.github/skills/memory-sync/decisions.py`. Guarded by
  `test_templates_ship_canonical_so_scaffold_can_render_per_mode`.
- `scaffold.py:JIG_ROOT_VAR_ASSIGNMENT` (fresh-shell bootstrap) — **changed**
  after review: honours `COPILOT_HOME` (the same override the locator reads, so
  the two agree) and iterates a quoted glob instead of parsing `ls`, so an
  install path containing spaces resolves. Guarded by
  `JigRootBootstrapCommandTests`.
- `jig_root._install_roots` — **changed** after review: a manifest that is valid
  JSON but not an object is skipped rather than raising `AttributeError`.
- `install_contract.COPILOT_INCLUDE_SCRIPT_FILES` — **changed** (ships locator).
- 13 generated `hosts/copilot/.github/skills/*/SKILL.md` — **regenerated**;
  0 remaining project-relative helper invocations, all 13 carry the note.
- Claude / Codex packages — **left alone by design**; both already have a
  working plugin-root variable. Drift check confirms they are byte-identical
  apart from the shared source changes.


## Already tried

## Regression test

`skills/scaffold-init/test_copilot_renderer.py::CopilotPluginModeHelperPathTests`
(+ `CopilotPluginModeHelperPathTests` note/idempotence cases,
`test_copilot_hook_adapter.py::JigRootPublicationTests` /
`::JigRootLocatorTests`, and
`test_build_copilot_plugin.py::test_every_documented_runtime_path_resolves_in_the_package`).

Witnessed **red** before the fix (3 failures, incl. the packaged-tree guard)
and **green** after, by the `bug.py` gate.


## Proof

Live, against the rebuilt package installed into an isolated `COPILOT_HOME`:

- `SessionStart` publishes the root **and** preserves the carrier's own line:
  `jig hint: Scaffolded jig project · active specs: 003 DRAFT · focus: 003-01 DRAFT`
  `jig runtime root: JIG_ROOT=<plugin>/.github — jig skills document helper commands as …`
- A live agent asked to follow spec-workflow "exactly as documented" resolved
  `$JIG_ROOT` from session context unaided and issued the correct absolute
  command — the pre-fix run instead reported *"There's no
  `.github/skills/spec-workflow/` in this project"* and had to hunt for the path.
- Helper execution at the normal installed-plugin path succeeds:
  `python3 "$HOME/.copilot/installed-plugins/jig/jig/.github/skills/spec-workflow/workflow.py" orient`
  → exit 0, `jig hint: Scaffolded jig project · active specs: 003 DRAFT …`
- Locator resolves under an isolated home and prefers in-repo machinery.
- Static: 0 of 88 project-relative helper invocations remain; 13/13 skills
  define `$JIG_ROOT`; `build_host_packages.py --check` reports in sync.

Test suites: `skills/scaffold-init` 539 passed; `scripts/` 1127 passed.


## Learning

## Main recheck

- 2026-09-17 - `origin/main@297465a` -> reproduces: git show origin/main:hosts/copilot/.github/skills/spec-workflow/SKILL.md | sed -n 184p  =>  python3 ".github/skills/spec-workflow/workflow.py" new <slug>  (path absent in a plugin-mode project; python3 exits Errno 2)
