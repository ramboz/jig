---
name: bug-fix
description: >
  Drive the teeth-gated lifecycle for reported defects: diagnose root cause,
  prove it, and prevent regression through REPORTED → DIAGNOSING → ROOT_CAUSED
  → FIXING → REVIEWED → DONE, with VERIFIED, ESCALATED, and RESOLVED_ON_MAIN
  paths where needed. Auto-fires on fix this bug, debug this, root-cause this,
  this regressed, this broke again, why is this failing, diagnose before
  fixing, or investigate this failure. Two modes: `diagnose` stops at
  ROOT_CAUSED; `diagnose_and_fix` runs through DONE. Uses a durable bug record,
  multiple hypotheses, a fresh-main recheck, and a witnessed red→green test.
  Do not use for spec-shaped work (use `spec-workflow`) or trivial one-liners
  (use `tdd-loop`).
user-invocable: true
---

> Spec 058 / [ADR-0016](../../docs/decisions/adr-0016-bug-fix-lifecycle.md)
> built this workflow. The deterministic state mutations and teeth gates live
> in `bug.py`; this SKILL.md drives the judgment layer. It is a **peer of
> `spec-workflow`** — a first-class jig workflow that owns its orchestration,
> not a deferring baseline.

## What this skill does

- Routes a reported bug to the **proportional** path: `triage` bows out of
  trivial work, reserving the record + gates for standard/gnarly tiers.
- Drives the bug lifecycle state transitions via `bug.py transition`, which
  enforces the teeth gates (diagnose-before-fix; red→green).
- Coordinates reviewer-subagent passes (bug-review, craft, conditional
  security) at `→ REVIEWED`, validated by the ADR-0014 evidence gate.
- Rechecks fresh main after `ROOT_CAUSED` and before `FIXING` so a stale
  parallel session does not re-fix a bug already solved on trunk.
- Provides the first-class escalation seam (`bug.py escalate`) for when a bug
  turns out to be a missing or under-specified behaviour.
- Imports the diagnose-first discipline (the diagnostic question,
  anti-anchoring, evidence-accruing re-entry) borrowed from
  diagnose-first debugging — see [ADR-0016 §9](../../docs/decisions/adr-0016-bug-fix-lifecycle.md).

## The diagnostic question (read first, every time)

> **Is this a problem with the output, or the process that created the
> output? Fixing the output is a treadmill.**

This is the heart of DIAGNOSING. A fix that patches the symptom — the bad
value, the wrong pixel, the failing assertion — without finding the process
that produced it does not close the bug; it relocates it. The bug-review pass
exists to catch exactly this (`fix_class: workaround` honestly labelled is
fine; a workaround disguised as a `structural_fix` is a blocker).

## Modes

- **`diagnose`** — stop at `ROOT_CAUSED`. Use when you (or the user) want the
  root cause established and reviewed before committing to a fix, or when the
  fix belongs to someone else. This is the default for "diagnose before
  fixing" / "root-cause this".
- **`diagnose_and_fix`** — run through `FIXING → REVIEWED → … → DONE`. Use
  when the fix is yours to land now.

The mode is a posture, not a flag — both run the same `bug.py transition`
gates; `diagnose` simply stops the forward walk at `ROOT_CAUSED`.

## Tiers — proportionality enforced *downward*

`bug.py triage` is the de-escalation gate. The antidote to ceremony is a
workflow that **refuses** to build ceremony for a one-liner.

| Tier | Behaviour |
|---|---|
| **trivial** (typo, one-liner, mechanical) | `triage --tier trivial` **deletes the record** and tells you to write the failing test with `tdd-loop`, fix, and commit. The workflow bows out. |
| **standard** | Single-file record + diagnose gate + red→green teeth + bug-review + craft. ≥2 hypotheses advisory. |
| **gnarly** (cross-layer, security, regression that didn't stick, design-gap) | Full rigor: ≥2 hypotheses **mandatory**, keeps the `VERIFIED` step, conditional security pass, `new --push` reserves the number on `origin/main`. May escalate to a spec. |

When in doubt about whether a bug is trivial, ask: would a regression test for
it be worth keeping? If yes, it is at least standard.

## Lifecycle

```
REPORTED → DIAGNOSING → ROOT_CAUSED → FIXING → REVIEWED → (VERIFIED) → DONE
                  │              └─ main already clean → RESOLVED_ON_MAIN
                  └──────────────── escalate → ESCALATED (→ spec NNN)
```

`(VERIFIED)` is gnarly/security-tier only — trivial/standard collapse
`REVIEWED → DONE`. Back-edges relax status and are ungated: `REVIEWED →
FIXING` (review needs changes), and a failed green-check or a
"symptom-not-cause" verdict routes back to `DIAGNOSING`, carrying the failed
attempt forward as new evidence (append it to `## Already tried` — it flows
into `learnings.md` at close).

`RESOLVED_ON_MAIN` is terminal: after the root cause is understood, the
session checks fresh `origin/main` before starting the fix. If the original
reported repro no longer fails there, another session already solved it; the
bug record is closed as resolved on main instead of generating a duplicate
patch.

### The teeth gates

`bug.py transition` enforces presence/shape, never quality (quality is the
reviewer's job). Each gate is bypassable as a deliberate act
(ADR-0011 lineage) — separate env vars so one gate can be relaxed without
silently relaxing the others.

| Transition | Gate | Bypass |
|---|---|---|
| `→ ROOT_CAUSED` | ≥2 candidate hypotheses + a leading one + an evidence pointer | `JIG_BUG_DIAGNOSE_GATE=0` |
| `ROOT_CAUSED → FIXING` | fresh-main recheck recorded as `main_repro_result: reproduces`; `fix_class` declared; `regression_test` runs **red** (shells to `tdd.py`, expects exit 1; stamps `red_confirmed_at`) | `JIG_BUG_MAIN_CHECK_GATE=0` (main recheck), `JIG_BUG_TEST_GATE=0` (test) |
| `→ REVIEWED` | the same `regression_test` now runs **green** (shells to `tdd.py`, expects exit 0; stamps `green_confirmed_at`) **and** the required review verdicts pass | `JIG_BUG_TEST_GATE=0` (test), `JIG_REVIEW_EVIDENCE_GATE=0` (verdicts) |
| `→ VERIFIED` | original reported repro re-run clean (gnarly/security only), attested in the record | — |
| `→ DONE` | required review verdicts pass + a learning recorded in `docs/memory/learnings.md` | `JIG_REVIEW_EVIDENCE_GATE=0` |

**The three distinctive gates** are the diagnose gate (the ≥2-hypotheses
anti-anchoring rule), the fresh-main recheck after root cause, and the
**red→green teeth**: the helper itself witnesses the test fail before the fix
and pass after, so "there is a regression test" is machine-attested, not
claimed. A bug already clean on fresh main becomes `RESOLVED_ON_MAIN`; a test
already green without the fix does not capture the bug — the `→ FIXING` gate
refuses it. A `tdd.py` env error (exit 2) **fails closed** (gate not
satisfied), distinct from red.

`fix_class` (declared at `→ FIXING`) is one of `workaround` / `local_patch` /
`structural_fix` / `guardrail` / `observability`.

## How to use

### 0. Confirm the project is scaffolded

Like `spec-workflow`, the bug record lives under `docs/bugs/`. If the project
is greenfield, route to `/jig:scaffold-init` first; if it has a spec layout
but no `scaffold.json`, route to `/jig:migrate`. Don't hand-roll `docs/bugs/`.

### 1. Create and triage the record

Before creating a new bug from a feedback/triage batch, scan
`docs/specs/README.md` for an overlapping active slice. If the work is already
owned by a spec, link that slice from the bug record or escalate/route instead
of creating a second owner.

```bash
# Reserve the number. Local by default; --push reserves on origin/main
# (gnarly tier), --pr via PR. Works from any branch/worktree (ADR-0015).
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" new <slug> [--push|--pr]

# Classify. trivial → record deleted, bows out to tdd-loop + commit.
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" triage <id> \
  --tier trivial|standard|gnarly [--severity <level>]
```

If `triage` bows out, **stop here** — write the failing test with
`/jig:tdd-loop`, fix, commit. Do not re-create the record.

Claim/release reuses the spec 049 machinery: `bug.py pickup <id>` claims;
`bug.py pickup <id> --release --reason "<why>"` force-releases a stale claim
(logged to the record's `## Release log`).

### 2. Diagnose (`→ DIAGNOSING → ROOT_CAUSED`)

Fill the record body — `## Symptom`, `## Repro`, `## Evidence`,
`## Hypotheses`, `## Root cause`. **Anti-anchoring: write ≥2 candidate
hypotheses** with confirm/falsify framing and mark the leading one (mandatory
for gnarly, advisory for standard, but always good practice — the first
explanation is rarely the right one). Write the hypotheses as a Markdown list
under `## Hypotheses` — any marker works (`-`, `*`, `+`, or `1.`) and the gate
counts **top-level** items only, so indented `- Confirm:` / `- Falsify:`
sub-bullets read as notes, not as extra hypotheses. Mark the leading one with
`[x]`, an inline `(leading)` tag, or a `Leading:` line. Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" transition <id> DIAGNOSING
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" transition <id> ROOT_CAUSED
```

In **`diagnose` mode, stop here** and present the root cause.

### 3. Fix (`→ FIXING → REVIEWED`), `diagnose_and_fix` mode

1. Declare `fix_class:` and name the `regression_test:` in the record.
2. Recheck fresh main before writing the fix. Fetch/inspect `origin/main`
   (usually from a detached worktree) and re-run the original reported repro.
   Then record the outcome:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" main-check <id> \
     --result reproduces \
     --ref origin/main@<sha> \
     --evidence "<original repro command + observed failure>"
   ```

   If the bug no longer reproduces on fresh main, record the terminal off-ramp
   and stop:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" main-check <id> \
     --result resolved-on-main \
     --ref origin/main@<sha> \
     --evidence "<original repro command + observed clean result>"
   ```

3. Write the regression test FIRST (it must fail without the fix — that is
   what the `→ FIXING` gate witnesses). Use `/jig:tdd-loop` for the red→green
   loop.
4. `transition <id> FIXING` — the gate requires the fresh-main recheck above,
   then shells to `tdd.py` and expects the test **red**; it stamps
   `red_confirmed_at`.
5. Implement the smallest change the diagnosis supports. Make the test green.
6. Run the review passes (below), record their verdicts, then
   `transition <id> REVIEWED` — the gate shells to `tdd.py` and expects the
   test **green** (stamps `green_confirmed_at`), then validates the verdicts.

### 4. Review passes (at `→ REVIEWED`)

Two required + one conditional, run as reviewer-subagent passes by the
host/orchestrator and validated by the ADR-0014 evidence gate. The reviewer
is read-only — `bug.py` validates the durable verdict artifacts they produce
(`docs/bugs/reviews/bug-NNN-<pass>.md`).

1. **bug-review** (always) — the compliance analogue, jig's own. Build the
   prompt with `review.py bug-review`:

   ```bash
   PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
     bug-review "docs/bugs/NNN-<slug>.md" "<deliverable-path>" ...)
   ```

   It asks: does the fix address root cause or paper over the symptom? is
   there a regression test that fails without the fix? blast radius? scope
   creep? If `fix_class: workaround`, is it honestly labelled and justified?

2. **craft** (`pr-review`, always) — **defers** to a richer installed
   `pr-review` skill on disk; falls back to jig's baseline `pr-review` skill.
   Run that skill's methodology against the bug's deliverables — it is
   diff-shaped, not spec-shaped, so there is **no** `review.py pr-review` call
   for a bug (that builder requires a spec + slice). Record the verdict with
   `prompt_source: pr-review skill craft pass` (as bugs 001–003 did).

3. **security** (`security-review`, conditional on `security_surface: true` in
   the record — mirrors how `arch_review: true` gates the arch pass) —
   **defers** to a richer installed `security-review` skill (Adobe's
   `adobe-security-*`, the user's own, or jig's baseline).

There is **no arch pass** — bugs carry no design.

Record each verdict with `review.py record-review --bug NNN --pass <name>
--verdict pass --reviewer <src>`. The `REVIEWED` gate requires `bug-review` +
`craft` (+ `security` when `security_surface: true`), each `verdict: pass`.

### 5. Verify (gnarly/security only) and close

```bash
# Gnarly/security: re-run the ORIGINAL reported repro (not just the proxy
# test), attest it in the record, then:
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" transition <id> VERIFIED

# Record the learning in docs/memory/learnings.md (the → DONE gate checks it),
# commit the work, then:
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" transition <id> DONE
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" status-board
```

Run `/jig:memory-sync` to consolidate any new learnings. Land the change with
`/jig:slice-land` if a formal landing checklist helps.

### Escalation (`→ ESCALATED`)

When diagnosis reveals the "bug" is a missing or under-specified
*behaviour* — not a defect in existing behaviour — escalate instead of
fixing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/bug-fix/bug.py" escalate <id> [--slug <spec-slug>]
```

This calls `workflow.py new`, stamps `escalated_to: NNN` on the bug and
"originated from bug NNN" on the new spec, and parks the bug in terminal
**ESCALATED** (not DONE — it was not fixed as a bug). Continue in
`spec-workflow`.

## De-escalation guidance

The single most important judgment in this workflow is **down-shifting**:

- A typo, a copy-paste error, a one-line off-by-one, a mechanical rename — let
  `triage --tier trivial` delete the record. Write the test, fix, commit.
  Creating a numbered record for a one-liner is the ceremony this workflow
  exists to refuse.
- A standard bug does **not** need the `VERIFIED` step or a security pass —
  `REVIEWED → DONE` is the path.
- Reach for gnarly only for genuinely cross-layer, security-surfaced,
  regression-that-didn't-stick, or design-gap bugs. If a "gnarly" bug is
  really a missing behaviour, **escalate** — don't grind it through the bug
  gates.

## Routing — bug-shaped vs spec-shaped

This is the bookend to `spec-workflow`'s "do not use for bug-shaped work"
clause. See [docs/workflow.md](../../docs/workflow.md) for the canonical
routing rule. In short: a reported defect → `jig:bug-fix` (proportional to
tier); a hard-to-reverse decision, cross-layer change, or ambiguous-scope new
behaviour → `spec-workflow`; a trivial one-liner → straight to `tdd-loop` +
commit.

## Gotchas

- **The `→ FIXING` gate refuses an already-green test.** A regression test
  that passes without the fix does not capture the bug. Write the test to fail
  first.
- **The `→ FIXING` gate also refuses a stale trunk check.** After
  `ROOT_CAUSED`, record `bug.py main-check … --result reproduces` against
  fresh `origin/main`; if the repro is clean there, mark
  `RESOLVED_ON_MAIN` and stop.
- **`tdd.py` env error fails the gate closed** (exit 2 ≠ red). Fix the
  environment; don't bypass blindly.
- **Bypass env vars are deliberateness escapes, not the default.**
  `JIG_BUG_DIAGNOSE_GATE=0` / `JIG_BUG_MAIN_CHECK_GATE=0` /
  `JIG_BUG_TEST_GATE=0` / `JIG_REVIEW_EVIDENCE_GATE=0` are for out-of-band
  flows — using them silently defeats the teeth.
- **Escalate, don't grind.** A bug whose fix introduces new routing/landing
  semantics or a missing behaviour is a spec — use the escalation seam.
- **`ESCALATED` and `RESOLVED_ON_MAIN` are terminal — closed, not
  unfinished.** A bug in a terminal non-`DONE` state was reclassified to a
  spec (`ESCALATED`) or already fixed on trunk (`RESOLVED_ON_MAIN`); it was
  never fixed as a bug, so its blank fix/test columns are *expected*. Don't
  flag it as stale or try to advance it to `DONE`. The status board
  segregates these rows under a `## Terminal` section (parity with the spec
  board's `## Deferred slices` / `## Abandoned slices`) so closure is legible.
- **`bug.py` never spawns subagents.** The host/orchestrator runs the reviewer
  passes; `bug.py` only validates the recorded verdict artifacts (ADR-0016
  Scope).
