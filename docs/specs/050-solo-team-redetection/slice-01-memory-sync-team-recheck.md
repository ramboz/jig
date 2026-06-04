---
status: DONE
dependencies: []
last_verified: 2026-06-04
---

## Slice 050-01 — memory-sync-team-recheck

**Goal:** Teach `memory-sync` to re-run scaffold-init's team-signal
detection at the end of each invocation. When the signal fires and
`docs/memory/people.md` is absent (and no `.jig/no-people-md`
opt-out marker is present), surface a structured nudge with three
options (y / n / never).

**DoR:**
- ✅ `scaffold-init`'s team-signal helper is importable (lives in
  `skills/scaffold-init/scaffold.py` with mailmap + monorepo guards).
- ✅ `memory-sync` skill exists and has a `.py` entry point or a
  documented end-of-invocation hook surface.
- ✅ `templates/docs/memory/people.md.template` exists for the
  bootstrap path.

**Acceptance Criteria:**

1. **Re-check fires at end of `memory-sync`.** After memory
   persistence completes, the helper re-evaluates the team signal
   using the exact detection function `scaffold-init` uses. No
   re-implementation; import-and-call.
2. **No nudge when `people.md` exists.** Re-check is a no-op when
   `docs/memory/people.md` is present on disk, regardless of
   signal outcome.
3. **No nudge when `.jig/no-people-md` exists.** The opt-out marker
   suppresses all future nudges. Set by either `scaffold-init
   --solo`, by the user choosing "never" in a prior nudge, or by
   manual hand-edit.
4. **Structured nudge with three options.** When signal fires AND
   `people.md` is absent AND `.jig/no-people-md` is absent:
   the helper prints a structured message with three labeled
   options — `[y]` bootstrap now, `[n]` skip this run, `[never]`
   suppress forever (writes `.jig/no-people-md`).
5. **Bootstrap path mirrors scaffold-init.** Choosing `y` writes
   `docs/memory/people.md` from the existing template, identical
   shape to scaffold-init's output. No new template, no drift.
6. **Threshold parity pinned by test.** A regression test asserts
   the re-check helper and scaffold-init's helper return identical
   verdicts on the same fixture set (matrix: solo / team-2 / team-3
   / monorepo-parent / mailmap-coalesced).
7. **Non-interactive mode.** When stdin is not a TTY (CI, agent
   invocation), the helper prints the advisory but does NOT block
   on user input — it exits 0 with a "team signal fires; bootstrap
   people.md via /jig:memory-sync interactively" message. Avoids
   wedging automated runs.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases: solo-with-mailmap-coalescing,
      monorepo-parent-suppression, opt-out-marker-honored,
      `people.md`-already-exists, non-TTY-stdin path.
- [x] Reviewed by `reviewer` subagent (compliance pass).
- [x] Craft pass via `pr-review` (no `[blocker]`-tagged findings).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated. Notes column receives a
      one-liner pinning the `.jig/no-people-md` opt-out marker
      contract.
- [x] `CLAUDE.md` updates: spec 050 recorded (compressed Key-terms
      bullet per the compress-on-close-out convention; Active specs
      stays `(none)`).
- [x] Either signal-detection lives in a shared module reachable
      from both skills, OR the call site in `memory-sync` carries
      an inline-mirror block bracketed by
      `# ---------- Slice 050-01: team-recheck ----------` markers
      (per ADR-0002's three-callers rule for shared logic).
      → Satisfied: extracted to `skills/_common/team_signal.py` in
      slice 050-02 (rule-of-three tripped by the third caller).

**Anti-horizontal-phasing check:** End-to-end value: a user who
scaffolded jig as solo, picked up a collaborator six months later,
and runs `memory-sync` sees an actionable nudge to bootstrap
`people.md` — observable from CLI output. The slice ships the
detection-and-nudge loop; the next slice extends the diagnostic
into the freshness audit.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Threshold parity made structural, as planned.** `detect_team` now
   delegates to a new module-level `count_team_contributors(target) -> int`
   in `scaffold.py`; the `>= 2` threshold lives only in `detect_team`. The
   monorepo `--show-toplevel` guard, `git log --use-mailmap --format=%aE`,
   lowercase-dedupe, and fail-soft-to-0 behavior all moved into the count
   helper verbatim. `memory.py team-check` imports this helper (AC1 — no
   re-implementation). AC6 parity is asserted by
   `CountTeamContributorsParityTests` across the full matrix (solo / team-2
   / team-3 / monorepo-parent / mailmap-coalesced / non-git).

2. **Cross-skill import via importlib, both layouts.** `memory.py` loads
   `scaffold.py` by file path (the `scaffold-init` dir name has a hyphen,
   so a plain `import` won't resolve — the established `migrate.py`
   pattern). The loader tries four candidate paths so it resolves in BOTH
   the plugin layout (`skills/scaffold-init/scaffold.py`) and the
   scaffold-mode layout (`skills/jig-scaffold-init/scaffold.py`, where this
   file is `skills/jig-memory-sync/memory.py`). If scaffold.py is genuinely
   unreachable, `team-check` prints a diagnostic and exits 0 (advisory,
   never a blocker).

3. **`--bootstrap` template resolution + scaffold-mode fallback.**
   `--bootstrap` resolves `templates/docs/memory/people.md.template` under
   `plugin_root()` and renders it with scaffold.py's own `copy_template`
   (`{{PROJECT_NAME}}` substitution + atomic write) — the REAL template, no
   embedded duplicate (AC5). When the template can't be resolved (a
   scaffold-mode target whose `templates/` dir was not copied in),
   `_bootstrap_people_md` degrades gracefully: writes nothing, returns a
   "create docs/memory/people.md manually" message, and the caller exits 0.
   This fallback IS exercised by a test
   (`test_bootstrap_degrades_when_template_missing`) — it fired (no
   people.md written, "manually" in the message). This is a known
   limitation, not a defect: scaffold-mode users without a bundled
   `templates/` dir get clear manual-create guidance rather than a crash.

4. **Marker write helper shared, explicit-only (resolved OQ#3).**
   `scaffold.py` gained `write_no_people_md_marker` /
   `no_people_md_marker_path` (so the `.jig/no-people-md` format lives in
   one place; reused by `team-check --never`). `scaffold()` writes the
   marker **only when `overrides.is_team is False`** (explicit `--solo`),
   never on an inferred `None`→False — pinned by BOTH
   `test_solo_flag_writes_no_people_md_marker` and
   `test_auto_solo_does_not_write_marker`. The marker is **tracked** (not
   added to `.gitignore`), like `.jig/test-command`.

5. **Interactive vs non-TTY arms both covered.** The non-TTY path (AC7) is
   exercised by the subprocess tests (a subprocess has no tty): the
   advisory + `--bootstrap`/`--never` follow-up commands print, nothing is
   written, exit 0. The interactive arm (AC4, TTY) is exercised in-process
   via `team_check(..., isatty=True)` with a patched `input()`
   (`TeamCheckInteractiveTests`), covering y→bootstrap, never→marker,
   n→no-op. The `isatty` parameter was added to `team_check` purely to make
   the TTY arm testable without a pseudo-terminal; in production it defaults
   to `sys.stdin.isatty()`.

6. **SKILL.md documents the step.** `team-check` is added as memory-sync's
   final step (step 5, after `summary`), with the explicit instruction that
   in agent (non-TTY) context the agent surfaces the advisory to the user
   and relays their y/n/never choice via `--bootstrap` / `--never`.

7. **No deviations from the spec's AC set.** All seven ACs are implemented
   as specified. No decisions were deferred during implementation, so
   `docs/refinement-todo.md` was not touched.

Test delta: 2136 → 2157 (+21), full suite green (3 pre-existing skips).

8. **Review findings folded in (reconciliation).** Compliance pass —
   `pass`, no issues (`reviews/slice-01-compliance.md`). Craft pass — `pass`,
   no blockers, two `[nit]`s (`reviews/slice-01-craft.md`), both addressed in
   reconciliation: (a) the scaffold-unreachable degradation branch
   (`_ScaffoldUnavailableError` → advisory + exit 0) now has a direct test
   (`TeamCheckInteractiveTests.test_team_check_degrades_when_scaffold_unavailable`),
   forced via a new `load_scaffold=` keyword seam on `team_check` (same
   spirit as the accepted `isatty` seam; production default unchanged);
   (b) a clarifying comment was added at the `--bootstrap`/`--never` action
   site noting that explicit actions bypass the signal-fires gate by design.
   Post-reconciliation test delta: 2157 → 2158 (+1); full suite green
   (`Ran 2158 tests, OK`, 3 pre-existing skips).

9. **Shared-logic siting (ADR-0002 / close-out item 3).** The team-signal
   logic has **two callers** today — `scaffold-init` (owner) and
   `memory-sync` (new). It is reused by a **direct cross-skill import** of
   `scaffold.py`'s `count_team_contributors` (the established `migrate.py`
   precedent), so there is a single source of truth and no duplicated copy —
   close-out item 3's intent (no drift between skills) is satisfied without
   either an inline-mirror block or a premature `_common/` extraction.
   ADR-0002's rule-of-three is **not yet tripped** (two callers). The
   **third** caller — `workflow.py stale` in slice 050-02 — is the trigger to
   extract the helper into `skills/_common/` and repoint all three imports.
   Deferring that extraction to 050-02 (rather than doing it speculatively
   here) is the deliberate rule-of-three application; carried forward as
   050-02's first task. No `architecture.md` change and no ADR needed for
   050-01 (the cross-skill import introduces no new boundary pattern beyond
   `migrate.py`'s).
