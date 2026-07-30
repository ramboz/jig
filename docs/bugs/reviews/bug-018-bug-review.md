---
bug: 018
pass: bug-review
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-07-30T19:32:12Z
prompt_source: review.py bug-review docs/bugs/018-copy-machinery-leaves-mode-inconsistent.md skills/migrate/migrate.py skills/scaffold-init/scaffold.py skills/migrate/SKILL.md skills/migrate/test_migrate.py
---

Reviewed post-merge, against `origin/main@f0a5be4`. The fix for bug 018 landed
as `dd0d350` (PR #145) without either required review pass being recorded; this
pass was run retroactively against the merged deliverable to close that gap.

VERDICT: needs-changes

## Reasoning

The manifest half is a genuine root-cause fix: `read_scaffold_mode` /
`write_scaffold_mode` mirror the existing `read_installed_tiers` /
`write_installed_tiers` pair, the flip is committed only after the copy
succeeds, a project with no `scaffold.json` is correctly left alone, and
`PluginModeConversionTests` (15 tests) covers the flip, idempotency, field
preservation, exit code, and byte-for-byte survival of user docs — with
`test_baseline_manifest_says_plugin_only` pinning the premise so the conversion
test cannot pass for the wrong reason. The docs half is deliberately advisory
per the maintainer's ruling on PR #145, and the record is honest about that
being a warning rather than a closed gap.

The blocking problem is host coverage. The stale-citation scan matches only the
literal `${CLAUDE_PLUGIN_ROOT}`, but Codex plugin-mode docs are rendered with
`${PLUGIN_ROOT}`. On `--host codex` the advisory can therefore never fire —
while the code is shaped as host-aware and the Codex-rendered `SKILL.md` tells
Codex users the warning will be printed.

## Specific issues

- `skills/migrate/migrate.py:1883` — `_PLUGIN_ROOT_TOKEN` is the single
  Claude-only literal `"${CLAUDE_PLUGIN_ROOT}"`. `CodexScaffoldRenderer`
  rewrites `${CLAUDE_PLUGIN_ROOT}` → `${PLUGIN_ROOT}` and bare
  `CLAUDE_PLUGIN_ROOT` → `PLUGIN_ROOT` when emitting docs
  (`scaffold.py:1087`, `1090`, `1186-1191`), so `_stale_plugin_root_docs`
  returns `[]` for every Codex project and `copy-machinery --host codex` prints
  no advisory. Detection must be host-aware the same way the replacement path
  already is.

  Confirmed empirically on `origin/main@f0a5be4`:

  ```
  scaffold.py <dir> --host codex --plugin-only --solo
  #   docs/workflow.md: 4 x ${PLUGIN_ROOT}, 0 x ${CLAUDE_PLUGIN_ROOT}
  migrate.py copy-machinery <dir> --host codex
  #   -> copied machinery into <dir>/.codex
  #   -> scaffold_mode: plugin-only -> in-repo
  #   -> (no warning)                          <-- half two never fires
  ```

  The equivalent Claude run on the same commit names 2 files.

- `skills/migrate/migrate.py:1895-1898` — `_IN_REPO_SKILL_PATH["codex"]` is
  consequently unreachable in practice: it is selected only when
  `resolved_host == "codex"`, which is exactly the case where the scan finds
  nothing.

- `hosts/codex/plugins/jig/skills/migrate/SKILL.md:392` — the shipped Codex
  package states that `copy-machinery` "prints a warning naming each affected
  file and its hit count", which the helper cannot do on Codex. This repeats
  this bug's own recorded learning: a documented contract wider than the
  callee's behaviour.

- `skills/migrate/test_migrate.py:2766` — no test exercises the docs half under
  `--host codex`; every fixture in `PluginModeConversionTests` is a Claude
  scaffold, so the gap above is invisible to the suite.

- `docs/bugs/018-copy-machinery-leaves-mode-inconsistent.md:258` — the
  `## Main recheck` log holds only the `00c3333` entry, but frontmatter carries
  `main_repro_ref: a03f6c8`. `bug.py main-check` appends a line per run
  (`bug.py:603-611`), so the `a03f6c8` recheck exists only as prose; the
  machine-readable trail and the log disagree.

- `docs/bugs/018-copy-machinery-leaves-mode-inconsistent.md:200` vs `:217` —
  "15 tests" versus "5 of 14 failing" on unmodified main. The 15th test
  (`test_codex_render_keeps_the_ask_before_editing_step`) was added after the
  fix and its red state was never witnessed against clean main. The record
  should say so plainly rather than leaving the counts to be reconciled by the
  reader.

## Reconciliation notes

- The `→ FIXING` transition was run with `JIG_BUG_TEST_GATE=0`, so
  `red_confirmed_at` was set without the gate stamping it (`bug.py:702`). This
  is disclosed in the record's `## Proof` section, but it is a gate bypass and
  should be logged as such.
- `fix_class: structural_fix` is recorded while one of the three named
  root-cause locations (rendered docs) is intentionally left to a warning plus
  a `SKILL.md` instruction, per the maintainer ruling quoted on PR #145. That
  deliberate partial closure — and the untaken dispositions 2 and 3 — should be
  logged as a scope deviation.
- `test_codex_render_keeps_the_ask_before_editing_step` self-skips when the
  Codex package is absent (`test_migrate.py:2941-2942`), so the guard against
  silent section deletion is conditional on the committed package being fresh.
- Pre-existing, not introduced here but surfaced by this change:
  `migrate.copy_machinery` does not pass `docs_root` to
  `scaffold.copy_machinery` (defaults to `"docs"`, `scaffold.py:2204`) while
  the new stale-doc scan does resolve the project's configured
  `layout.docs_root` — the two halves disagree about where a `docs_root="."`
  project's docs live.
