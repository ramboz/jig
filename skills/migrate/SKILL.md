---
name: migrate
description: >
  Inventory an existing spec-driven project and produce a read-only migration
  report (Inventory / Mapping / Conflicts / Ambiguities / Operations) that
  the user reviews before running mutating migration steps. Use when the
  user says "migrate this project to jig", "adopt jig here", "this repo
  already has specs — set up jig", "scaffold-init refused — what now", or
  "introduce jig to an existing codebase". The helper is read-only; the
  user runs subsequent `migrate.py` subcommands (rename-decisions,
  slice-to-spec, …) themselves once they've reviewed the plan.
user-invocable: true
---

> Spec 008 created this skill from scratch. The deterministic filesystem
> walk + verdict logic + report rendering live in `migrate.py`; this
> SKILL.md drives the judgment layer (when to invoke, how to interpret
> ambiguities, what operations to suggest in what order).

## What this skill does

Closes the "already spec-driven" gap that `scaffold-init` doesn't handle:
projects that organically grew the same workflow jig codifies but landed
on different conventions (folder names, filename prefixes, slice
topology). Direct example: a project with `docs/slices/` (flat) and
`docs/decisions/` (validator-style) — `scaffold-init` would not detect
it as scaffolded and would either refuse confusingly or pollute the
tree.

`migrate` flips that around: detect existing shape first, then propose
a migration plan, then (in later slices) apply the rename / restructure
operations.

For slice 008-01, only the `report` subcommand is implemented. The
helper is **read-only** — it walks the filesystem, reports what it
finds, and suggests what would happen. No mutations.

## How to use

### Run the migration report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/migrate/migrate.py" report \
  <project-dir>
```

- `<project-dir>` — path to the project root (e.g. `/path/to/repo`,
  `.` for cwd).

### Exit codes

- `0` — verdict is `adoptable` OR `not-yet-spec-driven` (the report is
  the deliverable regardless of verdict).
- `1` — verdict is `partial` (borderline; report still emits, but
  `/jig:scaffold-init` may be a better fit).
- `2` — user error (missing argument, dir doesn't exist, target is a
  file not a directory).

### Verdict logic

`migrate` counts four migration triggers in `<project-dir>`:

1. Spec-or-slice dir (`docs/specs/` or `docs/slices/`).
2. Decision-or-ADR dir (`docs/decisions/` or `docs/adrs/`).
3. Workflow doc (`docs/workflow.md`).
4. Architecture doc (`docs/architecture.md`).

| Triggers | Verdict | Recommendation |
|---|---|---|
| 3 or 4 | `adoptable` | Proceed with the suggested operations |
| 2 | `partial` | Borderline — `scaffold-init` may be a better fit |
| 0 or 1 | `not-yet-spec-driven` | Run `/jig:scaffold-init` instead |

### Report structure

Five sections, in fixed order:

1. **Inventory** — table of detected artifacts (paths + counts + shape
   notes). Inventories everything the helper found, including items
   that are inventoried-only (spikes, custom skills, custom agents).
2. **Mapping** — table of "current path/name → jig target name". For
   ADR files this includes the 3-digit-to-4-digit pad and the `adr-`
   prefix add (per ADR-0004). For flat slices, the row points to the
   Ambiguities section because no automated topology mapping exists
   in slice 008-01.
3. **Conflicts** — situations that block specific migration operations
   (e.g. `docs/adrs/` AND `docs/decisions/` both present means
   `rename-decisions` refuses on this project). Empty if no conflicts.
4. **Ambiguities** — judgment calls the user must make. Common entries:
   "flat slices reference M1–M6 milestones — map each to a parent
   spec?"; "custom skills overlap jig's stock set — replace or
   layer?"; "CLAUDE.md is 59KB with sprint log — port subset or
   leave?".
5. **Operations** — ordered list of `migrate.py <subcommand>` calls
   the user should run, with `--dry-run` first. For slice 008-01,
   the only operations mentioned are future subcommands marked
   `(slice 008-NN, not yet implemented)` — so the report's main
   value right now is the first four sections.

## When to invoke

Auto-trigger phrases (in this SKILL.md's description):

- "migrate this project to jig"
- "adopt jig here"
- "this repo already has specs — set up jig"
- "scaffold-init refused — what now"
- "introduce jig to an existing codebase"

Typical session flow:

1. User invokes the skill against an existing project.
2. Helper runs `migrate.py report <dir>`.
3. SKILL.md (this file's body) helps interpret ambiguities: what's a
   real conflict vs. just an open question? What's safe to defer?
4. User makes the judgment calls flagged in Ambiguities.
5. Once future slices land (008-02 `rename-decisions`, 008-04
   `slice-to-spec`), the user runs those operations from the report's
   suggested order, with `--dry-run` first.

## End-to-end example

```bash
# 1. Inventory the project.
python3 .../migrate.py report /path/to/existing-project

# Expected output (when 3+ triggers are present):
#
#   # Migration report — `/path/to/existing-project`
#
#   **Verdict:** adoptable
#
#   _Three or more migration triggers detected. Proceed with the
#   operations below._
#
#   ## Inventory
#
#   | Path | Count | Note |
#   |------|-------|------|
#   | `docs/slices/` | 27 | flat slice files (validator-style) |
#   | `docs/decisions/` | 22 | decision records (ADR-0004 aligned) |
#   | `docs/spikes/` | 4 | spike memos (inventoried only) |
#   | `docs/workflow.md` | 1 | workflow doc present |
#   | `docs/architecture.md` | 1 | architecture doc present |
#   | `CLAUDE.md` | 1 | 59231 bytes (larger than baseline) |
#
#   ## Mapping
#
#   | Current | jig target | Note |
#   |---------|------------|------|
#   | `docs/decisions/` | `docs/decisions/` | kept (already aligned) |
#   | `docs/decisions/adr-001-foo.md` | `docs/decisions/adr-0001-foo.md` |
#       pad to 4-digit + ensure `adr-` prefix |
#   | `docs/slices/slice-NN-*.md` (27 files) | topology question |
#       no automated mapping in 008-01 |
#
#   ## Conflicts
#
#   _None detected._
#
#   ## Ambiguities
#
#   - **Flat slices reference 6 milestone(s) (M1, M2, M3, M4, M5, M6).**
#     Under jig's nested model, each could become a parent spec...
#
#   ## Operations
#
#   Suggested order (each operation is `--dry-run` first):
#
#   1. **`migrate.py rename-decisions <dir>`** (slice 008-02, not yet
#      implemented) — apply ADR-0004 rename...
#   2. **`migrate.py slice-to-spec <dir>`** (slice 008-04, not yet
#      implemented) — interactively map flat slices...
```

## Gotchas

- **`migrate.py` is strictly read-only.** No file creation, no
  renames, no writes, not even directory creation. The `SafetyTests`
  in `test_migrate.py` enforce this via a regex sweep on the source —
  any call to `Path.write_text`, `.rename`, `os.replace`,
  `shutil.move`, `.unlink`, `.mkdir`, or `open(..., "w"/"a"/"x")`
  fails the safety tests. Mutating subcommands graduate into their
  own slices (008-02, 008-04) with their own safety surfaces.
- **The verdict counts trigger directories, not files.** A project
  with 100 ADR files but no workflow.md or architecture.md still
  scores only 1 trigger. The four triggers are about *kinds* of
  artifact, not volume.
- **Flat-slice → nested-spec mapping is deferred.** Slice 008-01's
  Mapping table flags flat slices as a topology question and points
  to slice 008-04. The helper does NOT propose a concrete parent-spec
  grouping — that requires user judgment (or the milestone manifest
  008-04 will accept). For 008-01, the report just names the question.
- **CLAUDE.md size is reported as a tripwire, not migrated.** The
  validator's 59KB CLAUDE.md contains sprint-log content jig's Hot
  Cache doesn't model. The report's Ambiguity row flags it; the user
  decides what to port verbatim, summarize, or leave behind. No
  automation in 008-01 (or any planned 008 slice).
- **Custom skills and agents are inventoried but never migrated.**
  Out of 008's scope by explicit non-goal. The Inventory row lists
  them; the Ambiguity row asks the user how to reconcile.
- **The report scans `docs/` and `.claude/` only.** Other directories
  (e.g. `documentation/`, `proposals/`, `architecture/`) are not
  inspected. A future slice may add `--docs-root` to broaden the
  scan — for 008-01, projects with non-standard layouts get a
  `not-yet-spec-driven` verdict and a recommendation to either
  rename their dirs or use `/jig:scaffold-init`.
- **Spikes are inventoried but not migrated.** jig has no
  spike-workflow skill yet (separate gap; tracked in inbox/refinement
  -todo). The Ambiguity section notes the count and recommends
  keeping `docs/spikes/` as-is.

## Relationship to other skills

- **`scaffold-init`** is the greenfield counterpart. `migrate` is for
  existing projects; `scaffold-init` is for blank slates. Slice 008-05
  (deferred) will teach `scaffold-init` to detect validator-style
  layout and suggest `/jig:migrate` instead of refusing opaquely.
- **`adr-workflow`** depends on `docs/decisions/` matching ADR-0004's
  layout. `migrate.py rename-decisions` (slice 008-02, deferred) will
  produce that layout from a `docs/adrs/` source. Until then, projects
  already on the legacy layout can run `adr-workflow` against
  `docs/adrs/` directly via the helper's path-tolerance (open question
  in ADR-0004 §"Backwards compatibility window for `adr.py`").
- **`spec-workflow`** assumes nested specs (`docs/specs/NNN-*/spec.md`).
  Projects with flat slices need `migrate.py slice-to-spec` (slice
  008-04, deferred) before `spec-workflow` operations can target them
  the way they target jig's own specs.
- **`slice-land`** is orthogonal — it operates on whatever shape the
  project ends up with after migration. No direct coupling.

## Out of scope for slice 008-01

- Any filesystem mutation. The `report` subcommand is read-only by
  design; mutating operations land in slices 008-02 (rename-decisions),
  008-03 (jig-self-migration via 008-02's helper), 008-04
  (slice-to-spec-mapping), 008-05 (scaffold-init suggestion wiring).
- Importing CLAUDE.md content into jig's Hot Cache template.
  Inventoried only; the user ports manually.
- Cross-format ADR template conversion (MADR, Y-statements, etc.).
  ADR-0004 just covers path/filename rename.
- JIRA / Linear / Asana milestone-to-ticket mapping.
- Custom-skill / custom-agent migration.
- Roundtripping (post-migration rollback). The user keeps the
  pre-migration commit as their rollback.
- Multi-project batch migration. One project at a time.
