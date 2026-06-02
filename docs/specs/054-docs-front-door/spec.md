---
status: DONE
skill: scaffold-init, spec-workflow, slice-land
tier: product/docs
adr_required: false
---

# Spec 054: Docs front door

## Overview

[Spec 048](../048-guidelines-gap-response/spec.md) answered the 2026-05/06
Mysticat comparison by making jig's public docs *current and honest* — it
refreshed the README status, added an adoption-readiness guide, exposed a
gap-response map, and seeded a cold-start reference spec. It deliberately did
**not** touch the axis a later reader review surfaced: **the craft and
leanness of the front door.** Spec 048's own Non-goals ("keep the machine
tight", "no broad organizational handbook") framed its README work as
*honesty*, not *readability*.

A 2026-06-01 user review found the public entry points still read as noisy
and hard to enter, even after 048:

- **The README carries internal build-state on the public front page** — a
  ~10-row gap-response triage plus per-slice spec references. Ironically that
  table was *added* by slice 048-01 (its plan default was
  "discoverability over leanness") and is pinned by
  `scripts/test_readme_status_current.py`.
- **The "why" is well-argued but dense** — a wall of cited bullets, not
  skimmable theses. The deeper why (`product-vision.md`) is strong but long
  and internal-flavored (positioning-audit history, spec cross-refs).
- **Getting started is split** across an unreconciled "Installation" thicket
  (four install shapes) and a separate five-line "Getting started"; the
  genuinely useful `docs/adoption-readiness.md` (slice 048-02) is buried
  behind a blockquote.
- **There are no copy-paste reference prompts** — neither for scaffolding nor
  for driving a spec end-to-end. This is the single biggest first-use gap,
  and one neither jig nor Mysticat currently fills.

This spec restructures the front door for that new reader: a lean
routing-hub README, a clean external "why," a prompt cookbook, and one
coherent getting-started path. The footprint is presentation only — leanness
plus two new docs and one retargeted test. It adds no
organizational-handbook surface (product-vision's standing non-goal).

## Goals

1. **README is a routing hub, not an encyclopedia.** A first-time reader can
   tell what jig is, why it exists, and where to go next within one screen —
   without wading through internal triage or install-shape caveats.
2. **The "why" is skimmable and lives in one place.** A short
   `docs/philosophy.md` carries the external why (one-line theses, named
   failure modes, objection-handling). `product-vision.md` stays the deep
   internal doc and is not replaced.
3. **Copy-paste prompts exist for the two core journeys** — scaffolding a
   project, and drafting + implementing a spec end-to-end.
4. **There is one obvious getting-started path.** The reader is never unsure
   what to read next; `adoption-readiness.md` is surfaced, not buried.
5. **Internal build-state moves off the public front page.** The
   gap-response map and dogfood ledger live where contributors look
   (`CONTRIBUTING.md`), with regression coverage retargeted accordingly and
   the stale-status guard preserved.

## Non-goals

- **No new positioning or product decisions.** This is a presentation
  restructure of existing, accurate content — not a re-pitch. Where 054
  reverses a 048-01 choice it is the *placement* of the gap map, not its
  content.
- **No organizational handbook.** No MkDocs site, leadership/leveling
  curriculum, or operating-mode/substrate framing — out of scope per
  product-vision and routed elsewhere by spec 048's gap inventory.
- **No content gaps from 048's inventory C.** Security floor (052), AI-usage
  PR disclosure, model-routing playbook, config-evolution, etc. keep their
  existing owners; 054 does not absorb them.
- **No trimming of `product-vision.md` depth.** philosophy.md links to it; it
  is not replaced or stripped of its internal history.
- **No change to skill/hook behavior.** Docs plus one retargeted test only.

## Current state (verified 2026-06-01)

- `README.md` is ~240 lines; its `## Status & roadmap` section (slice
  048-01) carries a 9–10 row gap-response map + per-slice spec references,
  pinned by `scripts/test_readme_status_current.py` (asserts the table lives
  in README, ≥8 rows, owner-spec links, routed-inventory link).
- `docs/adoption-readiness.md` (slice 048-02) already contains a
  "who's it for / your first 30 minutes" path, linked only from a blockquote
  inside README's Installation section.
- `docs/product-vision.md` is the why today (~13KB; includes the 2026-05
  positioning-audit history and spec cross-refs).
- No `docs/philosophy.md` and no prompt cookbook exist.
- Spec 048 is DONE; its Non-goals explicitly de-scoped handbook depth and
  framed README work as honesty, not leanness.

## Decomposition

**SPIDR axis: Interface.** The slices split by reader surface — the why doc,
the prompt cookbook, the README hub, and the cross-doc path — each delivering
standalone value to a new reader. Ordered **content-first** so the README hub
links only to docs that already exist, avoiding the forward-broken-link
hazard slice 048-01 flagged.

### Slices

1. **054-01 philosophy-doc** — New `docs/philosophy.md`: the lean external
   why. Skimmable bolded theses, named failure modes, and an
   objection-handling Q&A. Self-contained; links to `product-vision.md` for
   depth.
2. **054-02 prompt-cookbook** — New `docs/prompts.md`: copy-paste reference
   prompts for (a) scaffolding a new project and (b) driving a spec
   end-to-end (draft → SPIDR-split → implement → review → reconcile → land).
3. **054-03 readme-routing-hub** — Slim `README.md` to a routing hub: move the
   gap-response map + dogfood ledger to `CONTRIBUTING.md` and retarget
   `test_readme_status_current.py`; tighten "Why jig exists" to a teaser
   linking `philosophy.md`; collapse the two getting-started entry points into
   one "Start here" that links the cookbook + adoption-readiness.
4. **054-04 reading-path-coherence** — Establish one canonical getting-started
   path: surface `adoption-readiness.md` from the front door and add
   consistent "what to read next" links across the entry docs (README →
   philosophy → adoption-readiness → cookbook → workflow.md), with backlinks
   added to adoption-readiness (which predates philosophy.md and the
   cookbook). A link-reachability check pins the path.

## Dependencies / coordination

- **054-03 depends on 054-01 + 054-02** — its outbound links must resolve.
- **054-04 depends on 054-03.**
- **054-03 reverses the placement decision in slice 048-01** (gap map moves
  README → CONTRIBUTING). It must preserve the *content* and keep the
  stale-status guard; only the location and the test target change. 048 stays
  DONE. Per [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md),
  the README is *live operational prose* (corrected inline, git history is the
  audit trail), while slice 048-01 is a *closed record* — so 054-03's
  reconciliation adds a `## Amendments` note to the 048-01 slice recording the
  placement reversal.
- **philosophy.md must not fork product-vision's positioning** — it is a
  distilled, reader-facing view that links back, so the two can't drift into
  conflicting claims. Keep them consistent at reconciliation.
- No `docs/conventions.md` change is anticipated; if a slice needs one, stop
  and get explicit human approval.

## References

- [adobe/mysticat-ai-native-guidelines](https://github.com/adobe/mysticat-ai-native-guidelines)
  — comparison baseline; its `docs/01-foundations/philosophy.md` is the craft
  model for slice 054-01 (the *form*, not the content).
- [Spec 048: Guidelines gap response](../048-guidelines-gap-response/spec.md)
  — the honesty/adoption pass; 054 is its craft/leanness follow-up.
- [README.md](../../../README.md), [CONTRIBUTING.md](../../../CONTRIBUTING.md)
- [docs/product-vision.md](../../product-vision.md),
  [docs/adoption-readiness.md](../../adoption-readiness.md),
  [docs/workflow.md](../../workflow.md)
- [scripts/test_readme_status_current.py](../../../scripts/test_readme_status_current.py)
  — retargeted by slice 054-03.
- [ADR-0010: Amendment scope — records vs. live prose](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md)
  — governs how 054-03 records the 048-01 reversal.
