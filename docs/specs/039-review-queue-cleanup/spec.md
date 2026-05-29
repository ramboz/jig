---
status: DONE
skill: (none — agent definition cleanup)
tier: (none — dev infrastructure)
---

# Spec 039: Drop the dead `.claude/review-queue.json` contract

## Overview

`agents/implementer.md:32` instructs the implementer subagent to write
deliverable paths to `.claude/review-queue.json`. The file exists in
the jig repo, currently tracked in git, with one stale entry from
slice 005-02 (DONE May 2026). **Zero consumers.** A grep across the
codebase (`.py`, `.sh`, `.md`) finds only:

- The `implementer.md` instruction itself.
- Two historical references in old spec.md files (008, 014) — doc
  artifacts, not runtime consumers.

No skill reads it. No helper reads it. No hook reads it. The reviewer
subagent gets its file paths *via the prompt* (built by `review.py`),
not from this queue.

The file is: **specified, partially implemented, never consumed,
confusing**. Drop it.

## Why now

- **Decision is clean.** This session's analysis ruled out the
  "keep + document as external orchestrator handoff" path: jig's
  review loop is in-session (Claude spawning Claude), not async.
  A CI-driven review surface would want spec frontmatter, not a
  per-project JSONL queue.
- **It's the pattern spec 036 is trying to stamp out.** A
  documented contract with zero consumers is dead state masquerading
  as an interface.
- **Adjacent finding.** The file is committed to the repo and not
  gitignored — fix this as part of the same slice.

## Goals

1. **Remove the instruction.** Delete the bullet from
   `agents/implementer.md` describing the write-to-queue step.
2. **Remove the tracked file.** `git rm .claude/review-queue.json`
   to drop the stale entry from version control.
3. **Defensive gitignore.** Add `.claude/review-queue.json` to
   `.gitignore` so a future agent that mistakenly re-creates it
   (before the instruction propagates to every install) doesn't
   re-commit it.
4. **Confirm no other reference points at it.** Verify the two
   historical spec.md mentions in 008 and 014 are doc-history
   (not runtime contracts) — no fix needed there.

## Non-goals

- **No new review-queue tooling.** Dropping means the file is not
  a contract at all.
- **No retroactive scan** for other dead-state files. This spec
  covers one specific instance.
- **No edits to the historical spec.md references in 008/014.**
  Those are reconciled spec prose — they fall under spec 036's
  amendment convention, not this spec's scope. (If spec 036
  picks "immutable closed specs," the references stay as
  historical record.)

## Current state (verified 2026-05-26)

- `agents/implementer.md:32` — instruction still present.
- `.claude/review-queue.json` — **exists in the worktree** and
  **is tracked in git** (`git check-ignore` returned nothing).
- Consumer grep across `.py` / `.sh` / `.md`: zero live consumers.
  Only matches are (a) the implementer.md instruction, (b)
  `docs/specs/008-migrate-existing-project/spec.md:960`,
  (c) `docs/specs/014-arch-review/spec.md:415, 527`.

## Decomposition

**Single slice.** The decision is binary (drop vs. keep — already
decided this session); the action is small.

### Slices (TBD until clarify runs)

1. **`039-01 drop-review-queue-contract`** —
   - Remove the bullet at `agents/implementer.md:32`.
   - `git rm .claude/review-queue.json`.
   - Add `.claude/review-queue.json` to `.gitignore`.
   - Confirm no other doc still references the queue (grep clean
     post-edit). If 036 has landed and picked "amendment section,"
     append amendments to specs 008 and 014; otherwise leave them
     as historical record per 036's chosen policy.
   - Single commit, single review pass.

## Open questions for `/jig:clarify`

- **Q1.** Did the spec that originally added this instruction ship
  a consumer that was later removed, or was it always orphaned?
  Worth checking the git history of `agents/implementer.md` and
  the originating spec. Affects framing in the slice's deviation
  log only.
- **Q2.** Should the spec 008 / 014 references be touched? Depends
  on spec 036's policy outcome — if (a) immutable, leave them; if
  (b) amendment, add `## Amendments` notes.

## Dependencies / coordination

- **Light coordination with spec 036.** Q2 above. The slice can
  land before 036 by leaving the 008/014 references untouched; a
  later 036 sweep can address them under its convention.
- **None upstream from other clusters.**

## References

- External review brief: [`brief-07-review-queue-cleanup.md`](../../external-review/brief-07-review-queue-cleanup.md)
- This session (2026-05-26): decision to drop, with rationale —
  jig's review loop is in-session; the file is dead-state
  masquerading as a contract.
- Verification 2026-05-26: file tracked in git, not gitignored,
  zero live consumers.
