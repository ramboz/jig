---
name: contracts
description: >
  Enforce typed contracts at module boundaries: generate stack-appropriate contract
  scaffolding, validate contract compliance, detect breaking changes, and surface
  cross-boundary violations. Use when work touches a module boundary, when a new
  feature is designed that will interact with an existing module, or when an interface
  changes in a way that might affect callers.
  Do not use for intra-module refactoring that doesn't cross a boundary, or for
  test-only changes.
disable-model-invocation: true
user-invocable: true
---

> **Status: DRAFT — not yet implemented.**
> This skill is planned in the jig roadmap but not ready for use.

## What this skill does (when implemented)

1. Detects the project stack (TypeScript → interfaces + Zod; Python → Pydantic; etc.)
2. Creates/updates typed contracts in `contracts/` at module boundaries
3. Generates contract test scaffolding
4. Cross-references contract type names against `docs/memory/glossary.md` for naming consistency
5. Surfaces breaking changes: "this is a breaking contract change — update callers or version it"

## Why contracts are the highest-leverage thing for AI-native dev

AI agents have no tribal knowledge. An untyped, boundary-free codebase is illegible
to them — they generate well-written bugs because they can't see where one feature ends
and another begins. Explicit typed contracts make boundaries machine-consumable.

## Gotchas

- `architecture.md` declares the module boundaries; `contracts/` enforces them in code.
  Both must stay in sync — reconciliation checks this.
- Breaking changes require: new contract version + ADR + migration path for consumers.
- The PreToolUse hook that blocks cross-boundary edits is paired with this skill —
  the skill generates the contracts; the hook makes them enforceable.
