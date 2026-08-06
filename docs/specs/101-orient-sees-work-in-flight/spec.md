---
status: DONE
skill: orient
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 101: Orientation sees work in flight

> Reserved on 2026-07-22 via `workflow.py new`.

## Overview

Orientation answers *"where are we, what's next?"* from durable artifacts on
disk. Both layers — the deterministic `workflow.py orient` headline (slice
088-01) and the `/jig:orient` judgment briefing (slice 088-02) — read only the
**project's own files**. Neither looks at the collaboration layer: open pull
requests, and local commits that have not reached the default branch.

That makes a specific, repeatable failure. A status board describes the default
branch. Work that is *finished* but parked — in an open PR awaiting the owner,
or on a branch nobody merged — is invisible to every artifact orientation reads.
So orientation reports the project as though that work does not exist, and
confidently calls it unblocked.

The sharper half is what unattended workers do. A night/cron worker that
finishes a run opens a PR and writes **its questions for the owner in the PR
description** — not into any file in the repo. Orientation never opens that
description, so an agent asked "what's next" re-derives the question set from
the raw review artifacts instead, arrives at a worse-framed subset, and puts it
to the owner as if it were new.

**Field incident (2026-07-22, downstream `bouge` project).** An overnight worker
left a PR titled *"(5 decisions need you)"*, whose body posed five specific
questions in plain language with recommendations. A "what's next" pass surveyed
specs, ADRs, `refinement-todo.md`, the inbox, the bug board, commits and
branches — every local source — and never ran `gh pr list`. It found the same
*work* as an unmerged branch and concluded it was uncommitted drafts. It then
re-derived the questions from the review files, got four of the five, missed the
fifth entirely, and put worse-framed versions of the other four to the owner,
who had to answer them a second time. The owner's words: *"so I ask you what is
next and you don't see the PR...?"*

The fix is not a new subsystem. It is teaching both layers that **"what's next"
means what is blocked on a human, not what the repo contains** — the filesystem
gives state, the PR queue gives what is waiting on a decision.

## Current state (verified)

Read on `origin/main` @ `fd7115a` (2026-07-22):

- **`workflow.py orient()`** (`skills/spec-workflow/workflow.py:1687`) composes
  its headline from `classify_scaffold_state()`, `collect_slices()`,
  `_active_spec_summary()` and `_focus_summary()`. Its docstring states it "uses
  durable jig artifacts only". It runs no `git` and knows nothing about
  branches.
- **`skills/orient/SKILL.md`** — `grep -niE 'pull request|gh pr|branch'` returns
  **zero hits**. The survey (lines 82–130) lists spec status, DEFERRED triggers,
  standalone bugs, ADRs, refinement/deferred decisions, release plans and
  "recent work — the last few commits". The fixed output layout has nine
  sections and none of them is for work awaiting review.
- **The SessionStart hook** `hooks/scripts/jig-project-orient.sh` invokes
  `orient` with `timeout=4` and treats a non-zero exit as silent success. Any
  new work inside `orient` therefore has a hard latency budget and must never
  turn a working headline into no headline.
- **git is already established practice in this file.** `workflow.py` shells out
  to `git` for `slice-land` and the main-worktree sync (`:1105`, `:1114`,
  `:1125`, `:2758`, `:2844`, `:3069`, `:3126`). `_common/team_signal.py:60,69`
  does the same, and `_common/test_team_signal.py` shows the house pattern for
  testing it: `git init` a real repo in a temp dir.
- **An existing test pins the headline byte-for-byte.**
  `ProjectOrientationTests.test_scaffolded_headline_compacts_active_specs`
  (`skills/spec-workflow/test_workflow.py:8191`) asserts the complete string. Any
  added segment must be *absent* by default or that test breaks — which is the
  correct pressure, and this spec keeps it green rather than editing it.

## Assumptions

- **A1 — `git` is on `PATH` and the default branch is discoverable.** Neither is
  guaranteed: a scaffolded project may not be a git repo at all, may have no
  remote, or may name its trunk something other than `main`. **Mitigation is
  structural, not hopeful** — every git call is wrapped, bounded by an explicit
  timeout, and any failure (missing binary, not a repo, no resolvable base,
  timeout, non-zero exit) omits the segment rather than propagating. AC2 and AC3
  test this directly, so A1 failing degrades the headline to exactly today's
  behaviour and never worse.
- **A2 — `gh` availability is *not* assumed.** The pull-request survey lands in
  the judgment skill, never in the deterministic CLI, precisely because
  `gh pr list` needs network and auth and the CLI runs inside a 4-second
  SessionStart hook. The skill is instructed to report the tool's absence in one
  line rather than silently omitting the section.

## Decomposition

SPIDR — **Rules** axis. One vertical slice at the orientation boundary.

- **101-01 — orientation reports work in flight.** The deterministic segment,
  its tests, and the judgment-layer survey ship together. Splitting them would
  be textbook horizontal phasing: a headline that flags unmerged commits while
  the briefing still ignores the PR queue leaves the reported incident only
  half-fixed, and a survey change with no deterministic signal leaves the
  SessionStart hint as blind as it is today. Both layers are small; the value
  only exists when both land.

No Spike is needed — `orient()`, the hook's timeout, the existing git call
sites, the test pattern, and the byte-exact headline test were all read
directly and are cited above.

## Slices

- [101-01 — orientation reports work in flight](slice-01-orientation-reports-work-in-flight.md)
