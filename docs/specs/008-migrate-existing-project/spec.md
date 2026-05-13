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

**STATUS: DONE**

**Goal:** `migrate.py rename-decisions <project-dir> [--dry-run]`
applies ADR-0004's rename to a target project. The helper is the first
**mutating** migrate subcommand. It is bounded, idempotent, refuses on
conflict, and produces a structured operations plan that the user can
preview via `--dry-run` before applying.

What it does (concrete operations, in order):

1. **Rename the decisions directory** `docs/adrs/` → `docs/decisions/`,
   if `docs/adrs/` exists and `docs/decisions/` does not.
2. **Rename ADR files** to `adr-NNNN-<slug>.md` shape: pad 3-digit
   prefixes to 4-digit; prepend `adr-` where missing (per ADR-0004).
3. **Rewrite cross-references** in text files under `docs/`,
   `CLAUDE.md`, and `.claude/`: substitute every literal path mention
   that matches an old name (`docs/adrs/`, old filename) with its new
   equivalent. Idempotent: running twice on an already-migrated tree
   makes zero changes.

What it refuses to do (each is a hard exit, no partial writes):

- Both `docs/adrs/` and `docs/decisions/` present (conflict case from
  008-01's report — the user must merge manually).
- Filename collision after pad/prefix normalization (two files in the
  same source dir map to the same target name).
- `<project-dir>` does not exist, is not a directory, or contains no
  `docs/adrs/` or `docs/decisions/` (nothing to do — exit non-error
  with an "already aligned" message).

**DoR:**
- ✅ Slice 008-01 (`migrate.py report`) is DONE — its conflict-
  detection logic (`docs/adrs/` AND `docs/decisions/` both present)
  is the safety check 008-02 inherits.
- ✅ ADR-0004 is Accepted — the rename target shape is fixed.
- ✅ Atomic-write precedent exists: `adr.py` uses `tmp + os.replace`
  for content writes. `migrate.py rename-decisions` reuses the
  pattern.
- ✅ Cross-reference scope is bounded: validator-dogfood inventory
  (see 008-01 deviation log §2) confirms references live in
  `docs/**`, `CLAUDE.md`, and `.claude/**` — no surprise locations.
- ✅ Fixture tree exists: `skills/migrate/fixtures/tiny-validator`
  has the right shape for adapting into rename-test fixtures.

**Acceptance Criteria:**

1. **`migrate.py rename-decisions <project-dir>`** verifies the dir
   exists, walks the migration plan, and applies it. On success,
   exits 0 and prints a summary to stdout with one line per
   operation actually performed (e.g. `renamed docs/adrs/ →
   docs/decisions/`, `renamed docs/decisions/0001-foo.md →
   docs/decisions/adr-0001-foo.md`, `rewrote 4 cross-references in
   docs/architecture.md`). When there is nothing to do (the project
   is already on the canonical shape), the helper exits 0 with a
   single-line "already aligned" summary and no further output.

2. **`migrate.py rename-decisions <project-dir> --dry-run`** emits
   the planned operations to stdout in the same shape as #1, but
   prefixes every line with `[dry-run]` and performs zero filesystem
   mutations. Tests assert the project tree is byte-identical before
   and after a `--dry-run` invocation.

3. **Refusal cases** (each is exit code 2, with a structured error
   message to stderr; no filesystem mutations occur):
   - Both `docs/adrs/` and `docs/decisions/` present.
   - Filename collision after pad/prefix normalization within the
     decisions dir (e.g. `0001-foo.md` and `adr-0001-foo.md` both
     present → would both map to `adr-0001-foo.md`).
   - `<project-dir>` missing, not a directory, or not readable.

4. **No-op cases** (each is exit code 0, no mutations, no error):
   - Neither `docs/adrs/` nor `docs/decisions/` present (no ADRs to
     migrate — emit "already aligned" and return).
   - `docs/decisions/` present and every file is already on the
     `adr-NNNN-<slug>.md` shape (canonical — same message).

5. **Atomicity & idempotency:**
   - Every individual file write uses the `tmp + os.replace`
     pattern (same `_atomic_write` shape as `adr.py`).
   - The directory rename uses `os.replace(src, dst)` — POSIX-atomic
     on same-FS. The helper does NOT fall back to copy-then-delete.
   - Running the command twice on the same tree leaves the tree
     unchanged after the first successful run. Tests assert this
     by hashing the tree before and after the second run.

6. **Cross-reference rewriting scope:**
   - Scanned roots: `docs/` (recursive), `CLAUDE.md` (single file),
     `.claude/` (recursive).
   - File-type filter: text files only (`.md`, `.py`, `.txt`,
     `.json`, `.yaml`, `.yml`, `.toml`, plus files with no
     extension that decode as UTF-8 in the first 4KB). Binary
     files are skipped.
   - Skipped paths: any path component named `.git`, `node_modules`,
     `.venv`, `__pycache__`, or any path containing `/dist/` /
     `/build/`. The helper never reads or writes outside
     `<project-dir>`.
   - Two substitutions per file, applied in order: (a) literal
     `docs/adrs/` → `docs/decisions/`; (b) for each renamed file,
     its old name → new name. The two-step ordering matters
     because (b) operates on filenames only; (a) handles the
     directory-path portion.
   - The helper itself (`migrate.py`) and its tests
     (`test_migrate.py` / `fixtures/**`) are NEVER rewritten — they
     contain the canonical regexes and sample paths. Tests assert
     this.

7. **`--dry-run` plan is deterministic and order-stable.** The plan
   prints operations in a fixed order: directory rename first, then
   file renames (sorted by source filename), then cross-reference
   rewrites (sorted by file path). Re-running `--dry-run` against
   the same tree produces byte-identical output.

8. **SKILL.md updated:** `skills/migrate/SKILL.md` adds a new
   `### Run the rename-decisions migration` subsection under "How to
   use", removes the slice-008-02-deferred caveat from the existing
   text, and updates the Gotchas to reflect the new mutating
   subcommand (e.g. "**`migrate.py` is read-only EXCEPT for
   `rename-decisions`** — see Gotchas for the safety surface").
   The frontmatter description gains one trigger phrase:
   "apply ADR-0004 to my project".

9. **Tests** in `skills/migrate/test_migrate.py` (extending the
   existing 34) cover:
   - `RenamePlanTests` — `plan(project_dir)` returns the expected
     ordered list of operations for each fixture (adrs-only,
     decisions-misnumbered, already-aligned, conflict).
   - `RenameDryRunTests` — `--dry-run` prints the plan, every line
     prefixed `[dry-run]`, and the tree is byte-identical
     (hash-equal) before and after.
   - `RenameApplyTests` — actual rename on each fixture leaves the
     expected tree; the directory rename, file renames, and
     cross-reference rewrites all happen.
   - `RenamePadTests` — `0001-foo.md` → `adr-0001-foo.md`; existing
     `adr-0001-foo.md` is left alone; `1-bar.md` (1-digit, edge
     case) is left alone and reported as ambiguous (no normalization
     for sub-3-digit prefixes — same rule as 008-01).
   - `RenamePrefixTests` — `0001-foo.md` (no `adr-` prefix) →
     `adr-0001-foo.md`; `adr-001-baz.md` (3-digit, has prefix) →
     `adr-0001-baz.md`.
   - `RenameIdempotencyTests` — apply twice; second invocation prints
     "already aligned" and makes no further changes.
   - `RenameConflictTests` — both dirs present → exit 2, stderr has
     "conflict", tree is unchanged.
   - `RenameCollisionTests` — `0001-foo.md` and `adr-0001-foo.md`
     both in `docs/decisions/` → exit 2 with collision message,
     tree unchanged.
   - `RenameCrossRefTests` — fixture with `docs/architecture.md`
     containing `docs/adrs/0003-thing.md` reference → after run,
     reference reads `docs/decisions/adr-0003-thing.md`. Helper
     file (`migrate.py`) and tests file are NEVER rewritten.
   - `RenameContainmentTests` — `migrate.py rename-decisions` does
     not read or write outside `<project-dir>`. Test sets up a
     fixture with a sibling dir containing matching paths; asserts
     the sibling is untouched.
   - `RenameAtomicityTests` — regex sweep on `migrate.py`: every
     write site goes through `_atomic_write` (i.e. `tmp + os.replace`)
     OR `os.replace` directly for directory renames; no bare
     `Path.write_text` in the rename code path. (The 008-01 read-only
     `SafetyTests` is renamed/relaxed — see §10c below — to allow
     mutating calls inside `rename-decisions` while still forbidding
     them inside the `report` code path.)
   - `RenameErrorTests` — missing dir / non-dir / unreadable → exit
     2. Invalid argument combinations → exit 2 via argparse.
   - `RenameSkillSurfaceTests` — SKILL.md mentions
     `rename-decisions` as available (no longer "deferred"); the
     new trigger phrase appears; the Gotchas section names the
     read-only-except-for-rename caveat.

10. **Out of scope for this slice (each is documented in the
    Operations or Gotchas of SKILL.md and re-flagged here for
    review):**
    - **No `.gitignore` or git tracking awareness.** If a renamed
      file is tracked by git, the user must `git add -A` after the
      rename. The helper does NOT shell out to git. Future slice if
      it bites.
    - **No remote-link rewrites.** Cross-references in markdown
      pointing to GitHub URLs (e.g. `github.com/owner/repo/blob/main/docs/adrs/`)
      are NOT rewritten — those are external surface area and the
      user may have published links that need to keep working.
      Local paths only.
    - **No new test for `report` subcommand's safety regression.**
      The 008-01 `SafetyTests` is relaxed to be code-path-scoped
      (forbid mutations in the `report` path; allow them in the
      `rename-decisions` path). The existing 008-01 ACs continue to
      pass — `report` remains read-only — but the test shape
      changes.

**DoD:**
- [x] All 10 ACs pass; full test suite green (existing + new). **31 new migrate tests on top of 34 existing (65 total in skills/migrate/); 354 total tests across 9 skills; 3 pytest-skipped where runner is unavailable; zero regressions in the other 8 skills.**
- [x] Implementer test coverage exercises real filesystem operations against tempdir fixtures (no mocks). Atomic-write and idempotency are tested by hashing the tree before/after. **Confirmed — `_hash_tree` is used in `RenameDryRunTests.test_dry_run_does_not_mutate_tree`, `RenamePadTests.test_already_canonical_file_left_alone`, `RenameIdempotencyTests.test_second_run_is_noop`, `RenameConflictTests`, `RenameCollisionTests`, and `RenameContainmentTests`.**
- [x] Reviewed by `reviewer` subagent (fresh-context, read-only). Reviewer prompt built by `review.py` (dogfood). **Verdict: `needs-changes` — one real correctness bug (greedy substring corruption of canonical refs in mixed-state trees) + dead code in `_apply_substitutions` + missing regression test. All addressed inline before reconciliation; see §1–§3 below.**
- [x] Deviation log produced under this slice heading. **See below.**
- [x] Reconciliation review pass. **Two passes: first returned `needs-changes` with three precision issues (line-count overstatement in §7, claimed-but-not-captured Gotcha in §4d, line-ref drift in §1) — all addressed inline (see §9a–§9c). Second pass: `pass`.**
- [x] `docs/refinement-todo.md` left untouched (or updated only if a new deferred decision surfaces during implementation — flag it explicitly). **Untouched. The reviewer-flagged edge case "migrate.py copied to a user's project at e.g. `tools/migrate.py` would not self-protect" is logged under §4d as a deliberate non-fix (low likelihood, low severity, no real signal yet) rather than a new deferred decision.**

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition (convention from spec 009 / slice 009-01).

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`. **29 slices across 9 specs; 008-02 row shows DONE.**
- [x] `CLAUDE.md` Active-specs entry for spec 008 updated to reflect 008-02 DONE.

**Anti-horizontal-phasing check:** ✅ End-to-end value in one slice.
A user with a project that uses the pre-ADR-0004 layout
(`docs/adrs/0001-foo.md`) runs `migrate.py rename-decisions . --dry-run`,
reviews the plan, runs it for real → their project is now on the
ADR-0004 canonical shape. No layer-only or plumbing-only phase: the
rename operation is the entire user-facing deliverable.

**Resolution trigger:** Slice 008-01 is DONE (✅ as of 2026-05-12).
The mutator is the obvious next slice and unblocks slice 008-03
(jig-self-migration), where this helper is applied to jig itself.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. Reviewer-flagged correctness bug fixed before reconciliation: greedy-substring corruption of canonical refs.**

The first review pass returned `needs-changes` with a real bug: the
filename substitution loop in `_apply_substitutions` was a literal
`out.replace(old_name, new_name)`. In a mixed-state tree (legacy + canonical
references present in the same file — the natural case for a partially
hand-migrated project, or a self-reference inside a moved ADR), the second
occurrence of the legacy filename matches greedily inside the already-canonical
`adr-NNNN-<slug>.md` string and produces `adr-adr-NNNN-<slug>.md`. Silent
content corruption; not caught by the original test suite because every
fixture used inputs that only contained legacy references.

Fix at [skills/migrate/migrate.py:729](skills/migrate/migrate.py:729) (inside
`_apply_substitutions` defined at [line 704](skills/migrate/migrate.py:704)):
replaced literal `.replace` with `re.compile(r"(?<!adr-)" + re.escape(old_name)).subn(...)`.
The negative lookbehind skips matches preceded by `adr-`, preserving the
canonical reference in place. The substitution-count math (previously
fragile and dead-code-tangled per the reviewer) also collapses to a single
`out.count(old_dir)` plus the subn count; the comment block now explicitly
flags the count as "cosmetic — not load-bearing for correctness."

Regression test added at
[test_migrate.py:test_mixed_canonical_and_legacy_refs_no_corruption](skills/migrate/test_migrate.py:447):
builds a synthetic tree with `docs/architecture.md` containing four
references in a mix of forms (legacy path-prefixed, canonical path-prefixed,
bare legacy filename, bare canonical filename), runs the rename, asserts
`adr-adr-` never appears, asserts the right count of canonical references
ends up in the file. Total test count grew from 64 → 65.

**2. Dead code in `_apply_substitutions` cleaned up.**

Reviewer flagged that lines 712-713 set `count` via length-math that was
then immediately overwritten by 716-719 with both branches doing
`out.count(old_dir)`. Collapsed to `count += out.count(old_dir)` + single
substitution. The comment block now explicitly documents that `count` is
a cosmetic summary, not a correctness gate.

**3. Worktrees-skip path surfaced during validator dogfood.**

The first dry-run against `aso-shallow-validator` returned 323 lines —
because `.claude/worktrees/<branch>/` contains a full parallel checkout
of the validator that the helper happily scanned. Treating a worktree as
in-scope would rewrite a sibling branch's working tree, which is never
what the user wants. Fix at
[skills/migrate/migrate.py:_SKIP_PATH_NAMES](skills/migrate/migrate.py:567):
added `worktrees` to the skip set. Regression test:
`RenameCrossRefTests.test_claude_worktrees_skipped`. After the fix, the
validator dry-run shrinks from 323 → 62 lines (22 file renames + ~38
cross-reference rewrites), which matches the actual in-scope content.

**4. Design choices logged:**

   4a. **`_TEXT_EXTENSIONS` is broader than AC #6 enumerates.** AC #6 lists
   `.md`, `.py`, `.txt`, `.json`, `.yaml`, `.yml`, `.toml`. The implementation
   adds `.cfg`, `.ini`, `.sh`, `.html`, `.css`, `.js`, `.ts`. The reviewer
   flagged this as undocumented expansion. Defensive choice — any of those
   could contain a path mention; nothing in the AC forbade them, and the
   extension list is a hot-path guardrail before the binary-sniff fallback.
   Documented here.

   4b. **`_SKIP_PATH_NAMES` is broader than AC #6 enumerates.** AC #6 lists
   `.git`, `node_modules`, `.venv`, `__pycache__`, `/dist/`, `/build/`. The
   implementation adds `venv`, `.pytest_cache`, `.mypy_cache`, `.tox`,
   `.next`, `.cache`, and the regression-driven `worktrees` (§3). Same
   defensive shape as the extension list. Skipping `.pytest_cache` /
   `.mypy_cache` / `.tox` / `.next` is mechanical (tool-managed dirs that
   contain bytes which decode as text and would otherwise be corrupted).

   4c. **Execution order in `apply_rename` is cross-refs → dir rename → file renames.**
   This is opposite of the display order (dir → files → cross-refs). The
   choice is deliberate: rewriting text content BEFORE moving files keeps
   the recorded `CrossRefRewrite.path` valid at write time — no stale
   `docs/adrs/...` paths escape the planner. The display order is a UX
   choice (most "impactful" change first), not an execution constraint.

   4d. **`_is_helper_or_fixture` is path-anchored to `Path(__file__).resolve().parent`.**
   Reviewer flagged that this only protects files under the live
   `skills/migrate/` path: if a user copies `migrate.py` into their own
   project at e.g. `<project>/tools/migrate.py`, the copy would NOT be
   self-protected. Accepted as a known limitation; low likelihood (the
   intended invocation is `python3 ${CLAUDE_PLUGIN_ROOT}/.../migrate.py
   rename-decisions <project>`, never a copy), low severity (the copy
   only gets touched if it sits inside the `docs/`, `CLAUDE.md`, or
   `.claude/` scope, which is unusual). Captured in `SKILL.md`'s Gotchas
   instead of opening a new refinement-todo entry. Resolution trigger: a
   real report of a self-rewritten copy.

   4e. **Summary-line paths are pre-rename for cross-ref rewrites.**
   Because rewrites execute before the dir/file renames (§4c), the path
   in the summary line is the pre-rename location — e.g. a freshly-
   apply'd run will print `rewrote N cross-references in docs/adrs/0003-foo.md`
   even though the file ends up at `docs/decisions/adr-0003-foo.md`. The
   text content rewrite happened at the displayed path; the rename happened
   afterward. Deterministic and truthful, but worth noting because a user
   greppping the summary for the post-rename path won't find it. Not worth
   path-translating in 008-02; revisit if a real user reports the confusion.

   4f. **The dry-run output's line count for an empty plan is zero — no
   "already aligned" banner.** Only the `is_empty()` branch in
   `rename_decisions()` emits "already aligned: nothing to do\n"; the
   `apply_rename` summary line list is empty when nothing applies. The
   `--dry-run` path on an empty plan reaches the same `is_empty()` branch
   so users see the same "already aligned" message in dry-run too. Tests
   `RenameIdempotencyTests.test_second_run_is_noop` and
   `RenameErrorTests.test_no_adrs_or_decisions_dir_is_exit_zero` cover this.

**5. Validator dogfood transcript (post-fix).**

Invocation:
```
python3 skills/migrate/migrate.py rename-decisions /Users/ramboz/Projects/misc/aso-shallow-validator --dry-run
```

Exit code: `0`. Output: 62 lines. 22 ADR file renames (all 22 numbered ADRs
under `docs/decisions/adr-NNN-*.md` get padded to `adr-NNNN-*.md`); cross-
reference rewrites in 38 files (CLAUDE.md, architecture.md, corpus notes,
spec files, slice files, ADR self-references). The validator already has
`docs/decisions/` (per ADR-0004 alignment), so no directory rename — only
filename padding + cross-ref updates.

No conflicts; no collisions. This output is the input shape slice 008-03
(jig-self-migration) will use against jig itself, modulo the directory
rename (jig has `docs/adrs/`, not `docs/decisions/`).

**6. Self-dogfood (jig-internal --dry-run only).**

```
python3 skills/migrate/migrate.py rename-decisions . --dry-run
```

Produces 17 lines: 1 dir rename + 4 file renames + 12 cross-reference
rewrites. NOT applied in this slice — the actual application against jig
is slice 008-03's mandate, with its own review surface. This is just the
dogfood preview validating that the canonical plan reads sensibly.

**7. Doc updates from this slice:**

- `skills/migrate/migrate.py` — added the mutating code path below the
  `SAFETY_SENTINEL` comment. Final size: **1002 lines** (was 577 at
  slice 008-01 close; net new: ~425 lines).
- `skills/migrate/test_migrate.py` — `SafetyTests` rewritten to be
  region-scoped (read-only-region only); 31 new tests for rename-decisions
  added. Final size: **984 lines** (was 442 at slice 008-01 close; net new:
  ~542 lines).
- `skills/migrate/SKILL.md` — frontmatter description gains one trigger
  phrase; new "Run the rename-decisions migration" subsection; Gotchas
  rewritten to flag the safety-region split, scope bounding, no-git-
  awareness, no-remote-links, AND the helper-self-protection limit
  surfaced in review (the limitation per §4d is captured in the bullet
  starting "**`migrate.py`'s self-protection is path-anchored.**").
- No `architecture.md` changes (helper colocated with its skill — same
  precedent as `scaffold.py` / `memory.py` / `workflow.py` / `review.py` /
  `adr.py` / `tdd.py` / `land.py`).
- No new ADR (ADR-0004 already settled the structural questions; this
  slice operationalizes them).
- No new `_common/` helper. `_atomic_write` is inlined in `migrate.py`
  (second inline copy after `adr.py`'s); the three-caller extraction
  threshold isn't met yet.

**8. Reconciliation discipline note (lesson from spec 009).**

Per spec 009's anti-pattern, the "Reconciliation review pass" DoD
checkbox stays unticked until the reconciliation reviewer returns
`pass`. The status-board regen + CLAUDE.md update boxes live in the
"Close-out (post-DONE)" subsection so they don't false-positive-block
`slice-land`'s DoD check.

**9. Reconciliation-review-flagged precision fixes applied.**

The first reconciliation review verdict was `needs-changes` — three
small but real precision issues in the deviation log itself:

   9a. **Line-count overstatement.** §7 originally claimed `migrate.py`
   grew to ~660 lines; actual is 1002 (52% understated). Test file
   claimed ~875; actual is 984 (~12% understated). Both replaced with
   accurate values; the size growth claim now reads "1002 lines (was
   577 at slice 008-01 close; net new: ~425 lines)" for the helper and
   the analogous correction for the test file.

   9b. **SKILL.md self-protection limit was claimed-but-not-captured.**
   §4d originally said the limit was "Captured in SKILL.md's Gotchas",
   but no bullet named the limitation. Fix: added an explicit Gotcha
   to `skills/migrate/SKILL.md` titled "**`migrate.py`'s self-protection
   is path-anchored.**" §4d's claim is now true.

   9c. **Line-ref drift in §1.** The original `migrate.py:711-718`
   reference pointed at the docstring; the actual lookbehind regex is
   at line 729 inside `_apply_substitutions` (defined at line 704).
   §1 now cites both the function definition and the regex line.

A second reconciliation-review pass would confirm these are addressed.

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
