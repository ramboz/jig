# ADRs

> Architectural Decision Records. Nygard convention: immutable after acceptance.
> New decisions supersede old ones — never edit an accepted ADR.

## Index

- [ADR-0001: scaffold-stable trigger](0001-scaffold-stable.md) — scaffold-init generates docs with `Status: Draft (wizard-generated)` markers at the top. (2026-05-12, Accepted)
- [ADR-0002: `contracts` skill stays a deliberate stub](0002-contracts-stays-deferred.md) — `contracts` is the last Tier 0 skill that remains a `disable-model-invocation: true` stub after specs 001–004 promoted the other four (`scaffold-init`, `memory-sync`, `spec-workflow`, `independent-review`). (2026-05-12, Accepted)
- [ADR-0003: Extract `find_slice_section` to `skills/_common/parsing.py`](0003-extract-find-slice-section.md) — [ADR-0002](0002-contracts-stays-deferred.md) named "first time jig has three callers that need the same helper" as the trigger to extract `skills/_common/<module>.py`. (2026-05-12, Accepted)
- [ADR-0004: Rename docs/adrs/ to docs/decisions/ and prefix files with adr-](0004-decisions-folder-naming.md) — jig's default ADR layout is `docs/adrs/NNNN-<slug>.md`, which is internally consistent and matches Nygard's original blog post but has two usability gaps that surfaced while dogfooding jig against the aso-shallow-validator project — a mature spec-driven repo that organically grew the same workflow jig codifies but landed on a different naming convention (`docs/decisions/adr-NNN-<slug>.md`). (2026-05-12, Accepted)

## Format

Each ADR lives at `docs/adrs/NNNN-<slug>.md`. Title: `# ADR-NNNN: <Title>`.

Required sections: Status, Context, Decision Options Considered, Recommended Decision, Consequences.

## When to write an ADR

- Hard-to-reverse decisions
- Decisions that affect multiple modules or the public API
- When a contract changes in a breaking way
- When the `architect` subagent produces a proposal that is accepted
