---
status: DRAFT
skill: bug-fix
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 105: Durable-failure quarantine (jig half)

> **Status: recorded, not yet built.** [ADR-0050](../../decisions/adr-0050-durable-failure-quarantine.md)
> is Proposed and this spec is reserved; the `bug.py` lifecycle changes below are
> not implemented in the branch that introduced this record. Left DRAFT
> deliberately. This is the **jig half** of the durable failure-quarantine piece
> of the long-horizon-autonomy bridge; the servo half is servo spec 024.

## Overview

Implement the jig side of [ADR-0050](../../decisions/adr-0050-durable-failure-quarantine.md):
a durable anti-thrash boundary on the bug-fix lifecycle. Today the bug record has
no memory of how many times a fix has been attempted, so an unattended (or
supervised) loop can re-attempt the same doomed fix indefinitely — the core
long-horizon failure mode `oh-my-cli` bounds with "third identical failure →
quarantine; retry requires new diagnostic evidence."

This spec adds: a terminal **`QUARANTINED`** bug state, an **`attempts:`** counter,
an automatic route-to-quarantine at `attempts ≥ N` that freezes the evidence
sections and releases the claim, a **release-requires-new-evidence** rule, and the
**attest-only handshake** by which servo's plateau (servo spec 024) can drive a
jig bug to `QUARANTINED` without jig ever re-deriving an oracle score (ADR-0022
boundary).

## Assumptions

- `skills/bug-fix/bug.py` exposes `VALID_BUG_STATUSES`,
  `TERMINAL_NON_DONE_STATUSES`, `_BUG_TERMINAL_STATUSES`, `_record_text`, and
  `_diagnosis_gaps`, and re-enters `REVIEWED → DIAGNOSING` on a failed fix. These
  names come from a prior exploration pass and are **not re-verified at authoring
  time** — slice 105-01's DoR must confirm them against the live source before
  implementation (grounding-by-probe, ADR-0020).

## Decomposition

Single vertical slice: the state, the counter, the freeze/release, and the
attest-only ingest are one coherent lifecycle change — splitting them would leave
intermediate horizontal states (a counter with no terminal, or a terminal with no
release rule). SPIDR axis: **Rules** (a new lifecycle rule + state) with a thin
**Data** addition (`attempts:` frontmatter, frozen-evidence snapshot).

## Slices

- [105-01 — quarantine state, attempts counter, and attest-only ingest](slice-01-quarantine-state-and-attempts.md)
