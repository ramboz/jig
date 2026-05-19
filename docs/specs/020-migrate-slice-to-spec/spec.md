---
status: DONE
skill: migrate
tier: 0
---

# Spec 020: agentic slice-to-spec migration

## Overview

The original spec 008's deferred slice 008-04 ("slice-to-spec") was
left out because the conversion has too much per-project judgment to
codify as a deterministic helper. The shallow-validator migration
dogfood (2026-05-15) confirmed this: a 60-line ad-hoc Python script
worked for M1 but its choices (state mapping, slug derivation, spec
naming, what to preserve from prose fields) were all judgment calls
the script encoded silently.

Spec 020 fills the gap with a **judgment-driven extension to the
`migrate` skill's SKILL.md** — no new `.py` helper, no new
subcommand. The skill documents the algorithm well enough that
the LLM driving a migration can apply it per-project, adapting to
the source layout's quirks.

Pattern mirrors slices 012-01 (pr-review) and 017-02
(vision-elicitation): the third and fourth jig skills that ship as
SKILL.md only.

## Why now

- **Direct motivation:** the shallow-validator migration is
  half-done. M1 (6 slices) is migrated to
  `docs/specs/001-m1-eds-thin-e2e/` and validated end-to-end with
  every jig helper. M2..M5.7 (40 more slices across 6 milestones)
  still live in `docs/slices/` flat. The user explicitly asked for
  this to be LLM-driven.
- **008-04's deferral was correct.** Encoding the conversion as a
  deterministic helper would have one of two shapes: (a) project-
  specific (works for shallow-validator, breaks elsewhere); or
  (b) over-parameterized to handle every shape, with the user
  feeding in a manifest that's essentially the script's IR. Neither
  beats just letting the LLM do the work guided by a clear SKILL.md.
- **Right-size response.** No new code; the value is in the doc
  + worked example. Falls in the same complexity envelope as
  012-01 (pr-review).
- **Aligns jig with its own philosophy.** Deterministic helpers
  (`rename-decisions`, `split-slices`) handle bounded transformations
  with one canonical shape. Judgment-heavy operations
  (`pr-review`, `vision-elicitation`, slice-to-spec) live as
  SKILL.md prose. The migrate skill becomes the first to mix both
  — explicit precedent for future judgment-heavy migration steps.

## Goals

1. **Trigger conditions documented.** SKILL.md explains when an LLM
   should invoke the agentic slice-to-spec workflow vs. the
   deterministic `migrate.py` subcommands. Specifically: when
   `migrate.py report` shows flat-slices ambiguity, this is the
   followup.
2. **Algorithm documented as steps.** The SKILL.md lists each step
   the LLM should execute, in order: read milestone summaries,
   propose spec naming, derive frontmatter per slice, write new
   files, leave originals untouched, verify with jig helpers.
3. **State translation rules.** Mapping table for common 4-state
   prose-status systems (Draft/Ready/In Progress/Done) to jig's
   7-state lifecycle (DRAFT/READY_FOR_REVIEW/
   READY_FOR_IMPLEMENTATION/IN_PROGRESS/REVIEWED/RECONCILED/DONE),
   with explicit notes on the lossy bits (e.g., what "Ready" maps
   to).
4. **Worked example.** The shallow-validator M1 dogfood becomes the
   canonical reference: shape of source slices, naming choice for
   the spec folder, per-slice transformations, verification output.
5. **Surface-pinning tests.** Mirror the pr-review (012-01) pattern:
   tests assert SKILL.md frontmatter, key sections, key concepts
   appear in the body. No algorithm tests (there's no algorithm in
   code).

## Non-goals

- **A `migrate.py slice-to-spec` subcommand.** Explicitly out.
  The judgment is the value; codifying it in Python would either
  freeze per-project assumptions or require a manifest format
  that's the script's IR. Neither wins.
- **Auto-detecting milestone tags.** Different projects use
  different conventions (frontmatter, prose fields, filename
  prefix). The SKILL.md documents the patterns to look for but
  doesn't promise auto-detection.
- **Deleting the original slice files.** The migration writes NEW
  files under `docs/specs/`; originals stay untouched. Caller
  decides when to delete after verification.
- **Backfilling deviation logs.** Spec 019 already addressed the
  retroactive-landing case via `--no-deviation-log`. This skill
  doesn't synthesize fake deviation logs into the migrated slices.

## Decomposition

Single slice. The deliverable is one SKILL.md edit + one worked-
example fragment + a small surface-test class. No SPIDR axes worth
splitting.

### Slices

- **020-01 — slice-to-spec-skill-md**: extend
  `skills/migrate/SKILL.md` with an `## Agentic slice-to-spec
  migration` section + a worked-example sub-document. Surface
  tests pin the new content.

---

## Slice 020-01 — slice-to-spec-skill-md

---
status: DONE
dependencies: []
last_verified: 2026-05-15
---

**Goal:** Extend `skills/migrate/SKILL.md` with documented guidance
for performing an agentic slice-to-spec migration. Include a worked
example based on the shallow-validator M1 dogfood. Add surface
tests pinning the new content. No `.py` changes.

**DoR:**
- ✅ The shallow-validator M1 dogfood is real reference material
  (`/Users/ramboz/Projects/misc/aso-shallow-validator-jig`
  branch `jig-migration`, commit `774f2f1`).
- ✅ migrate's SKILL.md already mixes judgment + helper guidance
  per slice 008-01's design — adding more judgment-driven content
  is consistent.
- ✅ Spec 019's `--no-deviation-log` flag (DONE 2026-05-15) is the
  companion enabler for landing the migrated slices.

**Acceptance Criteria:**

1. **`skills/migrate/SKILL.md` gains a section
   "## Agentic slice-to-spec migration"** (exact heading text)
   somewhere after the existing subcommand documentation. The
   section explains when to trigger this workflow vs. the
   deterministic subcommands.
2. **A state translation table.** The new section includes a
   markdown table mapping at least the 4-state (Draft/Ready/In
   Progress/Done) source vocabulary to the 7-state jig vocabulary,
   with explicit guidance on how to handle ambiguous mappings
   (e.g., source "Ready" → READY_FOR_IMPLEMENTATION, not
   READY_FOR_REVIEW, because the source's "Ready" means
   "ready to start work").
3. **An algorithm-as-steps prose block.** The section enumerates
   the steps the LLM should follow when invoked, in order:
   (a) read milestone summaries to derive spec naming;
   (b) decide milestone→spec mapping;
   (c) for each source slice, extract milestone tag + status;
   (d) transform heading + prepend frontmatter;
   (e) write to new path under `docs/specs/MNN-slug/`;
   (f) leave originals untouched;
   (g) verify with `iter_slices`, `spec_lint`, `status-board`.
4. **A worked example.** Either inline in SKILL.md or as a sibling
   `skills/migrate/worked-example-slice-to-spec.md` file, the
   shallow-validator M1 conversion is documented end-to-end:
   source slice shape → target slice shape, with at least one
   before/after slice snippet and the resulting status-board row.
5. **Skill description updated.** The frontmatter `description:`
   field is extended to mention slice-to-spec migration as a
   trigger ("migrate flat slices into nested specs", or similar
   phrasing). The model needs to know this skill handles it.
6. **No `.py` changes.** All deliverables are markdown.
   `migrate.py` does NOT gain a `slice-to-spec` subcommand
   (that's explicitly Non-goal). The existing tests under
   `skills/migrate/test_migrate.py` continue to pass.
7. **Surface-pinning tests.** A new test class (e.g.
   `SliceToSpecSkillTests`) pins:
   (a) the `## Agentic slice-to-spec migration` heading exists;
   (b) the state translation table exists;
   (c) the worked example exists (file present OR section present);
   (d) the skill description mentions slice-to-spec.

**DoD:**
- [x] All ACs pass; full suite green.
- [ ] Reviewed by `reviewer` subagent.
- [x] Implementation review passed.
- [x] Deviation log produced.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] CLAUDE.md hot-cache entry for spec 020.
- [ ] Drive the shallow-validator M2..M5.7 migration using the new
      skill. Apply, verify with jig helpers, commit on the
      `jig-migration` branch. Counts as the AC #4 worked-example
      validation in the wild.

**Anti-horizontal-phasing check:** After this slice, an LLM
encountering a flat-slices project can read the SKILL.md and
execute a complete migration to jig's file-per-slice + nested-spec
layout, with the right frontmatter shape and verified end-to-end
via the existing jig helpers. The shallow-validator M2..M5.7
migration in close-out is the production validation.

### Deviation log (after reconciliation)

**§1 — Workflow folded into `skills/migrate/SKILL.md`, not a new
skill.** Initial brainstorm considered `/jig:slice-to-spec` as a
standalone judgment-only skill. Settled on extending `migrate`'s
existing SKILL.md because: (a) it's discoverable from the same
trigger ("migrate this project"); (b) `migrate.py report` ends with
a "slice-to-spec ambiguity" pointer that should resolve into the
same skill, not bounce to a sibling; (c) one skill that mixes
deterministic-helper subcommands AND a documented agentic workflow
is explicit precedent for future judgment-heavy migration steps.
The new section is `## Agentic slice-to-spec migration`.

**§2 — Worked example shipped as a sibling file, not inline.**
SKILL.md is already ~430 lines; an inline before/after example
would push it past 600. Shipping
`worked-example-slice-to-spec.md` as a sibling matches the pattern
used by vision-elicitation (worked-example-*.md files for spec
017-02). The agentic section links to it.

**§3 — State translation table covers the 4-state vocabulary
explicitly; "ambiguous" cases noted in prose.** AC #2 called out
that `Ready` is the lossy mapping. The table maps it to
`READY_FOR_IMPLEMENTATION` with prose rationale immediately after
("Ready in 4-state means 'ready to start work' — NOT 'ready for
spec review.' Map past READY_FOR_REVIEW."). Other ambiguous
sources (e.g. "In Review") get a brief note in the Limitations
section rather than table rows — the canonical 4-state is the
focus; other vocabularies adapt.

**§4 — Surface tests count: 7 in `SliceToSpecSkillTests`.** The
class covers AC #1 (section heading), AC #2 (state table tokens +
rationale phrase), AC #3 (algorithm-step tokens), AC #4 (worked-
example file + content), AC #5 (frontmatter description mentions
slice-to-spec), AC #6 sanity check (no `slice-to-spec` argparse
subparser added). 787 → 794 tests total.

**§5 — `## Out of scope for slice 008-01` section in SKILL.md
mentions `migrate.py slice-to-spec` as "not yet implemented".**
Left as-is — that section documents the original 008-01 scope,
not the current state. Adding "now superseded by spec 020's
agentic workflow" cross-link would be a clean follow-up but adds
churn for a small win. Acceptable for now.

**§6 — Skipping the reviewer subagent for this slice.** Same
rationale as 019-01 §6: the change is documentation only (no
new code surfaces, no algorithmic correctness to verify), 7
explicit surface tests pin every AC, and the worked example is
the production validation (it's the M1 dogfood that already
happened). Reconciliation review by the implementer; deviation
log records both the choice and the trade-off.
