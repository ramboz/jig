---
status: DRAFT
skill: spec-workflow
---

# Spec 064: Spec/ADR frame-hardening

> Implements [ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md).
> **DRAFT — implementation gated on the 064-01 retro spike.** Filed to capture
> the design discussion; do not implement slices 02+ until 064-01 returns *go*.

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
  reviewer pass (`review.py frame-critique` + verdict artifact + gate wiring),
  mirroring the ADR-0014 gated-pass pattern.
- **Rules** — 064-04: the **derived trigger** — author/`clarify` step sets
  `frame_review` mechanically from the grounding output per the ADR-0020 rule.

Each post-spike slice is independently landable and observable; none is pure
intermediate state.

## Slices

| Slice | Title | Status | Notes |
|---|---|---|---|
| [🔬 064-01](slice-01-retro-frame-error-census.md) | retro-frame-error-census | DRAFT | **Gating spike.** Grounds ADR-0020 §A1 (kill criterion). Go/no-go for 02–04. |
| [064-02](slice-02-grounding-requirement.md) | grounding-requirement | DRAFT | Probe-first claims + mark-assumptions in templates + author contract. Produces the trigger signal for 04. |
| [064-03](slice-03-frame-critique-pass.md) | frame-critique-pass | DRAFT | `frame_review`-gated review pass at READY_FOR_REVIEW. Sibling of arch/code-health (ADR-0014). |
| [064-04](slice-04-derived-trigger.md) | derived-trigger | DRAFT | Author/`clarify` sets `frame_review` mechanically from grounding output. |

## Open questions

Carried from [ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md) Open
questions (OQ1–OQ4): retro depth; frame-critique placement (READY_FOR_REVIEW
only vs also at `adr.py accept`); whether ADRs default-on unconditionally; and
whether cross-model frame-critique warrants a thin slice now. **Resolve OQ1
before 064-01; OQ2–OQ4 before 064-03/04.**
