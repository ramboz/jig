---
status: DONE
skill: spec-workflow
tier: (none — dev infrastructure)
---

# Spec 063: Scaffold-precondition gate (spec creation)

## Overview

A user skipped `/jig:scaffold-init`, asked the agent to start on their
first idea directly, and ended up with an ad-hoc `slices/` folder and
loose slice files — not jig's `docs/specs/NNN-slug/` structure. They
never got the scaffold (conventions, templates, hooks, status board,
seed reference spec), and they now have a non-jig layout that needs
migrating before any of the workflow machinery applies.

The entry point to spec work is `workflow.py new` (the `spec-workflow`
skill's reserve step). Today it has a **weak, dead-end precondition**:

```python
# skills/spec-workflow/workflow.py — reserve_spec()
specs_dir = project_dir / "docs" / "specs"
if not specs_dir.is_dir():
    raise WorkflowError(
        f"refusing: docs/specs/ not found under {project_dir} "
        f"(not inside a scaffolded jig project)"
    )
```

Two gaps let the reported failure through:

1. **It's a dead-end refusal, not a route.** When it fires it tells the
   user they're wrong but doesn't point them at `/jig:scaffold-init`
   (greenfield) or `/jig:migrate` (existing spec/`slices/` layout). The
   user is stuck, and an agent will tend to improvise structure rather
   than route — which is exactly how the loose `slices/` folder appeared.
2. **`docs/specs/`-presence is a weak proxy for "scaffolded."** It can't
   distinguish the three states that need *different* routing:
   *scaffolded* (proceed), *adoptable-but-unscaffolded* (→ migrate),
   *greenfield* (→ scaffold-init). jig already has a real completion
   sentinel — `scaffold.json` — and a real adoptability heuristic, but
   `new` consults neither.

Critically, the reported incident happened **without `workflow.py new`
being invoked at all** — the auto-triggered `spec-workflow` skill let
the orchestrator improvise a folder. So the Python teeth alone don't
close it: the skill's judgment layer needs a "Step 0: is this project
scaffolded?" precondition that routes before any structure is created.

This spec hardens the **spec-creation entry point only** (`new`), at
both layers:

- the deterministic `workflow.py new` precondition → a **three-way,
  `scaffold.json`-first scaffold-state classification** that **routes**
  to the right skill instead of dead-ending; and
- the `spec-workflow` SKILL.md **Step 0 precondition** so the
  auto-fired skill verifies scaffold state before improvising.

Scoped to `new` per direction — `transition`, `status-board`, and the
other subcommands are explicitly out of scope (they only make sense once
specs exist and degrade naturally).

## Why now

- **Observed failure, not hypothetical.** A real user produced a non-jig
  `slices/` layout by skipping scaffold. The dead-end refusal + the
  improvise-friendly auto-trigger path are the root cause.
- **The primitives already exist** — `scaffold.json` (completion
  sentinel, written last per spec 032-02), scaffold-init's
  `_looks_already_spec_driven()` / `_is_jig_partial_state()`, and
  migrate's `compute_verdict()`. We're wiring existing detection into the
  one place that currently improvises, not inventing detection.
- **Cheap, high-leverage, single chokepoint.** `new` is *the* door into
  spec work. One routing precondition there catches the failure for a
  small change.

## Goals

1. **Three-way scaffold-state classification, `scaffold.json`-first.**
   A shared helper classifies a project directory as exactly one of
   `scaffolded` / `adoptable` / `greenfield`:
   - `scaffolded` — `scaffold.json` present (the completion sentinel;
     covers both `in-repo` and `--plugin-only` modes, and
     migrate-copied projects which also carry a manifest).
   - `adoptable` — no `scaffold.json` but the project looks spec-driven
     (the existing ≥3-of-4-triggers heuristic: spec/slice dir +
     decision/adr dir + workflow.md + architecture.md).
   - `greenfield` — neither.
   The interrupted-scaffold case (jig CLAUDE.md watermark, no
   `scaffold.json` — `_is_jig_partial_state`) classifies as `greenfield`
   so the user is routed to re-run scaffold-init (recovery), not migrate.
2. **`workflow.py new` routes instead of dead-ending.** On `adoptable`,
   refuse with a message naming `/jig:migrate`; on `greenfield`, refuse
   naming `/jig:scaffold-init`. The message states *which* state was
   detected and the exact next command. `scaffolded` proceeds to the
   existing reserve flow unchanged.
3. **No new friction for scaffolded projects.** A `scaffold.json`-bearing
   project hits the exact same reserve path it does today (the
   classification is the only added step, and it short-circuits on
   `scaffolded`). All existing `new` tests stay green.
4. **SKILL.md Step 0 precondition (the layer that catches the no-helper
   path).** `spec-workflow` SKILL.md gains an explicit first step:
   before reserving or drafting *any* structure, confirm scaffold state;
   if not `scaffolded`, route to `/jig:scaffold-init` or `/jig:migrate`
   rather than improvising directories. This is what stops an
   auto-triggered run from hand-rolling a `slices/` folder.
5. **Reuse existing detection (rule-of-three).** The trigger-counting
   predicate is shared via `skills/_common/`, not copied a third time
   alongside scaffold-init and migrate. The classifier composes the
   `scaffold.json` check + the shared predicate.
6. **Route-don't-block doctrine (ADR-0011 / ADR-0013).** The precondition
   is a deliberateness gate that *redirects*, consistent with the
   spec-gate and security-floor models — not a hard human-only firewall,
   and it never runs scaffold-init / migrate on the user's behalf. A
   bypass escape hatch (see open questions) preserves the
   deliberate-out-of-band path.

## Non-goals

- **Gating any subcommand other than `new`.** `transition`,
  `status-board`, `session-plan`, `stale`, etc. are out of scope. They
  presuppose specs already exist and fail/no-op naturally; adding a
  precondition there is friction for no observed gain.
- **Gating `adr.py new`.** The ADR reservation door has the same shape
  and would benefit from the same treatment, but this spec is scoped to
  spec creation per direction. Noted as a future follow-on, not built.
- **Unifying scaffold-init's `_looks_already_spec_driven()` and
  migrate's `compute_verdict()`.** Those two have *deliberately
  different* semantics (scaffold-init treats empty spec/slice dirs as
  triggers because it must err toward routing-to-migrate before it
  pollutes the tree; migrate counts only dirs with content). This spec
  extracts only the shared trigger predicate it needs and does **not**
  retrofit/rewrite those two tuned call sites — that's a separate
  refactor with its own behavior-change risk.
- **A new ADR.** This applies existing ADR-0011 / ADR-0013 doctrine
  (deliberateness gate, defense-in-depth, real enforcement is
  out-of-band); it does not introduce a new policy worth its own record.
- **Hard / human-only enforcement.** Impossible in-process per ADR-0011;
  the bypass env var is satisfiable by the agent. The gate's value is
  *correct routing on the common accidental path*, not prevention.
- **Auto-running scaffold-init or migrate.** The precondition routes and
  instructs; the user / orchestrator chooses to act (ADR-0011).

## Resolved decisions

_(Were open questions; resolved 2026-06-08 before 063-01.)_

- **Bypass escape hatch → YES.** `new` honors `JIG_SCAFFOLD_PRECONDITION=0`
  (also `false`/`off`/`no`), mirroring `JIG_REVIEW_EVIDENCE_GATE` /
  `JIG_CONVENTIONS_APPROVED`. Chosen for doctrine consistency (ADR-0011 —
  a soft deliberateness gate, not human-only) and to keep a deliberate
  out-of-band path. AC6 of 063-01 stands.
- **Definition of "scaffolded" → `scaffold.json` only.** It is *the*
  completion sentinel (written last per spec 032-02); a jig CLAUDE.md
  watermark without it is the interrupted-scaffold case, which classifies
  as `greenfield` so the user is routed to scaffold-init recovery (not
  migrate). Encoded in AC1.
- **Shared-helper home + name → `skills/_common/scaffold_state.py`** with
  `classify_scaffold_state(project_dir) -> Literal["scaffolded",
  "adoptable", "greenfield"]`, exposing the shared ≥3-of-4 trigger
  predicate the classifier consumes (and the two existing call sites
  *may* later adopt — out of scope here per non-goals).

## Decomposition

SPIDR **Interface-axis** split: the same precondition reached through two
different interfaces — the deterministic `workflow.py new` CLI, and the
auto-triggered skill's judgment layer. Each slice is vertical and
delivers end-to-end value on its own; 063-02 depends on 063-01 so the
prose points at the now-routing command rather than duplicating logic in
prose.

### Slices

- [063-01 — classify-and-route-on-new](slice-01-classify-and-route-on-new.md) — DRAFT
- [063-02 — skill-step0-precondition](slice-02-skill-step0-precondition.md) — DRAFT

## References

- **Originating conversation:** 2026-06-05 — user reported a colleague
  skipping scaffold-init and producing a loose `slices/` folder instead
  of jig structure.
- **Existing detection reused:** `scaffold.py` `_looks_already_spec_driven`
  / `_is_jig_partial_state` (skills/scaffold-init/scaffold.py:236,217);
  `migrate.py` `compute_verdict` (skills/migrate/migrate.py:199);
  `scaffold.json` completion sentinel (spec 032-02).
- **Current weak precondition:** `workflow.py` `reserve_spec`
  (skills/spec-workflow/workflow.py:2388).
- **Doctrine:** [ADR-0011](../../docs/decisions/adr-0011-spec-gate-model.md)
  (deliberateness gate, not human-only) and
  [ADR-0013](../../docs/decisions/adr-0013-security-floor-policy.md)
  (defense-in-depth; real enforcement out-of-band). The route-don't-block
  precondition is the same shape: jig redirects, the user/agent acts.
- **Rule-of-three:** [ADR-0002] — the shared trigger predicate becomes
  the third consumer's extract trigger; the two tuned call sites are
  *not* retrofitted (see non-goals).
- **Adjacent:** Spec 008-05 (scaffold-init's own "looks already
  spec-driven → route to migrate" refusal) — this spec gives the
  *reverse* door (spec-workflow → scaffold-init/migrate) the same
  routing courtesy.

## Amendments

> Post-DONE corrections per [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md).
> The original spec above is preserved; dated entries below record reality.

### 2026-06-09 — jig itself self-classified `adoptable` (regression) → jig now carries a `scaffold.json`

Immediately after this spec landed, dogfooding surfaced a regression the
review passes missed: **the jig repo itself had no root `scaffold.json`**, so
`classify_scaffold_state(jig)` returned `adoptable` and `workflow.py new`
**refused inside the jig repo**, mis-routing jig to `/jig:migrate` — breaking
jig's own spec reservation. Every 063 test fixture had been given a
`scaffold.json`, and none asserted that the *real* jig repo can still reserve a
spec, so the gap shipped clean.

**Fix (no classifier code change):** jig now carries a real root
`scaffold.json` — dogfooding the completion sentinel it asks every jig project
to have (jig is the plugin *source*; the `note` field records that it was not
produced by scaffold-init). A new `JigSelfHostDogfoodTests` in
`skills/_common/test_scaffold_state.py` pins the invariant (jig root has a
`scaffold.json` **and** classifies `scaffolded`) so the regression cannot
recur. The classifier's `scaffolded ⟺ scaffold.json` rule is unchanged; the
alternative (special-casing the plugin source in the classifier) was rejected
in favor of jig conforming to the sentinel like any jig project.
