---
status: DONE
tier: standard
severity: medium
claimed_by: claude/bug-copy-machinery-docs-root
regression_test: skills/migrate/test_migrate.py::CopyMachineryTrackLocalDocsRootTests
main_repro_checked_at: 2026-07-30
main_repro_ref: origin/main@af8184ccc779f5f67cd777169e52b23054b89b51
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at: 2026-07-30
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 022: copy-machinery-ignores-docs-root

## Symptom

`migrate.py copy-machinery` writes its two managed `workflow.md` blocks — the
self-defining-vocabulary convention block (spec 065-04) and the reframe-practice
block (spec 067-03) — into a hardcoded `<project>/docs/workflow.md`, ignoring the
project's configured `layout.docs_root` (spec 084 / ADR-0033).

For a track-local project (`docs_root: "."`) the effect is doubly wrong:

1. the project's real `workflow.md` never receives the blocks, so the convention
   refresh silently does nothing on every run; and
2. a spurious `docs/` directory is created for a project that deliberately has
   none — the exact layer `docs_root: "."` exists to collapse.

Same class of miss for any non-default root (`docs/internal`, …): the blocks land
beside the real workflow doc instead of in it.

The two halves of the same command disagree about where the project's docs
live: the stale-citation scan added by bug 018 resolves the configured root via
`_project_docs_root`, while the machinery copy in the same function still takes
the `"docs"` default.

> **Line references in Symptom / Evidence / Hypotheses are "as found"** —
> coordinates in the pre-fix tree at `origin/main@af8184c`. The fix shifts them;
> `## Fix` onward cites post-fix lines. Both frames are kept deliberately rather
> than rewritten, so the diagnosis still reads against the tree it was made in.

## Repro

```
mkdir -p /tmp/repro/specs/001-demo /tmp/repro/decisions
echo '# Spec 001' > /tmp/repro/specs/001-demo/spec.md
echo '# ADR'      > /tmp/repro/decisions/adr-0001-demo.md
printf '# Workflow\n\nOur own house rules.\n' > /tmp/repro/workflow.md
echo '{"layout": {"docs_root": "."}, "installed_tiers": ["tier-0"]}' > /tmp/repro/scaffold.json

python3 skills/migrate/migrate.py copy-machinery /tmp/repro
```

Observed (before the fix):

- `/tmp/repro/workflow.md` — unchanged, `0` occurrences of the block markers.
- `/tmp/repro/docs/workflow.md` — created from scratch, holding all four markers
  (self-defining begin/end + reframe begin/end).

Expected: the blocks land in `/tmp/repro/workflow.md` and no `docs/` dir appears.

## Evidence

- `skills/migrate/migrate.py:2064-2067` — `scaffold_mod.copy_machinery(plugin,
  project_dir, force=..., installed_tiers=..., host=...)`: no `docs_root`
  argument.
- `skills/scaffold-init/scaffold.py:2200-2204` — the façade's signature carries
  `docs_root: str = "docs"`; the migrate call therefore silently takes the
  default.
- `skills/scaffold-init/scaffold.py:2274,2278` — that default flows straight into
  `_ensure_self_defining_convention_block(target, docs_root)` (`:2496`) and
  `_ensure_reframe_practice_block(target, docs_root)` (`:2569`), which resolve
  `<target>/<docs_root>/workflow.md`.
- `skills/migrate/migrate.py:1901` — `_project_docs_root` already exists in this
  very module and is already used by the stale-citation scan at `:1936`. The
  resolver is present; only this call site fails to use it.
- The greenfield caller (`scaffold()`) does pass its resolved root, so only the
  migrate entry point is affected — this is a missed call-site, not a broken
  helper.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: the two `_ensure_*_block` helpers ignore their `docs_root` parameter
      and hardcode `docs/` internally — falsify by calling
      `scaffold.copy_machinery(..., docs_root=".")` directly and checking the
      block lands at the project root.
- [x] H2 (leading): the helpers are correct and layout-aware, but
      `migrate.copy_machinery` never forwards the project's configured root and
      so lets the `"docs"` default apply — confirm by reading the call site at
      `migrate.py:2064` and by H1's direct-call check passing.
- [ ] H3: the root is meant to be discovered inside `scaffold.copy_machinery`
      from the target's `scaffold.json`, and the regression is that the
      discovery was dropped — falsify by grepping the façade for any
      `project_layout` / sentinel read.

H1 and H3 both falsified: `scaffold.copy_machinery(..., docs_root=".")` writes to
the project root correctly, and the façade performs no sentinel discovery — it
takes the caller's word. H2 confirmed.

## Root cause

`migrate.copy_machinery` treats `docs_root` as somebody else's problem. It
resolves the *host* (`_resolve_host`) and the *tier set*
(`read_installed_tiers` / `plan_installed_tiers`) from the target project, and
since bug 018 it even resolves the *docs root* for its own stale-citation scan
— but it never forwards that root to `scaffold.copy_machinery`, so the façade's
`docs_root: str = "docs"` default applies.

The deeper reason the miss survived: the parameter is optional with a default
that is *correct for most projects*. Spec 084 added `docs_root` to the façade and
updated the greenfield caller, but a defaulted keyword argument gives no signal
at the second call site — nothing fails, nothing warns, and the wrong output only
shows up on the minority of projects with a non-default root.

## Fix class

local_patch

## Fix

Forward the already-resolved root at the one call site that drops it:

```python
scaffold_mod.copy_machinery(
    plugin, project_dir, force=force, installed_tiers=copy_tiers,
    host=resolved_host,
    docs_root=_project_docs_root(project_dir),
)
```

`_project_docs_root` (`migrate.py:1901`) is the resolver to use here, and the
two candidates are not actually interchangeable:

- `_validated_docs_root` (`:199`) takes a **raw string** and validates it. It
  never reads `scaffold.json`, so it could not have answered "what is this
  project's configured root?" at all — it is the validator for a
  caller-supplied `--docs-root` value, not a resolver.
- `_project_docs_root` (`:1901`) reads the target's own `scaffold.json`, which
  is the question this call site is asking. It is also what the sibling
  stale-citation scan already uses, so one resolver keeps both halves of the
  command agreeing on where the docs live.

Its failure behaviour is right for this call site too: a malformed config must
not fail a machinery copy that would otherwise succeed, so it degrades to the
historical `"docs"` default rather than raising. That degrade is **bounded but
not free**, and this fix widens its blast radius from a read to a write:

- *Bounded* — `project_layout._validate_docs_root` rejects absolute and
  `..`-escaping roots before `_project_docs_root` can return one, so the new
  write path gains no reach outside the project. This is why
  `security_surface: false` is defensible rather than merely assumed.
- *Not free* — on a `docs_root: "."` project whose `scaffold.json` is
  malformed, the `"docs"` fallback silently reproduces this bug's exact
  symptom instead of reporting the bad config.
  `test_malformed_layout_degrades_instead_of_failing_the_copy` pins the
  degrade so a future swap to a raising resolver cannot pass silently.

Because the same resolver now feeds both a read (where to LOOK for stale
citations) and a write (where to PUT the managed blocks), its docstring was
updated to name both consumers and the write-side consequence of the fallback.

### Known limit — Codex host

`scaffold.copy_machinery` returns early for `host == "codex"`
(`scaffold.py:2253-2257`), before either `_ensure_*_block` call, so a
Codex-host project never receives the two managed blocks and `docs_root` is
inert on that path. Pre-existing and out of scope here; this fix corrects the
Claude path, where the blocks are actually written. Worth its own record.

## Already tried

Nothing discarded — the diagnosis pointed at a single call site, and the fix is
the one-line forward using a resolver that already exists in the module.

## Regression test

`CopyMachineryTrackLocalDocsRootTests` in `skills/migrate/test_migrate.py` —
seeds a `docs_root: "."` project through the real CLI and asserts both halves of
the defect:

- `test_convention_block_lands_at_configured_root` — the root `workflow.md` gets
  the block and keeps its pre-existing content;
- `test_no_spurious_docs_dir_is_created` — no `docs/` directory appears;
- `test_reframe_block_lands_at_configured_root` — the second managed block
  follows the same root;
- `test_nested_docs_root_is_honoured` — a non-`.` custom root
  (`docs/internal`) also receives the block, and nothing is written to the
  default `docs/workflow.md`, so the fix is not `.`-special-cased;
- `test_default_docs_root_still_lands_in_docs` — the ordinary `docs` project is
  unchanged;
- `test_malformed_layout_degrades_instead_of_failing_the_copy` — a malformed
  `layout.docs_root` still exits 0, pinning the degrade-not-raise contract the
  resolver choice rests on.

## Proof

Red (before the fix), on the four non-default-root assertions:

```
FAIL: test_convention_block_lands_at_configured_root
AssertionError: convention block missing from <project>/workflow.md
FAIL: test_no_spurious_docs_dir_is_created
AssertionError: True is not false : copy-machinery created a docs/ dir in a
  docs_root='.' project
FAIL: test_reframe_block_lands_at_configured_root
AssertionError: '<!-- >>> jig reframe-practice >>> -->' not found in
  '# Workflow\n\nOur own house rules.\n'
FAIL: test_nested_docs_root_is_honoured
Ran 5 tests — FAILED (failures=4)
```

`test_default_docs_root_still_lands_in_docs` passed red, confirming the
ordinary path was never broken.

Green (after the fix): `Ran 6 tests — OK`. Full suite `python3
scripts/run_tests.py` exits 0.

Original reported repro, re-run after the fix on a `docs_root: "."` project:
all 4 managed markers present in the project's real root `workflow.md`,
pre-existing content preserved, and no `docs/` directory created.

**Deviation from "every named regression test was observed red pre-fix."** The
red witness above covers five tests; the sixth
(`test_malformed_layout_degrades_instead_of_failing_the_copy`) did not exist
then — it was added in the review round, in response to both reviewer passes
noting that the degrade contract the fix rests on was untested. It pins a
property of the resolver rather than the defect, so it would pass pre-fix and
a red witness would prove nothing about it. Its discrimination was established
by mutation instead: forcing `_project_docs_root` to re-raise rather than
return `"docs"` turns it red (run under `python3 -B`, so stale bytecode cannot
mask the edit), and it asserts the degrade *outcome* — blocks land under the
fallback `docs/` — not merely a zero exit, so a copy that wrote nothing at all
would still fail it.

## Learning

An optional parameter with a sensible default is an invisible call site. When a
spec threads a new project-scoped setting (`docs_root`) through a shared façade,
the greenfield caller gets updated because it is the one being worked on; every
*other* caller silently keeps the default and nothing complains. Spec 084 had
exactly two callers of `scaffold.copy_machinery` and updated one.

The second-order lesson is about the *repair*: reusing an existing resolver
also inherits its documented contract. `_project_docs_root` was written to
answer "where should I LOOK?", and its docstring justified swallowing every
exception on exactly that basis. Forwarding it to the façade quietly promoted
it to "where should I WRITE?" — the same fallback, a materially different
consequence. A helper's docstring is part of its contract; widening the set of
consumers without revisiting it leaves a justification that no longer covers
the code.

Cheap guard for the class: when a shared helper gains a project-scoped
parameter, grep for every caller of that helper in the same change and decide
explicitly for each one — the default is a decision, not an absence of one.
And when you reuse a helper in a new role, re-read what its docstring promises.

## Main recheck

- 2026-07-30 - `origin/main@af8184ccc779f5f67cd777169e52b23054b89b51` -> reproduces: copy-machinery on a docs_root='.' project built from a fresh origin/main tree: root workflow.md unchanged (0 of the 4 managed markers), spurious docs/workflow.md created carrying all 4 (jig self-defining-vocabulary + jig reframe-practice, begin/end)
