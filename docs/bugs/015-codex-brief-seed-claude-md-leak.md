---
status: FIXING
tier: standard
severity: medium
claimed_by: claude/bug-codex-brief-claude-md
regression_test: skills/scaffold-init/test_scaffold_mode.py::CodexScaffoldAdapterTests::test_codex_brief_and_seed_name_agents_md_plugin_mode
main_repro_checked_at: 2026-07-29
main_repro_ref: bde9dfc
main_repro_result: reproduces
red_confirmed_at: 2026-07-29
green_confirmed_at: 2026-07-29
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 015: codex-brief-seed-claude-md-leak

## Symptom

A Codex-host scaffold tells the user to open `CLAUDE.md` — a file that exists
only in Claude projects. Codex projects get `AGENTS.md`. The wrong filename
appears in the two documents a new adopter reads *first*: `brief.md` (the
"what was detected / what to do next" hand-off) and the seed reference spec
under `docs/specs/001-adopt-jig/`.

Affects **both** scaffold modes. Cosmetic in the sense that nothing crashes;
not cosmetic in effect — step 1 of the getting-started list names a file the
user does not have.

## Repro

```bash
python3 skills/scaffold-init/scaffold.py /tmp/probe --host codex --solo
grep -rn 'CLAUDE.md' /tmp/probe/brief.md /tmp/probe/docs/specs/001-adopt-jig/
```

Observed on `main@bde9dfc` — 5 hits:

- `brief.md:29` — "1. Open [CLAUDE.md](CLAUDE.md) and fill in the Hot Cache"
- `docs/specs/001-adopt-jig/spec.md:13,35`
- `docs/specs/001-adopt-jig/slice-01-bootstrap.md:10,27`

Expected: every one of those names `AGENTS.md`, as the rendered `AGENTS.md`
and `docs/workflow.md` already do.

## Evidence

Every *other* rendered doc is correct, which localizes the fault to the render
path rather than the templates or the transform:

- `scaffold()` passes `post_render=doc_rewrite` when emitting the primer
  (`scaffold.py:2572,2576`) and the whole `docs/` tree (`:2593`). Those come
  out with Codex vocabulary.
- `brief.md` is written by `_render_brief` + `atomic_write_text` (`:2619-2622`)
  with **no** `post_render` at all.
- `_emit_seed_spec` (`:2061`) builds its own transform —
  `seed_rewrite = _make_layout_rewrite(docs_root)` (`:2084`) — which is the
  **layout** rewrite only (`docs/x` → `<root>/x`). The host transform is never
  applied to the seed.

Both are therefore the same fault in two places: a render path that was added
without being wired to the host transform. The Claude host hides it, because
there the untransformed text is already correct — which is why it survived.

`_emit_seed_spec`'s docstring actively reassures on a neighbouring axis: "The
seed templates carry only the `{{PROJECT_NAME}}` substitution and never leak
`${CLAUDE_PLUGIN_ROOT}` or source-checkout paths." True, and beside the point —
it says nothing about host *vocabulary*. A reader checking whether the seed
needs the transform would be told, accurately, that it is fine.

## Hypotheses

- [ ] H1: the seed/brief **templates** are wrong (missing a placeholder).
  Falsify by reading them: they legitimately say `CLAUDE.md`, exactly as
  `CLAUDE.md.template` does — the canonical templates are Claude-flavoured at
  source *by design*, and the host renderer is what translates them.
  **Falsified** — templates are correct; the seed/brief are the only rendered
  docs that never meet the renderer.
- [ ] H2: `CodexScaffoldRenderer.rewrite_skill_md_paths` fails to map
  `CLAUDE.md` → `AGENTS.md`. Falsify by checking the transform: it does
  (`out.replace("CLAUDE.md", "AGENTS.md")`), and the primer proves it works.
  **Falsified.**
- [x] H3 (leading): two render paths bypass the host transform —
  `_render_brief`/`atomic_write_text` passes no `post_render`, and
  `_emit_seed_spec` composes only the layout rewrite. **Confirmed** by reading
  both call sites and by the fact that every doc which *does* receive
  `doc_rewrite` is correct.

## Root cause

`brief.md` and the seed spec are rendered through paths that never receive the
host transform. `scaffold()` computes `doc_rewrite` once and threads it into
`copy_template` for the primer and `docs/`, but `_render_brief` writes directly
via `atomic_write_text`, and `_emit_seed_spec` constructs a *different*,
layout-only transform locally instead of accepting the caller's.

The class of defect: **the host transform is applied per-call-site rather than
being a property of "emitting a document"**, so each new render path has to
remember to opt in, and forgetting is invisible on the Claude host — the only
host most contributors run.

## Fix class

`local_patch`. Two render paths are wired to the transform the other paths
already receive, plus one new optional parameter on `copy_template`.

Not `structural_fix`, deliberately, and that is the honest label: the root
cause is that the host transform is opt-in per call site, so the *next* render
path added will forget it in exactly the same way. Making it structural means
routing every document emission through one seam that cannot skip the host
transform — a refactor of `scaffold()`'s emission paths that is out of
proportion to a wrong filename in two files, and that would be much easier to
review on its own. The guardrail against recurrence here is the host-parity
test, not the shape of the code.

## Fix

Thread the host transform into both paths — but apply it to the **template
text, before substitution**, not to the rendered output.

That ordering is load-bearing, and is why this fix is not a one-line
`post_render=doc_rewrite`. `copy_template` renders substitutions first and
post-renders second (`scaffold.py:195-197`), so the transform also sees
substituted *values*. The Codex transform includes a blanket
`replace("Claude", "Codex")`, and `PROJECT_NAME` is user-derived. Probed on
`main@bde9dfc`: a project directory named `Claude-Tools` is emitted into
`AGENTS.md` as `# Codex-Tools`. Reusing `post_render` here would have carried
that corruption into `brief.md` and the seed spec as well.

Applying the transform to the template first translates jig's own prose and
leaves substituted values untouched. `_render_brief`'s dynamic blocks
(`DETECTED_BLOCK` and friends) are jig-authored fixed strings containing no
host vocabulary, so they need no transform and are unaffected by the ordering.

**Adjacent defect, deliberately NOT fixed here:** the `Claude-Tools` →
`Codex-Tools` mangle on the primer/`docs/` path is a distinct bug in a
different code path, found while proving this one. Fixing it means moving those
call sites to the same pre-substitution ordering — a behaviour change to
already-shipped output that deserves its own record and its own review.

## Already tried

Nothing discarded — H1/H2 were falsified by reading, before any edit.

## Regression test

`skills/scaffold-init/test_scaffold_mode.py::CodexScaffoldAdapterTests` — four
tests, two of which are the red/green pair and two of which guard the *fix's
shape* rather than the bug:

- `test_codex_brief_and_seed_name_agents_md_plugin_mode`
- `test_codex_brief_and_seed_name_agents_md_in_repo_mode`
  Both assert the concatenated `brief.md` + seed spec contains no `CLAUDE.md`
  and does contain `AGENTS.md`. Both modes, because the fault was in the render
  path, not the mode.
- `test_codex_host_rewrite_does_not_mangle_project_name` — scaffolds into a
  directory named `Claude-Tools` and asserts the name survives.
- `test_claude_host_brief_and_seed_are_unchanged` — the Claude host must still
  say `CLAUDE.md`; guards against a fix that translates unconditionally.

Run:

```bash
python3 -m pytest skills/scaffold-init/test_scaffold_mode.py \
  -k "brief_and_seed or mangle_project_name or claude_host_brief"
```

## Proof

Red and green witnessed by reverting only `scaffold.py` (copied aside, not
stashed) while keeping the tests:

- **RED** (`git show HEAD:skills/scaffold-init/scaffold.py` in place): both
  `*_name_agents_md_*` tests fail — `AssertionError: 'CLAUDE.md' unexpectedly
  found in '# Scaffold Brief: demo-project … 1. Open [CLAUDE.md](CLAUDE.md) …'`.
- **GREEN** (fix restored): 4 passed.

The two guard tests pass in *both* states, and that is correct — they do not
witness this bug, they witness a wrong fix. Proven separately with a
single-variable variant: changing **only** the brief from pre- to
post-substitution rewriting (everything else identical) turns
`test_codex_host_rewrite_does_not_mangle_project_name` red, and restoring the
ordering turns it green. So the guard has teeth against the obvious one-line
fix, which is the whole reason it exists.

Full suite on this branch: **3690 tests OK, pyright clean.**

Cross-host no-op check: with the fix applied, a Claude-host scaffold's docs are
byte-identical to the pre-fix output (compared two scaffolds, differing only by
project name and timestamp). The Codex diff is exactly the intended line —
`1. Open [CLAUDE.md](CLAUDE.md)` → `1. Open [AGENTS.md](AGENTS.md)`.

## Learning

**A transform that must apply to every document should not be an argument each
call site remembers to pass.** Two render paths were added over time
(`_render_brief`, `_emit_seed_spec`) and each simply forgot the host hook —
`_emit_seed_spec` even built its own *narrower* transform, which reads as
deliberate and is easy to approve in review. Nothing detected the omission
because the Claude host is the identity case: on the host every contributor
runs, unrewritten text is already correct. **A cross-host transform is only
tested by the non-default host**, so host-parity assertions have to be written
deliberately; they will never fall out of ordinary development.

Second, narrower: **a docstring that reassures on a neighbouring axis can
suppress the question you needed asked.** `_emit_seed_spec` promised the seed
templates "never leak `${CLAUDE_PLUGIN_ROOT}` or source-checkout paths" — true,
and about *paths*. A reader wondering whether the seed needed the host
transform would have found an authoritative-sounding "this is fine" that did
not cover *vocabulary*. Reassurance should name its axis.

Third: **the obvious fix was wrong in a way the bug's own tests could not
catch.** `post_render=doc_rewrite` fixes the symptom and corrupts user data
(`Claude-Tools` → `Codex-Tools`), because `copy_template` substitutes before
post-rendering and the Codex transform does blanket word replacement. When a
fix reuses an existing hook, check what else flows through that hook — here,
user-derived values.

## Main recheck

- 2026-07-29 - `bde9dfc` -> reproduces: Branch is rooted at origin/main@bde9dfc (fresh). Ran: python3 skills/scaffold-init/scaffold.py /tmp/probe --host codex --solo; then grep -rn 'CLAUDE.md' /tmp/probe/brief.md /tmp/probe/docs/specs/001-adopt-jig/ — 5 hits (brief.md:29; spec.md:13,35; slice-01-bootstrap.md:10,27). Reproduces on unmodified main, so this is not an artifact of local state or of PR #136.
