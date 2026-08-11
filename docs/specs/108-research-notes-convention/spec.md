---
status: IN_PROGRESS
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 108: Research-notes convention

> Implements [ADR-0054](../../decisions/adr-0054-research-notes-artifact-convention.md)
> (Accepted 2026-08-11). Closes the standalone-investigation ask in
> [issue #196](https://github.com/ramboz/jig/issues/196).

## Overview

jig has no home for the **open investigation phase** — the stretch *before* a
decision is even named, when you are gathering sources, weighing pros/cons, and
holding open questions on a generic idea not attached to any committed build.
[ADR-0054](../../decisions/adr-0054-research-notes-artifact-convention.md)
decided the answer is a **lightweight, convention-level artifact**, not a
machine: a `docs/research/R-NNN-<slug>.md` note with light frontmatter, a
hand-maintained index, and two documented hand-offs — *not* a `research.py`
helper, index-regen, link-linter, or reservation-style numbering (all
explicitly deferred).

This spec ships that convention. Research notes are **sequential with, not
competing against**, `docs/refinement-todo.md`: a note is the open phase; when
it crystallizes a *named deferred decision + trigger* it **promotes into** a
refinement-todo entry (or an ADR / spec), citing the note. The existing
`docs/research/00`–`09` founding corpus is formally declared **frozen seed
research** and kept in place, unrenamed (ADR-0010 ethos).

**Non-goals** (deferred per ADR-0054 → registered as trigger-gated
`refinement-todo` entries in slice 108-02):
- No `research.py` creation helper, no index regeneration, no link-resolution
  linter, no numbering-collision handling.
- No retro-migration of the existing thick `docs/inbox.md` entries.
- No `scaffold-init` adopter-facing surface (jig-internal convention first).

## Assumptions

None.

_No unverified load-bearing runnable-surface claims beyond ADR-0054's, which were probe-verified (`docs/research/` holds exactly `00-starter-prompt.md` + `01`–`09`, frozen prose, no status frontmatter, confirmed this session); this spec adds documentation + one template file and introduces no code path. Risk-gated per ADR-0020 §1–§2; kept parser-clean so frame-review-needed derives false — the frame was already critiqued at ADR-0054._

## Reconciliation carry-forward

**Carry into 108-01's deviation log verbatim (from the ADR-0054 frame-critique
pass):** the decision to build this convention *now* is justified by the
external ask (#196) + the existing frozen seed corpus + near-zero reversible
cost, and explicitly **not** by demonstrated recurring internal open-phase
demand (which is ≈ n=0–1 and unproven). ADR-0054's distinctness kill criterion
is the tripwire; this spec must not silently manufacture the demand it was meant
to test.

## Decomposition

SPIDR analysis. The work is a small documentation/convention change; the split
is a **Path** split — happy path first (a contributor can capture and register
an open investigation), governance/codification second — with no Spike (the
open questions were settled in ADR-0054).

- **S (Spike):** none — ADR-0054 already framed the decision; no unknown remains.
- **P (Path):** ✅ the split axis. 108-01 = the capture-and-register path (create
  a note from a template, register it in the index, promote it out). 108-02 =
  the codify-and-defer path (enshrine in `conventions.md`, register the deferred
  machinery).
- **I / D / R:** not the dividing axis (single interface — Markdown files under
  `docs/research/`; no data subsets; the only "rules" are the hand-off
  conventions, documented in 108-01 and codified in 108-02).

Each slice is vertical: 108-01 delivers a usable convention on its own (a
contributor can create + register + promote a note without 108-02); 108-02 adds
governance + deferred-machinery registration.

## Slices

- [108-01 — living research-note home: template, index, hand-offs](slice-01-living-research-note-home.md)
- [108-02 — codify in conventions.md + register deferred machinery](slice-02-codify-and-defer.md)
