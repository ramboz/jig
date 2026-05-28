# Decisions

> Architectural Decision Records. Nygard convention: immutable after acceptance.
> New decisions supersede old ones — never edit an accepted ADR.

## Index

- [ADR-0001: scaffold-stable trigger](adr-0001-scaffold-stable.md) — scaffold-init generates docs with `Status: Draft (wizard-generated)` markers at the top. (2026-05-12, Accepted)
- [ADR-0002: `contracts` skill stays a deliberate stub](adr-0002-contracts-stays-deferred.md) — `contracts` is the last Tier 0 skill that remains a `disable-model-invocation: true` stub after specs 001–004 promoted the other four (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`). (2026-05-15, Superseded)
- [ADR-0003: Extract `find_slice_section` to `skills/_common/parsing.py`](adr-0003-extract-find-slice-section.md) — [ADR-0002](adr-0002-contracts-stays-deferred.md) named "first time jig has three callers that need the same helper" as the trigger to extract `skills/_common/<module>.py`. (2026-05-12, Accepted)
- [ADR-0004: Rename docs/adrs/ to docs/decisions/ and prefix files with adr-](adr-0004-decisions-folder-naming.md) — jig's default ADR layout (at the time of this ADR) was `docs/adrs/NNNN-<slug>.md`, which is internally consistent and matches Nygard's original blog post but has two usability gaps that surfaced while dogfooding jig against the aso-shallow-validator project — a mature spec-driven repo that organically grew the same workflow jig codifies but landed on a different naming convention (`docs/decisions/adr-NNN-<slug>.md`). (2026-05-12, Accepted)
- [ADR-0005: contracts skill is a judgment-skill nudging toward standard external-interface artifacts](adr-0005-contracts-as-judgment-skill.md) — [ADR-0002](./adr-0002-contracts-stays-deferred.md) deferred the `contracts` skill until "a third caller needs the duplicated lookup, OR a real user reports cross-module-coupling pain." Both triggers framed contracts as an **internal-boundary** problem inside the codebase: duplication of lookup logic, cross-module imports, scaffolding-with-stubs. (2026-05-15, Accepted)
- [ADR-0006: adr.py accept-then-index ordering](adr-0006-adr-accept-then-index-ordering.md) — `adr.py` ships four subcommands: `new`, `accept`, `index`, `resolve-todo`. (2026-05-15, Accepted)
- [ADR-0007: scaffold.json gains per-skill install list](adr-0007-scaffold-json-installed-skills.md) — The `scaffold.json` install-state manifest currently tracks granularity at the tier level only. (2026-05-15, Accepted)
- [ADR-0008: Closed-spec drift policy](adr-0008-closed-spec-drift-policy.md) — jig's process treats ADRs as immutable per ADR-0006 / Nygard. (2026-05-27, Accepted)

## Format

Each ADR lives at `docs/decisions/adr-NNNN-<slug>.md`. Title: `# ADR-NNNN: <Title>`.

Required sections: Status, Context, Decision Options Considered, Recommended Decision, Consequences.

## When to write an ADR

- Hard-to-reverse decisions
- Decisions that affect multiple modules or the public API
- When a contract changes in a breaking way
- When the `architect` subagent produces a proposal that is accepted
