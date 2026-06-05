---
name: migrate
description: >
  Inventory an existing spec-driven project (read-only report) and apply
  bounded migration operations to bring it under jig's defaults. Slice
  008-01 added `report`; slice 008-02 added `rename-decisions` (apply
  ADR-0004's `docs/adrs/` → `docs/decisions/` rename + filename shape).
  Slice 018-04 added `split-slices` (extract `## Slice` sections out of
  spec.md into sibling slice files). Slice 020-01 added an agentic
  slice-to-spec migration workflow — judgment-driven, no helper — for
  projects with flat `docs/slices/*.md` files that need to be grouped
  into nested `docs/specs/MNN-slug/slice-NN-*.md` form. Slice 021-01
  added `copy-machinery` (copy jig's skills + agents + hooks into the
  target's host-local runtime, reusing scaffold-mode's helpers). Use
  when the user says "migrate this project to jig",
  "adopt jig here", "this repo already has specs — set up jig",
  "scaffold-init refused — what now", "introduce jig to an existing
  codebase", "apply ADR-0004 to my project", "migrate flat slices into
  nested specs", or "copy jig's machinery into my project". The report
  is read-only; mutating subcommands have a `--dry-run` mode (where
  available) and refuse on conflict before any write; the agentic
  slice-to-spec workflow never deletes originals (caller decides when
  to clean up).
user-invocable: true
---

> Codex adapter note: `rename-decisions` and `copy-machinery` are host-aware. Use `--host codex` when running them from Codex-facing docs or source checkouts; helpers copied under `.codex/skills/` infer Codex by default.

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

`migrate.py` exposes four subcommands:

- `report` — strictly read-only inventory + plan.
- `rename-decisions` — applies ADR-0004's rename. Idempotent; refuses on conflict; has a `--dry-run` mode; use `--host codex` when running from Codex-facing source or plugin paths.
- `split-slices` — extracts embedded slice sections into sibling slice files.
- `copy-machinery` — copies jig runtime machinery into the target's Codex scaffold runtime under `.codex/`; use `--host codex` from source or plugin paths.

## How to use

### Run the migration report

```bash
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" report \
  <project-dir>
```

- `<project-dir>` — path to the project root (e.g. `/path/to/repo`,
  `.` for cwd).

### Run the rename-decisions migration

Once `report` has been reviewed and the verdict is `adoptable`, the
recommended sequence is:

```bash
# 1. Preview the plan (no writes).
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" \
  rename-decisions <project-dir> --host codex --dry-run

# 2. After reviewing the planned operations, apply them.
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" \
  rename-decisions <project-dir> --host codex
```

What it does, in display order:

1. `docs/adrs/` → `docs/decisions/` (directory rename, atomic).
2. Per-file renames: `NNN-<slug>.md` → `adr-NNNN-<slug>.md`
   (pad 3-digit to 4-digit; add `adr-` prefix where missing).
3. Cross-reference rewrites in text files under `docs/`, `AGENTS.md`,
   and `.codex/` by default. With `--host codex`, rewrites scan
   `docs/`, `AGENTS.md`, and `.codex/` instead. The helper itself
   (`migrate.py` and its fixtures) is never rewritten.

Refusal cases (exit 2, no mutations):

- Both `docs/adrs/` and `docs/decisions/` present (manual merge first).
- Two source files normalize to the same target name (collision).
- `<project-dir>` missing, not a directory, or unreadable.

No-op cases (exit 0):

- Neither dir present, OR all files already on the canonical shape —
  emits "already aligned: nothing to do" and returns.

### Run the copy-machinery operation

`copy-machinery` brings a migrated project to scaffold-mode parity —
the same host-local runtime shape `/jig:scaffold-init` produces by
default for greenfield projects. See the dedicated section
[`## Copying machinery into your project`](#copying-machinery-into-your-project)
below for the full description.

Quick reference:

```bash
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" \
  copy-machinery <project-dir> --host codex
```

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

Six sections, in fixed order:

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
   layer?"; "AGENTS.md is 59KB with sprint log — port subset or
   leave?".
5. **Contract surfaces detected** — *(added by spec 022-02)* flags
   external-interface artifacts already on disk and prose API contracts
   that would benefit from standard schemas (OpenAPI / JSON Schema /
   AsyncAPI / `.proto` / GraphQL SDL). Four detection types: (a)
   existing schema artifacts, (b) prose API contracts in canonical
   doc files, (c) env-contract triple (markdown + `.env.example` +
   checker), (d) hand-typed boundary types (e.g.
   `problem-details.ts`). Each detected surface gets a one-line
   classification + recommendation; "No contract surfaces detected"
   prose when empty. Companion to the `/jig:contracts` skill's
   per-surface recommendation table.
6. **Operations** — ordered list of `migrate.py <subcommand>` calls
   the user should run, with `--dry-run` first. For slice 008-01,
   the only operations mentioned are future subcommands marked
   `(slice 008-NN, not yet implemented)` — so the report's main
   value right now is the first five sections.

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
#   | `AGENTS.md` | 1 | 59231 bytes (larger than baseline) |
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

## Copying machinery into your project

`copy-machinery` brings a migrated project to scaffold-mode parity —
the same host-local runtime shape `/jig:scaffold-init` produces by
default for greenfield projects. After running it, the project owns its
own copy of jig's skills, agents, hook scripts, and hook registration.
The dev can edit those files in their own repo, and they ride along
under version control.

When to use it:

- **After `rename-decisions`** has applied ADR-0004 to existing ADRs.
- **After `split-slices`** has split any monolithic `spec.md` files
  with embedded slices into the file-per-slice layout.
- **Standalone**, when a project already has spec-driven layout but
  the dev wants the machinery in their tree (rather than only in the
  installed plugin under `${PLUGIN_ROOT}`).

`migrate.py report` will surface this subcommand in the Operations
section when the verdict is `adoptable` or `partial` and the default
host scan does not find pre-existing jig-managed skills. Codex users can
also run the explicit `copy-machinery --host codex` command when they
want Codex runtime machinery even if the conservative report wording is
not the deciding signal.

Host selection:

- Use `--host codex` when invoking from Codex-facing source or plugin docs.
- `--host auto` infers Codex only when this helper itself runs under `.codex/skills/`; from source or plugin paths, pass `--host codex` explicitly.

How to run it:

```bash
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" \
  copy-machinery <project-dir> --host codex
```

What it does:

1. Copies Codex skills into `.codex/skills/jig-<name>/`, rewriting helper paths in SKILL.md bodies to that runtime.
2. Copies non-discoverable helper aliases under `.codex/skills/<name>/` so peer helper imports continue to resolve without duplicate discoverable skills.
3. Copies Codex agents into `.codex/agents/jig-*.toml`.
4. Copies hook scripts into `.codex/hooks/scripts/`, pinning each script's mode to `0o755`.
5. Generates or merges Codex hook registration in `.codex/hooks.json`, with a top-level jig-managed metadata marker.

Subsequent runs are idempotent: re-running `copy-machinery` overwrites copied runtime files in place and regenerates jig-managed `.codex/hooks.json` as a whole.

### Refusal: unmanaged hooks

If `.codex/hooks.json` already exists without top-level `metadata.managed_by_jig: true`, `copy-machinery` exits non-zero (exit code 3) and emits the `UnmanagedHooksError` refuse-message to stderr — no filesystem writes occur. This matches the same safety stance `scaffold-init` enforces.

The documented escape is `--force`:

```bash
python3 "${PLUGIN_ROOT}/skills/migrate/migrate.py" \
  copy-machinery <project-dir> --host codex --force
```

With `--force`, Codex replaces an unmanaged `.codex/hooks.json` with jig's generated hook registration. Use this only when you are sure the existing hook config should be replaced or has been backed up.

### Relationship to scaffold-mode

`migrate.py copy-machinery` is the migration-path equivalent of
`scaffold-init --with-machinery` (default since slice 016-03). Both
end up calling the same host-aware `copy_machinery(plugin, target, *,
force, host)` façade in `scaffold.py`, so the resulting host runtime
shape is equivalent regardless of which adoption path produced it.
Closing this gap for Codex was spec 021's reason for being; spec 059-01
extends the same adoption path to Codex.

## Agentic slice-to-spec migration

For projects where `migrate.py report` returns **Verdict: adoptable**
AND the inventory shows flat slice files under `docs/slices/` rather
than nested `docs/specs/NNN-slug/spec.md` form, there is no
deterministic helper to do the grouping (slice 008-04 was deferred
deliberately — see Non-goals on spec 020). Instead, the LLM driving
the migration follows the algorithm below. Output is a new
`docs/specs/` tree; originals stay where they are until the caller
verifies and chooses to clean up.

### When to invoke

After `migrate.py rename-decisions` (so ADR filenames are jig-shaped),
when the report's Ambiguities section names
**"Flat slices reference N milestone(s)"** or similar. The follow-up
is this agentic workflow. Do NOT run it if specs already live under
`docs/specs/NNN-slug/spec.md` — that's already the jig shape.

### Algorithm

For each migration, in order:

1. **Read milestone summaries.** Walk
   `docs/milestones/*.md` (or whatever the source's milestone-doc
   convention is). For each milestone, capture the title, scope,
   and slice list. These become the basis for spec naming.
2. **Decide milestone → spec mapping.** Each milestone becomes one
   spec folder. Naming convention:
   `docs/specs/NNN-mM-<title-slug>/` where:
   - `NNN` is a 3-digit spec number (start at 001, ascend per
     milestone order — match the project's chronology when
     possible);
   - `mM` is the milestone tag lowercased (e.g. `m1`, `m4.5`);
   - `<title-slug>` is a slug of the milestone's headline
     ("EDS thin E2E" → `eds-thin-e2e`).
   Skip milestones that have no slices.
3. **For each source slice file:**
   1. Read its body. Locate the milestone tag (prose
      `- **Milestone:** M1`, frontmatter `milestone: M1`, or
      filename prefix — adapt to what the source uses).
   2. Locate its status. The source's vocabulary is usually
      4-state — translate per the table below.
   3. Locate the heading. Source shape is usually
      `# Slice NN — Title` (H1, single number, no spec prefix).
      Transform to `## Slice NNN-NN — <slug-of-title>` (H2, jig
      spec-slice fragment, slug-form title). Use the target spec's
      `NNN` from step 2 and the original slice number for the
      second `NN`.
   4. Prepend a frontmatter block (frontmatter shape per spec 015
      + 018):
      ```
      ---
      status: <translated-status>
      dependencies: []
      last_verified:
      ---
      ```
      Leave `dependencies: []` for now — backfilling structured
      deps from prose "Depends on" lines is per-slice judgment
      work, not bulk-migration scope.
   5. Preserve the original slice body verbatim AFTER the new
      heading (Status / Milestone / Depends on / Estimated size
      prose lines included — they're harmless trailing context).
4. **Write new files** under
   `docs/specs/NNN-mM-<title-slug>/`:
   - `spec.md` synthesized from the milestone summary (header +
     overview + `## Decomposition` + `## Slices` link list).
   - One `slice-NN-<original-shortname>.md` per source slice. Keep
     the original filename's shortname (no re-slugging) so existing
     cross-references resolve.
5. **Do NOT delete originals.** The source `docs/slices/` and
   milestone summaries stay in place. Caller decides when to
   clean up after verifying.
6. **Verify with jig helpers.** Run the following against the new
   spec dir and confirm clean output:
   ```bash
   # All slices resolvable
   python3 -c "import sys; sys.path.insert(0, 'skills/_common'); \
     from parsing import iter_slices; \
     [print(l.label) for l in iter_slices('docs/specs/NNN-mM-slug/spec.md')]"

   # Lint walks all slices, no AC contradictions
   python3 scripts/spec_lint.py docs/specs/NNN-mM-slug/spec.md

   # Status board generates the table
   python3 skills/spec-workflow/workflow.py status-board <project-dir>
   ```
   `land.py prepare --no-deviation-log` (slice 019-01) lands
   without complaining about absent deviation logs on pre-jig
   DONE slices.

### State translation

| Source (4-state)   | Jig (7-state)               | Notes                                                                 |
|--------------------|-----------------------------|-----------------------------------------------------------------------|
| `Draft`            | `DRAFT`                     | Direct.                                                               |
| `Ready`            | `READY_FOR_IMPLEMENTATION`  | "Ready" in 4-state means "ready to start work" — NOT "ready for spec review." Map past READY_FOR_REVIEW. |
| `In Progress`      | `IN_PROGRESS`               | Direct.                                                               |
| `Done`             | `DONE`                      | Direct.                                                               |
| `Deferred` (rare)  | `DEFERRED` (spec 014)       | If the source uses a Deferred state with a resolution trigger.        |

`REVIEWED` and `RECONCILED` are intermediate gates the source never
had. Pre-jig slices that landed under the old lifecycle skip those
gates by definition — the auto-tick on jig's REVIEWED→RECONCILED
transitions doesn't fire for them and shouldn't. Use spec 019's
`--no-deviation-log` flag when landing these retroactively.

### Worked example

The shallow-validator M1 dogfood (2026-05-15) is the canonical
reference. See
[`worked-example-slice-to-spec.md`](worked-example-slice-to-spec.md)
for the source → target before/after, status-board output, and
verification report.

### Limitations

- **No backfill of `dependencies:`.** Prose "Depends on" lines stay
  in the slice body; the frontmatter `dependencies: []` is empty.
  Future slices can populate them per-slice.
- **No backfill of `### Deviation log`.** Pre-jig slices never had
  one. Use `land.py prepare --no-deviation-log` to land them
  retroactively (spec 019-01).
- **Originals NOT deleted.** Caller decides post-verification.
- **No status-vocabulary auto-detection.** The 4-state vocabulary
  above is the most common, but adapt to what the source actually
  uses (e.g., "In Review" might map to `IN_PROGRESS` or `REVIEWED`
  depending on context).
- **AGENTS.md references to old slice paths are NOT rewritten.**
  Cross-references like `[slice-01](docs/slices/slice-01.md)` in
  AGENTS.md / milestone summaries / etc. keep pointing at the
  original files. After the caller deletes originals, those refs
  must be updated by hand or via a follow-up
  `migrate.py rename-decisions`-style sweep (out of scope here).

## Gotchas

- **`migrate.py report` is read-only; migration operations are bounded
  mutators.** The first mutating region was introduced by
  `rename-decisions` and remains protected by the sentinel comment
  (`# ---------- BEGIN MUTATING CODE PATH (rename-decisions) ----------`);
  later mutators (`split-slices`, `copy-machinery`) have their own
  command-specific preflights and tests. The `report` subcommand stays
  pure-read.
- **`rename-decisions` is bounded by `<project-dir>`.** It never reads or writes outside the directory passed on the CLI. With `--host codex`, it scans shared `docs/` plus `AGENTS.md` and `.codex/`. Well-known skip paths (`.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, etc.) are excluded from cross-reference scanning.
- **Always `--dry-run` first.** Even with idempotency and refusal
  on conflict, the plan output is the canonical preview surface.
  Two consecutive `--dry-run` invocations produce byte-identical
  output (AC #7), which is also how the test suite verifies stability.
- **Remote links (GitHub URLs) are NOT rewritten.** `docs/adrs/`
  paths inside `https://github.com/.../docs/adrs/...` URLs stay
  untouched — external surface area the user may have published.
  Only local paths are rewritten.
- **No git awareness.** `rename-decisions` performs filesystem
  renames; if the project is a git repo, the user must `git add -A`
  to record the renames as tracked changes. Future slice if it bites.
- **`migrate.py`'s self-protection is path-anchored.** The helper
  refuses to rewrite files under its own `skills/migrate/` directory
  (so the canonical regexes + fixtures never get mangled by the
  helper running on its own repo). If a user copies `migrate.py`
  into their own project at e.g. `<project>/tools/migrate.py`, the
  copy is NOT covered by the self-protection — it would be rewritten
  like any other text file in scope. Invoke `migrate.py` from the
  installed plugin path (`${PLUGIN_ROOT}/skills/migrate/migrate.py`),
  never a copied-in-tree version, to keep the guarantee.
- **The verdict counts trigger directories, not files.** A project
  with 100 ADR files but no workflow.md or architecture.md still
  scores only 1 trigger. The four triggers are about *kinds* of
  artifact, not volume.
- **Flat-slice → nested-spec mapping is deferred.** Slice 008-01's
  Mapping table flags flat slices as a topology question and points
  to slice 008-04. The helper does NOT propose a concrete parent-spec
  grouping — that requires user judgment (or the milestone manifest
  008-04 will accept). For 008-01, the report just names the question.
- **AGENTS.md size is reported as a tripwire, not migrated.** The
  validator's 59KB AGENTS.md contains sprint-log content jig's Hot
  Cache doesn't model. The report's Ambiguity row flags it; the user
  decides what to port verbatim, summarize, or leave behind. No
  automation in 008-01 (or any planned 008 slice).
- **Custom skills and agents are inventoried but never migrated.**
  Out of 008's scope by explicit non-goal. The Inventory row lists
  them; the Ambiguity row asks the user how to reconcile.
- **The report scans jig's canonical docs shape only.** Other
  directories (e.g. `documentation/`, `proposals/`, `architecture/`) are
  not inspected. A future slice may add `--docs-root` to broaden the
  scan — for 008-01, projects with non-standard layouts get a
  `not-yet-spec-driven` verdict and a recommendation to either rename
  their dirs or use `/jig:scaffold-init`.
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
- Importing AGENTS.md content into jig's Hot Cache template.
  Inventoried only; the user ports manually.
- Cross-format ADR template conversion (MADR, Y-statements, etc.).
  ADR-0004 just covers path/filename rename.
- JIRA / Linear / Asana milestone-to-ticket mapping.
- Custom-skill / custom-agent migration.
- Roundtripping (post-migration rollback). The user keeps the
  pre-migration commit as their rollback.
- Multi-project batch migration. One project at a time.
