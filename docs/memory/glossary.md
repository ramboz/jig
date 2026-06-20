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
both at copy time. `.claude/settings.json` is generated (or merged) with the seven jig hooks
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

## git-common-dir

The shared `.git/` directory used across all worktrees of the same
project, resolved via `git rev-parse --git-common-dir`. For the main
repo, this equals `.git/`; for secondary worktrees, the secondary's
`.git` is a file pointing to `.git/worktrees/<name>/` but the
common-dir is still the main `.git/`. Useful as a cross-worktree
synchronization surface (e.g. `.git/jig-locks/` for file locks shared
across parallel sessions; see slice 028-02).

## Closed-spec drift
When a closed (DONE or SUPERSEDED) spec's prose no longer matches reality because the code/process evolved around it. Governed by [ADR-0008](../decisions/adr-0008-closed-spec-drift-policy.md): default to a `## Amendments` section appended to the drifted artifact; escalate to a new ADR (or superseding spec) when the delta is decision content (a contract, interface, or behavior the spec committed to). Scope: DONE and SUPERSEDED specs plus load-bearing skill/router prose. Excludes IN_PROGRESS, REVIEWED, RECONCILED, DEFERRED.

## ## Amendments section
The dated-entry append-only section ADR-0008 establishes for correcting drift in closed specs and load-bearing skill/router prose. One H2 `## Amendments` block at the end of the drifted artifact; each entry is `### YYYY-MM-DD — <one-line summary>` heading + body explaining what changed and why + a link to the slice/ADR/PR that caused the drift. In-body edits to the original prose remain forbidden. Mirrors deviation-log discipline.

## Cold-start cliff
The failure mode where a freshly scaffolded jig project skips the spec-driven workflow and review gates. jig enforces almost nothing via hooks (only the conventions.md spec-gate blocks); adherence relies on advisory skill/doc prose PLUS the gravitational pull of existing spec artifacts as a few-shot pattern. A blank scaffold has neither enforcement nor examples, so the model just codes. Mature repos (e.g. servo) follow the workflow because their populated docs/specs act as a worked example. Addressed by spec 048-05 (seed reference spec) + 048-06 (scaffold-completion verification).

## install_contract.py
scripts/install_contract.py — the single validator-facing plugin/release install contract (spec 047-01). Stdlib-only, pure (ok, [diagnostics]) helpers: EXPECTED_SKILLS (restated == scaffold._TIER_SKILLS union, pinned by a consistency test), REQUIRED_AGENTS, hook-command shape validation derived from hooks/hooks.json (enforces 'bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>', no bare names, script exists), manifest field/path rules (plugin.json + marketplace.json incl. relative source.path), and is_excluded_release_path. Consumed by validate_manifests.py, verify_install.py plugin mode (check_hook_contract + full-skill-set check), and test_build_release_zip.py smoke. Slice 047-02 reuses it for the scaffold-target contract.

## scaffold_contract.py
scripts/scaffold_contract.py — the single validator-facing scaffold-target contract (spec 047-02), sibling to install_contract.py (047-01's plugin/release contract). Stdlib-only, pure (ok, [diagnostics]) helpers for a generated .claude/ tree: expected_scaffold_skills (tier-gated via scaffold.json installed_tiers/installed_skills; tier tables restated + consistency-pinned to scaffold._TIER_SKILLS), scaffold_skill_problems (helper closure + stale-${CLAUDE_PLUGIN_ROOT}/skills/ path detection), validate_scaffold_settings (settings.json hook coherence; reuses install_contract._iter_hook_commands), validate_scaffold_manifest (scaffold.json fields incl. jig_version), scaffold_doc_problems (broken local helper commands / missing markdown links). Wired into verify_install.py scaffold mode (check_scaffold_skill_closure/manifest/docs).

## frame-critique
jig's adversarial, PRE-implementation review pass (spec 064 / ADR-0020): a fresh reviewer hunts the single load-bearing assumption in a spec/ADR most likely to be WRONG — explicitly NOT a conformance check. Gated on a truthy `frame_review` flag (derived from the spec's `## Assumptions` via `workflow.py frame-review-needed`); runs at READY_FOR_REVIEW for specs and at `adr.py accept` for ADRs (ADRs always-on). Equal-or-stronger model policy — never downgraded for cost. Built by `review.py frame-critique`; verdict at `reviews/slice-NN-frame-critique.md` (specs) or `docs/decisions/reviews/adr-NNNN-frame-critique.md` (ADRs).

## test-scope taxonomy
EngTip #21's five test *types*, distinguished by **scope** (how much of the system each exercises), used as a shared vocabulary so "do we have enough tests?" becomes answerable. (1) **Unit** — a single operation in a single component; fast, hermetic, dependencies doubled. (2) **Component** — multiple operations within one component, verifying its invariants as a stateful whole. (3) **Seam-integration** — exactly one component against exactly one real dependency across a boundary, verifying the doubled contract actually holds (the type most often missing). (4) **System-integration** — several components together (service + DB + downstream). (5) **End-to-end** — a full user journey across the stack; highest fidelity, poorest at localizing failure. The point isn't a coverage number (gameable) but a checklist for finding gaps and assigning ownership. jig currently tracks *artifact* coverage (`workflow.py coverage`, use-cases), not test-scope coverage — parked as an [inbox](../inbox.md) item, not a spec, pending a real escaped defect. See [eng-tips brief-03](../external-review/eng-tips-2026-06/brief-03-test-type-taxonomy.md).
