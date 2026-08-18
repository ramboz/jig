---
status: DONE
skill: bug-fix
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 091: Bug-fix repository closure

> **Status: built.** [ADR-0037](../../decisions/adr-0037-bug-fix-repository-closure-evidence.md)
> is Accepted (2026-08-18, after four frame-critique passes) and slice 091-01
> shipped the lifecycle changes below: the `closure_schema:` marker, the
> pre-fix inventory gate, the post-fix call-site closure gate, the bug-review
> closure lens, and the tool-neutral skill guidance.

## Overview

Implement [ADR-0037](../../decisions/adr-0037-bug-fix-repository-closure-evidence.md):
non-trivial bug fixes must inventory existing/convergent logic and history
before implementation, then account for affected call sites before review.
The change closes the workflow gap exposed by Mystique PR 3417 without making
semantic indexing a prerequisite.

## Assumptions

- The existing bug parser can add versioned sections without invalidating any
  record created before this schema. Compatibility is keyed to an **explicit,
  creation-time frontmatter marker** — a `closure_schema:` field stamped by
  `bug.py new` — **not** to the presence or absence of the closure body
  sections, and **not** to an enumerated record range (the legacy corpus keeps
  growing while this spec sits DRAFT — 001–033 at time of writing).

  This distinction is load-bearing: "legacy" must be an independent signal, not
  inferred from section-absence. If legacy were defined as "no closure
  sections," the FIXING gate could not tell a genuine pre-schema record apart
  from a new record whose author simply omitted the headings to evade the gate
  — the parser hands both identical text. Keying to a stamped frontmatter field
  makes *legacy-by-omission* (no marker → exempt) distinguishable from
  *evasion-by-omission* (marker present, sections empty → gate fires). Verified
  absent today: no existing record (001–033) carries any schema/version
  frontmatter field, and `bug.py`'s record template emits none, so a new field
  is additive and cannot collide. This must be proved with compatibility
  fixtures covering both a marker-bearing new record (gate enforced) and an
  unmarked legacy record (gate exempt, still transitionable) before the gate is
  enabled.

- The marker scheme presumes **tool-mediated creation**: only `bug.py new`
  stamps `closure_schema:`, so a hand-authored record (or any non-`new_bug`
  path) is unmarked and travels the legacy-exempt path. This is acceptable and
  intended — it collapses into the same deliberateness-gate / `*_GATE=0` bypass
  limit the ADR-0011 lineage and ADR-0037 already concede (a gate cannot compel
  an actor who bypasses the tool). It matters most for jig's own dogfood: jig
  bug records must be created via `bug.py new` to be gated at all. The
  compatibility fixtures pin both the tool-created-marked and legacy-unmarked
  cases explicitly.

## Decomposition

SPIDR rules split: one vertical slice changes the record schema, transition
gates, reviewer prompt, skill guidance, and compatibility tests together.
Splitting the template from enforcement would create an unusable intermediate
state.

## Slices

- [091-01 — repository-closure evidence and gates](slice-01-repository-closure-evidence-and-gates.md)
