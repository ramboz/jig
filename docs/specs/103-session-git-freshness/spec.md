---
status: DONE
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 103: SessionStart git-freshness hook

## Overview

A jig session can start on a worktree/branch that has silently drifted behind
its upstream. When it does, the agent forms its whole premise — "what's built",
spec/slice `STATUS`, file contents — from stale state *before any gate runs*.
[Issue #105](https://github.com/ramboz/jig/issues/105) reports a real incident:
a local `origin/main` was 18 commits ahead of the working branch at session
start, and everything downstream was reasoned against the dead premise.

jig has freshness-adjacent signals, but **none covers git-branch staleness at
time-zero**: `jig-context-check.sh` (context fill), `jig-project-orient.sh`
(orientation headline), and `last_verified` (spec/ADR age) all look elsewhere.
[Bug 001](../../bugs/001-branch-freshness-preflight.md) (DONE) added a
`HEAD..origin/main` warning — but only inside `land.py prepare` and the
REVIEWED/RECONCILED transitions, **at command time and only if you reach those
commands.** Issue #105 names exactly that gap: the stale premise is already
formed by the time a `transition`/`land` runs. This spec adds the missing
**earlier tripwire** — a `SessionStart` hook.

[ADR-0048](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md)
(Proposed 2026-08-03) records the two load-bearing shape decisions; this spec
implements them. The hook is a sibling of the
[lifecycle entry gate](../098-lifecycle-entry-gate/spec.md) and
[context-cost](../055-context-cost-discipline/spec.md) hooks: soft, fail-open,
never-block. The mechanism is deliberately modelled on machinery already in the
tree:

- **`jig-context-check.sh`** — the co-located `SessionStart` sibling this hook
  joins: a thin `bash` wrapper delegating to a testable `lib/*.py` helper,
  emitting a soft `additionalContext` nudge, with an opt-out env var and
  `except Exception: pass`.
- **`land.py` `_check_ff_viable()`** — the proven fetch-then-compare-`origin/main`
  shape already in this codebase (bug 001).
- **`append_additional_context_event`** (`lib/read_attribution.py`) — the
  existing auditable-trace path every soft nudge uses.

## What this spec does NOT do

- **It does not block, prompt the owner, or run any git command that mutates
  state.** jig recommends; it never runs `fetch`/`merge`/`rebase` *for* you
  beyond the read-only `git fetch` that advances remote-tracking refs
  ([ADR-0011](../../decisions/adr-0011-spec-gate-model.md)). Always exits 0.
- **It does not replace bug 001's command-time warning.** The two are
  complementary — this is the time-zero tripwire; bug 001 is the last-line
  check before landing. Neither depends on the other.
- **It does not add a configurable threshold.** Warn at any `N>0` behind
  (settled default, see below). A behind-floor knob is deliberately out of
  scope until a real noise complaint justifies it.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — ground factual claims by probe/citation, else list
     them here. Risk-gated. -->

- **`git fetch` honours a subprocess timeout and a killed/failed fetch leaves
  refs usable for the subsequent `rev-list`.** Grounded: fetch only advances
  remote-tracking refs, and `land.py._check_ff_viable()` already fetches
  `origin/main` at command time here — the fetch-then-compare shape is proven in
  this codebase.
- **The Claude host delivers a SessionStart `source` field** (`startup` /
  `resume` / `clear` / `compact`). **Not yet probed on a live payload** — no
  existing hook reads SessionStart `source`. The hook must degrade safely: if
  the field is absent or differently named it simply runs on every SessionStart
  (an extra bounded fetch on compaction, never an error). Load-bearing enough to
  drive `frame_review`.
- **SessionStart hooks run identically on the Codex host.** Grounded by probe:
  `hosts/codex/plugins/jig/hooks/hooks.json` already registers the three
  existing SessionStart hooks, so the mechanism is established. The new hook is
  host-agnostic (pure git + stdout) and rides `build_host_packages.py` regen to
  both hosts — so host parity is a regen + assertion, not separate host-specific
  work (contrast spec 098-02, which had to re-probe a host-specific payload).

## Decomposition

**SPIDR analysis.** Spike — not needed (the shape is settled by ADR-0048 and the
fetch mechanism is proven by bug 001). Paths — there is one path: session start →
check → maybe nudge. Interfaces — a single host-agnostic hook that regen mirrors
to both hosts; the Codex "parity" is mechanical (`build_host_packages.py`), not a
distinct payload-shaped surface, so it does **not** earn its own slice (that
would be a near-empty "regen and confirm" slice — horizontal phasing). Data /
Rules — one rule (behind → nudge), no data subsets.

**Result: a single vertical slice.** It ships the SessionStart nudge end-to-end
across both hosts, with scaffold parity. Both-host package parity is asserted in
the slice DoD rather than split out.

## Slices

| Slice | Title | Status | Why |
|-------|-------|--------|-----|
| 103-01 | SessionStart git-freshness nudge | DONE | The whole spec: a fail-open SessionStart hook that fetches (timeout-guarded) and actively nudges to sync when the branch is behind its integration base. Host-agnostic; scaffold + both-host parity in DoD. |

### Settled calls (maintainer)

Issue #105 posed five open questions. The maintainer settled them 2026-08-03:

1. **In scope for jig? — yes.** Built as this spec.
2. **Fetch behavior — always fetch, timeout-guarded.** Rejects the proposal's
   own fetch-free bias; the hard timeout (not fetch-freeness) is the
   never-hang safety. See
   [ADR-0048 Q1](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md#question-1--how-the-hook-obtains-the-remote-ref).
3. **Response style — active nudge to sync.** Rejects warn-only; recommend
   fetch/rebase before trusting state. See
   [ADR-0048 Q2](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md#question-2--what-the-warning-does).
4. **Opt-out env var — `JIG_GIT_FRESHNESS=0`** (widened token set
   `{0,false,off,no}`, matching the other hooks). Conventional default.
5. **Threshold — warn at any `N>0` behind.** No behind-floor knob. Conventional
   default. **Known tradeoff (frame critique):** on a high-velocity trunk a
   *resumed* long-lived task branch is routinely behind `origin/main` until
   rebased, so `N>0` may fire on most resumes — each fire correct (the base
   really aged), but repeated correct fires risk training the agent to tune the
   nudge out. Accepted for now; escape hatches are the `JIG_GIT_FRESHNESS`
   opt-out and a deferred behind-floor knob. See
   [ADR-0048 § Upstream semantics and nudge cadence](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md#upstream-semantics-and-nudge-cadence-why-behind-means-stale-premise).

## Acceptance (spec-level)

- The hook fires at `SessionStart`, co-located with the three existing
  SessionStart hooks in `hooks/hooks.json`, and ships to both hosts.
- It attempts a timeout-guarded `git fetch` of the resolved **integration base**
  (a real non-own `@{upstream}` when the branch tracks a base other than its own
  remote — git-flow/fork/explicit; else the `origin/main`/`origin/master` trunk —
  per [ADR-0048 § Upstream semantics](../../decisions/adr-0048-session-git-freshness-fetch-and-nudge.md#upstream-semantics-and-nudge-cadence-why-behind-means-stale-premise)),
  then nudges — actively recommending a sync — iff `HEAD` is behind that base,
  and is otherwise silent.
- It never blocks, never mutates working-tree state, always exits 0, and is
  opt-out via `JIG_GIT_FRESHNESS`.
- It degrades (never errors) when: not in a repo, no upstream resolvable, git
  missing, offline, or the fetch times out — falling back to a best-effort
  compare against the last-known ref.
- Scaffold-mode parity: a scaffolded install ships and registers the hook
  (`verify_install._EXPECTED_HOOK_SCRIPTS`, scaffold.py, the hook-count
  contract test), and both host packages reference the script.
- **The hook demonstrably fires and demonstrably stays silent** — a behind
  branch nudges; an up-to-date branch is silent (the anti-dead-gate proof).
