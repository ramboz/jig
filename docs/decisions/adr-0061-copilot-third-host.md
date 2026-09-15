---
status: Proposed
dependencies: ["adr-0018-dual-host-generated-plugin-artifacts"]
last_verified: 2026-09-15
frame_review: true
---

# ADR-0061: GitHub Copilot CLI as a third committed host

## Status

Proposed (2026-09-15)

## Context

Adobe is retiring Claude Code as its sanctioned coding agent. Per the internal
migration hub (`github-copilot.corp.adobe.com`, read 2026-09-15), **GitHub
Copilot becomes the primary coding agent on 2026-09-28, and Claude Code is
disabled on that date.** jig ships today as a Claude Code plugin and a Codex
plugin under the committed, source-derived per-host model of
[ADR-0018](adr-0018-dual-host-generated-plugin-artifacts.md). To keep jig usable
for its own maintainers and for scaffolded projects after the cutover, jig must
support GitHub Copilot CLI as a first-class host.

Copilot CLI is deliberately Claude-compatible at the repository layer. Verified
against the Adobe "Moving from Claude Code" guide and the "Claude → Copilot
terminology" map (both read 2026-09-15):

- Copilot CLI reads `CLAUDE.md` / `.claude/CLAUDE.md`, `.claude/skills/<name>/SKILL.md`
  (the **same** Agent-Skills `SKILL.md` format), and `.mcp.json` **directly**, no
  rename.
- `/plugin` installs **Claude-format plugins from marketplaces**, so jig's
  existing marketplace packaging is largely consumable — "hook-heavy plugins need
  the checks" the guide describes.
- Scout integrates with Copilot (`scout setup --copilot`), so the Scout-based
  workflow survives.

But "reads the files" is not "behaves correctly." Several jig-specific things
break or degrade under Copilot as-is:

1. **Skill-loader limits (hard failures).** Copilot's loader **fails to load**
   skills whose name contains `:` or whose description exceeds **1,024
   characters**. A probe of jig source (2026-09-15) found this exposure is small
   but real: 2 of 20 skills already exceed the limit (`memory-sync` 1059,
   `vision-elicitation` 1058), and 0 source names contain `:` — but jig
   *namespaces* skills as `jig:<skill>` at invocation, and that prefix must not
   surface as a `:`-bearing loaded name under Copilot.
2. **Hooks port but differ.** Copilot supports hooks, but with **14 events**
   (`sessionStart`/`End`, `userPromptSubmitted`/`Transformed`, `preToolUse`,
   `postToolUse`, `postToolUseFailure`, `permissionRequest`, `preCompact`,
   `notification`, `agentStop`, `errorOccurred`, `subagentStart`/`Stop`) in
   camelCase, with payloads and decision-output schemas that differ from Claude's
   PascalCase set, and Claude fires more event types than Copilot covers. Copilot
   reads `.claude/settings.json` hooks cross-tool, but the guide is explicit that
   payloads differ and "skills that hard-code Claude hook behavior needed edits
   in the pilot." jig is hook-heavy (spec-gate, review-evidence, entry-gate,
   session-git-freshness, bug-closure, boundary-change-warn, …) — these are jig's
   enforcement teeth and must be translated and validated, not assumed portable.
3. **Agents render differently.** jig's custom agents (implementer, reviewer,
   architect) map to Copilot custom agents under `.github/agents/`, with
   different frontmatter and model conventions (Adobe's default model is GPT-5.6
   Terra; Opus is available — model IDs must not be hard-coded).
4. **`.github/` is Copilot's durable config home.** The terminology map states
   the unit of configuration for Copilot is `.github/` (instructions, skills,
   agents, hooks, MCP, settings), shared with the cloud agent and code review —
   whereas Claude centers on `.claude/` and `CLAUDE.md`.
5. **Permissions differ** (Copilot syntax such as `shell(git:*)`; allowlists are
   per-session, not persistent).

ADR-0018 already anticipated this: Option E was chosen partly so that "future
host adapters follow one pattern: canonical source in root, committed
`hosts/<host>/` package, host-named zip." Adding Copilot is the first exercise of
that promise, and it is time-boxed by the 2026-09-28 cutover.

**Scope.** This ADR and its implementing spec target **GitHub Copilot CLI**,
matching the Adobe guide's own scope ("GitHub Copilot CLI, not IDE integrations")
and jig's CLI-first nature. IDE-surface parity is out of scope.

## Decision Options Considered

### Option A: Cross-tool reliance only — no new host package

Lean on Copilot's direct reading of `.claude/` (skills, `CLAUDE.md`, settings
hooks) and `/plugin` marketplace install; fix only the skill-loader breakers in
the canonical source.

- **Pros:** Smallest change; fastest to the cutover; no new committed package to
  drift-guard.
- **Cons:** Privileges the Claude shape as "the real tree" — the asymmetry
  ADR-0018 rejected for Codex. Hooks fire with Claude payloads/schemas that
  differ from Copilot's, so jig's gates degrade silently. Agents and permissions
  are never rendered into Copilot's native homes. Ignores that `.github/` is
  Copilot's durable config home. Forcing canonical descriptions to ≤1024 chars to
  satisfy a Copilot limit would degrade Claude/Codex trigger quality — a
  cross-host coupling the render layer should absorb, not the source.

### Option B: Advisory / instructions-only

Emit `.github/copilot-instructions.md` (and keep `CLAUDE.md`) so Copilot users
get workflow guidance, but do not port skills/agents/hooks natively; treat the
gates as documentation.

- **Pros:** Trivial; no rendering machinery.
- **Cons:** jig's value is its *enforced* lifecycle; dropping the teeth makes it
  a style guide. The migration guide itself warns "instruction files are not
  security controls." Rejected.

### Option C (chosen): Copilot as a third committed host under `hosts/copilot/`

Extend ADR-0018's pattern to a tri-host layout. Add a `CopilotScaffoldRenderer`
alongside `ClaudeScaffoldRenderer` and `CodexScaffoldRenderer`, wire it into
`renderer_for_host` / `read_host_renderer`, and generate a committed,
drift-guarded `hosts/copilot/` package that renders jig into Copilot-native homes
(`.github/`), with a host-explicit `jig-copilot-vX.Y.Z.zip` release archive.

- **Pros:** Symmetric with Claude and Codex; honors `.github/` as Copilot's
  durable home; the render layer (not the canonical source) absorbs the loader
  limits and hook-schema translation, so Claude/Codex quality is untouched; jig's
  gates keep their teeth via translated hooks; follows the one pattern ADR-0018
  promised for future hosts.
- **Cons:** A third committed package to build, drift-guard, version, and
  release; the hook-translation layer is real engineering (event-name mapping,
  payload/response-schema adaptation, and an explicit inventory of Claude events
  Copilot cannot express); more release/CI surface. Larger than A/B under a tight
  deadline — mitigated by spec sequencing (below).

### Option D: A separate Copilot-only plugin / repository

Ship jig-for-Copilot as its own artifact, decoupled from the jig source tree.

- **Pros:** No coupling to the existing builder.
- **Cons:** Immediate source divergence and double maintenance — the exact
  failure ADR-0018's single-source-of-truth model exists to prevent. Rejected.

## Recommended Decision

Adopt **Option C: GitHub Copilot CLI as a third committed host**, extending
ADR-0018 to a tri-host layout.

```text
repo root/                         canonical source (unchanged)
  skills/ agents/ hooks/ templates/
  .claude-plugin/ .codex-plugin/   existing host source manifests
  hosts/
    claude/                        committed Claude package (ADR-0018)
    codex/                         committed Codex package (ADR-0018)
    copilot/                       COMMITTED Copilot package (this ADR)
      .github/
        copilot-instructions.md    rendered from CLAUDE.md / brief
        skills/<name>/SKILL.md      loader-safe (name + <=1024 desc)
        agents/<name>.md            rendered Copilot custom agents
        hooks/*.json               Claude hooks translated to Copilot events
        copilot/settings.json      permissions floor in Copilot syntax
      <plugin manifest for /plugin install — shape TBD, see Open questions>
  dist/                            gitignored — adds jig-copilot-vX.Y.Z.zip
```

The decision commits jig to:

- **A `CopilotScaffoldRenderer`** implementing the `HostRenderer` contract:
  `translate_hook_protocol` (Claude PascalCase → Copilot 14-event camelCase, with
  payload/response-schema adaptation), `bind_paths` (Copilot path/plugin-root
  model), `rewrite_skill_md_paths`, agent rendering to `.github/agents/`, and a
  **loader-compat invariant** — the renderer guarantees every emitted skill has a
  namespace-safe name and a description ≤1024 chars (full text preserved in the
  SKILL.md body), so no source skill can silently fail to load under Copilot,
  now or later.
- **A committed `hosts/copilot/` package** rendering into the `.github/` layout,
  built by the same single builder that produces `hosts/claude` and
  `hosts/codex`, and fenced by the **same drift guard** (CI regenerates and fails
  on a dirty `git diff`).
- **Host-explicit release + verification:** a `jig-copilot-vX.Y.Z.zip` archive
  and a per-host install/smoke verification run in a Copilot CLI environment (or
  the closest deterministic substitute, recorded honestly), coordinated with
  release-please the same way ADR-0018 requires for the other two hosts.
- **A hook-translation inventory invariant:** every jig hook is either mapped to
  a Copilot event with equivalent enforcement, or **explicitly recorded as
  unmappable** with the residual documented — mirroring servo ADR-0028's honesty
  that "host packaging does not make execution primitives portable." The gates
  keep their teeth where Copilot can express them and degrade *visibly*, never
  silently, where it cannot.
- **Model-id neutrality** for rendered agents (no hard-coded `opus`/`sonnet`).

**Deadline-aware sequencing.** Because 2026-09-28 is hard, the implementing spec
(spec 113) orders the "actually works under Copilot" core first — loader-compat +
skill/instruction/agent rendering + hook translation — with the committed-package
drift-guard, release archive, and release-please coordination as following
slices. A usable Copilot install can therefore exist before the deadline even if
release automation lands just after it.

This ADR does **not** decide servo's or shaper's adoption; those are sibling
decisions that will mirror this pattern (jig-first, per owner direction), each in
its own repo's ADR.

## Consequences

**Becomes easier:**

- jig survives the Adobe Claude Code cutover and installs natively for Copilot
  CLI users via `/plugin` and a host-named zip.
- Copilot's cloud agent and server-side code review pick up jig's conventions,
  since they read `.github/`.
- Future hosts still follow one pattern; the third host proves the ADR-0018
  adapter promise rather than special-casing.

**Becomes harder:**

- A third generated package must be drift-guarded, versioned, and released; the
  builder, CI, and release workflow all grow a Copilot arm.
- The hook-translation layer is genuine engineering and must be re-verified as
  Copilot's hook schema evolves (the guide warns "product behavior changes
  quickly").
- Contributors regenerate three packages after touching shared source.

**Invariants:**

- The repository root stays canonical source; `hosts/copilot/` is a generated
  build output kept in sync by the drift guard, never hand-edited.
- The Copilot render layer — not the canonical source — enforces Copilot's
  loader limits and hook-schema shape, so Claude/Codex output is unchanged.
- Every jig hook is mapped or explicitly recorded as unmappable; gates degrade
  visibly, never silently.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **Copilot capability facts are sourced from Adobe's internal migration guide
  and terminology map** (`github-copilot.corp.adobe.com/guides/claude-code-migration`
  and `/guides/terminology`, read 2026-09-15), not from a jig-run probe of
  Copilot itself. They reflect Copilot CLI ~1.0.84. The guide warns behavior
  changes quickly, so each load-bearing fact (14 hook events + payload shapes,
  `/plugin` accepting Claude-format marketplaces, skill-loader limits, agent file
  location) must be **re-verified against GitHub's own Copilot CLI docs and a
  live `copilot` session at implementation time**.
- **Skill-loader exposure — probed (2026-09-15).** Of 20 source skills, 2 have
  descriptions >1024 chars (`memory-sync` 1059, `vision-elicitation` 1058) and 0
  source `name:` fields contain `:`. Whether the `jig:` invocation namespace
  surfaces as a `:`-bearing loaded name under Copilot's `/plugin` is **not yet
  verified** — it depends on how Copilot namespaces an installed Claude-format
  plugin.
- The Copilot plugin/marketplace manifest shape a committed `hosts/copilot/`
  package must present for `/plugin` install is **unverified** (see Open
  questions); the layout diagram's manifest line is provisional.

## Kill criteria

- Adobe reverses or indefinitely postpones the Claude Code disablement — the
  deadline pressure evaporates (the parity value does not, but priority drops).
- Copilot's `/plugin` cannot install jig's Claude-format marketplace package
  **and** no `.github/`-native discovery path works — the committed-package shape
  needs rethinking before building it.
- The hook-translation inventory shows the load-bearing gates (spec-gate,
  review-evidence, entry-gate) have **no** Copilot-expressible equivalent — then
  Option C's "keeps its teeth" premise fails and enforcement must move
  out-of-band (CI), changing the decision's cost/benefit.

## Open questions

- **Exact Copilot plugin/marketplace manifest** for a committed `hosts/copilot/`
  package installed via `/plugin` — verify against GitHub docs and a live
  session; may warrant a spike as spec 113's first slice.
- **Agent file extension:** the terminology map shows `.github/agents/*.md`; the
  migration guide shows `.github/agents/*.agent.md`. Verify the loaded form.
- **Which jig hooks have no Copilot-event equivalent** — the translation
  inventory is a spec deliverable, not resolved here.
- **`.github/copilot-instructions.md` vs. `CLAUDE.md` direct read** — durable-home
  guidance favors emitting the former; confirm it does not double-load with the
  `CLAUDE.md` Copilot already reads.
