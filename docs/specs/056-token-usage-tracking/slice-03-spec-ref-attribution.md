---
status: DONE
dependencies: [056-01]
last_verified: 2026-06-02
---

## Slice 056-03 — `.jig/spec-ref` marker for exact session→spec attribution

**Goal:** Replace the content-heuristic attribution with an explicit
`.jig/spec-ref` marker stamped when work begins on a slice, so the report maps
sessions → specs exactly (and is transparent when it can't).

**DoR:**
- ✅ 056-01 landed (the heuristic attribution this hardens).
- ✅ Stamping point decided (spec Open question — `workflow.py transition …
  IN_PROGRESS` vs worktree creation).

**Acceptance Criteria:**

1. When a slice transitions to `IN_PROGRESS`, `workflow.py transition` writes /
   updates a `.jig/spec-ref` file in the working tree recording the spec number
   (and current slice). Idempotent; never blocks the transition on failure.
2. `usage.py report` **prefers `.jig/spec-ref`** for attribution when present
   in a session's `cwd`, falling back to the 056-01 content heuristic
   otherwise.
3. The report **flags sessions attributed only heuristically** (vs. by marker)
   so the reader knows the confidence of each attribution.
4. No regression to the existing `workflow.py transition` behavior or its
   review-evidence gates (the marker write is additive and side-effect-isolated).

**DoD:**
- [x] All ACs pass; full suite green.
- [x] Coverage: a `.jig/spec-ref`-bearing session attributes by marker; a
      bare session falls back to the heuristic and is flagged; the marker write
      is idempotent and non-blocking; transition gates unaffected.
- [x] Reviewed by `reviewer` subagent; implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Deviation log produced.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if decisions were deferred. (none deferred — N/A)

**Anti-horizontal-phasing check:** After this slice the report's per-spec
attribution is exact (marker-based) where the marker exists, and honestly
flagged where it falls back — the developer trusts the numbers more.

### Deviation log (after reconciliation)

Implemented as specified; all four ACs met (compliance + craft passes both
`pass`, no blockers). Decisions / deviations during implementation:

- **Marker format.** A line-oriented `key=value` file `.jig/spec-ref`:
  `spec=NNN` (the attribution key) + `slice=NNN-NN` (human/debug context).
  Writer (`workflow.py`) and reader (`usage.py`) share the format; the reader
  normalizes `spec=N` → three digits and tolerates a missing `slice=` line.
- **Fifth touched file (`.gitignore`).** Beyond the four enumerated
  deliverables, a *scoped* ignore for `.jig/spec-ref` was added (not a blanket
  `.jig/`), so the already-tracked `.jig/test-command` is unaffected. The marker
  is working-tree-local by design (AC#1/#2) and must not be committed or travel
  across branches.
- **Attribution invariant (load-bearing).** Marker attribution assumes a
  session's `cwd` equals the project root holding `.jig` (the worktree≈root
  model); the writer derives that root from `spec_md.resolve().parents[3]`. A
  spec edited from outside its own worktree would stamp the marker in the spec's
  tree, not the editor's cwd — consistent with the worktree-per-task design.
- **Craft nits addressed.** (1) Reworded the `workflow.py` comment that said the
  marker "follows a committed transition" — the transition writes files, it does
  not `git commit`. (2) Corrected `usage.py`'s module-docstring forward-reference
  ("056-03 will replace this heuristic") to present tense now that the marker is
  live. (3) Kept the single-use `IN_PROGRESS_STATUS` constant the craft pass
  flagged as cosmetic — a named status constant reads clearly and is harmless.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the
      `.jig/spec-ref` shape + stamping point.
- [ ] CLAUDE.md hygiene per spec 025-01 rule (if 056 closes here, compress the
      Active-specs entry).
