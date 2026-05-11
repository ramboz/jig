# Claude Code Starter Prompt: AI-Native Dev Scaffold

> Paste everything below the `---` as the first message in a new Claude Code
> session, in an empty directory where you want the skill pack repo to live.

---

# Project: AI-Native Dev Scaffold (Claude Code skill pack)

## What we're building

A Claude Code skill pack that scaffolds AI-native development practices into new projects. The skill pack provides:

- A wizard for initializing new projects (greenfield in v1; existing-repo migration in v2)
- Spec-driven development workflow with SPIDR-based vertical slicing
- Independent reviewer pattern enforced via subagents with isolated context
- Hook-enforced gates for spec compliance, review completeness, and test passing
- TDD by default; EDD (eval-driven development) opt-in based on project signals (LLM/agent/prompt detection)
- Strong typed contracts at module boundaries to enable parallel AI-driven work
- Documentation that stays aligned with implementation via reconciliation, not drift

The north star: **intuitive automated triggering at the right moments, over explicit calls.** Developers should not have to memorize a command surface. Skills auto-trigger via well-crafted descriptions; hooks deterministically enforce gates that skills might miss.

## Why we're building it

Existing solutions (ECC, Spec Kit, cc-sdd) are either too heavy (kitchen-sink installs with 100+ skills, cognitive overload, duplicate-install foot-guns) or too light (just templates, no enforcement). We want a focused, opinionated, auto-triggered skill pack — 8–12 skills, 3 subagents, hooks for deterministic gates. Composable, not monolithic.

## Decisions already made

### Architecture
- **Skill pack, not monolith.** Tiered: Tier 0 (always installed, 4 skills), Tier 1 (default for most projects, 4 skills), Tier 2 (opt-in by signal, 4 skills).
- **Claude Code first** in v1. Design for portability later (core logic + adapters), but don't build adapters yet.
- **Auto-triggered skills over explicit commands.** Every skill description follows: `<verb-led summary>. Use when <specific triggers>. Do not use for <common false positives>.`
- **3 subagents only**, defined in `.claude/agents/`: `implementer`, `reviewer`, `architect`. (Optional 4th: `researcher` for spec discovery.) Sharp system prompts, narrow tool access, fresh context per invocation.
- **Hooks are the deterministic spine; skills are the LLM layer.** Hooks enforce gates that don't require judgment. Skills carry the workflows.

### Independent reviewer pattern
- Subagents in Claude Code don't fully isolate context (parent context leaks to spawned agents). Open issue #20304 confirms this.
- Workaround: implementer writes deliverable to disk → reviewer spawned via Task with system prompt that forbids referring to prior context → reviewer reads only spec, deliverable, acceptance criteria.
- Reviewer fires on `SubagentStop` of implementer, deterministically, via hook.
- This pattern also applies to the **reconciliation review** (see below).

### Spec-driven workflow
- SPIDR for spec splitting (Spike, Path, Interface, Data, Rules), with Spike as last resort not first. Enforce vertical slicing — anti-horizontal-phasing guardrail in the spec-workflow skill.
- Spec lifecycle states: `DRAFT` → `READY_FOR_REVIEW` → `READY_FOR_IMPLEMENTATION` → `IN_PROGRESS` → `REVIEWED` → `RECONCILED` → `DONE`.
- Each spec slice has explicit Definition of Done.

### Reconciliation (after implementation, before "done")
- Reviewer runs against the **original** spec, not the reconciled one. Reconciliation happens *after* reviewer pass.
- Reconciliation produces a **deviation log**: what changed during implementation and why. Surfaces drift honestly rather than papering over it.
- Updates: specs get deviation log annotations (original preserved); `architecture.md` only if module boundaries / contracts changed (signal to write an ADR); ADRs never edited after acceptance (superseded by new ADRs); `conventions.md` requires explicit human approval to change.
- A **second reviewer pass** runs on the reconciliation itself: are doc changes faithful, explained, properly scoped?
- The Stop hook blocks completion if reconciliation hasn't happened.

### Repository structure (output of the wizard)

```text
docs/
├── architecture.md       # light, grows over time
├── workflow.md           # how we build (the dev cycle)
├── conventions.md        # project rules and best practices
├── refinement-todo.md    # explicit list of wizard-deferred decisions
├── specs/
│   ├── README.md         # status board
│   └── NNN-feature/
│       ├── spec.md       # SPIDR-split, status-tracked
│       ├── plan.md       # technical plan
│       └── tasks.md      # task breakdown
└── adrs/
    ├── README.md
    └── NNNN-decision.md  # Nygard convention, immutable post-acceptance

contracts/                # typed contracts at module boundaries
.claude/
├── skills/               # the skill pack
├── agents/               # implementer, reviewer, architect
├── hooks/                # hooks.json + scripts
└── scaffold.json         # install state manifest (for v2 migration / cleanup)
CLAUDE.md                 # references docs/ + .claude/
```

### The wizard (scaffold-init skill)
- Produces **80% of the scaffolding**; the remaining 20% accretes from the first 2–3 specs.
- Every wizard-generated doc gets a `Status: Draft (wizard-generated)` marker at the top.
- Wizard explicitly **defers** decisions it doesn't have signal for, rather than inventing plausible-but-fictional content. Pattern: `> **Deferred — no signal from initial pitch.** Will be decided in the first <X>-touching spec via ADR.`
- After specs 1, 2, and 3 reconcile, a **scaffold reconciliation** check fires (skill, not hook — needs judgment) — does the scaffolding itself need updating based on what we learned? After 3–5 stable specs, scaffolding stability gets marked via a `scaffold-stable` ADR; the `Draft` markers flip to `Stable`.
- The wizard does **discovery routing**, not "generate everything" — borrowed from cc-sdd's `/kiro-discovery` pattern. Outputs a `brief.md`, decides which tiers to install.

### Skill design conventions
- Descriptions auto-trigger via the template above. Negative clauses ("Do not use for...") matter as much as positive ones.
- One skill, one job. No mega-skills. 8–12 total in the pack.
- Each skill has a `## Gotchas` section that accumulates failure points over time.
- Progressive disclosure: SKILL.md is concise, supporting files (`FORMS.md`, `REFERENCE.md`, scripts) loaded as needed.
- `disable-model-invocation: true` for skills with side effects (deploy-style). `user-invocable: false` for background-knowledge skills that aren't meaningful as commands.

### Telemetry on day one
- A PreToolUse hook on Task logs every skill invocation to `.claude/skill-usage.jsonl` (gitignored). This is the feedback loop — after a week or two of real use, we can see which descriptions are too vague (never fire) or too broad (fire on irrelevant prompts).

### Hook strictness profiles
- Borrowed from ECC: `minimal | standard | strict`. Same hooks, different gate enforcement levels. Wizard picks the default based on team maturity signals.

### What's explicitly out of scope for v1
- Cross-harness portability (Cursor, Codex, etc.) — design for it but don't build adapters
- Migration of existing repos — v2 territory
- Hosted skills marketplace, dashboards, security scanners (ECC sprawl we're explicitly avoiding)
- Generated project-tailored skills (probably v1.5 — useful but secondary)

## Tier 0 skills (always installed) — what we're starting with

1. **`scaffold-init`** — the wizard. Discovery routing. Outputs `brief.md`, the docs/ scaffolding, `refinement-todo.md`, hooks, agent definitions. Decides which other tiers to install.
2. **`spec-workflow`** — auto-triggers when user describes non-trivial work. Enforces SPIDR splitting, vertical slicing, Definition of Done per slice. Manages spec lifecycle states.
3. **`independent-review`** — auto-triggers on `SubagentStop` of implementer. Spawns fresh reviewer with isolated system prompt. Also handles reconciliation review.
4. **`contracts`** — auto-triggers when work touches module boundaries. Enforces typed contracts at interfaces. Generates contract test scaffolding.

Tier 1 (`tdd-loop`, `local-dev-parity`, `pr-review`, `adr-workflow`) and Tier 2 (`eval-harness`, `e2e-testing`, `migration-mode`, `skill-stocktake`) come later.

## How to approach the build

1. **Build Tier 0 first, dogfooding as we go.** Use Claude Code to build `scaffold-init` while running in a project that itself is being scaffolded by `scaffold-init`. The friction surfaces design bugs early.

2. **Test the independent reviewer pattern on the skills themselves.** While building `spec-workflow`, spawn a reviewer subagent on the spec for it. If the review loop is annoying or unreliable, the design has a bug we need to fix before shipping.

3. **Telemetry hook on day one.** Before any skill is written, install the PreToolUse hook on Task that logs invocations. This is the feedback loop.

4. **Use git worktrees for parallel work on independent skills.** Each Tier 0 skill in its own worktree, so we can dogfood the "parallel agentic development" pattern.

## Starting move

Let's start with the repository structure for the skill pack itself. Initialize a git repo, set up the directory layout for an installable Claude Code skill pack (referring to <https://code.claude.com/docs/en/skills> for the SKILL.md format and <https://code.claude.com/docs/en/hooks-guide> for hooks), and set up the telemetry hook on the Task tool before we write a single skill.

Then we draft the `scaffold-init` skill's spec — yes, we're spec-driven from move one. The spec for `scaffold-init` will itself be SPIDR-split, and we'll dogfood the independent reviewer pattern on it.

Be opinionated. Push back on anything in the decisions above if you spot a problem. Surface trade-offs explicitly. When uncertain about Claude Code API specifics (skill frontmatter fields, hook event names, subagent invocation patterns), check the docs rather than assuming.

## Additional context available

The decisions above were the output of several rounds of research and design. If at any point you need deeper background, the following research notes are available (saved alongside this prompt):

- `01-research-skills-and-triggering.md` — how Claude Code skills auto-trigger, description patterns, what makes them fire reliably
- `02-research-hooks.md` — hook events, patterns, gotchas, the deterministic-spine role
- `03-research-subagents-and-isolation.md` — context isolation findings (the critical caveat), orchestrator-worker pattern, sub-agent count rationale
- `04-research-spec-driven-and-spidr.md` — Spec Kit, cc-sdd, SPIDR splitting techniques in detail
- `05-research-eval-driven-development.md` — EDD framing, grader types, when to opt in
- `06-research-12-factor-and-operations.md` — Dex Horthy's principles, the "dumb zone," context economics
- `07-research-contracts-and-architecture.md` — typed contracts as leverage point for AI-native dev
- `08-research-ecc-lessons.md` — what to steal and what to skip from everything-claude-code

Pull these into context only when relevant to the decision at hand — they're reference material, not session bootstrap.
