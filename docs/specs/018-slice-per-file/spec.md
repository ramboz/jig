---
status: DRAFT
skill: spec-workflow
tier: 1
---

# Spec 018: slice-per-file

## Overview

Each slice becomes its own file on disk — `docs/specs/NNN-slug/slice-NN-shortname.md`
— instead of a `## Slice NNN-MM — shortname` section inside one
monolithic `spec.md`. The parent `spec.md` keeps the spec-level
frontmatter, overview, goals, non-goals, and decomposition rationale;
slice bodies move out.

Spec 015 already standardized per-slice frontmatter (`status`,
`dependencies`, `last_verified`) as a `--- ... ---` block immediately
after the `## Slice` heading. That frontmatter shape carries over to
the file-per-slice layout unchanged — what changes is *where the block
lives*, not *what's in it*. This spec is therefore additive on top of
015, not a re-design.

## Why now

- **Monolithic spec files are at the size where they hurt.** Recent
  specs are 400–700 lines. A single slice's close-out (status-board
  regen, CLAUDE.md edits, deviation log) requires editing the same
  file that other slices are still in flight inside. The reconciliation
  pass for slice 008-03 took **four** review rounds, partly because
  diffs across adjacent slice blocks collapsed bidirectionally — a
  class of bug spec 015 partly addressed with structured dependencies,
  but only partly.
- **PR scoping is wrong-shaped.** A PR landing one slice currently
  diffs the whole spec.md (every other slice's text is part of the
  change-set context). With file-per-slice, the PR diff is
  `spec.md` (small header tweak) + one `slice-NN-*.md`. Reviewers see
  what they need.
- **Helpers already pay the cost of section-walking.** `workflow.py
  find_slice_section`, `land.py find_slice_section`, `review.py`,
  `spec_lint.py`, and `migrate.py rename-decisions` all locate slices
  by scanning `## Slice` headers. A file-based locator is simpler:
  read `slice-NN-*.md` directly. Section-walking stays as the legacy
  fallback for existing specs.
- **Aligns jig with downstream projects that already do this.**
  aso-shallow-validator (the primary external consumer that motivated
  this re-evaluation) keeps each slice in its own `slice-NN.md` file
  under `docs/slices/`. Adopting the same shape removes one of the
  three blocking migration deltas identified in the gap analysis;
  the other two (state vocabulary, milestone grouping) are independent.

## Goals

1. **New specs are file-per-slice from creation.** `workflow.py new`
   produces `docs/specs/NNN-slug/spec.md` (header + overview) and
   subsequent slices land as sibling `slice-NN-shortname.md` files.
2. **Existing specs continue to work unchanged.** Every helper that
   currently locates slices by scanning `## Slice` headers does so
   via a single shared helper (`_common.parsing.find_slice_section`).
   That helper gains a file-first dual-read: prefer
   `spec_dir/slice-NN*.md` when it exists; fall back to scanning
   `spec.md` sections otherwise. No forced migration.
3. **`migrate.py split-slices <spec-dir>` is available** for
   projects (or jig itself) that want to convert an existing
   monolithic `spec.md` into the file-per-slice shape. Atomic,
   idempotent, refuses on conflict (e.g., target `slice-NN-*.md`
   already exists).
4. **Slice frontmatter shape is unchanged.** The `--- status /
   dependencies / last_verified ---` block from spec 015 sits at
   the top of each slice file, identical to its current position
   right after the `## Slice` heading.
5. **No skill auto-trigger changes, no agent boundary changes.**
   The skill descriptions, the reviewer's tool boundaries, and the
   implementer's instructions are not touched. This is parser /
   templater work.
6. **Cross-references continue to use slice fragments** (e.g.
   `018-02`, `007-03`). Helpers resolve the fragment to either a
   file or a section transparently — callers don't need to know
   which layout the target spec uses.

## Non-goals

- **State machine changes.** The seven-state lifecycle (DRAFT,
  READY_FOR_REVIEW, READY_FOR_IMPLEMENTATION, IN_PROGRESS, REVIEWED,
  RECONCILED, DONE, plus 015's DEFERRED) is unchanged.
- **Frontmatter shape changes.** Status, dependencies, and
  last_verified stay as spec 015 defined them.
- **Renaming the directory layout.** Specs still live at
  `docs/specs/NNN-slug/`. Only the contents change.
- **Renumbering existing slices.** A spec that was `007-01..007-03`
  stays `007-01..007-03` post-split.
- **Migrating jig's own historical specs by default.** Slice 018-04
  splits one recent spec as a dogfood; the rest stay as monolithic
  `spec.md` files. Re-splitting closed work has no value.

## Open questions

- **Filename shape.** Three candidates:
  (a) `slice-NN.md` (minimal, matches shallow-validator),
  (b) `slice-NN-shortname.md` (descriptive),
  (c) `NN-shortname.md` (no prefix; folder context implies "slice").
  Recommendation: (b). The `slice-` prefix is searchable; the
  shortname makes the file self-describing in tree views.
- **Where do close-out and deviation logs live?** Inside each slice
  file (post-RECONCILED). This is already the convention with the
  monolithic layout — the H3 subsections (`### Close-out (post-DONE)`,
  `### Deviation log (after reconciliation)`) sit inside the slice
  block. File-per-slice keeps them in the same logical place.
- **What about spec-level deviation summary?** spec.md gains an
  optional `## Deviation summary` section that points at each
  slice's deviation log via relative links. Not required.

## Decomposition

S — **Spike**: none. The design pattern is direct application of
spec 015's lazy-migration approach.

P — **Paths**: split by read-side / write-side / scaffold-side /
migrate-side. Four slices.

I — **Interfaces**: one shared helper (`find_slice_section` in
`_common.parsing`) gains a dual-read mode. All callers reach it
through the same entry point — no per-caller surgery.

D — **Data**: existing slice frontmatter shape unchanged. New file
layout: `slice-NN-shortname.md` with frontmatter at top,
H2 heading `## Slice NNN-MM — shortname` immediately following.

R — **Rules**: dual-read everywhere (file > section); single-write
(transition writes to whichever shape the slice currently uses, no
forced migration); refuse-on-conflict in migrate (never silently
overwrite an existing slice file).

### Slices

- **018-01 — parser-foundation-and-dual-read**: extend
  `_common.parsing.find_slice_section` to prefer
  `spec_dir/slice-NN-*.md` over scanning `spec.md`. Add a new helper
  `find_slice_file(spec_dir, fragment) → Path | None`. Unit tests.
  No caller changes — every existing helper benefits because they
  all route through the common parser.
- **018-02 — caller-recognition-and-fixtures**: verify (via
  fixture-driven tests) that `workflow.py`, `land.py`, `review.py`,
  `spec_lint.py`, and `migrate.py` all correctly resolve slice
  references in a mixed spec dir (one slice in a file, one slice
  still in spec.md). Write-side regression tests: `transition`
  writes to the slice file when present, to spec.md section
  otherwise.
- **018-03 — scaffold-new-specs-as-file-per-slice**: update
  `templates/docs/specs/spec.md.template` to be header-only;
  rename `templates/docs/specs/slice-template.md` to clarify it's a
  full-file template; update `workflow.py new` to emit a spec.md +
  one starter slice file (instead of one monolithic spec.md with an
  embedded `## Slice` section).
- **018-04 — migrate-split-slices**: new
  `migrate.py split-slices <spec-dir> [--dry-run]` subcommand.
  Atomic, idempotent. Splits each `## Slice` block out of `spec.md`
  into its own `slice-NN-*.md` file, preserving frontmatter and
  body verbatim. Refuses if any target file already exists.
  Dogfood: apply to one recent spec (likely 017-vision-elicitation)
  to validate the tool; leave the rest as legacy.

Suggested order: 018-01 → 018-02 → 018-03 → 018-04.

018-01 is mechanical and small. 018-02 is the read-side
validation gate — once it passes, file-per-slice is safe to use
in new work. 018-03 wires the helpers and templates so new specs
default to the right shape. 018-04 finishes the loop by providing
the migration path for downstream projects (and a one-spec
dogfood).

---

## Slice 018-01 — parser-foundation-and-dual-read

---
status: DONE
dependencies: []
last_verified: 2026-05-15
---

**Goal:** `_common.parsing.find_slice_section` learns to look for a
sibling slice file (`<spec_dir>/slice-NN-*.md`) before falling back
to scanning `## Slice` sections inside `spec.md`. New helper
`find_slice_file(spec_dir, fragment) → Path | None`. Every existing
caller benefits transparently — no caller-side changes in this
slice.

**DoR:**
- ✅ `_common.parsing.find_slice_section` exists and is used by
  every slice-walking helper.
- ✅ Spec 015's slice frontmatter parser handles `--- ... ---`
  blocks immediately after the `## Slice` heading; the same parser
  works on a slice-file (frontmatter at top of file, heading
  follows).

**Acceptance Criteria:**

1. **`find_slice_file` resolves a fragment to a file.** Given a
   directory containing `slice-01-foo.md` and `slice-02-bar.md`,
   `find_slice_file(spec_dir, "018-01")` returns the path to
   `slice-01-foo.md`. Match is on the `## Slice NNN-MM` heading
   inside the file, not the filename — filenames are for humans,
   not parsers.
2. **`find_slice_file` returns `None` cleanly.** No matching file
   present → returns `None` (not raise), so callers can fall
   through to `spec.md` section scan.
3. **`find_slice_file` raises on ambiguity.** Two slice files
   whose `## Slice` headings both match the fragment → raise
   `SliceLookupError("ambiguous fragment ...")`, same shape as
   the existing section-walker.
4. **New `load_slice(spec_path, slice_fragment) → SliceLocation`
   helper.** `SliceLocation` is a namedtuple
   `(path: Path, text: str, start: int, end: int, label: str)`.
   The helper dual-reads: it calls `find_slice_file(spec_path.parent,
   fragment)` first; if a slice file matches, returns
   `(slice_file_path, slice_file_text, 0, len(slice_file_text),
   label)`. Otherwise it reads `spec_path`, scans for the
   `## Slice` section via the existing `find_slice_section`, and
   returns `(spec_path, spec_text, start, end, label)`. Callers
   that need dual-read use `load_slice` and get `loc.text[loc.start:loc.end]`
   uniformly — they don't branch on the layout themselves.
5. **Existing `find_slice_section` unchanged.** Callers that pass
   `spec_text` directly (without going through `load_slice`)
   continue to work exactly as today. No caller code outside
   `_common/parsing.py` is modified in this slice — callers
   migrate in slice 018-02.
6. **Tests in `skills/_common/test_parsing.py`**: `find_slice_file`
   covers present / absent / ambiguous / non-`.md`-files-ignored /
   filename-vs-heading-match-precedence (heading wins). `load_slice`
   covers slice-file-hit (returns file path + content + offsets
   spanning whole file), spec.md-fallback (returns spec_path +
   spec text + section offsets), and tolerance of leading blank
   lines / frontmatter inside the slice file.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] At least one fixture per AC.
- [ ] Reviewed by `reviewer` subagent.
- [x] Implementation review passed.
- [x] Deviation log produced.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md hot-cache entry added for spec 018 + slice 018-01.

**Anti-horizontal-phasing check:** A user can drop a `slice-01-foo.md`
file into a spec dir and `find_slice_section` resolves it — the
helper is callable end-to-end after this slice. No caller has to
change to see the benefit (any helper using the common parser
inherits the dual-read for free).

### Deviation log (after reconciliation)

**§1 — AC #4 reshaped pre-implementation to use a `load_slice`
helper instead of overloading `find_slice_section` with a
`spec_dir=` kwarg.** The original AC said
`find_slice_section(spec_text, fragment, *, spec_dir=None)` would
"return the slice file's content wrapped in the same `(start, end,
label)` tuple shape." That doesn't actually work — callers do
`text = spec_path.read_text(); section = text[start:end]`, but when
the slice lives in a sibling file, `text` is the wrong source. The
offsets would be into a string the caller never reads. Resolved by
introducing a separate `load_slice(spec_path, fragment) →
SliceLocation` helper that returns `(path, text, start, end,
label)` — callers do `loc.text[loc.start:loc.end]` and the layout
is invisible. Existing `find_slice_section` is untouched. Spec
text edited in this PR.

**§2 — `scripts/run_tests.py` silently skipped `skills/_common/`
tests.** The runner's `skill_dir.name.startswith("_")` skip
condition was intended to exclude `__pycache__`, but it also
excluded `_common` — meaning the existing 22 parsing tests (and
my 16 new ones) were never running in the official suite. Fixed
the skip predicate to drop dot-dirs and `__pycache__` only;
`_common` now contributes its tests. Test count went 709 → 747
on this slice (38 = 22 pre-existing + 16 new). Unrelated to the
slice's intent, but discovered while verifying the suite count
moved as expected. Filing this here rather than as a separate
fix because reverting would re-hide the pre-existing tests.

**§3 — Helper docstring at the top of `_common/parsing.py`
updated** to document the two new entry points (find_slice_file
and load_slice) alongside the existing ones. No behavior change.

**§4 — `find_slice_file` ignores `slice-*.md` files that fail to
read** (OSError/UnicodeDecodeError). Tested implicitly by the
"non-md files ignored" path; not exercised by an explicit test
because constructing an unreadable file portably across OSes is
fiddly. Filed in the inbox as a "could-add-test-if-it-bites" item.

---

## Slice 018-02 — caller-recognition-and-fixtures

---
status: DRAFT
dependencies: [018-01]
last_verified:
---

**Goal:** Validate that every slice-walking helper resolves
references correctly in a **mixed** spec directory (one slice
moved to its own file, one slice still embedded in `spec.md`).
Add fixture-driven tests covering all five callers: `workflow.py`,
`land.py`, `review.py`, `spec_lint.py`, `migrate.py`. Confirm
write-side: `workflow.py transition` writes to a slice file when
present, to a spec.md section otherwise.

**DoR:**
- ✅ Slice 018-01 landed: dual-read parser available.

**Acceptance Criteria:**

1. **Mixed-layout fixture.** A new test fixture provides a spec
   directory with `spec.md` (containing one `## Slice` section)
   and one sibling `slice-NN-*.md` file (with the same shape).
2. **`workflow.py transition` resolves both shapes.** Transitioning
   the file-based slice rewrites the frontmatter inside that file;
   transitioning the spec.md-based slice rewrites the prose
   `**STATUS:**` marker (or the frontmatter block if 015 added
   one) inside `spec.md`. Both shapes work in the same run.
3. **`land.py prepare` resolves both shapes.** Readiness check
   (status / tests / deviation log / DoD) runs against the right
   content regardless of which shape the target slice uses.
4. **`review.py` resolves both shapes.** The reviewer prompt
   builder retrieves the slice body via the common parser; the
   prompt is identical in length and content modulo the layout.
5. **`spec_lint.py` resolves both shapes.** Lint validates the
   frontmatter shape per spec 015 regardless of layout.
6. **`migrate.py rename-decisions`** continues to rewrite
   structured `dependencies:` entries; the rewriter walks slice
   files and spec.md sections via the same parser entry point.
7. **No production code outside `_common/parsing.py`'s
   integration changes.** This slice is a wiring + regression-test
   pass; if a caller needs more than a one-line `spec_dir=` change,
   that's a signal the abstraction in 018-01 is wrong and we revisit.

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Mixed-layout fixture lives at `tests/fixtures/mixed-layout/`.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] CLAUDE.md hot-cache entry updated for slice 018-02.

**Anti-horizontal-phasing check:** After this slice, file-per-slice
is fully usable for new work — author a spec, drop slices in
separate files, every helper resolves them correctly. The next
slice (018-03) makes it the *default*; this slice makes it *work*.

### Deviation log (after reconciliation)

_TBD post-implementation._

---

## Slice 018-03 — scaffold-new-specs-as-file-per-slice

---
status: DRAFT
dependencies: [018-02]
last_verified:
---

**Goal:** New specs scaffolded via `workflow.py new <slug>` get the
file-per-slice shape by default. `templates/docs/specs/spec.md.template`
shrinks to a header-only stub (frontmatter + overview placeholders).
A starter `slice-01-<placeholder>.md` lands alongside it from
`templates/docs/specs/slice-template.md`. Templates updated; existing
specs not touched.

**DoR:**
- ✅ Slice 018-02 landed: helpers all resolve file-based slices.
- ✅ `templates/docs/specs/slice-template.md` already exists from
  spec 015.

**Acceptance Criteria:**

1. **`workflow.py new <slug>` emits spec.md + one slice file.**
   The scaffolded directory contains: `spec.md` (frontmatter +
   `## Overview` placeholder + `## Decomposition` placeholder)
   AND `slice-01-placeholder.md` (frontmatter + `## Slice NNN-01`
   heading + DoR/AC/DoD placeholders). No `## Slice` section
   appears inside `spec.md`.
2. **Template files updated.** `templates/docs/specs/spec.md.template`
   loses the embedded `## Slice` block; the slice template
   already shipped via spec 015 is now also wired into
   `workflow.py new`.
3. **Existing scaffolded specs continue to work.** Specs 001–017
   are not rewritten. Helpers continue to find their `## Slice`
   sections via the parser's fallback.
4. **Tests cover the scaffold output.** `tests/test_workflow.py`
   gains a case that runs `workflow.py new` against a tmpdir and
   asserts the two-file shape.

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] CLAUDE.md hot-cache: spec 018 marked partially DONE (slices
      01–03); 018-04 still in flight.

**Anti-horizontal-phasing check:** After this slice, `workflow.py
new my-spec` produces a directory the user can start writing into
in the new shape. They don't need to manually split anything.

### Deviation log (after reconciliation)

_TBD post-implementation._

---

## Slice 018-04 — migrate-split-slices

---
status: DRAFT
dependencies: [018-03]
last_verified:
---

**Goal:** `migrate.py split-slices <spec-dir> [--dry-run]`
extracts each `## Slice NNN-MM` block out of `spec.md` into its
own `slice-NN-shortname.md` file. Atomic, idempotent, refuses on
collision. Dogfood: run it against `docs/specs/017-vision-elicitation/`
(one recent jig spec) to validate end-to-end. Other historical
specs remain monolithic by choice — re-splitting closed work has
no value.

**DoR:**
- ✅ Slice 018-03 landed: scaffold defaults to file-per-slice.
- ✅ `migrate.py` already has the conflict-refusal + atomic-write
  pattern (from `rename-decisions`, slice 008-02).

**Acceptance Criteria:**

1. **Subcommand exists.** `python3 migrate.py split-slices <dir>`
   parses every `## Slice NNN-MM — shortname` heading inside
   `<dir>/spec.md`, including the frontmatter block following the
   heading and all content up to the next `## Slice` heading (or
   EOF).
2. **One file per slice.** Each extracted block lands at
   `<dir>/slice-NN-shortname.md` with the frontmatter at file top
   (no leading H2 wrapper around frontmatter — the `## Slice`
   heading follows the frontmatter block, mirroring the
   slice-template shape).
3. **`spec.md` is rewritten** to drop the `## Slice` sections it
   exported. The `## Decomposition` section (and any prose before
   the first `## Slice`) is preserved. A new
   `## Slices` section is appended listing each extracted file by
   relative path.
4. **`--dry-run` shows the plan.** Lists each `(source heading,
   target file)` pair and exits 0 without writing.
5. **Refuses on conflict.** Exit 2 with a clear message if any
   target `slice-NN-*.md` already exists. No partial writes.
6. **Idempotent on re-run.** A spec.md whose `## Slice` sections
   are all already split out (none remain inside spec.md) → no-op,
   exit 0 with `nothing to split`.
7. **Dogfood.** Apply `migrate.py split-slices` to
   `docs/specs/017-vision-elicitation/`. Commit as part of this
   slice's deliverable. The other 16 historical specs stay
   monolithic by design (recorded in this slice's deviation log).
8. **Tests in `skills/migrate/test_migrate.py`** cover: clean
   split, no slices in spec.md (no-op), one target file already
   exists (refuse), `--dry-run` writes nothing, frontmatter
   preservation, label-to-filename derivation (`shortname` ←
   heading suffix after `— `, slugified).

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Spec 017 successfully split + landing-verified
      (`land.py prepare` for an arbitrary slice resolves it post-split).
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] CLAUDE.md hot-cache: spec 018 marked DONE.
- [ ] Spec 017's "spec.md is a single file" assumption checked in
      glossary / conventions docs and updated if referenced.

**Anti-horizontal-phasing check:** After this slice, a user with
an existing monolithic spec can run one command and have it
restructured into the new shape — the migration path is complete.
shallow-validator (and other downstream projects) can adopt jig's
spec layout without manual cut-and-paste.

### Deviation log (after reconciliation)

_TBD post-implementation._
