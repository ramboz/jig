---
dependencies: []
last_verified: 2026-06-03
---

# ADR-0016: Parallel proportional bug-fix lifecycle

## Status

Proposed (2026-06-03)

## Context

Not all work in a jig project is spec-driven. A reported bug rarely
introduces a hard-to-reverse decision, rarely spans layers, and is
usually easy to revert — so forcing it through the full spec lifecycle
(DRAFT → … → DONE, vertical slices, three review passes) is ceremony
without payoff. jig already *says* this: `spec-workflow`'s own skill
description tells the reader not to use it for "quick one-off fixes that
don't need a spec, or for bug-shaped work where `debug-workflow` is the
better fit."

But the routing target it names — a `debug-workflow` skill — does not
exist in the jig pack. It exists only as a **personal, global** skill in
some users' `~/.claude/`, which is:

- **Judgment-only.** It prescribes a diagnose-first discipline (Frame →
  Gather Evidence → Hypothesize → Choose Fix Strategy → Implement →
  Prove → Close) but enforces nothing — no gate refuses a fix that
  skipped diagnosis.
- **Ephemeral.** Its "Task Spec" lives in the conversation, not on disk.
  There is no durable, numbered record, no regression-test proof, and no
  learning artifact that survives the session.

So jig has a **gap in the middle**: a heavyweight spec lifecycle on one
side, "just commit it" on the other, and nothing proportional in
between for the most common kind of work — fixing a reported bug with
rigor but without spec ceremony.

Three forces bound the design:

- **Proportionality is the point.** A bug workflow as heavy as SDD
  defeats its own purpose. The mechanism must *de-escalate* — actively
  refuse to create ceremony for a one-liner — not just offer a lighter
  template.
- **The discipline that matters for bugs is different from SDD's.** A
  spec's center of gravity is *specify intended behavior, split into
  slices*. A bug's is *diagnose the true root cause, prove it, prevent
  regression*. Same values (evidence, independent review, a durable
  record), different backbone.
- **Reuse over reinvention.** jig already has the load-bearing pieces:
  `tdd.py` (normalized red/green), `_common/review_evidence.py` (the
  ADR-0014 verdict gate), the reviewer-subagent + `independent-review`
  machinery, the 049 claim/release logic, and the ADR-0015 worktree-aware
  reservation. A bug workflow should *borrow* these, not fork them.

And one honesty constraint inherited wholesale from
[ADR-0011](./adr-0011-spec-gate-model.md): any in-process gate sits
inside the agent's trust boundary. A bug-fix gate enforces
**deliberateness and evidence consistency**, not human sign-off. Real
enforcement (who fixed it, did a human verify) stays out-of-band
(CODEOWNERS / CI / branch protection).

## Decision Options Considered

### Option A: Extend `spec-workflow` with a "bug mode"

Add a `kind: bug` to specs and special-case the lifecycle inside
`workflow.py`.

- **Pros:** One helper, one lifecycle vocabulary, no new surface.
- **Cons:** Forces a fundamentally different spine into the spec state
  machine. The states (`DIAGNOSING`, `ROOT_CAUSED`) and gates (red→green
  proof, diagnose-before-fix) have no SDD analog; the artifact shape
  (one file, not a slice tree) conflicts with the spec-per-directory
  convention; the proportionality/de-escalation behaviour has no home.
  Bolting it on makes both workflows harder to read.

### Option B: A judgment-only `jig:bug-fix` skill, no helper

Ship the diagnose-first discipline as skill prose (essentially adopt the
global skill into the pack), with no `.py` helper and no enforced gate.

- **Pros:** Fastest to ship; no new helper to maintain; lowest risk of
  over-building.
- **Cons:** Reproduces exactly the gap above — no teeth on the
  diagnose-before-fix rule, no durable numbered record, no machine-
  attested regression proof. The discipline degrades to a suggestion.
  jig's own honesty lineage (ADR-0011/0014, spec 040) argues against
  shipping a "gate" that gates nothing.

### Option C: A parallel, first-class, teeth-gated bug-fix lifecycle (recommended)

A new `jig:bug-fix` workflow — peer to `spec-workflow`, owning its own
orchestration — with a `bug.py` helper (sibling of `workflow.py`,
sharing `_common/`), a durable numbered record (`docs/bugs/NNN-slug.md`),
its own board, mechanized teeth gates, and designed-in proportionality.

- **Pros:** Fits the bug-shaped spine without distorting SDD. The
  diagnose-before-fix and red→green rules become real (mechanized)
  gates. The record is durable and reviewable. Reuses jig's existing
  machinery rather than forking it. Proportionality is a first-class
  feature (the helper de-escalates trivial work).
- **Cons:** A new helper + skill + reviewer-prompt variant to maintain;
  a `tdd.py` capability (targeted single-test runs) must be added first.
  Two lifecycles for contributors to learn — mitigated by a clear
  routing rule in `docs/workflow.md`.

### A note on deferral (the #5 decision)

`spec-workflow` is a first-class jig workflow: it does **not** defer its
orchestration to an external skill. The bug-fix workflow follows the
same rule — it owns its lifecycle. Only the **commodity review steps it
reuses** keep their established defer-to-richer behaviour: the craft pass
(`pr-review`) and the conditional security pass (`security-review`)
already defer to a richer installed skill if present. The orchestration
is jig's; the interchangeable steps stay swappable. (This is why the
skill is named `jig:bug-fix`, not `jig:debug-workflow` — a distinct
trigger that does not collide with a user's personal `debug-workflow`.)

## Recommended Decision

**Option C.** A parallel, proportional, teeth-gated bug-fix lifecycle.

### 1. Lifecycle and states

```
REPORTED → DIAGNOSING → ROOT_CAUSED → FIXING → REVIEWED → (VERIFIED) → DONE
                  └──────────────── escalate → ESCALATED (→ spec NNN)
```

- **REPORTED** — symptom captured.
- **DIAGNOSING** — gather evidence, form hypotheses.
- **ROOT_CAUSED** — a leading hypothesis is backed by evidence. This is
  the stopping point for *diagnose-only* mode.
- **FIXING** — implement the smallest change the diagnosis supports
  (TDD's red→green nested here).
- **REVIEWED** — review passes recorded and passing.
- **VERIFIED** — the *original reported repro* (not just the proxy test)
  re-run clean. Only for gnarly/security tier; trivial/standard collapse
  this into `REVIEWED → DONE`.
- **DONE** — landed, learning captured.
- **ESCALATED** — terminal off-ramp: diagnosis revealed the "bug" is a
  missing or under-specified behaviour; a spec is opened and the bug is
  parked (not fixed as a bug).

Back-edges (relax status, ungated): `REVIEWED → FIXING` (review needs
changes), and a failed green-check or a "symptom-not-cause" verdict
routes back to `DIAGNOSING` — carrying the failed attempt forward as new
evidence (see §9, evidence-accruing re-entry).

### 2. The teeth gates

`bug.py transition` enforces the following, mirroring `workflow.py
transition`'s gate architecture (ADR-0014). Each gate checks
**presence/shape**, never quality — quality is the reviewer's job.

| Transition | Gate (what `bug.py` enforces) | Mechanism |
|---|---|---|
| `→ ROOT_CAUSED` | ≥2 candidate hypotheses + a leading one + an evidence pointer | presence-check on record sections |
| `→ FIXING` | `fix_class` declared **and** the `regression_test` runs **red** | shells to `tdd.py` (targeted), expects exit 1; stamps `red_confirmed_at` |
| `→ REVIEWED` | the same `regression_test` now runs **green** + review prompt built | shells to `tdd.py`, expects exit 0; stamps `green_confirmed_at` |
| `→ VERIFIED` | original reported repro re-run clean (gnarly/security only) | attested in record |
| `→ DONE` | required review verdicts pass + learning recorded in `docs/memory/learnings.md` | reuses ADR-0014 evidence gate + presence-check |

**The two distinctive gates** are the diagnose gate (`→ ROOT_CAUSED`,
the ≥2-hypotheses anti-anchoring rule) and the **red→green teeth**: the
helper itself *witnesses* the regression test fail before the fix and
pass after, so "there is a regression test" is machine-attested, not a
writer's claim. A test that is already green without the fix does not
capture the bug, and the `→ FIXING` gate refuses it.

**Deliberateness, not human sign-off** (ADR-0011 lineage). Each gate is
bypassable as a deliberate act: `JIG_BUG_DIAGNOSE_GATE=0` (diagnose
gate) and `JIG_BUG_TEST_GATE=0` (red→green teeth) — two separate vars so
one can be relaxed without the other. A `tdd.py` env error (exit 2)
**fails closed** (gate not satisfied), distinct from red.

### 3. Tiers — proportionality enforced *downward*

`bug.py triage` classifies the report and, for the **trivial** tier,
**refuses to create a record** — it tells the caller to just write the
failing test with `tdd-loop`, fix, and commit. A gate that de-escalates
is the antidote to ceremony.

| Tier | Behaviour |
|---|---|
| **trivial** (typo, one-liner, mechanical) | No record. `tdd-loop` + commit. The workflow bows out. |
| **standard** | Single-file record + diagnose gate + red→green teeth + bug-review + craft. ≥2 hypotheses advisory. |
| **gnarly** (cross-layer, security, regression that didn't stick, design-gap) | Full rigor: ≥2 hypotheses **mandatory**, keeps `VERIFIED`, conditional security pass, `--push` reserves the number on `origin/main`. May escalate to a spec. |

### 4. Record, artifact location, and board

One file per bug: **`docs/bugs/NNN-slug.md`** (not a slice tree — bugs
are higher-volume, lower-ceremony than specs). Frontmatter carries the
machine-checked fields; the body is the human-readable diagnosis (≈ the
global skill's Task Spec, adapted):

```yaml
---
status: ROOT_CAUSED
severity: high            # triage input
tier: standard            # trivial | standard | gnarly → gate strictness
claimed_by: <branch>      # reuses the 049 claim/release machinery
regression_test: tests/test_foo.py::test_bar
red_confirmed_at:         # stamped by the → FIXING gate
green_confirmed_at:       # stamped by the → REVIEWED gate
fix_class:                # workaround | local_patch | structural_fix | guardrail | observability
security_surface: false   # gates the conditional security pass (like arch_review)
escalated_to:             # spec ref if the escalation seam fired
---
## Symptom / ## Repro / ## Evidence / ## Hypotheses / ## Root cause /
## Fix class / ## Fix / ## Already tried / ## Regression test /
## Proof / ## Learning
```

Bugs get their **own board**, `docs/bugs/README.md`, regenerated by
`bug.py status-board` (Notes column preserved across regen, mirroring the
spec board). Columns: ID / slug / severity / tier / status / reproduces?
/ regression test / claimed_by / escalated_to. A separate board keeps
"what spec work is in flight" uncluttered.

### 5. Reuse and module layout

`bug.py` is a **sibling of `workflow.py` that shares `_common/`**, not a
fork:

- `_common/review_evidence.py` — the verdict artifact + validator, reused
  for the bug-review pass (with bug-specific pass names).
- `_common/parsing.py` — `clear_frontmatter_field` (for `--release`),
  `FRONTMATTER_TRUTHY` (for `security_surface`).
- **049 claim/release** — `claimed_by` on the record, local by default;
  `--push`/`--pr` reserve `NNN` on `origin/main` via the **ADR-0015**
  ephemeral-detached-worktree-pushed-by-SHA path. Inherits 049/051's
  stance: best-effort serialization, **land-time collision backstop
  deferred** (not a new gap).
- `tdd.py` — the red→green teeth (requires the new targeted-test
  capability; see Scope / slice 01).
- `independent-review` + reviewer subagent, `pr-review`,
  `security-review`, `slice-land`, `memory-sync` — reused as steps.

### 6. Review passes

Two required passes + one conditional, validated by the ADR-0014
evidence gate at `→ REVIEWED`:

- **bug-review** (the "compliance" analog) — a bug-tailored reviewer
  prompt: does the fix address root cause or paper over the symptom? is
  there a regression test that fails without the fix? blast radius? scope
  creep? If `fix_class: workaround`, is it honestly labelled and
  justified?
- **craft** (`pr-review`) — unchanged; defers to a richer installed skill.
- **security** (`security-review`) — conditional on `security_surface:
  true` (mirrors how `arch_review: true` gates the arch pass); defers to
  a richer installed skill.

No arch pass — bugs carry no design. (Gnarly tier *may* add an optional
independent **diagnosis** review before the fix; deferred enhancement.)

### 7. Escalation seam

`bug.py escalate` is the first-class off-ramp for "this bug is actually a
missing/under-specified behaviour." It calls `workflow.py new`, stamps
`escalated_to: NNN` on the bug and "originated from bug NNN" on the new
spec, and parks the bug in terminal **ESCALATED** (not DONE — it was not
fixed as a bug).

### 8. Fix-class taxonomy

`fix_class` is declared at `→ FIXING`, one of: `workaround` /
`local_patch` / `structural_fix` / `guardrail` / `observability`
(borrowed from the global skill's "Choose Fix Strategy" phase). It makes
the bug-review concrete and enforces honesty: a workaround declared as a
workaround is fine; a workaround disguised as a structural fix is a
review blocker.

### 9. Content borrowed from diagnose-first debugging

The global `debug-workflow` skill's *phases* map onto these *states*, so
its prose content is imported into the `jig:bug-fix` skill rather than
reinvented:

- **The diagnostic question** — *"Is this a problem with the output, or
  the process that created the output? Fixing the output is a
  treadmill."* — lifted verbatim into DIAGNOSING.
- **Anti-anchoring** — ≥2 hypotheses with confirm/falsify framing → the
  diagnose-gate content (§2).
- **diagnose vs diagnose_and_fix modes** — `diagnose` mode stops at
  `ROOT_CAUSED`; `diagnose_and_fix` runs through `FIXING`.
- **Evidence-accruing re-entry** — a failed proof never gets silently
  patched; the failed attempt is appended to `## Already tried` (which
  flows into `learnings.md` at close) and downgrades a hypothesis.

## Consequences

**Becomes easier:**

- The routing question that motivated this ("a reported bug — do I need a
  spec?") has a clear answer: no — `jig:bug-fix`, proportional to tier.
- The diagnose-before-fix discipline is real (mechanized), not a
  suggestion. "There is a regression test" is machine-attested red→green,
  not a claim.
- Bug knowledge is durable and reviewable: a numbered record, a learning
  in `learnings.md`, a board — instead of ephemeral chat.

**Becomes harder:**

- Two lifecycles to learn. Mitigated by an explicit routing rule in
  `docs/workflow.md` and the helper's own de-escalation.
- A new helper + skill + reviewer-prompt variant to maintain, plus a
  `tdd.py` capability to add first.
- The gate cannot prove *who* fixed it or that a human verified
  (ADR-0011 trust-boundary limit). It enforces deliberateness + evidence
  consistency; human sign-off stays out-of-band.

## Scope

**In scope:** the bug-fix lifecycle, the `bug.py` helper (`new` /
`triage` / `transition` / `escalate` / `status-board` / `--release`), the
teeth gates, the record schema + board, the bug-review prompt, the
`jig:bug-fix` skill, and the `tdd.py` targeted-test prerequisite.

**Deferred enhancements (named, no slice reserved):**

- **Optional independent diagnosis review** (gnarly tier) before the fix.
  Trigger: observed anchoring on a wrong diagnosis in practice.
- **"This keeps happening" detector** — recurring-area signal that
  recommends a guardrail/invariant (from the global skill's "recommend
  stronger infrastructure"). Trigger: repeated bugs in one area.
- **Land-time collision backstop** for bug numbers — same deferral as
  051-03 for specs.

**Out of scope:** automatic subagent spawning; proving human
verification; CI consumption.

## Relationship to other decisions

- **[ADR-0011](./adr-0011-spec-gate-model.md) (spec-gate model).** The
  teeth gates are deliberateness gates inside the agent's trust boundary,
  bypassable by env var — not human-only enforcement.
- **[ADR-0014](./adr-0014-review-evidence-model.md) (review-evidence
  model).** The bug-review pass reuses the durable verdict artifact +
  `_common/review_evidence.py` validator and the transition-gate pattern.
- **[ADR-0015](./adr-0015-worktree-aware-reservation.md) (worktree-aware
  reservation) / spec 049 (slice-claim).** Bug numbering + `claimed_by`
  reuse the local-by-default, `--push`-reserves-on-origin/main machinery,
  including the deferred land-time backstop.
- **Spec 040 / honesty lineage.** Same theme: a gate that claims to gate
  must actually gate. The red→green teeth are the honesty move here.

## Open questions

- **Should `tier` be re-evaluated mid-flight** (e.g., a standard bug that
  turns out gnarly during diagnosis)? Lean: allow `bug.py retriage`,
  re-running the relevant gate strictness. Revisit if it adds noise.
- **Where does a security-surfaced bug's evidence overlap the security
  floor** (spec 052)? Lean: the conditional security pass is sufficient;
  no new plumbing. Revisit if the floor's scanners want a hook here.
