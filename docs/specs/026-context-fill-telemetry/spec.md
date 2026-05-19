---
status: DONE
skill: (none — dev infrastructure)
tier: (none — dev infrastructure)
---

# Spec 026: context-fill telemetry (extend `jig-context-check.sh`)

## Overview

`hooks/scripts/jig-context-check.sh` fires on `SessionStart` and is
jig's only context-budget guardrail today. It counts MCP-server entries
in project config and warns above 8 — that's a **proxy** for tool-
description overhead, not a measure of actual context-window
consumption. The same CLAUDE.md that asserts "Dumb zone = >40% context
fill; above this, model recall degrades" gives the agent no signal of
how full the window actually is — until recall has already started
degrading.

This spec extends the hook (and adds at least one companion firing
point) so the warning is rooted in actual byte / token estimates of
what the session has loaded — primer doc (CLAUDE.md), key always-loaded
docs, and an estimate of transcript growth — not in a five-year-old
proxy metric. Jig's surface stays a **soft warning**: it emits
`additionalContext` once an estimate crosses a threshold and suggests
`/jig:memory-sync` + `/compact`. **It does not refuse** any action —
that's servo's domain (cf. servo spec 003 context-fill hard refusal
gate per [servo specs/README.md](https://github.com/ramboz/servo/blob/main/docs/specs/README.md)).

## Why now

- **Empirical trigger.** The 2026-05-18 AI-native review of jig (this
  conversation) identified context-fill measurement as the highest-
  leverage gap for long-running sessions. The dumb-zone threshold is
  cited in CLAUDE.md as load-bearing; the current hook can't measure
  it.
- **CLAUDE.md just got slimmed** (spec 025 in flight) — the primer-doc
  contribution to context becomes a stable enough baseline to measure
  against. Before 025, a moving target.
- **Servo defines the hard-gate side.** With servo spec 003 closing
  the unattended path, jig can ship the supervised-warning side
  without scope creep — and the two halves share a clear contract:
  same estimate function, different action (warn vs refuse).

## Goals

1. **Measure, don't proxy.** The hook estimates context bytes / tokens
   consumed by always-loaded artifacts (CLAUDE.md + memory layer + any
   doc the session has pulled into context by SessionStart). The
   MCP-server count check stays as a secondary signal.
2. **Threshold lives in one place.** A single soft-warn threshold
   (default ~30% of a configurable context window size) emitted as
   `additionalContext` — *not* hardcoded across multiple scripts.
3. **Estimate is honest about its limits.** Bytes ≠ tokens; the
   estimator documents the conversion ratio it uses and surfaces it
   in the warning so the user can calibrate.
4. **One additional firing point.** Beyond `SessionStart`, the hook
   re-evaluates at a second checkpoint — most likely on
   `UserPromptSubmit` at sampled intervals, or on `Stop`. Avoid firing
   every turn (cost).
5. **No refusal behavior.** The hook only ever emits warnings; it
   never sets `continue: false`. Hard-gate logic stays in servo.
6. **Shared estimator interface.** The byte/token estimator is
   factored as a small Python module (importable, testable in
   isolation) so servo can call it via subprocess for its hard-gate
   path without re-implementing the math.

## Non-goals

- **No measurement of model-side context fill.** The hook can't see
  what the model has in its window; it can only estimate from on-disk
  + transcript bytes. The warning is best-effort.
- **No transcript-token telemetry.** Per-turn token counting is
  servo's domain (cost ceiling); jig keeps a static-bytes estimate.
- **No CLAUDE.md slimming.** That's spec 025. Spec 026 assumes 025
  has landed and consumes its output.
- **No changes to other hooks** (`jig-memory-scan.sh`, `jig-spec-gate.sh`,
  `jig-task-capture.sh`, `jig-telemetry.sh`). The estimator may be
  *callable* from any of them, but each retains its current scope.
- **No new skill.** Hook + helper module only.

## Open questions

- **Threshold value.** Default 30%? 35%? The dumb-zone threshold
  CLAUDE.md cites is 40%; warning at 30% gives the user time to act
  before degradation hits. Pin during slice 026-01 with a one-line
  rationale.
- **Context window size assumption.** Opus 4.7's window is large
  enough that absolute byte counts matter more than percentages.
  Decide whether the env var override is in tokens, bytes, or % of
  a sentinel constant. Lean: bytes with a configurable model-context-
  size sentinel (default sized for Opus 4.7), with the percentage
  computed at warning time.
- **Second firing point.** `UserPromptSubmit` (sample every Nth turn)
  vs `Stop` (after each completed exchange). Lean `Stop` — keeps the
  cadence predictable and avoids stuttering on rapid turns. Decide
  during implementation.
- **Estimator boundary with servo.** Servo's spec 003 wants the same
  estimator math to drive its refusal gate. Options: (a) servo
  subprocess-invokes a jig helper, (b) both projects copy the math.
  Lean (a) — same shape as servo's ADR-0001 jig-detector reuse.
  Crystallize when servo spec 003 reaches READY_FOR_REVIEW; this spec
  doesn't block on it.

## Decomposition

One active slice; companion slices DEFERRED on signal.

### Slices

- [026-01 — estimator-and-soft-warn-hook](slice-01-estimator-and-soft-warn-hook.md) — DRAFT
- 026-02 — second-firing-point — DEFERRED (no slice file yet; promote
  to DRAFT once 026-01 is in use and the static SessionStart-only
  warning is shown to be insufficient).
- 026-03 — servo-shared-estimator — DEFERRED (no slice file yet;
  promote to DRAFT when servo spec 003 reaches READY_FOR_REVIEW and
  the subprocess-call boundary is needed).

## References

- **Originating conversation:** 2026-05-18 — AI-native review of jig,
  P0 item #1 ("No real context-fill measurement"). See review summary
  in the same conversation.
- **Servo counterpart:** servo spec 003-agent-loop carries the hard-
  gate refusal — the unattended cousin of jig's soft warning. The
  estimator math is shared; the action diverges.
- **Existing hook:** `hooks/scripts/jig-context-check.sh` — current
  MCP-count-only implementation.
- **Dumb-zone principle:** CLAUDE.md "Key terms" section cites
  Horthy's >40% context-fill threshold. This spec converts the cited
  rule from descriptive (in the hot cache) to measurable (in a hook).
