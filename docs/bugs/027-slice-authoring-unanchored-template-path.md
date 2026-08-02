---
status: DONE
tier: standard
severity: low
claimed_by: claude/bug-027-slice-template-anchor
regression_test: skills/spec-workflow/test_spec_workflow_skill_surface.py::SliceAuthoringReferenceAnchorTests
main_repro_checked_at: 2026-08-01
main_repro_ref: origin/main@80110ba
main_repro_result: reproduces
red_confirmed_at: 2026-08-01
green_confirmed_at: 2026-08-02
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 027: slice-authoring-unanchored-template-path

Reported as [GitHub issue 173](https://github.com/ramboz/jig/issues/173).

## Symptom

`skills/spec-workflow/SKILL.md` tells slice authors to build a new slice from
`templates/docs/specs/slice-template.md` — a bare, **unanchored** relative path.
It appears twice:

- step 5 of *How to use → Creating a new spec* (line ~248): "use the template at
  `templates/docs/specs/slice-template.md`".
- the *Slice frontmatter* section (line ~658): "New slices written from
  `templates/docs/specs/slice-template.md` are whole-file templates".

The path names no root, so different readers resolve it differently, and the
one authoritative in-project structural reference — the scaffolded first spec
`docs/specs/001-adopt-jig/` — is never cited as the place to look.

## Repro

1. Read `skills/spec-workflow/SKILL.md`, step 5 of "Creating a new spec".
2. Follow the instruction literally from **inside a scaffolded project** (the
   audience for the shipped skill): resolve `templates/docs/specs/slice-template.md`
   from the project root.
3. Observe: no such file. Scaffold copies `templates/` to
   `<project>/.claude/templates/` (see Evidence), so the project-root path the
   wording implies does not exist. A reader/agent then rummages in the plugin's
   own install directory — the wrong boundary — instead of the in-project
   worked example.

## Evidence

- `skills/scaffold-init/scaffold.py:951` `_copy_claude_templates` copies
  `plugin/templates/` → `target/.claude/templates/` (slice 095-01). So in a
  scaffolded project the slice template lives at
  `<project>/.claude/templates/docs/specs/slice-template.md`, **not** at the
  project-root `templates/…` the SKILL.md wording implies. The literal
  instruction is therefore wrong on two counts inside a scaffolded repo:
  unanchored *and* pointing at a path that does not exist from project root.
- `hosts/claude/scripts/verify_install.py:550-551` asserts the scaffold seeds
  `docs/specs/001-adopt-jig/spec.md` + `slice-01-bootstrap.md` at **project
  root** (host-agnostic, not under `.claude/`).
- `templates/CLAUDE.md.template:24` (and the codex/claude host mirrors) already
  names `docs/specs/001-adopt-jig/` as the "DONE worked example to imitate."
- The two live references: `skills/spec-workflow/SKILL.md:249` and `:658`.

## Hypotheses

- **[x] (leading) Repo-centric wording that breaks on ship.** The path was
  written from the jig source repo, where `templates/docs/specs/slice-template.md`
  does resolve from repo root. It was never re-anchored for the shipped audience
  (scaffolded projects), where the template lands under `.claude/templates/` and
  the better structural reference (`001-adopt-jig`) sits at project root.
  *Confirm:* scaffold copies to `.claude/templates/` (Evidence) and the
  in-project worked example exists at project root; the wording cites neither.
  *Falsify:* would fail if scaffold copied `templates/` to the project root
  verbatim — it does not.
- **Missing exemplar pointer only.** The path is fine; the skill just omits a
  pointer to the worked example. *Falsify:* even granting the pointer, the bare
  `templates/…` path stays unanchored and mislocated post-ship, so the report's
  core (ambiguous root, points outside the project) is unaddressed. Rejected as
  the *sole* cause — the pointer is necessary but not sufficient.

## Root cause

The slice-authoring guidance was authored against the jig **source repo's**
layout (`templates/…` at repo root) and never re-anchored for the **shipped**
audience — a scaffolded project, where (a) the template is copied under
`.claude/templates/`, so the bare project-root path does not exist, and (b) the
authoritative structural reference, the scaffolded first spec
`docs/specs/001-adopt-jig/`, sits at project root and is host-agnostic but is
never cited. The reference points a reader/agent at the wrong boundary (plugin
internals) instead of the in-project worked example.

## Fix class

`local_patch` — a bounded, correct rewrite of the two prose references in
`skills/spec-workflow/SKILL.md`. It corrects the root cause (wording never
re-anchored for the shipped audience) directly in the one place it lives; no
mechanism or path-resolution change is needed.

## Fix

Reword both slice-authoring references so the **in-project scaffolded worked
example** `docs/specs/001-adopt-jig/` (`spec.md` + `slice-01-bootstrap.md`) is
the primary structural reference — the same file the scaffolded `CLAUDE.md`
already names "the worked example to imitate," host-agnostic and at project
root. The bare, unanchored, post-ship-mislocated `templates/docs/specs/slice-template.md`
path is removed; authors get a well-formed starter slice mechanically via
`workflow.py new` (which emits `slice-01-tbd.md` from that template), so the raw
template path — whose real location is host-dependent (`.claude/templates/…`) —
no longer needs to be cited by hand.

Edited:
- `skills/spec-workflow/SKILL.md` step 5 of *Creating a new spec*.
- `skills/spec-workflow/SKILL.md` *Slice frontmatter* section.
- `hosts/claude/skills/spec-workflow/SKILL.md` +
  `hosts/codex/plugins/jig/skills/spec-workflow/SKILL.md` — regenerated via
  `scripts/build_host_packages.py` so the committed host mirrors carry the
  reword (the CI host-package drift guard `--check` passes).

Craft-review nits addressed in the same reword: step 5 no longer reads as if
`workflow.py new` is re-run per slice (it runs once, in step 2); a dropped
relative pronoun ("the worked example *that* scaffolding installs") is fixed.

## Already tried

(none — first attempt)

## Regression test

`skills/spec-workflow/test_spec_workflow_skill_surface.py::SliceAuthoringReferenceAnchorTests`
— pure-file inspection of SKILL.md: (1) the bare unanchored
`templates/docs/specs/slice-template.md` path no longer appears; (2) the
in-project worked example `docs/specs/001-adopt-jig/` is cited as the structural
reference. Fails red on current main (the bare path is present); passes green
after the reword.

## Proof

- **Red (pre-fix):** `bug.py transition 027 FIXING` shelled to `tdd.py` and
  witnessed the regression test fail; `red_confirmed_at: 2026-08-01`.
- **Green (post-fix):** the two reworded references + regenerated host mirrors
  make `SliceAuthoringReferenceAnchorTests` pass; `grep -c
  'templates/docs/specs/slice-template.md'` → 0 in all three SKILL.md copies,
  `001-adopt-jig` present in each. `bug.py transition 027 REVIEWED` re-runs the
  suite green (`green_confirmed_at`).
- **Reviews:** bug-review + craft both `pass` (independent read-only reviewers) —
  `docs/bugs/reviews/bug-027-{bug-review,craft}.md`.

## Learning

A doc reference in a **shipped** skill must be anchored for the *shipped*
audience, not the source-repo layout. `skills/spec-workflow/SKILL.md` cited
`templates/docs/specs/slice-template.md` — correct from the jig repo root, but
in a scaffolded project the template is copied under `.claude/templates/` and
the authoritative structural exemplar (`docs/specs/001-adopt-jig/`) sits at
project root. The fix removes the fragile path and points at the host-agnostic
in-project worked example. General rule: when prose ships to a different tree
than it was authored in, resolve every relative path against the *destination*.

## Main recheck

- 2026-08-01 - `origin/main@80110ba` -> reproduces: git show origin/main:skills/spec-workflow/SKILL.md | grep -n 'templates/docs/specs/slice-template.md' → 2 hits (lines 249, 658); unanchored path still present on fresh main
