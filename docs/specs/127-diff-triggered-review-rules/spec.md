---
status: DRAFT
skill: independent-review
use_cases: [UC-7, UC-8]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 127: Diff-triggered review rules

> Implements [ADR-0072](../../decisions/adr-0072-diff-triggered-review-rules.md)
> (Proposed). Investigation record:
> [R-002](../../research/R-002-claude-code-verification-assessment.md).
> **Status: recorded, not yet built** — the ADR must be Accepted before 127-01
> moves past DRAFT.

## Overview

Every bug jig closes leaves a lesson in `docs/memory/learnings.md`: the bug
`→ DONE` gate refuses without one (`skills/bug-fix/bug.py:1035-1040`). No
reviewer ever reads those lessons. `review.py` mentions memory only to forbid
writing to it (`skills/independent-review/review.py:149-150`). The lessons are
also prose, with nothing that says which diff they apply to. The Claude Code
team's answer (R-002 items 7, 8, 13 and 15) is a short checklist of rules. Each
rule has a trigger that can be read from a diff, one check, and the incidents
behind it. Only the matching rules reach the reviewer, new rules need two
occurrences and a human's approval, and the list is pruned on a routine.

This spec builds that loop on surfaces jig already has:

- **127-01:** a structured `docs/memory/review-rules.md`. The craft (slice) and
  `bug-review` (bug) prompts carry the rules whose trigger matches the diff,
  read from the base ref, at most 10, each with its provenance.
- **127-02:** a bug record can carry a rule candidate in its `## Learning`
  section. `memory-sync` promotes a candidate to an active rule once it has two
  occurrences, and the change lands in a code-owner-reviewed PR.
- **127-03:** each review record says which rules were shown, and
  `memory-sync` reports which rules never fire or never find anything, so they
  can be pruned.

**Decisions (ADR-0072 §1–§7, summarized):**

- **D1 — one file, active rules only; candidates stay in bug records.** The
  reviewer-facing file holds only what gets injected. Candidates sit beside
  their evidence, and `bug.py` never writes to `docs/memory/`.
- **D2 — inject into craft and `bug-review` only, not compliance.** Both
  compliance and craft run on every slice
  (`skills/_common/review_evidence.py:293-295`). Compliance walks the ACs one
  by one; craft looks at the change as a whole, which is where a diff-level
  check belongs. On the bug path, `bug-review` is the only pass `review.py`
  builds, because bug craft runs the `pr-review` skill directly
  (`skills/bug-fix/SKILL.md:334-339`). One injection site per lifecycle means
  a rule's finding is reported once.
- **D3 — read from the base ref, through spec 123-03's seam.** A change cannot
  edit the rules that judge it (R-002 item 9). This spec depends on the
  `_common` seam from slice 123-03 of
  [spec 123](../123-base-anchored-gate-definitions/spec.md) and follows its
  rules:
  - the base rules apply, with a notice when the branch edits the file;
  - a file absent at the base means no rules;
  - the working tree is read only under the seam's deliberate bypass.

  With no base there is no diff to select against, so the prompt says rules
  are unavailable.
- **D4 — the reviewer only reads.** Its tools, prohibitions and agent
  definition are unchanged. Only `memory.py` writes the rules file, and the file
  becomes a governance protected path.
- **D5 — no new pass, no new gate.** Rules ride existing passes and do not
  change the verdict rule (ADR-0014 §3) or which passes run.

### What this spec does not claim

- **The refinement-todo loop.** "Instrument the review→learnings→clarify loop
  before building it" (`docs/refinement-todo.md:140-152`) has a trigger of
  "≥3 distinct specs" and records "**Count today: 1**". That trigger has not
  fired. This spec is owner-directed from R-002. It builds the reviewer's
  *read* path and a harvest that starts from bug records. It does not build
  that entry's `[spec]`-theme rollup or the clarify grounding pass. It honors
  the entry's routing rule: harvest goes through `memory-sync`, "**NOT** the
  read-only reviewer". 127-03's report counts rule ids, not finding themes.
- **The inbox entry `memory/correction-must-be-read-at-invocation`**
  (`docs/inbox.md:68`). This spec is the "skill-scoped pull at invocation" that
  entry asks for, for the review skill only. Recall for other skills stays open
  there.
- **PR #230's convention rules.** That open PR proposes severity and promotion
  for `docs/conventions.md` rules. Those are protected project conventions;
  review rules are incident-derived and diff-scoped. The two files and their id
  namespaces stay separate (ADR-0072 §7).
- **Siblings.**
  - [Spec 126](../126-reviewer-recall-eval/spec.md) (reviewer recall eval) is
    the optional detectability check for a candidate and the measure of whether
    rules help (126-02's optional rules arm). Nothing here depends on it.
  - [Spec 124](../124-commit-bound-verification-evidence/spec.md)-02 captures
    the reviewed commit and a deliverables digest when the prompt is built.
    When that capture exists, 127-03 records the shown rule ids there, at
    prompt time, instead of recomputing them at record time.
  - [Spec 125](../125-gate-modes-observe-enforce/spec.md)'s `observe` mode is a
    possible rollout path for new rules (ADR-0072, open question).
  - Spec 129 (three-round cap) is unrelated.

## Assumptions

- **A1 — the reviewer never sees learnings (grounded).** `grep -n -i
  "memory\|learnings" skills/independent-review/review.py` → only the
  prohibition (`review.py:149-150`) and a refinement-todo pointer inside the
  craft output format (`review.py:903`). `agents/reviewer.md:48` repeats the
  prohibition.
- **A2 — the bug record has a `## Learning` section, and DONE checks
  learnings (grounded).** `_record_text` emits `## Learning`
  (`bug.py:303`). `_learning_recorded` (`bug.py:726-736`) substring-matches
  `bug NNN` or the record's filename in `learnings.md`.
- **A3 — a merge-base diff has precedent (grounded).** `_touched_files_block`
  (`review.py:480-546`) runs `git merge-base main HEAD` and `git diff
  --name-only`, with the base hard-coded as `main` (`review.py:447`).
  127-01's selection takes the same approach, using the base that spec
  123-03's `resolve_base` returns instead of a literal `main`. On a branch that
  holds several slices, the diff includes earlier slices' changes too, as
  today's block does.
- **A4 — templates and summary (grounded).** Any
  `templates/docs/**/*.md.template` is emitted by `scaffold-init`
  (`skills/scaffold-init/scaffold.py:3978-3988`). `memory.py summary` counts
  only glossary and learnings headings (`skills/memory-sync/memory.py:533-553`).
- **A5 — verdict records take optional fields (grounded).** `record-review`
  already stamps an optional `substrate:` line (`review.py:2061-2072`, spec
  096-05).
- **A6 — `memory.py` owns `docs/memory/` (grounded).** `decisions.py`'s
  docstring (`skills/memory-sync/decisions.py:9-11`) states it. The rules
  commands therefore go in `memory.py`, not a new helper.
- **A7 — governance glob grammar (grounded).** `PROTECTED_PATHS`
  (`skills/scaffold-init/governance.py:60-67`) and `path_matches_glob`
  (`governance.py:77`) give a `**` / `*` grammar. `governance.py` is
  stdlib-only and imports no `_common`, so sharing the grammar means lifting the
  function into `_common`; 127-01 decides.
- **A8 — spec 123-03's seam (sibling draft, not built).** The 123-03 draft
  defines:
  - `resolve_base` — spec 103's base rule;
  - `read_at_base(project_dir, relpath)` — text plus source (`base` or
    `working-tree`), the ref used, and a fallback reason;
  - `modified_on_branch` — commits, uncommitted edits and untracked files
    against the merge base;
  - a `JIG_BASE_DEFINITIONS=0` bypass.

  127-01's AC3 is written to that contract. If 123-03 changes it, AC3
  follows.
- **A9 — reviewers apply injected checks (not grounded).** This includes
  reviews where a richer craft skill "supersedes the baseline buckets"
  (`review.py:960-968`). Spec 126 can measure it.
- **A10 — enough repeats exist (not grounded).** We assume jig's bug history
  holds patterns that clear two occurrences. No count was made.
- **A11 — closed bug records stay closed (grounded).** Editing a DONE record
  needs owner approval (ADR-0010, spec 102; spec 126 D1 makes the same call).
  Candidate blocks therefore come from bugs still in flight, and historic
  lessons become rules by hand-writing an active entry (127-01).

## Decomposition

SPIDR, along the path a rule travels:

- **Interfaces / Data (127-01):** the rule file contract, its lint and
  template, and the read path into two existing prompts. It is usable on its
  own: an owner hand-writes a rule in a PR, and the next matching review
  checks it.
- **Paths (127-02):** the harvest path, from bug record to candidate to
  active rule through `memory-sync`.
- **Rules (127-03):** the fire record and the pruning rules that keep the file
  small.
- **Spike:** none. Whether rules help is measured by spec 126, not by a spike
  here.

**Anti-horizontal-phasing.** Each slice changes something a user sees:

- 127-01: what a reviewer is asked.
- 127-02: what closing a bug can produce.
- 127-03: what the session-end routine proposes to remove.

## Slices

- [127-01 — rules-reach-the-reviewer](slice-01-rules-reach-the-reviewer.md) — structured `review-rules.md` + lint + template, base-ref read, diff selection, capped injection into craft / `bug-review` with provenance.
- [127-02 — bug-candidates-and-promotion](slice-02-bug-candidates-and-promotion.md) — optional candidate block on the bug →DONE edge, `memory.py` candidate listing and promotion at two occurrences.
- [127-03 — fire-record-and-pruning](slice-03-fire-record-and-pruning.md) — `review_rules:` stamp on verdict records, per-rule shown/cited report, prune proposals in the `memory-sync` routine.
