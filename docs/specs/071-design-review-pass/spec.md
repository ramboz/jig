---
status: IN_PROGRESS
skill: spec-workflow
---

# Spec 071: Design-review pass (attest-only EDD eval gate)

> Extends [ADR-0014](../../decisions/adr-0014-review-evidence-model.md) (a new
> gated review pass) and resolves [ADR-0022](../../decisions/adr-0022-pluggable-oracle-boundary.md)
> OQ2 (how thin is attest-only for the eval oracle). First concrete consumer:
> food-log's servo design-fidelity eval (slice 002-01).

## Overview

jig's review passes (`compliance`, `craft`, `arch`, `code-health`,
`reconciliation`, `frame-critique`) all attest *jig-internal* judgments. None
attests a **non-deterministic external eval** — e.g. servo's design-fidelity
oracle, which scores "does the built UI match the design mockup?" with a frozen
vision judge whose score wobbles run-to-run. ADR-0019/0022 fixed jig's posture
as **attest-only**: jig records that an eval ran and met its bar; it never
re-derives the score (servo runs and scores; jig attests; the honesty boundary
holds — `env_error ≠ pass`).

This spec adds a `design_review`-gated review pass — the REVIEWED-stage sibling
of `arch_review` / `code_health_review` — whose reviewer reads the external
eval's frozen verdict (e.g. servo's `.servo/design-eval/` ledger + threshold)
and attests pass/fail **without re-running the judge**. It is the thin, generic
integration point ADR-0022 OQ2 asked for: the eval verdict rides the existing
ADR-0014 review-evidence rails (a standard `reviews/slice-NN-design-review.md`
verdict file) — no bespoke servo interface, schema-only, attest-only.

**Out of scope (deferred to the ADR-0022 signal):** a tight machine interface to
servo's `.servo/install.json` (auto-discovery, composite re-read, threshold
sync). ADR-0019's revisit trigger stands — "≥2 eval-oracle refactors where the
attest-only posture proves too loose." This slice ships the loose, generic pass.

## Slices

| Slice | Title | Status |
|---|---|---|
| [071-01](slice-01-design-review-pass.md) | design-review pass + REVIEWED gate | IN_PROGRESS |
