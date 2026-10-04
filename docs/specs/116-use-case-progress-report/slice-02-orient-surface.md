---
status: DONE
dependencies: [116-01]
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

## Slice 116-02 — orient-surface

**Goal:** The `/jig:orient` project briefing carries a short use-case progress
section whenever the project has adopted the use-case layer, so a returning
owner sees the project-wide done/known totals, the goals with nothing done yet,
and the untraced work — with a pointer to the full per-use-case listing —
without knowing `workflow.py progress` exists.
The section is printed by a deterministic `progress --summary` mode, so orient
copies it rather than filtering the full tree by hand.

**DoR:**
- ✅ 116-01 DONE — `workflow.py progress` exists and is the single source the
  summary is computed from.
- ✅ The briefing's structure is known:
  [skills/orient/SKILL.md](../../../skills/orient/SKILL.md) has a "What it reads
  (the survey)" section and a fixed, numbered output layout whose sections are
  each marked always / usually / "when they exist". Its headline section tells
  the model not to re-derive by hand what a deterministic command already
  computes — the reason the selection below lives in code.

**Acceptance Criteria:**

1. **A deterministic summary mode.** `workflow.py progress --summary` prints
   exactly three things, computed with slice 01's counting rule: the summary
   totals line; the use cases with no done slice or no spec (id, goal text, and
   which of the two); and the Unanchored count with its spec names. Each of
   the two name lists is capped at 10 entries, followed by an `… and N more`
   line when longer — a project that adopts the use-case layer late starts with
   every spec unanchored. It prints no per-spec tree and no percentage, and in the two not-adopted states it
   prints the same one-line `skipped` / `no-op` notes as the full mode. It
   always exits 0 and writes nothing. Observable: fixture tests over the same
   kinds of fixtures as slice 01, each shown to fail when its feature is
   removed.
2. **A named survey source.** The "What it reads (the survey)" section of the
   orient `SKILL.md` names `workflow.py progress --summary` as a read-only
   source, read only when the project's vision has a `## Use cases` section.
   Observable: the skill text names the command and the condition.
3. **One conditional section in the fixed layout.** The output layout gains a
   "Use-case progress" section marked "when the use-case layer is adopted". It
   carries the `--summary` output's three things and no more, copied rather
   than re-derived, plus one line naming `workflow.py progress` for the full
   per-use-case listing. It never reproduces the full tree and never states a
   percentage. Observable: the skill text specifies exactly those contents and
   both exclusions.
4. **Silent when not adopted.** For a project with no `## Use cases` section the
   briefing is unchanged — no section and no mention of use cases. Observable:
   the skill text states the omission rule.
5. **Orient still writes nothing.** The "Orient writes nothing" contract is
   unchanged; the new source is a read-only command. Observable: that section
   of the skill is untouched and the new source is described as read-only.
6. **Pinned and shipped to every host.**
   `skills/orient/test_orient_skill_surface.py` pins the new survey source and
   the new section, the spec-workflow `SKILL.md` bullet for `progress` names
   `--summary`, and the host packages are regenerated. Observable: the pins
   fail when either is removed, and `scripts/build_host_packages.py --check`
   exits 0.

7. **An unelicited vision is not adopted** (added 2026-10-03, owner-approved,
   from the craft review). The scaffold template ships `## Use cases` with
   placeholder bullets under an `<!-- elicited: PENDING / status: unfilled -->`
   marker, so every never-elicited project would otherwise show placeholder
   goals in every briefing. When the section's elicited marker says
   `status: unfilled` or `status: skipped`, `progress` — full and `--summary`
   — prints the one-line `no-op` note and no rollup, and orient's omission rule
   applies. A section with no marker, or a `status: filled` marker, is adopted.
   `coverage` and the spec-workflow step-2a prompt are unchanged (aligning them
   is parked in `docs/refinement-todo.md`). Observable: fixtures for unfilled,
   skipped, filled and no-marker sections, and one built from
   `templates/docs/product-vision.md.template`.

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

**Anti-horizontal-phasing check:** After this slice, a user who asks jig where
the project stands gets the done/known totals, the untouched goals, and the
unanchored work in the same briefing — no extra command, no new knowledge
required.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Pre-implementation frame changes** (deferred here from 116-01's sweep).
   Round-1 frame-critique was `needs-changes`: the three-item section was framed
   as surfacing the owner's rabbit-hole drift, which the agent-assigned links
   cannot deliver, and having the orient model filter the full `progress` tree
   by hand ran against orient's "don't re-derive by hand" rule and cost
   orchestrator context every run. Changes before implementation (commit
   `5564906d`): a new AC1 adds a deterministic `progress --summary` mode, so the
   selection lives in tested code; AC3 makes orient copy it and point at
   `workflow.py progress` for the full listing; the claim is narrowed project-wide
   (ADR-0064 bound 5). Round-2 pass nits, also applied pre-implementation: each
   name list capped at 10 with an `… and N more` line (a late adopter starts with
   every spec unanchored); the Goal and anti-horizontal check describe the
   section accurately (totals, untouched goals, untraced work); the spec's first
   assumption gains an owner checkpoint at the first `/jig:orient` run after the
   spec lands.
2. **Shared formatters.** The totals and closing `Summary:` line moved out of
   slice 01's full renderer into `_progress_totals` / `_progress_summary_line`,
   used by both modes, and a test asserts the two summary lines are identical.
   Full-mode output is byte-equivalent; slice 01's tests still pass.
3. **`--summary` output shape** (the ACs fixed content, not format): the
   `Summary:` line verbatim from the full report; `No done slice or no spec (N):`
   or `…: none`; `Unanchored (N):` or `…: none`; entries indented two spaces;
   overflow as `  … and N more`; a use case whose specs have zero slices counts
   as "no done slice", not "no spec"; no advisory header, so the output is
   exactly the three things.
4. **Orient layout.** The new "Use-case progress" section is #5, after "The one
   decision blocking the most" and before "Larger deferred bets", which
   renumbered the later sections to 6–11. The craft review searched skills,
   docs, tests and all host copies: nothing referenced the old numbers, and the
   existing tests match headings number-agnostically.
5. **AC7 added mid-slice (owner-approved 2026-10-03).** The craft review found
   that the scaffold template ships `## Use cases` with placeholder bullets
   under `status: unfilled`, so every unelicited project would see
   `UC-1 (actor) can (goal)` goals in each orient briefing. The owner chose a
   `progress`-only fix: `use_cases_unelicited` in `skills/_common/use_cases.py`
   reads the first `<!-- elicited: … -->` marker in the `## Use cases` section
   (tolerating trailing fields such as `/ hash: …`), and `progress` prints a
   one-line `no-op` in both modes when it says `unfilled` or `skipped`.
   `has_use_cases_section`, `classify_spec` and `coverage` are deliberately
   unchanged, so `progress` and `coverage` now disagree on whether an
   unelicited vision is adopted. Paper trail: a dated `## Amendments` entry on
   DONE slice 116-01 (its AC7 said "the same two states `coverage` has"), and a
   refinement-todo entry that also records the marker-only rule's residual (the
   step-2a grow path, or a hand-filled section, can leave a stale marker).
6. **Reviewer findings folded in** (both passes passed in each round). Round 1:
   orient now copies the `--summary` content "as bullets" (its formatting rules
   forbid inline lists); long line re-wrapped; over-claiming test renamed to
   `test_progress_without_summary_flag_still_prints_full_tree`; the zero-write
   guard's bare "progress" token tightened to specific phrases. Round 2: the
   marker regex fix above (it had required `status:` to be the last field), with
   hashed-marker and first-marker-decides tests; the `workflow.py` comment block
   and `progress()` docstring corrected from "two" to three not-adopted cases;
   orient's parentheticals now name all three (no vision file, no section, not
   elicited yet); the spec-workflow `SKILL.md` `progress` bullet names
   `--summary` and the unelicited no-op.
7. **Known residual.** `test_zero_write_section_does_not_gain_a_progress_exception`
   passes with the feature deleted by design: it guards AC5's "section
   untouched", and is not the evidence that the new source is read-only (that is
   `test_survey_describes_the_new_source_as_read_only`).
8. **Plan adherence.** `--summary` is the only new flag. Tests: 12 `--summary`
   tests, 12 orient pins and 1 spec-workflow pin at first delivery; the fix
   rounds added 6 AC7 workflow tests, 10 `UseCasesUnelicitedTests`, 2 orient
   pins. Each new test was mutation-checked. On jig: `progress --summary` prints
   282/300 slices done, UC-21 and UC-22 with no done slice, and 022 / 032
   unanchored.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | The front door documents neither orient's briefing sections nor `workflow.py` subcommands (no `orient` mention); nothing at that level changed. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` at each transition; `check-board` clean. |
| `docs/product-vision.md` | `no-op` | The AC9 exception wording (116-01) names `workflow.py progress`; `--summary` and the orient section stay inside it. No scope drift. |
| `docs/architecture.md` | `no-op` | Line 421 already lists `_common/use_cases.py` and `workflow.py`; a new helper and flag inside them change no module boundary. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | This slice closes spec 116. `CLAUDE.md`: Active-specs line says shipped through 113 plus 116, and a compact ADR-0064 clause ("don't grow it here") is appended to the existing "Recent review/posture closures" bullet — a separate line broke the spec 076 primer budget (70 lines / 14 KiB; `test_lean_primer` green at 70 lines / 14,280 bytes). `AGENTS.md`: the same one-liner in its Key-terms list for Codex parity (its stale "none in-flight" Active-specs line predates this spec and is left alone). `templates/` unchanged: the vision template's placeholder block is what AC7 now reads, not something it edits. |
| `docs/inbox.md` | `no-op` | Swept: no item is resolved by this slice; nothing new to park. |
| `docs/refinement-todo.md` | `updated` | New entry "should `coverage` and the step-2a prompt treat an unelicited vision as not adopted?", including the stale-marker residual. |
| `docs/memory/**` | `updated` | Glossary "use-case progress report" now covers `--summary`, the 10-entry caps, and the third not-adopted case (unelicited section). |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR touched; ADR-0064 already covers the orient section ("one subcommand plus one orient section"). `check-index` clean. |
| `slice-01-progress-rollup.md` | `updated` | Dated, owner-approved `## Amendments` entry recording that AC7's two not-adopted states became three for `progress` (AC text preserved, ADR-0010). |
| `spec.md` | `updated` | The overview banner's stale "**DRAFT.**" is dropped as this slice closes the spec. Checked and left as written: the Decomposition's "the two not-adopted paths" (slice-01 split reasoning); the "What it is not" paragraph and Assumptions still hold. |
| 116-01's `deferred` sweep row "slice-02 frame-review edits" | `updated` | Discharged by deviation item 1 above. |
| `reviews/slice-02-*.md` | `no-op` | Review evidence is written by `review.py record-review`, not reconciled prose; excluded from the sweep by convention. |
| Additional live prose / generated templates touched by this slice | `updated` | `skills/orient/SKILL.md` (survey bullet + section 5 + renumbering), `skills/spec-workflow/SKILL.md` (`progress` bullet), `skills/_common/use_cases.py` and `workflow.py` docstrings/comments, and the regenerated `hosts/{claude,codex,copilot}` mirrors (`build_host_packages.py --check` exit 0). |
