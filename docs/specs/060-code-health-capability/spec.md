---
status: DONE
skill: code-health
---

# Spec 060: Code-health capability

> Implements [ADR-0017](../../decisions/adr-0017-scaffolded-code-health.md) — code-health as a scaffolded, language-detected capability.

## Overview

jig provisions language-appropriate dev practices for the projects it scaffolds — tests (`tdd-loop`), security (`security-review`), contracts (`contracts`) — but has no equivalent for the **static-analysis** dimension: linting, formatting, complexity, dead-code, duplication. A 2026-06-04 audit confirmed jig's own repo has no automated code-health floor either; its quality rests on manual discipline plus tests.

This spec builds the missing capability as the **fourth member of jig's detect-and-orchestrate family** (per ADR-0017). It is a new skill, `jig:code-health`, backed by a `health.py` helper that is the static-analysis sibling of `tdd.py`:

> **detect the project's ecosystem → orchestrate its blessed tools → normalize to exit codes (0 / 1 / 2) → return a tight summary → degrade gracefully when no tool is installed.**

It imposes no tool by default (Tier 1 — detect-and-drive); a Tier-2 opt-in can scaffold a default config into the target. **jig itself is the first dogfood target.** See ADR-0017 for the decision and the rejected alternatives; this spec turns that decision into vertical slices.

## Goals / Non-goals

**Goals**
- A `jig:code-health` skill + `health.py` that detects ecosystem, drives installed linters / complexity / duplication tools, normalizes results, and degrades gracefully.
- Multi-ecosystem (Python first, then Node and others).
- A distinct code-health reviewer pass (the judgment layer) consuming the runner's summary.
- jig dogfoods it — a Ruff floor on jig's own Python, in CI.
- Tier-2 (opt-in) scaffold-the-floor.

**Non-goals**
- Reimplementing any linter — jig orchestrates, never reimplements (exactly like `tdd-loop`).
- Forcing a tool on a project that hasn't chosen one — Tier 1 degrades to a recommendation.
- Auto-fixing code — the capability reports / gates; `ruff --fix` etc. stay the dev's call.
- Architecture / doc-drift detection (e.g. the "every helper path named in `architecture.md` exists" check — it would have caught this session's drift) — a related but separate deterministic check; **out of scope here** (worth a separate follow-on).

## Decomposition (SPIDR)

No **Spike** — ADR-0017 settled the design. The capability splits cleanly along three axes:

- **Rules** (which check, simplest first): lint (01) → complexity (03) → duplication (04, the ADR's awkward cross-ecosystem case).
- **Data** (which ecosystem, least first): Python first — jig's own language, dogfood-ready (01) → Node and others (03).
- **Interface** (how it's surfaced): skill + `health.py` runner (01) → jig CI gate (02) → reviewer pass (05) → scaffold-the-floor (06).
- **Path**: detect-and-drive (tools present) is the happy path throughout; graceful degradation (no tool installed) is built into each runner slice, not deferred.

Slice 03 bundles a Data-axis step (Node) with a Rules-axis step (complexity); it may split in two when picked up.

## Slices

| Slice | Title | Status | Notes |
|---|---|---|---|
| [060-01](slice-01-python-lint-drive.md) | Python lint, detect-and-drive (`jig:code-health` + `health.py`) | DRAFT | Tier-1 MVP; `arch_review` |
| [060-02](slice-02-dogfood-jig-ci.md) | Dogfood onto jig — CI Ruff floor | DRAFT | proves 01 on jig; closes the audit gap |
| [060-03](slice-03-ecosystems-complexity.md) | Broaden ecosystems (Node+) + complexity dimension | DRAFT | Data + Rules; may split |
| [060-04](slice-04-duplication.md) | Duplication — native-first, `npx jscpd` fallback | DRAFT | resolves ADR-0017 OQ1 |
| [060-05](slice-05-codehealth-reviewer.md) | Distinct code-health reviewer pass | DRAFT | `arch_review`; resolves ADR-0017 OQ4 |
| [060-06](slice-06-scaffold-floor.md) | Tier-2 scaffold-the-floor (opt-in) | DEFERRED | resolves ADR-0017 OQ3 (Tier-2) |

## Open questions

- **Tier placement (ADR-0017 OQ3).** Resolved by construction here: Tier-1 = detect-and-drive + reviewer (slices 01–05); Tier-2 = scaffold-the-floor (slice 06). What exactly `scripts/verify_install.py` / the scaffold contract assert is pinned down in slice 02 (Tier-1 dogfood) and slice 06 (Tier-2).
