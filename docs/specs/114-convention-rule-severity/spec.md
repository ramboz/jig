---
status: DRAFT
skill: independent-review
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 114: Convention-rule severity and promotion

> Implements [ADR-0062](../../decisions/adr-0062-convention-rule-severity-and-promotion.md)
> (Proposed). Investigation record: [R-001](../../research/R-001-cloudflare-adlc-assessment.md).
> **Status: recorded, not yet built** — reserved alongside the ADR so the
> decision has a home for its build; the ADR must be Accepted before 114-01
> moves past DRAFT.

## Overview

Give every rule in `docs/conventions.md` a stable id, a severity (`MUST` /
`SHOULD`), and a promotion state (`advisory` / `enforced`), and make the review
passes consume them: enforced-MUST breaches withhold the review verdict's
`pass`, everything else is reported. New rules start advisory; promotion is a
deliberate, owner-approved edit to the protected file (the spec-gate of
ADR-0011 already makes it so). Findings cite a rule id, which gives
`workflow.py gate-stats` a per-rule fire count — the denominator the deferred
spec 078 entry has been waiting on.

This is a **review-pass change plus a doc-shape change**, not a new gate
(ADR-0055). The design principles in `docs/product-vision.md` are untouched;
`_principles_check_block` stays as it is.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **Probed 2026-09-22:** `docs/conventions.md` is four `##` sections of
  `**Rule:** / **Why:** / **How to apply:**` blocks (~20 rules, no severity
  markers); `review.py` composes reviewer prompts from named blocks with a
  ~500-character per-block hygiene precedent; the review-evidence gate keys on
  `verdict: pass`; `templates/docs/conventions.md.template` mirrors the prose
  shape.
- **Unverified, load-bearing:** a model reviewer reliably cites the *right*
  rule id for a breach when the rules are rendered inline. 114-01 carries a
  fixture that checks this before the telemetry leg is trusted.
- **Owner approval required:** the migration that assigns severity and state
  to existing rules edits `docs/conventions.md`, which is human-approval-only
  (ADR-0011, spec 102). The slice cannot pre-assign them; it renders whatever
  the owner approved.

## Decomposition

Two slices along the **Rules** axis, split simple → edge:

- **114-01** — the tagged rule shape (id / severity / state), the template
  mirror, and the review passes rendering enforced vs advisory rules with
  verdict semantics. End-to-end: a reviewer verdict names the rule it found
  against and withholds `pass` only on an enforced MUST.
- **114-02** — the promotion record and the telemetry leg: a lint that refuses
  an untagged or malformed rule block, the lightweight-decision shape for a
  promotion/demotion, and per-rule fire counts in `gate-stats` beside the
  existing bypass counts.

**Anti-horizontal-phasing.** 114-01 alone changes what a reviewer says and
when a verdict is withheld; 114-02 alone makes promotion auditable and the
keep/retire question answerable from data. Neither is an internal-only layer.

## Slices

- [114-01 — severity-tags-and-review-rendering](slice-01-severity-tags-and-review-rendering.md) — tagged rule blocks + template mirror + review passes render enforced vs advisory with verdict semantics.
- [114-02 — promotion-record-and-rule-telemetry](slice-02-promotion-record-and-rule-telemetry.md) — rule-block lint, promotion/demotion record shape, per-rule fire counts in `gate-stats`.
