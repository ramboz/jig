---
status: DRAFT
skill: spec-workflow
use_cases: [UC-4, UC-5, UC-7, UC-20]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 129: Verification-loop hardening

> Investigation record:
> [R-002](../../research/R-002-claude-code-verification-assessment.md)
> (mechanisms 3, 5 and 10). **Status: recorded, not yet built.** No ADR of its
> own: each slice extends an existing decision, named below. 129-01 also
> depends on [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md)
> (Proposed) through spec 125, and cannot move past DRAFT before that ADR is
> Accepted. Reserved on 2026-11-21 via `workflow.py new --no-push`; the number
> is provisional until merged.

## Overview

Three small changes to the loop an agent runs between writing code and asking
for review, each taken from the Claude Code team's verification post:

1. **Cheap checks first (129-01).** "Tests, build, and linter run before a PR
   opens." In jig the green-tests check sits at slice-land
   (`skills/slice-land/land.py:309-339`), after every review pass has already
   been paid for. 129-01 checks for a green full-suite run of the current code
   before the compliance pass is built and before `REVIEWED`, born in
   spec 125's observe mode.
2. **Three rounds, then a person (129-02).** "If a check is still failing
   after three rounds, Claude stops and brings in a human." Spec 122 stops a
   slice only on an explicit arch `ESCALATE:`. 129-02 gives every slice review
   pass the same stop when it is still not passing on its third round.
3. **Property tests where they fit (129-03).** Round-trip, invariant,
   idempotency and equivalence checks find edge cases "not created with the
   same bias as the agent that created the original code." tdd-loop does not
   mention them. 129-03 adds the nudge and ships jig's first property test.

### Which decision each slice extends

- **129-01 → [ADR-0014](../../decisions/adr-0014-review-evidence-model.md) §5
  under [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md).**
  A new gate, `tests-before-review`, is registered on spec 125's resolver and
  is born `observe` (ADR-0070 §3). In observe nothing in ADR-0014 §5's
  transition map changes. Promoting it to `enforce` adds a requirement to the
  `REVIEWED` set; that promotion is ADR-0070 §5's recorded decision, and it
  should cite ADR-0014 so the owner can judge whether ADR-0014 needs an
  amendment note (ADR-0010, spec 102). Not part of this spec.
- **129-02 → [spec 122](../122-arch-pass-escalation-and-rounds/spec.md) D2
  and D3, and ADR-0014 §2.** 122's D2 reads "Escalation reuses existing
  surfaces … No new lifecycle state, no new command." 129-02 stays inside it:
  the round-3 stop reuses `record-review`'s STOP notice, the gate's "a person
  decides" diagnostic, `memory.py add-inbox` and `blocked_by:`
  ([ADR-0057](../../decisions/adr-0057-first-class-blockers-are-annotations.md)).
  122's D3 ("Round carry-over is arch-only and on disk only") is kept: no
  other pass's prompt changes. The round count is a new optional frontmatter
  field on verdict records, additive in the way spec 096-05's `substrate:` was
  (`skills/independent-review/review.py:2059-2073`); ADR-0014 §3 (only `pass`
  clears) and §4 (overwrite in place) are unchanged.
- **129-03 → tdd-loop's contract** (`skills/tdd-loop/SKILL.md`), which already
  forbids weakening, skipping, `xfail`-ing or quarantining a test
  (`SKILL.md:62-63`). The nudge is judgment only; `tdd.py` does not change.

### How this relates to deferred work

- **Slice 006-03 — pre-commit-gate (DEFERRED).** "PreToolUse hook that blocks
  `git commit` calls when `tdd.py run` returns non-zero exit." Trigger: "First
  production-grade red-tests-committed incident, OR a sustained run of more
  than 2 commits-with-red-tests within a single spec."
  ([spec 006](../006-tdd-loop/spec.md)). 129-01 is not a commit hook and does
  not resolve 006-03; its trigger is unchanged. 129-01's observe log is a
  cheap way to see whether that trigger is close.
- **refinement-todo "Warn when an escalated arch record is overwritten (spec
  122-01)"** (`docs/refinement-todo.md:52-54`). "Nothing prevents an orchestrator from re-running the arch pass
  before a person decides and overwriting the escalated record with a `pass`."
  Trigger: "First observed run where an escalated arch record was overwritten
  before a person decided, OR the arch-review redesign's round-two evals show
  reviewers dropping open escalations." Not resolved here: a `pass` recorded
  over a round-3 stop clears, exactly as a `pass` over an escalation does
  today. 129-02 reads the previous record at the same point the warning would,
  so the mitigation stays a few lines when its trigger fires.
- **ADR-0070 Option D (anti-stuck valve) is the opposite answer.** ADR-0070
  rejects "after two refusals, let it through" for lifecycle gates and points
  at this spec: "A lifecycle gate that keeps failing is a case for a person
  (spec 129's round cap), not for letting it through."

### Non-goals

No commit hook (006-03). No change to `land.py`'s check, which stays the
merge-time backstop. No round cap for bug-side (`--bug`) or ADR-side
(`--adr`) records; bug-fix has its own lifecycle gates. No new lifecycle
state, command or flag (spec 122 D2). No test dependency added to any user
project, and none to jig.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **A1 — a `tdd.py run` leaves no record (grounded).** `cmd_run` returns the
  normalized exit code and writes nothing (`skills/tdd-loop/tdd.py:346-418`).
  129-01 has to record the result itself.
- **A2 — spec 124 leaves the pre-review run to this spec (grounded in its
  draft).** Spec 124's non-goals list "Running tests before review (spec
  129)", and it does not reuse that run for its landing stamp because it is on
  an earlier commit. 129-01 keeps its own working-tree digest (129-01 AC2)
  rather than sharing 124-02's deliverable-manifest helper: it identifies the
  tree a test run saw, not a set of named deliverables.
- **A3 — spec 125-01 gives new gates a resolver and an observe event
  (grounded in its draft, not built).** 125-01's resolver lives at
  `skills/_common/gate_mode.py` with a registry of name, env var, default mode
  and rule; observe prints one `would block` note and appends
  `gate_would_block`. If 125's final shape differs, 129-01 adapts at
  READY_FOR_REVIEW.
- **A4 — verdict records tolerate an extra frontmatter field (grounded).**
  Only the fields in `REQUIRED_FIELDS` are checked
  (`skills/_common/review_evidence.py:75-82`); `substrate:` and
  `applied_skill:` were added this way.
- **A5 — Hypothesis is not available to jig's tests (grounded).** CI sets up
  Python 3.9 and 3.12 and runs scripts with no install step
  (`.github/workflows/ci.yml:30-82`); the runner is stdlib `unittest`
  (`scripts/run_tests.py:40-60`); `import hypothesis` fails in this
  environment. jig's first property test therefore uses a seeded stdlib
  generator.
- **A6 — jig has no property test yet (grounded).** No test file imports
  `random` or builds a `random.Random`; the status board's idempotency is
  pinned by fixed examples (`skills/spec-workflow/test_workflow.py:500`,
  `:848`, `:1435`, `:4147`).

## Decomposition

**SPIDR (Spike / Paths / Interfaces / Data / Rules): Rules.** Three
independent slices, one rule each; none needs another:

- **129-01** — a green full-suite run of the current code before the first
  review pass (observe by default).
- **129-02** — a pass still failing on round 3 stops the slice for a person.
- **129-03** — tdd-loop suggests property tests; jig ships one.

No Spike: each surface was probed (Assumptions). **Anti-horizontal-phasing:**
each slice changes what an agent or reviewer sees on its own — a would-block
note before review, a STOP at round 3, a nudge and a real property test.

## Slices

- [129-01 — green-tests-before-review](slice-01-green-tests-before-review.md) — a recorded green full-suite run of the current code is checked before the compliance pass and `REVIEWED`; born in observe mode.
- [129-02 — three-rounds-then-a-person](slice-02-three-rounds-then-a-person.md) — any slice review pass still not passing on round 3 gets spec 122's STOP / inbox / `blocked_by:` treatment.
- [129-03 — property-tests-where-they-fit](slice-03-property-tests-where-they-fit.md) — tdd-loop names the four property shapes; jig's status-board regeneration gets a seeded property test.
