---
status: DRAFT
skill: migrate
tier: 0
---

# Spec 008: migrate

## Overview

Introduce `migrate` — a sibling to `scaffold-init` that handles the
inverse case: jig adoption into a project that **already has** spec-driven
structure. The motivating fixture is
[aso-shallow-validator](https://github.com/...), a mature internal project
that organically grew the same workflow jig codifies (27 slices, 22 ADRs,
4 spikes, custom skills, custom agents) but landed on different
conventions, different filenames, and different topology.

`scaffold-init` today refuses on already-scaffolded projects. The refusal
is correct — overwriting an existing CLAUDE.md or `docs/architecture.md`
is unsafe — but it leaves the user with no path forward. `migrate` is
that path: detect the existing shape, produce a mapping plan,
and (in later slices) apply the rename / restructure operations needed
to bring the project under jig's defaults without losing existing work.

This spec is also the **first real test of jig's `docs/decisions/` rename**
(decided in [ADR-0004](../../adrs/0004-decisions-folder-naming.md)). One of
its slices will perform that rename — both inside jig itself (the smallest
possible fixture) and as a reusable operation `migrate.py` exposes for
external projects.

## Why now

- **scaffold-init has a gap users will hit.** Anyone introducing jig to
  an existing repo (not greenfield) currently has no documented path.
  The aso-shallow-validator dogfood made this concrete: jig's detection
  check (`scaffold.json` or `docs/specs/`) misses validator-style layout
  (`docs/slices/`, `docs/decisions/`), so scaffold-init would either
  refuse confusingly or worse, pollute the tree.
- **ADR-0004's rename has nowhere to land.** The folder rename
  (`docs/adrs/` → `docs/decisions/`, plus `adr-NNNN-` filename prefix)
  is accepted but unimplemented. It needs an implementation home. A
  general `migrate.py rename-decisions` subcommand serves both jig's
  self-migration AND every future external project — same code path.
- **The validator is a complete, real fixture.** 27 flat slices across
  6 milestones, 22 ADRs, 4 spikes, sub-slicing (18.1–18.5). Designing
  `migrate` against this fixture surfaces every topology question
  spec 008 needs to answer.
- **Spec 008 is the first cross-Tier work.** Slices touch scaffold-init
  (Tier 0), spec-workflow (Tier 0), adr-workflow (Tier 1). It will
  exercise jig's own cross-skill coordination — useful signal about
  whether `skills/_common/` is sized correctly.

## Goals

1. Produce a **read-only migration report** that a user can run against
   any existing project to see (a) what jig would change, (b) what
   conflicts exist, (c) what's ambiguous and needs human judgment.
2. Provide **bounded, idempotent migration operations** as separate
   `migrate.py` subcommands — `rename-decisions`, future
   `slice-to-spec`, etc. Each operation is independently runnable, has
   a `--dry-run` mode, and refuses on conflict rather than corrupting.
3. **Apply ADR-0004's rename to jig itself** as the first production
   use of `migrate.py rename-decisions`. Closes ADR-0004's open
   question #1 (was the rename its own spec, or part of 008? Answer:
   part of 008, via the shared helper).
4. Teach `scaffold-init` to detect "this dir looks already-spec-driven"
   and suggest `/jig:migrate` instead of refusing opaquely.

## Non-goals

- **Auto-migration without user judgment.** The report names what's
  ambiguous (e.g. "27 flat slices and 6 milestones — should each
  milestone become a parent spec?"). The user answers; the helper
  doesn't guess.
- **Migrating non-spec artifacts.** Custom skills, custom agents,
  domain-specific docs (`recipe-coverage-matrix.md`-style trackers) are
  left untouched. They're inventoried in the report so the user knows
  they exist, but they're out of `migrate`'s mandate.
- **JIRA/Linear/Asana ticket mapping.** The validator references
  milestones (M1–M6) that map to JIRA epics; jig has no ticketing
  signal anywhere. Ticket mapping is a separate skill, not in 008.
- **Cross-format ADR conversion.** Projects using a different ADR
  template (MADR, Y-statements, etc.) get inventoried but not
  reformatted. ADR-0004 just covers the path/filename rename.
- **Importing existing CLAUDE.md content.** The validator's 59KB
  CLAUDE.md has accumulated sprint log entries jig's Hot Cache
  doesn't model. The report flags this; the user decides what to
  port.
- **Sub-slice topology implementation.** Sub-slicing (validator's
  18.1–18.5 pattern) is captured in
  [refinement-todo](../../refinement-todo.md#decision-sub-slice-topology-and-naming)
  with four open questions. Slice 008-05 may pick it up; if so, the
  open questions get answered in that slice's design. If sub-slicing
  is deferred past 008, the migration report just notes the validator
  has them and recommends manual handling.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| **S** — Spike | Do we need a spike to discover what's in existing projects? | **No.** ADR-0004 settled the structural questions (folder name, filename prefix). The validator is a complete fixture for design. Anything we don't yet know will surface as ambiguity in the report — the report itself is the discovery mechanism. |
| **P** — Path | Read-only report vs. mutating operations vs. wizard. | **Report-only first** (slice 008-01) — mirrors `land.py prepare`. Each mutating operation lands as its own slice with its own safety surface (008-02 rename-decisions, 008-03 jig-self-migration as dogfood, etc.). No bundled wizard; SKILL.md orchestrates the sequence. |
| **I** — Interface | One helper or several? | **One `migrate.py` with subcommands** (`report`, `rename-decisions`, `slice-to-spec`, …). Matches the `workflow.py` precedent (`transition`, `status-board`). One SKILL.md, auto-triggering on adoption-related prompts. |
| **D** — Data | What does the report contain, and how is the mapping plan structured? | Five sections: **Inventory** (what's present), **Mapping** (what becomes what under jig), **Conflicts** (collisions that block migration), **Ambiguities** (judgment calls the user must make), **Operations** (suggested `migrate.py` subcommand invocations in order). The mapping is a structured table, not free prose. |
| **R** — Rules | What does the report consider "spec-driven enough" to migrate? | **Three of the following four** trigger an "adoptable" verdict: `docs/slices/` or `docs/specs/`; `docs/decisions/` or `docs/adrs/`; `docs/workflow.md`; `docs/architecture.md`. Two or fewer → report flags as "not yet spec-driven" and recommends `scaffold-init` instead of `migrate`. Zero of the four → unambiguous greenfield, run `scaffold-init`. |

## Out of scope for spec 008 (any slice)

- Importing arbitrary directory structures from non-spec-driven projects
  (e.g. only `docs/design.md` and `docs/decisions.md`).
- Cross-tool migrations from spec frameworks that aren't jig-shaped
  (e.g. RFC-based, BDD-based).
- Roundtripping: once migrated, going back. Not supported. The
  migration is one-way; the user keeps the pre-migration commit as
  their rollback.
- Auto-generating ADRs from existing decisions buried in commit
  messages or doc comments.
- Multi-project batch migration. One project at a time.

---

## Slice 008-01 — migrate-report

**STATUS: DONE**

**Goal:** `migrate.py report <project-dir>` produces a structured
markdown report on the existing project's spec-driven shape, with
five sections (Inventory / Mapping / Conflicts / Ambiguities /
Operations). Active SKILL.md (or extension to scaffold-init's SKILL.md
— design point in plan.md) auto-triggers on adoption-related prompts.
No filesystem mutations whatsoever — pure read.

**DoR:**
- ✅ ADR-0004 accepted: settles the rename target shape.
- ✅ Fixture available: aso-shallow-validator at
  `/Users/ramboz/Projects/misc/aso-shallow-validator/`.
- ✅ Precedent for read-only report pattern:
  [land.py prepare](../../../skills/slice-land/land.py) (slice 007-01).
- ✅ Tier 0 (`spec-workflow`, `scaffold-init`) and Tier 1
  (`adr-workflow`) are all DONE — `migrate.py` can reference their
  conventions without circular dependency.

**Acceptance Criteria:**

1. **`migrate.py report <project-dir>`** verifies the dir exists and
   emits a structured markdown report to stdout. The report has five
   sections, in this order:
   - **Inventory** — a table listing detected artifacts: spec/slice
     dirs (e.g. `docs/slices/`, `docs/specs/`), decision dirs (e.g.
     `docs/decisions/`, `docs/adrs/`), spike dirs, workflow docs,
     architecture doc, custom skills under `.claude/skills/`, custom
     agents under `.claude/agents/`, and a CLAUDE.md size. Each row:
     path + count + one-line shape note.
   - **Mapping** — a table of "current path/name → jig path/name":
     `docs/adrs/` → `docs/decisions/`,
     `docs/decisions/` → kept (already matches ADR-0004),
     `adr-NNN-slug.md` → `adr-NNNN-slug.md` (4-digit zero-pad if
     currently 3-digit),
     `docs/slices/slice-NN-name.md` → noted as "topology question —
     see Ambiguities" (no automated mapping until 008-04 lands).
   - **Conflicts** — items that block migration. Examples:
     `docs/adrs/` AND `docs/decisions/` both present (helper can't
     merge — refuses); filename collision after prefix add; CLAUDE.md
     contains markers from a different scaffolder.
   - **Ambiguities** — judgment calls the user must make. Examples:
     "27 flat slices and 6 milestones — should each milestone become
     a parent spec? (See 008-04 — currently deferred)";
     "validator has custom skills overlapping jig's stock set —
     replace, layer, or leave?";
     "CLAUDE.md is 59KB with sprint log — port subset to Hot Cache
     or leave as-is?".
   - **Operations** — an ordered list of suggested
     `migrate.py <subcommand>` invocations the user should run, with
     `--dry-run` first. For slice 008-01 the only available operation
     is `rename-decisions` (slice 008-02, deferred); the report names
     it but flags that the subcommand isn't yet implemented.

2. **Adoptability verdict** at the top of the report:
   `**Verdict:** adoptable | partial | not-yet-spec-driven`.
   - `adoptable` — three of the four triggers present (see SPIDR
     Rules).
   - `partial` — exactly two triggers present; report still runs but
     flags that scaffold-init may be the better path.
   - `not-yet-spec-driven` — zero or one trigger; report still runs
     for transparency but the top-line recommends `scaffold-init`.

3. **Exit codes:** 0 on `adoptable`; 1 on `partial` (informational, not
   an error — the report is still useful); 2 on user error (no
   `<project-dir>` argument, dir doesn't exist, dir not readable).
   `not-yet-spec-driven` returns 0 — the report is the deliverable
   regardless of verdict.

4. **`migrate.py` does NOT execute any filesystem-mutating commands**
   anywhere in the report subcommand. Tests assert this via a regex
   sweep on the helper's source for `os.replace`, `shutil.move`,
   `Path.write_text`, `Path.unlink`, `Path.rename`, etc. — none of
   these should appear in the `report` code path. `open()` is allowed
   for reads only.

5. **`skills/migrate/SKILL.md`** is created with active frontmatter
   (no `disable-model-invocation`). Description auto-triggers on:
   "migrate this project to jig", "adopt jig here", "this repo already
   has specs — set up jig", "scaffold-init refused — what now",
   "introduce jig to an existing codebase". Body documents the
   `report` subcommand and mentions future subcommands as `Coming in
   slice 008-NN`.

6. **Tests** in `skills/migrate/test_migrate.py` cover:
   - `InventoryTests` — fixture project (synthesized from a tiny
     validator-shaped tree) → inventory table has expected rows.
   - `VerdictTests` — fixture with three triggers → `adoptable`;
     two → `partial`; one → `not-yet-spec-driven` with exit 0.
   - `MappingTests` — fixture with `docs/adrs/0001-foo.md` → mapping
     row maps to `docs/decisions/adr-0001-foo.md`.
   - `ConflictTests` — fixture with both `docs/adrs/` and
     `docs/decisions/` present → conflict row, verdict still
     `adoptable` but Operations section refuses to suggest
     `rename-decisions`.
   - `AmbiguityTests` — fixture with flat slices and a milestone doc
     → ambiguity row names the topology question.
   - `SafetyTests` — regex sweep on helper source confirms no
     mutating calls in the `report` code path.
   - `SkillSurfaceTests` — frontmatter active; description has trigger
     phrases; body references `migrate.py report`.
   - `DogfoodTests` (optional, gated on the validator path existing) —
     runs `migrate.py report` against the actual validator and
     asserts the verdict is `adoptable`. Skipped in CI / when the
     validator isn't present.

7. **The first real run is against the validator.** As part of slice
   closure (not the test suite — the validator is a private path),
   the implementer runs `migrate.py report
   /Users/ramboz/Projects/misc/aso-shallow-validator/` and captures
   the report's verdict + section summaries in the deviation log.
   That report becomes the input for sizing slice 008-04
   (slice-to-spec-mapping) and the sub-slice work in
   [refinement-todo](../../refinement-todo.md#decision-sub-slice-topology-and-naming).

**DoD** (same shape as 003-01 / 004-01 / 005-01 / 006-01 / 007-01):
- [x] All 7 ACs pass; full test suite green (existing + new). **34 new migrate tests (32 from implementation + 2 from §7 reviewer-flagged fixes); 291 total across 8 skill directories; no regressions in the 257 existing tests.**
- [x] Implementer test coverage exercises a realistic fixture structure (mini-validator tree under `skills/migrate/fixtures/`). **Four fixtures: `tiny-validator` (3+ triggers, exercises Inventory/Mapping/Ambiguities); `greenfield` (zero triggers, exercises `not-yet-spec-driven` verdict); `partial` (two triggers, exercises exit-1 verdict); `conflict` (both `docs/adrs/` + `docs/decisions/`, exercises Conflicts section).**
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py` (dogfood). **Verdict: `pass` with 4 specific issues (README leak in slices/spikes, header asymmetry in empty Operations branch, description-regex brittleness, undocumented 5+ digit ADR pass-through). All 4 addressed inline before reconciliation; logged in §7a–§7d.**
- [x] Deviation log produced under this slice heading. **See below — includes validator-dogfood transcript per AC #7.**
- [x] Reconciliation review pass. **Two passes: first returned `needs-changes` with line-ref drift in §7 and a 23→22 ADR-pad count discrepancy in §2; corrections applied; second pass confirmed `pass` conditional on the final 165/170 → 159/163 call-site line-ref fix, which was applied.**
- [x] `docs/refinement-todo.md` left untouched (no resolutions yet — 008-01 only reports; the sub-slice and topology open questions remain open for later slices). **Confirmed: only the prior-session edits remain (sub-slice entry, `adr.py` index bug, accept/index ordering).**

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. They are deliberately outside the DoD so that `slice-land`'s
`check_dod` doesn't false-positive-block landing on items that depend on
the DONE state. Convention introduced by spec 009 / slice 009-01.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board` AFTER the final status transition. **29 slice(s) across 9 spec(s); 008-01 row shows DONE.**
- [x] `CLAUDE.md` skills table adds `migrate` as a new active row, tier 0. **Done — added `/jig:migrate` row to the Skills table; added spec 008 entry under Active specs; sprint focus updated to mention spec 008 closed.**

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice.
A user with an existing spec-driven repo runs `migrate.py report .`
→ gets a five-section report with a verdict → knows what to do next.
The report is the entire user-facing deliverable; no plumbing slice
that doesn't itself produce value.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. Added two test classes beyond the spec's enumerated eight (`OperationsTests`, `ErrorTests`).**
The spec's AC #6 enumerated eight test classes (Inventory, Verdict, Mapping, Conflict, Ambiguity, Safety, SkillSurface, Dogfood). During TDD I split `OperationsTests` out as a ninth class because the Operations section is independently testable (per AC #1 it's one of the five report sections) and bundling its assertions inside one of the other classes would have muddied the per-section coverage. `ErrorTests` was also added as a tenth class — it's not in AC #6's enumeration but is implied by AC #3's exit-2 user-error requirement. Total test classes: **10**. Test count: **32 initially, growing to 34 after the §7 reviewer-flagged regression tests landed.**

**2. Validator dogfood (AC #7) — full transcript.**

Invocation:
```
python3 skills/migrate/migrate.py report /Users/ramboz/Projects/misc/aso-shallow-validator/
```

Exit code: `0`. Verdict: `adoptable`. Section counts:
- **Inventory rows:** 9 (slices=32, decisions=23, spikes=4, workflow=1, architecture=1, product-vision=1, custom skills=3, custom agents=3, CLAUDE.md=59075 bytes).
- **Mapping rows:** 26 (1 decisions-dir kept + 22 ADR file pads + 1 flat-slices topology + 2 doc-landmark kept). **Note:** the validator's `docs/decisions/` contains 23 `.md` files, but only 22 are pad-mappable — `adr-review-2026-04-22.md` (a quarterly review log, not a numbered ADR) has a non-numeric stem that `PAD_RE` doesn't match, so `_map_adr_filename` passes it through unchanged and `render_mapping` suppresses the row when current==target. Reviewer-caught discrepancy from the original "23 pads" claim; the headline 26 was always correct.
- **Conflicts:** none.
- **Ambiguities:** 5 rows (milestone-to-spec mapping for M1–M5; custom skills overlap; custom agents overlap; CLAUDE.md size; spike-workflow gap).
- **Operations:** 2 numbered suggestions (rename-decisions deferred to 008-02; slice-to-spec deferred to 008-04).

Surprises:
- **Validator has 32 slices, not 27.** The "27 slices, 22 ADRs, 4 spikes" stats from the prior session's gap analysis were under-counts (new work landed in the interim). Real numbers: 32 slices, 23 ADRs, 4 spikes.
- **Validator references 5 milestones (M1–M5), not 6.** ADR-013 names M1–M6 but slices only reference through M5 so far. M6 work hasn't started or doesn't tag the milestone field. This narrows slice 008-04's parent-spec target count from 6 to 5 (revisable once M6 work lands).
- **Validator's `docs/decisions/` is already on the "kept" side of ADR-0004 (no `docs/adrs/`).** This means jig's own migration (slice 008-03) will be a more rigorous test of `rename-decisions` than the validator's — the validator only needs filename padding (3-digit → 4-digit), not the folder rename.

**3. Two dogfood-surfaced bugs fixed before review (with regression tests).**

The first dogfood run produced two real bugs the test fixtures hadn't caught:

   3a. **Operations numbering skipped 2.** The output read `1. ... 3. ...` because the original code computed `len(ops) + 1` where `ops` already contained the header line. Fixed by separating header from items and numbering items via `enumerate()`. Regression test: `OperationsTests.test_operations_numbering_is_sequential`. The test checks that the numbered items in the Operations section run 1, 2, 3, … with no gaps.

   3b. **`.claude/agents/README.md` was listed as a custom agent.** The fixtures didn't include a README under `.claude/agents/`; the validator does, so the dogfood exposed the leak (and the same pattern would have leaked under `.claude/skills/README.md`). Fixed by adding the same `name.lower() != "readme.md"` filter already used for `docs/decisions/` and `docs/adrs/`. Regression test: `AmbiguityTests.test_readme_excluded_from_agents_listing` builds a synthetic tree with `.claude/agents/README.md` + `.claude/agents/real-agent.md` and asserts only the real agent appears in the Custom agents inventory row.

Both fixes added 2 tests (32 total, up from 30 originally). No existing tests modified. The second dogfood run after the fixes produced the clean transcript captured above.

**4. Design choices logged:**

   4a. **Helper does NOT use `skills/_common/parsing.py`.** The `find_slice_section` helper that the parent's brief flagged is for slice-section parsing inside spec files; `migrate.py` walks the filesystem and only reads files for milestone-frontmatter regex matching, not for slice-section navigation. No cross-skill import needed.

   4b. **Helper does NOT use `subprocess` at all.** Unlike `land.py`, `migrate.py` doesn't shell out to anything (no `git rev-parse`, no `tdd.py run`). This kept the `SafetyTests` simpler (no need to special-case allowed git invocations like `land.py` does) and matches the "strictly read-only" intent. If a future subcommand needs git state (e.g. `rename-decisions` for tracked-file detection), it gets its own SafetyTests carve-out at that time.

   4c. **`_safe_read_text` caps reads at 200KB.** Validator's CLAUDE.md is 59KB; jig's template is 7KB; 200KB is a generous upper bound that protects against pathological inputs without preventing legitimate large CLAUDE.md / slice files from being scanned for milestone references. Not tested directly (no fixture is that large); if a real project hits the cap, the milestone scan misses the tail of the file — degradation is silent and graceful (no crash).

   4d. **Inventory's "out of 008-01 scope" inline notes.** Each custom-skill / custom-agent row in Inventory says "(out of 008-01 scope)" inline. The same content is restated in the Ambiguities section. The duplication is intentional: a user scanning Inventory should see the caveat without having to jump sections, AND the Ambiguities section should still enumerate every judgment call so it's a complete punch-list.

   4e. **`docs/product-vision.md` is inventoried but not migration-relevant.**
   It doesn't count toward the four-trigger verdict logic, doesn't appear in Mapping (no rename needed), and isn't called out in Ambiguities. Inventory-only. Rationale: jig's scaffold-init template creates `docs/product-vision.md` too, so any migration would preserve it as-is.

   4f. **`OperationsTests.test_operations_numbering_is_sequential` asserts >=2 items.**
   The test gracefully skips the assertion when fewer than 2 items are present (a project with only 1 operation can't have a numbering-gap bug). If 008-02 lands and adds a third operation, the test catches a gap there automatically.

**5. Doc updates from this slice:**

- `skills/migrate/migrate.py` — net-new helper, ~370 lines.
- `skills/migrate/test_migrate.py` — net-new test suite, 34 tests (32 from initial implementation + 2 README-exclusion regression tests added during reconciliation per §7a).
- `skills/migrate/SKILL.md` — net-new active SKILL.md.
- `skills/migrate/fixtures/` — four fixture trees (`tiny-validator`, `greenfield`, `partial`, `conflict`).
- No `architecture.md` changes (helper colocated with its skill — same precedent as `scaffold.py` / `memory.py` / `workflow.py` / `review.py` / `adr.py` / `tdd.py` / `land.py`).
- No new ADR required (ADR-0004 already settled the structural questions this slice operationalizes).
- No `learnings.md` entry — the dogfood-surfaced bugs were fixed before review, with regression tests; they're closer to TDD coverage gaps than memorable lessons.

**6. CLAUDE.md / status-board update deferred until DONE transition.**

Per the reconciliation order lesson recorded in slice 006-01's deviation log, `CLAUDE.md` skills-table promotion and `docs/specs/README.md` regen happen AFTER the final DONE transition, not during implementation. Both DoD boxes for those are intentionally left unticked at this point.

**7. Reviewer-flagged fixes applied during reconciliation:**

The implementation review verdict was `pass` with four specific issues, all non-blocking. All four were addressed inline before reconciliation; total test count grew from 32 → 34 (two new regression tests for the latent README leak).

   7a. **README-exclusion asymmetry (latent bug).** Reviewer flagged that `_is_content_md`-style filtering was applied to decisions/adrs/skills/agents but NOT to slices/spikes. A `docs/slices/README.md` or `docs/spikes/README.md` would have leaked into the inventory counts. The validator doesn't currently have those files, but a future project might. **Fix:** extracted the README-exclusion logic into a single `_is_content_md(entry)` helper at `migrate.py:70-82` and applied it uniformly to all six `.md`-listing scans (slices, decisions, adrs, spikes, skills, agents) — call sites at lines 116, 130, 136, 142, 159, 163. **Regression tests:** `AmbiguityTests.test_readme_excluded_from_slices_count` and `AmbiguityTests.test_readme_excluded_from_spikes_count` (at `test_migrate.py:181-223`) build synthetic trees with `README.md` siblings and assert the count column reflects only content files.

   7b. **"Suggested order" header asymmetry.** When the Operations section had no items, the helper still emitted `Suggested order (each operation is --dry-run first):` followed by `_No automated operations apply..._` — header was misleading when there was nothing to order. **Fix:** suppress the header in the empty-items branch at `migrate.py:470-478`. No new test (the empty-items state isn't exercised by any current fixture; `tiny-validator` always produces at least one operation).

   7c. **Description-regex brittleness.** Reviewer flagged that the test's description-extraction regex `(?=\n\w+:|\Z)` overran into `user-invocable:` because the folded `>` block is indented. The test passed only because the five trigger phrases happened to sit before `user-invocable:` in the SKILL.md. **Fix:** anchored the lookahead on `^[A-Za-z][\w-]*:\s` with `re.MULTILINE` (only zero-indent YAML keys terminate the description), and added an explicit guard `assertNotIn` against `user-invocable:` / `name:` leaking into the captured description. The fix is in `test_description_has_all_five_trigger_phrases` at `test_migrate.py:370-410`. Now any future SKILL.md layout that places `user-invocable:` before the trigger phrases would fail the test loudly instead of silently passing on broken extraction.

   7d. **5+ digit ADR pass-through (documentation only).** Reviewer flagged that `PAD_RE` (`\d{3,4}`) silently passes through 5+ digit ADR numbers without normalization (the `-.+` group absorbs the extra digits). This is intentional — jig itself only standardizes on 4-digit per ADR-0004, and a project with >9999 ADRs is well outside any realistic migration target. **Fix:** added a clarifying docstring to `_map_adr_filename` at `migrate.py:258-276` (the function spans the `PAD_RE` definition at line 255 through the close of the function body) so the behavior is explicit rather than undocumented. No code change, no new test.

**8. Reconciliation-review-prep note: brittle-regex pattern.**

The description-regex fix in §7c is a generic anti-pattern worth flagging beyond this slice: regex lookaheads of the form `(?=\n\w+:|\Z)` are unreliable for YAML frontmatter parsing because they don't account for the difference between top-level keys (zero-indent) and content of folded `>` blocks (indented). Any future SKILL.md surface test that uses similar extraction logic should anchor on either the explicit closing `---` of the frontmatter or on `^[A-Za-z][\w-]*:` with `re.MULTILINE`. If a third occurrence of this pattern emerges, it's a candidate for a shared helper in `skills/_common/`.

---

## Slice 008-02 — rename-decisions

**STATUS: DRAFT** _(deferred — first mutator; needs slice 008-01's report
output to validate safety surface)_

**Goal:** `migrate.py rename-decisions <project-dir> [--dry-run]`
applies ADR-0004's rename to a target project:
- `docs/adrs/` → `docs/decisions/`
- `NNNN-<slug>.md` → `adr-NNNN-<slug>.md` (pad to 4 digits if
  currently 3-digit, per ADR-0004)
- Update cross-references in any file under `docs/`, `CLAUDE.md`, and
  `.claude/` that contains a path matching `docs/adrs/...` (regex
  sweep + replace, idempotent).
- Refuse if both `docs/adrs/` and `docs/decisions/` exist (conflict
  case from 008-01's report).
- `--dry-run` emits the planned operations + diffs without writing.

Deferred from 008-01 because: first mutator slice deserves its own
review pass, and 008-01's report needs to exist first to validate
that the conflict-detection logic catches every case before a
mutator runs.

**Resolution trigger:** Slice 008-01 lands and produces a clean
report against the validator. The mutator is the obvious next slice.

---

## Slice 008-03 — jig-self-migration

**STATUS: DRAFT** _(deferred — production use of 008-02 on jig itself)_

**Goal:** Apply slice 008-02's `migrate.py rename-decisions` to the
jig repo. This is the first production use, doubling as ADR-0004's
implementation. Affects:
- Physical rename of `docs/adrs/` → `docs/decisions/` (4 files).
- File renames `0001-…` → `adr-0001-…`, etc.
- Cross-reference updates in `CLAUDE.md`, `docs/architecture.md`,
  every spec file referencing an ADR, every SKILL.md mentioning
  `docs/adrs/`.
- `skills/adr-workflow/adr.py` defaults updated to write to the new
  path with the new filename pattern (note: this is a code change,
  not a `rename-decisions` mutation — flagged as scope expansion for
  008-03 or split into a separate small slice).
- `templates/docs/adrs/` → `templates/docs/decisions/` with template
  content updates.
- `skills/scaffold-init/scaffold.py` target-dir creation updated.

Deferred because: needs 008-02 to land first.

**Resolution trigger:** 008-02 DONE.

**Open question:** Does the `adr.py` and `scaffold.py` code update
belong in 008-03 or in a separate slice 008-3b? The mechanical
rename is one operation; updating the helper's defaults is another.
Lean toward one slice for atomicity (jig's ADR conventions are wholly
new after this slice — partial states would confuse).

---

## Slice 008-04 — slice-to-spec-mapping

**STATUS: DRAFT** _(deferred — needs design work; depends on
sub-slice-topology decision)_

**Goal:** `migrate.py slice-to-spec <project-dir>` interactively (or
via a manifest file) maps flat `docs/slices/slice-NN-name.md` files
into jig's `docs/specs/NNN-<parent>/spec.md` nested model. The
parent specs are synthesized from milestone designators (validator
case: M1–M6 → six parent specs), or from a user-supplied grouping
manifest.

Deferred because: this is the biggest topology question and it
needs a real session with the validator's full slice set to design.
Also depends on the sub-slice topology decision (see
[refinement-todo](../../refinement-todo.md#decision-sub-slice-topology-and-naming)).

**Resolution trigger:** Either (a) 008-01 + 008-02 + 008-03 all
DONE and the validator migration is actively in progress, OR (b) a
second project with similar flat-slice topology surfaces.

---

## Slice 008-05 — scaffold-init --migrate suggestion

**STATUS: DRAFT** _(deferred — small wiring slice, depends on 008-01)_

**Goal:** Extend `scaffold-init`'s "already scaffolded" detection
(currently checks `scaffold.json` or `docs/specs/`) to also detect
validator-style layout (`docs/slices/`, `docs/decisions/`,
`docs/workflow.md`, etc.). On detection, refuse with a structured
message that invokes `migrate.py report` and suggests
`/jig:migrate`.

Deferred because: small wiring task, doesn't deliver standalone
value until 008-01 exists.

**Resolution trigger:** 008-01 DONE.
