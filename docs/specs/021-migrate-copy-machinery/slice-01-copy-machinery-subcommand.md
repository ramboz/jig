---
status: DONE
dependencies: [016-02, 016-03, 008-05]
last_verified: 2026-05-15
---

## Slice 021-01 — copy-machinery-subcommand

**Goal:** Add `migrate.py copy-machinery <project-dir> [--force]` that
copies skills + agents + hooks + settings.json into the target
project's `.claude/`, reusing scaffold.py's machinery-copy helpers
verbatim via a new public `copy_machinery()` façade. After this slice,
`/jig:migrate` users get the same `.claude/` shape that
`/jig:scaffold-init` produces by default.

**DoR:**
- ✅ scaffold.py exposes `_copy_skills_and_agents` and
  `_copy_hooks_and_register` as small testable helpers (already true
  per slices 016-01 / 016-02).
- ✅ `UnmanagedHooksError` is a module-level class importable from
  `skills.scaffold-init.scaffold` (already true per slice 016-02).
- ✅ `migrate.py` has the subcommand-registration shape (report /
  rename-decisions / split-slices) that the new subcommand will
  follow.
- ✅ The plugin-root location convention (`plugin_root()` fallback
  on `Path(__file__).resolve().parents[N]`) is already used by all
  jig helpers — no new self-location machinery needed.

**Acceptance Criteria:**

1. **Public façade exists.** `skills/scaffold-init/scaffold.py`
   exposes a public `copy_machinery(plugin: Path, target: Path, *,
   force: bool = False) -> None` function that calls
   `_copy_skills_and_agents(plugin, target)` then
   `_copy_hooks_and_register(plugin, target, force=force)` in that
   order (matching the order in `scaffold()` at lines 752–760).
   The existing `scaffold()` body is refactored to call
   `copy_machinery()` for the two lines it replaces — no behavior
   change for scaffold-init.
2. **New subcommand registered.** `migrate.py` registers a
   `copy-machinery` subparser via `add_parser("copy-machinery",
   ...)` alongside the three existing subcommands. It accepts a
   positional `project_dir` and a `--force` flag (mirroring
   scaffold-init's `--force` semantics).
3. **Subcommand calls the façade.** `main()`'s `cmd ==
   "copy-machinery"` branch resolves the plugin root via the same
   `plugin_root()` convention scaffold.py uses, then calls
   `copy_machinery(plugin, project_dir, force=ns.force)`.
   Exit 0 on success.
4. **UnmanagedHooksError refuses cleanly.** When the target's
   `.claude/settings.json` has hooks without the `managed_by_jig`
   marker, `copy-machinery` exits non-zero (exit code 3, matching
   `LooksAlreadySpecDrivenError` precedent from 008-05) and the
   error message names `--force` as the documented escape. The
   refuse-message is rendered to stderr; stdout stays empty.
5. **Pre-existing scaffold-mode install is idempotent.** Running
   `copy-machinery` against a project whose `.claude/skills/jig-*`
   already exists overwrites the copied files in place (matching
   the behavior of re-running `scaffold-init --force`), and the
   settings.json merge runs `_merge_settings`'s
   replace-in-place-by-marker logic. No partial state is left
   behind.
6. **Report's Operations section suggests the new subcommand.**
   `render_operations` (migrate.py:423) gains a new item that
   surfaces when `verdict in {"adoptable", "partial"}` AND the
   target's `.claude/skills/` does not already contain at least one
   `jig-*` skill dir. Item text: **`migrate.py copy-machinery
   <project-dir>`** — copy jig's hooks / agents / skill helpers
   into the target's `.claude/` (scaffold-mode parity).
7. **SKILL.md documents the subcommand.** A new `## Copying
   machinery into your project` section in `skills/migrate/SKILL.md`
   covers when to use it (after a successful `rename-decisions` /
   `split-slices` run, or as a standalone op), the `--force`
   escape, and the relationship to spec 016's scaffold-mode.
8. **End-to-end fixture test.** A new `CopyMachineryTests` class in
   `test_migrate.py` invokes `copy-machinery` against a tmpdir
   spec-driven fixture and asserts (a) `.claude/skills/jig-migrate/`
   exists with a rewritten SKILL.md, (b) `.claude/hooks/scripts/`
   contains at least one `jig-*.sh` script with 0o755 perms, (c)
   `.claude/settings.json` exists and every hook entry carries the
   `managed_by_jig: true` marker, (d) the UnmanagedHooksError
   refusal path returns exit 3 with the documented message
   substring, and (e) re-running on a `.claude/` already populated
   by a prior run is idempotent (no diff in skills, hooks, or
   settings.json).
9. **Operations-section test.** A test asserts the new operations
   item appears in `report` output for an `adoptable`-verdict
   fixture WITHOUT pre-existing `jig-*` skills, AND is suppressed
   for the same fixture WITH pre-existing `jig-*` skills.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. The five sub-cases under AC #8 each get their own
      test method.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. _(no items deferred during
      implementation — parked items in deviation §6 are reviewer
      cosmetic notes, not deferred decisions)_

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `CLAUDE.md` updates: hot-cache entry for spec 021; migrate
      Skills-table row updated to mention `copy-machinery`.
- [x] Dogfood: run `migrate.py copy-machinery` against a real
      spec-driven project (e.g. shallow-validator post-M1) and
      confirm the resulting `.claude/` matches what
      `scaffold-init --with-machinery` would produce on a
      greenfield. Log result in the deviation log. _(Dogfooded
      2026-05-15 against aso-shallow-validator's spec-driven shape
      cloned to tmpdir — see deviation §9.)_

**Anti-horizontal-phasing check:** A `/jig:migrate` user runs
`migrate.py copy-machinery <project-dir>` and ends with a
project-local `.claude/skills/jig-*/`, `.claude/agents/jig-*.md`,
`.claude/hooks/scripts/jig-*.sh`, and a `.claude/settings.json` that
registers jig's hooks against project-relative paths — exactly the
shape `scaffold-init --with-machinery` produces today. That's
end-to-end user value, not intermediate state.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **SKILL.md section placement split.** AC #7 named a `## Copying
   machinery into your project` H2 section. The natural in-`## How to
   use` placement would have demoted the trailing `### Exit codes` /
   `### Verdict logic` / `### Report structure` H3 subsections under
   the wrong H2 semantically. Implementer split the difference: the
   full H2 lives between `## End-to-end example` and `## Agentic
   slice-to-spec migration`, while a short `### Run the
   copy-machinery operation` quick-reference lives inside `## How to
   use` alongside `### Run the migration report` / `### Run the
   rename-decisions migration`. Both pieces of prose are
   discoverable. AC #7 satisfied; no AC change required.

2. **Subcommand code path lives below the SAFETY_SENTINEL marker.**
   The new `copy_machinery()` function in migrate.py is below the
   safety regex sweep boundary because it mutates the filesystem
   (delegating to scaffold.copy_machinery). Correct placement.

3. **scaffold module loaded via `importlib.util.spec_from_file_location`,
   not namespace-package import.** The slice spec was silent on import
   mechanics. `skills/scaffold-init/` contains a hyphen, so the
   dotted-name import `skills.scaffold-init.scaffold` only works when
   migrate.py is loaded as part of the `skills` package
   (`python3 -m unittest`); it breaks when migrate.py is invoked as a
   script (`python3 migrate.py …`). File-path loading via
   `importlib.util` works in both invocation shapes — same pattern
   `skills/scaffold-init/test_scaffold.py:1021` uses internally.

4. **`type(exc).__name__ == "UnmanagedHooksError"` (initial) →
   `isinstance` via typed migrate-side exception (post-review).**
   Implementer's first pass identified the scaffold-side
   `UnmanagedHooksError` by class-name string match inside main()'s
   except clause, on the reasoning that `scaffold_mod` was loaded
   lazily inside `copy_machinery()` and not in main()'s scope.
   Implementation reviewer flagged this as brittle (false-negative on
   subclasses, false-positive on any unrelated class with the same
   name). **Addressed during reconciliation prep:** introduced
   `MigrateMachineryRefusalError(RuntimeError)` at module top,
   `copy_machinery()` now catches `scaffold_mod.UnmanagedHooksError`
   using true `isinstance` (scaffold_mod is in scope at that point)
   and re-raises as the typed migrate-side exception. main()'s
   exception chain routes via `except MigrateMachineryRefusalError`
   to exit 3. Identical user-facing behavior, structurally sound
   discrimination.

5. **AC #6 partial-verdict branch not test-covered in implementer's
   first pass.** Reviewer flagged: `CopyMachineryOperationsTests`
   only exercised the `adoptable` verdict branch of AC #6's
   `verdict in {"adoptable", "partial"}` condition. **Addressed
   during reconciliation prep:** added
   `test_operations_section_suggests_copy_machinery_on_partial_verdict`
   that seeds specs + decisions only (no workflow.md /
   architecture.md) to produce exactly two `compute_verdict`
   triggers → partial, then asserts `copy-machinery` appears in
   Operations and exit code is 1 (partial-verdict convention).

6. **Reviewer findings parked (non-blocking).**
   - `_load_scaffold_module()` is called on every `copy_machinery()`
     invocation with no caching. Inconsequential for one-shot CLI
     use. No inbox entry.
   - `test_migrate.py` uses
     `importlib.import_module("skills.scaffold-init.scaffold")` (with
     a hyphenated path) in BOTH `CopyMachineryTests.test_public_facade_is_importable_from_scaffold`
     AND `CopyMachinerySkillSurfaceTests` — works today via
     namespace-package semantics but structurally inconsistent with
     the file-path loader used in production (deviation §3). Left
     as-is across both test classes. _(Reconciliation reviewer
     noted the original deviation §6 wording understated the
     scope.)_
   - `scaffold.py`'s new `copy_machinery` is not in any `__all__`.
     jig modules don't use `__all__` consistently. No change.

7. **`scaffold()` refactor — zero behavior change for scaffold-init.**
   AC #1's "no behavior change" was verified by re-running the full
   suite (808 green, 3 skipped) including `test_scaffold_mode.py`'s
   machinery-copy tests after the refactor.

8. **Test count delta.** 794 → 808 (+14): 9 in `CopyMachineryTests`,
   3 in `CopyMachineryOperationsTests` (2 from implementer + 1
   partial-verdict added during reconciliation), 2 in
   `CopyMachinerySkillSurfaceTests`. AC #8's five sub-cases each
   map to a dedicated test method (`test_8a_…` through
   `test_8e_…`).

9. **Live dogfood against aso-shallow-validator (2026-05-15).**
   Ran four scenarios against real filesystem state, all green:
   - **AC #9 suppression (live):** `migrate.py report` against
     `/Users/ramboz/Projects/misc/aso-shallow-validator` (which has
     12 pre-existing `.claude/skills/jig-*/` dirs) produced an
     Operations section with the empty-state message and **no**
     `copy-machinery` suggestion. ✓
   - **AC #6 surface + AC #1/#2/#3/AC #8a-c (live):** Cloned the
     project's spec-driven shape (`docs/` + `CLAUDE.md`) to a
     tmpdir with no `.claude/`. `report` then surfaced
     `copy-machinery` as Operations item #1. Running the
     subcommand exited 0 and produced 12 jig-* skill dirs + 3
     jig-* agents + 5 hook scripts (rwxr-xr-x, 0o755) + a valid
     settings.json with the `managed_by_jig` marker on all 5 hook
     entries — byte-shape identical to what `scaffold-init
     --with-machinery` would produce. ✓
   - **AC #5 idempotency (live):** Re-ran on the same tmpdir;
     SHA-256 of `settings.json`, a representative SKILL.md, and a
     hook script were identical across runs (zero byte diff). ✓
   - **AC #4 refusal (live):** Seeded a fresh tmpdir with a
     `.claude/settings.json` carrying a non-jig hook entry. Ran
     `copy-machinery`; exit 3, stderr named `--force` as the
     documented escape, and `settings.json` was preserved
     byte-for-byte. ✓

10. **Two pre-existing rough edges surfaced by live dogfood
    (filed to inbox, not addressed in this slice).**
    - **Inventory row for `jig_skill_dirs` not rendered.** A
      project with 12 jig-* skill dirs has no `.claude/skills/`
      row in the report's Inventory section, because
      `render_inventory` only emits a row when `inv.custom_skills`
      (top-level `.md` files in `.claude/skills/`, almost always
      empty) is non-empty. AC #9 suppression therefore looks
      "silent" — the user has no in-report explanation for why
      Operations doesn't suggest `copy-machinery`. Logged to
      `docs/inbox.md`. Polish, not a correctness gap (ACs all
      pass); recommend adding a separate Inventory row for
      `jig_skill_dirs` in a follow-up touch.
    - **Partial-state-on-refuse inherited from scaffold-mode.**
      When the hooks safety check refuses (UnmanagedHooksError),
      `_copy_skills_and_agents` has already run because the two
      copies execute sequentially inside `copy_machinery`. Result
      on a pre-seeded refuse target: `.claude/skills/` and
      `.claude/agents/` written; `.claude/hooks/` and
      `settings.json` correctly untouched. Same pre-existing rough
      edge noted in 016-03 deviation §7. Logged to
      `docs/inbox.md`. Fix shape: extract the safety check into a
      `precheck()` callable that runs at top of `copy_machinery`
      before any write. Not in scope for 021-01.
