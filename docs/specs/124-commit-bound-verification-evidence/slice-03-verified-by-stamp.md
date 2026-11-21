---
status: DRAFT
dependencies: [adr-0069, 124-01, 124-02]
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

## Slice 124-03 — verified-by-stamp

**Goal:** every slice landed with `land.py execute` leaves a stamp in the
repository saying how it was verified, with `none` as a value and an optional
reason. `land.py stamps --unverified` then lists the commits on a branch that
landed unverified or without any stamp.

**Decision:** spec 124 D4 / ADR-0069 decisions 4–6 (option H-6: an in-tree
landing record, mirrored as message lines).

**DoR:**
- ✅ 124-01's Test plan and 124-02's freshness check are the evidence the
  stamp is derived from.
- ✅ A helper making a path-limited commit that leaves other staged work alone
  has a precedent: `workflow.py:4312-4319`.
- ✅ The squash shape the query must read was probed (spec A3): stamp lines in
  the body sit above GitHub's `Co-authored-by:` paragraph, so they are not git
  trailers.
- ⬜ ADR-0069 Accepted.

**Acceptance Criteria:**

1. **One renderer, closed vocabulary.** A `_common` module derives the tokens
   (rules below) and renders `Verified-by: <tokens>` (order: `tests`,
   `review`, `scenario`; `none` alone), `Verified-at: <full HEAD sha>`, and,
   when given, `Verification-note: <one line>`. It also parses them back. An
   unknown token, or `none` combined with another token, is a parse error
   that names the token.
2. **The landing record is committed.** `land.py execute` (both modes, not
   `--dry-run`), after its existing guards and before pushing, writes
   `<spec_dir>/verification/slice-NN-landing.md`. Its frontmatter holds
   `slice`, `verified_by`, `verified_at`, `verification_note`, `commits` and
   `landed_at`; its body is 124-01's Test plan section. It then runs
   `git add` and a path-limited `git commit -- <record>` with the message
   `chore(land): record verification for slice NNN-NN`, a blank line, the
   stamp lines, and `Verified-commits: N`. N is the count of commits in
   `origin/main..HEAD` before the landing commit, falling back to local `main`
   the way `_check_ff_viable` does. Unrelated staged changes stay staged and
   out of the commit. `--dry-run` prints the record and the message and
   writes nothing.
3. **The PR body ends with the stamp.** In PR mode, the last paragraph of the
   body is the stamp lines. `prepare --mode pr` shows the same lines, as a
   preview, in the body it stages.
4. **A reason can be given.** `prepare` and `execute` accept
   `--verification-note TEXT`; a value containing a newline exits 2. When the
   stamp is `none` and no note was given, the readiness report shows
   `[?] Verification stamp: none, no note — pass --verification-note "<why>"`.
   Blockers and exit code are unchanged.
5. **`land.py stamps` lists stamps, read-only.**
   `land.py stamps [--since REF] [--limit N] [--unverified]` walks first-parent
   commits from HEAD (back to `REF`, or the last `N`, default 50) and resolves
   each, in this order:
   1. the commit adds or modifies a `verification/slice-*-landing.md` → that
      record's stamp;
   2. `Verified-by:` lines anywhere in the message (the last block wins);
   3. a merge commit → its second parent, by rules 1–2;
   4. inside the `Verified-commits` window of a newer landing commit already
      seen → `covered by <short sha>`;
   5. otherwise `unstamped`.

   It prints one line per commit:
   `<short sha> <subject> | <tokens | none: <note> | covered by <sha> | unstamped>`.
   When the record and the message disagree, the record wins and the line is
   marked `(message differs)`. `--unverified` keeps only `none` and
   `unstamped` rows. A malformed stamp prints `malformed stamp (<reason>)`.
   Exit 0 on any readable history. It never writes.
6. **Hand stamps count.** A commit made by hand with `Verified-by: none` and a
   `Verification-note:` in its message shows as `none: <note>`, so a commit
   outside any slice can say why it wasn't verified.
7. **The stamp never gates.** No exit code of `prepare`, `execute` or
   `workflow.py transition` depends on the stamp's value. A `none` landing
   proceeds exactly as today. Blocking is spec 125's question.
8. **Docs.** slice-land SKILL.md describes the record, the stamp lines, the
   note and the query, and asks authors who rewrite a PR body to keep the
   stamp lines. `docs/workflow.md` and its scaffold template mention
   `land.py stamps --unverified` beside landing. Host packages are
   regenerated.

### Behavioral rules

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | `tests` token | `land.py` | `check_tests` is `green` and the working tree was clean for the run | present | The run describes the landed bytes | AC1 |
| BR-2 | `tests` token | `land.py` | `warn`, `not_run`, or green on a dirty tree | absent; the Test plan row says why | Not evidence for the commit | AC1 |
| BR-3 | `review` token | `land.py` | every pass in `required_passes("REVIEWED", flags)` plus `reconciliation` clears and none is `stale` (124-02) | present | Review evidence matches the landed code | AC1 |
| BR-4 | `review` token | `land.py` | a required pass is missing, not `pass`, or `stale` | absent | A bypassed gate or stale review shows in history | AC1 |
| BR-5 | `review` token | `land.py` | required records clear but are unbound (recorded before 124-02) | present; the Test plan marks them unbound | Staleness can't be shown; same as today's gate (ADR-0069 open question 5) | AC1 |
| BR-6 | `scenario` token | `land.py` | at least one parsed step and every step `pass` (124-01 AC4) | present | Runtime evidence was recorded | AC1 |
| BR-7 | `verify` token | — | any | not emitted by this slice; accepted by the parser | ADR-0073 point 5 defines what earns it (a scenario `Produced via:` the verify skill, every step `pass`, revision equal to `Verified-at`); the renderer gains that rule once spec 128 lands | AC1 |
| BR-8 | `none` | `land.py` | no token earned | `Verified-by: none`, alone | Absence is recorded, not implied | AC1 |
| BR-9 | landing | `land.py` | stamp is `none` | same blockers and exit code as today | The stamp is a record, not a gate | AC7 |

**Edge cases to cover explicitly:**
- A squash-shaped message (PR body with stamp lines, then `---------`, then a
  `Co-authored-by:` paragraph) resolves to the stamp (rule 2).
- A direct landing of three commits shows the landing commit stamped and the
  three before it `covered by` it.
- A merge commit whose second parent is the landing commit shows that stamp.
- A release-bot commit with no stamp shows `unstamped`.
- Staged, unrelated changes are still staged after `execute` and are not in
  the landing commit.
- A commit that only edits an existing landing record is read by rule 1. The
  test pins this so a change to the rule is deliberate.

**Out of scope:** bug-fix landings (ADR-0069 open question 3), refreshing a
stamp after a PR gains commits (open question 4), and amending the tip
instead of adding a commit (open question 2).

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

**Anti-horizontal-phasing check:** after this slice, `land.py stamps
--unverified` lists every commit on `main` that landed with `none` or outside
jig, with the reason when one was given.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TBD — not yet implemented (recorded, not built)._

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `skills/slice-land/SKILL.md` | `updated` | _TBD — record, stamp, note, query (AC8)._ |
| `docs/workflow.md` + `templates/docs/workflow.md.template` | `updated` | _TBD — `land.py stamps --unverified` beside landing._ |
| `docs/architecture.md` | `updated` | _TBD — the stamp module and the landing record._ |
| `docs/memory/glossary.md` | `updated` | _TBD — candidate term "Verification stamp"._ |
| Host packages (`build_host_packages.py`) | `updated` | _TBD — regenerate._ |
| `docs/specs/README.md` | `updated` | _TBD — regenerate by `workflow.py status-board` at close._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TBD — compress the entry if this slice closes the spec._ |
