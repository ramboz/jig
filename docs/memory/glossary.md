# Glossary

> Domain terms and project-specific vocabulary. Loaded on demand when the hot cache misses.
> Update via `/jig:memory-sync` or when `jig-memory-scan` surfaces an unknown.

## jig

The skill pack itself. Short for "a jig is a tool that guides other tools."

## SPIDR

Mike Cohn's five story-splitting techniques: Spike, Path, Interface, Data, Rules.
Used to split feature specs into implementable vertical slices. Spike is last resort.

## Tier 0 / Tier 1 / Tier 2

Installation tiers for jig skills:
- **Tier 0**: Always installed (scaffold-init, spec-workflow, independent-review, contracts, memory-sync). Sibling: `migrate` (adopts an existing spec-driven project to jig).
- **Tier 1**: Default for most projects. Built: `adr-workflow` (005), `tdd-loop` (006), `slice-land` (007 + 009 close-out fix), `pr-review` (012), `arch-review` (014). Outstanding candidate: `local-dev-parity` (no signal yet).
- **Tier 2**: Opt-in by signal (eval-harness, e2e-testing, migration-mode, skill-stocktake) — not yet built.

## Hot Cache

The structured section of `CLAUDE.md` for frequently-referenced project terms, people,
codenames, and active specs. Loaded at every session start.

## Dumb zone

The context fill level (~40%) above which model recall and reasoning degrades.
Horthy's term from 12-Factor Agents. Practical ceiling: 8 MCP servers, ~80 active tools.

## Reconciliation

The phase after implementation and review, before marking a slice DONE. Produces a
deviation log, updates architecture.md if module boundaries changed, runs a second
reviewer pass on the doc changes themselves.

## Vertical slice

A spec slice that crosses all layers (DB + service + UI) and delivers end-to-end value.
Contrast with horizontal phasing (DB phase, then API phase, then frontend phase), which
is the AI's default failure mode.

## Scaffolded install / scaffold mode

The second of jig's two install shapes (the other being plugin install). Introduced by
[spec 016-scaffold-mode](../specs/016-scaffold-mode/spec.md). `scaffold-init` (default-on as of slice 016-03; opt out with `--plugin-only`) copies `skills/`, `agents/`, and `hooks/scripts/` into the
target's `.claude/` directory under `jig-` prefixed names (e.g.
`.claude/skills/jig-scaffold-init/SKILL.md`, `.claude/hooks/scripts/jig-context-check.sh`).
SKILL.md path strings are rewritten from `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` to
`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`, and hook command paths from
`${CLAUDE_PLUGIN_ROOT}/hooks/scripts/` to `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`,
both at copy time. `.claude/settings.json` is generated (or merged) with the five jig hooks
registered under `metadata: {managed_by_jig: true}` so re-runs replace-in-place rather than
duplicate. A safety check (`UnmanagedHooksError`) refuses to overwrite settings.json when
hooks exist but none carry the jig marker; `--force` is the escape. The dev owns the in-repo
files — they can edit any SKILL.md or helper, version-control their customizations, and
pick up the original "scaffolding library" positioning. Plugin install via
`/plugin install jig@jig` still works unchanged; project-scoped wins when both are present.

**Naming distinction (worth knowing).** The `jig-` prefix lives on the
**directory** name only (`.claude/skills/jig-scaffold-init/`,
`.claude/agents/jig-reviewer.md`); the SKILL.md frontmatter `name:` field
is left untouched at copy time, so Claude Code surfaces the scaffolded
copies as **unprefixed** skills (`scaffold-init`, `tdd-loop`, etc.). The
plugin-installed versions are namespaced as `jig:scaffold-init`,
`jig:tdd-loop`, etc. So a dev with BOTH installs sees two non-colliding
sets — `/scaffold-init` (their owned, editable copy) and
`/jig:scaffold-init` (the upstream plugin version) address different
files. Confirmed empirically in slice 016-03 deviation log §close-out
runtime verification (session
`54d38632-dec1-42e4-bd6a-f8f12274ee1a`).

## DEFERRED

A spec-lifecycle state added in slice 015-02. A slice marked `DEFERRED` was scoped
but parked — the work is identified but not the current priority. Different from
`DRAFT`, which means "not yet fleshed out." Outbound transitions are restricted:
`DEFERRED → DRAFT` (re-open) only; all other targets are refused so review gates
aren't silently skipped when a parked slice is picked back up. This is the **first
FROM-state-restricted transition** in jig's lifecycle.

## Resolution trigger

A line (`**Resolution trigger:** <condition>`) under a deferred slice or a deferred
decision describing the concrete signal that would justify re-opening it. The
status board's `## Deferred slices` section renders this as the per-row context
(slice 015-02). The same convention is reused from `docs/refinement-todo.md`.

## Lazy migration

Convention introduced by slice 015-01: when a layout change is introduced (here,
frontmatter on slices), parsers tolerate both old and new shapes indefinitely;
only newly authored items use the new shape. No mass rewrite of existing items.
Tradeoff: long-lived support for two shapes; benefit: zero high-churn migration
diff and zero risk of garbling rare existing variants.

## Conjunctive staleness

The criterion used by `workflow.py stale` (slice 015-03): an item is stale iff
BOTH `(today - last_verified) > --days` AND at least one file in `dependencies`
has been modified since `last_verified`. Pure age alone or pure dep-recency alone
is not enough.
