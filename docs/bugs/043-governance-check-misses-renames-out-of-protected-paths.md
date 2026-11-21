---
status: REPORTED
tier:
severity:
regression_test:
main_repro_checked_at:
main_repro_ref:
main_repro_result:
red_confirmed_at:
green_confirmed_at:
fix_class:
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 043: governance-check-misses-renames-out-of-protected-paths

Reported: found while drafting spec 123 (R-002), 2026-11-21. Renumbered from
the helper's local 042 because open PR #255 already holds bug 042.

## Symptom

The protected-path check that `scaffold-init` writes into adopting projects
(`jig-governance.yml`, ADR-0051 / spec 106) does not flag a pull request that
moves or renames a protected file *out of* a protected path. A PR can relocate
`docs/decisions/adr-0001-x.md` to `archive/adr-0001-x.md` and the job lists only
the new path, which matches no protected glob, so no owner review is requested.

## Repro

The scaffolded job runs `git diff --name-only origin/<base>...HEAD`
(`skills/scaffold-init/governance.py:204`). With git 2.43.0 in a scratch repo:

```bash
git init -q -b main && mkdir -p docs/decisions
printf 'adr body\nline2\nline3\n' > docs/decisions/adr-0001-x.md
git add . && git commit -qm base
git checkout -qb pr && mkdir archive
git mv docs/decisions/adr-0001-x.md archive/adr-0001-x.md && git commit -qm move
git diff --name-only main...pr               # -> archive/adr-0001-x.md
git diff --name-only --no-renames main...pr  # -> both paths
```

## Evidence

- `git diff --name-only` applies rename detection by default (`diff.renames`),
  so a rename reports only its destination path.
- `--no-renames` (or `--name-status` and reading both sides of an `R` line)
  reports the source path too.
- Not checked: whether a copy (`C`) or a delete-plus-add split across commits
  behaves the same; whether jig's own CI has the same pattern elsewhere.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: <alternative explanation>, falsify by <check>
- [x] H2 (leading): <leading explanation>, confirm by <check>

## Root cause

## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:**

**Relevant history inspected:**

**Affected call sites:**

**Reuse decision:**

## Fix class

## Fix

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

## Already tried

## Regression test

## Proof

## Learning

## Release log

- 2026-11-21 - released claim from ccr-8cc8a4fd-rgnriz: reported from R-002 drafting; not being fixed in this session
