---
status: DONE
tier: standard
severity: medium
claimed_by: claude/jig-orient-origin-check-1ccf06
regression_test: skills/spec-workflow/test_workflow.py::OrientOriginFreshnessTests::test_fetch_reports_commits_behind_origin
main_repro_checked_at: 2026-08-04
main_repro_ref: origin/main@afb7185
main_repro_result: reproduces
red_confirmed_at: 2026-08-04
green_confirmed_at: 2026-08-04
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 031: orient-skips-origin-freshness

## Symptom

`/jig:orient` reports obsolete project state. A session was oriented against
local boards (`docs/specs/README.md`, `docs/bugs/README.md`, `adr-*.md`, slice
`STATUS` markers) whose branch base had drifted behind `origin/main`; orient
presented the stale picture as current and the session reasoned against a dead
premise (work already shipped on trunk was reported as still open).

## Repro

1. On a checkout whose base is behind `origin/main` (e.g. `origin/main` has
   commits the local branch has not integrated), run `/jig:orient`.
2. Observe the briefing: it summarizes specs/bugs/ADRs from the local tree and
   never signals that the checkout is behind, so shipped-on-trunk items read as
   open. `workflow.py orient` emits no "behind" segment; the skill never
   fetches before surveying.

## Evidence

- `orient()` (`skills/spec-workflow/workflow.py:1895`) composes its headline
  from local artifacts + `_in_flight_summary` (commits **ahead** of trunk). It
  has **no** commits-**behind** signal and issues **no fetch**.
- `_in_flight_summary` (`workflow.py:1846`) and its helpers deliberately avoid
  the network (tight `_ORIENT_IN_FLIGHT_TOTAL_BUDGET = 1.5s`; the SessionStart
  hook bounds the whole command at 4s and treats a timeout as *no* headline).
- The `orient` **SKILL.md** survey (`skills/orient/SKILL.md`) reads boards and
  runs `gh pr list`, but has no "refresh/verify against origin" step.
- The pattern to reuse already exists: `_branch_freshness_warning`
  (`workflow.py:1098`, bounded `git fetch` + `HEAD..origin/main` behind-count,
  used only by `transition`/`land`) and spec-103's `git_freshness.py`
  (`hooks/scripts/lib/git_freshness.py`, the SessionStart fetch+nudge). Neither
  fires at orient-time on demand.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: spec-103's SessionStart git-freshness hook already covers this, so
  the defect is only that its nudge was lost in a long context — no orient
  change needed. Falsify by: spec-103 fires **once at time-zero**; drift
  accrues afterward and orient re-reads boards mid-session with no re-check, so
  a session oriented after time-zero is unprotected. Confirmed: the incident is
  a mid-session `/jig:orient`, not a session-start signal.
- [x] H2 (leading): orient has **no** origin-freshness step of its own — it
  neither fetches at orient-time nor reports commits-behind — so whenever the
  local base is stale it renders the stale boards as current. Confirm by: read
  `orient()` and `_in_flight_summary` (no fetch, ahead-only) and the orient
  SKILL survey (no refresh step) — both hold.

## Root cause

Orient's freshness contract has a hole: it reports commits **ahead** of trunk
but never commits **behind** origin, and it never refreshes remote-tracking
refs at orient-time. Its entire picture is built from local artifacts that are
only as current as the last fetch. spec-103 fetches once at `SessionStart` via
a separate hook, but an interactive `/jig:orient` run later in the session
re-reads the boards without re-verifying against origin, so a base that drifted
behind trunk after time-zero is presented as current. The fix belongs in
orient itself: a bounded, fail-soft origin check on the interactive path.

## Fix class

guardrail — adds a freshness tripwire (fetch + behind-count segment) to
orient's interactive path; it does not change how any board is computed, only
surfaces when those boards may be stale.

## Fix

`skills/spec-workflow/workflow.py`:

- New `orient(project_dir, *, fetch=False)` parameter + `--fetch` CLI flag.
  When `fetch` is False the headline is byte-identical to its pre-031 form, so
  the 4 s `jig-project-orient.sh` SessionStart hook (which passes no `--fetch`)
  is untouched and spec 103 remains the sole time-zero freshness signal.
- `_orient_fetch_origin()` — one bounded (`_ORIENT_FRESHNESS_FETCH_TIMEOUT =
  5 s`), fail-soft `git fetch --quiet origin`; returns success/failure, never
  raises.
- `_freshness_summary()` — after a successful (or attempted) fetch, resolves
  the trunk base (reusing `_in_flight_base`) and counts `HEAD..<base>`. Emits
  `· freshness: <n> commit(s) behind <base>` when behind, or `· freshness:
  could not reach origin` when the remote is configured but the fetch failed
  (so a stale view is never reported as fresh). Silent for a local-only repo,
  a clean checkout, or any degraded git state.

`skills/orient/SKILL.md` — the headline command now passes `--fetch`, with a
paragraph explaining that a `behind`/`could not reach origin` reading means the
local boards below may be stale and origin should be integrated (or orient
re-run after a pull) before they are trusted.

## Already tried

## Regression test

`skills/spec-workflow/test_workflow.py::OrientOriginFreshnessTests` (8 tests)
covers the behind segment (plural + singular), silence when up-to-date /
local-only / non-git, the unreachable-origin signal, the byte-identical
default (hot) path, and the `--fetch` CLI wiring against a real bare-remote
fixture. `skills/orient/test_orient_skill_surface.py::
OrientOriginFreshnessSurfaceTests` (3 tests) pins the SKILL.md guidance. The
named `regression_test` fails red before the fix (`orient() got an unexpected
keyword argument 'fetch'`) and passes green after.

## Proof

- Red witnessed: the FIXING gate ran `.jig/test-command` with `workflow.py`
  reverted to trunk (behind-detection absent) — full suite red — then the fix
  was restored.
- Green witnessed: the REVIEWED gate ran the full suite + `uvx pyright` green.
- See `red_confirmed_at` / `green_confirmed_at` in the frontmatter.

## Learning

A read-only reporter that narrates *local* artifacts is only as current as the
last fetch — reading boards without checking origin reports a stale premise as
current. The durable fix is a bounded, fail-soft origin check on the
**interactive** path only, gated behind a flag so the hot SessionStart path
(and spec 103's sole time-zero freshness signal) stay untouched. Never report
"fresh" against refs you didn't refresh — surface `could not reach origin`
instead. Process corollary: editing a `SKILL.md` or a `skills/**` helper
requires regenerating the `hosts/` mirrors or the drift guard fails. Recorded
in `docs/memory/learnings.md`.

Base resolves against the default-branch trunk (`_in_flight_base`:
`origin/HEAD` → `origin/main`/`origin/master`), not the branch's own
`@{upstream}` — intentional parity with orient's existing "status board
describes the default branch" model, not an oversight.

## Main recheck

- 2026-08-04 - `origin/main@afb7185` -> reproduces: On fresh origin/main (afb7185 == HEAD): orient() has no fetch and only _in_flight_summary (ahead-only); no 'behind' segment exists, so a checkout behind origin renders stale boards as current. grep 'behind' skills/spec-workflow/workflow.py returns only _branch_freshness_warning (transition/land path), never orient.
