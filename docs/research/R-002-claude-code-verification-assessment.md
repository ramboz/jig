---
status: CONCLUDED
topic: The Claude Code team's verification practices read against jig and servo
created: 2026-11-21
related:
  - docs/decisions/adr-0068-base-anchored-gate-definitions.md
  - docs/decisions/adr-0069-commit-bound-verification-evidence.md
  - docs/decisions/adr-0070-gate-modes-off-observe-enforce.md
  - docs/decisions/adr-0071-reviewer-recall-eval.md
  - docs/decisions/adr-0072-diff-triggered-review-rules.md
  - docs/decisions/adr-0073-repo-verify-skill-contract.md
  - docs/specs/123-base-anchored-gate-definitions/spec.md
  - docs/specs/124-commit-bound-verification-evidence/spec.md
  - docs/specs/125-gate-modes-observe-enforce/spec.md
  - docs/specs/126-reviewer-recall-eval/spec.md
  - docs/specs/127-diff-triggered-review-rules/spec.md
  - docs/specs/128-repo-verify-skill/spec.md
  - docs/specs/129-verification-loop-hardening/spec.md
---

# R-002: The Claude Code team's verification practices, read against jig and servo

> This is an **open investigation**, not a decision and not committed work.
> A decision belongs in an ADR (`docs/decisions/`); committed work belongs in
> a spec (`docs/specs/`). This note holds the question, sources, and
> pros/cons *before* either of those is warranted — see
> [ADR-0054](../decisions/adr-0054-research-notes-artifact-convention.md).

## Question

The Claude Code team says Claude writes and reviews about 90% of its code, and
that what makes that safe is how agents verify their work. Which of the
practices in "How the Claude Code team thinks about verification" do jig and
its sibling servo already embody, where are the gaps, and which are worth
adopting?

## Sources / findings

**Provenance.** Primary source: "How the Claude Code team thinks about
verification", claude.dev blog
(`claude.dev/blog/how-the-claude-code-team-thinks-about-verification/`,
2026-11-16). Both it and the New Stack coverage
(`thenewstack.io/anthropic-claude-code-verification/`, 2026-11-20) were
egress-blocked from the authoring environment; the owner supplied the full
text of the primary post on 2026-11-21 and this note is written against that
text. The New Stack figures below come from search snippets only and are
marked as second-hand.

### What the post claims, mechanism by mechanism

Short quotes are verbatim from the primary post.

1. **Verification loops are what make delegation scale.** "Verification loops
   are the building block that lets you delegate more work to Claude." A
   separate grader checking work against a rubric "improved task success by up
   to 10 points over a standard prompting loop" on structured file generation.
   Repeated failures should be turned into a hook or a CLAUDE.md rule.
2. **Test-suite failure modes.** "If your tests are flaky you'll train the
   agent to run them again rather than fixing the failing code." Slow tests mean
   fewer runs; heavier tests belong before commit.
3. **Three test types worth investing in.** End-to-end (hard to fool; a feature
   map doubles as the agent's rubric), property tests (round-trip, invariants,
   idempotency, equivalence — edge cases "not created with the same bias as the
   agent that created the original code"), and differential tests (old system
   as the oracle; normalise noise; keep a list of approved differences).
4. **Verification means running the change.** "Running the app end to end
   matters more than tests." Codify how to boot and drive the app in a skill
   named `verify` under `.claude/skills/`, close to the code; "Claude knows to
   use the verify skill before committing changes." Treat it as the smoke-test
   harness and make it fast and reliable.
5. **Failing checks decide what needs a person.** "If a check is still failing
   after three rounds, Claude stops and brings in a human."
6. **Code owners write their own checks**, and "When a check pulls in a
   reviewer, it should say why".
7. **Reliability checks trigger on the diff.** A 39-item checklist, each item
   with "a trigger that can be read from a diff, a check, and the incidents or
   PRs behind it". Claude runs only the matching items, "usually 3 to 10–so
   nobody has to memorize past outages."
8. **One reviewer, multiple rounds.** "Adding a second, more expensive,
   reviewer on top of the primary one is often a worse approach than tuning the
   primary." A per-area `REVIEW.md` tells the reviewer what to watch; each round
   is pointed "at context from earlier rounds and past failures rather than
   re-checking everything from scratch."
9. **Changes can't modify their own checks.** "If a change can modify the check
   that judges it, the check is broken." Code Review reads `REVIEW.md` from the
   base branch, never the PR. Reviews are bound to commits: "A passing review on
   an out-of-date commit means nothing."
10. **Cheap checks first.** Tests, build, and linter run before a PR opens,
    enforceable with a hook that runs tests when Claude finishes.
11. **Verification stamps and a commit gate.** Each commit is stamped with how
    it was verified; "The stamp even includes "none" so we can query for commits
    that weren't verified." A commit gate blocks a commit when the session lacked
    `/code-review` or `/verify`, with **off / observe / enforce** modes. Observe
    logs what would have been blocked so false positives can be reviewed. A
    commit message can carry an explanation instead of verification, and after
    two blocks in a session the next commit is let through so Claude doesn't get
    stuck.
12. **Review the reviewers.** Track reverts, maintainer rejections before merge,
    and a size-matched clean control. Formally: rebuild the repo at review time
    for each past incident or revert, write a one-sentence answer key, and credit
    only findings that describe that bug; use merged, stable changes as an
    over-flagging control; keep the tuning set apart from the fixed test set;
    measure recall separately for raw findings, post-verification, and the final
    review, so you can see a pipeline losing bugs it found. Rank findings by
    importance (Code Review tags Important / Nit / Pre-existing). Tune recall
    until the next gain would be overfitting.
13. **Turn misses into rules.** Mine human review comments and reverts for
    patterns that occur in at least two PRs and are identifiable from a diff;
    three agents try to disprove each candidate and a human approves it in a PR.
    Separately, replay three bug finders against an incident PR: if at least two
    find it, it is detectable; a miss on a small diff becomes a `REVIEW.md` rule.
14. **Flaky tests.** Claude can't skip them, add sleeps, or retry until they
    pass; without a root cause it deletes the test and writes down why.
15. **Prune.** "Test suites, verification steps and .md files only grow if you
    let them, so we tidy them up on a routine."

**Second-hand (New Stack, via search snippets):** merged PRs more than doubled
between June and September and the revert share fell by more than 40%, but
Anthropic did not isolate verification's contribution, and it has not published
false-positive or false-negative rates for its reviewers. Read the post as a
practice report, not as evidence of effect size.

### Where jig and servo stand

Probed 2026-11-21 against `main` at jig `87610a9` and servo `17b9ae9`.

| Mechanism | jig today | servo today |
|---|---|---|
| Run the change (4) | Spec 118 adds optional "Verification scenario" sections with pass / fail / not-run / environment-error outcomes; no repo-owned "how to run the app" artifact; nothing gates on it. | design-eval captures the running app for visual fidelity; `_gather_candidate` (running the system under test) is a deliberately unbuilt seam (`refinement-todo.md`). |
| Cheap first (10) | CI runs lint and tests for jig itself; for specs, the green-tests check sits at slice-land, *after* review. | `oracle.sh.template` runs every component and averages, so judged components run even when tests score 0. |
| Can't modify own checks (9) | Governance plane (ADR-0051) scaffolds CODEOWNERS + a protected-path workflow, but the workflow runs `on: pull_request` (the PR's own copy). `review.py` config is read from the working tree. jig does not run its own governance plane. | Freeze hashes are "tripwires for honest drift … not a sandbox" (`docs/architecture.md`); approval records live in the same worktree as the runner. |
| Bound to a commit (9, 11) | Review records carry `reviewed_at`, not a commit. `land.py` writes hard-coded `[x] All ACs pass` lines into PR bodies. Code-staleness gating for review evidence is deferred. | Run state and ledgers carry no evaluated commit; `gate.py` writes no ledger. |
| Off / observe / enforce (11) | Gates are on/off with `JIG_*_GATE=0` bypasses; spec 078 logs bypass events. | `oracle-hook` blocks a stop once, then lets the next through (aligned with the anti-stuck valve). |
| Diff-triggered checklist (7, 13) | `learnings.md` (~1,500 lines of prose) never reaches the reviewer; review passes are switched on by author-set flags. | Nothing equivalent. |
| Three rounds then a human (5) | Spec 122: an arch `ESCALATE:` stops the slice and rounds are carried; no numeric round cap for any pass. | Loop caps (5 iterations, plateau window 3) and quarantine; escalation is recorded, not raised. |
| Review the reviewers (12) | `evals/` only scores skill routing. No reviewer eval set; reviewer prompt changes are not re-scored. | `judge_audit` (spec 008-06) calibrates one eval's judge against human labels, advisory only; judge definition changes force re-freeze but not re-audit. |
| Property tests (3) | Not nudged by tdd-loop. | Not used in spec-oracle check families. |

Already aligned: the independent-review subagent is the post's separate grader;
ADR-0055 folded leanness into existing passes rather than stacking a reviewer;
tdd-loop already forbids weakening, skipping, `xfail`-ing or quarantining a test;
bug-fix refuses DONE without a learnings entry; spec 118 and servo both refuse
to read "not run" as a pass.

**Related in-flight work (unmerged):** jig PR #230 (R-001, the Cloudflare ADLC
read) proposes convention-rule severity with advisory/enforced promotion and
agent fix-evidence separation. Its spec and ADR numbers are provisional and
already collide with `main`, so the artifacts promoted from this note cite it by
PR number. Overlap to reconcile at merge: rule severity (post item 12), rule
promotion (items 11, 13), and fix-evidence separation (item 9).

## Options / pros & cons

- **Adopt as structure, not as a copy.** Most of the post's ideas already exist
  in jig and servo as intent; the gaps are mechanical (checks readable by the
  change they judge, evidence not bound to a commit, reviewers never measured).
  Closing those keeps jig's lifecycle and adds no new review pass. Preferred.
- **Add more review passes or a second reviewer.** Rejected by the post's own
  finding and by ADR-0055; measure the existing passes first (ADR-0071).
- **Make everything enforcing immediately.** Rejected: jig's gate philosophy is
  deliberateness plus out-of-band control (ADR-0011), and the post itself rolls
  new gates out through observe mode (ADR-0070).
- **Differential tests.** No current migration consumer in either repo; noted,
  not promoted.

## Open questions

- Does `pull_request_target` (or a base-ref read) fit every host jig scaffolds
  for, and what is the fallback without GitHub Actions? (ADR-0068)
- Who owns the reviewer eval's model-call cost, and is a run per reviewer-prompt
  change affordable? (ADR-0071)
- Should the verify-skill contract be one file across Claude Code, Codex, and
  Copilot, or one per host? (ADR-0073)

## Conclusion

Adopt the post's verification-as-a-system stance through six jig decisions and
three servo decisions. Each decision is Proposed and must be Accepted before its
spec moves past DRAFT. Spec and ADR numbers were reserved with `--no-push` on a
working branch, so they are provisional until merged.

Promoted to:

- jig: [ADR-0068](../decisions/adr-0068-base-anchored-gate-definitions.md) /
  [spec 123](../specs/123-base-anchored-gate-definitions/spec.md) — gate
  definitions read from the base ref, plus jig dogfooding its governance plane.
- jig: [ADR-0069](../decisions/adr-0069-commit-bound-verification-evidence.md) /
  [spec 124](../specs/124-commit-bound-verification-evidence/spec.md) —
  verification evidence bound to a commit, with `none` recorded.
- jig: [ADR-0070](../decisions/adr-0070-gate-modes-off-observe-enforce.md) /
  [spec 125](../specs/125-gate-modes-observe-enforce/spec.md) — off / observe /
  enforce gate modes.
- jig: [ADR-0071](../decisions/adr-0071-reviewer-recall-eval.md) /
  [spec 126](../specs/126-reviewer-recall-eval/spec.md) — reviewer recall
  measured against jig's bug history.
- jig: [ADR-0072](../decisions/adr-0072-diff-triggered-review-rules.md) /
  [spec 127](../specs/127-diff-triggered-review-rules/spec.md) — structured,
  diff-triggered review rules with promotion and pruning.
- jig: [ADR-0073](../decisions/adr-0073-repo-verify-skill-contract.md) /
  [spec 128](../specs/128-repo-verify-skill/spec.md) — a repo-owned `verify`
  skill as the run-the-app contract.
- jig: [spec 129](../specs/129-verification-loop-hardening/spec.md) — tests
  green before review, a three-round cap, property-test nudges.
- servo (`ramboz/servo`): ADR-0051 / spec 045 (freeze anchored to the base
  ref), spec 046 (commit-bound evaluation evidence), ADR-0052 / spec 047
  (deterministic components gate judged ones), ADR-0053 / spec 048 (judge
  regression set), spec 049 (verify skill as candidate gathering).
