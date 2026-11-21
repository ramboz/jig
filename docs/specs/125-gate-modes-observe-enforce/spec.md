---
status: DRAFT
skill: spec-workflow
use_cases: [UC-4, UC-17, UC-20]
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 125: Gate modes — off, observe, enforce

> Reserved on 2026-11-21 via `workflow.py new --no-push` (local provisional —
> the number is not yet on `origin/main`).

## Overview

> Implements [ADR-0070](../../decisions/adr-0070-gate-modes-off-observe-enforce.md) (Proposed). Investigation record: [R-002](../../research/R-002-claude-code-verification-assessment.md). **Status: recorded, not yet built** — the ADR must be Accepted before 125-01 moves past DRAFT.

jig's refusing gates are on or off. Each is on by default and has one
deliberate escape, an env var such as `JIG_REVIEW_EVIDENCE_GATE=0`
([ADR-0011](../../decisions/adr-0011-spec-gate-model.md)), and spec 078 logs
when an escape is used. That leaves no way to run a check, see what it would
have refused, and decide whether it is right before it starts refusing. The
Claude Code team's commit gate has that middle step: "Observe mode will log
what would have been blocked, so that we can review any false positives and
ensure no one is impacted" (R-002, item 11).

This spec gives every gate that can refuse three modes through one shared
resolver, records what each gate blocked or would have blocked, reports it
for false-positive review, and lets a lifecycle transition pass one gate with
a written reason kept on the record. Defaults keep today's behaviour exactly.
It is a mechanism for existing and future gates, **not a new gate**
([ADR-0055](../../decisions/adr-0055-leanness-lens-folds-into-existing-passes.md)).

### Gate inventory (probed 2026-11-21)

| Gate (config key) | Kind | Where it refuses | Escape today | Logs the escape today |
|---|---|---|---|---|
| `review-evidence` | CLI | `workflow.py:919` transition, `adr.py:933` accept, `review_evidence.py:830` bug evidence | `JIG_REVIEW_EVIDENCE_GATE=0` | transition only (`workflow.py:926`) |
| `scaffold-precondition` | CLI | `workflow.py:4544` new, `adr.py:675` new | `JIG_SCAFFOLD_PRECONDITION=0` | no |
| `start-collision` | CLI | `workflow.py:5366`, `:5422` | `JIG_START_COLLISION_GATE=0` | yes |
| `cross-ref` | CLI | `workflow.py:5529-5536`, `:5604-5610`, `land.py:213` | `JIG_CROSSREF_GATE=0`, `--reopen` | yes |
| `bug-diagnose` | CLI | `bug.py:894` (refuses on `gnarly`, warns on `standard`) | `JIG_BUG_DIAGNOSE_GATE=0` | no |
| `bug-main-check` | CLI | `bug.py:917` | `JIG_BUG_MAIN_CHECK_GATE=0` | no |
| `bug-closure` | CLI | `bug.py:938`, `:982` | `JIG_BUG_CLOSURE_GATE=0` | no |
| `bug-test` | CLI | `bug.py:947`, `:989` | `JIG_BUG_TEST_GATE=0` | no |
| `conventions` | hook (PreToolUse, exit 2) | `jig-spec-gate.sh:61-81` | `JIG_CONVENTIONS_APPROVED=1` | yes (`:63-71`) |
| `secret-scan` | hook (PreToolUse, exit 2) | `jig-secret-scan.sh:192-203` | `JIG_SECRET_SCAN_APPROVED=1` | no (exits at `:31` before scanning) |

**Out of scope, nudges that never refuse:** entry gate (`JIG_ENTRY_GATE`,
`lib/entry_gate.py:321`), git freshness (`JIG_GIT_FRESHNESS`,
`lib/git_freshness.py:179`), boundary-change warn (`JIG_BOUNDARY_CHECK`,
`jig-boundary-change-warn.sh:113`), post-edit verify (`JIG_POST_EDIT_VERIFY`,
`jig-post-edit-verify.sh:53`), claim-check, context-check and the other
advisory hooks. They keep whatever opt-out they have; a nudge is already
"report, don't block". Host permission floors
(Claude `permissions.deny`, Copilot `jig-permissions-floor`) are not jig gates
and are untouched.

### Decisions

- **D1 — Reuse each gate's env var.** `=0` keeps meaning off; the same var
  also accepts `observe` and `enforce`. No second name per gate (the guard
  family already complains about one: `refinement-todo.md`, "unify the
  cross-ref guard family").
- **D2 — Observe is silent to the agent in hooks, one line in CLIs.** Hook
  gates record and exit 0 with no output ("ensure no one is impacted"). CLI
  gates print one `would block` note on stderr because the operator ran the
  command and the note helps them fix the gap voluntarily.
- **D3 — The override reason lives on the record, not in telemetry.** It
  mirrors `--release --reason` (`workflow.py:5638`). The 078 sink stays
  content-free.
- **D4 — Anti-stuck release is not sliced.** ADR-0070 §6 specifies it and
  explains why none of the ten gates should use it. It is built with its
  first consumer, which no current draft proposes (see Sibling specs).

### How this relates to deferred work

Quoted from `docs/refinement-todo.md`; none of these triggers is changed by
this spec unless stated.

- **"gate-bypass digest denominator"** — *"Resolution trigger: A maintainer
  wants to make a keep/retire decision on a gate from data …"*. The
  observe → enforce promotion **is** that decision, so 125-02 meets the
  trigger and adds the fire counts. Resolves the entry when 125-02 lands.
- **"unify the cross-ref guard family (now FOUR sites)"** — *"The obligation
  stands for the next guard-touching slice."* 125-03 touches all four sites,
  so it takes the preamble half (mode, event, override) and converges the
  `--reopen` asymmetry through the generic `--override`. The `endswith`
  branch-exclusion and ADR-evidence keying residuals are not mode work and
  stay on that entry.
- **"hard `PreToolUse` gate protecting `docs/decisions/**`"** — *"defer 3 for
  now until we see it explicitly hitting ADRs in a recurrent way."* Not built
  here. When the trigger fires, the gate can be born in `observe`, which also
  measures "recurrent" before anything refuses.
- **"CI consumption of `check-reviews`"** and **"Code-staleness hard-gating
  for review evidence"** (*"staleness is at most a `check-reviews` warning,
  not a gate"*) — not built here. Spec 124-02 builds the staleness warning
  (124 D3); making it block would register it on this resolver, in
  `observe` first, when the entry's trigger fires. CI consumption gets the
  same observe-first route.
- **"hard write-boundary enforcement for unattended (servo-driven) jig runs"**
  / [ADR-0060](../../decisions/adr-0060-unattended-execution-write-boundary.md)
  (Proposed, acceptance deferred) — an executor could set a gate's env var to
  `enforce` for its runs. Who owns the hard-deny stays ADR-0060's call.

**Sibling specs (R-002):** [123](../123-base-anchored-gate-definitions/spec.md)
owns reading gate definitions from the base ref; ADR-0068 §2 lets other gates
opt in "when they gain a project-editable definition", and `gates.<name>.mode`
is one. Until 123 builds the seam, 125 reads the working tree and records
`mode_source`.
[124](../124-commit-bound-verification-evidence/spec.md) records verification
stamps and reports staleness, and leaves blocking on either to this spec. This
spec answers with the mechanism, not a gate: registering 124's staleness
report or an "unverified landing" check as a gate is its own decision, born in
`observe` on this resolver, and would be the first user of the anti-stuck
valve.
[127](../127-diff-triggered-review-rules/spec.md) owns say-why checks inside
existing review passes; pulling in an extra pass or a person stays open
(ADR-0072 open question 1). [129](../129-verification-loop-hardening/spec.md)
owns the three-round cap, the escalate-to-a-person counterpart of the
anti-stuck valve, and 129-01 registers a new `tests-before-review` gate on
this resolver, born in `observe` mode. PR #230's rule `advisory` /
`enforced` states map onto `observe` / `enforce` (ADR-0070, open
question 2); its per-rule fire counts
and 125-02's per-gate counts both extend `gate-stats` and should share one
table shape.

## Assumptions

- **A1 — every refusing gate is in the inventory (grounded).** `grep -rn
  'JIG_[A-Z_]*' skills hooks` excluding tests, plus `docs/architecture.md:185`
  ("two can block tool calls with exit-code 2"). A gate added between now and
  125-03 must be added to the registry.
- **A2 — hooks can read `scaffold.json` fail-open (grounded).**
  `hooks/scripts/lib/protected_paths.py:74` already does, and
  `jig-spec-gate.sh:63-71` already imports from `skills/_common` inside a
  `try`.
- **A3 — jig's own repo has a `scaffold.json` (grounded).** It is a
  hand-authored sentinel at the repo root with no `gates` block, so jig keeps
  today's defaults unless someone adds one.
- **A4 — observe is host-uniform; enforce is not (partly grounded).** Observe
  exits 0 on every host. Enforce keeps each host's semantics: Claude blocks
  on exit 2; Copilot maps it to a deny through the adapter's `--enforce` mode
  (`skills/scaffold-init/copilot_hook_adapter.py:85-99`); Codex runs plugin
  hooks only after the user trusts them (`docs/architecture.md:241-243`).
  The Codex and Copilot runtime behaviour was not re-probed for this spec.
  CLI gates run in the Python helpers and are host-neutral.
- **A5 — the event sink is shared (grounded).** `gate_telemetry.py:38-40`
  writes `.claude/skill-usage.jsonl` and `gate_stats` reads the same path
  (`workflow.py:3227`) on every host, so they agree.

## Decomposition

SPIDR, three vertical slices:

- **125-01 (Interfaces + Rules):** the shared resolver and the review-evidence
  gate on it, end to end. A user can set that gate to `observe`, see the
  would-block note, and find the event in the log; refusals say why.
- **125-02 (Data):** recorded refusals (`gate_blocked`), the `gate-stats`
  report for false-positive review, and the written promotion rule.
- **125-03 (Paths):** the other nine gates on the resolver (CLI and hook
  paths), plus the reasoned `--override` on lifecycle transitions.

**Anti-horizontal-phasing.** 125-01 alone lets a project trial the most-used
gate in observe. 125-02 alone turns the log into a decision. 125-03 alone
extends both to every gate and gives overrides a reason.

**Not sliced:** the anti-stuck release (D4); per-gate `--override` on
`adr.py accept`, `land.py execute` and `workflow.py new` (ADR-0070, open
question 4).

## Slices

- [125-01 — gate-mode-resolver](slice-01-gate-mode-resolver.md) — shared `off | observe | enforce` resolver; review-evidence gate adopts it at all three sites; refusals say why.
- [125-02 — observe-report-and-promotion](slice-02-observe-report-and-promotion.md) — `gate_blocked` events, `gate-stats` fire counts and false-positive view, written promotion rule.
- [125-03 — mode-aware-gates-and-override](slice-03-mode-aware-gates-and-override.md) — remaining nine gates on the resolver; `--override <gate> --reason` on lifecycle transitions.
