# ADRs

> Architectural Decision Records. Nygard convention: immutable after acceptance.
> New decisions supersede old ones — never edit an accepted ADR.

## Index

- [ADR-0001: scaffold-stable trigger](0001-scaffold-stable.md) — 3 reconciled slices triggers scaffold-stable promotion (2026-05-12, Accepted)
- [ADR-0002: contracts skill stays deferred](0002-contracts-stays-deferred.md) — keep `contracts` as a deliberate stub until a real trigger fires (third caller needs the shared lookup, or a real user reports cross-module-coupling pain) (2026-05-12, Accepted)

## Format

Each ADR lives at `docs/adrs/NNNN-<slug>.md`. Title: `# ADR-NNNN: <Title>`.

Required sections: Status, Context, Decision Options Considered, Recommended Decision, Consequences.

## When to write an ADR

- Hard-to-reverse decisions
- Decisions that affect multiple modules or the public API
- When a contract changes in a breaking way
- When the `architect` subagent produces a proposal that is accepted
