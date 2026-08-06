---
status: Accepted
dependencies: []
last_verified: 2026-08-03
frame_review: true
---

# ADR-0048: SessionStart git-freshness — always-fetch, timeout-guarded, active nudge

## Status

Accepted (2026-08-03)

## Context

A jig session can start on a worktree/branch that has silently drifted behind
its upstream. When it does, the agent forms its whole premise — "what's built",
spec/slice `STATUS`, file contents — from stale state *before any gate runs*.
[Issue #105](https://github.com/ramboz/jig/issues/105) reports a real incident
where a local `origin/main` was 18 commits ahead of the working branch at
session start.

jig already has freshness-adjacent signals, but none covers *git branch*
staleness at time-zero:

- `jig-context-check.sh` → **context** freshness (fill %, MCP count).
- `jig-project-orient.sh` → orientation headline from jig artifacts.
- spec-workflow `last_verified` → **spec/ADR** staleness.
- [Bug 001](../bugs/001-branch-freshness-preflight.md) (DONE) → a
  `HEAD..origin/main` warning, but only inside `land.py prepare` and the
  REVIEWED/RECONCILED transitions — **at command time, and only if you reach
  those commands.** Issue #105 explicitly calls this out as insufficient:
  the stale premise is already formed by then.

The gap is an **earlier tripwire** — one that fires at `SessionStart`, before
the agent trusts repo state. This ADR records the two load-bearing shape
decisions for that hook. It is a sibling of the
[lifecycle entry gate](adr-0044-lifecycle-entry-gate.md) (ADR-0044) and the
[context-cost discipline](../specs/055-context-cost-discipline/spec.md) hooks:
same soft, fail-open, never-block philosophy.

The issue left five questions open for the maintainer. Three take their
conventional jig default and are not load-bearing enough to record here (opt-out
`JIG_GIT_FRESHNESS=0` matching the other hooks; warn at any `N>0`; a new
SessionStart hook script). **Two are load-bearing and settled against the
proposal's own stated bias** — the reason this ADR exists is precisely that a
future agent (or the issue author's own draft) would plausibly reverse them.

## Decision Options Considered

The two settled questions, with the alternatives rejected.

### Question 1 — how the hook obtains the remote ref

**Option A — fetch-free (the proposal's bias).** Compare `HEAD` against the
already-known local `origin/main` ref. Instant, cannot hang, no network.
- **Pros:** Zero latency; can never hang a session — the proposal's stated
  reason to prefer it. **And it already catches the one recorded incident:** in
  #105 the local `origin/main` was 18 commits ahead of the working branch, so
  the divergence was visible *without* any fetch. Fetch-free is not a strawman;
  it is a real, cheaper option that handles the motivating case.
- **Cons (a hypothesis, not evidence — see Assumptions):** in a
  downstream/scaffolded project the local ref may be only as fresh as the user's
  last fetch, so a stale local `origin/main` could report "up to date" against a
  branch that is really behind the true remote. This staleness is **plausible
  but unprobed** — we have not measured how often a downstream checkout's local
  `origin/main` actually lags at session start. If it rarely lags, Option A
  loses little.

**Option B — always fetch, timeout-guarded (chosen).** Attempt a
`git fetch` of the upstream at session start under a hard subprocess timeout,
then compute `HEAD..<upstream>` against the (now refreshed) ref.
- **Pros:** It is a **safe superset** of Option A — never *worse* for
  correctness, because on timeout/offline it falls through to exactly the local
  ref Option A would have used, and when the fetch succeeds it can only *add*
  freshness. It covers the unprobed stale-local-ref case above at no correctness
  risk. The hard timeout is the safety the proposal wanted fetch-freeness for:
  the fetch is killed at the timeout and the hook falls through, so it cannot
  hang the session.
- **Cons:** Buys nothing over Option A for the recorded incident, and adds a
  bounded network cost on every genuine session start whose benefit rests on the
  unprobed downstream-staleness hypothesis. This is the honest cost of choosing
  the superset before the hypothesis is measured — accepted deliberately (see
  Recommended Decision), with the under-fire/latency kill criteria as the
  post-ship check.

**Option C — always fetch, unbounded.** Rejected outright: reintroduces the hang
the proposal was right to fear.

### Question 2 — what the warning does

**Option A — active nudge to sync (chosen).** Warn, and explicitly recommend
syncing (fetch + merge/rebase) before trusting repo state, plus the command to
review the incoming commits.
- **Pros:** Actionable at the exact moment the premise is being formed; tells
  the agent what to *do*, not merely that something is off.
- **Cons:** A stronger steer; must be phrased as advice, never as an auto-run
  action (jig recommends, never executes git state changes — ADR-0011).

**Option B — warn-only, informational.** Print the behind-count, no suggested
action. Rejected: leaves the agent to infer the remedy at the very moment its
context is least reliable.

## Recommended Decision

**Always fetch under a hard timeout, and emit an active nudge to sync.**

The hook attempts `git fetch <remote> <branch>` for the resolved base target
(see "Upstream semantics" below — a real non-own `@{upstream}` if present, else
the `origin/main`/`origin/master` trunk) bounded by `JIG_GIT_FRESHNESS_TIMEOUT`
(default 5s, well under the hook-level timeout), then compares `HEAD..<base>`
and, when the branch is behind, emits an
`additionalContext` nudge that (a) states the behind-count and base ref, (b)
recommends syncing before forming conclusions, and (c) gives the command to
review the incoming commits. It is fail-open (always exits 0, never blocks),
opt-out via `JIG_GIT_FRESHNESS`, and audited via
`append_additional_context_event`.

**This is chosen with eyes open.** The sole recorded incident (#105) is
catchable without fetching (Option A handles it), and the accuracy edge Option B
adds rests on the *unprobed* downstream-staleness hypothesis. The maintainer's
call is to ship the safe superset — never worse for correctness — over the
proposal's fetch-free bias, accepting a bounded per-session network cost now and
letting the kill criteria (under-fire / latency) decide post-ship whether the
fetch earns its keep. A cheap pre-ship probe (how often a downstream checkout's
local `origin/main` is stale at session start; how often a 5s fetch completes vs.
times out) would strengthen the call and is noted as a kill-criterion trigger,
not a blocker.

**The timeout is the load-bearing safety, not fetch-freeness.** The fetch is a
best-effort freshness *improver* on a comparison that is always the local
`rev-list`: on success the local ref is current; on timeout/offline the hook
falls through to the last-known ref and still compares (a stale-but-real
"behind" is still worth surfacing). This unifies both paths — the fetch never
gates correctness, only accuracy — so the hook can honour "always fetch" while
being structurally incapable of hanging.

### Upstream semantics and nudge cadence (why "behind" means "stale premise")

The nudge is only useful if "HEAD is behind the target" reliably means "the
premise I'm about to form is stale," and not "this is a normal mid-flight
branch." The target must be the **integration base** — the ref this branch
integrates *into* — which is not the same thing as either "always `origin/main`"
or "always `@{upstream}`". Getting this precedence right is the single most
load-bearing part of the design, so the rule is recorded in full:

**Target resolution (in order):**

1. **`@{upstream}`, when it resolves and is NOT this branch's own remote
   (`origin/<current-branch>`).** A tracking upstream that points at something
   *other* than the branch's own remote branch is a real integration base — the
   git-flow feature branch tracking `origin/develop`, the fork workflow tracking
   `upstream/main`, or a branch explicitly `set-upstream-to` its base. In those
   models `@{upstream}` *is* the base, and `origin/main` may not be — so this
   case wins.
2. **`origin/main`, then `origin/master`** — the trunk base, used when there is
   no usable tracking upstream (rule 1 didn't fire). This is jig's own case:
   under the one-worktree-per-task convention a task branch is pushed to its
   *own* remote, so `@{upstream}` resolves to `origin/<that-branch>` and is
   excluded by rule 1's own-remote guard; the branch is *cut from* `origin/main`
   (the `worktree.baseRef: fresh` setup forks off `origin/HEAD`), so `origin/main`
   is the true base. `HEAD..origin/main` is also precisely what bug 001's
   `land.py._check_ff_viable()` measures.
3. **Otherwise silent** (not a work tree, or no target resolves).

**Why the own-remote guard in rule 1 is load-bearing.** Once a jig task branch is
pushed, `@{upstream}` = `origin/<that-branch>`, and `HEAD..@{upstream}` measures
*whether my own remote branch advanced* — ~0 for a solo task branch — **not**
whether my base drifted. A naïve "prefer `@{upstream}`" rule would go **silent on
the #105-shaped case** (a resumed, pushed branch whose `origin/main` base moved
18 commits compares HEAD against its own up-to-date remote → 0 behind → silent).
The own-remote guard is exactly what keeps rule 1 from swallowing that case while
still honouring a genuine non-main integration base. A future agent simplifying
this to "just `@{upstream}`" *or* "just `origin/main`" reintroduces a blind spot
in one branching model or the other — this is why both halves are recorded.

A freshly cut branch is **0 behind → silent** under this rule; it becomes
"behind" only once its base advances underneath it — exactly the stale-base
condition #105 describes, and the reason this is a *real* signal, not a permanent
background state.

**The honest exposure:** in a high-velocity trunk (jig itself — many concurrent
sessions land daily), a *resumed* older task branch will be behind `origin/main`
at most session starts until it is rebased, so with the settled "warn at any
`N>0`" threshold the nudge may fire on most resumes of a long-lived branch. Each
such fire is *correct* (the base really has aged), but repeated correct fires can
still train the agent to tune the nudge out — a dead-gate-by-fatigue failure the
anti-dead-gate test (which only pins the silent-when-fresh path) cannot catch.
This is accepted for now, with two escape hatches: the `JIG_GIT_FRESHNESS`
opt-out, and a **behind-floor threshold knob deliberately deferred** until a real
fatigue complaint justifies it (spec § Settled call 5). The fatigue mode is
added to the kill criteria below so it is watched explicitly, distinct from
under-fire.

## Consequences

**Becomes easier:**
- A session that starts on a drifted branch is told so before it reads a single
  file — the #105 incident is caught at time-zero.
- The check is meaningfully accurate in downstream projects, not just in the
  maintainer's push-kept-current worktree setup.

**Becomes harder:**
- Every genuine session start pays a bounded (≤ timeout) network cost. Mitigated
  by skipping the `compact` SessionStart source (no re-fetch on mid-session
  compaction) and by the opt-out.
- A future "optimisation" back to fetch-free would silently regress accuracy —
  this ADR exists to make that reversal a conscious, recorded choice.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **`git fetch` honours a subprocess timeout and a killed fetch leaves the
  working tree and refs usable.** Grounded: `git fetch` only advances
  remote-tracking refs; interrupting it leaves prior refs intact, and the
  subsequent `rev-list` reads whatever ref state exists. `land.py`'s
  `_check_ff_viable()` already fetches `origin/main` at command time in this
  codebase (bug 001), so the fetch-then-compare shape is proven here.
- **The Claude host delivers a SessionStart `source` field** (`startup` /
  `resume` / `clear` / `compact`) usable to skip the `compact` re-fetch. Not yet
  probed on a live payload; the hook degrades safely if the field is absent or
  differently named — it simply runs on every SessionStart (an extra bounded
  fetch on compaction, never an error). Marked as an assumption, not asserted.
- **The heuristic "`@{upstream}` ≠ `origin/<current-branch>` ⇒ it is an
  integration base" holds across the common branching models.** It is correct
  for git-flow (`origin/develop`), fork workflows (`upstream/main`), explicit
  `set-upstream-to` a base, and jig's own convention (where `@{upstream}` *is*
  the own remote, so the guard correctly falls through to `origin/main`). It
  could misfire only if someone sets a branch's upstream to an unrelated,
  non-base branch — an uncommon, self-inflicted setup. The failure is bounded:
  the hook is soft, fail-open, and opt-out, so a wrong target produces a
  spurious (or absent) advisory nudge, never a block or a mutation. Recorded as
  an assumption, watched by the "wrong-base" kill criterion.
- **SessionStart hooks run identically on the Codex host.** Grounded by probe:
  `hosts/codex/plugins/jig/hooks/hooks.json` already registers
  `jig-context-check.sh`, `jig-project-orient.sh`, and `jig-semantic-index.sh`
  under `SessionStart`, so the mechanism is established; the new hook is
  host-agnostic (pure git + stdout) and rides `build_host_packages.py` regen to
  both hosts.

## Kill criteria

- **Fetch buys no accuracy (probe result).** If a pre-ship or early-real-use
  measurement shows downstream checkouts' local `origin/main` is rarely stale at
  session start, or the 5s fetch usually times out (so the hook falls through to
  the local ref anyway), then Option B adds latency for no accuracy over
  fetch-free — default to fetch-free compare, keeping fetch as an opt-in.
- **Nudge fatigue / fires on normal mid-flight branches.** If the nudge fires so
  often on routinely-behind resumed branches that the agent tunes it out (a
  dead-gate-by-fatigue the anti-dead-gate test cannot see), promote the deferred
  behind-floor threshold from "settled at N>0" to a real default, or gate the
  nudge on additional signal (e.g. base age, not just commit count).
- **Wrong-base mismeasurement in an unanticipated topology.** If the target
  heuristic (Assumptions) picks the wrong ref in some real branching model — so
  the nudge fires against, or stays silent against, a ref that is not the
  branch's true integration base, and the "sync `<base>`" advice is misleading —
  refine the resolution rule (e.g. read a configured base, or consult the host's
  known trunk) rather than the current two-rule heuristic.
- **Session-start latency.** If the bounded fetch measurably degrades
  session-start responsiveness even at a low timeout, reconsider gating the
  fetch behind an opt-in and defaulting to fetch-free compare.

## Open questions

None. The three non-recorded questions took their conventional jig default
(see Context); the two load-bearing questions are settled above.
