---
status: DRAFT
dependencies: [adr-0070, 125-01]
last_verified: 2026-11-21
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 125-02 — observe-report-and-promotion

**Goal:** a maintainer can see, per gate, how often it refused, would have
refused, and was bypassed; list the recent fires to check them for false
positives; and follow a written rule to move a gate from `observe` to
`enforce` (or back).

**Decision:** [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md)
§5. Resolves the trigger of the `docs/refinement-todo.md` entry "gate-bypass
digest denominator" (*"A maintainer wants to make a keep/retire decision on a
gate from data"*).

**DoR:**
- ⬜ ADR-0070 Accepted; 125-01 `DONE` (the resolver and `gate_would_block`
  exist).
- ✅ Events append to `.claude/skill-usage.jsonl` through
  `_common/gate_telemetry.py:24-52` (fail-open, content-free).
- ✅ `workflow.py gate-stats` reads that file, filters on `event`, windows by
  `--days` (`workflow.py:3221-3285`, CLI at `:5943-5952`).
- ⬜ Check PR #230's state: if its per-rule fire counts in `gate-stats` have
  merged, share its table shape instead of adding a second one.

**Assumptions:** None beyond spec A5.

**Acceptance Criteria:**

1. **Refusals are recorded.** Every refusal by a resolver-backed gate in
   `enforce` appends a `gate_blocked` event with the same fields as
   `gate_would_block` (gate, reason codes, spec ref, `mode_source`,
   timestamp). Fail-open: a failed write never changes the refusal.
2. **`gate-stats` counts fires.** For every registered gate, and any other
   gate name seen in the window, it prints `blocked`, `would-block` and
   `bypassed` counts plus the gate's current mode and source for this
   project (from the resolver, so a gate with no events still shows its
   mode). Pre-125 `gate_bypassed` rows count as
   `bypassed`; unknown event types and malformed lines are skipped, as today.
3. **A false-positive view.** `gate-stats --gate <name>` lists that gate's
   most recent `gate_blocked` and `gate_would_block` events, newest first,
   capped at 20: timestamp, event, spec ref, reason codes, `mode_source`.
   Read-only, exit 0, including for an unknown gate name (which says so).
4. **An honest legend.** The legend replaces the "no denominator" caveat
   (`workflow.py:3279-3284`): `blocked` + `would-block` are fires,
   `bypassed` is the escape being used, and a gate with zero fires "did not
   fire in the window", which is not a verdict that it is useless.
5. **A written promotion rule.** `docs/workflow.md` and
   `templates/docs/workflow.md.template` state it:
   - a new gate ships `observe` unless its spec argues for `enforce`;
   - promote to `enforce` after reviewing the gate's fires with
     `gate-stats --gate`, when every false positive found is fixed or
     accepted as a known exception;
   - demote to `observe` when a false positive blocks real work;
   - record each promotion or demotion as a lightweight decision
     (`decisions.py`) that cites the window reviewed. No automatic promotion.

**Edge cases to cover explicitly:**
- A sink with only pre-125 `gate_bypassed` rows renders as before plus zero
  fire columns.
- A gate configured `observe` with no events in the window still appears with
  its mode.
- `--gate` with more than 20 events shows the newest 20 and says how many
  were omitted.
- Events older than `--days` are excluded from both the table and `--gate`.

### Verification scenario

**Preconditions:** a temp project with `scaffold.json` setting
`gates.review-evidence.mode` to `observe`, one slice missing its compliance
verdict.

**Invocation:** `workflow.py transition <spec> <slice> REVIEWED`, then
`workflow.py gate-stats --project-dir <tmp>` and
`workflow.py gate-stats --project-dir <tmp> --gate review-evidence`.

**Preserved behavior:** `gate-stats` on a project with no sink still exits 0
with a "not found" message (today's `no gate-bypass data — … not found`,
reworded only if the fire counts make "bypass" too narrow).

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| 1 | AC2 | `review-evidence` row: would-block 1, mode `observe (config)` | | not-run | |
| 2 | AC3 | one `gate_would_block` line naming the missing compliance verdict | | not-run | |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule (only if this slice closes the
      spec).

**Anti-horizontal-phasing check:** after this slice, a maintainer running
a gate in `observe` can open one report, read what it would have refused,
and make and record the promote-or-not call from that evidence.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO_ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `updated` | _TODO: mark "gate-bypass digest denominator" resolved by this slice._ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
