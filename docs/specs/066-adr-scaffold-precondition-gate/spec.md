---
status: DONE
skill: adr-workflow
---

# Spec 066: Scaffold-precondition gate (ADR creation)

## Overview

The direct sibling of [spec 063](../063-scaffold-precondition-gate/spec.md),
applied to the **ADR-creation** door. Spec 063 hardened spec creation
(`workflow.py new`) so an unscaffolded project is *routed* to setup
(`/jig:scaffold-init` or `/jig:migrate`) instead of dead-ending or
improvising structure. The ADR-creation entry point has the **identical
gap** and was explicitly named as 063's out-of-scope follow-on (063
non-goal: "Gating `adr.py new`").

The deterministic door is `adr.py cmd_new` / the `reserve_adr` flow. Its
current precondition is the same weak, dead-end shape 063 replaced:

```python
# skills/adr-workflow/adr.py — cmd_new()
if not adrs_dir.is_dir():
    raise AdrError(f"decisions directory not found: {adrs_dir}")
```

It refuses when `docs/decisions/` is absent but doesn't route anywhere,
and an auto-triggered `adr-workflow` run can improvise a `docs/decisions/`
skeleton when scaffold was skipped — the ADR-side of the loose-`slices/`
failure 063 documented.

This spec applies 063's settled design to the ADR door at both layers:

- the deterministic `adr.py` reserve path → **reuse** the shared
  `classify_scaffold_state` classifier (shipped by 063-01) to route
  greenfield → `/jig:scaffold-init` and adoptable → `/jig:migrate`,
  with the same `JIG_SCAFFOLD_PRECONDITION` bypass; and
- the `adr-workflow` SKILL.md **Step 0 precondition** so the
  auto-fired skill verifies scaffold state before improvising.

## Why now

- **Symmetry / known gap.** 063 proved the pattern and shipped the
  reusable primitive; the ADR door is the one entry point left with the
  old dead-end behavior. Closing it removes an inconsistency a user would
  hit the moment they reserve an ADR in an unscaffolded project.
- **Zero new design.** Everything was decided in 063 / [ADR-0011](../../docs/decisions/adr-0011-spec-gate-model.md)
  / [ADR-0013](../../docs/decisions/adr-0013-security-floor-policy.md).
  `classify_scaffold_state(project_dir)` is door-agnostic (it classifies a
  project directory, nothing spec-specific), so this is wiring + prose, not
  new detection.
- **Cheap.** One reused classifier call at one chokepoint, plus the
  parallel SKILL.md Step 0.

## Assumptions

None.

_(Grounding, not an open assumption — kept on one line so the 064-04 deriver correctly reads it as non-assumption: 066 rests on the 063-01 `classify_scaffold_state` classifier being reusable for the ADR door, which is **verified by inspection** — it classifies a project directory from the `scaffold.json` sentinel + the shared trigger predicate, nothing spec/ADR-specific (see "Overview"/"Why now"). So there is no **unverified** load-bearing assumption and no open frame to attack; per 064-02 risk-gating that is exactly when `## Assumptions` is `None` and frame-critique does not apply. Contrast 063-01, which introduced the classifier and carried `arch_review`; 066 only consumes it.)_

## Goals

1. **`adr.py` reserve path routes instead of dead-ending.** Replace the
   weak `docs/decisions/`-presence refusal with the three-way
   `classify_scaffold_state` classification: `scaffolded` proceeds to the
   existing reserve/scaffold flow unchanged; `adoptable` refuses naming
   `/jig:migrate`; `greenfield` refuses naming `/jig:scaffold-init`. The
   message states the detected state and the exact next command.
2. **Reuse the shared classifier (no second copy).** Consume
   `_common/scaffold_state.classify_scaffold_state`; do **not** re-implement
   classification or trigger-counting in `adr.py`.
3. **Same bypass, same vocabulary.** Honor `JIG_SCAFFOLD_PRECONDITION`
   (`0`/`false`/`off`/`no`) via the existing `precondition_enabled()` —
   one bypass governs both doors (ADR-0011 deliberateness gate).
4. **No new friction for scaffolded projects.** A `scaffold.json`-bearing
   project (incl. the jig repo itself) reserves an ADR exactly as today;
   all existing `adr.py` reserve tests stay green.
5. **SKILL.md Step 0 precondition.** `adr-workflow` SKILL.md "Author a new
   ADR" gains an explicit first step: confirm scaffold state before
   reserving/drafting; if not scaffolded, route to `/jig:scaffold-init` or
   `/jig:migrate` rather than hand-rolling `docs/decisions/`. It points at
   `adr.py new`'s own routing (066-01) without restating the heuristic.
6. **Route-don't-block doctrine.** Same ADR-0011/0013 deliberateness-gate
   shape as 063 — redirect, never auto-run scaffold-init/migrate.

## Non-goals

- **A new classifier or any change to `_common/scaffold_state.py`.** 066
  consumes the 063-01 helper unchanged. If the classifier needs a change,
  that is a 063-lineage change, not 066.
- **A new ADR or new policy.** Pure application of 063 / ADR-0011 / ADR-0013.
- **Gating any `adr.py` subcommand other than `new`.** `accept`,
  `supersede`, `index`, `resolve-todo` presuppose ADRs exist and degrade
  naturally — out of scope (mirrors 063's `new`-only scope).
- **Re-deriving 063's resolved decisions.** Bypass = yes (same env var);
  "scaffolded" = `scaffold.json` only; classifier home = `_common`. All
  settled in 063; see Resolved decisions.
- **Hard / human-only enforcement.** Impossible in-process (ADR-0011); the
  bypass is satisfiable by the agent. Value is correct routing on the
  common accidental path.

## Resolved decisions

_Inherited verbatim from [spec 063](../063-scaffold-precondition-gate/spec.md#resolved-decisions)
— 066 introduces no new open questions._

- **Bypass → YES**, via the shared `JIG_SCAFFOLD_PRECONDITION`
  (`0`/`false`/`off`/`no`) and `precondition_enabled()`. One env var
  governs both the spec and ADR doors.
- **"Scaffolded" = `scaffold.json` only** (the completion sentinel);
  interrupted-scaffold (watermark, no sentinel) → greenfield. Encoded in
  the shared classifier.
- **Classifier home = `skills/_common/scaffold_state.py`** — exists from
  063-01, consumed here.

## Decomposition

SPIDR **Interface-axis** split (identical shape to 063): the same
precondition reached through two interfaces — the deterministic `adr.py`
reserve CLI, and the auto-triggered skill's judgment layer. 066-02 depends
on 066-01 so the prose points at the now-routing command.

### Slices

- [066-01 — classify-and-route-on-adr-new](slice-01-classify-and-route-on-adr-new.md) — DRAFT
- [066-02 — adr-skill-step0-precondition](slice-02-adr-skill-step0-precondition.md) — DRAFT

## References

- **Parent / settled design:** [spec 063](../063-scaffold-precondition-gate/spec.md)
  (scaffold-precondition gate for spec creation; all 5+2 ACs DONE) — 066
  mirrors its 063-01 (classify-and-route) and 063-02 (SKILL.md Step 0).
- **Reused primitive:** `skills/_common/scaffold_state.py`
  `classify_scaffold_state` / `precondition_enabled` (063-01).
- **Current weak precondition:** `adr.py` `cmd_new`
  (skills/adr-workflow/adr.py:147-148); reserve flow `reserve_adr`
  (slice 028-01).
- **Doctrine:** [ADR-0011](../../docs/decisions/adr-0011-spec-gate-model.md)
  (deliberateness gate) + [ADR-0013](../../docs/decisions/adr-0013-security-floor-policy.md)
  (defense-in-depth; enforcement out-of-band).
- **Origin:** the `adr.py new` follow-on parked in
  [`docs/refinement-todo.md`](../../refinement-todo.md) at 063's
  reconciliation; promoted to this spec.
