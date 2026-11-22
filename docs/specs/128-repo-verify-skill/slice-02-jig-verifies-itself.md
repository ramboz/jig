---
status: DRAFT
dependencies: [128-01]
last_verified: 2026-11-21
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 128-02 — jig-verifies-itself

**Goal:** jig's own repository gets a filled `verify` skill whose command
scaffolds a throwaway project from the working tree and drives jig's real
helpers through one slice's lifecycle, so a change to jig is checked by running
jig, not only by its unit tests.

**Decision:** [ADR-0073](../../decisions/adr-0073-repo-verify-skill-contract.md)
point 7. For a plugin, "the app" is a project with jig in it: **Boot** =
scaffold a temporary project from the working tree; **Drive** = take a slice
from `new` to `DONE` with the real helpers; **Inspect** = the scaffold
verifier, the linter and the status board; **Teardown** = delete the
temporary project.

**DoR:**
- ⬜ 128-01 DONE (the contract's shape and the stub template exist).
- ✅ The pieces exist and run offline: `scaffold.py` (greenfield, plugin
  mode), `workflow.py new --no-push` / `transition` / `status-board`,
  `tdd.py run`, `review.py implementation` / `record-review`,
  `verify_install.py --mode scaffold`, `spec_lint.py --all`.
- ✅ spec 118's worked example already drives a real helper on an isolated
  fixture and records a runtime identity
  (`skills/spec-workflow/worked-example-behavioral-verification.md`); this
  slice reuses its identity shape (revision + dirty-change digest), not its
  code.

**Acceptance Criteria:**

1. **One journey command.** `python3 scripts/verify_app.py` runs from the
   repository root against the working tree, prints one line per step with its
   outcome (`pass` / `fail` / `not-run` / `environment-error`), ends with a
   JSON summary carrying the code revision and a digest of uncommitted
   changes, and exits `0` (all pass), `1` (any fail) or `2` (environment
   error, e.g. `git` missing).
2. **Boot and drive.** The journey scaffolds a temporary project (Claude host,
   plugin mode), initialises git in it, gives it a `.jig/test-command` running
   one stdlib `unittest` test, reserves a spec with `workflow.py new
   --no-push` (it gets number `001`; ADR-0067 keeps `000` for genesis), and
   takes its slice from `DRAFT` to `DONE` through every state with all
   evidence gates armed. Review verdicts in that throwaway project are fixture
   records written by `record-review` with `--reviewer verify-fixture`; no
   verdict is written in jig's own `docs/`.
3. **Inspect, including a refusal.** The journey checks:
   `verify_install.py --mode scaffold` passes on the fresh project;
   `transition … REVIEWED` with no verdicts recorded is refused (exit 2,
   preserved behavior); `tdd.py run` exits 0; `review.py implementation`
   builds a prompt naming the slice; the status board shows the slice `DONE`;
   `spec_lint.py --all` exits 0 in the temporary project.
4. **Fast and repeatable.** No network access and no `JIG_*` gate bypass; the
   journey finishes in under 60 seconds on the CI runner; three consecutive
   runs give the same step outcomes. Measured times are recorded in this
   slice's verification scenario.
5. **jig's verify skill.** `.claude/skills/verify/SKILL.md` — a real folder
   beside the symlinked plugin skills — follows ADR-0073's contract with
   `verify-command: python3 scripts/verify_app.py` and filled Boot, Drive,
   Inspect, Teardown and Known flaky sections (Known flaky names the git
   `safe.bareRepository` setting spec 118 hit, deviation 6). A link
   `.agents/skills/verify` → `../../.claude/skills/verify` lets Codex sessions
   on jig find it. `.claude/README.md` gains a row for it. Nothing is added
   under `skills/`, and `build_host_packages.py --check` passes unchanged.
6. **Capable of failing.** Breaking a lifecycle helper — making `transition`
   skip the `REVIEWED` evidence check, or making `status-board` drop a row —
   turns the journey red; both mutations are witnessed and recorded in the
   deviation log.

**Edge cases to cover explicitly:**
- `git` absent or unusable: exit 2 with `environment-error`, not `fail`.
- A dirty working tree: the summary's digest changes; the journey still runs
  against the working tree, not `HEAD`.
- The temporary project is removed on success, failure and interrupt.

### Verification scenario (optional)

**Preconditions:** Python 3.9+, the `git` executable, the jig working tree; no
network, accounts or credentials.

**Invocation:** `python3 scripts/verify_app.py`, through jig's own `verify`
skill — this slice's scenario is the first one produced through it.

**Preserved behavior:** `scripts/run_tests.py` and `ci_check.py` are unchanged;
no host package changes.

**Code revision / dirty-change identity:** _recorded by the journey's JSON
summary at execution._

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| 1 | 1–3 | Every step `pass`; exit 0 | _at execution_ | _not-run_ | _saved JSON summary_ |
| 2 | 4 | Under 60 s; three runs agree | _at execution_ | _not-run_ | _timings_ |
| 3 | 6 | Each mutation turns the journey red | _at execution_ | _not-run_ | _deviation log_ |

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
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec).

**Anti-horizontal-phasing check:** after this slice, anyone changing jig —
person or agent — can run `/verify` and see jig scaffold a project and take a
slice to `DONE` with the real helpers, before committing.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO_ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: `CONTRIBUTING.md` may name `/verify` beside `ci_check.py`._ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
