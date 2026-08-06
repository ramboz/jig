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
- **Tier 1**: Default for most projects. Built: `adr-workflow` (005), `tdd-loop` (006), `slice-land` (007 + 009 close-out fix), `pr-review` (012), `arch-review` (014), `clarify`, `analyze`, `security-review`, `code-health` (060), `explain` (065), `bug-fix` (058), `reframe` (067), `orient` (read-only project-orientation briefing, the judgment layer over `workflow.py orient`). Outstanding candidate: `local-dev-parity` (no signal yet).
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
[spec 016-scaffold-mode](../specs/016-scaffold-mode/spec.md). **Opt-in as of slice 099-01 /
[ADR-0041](../decisions/adr-0041-scaffold-defaults-to-plugin-mode.md)** — pass `--in-repo`
(aliases `--with-machinery`, `--copy-machinery`); plugin mode is the default, because copying
the machinery pins it to the scaffold-time jig version (silent drift), dominates the repo's
file count and history, and makes ownership of the copies ambiguous. Choose in-repo when the
plugin cannot be assumed present: CI or cloud agents on a bare checkout, teammates without
jig installed, archival repos. It was default-on between slices 016-03 and 099-01. When
selected, `scaffold-init` copies `skills/`, `agents/`, and `hooks/scripts/` into the
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

## ABANDONED

A second terminal-adjacent spec-lifecycle state, added in slice 085-01 (filed as
[GitHub issue #72](https://github.com/ramboz/jig/issues/72)). Distinct from
`DEFERRED`: `DEFERRED` means "parked, with a stated resolution trigger that will
resurface it"; `ABANDONED` means permanently dropped, no intent to resume. Reachable
from any pre-`DONE` state (`DONE → ABANDONED` is refused — marking already-shipped
work abandoned is a different, out-of-scope concept, see spec 085 Non-goals).
Mirrors `DEFERRED`'s restricted outbound edges (`ABANDONED → DRAFT` re-open only)
and gets its own `## Abandoned slices` status-board section (a `**Abandonment
reason:**` line, parallel to `**Resolution trigger:**`). `compute_spec_status`
gained a 4th rollup value: a spec where every slice is `ABANDONED` rolls up to
`ABANDONED` itself, resolving [spec 036](../specs/036-closed-spec-drift/spec.md)
Q3's previously-open "specs whose entire scope was abandoned" case. Marking a slice
`ABANDONED` also emits a one-time, non-blocking warning naming any live dependent
slice elsewhere in the project — advisory only, no cascade.

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
When a closed (DONE or SUPERSEDED) spec's prose no longer matches reality because the code/process evolved around it. Governed by [ADR-0010](../decisions/adr-0010-amendment-scope-records-vs-live-prose.md) (which supersedes [ADR-0008](../decisions/adr-0008-closed-spec-drift-policy.md)): closed records (DONE / SUPERSEDED specs + slices) get a `## Amendments` section preserving the original; live operational prose (SKILL.md, `docs/workflow.md`, README) is corrected **inline** (git = audit trail); a new ADR is required when the delta is decision content. Scope excludes IN_PROGRESS, REVIEWED, RECONCILED, DEFERRED.

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
EngTip #21's five test *types*, distinguished by **scope** (how much of the system each exercises), used as a shared vocabulary so "do we have enough tests?" becomes answerable. (1) **Unit** — a single operation in a single component; fast, hermetic, dependencies doubled. (2) **Component** — multiple operations within one component, verifying its invariants as a stateful whole. (3) **Seam-integration** — exactly one component against exactly one real dependency across a boundary, verifying the doubled contract actually holds (the type most often missing). (4) **System-integration** — several components together (service + DB + downstream). (5) **End-to-end** — a full user journey across the stack; highest fidelity, poorest at localizing failure. The point isn't a coverage number (gameable) but a checklist for finding gaps and assigning ownership. jig currently tracks *artifact* coverage (`workflow.py coverage`, use-cases), not test-scope coverage — parked as an [inbox](../inbox.md) item, not a spec, pending a real escaped defect. The original EngTips brief was retired after folding the durable content here.

<!-- Relocated from the CLAUDE.md Hot Cache by spec 076-01 (lean primer):
     dense decision-summary prose moved off the always-loaded path and
     reachable on demand via /jig:explain (merged-lexicon overlay). -->

## Lifecycle-family spine

[ADR-0023](../decisions/adr-0023-lifecycle-family-spine.md) — spec-workflow, `jig:bug-fix` ([ADR-0016](../decisions/adr-0016-bug-fix-lifecycle.md)), and `jig:refactor` ([ADR-0019](../decisions/adr-0019-refactor-workflow.md)) are one gated-evidence lifecycle family sharing a C1–C7 spine contract; the shared code is extracted to `_common/lifecycle.py` only at the *third* concrete `transition` (today only `workflow.py` exists; bug/refactor are Proposed). The pluggable-oracle boundary to servo ([ADR-0022](../decisions/adr-0022-pluggable-oracle-boundary.md), clause C5) is PARKED — don't re-propose it without a real eval case, a servo spec 006, or a built consumer.

## Reframe

[ADR-0024](../decisions/adr-0024-reference-reframe.md) / [spec 067](../specs/067-reframe/spec.md) — re-baseline the corpus when a **load-bearing reference** (design system, vendor / API contract, test infra, compliance regime, target platform, product-positioning / strategic-vision shift) moves *from outside the system*. The `/jig:reframe` skill (Tier-1, judgment-only, no `.py`) reads the accepted corpus against the new reference and drafts a **keystone reframe-ADR** — new reference authoritative as of `<date>`, old premise superseded, a **re-baselining manifest** giving every affected artifact a disposition (`reaffirm`/`amend`/`supersede`/`retire-draft`/`retrofit`/`rewrite`), and a **two-level coverage floor** (L1 per-class scanned/excused; L2 artifact-level within touched classes) that makes an omission *visible* at the frame-critique `accept` gate. A *capability over the spine* (ADR-0023 §4), **not** a gated lifecycle member: no `transition`, it orchestrates the ADR/spec lifecycles it spawns. Systematic blast-radius **detection is parked** (triggers T1/T2/T3); the noticing half is a best-effort nudge, not a detector.

## Spec-gate model

[ADR-0011](../decisions/adr-0011-spec-gate-model.md) — `jig-spec-gate.sh` is a *deliberateness* gate on `docs/conventions.md` edits (`JIG_CONVENTIONS_APPROVED=1` bypass satisfiable by any shell incl. the agent), **not** human-only enforcement — real control is out-of-band (CODEOWNERS / CI / branch-protection). The policy "human approval to change conventions.md" stays; the gate is jig-layout-specific (`JIG_GATED_FILES` deferred).

## Security floor

[ADR-0013](../decisions/adr-0013-security-floor-policy.md) / [spec 052](../specs/052-security-scaffold/spec.md) — every scaffolded/migrated project gets a 5-part floor: `.gitignore` secret patterns + the agent-time `jig-secret-scan.sh` PreToolUse hook (`JIG_SECRET_SCAN_APPROVED=1` bypass, fails open) + conservative `permissions.deny` defaults + a `## Security (MUST)` CLAUDE.md block + the slim `jig:security-review` skill. Defense-in-depth, not a firewall (mirrors ADR-0011); flows to existing projects via `migrate copy-machinery`, asserted by `scripts/verify_install.py`.

## Copied templates tree

[ADR-0038](../decisions/adr-0038-claude-scaffold-template-copy.md) / [spec 095](../specs/095-scaffold-template-copy/spec.md) — **both** scaffold hosts copy jig's `templates/` beside the copied machinery (`.claude/templates/`, `.codex/templates/`), because five record helpers resolve their template as `CLAUDE_PLUGIN_ROOT`, else `parents[2]/templates/` — which in scaffold mode lands on `<project>/.claude` (or `.codex`), the one install mode with no plugin root to fall back on. Copied by `_copy_claude_templates` / `_copy_codex_templates` in `scaffold.py`, both behind `copy_machinery`, both rewriting `*.md.template` plugin-root skill paths to the copied runtime; ungated infra, never tier-scoped (templates have no natural tier — mirrors the `.gitignore` security floor). **The tree is jig's source materialized so helpers can read it — not the project's content: edit your project's files, never `.claude/templates/`** (a `copy-machinery` refresh overwrites it). Readers: `decisions.py` + `migrate.py seed-decisions` (lightweight-decisions), `adr.py new`, `workflow.py` (slice-template), `memory.py` (people.md) — 4 live files of 25; the other 21 are `scaffold-init` seed templates, inert in a scaffolded project. Retrofit for pre-095 projects needs `copy-machinery` **from a jig install** — a scaffolded project cannot repair itself from inside — and `migrate report` now flags the gap and routes there (maintainer's call on [#119](https://github.com/ramboz/jig/pull/119); ADR-0038 Open questions, resolved).

## Review-evidence gate

[ADR-0014](../decisions/adr-0014-review-evidence-model.md) (spec 045) — durable verdict artifacts at `docs/specs/NNN-slug/reviews/slice-NN-<pass>.md` (body = the VERDICT envelope); `review.py record-review` writes, `check-reviews` validates. `workflow.py transition` gates READY_FOR_REVIEW (frame-critique iff `frame_review`), REVIEWED (compliance+craft, +arch/+code-health/+design-review iff their flags), RECONCILED (reconciliation verdict + deviation log), DONE (re-validates the set + dep-check) — each clears iff `verdict: pass`. Bypass `JIG_REVIEW_EVIDENCE_GATE=0` (deliberateness, not human-only). Shared schema/validator `skills/_common/review_evidence.py` (`PASSES` = compliance/craft/arch/code-health/reconciliation/frame-critique/design-review; `validate_evidence` reads the gating flags itself so spawner+gate can't drift); flag-truthy set in `skills/_common/parsing.py`. arch/code-health/design (REVIEWED) + frame-critique (READY_FOR_REVIEW) gate on per-slice flags (default-off). Frame-critique = adversarial PRE-implementation hardening (spec 064 / [ADR-0020](../decisions/adr-0020-spec-frame-hardening.md)); also gates `adr.py accept` (064-05, ADR evidence at `docs/decisions/reviews/adr-NNNN-<pass>.md`); rung-3 cross-model critique deferred. Design-review = attest-only external-eval pass (spec 071 / [ADR-0022](../decisions/adr-0022-pluggable-oracle-boundary.md)).

## Lifecycle entry gate

[ADR-0044](../decisions/adr-0044-lifecycle-entry-gate.md) / [spec 098](../specs/098-lifecycle-entry-gate/spec.md) — the teeth-not-trust gate for lifecycle *entry* (the last step #111 measured as enforced only by the agent remembering: 11 out-of-lifecycle edits). `hooks/scripts/jig-entry-gate.sh` + testable `hooks/scripts/lib/entry_gate.py` fire on `PostToolUse` `Edit|Write|MultiEdit` (co-located with `jig-post-edit-verify` / `jig-boundary-change-warn`) and inject ONE agent-facing `additionalContext` nudge when an edit to **project source** happens while the session is **outside** the lifecycle. Never blocks, never prompts the owner (Option C, rejected the hard-block B); fail-open; `JIG_ENTRY_GATE=0` opt-out. **Inside** = `.jig/spec-ref` names a work item `claimed_by` this checkout (branch scoping, not operator identity) AND in a working status — slice arm via #138's `_CLAIM_WORKING_STATUSES`, bug arm via slice 098-04's `bug=NNN` marker (extends `.jig/spec-ref` in place; invisible to the three `spec=`-keyed readers). The status cross-check makes a stale marker harmless. **Source boundary** (settled call #3) = `git check-ignore` OR the NAMED lifecycle-artifact subtrees (`specs`/`bugs`/`decisions`/`memory` under docs base, + `.jig`/`.claude`/`.codex`/`.git`) — never `docs_base` wholesale (the `docs_root="."` dead-gate trap). Once-per-session cadence, re-armed on lifecycle-state change. Two under-fire kill criteria pinned by anti-dead-gate tests (unrelated open work still nudges; `.`-root source still nudges). Codex parity (098-02): packaging + logic verified from the Claude host; runtime payload/cadence rows honestly `degraded` (need the Codex runtime — see the host-capability matrix in [architecture.md](../architecture.md)). Slice 098-03 (edit-anchored capture stub, #108 direction #2) DEFERRED behind the capture-rewrite decision.

## Worktree-aware reservation

[ADR-0015](../decisions/adr-0015-worktree-aware-reservation.md) / [spec 051](../specs/051-worktree-aware-reservation/spec.md) (051-03 land-guardrail DEFERRED) — `workflow.py new` / `adr.py new` route on the current branch: on `main` the proven in-place flow; off `main` push-mode builds the reservation commit in an ephemeral detached worktree at `origin/main` and pushes BY SHA from `project_dir` (pushing from the temp worktree breaks relative-`origin` repos), torn down in `finally`. Off `main` `--no-push` = pathspec-scoped provisional commit on the current branch. Caller's branch/cwd/tree never touched; inline-mirrored across both helpers. Best-effort serialization; durable land-time backstop is the deferred 051-03.

## Context-cost discipline

[spec 055](../specs/055-context-cost-discipline/spec.md) — orchestrator context is the expensive real estate (cost ≈ context-size × turns; in-session *growth*, not the primer, is the cost). Four soft mechanisms: (01) delegate file-heavy reads to a read-only subagent, keep the summary; (02) growth nudge `jig-context-check.sh` (`JIG_CONTEXT_GROWTH_WARN_PCT`); (03) read-once/lean `PreToolUse(Read)` (`JIG_READ_LEAN_BYTES`); (04) verbose-Bash results-not-logs. Guidance in [docs/workflow.md](../workflow.md#context-cost-discipline); same place as the Dumb-zone quality argument.

## Thin-orchestrator

[spec 057](../specs/057-thin-orchestrator/spec.md) — follow-on to spec 055: cost is two knobs — turn count (r=0.92) + peak context (r=0.96) — plus output volume (~22%, 5×-priced); cache-TTL and model-downgrade were falsified as levers. Three soft mechanisms, one per knob: (01) `workflow.py session-plan <spec.md>` emits a per-slice DELEGATE-vs-ORCHESTRATOR dispatch plan; (02) `JIG_CONTEXT_COMPACT_PCT` (0.75) escalates the context-check nudge to a compact/handoff prompt (never runs `/compact`); (03) lean-output conventions in `agents/implementer.md`/`reviewer.md`. jig recommends, the user/harness acts.

## Token-usage tracking

[spec 056](../specs/056-token-usage-tracking/spec.md) — `scripts/usage.py report <spec>` prints per-spec orchestrator/subagent/combined token totals (measured from transcript `message.usage`) + a ccusage-priced `$` estimate (price via `npx ccusage`, never hand-roll rates — Opus hand-rolled ran ~3× high). Attribution prefers the exact `.jig/spec-ref` marker (stamped by `transition … IN_PROGRESS`, gitignored), falls back to a content heuristic (flagged lower-confidence). Measures the lever 055 optimizes.

## Slice-claim on working states

[spec 049](../specs/049-slice-claim-on-in-progress/spec.md) / [ADR-0015](../decisions/adr-0015-worktree-aware-reservation.md) lineage, amended by [ADR-0045](../decisions/adr-0045-slice-claim-covers-active-lifecycle.md) — the lifecycle splits two ways for ownership. **Working states** (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`) STAMP `claimed_by:` (branch name or `JIG_CLAIM_ID`) on a file-per-slice slice, so spec-level work — `REVIEWED → RECONCILED` reconciliation above all — is marked and not just implementation. **Release points** CLEAR it: the two pickup-queue states (`DRAFT` / `READY_FOR_IMPLEMENTATION`, which the pickup flow tells readers to choose from — a residual owner there would mark a free slice occupied, inverting the bug) plus the three terminal states (`DONE` / `DEFERRED` / `ABANDONED`); `--release --reason "<why>"` force-clears anywhere and logs `## Release log`. The two sets partition `VALID_STATUSES`, pinned by test. **Hard-refuses** only an already-`IN_PROGRESS` foreign claim on a `→ IN_PROGRESS` move (locally and on origin/main); every other foreign claim — own copy or trunk — is a non-blocking warning naming the holder. Board renders `<STATUS> (<claimed_by>)` on working rows. Claim is LOCAL by default (offline-friendly); `--push`/`--pr` reserve it on `origin/main` via the uniform ephemeral detached-worktree at any working state, but only an `IN_PROGRESS` reservation also publishes trunk `status:` (that write feeds the 051-04 start-collision guard; publishing any other state would regress trunk lifecycle state, which the landing flow owns). Frontmatter-only. **An empty `claimed_by:` means no claim is RECORDED — not that the slice is free** (unpushed claims are invisible; plain `Edit` writes take none); reading blank as available is [bug 014](../bugs/014-slice-claim-covers-only-in-progress.md).

## Solo→team re-detection

[spec 050](../specs/050-solo-team-redetection/spec.md) — the team signal (≥2 mailmap-normalized git authors, monorepo-guarded) is re-evaluated after init: `memory.py team-check` (memory-sync's final step) nudges [y]/[n]/[never] to bootstrap `people.md`, and `workflow.py stale` surfaces it as a `category: team-context` row (read-only, stays exit-0). Opt-out = tracked `.jig/no-people-md` (written by `scaffold-init --solo` only). Shared logic in `skills/_common/team_signal.py` (`team_context_drift()` predicate).

## Vocabulary barrier / lexicon

[spec 065](../specs/065-lower-vocabulary-barrier/spec.md) / [ADR-0021](../decisions/adr-0021-lexicon-home-and-overlay.md) — jig explains its own jargon on demand, off the hot path. One canonical lexicon (`_common/lexicon.json` + loader `_common/lexicon.py` merging the project `glossary.md` overlay, project wins) feeds the `jig-memory-scan` hook (just-in-time defs), the `/jig:explain` skill (term/artifact/passage modes, ephemeral), and the self-defining-vocabulary convention (managed block in `docs/workflow.md`). Nothing definitional injected into always-loaded `CLAUDE.md` (respects 055/057).

## Status board

[docs/specs/README.md](../specs/README.md), regenerated by `workflow.py status-board`; the Notes column is preserved across regen and carries per-slice load-bearing invariants. Renders a 🔬 prefix on `kind: spike` rows and `<STATUS> (<claimed_by>)` on claimed slices in any WORKING state (ADR-0045); pickup-queue and terminal rows never carry an owner.

## lightweight decisions
Shipped decisions settled mid-session that fall outside spec slices, recorded in docs/decisions/lightweight-decisions.md. Routing heuristic: lightweight iff (a) no module-boundary/contract/policy change AND (b) a future agent would need it to avoid undoing it; else ADR; refinement-todo if still open; drop if ephemeral. Template: Date, Decision, Context, Scope, Commit (optional). **Phase 1 (083-01..03, DONE, ADOPTED 2026-06-25):** the browsable home + scaffold seeding + reconcile/memory-sync *nudges*. **Phase 2 (083-04..08, DRAFT — food-log report 2026-06-25):** the real failure mode is recall-dependence (decisions lost regardless of size because nothing *remembers* to ask). Three frame-critique rounds (Opus) converged on a **two-tier** model: a deterministic floor (Stop-hook **scan** for lexical Tiers 1–2, sibling of jig-task-capture.sh; **+ in-flight Tier-1 structured capture**, 083-07 ACTIVE — the only recall-free path) plus a judgment ceiling (reconciliation + memory-sync prompts, 083-06, single-sourced via its own ADR) for discursive load-bearing decisions that no regex can see. NOT "recall eliminated" — recall-*reduced*. Three-way coverage map by in-spec/out-of-spec × lexical/load-bearing; out-of-spec load-bearing has no reconciliation phase so the memory-sync judgment escape hatch owns it. 083-08 = Codex host-parity validation (handoff). Constraints: owner-gated writes, mandatory provenance (who + quote), precision over recall.

## advisory lint
A **report-only** check whose findings are a prompt to judge, never a verdict — the opposite of a gate, and the distinction is load-bearing rather than stylistic. Introduced by `decisions.py lint` (spec 100-04 / [ADR-0042](../decisions/adr-0042-decision-routing-gate.md)): it sweeps `lightweight-decisions.md` for entries whose wording reads ADR-worthy, names the matched phrases and the `promote` command that fixes each, and **never writes** — not the entry, not the file, not a seed. It exists because the routing enforcement it backs up is *judgement*, prompted in memory-sync's skill description at the moment a recorded decision is revised, not a keyword matcher on the write path: jig distrusts lexical matching as a gate (the maintainer, on [#121](https://github.com/ramboz/jig/issues/121): "likely brittle… we've seen this pattern failing repeatedly"), and a prototype write-gate duly refused an ordinary "user interface" copy decision. The lexical evaluator therefore survives **only here**, where a false positive costs a glance instead of a blocked write. Do NOT re-wire it into `add-lightweight` or `update` — that gate was built and deliberately removed. Known weakness, recorded in ADR-0042's kill criteria: the honest risk is false **negatives**, since ADR-0031 already found lexical scans miss the most load-bearing decisions precisely because they carry no stock phrase.

## configurable docs root
The `layout.docs_root` knob in scaffold.json (default `"docs"`) that lets jig redefine where its artifacts live, so a project can be adopted **track-local** inside a larger repo: `docs_root="."` puts specs/decisions/memory directly under the project dir instead of forcing a second `docs/` layer. Read via `_common/project_layout.py`; created via `scaffold-init --docs-root`. Project-root discovery is **sentinel-anchored** (nearest `scaffold.json`), never structure-derived; push-mode reservation is refused in a subtree (git anchoring stays out of scope). See ADR-0033 / spec 084.

## autonomy governance plane
The scaffolded, out-of-band protection of a repo's *governing* artifacts plus the checkable precondition for running that repo unattended (spec 106 / [ADR-0051](../decisions/adr-0051-autonomy-governance-plane.md)). Two halves. **The protected plane:** `scaffold-init` writes a `CODEOWNERS`, a `.github/workflows/jig-governance.yml` job that flags any PR diff touching a protected path for owner review, and `<docs>/governance.md` (the branch-protection arming checklist). `governance.PROTECTED_PATHS` — `docs/conventions.md`, `docs/decisions/**`, `oracle.sh`, `.servo/**/config.json`, **and the plane's own `.github/workflows/**` + `CODEOWNERS`** (self-reference by construction) — is mirrored into `scaffold.json.protected_paths`, which `jig-boundary-change-warn` reads to soft-nudge in-boundary edits. **These files are inert until branch protection is armed** (require-status-check + require-Code-Owner-review + forbid-bypass): scaffold writes files, not the server-side settings that enforce, so jig documents the arming step and the servo readiness gate verifies the armed state — the files are never advertised as enforcement on their own (ADR-0011/0013 posture). **The identity/capability precondition:** `governance.check_identity_separation` keys on merge *capability*, not identity name — a distinct-but-over-privileged bot is still unsafe, a distinct name without an attested capability is not-ready (a name mismatch does not prove non-capability), and an absent capability signal fails safe to not-ready. It is deterministic *over supplied/attested inputs* (jig does not observe GitHub merge permissions in-process); the servo autonomy-readiness gate (servo 023 / ADR-0029) derives the capability input from the GitHub API and subprocess-invokes `governance.py identity-check` (stdout `IdentityVerdict` JSON with authoritative `ready`; exit `0` ready / `3` not-ready / `2` usage).
