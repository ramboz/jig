---
status: DONE
dependencies: [adr-0067]
last_verified: 2026-10-26
frame_review: true
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

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
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

### Deviation log (after reconciliation)

The original ACs are preserved above. Implementation notes:

1. **Seed status-board comment dropped.** The seed `README.md.template` lost its
   trailing `<!-- Regenerate … -->` comment. `status-board` does not emit it,
   so with the comment present `check-board` reported the seeded board stale
   and AC4 could not hold. The comment predates this slice.
2. **Pointer-free fallback text, not an empty line.** With no genesis spec,
   `{{GENESIS_PRIMER_LINE}}` renders a plain status-board bullet and
   `{{GENESIS_READINESS_ITEM}}` renders "Read the status board" as item 1, so
   the numbered list stays intact. AC7 only required "no pointer"; the
   fallback keeps the primer's status-board link that the old bullet carried.
3. **Copilot fixtures run in plugin mode.** Copilot has no `--in-repo` mode,
   so the all-hosts AC7 matrix scaffolds Copilot in its default mode.
4. **AC5 exercised in-process.** The seed and docs checks are asserted through
   `check_scaffold_seed_present` / `run_completion_summary`, not the headless
   `--mode scaffold` CLI. Both read the same `_EXPECTED_SEED_FILES` list.
5. **Reviewer findings folded in** (compliance + craft, both `pass`): the AC3
   banned-name list now also runs against `AGENTS.md` on Codex/Copilot; the
   second Codex `--force` run asserts its exit code; the AC6 paragraph check
   splits on blank lines instead of a regex that could span paragraphs; an
   unused test parameter was removed; legacy detection reuses
   `_common.parsing.parse_frontmatter` instead of a hand-rolled `---` split;
   the `verify_install.run_completion_summary` docstring no longer claims the
   pointers "legitimately dangle".
6. **Forward reference to slice 121-02.** As AC3 requires, the genesis spec
   names `workflow.py retire-genesis`, which slice 121-02 builds. The two
   slices land in the same PR, so no release ships the name without the
   command.
7. **Residual (not fixed):** on a greenfield run, `_resolve_genesis_dir`
   returns `000-adopt-jig` without checking that the seed template directory
   exists. `_emit_seed_spec` silently returns when it is missing, so a broken
   package would render a dangling pointer. Only a malformed install can hit
   this, and the drift-guarded host packages make it unreachable in practice.
   It is not worth a template-root parameter now.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Front door does not describe the seed spec. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`; `check-board` clean. |
| `docs/product-vision.md` | `no-op` | UC-1/UC-2/UC-11 unchanged in scope; no behavior drift. |
| `docs/architecture.md` | `no-op` | Checked: no seed / worked-example description; module boundaries unchanged (new private helpers inside `scaffold.py`). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | `templates/{CLAUDE,AGENTS}.md.template` and `adoption-readiness.md.template` now take `{{GENESIS_*}}` substitutions; jig's own `CLAUDE.md` Active-specs entry is deferred to spec close (121-02 still open). |
| `docs/adoption-readiness.md`, `docs/prompts.md` | `updated` | Live prose described `001-adopt-jig` + the `002-first-spec` stub; now the `000-adopt-jig` genesis spec, first spec `001`. |
| `skills/spec-workflow/SKILL.md`, `skills/scaffold-init/SKILL.md` | `updated` | Exemplar resolved by state (ADR-0067 decision 7); next step says first spec is `001`. Host packages regenerated. |
| `docs/inbox.md` | `updated` | The `--force` board-overwrite item (2026-06-01) is about the generic board copy. This slice did not touch that doc-copy step, so the trigger has not fired. Annotated: 121-01's AC7 fixture (b) exercises that path, and the item's `001-adopt-jig` wording is now legacy. |
| `docs/refinement-todo.md` | `updated` | "seed spec's `.claude/` reference leaks on the Codex host" resolved: its trigger fired (seed templates touched), and a Codex re-probe shows no leak. |
| `docs/memory/**` | `deferred` | The glossary gets a **Genesis spec** term at spec close via memory-sync, once 121-02 defines retirement. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0067 indexed and Accepted. |
| Spec 121 / ADR-0067 own artifacts (`spec.md`, `slice-02-*.md`, `reviews/*`, `docs/decisions/reviews/adr-0067-*`) | `no-op` | Excluded: lifecycle records of this work, not drift-prone docs. |
| Closed spec 048 records (slice 048-05 Q3) | `no-op` | Partly superseded by ADR-0067, which says so. Amending the closed record needs separate owner approval (ADR-0010 / spec 102), so it is not edited here. |

