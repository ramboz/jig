---
status: READY_FOR_REVIEW
dependencies: [056-01]
last_verified:
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
- [ ] All ACs pass; full suite green.
- [ ] Coverage: a `.jig/spec-ref`-bearing session attributes by marker; a
      bare session falls back to the heuristic and is flagged; the marker write
      is idempotent and non-blocking; transition gates unaffected.
- [ ] Reviewed by `reviewer` subagent; implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if decisions were deferred.

**Anti-horizontal-phasing check:** After this slice the report's per-spec
attribution is exact (marker-based) where the marker exists, and honestly
flagged where it falls back — the developer trusts the numbers more.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records the
      `.jig/spec-ref` shape + stamping point.
- [ ] CLAUDE.md hygiene per spec 025-01 rule (if 056 closes here, compress the
      Active-specs entry).
