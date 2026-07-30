---
bug: 018
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T20:23:43Z
prompt_source: review.py bug-review docs/bugs/018-copy-machinery-leaves-mode-inconsistent.md skills/migrate/migrate.py skills/scaffold-init/scaffold.py skills/migrate/SKILL.md skills/migrate/test_migrate.py (re-review after follow-up 730bb48)
---

Re-review after the follow-up fix. Supersedes the `needs-changes` verdict
recorded earlier in this file (git history is the audit trail, ADR-0014 §4).
Reviewed against commits `dd0d350` (original, on main) and `730bb48` (the
follow-up).

VERDICT: pass

## Reasoning

Both blocking issues from the earlier bug-review are genuinely fixed, not
relocated: `_plugin_root_token` / `_in_repo_skill_path`
(`skills/migrate/migrate.py:1900-1913`) read `PLUGIN_ROOT_PREFIX` /
`SKILL_PATH_REPLACEMENT` off `scaffold.renderer_for_host(host)`, and for Codex
that is the *same* constant `_rewrite_host_paths` uses to emit the docs
(`scaffold.py:1165`, `1191`, `1196`), so detection and rendering can no longer
disagree. The Claude side is additionally pinned end-to-end by a real scaffold
fixture.

`CodexPluginModeConversionTests` (11 tests) exercises the previously-dark host,
and the recorded second red (4 FAIL + 2 ERROR) is consistent with the
pre-change code — the two `ERROR`s are exactly the two helpers that did not yet
exist.

Blast radius is contained: `ClaudeScaffoldRenderer.PLUGIN_ROOT_PREFIX` /
`PLUGIN_ROOT_VAR` are read by no Claude render path and are shadowed by Codex's
own overrides, and `renderer_for_host` is an exact substitution for the inline
ternary with `scaffold()` still validating the host first
(`scaffold.py:2740`). The record's correction of the earlier
drift-guard/bug-008 claim is honest, and its "the gate runs the whole suite
regardless of the selector" claim checks out (`.jig/test-command` →
`run_tests.py:162-165` ignores argv).

Reviewer is read-only, so the suite was not executed; green counts were
assessed only for internal consistency.

## Specific issues (all non-blocking)

- `docs/bugs/018-copy-machinery-leaves-mode-inconsistent.md:288` — "Green
  after: `PluginModeConversionTests` 15/15 OK" is stale relative to the current
  14-test class. *Addressed after this review*: the paragraph is now explicitly
  marked as the first cycle's historical record and states the current count.

- `skills/migrate/migrate.py:2119,2123` — the host is taken from the invocation
  (`_resolve_host`, inferred from where `migrate.py` lives,
  `migrate.py:50-61`), not from the project's own `host_renderer` field
  (`scaffold.py:2680`). Running a Codex-installed helper against a
  Claude-scaffolded plugin-mode project flips `scaffold_mode` while scanning
  for `${PLUGIN_ROOT}` in Claude-rendered docs → advisory silently empty.
  Narrower than the fixed defect, but the same class, and the manifest already
  records the answer. **Follow-up, own record.**

- `skills/migrate/migrate.py:2090-2093` — `docs_root` is still not forwarded to
  `scaffold_mod.copy_machinery` (default `"docs"`, `scaffold.py:2224`), while
  the new scan resolves the configured root (`migrate.py:1951`). On a
  `docs_root="."` project this makes `_ensure_self_defining_convention_block`
  (`scaffold.py:2294`, `2516-2534`) create a spurious `docs/workflow.md` next to
  the real root-level one. Pre-existing and flagged by the prior review; the new
  `CopyMachineryStaleScanScopeTests` fixture is precisely that shape and asserts
  nothing about it. **Follow-up, own record.**

- `skills/migrate/test_migrate.py:3071-3098` — the two anti-drift guards mirror
  the one-line implementations exactly (`.replace("\\1", "<name>")` on both
  sides), so they cannot catch a renderer changing its template form (e.g.
  `\g<1>`); they only catch a re-introduced literal table. The real host
  coverage is the end-to-end tests above them. Fine as written, but they are not
  the drift guard on their own.

- `skills/scaffold-init/scaffold.py:1009-1010` — `PLUGIN_ROOT_VAR` on the Claude
  renderer is read by nothing (only Codex's override at `:1098` is consumed, at
  `:1166`), and `PLUGIN_ROOT_PREFIX` restates the literal already embedded in
  `PLUGIN_HOOK_SCRIPT_PREFIX` (`:1001`). Symmetry is defensible; for Claude the
  constant remains a restatement of the templates, guarded by the end-to-end
  test rather than structurally.

- `skills/migrate/test_migrate.py:2940-2941` — carried over unresolved: the
  rendered-artifact guard self-skips when the committed Codex package is
  absent, so protection against silent section deletion is conditional on
  package freshness.

## Reconciliation notes

- `fix_class: structural_fix` covers two of the three named root-cause
  locations; the rendered docs are deliberately left to an advisory plus a
  `SKILL.md` instruction per the maintainer ruling on PR #145. Dispositions 2
  and 3 untaken. A deliberate scope deviation.
- The `→ FIXING` transition ran with `JIG_BUG_TEST_GATE=0`, so
  `red_confirmed_at` was stamped without the gate (`bug.py:686-702`). Disclosed
  in `## Proof`; a gate bypass.
- `main_repro_ref: a03f6c8` has no matching `## Main recheck` line; the record
  now discloses this as a bookkeeping gap and declines to back-date.
- `regression_test` frontmatter names only `PluginModeConversionTests`; the
  second cycle's real evidence is `CodexPluginModeConversionTests`. Safe here
  only because this repo's `.jig/test-command` runs the whole suite. The
  selector under-names the guard; the record's `## Regression test` table
  states this explicitly.
- Two follow-ups worth their own records, not this one: (a) resolving the
  advisory's host from the project's `host_renderer` instead of the invocation;
  (b) `migrate.copy_machinery` forwarding `docs_root` to
  `scaffold.copy_machinery`.
