---
status: DONE
skill: spec-workflow
---

# Spec 064: Spec/ADR frame-hardening

> Implements [ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md).
> **DONE (2026-06-08).** The 064-01 retro spike returned **GO** (qualified;
> ADR-0020 Accepted). All five slices shipped: grounding (02), the spec-side
> frame-critique pass + READY_FOR_REVIEW gate (03), the derived trigger +
> session-plan dispatch (04), and the ADR-side `adr.py accept` gate (05).
> OQ1–OQ4 resolved (ADR-0020 `## Amendments`). Per-slice load-bearing invariants
> live in the [status-board](../README.md) Notes column.

## Overview

jig's reviewers validate that an implementation *conforms to its spec/ADR* —
they reduce **variance** around the frame but never validate **the frame
itself**. A wrong premise (hallucinated library capability, misread of existing
code, unstated load-bearing assumption) propagates and gets executed with
discipline, which *masks* the error. This spec adds an early, mostly-soft
**frame-hardening** layer at spec/ADR authoring time, per ADR-0020:

1. **Grounding (probe-first)** — factual claims about runnable surfaces are
   backed by an executed probe or a citation, or else explicitly marked as an
   assumption. Never asserted.
2. **Assumptions / kill-criteria** — a risk-gated first-class section
   enumerating load-bearing assumptions and "what would make this wrong."
3. **Adversarial frame-critique pass** — a `frame_review`-gated review pass
   (sibling of `arch_review` / `code_health_review`) whose reviewer hunts the
   one load-bearing assumption most likely to be wrong, at READY_FOR_REVIEW,
   *before* implementation. **Trigger is derived from the grounding output**, not
   an author judgment call.

**Deferred (per ADR-0020 Option C):** Tier 2 best-of-N drafting + reconciliation
— addresses variance not bias, correlated samples manufacture false consensus,
~4× cost. Revisit only behind a generator-independent verifier + forced-orthogonal
draft objectives. **Not in this spec's scope.**

## Goals / Non-goals

**Goals**
- Catch wrong-premise specs/ADRs *before* implementation spends effort on them.
- Make the frame-critique pass **auto-trigger** off a derived signal, so it is
  neither a dead loop nor a per-author judgment call.
- Keep every mechanism **advisory / deliberateness-signal** (ADR-0011), never a
  hard blocking gate.
- Default-off on jig's common case (inline-mirror / refactor / docs) to honor
  the 055/057 lean arc.

**Non-goals**
- Tier 2 best-of-N (deferred, ADR-0020 Option C).
- Cross-model frame-critique (noted in ADR-0020 as a future knob; OQ4).
- Any hard human-only or CI-style enforcement (stays out-of-band per ADR-0011).
- Mandatory assumptions section on non-triggering artifacts.

## Decomposition (SPIDR)

- **Spike** — 064-01: retro over existing specs/ADRs to ground ADR-0020 §A1
  (does this class of error recur, would the machinery have caught it?). Gates
  everything below.
- **Rules** — 064-02: the grounding requirement (probe-first claims; mark
  assumptions) baked into the spec/ADR templates + author-step contract. This
  step *produces* the trigger signal.
- **Interface** — 064-03: the `frame_review`-gated adversarial frame-critique
  reviewer pass (`review.py frame-critique` + verdict artifact) + the **spec-side**
  READY_FOR_REVIEW gate, mirroring the ADR-0014 gated-pass pattern.
- **Rules** — 064-04: the **derived trigger** — author/`clarify` step sets
  `frame_review` mechanically from the grounding output per the ADR-0020 rule.
- **Interface** — 064-05: the **ADR-side** gate at `adr.py accept` + an
  ADR-appropriate evidence-artifact home (split from 064-03 on 2026-06-07 because
  ADRs aren't slices and need a separate evidence subsystem; OQ2/OQ3 enforcement
  for ADRs lands here).

Each post-spike slice is independently landable and observable; none is pure
intermediate state.

## Slices

| Slice | Title | Status | Notes |
|---|---|---|---|
| [🔬 064-01](slice-01-retro-frame-error-census.md) | retro-frame-error-census | **DONE** | **Gating spike → GO.** Grounded ADR-0020 §A1 (4 catchable frame errors / 33 artifacts; kill-criterion not met). |
| [064-02](slice-02-grounding-requirement.md) | grounding-requirement | **DONE** | Probe-first claims + risk-gated `## Assumptions`/`## Kill criteria` in templates + author contract. Produces the trigger signal for 04. |
| [064-03](slice-03-frame-critique-pass.md) | frame-critique-pass | **DONE** | `frame_review`-gated adversarial pass + **spec-side** READY_FOR_REVIEW gate. Sibling of arch/code-health (ADR-0014). ADR-side gate split to 064-05. |
| [064-04](slice-04-derived-trigger.md) | derived-trigger | **DONE** | `derive_frame_review` + `frame-review-needed` from the spec's `## Assumptions`; `session_plan` dispatches the pass. |
| [064-05](slice-05-adr-accept-gate.md) | adr-accept-gate | **DONE** | **ADR-side** gate at `adr.py accept` + ADR evidence home + `record-review --adr`. Enforces OQ2/OQ3 for ADRs (always-on + legacy grace). |

## Open questions

**All resolved** (see [ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md)
`## Amendments`, 2026-06-07): OQ1 retro depth → stratified sample (GO); OQ2
placement → specs @ READY_FOR_REVIEW + ADRs @ `adr.py accept`; OQ3 → ADRs
always-on (legacy markerless ADRs grandfathered); OQ4 → ship rung-1 (fresh-context
subagent + equal-or-stronger model policy), defer rung-3 (non-Claude cross-model)
to `docs/refinement-todo.md`.
