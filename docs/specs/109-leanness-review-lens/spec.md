---
status: DONE
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 109: Leanness-review lens

## Overview

SPIDR gives jig strong vertical-slice discipline at the spec→slice altitude, but
the leanness value it embodies — *smallest thing first, avoid over-engineering* —
never propagated into jig's review surfaces. A maintainer audit found jig has
**no guidance toward a minimal viable architecture**: the value is re-derived
case by case inside individual ADRs (e.g. ADR-0002's deliberate stub, ADR-0023's
extract-at-third-transition), never applied as a standing review lens.

Concretely, the two **spec-workflow** review passes where over-engineering would
surface carry no leanness evaluation today:

- The **arch pass** prompt (`build_arch_review_prompt`,
  [review.py:996](../../../skills/independent-review/review.py)) evaluates module
  boundaries, public contracts, and design coherence (its `## Evaluate` block,
  ~L1088), but never asks whether a *simpler* architecture would satisfy the
  same acceptance criteria. The bundled `arch-review` SKILL.md baseline buckets
  (summary / strengths / concerns / open questions) contain no
  over-engineering / YAGNI / minimal-architecture language (grep of
  `skills/arch-review/` for `lean|yagni|premature|minimal viable|simplest`
  returns no relevant hit).
- The **reconciliation review** (`build_reconciliation_prompt`,
  [review.py:1463](../../../skills/independent-review/review.py)) judges
  faithfulness, honesty, and scope-creep-in-docs, but does not sweep for
  *over-build* — code or abstraction added beyond what the spec's ACs need.

This spec adds a **leanness lens** — over-engineering / premature-abstraction /
minimal-viable-architecture — to those two existing passes. It is the
**retrospective** half of a two-altitude value: the **prospective** half
(shaping new work lean, before specs exist) is owned by the sibling `shaper`
project (its ADR-0005 / spec 008). This spec deliberately does **not** build a
new gate.

**Scope boundary.** Coverage is spec-workflow-only. The bug-fix lifecycle (no
arch pass, no reconciliation — `skills/bug-fix/SKILL.md:299`) gets no leanness
coverage from this spec; extending it there is a demand-gated follow-up
([docs/refinement-todo.md](../../refinement-todo.md)). See
[ADR-0055](../../decisions/adr-0055-leanness-lens-folds-into-existing-passes.md).

## Assumptions

None.

*(All load-bearing claims are probe-verified: arch builder `review.py:996`, reconciliation builder `review.py:1463`, and a bounded grep of `skills/arch-review/` for leanness language returning no relevant hit.)*

## Decomposition

**Design rationale — the load-bearing choice (ADR trigger, surfaced at
reconciliation).** The leanness lens is **folded into the existing arch +
reconciliation passes** (always-on *within* those passes), **not** built as a
new standalone gated `leanness_review` pass with its own frontmatter flag and
evidence file (the shape of `code_health_review`). Folding in is the
minimal-viable choice — it reuses passes that already run, adds no new gate,
and self-demonstrates the spec's own thesis. The rejected alternative (a
dedicated leanness gate) is heavier and would itself be the over-engineering
this spec fights. Whether this choice warrants a written ADR is decided at
reconciliation per the checklist's ADR-trigger item; it is recorded here so the
decision isn't silently re-litigated.

SPIDR — split by **Interface** (which review surface), arch pass first:

- **109-01 (Interface)** — arch-pass leanness lens: extend
  `build_arch_review_prompt`'s `## Evaluate` block and the `arch-review`
  SKILL.md baseline buckets so the arch pass explicitly asks whether a simpler
  architecture satisfies the ACs (over-engineering / premature abstraction /
  speculative generality). Findings flow through the existing
  `[blocker]`/`[nit]` verdict envelope — no new gate.
- **109-02 (Interface)** — reconciliation leanness sweep: extend
  `build_reconciliation_prompt` and the reconciliation checklist so
  reconciliation retrospectively sweeps for over-build relative to the spec's
  actual needs.

**Out of scope.** No new review pass, flag, or evidence file. No change to the
compliance/craft/code-health/design passes. The prospective shaping half lives
in `shaper`, not here.

## Slices

- [109-01 — arch-pass-leanness-lens](slice-01-arch-pass-leanness-lens.md)
- [109-02 — reconciliation-leanness-sweep](slice-02-reconciliation-leanness-sweep.md)
