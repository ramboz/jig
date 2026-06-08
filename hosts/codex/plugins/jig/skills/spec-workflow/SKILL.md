---
name: spec-workflow
description: >
  Drive the spec-driven lifecycle for any non-trivial work item: SPIDR-split a
  new spec into vertical slices, transition state markers (DRAFT → READY_FOR_REVIEW
  → READY_FOR_IMPLEMENTATION → IN_PROGRESS → REVIEWED → RECONCILED → DONE; also
  DEFERRED for parked slices with a stated resolution trigger), enforce the
  reconciliation checklist before commit, and surface stale specs/ADRs whose
  `last_verified` date has aged past dependency changes. Use when starting
  non-trivial new work, creating a spec, transitioning a slice's state,
  parking a slice as DEFERRED, reconciling a reviewed slice, or auditing
  doc freshness. Do not use for quick one-off fixes that don't need a spec,
  or for bug-shaped work where `debug-workflow` is the better fit.
user-invocable: true
---

> Spec 003 promoted this skill from stub to active. The deterministic state
> mutations live in `workflow.py`; this SKILL.md drives the judgment layer.

## What this skill does

- Guides SPIDR-splitting a new spec into vertical slices (Spike last, not first —
  try Rules / Data / Interface / Path first).
- Flags slices that look like horizontal phasing (no user-facing layer touched).
- Drives the spec lifecycle state transitions via `workflow.py`.
- Coordinates implementer + reviewer subagent invocations at the right points.
- Enforces the reconciliation checklist before a slice goes DONE.
- Consults `docs/memory/glossary.md` when drafting ACs to surface unknown domain terms.
- Surfaces skill-routing observability via `workflow.py routing-stats [--days N]` —
  a read-only histogram of which skills fired (jig baseline vs. richer/"other"
  skill per category) from `.codex/skill-usage.jsonl` (slice 041-02).

## SPIDR splitting

All non-trivial specs are SPIDR-split into vertical slices before
implementation begins. **Spike is the last resort — try Path /
Interface / Data / Rules first.**

- **S — Spike**: research/learning activity. Only when none of P/I/D/R
  apply. AI agents default to spiking too eagerly — resist.
- **P — Path**: split by alternative paths through the story (happy
  path first, edge paths later).
- **I — Interface**: split by UI / platform / channel (minimal first,
  polish later).
- **D — Data**: split by data subset or format (less data first).
- **R — Rules**: split by business rules (simple first, edge cases later).

**Anti-horizontal-phasing rule:** every slice must touch the
user-facing layer and deliver end-to-end value. A slice that touches
only the DB or only the parser is horizontal phasing — re-split.

See [`worked-example-spidr-split.md`](worked-example-spidr-split.md)
for one applied example per axis plus a jig-native dogfood case (spec
017's three-axis split). The canonical primer for all five axes lives
at [`docs/spec-workflow/spidr-primer.md`](../../docs/spec-workflow/spidr-primer.md).

### Spike slices

When SPIDR's S axis fires during decomposition (none of P / I / D / R
apply because the team doesn't yet know enough to pick), the
resulting slice is marked `kind: spike` in its frontmatter — the
typed enum that `spec_lint.py` validates.

**When to introduce a spike during decomposition.** Reach for S only
after trying R / D / I / P. The bias to resist is "let me research
this first" as a prelude to "now let me build it as one big slab" —
that is horizontal phasing in a trench coat. If the spike would
conclude with "now ship the implementation," the implementation IS
the slice, and the research goes inside it.

**Body shape (four labelled blocks).** A `kind: spike` slice carries
four blocks alongside the standard Goal / DoR / AC / DoD scaffolding.
**Each label must be written with the trailing colon (`**Question:**`,
etc.) — that is what `spec_lint.py` matches against.**

- **Question:** — one sentence stating the open question. Set at DRAFT.
- **Time-box:** — explicit budget (e.g., "1 day", "4 hours"). Set at DRAFT.
- **Findings:** — bullet evidence collected during the spike. Filled
  during IN_PROGRESS.
- **Outcome:** — one of `ADR-NNNN created` / `spec NNN-NN unblocked` /
  `abandoned (reason)`. Multiple outcomes separated by `;`
  (e.g., `ADR-0007 created; spec 030-02 unblocked`). Set at DONE.

`spec_lint.py` soft-warns when a `kind: spike` slice is missing any of
the four labels — mid-flight spikes legitimately have empty Findings /
Outcome, so this is a warning, not a hard error.

**Always nested, never standalone.** Spike slices live inside a real
spec — never as a standalone `docs/spikes/` artifact. The
1-slice-spec case (no clear downstream spec yet, just an
investigation) collapses to "spawn a normal spec where the only slice
is `kind: spike`." This forces the investigator to articulate the
downstream change up front and keeps jig at two numbered families
(specs+slices, ADRs).

**Abandoned-spike manual-reshape failure mode.** When a spike's
Outcome is `abandoned (reason)`, dependents are NOT automatically
cascade-flagged. The human (or the next session) audits each
dependent slice and decides whether the original design still holds.
Automation here over-fires: "approach A abandoned" often means
"approach B from the same findings still satisfies the dependents."
`workflow.py` deliberately stays out of the cascade business; the
SKILL.md hand-off is the documented gate.

## How to use

### Creating a new spec

1. Confirm the work needs a spec. Trivial fixes don't.
2. **Reserve the next free number on origin/main:**

   ```bash
   python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" new <slug>
   ```

   The helper computes `max(NNN) + 1` across `docs/specs/`, writes a
   minimum stub `docs/specs/NNN-<slug>/spec.md` (frontmatter + Overview
   + SPIDR-analysis headers), commits it as
   `docs(specs): reserve NNN-<slug>`, and pushes to `origin/main`. If
   the push is refused by branch protection / permissions, the helper
   automatically falls back to a `reserve/NNN-<slug>` branch + `gh pr
   create`. This locks the number **team-wide** before any drafting
   begins, killing the parallel-worktree spec-number-collision failure
   mode logged across specs 014/015/016/017.

   **Works from any branch or worktree** (ADR-0015 / spec 051). The
   helper routes on the current branch: on `main` it runs the proven
   in-place flow (clean tree required, since the commit lands on local
   `main`); off `main` — a feature branch or a linked `.codex/worktrees/*`
   worktree — it builds the reservation commit in an *ephemeral detached
   worktree* checked out at `origin/main` and pushes it by SHA, never
   touching your branch, cwd, or working tree. You no longer need to
   switch to `main` (and a linked worktree can't, anyway).

   Flags: `--no-push` for solo machines without a remote, or for an
   off-main *provisional* reservation committed on the current branch
   (the number is local-view and may collide at merge — treat it as
   provisional); `--pr` to skip the direct-push attempt on
   protection-locked main.
3. Create `docs/specs/NNN-<slug>/{spec.md,plan.md,tasks.md}` with the conventional
   structure: status frontmatter, overview, SPIDR analysis, ordered slices.
4. SPIDR-split: for each slice, the goal is **one vertical piece** that delivers
   end-to-end value. Spike is the last resort, not the first reach.
5. For each new slice, use the template at
   `templates/docs/specs/slice-template.md` — it ships the canonical
   frontmatter shape (`status`, `dependencies`, `last_verified`) plus
   DoR / AC / DoD / Close-out sections. Set `status: DRAFT` in the
   frontmatter. Legacy slices that use prose `**STATUS: DRAFT**` markers
   still work (lazy migration); no need to rewrite them.
6. Add rows to `docs/specs/README.md` (or regenerate via `workflow.py status-board`).

### Picking up a slice

1. Check `docs/specs/README.md` for the next slice in `READY_FOR_IMPLEMENTATION`
   (or `DRAFT` for a slice you intend to plan now).
2. Run:
   ```bash
   python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" transition \
     "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" IN_PROGRESS
   ```
   **Claim-on-IN_PROGRESS (spec 049-01).** On a frontmatter (file-per-slice)
   slice this stamps `claimed_by:` (the current branch name, or
   `JIG_CLAIM_ID`) so parallel worktrees don't both pick up the same slice.
   It refuses if the slice is already claimed by a *different* identifier and
   still `IN_PROGRESS` — naming the holder and pointing at `--release`. The
   claim is **local by default**; add `--push` (direct) or `--pr` (via PR) to
   reserve it on `origin/main` so other worktrees see it (race / protected-
   branch handling mirrors `workflow.py new`). The claim is cleared on the
   forward move to `REVIEWED` and on any back-transition to
   `READY_FOR_IMPLEMENTATION` / `DRAFT`. To force-release a stale claim:
   `transition <spec> <slice> READY_FOR_IMPLEMENTATION --release --reason
   "<why>"` (clears `claimed_by:`, logs to the slice's `## Release log`).
3. Fill in / refresh `plan.md` and `tasks.md` for the slice.
4. Spawn the `implementer` subagent with the spec path. Implementer writes the
   deliverable to disk (TDD — failing tests first).

### After implementation

Slices 031-01 + 031-02 + 060-05 wired a **multi-pass review flow** into the
post-implementation step. Every slice runs through two passes before the
`IN_PROGRESS → REVIEWED` transition; two further passes fire on demand —
the **arch** pass when the slice declares `arch_review: true`, and the
**code-health** pass when it declares `code_health_review: true`.

The orchestrator runs the passes in this order:

1. **Compliance pass — `jig:independent-review`** (always). Spawn the
   `reviewer` subagent against the deliverable using the prompt built by
   `review.py implementation`. Reviewer is read-only; it evaluates each
   acceptance criterion and returns
   `pass | fail | needs-changes`.

2. **Craft pass — `pr-review`** (always). After the compliance pass
   returns, build the craft-pass prompt with `review.py pr-review` and
   spawn a second `reviewer`-shaped subagent. The reviewer is read-only
   (Read/Glob/Grep, **no `Skill` tool**), so it cannot route to a skill
   via Codex's skill router; instead `review.py` detects a user-installed
   `pr-review` skill on disk (`$HOME/.agents/skills/pr-review/`) and the prompt
   points the reviewer at that concrete path to read-and-apply, falling
   back to jig's inlined baseline buckets (scope / blockers / nits /
   strengths) when none is installed. (File-read dispatch — spec 031
   Open-question-#1 option (b); a live probe showed the original
   prose-router dispatch was inert on the no-Skill-tool subagent path.)
   The pass returns the same `VERDICT / REASONING / SPECIFIC ISSUES /
   RECONCILIATION NOTES` envelope as the compliance pass, with
   SPECIFIC ISSUES entries tagged `[blocker]` / `[nit]` / `[strength]`.

3. **Arch pass — `arch-review`** (on-demand). Before running this pass,
   query the slice's `arch_review:` frontmatter flag via
   `workflow.py arch-review-needed`. When the helper prints `true`,
   build the arch-pass prompt with `review.py arch-review` and spawn a
   third `reviewer`-shaped subagent. The pass produces the four
   canonical arch buckets (summary / strengths / concerns / open
   questions) wrapped in the same verdict envelope, using the same
   file-read dispatch (`review.py` detects `$HOME/.agents/skills/arch-review/`,
   else inlines jig's baseline buckets). When the helper prints `false`, skip this
   pass entirely. Slice authors flip the flag by uncommenting the
   `arch_review: true` line in the slice template's frontmatter — set
   it when the slice changes module boundaries, public contracts, or
   architecture-shaped concerns.

4. **Code-health pass — `jig:code-health`** (on-demand, **gated**). Before
   running, query the slice's `code_health_review:` frontmatter flag via
   `workflow.py code-health-review-needed`. When it prints `true`, **run
   `health.py` yourself** (the orchestrator / CI), capture its tight
   summary, and feed THAT summary into `review.py code-health … --summary-file`
   (or via stdin). Then spawn a `reviewer`-shaped subagent. **The reviewer
   is read-only (Read/Glob/Grep, no Bash) — it must NOT run `health.py`;
   it judges the summary you provide.** The reviewer renders the judgment a
   tool can't: is duplication within the [ADR-0002](../../docs/decisions/adr-0002-extract-helper-on-third-caller.md)
   inline-mirror budget? is a complex function inherent or fixable? are
   the lint findings worth blocking on? The pass returns the same verdict
   envelope, with SPECIFIC ISSUES tagged `[blocker]` / `[nit]` /
   `[strength]`. **Why gated, not always-on:** [ADR-0017](../../docs/decisions/adr-0017-scaffolded-code-health.md)
   flags the per-slice review cost (specs 055/057 context-cost discipline)
   and recommends gating it like arch-review — so it defaults off and slice
   authors opt in with `code_health_review: true`. The evidence file is
   `reviews/slice-NN-code-health.md`.

**Block rule for the REVIEWED transition.** All required passes
(compliance + craft, plus arch when `arch_review: true`, plus code-health
when `code_health_review: true`) must pass before
`transition <slice> REVIEWED`:

- Any `fail` verdict from any pass blocks the transition.
- `needs-changes` from the compliance pass blocks (the implementer
  addresses findings and re-runs).
- `needs-changes` from the craft pass does NOT block — the
  `[nit]`-tagged entries become reconciliation-log items (the
  implementer captures them in the deviation log during reconciliation).
  Only `[blocker]`-tagged entries from the craft pass block the
  transition.
- The arch pass follows the same rule as the craft pass:
  `[blocker]`-tagged entries block; `[nit]`-tagged entries and
  `needs-changes` become reconciliation-log items.
- The code-health pass follows the same rule: `[blocker]`-tagged entries
  block the `REVIEWED` transition; `[nit]`-tagged entries become
  reconciliation-log items.

**The gate is mechanical, not advisory (slice 045-03 / [ADR-0014](../../docs/decisions/adr-0014-review-evidence-model.md) §5).**
`workflow.py transition` now *refuses* the `REVIEWED` / `RECONCILED` /
`DONE` moves unless the required review evidence — recorded with
`review.py record-review` as `docs/specs/NNN-<slug>/reviews/slice-NN-<pass>.md`
— exists and clears (`verdict: pass`). `REVIEWED` requires
`compliance` + `craft` (+ `arch` when the slice declares
`arch_review: true`, + `code-health` when it declares
`code_health_review: true`); `RECONCILED` requires the `reconciliation` verdict
**and** a `### Deviation log` subsection; `DONE` re-validates the whole
set (in addition to the existing `dependencies:` check). A refusal names
the missing/invalid artifact and the `record-review` command to produce
it. The gate enforces *evidence consistency*, not human sign-off (it
lives in the agent's trust boundary per [ADR-0011](../../docs/decisions/adr-0011-spec-gate-model.md)).
Bypass it for a deliberate out-of-band flow by setting
`JIG_REVIEW_EVIDENCE_GATE=0` (also `false`/`off`/`no`) — the status still
transitions and the `DONE` dependency check still runs; only the evidence
check is skipped.

After all required passes pass:

4. Address any reviewer findings, adding regression tests for any real
   bugs found.
5. **Record each pass's verdict** as durable evidence with
   `review.py record-review` (writes
   `docs/specs/NNN-<slug>/reviews/slice-NN-<pass>.md` — see the
   independent-review SKILL.md § "Recording and checking review
   evidence"). The `REVIEWED` transition is gated on this evidence, so it
   is not optional.
6. Transition: `transition <spec.md> <slice> REVIEWED`. The gate
   re-validates the recorded `compliance` + `craft` (+ `arch`,
   + `code-health`) verdicts before the status flips (and before the
   003-04 auto-tick).

**Recovering from a failed review.** A `fail`/`needs-changes` verdict — or
a `[blocker]`-tagged craft/arch finding, which is recorded as a non-`pass`
verdict — blocks the `REVIEWED` transition. To recover: address the
findings, re-run the pass against the updated deliverable, `record-review`
the new verdict (it **overwrites in place** the earlier file for that
`(slice, pass)`; git history keeps the prior one), then re-run
`transition … REVIEWED`. With every required pass now `pass`, the gate
clears. A non-`pass` artifact never overwritten by a later `pass` keeps
blocking — the "superseded without a later pass" case (ADR-0014 §4).

```bash
# Compliance pass (always)
PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  implementation "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" \
  "<deliverable-path-1>" ...)
SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type implementation)
# … feed $PROMPT to Task with subagent_type: $SUBAGENT, wait for pass …

# Craft pass (always)
PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  pr-review "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" \
  "<deliverable-path-1>" ...)
SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type pr-review)
# … feed $PROMPT to Task with subagent_type: $SUBAGENT, wait for pass …

# Arch pass (only when slice frontmatter has `arch_review: true`)
# IMPORTANT: capture the helper exit code — a non-zero exit means the
# slice lookup failed (missing spec / unknown fragment / ambiguous),
# not "no arch pass needed." Surface the error rather than silently
# skipping the pass.
if ! NEED_ARCH=$(python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" \
    arch-review-needed "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>"); then
  echo "arch-review-needed failed — aborting" >&2
  exit 2
fi
if [ "$NEED_ARCH" = "true" ]; then
  PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    arch-review "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" \
    "<deliverable-path-1>" ...)
  SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    subagent-type arch-review)
  # … feed $PROMPT to Task with subagent_type: $SUBAGENT, wait for pass …
fi

# Code-health pass (only when slice frontmatter has `code_health_review: true`)
# The orchestrator runs health.py and feeds its summary IN — the read-only
# reviewer never runs the tool (no Bash).
if ! NEED_CH=$(python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" \
    code-health-review-needed "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>"); then
  echo "code-health-review-needed failed — aborting" >&2
  exit 2
fi
if [ "$NEED_CH" = "true" ]; then
  # Run the jig:code-health runner yourself (health.py check .) and capture
  # its tight summary to /tmp/health-summary.txt — the read-only reviewer
  # MUST NOT run it. (The runner ships with the Tier-1 jig:code-health skill;
  # if it isn't installed, note "summary unavailable" and judge on the
  # deliverables.)
  PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    code-health "docs/specs/NNN-<slug>/spec.md" "<slice-fragment>" \
    "<deliverable-path-1>" ... --summary-file /tmp/health-summary.txt)
  SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    subagent-type code-health)
  # … feed $PROMPT to Task with subagent_type: $SUBAGENT, wait for pass …
fi
```

### Reconciliation (REVIEWED → RECONCILED)

Walk the **Reconciliation checklist** below. Every item is a gate.

### Closing the slice

1. After the reconciliation review passes, **record its verdict** with
   `review.py record-review … --pass reconciliation`, then
   `transition <spec.md> <slice> RECONCILED`. That move is gated on the
   recorded `reconciliation` verdict (`pass`) **and** a `### Deviation log`
   subsection under the slice heading (ADR-0014 §5).
2. Commit the work.
3. After commit: `transition <spec.md> <slice> DONE`. `DONE` re-validates
   the whole evidence set — `compliance` + `craft` (+ `arch`,
   + `code-health`) + `reconciliation` — on top of the existing
   `dependencies:` check.
4. Regenerate the board: `workflow.py status-board <project-dir>`.
5. Run `/jig:memory-sync` (or `memory.py`) to consolidate any new learnings.

## Spec lifecycle states

```
DRAFT → READY_FOR_REVIEW → READY_FOR_IMPLEMENTATION → IN_PROGRESS
  → REVIEWED → RECONCILED → DONE

         DEFERRED ⇄ DRAFT  (parked slices with a stated resolution trigger)
```

Status transitions are mutations on either `spec.md`'s frontmatter `status:`
field (new convention, slice 015-01) or the prose `**STATUS: ...**` line
(legacy — still supported via lazy migration), AND the matching row in
`docs/specs/README.md`. Use `workflow.py transition` for the spec mutation
and `workflow.py status-board` to re-sync the board.

**Spec-level `status:` is derived, not authored** (slice 030-01). The
frontmatter `status:` at the top of each `spec.md` overview file is
computed by `compute_spec_status(spec_path)` from its slices: `DONE` when
every non-DEFERRED slice is DONE, `DRAFT` when no slices exist or every
non-DEFERRED slice is DRAFT (and `DRAFT` when every slice is DEFERRED),
otherwise `IN_PROGRESS`. The rollup write happens automatically inside
`workflow.py transition` (after the slice mutation) and inside
`workflow.py status-board` (during regen). Don't set `spec.md`'s
`status:` by hand — it'll be overwritten on the next transition or
regen anyway.

### DEFERRED state

A slice is `DEFERRED` when scoped but parked — the work is identified but
not the current priority. Different from `DRAFT` which means "not yet
fleshed out." Transitions:

- Any state → `DEFERRED` is allowed.
- `DEFERRED` → `DRAFT` (re-open) is allowed.
- `DEFERRED` → any other state is **refused** — re-open via DRAFT first
  so review gates aren't silently skipped. This is the first
  FROM-state-restricted transition in jig's lifecycle.

When transitioning a slice to `DEFERRED`, add a `**Resolution trigger:**`
line in the slice body (same convention `docs/refinement-todo.md` uses).
The status-board renders deferred slices in a separate `## Deferred slices`
section with that trigger as the per-row context.

### Slice frontmatter (slice 015-01 convention, file shape per 018-03)

New slices written from `templates/docs/specs/slice-template.md` are
whole-file templates — frontmatter at the top, `## Slice ...` heading
immediately following the closing frontmatter delimiter. `workflow.py
new` emits a starter `slice-01-tbd.md` alongside `spec.md` in this
shape. Legacy specs that embed `## Slice` sections inside `spec.md`
(heading-first, frontmatter-after) remain supported by every helper —
no forced migration.

```yaml
---
status: DRAFT
dependencies: [007-02, adr-0004]
last_verified:
---
```

- `status` — current lifecycle state. `workflow.py transition` updates
  this when present.
- `dependencies` — flow-style list of slice fragments (e.g. `007-02`)
  and ADR IDs (e.g. `adr-0004`). `transition <slice> DONE` refuses if
  any listed dependency is not DONE / accepted.
- `last_verified` — date the slice was last reconciled. `transition`
  stamps this automatically on `→ RECONCILED`. Used by `stale`.

Legacy slices using prose `**STATUS:**` markers still work — the
transition helper writes to whichever shape is present. No retroactive
mass migration; new slices use the template, old slices stay as-is.

## Reconciliation checklist

When a slice transitions `REVIEWED → RECONCILED`, walk this checklist before the
status flip is allowed. Each item is a gate.

- [ ] **Deviation log** — write what changed during implementation and why,
      under a "Deviation log (after reconciliation)" subsection of the slice
      in `spec.md`. Original ACs preserved above; deviations append, not overwrite.
- [ ] **Architecture impact** — did module boundaries or public contracts change?
      If yes, update `docs/architecture.md` AND write an ADR.
- [ ] **Conventions impact** — did this slice introduce or change a rule worth
      recording? If yes, edit `docs/conventions.md` (requires
      `JIG_CONVENTIONS_APPROVED=1`).
- [ ] **Inbox triage** — sweep `docs/inbox.md` for items resolved by this slice;
      move them to the relevant memory file or strike them through.
- [ ] **AGENTS.md hygiene** — if this slice closes the spec (all non-deferred
      slices DONE), apply the compress-on-close-out rule per the slice
      template's `### Close-out (post-DONE)` section. AGENTS.md's "Active
      specs" section should only carry in-flight work; load-bearing
      per-slice invariants migrate to the status board Notes column (which
      `workflow.py status-board` preserves across regen).
- [ ] **Memory-sync** — run `/jig:memory-sync` (or invoke `memory.py` directly)
      to persist any new domain terms, dead-end learnings, or tool decisions
      that emerged during implementation. **This is where slice 002-04's
      integration lives**: the reconciliation phase explicitly surfaces
      memory-worthy items for persistence. The reviewer subagent reads from
      memory but never writes to it (see `agents/reviewer.md`).
- [ ] **Closed-spec drift** — if reconciliation surfaces a prior
      closed-spec inaccuracy (a `DONE` / `SUPERSEDED` spec/slice, or
      load-bearing skill/router/workflow prose that no longer matches
      reality), follow the policy in [ADR-0010](../../docs/decisions/adr-0010-amendment-scope-records-vs-live-prose.md)
      (supersedes ADR-0008). **Records** (closed specs/slices): append a
      dated `## Amendments` entry preserving the original. **Live prose**
      (SKILL.md / workflow.md / README): fix it **inline** — git history
      is the audit trail. New ADR (or superseding spec) only for
      decision-content changes.
- [ ] **Reconciliation review** — spawn a second reviewer subagent with a
      reconciliation-review prompt: are the doc changes faithful? Is the
      deviation log honest? Is scope appropriate (no scope creep in docs)?
- [ ] **Commit** — only after all gates pass.

### Auditing staleness (`workflow.py stale`)

Slice 015-03 added a read-only freshness audit:

```bash
python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" stale \
  [--project-dir DIR] [--days N]
```

Walks `docs/specs/*/spec.md` and `docs/decisions/adr-*.md`, extracts
`last_verified` + `dependencies` from frontmatter, and lists items
meeting the **conjunctive criterion**:

> An item is stale iff (a) `today - last_verified > --days` (default 90)
> AND (b) at least one file referenced by `dependencies` was modified
> since `last_verified`.

Pure age isn't enough — a verified-2-years-ago ADR for an unchanged
decision shouldn't fire. Pure recency-of-dep isn't either — a doc
verified yesterday with old deps is fine. Both conditions must hold.

The check uses `git log -1 --format=%cs <path>` for committed-state
authority and falls back to filesystem mtime when git is unavailable
or the file isn't tracked. Read-only: it lists, doesn't transition.
Bumping `last_verified` is a deliberate human/agent action — edit the
file, or re-run `transition <slice> RECONCILED` after re-verifying.

## Gotchas

- **Spike is the LAST SPIDR technique** to reach for, not the first. AI agents
  default to spiking too eagerly; try Rules / Data / Interface / Path first.
- **Every slice must be vertical** (crosses all layers, delivers end-to-end value).
  A slice that touches only the DB or only the parser is horizontal phasing — flag it.
- **The reviewer subagent must NOT be invoked with prior implementation context.**
  Write the deliverable to disk first; reviewer reads only the spec + deliverable
  + acceptance criteria.
- **The reviewer is read-only on `docs/memory/`** — memory-sync runs as a separate
  step during reconciliation, never as part of review.
- **`workflow.py transition` uses substring matching on slice names** — `001-01`
  matches `## Slice 001-01 — greenfield-scaffold`. If you have multiple slices
  whose names share a fragment, the helper refuses with an `ambiguous` error;
  use a more specific fragment.
- **`workflow.py status-board` preserves the preamble** before the `| Spec` table
  header. Custom intro text survives regen. Idempotent: no churn if the board is
  already current. **Notes column** also survives regen (the helper parses existing
  Notes and re-emits them). **Deferred slices** appear in a separate `## Deferred
  slices` table below the active table; only the active table preserves Notes.
- **`workflow.py status-board` refuses to overwrite on a mid-regen race** (slice
  028-03). The helper captures a SHA256 of `docs/specs/README.md` at the start of
  regen and re-checksums right before the write; if another writer mutated the file
  in the gap, it raises `StatusBoardRaceError` and exits **4** with the message
  `status board changed during regen — another writer may have run. Re-run
  workflow.py status-board to retry.`. Pass `--force` to bypass the guard and
  overwrite anyway (use only when you've manually reconciled the conflict).
  Identical-content rewrites do NOT trigger a refusal (checksum is content-based,
  not mtime-based).
- **`workflow.py` ignores `## Spike` headers.** Spikes are research artifacts, not
  lifecycle-managed work items. They don't have a STATUS marker the helper can
  transition. If you need a spike to be tracked in the status board, model it as a
  `## Slice Nnna — <name>` instead, or update the board's Notes column manually.
- **Avoid raw `|` characters in the Notes column** of `docs/specs/README.md`.
  Markdown tables use pipes as cell separators; raw pipes in a Note value would
  truncate the cell during regen's preservation step. Use HTML-entity `&#124;`
  or rephrase if you really need a pipe.
- **`DEFERRED → DONE` (or any non-DRAFT state) is refused.** Re-open the
  slice with `DEFERRED → DRAFT` first, then advance through the normal
  lifecycle. This prevents silently skipping review gates when a parked
  slice is picked back up.
- **`transition <slice> DONE` validates `dependencies:`.** If any
  listed dep slice isn't DONE or any listed ADR isn't Accepted, the
  helper refuses with a structured error naming each unsatisfied dep.
  Empty / missing `dependencies:` skips the check.
