# Plan: Slice 008-01 — migrate-report

> Plan is DRAFT alongside the spec. Refresh when slice 008-01 transitions
> to IN_PROGRESS.

## Approach

Same shape as `workflow.py` / `review.py` / `adr.py` / `tdd.py` / `land.py`:
deterministic Python 3 helper, SKILL.md drives the judgment layer.

The helper performs a read-only filesystem walk of `<project-dir>` and
emits a five-section markdown report. It MUST NOT mutate filesystem
state — enforced by the `SafetyTests` regex sweep on the source.

## `migrate.py` CLI surface (slice 008-01)

```bash
python3 migrate.py report <project-dir>
```

Future subcommands (deferred to later slices):

```bash
python3 migrate.py rename-decisions <project-dir> [--dry-run]   # slice 008-02
python3 migrate.py slice-to-spec <project-dir> [--manifest path] # slice 008-04
```

Report goes to stdout; exit codes documented in spec AC #3. No
options beyond the positional `<project-dir>` argument for 008-01.

## Detection logic

Five things to detect:

1. **Spec/slice dirs.** Glob: `docs/specs/*/spec.md`, `docs/slices/slice-*.md`.
   The two are mutually informative — both present is unusual; flag in
   Ambiguities.
2. **Decision dirs.** Glob: `docs/adrs/*.md`, `docs/decisions/*.md`.
   Both present → Conflict.
3. **Spike dirs.** Glob: `docs/spikes/*.md`. Optional; inventoried,
   not migrated by 008-01.
4. **Doc landmarks.** `docs/workflow.md`, `docs/architecture.md`,
   `docs/product-vision.md`. Each present/absent.
5. **Custom assets.** `.claude/skills/*.md`, `.claude/agents/*.md`.
   Inventoried with names; not migrated.

The verdict logic counts the four migration-relevant triggers
(spec-or-slice dir, decision dir, workflow doc, architecture doc) and
maps to `adoptable | partial | not-yet-spec-driven` per spec AC #2.

## Mapping table construction

For each detected item, produce a mapping row. Cases:

- `docs/adrs/` present → row maps to `docs/decisions/`.
- `docs/adrs/0001-foo.md` → row maps to `docs/decisions/adr-0001-foo.md`.
- `docs/decisions/adr-001-foo.md` (validator style — already has prefix) →
  row maps to `docs/decisions/adr-0001-foo.md` (pad 3-digit to 4).
- `docs/decisions/` present without `docs/adrs/` → row notes "kept".
- `docs/slices/slice-NN-name.md` → row notes "topology question — see
  Ambiguities (slice 008-04)". No automated mapping for 008-01.
- `docs/specs/NNN-name/` present → row notes "already nested — kept".

## Conflict detection

The single sharpest conflict for 008-01: both `docs/decisions/` AND
`docs/decisions/` present with overlapping filenames (or near-misses
like `0001-foo.md` in one and `adr-0001-foo.md` in the other).
Report names each colliding pair under Conflicts.

Other conflicts that block migration:
- CLAUDE.md contains markers from a different scaffolder (e.g.
  cookiecutter, copier templates). Pattern: regex for known marker
  strings.
- `.claude/skills/<name>.md` already exists for a jig stock skill
  name. Flag as conflict only if the existing skill differs from
  jig's; otherwise inventoried as "already aligned".

## Fixture strategy

`skills/migrate/fixtures/` contains a tiny validator-shaped tree:

```
fixtures/
├── tiny-validator/
│   ├── CLAUDE.md
│   ├── docs/
│   │   ├── workflow.md
│   │   ├── architecture.md
│   │   ├── decisions/
│   │   │   ├── adr-001-foo.md
│   │   │   └── adr-002-bar.md
│   │   ├── slices/
│   │   │   ├── slice-01-thing.md
│   │   │   └── slice-02-other.md
│   │   └── spikes/
│   │       └── spike-01-investigation.md
│   └── .claude/
│       └── skills/
│           └── custom-skill.md
├── greenfield/         # zero triggers
│   └── README.md
├── partial/            # two triggers
│   ├── docs/
│   │   ├── workflow.md
│   │   └── architecture.md
└── conflict/           # both docs/adrs/ and docs/decisions/
    └── docs/
        ├── adrs/
        │   └── 0001-foo.md
        └── decisions/
            └── adr-0001-foo.md
```

Fixtures live in-tree so tests are hermetic. The real validator at
`/Users/ramboz/Projects/misc/aso-shallow-validator/` is exercised
only in `DogfoodTests` (gated on path existence) and at slice closure
per AC #7.

## SKILL.md

Active frontmatter. Description trigger phrases listed in spec AC #5.
Body documents `migrate.py report` and forward-references slices
008-02 through 008-05 as "Coming in slice 008-NN".

Decision deferred to plan refinement: does this SKILL.md sit at
`skills/migrate/SKILL.md` (new sibling to `scaffold-init/`), or is
it folded into `scaffold-init/`'s SKILL.md as a Q-and-A branch? My
lean: separate skill. Different mechanics (read-only walk vs.
template copy), different user mental model ("I have existing
work" vs. "I'm starting fresh"). The cross-link from scaffold-init
to migrate lives in slice 008-05.

## Risks

- **Detection breadth.** The four-trigger heuristic might miss
  spec-driven projects that use non-conventional paths
  (e.g. `documentation/` instead of `docs/`). Slice 008-01 only
  checks `docs/`; a follow-up could accept a `--docs-root` flag.
  Acceptable for 008-01.
- **Report verbosity.** A mature project (validator: 27 slices,
  22 ADRs) produces a long report. Section truncation deferred —
  the report is meant to be consumed once. Mitigation: each section
  is independently scrollable in markdown viewers.
- **Validator drift.** The dogfood asserts `verdict == adoptable`
  against the validator. If the validator's structure changes
  after this slice lands, the assertion is wrong — but it's gated
  on the validator path existing, and run only at slice closure
  (not in CI). Acceptable.
