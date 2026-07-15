---
status: DRAFT
skill: bug-fix
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 091: Bug-fix repository closure

> Reserved on 2026-07-15 via `workflow.py new`. Body to be drafted in a feature branch.

## Overview

Implement [ADR-0037](../../decisions/adr-0037-bug-fix-repository-closure-evidence.md):
non-trivial bug fixes must inventory existing/convergent logic and history
before implementation, then account for affected call sites before review.
The change closes the workflow gap exposed by Mystique PR 3417 without making
semantic indexing a prerequisite.

## Assumptions

- The existing bug parser can add versioned sections without invalidating bugs
  001-010. This must be proved with compatibility fixtures before the gate is
  enabled.

## Decomposition

SPIDR rules split: one vertical slice changes the record schema, transition
gates, reviewer prompt, skill guidance, and compatibility tests together.
Splitting the template from enforcement would create an unusable intermediate
state.

## Slices

- [091-01 — repository-closure evidence and gates](slice-01-repository-closure-evidence-and-gates.md)
