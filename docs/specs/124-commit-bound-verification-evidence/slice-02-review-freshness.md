---
status: DRAFT
dependencies: [adr-0069, 124-01]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 124-02 — review-freshness

**Goal:** a slice's review verdict records say which commit and which
deliverable bytes the reviewer was shown, and jig reports a `pass` whose
deliverables have changed since, at the transition, in `check-reviews`, and
before landing. It reports; it does not block.

**Decision:** spec 124 D2 + D3 / ADR-0069 decisions 1–2. Extends ADR-0014 §2
with optional fields; §3 and §4 are unchanged.

**DoR:**
- ✅ Every prompt builder that reviews code already receives the deliverable
  paths: `implementation`, `pr-review`, `arch-review`, `code-health`,
  `design-review` (`skills/independent-review/review.py:43-49`).
- ✅ A prompt-time sidecar consumed by `record-review` has a precedent:
  `_common/candidate_sidecar.py` (written by `candidates`, consumed at
  `review.py:867`, gitignored at `.gitignore:47-51`).
- ✅ The digest shape exists in spec 118's worked example:
  `sha256(json.dumps({path: sha256(bytes)}, sort_keys=True))`
  (`skills/spec-workflow/worked-example-behavioral-verification.md:50-60`).
- ✅ 124-01 renders one PR-body row per required pass (AC3 there).
- ⬜ ADR-0069 Accepted.

**Acceptance Criteria:**

1. **Prompt builders capture the subject.** `review.py implementation`,
   `pr-review`, `arch-review`, `code-health` and `design-review` each write
   `<spec_dir>/reviews/.subject/slice-NN-<pass>.json` holding the HEAD commit
   (empty outside git), the sorted repo-relative deliverable paths, the
   excluded paths, the digest and a `created_at`. Re-running a builder
   overwrites it. The prompt text is unchanged. The `.subject/` directory is
   gitignored the same way `.candidates/` is.
2. **One digest function.** A `_common` helper computes the digest:
   `sha256:` over the sorted JSON manifest of each deliverable file's
   working-tree SHA-256. A directory expands to the regular files under it;
   a missing path maps to `"absent"`. The slice's own `spec.md` and slice
   file, and anything under `reviews/`, are excluded and listed as excluded.
   Two calls on unchanged bytes give the same digest; changing one byte in
   one deliverable changes it.
3. **`record-review` stamps and consumes.** Recording a slice verdict reads
   the matching sidecar, adds `reviewed_commit`, `deliverable_digest` and
   `deliverables` (block list) to the frontmatter, then deletes the sidecar.
   With no sidecar it writes `reviewed_commit` (HEAD now) and
   `deliverable_digest: unbound`, and prints a one-line note that this record
   can't be checked for staleness. `REQUIRED_FIELDS`
   (`review_evidence.py:75`) is unchanged, and every existing record still
   parses and clears as before.
4. **Freshness is one function.** `review_evidence` exposes a freshness check
   that returns `fresh`, `stale` or `unbound` for a record by recomputing the
   digest over its recorded `deliverables`. A stale result includes
   `git diff <reviewed_commit> -- <deliverables>` as the way to see what
   changed. Records without the new fields, and the `reconciliation` record
   (its prompt takes no deliverables), are `unbound`.
5. **Reported everywhere evidence is read, never blocking.**
   - `check-reviews` prints `[stale] <pass>: deliverables changed since review
     at <short sha> — <diff hint>` on stderr; its exit code is unchanged.
   - `workflow.py transition` to `REVIEWED`, `RECONCILED` or `DONE` prints the
     same notice and proceeds when the evidence otherwise clears.
   - `land.py prepare` adds a readiness row: `[x] Review freshness: N bound
     records fresh`, or `[?] Review freshness: <pass> stale (…)`, plus a count
     of unbound records. It is never a blocker.
   - 124-01's PR-body review row appends `— stale since review at <sha>` to a
     stale pass.
   Unbound records print nothing at a transition.
6. **Bug 039's rule is untouched.** The `review_reopened_at` back-edge check
   (`review_evidence.py:142`) still decides whether a verdict clears. A test
   holds a record that is both back-edge-stale (refused, as today) and
   digest-fresh, and one that is back-edge-fresh and digest-stale (clears,
   with the notice).
7. **Docs match.** `skills/independent-review/SKILL.md` (the "Code-staleness
   … deliberately NOT checked" sentence, `:378-380`) and the stale-but-passing
   comment in `review.py` (`:1807-1812`) describe the report-only check.
   `spec-workflow/SKILL.md` says what to do with a stale notice: re-run the
   pass and re-record it.

**Edge cases to cover explicitly:**
- Fixing nits after the prompt was built and recording afterwards gives a
  stale record. That is the intended signal (ADR-0069 open question 1).
- A renamed deliverable shows as `absent`, so the record is stale.
- The slice file listed as a deliverable is excluded, so ticking DoD boxes or
  a status change never makes a record stale.
- Outside a git repo, `reviewed_commit` is empty and the digest still works.
- A rebase that leaves the deliverable bytes unchanged keeps the record fresh.

**Enforcement is not here.** Making `stale` block is spec 125's call, under
its observe-then-enforce modes (ADR-0070). This slice adds no env var and no
mode setting. The refinement-todo trigger ("First incident where
stale-but-passing evidence lets a materially-changed slice transition …")
still decides whether hard gating is warranted. When it fires, the route is
spec 125, not a switch added here.

**Out of scope:** bug-record binding (the bug craft and security passes don't
go through a `review.py` builder; spec 124 Non-goals); ADR-side
frame-critique records (pre-implementation, no code deliverables).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: if this slice closes the spec,
      compress the Active-specs entry; otherwise leave it.

**Anti-horizontal-phasing check:** after this slice, a reviewer's `pass` that
no longer matches the code is flagged at the next transition and before
landing, so nobody lands it believing it was reviewed.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TBD — not yet implemented (recorded, not built)._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/refinement-todo.md` | `updated` | _TBD — add a "Partial (spec 124-02)" line to "Code-staleness hard-gating for review evidence"; the trigger stays._ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TBD — ADR-0069 indexed when accepted; ADR-0014 not amended._ |
| `.gitignore` (and the scaffolded ignore list, if any) | `updated` | _TBD — `reviews/.subject/`._ |
| `docs/architecture.md` | `updated` | _TBD — new `_common` digest helper and the `.subject` sidecar._ |
| `docs/specs/README.md` | `updated` | _TBD — regenerate by `workflow.py status-board` at close._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TBD at close._ |
