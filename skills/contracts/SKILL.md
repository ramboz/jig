---
name: contracts
description: >
  Future home for typed-contract scaffolding at module boundaries — generating
  stack-appropriate contract types, detecting breaking changes, and surfacing
  cross-boundary violations. Currently a deliberate stub. Invoke explicitly to
  read the deferral rationale; do not auto-trigger.
disable-model-invocation: true
user-invocable: true
---

> **Status: Deliberate stub — see [ADR-0002](../../docs/decisions/adr-0002-contracts-stays-deferred.md).**
>
> This skill is **not** half-built or in progress. It is deliberately not
> implemented yet because jig itself has no real module-boundary coupling to
> codify, and shipping speculative `contracts/` scaffolding into target
> projects would create the "what do I put here?" trap we explicitly want to
> avoid.

## Why it stays a stub

The other four Tier 0 skills (`scaffold-init`, `memory-sync`, `spec-workflow`,
`independent-review`) were each promoted after we'd run their pattern by hand
10+ times. We had clear shape to codify.

We have run the `contracts` pattern **zero times** in jig. The one place we
hit cross-skill coupling — `find_slice_section` vs `find_slice_label` between
`workflow.py` and `review.py` — we chose duplication over abstraction (see
slice 004-01 deviation log, design choice #1). That's the exact situation
`contracts` is meant to address, and we declined to address it. Encoding a
rule we just chose not to follow would be incoherent.

## When this skill gets promoted

Two clear triggers, either of which is enough:

1. **A third caller needs the duplicated lookup function.** That is the
   trigger to extract `skills/_common/<module>.py` AND to introduce a real
   contract for it. From there, the broader `contracts` skill has a concrete
   case to design against.
2. **A real user reports cross-module-coupling pain** their project
   experienced and that jig could have prevented with typed contracts at
   boundaries.

Until one of those fires, this skill stays a stub.

## What the eventual implementation will do

See [docs/research/07-research-contracts-and-architecture.md](../../docs/research/07-research-contracts-and-architecture.md)
for the original ambition. In short: stack-aware contract scaffolding, a
PreToolUse hook blocking cross-boundary edits, breaking-change detection, and
a glossary-aware naming check. Multi-slice spec. Not started.

## Gotchas

- Do **not** auto-promote this skill on the basis of "we've got all the other
  Tier 0 skills done." That logic produced the ECC trap (kitchen-sink
  scaffolding for its own sake). Wait for a real trigger.
- If you find yourself extracting `skills/_common/parsing.py` to share
  `find_slice_section`, that's the trigger — open a spec for `contracts`
  promotion at the same time as that extraction.
