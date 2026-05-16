---
dependencies: [adr-0002]
last_verified: 2026-05-15
---

# ADR-0005: contracts skill is a judgment-skill nudging toward standard external-interface artifacts

## Status

Accepted (2026-05-15)
Supersedes ADR-0002

## Context

[ADR-0002](./adr-0002-contracts-stays-deferred.md) deferred the `contracts` skill until "a third caller needs the duplicated lookup, OR a real user reports cross-module-coupling pain." Both triggers framed contracts as an **internal-boundary** problem inside the codebase: duplication of lookup logic, cross-module imports, scaffolding-with-stubs.

Real-world signal from dogfooding plus one downstream project (aso-shallow-validator) points at a different problem entirely: **external-interface drift**. Prose API specs in architecture docs that the code doesn't actually match. Parallel frontend/backend work without a shared schema. LLM iteration that silently changes response shapes during fast vibe-coding cycles.

Two artifacts in aso-shallow-validator bracket the spectrum:

1. **Working pattern** ([docs/env-contract.md](../../../aso-shallow-validator/docs/env-contract.md) + `.env.example` + [tools/env-contract/check.mjs](../../../aso-shallow-validator/tools/env-contract/check.mjs)): A complete triple — prose doc with table + machine-readable seed + 139-line stdlib enforcer + `npm run check:env-contract` CI gate — for one boundary (env vars). Bespoke, but proves the doc+seed+checker pattern holds when applied per boundary.
2. **Unfinished pattern** ([docs/architecture.md §5](../../../aso-shallow-validator/docs/architecture.md)): ~230 lines of prose HTTP API contract — endpoint table, request/response jsonc bodies, RFC 7807 error model, idempotency rules, rate limits. All asserted in prose, none enforced by tooling. Exactly the surface where OpenAPI + `spectral` lint + `ajv` validate + `openapi-typescript` codegen would close the drift loop *and* give the LLM a strict reference to iterate against.

ADR-0002 didn't picture either case. Its Option A ("scaffold a `contracts/` dir") and Option C ("PreToolUse hook blocking cross-module imports") both treated contracts as a problem internal to the codebase. The actual concept is external — **what artifacts does the project owe its callers, and how does jig keep them honest without locking devs out of opt-outs?**

## Decision Options Considered

### Option A: Keep ADR-0002 in force; wait for the originally-named triggers

- **Pros:** Honors the existing deferral. Costs nothing.
- **Cons:** The triggers were wrong-axis. "Third caller needs the same lookup" inside jig means the skill never ships — jig has no cross-module coupling problem. The real signal (external-interface drift) goes unaddressed indefinitely.

### Option B: Promote ADR-0002's original concept (helper that scaffolds a `contracts/` dir at init)

- **Pros:** Matches the existing framing.
- **Cons:** Still the kitchen-sink trap ADR-0002 itself diagnosed. "Here's a `contracts/` dir, figure out what to put in it" doesn't help anyone, and a bespoke jig-shaped scaffold competes with industry-standard artifacts (OpenAPI, JSON Schema, AsyncAPI, etc.) the dev already knows.

### Option C: Reframe `contracts` as a judgment-skill that nudges toward standard external-interface artifacts

Pure SKILL.md (no `.py` helper), same archetype as `pr-review` (012), `arch-review` (014), `vision-elicitation` (017-02), `slice-to-spec` (020):

- **Per-surface recommendations** — OpenAPI for HTTP, JSON Schema for data shapes, AsyncAPI for events, `.proto` for gRPC, GraphQL SDL, etc. Skill documents the table; per surface, recommends the canonical artifact.
- **Nudge, don't mandate.** Devs ultimately decide whether to opt out, especially when migrating existing projects with their own conventions. `migrate.py report` surfaces existing contract surfaces and recommends — never auto-rewrites.
- **Orchestrate ecosystem tools** — `spectral`, `ajv`, `buf`, `graphql-inspector`, `openapi-typescript`, etc. — for validation, codegen, CI gating. Skill ships none of its own.
- **Two integration touchpoints with existing skills:**
  - **`vision-elicitation` (017):** Appendix A grows a section asking what external surfaces the project exposes; per choice, recommends the canonical artifact and offers to scaffold a stub.
  - **`independent-review` (004):** reviewer prompt template gains a "slice touches a declared contract surface? artifact updated in the same change-set?" check. Second pass after the spec-author's first attention.

- **Pros:**
  - Matches the real pain: prose specs drift from code; standard artifacts give the LLM a strict reference and CI a real gate.
  - Same archetype jig has converged on for other judgment skills — proven shape.
  - Dev opt-out preserved (important for migrations).
  - Two passes (spec-author + independent-review) rather than one.
- **Cons:**
  - aso-shallow-validator is one project. The worked example is JS/Node-flavored. The skill must abstract **what the triple is** (artifact + ecosystem tool + CI gate), not lift specifics from one ecosystem.
  - Reviewer-prompt integration only catches what the author declared. Surfaces not in the declaration slip past both passes. Acceptable tradeoff: jig is a nudge, not a wall.

## Recommended Decision

**Option C.** Reframe `contracts` as a judgment-skill that nudges toward standard external-interface artifacts per surface, orchestrates ecosystem tooling, and integrates with `vision-elicitation` (017) + `independent-review` (004).

ADR-0002 stays in the historical record as the pre-pivot framing. Its `disable-model-invocation: true` stub of `contracts/` stays in place until this skill ships under a new spec.

The concrete implementation lands as a separate spec (to be reserved via `workflow.py new`).

## Consequences

**Becomes easier:**

- Projects scaffolded via `jig:scaffold-init` get nudged toward contract-first artifacts at project birth, before drift accumulates.
- LLM coding sessions have a strict reference (OpenAPI / JSON Schema / etc.) to validate against during fast iteration — reduces the "response shape silently shifted on the third iteration" failure mode.
- Parallel frontend/backend work has a single source of truth, and the standard ecosystem affords codegen for both sides.
- Drift between architecture docs and code surfaces in CI, not at the next audit.

**Becomes harder:**

- One more skill to maintain.
- Worked examples must stay current with ecosystem tooling churn (`spectral`, `ajv`, `buf` versions). Same maintenance shape as `tdd-loop`'s runner detection.
- Migrating existing projects with bespoke contract patterns (like aso-shallow-validator's env-contract checker) requires judgment — `migrate.py report` flags the surface and suggests, doesn't auto-convert.

**Resolution trigger for revisiting:**

- If contract artifacts ship and projects systematically opt out, revisit whether the nudge is too soft or the recommended artifacts wrong for the project shapes jig is seeing.
- If a second worked example (non-Node project) lands cleanly with the same doc+artifact+CI triple, lock the abstraction. If the second project needs a fundamentally different shape, supersede with a more general framing.

## Open questions

- **Sequencing vs spec 017.** The Appendix A integration assumes 017's wizard is live. Lean: sequence the contracts spec after 017.
- **Per-surface artifact recommendations — one canonical vs short menu.** The skill's per-surface table can prescribe one canonical artifact per surface (firmer nudge) or list 2–3 options with tradeoffs (softer, more inclusive of existing stack conventions). Deferred to the spec.
- **Internal-data-shape recommendation.** Default: JSON Schema, TypeBox, Pydantic, Zod, or "pick whatever your stack already uses"? Latter is more in the spirit of nudge-don't-force but produces less actionable nudge. Deferred to the spec.
