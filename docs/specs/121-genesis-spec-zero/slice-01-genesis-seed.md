---
status: IN_PROGRESS
dependencies: [adr-0067]
last_verified:
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

## Slice 121-01 — genesis-seed

**Goal:** A greenfield `scaffold-init` seeds the worked example as the genesis
spec `000-adopt-jig` and no placeholder spec, so the project's own first spec,
reserved with `workflow.py new`, is `001`.

**DoR:**
- ✅ [ADR-0067](../../decisions/adr-0067-genesis-spec-zero.md) records the decision.
- ✅ `000` viability probed (spec `## Overview`, current state).

**Acceptance Criteria:**

1. **Genesis seed shape.** A greenfield scaffold (any host, any
   `layout.docs_root`) emits `<specs>/000-adopt-jig/spec.md` and
   `<specs>/000-adopt-jig/slice-01-bootstrap.md` with `status: DONE`, headed
   `# Spec 000: Adopt jig` and `## Slice 000-01 — bootstrap`, and **no**
   `002-first-spec/` (nor any other `NNN-*` spec dir).
2. **First own spec is 001.** In that freshly scaffolded project,
   `workflow.py new <slug> --no-push` reserves `001-<slug>`.
3. **Seed prose has no placeholder hand-off.** In a greenfield scaffold, no
   emitted seed file, status board, primer (`CLAUDE.md` / `AGENTS.md`), or
   `docs/adoption-readiness.md` names `002-first-spec`, `001-adopt-jig`, or
   "spec 002". The genesis spec
   and `adoption-readiness.md` point at `/jig:spec-workflow new <slug>` as the
   next step and say it will be spec `001`. The genesis overview says it is
   kept by default and may be removed once the project has its own specs
   (naming the slice 02 command).
4. **Status board.** The seeded `docs/specs/README.md` carries exactly one
   row, `000-adopt-jig` / `000-01 — bootstrap` / `DONE`, and
   `workflow.py check-board` passes on it.
5. **Verify stays green.** `verify_install.py --mode scaffold` passes its
   seed and docs checks on a fresh scaffold; the seed check expects the
   genesis files, not the old three.
6. **Skill prose follows (ADR-0067 decision 7).** Every place
   `skills/spec-workflow/SKILL.md` points authors at the worked example
   resolves it by state: the genesis spec (`000-adopt-jig/`, or
   `001-adopt-jig/` in projects scaffolded earlier) if present, otherwise any
   `DONE` slice in the project. No shipped skill file names
   `001-adopt-jig` as the *sole* exemplar path. And
   `skills/scaffold-init/SKILL.md`'s next-steps tell the user their first spec
   is `001` via `/jig:spec-workflow new <slug>`.
7. **Pointers follow the seed (ADR-0067 decision 4 invariant).** The
   genesis pointers in the rendered `CLAUDE.md`, `AGENTS.md` and
   `docs/adoption-readiness.md` name the genesis directory that is actually
   there: `000-adopt-jig` when this run emits the seed or it already exists,
   the legacy `001-adopt-jig` (detected by slug + `skill: scaffold-init`
   frontmatter, ADR-0067 decision 3) when only that exists, and no pointer at
   all when there is no genesis spec. Fixtures cover a `--force` re-scaffold of
   (a) a legacy-seed project and (b) a project with no genesis spec but at
   least one spec of its own (a spec-less specs dir is greenfield and is
   re-seeded with `000-adopt-jig`, by design). Greenfield-ness is decided
   before the primers render, with the same `_specs_dir_has_content`
   predicate as the seed. In both fixtures,
   no Markdown link in the rendered `CLAUDE.md`, `AGENTS.md` or
   `adoption-readiness.md` targets a missing directory. Tests assert this on
   the files themselves, because the completion verify only runs on greenfield
   and its docs check does not scan `AGENTS.md`.
8. **Packages in sync.** `scripts/build_host_packages.py --check` passes
   (Codex/Copilot packages regenerated from the changed templates).

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
      the spec's Active-specs entry. If the spec is still in flight, leave
      the entry.

**Anti-horizontal-phasing check:** After this slice lands, a developer who
scaffolds a new project sees one genesis row on the board and gets `001` for
their first spec — the user-reported numbering complaint is gone end to end.
