---
status: IN_PROGRESS
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 074: Host-native phase modes

> Parked follow-up to [ADR-0027](../../decisions/adr-0027-host-native-phase-modes.md):
> use Codex / Claude planning and implementation modes as advisory workflow
> affordances, while keeping jig's specs, slices, and review evidence as the
> canonical lifecycle state.

## Overview

Jig's current workflow is artifact-first: specs and slices define work;
`workflow.py` transitions state; reviewer artifacts gate progress. That model
is the right source of truth, but the host UX can still help. Codex and Claude
both have planning/editing rhythms that can make the jig lifecycle feel more
natural: plan first, commit the plan to artifacts, then implement.

This spec captures the deferred work needed to make jig **mode-aware, not
mode-dependent**. The user-facing promise is small:

- use the host's planning surface for clarify/spec/session-plan work;
- use the host's implementation/editing surface for slice execution;
- keep review and reconciliation anchored in jig's existing read-only
  reviewer prompts and durable evidence files;
- never treat host mode state as a transition gate.

The idea is parked until a concrete host-adapter push resumes, especially
Codex scaffold/plugin work from [Spec 033](../033-host-adapter-portability/spec.md),
or until repeated workflow friction shows that the current prompt cookbook
needs explicit phase-mode guidance.

## Assumptions

- Jig's own docs already support the design direction: host adapters are the
  portability boundary (spec 033), `session-plan` is the thin-orchestrator
  planning bridge (spec 057), and review evidence remains the gate input
  (ADR-0014).
- Exact host-mode behavior is not stable enough to encode without a fresh
  implementation-time verification pass. Each slice below must re-check the
  current Codex and Claude surfaces before changing generated host files.

## Decomposition

SPIDR - primarily **Interface** plus **Rules**:

- **Interface:** Claude and Codex need different host-native wording and
  adapter rendering.
- **Rules:** mode hints must never become lifecycle gates or a second source
  of truth.

No spike is needed yet because the architectural posture is captured in
ADR-0027. If a future host surface is unclear, that verification belongs in the
first resumed slice as implementation grounding.

## Slices

- [074-01 - phase-mode vocabulary and docs](slice-01-phase-mode-vocabulary-and-docs.md)
- [074-02 - session-plan mode hints](slice-02-session-plan-mode-hints.md)
- [074-03 - host-adapter rendering](slice-03-host-adapter-rendering.md)
