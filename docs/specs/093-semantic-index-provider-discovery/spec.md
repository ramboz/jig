---
status: DRAFT
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 093: Semantic-index provider discovery

> Reserved on 2026-07-15 via `workflow.py new`. Body to be drafted in a feature branch.

## Overview

Fix the provider-selection mismatch in spec 080. The public registry lists
multiple supported providers, but an unconfigured project always selects
`tokensave`; when it is absent jig never probes another installed public
provider. Missing-provider outcomes are telemetry-only, so users receive no
actionable path. Make implicit selection capability-based while preserving
explicit provider choices and the Scout internal-overlay boundary.

## Assumptions

- `shutil.which` is an adequate bounded readiness probe for provider discovery;
  provider-specific health remains the existing status/attach contract.

## Decomposition

SPIDR rules/path split: one vertical slice changes default selection, adapter
messaging, state interpretation, telemetry, and tests together. No provider is
installed or downloaded by jig.

## Slices

- [093-01 — discover installed providers and explain absence](slice-01-discover-installed-providers-and-explain-absence.md)
