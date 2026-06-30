---
status: DONE
tier: standard
severity: medium
claimed_by: detached
regression_test: targeted unittest command in bug record
main_repro_checked_at: 2026-06-30
main_repro_ref: origin/main@557775a
main_repro_result: reproduces
red_confirmed_at:
green_confirmed_at:
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 002: bug-registry-invisible

## Symptom
Spec authors working from the loaded primer and `docs/specs/README.md` have no
visible pointer to tracked bug records. Feedback/triage specs can therefore
duplicate a `docs/bugs/` defect as a spec acceptance criterion.

## Repro
Before this fix:

```bash
python3 -m unittest \
  skills.bug-fix.test_bug.BugCoreTests.test_status_board_default_preamble_links_spec_board \
  skills.spec-workflow.test_workflow.StatusBoardTests.test_status_board_preamble_links_bug_board \
  skills.spec-workflow.test_workflow.SkillPromotionTests.test_creating_spec_cross_checks_bug_registry \
  scripts.test_lean_primer.ScaffoldPrimerIndexShape.test_primer_templates_link_bug_status_board \
  skills.scaffold-init.test_scaffold.GreenfieldScaffoldTests.test_creates_full_tree \
  skills.scaffold-init.test_scaffold.GreenfieldScaffoldTests.test_claude_md_hot_cache \
  skills.scaffold-init.test_scaffold.DocContentTests.test_workflow_routes_feedback_against_bug_registry
```

The targeted suite failed because bug-board/scaffold/spec-workflow surfaces did
not mention `docs/bugs/README.md` or the reciprocal spec-board link.

## Evidence
- `docs/specs/README.md` had no bug-board cross-link.
- `docs/bugs/README.md` had no spec-board cross-link.
- `templates/CLAUDE.md.template` and `templates/AGENTS.md.template` listed the
  spec board but not `docs/bugs/README.md`.
- `skills/spec-workflow/SKILL.md` had no bug-registry check in "Creating a new
  spec".

## Hypotheses
- [x] H1: discoverability was only documented inside `bug-fix`, leaving
  the spec-facing entry points (`docs/specs/README.md`, scaffolded primers, and
  spec authoring procedure) unaware of the bug registry.
- [ ] H2: the bug board existed, but `bug.py status-board` discarded a custom
  cross-link on regeneration.

H2 is falsified by `bug.py`'s preamble-preservation behavior; the missing link
was never emitted in the default/new-board path or source templates.

## Root cause
The spec and bug lifecycles were implemented as separate registries without a
shared discoverability contract. The scaffolded primer, spec-board template,
live spec board, and `spec-workflow` authoring steps all treated the spec board
as the only session work list.

## Fix class
structural_fix

## Fix
- Add reciprocal spec/bug board links to live boards and scaffold templates.
- Emit a default spec-board link from `bug.py status-board` for new bug boards.
- Scaffold `docs/bugs/README.md` so the primer link resolves in new projects.
- Add an explicit `spec-workflow` step to check `docs/bugs/README.md` before
  drafting feedback/triage spec acceptance criteria.

## Already tried
N/A

## Regression test
Targeted unittest command in frontmatter.

## Proof
The targeted unittest command failed before the fix and passes after the fix.

## Learning
When adding a first-class lifecycle registry, update every spec-facing entry
point, not only the new lifecycle's own skill and board.

## Main recheck

- 2026-06-30 - `origin/main@557775a` -> reproduces: targeted regression suite failed before fix: missing bug-board/spec-board links, scaffold docs/bugs/README.md, primer docs/bugs/README.md, and spec-workflow bug cross-check
