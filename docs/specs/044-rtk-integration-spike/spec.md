---
status: DONE
---

# Spec 044: RTK integration spike

## Overview

[RTK](https://github.com/rtk-ai/rtk) is a command-output compression layer
for coding agents. Its pitch overlaps with jig's context-economy principle:
reduce noisy command output before it consumes the model's useful context.

The question is not whether RTK is conceptually attractive. It is. The
question is whether it works cleanly with jig's real workflow: scaffolded
hooks, spec/slice lifecycle, test loops, review prompt construction, and
the eventual host-adapter path for Codex.

This spec creates a time-boxed research spike. The spike installs RTK in
the jig project, runs a full disposable jig spec/slice implementation
with RTK disabled and enabled, measures where output shrinks, and records
the gaps that would need integration work.

## Why now

- **A real integration question surfaced.** RTK is close enough to jig's
  context-economy goals that it is worth measuring rather than leaving as
  an intuition.
- **Jig already has hook-shaped machinery.** Scaffold mode writes
  `.claude/settings.json` hook entries, and RTK's strongest Claude Code
  integration also uses hooks. Compatibility needs to be tested with the
  real hook merge behavior, not assumed.
- **Codex portability is already on the roadmap.** Spec 033 defers Codex
  scaffold/plugin support. RTK's Codex story may be different from its
  Claude hook story, so this spike should feed that future adapter work.
- **A dummy E2E run is cheap and high-signal.** A deliberately disposable
  spec/slice implementation can exercise the jig workflow without
  betting the product design on anecdotes.

## Goals

1. **Install RTK in the jig project for the spike** using the current
   official installation path, recording the RTK version, config files
   touched, hook entries added, telemetry setting, and disable/uninstall
   path.
2. **Run a paired measurement** with RTK disabled and enabled over a
   fixed command/workflow corpus representative of jig work: search,
   file reads, git status/diff, test runs, status-board regeneration,
   review-prompt construction, and a dummy spec/slice implementation.
3. **Exercise a full disposable jig E2E flow.** Create a throwaway
   spec/slice, implement a tiny low-risk dummy change, run tests, build
   review prompts, reconcile, and then either remove the dummy artifacts
   or leave only the measurement evidence called out in the spike.
4. **Attribute savings by surface.** Separate command families where RTK
   saves context from surfaces it does not touch: model reasoning, MCP
   outputs, non-shell tool results, hook-injected additional context, and
   host-specific skill/agent routing.
5. **Identify integration gaps.** Explicitly evaluate jig hook
   cohabitation, scaffold-mode behavior, plugin-mode behavior, Codex
   host-adapter implications, privacy/telemetry defaults, and
   disable/raw-output escape hatches.
6. **Produce a recommendation.** The spike should end with one of:
   no jig work needed; docs-only compatibility note; a narrow
   `rtk-compat` slice; changes to spec 033's host-adapter path; or
   abandon RTK integration for stated reasons.

## Non-goals

- **No default RTK install.** This spec does not add RTK as a jig
  dependency or install it for users.
- **No RTK integration implementation.** The spike may create temporary
  local config to measure behavior, but productized hook merging,
  scaffold support, or plugin packaging happens only in follow-up specs.
- **No permanent dummy feature.** The E2E implementation is a measuring
  instrument, not a user-facing jig feature.
- **No model-quality benchmark.** This spike measures context/output
  impact and workflow friction. Whether the model makes better decisions
  with compressed output is a later, harder evaluation.
- **No broad agent-framework comparison.** RTK is the only tool under
  test here.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** - Spike | Do we know whether RTK works cleanly inside jig's hook-heavy workflow? | **Spike.** We need measured behavior before designing an integration. |
| **P** - Path | Should we implement compatibility first or measure first? | **Measure first.** Install RTK locally, run a disposable E2E jig slice, then decide which follow-up path exists. |
| **I** - Interface | Where could integration be needed? | Hook config, scaffold/plugin installation, host adapters, and docs. The spike records which interfaces actually need work. |
| **D** - Data | What evidence decides the next step? | Paired disabled/enabled output metrics by command family plus qualitative friction notes. |
| **R** - Rules | What protects users from surprise behavior? | RTK remains opt-in; raw-output/disable behavior and telemetry settings must be documented before any follow-up integration is proposed. |

## Known constraints

- **RTK installation may require network and user approval.** The spike
  must re-verify the current official install docs before running any
  installer and record exactly what changed.
- **Token accounting may be approximate.** If the host does not expose
  exact context/token usage, the spike records raw UTF-8 bytes, line
  counts, and a consistent estimated-token formula for shell outputs.
- **Claude and Codex integration paths may differ.** Claude can use
  hook-level command rewriting. Codex may only see prompt-level
  `AGENTS.md` guidance unless or until Codex exposes an equivalent hook
  surface in jig's adapter.
- **Hook order matters.** Jig's own hooks include blocking and
  context-injecting behavior. The spike must note whether RTK runs
  before/after jig hooks and whether either system masks the other.
- **RTK should not hide debugging evidence.** Any recommendation must
  include an escape hatch for commands where full raw output is needed.

## Slices

- [044-01 - rtk-e2e-measurement-spike](slice-01-rtk-e2e-measurement-spike.md)

## Clarifications

### Q1: Should RTK be treated as a dependency candidate or as an optional accelerator?

Optional accelerator. The spike can recommend integration affordances,
but jig should not require RTK to run.

### Q2: Should the dummy E2E implementation land as a real feature?

No. It is disposable measurement scaffolding. The durable artifact is the
Findings/Outcome evidence in the spike and any follow-up specs it opens.

### Q3: What counts as enough evidence?

One complete paired run with RTK disabled and enabled, covering both the
fixed command corpus and the dummy spec/slice implementation. More runs
are welcome if the first run is noisy, but the spike should not turn into
a long-running benchmarking project.
