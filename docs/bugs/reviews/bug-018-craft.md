---
bug: 018
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T20:23:43Z
prompt_source: pr-review skill craft pass (re-review after follow-up 730bb48)
---

Re-review after the follow-up fix. Supersedes the `needs-changes` verdict
recorded earlier in this file (git history is the audit trail, ADR-0014 §4).
Reviewed against commits `dd0d350` (original, on main) and `730bb48` (the
follow-up). Methodology: this project's baseline `skills/pr-review/SKILL.md`.

VERDICT: pass

## Reasoning

All three blockers from the earlier craft pass are closed, and closed
structurally rather than papered over: detection and replacement are both read
off `scaffold.renderer_for_host(host)` (`migrate.py:1900-1913`), the dead
`_IN_REPO_SKILL_PATH` table is gone, and `SKILL.md:434-437` no longer
overclaims ("the plugin-root variable **this host actually renders**") in both
the source and the Codex render.

Two behavioural questions this raised were verified directly:
`renderer_for_host` is only reached after host validation
(`scaffold.py:2740-2741`, `migrate.py:2058`), so it is behaviourally identical
to the inline branch it replaced; and `PLUGIN_ROOT_PREFIX` / `PLUGIN_ROOT_VAR`
on `ClaudeScaffoldRenderer` are inert for Claude rendering because the only
readers (`scaffold.py:1165`, `1191`) live in
`CodexScaffoldRenderer._rewrite_host_paths`, where `cls` is always Codex.

Five of the six prior nits are fixed with teeth — notably
`test_copied_machinery_is_not_reported_as_stale_user_docs` now runs on a
`docs_root="."` fixture where `.claude/skills/jig-{scaffold-init,migrate,
analyze}/SKILL.md` really do retain `${CLAUDE_PLUGIN_ROOT}/templates/`
citations, so deleting the skip-set would now fail it. Remaining items are nits
only.

## Specific issues

### Nits

- `skills/migrate/migrate.py:1968-1981` — the prune walk uses `entry.is_dir()`,
  which follows directory symlinks; the `root.rglob("*.md")` it replaced never
  descended into symlinked dirs. Under `docs_root="."` a symlink cycle now loops
  and a symlink to a large tree is traversed. It matches the module's own idiom
  (`_walk_text_files:1303-1310`), so this is consistency-with-existing-warts
  rather than a new class of bug — but it is a behaviour change against the code
  replaced, and unlike `_walk_for_files:819` there is no depth bound on a scan
  whose root can be the whole project.

- `skills/migrate/test_migrate.py:3087-3098` — nothing pins that the *printed*
  replacement contains `<name>`. `test_in_repo_replacement_path_tracks_the_
  renderer` re-applies the production transform (`.replace("\\1", "<name>")`,
  mirroring `migrate.py:1913`), and the two output tests stop at the `jig-`
  prefix (`test_migrate.py:2876`, `3030`). If a renderer template ever used
  `\g<1>` instead of `\1`, users would see `jig-\1/` in the warning with the
  whole suite green.

- `skills/migrate/migrate.py:1916-1939` — previously flagged, unresolved: still
  a second near-duplicate `importlib` loader for `_common/project_layout.py`
  alongside `_validated_docs_root` (`migrate.py:199-210`), registering the same
  file under a second `sys.modules` name. The differing failure semantics
  (degrade to `"docs"` vs raise) are correctly justified in the docstring; only
  the ~10 lines of loader boilerplate are duplicated.

- `skills/scaffold-init/scaffold.py:1564-1567` — `renderer_for_host` silently
  falls back to Claude for an unknown host, while the module's other host entry
  points raise `ValueError` (`scaffold.py:2741`, `2278-2279`). Unreachable
  today because every caller validates first, but the fix's own thesis is "one
  place owns host → renderer", and that one place is the most permissive of the
  three.

- `skills/scaffold-init/scaffold.py:1010` — `PLUGIN_ROOT_VAR` on the base class
  is read by no Claude code path and by nothing in this fix; only
  `PLUGIN_ROOT_PREFIX` is consumed by `migrate.py`. Defensible as base/subclass
  symmetry, but it is an unread constant added by this change and the comment at
  `1003-1008` justifies only the prefix.

## Reconciliation notes

- The `hosts/claude/` and `hosts/codex/` mirrors are in sync with the sources
  for every changed line checked (identical line numbers and content at
  `migrate.py:1886`, `1903`, `1912-1913`, `1980` and `scaffold.py:1009-1010`,
  `1097-1098`, `1558-1567`), and the Codex-rendered `SKILL.md:370-415` carries
  the reworded advisory section.
- Test counts in the bug record's regression table are accurate as written:
  `PluginModeConversionTests` 14, `CodexPluginModeConversionTests` 11,
  `CopyMachineryStaleScanScopeTests` 3 = 28. The "15/15" in `## Proof` is the
  pre-follow-up count and reads as a historical first-cycle record.
- `_STALE_SCAN_SKIP_DIRS`'s comment (`migrate.py:1883-1885`) says the host
  runtime dirs hold "jig-owned machinery that THIS command just refreshed".
  Worth recording that the refresh does not make those files path-correct:
  `_copy_skill_dir` rewrites only `${CLAUDE_PLUGIN_ROOT}/skills/<name>/`
  (`scaffold.py:852-854`), so the copied `jig-scaffold-init/`, `jig-migrate/`,
  and `jig-analyze/` SKILL.md keep a `${CLAUDE_PLUGIN_ROOT}/templates/` citation
  that is unset in in-repo mode. A separate pre-existing defect, correctly out
  of scope for bug 018 — but the comment reads as though the skip is safe
  because the files are correct, when the real reason is that they are jig's
  problem, not the user's.
- The `Learning` entries in `docs/memory/learnings.md:758-789` are faithful to
  what was built and honest about the recurrence; no drift between them and the
  code.
