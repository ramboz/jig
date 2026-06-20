---
status: DONE
skill:
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 073: ADR status in frontmatter

> Implements [ADR-0026](../../decisions/adr-0026-adr-status-frontmatter.md)
> (Accepted 2026-06-15). Reserved 2026-06-15 via `workflow.py new`.

## Overview

[ADR-0026](../../decisions/adr-0026-adr-status-frontmatter.md) makes
**frontmatter the canonical home for ADR status**. Today an ADR's lifecycle
state (Proposed / Accepted / Superseded) lives only in the prose `## Status`
section: `_lookup_adr_accepted` (the `adr-NNNN` dependency reader in
`workflow.py`) scrapes it for an `^Accepted` line, while the slice reader
`_lookup_slice_status` reads frontmatter first. This spec closes that
asymmetry and fixes the consequent bug — a dependency on a *superseded* ADR
is currently treated as satisfied, because `supersede` leaves the
`Accepted (date)` prose line in place and the reader only matches `^Accepted`.

**End state:** `adr.py` stamps a `status:` frontmatter field in lockstep with
the prose; `_lookup_adr_accepted` reads frontmatter first and falls back to
prose for legacy ADRs; `Superseded` is not `Accepted` for dependency
resolution.

Two ADR rulings are load-bearing here:

- **Frontmatter-first, prose fallback** — legacy ADRs (no `status:` field)
  grandfather through the existing prose scan; no backfill (ADR-0026 Open
  question).
- **Synchronized atomic write** — the prose `## Status` must remain (Nygard
  convention, human-readable dates, the `Superseded by` links `adr.py
  supersede` parses), so the frontmatter field is a *mirror*; the writer
  updates both in one write, locked by a regression test.

All load-bearing factual claims behind this work were **probe-verified during
ADR-0026** (which itself passed an adversarial frame-critique —
[evidence](../../decisions/reviews/adr-0026-frame-critique.md)), so no slice
here surfaces a *new* unverified assumption.

## Assumptions

None.

## Decomposition

SPIDR — primarily a **Rules** split (the status-resolution rule), separated
by the two sides of the read/write contract. Each side delivers independent
end-to-end value, so this is a vertical split, not horizontal phasing:

- **073-01 (read side):** make the consumer (`_lookup_adr_accepted`) honor
  frontmatter status and recognize `Superseded`. Delivers immediate value on
  the *existing* prose-only corpus — a dependency on a superseded ADR now
  correctly fails — and readies the reader for the frontmatter field. (The
  frontmatter-first branch is exercised by fixtures here and activated for
  real ADRs by 073-02.)
- **073-02 (write side):** make the producer (`adr.py` new / accept /
  supersede) stamp the canonical `status:` field in sync with prose, and add
  it to the ADR template. Delivers: new ADRs carry frontmatter status that
  073-01's reader honors.

Not a Spike — the design is settled by ADR-0026. Not Path / Interface /
Data-subset — the natural seam is the read/write contract.

## Slices

- [073-01 — reader honors frontmatter status](slice-01-reader-frontmatter-status.md)
- [073-02 — writer stamps frontmatter status](slice-02-writer-stamps-status.md)
