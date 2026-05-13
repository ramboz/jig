# ADR-0004: Rename docs/adrs/ to docs/decisions/ and prefix files with adr-

## Status

Accepted (2026-05-12)

## Context

jig's default ADR layout is `docs/adrs/NNNN-<slug>.md`, which is internally
consistent and matches Nygard's original blog post but has two usability gaps
that surfaced while dogfooding jig against the aso-shallow-validator project —
a mature spec-driven repo that organically grew the same workflow jig codifies
but landed on a different naming convention (`docs/decisions/adr-NNN-<slug>.md`).

**Gap 1 — "ADR" is jargon at the directory level.**
A new contributor opening a repo sees a top-level `docs/adrs/` folder and has
to already know what an ADR is to recognize it as the decisions log. The
validator uses `docs/decisions/`, which reads as plain English: a folder of
decisions. The jargon belongs *inside* the file (where the reader is already
opening a specific record), not on the folder.

**Gap 2 — bare-number filenames lose self-documentation when surfaced out of
context.**
A search-result hit on `0003-extract-find-slice-section.md` or a link rendered
in a different tool (issue tracker, wiki) loses the signal that this file is
an ADR vs. some other record type. The validator's `adr-NNN-<slug>.md`
form survives that context loss: `adr-003-monkey-patch-via-cdp.md` is
self-identifying anywhere it appears.

The cost of changing now is bounded: jig has three ADRs and one scaffolded
project (the validator we're about to migrate is not yet on jig). After spec
008 lands and real users adopt jig, the same change costs more.

This decision is **about jig's defaults**, not about forbidding the old
convention. Existing projects that adopted `docs/adrs/` shouldn't be forced
to migrate; the `--migrate` flow (spec 008) will read both layouts.

## Decision Options Considered

### Option A: Rename folder to `docs/decisions/`, keep bare-number filenames

- **Pros:**
  - Addresses the "jargon at the folder level" gap (the bigger of the two).
  - Smaller surface change: only the directory rename, no per-file rename.
  - Filename format stays compatible with most ADR tooling in the wild.
- **Cons:**
  - Gap 2 (self-documenting filenames) is unaddressed. A file URL pasted
    into a JIRA ticket still reads as `0003-extract-...md` with no type hint.
  - Half-measures invite "why didn't you just go all the way?" follow-ups.

### Option B: Rename folder to `docs/decisions/` AND prefix files with `adr-`

- **Pros:**
  - Closes both gaps in a single change.
  - Filename is explicit about the record type it follows
    (`adr-NNNN-<slug>.md`), independent of its directory.
  - Matches the validator's existing convention, which is a small signal
    that the convention survives real-world use.
  - The `adr-` prefix leaves room for sibling record types in the same
    folder later (e.g. `decision-log-NNNN-...` if a lighter-weight log
    format is introduced) without renaming.
- **Cons:**
  - Bigger surface change: `adr.py` regex, templates, README index format,
    auto-numbering glob, all need updating.
  - One more migration step for any future user who adopted the existing
    jig defaults.

### Option C: Keep `docs/adrs/` and bare-number filenames

- **Pros:**
  - No migration cost; no scaffold change.
  - Matches the strictest reading of Nygard's original post.
- **Cons:**
  - Locks in the jargon-at-folder-level usability friction permanently.
  - Adoption studies (n=1, the validator) suggest experienced practitioners
    don't actually land on this convention when they have the choice.
  - The fix gets more expensive after each new user.

### Option D: Make folder name configurable

- **Pros:**
  - Defers the choice to each project.
  - No default migration cost.
- **Cons:**
  - Adds a configuration surface jig doesn't otherwise need.
  - Spec 008 (`--migrate`) still has to handle both shapes, so the
    "configurability" doesn't actually reduce code complexity downstream.
  - Defaults matter — most projects will accept whatever ships, so picking
    a default still has to happen.

## Recommended Decision

**Option B.** Rename `docs/adrs/` → `docs/decisions/` as jig's default, and
prefix files with `adr-` to produce `docs/decisions/adr-NNNN-<slug>.md`.

The half-measure (Option A) leaves the second gap in place for a marginal
implementation saving; if the rename is happening anyway, do both in one
swing. Option D over-engineers a defaults question.

This is a decision about defaults. Spec 008's `--migrate` skill must read
both the old (`docs/adrs/NNNN-<slug>.md`) and new (`docs/decisions/adr-NNNN-<slug>.md`)
shapes; nothing in this ADR forbids either layout downstream.

## Consequences

**Becomes easier:**

- New contributors recognize the decision log from the folder name without
  prior context.
- Filenames are self-identifying when copied into other tools (JIRA, wiki,
  Slack, search results).
- Sibling record types can join `docs/decisions/` later without folder
  conflicts.
- Migrating projects that already use the validator-style convention is a
  no-op rather than a rename — broadens jig's "feels native" footprint.

**Becomes harder:**

- One-time migration cost inside the jig repo: rename `docs/adrs/` →
  `docs/decisions/`, rename three existing ADR files to `adr-NNNN-*.md`,
  update every cross-reference in the repo (CLAUDE.md, README, specs,
  skill docs, templates).
- `adr.py` needs updating: default `--dir` argument, glob pattern for
  auto-numbering, filename construction in `new`, index regeneration.
- Templates in `templates/docs/adrs/` need renaming and content updates.
- Any documentation snippet that says "ADRs live in `docs/adrs/`" needs to
  flip to "`docs/decisions/`".

**Implementation status:**

Not yet implemented. This ADR records the *decision*; the implementation
will be tracked as a follow-up slice (probably a small dedicated spec, or
folded into spec 008 if scope and ordering allow). The migration touches:

1. Physical rename of `docs/adrs/` → `docs/decisions/` in the jig repo.
2. Per-file rename to `adr-NNNN-<slug>.md`.
3. `skills/adr-workflow/adr.py`: directory default, filename pattern,
   numbering glob, index path.
4. `skills/adr-workflow/test_adr.py`: fixture paths and assertions.
5. `templates/docs/adrs/` → `templates/docs/decisions/`, plus template
   content updates.
6. `skills/scaffold-init/scaffold.py`: target directory creation.
7. Cross-references in `CLAUDE.md`, `docs/architecture.md`, every spec
   that cites an ADR, every skill doc that mentions `docs/adrs/`.
8. `docs/specs/README.md` and any spec-status notes referencing ADRs.

**Resolution trigger for revisiting:**

- If real users on jig report friction with `docs/decisions/` (e.g.
  conflicts with another tool that expects `docs/adrs/`), the folder name
  can be revisited via supersession.
- If a sibling record type lands in `docs/decisions/`, the `adr-` prefix
  is validated; if no sibling has emerged after, say, 12 months of real
  use, consider whether the prefix is paying its keep.

## Open questions

- **Scope of the implementation slice.** Should the rename land as its own
  small spec (e.g. spec 008.5 or spec 009), or as a slice inside spec 008's
  `--migrate` work? Argument for own spec: it's a self-contained mechanical
  change with no real design content. Argument for folding in: spec 008
  already has to teach `--migrate` to read both shapes, so the codepath
  exists either way. Defer until spec 008 is drafted.
- **Backwards compatibility window for `adr.py`.** Should `adr.py` continue
  reading `docs/adrs/` when present (logging a deprecation), or require an
  explicit `--dir docs/adrs` flag? Lean toward "read both silently"; revisit
  if it becomes a maintenance burden.
