# jig — AI-Native Dev Scaffold

> The Codex skill pack that scaffolds AI-native development practices.
> We dogfood the workflow we build.

## Hot Cache

Always-loaded primer, kept lean per [spec 055/057](docs/specs/055-context-cost-discipline/spec.md) (orchestrator context × turns is the cost). This is an **index**: each **bold term** is a one-line claim + link; full definitions live in [docs/memory/glossary.md](docs/memory/glossary.md) + the lexicon and expand on demand via `/jig:explain <term>`. Update via `/jig:memory-sync`.

### Project codenames / active work
- **jig** = this skill pack repo (the plugin itself).
- **Branch routing** — `main` is the sole active line: 1.x and the 2.0 multi-host work both shipped here (latest tag `v2.10.0`). The legacy `v2` branch is closed — don't route work to it. See [docs/roadmap.md](docs/roadmap.md).
- **Active specs:** none in-flight (088 `/jig:orient` skill shipped + closed). **Recorded, not yet built:** spec 091 — bug-fix repository-closure evidence ([ADR-0037](docs/decisions/adr-0037-bug-fix-repository-closure-evidence.md), Proposed); gates don't exist yet. **Long-horizon-autonomy bridge (oh-my-cli follow-on), recorded not built:** spec 105 — durable failure-quarantine jig-half ([ADR-0050](docs/decisions/adr-0050-durable-failure-quarantine.md), Proposed) + spec 106 — autonomy governance plane & identity separation ([ADR-0051](docs/decisions/adr-0051-autonomy-governance-plane.md), Proposed); servo halves live in `ramboz/servo` (servo specs 023/024/025, ADR-0029/0030). Nothing built yet. See [docs/specs/README.md](docs/specs/README.md). Deferred → [docs/refinement-todo.md](docs/refinement-todo.md).

### Key terms (one-line index — full defs via `/jig:explain <term>`)
- **Configurable docs root** — [ADR-0033](docs/decisions/adr-0033-configurable-docs-root.md) / [spec 084](docs/specs/084-configurable-docs-root/spec.md) — `layout.docs_root` in scaffold.json (default `docs`); `.` = track-local adoption inside a larger repo; discovery sentinel-anchored; subtree push-mode refused. Read via `_common/project_layout.py`.
- **Subagent permission** — In this jig project, the user explicitly permits Codex to use subagents when they materially help implementation, review, reconciliation, or coordination work.
- **Lifecycle-family spine** — [ADR-0023](docs/decisions/adr-0023-lifecycle-family-spine.md) — spec-workflow / bug-fix / refactor share one C1–C7 gated-evidence spine; extract to `_common/lifecycle.py` only at the *third* `transition`. **PARKED — don't re-propose** the servo pluggable-oracle boundary ([ADR-0022](docs/decisions/adr-0022-pluggable-oracle-boundary.md) C5) without a real eval case / servo spec 006 / a built consumer.
- **Closed-spec drift** — [ADR-0010](docs/decisions/adr-0010-amendment-scope-records-vs-live-prose.md) (supersedes [ADR-0008](docs/decisions/adr-0008-closed-spec-drift-policy.md)) — closed records get `## Amendments`; live prose corrected inline; new ADR for decision changes. **Amending a record needs explicit owner approval** ([spec 102](docs/specs/102-amendment-authorization-guardrail/spec.md), issue #125): surface a canon-artifact conflict and stop; approving a behaviour ≠ authority to rewrite the record; read the whole criteria block before asserting a contradiction.
- **Spec-gate model** — [ADR-0011](docs/decisions/adr-0011-spec-gate-model.md) — `jig-spec-gate.sh` is a *deliberateness* gate on `conventions.md`, not human-only enforcement; real control is out-of-band.
- **Security floor** — [ADR-0013](docs/decisions/adr-0013-security-floor-policy.md) / [spec 052](docs/specs/052-security-scaffold/spec.md) — 5-part scaffolded floor; defense-in-depth, not a firewall.
- **Review-evidence gate** — [ADR-0014](docs/decisions/adr-0014-review-evidence-model.md) (spec 045) — `transition` gates REVIEWED/RECONCILED/DONE on recorded verdict artifacts; bypass `JIG_REVIEW_EVIDENCE_GATE=0`. Sibling **Lifecycle entry gate** — [ADR-0044](docs/decisions/adr-0044-lifecycle-entry-gate.md) / [spec 098](docs/specs/098-lifecycle-entry-gate/spec.md) — fail-open `PostToolUse` nudge on an out-of-lifecycle source edit (no live claim held by this checkout); reads `.jig/spec-ref` (slice + 098-04 `bug=NNN` arms) w/ a `.gitignore`/named-artifact boundary; `JIG_ENTRY_GATE=0`. Sibling **Session git-freshness** — [ADR-0048](docs/decisions/adr-0048-session-git-freshness-fetch-and-nudge.md) / [spec 103](docs/specs/103-session-git-freshness/spec.md) — fail-open `SessionStart` time-zero nudge: fetches (timeout-guarded, best-effort) the integration base, warns when `HEAD` is behind before a stale premise forms; smart-target resolution (non-own `@{upstream}` else `origin/main`→`origin/master`; own-remote guard = base drift, not own-branch advancement); `JIG_GIT_FRESHNESS=0`.
- **Worktree-aware reservation** — [ADR-0015](docs/decisions/adr-0015-worktree-aware-reservation.md) / [spec 051](docs/specs/051-worktree-aware-reservation/spec.md) — `new` routes on branch; off-main reserves via an ephemeral detached worktree at origin/main.
- **Context-cost discipline** — [spec 055](docs/specs/055-context-cost-discipline/spec.md) — cost ≈ orchestrator context × turns; delegate reads, keep the primer lean.
- **Thin-orchestrator** — [spec 057](docs/specs/057-thin-orchestrator/spec.md) — turn count + peak context are the top cost knobs; `workflow.py session-plan` dispatches.
- **Token-usage tracking** — [spec 056](docs/specs/056-token-usage-tracking/spec.md) — `usage.py report <spec>` per-spec token/$ totals; price via ccusage, never hand-rolled.
- **Slice-claim on working states** — [spec 049](docs/specs/049-slice-claim-on-in-progress/spec.md) / [ADR-0045](docs/decisions/adr-0045-slice-claim-covers-active-lifecycle.md) — `transition` stamps `claimed_by:` on WORKING states, releases on the pickup queue + terminal; blank ≠ free.
- **Solo→team re-detection** — [spec 050](docs/specs/050-solo-team-redetection/spec.md) — re-evaluates the team signal; nudges to bootstrap `people.md`.
- **Vocabulary barrier / lexicon** — [spec 065](docs/specs/065-lower-vocabulary-barrier/spec.md) / [ADR-0021](docs/decisions/adr-0021-lexicon-home-and-overlay.md) — on-demand jargon via `/jig:explain` + lexicon, off the hot path.
- **Status board** — [docs/specs/README.md](docs/specs/README.md), regenerated by `workflow.py status-board`; Notes column preserved + load-bearing.
- **SPIDR**, **Vertical slice**, **Dumb zone**, **Reconciliation**, **Reframe** (`/jig:reframe` — [ADR-0024](docs/decisions/adr-0024-reference-reframe.md)), **Tier 0/1/2**, **Hot Cache**, **Research note** (`docs/research/R-NNN`, [ADR-0054](docs/decisions/adr-0054-research-notes-artifact-convention.md)) — see [glossary](docs/memory/glossary.md) / `/jig:explain`.

## Key documents

| Document | When to read |
|---|---|
| [docs/product-vision.md](docs/product-vision.md) | What jig is; before any positioning discussion |
| [docs/workflow.md](docs/workflow.md) | How we build — start of every session |
| [docs/architecture.md](docs/architecture.md) | Plugin internals / module boundaries |
| [docs/conventions.md](docs/conventions.md) | Before authoring any skill / hook / agent |
| [docs/decisions/](docs/decisions/) | ADR index |
| [docs/specs/README.md](docs/specs/README.md) | Spec status board — pick up next work |
| [docs/bugs/README.md](docs/bugs/README.md) | Bug status board — check before folding defects into specs |
| [docs/roadmap.md](docs/roadmap.md) | Milestone / branch overlay |
| [docs/refinement-todo.md](docs/refinement-todo.md) | Deferred decisions |
| [docs/memory/glossary.md](docs/memory/glossary.md) | Domain terms (the on-demand home for the index above) |
| [docs/memory/learnings.md](docs/memory/learnings.md) | Dead ends and gotchas |
| [docs/inbox.md](docs/inbox.md) | Parked ideas |

## Skills in this repo

The host surfaces every jig skill **with its description each session** — this primer does not re-list them (EngTip #23 / spec 076). Each skill's contract is its `skills/<name>/SKILL.md`; the per-tier roster is `scaffold._TIER_SKILLS` (mirrored in the glossary's **Tier 0/1/2** entry). Skills with a `.py` helper: `spec-workflow` (`workflow.py`), `independent-review` (`review.py`), `adr-workflow` (`adr.py`), `tdd-loop` (`tdd.py`), `slice-land` (`land.py`), `migrate` (`migrate.py`), `memory-sync` (`memory.py`), `code-health` (`health.py`), `bug-fix` (`bug.py`); the rest are judgment-only. Explain any skill, term, or artifact with `/jig:explain`.

Host packaging details live in [docs/architecture.md](docs/architecture.md); Codex plugin packaging is built by `scripts/build_codex_plugin.py`, with `--install-codex-agents` for the explicit custom-agent TOML install step.

## Session workflow

1. Check [docs/specs/README.md](docs/specs/README.md) + [docs/bugs/README.md](docs/bugs/README.md); route reported defects to `bug-fix`, then pick up the next `READY_FOR_IMPLEMENTATION` slice.
2. Implement (TDD). After the deliverable is on disk, run post-impl review — compliance + craft always, +arch/+code-health/+frame/+design iff the slice flags them. See [docs/workflow.md](docs/workflow.md#post-implementation-review) + [spec-workflow/SKILL.md](skills/spec-workflow/SKILL.md).
3. Reconcile: deviation log, doc updates, reconciliation review.
4. `/jig:memory-sync`; update spec status + regenerate the status board.

## Constraints for agents working on this repo

- Do not modify [docs/conventions.md](docs/conventions.md) without explicit human approval.
- Reviewer subagent is read-only (Read / Glob / Grep) — it cannot write to memory.
- [templates/AGENTS.md.template](templates/AGENTS.md.template) is the scaffold source — not this file.
- Hook commands use host-rendered paths (`${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` in Claude plugin mode, `${CODEX_PROJECT_DIR:-$PWD}/.codex/hooks/scripts/...` in Codex scaffold mode); never rely on bare hook names. All hooks use Python 3 for JSON (never jq).
- ADRs → `docs/decisions/adr-NNNN-<slug>.md` (ADR-0004); slices → `docs/specs/NNN-<slug>/slice-NN-<short>.md` (spec 018, sibling files; `spec.md` is the overview).
- When a slice closes a spec, **compress** its Active-specs entry (spec 025-01); load-bearing per-slice invariants migrate to the status board Notes column, not AGENTS.md.
