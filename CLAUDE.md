# jig — AI-Native Dev Scaffold

> The Claude Code skill pack that scaffolds AI-native development practices.
> We dogfood the workflow we build.

## Hot Cache

Frequently-referenced terms and project state. Loaded every session.
Update via `/jig:memory-sync` or when `jig-memory-scan` surfaces an unknown reference.

### Project codenames / active work

- **jig** = this skill pack repo (the plugin itself)

### Key terms
- **Closed-spec drift policy** — [ADR-0010](docs/decisions/adr-0010-amendment-scope-records-vs-live-prose.md) (supersedes [ADR-0008](docs/decisions/adr-0008-closed-spec-drift-policy.md)) — **records** (closed DONE / SUPERSEDED specs + slices) get a `## Amendments` section that preserves the original; **live operational prose** (SKILL.md descriptions, `docs/workflow.md`, README) is corrected **inline**, with git history as the audit trail. New ADR (or superseding spec) for decision-content changes. Excludes IN_PROGRESS / REVIEWED / RECONCILED / DEFERRED.

- **Spec-gate model** — [ADR-0011](docs/decisions/adr-0011-spec-gate-model.md) — `hooks/scripts/jig-spec-gate.sh` is a *deliberateness* gate that blocks accidental side-effect edits to `docs/conventions.md`, **not** human-only enforcement (the `JIG_CONVENTIONS_APPROVED=1` env var is satisfiable by any shell, incl. the agent via Bash). Real human-only control is out-of-band (`CODEOWNERS` / CI / branch-protection). The *policy* "human approval to change conventions.md" stays; only the claim that the *hook enforces* it was the honesty gap. Gate is jig-layout-specific (`docs/conventions.md` only; `JIG_GATED_FILES` deferred).

- **Security floor** — [ADR-0013](docs/decisions/adr-0013-security-floor-policy.md) / [spec 052](docs/specs/052-security-scaffold/spec.md) — every scaffolded/migrated project gets a 5-part floor: `.gitignore` secret patterns (with `!.env.example` re-includes) + an agent-time `jig-secret-scan.sh` PreToolUse hook (blocks high-confidence secrets — AWS key / PEM / secret-named `.env` assignment — overridable via `JIG_SECRET_SCAN_APPROVED=1`, fails open) + conservative `permissions.deny` defaults (force-push / hard-reset / `rm -rf`, merged by **set-membership** marker since a string array can't carry the hooks' `metadata.managed_by_jig`) + a lean `## Security (MUST)` CLAUDE.md block + the slim Tier-1 `jig:security-review` skill (orchestrate-installed-scanners + defer-to-richer). **Defense-in-depth, not a firewall** (mirrors [ADR-0011](docs/decisions/adr-0011-spec-gate-model.md)): real enforcement is out-of-band (CI / server-side hooks / branch protection). Non-exhaustive by design; tuning surfaces parked in `docs/refinement-todo.md`. The floor flows to existing projects via `migrate copy-machinery` and is asserted by `scripts/verify_install.py`.
- **Review-evidence gate** — [ADR-0014](docs/decisions/adr-0014-review-evidence-model.md) (spec 045) — review/reconciliation verdicts are durable artifacts at `docs/specs/NNN-slug/reviews/slice-NN-<pass>.md` (frontmatter: `slice`/`pass`/`verdict`/`reviewer`/`reviewed_at`/`prompt_source`; body = the VERDICT envelope). `review.py record-review` writes them, `check-reviews` validates. `workflow.py transition` **gates** REVIEWED (compliance+craft, +arch iff `arch_review`), RECONCILED (reconciliation verdict + deviation log via `check_deviation_log`), DONE (re-validates the full set + dep-check) — each clears iff `verdict: pass`; refuses naming the missing artifact + the `record-review` command. Bypass `JIG_REVIEW_EVIDENCE_GATE=0` (deliberateness signal per ADR-0011, **not** human-only). Supersede = overwrite-in-place + git history (ADR-0010). Shared schema/validator: `skills/_common/review_evidence.py`; arch-flag truthy set unified in `skills/_common/parsing.py` (`FRONTMATTER_TRUTHY`). The three review passes (compliance/craft/arch) are unchanged; each now leaves a verdict artifact the gate checks.
- **Context-cost discipline** — [spec 055](docs/specs/055-context-cost-discipline/spec.md) — the orchestrator's context is the most expensive real estate (re-read every turn → cost ≈ context-size × turns; measured on jig: ~90% orchestrator / ~97% `cache_read` / ~4% baseline — in-session *growth*, not the primer, is the cost). Four soft, non-blocking, scaffolded mechanisms keep it lean: (01) **delegate** file-heavy reading to a read-only built-in `Explore`/`general-purpose` subagent, keep only the summary; (02) **growth nudge** — `jig-context-check.sh` on `UserPromptSubmit` warns past dumb-zone bands (`JIG_CONTEXT_GROWTH_WARN_PCT`; 40/60/80; re-arm-on-drop); (03) **read-once/lean** — `PreToolUse(Read)` warns duplicate / oversized (`JIG_READ_LEAN_BYTES`) reads; (04) **verbose-Bash** — the implementer surfaces results-not-logs. Standing guidance: [docs/workflow.md](docs/workflow.md#context-cost-discipline). The *cost* argument lands on the same place as the **Dumb zone** *quality* argument.

- **SPIDR** = Mike Cohn's five story-splitting techniques (Spike, Path, Interface, Data, Rules)
- **Tier 0/1/2** = installation tiers for jig skills (see [docs/memory/glossary.md](docs/memory/glossary.md))
- **Hot Cache** = the structured CLAUDE.md section for high-frequency terms
- **Dumb zone** = >40% context fill; above this, model recall degrades (Horthy)
- **Vertical slice** = a spec slice that crosses all layers and delivers end-to-end value
- **Reconciliation** = post-implementation phase: deviation log, doc updates, second review pass
- **Status board** = [docs/specs/README.md](docs/specs/README.md), regenerated by `workflow.py status-board`; Notes column is preserved across regen and carries per-slice load-bearing invariants

### Active specs

_(none — see [docs/specs/README.md](docs/specs/README.md) for the
status board; per-slice load-bearing invariants live in its Notes
column.)_

### Deferred decisions

→ See [docs/refinement-todo.md](docs/refinement-todo.md)

## Key documents

| Document | Purpose | When to read |
|---|---|---|
| [docs/product-vision.md](docs/product-vision.md) | What jig is, target users, design principles, competitive landscape | First read for new contributors; before any positioning discussion |
| [docs/workflow.md](docs/workflow.md) | How we build — spec lifecycle, session workflow | Start of every session |
| [docs/architecture.md](docs/architecture.md) | Tech stack, module boundaries, decisions (mechanics; principles live in product-vision.md) | Before touching plugin internals |
| [docs/conventions.md](docs/conventions.md) | Skill/hook/agent authoring standards | Before writing any skill or hook |
| [docs/decisions/](docs/decisions/) | ADR index | When recording or reading a hard-to-reverse decision |
| [docs/specs/README.md](docs/specs/README.md) | Spec status board | To pick up next work |
| [docs/refinement-todo.md](docs/refinement-todo.md) | Deferred decisions | When hitting an undefined case |
| [docs/memory/glossary.md](docs/memory/glossary.md) | Domain terms | When encountering unknown terms |
| [docs/memory/learnings.md](docs/memory/learnings.md) | Dead ends and gotchas | Before repeating a mistake |
| [docs/inbox.md](docs/inbox.md) | Parked ideas | During reconciliation |

## Skills in this repo

| Skill | Purpose | Invocable |
|---|---|---|
| `/jig:scaffold-init` | Initialize jig in a fresh project. Copies skills + agents + hooks + settings.json into the target's `.claude/` by default; `--plugin-only` opts out. Refuses on spec-driven layouts without `scaffold.json` (routes to `/jig:migrate`). | Yes (explicit) |
| `/jig:vision-elicitation` | Lightweight wizard that fills the elicitation slots in `docs/product-vision.md` and `docs/architecture.md` after scaffold-init. Re-runnable with hash-based edit detection (per-section refresh / skip / diff). Judgment-only, no `.py` helper. | Yes (auto + explicit) |
| `/jig:memory-sync` | Persist domain terms, learnings, and project knowledge to the CLAUDE.md hot cache + `docs/memory/` + `docs/inbox.md`. | Yes (explicit) |
| `/jig:spec-workflow` | `workflow.py` for spec lifecycle: `new <slug>` reserves a spec number on `origin/main` (PR-fallback when push refused); `transition` **gates** REVIEWED / RECONCILED / DONE on recorded review evidence (ADR-0014 §5 — refuses without passing `compliance`/`craft`/`arch`/`reconciliation` verdicts + a deviation log; bypass `JIG_REVIEW_EVIDENCE_GATE=0`) and auto-ticks the two review-passed boxes *after* the gate clears; `status-board` regen (preserves Notes column; renders a 🔬 prefix on `kind: spike` rows in both active + deferred tables); `stale` audits `last_verified`; `amendments` (slice 048-04) prints a read-only, code-fence-aware digest of `## Amendments` overrides on closed records (specs + ADRs) so a reader sees current truth without rereading historical drift. Recognizes `kind: spike` slices (per spec 029) with a four-block body shape (Question / Time-box / Findings / Outcome) — see [docs/spec-workflow/spidr-primer.md](docs/spec-workflow/spidr-primer.md). | Yes (auto + explicit) |
| `/jig:independent-review` | `review.py` builds standardized prompts for implementation + reconciliation review, and records/validates verdict evidence: `record-review` writes `docs/specs/NNN-slug/reviews/slice-NN-<pass>.md` (overwrites in place), `check-reviews` validates the set for a transition stage (the `workflow.py transition` gate shares the validator). `subagent-type` picks `reviewer` (plugin install) or `general-purpose` (fallback). Reviewer prompts conditionally check declared contract surfaces and unconditionally check design-principle adherence. | Yes (auto + explicit) |
| `/jig:contracts` | Judgment-skill nudging toward standard external-interface artifacts (OpenAPI / JSON Schema / AsyncAPI / `.proto` / GraphQL SDL). Defers to richer user-installed `~/.claude/skills/contracts/`. | Yes (auto + explicit) |
| `/jig:adr-workflow` | `adr.py` helper: `new <slug>` reserves an ADR number on `origin/main` with PR-fallback (slice 028-01; mirrors `workflow.py new` per spec 003-03; `--no-push` / `--pr` flags; preflight refuses off-main and dirty trees; race-on-push drops both the stranded commit and the stranded ADR file) / `accept` / `supersede <old> <new>` (slice 005-02; appends `Superseded by [ADR-NNNN](./...) (date)` to old + `Supersedes ADR-NNNN` to new; refuses Proposed-/already-Superseded sides + self-supersession; both ADRs must be Accepted) / `index` / `resolve-todo`. Writes to `docs/decisions/adr-NNNN-<slug>.md`. | Yes (auto + explicit) |
| `/jig:tdd-loop` | `tdd.py` detect + run with normalized exit codes (0 green / 1 red / 2 env error). pytest > vitest > jest. `.jig/test-command` override file overrides auto-detection. | Yes (auto + explicit) |
| `/jig:slice-land` | `land.py prepare` emits readiness report (recognizes `### Close-out (post-DONE)` and excludes its checkboxes from the DoD count). `execute --mode direct` runs local merge; `execute --mode pr` runs `git push -u origin` + `gh pr create` with branch + gh-binary + github-remote guards. `--no-deviation-log` demotes the missing-deviation-log blocker to a warning. | Yes (auto + explicit) |
| `/jig:migrate` | `migrate.py` subcommands: `report` (read-only inventory), `rename-decisions` (ADR-0004 rename), `split-slices` (per-slice file split), `copy-machinery` (scaffold-mode parity for migrating projects; reads `installed_tiers` from the target `scaffold.json` to gate the copy, and `--add-tier <tier>` additively upgrades an already-scaffolded project to a higher tier without re-scaffolding — spec 038-04 / ADR-0012). Plus an agentic slice-to-spec workflow documented in SKILL.md. | Yes (auto + explicit) |
| `/jig:pr-review` | Lightweight baseline PR review (scope / blockers / nits / strengths). Judgment-only, no `.py` helper. Defers to richer user-installed `~/.claude/skills/pr-review`. | Yes (auto + explicit) |
| `/jig:arch-review` | Lightweight baseline architecture / design-doc / RFC review (summary / strengths / concerns / open questions). Judgment-only. Defers to richer user-installed skill if present. | Yes (auto + explicit) |
| `/jig:clarify` | Lightweight pre-spec ambiguity scan: six-category coverage taxonomy + up to 5 prioritized questions + appends a `## Clarifications` section. Judgment-only; ships without a category-based deferral hint. | Yes (auto + explicit) |
| `/jig:analyze` | Non-destructive cross-artifact consistency report. Six finding categories at CRITICAL / HIGH / MEDIUM / LOW; max 50 findings; stdout-only. Bundles the **constitution-gate**: an unconditional `_principles_check_block()` appended to both implementation + reconciliation reviewer prompts. | Yes (auto + explicit) |
| `/jig:security-review` | Slim Tier-1 baseline security review (summary / blockers / nits / strengths) over a diff. Judgment-only, no `.py` helper. Orchestrates installed scanners (semgrep / bandit / gosec / `npm audit` / osv-scanner) on `PATH` + degrades to a heuristic-only pass across 8 categories (secrets / injection / authn-authz / crypto / input-validation / deserialization / dangerous-functions / dependency-risk); category-based deferral to any richer installed security/SAST/vuln skill (`adobe-security-*` / user / built-in). Honest: best-effort floor, not a guarantee; secret *prevention* is the `jig-secret-scan` hook, this is *review*. Spec 052-05 / ADR-0013. | Yes (auto + explicit) |

## Session workflow

1. Check [docs/specs/README.md](docs/specs/README.md) for current status.
2. Pick up next `READY_FOR_IMPLEMENTATION` slice.
3. Spawn `implementer` subagent with the spec path.
4. After deliverable is on disk, run the post-implementation review — three passes: compliance via `jig:independent-review` (always), craft via `pr-review` (always), arch via `arch-review` (only when slice frontmatter has `arch_review: true`). See [docs/workflow.md](docs/workflow.md#post-implementation-review) and [skills/spec-workflow/SKILL.md](skills/spec-workflow/SKILL.md) § "After implementation" for the block rule.
5. Reconcile: update docs, write deviation log, run reconciliation review.
6. Run `/jig:memory-sync` to consolidate learnings.
7. Update spec status and status board.

## Constraints for agents working on this repo

- Do not modify [docs/conventions.md](docs/conventions.md) without explicit human approval.
- Reviewer subagent has read-only tools (Read, Glob, Grep). It cannot write to memory.
- [templates/CLAUDE.md.template](templates/CLAUDE.md.template) is the source template for scaffold-init. Do not confuse it with this file.
- Hook commands use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` — never bare names.
- All hook scripts use Python 3 for JSON parsing — never jq.
- ADRs live at `docs/decisions/adr-NNNN-<slug>.md` (per ADR-0004). `adr.py` writes new ADRs there.
- Spec slices live in sibling files: `docs/specs/NNN-<slug>/slice-NN-<short>.md` (per spec 018). The `spec.md` is the overview; each slice is its own file.
- When a slice closes a spec, **compress** the spec's "Active specs" entry above per the rule in the slice template's `### Close-out (post-DONE)` section (per spec 025-01). Load-bearing per-slice invariants migrate to the status board Notes column, not to CLAUDE.md.
