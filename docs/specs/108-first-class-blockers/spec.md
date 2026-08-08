---
status: DRAFT
skill:
use_cases: []
---

# Spec 108: First-class blockers

> Reserved 2026-08-07. DRAFT — origin is a downstream consumer (the Gauge
> portfolio dashboard) that wants a clean "blocked" count; jig has no first-class
> blocker concept today, only heterogeneous proxies. Body is a starting sketch,
> to be shaped before implementation.

## Overview

jig tracks lifecycle state (`DRAFT → … → DONE`, plus `DEFERRED`/`ABANDONED`) and
dependencies, but it has **no first-class notion of "this work is blocked, and on
what."** Consumers that want to answer *"how many blockers does this project
have right now?"* must approximate from a grab-bag of proxies that mostly mean
**parked**, not **actively blocking**:

- `DEFERRED` slices carrying a `**Resolution trigger:**` line,
- deferred decisions in `docs/refinement-todo.md`,
- unmet slice `dependencies:`,
- the legacy Compass narrative `blockers` array (only present for
  legacy-Compass sources).

These conflate *"deferred by choice, will resurface on a trigger"* with *"a live
work item is stuck waiting on X."* A downstream dashboard (Gauge) is currently
forced to render an **approximate, labelled** blocker count from them. This spec
proposes a small, explicit convention so the signal becomes honest and
derivable.

## Sketch of the decision (to be shaped)

A **first-class blocker** on an in-flight slice: a `**Blocked:**` body line
(mirroring the existing `**Resolution trigger:**` / `**Deferred:**` conventions)
and/or a `blocked_by:` frontmatter field naming what it is blocked on (an owner
decision, another slice, an external dependency, a review). Distinct from
`DEFERRED` (parked by choice) and from `dependencies:` (not-yet-started ordering)
— a blocker is *"started, cannot proceed, waiting on a named thing."* The status
board and any `workflow.py` blocked-count helper then read it directly.

Open questions for shaping: is a blocker a slice **state** or an **annotation on
`IN_PROGRESS`**? Does it need a typed reason (you / external / dependency /
review)? Does clearing it require a trigger like `DEFERRED`?

## Assumptions

- jig has no `Blocked`/`blocked_by` field today — verified: the only
  blocker-shaped tokens in the corpus are `**Resolution trigger:**` (on
  `DEFERRED` slices), refinement-todo deferred decisions, `dependencies:`, and
  the legacy narrative `blockers` array. (Enumerated by search across
  `docs/specs/**` and `workflow.py`; if a `Blocked:` convention already exists
  elsewhere, this spec folds into documenting it.)

## Decomposition

_TBD — SPIDR. Likely small: a **Rules/Data** slice defining the convention +
`spec_lint` validation, and an **Interface** slice surfacing a blocked count on
the status board (the consumer-visible value)._

## Slices

- [108-01 — tbd](slice-01-tbd.md)
