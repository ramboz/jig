---
status: DONE
skill: contracts
tier: 1
---

# Spec 022: contracts skill (judgment-style, external-interface artifacts)

## Overview

[ADR-0005](../../decisions/adr-0005-contracts-as-judgment-skill.md) reframed the `contracts` skill from a kitchen-sink scaffold (the original [ADR-0002](../../decisions/adr-0002-contracts-stays-deferred.md) framing) to a judgment-skill that **nudges devs toward standard external-interface artifacts** — OpenAPI for HTTP APIs, JSON Schema for data shapes, AsyncAPI for events, `.proto` for gRPC, GraphQL SDL, etc.

The skill ships as **SKILL.md only** — no `.py` helper, no scaffolded `contracts/` dir, no PreToolUse hook. Same archetype as `pr-review` (012), `arch-review` (014), `vision-elicitation` (017-02), `slice-to-spec` (020).

Two integration touchpoints give a two-pass safety net for drift detection: the spec-author declares the surface (via `vision-elicitation`'s wizard at init or mid-flight) and `independent-review`'s reviewer prompt checks during slice review.

## Why now

- **Direct motivation.** aso-shallow-validator dogfood surfaced two contract surfaces — one worked (env-contract triple), one prose-only (HTTP API in [architecture.md §5](../../../aso-shallow-validator/docs/architecture.md), ~230 lines of jsonc bodies + RFC 7807 + idempotency + rate-limit policy). The §5 case is the canonical drift candidate that an OpenAPI artifact + `spectral` lint + `openapi-typescript` codegen would close in one CI pass. The hand-typed [`src/problem-details.ts`](../../../aso-shallow-validator/src/problem-details.ts) — which duplicates §5.9's schema in TS — is the symptom.
- **The shape is proven.** Four jig skills already ship in the SKILL.md-only judgment archetype (012/014/017-02/020). Contracts is the fifth; no new mechanics to invent.
- **LLM iteration story.** During fast vibe-coding, the LLM silently drifts response shapes between iterations. A strict reference artifact (OpenAPI / JSON Schema) gives both the LLM and CI something to validate against. Load-bearing per ADR-0005.
- **Parallel FE/BE work.** Same artifact gives both sides a single source of truth; standard ecosystem affords codegen for both.

## Goals

1. **Per-surface recommendation table.** SKILL.md documents the canonical industry-standard artifact per external surface type (HTTP / events / RPC / GraphQL / internal data shapes / CLI output / etc.). Each row points at the canonical ecosystem tools for validation (`spectral`, `ajv`, `buf`, `graphql-inspector`) and codegen (`openapi-typescript`, `quicktype`, etc.).
2. **Nudge, never mandate.** Devs opt out by choice — especially when migrating projects with bespoke contract patterns. The skill recommends; the dev decides.
3. **Worked examples in at least two different shapes.** One JS/Node example (OpenAPI for an HTTP API, lifted from aso-shallow-validator's §5 unfinished case) + one different-shape example (JSON Schema for an internal data envelope, or AsyncAPI for an event payload). The second example proves the abstraction holds across ecosystems, not just one.
4. **`vision-elicitation` (017) integration.** Appendix A grows a section asking what external surfaces the project exposes; per choice, the wizard recommends the canonical artifact and offers to scaffold a stub.
5. **`independent-review` (004) integration.** Reviewer prompt template gains a "slice touches a declared contract surface? artifact updated in the same change-set?" check. Second pass after the spec-author's first attention.
6. **`migrate.py report` integration.** Output grows a "Contract surfaces detected" section that flags existing artifacts on disk (`openapi.yaml`, `*.schema.json`, `*.proto`, `schema.graphql`, etc.), prose API-shaped sections in `architecture.md`, env-contract-style patterns, and hand-typed boundary types like `problem-details.ts`. Recommends migrations per surface; never auto-rewrites.
7. **Surface-pinning tests** for the SKILL.md (mirror 012-01 / 020-01 pattern): frontmatter, key sections, per-surface table tokens, worked-example file presence, deferral language for richer user-installed contracts skills.

## Non-goals

- **A `contracts/` directory scaffolded at init.** Explicitly out — this is the kitchen-sink trap ADR-0002 diagnosed and ADR-0005 preserved. The skill recommends per surface; it doesn't enforce a fixed file layout.
- **A `.py` helper for `contracts`.** No `contracts.py` subcommands. Validation is delegated to ecosystem tools the dev installs separately. SKILL.md documents how to wire them; doesn't ship them. (`migrate.py report` *is* extended in 022-02 — that's a different helper.)
- **A PreToolUse hook blocking edits to API surfaces without a matching artifact update.** Per the nudge-not-wall ethos. The reviewer-prompt integration (Goal 5) is the structural enforcement; the wall version is rejected.
- **Auto-rewriting prose API specs to OpenAPI / JSON Schema.** `migrate report` flags the gap; the dev (or the LLM driving the migration via prompt) does the conversion. Auto-conversion is too lossy for a one-shot tool.
- **Codegen orchestration.** The skill documents which tools generate clients/types from which artifacts (`openapi-typescript`, `quicktype`, etc.), but doesn't ship a "run codegen" command. That's per-project wiring.

## Decomposition

Two slices, SPIDR Data + Interface axes:

- **022-01 (Data) — `contracts-skill-md`**: extends `skills/contracts/SKILL.md` from stub to active. Per-surface recommendation table, two worked-example fragments, deferral language for richer user-installed alternatives, surface-pinning tests. Activates standalone; integration touchpoints land in 022-02. After this slice, an LLM invoking `/jig:contracts` gets the recommendation table and can recommend artifacts for any surface it sees.
- **022-02 (Interface) — `integration-touchpoints`**: wires `vision-elicitation` (017) Appendix A to ask "what external surfaces does this project expose?" (calling back to the contracts skill), extends `independent-review` (`review.py`'s prompt template) with the "contract surface touched? artifact updated?" check, and grows `migrate.py report` output with the "Contract surfaces detected" section. After this slice, the skill is wired into the wider jig flow on both ends (init + slice review + migration).

### Slices

- [slice-01-contracts-skill-md](slice-01-contracts-skill-md.md) — DRAFT
- [slice-02-integration-touchpoints](slice-02-integration-touchpoints.md) — DRAFT

## Open questions

- **One canonical artifact per surface vs short menu.** Inherited from ADR-0005. Lean: one canonical (firmer nudge) with a prose tradeoffs sidebar where the second option is non-trivial (e.g., for internal data shapes: JSON Schema canonical, with TypeBox/Zod/Pydantic noted as stack-specific alternatives).
- **Internal-data-shape default.** Lean: JSON Schema (most portable, most ecosystem tooling, least stack-coupled). Stack-coupled alternatives (Zod for TS, Pydantic for Python) called out in the worked example.
- **Worked example #2 shape.** Pick from: AsyncAPI for events, JSON Schema for envelope, GraphQL SDL for query surface. Lean: JSON Schema for an internal envelope (smallest tooling install + most cross-ecosystem coverage).
- **Sequencing.** 022-02 depends on spec 017 (vision-elicitation) being live and its Appendix A in place. Confirm 017 is fully landed before unblocking 022-02. 022-01 has no such dependency and can land standalone.
- **Migrate report integration depth.** Should `migrate.py report` ship a separate `--contracts` flag or always include the new section? Lean: always include, with explicit "no contract surfaces detected" prose when empty — same shape as existing sections.
