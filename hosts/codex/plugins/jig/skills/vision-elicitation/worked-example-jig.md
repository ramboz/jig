# Worked example: vision-elicitation against jig's own pitch

> **Purpose.** Demonstrates the 12-section Q&A flow run against jig's
> pitch (README "what it does" + the audit-stage positioning-recovery
> story). Shows question → answer → rendered section heading + body
> for each section, so the elicitation skill's output shape is
> grounded in a concrete example.
>
> **Structural acknowledgment.** The hand-seeded
> [`docs/product-vision.md`](../../docs/product-vision.md) predates
> the vision template (`templates/docs/product-vision.md.template`)
> and uses bespoke H2 names — "Vision statement" instead of
> "Identity", "The core problem" instead of "Core problem", "Future
> scope" instead of an Open questions section, etc. The elicitation
> skill is **template-driven**: it produces output with the template's
> 9 H2s, regardless of what the hand-seeded artifact looks like. This
> worked example shows the template-shaped output and annotates the
> divergence inline.

## Pitch ingested

From [README.md](../../README.md) and the audit-stage conversation
recorded in [docs/specs/016-scaffold-mode/spec.md](../../docs/specs/016-scaffold-mode/spec.md):

> jig is a Claude Code plugin that scaffolds AI-native development
> practices into new projects: spec-driven slices, independent
> review, memory continuity, deterministic gates. A user audit
> surfaced that it had drifted from its original "scaffolding library"
> framing toward an "install-and-forget plugin" shape; specs 016 and
> 017 close that gap.

## The 12-section walk-through

### Section 1 — Identity

**Skill asks Q1.1:** *"In one sentence, what does this project do?"*

**User answers:** *"A small, opinionated Claude Code plugin that
scaffolds AI-native development practices — spec-driven slices,
independent review, memory continuity, deterministic gates — into
a project on day 1, and gets out of the way after."*

**Skill asks Q1.2 (optional tagline):** *"If you were defining the
project's name as a noun, what's its essence?"*

**User answers:** *"jig (noun): a tool that guides other tools to
work accurately and consistently."*

**Skill asks Q1.3 (optional positioning story):** *"Is there a
positioning story worth recording?"*

**User answers:** *"Yes — a user-led audit in 2026-05 found jig had
drifted from 'scaffolding library' (files-in-your-repo, dev owns
and extends) toward 'install-and-forget plugin' (machinery under
${CLAUDE_PLUGIN_ROOT}, opaque to the dev). Spec 016 closes the gap
mechanically; spec 017 closes the content half."*

**Skill renders into `## Identity`:**

```markdown
## Identity

<!-- elicited: 2026-05-15 / status: filled -->

- **Vision statement:** A small, opinionated Claude Code plugin that
  scaffolds AI-native development practices — spec-driven slices,
  independent review, memory continuity, deterministic gates — into
  a project on day 1, and gets out of the way after.
- **Tagline:** jig (noun): a tool that guides other tools to work
  accurately and consistently.
- **Positioning story:** A user-led audit in 2026-05 found jig had
  drifted from "scaffolding library" toward "install-and-forget
  plugin." Spec 016 closes the gap mechanically; spec 017 closes
  the content half.
```

**Hand-seeded divergence.** [`docs/product-vision.md`](../../docs/product-vision.md)
labels this section `## Vision statement` (only) plus a separate
sub-section "The positioning recovery (2026-05 audit)". The
template's `## Identity` is one bucket for vision + tagline + story
together — broader by design.

### Section 2 — Target users

**Skill asks Q2.1:** *"List 2–4 specific user types this project
serves."*

**User answers:**
- Devs starting a new AI-native project on Claude Code
- Devs adopting AI-native practices on an existing project
- Teams who want a thin, opinionated baseline to extend
- Solo devs who want sane defaults

**Skill asks Q2.2:** *"Who is this *not* for?"*

**User answers:**
- Devs who want a maximalist skill marketplace
- Devs who want their tooling to make architectural decisions for them

**Skill renders into `## Target users`:**

```markdown
## Target users

<!-- elicited: 2026-05-15 / status: filled -->

**For:**
- Devs starting a new AI-native project on Claude Code
- Devs adopting AI-native practices on an existing project
- Teams who want a thin, opinionated baseline to extend
- Solo devs who want sane defaults

**Not for:**
- Devs who want a maximalist skill marketplace
- Devs who want their tooling to make architectural decisions for them
```

**Hand-seeded match.** Direct match with
[`docs/product-vision.md`](../../docs/product-vision.md) section
of the same name; H2 label is identical.

### Section 3 — Core problem

**Skill asks Q3.1:** *"Describe the problem in 2–3 sentences."*

**User answers:** *"Claude Code is powerful but deliberately
unopinionated about project workflow. Teams adopting it land in
one of three places: build the workflow themselves slowly, install
a sprawling skill pack that fills the dumb zone, or hand-roll
conventions in CLAUDE.md."*

**Skill asks Q3.2:** *"Enumerate the 2–3 paths users take today
and where each falls short."*

**User answers:**
1. Build it yourself — slow, lessons don't carry across projects
2. Sprawling skill pack — context window cost; ~40% fill ceiling
3. Hand-rolled CLAUDE.md — common, expensive, non-portable

**Skill renders into `## Core problem`:**

```markdown
## Core problem

<!-- elicited: 2026-05-15 / status: filled -->

Claude Code is powerful but deliberately unopinionated about project
workflow. Teams adopting it land in one of three places: build the
workflow themselves slowly, install a sprawling skill pack that fills
the dumb zone, or hand-roll conventions in CLAUDE.md.

**Today's paths and where they fall short:**
1. Build it yourself — slow, lessons don't carry across projects
2. Sprawling skill pack — context window cost; ~40% fill ceiling
3. Hand-rolled CLAUDE.md — common, expensive, non-portable
```

**Hand-seeded divergence.**
[`docs/product-vision.md`](../../docs/product-vision.md) labels
this section `## The core problem` (with the article "The"). The
template drops the article for terseness.

### Section 4 — Competitive landscape

**Skill asks Q4.1, Q4.2, Q4.3 (per alternative), Q4.4 (positioning):**

**User answers:**
- Built-in Claude Code skills: generic single-skill helpers; no workflow
- anthropic-skills marketplace: atomic, well-designed; no opinionated workflow
- Large skill packs (ECC-style): maximalist coverage; context-window cost
- Hand-rolled team CLAUDE.md: tailored; expensive, non-portable
- Where jig fits: a fixed-size opinionated workflow layer between atomic skills and maximalist packs

**Skill renders into `## Competitive landscape`:**

```markdown
## Competitive landscape

<!-- elicited: 2026-05-15 / status: filled -->

| Option | What it does | Where it falls short |
|---|---|---|
| Built-in Claude Code skills | Generic single-skill helpers | No workflow stitching |
| anthropic-skills marketplace | Atomic well-designed skills | No opinionated workflow |
| Large skill packs (ECC-style) | Maximalist coverage | Context-window cost |
| Hand-rolled team CLAUDE.md | Tailored to one team | Expensive, non-portable |

**Where jig fits:** between atomic skills and maximalist packs — a
fixed-size opinionated workflow layer (7 Tier 0 + 10 Tier 1 skills,
3 subagents) that ships with templates, hooks, and helpers.
```

**Hand-seeded match.** Same H2 name in
[`docs/product-vision.md`](../../docs/product-vision.md); same table
shape.

### Section 5 — Scope

**Skill asks Q5.1, Q5.2, Q5.3, Q5.4:**

**User answers:**
- Core features: scaffold-init, memory-sync, spec-workflow, independent-review, migrate, vision-elicitation, contracts (Tier 0); adr-workflow, tdd-loop, slice-land, pr-review, arch-review, clarify, analyze, security-review, code-health, explain (Tier 1); local-dev-parity (Tier 2, deferred)
- Tier clustering: yes — Tier 0 / Tier 1 / Tier 2
- MVP: Tier 0 + Tier 1 (already shipped)
- Out of scope: project-management surface; auto-coding; polyglot test runners; web UI

**Skill renders into `## Scope`:**

```markdown
## Scope

<!-- elicited: 2026-05-15 / status: filled -->

### Core features (prioritized)

Tier 0 (always installs): scaffold-init / memory-sync / spec-workflow /
independent-review / migrate / vision-elicitation / contracts.
Tier 1 (default-on): adr-workflow / tdd-loop / slice-land / pr-review /
arch-review / clarify / analyze / security-review / code-health / explain.
Tier 2 (opt-in by signal): local-dev-parity (deferred — no user signal).

### Tiers / phases

Three-tier install model: Tier 0 always, Tier 1 default-on, Tier 2
opt-in by signal.

### MVP scope

Tier 0 + Tier 1 — already shipped as of 2026-05-15.

### Out of scope (deliberately)

- Project management surface (no backlog rendering)
- Auto-coding from the elicited spec
- Polyglot test runners beyond pytest/vitest/jest
- Web UI / dashboard / external service
```

**Hand-seeded divergence.**
[`docs/product-vision.md`](../../docs/product-vision.md) has
`## Core features (prioritized)` directly as an H2 plus separate
`## Future scope` and `## References` H2s. The template's `## Scope`
groups the prioritized features + tiers + MVP + non-goals under
one bucket — broader/tighter by design.

### Section 6 — Repository structure *(feeds architecture.md)*

**Skill asks Q6.1:** *"What's the top-level directory layout?"*

**User answers:** *"6 top-level concerns: skills/, agents/, hooks/,
templates/, scripts/, .claude-plugin/."*

**Skill renders into `architecture.md ## Repository structure`:**

```markdown
## Repository structure

<!-- elicited: 2026-05-15 / status: filled -->

```
jig/
├── .claude-plugin/        # Plugin manifest + marketplace descriptor
├── skills/                # SKILL.md per skill + tests
├── agents/                # 3 subagent definitions
├── hooks/                 # hooks.json + Python 3 scripts
├── scripts/               # Python helpers per skill (one per skill)
├── templates/             # Source templates scaffold-init copies
└── docs/                  # Dev docs for jig itself (dogfooded)
```
```

### Section 7 — Tech stack *(feeds architecture.md)*

**Skill asks Q7.1, Q7.2, Q7.3:**

**User answers:**
- Runtime: Python 3 for helpers; Markdown for skill content; Bash for hook scripts
- Platform: Claude Code (plugin runtime) + GitHub (release pipeline)
- Locked-in: Python 3, Bash, ${CLAUDE_PLUGIN_ROOT} for hook paths
- Open: AGENTS.md sibling (deferred until non-Claude-Code user signal)

**Skill renders into `architecture.md ## Tech stack`:**

```markdown
## Tech stack

<!-- elicited: 2026-05-15 / status: filled -->

- **Runtime / language:** Python 3 (helpers), Markdown (skills, ADRs),
  Bash (hook scripts only)
- **Platform commitments:** Claude Code plugin runtime; GitHub for
  release pipeline (release-please)
- **Package manager:** n/a (stdlib-only Python; no pip dependencies)
- **Database / state:** none — small on-disk state under .jig/ +
  docs/specs/
- **Key external services:** GitHub API (via `gh` CLI for slice-land
  PR mode)
- **Locked-in:** Python 3 (ADR-pending), ${CLAUDE_PLUGIN_ROOT} paths
  for hooks
- **Still open:** AGENTS.md sibling support (deferred until non-Claude-
  Code user signal — refinement-todo entry)
```

### Section 8 — Module boundaries *(feeds architecture.md)*

**Skill asks Q8.1, Q8.2:**

**User answers:**
- Concerns: skills, agents, hooks, templates, scripts (Python helpers), .claude-plugin
- Interface contracts: read-only, one-directional today; skills read templates, helpers read specs, hooks read events

**Skill renders into `architecture.md ## Module boundaries`:**

```markdown
## Module boundaries

<!-- elicited: 2026-05-15 / status: filled -->

- `skills/` — auto-triggering LLM behaviors (one SKILL.md per skill)
- `agents/` — 3 subagent definitions (implementer / reviewer / architect)
- `hooks/` — deterministic spine (hooks.json + Python 3 scripts)
- `templates/` — source templates scaffold-init copies
- `scripts/` — Python helpers (one per skill where work is mechanical)
- `.claude-plugin/` — plugin manifest + marketplace descriptor

Interface contracts: today's coupling is read-only and one-directional
(skills read templates; helpers read specs; hooks read events; nothing
writes across the module boundary).
```

### Section 9 — Data model *(feeds architecture.md)*

**Skill asks Q9.1, Q9.2:**

**User answers:**
- State: minimal — `.jig/scaffold.json` (install manifest), `.jig/skill-usage.jsonl` (telemetry, deferred), `docs/specs/**` (spec files)
- Stateless beyond on-disk state: yes

**Skill renders into `architecture.md ## Data model`:**

```markdown
## Data model

<!-- elicited: 2026-05-15 / status: filled -->

Jig is a workflow layer, not a data application. State is small and on-disk:

- `.jig/scaffold.json` — install manifest (tiers chosen, jig version)
- `.jig/skill-usage.jsonl` — telemetry append-only (deferred until consumer)
- `docs/specs/**/spec.md` — the only project-level state jig owns
```

### Section 10 — Design principles & constraints

**Skill asks Q10.1, Q10.2:**

**User answers:** (the 7 design principles from
[`docs/product-vision.md`](../../docs/product-vision.md): Hooks are
deterministic, Context economy, Three subagents, Dogfood,
Bring-your-own-depth, No backwards-compat shims, Own-the-scaffolding)

**Skill renders into `## Design principles & constraints`:**

```markdown
## Design principles & constraints

<!-- elicited: 2026-05-15 / status: filled -->

1. Hooks are deterministic; skills carry judgment.
2. Stay below the dumb zone (~40% context fill).
3. Three subagents, no more — defined by isolation, not job title.
4. Dogfood the workflow we build.
5. Bring your own depth; jig provides the floor.
6. No backwards-compat shims when conventions change.
7. Owning the scaffolding beats renting the plugin.

**Non-obvious constraints:**
- Context-window economics: ~40% fill ceiling, 8 MCP servers, ~80 active tools
- No external dependencies (Python stdlib only)
```

**Hand-seeded divergence.**
[`docs/product-vision.md`](../../docs/product-vision.md) labels
this section `## Design principles` (without "& constraints"). The
template includes constraints in the same section so the load-bearing
non-obvious limits (perf, regulatory, etc.) have a home rather than
floating.

### Section 11 — How new work enters

**Skill asks Q11.1, Q11.2:**

**User answers:**
- Signal-driven prioritization
- Spec triggers: user signal hit twice, dogfooding revelation, cross-project comparison

**Skill renders into `## How new work enters`:**

```markdown
## How new work enters

<!-- elicited: 2026-05-15 / status: filled -->

Jig grows by **signal**, not speculation. A new spec is justified
when one of:

- User signal: real pain hit two or more times
- Dogfooding revelation: gap found while using jig on jig
- Cross-project comparison: pattern recurring in multiple projects

Speculative tier promotion is explicitly disallowed.
```

**Hand-seeded divergence.**
[`docs/product-vision.md`](../../docs/product-vision.md) labels
this section `## How new work enters jig` (with the project-name
suffix). The template drops the suffix so the H2 stays portable.

### Section 12 — Open questions *(feeds refinement-todo.md)*

**Skill asks Q12.1:** *"What's still uncertain?"*

**User answers:**
- AGENTS.md sibling support (deferred until non-Claude-Code user signal)
- Tier 2 — does anyone need local-dev-parity?
- `contracts` skill — when does the third caller appear?

**Skill renders into `docs/refinement-todo.md` as new entries**
(architecture.md's `## Open questions` is just a pointer). The
hand-seeded [`docs/product-vision.md`](../../docs/product-vision.md)
does not have an `## Open questions` H2 — uncertainties live in
refinement-todo.md, which the template's Open questions footer
points to.

## Result: rendered docs/product-vision.md

After this elicitation pass, the project's `docs/product-vision.md`
has 9 H2 sections in the template's order (Identity / Target users /
Core problem / Competitive landscape / Scope / Stack / Design
principles & constraints / How new work enters / Open questions),
each with its marker transitioned from `unfilled` to `filled`. The
content reflects the user's literal words; the skill did not
paraphrase or expand.

`docs/architecture.md` has 4 of its elicitation slots filled (Repository
structure / Tech stack / Module boundaries / Data model) and 0 still
`unfilled`. The two non-marker sections (Core architecture decisions /
Open questions) are unchanged.

## Summary of divergences with the hand-seeded vision.md

| Hand-seeded H2 | Template H2 | Reason for divergence |
|---|---|---|
| Vision statement | Identity | Template groups vision + tagline + positioning story in one bucket |
| The core problem | Core problem | Terseness — drop the article |
| Core features (prioritized) | Scope > Core features (H3) | Template groups features + tiers + MVP + non-goals under one Scope H2 |
| Design principles | Design principles & constraints | Template includes constraints in the same section |
| How new work enters jig | How new work enters | Template drops project-name suffix |
| Future scope | Scope > (Tiers / phases or Out of scope sub-bullet) | Template fits future scope into the existing Scope buckets |
| References | (not in template) | Template uses inline links rather than a separate References section |
| (not in hand-seeded) | Stack | Template includes high-level platform framing (orthogonal to architecture.md's concrete Tech stack) |
| (not in hand-seeded) | Open questions | Template links to refinement-todo.md |

These divergences are intentional — the template's H2s are designed
to be project-agnostic and to map cleanly to the 12-section Q&A
flow. The hand-seeded `docs/product-vision.md` predates the template
and uses jig-specific section names. **The template is the source
of truth for elicitation output shape.**
