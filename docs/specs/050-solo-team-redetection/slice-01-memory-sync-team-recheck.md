---
status: DRAFT
dependencies: []
last_verified:
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
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases: solo-with-mailmap-coalescing,
      monorepo-parent-suppression, opt-out-marker-honored,
      `people.md`-already-exists, non-TTY-stdin path.
- [ ] Reviewed by `reviewer` subagent (compliance pass).
- [ ] Craft pass via `pr-review` (no `[blocker]`-tagged findings).
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated. Notes column receives a
      one-liner pinning the `.jig/no-people-md` opt-out marker
      contract.
- [ ] `CLAUDE.md` updates: spec 050 added to Active specs.
- [ ] Either signal-detection lives in a shared module reachable
      from both skills, OR the call site in `memory-sync` carries
      an inline-mirror block bracketed by
      `# ---------- Slice 050-01: team-recheck ----------` markers
      (per ADR-0002's three-callers rule for shared logic).

**Anti-horizontal-phasing check:** End-to-end value: a user who
scaffolded jig as solo, picked up a collaborator six months later,
and runs `memory-sync` sees an actionable nudge to bootstrap
`people.md` — observable from CLI output. The slice ships the
detection-and-nudge loop; the next slice extends the diagnostic
into the freshness audit.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._
