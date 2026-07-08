---
status: DONE
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 078: Gate-bypass telemetry

> Source: EngTips self-audit brief-04, folded into this spec and retired
> (EngTip #19 "Don't Be a Hero", #20 "AI, Authorship, and
> Accountability"). Reserved 2026-06-19 via `workflow.py new`.

## Overview

jig's gates are, per ADR-0011, **deliberateness signals, not human-only
enforcement** — each carries an env-var escape (`JIG_REVIEW_EVIDENCE_GATE=0`,
`JIG_SECRET_SCAN_APPROVED=1`, `JIG_CONVENTIONS_APPROVED=1`). This framing
is honest, but the escapes are **un-instrumented**: when a gate is
bypassed, nothing is logged. So a maintainer can't tell after the fact
that a slice reached DONE with the evidence gate off, and nobody can
answer "how often is each gate bypassed?" — an override-frequency audit
trail that *informs* (though a bypass count alone, lacking a respected-fire
denominator, cannot by itself *settle*) whether a gate earns its keep or is
pure friction. A bypass that leaves no trace is the EngTip #19 "silent
heroics" failure mode.

jig already has the infrastructure: `jig-telemetry`, the skill-routing
trace (`.claude/skill-usage.jsonl`, spec 041), and `workflow.py
routing-stats` as a read-only histogram surface. A bypass event is a
natural sibling.

**End state:** each gate emits one structured, content-free event when it
honors its override (gate name, env var, timestamp, branch/spec-ref),
fail-open, to the existing local gitignored telemetry sink; a read-only
digest prints per-gate bypass counts over `--days N`.

Non-goal inherited from the source review: this does **not** make gates
harder to bypass. The bypasses stay bypassable; the change makes them
visible. Events stay local, content-free, and gitignored — log the fact of
the bypass, never the diff, secret, or prompt content.

## Assumptions

- **The existing telemetry sink/format can carry a new event type**
  without disrupting `routing-stats` readers. *Probe-back in slice 01*
  against `jig-telemetry` + `.claude/skill-usage.jsonl` before reusing it;
  if reuse is awkward, a sibling JSONL is acceptable (same pattern).
- **spec 056's `.jig/spec-ref` marker** is available for attribution
  (working-tree-local, gitignored). Used best-effort; absence must not
  block the emit.

## Clarifications

- **Depth (resolved 2026-06-19):** spec.md + SPIDR slice files now.
- **Gates in scope for v1 (resolved):** start with the **review-evidence
  gate** (highest value) and the **conventions spec-gate** (feeds the
  parent brief-08 open question — "is the gate catching anything?" — with
  override-frequency evidence; a full answer needs the deferred
  respected-fire denominator, per the refinement-todo entry). Secret-scan +
  context bands follow.
- **Event vs. counter (guidance):** per-event append (matches the JSONL
  pattern); aggregate at read time in the digest.
- **No fail-closed (hard rule):** a telemetry write failure must never
  block the underlying operation — the gate already decided to allow it.

## Decomposition

SPIDR — primarily a **Data** split (a new event record + its read-only
aggregation), with a **Path** seam (the bypass code path in each gate).

- **078-01 (emit):** add the bypass event at the override point of the
  review-evidence gate + conventions spec-gate; reuse the telemetry sink;
  fail-open; gitignored; content-free. Delivers an auditable trail today.
- **078-02 (digest):** a read-only per-gate bypass histogram over `--days
  N` (extend `routing-stats` or a sibling `gate-stats`) — an
  override-frequency audit trail answering "how often is each gate
  bypassed?" (a bypass count has no respected-fire denominator, so it is
  deliberately not a "gate is deadweight" verdict).

## Slices

- [078-01 — emit bypass events](slice-01-bypass-event-emit.md)
- [078-02 — gate-stats digest](slice-02-gate-stats-digest.md)
