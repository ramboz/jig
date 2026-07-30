---
bug: 018
pass: craft
verdict: needs-changes
reviewer: jig:reviewer
reviewed_at: 2026-07-30T19:32:12Z
prompt_source: pr-review skill craft pass
---

Reviewed post-merge, against `origin/main@f0a5be4`. The fix for bug 018 landed
as `dd0d350` (PR #145) without either required review pass being recorded; this
craft pass was run retroactively against the merged deliverable to close that
gap. Methodology: this project's baseline `skills/pr-review/SKILL.md`.

VERDICT: needs-changes

## Reasoning

Part 1 (the manifest flip) is well done: `read_scaffold_mode` /
`write_scaffold_mode` mirror the `read_installed_tiers` /
`write_installed_tiers` pair exactly — same manifest, same `atomic_write_text`,
same commit-only-after-the-copy ordering — the no-manifest case correctly stays
a no-op, and the `hosts/claude` and `hosts/codex` mirrors are byte-consistent
with the sources. Part 2 (the docs advisory) has a real host gap: it detects
only the literal `${CLAUDE_PLUGIN_ROOT}`, but a Codex plugin-mode scaffold
renders its docs with `${PLUGIN_ROOT}` (`scaffold.py:1188` with
`PLUGIN_ROOT_PREFIX`, `scaffold.py:1089`), so the advisory silently produces
nothing for the entire Codex half of the population the fix targets — and the
`codex` branch of `_IN_REPO_SKILL_PATH` is therefore unreachable in practice
and untested. Two of the new tests also pass without exercising the machinery
they claim to pin.

## Specific issues

### Blockers

- `skills/migrate/migrate.py:1883` — `_PLUGIN_ROOT_TOKEN` is a single
  Claude-only literal, but the function is host-aware (`resolved_host` is
  threaded through to `_stale_docs_warning`) and `--host codex` is a supported,
  tested path (`test_migrate.py:1979`). For a project scaffolded
  `--host codex --plugin-only`, `scaffold.py:1186-1191` rewrites
  `${CLAUDE_PLUGIN_ROOT}` → `${PLUGIN_ROOT}` in the emitted docs, so
  `_stale_plugin_root_docs` returns `[]` and no warning is printed. Half two of
  the fix does not fire for Codex projects at all. Detection must be host-aware
  the same way the replacement already is.

- `skills/migrate/migrate.py:1895-1898` — as a consequence,
  `_IN_REPO_SKILL_PATH["codex"]` is dead: it can only be selected when
  `resolved_host == "codex"`, which is exactly the case where the scan finds
  nothing. No test covers it; `test_summary_states_the_replacement_path`
  (`test_migrate.py:2865`) only asserts the Claude form.

- `skills/migrate/SKILL.md:434` — the rendered Codex package
  (`hosts/codex/plugins/jig/skills/migrate/SKILL.md`) carries the same claim
  that `copy-machinery` "prints a warning naming each affected file", which is
  false on Codex given the above. The doc overclaims relative to the code.

### Nits

- `skills/migrate/test_migrate.py:2902-2916` —
  `test_copied_machinery_is_not_reported_as_stale_user_docs` passes vacuously.
  The fixture is a default-`docs_root` project, so the scan roots are `docs/`
  plus the root primers; `.claude/` is structurally out of scope and
  `_STALE_SCAN_SKIP_DIRS` is never consulted. Deleting the whole skip-set would
  leave this test green. It only becomes meaningful with `docs_root="."`.

- `skills/migrate/migrate.py:1901-1924` — `_project_docs_root` (and hence the
  configurable-docs-root behaviour the docstring promises) has no test
  anywhere; no test in `PluginModeConversionTests` builds a track-local
  (`docs_root="."`) project.

- `skills/migrate/migrate.py:1955-1959` — `root.rglob("*.md")` filters
  skip-dirs after the fact rather than pruning, so under `docs_root="."` it
  still descends into `.git`, `node_modules`, `.venv`. The module already has a
  pruning walker (`_walk_text_files` / `_walk`, `migrate.py:1294-1303`) and a
  pruning `_walk_for_files` (`migrate.py:819`). Inconsistent with the file's
  own idiom.

- `skills/migrate/migrate.py:1942` — `path.read_text(errors="replace")` with no
  size cap, where the module's established idiom for exactly this is
  `_safe_read_text(p, max_bytes=200_000)` (`migrate.py:152`).

- `skills/migrate/migrate.py:1901-1924` — second near-duplicate `importlib`
  loader for `_common/project_layout.py` alongside `_validated_docs_root`
  (`migrate.py:199-210`), registering the same file under a second
  `sys.modules` name. The differing failure behaviour is justified in the
  docstring, but the loading boilerplate could be shared.

- `skills/migrate/test_migrate.py:2808-2811` —
  `test_summary_reports_the_mode_flip` asserts `"plugin-only"` and `"in-repo"`
  as independent substrings, weaker than its own negative counterparts at 2829
  and 2843 which assert the full `"plugin-only -> in-repo"` line. Assert the
  line.

- `skills/migrate/test_migrate.py:2817-2820` — the field-preservation check is
  one-directional: it verifies pre-existing keys survive but not that no keys
  were added, while the record claims "field preservation" as coverage.

### Strengths

- The commit-after-the-copy ordering at `migrate.py:2085-2088` is correct and
  consistent with the tier write above it; `read_scaffold_mode` returning
  `None` on a malformed manifest means `write_scaffold_mode`'s unguarded
  `json.loads` can never be reached with unparseable input.
- `test_codex_render_keeps_the_ask_before_editing_step`
  (`test_migrate.py:2931`) guards the rendered artifact rather than the source
  — the right response to a build step that can delete a section and still
  report success.
- `test_stale_docs_are_not_rewritten` (`test_migrate.py:2869`) pins the byte
  survival of user prose with a real hand-written fixture rather than the
  scaffolded default, and the `startswith` check correctly tolerates the
  managed convention-block append.
- Comment density in the new block (`migrate.py:1861-1881`) matches the file's
  norms and records *why* the two halves differ, not just what the code does.

## Reconciliation notes

- The bug record's `## Fix` section says half two "scans the project's own
  markdown … for surviving `${CLAUDE_PLUGIN_ROOT}` citations … plus the
  host-correct in-repo form". The asymmetry should be recorded honestly: the
  *replacement* is host-correct, the *detection* is not, so on Codex the
  advisory never fires. Either fix the detection or scope the record and
  `SKILL.md` explicitly to the Claude host.
- The record's coverage list claims "machinery not being mis-reported as user
  docs" and implies docs-root awareness. Neither is actually pinned by a test
  (see the two nits above). The coverage claim should be narrowed or the tests
  strengthened.
- Worth recording as a learning alongside the existing one: the same "a caller
  widened a callee's contract" pattern recurs here at the host layer — spec
  099-01 made plugin mode the default for *both* hosts, and the fix was written
  against the Claude rendering only.
