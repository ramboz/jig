# Glossary

> Domain terms and project-specific vocabulary. Loaded on demand when the hot cache misses.
> Update via `/jig:memory-sync` or when `jig-memory-scan` surfaces an unknown.

## jig

The skill pack itself. Short for "a jig is a tool that guides other tools."

## SPIDR

Mike Cohn's five story-splitting techniques: Spike, Path, Interface, Data, Rules.
Used to split feature specs into implementable vertical slices. Spike is last resort.

## Tier 0 / Tier 1 / Tier 2

Installation tiers for jig skills:
- **Tier 0**: Always installed (scaffold-init, spec-workflow, independent-review, contracts, memory-sync)
- **Tier 1**: Default for most projects (tdd-loop, local-dev-parity, pr-review, adr-workflow) — not yet built
- **Tier 2**: Opt-in by signal (eval-harness, e2e-testing, migration-mode, skill-stocktake) — not yet built

## Hot Cache

The structured section of `CLAUDE.md` for frequently-referenced project terms, people,
codenames, and active specs. Loaded at every session start.

## Dumb zone

The context fill level (~40%) above which model recall and reasoning degrades.
Horthy's term from 12-Factor Agents. Practical ceiling: 8 MCP servers, ~80 active tools.

## Reconciliation

The phase after implementation and review, before marking a slice DONE. Produces a
deviation log, updates architecture.md if module boundaries changed, runs a second
reviewer pass on the doc changes themselves.

## Vertical slice

A spec slice that crosses all layers (DB + service + UI) and delivers end-to-end value.
Contrast with horizontal phasing (DB phase, then API phase, then frontend phase), which
is the AI's default failure mode.
