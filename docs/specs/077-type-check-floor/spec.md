---
status: DONE
skill: code-health
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 077: Type-check floor for code-health

> Source: EngTips self-audit brief-02, folded into this spec and retired
> (EngTip #3 "Tighten Contracts on Nullable Values", #11 "Tests and
> Contracts"). Reserved 2026-06-19 via `workflow.py new`.

## Overview

EngTip #3 argues for making contracts *statically enforceable* rather
than relying on authors being "careful enough." jig's whole thesis is
contract-tightening, yet jig's own helpers have **no type-checker** in
the loop: `ruff.toml` selects `F,E,W,I,B` (lint + import hygiene, no type
analysis) and there is no mypy/pyright in CI. The helpers in
`skills/_common/` and the per-skill `*.py` use type hints inconsistently,
and nothing checks them — a function that starts returning `None` on a
new path has nothing flagging unguarded callers.

`code-health` already has the exact mechanism: ADR-0017's `AdvisoryProbe`
— a report-but-never-gate signal (already used for complexity and
prettier). A type-checker fits that slot.

**End state:** `health.py` runs **pyright** as an `AdvisoryProbe`
(resolved on PATH, else ephemerally via `uvx`/`pipx run`, else "skipped"
— never crashes, never maps the 0/1/2 exit for scaffolded projects); jig's
**own** repo holds itself to the stricter bar (the probe gates jig's CI),
with its helpers brought to a passing typed baseline.

## Assumptions

- **pyright runs ephemerally without a project install** (`uvx pyright` /
  `pipx run pyright`) on jig's stdlib-only helpers. *Probe-back in slice
  01* before relying on it — mirror the existing ruff resolver chain and
  degrade to "skipped (no type-checker)" if not.
- **A small ignore/baseline set will be needed** for jig's deliberate
  `sys.path.insert`-before-import pattern (already `E402`-ignored in
  ruff). Captured explicitly in slice 02, not assumed away.

## Clarifications

- **Gating model + checker (resolved 2026-06-19):** advisory probe,
  **pyright**. Report-only `AdvisoryProbe` for scaffolded projects; jig's
  **own** repo gates on it.
- **Strictness (guidance):** start permissive (catch obvious null/attr
  paths); strict mode is a later dial, not v1.
- **Node/tsc (out of scope):** Python only; the `ECOSYSTEMS` table
  extension point for a future tsc probe is documented, not built.

## Decomposition

SPIDR — primarily a **Rules** split (what the floor checks and where it
gates), with an **Interface** seam (the `health.py` probe surface).

- **077-01 (the probe):** add pyright as an `AdvisoryProbe` in `health.py`
  — resolver chain, summarizer, "skipped" degrade — reported, never
  gating. Self-contained, ships value to any scaffolded Python project.
- **077-02 (jig's own baseline):** run the probe over jig's helpers, add
  missing hints, fix real findings, and wire the check into
  `run_tests.py` / the local CI gate so jig holds itself to the gating
  bar. This is the EngTip #3 payoff and the unknown-sized work.

## Slices

- [077-01 — pyright advisory probe](slice-01-pyright-probe.md)
- [077-02 — jig self typed baseline](slice-02-self-baseline.md)
