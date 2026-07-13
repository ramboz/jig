> Status: Draft (hand-seeded as the worked-example artifact for [spec 017](specs/017-vision-elicitation/spec.md))
>
> This document captures *why* jig exists, *for whom*, and *with what
> principles*. Architectural mechanics live in [architecture.md](architecture.md).
> Update via reconciliation, or via `/jig:vision-elicitation` (shipped in spec 017).

# Vision: jig

## Vision statement

A small, opinionated workflow scaffold for Claude Code and Codex that installs
AI-native development practices — spec-driven slices, independent review,
memory continuity, deterministic gates — into a project on day 1, and gets out
of the way after.

> *jig (noun): a tool that guides other tools to work accurately and
> consistently.*

## Target users

- **Devs starting a new AI-native project in Claude Code or Codex** who want a
  structured workflow on day 1 instead of inventing one over the first
  three sprints.
- **Devs adopting AI-native practices on an existing project** —
  served by the sibling `/jig:migrate` skill rather than `scaffold-init`.
- **Teams who want a thin, opinionated baseline** they can extend with
  their own richer skills (jig's extension-point pattern lets user
  skills override jig's baselines without configuration).
- **Solo devs who want sane defaults** without committing to a
  100-skill mega-pack that fills the context window.

**Not for:** devs who want a maximalist skill marketplace; devs who
want their tooling to make architectural decisions for them.

> **Deciding whether to adopt jig?** See the
> [adoption & readiness guide](adoption-readiness.md) — who it's for, who
> should wait, prerequisites, and a readiness checklist.

## The core problem

Claude Code and Codex are powerful but deliberately unopinionated about
*project workflow*. Teams adopting them tend to land in one of three places:

1. **Build the workflow yourself, slowly.** Each project re-invents
   spec discipline, review gates, memory conventions, and
   deterministic enforcement. Two months in, the team still doesn't
   have it right, and lessons don't carry across projects.
2. **Install a sprawling skill pack** (e.g. ECC's ~48 subagents, large
   skill marketplaces). The toolset works, but ~40% context fill is
   the practical ceiling for model recall (the "dumb zone"), and a
   mega-pack blows through it before the dev's actual work loads.
3. **Hand-roll team conventions in CLAUDE.md or AGENTS.md.** Common;
   expensive; non-portable; no enforcement.

There's a gap in the middle: **a focused, opinionated, *extensible*
workflow layer that respects context economy and dogfoods its own
conventions.** That's what jig is.

### The positioning recovery (2026-05 audit)

A user-led audit in May 2026 surfaced that jig was drifting from its
original framing — *"scaffolding library: puts the machinery in your
repo, then gets out of the way"* — toward an install-and-forget plugin
where the machinery lives under `${CLAUDE_PLUGIN_ROOT}` and stays
opaque to the dev. **The dev should own and extend the scaffolding,
not depend on a plugin runtime they can't see.** [Spec 016](specs/016-scaffold-mode/spec.md)
shipped dual-mode install (plugin OR scaffolded-in-repo) to recover
that framing, and [spec 017](specs/017-vision-elicitation/spec.md)
closed the second half by adding content-guidance at init time so a
new project leaves the wizard with a real vision + architecture seed,
not three "Deferred — no signal" stanzas.

## Competitive landscape

| Option | What it does | Where it falls short for this gap |
|---|---|---|
| **Built-in Claude Code skills** (`review`, `init`, `security-review`) | Generic single-skill helpers | No workflow stitching; no spec discipline; no memory continuity |
| **anthropic-skills marketplace** (`skill-creator`, `consolidate-memory`, `pdf`, `xlsx`, …) | Atomic, well-designed skills | Each is excellent at one thing; none impose a project workflow |
| **Large skill packs (ECC-style)** | Maximalist coverage | Context-window cost; tools you don't use crowd out the ones you do; no clear "shape" for new projects |
| **Hand-rolled team CLAUDE.md** | Tailored to one team | Expensive to author; non-portable; no enforcement; rots |
| **claude-code-templates-style boilerplate** | Solves day-1 layout | Static — no living workflow, no reviewer subagent, no spec lifecycle |

**Where jig fits:** between "atomic skills" and "maximalist packs" —
a fixed-size opinionated workflow layer (7 Tier 0 + **13** Tier 1
skills, 3 subagents) that ships with the templates, hooks, and helpers
to enforce it, and that defers to richer user-installed skills where
they exist.

## Core features (prioritized)

Jig ships in **tiers** so the install size matches the project's
signal, not jig's wish list. See [docs/memory/glossary.md](memory/glossary.md)
for tier definitions.

### Tier 0 — always installs (the floor)

The minimum coherent workflow. Nothing useful without all seven.

1. **`scaffold-init`** — generate docs/, the host primer (`CLAUDE.md` or
   `AGENTS.md`), and host hook/skill config
2. **`memory-sync`** — cross-session continuity; hot cache + deep storage + inbox
3. **`spec-workflow`** — SPIDR-split slices; DRAFT → DONE state machine; status board
4. **`independent-review`** — reviewer subagent with a fresh prompt and read-only tools. Owns the compliance pass (always) and the reconciliation pass; also builds the verdict-envelope prompts that wrap the Tier 1 `pr-review` + `arch-review` skills when `spec-workflow` invokes them.
5. **`migrate`** — sibling entry path for projects that already have specs
6. **`vision-elicitation`** — lightweight wizard that fills the elicitation slots in this document and `architecture.md` after `scaffold-init`; re-runnable with hash-based edit detection (per-section refresh / skip / diff)
7. **`contracts`** — judgment-skill nudging toward standard external-interface artifacts (OpenAPI / JSON Schema / AsyncAPI / `.proto` / GraphQL SDL); defers to richer user skills. Deliberate stub per [ADR-0002](decisions/adr-0002-contracts-stays-deferred.md), still installed at Tier 0.

### Tier 1 — default-on (the working surface)

Enabled by default; can be disabled per install. These are the daily
drivers once Tier 0 is in place.

8. **`adr-workflow`** — capture decisions; resolve refinement-todo entries
9. **`tdd-loop`** — auto-detected test runner; normalized exit codes (0/1/2)
10. **`slice-land`** — readiness check + landing checklist (direct merge or PR)
11. **`pr-review`** — slim baseline four-section review; defers to richer user skills. `spec-workflow` invokes it automatically as the **craft pass** of the post-implementation review (always runs).
12. **`arch-review`** — slim baseline architecture / RFC / design-doc review; same deferral pattern. `spec-workflow` invokes it automatically as the **arch pass** of the post-implementation review, **on-demand** when the slice's frontmatter declares `arch_review: true`.
13. **`clarify`** — slim baseline pre-spec ambiguity scan; six-category coverage + up to 5 prioritized questions appended as `## Clarifications` (per spec 023, **no** deferral hint to spec-kit per explicit user direction 2026-05-18)
14. **`analyze`** — non-destructive cross-artifact consistency report; six finding categories with CRITICAL/HIGH/MEDIUM/LOW severity. Bundles the constitution-gate (per spec 024 AC #6 — `_principles_check_block()` appended unconditionally to every reviewer prompt). Same no-deferral-hint stance as clarify
15. **`security-review`** — slim baseline security review; orchestrates installed scanners (semgrep / bandit / gosec / npm audit / osv-scanner) + defers to a richer installed security skill (the user's own, Adobe's `adobe-security-*`, or a built-in `security-review`) via the same per-skill deferral pattern as `pr-review`. Heuristic-only floor when no scanner is present (per [ADR-0013](decisions/adr-0013-security-floor-policy.md))
16. **`code-health`** — the static-analysis sibling of `tdd-loop`: detects the project's linter and drives it via `health.py` with normalized exit codes (0 clean / 1 findings / 2 no-linter). Scope today is Python + ruff (resolved on PATH or ephemerally via `uvx` / `pipx`); degrades to a recommendation when no linter is present and defers to a richer installed lint/static-analysis skill (per [ADR-0017](decisions/adr-0017-scaffolded-code-health.md))
17. **`explain`** — on-demand vocabulary/artifact explainer (third consumer of the shipped lexicon): term mode defines a single jig term from the merged lexicon (shipped + project-glossary overlay) and flags an absent term rather than inventing one; artifact mode produces a junior-grade walkthrough of a spec/ADR, auto-pulling the refs it links. Ephemeral (chat-only), judgment-only/no-`.py`; defers to a richer installed plain-language/onboarding/walkthrough skill (per spec 065)
18. **`bug-fix`** — proportional, teeth-gated bug-fix workflow (peer of `spec-workflow`, owns its orchestration) backed by `bug.py`: diagnose-before-fix gate (≥2 hypotheses) + red→green teeth that witness the regression test fail before the fix and pass after, a durable `docs/bugs/NNN-slug.md` record + board, and de-escalation (trivial bugs bow out to `tdd-loop`). Reuses the ADR-0014 evidence gate; only the craft (`pr-review`) and conditional security (`security-review`) passes defer (per [ADR-0016](decisions/adr-0016-bug-fix-lifecycle.md))
19. **`reframe`** — re-baseline the corpus when a load-bearing reference moves (a design system, vendor / API contract, test infra, compliance regime, target platform, or product-positioning / strategic-vision shift): reads the accepted corpus against the new reference and drafts a **keystone reframe-ADR** (new reference authoritative, old premise superseded) + a re-baselining manifest assigning every affected artifact a disposition + a two-level coverage floor; a competent session then executes through the existing ADR / spec lifecycles. A lightweight correction *capability over the spine* (not a gated lifecycle member); judgment-only, no `.py`; defers to a richer installed re-baselining skill (per spec 067 / [ADR-0024](decisions/adr-0024-reference-reframe.md))
20. **`compass`** — the calm "what's next" briefing: surveys the project's own artifacts (spec status boards + slice STATUS markers, `Proposed` ADRs, DEFERRED slices and their triggers, refinement-todo, release plans, the inbox, standalone bugs) and answers in one fixed, readable shape — an honest headline, titled sections, a single recommendation, and an offer to hand off to the skill that owns the work. Read-only about lifecycle/spec state; its one write is an append-only run log at `docs/status/compass-history.jsonl` so runs become a trackable data point over time. Judgment-only, no `.py`; defers to a richer installed "status / what's next" skill

### Tier 2 — opt-in by signal (deferred until pain reported)

Hypothetical. Only one candidate today (`local-dev-parity`) and no
user signal yet. Tier 2 stays empty until pain is reported.

### MVP scope (already shipped)

Tier 0 + Tier 1 are both **complete** — all 20 skills ship today
(the original floor plus later Tier 1 additions: `code-health`,
`explain`, `bug-fix`, `reframe`, `compass`, and the rest). See [docs/specs/README.md](specs/README.md)
for the live status board.

### Out of scope (deliberately)

- **Project management surface.** No backlog rendering, no estimation,
  no roadmap visualization. Specs are the only project state.
- **Auto-coding from the elicited spec.** Elicitation produces *docs*
  (vision, architecture, draft ADRs). Implementation is still
  `/jig:spec-workflow` + `implementer` subagent.
- **Polyglot test runner support beyond pytest/vitest/jest.** Add
  others when a real project hits the gap.
- **A web UI, dashboard, or external service.** Jig is a pair of host-native
  plugins plus scaffolded project files. That's the whole product.

## Design principles

These are load-bearing — every spec is judged against them at
reconciliation.

1. **Hooks are deterministic; skills carry judgment.** *Everything
   that MUST happen is a hook. Everything that should happen when
   relevant is a skill.* Determinism is non-negotiable; pattern-matched
   skill triggering is a probabilistic best-effort.
2. **Stay below the dumb zone (~40% context fill).** Practical
   ceiling: 8 MCP servers, ~80 active tools. Skills use progressive
   disclosure: body loads only on trigger; supporting files load only
   when referenced. `jig-context-check` warns at session start.
3. **Three subagents, no more — defined by isolation, not job title.**
   `implementer` (TDD, writes), `reviewer` (read-only tools, fresh
   prompt), `architect` (rare, ADR-style output). New subagent shapes
   require a new isolation argument, not a new role description.
   ("Isolation" here is permission- and prompt-scope — read-only tools
   are a real, enforced boundary; the fresh prompt is not a hard
   context sandbox. See `skills/independent-review/SKILL.md` § Context
   isolation pattern.)
4. **Dogfood the workflow we build.** Every jig feature is built using
   jig's own spec lifecycle. The repo's `docs/` is the worked example
   of what `scaffold-init` produces — including this vision document
   (and the audit gap it closes).
5. **Bring your own depth; jig provides the floor.** Where jig ships a
   "lightweight baseline" skill, **the deferral pattern is per-skill,
   not universal**. Some baselines carry a *category-based deferral
   hint* in their auto-trigger description so a richer user-installed
   skill in the same category wins without configuration (today:
   `pr-review`, `arch-review`, `contracts`); others ship as standalone
   baselines when the user explicitly prefers jig's version remain the
   primary entry point (today: `clarify`, `analyze` — per the
   2026-05-18 spec-kit-gap-analysis decision). Both shapes honor the
   principle: jig stays opinionated about *workflow* and out of the way
   of *judgment skills the user has invested in* — the only question is
   whether the user has installed a richer alternative they want
   auto-routed to, or whether jig's baseline is the right standalone
   default for that surface.
6. **No backwards-compat shims when conventions change.** When a
   convention is wrong, flip it wholly (e.g. ADR-0004's `docs/adrs/`
   → `docs/decisions/` rename was a clean cut, not a dual-read
   transition). Backwards-compat is a tax on every future spec; pay
   the migration cost once instead.
7. **Owning the scaffolding beats renting the plugin.** Default install
   mode after [spec 016](specs/016-scaffold-mode/spec.md) and the v2
   host-adapter work puts the machinery (`skills/`, `agents/`, `hooks/`)
   in the dev's host-native project directory (`.claude/` or `.codex/`)
   where it can be read, modified, and extended. Plugin mode stays
   available for users who want it; scaffolded mode is the default
   because positioning matters.
8. **Designed to reduce token cost.** Beyond keeping context below the
   dumb zone for *quality* (principle #2), jig is built to keep token
   usage — and the bill — *down*: it favors a lean context, delegates
   file-heavy reading to subagents, and keeps output tight, so a session
   costs less to run. jig also measures its own spend rather than guessing
   at it. Mechanics and evidence live in the specs and ADRs.

## How new work enters jig

Jig grows by **signal**, not by speculation. A new spec is justified
when one of the following lands:

- **User signal**: a real pain hit two or more times across sessions,
  or once and clearly load-bearing.
- **Dogfooding revelation**: a gap found while using jig on jig
  (e.g. [spec 009](specs/009-dod-close-out-separation/spec.md)
  separated post-DONE close-out items from blocking DoD checks after
  the chicken-and-egg hit slice 008-01).
- **Cross-project comparison**: a pattern that recurs in multiple
  projects (e.g. [spec 015](specs/015-structured-lifecycle-metadata/spec.md)
  was born from comparing spec frontmatter across projects).

Speculative tier promotion — "what if we also shipped X?" — is
explicitly disallowed. Tier 2 stays empty until a real user reports
real pain.

## Future scope

Track in [docs/specs/README.md](specs/README.md) and
[docs/refinement-todo.md](refinement-todo.md). High-level horizon:

- **Multi-host portability** — shipped in the v2 line through the
  host-adapter layer for Claude Code and Codex
  ([spec 033](specs/033-host-adapter-portability/spec.md)). The next
  horizon is a multi-repo federation tier
  ([spec 034](specs/034-federation-tier/spec.md)), tracked in
  [docs/roadmap.md](roadmap.md).
- **Tier 2 stays empty** until `local-dev-parity` (or another
  candidate) gets a real user signal.
- **`contracts` skill stays a deliberate stub** ([ADR-0002](decisions/adr-0002-contracts-stays-deferred.md))
  until a third caller needs the duplicated lookup logic.

## References

- [README.md](../README.md) — install + entry points
- [docs/architecture.md](architecture.md) — technical mechanics; this
  vision document supplies the *why*, architecture.md supplies the *how*
- [docs/workflow.md](workflow.md) — spec lifecycle, session workflow
- [docs/specs/README.md](specs/README.md) — current status board
- [docs/specs/016-scaffold-mode/spec.md](specs/016-scaffold-mode/spec.md)
  — positioning recovery (mechanical)
- [docs/specs/017-vision-elicitation/spec.md](specs/017-vision-elicitation/spec.md)
  — positioning recovery (content) — this document is its worked-example artifact
