# Brief: Make gate bypasses observable (don't let heroics be silent)

> EngTip #19 ("Don't Be a Hero") and #20 ("AI, Authorship, and
> Accountability") share a lesson: when you absorb a failure or step
> around a control, *make the cost visible* — silent bypass normalizes
> the behavior and hides the real signal. jig's gates are honestly
> bypassable by design, but the bypasses leave no trace.

## Problem

jig's gates are, per ADR-0011, **deliberateness signals, not
human-only enforcement** — each carries an env-var escape:

- `JIG_REVIEW_EVIDENCE_GATE=0` — skip the review-evidence gate (ADR-0014).
- `JIG_SECRET_SCAN_APPROVED=1` — override the secret-scan hook (ADR-0013).
- `JIG_CONVENTIONS_APPROVED=1` — pass the conventions spec-gate (ADR-0011).
- `JIG_CONTEXT_*` / compact bands — soft context nudges (spec 055/057).

This framing is *honest* (the review even praised it). But the escape
hatches are **un-instrumented**: when a gate is bypassed, nothing is
logged. So:

- A reviewer/maintainer can't tell, after the fact, that a slice reached
  DONE with the evidence gate switched off.
- There's no way to answer "how often is each gate bypassed?" — which is
  exactly the data that tells you whether a gate is *earning its keep* or
  is pure friction (the open question already noted for the spec-gate in
  the parent bundle's brief-08).
- The "deliberateness" claim is only as good as its visibility. A bypass
  that leaves no trace is indistinguishable from the gate never having
  fired — the EngTip #19 "silent heroics" failure mode.

jig already has the infrastructure: `jig-telemetry`
(`hooks/scripts/test_jig_telemetry.py`), the skill-routing trace
(`.claude/skill-usage.jsonl`, spec 041), and `workflow.py routing-stats`
as a read-only histogram surface. A bypass event is a natural sibling.

## Scope

1. **Emit a bypass event** wherever a gate honors its override — the
   review-evidence gate (`workflow.py transition`), the secret-scan hook,
   the conventions spec-gate, and (optionally) the context bands. One
   structured line per bypass: gate name, env var, timestamp, branch/
   spec-ref (reuse spec 056's `.jig/spec-ref` attribution), best-effort.
2. **Pick the sink** — reuse the existing telemetry/JSONL channel rather
   than inventing a new one (prefer-the-standard; mirror
   `.claude/skill-usage.jsonl`). Working-tree-local, gitignored, fails
   open (never block on a telemetry write — ADR-0013 floor pattern).
3. **A read-only digest** — extend `routing-stats` (or a sibling
   `gate-stats`) to print per-gate bypass counts over `--days N`, so the
   "is this gate deadweight?" question becomes answerable.

## Non-goals

- **No new gating, no harder enforcement.** The bypasses stay bypassable
  — ADR-0011's model is deliberate and correct. This brief makes them
  *visible*, not *blocked*.
- **No PII / content capture.** Log that a gate was bypassed and which,
  not the diff or the secret. The secret-scan bypass especially must log
  the *event*, never the matched value.
- **No phone-home.** Local JSONL only, gitignored, like every other jig
  telemetry surface. Nothing leaves the machine.
- **No fail-closed.** A telemetry write failure must never prevent the
  underlying operation (the gate already decided to allow it).

## Suggested SPIDR axis

**D (Data)** primary — the deliverable is a new event record and its
read-only aggregation. **P (Path)** secondary — the bypass code path in
each gate.

## Sketch of slices

1. **bypass-event-emit** — add the structured bypass event at each gate's
   override point, writing to the existing telemetry sink; fail-open;
   gitignored. Tests: each gate emits on bypass, emits nothing on the
   normal path, and a write failure doesn't break the transition/hook.
   Start with the **review-evidence gate** (highest value) and the
   **conventions spec-gate** (directly answers brief-08's open question).
2. **gate-stats-digest** — read-only per-gate bypass histogram over
   `--days N` (extend `routing-stats` or add `gate-stats`). Tests: counts
   aggregate correctly; empty/no-log stays exit 0 (mirror `routing-stats`
   / `stale`).

## Dependencies

- **None blocking.** Builds on existing telemetry (`jig-telemetry`, spec
  041) and spec 056's `.jig/spec-ref` attribution (both DONE).
- **Directly serves parent-bundle brief-08** (spec-gate model): that
  brief's recurring open question is "is the gate catching anything in
  practice?" — this telemetry is the evidence channel that answers it. If
  both are scheduled, do this first.

## Notes for clarify / SPIDR

- Likely clarify question: "Which gates are in scope for v1?" Recommend
  the review-evidence gate + conventions gate first (highest-signal,
  human-policy-adjacent); secret-scan and context bands can follow.
- Likely clarify question: "event-per-bypass or counter?" Per-event is
  more flexible and matches the existing JSONL-append pattern; aggregate
  at read time in the digest.
- Frame in the spec as closing the EngTip #19/#20 loop: jig already
  *allows* the escape honestly; this makes the escape *accountable*.
- The context-band nudges (055/057) are softer and arguably already
  observable via spec 056 usage data — treat them as optional/last.
