---
status: DRAFT
skill: jig:refactor
---

# Spec 062: Refactor / migration workflow

> Implements [ADR-0019](../../decisions/adr-0019-refactor-workflow.md):
> a parallel, proportional, teeth-gated refactor lifecycle distinct from
> the spec-driven (SDD) and bug-fix lifecycles, for behaviour-preserving
> structural change and migrations — the third member of the
> behaviour-change taxonomy (add / restore / **preserve**).

## Overview

jig has `spec-workflow` for **adding new behaviour** and (drafted in
[spec 058](../058-bug-fix-workflow/spec.md) / [ADR-0016](../../decisions/adr-0016-bug-fix-lifecycle.md))
`jig:bug-fix` for **restoring correct behaviour**. Refactors and
migrations — **changing structure while preserving behaviour** — have no
home: they either get over-ceremonied through SDD (a migration isn't
*new* behaviour, so slices/AC fit awkwardly and the thing that matters,
proof behaviour didn't change, has nowhere to live) or under-disciplined
as "just commit it" (no captured *before*-baseline = no attestation
behaviour was preserved, the most common silent-regression path).
`code-health` ([spec 060](../060-code-health-capability/spec.md)) *detects*
debt but does not *discipline paying it down*.

This spec adds **`jig:refactor`** — a first-class workflow (peer to
`spec-workflow` and `jig:bug-fix`, owns its orchestration) backed by a
`refactor.py` helper (sibling of `workflow.py` / `bug.py`, sharing
`_common/`). It delivers:

- a refactor-shaped lifecycle `SCOPED → BASELINED → REFACTORING →
  REVIEWED → (EQUIVALENCE_CONFIRMED) → DONE`, plus a `CARVED_OUT` seam;
- **teeth gates inverted from bug-fix** — capture the equivalence
  baseline **green on unmodified code before any edit** (ordering-
  enforced), then prove it **green/at-baseline after**;
- a **pluggable equivalence oracle** — `deterministic` (golden/
  characterization tests via `tdd.py`, machine-witnessed) **or** `eval`
  (score ≥ recorded baseline within a variance bound, for non-
  deterministic / LLM-driven units; jig **attests presence + a recorded
  verdict**, it does not run evals — ADR-0011 trust boundary);
- **proportionality enforced downward** — `triage` bows out of trivial
  refactors ("lean on the existing suite + commit"), reserving the
  record + gates for standard/gnarly tiers;
- a **carve-out seam** that hands the genuinely-new-behaviour remainder
  of a migration to `workflow.py new` instead of letting it masquerade
  as preserved behaviour;
- a durable one-file record `docs/refactors/NNN-slug.md` and its own
  board `docs/refactors/README.md`;
- a refactor-tailored review pass reusing the ADR-0014 evidence gate,
  plus reused craft (`pr-review`), **conditional** security
  (`security-review`), and **conditional arch** (`arch-review`) — the
  arch pass returns here vs bug-fix because a refactor *can* carry design.

See [ADR-0019](../../decisions/adr-0019-refactor-workflow.md) for the full
decision (gate table, pluggable-oracle rationale, record schema, reuse
map, and the CWV migration worked example).

## Decomposition

**SPIDR analysis:**

- **Spike** — none. The design is settled in ADR-0019. The one capability
  the teeth shell out to (single-named-test runs via `tdd.py`) is **not**
  a new prerequisite here — it is delivered by [058-01](../058-bug-fix-workflow/slice-01-tdd-targeted-test.md)
  (ADR-0016), on which 062-02 depends.
- **Paths** — the lifecycle is a path through states. The vertical cut is
  by *capability* (record+numbering, then the oracle gates, then review,
  then carve-out+close, then skill+routing), each observable end-to-end
  via the CLI.
- **Interfaces** — `refactor.py` subcommands (`new` / `triage` /
  `transition` / `carve-out` / `status-board` / `--release`) and the
  `jig:refactor` skill are the external surfaces.
- **Data** — the record frontmatter schema (`status` / `tier` /
  `claimed_by` / `equivalence_oracle` / `baseline_ref` /
  `baseline_confirmed_at` / `equivalence_confirmed_at` / `behaviour_delta`
  / `carved_out_to` / `security_surface` / `arch_surface`) and the board.
- **Rules** — the gate predicates (baseline-green-before-edit ordering;
  equivalence green/≥-baseline after; review evidence at REVIEWED;
  behaviour-delta + learning at DONE), the pluggable-oracle dispatch,
  tier-driven strictness, and the deliberateness bypass env vars.

**Slicing rationale.** Each slice lands end-to-end observable value:
062-01 lets you *create and triage* a refactor; 062-02 adds the
pluggable-oracle teeth (the heart of the workflow); 062-03 adds review;
062-04 adds the carve-out seam + close gate; 062-05 ships the skill +
routing docs. 062-02 depends on 058-01 (deterministic oracle shells to
`tdd.py` targeted runs) and 062-01 (the record to gate). The bug-fix
workflow (058) and this one share the `_common/` machinery; landing 058
first lets 062 reuse the bug record/board/claim patterns rather than
re-deriving them.

## Slices

- [062-01 — `refactor.py` core: new / triage / numbering / record / board / claim](slice-01-refactor-core.md)
- [062-02 — pluggable-oracle teeth: baseline-before-edit + equivalence gates (deterministic + eval-attest)](slice-02-oracle-gates.md)
- [062-03 — review integration: refactor-review + craft + conditional security + conditional arch](slice-03-review-integration.md)
- [062-04 — carve-out seam + close/learning + behaviour-delta gate + origin/main reservation](slice-04-carveout-close.md)
- [062-05 — `jig:refactor` skill + plugin wiring + workflow.md routing](slice-05-skill-and-docs.md)
