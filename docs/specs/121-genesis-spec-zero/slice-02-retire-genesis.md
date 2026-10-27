---
status: RECONCILED
dependencies: [121-01, adr-0067]
last_verified: 2026-10-26
frame_review: true
claimed_by: claude/jig-spec-scaffolding-177ac9
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 121-02 — retire-genesis

**Goal:** A project that no longer wants its seed can remove it with
`workflow.py retire-genesis`, in either the new (`000-adopt-jig`) or legacy
(`001-adopt-jig` + `002-first-spec`) shape, without leaving dangling links in
the scaffolded pointer files (other links into it are reported),
and
`transition` points at the command once the project's first own spec is done.

**DoR:**
- ✅ 121-01 defines the genesis shape.
- ✅ The removal hazard is probed (spec `## Overview`: seed check + dangling
  primer/adoption links).

**Acceptance Criteria:**

1. **Retire the genesis spec.** `workflow.py retire-genesis [--project-dir
   DIR]` in a project whose specs dir contains `000-adopt-jig/` removes that
   directory, regenerates the status board without its row, and prints each
   removed path. Exit 0.
2. **Legacy shape.** With a legacy seed, it removes `001-adopt-jig/` when that
   spec's frontmatter has `skill: scaffold-init`. It removes `002-first-spec/`
   **only** when every untouched-stub check holds: the directory holds nothing
   but `spec.md`, and that file still has `status: DRAFT`, its
   `# Spec 002: First spec — replace me` heading, the
   `**Replace this with your first real spec.**` lead, the
   `## Slice 002-01 — replace-me` heading, and the
   `_TODO: describe the first vertical slice._` placeholder. These are content
   markers frozen in the command (the live template is gone after 121-01).
   Grounding: every committed version of both legacy seed templates
   (`git log` on `templates/docs/specs/seed/{001-adopt-jig,002-first-spec}/spec.md.template`,
   since `325f9ba7`) carries these markers and `skill: scaffold-init`. A
   `001-adopt-jig/` lacking the marker is reported by name ("not recognised as
   the jig seed; left in place"), not silently treated as nothing to retire.
   If any check fails, the directory is kept and reported as kept. Fixtures
   cover an edited stub that is still `DRAFT` with its heading intact, and a
   stub dir with an extra slice file. Both are kept.
3. **No dangling links.** The rewrite scope is exactly the files jig
   scaffolds with a genesis pointer: project-root `CLAUDE.md` and `AGENTS.md`,
   `<docs_root>/adoption-readiness.md` (docs root resolved via
   `layout.docs_root`, so `.` and custom roots work), and a **kept** legacy
   `002-first-spec/spec.md` (its stub text links `../001-adopt-jig/`). In
   those files, every Markdown link into a removed directory is resolved:
   - A **list item** (bullet or numbered) whose first link targets a removed
     directory is deleted entirely, with its indented continuation lines. This
     covers the real primer bullet (`- [001-adopt-jig](…) - DONE worked example
     to imitate; see [docs/specs/README.md](…)…`) and the adoption-readiness
     "Read the worked example" item, so no stale "imitate this" guidance is
     left behind. A numbered list left starting at `2.` is accepted (valid
     Markdown, renders renumbered).
   - Any other link is replaced by its link text in backticks.

   The status board is regenerated. Any other link into a removed directory
   anywhere under `<docs_root>/` (e.g. in the user's own specs) is **reported,
   not rewritten**, so nothing breaks silently. Tests assert on the files
   themselves (the existing docs check does not scan `AGENTS.md` or custom
   docs roots), under the default, `.` and a custom docs root, with fixtures
   for the actual legacy primer bullet, the legacy adoption-readiness item,
   a kept legacy stub, and a user spec linking the genesis (reported, unchanged).
4. **Safe no-ops, refusal and dry run.** With no genesis spec present, the
   command prints that there is nothing to retire and exits 0 without writing.
   When the specs dir holds no spec other than the genesis spec (and an
   untouched legacy stub), it **refuses** (non-zero exit, nothing written) and
   tells the user to write their first spec first. The scaffold seeds any
   spec-less specs dir as greenfield (`_specs_dir_has_content`,
   `skills/scaffold-init/scaffold.py:3255`), so retiring there would not stick.
   `--dry-run` prints what would be removed or rewritten and writes nothing.
5. **First-done hint.** When `transition … DONE` makes the first
   non-genesis spec roll up to `DONE` while a genesis spec is still present,
   it prints one non-blocking line naming `workflow.py retire-genesis`. It
   prints nothing on later spec completions, never deletes anything, and never
   changes the exit code. (Legacy projects that already have a `DONE` spec never
   see the hint. They find the command through the `SKILL.md` documentation in
   AC7.)
6. **Retired stays retired.** After `retire-genesis` (which by AC4 leaves at
   least one non-genesis spec), a
   `scaffold-init --force` re-scaffold neither re-emits the genesis spec nor
   re-adds a pointer to it (no rendered file links into a removed directory).
   A fixture covers the refusal on a specs dir holding only the genesis spec.
   Genesis detection (command, hint, scaffold pointer) keys on the directory
   slug and shape, not on the spec number's integer value.
7. **Documented.** `skills/spec-workflow/SKILL.md` documents
   `retire-genesis` (what it removes, both shapes, `--dry-run`, the hint).

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

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry.

**Anti-horizontal-phasing check:** After this slice lands, a developer with a
new or legacy seed runs one command and the seed is gone. The board and the
scaffolded pointer files are clean, and any other link into the removed spec is
reported.

### Deviation log (after reconciliation)

The original ACs are preserved above. Implementation notes:

1. **`000-adopt-jig` also needs the seed frontmatter.** AC1 removes
   `000-adopt-jig/` on its slug. The code also requires `skill: scaffold-init`
   in its frontmatter, the same rule AC2 applies to legacy `001-adopt-jig/`.
   Without it, the directory is reported as "not recognised as the jig seed"
   and left in place. This came from the craft review: a user's own
   `000-adopt-jig` is never deleted. The seeded template carries the field.
   The reconciliation review found that this left scaffold-init's
   `_resolve_genesis_dir` (121-01) accepting `000` on slug alone, so a user's
   own unmarked `000-adopt-jig` would still be linked as "the worked example to
   imitate". Aligned in this slice: both now require the frontmatter for `000`
   and legacy `001`, which is AC6's single predicate. A new 121-01-side test
   (`test_existing_000_without_seed_frontmatter_is_not_pointed_at`) covers it.
2. **The status board is not scanned for links.** `<specs>/README.md` is
   regenerated by the command, so its rows are not "links left in place". The
   first implementation reported the board's own genesis row on every run;
   both reviewers caught it. Fixed, with a row-bearing board fixture.
3. **A list item is the item's own lines.** Continuation lines belong to the
   item; nested list items do not. A child bullet's genesis link therefore
   never deletes its parent or siblings (a craft-review blocker, fixed and
   tested). When a parent's *own* first link is the genesis, the parent goes
   and its nested children stay, attached to the previous item. The
   scaffolded pointer shapes have no children.
4. **Hint on stderr.** `transition` returns the summary string that callers
   compare exactly, so the first-done hint goes to stderr like the other
   advisories. AC5 says "prints" without naming a stream.
5. **Write order.** Pointer files are rewritten atomically before any
   directory is removed. A failure partway through leaves the genesis spec
   without its pointers, never pointers into a missing directory. The plan
   and the AC4 refusal are both computed before any write.
6. **Known limits (not fixed, low risk for scaffolded files):**
   - Only inline single-line links are rewritten or reported; reference-style,
     angle-bracket and titled links are not (commented at `_MD_LINK_RE`).
   - Fenced code is not skipped by the rewrite.
   - Under `docs_root: .` the report scan walks the project tree, minus a
     small skip set, with no `.gitignore` awareness.
   - A refusal drops any "not recognised" notes gathered before it.
7. **Legacy stub interpretation.**
   - The legacy `002-first-spec` is only considered when a recognised legacy
     `001-adopt-jig` is present.
   - A stub that keeps every AC2 marker but has text appended counts as
     untouched, per AC2's literal marker list.
   - A kept (edited) stub counts as an own spec for the AC4 refusal, but is
     excluded from the first-done hint's "done" set.
8. **Board regenerated only when it exists.** `regenerate_status_board`
   raises on a missing board, which would otherwise fail after the
   directories were already gone.
9. **SKILL.md wording.** The `retire-genesis` bullet says "the legacy
   `first-spec` stub dir", because a 121-01 test forbids the literal
   `002-first-spec` in that file.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Front door does not list workflow subcommands. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`. |
| `docs/product-vision.md` | `no-op` | UC-1/UC-2/UC-11 scope unchanged. |
| `docs/architecture.md` | `no-op` | New subcommand inside `workflow.py`; no module boundary or public-contract change. Genesis detection stays local to each caller (ADR-0002: two callers, no shared helper). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | Scaffold templates were already updated in 121-01. jig's own `CLAUDE.md` gets no new hot-cache entry: the glossary is the on-demand home (spec 055 primer discipline). |
| `skills/spec-workflow/SKILL.md` | `updated` | `retire-genesis` bullet (both shapes, refusal, `--dry-run`, report-only links, the hint). Host packages regenerated. |
| `docs/adoption-readiness.md` | `no-op` | Already names `retire-genesis` (updated in 121-01). |
| `docs/prompts.md` | `no-op` | Updated in 121-01; this slice adds nothing it describes. |
| `skills/scaffold-init/scaffold.py` | `updated` | `_resolve_genesis_dir` aligned to the shared genesis predicate (deviation 1). |
| `docs/inbox.md` | `no-op` | Checked; nothing resolved by this slice. |
| `docs/refinement-todo.md` | `no-op` | The known limits in deviation 6 are low-risk and not deferred decisions. |
| `docs/memory/glossary.md` | `updated` | New **Genesis spec** entry (the memory-sync item deferred from 121-01). |
| `docs/decisions/README.md` / ADR index | `no-op` | No ADR change; ADR-0067 already Accepted and indexed. |
| Spec 121 own artifacts (`reviews/*`, `spec.md`) | `no-op` | Lifecycle records of this work, not drift-prone docs. |
| 121-01's committed files (templates, ADR-0067 records, `verify_install.py`, `docs/inbox.md`, `docs/refinement-todo.md`, `docs/adoption-readiness.md`, `docs/prompts.md`) | `no-op` | Accounted for in 121-01's own sweep; the branch diff includes them. |
| Code and test files (`workflow.py`, `test_retire_genesis.py`, `test_scaffold_genesis.py`) | `no-op` | Deliberately outside the sweep: they are the slice's deliverables, covered by the compliance and craft passes. |

