---
status: IN_PROGRESS
skill: jig:bug-fix
---

# Spec 058: Bug-fix workflow

> Implements [ADR-0016](../../decisions/adr-0016-bug-fix-lifecycle.md):
> a parallel, proportional, teeth-gated bug-fix lifecycle distinct from
> the spec-driven (SDD) lifecycle, for bug-shaped work that needs rigor
> without spec ceremony.

## Overview

jig has a heavyweight spec lifecycle on one side and "just commit it" on
the other, with nothing proportional in between for the most common kind
of work: fixing a reported bug. `spec-workflow` even routes bug-shaped
work away to a `debug-workflow` skill that **does not exist** in the
pack (only as some users' personal, judgment-only, ephemeral global
skill).

This spec adds **`jig:bug-fix`** — a first-class workflow (peer to
`spec-workflow`, owns its orchestration) backed by a `bug.py` helper
(sibling of `workflow.py`, sharing `_common/`). It delivers:

- a bug-shaped lifecycle `REPORTED → DIAGNOSING → ROOT_CAUSED → FIXING →
  REVIEWED → (VERIFIED) → DONE`, plus an `ESCALATED` off-ramp;
- **teeth gates** — a diagnose-before-fix gate (≥2 hypotheses) and a
  **red→green** gate that shells to `tdd.py` to *witness* the regression
  test fail before the fix and pass after (machine-attested, not
  claimed);
- **proportionality enforced downward** — `triage` bows out of trivial
  bugs ("just `tdd-loop` + commit"), reserving the record + gates for
  standard/gnarly tiers;
- a durable one-file record `docs/bugs/NNN-slug.md` and its own board
  `docs/bugs/README.md`;
- a bug-tailored review pass reusing the ADR-0014 evidence gate, plus the
  reused craft (`pr-review`) and conditional security (`security-review`)
  passes, run by reviewer subagents through the host/orchestrator while
  `bug.py` validates their recorded verdict artifacts.

See ADR-0016 for the full decision (gate table, record schema, reuse
map, deferral note).

## Priority trigger

**Trigger met on 2026-06-20.** A retrospective pass over prior specs found
at least six strong cases that would have been better represented as
bug-fix records than full specs if `jig:bug-fix` had existed:

- [019 — land deviation-log tolerance](../019-land-deviation-log-tolerance/spec.md)
- [035 — fixture exclusion](../035-fixture-exclusion/spec.md)
- [037 — git origin safety](../037-git-origin-safety/spec.md)
- [039 — review queue cleanup](../039-review-queue-cleanup/spec.md)
- [040 — isolation honesty](../040-isolation-honesty/spec.md)
- [075 — spec-lint shipped reference leak](../075-spec-lint-shipped-reference-leak/spec.md)

Probable-but-escalation-shaped examples include [063](../063-scaffold-precondition-gate/spec.md),
[066](../066-adr-scaffold-precondition-gate/spec.md), and
[081](../081-main-worktree-sync-on-landing/spec.md): each starts from a
bug-shaped invariant failure but may still escalate when the fix introduces
new routing or landing semantics.

This is enough evidence to prioritize spec 058 as actionable workflow debt:
the missing middle path is no longer hypothetical, and the expected payoff is
reduced spec ceremony for observed defect-shaped work.

## Decomposition

**SPIDR analysis:**

- **Spike** — none. The design is settled in ADR-0016; the one unknown
  (does `tdd.py` support targeted single-test runs?) is resolved as a
  concrete prerequisite slice (058-01), not a timeboxed spike.
- **Paths** — the lifecycle is a path through states. The vertical cut
  is by *capability* (numbering+record, then gates, then review, then
  escalation+close), each observable end-to-end via the CLI.
- **Interfaces** — `bug.py` subcommands (`new` / `triage` / `transition`
  / `escalate` / `status-board` / `--release`) and the `jig:bug-fix`
  skill are the external surfaces. `tdd.py` gains a targeted-test
  interface (058-01).
- **Data** — the record frontmatter schema (`status` / `severity` /
  `tier` / `claimed_by` / `regression_test` / `red_confirmed_at` /
  `green_confirmed_at` / `fix_class` / `security_surface` /
  `escalated_to`) and the board.
- **Rules** — the gate predicates (diagnose ≥2 hypotheses; red→green via
  `tdd.py`; review-evidence at REVIEWED; learning at DONE), tier-driven
  strictness, and the deliberateness bypass env vars.

**Slicing rationale.** Each slice lands end-to-end observable value:
058-01 makes targeted test runs work (usable on its own); 058-02 lets you
*create and triage* a bug; 058-03 adds the gated lifecycle; 058-04 adds
review; 058-05 adds escalation + close; 058-06 ships the skill + routing
docs. 058-03 depends on 058-01 (the teeth shell out to it) and 058-02
(the record to gate).

## Slices

- [058-01 — `tdd.py` targeted-test support](slice-01-tdd-targeted-test.md)
- [058-02 — `bug.py` core: new / triage / numbering / board / claim](slice-02-bug-core.md)
- [058-03 — gated transitions: diagnose gate + red→green teeth + fix_class](slice-03-gated-transitions.md)
- [058-04 — review integration: bug-review + craft + conditional security](slice-04-review-integration.md)
- [058-05 — escalation seam + close/learning gate + origin/main reservation](slice-05-escalation-close.md)
- [058-06 — `jig:bug-fix` skill + plugin wiring + workflow.md routing](slice-06-skill-and-docs.md)
