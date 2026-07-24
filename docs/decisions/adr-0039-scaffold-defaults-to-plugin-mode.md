---
status: Proposed
dependencies: [adr-0013]
last_verified: 2026-07-24
frame_review: true
---

# ADR-0039: scaffold-init defaults to plugin mode

## Status

Proposed (2026-07-24)

This record reverses a default set by [spec 016-03](../specs/016-scaffold-mode/spec.md)
and is implemented by [spec 096](../specs/096-scaffold-default-plugin-mode/spec.md).
It starts `Proposed`; because it reverses a framing decision it carries
`frame_review: true`, so `adr.py accept` will not flip it to `Accepted` without a
passing frame-critique verdict (ADR-0020). Provenance: reported by Marie-Rose on
[issue #127](https://github.com/ramboz/jig/issues/127); the ADR-plus-spec route
was her call.

## Context

jig has two scaffold topologies, selected by one axis in `scaffold.py`:

- **plugin mode** (`scaffold_mode: "plugin-only"`) — scaffold writes only the
  docs tree and the host primer. Skills, agents, hooks, and templates stay under
  the installed jig plugin and run from `${CLAUDE_PLUGIN_ROOT}`.
- **in-repo mode** (`scaffold_mode: "in-repo"`) — scaffold additionally *copies*
  jig's machinery into the project's `.claude/` (skills, agents, hooks,
  templates, a generated `settings.json`), so the project is self-contained and
  needs no installed plugin.

Spec 016-03 flipped the default from plugin mode to **in-repo** and pinned it
with `test_default_includes_machinery`. So today a no-flag scaffold copies jig's
whole machinery into the target. In one real scaffold that was **79 tracked
files** (21 skills, 19 hooks, agents, `_common` helpers) — about half the repo's
tracked files, dwarfing the actual project.

For the common case — a solo or personal project on a machine where the jig
plugin is already installed — that is the wrong default, for four reasons:

1. **Two sources of truth / silent drift.** The copied machinery is pinned to the
   jig version at scaffold time and never updates with the installed plugin. The
   project diverges from jig with no signal.
2. **Repo pollution.** Vendored tooling dominates the file count, every diff, and
   every `git log`. Reviews and history are mostly jig internals, not the project.
3. **Ownership ambiguity.** The user now holds editable copies of jig's internals.
   Are edits customizations or stale copies? There is no answer in the tree.
4. **The heavier choice, taken silently.** in-repo is a real commitment
   (self-contained, no plugin dependency). Defaulting to it for a project that
   *has* the plugin inverts the principle of least surprise.

in-repo genuinely serves cases where the plugin cannot be assumed present — CI or
cloud agents running a bare checkout, teams where not every contributor has jig
installed, fully self-contained or archival repos. The problem is not that in-repo
exists; it is that it is the **silent default**. And the axis is undiscoverable:
the `scaffold-init` Q&A lists five *content* questions (runtime, team, CI, tests,
LLM/AI) and never surfaces the machinery-vs-plugin choice, which is architectural
(repo topology, what gets committed) and appears in no project's own docs. So an
operator following the skill never sees the choice and silently accepts in-repo.

### Why 016-03 chose in-repo, and why that reasoning has narrowed

016-03's driving goal was **dogfooding**: jig itself, and early adopters, needed a
scaffold that fully wired up `.claude/` — hooks registered, settings written — so
the workflow could be exercised end-to-end without a separately-installed plugin.
At that stage jig was not yet distributed as a stable plugin, so "copy everything
in" was the only way to get a working install. That constraint has since lifted:
jig ships as a versioned Claude plugin (`.claude-plugin/plugin.json`, currently
2.8.0) whose own `hooks/hooks.json` registers every gate globally from
`${CLAUDE_PLUGIN_ROOT}`. The mode that 016-03 needed to *manufacture* now exists
by installing the plugin. What remains correct about 016-03 is that in-repo must
stay a first-class, fully-wired mode — this ADR keeps it exactly, behind a flag.

### What plugin mode does and does not provide (the security-floor question)

Flipping the default raises one real question: does a no-flag scaffold still get
jig's security floor (ADR-0013)? Probed against `hooks/hooks.json` and the
`scaffold()` plugin-only branch:

| Floor part | in-repo | plugin mode | Source in plugin mode |
|---|---|---|---|
| `.gitignore` secret patterns | ✅ | ✅ | scaffold writes it in **both** modes (`_write_gitignore_secret_block`) |
| secret-scan hook (`jig-secret-scan.sh`) | ✅ copied + registered in project `settings.json` | ✅ **runs from the plugin** | plugin `hooks/hooks.json` `Edit\|Write\|MultiEdit` |
| spec-gate / context-check / other gates | ✅ copied | ✅ **run from the plugin** | plugin `hooks/hooks.json` |
| `## Security (MUST)` primer block | ✅ | ✅ | primer template, written in both modes |
| `permissions.deny` guardrails (force-push / `rm -rf` / hard-reset) | ✅ written to project `settings.json` | ❌ **not written** | — (no plugin mechanism injects project `permissions`) |

So four of the five floor parts hold in plugin mode — the hooks come from the
installed plugin, and the `.gitignore` floor is written regardless. The **one**
part plugin mode does not seed is the `permissions.deny` block, because a plugin
cannot write entries into a project's `settings.json permissions`. This is **not
a regression introduced here** — it is the pre-existing behavior of the
already-shipped `--plugin-only` path (spec 052-04 deliberately routed only the
`.gitignore` floor onto that path, not the settings write). This ADR changes which
mode is the default, not what plugin mode does. The consequence is that more
projects will, by default, lack the `permissions.deny` guardrails; whether plugin
mode *should* also seed them is left as an open question below rather than folded
into this change.

## Decision Options Considered

### Option A: Default to plugin mode; in-repo behind an explicit `--in-repo`
Flip `with_machinery` to default `False`. Add `--in-repo` (with `--with-machinery`
and `--copy-machinery` as aliases) as the deliberate opt-in. Keep `--plugin-only`
(now redundant with the default) for clarity and back-compat. Surface the axis as
a sixth Q&A question, and have the wizard summary name the chosen mode and why.

- **Pros:** The lean topology is the default for the common (plugin-installed)
  case, eliminating silent drift, pollution, and ownership ambiguity. in-repo
  becomes the deliberate choice its weight deserves. The axis is discoverable in
  both the Q&A and the summary. Minimal code change — the off-switch already
  exists; this flips which side is the default and renames the opt-in for clarity.
- **Cons:** Reverses a pinned 016-03 default, so its tests must invert and the
  many machinery-exercising tests must pass `--in-repo` explicitly. A no-flag
  scaffold no longer seeds `permissions.deny` (see the floor table). Existing
  automation that relied on the implicit in-repo default must add a flag.

### Option B: Keep in-repo default; only add the sixth question + summary
Leave the default as in-repo; make the axis discoverable via the Q&A and summary,
so at least the operator is prompted before accepting the heavy mode.

- **Pros:** No test inversion; no behavior change for existing callers. Addresses
  the pure *discoverability* complaint.
- **Cons:** Does not address the core objection — the heavy mode stays the default
  and stays taken by anyone who skips the question. "Principle of least surprise"
  is unfixed; a skipped question still lands in-repo. The four structural
  problems (drift, pollution, ownership, silent heaviness) remain the out-of-box
  reality for most projects.

### Option C: Per-host default (plugin for Claude, in-repo for Codex)
Flip the default only for the Claude host, leaving Codex on in-repo.

- **Pros:** Smaller Codex test churn.
- **Cons:** The in-repo-vs-plugin axis is host-independent, and the four
  objections apply identically to a Codex project whose plugin is installed. A
  split default is a surprising inconsistency that the ADR would have to justify
  on grounds that do not exist. It also complicates the mental model and the
  summary ("why did the same command choose differently here?").

## Recommended Decision

**Option A**, applied to **both hosts**. The change is small where it counts (one
default, one new flag name, one summary line, one Q&A question) and the reversal
is proportionate: 016-03's in-repo default solved a problem — no installable
plugin — that no longer exists. in-repo stays a fully-wired, first-class mode; it
just stops being the silent default. The default now matches the common case
(plugin installed) and the principle of least surprise (the lean topology is the
unsurprising one; the heavy, self-contained commitment is opt-in).

The record is explicit that Option A is not free: it accepts the `permissions.deny`
gap in the default path (Open questions), and it forces every machinery-exercising
test and any in-repo-dependent automation to name `--in-repo` rather than rely on
the implicit default.

## Consequences

**Becomes easier:**
- The common case: a plugin-installed project scaffolds lean, and jig updates flow
  from the plugin with no drift.
- Reviewing and reasoning about a scaffolded repo — its history and diffs are the
  project's, not jig's internals.
- Choosing in-repo *deliberately*, for the cases that need it (CI, cloud agents,
  plugin-less teammates, archival), with the summary stating which mode ran and why.

**Becomes harder:**
- Anyone (or any script) that relied on the implicit in-repo default must now pass
  `--in-repo`. The wizard summary and the sixth Q&A question mitigate the
  interactive case; automation is on its own and must be updated.
- The default path no longer seeds `permissions.deny` guardrails (see the floor
  table); a project wanting them either opts into in-repo or adds them by hand.

## Assumptions

Probed on this branch (`main@fd7115a`), not asserted:

- **The plugin registers every gate globally.** `hooks/hooks.json` at the plugin
  root registers `jig-secret-scan.sh`, `jig-spec-gate.sh`, `jig-context-check.sh`,
  and the rest under `${CLAUDE_PLUGIN_ROOT}` — so in plugin mode the hooks run
  from the installed plugin, not from a per-project copy. This is what makes the
  floor table's "runs from the plugin" rows true.
- **plugin mode already writes the `.gitignore` floor and omits the settings
  write.** The `scaffold()` `else` (plugin-only) branch calls
  `_write_gitignore_secret_block`, `_ensure_self_defining_convention_block`, and
  `_ensure_reframe_practice_block`, and does **not** call `copy_machinery` — so no
  `settings.json` and no `permissions.deny` on that path. The default flip inherits
  this branch unchanged; it introduces no new plugin-mode behavior.
- **The off-switch already exists.** `--plugin-only` (dest `with_machinery`,
  `store_false`) has shipped since 016-03; this ADR flips the group's default and
  adds `--in-repo`/`--copy-machinery` as `store_true` aliases of the existing
  `--with-machinery`. No new copy/skip machinery is written.

## Kill criteria

- **The plugin stops registering the gates globally.** If a future change moves
  hook registration out of the plugin's `hooks/hooks.json` (e.g. hooks become
  per-project-only), plugin mode would silently lose the secret-scan and spec-gate
  floor, and defaulting to it would be unsafe. *Detector:* the plugin manifest /
  `hooks/hooks.json` no longer lists `jig-secret-scan.sh`.
- **plugin mode proves too lean to be usable out of the box.** If real adopters
  routinely hit "jig doesn't work here" because they scaffolded plugin mode without
  the plugin installed, the default is wrong for the population and in-repo should
  return (or a detect-plugin-presence default should replace this static one).
  *Detector:* repeated reports of plugin-mode scaffolds in plugin-less environments.

## Open questions

- **Should plugin mode also seed `permissions.deny`?** The one floor part plugin
  mode does not provide is the destructive-command guardrail, because it lives in
  the project's `settings.json` and no plugin mechanism injects it. Writing just
  the `permissions.deny` block (without the rest of the machinery) onto the
  plugin-only path would close the gap without reintroducing pollution, but it
  changes what plugin mode does and so is deliberately **out of scope** for this
  ADR. Tracked for a follow-up decision; if taken, it should reuse the existing
  `_merge_settings` / `_PERMISSIONS_DENY_DEFAULTS` path, guarded so it does not
  drag the hook copy or skills along with it.
- **Should the default eventually be *detected* rather than static?** A smarter
  default would pick in-repo when no jig plugin is detected and plugin mode when it
  is. That needs a reliable plugin-presence probe from inside the scaffold, which
  does not exist today; a static plugin-mode default is the honest floor until it
  does.
