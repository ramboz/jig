---
status: DONE
skill: spec-workflow
use_cases: [UC-11, UC-12]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 116: Use-case progress report

> Builds on [ADR-0025](../../decisions/adr-0025-use-cases-breadth-layer.md)
> (Architecture Decision Record) and [spec 068](../068-use-cases-breadth-layer/spec.md).
> A read-only `workflow.py progress` query that joins the
> `use_cases:` trace links with slice state and prints **use case → specs → done
> slices**, plus an explicit **Unanchored** bucket for specs that cite no stated
> use case. Stdout only, advisory, no new artifact; then surfaced in the
> `/jig:orient` briefing.

## Overview

**Problem.** On a project with many specs the owner cannot tell whether work is
still advancing the product's goals. The status board
([docs/specs/README.md](../README.md)) is spec-ordered: it gives each spec's
state, not which intended behavior the spec serves. `workflow.py coverage`
(slice 068-03) answers a yes/no question per use case — is it cited by at least
one spec — and says nothing about how far along it is. The originating report
(owner, 2026-10-03): agents go down rabbit holes in directions the owner is not
fully familiar with, and it is hard to reconcile the corpus and confirm the
project is still progressing toward its goals rather than straying.

**What this spec adds.** The missing join — trace links × slice state:

1. **`workflow.py progress`** (slice 01) — for each use case in the vision, the
   specs citing it with their status and done/known slice counts; then the
   specs that cite no use case (**Unanchored**). Deterministic, read-only,
   always exit 0.
2. **`/jig:orient` surfacing** (slice 02) — a deterministic `progress --summary`
   mode, and a short use-case progress section in the project briefing built
   from it, so a returning owner sees it without knowing the command exists.

**What it is not.** A progress view, not a drift detector
([ADR-0064](../../decisions/adr-0064-use-case-progress-rollup-in-jig.md) bound
5). The trace links are assigned by the agents whose direction is in question,
so an off-goal spec usually appears under some plausible use case rather than
in Unanchored (see Assumptions). What the report does give the owner is every
spec, with its status, under the use case it claims to serve — the place to
audit a claim, not a verdict on it.

**Illustrative output.** Shape only — the slice acceptance criteria are the
contract, and every count below is invented:

```text
# Use-case progress

UC-7   A developer can get an independent review of finished work     31/31 slices done
  004-independent-review-promotion     DONE          3/3
  045-review-lifecycle-gates           DONE          4/4
  ...
UC-20  A developer can hand work to unattended agent loops (servo)    6/9 slices done
  072-servo-pull-hint                  DONE          2/2 (+1 deferred)
  105-durable-failure-quarantine       DRAFT         0/3
  106-autonomy-governance-plane        DONE          4/4
UC-22  A team can run jig's workflow across several repositories      0/2 slices done
  034-federation-tier                  DRAFT         0/2

Unanchored (cites no use case)                                        4/4 slices done
  022-contracts                        DONE          2/2
  032-atomic-writes                    DONE          2/2

Summary: 22 use cases · 113 specs · 2 unanchored · 250/262 slices done (each spec and slice counted once)
```

**Current state (verified 2026-10-03).**

- **The trace spine exists.** The vision's `## Use cases` entries carry stable
  `UC-N` ids, parsed in document order by `parse_use_cases`
  ([skills/_common/use_cases.py](../../../skills/_common/use_cases.py)); each
  spec's `use_cases:` frontmatter is read and resolved by `coverage()` in
  [skills/spec-workflow/workflow.py](../../../skills/spec-workflow/workflow.py).
  Links are **spec-level** — `coverage()` globs `*/spec.md` and reads only that
  file's frontmatter.
- **Slice state per spec is already derivable.** `compute_spec_status` (same
  file) reads every slice's status through `_iter_slices_common` — both the
  file-per-slice layout and legacy embedded `## Slice` sections — and leaves
  `DEFERRED` and `ABANDONED` slices out of the rollup.
- **No `workflow.py` subcommand joins the two.** The subcommand set is closed by
  the argument parser; its usage line lists exactly `transition`,
  `status-board`, `check-board`, `stale`, `routing-stats`, `gate-stats`,
  `orient`, `new`, `arch-review-needed`, `code-health-review-needed`,
  `design-review-needed`, `frame-review-needed`, `session-plan`, `amendments`,
  `coverage`. None renders per-use-case progress.
- **There is a real corpus to run on.** jig's own repo adopted the use-case
  layer on 2026-10-03 (commit `4cdbf6f1`): 22 use cases, `use_cases:` links on
  110 specs. Run that day, `workflow.py coverage` printed `22 use case(s), 112
  spec(s) traced; 0 gap(s) / 2 orphan(s) / 0 dangling`.

**Owner ruling (2026-10-03).** [docs/product-vision.md](../../product-vision.md)
§ "Out of scope (deliberately)" lists a **project management surface** — "No
backlog rendering, no estimation, no roadmap visualization. Specs are the only
project state." The owner ruled this report in scope for jig as a bounded
exception: it is not full project management, and it is the lightweight effort
jig takes on. Two alternatives were rejected: **shaper** as the home (it is
release-scoped, and its vision rules out status boards), and **a new dedicated
project** now (reserved for the day deeper project-management features are
wanted, the way shaper became one). The report keeps "specs are the only project
state" true — it is a derived view that stores nothing.

## Goals / Non-goals

**Goals**

- One command answers: per intended behavior, how much of the known work is
  done — and which specs cite no stated behavior.
- **Derived, not stored.** No new artifact and no new state; the report is
  computed from the vision and the spec records on every run.
- **Advisory** ([ADR-0011](../../decisions/adr-0011-spec-gate-model.md)): never
  gates a transition, never writes.
- **Counts, not percentages.** The denominator is the slices known today, not
  the eventual scope of a use case, so a percentage would overstate progress.

**Non-goals**

- Percentages, weighting, estimation, velocity, burndown, or dates.
- A persisted progress board (no `docs/progress.md`) — a second derived file
  would need its own drift check.
- Slice-level trace links — links stay spec-level (slice 068-02).
- A time-windowed "what moved lately" view.
- Echoing vision sub-groupings (such as `### Upcoming`) as report groups — the
  counts already show what has not started.
- Bugs (`docs/bugs/`) in the rollup — bug records carry no use-case link.
- Any consumption by shaper — that is shaper's own spec if it is ever wanted.
- A general project-management surface — per the owner ruling, a separate
  project.

## Assumptions

> Risk-gated (ADR-0020). Each entry is real and unverified, so together they
> are the frame-critique trigger for this spec.

- **Load-bearing (thin evidence):** a done/known slice count per use case, with each spec listed under the use case it cites, is a useful progress view for the owner — one owner request (2026-10-03), not measured. ADR-0025 §A2 already warns that goal-level use cases can read "complete" while specs still diverge, and a count inherits that: every slice `DONE` does not prove the behavior works end to end. Not mitigated: counts rather than percentages only keep partial progress from looking more precise than it is (`31/31` still reads as complete). Kill signal: the owner stops consulting the report or its orient section. Since orient writes nothing, that is only observable when the owner says so — checkpoint: the owner confirms or rejects the orient section's value at the first `/jig:orient` run after this spec lands.
- **Load-bearing (unverified data):** the trace links backfilled on jig's own specs on 2026-10-03 were assigned from each spec's title and first paragraph, not a full read, so some are probably wrong — and the report is only as truthful as the links. Partly mitigated: the full listing puts every spec under the use case it cites (the owner kept the full tree on 2026-10-03 for this reason), so a mis-mapped spec can be spotted by a reader who knows it. It is not self-correcting.
- **Known limit (false anchoring):** the links are written by the same agents whose direction is in question, against goal-level use cases broad enough to fit almost any work, and spec-workflow step 2a prompts every new spec to cite or add a use case — 110 of 112 specs were anchored on adoption day. So Unanchored mostly holds deliberate declines, and an off-goal spec usually reads as ordinary progress. Hence "a progress view, not a drift detector" (ADR-0064 bound 5). Escalation trigger (not a kill signal — this limit predicts it): a spec the owner later judges off-goal turns out to have been listed as ordinary progress; then build one of the signals the drafting agent does not author, parked in `docs/refinement-todo.md`.

## Open questions

- ~~**OQ1 — where the owner ruling is recorded.**~~ **Resolved 2026-10-03:**
  the owner chose an ADR —
  [ADR-0064](../../decisions/adr-0064-use-case-progress-rollup-in-jig.md),
  which records the ruling, the rejected alternatives (shaper, a new project
  now, `coverage` only), and the bounds of the exception. Slice 01 depends on
  it.

## Decomposition

SPIDR (Spike / Paths / Interfaces / Data / Rules) analysis:

- **Rules** — one counting rule: `DONE` slices over known slices, with the same
  `DEFERRED` / `ABANDONED` exclusions the spec rollup already applies. No
  weighting.
- **Data** — spec-level trace links only; use cases in vision order, flat.
- **Interfaces** — the split axis. Command-line output first (slice 01), then
  a compact `--summary` mode and the `/jig:orient` briefing built from it
  (slice 02). No persisted board.
- **Paths** — the adopted-project path and the two not-adopted paths (no vision
  file; vision with no `## Use cases` section) ship together in slice 01: the
  silent no-op is what keeps non-adopting projects unaffected, so it cannot
  trail the happy path.
- **Spike** — none needed; every surface the report reads is already verified
  above.

## Slices

- [116-01 — progress-rollup](slice-01-progress-rollup.md)
- [116-02 — orient-surface](slice-02-orient-surface.md)
