---
slice: 099-01 — default-plugin-mode
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-30T16:49:53Z
prompt_source: craft review of slice 099-01 deliverables (4 independent rounds)
---

Independent craft review of slice 099-01, run as four rounds.

Rounds 1-3 returned `needs-changes`; round 4 returned `pass`.

**Judged sound:** `_rewrite_host_paths` is a clean seam — one body, mode-keyed
constants, two thin named wrappers, no boolean trap at the call sites — so the
host-vocabulary rules cannot drift between modes. The flag surface is aliased by
construction rather than by duplicated logic. The shipped-package fixture reads
symmetrically as a `(mode_flag, expect, forbid)` table and pins the actual defect
(docs citing a tree that was never created) rather than a string.

**Blockers found and fixed across the rounds:**

- A class docstring contradicting the first test inside it — it said plugin mode
  writes no `settings.json`, three lines above a test asserting it does.
- `SKILL.md`'s Output section omitting the `settings.json` the default path now
  writes, then — once fixed — naming a host inside a machine-translated
  conditional, which inverted on the Codex render.
- `test_default_mode_permissions_write_preserves_user_settings` passing
  `--force`, which also overrides the unmanaged-hooks refusal, so the test could
  not prove the "plugin mode stays refusal-free" property its own docstring
  claims. Dropping the flag made it prove it.

**Nits, applied:** ~110 lines of review-round narration in `scaffold.py` — a
verbatim third copy of the deviation log, citing "round 2" that no reader can
resolve, and contrasting strings that no longer exist. The repo's house style is
comment-heavy but cites slices and ADRs, not review rounds; scope and limits kept
(a caller genuinely must know what the detector misses), history cut. Plus an
orientation comment pointing "above" at constants below it, a duplicated
read/parse/raise block including its error string (extracted to
`_read_settings_json`), `--plugin-only`'s help understating what the path writes,
three tests pinning one fact, an ad-hoc tempdir beside a sibling using the class
fixture, and a note-test assertion that held whether or not the note fired.

**Stale framing, and the blind spot it exposed:** `PluginOnlyOptOutTests` and its
banner still described `--plugin-only` as an *opt-out* from an in-repo default —
true under 016-03, false the moment this slice flipped the default back, at which
point the flag opts out of nothing. The in-body comments had been updated; the
class name and docstring had not. **The reconciliation sweep enumerates docs and
never reaches the test suite's own prose** — arguably worse, since a class name
is what the next contributor reads first.

**Comment value, asked explicitly and answered both ways:** the remaining large
blocks earn their place — `_write_permissions_deny_floor`'s docstring justifies
two deliberate omissions (`_merge_settings`, the `UnmanagedHooksError` check)
that a future reader would otherwise "fix", and the mode-line↔note coupling
warning states an invariant the code cannot. What did not earn its place was the
process history, and it was removed.

**Deferred with rationale rather than fixed:** `rewrite_skill_md_paths`
(artifact-named) vs `rewrite_doc_paths_plugin_mode` (mode-named) do not parallel,
but the former is a pre-existing public override referenced by
`scripts/build_codex_plugin.py` and ADR-0038, so the rename is cross-cutting and
does not belong in a slice about a default flag. Entered in `refinement-todo.md`
with a trigger so the next renderer-touching slice picks it up.
