---
status: DONE
dependencies: [adr-0025, adr-0064, 068-03]
last_verified: 2026-10-03
frame_review: true
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice's fidelity must be a HARD
#                      # gate: extract the mockup's design values (colours,
#                      # spacing, sizes, layout rules) into this slice's ACs,
#                      # then wire a servo `design-eval` as the done-condition
#                      # (attest-only at REVIEWED; ADR-0014, ADR-0022,
#                      # ADR-0049).
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 116-01 — progress-rollup

**Goal:** `workflow.py progress [--project-dir DIR]` prints, for each use case
in the vision, the specs that cite it and how many of their slices are done,
followed by the specs that cite no use case — so the owner sees in one report
how far along each intended behavior's known work is, which specs are still
open under it, and which work cites no behavior at all.

**DoR:**
- ✅ 068-03 DONE — `coverage`, the spec-level `use_cases:` trace links, and
  `parse_use_cases` / `resolve_use_cases` exist
  ([skills/_common/use_cases.py](../../../skills/_common/use_cases.py)).
- ✅ jig's own repo carries a `## Use cases` section and backfilled trace links
  (commit `4cdbf6f1`) — the dogfood corpus.
- ✅ The owner ruling that places this report in jig is recorded as a decision
  record (spec OQ1) —
  [ADR-0064](../../decisions/adr-0064-use-case-progress-rollup-in-jig.md).

**Acceptance Criteria:**

1. **Rollup by use case.** On a project whose vision has a `## Use cases`
   section, the output lists every use case in vision order as its `UC-N` id,
   goal text, and `D/K slices done`; under each, every spec citing it as spec
   directory name, spec status (the `compute_spec_status` value), and `d/k`.
   Observable: a fixture with two use cases and three specs in known slice
   states prints exactly the expected counts.
2. **The counting rule mirrors the spec rollup.** A slice counts toward K unless
   its status is `DEFERRED` or `ABANDONED` — the exclusions `compute_spec_status`
   applies — and toward D only when its status is `DONE`. Deferred slices are
   shown as a separate `(+N deferred)` suffix, never inside K. Slices are read
   in both layouts (file-per-slice and legacy embedded `## Slice` sections).
   Observable: a fixture spec with 2 `DONE` + 1 `DRAFT` + 1 `DEFERRED` + 1
   `ABANDONED` slice prints `2/3 (+1 deferred)`; a legacy-layout fixture spec is
   counted the same way.
3. **Unanchored bucket.** Specs that cite no resolvable use case — an empty or
   absent `use_cases:`, or only ids absent from the vision — are listed under a
   final `Unanchored` heading with the same per-spec line and a bucket total. A
   spec citing an unknown id names that id on its line. Observable: a fixture
   with one orphan spec and one spec citing only `UC-99` shows both there;
   neither is dropped.
4. **A use case with no spec is still listed.** It appears in vision order,
   marked `no spec yet`. Observable on a fixture with one uncited use case.
5. **Multi-cited specs.** A spec citing two use cases appears under both and
   counts toward both use-case totals; the closing summary line counts each spec
   and each slice **once**, and says so. Observable: on a fixture with one
   doubly-cited spec, the summary total is smaller than the sum of the
   per-use-case totals.
6. **Counts, not percentages.** No percentage appears anywhere in the output.
   Observable: no `%` character in the output of any fixture.
7. **Read-only, advisory, silent when not adopted.** `progress` always exits 0
   and writes nothing. With no `product-vision.md` it prints a one-line
   `skipped` note; with a vision that has no `## Use cases` section it prints a
   one-line `no-op` note and **no** rollup — the same two states `coverage`
   has. Observable: both fixtures; a before/after snapshot of the fixture tree
   is identical.
8. **Documented beside its sibling.** The "What this skill does" list in
   [skills/spec-workflow/SKILL.md](../../../skills/spec-workflow/SKILL.md) gains
   a `progress` bullet next to `coverage`, and the host packages are
   regenerated. Observable: `scripts/build_host_packages.py --check` exits 0.
9. **The vision's out-of-scope line is squared with the ruling.** The "Project
   management surface" bullet in [docs/product-vision.md](../../product-vision.md)
   names the read-only use-case progress rollup as the bounded exception. The
   wording is **proposed to the owner and written only after the owner approves
   it**. Observable: the approved wording is in the vision and the approval is
   noted in the deviation log.
10. **The stale "jig's own repo" example is gone from live text.** jig adopted
    the use-case layer on 2026-10-03, so live text may no longer cite jig's own
    repo as an example of a project that has not. Known sites: the `coverage`
    no-op message and docstring in `workflow.py`, the module docstring of
    `use_cases.py`, and the "no-section no-op" paragraph of the spec-workflow
    `SKILL.md`. Closed records (spec 068's slices, ADR-0025) are left as written
    (ADR-0010). Observable: a search of `skills/` for the phrase returns no hit
    that presents jig's own repo as not adopted.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [x] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [x] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** After this slice, the owner runs one command
in jig's own repo and reads progress per use case plus the unanchored bucket —
end to end, on real data.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Pre-implementation frame changes.** All three frame-critiques (ADR-0064,
   116-01, 116-02) returned `needs-changes` in round 1 on one finding: the
   `use_cases:` links are assigned by the agents whose direction is in
   question, so the report cannot be a drift detector. The owner kept the full
   tree for this slice (AC1 unchanged) and the claim was narrowed instead: the
   Goal no longer says "on one screen", the spec carries a "What it is not"
   paragraph and a false-anchoring known limit, ADR-0064 adds bound 5 ("a
   progress view, not a drift detector"), and the agent-independent signals are
   parked in `docs/refinement-todo.md`. Round 2 passed. OQ1 was resolved by the
   owner choosing an ADR; ADR-0064 is Accepted and is a dependency of this
   slice.
2. **AC9 — owner approval.** The owner approved the vision wording verbatim on
   2026-10-03 (offered as a two-option choice; the longer variant was picked).
   The orchestrator wrote it before implementation began. It keeps the approved
   phrase "the specs that serve no use case" even though the spec now says
   "cite" — the approved wording was not re-edited without a new approval.
3. **Shared status reader (beyond the ACs).** `compute_spec_status` was split
   into `_spec_slice_statuses` (read every slice's status, both layouts) and a
   pure `_rollup_status` core, with the `DEFERRED` / `ABANDONED` exclusion held
   in one `_UNCOUNTED_SLICE_STATES` constant. `progress` reads each spec's
   slices once and applies the same exclusion, so AC2's "mirrors the spec
   rollup" is enforced by shared code rather than duplicated literals.
   Behaviour of `compute_spec_status` is unchanged; its existing tests are the
   guard, and every new branch was mutation-checked.
4. **Render-free data core.** `_progress_data` computes the per-use-case rows,
   the Unanchored bucket and the once-counted totals with no rendering, because
   slice 116-02's `--summary` renders the same data. This is a scheduled
   consumer, not a speculative seam (craft review agreed).
5. **Output details the illustrative block left open** (it is shape only):
   use-case header lines read `UC-N  goal  —  D/K slices done` without column
   alignment, while spec rows are padded to the widest name and status; `(s)` plurals in
   the summary, following `coverage`; one advisory header line saying the counts
   are done/known slices and that this is a progress view, not an on-goal check
   (ADR-0064 bound 5); unknown ids rendered as `[cites unknown: UC-99]`; a spec
   citing a valid and an unknown id listed under the valid use case with the
   unknown id named; the Unanchored heading reads `Unanchored (cites no
   resolvable use case)` and shows `none` when empty; a use case whose only
   specs have no slices shows `0/0`, not `no spec yet`.
6. **Reviewer findings folded in (polish round after compliance + craft both
   passed).** From craft: single-sourced exclusion constant, no double slice
   parse, heading wording, tightened orphan-status regex, the AC10 behavioural
   test moved into `CoverageTests` with a narrower assertion, new tests for
   duplicate / case-variant citations, an empty Unanchored bucket and a
   zero-slice spec. From compliance: the two "jig itself" comments in
   `skills/_common/test_use_cases.py` and a stronger AC7 parity test. Each new
   or changed test was mutation-checked.
7. **AC10 scope.** Live text fixed: the `coverage` comment block, docstring and
   no-op message; `use_cases.py` module and `classify_spec` docstrings; the
   spec-workflow `SKILL.md` no-section paragraph; four test sites (the
   `CoverageTests` docstring, the `test_spec_workflow_skill_surface.py` module
   docstring, and two comments in `skills/_common/test_use_cases.py`); and the
   status-board Notes for 068-02 / 068-03 (live curated text, corrected inline
   per ADR-0010). The source-text guard covers `SKILL.md` and `use_cases.py`;
   `workflow.py` is guarded through the runtime message, because the phrase
   legitimately remains there about jig having no `scaffold.json` sentinel.
   Remaining `skills/` hits are all about scaffold sentinels, paths or
   `.gitignore`. Closed records (spec 068's slice files, ADR-0025) left as
   written.
8. **Adjacent finding parked, not fixed.** A scalar `use_cases: UC-1` is read
   as citing nothing by both `coverage` and `progress` (inherited from 068-03);
   parked in `docs/inbox.md`.
9. **Plan adherence.** One subcommand, one flag (`--project-dir`), no JSON
   mode, no config. 18 tests at first delivery plus 4 from the polish round;
   jig's own repo renders 22 use cases, 113 specs, 2 unanchored, 281/300 slices
   done.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | The front door does not list `workflow.py` subcommands (it does not mention `coverage` either); nothing user-facing at that level changed. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` at each transition; `check-board` clean. |
| `docs/product-vision.md` | `updated` | AC9: the "Project management surface" out-of-scope bullet names the bounded exception and links ADR-0064, wording approved by the owner on 2026-10-03. |
| `docs/architecture.md` | `no-op` | Checked line 421 (skill helpers): `workflow.py` and `_common/use_cases.py` are already listed; a new subcommand inside an existing helper changes no module boundary. The CLI-surface decision is recorded in ADR-0064. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | Spec 116 is still in flight (116-02 open), so no Active-specs compression yet. Neither `AGENTS.md` nor `templates/CLAUDE.md.template` mentions `coverage` or `use_cases:`. |
| `docs/inbox.md` | `updated` | Swept: no existing item is resolved by this slice (the 2026-06-10 depth-layer entry is unrelated). Added the scalar `use_cases:` finding from the craft review. |
| `docs/refinement-todo.md` | `updated` | Pre-implementation (spec-review commit `5564906d`): the entry "a progress signal the drafting agent does not author". No decision was deferred during implementation itself. |
| `docs/memory/**` | `updated` | Glossary gains "use-case progress report" (memory-sync). No new learnings worth a `learnings.md` entry. |
| `docs/decisions/README.md` / ADR index | `updated` | Pre-implementation (spec-review commit `5564906d`): ADR-0064's index line, regenerated by `adr.py index` (`check-index` clean). No ADR touched during implementation. |
| Spec-116 frame-review artifacts: `spec.md`, `docs/decisions/adr-0064-use-case-progress-rollup-in-jig.md`, `docs/decisions/reviews/adr-0064-frame-critique.md`, `reviews/slice-01-frame-critique.md`, `reviews/slice-02-frame-critique.md` | `updated` | Pre-implementation (spec-review commit `5564906d`), summarised in deviation item 1. |
| `slice-02-orient-surface.md` frame-review edits | `deferred` | Changed pre-implementation in `5564906d` (deterministic `--summary` mode, 10-entry name-list caps, Goal and anti-horizontal rewrite, orient checkpoint). To be written up in 116-02's own deviation log; trigger: 116-02 reconciliation. |
| `docs/specs/README.md` Notes column | `updated` | 068-02 / 068-03 Notes no longer cite jig's own repo as not adopted (AC10 spirit; live text). |
| Additional live prose / generated templates touched by this slice | `updated` | `skills/spec-workflow/SKILL.md` (`progress` bullet + AC10), `skills/_common/use_cases.py` docstrings, and the regenerated `hosts/{claude,codex,copilot}` mirrors (`build_host_packages.py --check` exit 0). |

## Amendments

- **2026-10-03 — AC7's not-adopted states extended by slice 116-02 AC7
  (owner-approved).** AC7 above says `progress` has "the same two states
  `coverage` has" (no vision file; vision without `## Use cases`). The 116-02
  craft review found that the scaffold template ships the section with
  placeholder bullets under a `status: unfilled` marker, so an unelicited
  project would show placeholder goals in every `/jig:orient` briefing. The
  owner chose to fix it in `progress` only: a section whose elicited marker says
  `status: unfilled` or `status: skipped` now also gets the one-line `no-op`
  note. From 116-02 on, `progress` has three not-adopted cases and `coverage`
  keeps two; aligning `coverage` and the step-2a prompt is parked in
  `docs/refinement-todo.md`. The AC text above is preserved as written.
