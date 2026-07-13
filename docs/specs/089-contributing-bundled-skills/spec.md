---
status: DONE
skill: contributor-docs
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 089: Contributing bundled skills

## Overview

Adding a bundled jig skill is intentionally uncommon: jig positions itself as a
lean, opinionated workflow layer, and every bundled skill expands the default
routing and maintenance surface. When the exception is justified, however, the
contributor-facing guide does not explain how to author, register, validate, and
package the skill. The only complete checklist lives in an internal learning,
where it has already drifted from the current primer shape.

Add one canonical contributor-facing runbook that first makes the lean-product
admission decision explicit, then documents the current registration and
verification flow. Keep the historical learning as provenance, but point it at
the live runbook instead of maintaining a second checklist.

## Assumptions

None. The registration surfaces and validation commands are grounded in the
current repository files and CI-equivalent contributor guidance.

## Decomposition

SPIDR axis: **Rules**. The change establishes one contributor-facing rule for
the exceptional bundled-skill path. A single vertical documentation slice
delivers the admission framing, authoring links, registration checklist, and
verification commands together; splitting those would leave contributors with
an incomplete flow.

## Slices

- [089-01 — bundled-skill contributor runbook](slice-01-bundled-skill-runbook.md)
