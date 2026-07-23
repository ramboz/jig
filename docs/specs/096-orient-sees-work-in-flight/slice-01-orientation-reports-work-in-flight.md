---
status: DONE
dependencies: []
last_verified: 2026-07-22
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-01 — orientation reports work in flight

**Goal:** An agent picking the project up learns that finished work is sitting
unmerged or in an open pull request — instead of reporting the project as if
only the default branch existed, and re-asking the owner questions a PR body
already put to them.

**DoR:**
- ✅ `orient()` reads durable artifacts only and runs no `git` —
  `skills/spec-workflow/workflow.py:1687`, read on `origin/main` @ `fd7115a`.
- ✅ `skills/orient/SKILL.md` has zero occurrences of `pull request`, `gh pr`
  or `branch` — `grep -niE` returns nothing.
- ✅ The SessionStart hook bounds `orient` at `timeout=4` and exits silently on
  any non-zero return — `hooks/scripts/jig-project-orient.sh`.
- ✅ `git` subprocess use is established in this codebase and has a house test
  pattern: `_common/team_signal.py:60,69` and `_common/test_team_signal.py`
  (`git init` into a temp dir).
- ✅ The byte-exact headline test that constrains AC2 exists and passes today —
  `test_workflow.py:8191`.

**Assumptions:** A1 and A2, inherited from
[spec 096](./spec.md#assumptions). A1 is what AC2 and AC3 exist to contain; A2
is why no `gh` call appears in the CLI.

**Acceptance Criteria:**

1. **The headline reports commits that have not reached the default branch.**
   When the project is a git repository whose `HEAD` is ahead of its default
   branch, `workflow.py orient` appends one segment naming the count and the
   branch — e.g. `· in flight: 5 commits ahead of main on claude/night-prep`.
   Singular/plural is correct at 1 (`1 commit ahead`), because a headline that
   reads "1 commits" is the kind of thing that trains readers to skim past it.
2. **Silence is the default, and the existing headline is byte-identical.**
   The segment is absent — and `orient`'s output unchanged from today, character
   for character — in every one of: not a git repository; `git` not on `PATH`;
   no resolvable default branch; `HEAD` level with or behind the default branch;
   any git invocation returning non-zero. This is asserted against the *existing*
   `test_scaffolded_headline_compacts_active_specs` expectation rather than by
   editing it: that test runs in a non-git temp dir and must stay green
   untouched.
3. **Orientation never fails because git did.** No git failure — missing binary,
   corrupt repo, timeout, unexpected or undecodable output — may raise out of
   `orient()` or change its exit code. **The bound is aggregate, not
   per-call:** all git work in one `orient` call shares a single wall-clock
   deadline, and once it is spent every remaining call returns immediately
   without spawning a process. *(Amended during implementation; see the
   deviation log.)*
4. **The default branch is resolved, not assumed to be `main`.** Resolution
   order is `origin/HEAD` → `origin/<trunk>` → local `main` → local `master`,
   first hit wins; if none resolves, AC2's silence applies. A project whose
   trunk is `master` gets a correct segment, not a wrong one.
5. **The judgment skill surveys the collaboration layer, and does it first.**
   `skills/orient/SKILL.md`'s survey gains open pull requests as its **first**
   bullet, instructing `gh pr list` *and* `gh pr view <n>` to read the PR
   **body** — naming why the body specifically matters: unattended workers put
   their questions for the owner there and nowhere else. When `gh` is absent or
   the repo has no remote, the skill says so in one line rather than silently
   omitting the section.
6. **The fixed output layout has somewhere to put it.** A "Waiting on you"
   section lands ahead of "the one decision blocking the most", carrying one
   titled bullet per open PR or unmerged branch, and explicitly flagging the
   three states that each mislead differently: **stale** (newer local commits
   already answer it), **unmerged branch with no PR** (invisible to every status
   board), and **superseded** (the PR's branch is an ancestor of newer local
   work, so it can be fast-forwarded rather than redone).
7. **A decision already put to the owner is not re-derived.** The skill's
   decision section is instructed to cross-check open PRs first: a question the
   owner has already been asked in a PR body is an *outstanding* one to point
   at, not a fresh one to re-frame. This is the specific failure the field
   incident produced.
8. **The rule is stated where it generalises.** The skill's Judgment section
   carries the principle in one line — *"what's next" means what is blocked on a
   human, not what the repo contains* — including the re-ask case: check the
   collaboration layer again on a later re-ask in the same session, rather than
   answering from context already in hand. That was the second miss in the field
   incident, after the first had been corrected.
9. **Repository-controlled text cannot forge the headline.** The branch and
   base names reach the SessionStart `additionalContext` line, which is
   injected into the agent's context. They are sanitised to the same whitelist
   as the existing claim field and length-capped, so a ref containing the
   headline's own `·` separator cannot fabricate a field.

**How this will be tested** (`python3 scripts/run_tests.py`; unittest per
CONTRIBUTING):

- **AC1 / AC4** — `git init` a temp repo (the `test_team_signal.py` pattern),
  commit on the trunk, branch, add N commits, assert the segment's exact text;
  repeat with the trunk named `master`; assert the singular form at exactly one
  commit.
- **AC2** — a non-git temp dir asserts the legacy headline's prefix and shape;
  the *byte-exact* guard is the pre-existing
  `test_scaffolded_headline_compacts_active_specs`, left untouched. Also: a repo with `HEAD` level with trunk, and
  one behind it.
- **AC3** — a stub `git` earlier on `PATH` that: exits 1; is absent entirely;
  hangs (asserting **elapsed time**, not merely silence — silence alone passes
  with no timeout at all); answers the cheap probes then hangs on every ref
  read, proving the *aggregate* bound; returns non-decimal output; and returns
  bytes that are undecodable in the ambient encoding. All assert the plain
  headline and no raise; one additionally asserts a zero CLI exit through the
  real command-line entry point.
- **AC9** — a branch named with the headline's own `·` separator asserts the
  rendered line still contains exactly three separators; a 200-character branch
  asserts the cap *boundary* (character `MAX` survives, `MAX+1` does not).
- **AC5–AC8** — surface assertions over `skills/orient/SKILL.md` in the spirit
  of the existing `test_spec_workflow_skill_surface.py`: the survey names
  `gh pr list` and `gh pr view`, the layout contains the "Waiting on you"
  heading ahead of the decision heading, and the Judgment section carries the
  blocked-on-a-human rule. Prose is what this half of the slice ships, so the
  test pins the load-bearing phrases rather than re-reviewing the wording.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). `Ran 3527 tests … OK (skipped=4)`, `pyright: clean`.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly — trunk named `master`,
      exactly one commit, git absent, git failing, git hanging.
- [x] `test_scaffolded_headline_compacts_active_specs` still passes **unedited** — `git diff origin/main` on that file has zero deletion lines
      — if it needed changing, AC2 was not met.
- [x] Reviewed by `reviewer` subagent (2 compliance rounds + 1 craft). Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading (9 entries).
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` unchanged — nothing was deferred during
      implementation.

**Anti-horizontal-phasing check:** After this slice lands, an agent opening a
project with an unreviewed PR or an unmerged branch is told so at SessionStart
and again in the `/jig:orient` briefing, and is told not to re-ask what the PR
already asked. Both halves of the reported failure are closed; shipping either
alone would leave the other open.

### Deviation log (after reconciliation)

**1. AC3's bound was widened from per-call to aggregate.** The slice as drafted
said each git call is "bounded by an explicit timeout well inside the hook's
4-second budget", which the first implementation satisfied literally with a
2.0 s per-call timeout. Round 1 of the implementation review showed that is not
a bound at all: `_in_flight_summary` can issue **nine** calls, so the real
worst case was ~16 s against a hook that gives up at 4 s and then emits *no
headline* — strictly worse than the pre-096 behaviour this slice was supposed
to improve. Fixed with a single shared wall-clock deadline
(`_ORIENT_IN_FLIGHT_TOTAL_BUDGET`, 1.5 s); AC3 was rewritten to state the
aggregate requirement rather than left to be satisfied on a technicality.

**2. AC9 was added mid-implementation.** Round 2 found that the two ref names
flow unsanitised into the SessionStart `additionalContext` line — the text the
hook injects into the agent's context. Git permits `·`, the headline's own
field separator, in a ref name, so a branch could fabricate a headline field;
`base` is additionally remote-derived via `origin/HEAD`. The module already had
`_sanitize_orient_claim` and a hostile-input test for the sibling field, so the
gap was an inconsistency rather than a novel risk. Added `_sanitize_orient_ref`
(same whitelist, 60-char cap so real branch names survive) and AC9 to cover it.

**3. Per-call timeout is 0.75 s, not the 2.0 s first implemented.** A
consequence of (1): the aggregate budget is 1.5 s and a single call may not
consume it all. On a very large or cold repository `rev-list --count` can
exceed 0.75 s, in which case the segment silently disappears. That is
AC2-compliant — it degrades to exactly the pre-096 headline — but it is a real
behavioural difference from the first implementation and is recorded here
rather than left to be discovered.

**4. AC4's wording does not literally describe the implementation.** AC4 says
the order is `origin/HEAD` → `origin/<trunk>` → local `main` → local `master`.
The code consults `origin/HEAD` and then a *fixed* list
(`origin/main, origin/master, main, master`). Equivalent in effect for the
cases AC4 names, but "`origin/<trunk>`" implies a lookup that does not exist.
Left as-is rather than reworded post-hoc; noted so a future reader does not go
hunting for the missing mechanism.

**5. Accepted heuristic: first *resolvable* candidate, not the true fork
point.** A repository whose trunk is `develop`, with `origin/HEAD` unset and a
stale local `main` still present, will report its count against `main`. This
follows from AC4's stated resolution order and is cheap and predictable, but it
is a heuristic, not a computation of the merge base. Recorded because the
failure is silent — a plausible-looking count against the wrong base.

**6. `skills/orient/` became a test-discovery directory.** It previously held
only `SKILL.md`; `scripts/run_tests.py` skips skill dirs with no `test_*.py`.
Adding `test_orient_skill_surface.py` means that directory is now discovered
for the first time. No configuration change was needed — noted because it is a
new surface, not a modified one.

**7. Constants renamed and relocated after the craft pass.** They were first
written as `_IN_FLIGHT_*` beside the new functions, with PEP-257 attribute
docstrings. The module already has an `_ORIENT_*` constant block and uses `#`
comments throughout, so they were moved there and renamed
`_ORIENT_IN_FLIGHT_*`. Behaviour-neutral; recorded because the test file
patches these names.

**8. Test stubs use `exec sleep`, not `sleep`.** Round 2 flagged that a
`#!/bin/sh` stub which *forks* `sleep` would leave an orphan holding the pipe
after `subprocess.run` kills the shell, making `communicate()` block for the
full 5 s and turning two timing tests into deterministic failures on shells
that fork (this did not reproduce on the implementer's macOS `sh`). `exec`
replaces the shell with `sleep`, so the kill lands on the process that holds
the pipe. Pre-emptive; the hazard was never observed here.

**10. `test_long_branch_name_is_capped` was vacuous and was rewritten.** It
asserted `len(headline) < 400`, which a 201-character branch satisfies even
with the cap deleted (~309 chars) — the same class of defect round 1 caught
three times, slipping through because the mutation re-check had been scoped
only to those three. It now pins the boundary: character `MAX` survives,
`MAX+1` does not. Found by the reconciliation pass, not by either compliance
round.

**11. The record itself needed four corrections.** The reconciliation pass
checked the written account against the tree and found: the status board still
showing `IN_PROGRESS` after the REVIEWED transition cleared the claim; the
"Reconciliation review passed" box ticked before that review existed (it is
ticked by the RECONCILED transition, not by hand); a new-test count of 27 that
should be 30; and `SKILL.md`'s headline template still showing three fields
with no `· in flight:`. All four are fixed. Recorded because a deviation log
that reads well while the artifacts disagree is exactly the failure this pass
exists to catch.

**12. All three reviewer subagents had read-only tools.** None could run
`scripts/run_tests.py`, `git diff`, or the drift check, so the claims they
flagged as unverified were verified here instead and are recorded in
[`reviews/slice-01-compliance.md`](reviews/slice-01-compliance.md): the full
suite (`Ran 3527 tests … OK (skipped=4)`, pyright clean), the insertions-only
diff of `test_workflow.py`, and `build_host_packages.py --check` reporting in
sync. **This is a real limitation of the evidence, not a formality:** every
executable claim in this record was verified by the implementer, so the
independent checks are of the *code and the record*, not of the test run.

### Reconciliation sweep

- **Tests:** `python3 scripts/run_tests.py` → `Ran 3527 tests … OK (skipped=4)`,
  `pyright: clean`. **30** tests are new — 19 in `OrientWorkInFlightTests` and 11
  in `test_orient_skill_surface.py`. (An earlier draft of this sweep said 27,
  subtracting the three rewritten vacuous tests; that was wrong — those three
  live *inside* the 30, and neither file existed in this form on `origin/main`.)
- **The DoD's byte-identical guard holds mechanically:**
  `git diff origin/main -- skills/spec-workflow/test_workflow.py` contains
  **zero** deletion lines, so `test_scaffolded_headline_compacts_active_specs`
  is provably unedited.
- **Mutation-checked, not just green:** disabling the shared deadline makes
  `test_total_git_budget_is_bounded_across_many_calls` fail (2.69 s against a
  2.0 s assertion) and restoring it makes it pass. The three tests round 1
  showed were vacuous were each re-checked the same way.
- **Host packages:** regenerated with `scripts/build_host_packages.py`;
  `--check` reports in sync. Tests are correctly excluded from both host
  packages; the Codex copy carries the builder's
  `${CLAUDE_PLUGIN_ROOT}` → `${PLUGIN_ROOT}` rewrite, which a hand edit would
  not produce.
- **Status board:** regenerated with `workflow.py status-board` — spec 096 was
  absent from `docs/specs/README.md` until this step.
- **Spec lint:** `scripts/spec_lint.py` reports no AC contradictions across all
  96 specs.
- **`docs/refinement-todo.md`:** unchanged. Nothing was deferred during
  implementation — every open question raised by either review was resolved in
  this slice or recorded in the deviation log above.
- **Docs consistency:** `orient()`'s docstring and `SKILL.md`'s frontmatter
  `description` both claimed a survey that no longer matched the behaviour;
  both were corrected. No other reference to the renumbered layout sections
  exists in the repo (grepped).
