---
status: DRAFT
skill: slice-land
use_cases: [UC-6, UC-7]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 124: Commit-bound verification evidence

> Implements [ADR-0069](../../decisions/adr-0069-commit-bound-verification-evidence.md) (Proposed). Investigation record: [R-002](../../research/R-002-claude-code-verification-assessment.md). **Status: recorded, not yet built** — the ADR must be Accepted before 124-01 moves past DRAFT.
>
> Reserved on 2026-11-21 via `workflow.py new --no-push` (local provisional; the
> number is not yet on `origin/main`).

## Overview

The Claude Code team's verification post makes two points this spec takes up:
"A passing review on an out-of-date commit means nothing.", and every commit is
stamped with how it was verified, where the stamp "even includes "none" so we
can query for commits that weren't verified."

jig falls short of both in three places (details and citations in ADR-0069's
Context):

1. **The PR body ticks boxes it didn't check.** `land.py` writes "All ACs pass
   (full suite green)", "Reviewed by `reviewer` subagent" and "Reconciliation
   review pass" as `[x]` lines into every PR body
   (`skills/slice-land/land.py:704-707`), even when its own readiness report
   says the tests were `NOT RUN`.
2. **Review records don't say what was reviewed.** A verdict file has
   `reviewed_at` but no commit and no deliverable identity
   (`skills/_common/review_evidence.py:75`), so a `pass` keeps clearing after
   the code it judged has changed. Only the review back-edge case is caught
   (bug 039).
3. **Nothing records whether a landing was verified.** `land.py` creates no
   commit and writes no stamp; a slice landed through a bypassed gate looks
   like any other in history.

### Decisions (from ADR-0069)

- **D1 — Render, don't assert.** Every Test plan row comes from evidence or
  says `NOT RUN` / `NOT RECORDED`.
- **D2 — Bind reviews to content.** Records carry `reviewed_commit` (where to
  look) and a digest of the deliverables (what decides freshness), captured
  when the prompt is built. Spec 118's worked example is the digest shape.
- **D3 — Report staleness; don't gate it here.** Enforcement is spec 125's
  observe/enforce modes. This spec adds no env var or mode switch.
- **D4 — Stamp every landing, `none` included.** An in-tree landing record,
  mirrored as `Verified-by:` lines in the landing commit's message and the PR
  body, plus a read-only `land.py stamps` query.

### Relation to deferred work

- `docs/refinement-todo.md`, "Decision: Code-staleness hard-gating for review
  evidence" (trigger: "First incident where stale-but-passing evidence lets a
  materially-changed slice transition to `REVIEWED`/`DONE` without re-review.
  Until then, staleness is at most a `check-reviews` warning, not a gate.").
  124-02 builds that interim warning, which was never built
  (`skills/independent-review/SKILL.md:378-380`), using a content digest rather
  than the git-log/mtime reuse the entry suggests (that machinery is
  day-granular: `skills/spec-workflow/workflow.py:2893-2909`). It does not
  fire or replace the trigger. Hard gating still waits for it, and would go
  through spec 125.
- ADR-0014 Scope names the same deferral. ADR-0014 is extended, not amended.

### Non-goals

- A commit gate (unowned — spec 125 supplies modes only; see R-002 open
  questions), or any other blocking on verification (spec 125).
- The `verify` skill and what earns the `verify` token (spec 128).
- Running tests before review (spec 129).
- Binding bug-record evidence. The bug craft and security passes don't go
  through a `review.py` prompt builder (`skills/bug-fix/SKILL.md:335-339`), so
  only `bug-review` could be bound; a half-bound record would mislead. See
  ADR-0069 open question 3.
- CI wiring.

### Related drafts

Spec 125 / ADR-0070 (modes) is where 124-02's report and any "unverified
landing" check would become enforcing. Spec 126 (reviewer recall) can use
`land.py stamps` to see how reverted commits were verified. Spec 127 /
ADR-0072 also adds an optional verdict-record field (`review_rules:`); both
extend ADR-0014 §2 the way `substrate:` did. Spec 128 / ADR-0073 defines what
earns `verify` (ADR-0073 point 5). Spec 129 moves the test run before review; that run is on an
earlier commit than the landing, so 124-01 does not substitute it for its own
run. servo spec 046 binds servo's evaluation evidence the same way. PR #230's
fix-evidence separation (clause 3) keys green evidence to the fix revision,
which is compatible.

## Assumptions

- **A1 — `land.py` already knows the test result; the PR body ignores it
  (grounded).** `check_tests` returns `green`/`red`/`warn`/`not_run`
  (`land.py:309-339`); `prepare` computes it (`:980`) but calls
  `render_pr_body` without it (`:1048`); `execute --mode pr` rebuilds the body
  without checks (`:1537`).
- **A2 — `land.py` creates no commits today (grounded).** Direct mode pushes
  `<branch>:main` (`:1454`); PR mode pushes and opens the PR (`:1545-1549`).
  The landing commit in 124-03 is new behaviour.
- **A3 — jig's own `main` is squash-merged with the PR description as the
  message, and the description is hand-written (grounded).** `87610a9` and
  `1ccd3cd`; no merge commits in the fetched history. Branch-commit trailers
  other than `Co-authored-by:` don't survive (PR #230's `05d123f` carries
  `Claude-Session:`, no squash commit does). `git interpret-trailers --parse`
  on the squash shape returns only `Co-authored-by` (git 2.43).
- **A4 — record-review can't recover deliverables from `prompt_source`
  (grounded).** It is free text, abbreviated in practice (`… <6
  deliverables>` in spec 122's records). A prompt-time sidecar is needed; the
  candidates sidecar is the precedent (`skills/_common/candidate_sidecar.py`,
  consumed at `skills/independent-review/review.py:867`).
- **A5 — anything under `reviews/` named `slice-NN-*.md` is read as a verdict
  (grounded).** `review.py:2102-2106` globs that pattern, so the landing record
  lives in `verification/`, the per-spec evidence directory spec 118 uses.
- **A6 — other GitHub merge settings (not probed).** Squash with "commit
  messages" or "blank", and rebase merges, were not exercised. The in-tree
  record is what keeps the stamp across them (ADR-0069 Assumptions).

## Decomposition

SPIDR (Spike / Paths / Interfaces / Data / Rules), three vertical slices in
build order:

- **124-01 (Rules):** the PR body's Test plan renders real evidence. Usable
  alone: the next PR opened with slice-land stops claiming checks it didn't
  make.
- **124-02 (Data):** review records bind to the deliverables they judged, and
  stale ones are reported before landing. Comes before the stamp so the
  `review` token never counts stale evidence.
- **124-03 (Interfaces):** each landing writes a stamp, `none` included, and
  `land.py stamps` lists unverified commits.

No spike: every surface involved was probed (Assumptions). Per-commit trailers
and git notes were weighed and rejected in ADR-0069.

## Slices

- [124-01 — honest-test-plan](slice-01-honest-test-plan.md) — PR body Test plan rows come from the test run, the recorded verdicts, and the scenario outcomes.
- [124-02 — review-freshness](slice-02-review-freshness.md) — verdict records carry the reviewed commit and a deliverable digest; stale evidence is reported, not gated.
- [124-03 — verified-by-stamp](slice-03-verified-by-stamp.md) — landing record plus `Verified-by:` lines with `none` as a value, and the `land.py stamps` query.
