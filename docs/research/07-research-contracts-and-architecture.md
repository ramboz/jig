# Research: Contracts and AI-Friendly Architecture

> Reference notes from the design phase. Pull into context only when relevant.

## The leverage point

Of everything in our scaffold, **typed contracts at module boundaries are the single highest-leverage thing for AI-native dev.** Three converging sources from the research:

1. **Aditya Bawankule's AI agent architecture rules:** "All communication between modules must use shared, type-safe contracts. Features are developed as independent modules with no hidden coupling. Architecture rules are enforced by CI/CD, static analysis, and test contracts."

2. **InfoQ's Spec-Driven Development piece:** specs cover interface contracts (capabilities, I/O, behavioral guarantees), data schemas and invariants, event topologies, security boundaries. Specifications can generate code, documentation, SDKs, mocks.

3. **Nitin Gavhane's "AI coding agents are failing — and your architecture is the reason":** the prescribed remedy is *introducing typed interfaces.* "Day 3: Introduce one typed interface to replace one direct import. Add a test for the interface contract."

## Why this matters more for AI than for humans

Humans navigating an untyped, tangled codebase rely on **tribal knowledge** — they know that the `UserService` is *supposed* to be the only thing that touches `users`. AI agents have no tribal knowledge. They have only what's in the codebase and the prompt.

**An untyped, boundary-free codebase is illegible to AI agents.** They generate well-written bugs because they can't see where one feature ends and another begins.

Contracts make boundaries **explicit and machine-consumable**. An agent working on Feature A can:

- See exactly what Feature A may use from Feature B (the contract)
- Be blocked from touching Feature B's internals (hook enforcement)
- Validate its own work against the contract (test scaffolding)
- Be reviewed against the contract by an independent agent

## What "contracts" means in practice

Stack-appropriate format:

- **TypeScript:** typed interfaces + branded types + runtime validators (Zod, io-ts, valibot)
- **Python:** Pydantic models + protocol types + dataclasses
- **Go:** interfaces + protobuf for cross-service
- **Multi-language:** OpenAPI / JSON Schema for HTTP; AsyncAPI for events; protobuf for RPC
- **Frontend:** typed component prop interfaces + design system tokens

The `contracts` skill generates the right format based on what the wizard detects in the project stack.

## What the `contracts` skill produces

1. **A `contracts/` directory** in the project root.
2. **Stack-appropriate scaffolding** — types/schemas in the right language, organized by domain.
3. **Contract test framework** — every feature must have contract tests validating compliance.
4. **A linter / static analysis rule** that blocks direct imports across feature boundaries.
5. **A CI check** that runs contract tests on every PR.
6. **A `contracts/README.md`** that explains the rules and the rationale.

## The hook that enforces it

PreToolUse hook on `Write|Edit`:

```bash
# Block edits to other features' internals
if [[ "$file_path" == features/*/internal/* ]]; then
  current_feature=$(detect_active_feature)
  edit_feature=$(extract_feature_from_path "$file_path")
  if [[ "$current_feature" != "$edit_feature" ]]; then
    echo "Cannot edit ${edit_feature}'s internals from ${current_feature}. Use the contract." >&2
    exit 2
  fi
fi
```

The hook is what makes the convention real. Without it, agents will violate boundaries and generate plausible-looking code that creates hidden coupling.

## Versioning and breaking changes

Contracts are versioned. Breaking changes require:

1. A new contract version (or a new contract).
2. An ADR documenting the rationale.
3. Migration path for consumers.

Our scaffold's `adr-workflow` skill detects when a PR touches a contract in a breaking way and surfaces "this should be an ADR."

## The `architecture.md` connection

`architecture.md` declares the module/feature boundaries. `contracts/` enforces them. The two documents are in conversation:

- `architecture.md` says **what** the boundaries are
- `contracts/` says **how** the boundaries are expressed in code
- The PreToolUse hook says **you cannot cross them**

Reconciliation tightens the loop: if implementation changed module boundaries, `architecture.md` is updated, and likely an ADR is written. If contracts changed, callers need updating or versioning.

## What we don't do (yet)

- **Full SDD where specs generate code.** Interesting direction (InfoQ piece, Pre.dev) but too heavy for v1. Specs and code coevolve via reconciliation; specs don't generate code directly.
- **Cross-service contracts at the infrastructure level.** Service mesh, agent protocols, capability discovery — relevant for distributed agent systems but out of scope for our skill pack.
- **Auto-generated SDKs from contracts.** Useful but not core. Could be a v1.5 addition.

## Adoption pattern for existing codebases (v2 preview)

The research is consistent: **don't try to retrofit contracts to a whole codebase at once.** Pattern:

1. Identify the modules an AI agent struggles with most.
2. Introduce ONE typed interface to replace ONE direct import in that module.
3. Add a contract test for the interface.
4. Have the agent work on that module again. Measure: did it touch fewer files? Did changes make more sense?
5. Next sprint: pick the next module. Repeat.

This is the migration pattern for our v2 `migration-mode` skill.

## Source signals

- Aditya Bawankule: <https://adityabawankule.io/avoiding-tech-debt-disasters-caused-by-coding-agents/>
- Enrico Piovesan on composable boundaries
- InfoQ on Spec-Driven Development as architecture
- Nitin Gavhane on architecture for AI coding agents
- Mindstudio on parallel agentic development (worktrees + schemas + ports)
