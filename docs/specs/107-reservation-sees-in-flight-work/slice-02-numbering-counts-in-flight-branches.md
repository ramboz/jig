---
status: DONE
dependencies: [107-01]
last_verified: 2026-08-14
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 107-02 — numbering counts every in-flight branch

**Goal:** The next reserved number accounts for claims sitting on any branch —
local or remote-tracking — not only files already merged to `origin/main`. Two
sessions reserving the same number, the failure the whole mechanism exists to
prevent, stops being reachable through an unmerged reservation.

**Decision:** [ADR-0053](../../decisions/adr-0053-reservation-numbering-sees-in-flight-branches.md)
(Option C).

**DoR:**
- ✅ All three push-mode numbering paths derive the next id from a single
  `origin/main` view: `bug.py:_next_number` on the detached worktree
  (`skills/bug-fix/bug.py:352`), `adr.py` `max(_parse_adr_number …)+1`
  (`skills/adr-workflow/adr.py:553-556`), `workflow.py:_next_spec_number(…,
  use_origin=True)` (`skills/spec-workflow/workflow.py:3810`).
- ✅ `git ls-tree --name-only <ref> -- docs/<x>/` lists the immediate children
  of a docs directory on any ref without checkout — probed 2026-07-31 against
  `origin/main` (spec dirs) and 91 local+remote refs enumerable via
  `git for-each-ref refs/heads refs/remotes`.
- ✅ Reservation branch names do not carry the number for the common case
  (assumption A2) — the scan must read trees, not ref names.
- ✅ `skills/_common/reservation.py` exists after slice 107-01 and is the home
  for this scanner.

**Assumptions:** A1, A2 from [spec 107](./spec.md#assumptions).

**Acceptance Criteria:**

1. **The next number is the max across every readable ref, plus one.**
   `scan_max_reserved_number(project_dir, "docs/bugs", <NNN-re>)` returns the
   highest `NNN` found in the working tree, on any local branch
   (`refs/heads/*`), and on any remote-tracking branch (`refs/remotes/*`). Given
   a repo where `origin/main` holds bug 023 and an unmerged branch holds bug
   024, reservation allocates 025 — not 024.

2. **All three families use it in coordinating modes.** `bug.py` push/pr,
   `adr.py` push/pr, and `workflow.py` push/pr compute their next id through the
   shared scanner (widths: bugs/specs `\d{3}`, ADRs `\d{4}`). The `--no-push`
   local-only paths keep working-tree-only semantics — they publish nothing, so
   they carry no team-coordination contract (matches the existing
   `_next_spec_number` `use_origin` split).

3. **Offline degrades loudly, never fails.** A best-effort `git fetch` precedes
   the scan; if it fails, the scan proceeds over the refs already in the local
   cache and writes one warning to stderr. If ref enumeration itself fails, the
   scanner falls back to the working-tree / `origin/main` view (current
   behaviour) and warns. Numbering never raises because the network is down.

4. **A ref with no docs directory contributes nothing.** `git ls-tree` on a ref
   that lacks `docs/<x>/` (empty output, non-zero rc, or a detached lineage)
   is skipped silently — it is not an error, it contributes 0.

5. **Non-conforming entries are ignored.** `README.md`, `reviews/`, files that
   don't match the `NNN-` / `adr-NNNN-` shape, and directories with the wrong
   digit width do not affect the maximum (same regex as the working-tree scan).

6. **The #161/#162 shape is closed.** A regression test reproduces two
   sequential reservations against a repo whose only difference between calls is
   a reservation branch pushed by the first call; the second call returns the
   next number, not a duplicate. Built with local bare repos, no network.

7. **Host packages regenerated.** `scripts/build_host_packages.py` reproduces
   `hosts/claude/` and `hosts/codex/` with no diff after the change.

**Definition of Done:**
- [x] `scan_max_reserved_number` in `skills/_common/reservation.py`, covered by
      `test_reservation.py` for AC1, AC3, AC4, AC5 against local git fixtures.
- [x] `bug.py`, `adr.py`, `workflow.py` push/pr paths call it; `--no-push`
      paths unchanged.
- [x] AC6 regression test lives with the family it most directly reproduces
      (`test_adr.py`, matching the observed #161/#162 incident); proven red
      before the fix, green after.
- [x] Refinement-todo entry recording ADR-0053 Option D (atomic claim ref) as
      deferred, with a resolution trigger: a duplicate number observed after
      this ships.
- [x] Host mirrors regenerated; `run_tests.py` green.

**Non-goals:** fork branches (invisible to `git ls-remote origin`); the atomic
claim ref (Option D, deferred); capping the scan for repos with hundreds of
branches (noted in ADR-0053 kill criteria, not built).

### Deviation log

> Recorded post-hoc for lifecycle close-out. This slice shipped and was
> reconciled in-band on [PR #165](https://github.com/ramboz/jig/pull/165)
> (merged to `main` as `409ba19`); the subsections below capture that trail so
> the RECONCILED → DONE transition passes ADR-0014 §5 on real evidence rather
> than a gate bypass.

- **Scan folded in additively at the call sites, not inside `_next_spec_number`.**
  Rather than rewrite the well-tested `_next_spec_number(use_origin=…)` internals
  (spec 037 contract), each push call site takes `max(existing_number,
  scan + 1)`. The scan uses the helper's own `_run` (injected via `run=`) so the
  existing mocked reservation tests intercept its git calls the same way they
  already do — the scan is inert (no refs) under those stubs, and the spec-037
  contract is untouched.
- **Two `git fetch` calls in push mode.** The reserve helpers already fetch
  `origin main` before building the detached worktree; the scan then does a
  best-effort full `git fetch --quiet` to see sibling reservation branches. The
  redundant targeted fetch is left in place (cheap, and removing it would touch
  the tested preflight flow).

### Reconciliation sweep

Recorded post-hoc (see the note above); dispositions reflect what #165 landed.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/_common/reservation.py` + host mirrors | `updated` | `scan_max_reserved_number` added and wired into the `bug.py` / `adr.py` / `workflow.py` push/PR paths; mirrors regenerated at merge. |
| `docs/specs/README.md` | `deferred` | Status-board row still showed IN_PROGRESS post-merge; regenerated during this close-out pass. |
| `docs/refinement-todo.md` | `updated` | ADR-0053 Option D (atomic claim ref) recorded as deferred, with a resolution trigger: a duplicate number observed after this ships. |
| `docs/decisions/` (ADR-0053) | `no-op` | Decision recorded before implementation; the deferred option is tracked in refinement-todo, not a new ADR. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `no-op` | Spec 107 still in flight at merge; no primer compression due. |
