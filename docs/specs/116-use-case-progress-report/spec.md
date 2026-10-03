---
status: DRAFT
skill: spec-workflow
use_cases: [UC-11, UC-12]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 116: Use-case progress report

> Builds on [ADR-0025](../../decisions/adr-0025-use-cases-breadth-layer.md)
> (Architecture Decision Record) and [spec 068](../068-use-cases-breadth-layer/spec.md).
> **DRAFT.** A read-only `workflow.py progress` query that joins the
> `use_cases:` trace links with slice state and prints **use case → specs → done
> slices**, plus an explicit **Unanchored** bucket for specs that serve no stated
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
   specs citing it and their done/known slice counts; then the specs that cite
   no use case (**Unanchored** — the rabbit-hole signal). Deterministic,
   read-only, always exit 0.
2. **`/jig:orient` surfacing** (slice 02) — the project briefing carries a short
   use-case progress section, so a returning owner sees it without knowing the
   command exists.

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
  done — and how much work serves no stated behavior.
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

> Risk-gated (ADR-0020). Both entries are real and unverified, so they are the
> frame-critique trigger for this spec.

- **Load-bearing (thin evidence):** a done/known slice count per use case is a useful drift signal for the owner — one owner request (2026-10-03), not measured. ADR-0025 §A2 already warns that goal-level use cases can read "complete" while specs still diverge, and a count inherits that: every slice `DONE` does not prove the behavior works end to end. Mitigated by showing counts rather than percentages and by the Unanchored bucket. Kill signal: the report reads all-done while the owner still feels drift, or the owner stops consulting it.
- **Load-bearing (unverified data):** the trace links backfilled on jig's own specs on 2026-10-03 were assigned from each spec's title and first paragraph, not a full read, so some are probably wrong — and the report is only as truthful as the links. Mitigated by the report itself: every spec is listed under the use case it cites, so a mis-mapped spec is visible and is corrected on sight.

## Open questions

- **OQ1 — where the owner ruling is recorded.** It is a choice with rejected
  alternatives that a future agent would otherwise undo by citing the
  out-of-scope line, which is the ADR trigger
  ([ADR-0031](../../decisions/adr-0031-load-bearing-decision-adr-trigger.md),
  routed per [ADR-0042](../../decisions/adr-0042-decision-routing-gate.md)). Recommended:
  an ADR, written before slice 01 starts. The owner may instead route it as a
  lightweight decision. Slice 01's Definition of Ready (DoR) carries it either
  way.

## Decomposition

SPIDR (Spike / Paths / Interfaces / Data / Rules) analysis:

- **Rules** — one counting rule: `DONE` slices over known slices, with the same
  `DEFERRED` / `ABANDONED` exclusions the spec rollup already applies. No
  weighting.
- **Data** — spec-level trace links only; use cases in vision order, flat.
- **Interfaces** — the split axis. Command-line output first (slice 01), then
  the `/jig:orient` briefing (slice 02). No persisted board.
- **Paths** — the adopted-project path and the two not-adopted paths (no vision
  file; vision with no `## Use cases` section) ship together in slice 01: the
  silent no-op is what keeps non-adopting projects unaffected, so it cannot
  trail the happy path.
- **Spike** — none needed; every surface the report reads is already verified
  above.

## Slices

- [116-01 — progress-rollup](slice-01-progress-rollup.md)
- [116-02 — orient-surface](slice-02-orient-surface.md)
