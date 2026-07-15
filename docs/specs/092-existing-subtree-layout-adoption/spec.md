---
status: DONE
skill: migrate
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 092: Existing-subtree layout adoption

## Overview

Close the adoption gap explicitly deferred by spec 084 and ADR-0033. jig can
operate with `layout.docs_root`, but an existing track-local corpus has no safe
way to create the sentinel/config that lets `workflow.py transition` discover
its project root. Add a bounded migrate operation that adopts the existing
layout without overwriting its specs, decisions, workflow, or architecture.

## Assumptions

- A track-local project with existing `specs/`, `decisions/`, `workflow.md`,
  and `architecture.md` can truthfully use a plugin-only scaffold manifest;
  the migration must refuse weaker/ambiguous shapes rather than invent files.

## Decomposition

SPIDR path/rules split: one vertical slice makes migration inventory
layout-aware, writes the validated sentinel in dry-run/apply modes, and proves
the downstream transition helper works. No artifact-moving phase is needed.

## Slices

- [092-01 — adopt an existing custom-root corpus](slice-01-adopt-existing-custom-root-corpus.md)
