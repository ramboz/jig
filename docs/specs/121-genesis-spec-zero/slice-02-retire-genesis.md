---
status: READY_FOR_IMPLEMENTATION
dependencies: [121-01, adr-0067]
last_verified:
frame_review: true
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
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
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
