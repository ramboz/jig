---
slice: 103-01 — SessionStart git-freshness nudge
pass: frame-critique
verdict: pass
reviewer: reviewer-subagent (2 rounds)
reviewed_at: 2026-08-03T17:51:27Z
prompt_source: review.py frame-critique docs/specs/103-session-git-freshness/spec.md 103-01
---

Slice-level frame-critique on 103-01 (SessionStart git-freshness nudge). Two
adversarial rounds against fresh read-only reviewers, pre-implementation.

Round 1 (needs-changes): the "base-first (origin/main), @{upstream} last-resort"
resolution rule was wrong for git-flow / fork / explicit-base-tracking repos,
where @{upstream} IS the integration base (e.g. a feature branch tracking
origin/develop) but origin/main also resolves — so origin/main-first mismeasures
and the "sync origin/main" advice is misleading, contradicting the ADR's claimed
downstream generality.

Round 2 (PASS): resolution reworked to a smart-target rule — (1) prefer
@{upstream} iff it resolves AND is not the branch's own remote
(origin/<current-branch>); (2) else origin/main→origin/master; (3) else silent.
The own-remote guard routes jig's pushed task branch to the trunk (correct for
#105 base drift), git-flow to origin/develop, and forks to upstream/main — pinned
by an own-remote-guard regression test and a non-own-upstream-wins precedence
test plus the anti-dead-gate silent path. Consistent across ADR + spec + slice +
tests. Reviewer: "None survive — frame holds." Remaining edges
(fork-tracks-own-fork, detached HEAD, exotic upstreams) are bounded by the
soft/fail-open/opt-out design and named in the wrong-base kill criterion.
