---
dependencies: [docs/decisions/adr-0016-bug-fix-lifecycle.md]
last_verified: 2026-06-05
---

# ADR-0019: Parallel proportional refactor / migration workflow

## Status

Proposed (2026-06-05)

## Context

jig is growing a small family of work-shaped lifecycles. SDD
(`spec-workflow`) handles **adding new behaviour**: specify intent,
split into vertical slices, three review passes.
[ADR-0016](./adr-0016-bug-fix-lifecycle.md) adds a proportional bug-fix
lifecycle for **restoring correct behaviour**: diagnose the true root
cause, prove it, prevent regression. Both share jig's values — evidence,
independent review, a durable record — over a different backbone.

That leaves the third member of the behaviour-change taxonomy with no
home:

| Work shape | Backbone | Workflow |
|---|---|---|
| Add new behaviour | specify intent → slices | `spec-workflow` |
| Restore correct behaviour | root-cause → prove → prevent regression | `jig:bug-fix` (ADR-0016) |
| **Change structure, preserve behaviour** | **capture a baseline → restructure → prove equivalence** | **— (this ADR)** |

Refactors and migrations fall into the third row, and today they land in
one of two bad places:

- **Over-ceremonied through SDD.** A migration is not *new* behaviour, so
  the slice/AC/DoD machinery fits awkwardly — there is nothing to
  "specify," and the thing that actually matters (proof that behaviour
  did *not* change) has no home in the spec lifecycle.
- **Under-disciplined as "just commit it."** A structural change shipped
  on a green CI run with no captured *before*-baseline has no attestation
  that behaviour was preserved — the most common way a refactor silently
  ships a regression.

[Spec 060 / ADR-0017](./adr-0017-scaffolded-code-health.md) (`code-health`)
*detects* debt (does the linter pass? duplication? complexity?) but it
does not *discipline paying it down*. Detection and the change-discipline
are complementary, not the same tool.

Four forces bound the design:

- **Proportionality is the point** (inherited from ADR-0016). A rename or
  extract-variable must not acquire ceremony. The mechanism must
  de-escalate trivial work, not just offer a lighter template.
- **The discipline that matters is behaviour-preservation.** A refactor's
  centre of gravity is *capture what the code does now, restructure,
  prove it still does exactly that*. The distinctive gate is the inverse
  of bug-fix's red→green: you must witness the equivalence baseline
  **green before** touching code, and prove it **green/at-baseline after**.
- **The oracle of "preserved" is not always a deterministic test.** This
  is the sharp lesson from the [CWV migration](#worked-example-the-cwv-migration)
  (mysticat blackboard, profile `migration/profiles/cwv.md`): when the
  refactored unit is non-deterministic / LLM-driven, "equivalence" cannot
  be golden-string equality — it is an **eval baseline** ("score ≥ legacy
  on a scored dataset, within a variance bound"), exactly the
  Eval-Driven-Development bar that migration plan already mandates. The
  workflow must treat the equivalence **oracle as pluggable**, not assume
  a deterministic test.
- **Reuse over reinvention** (inherited from ADR-0016). jig already has
  `tdd.py` (normalized red/green), `_common/review_evidence.py` (the
  ADR-0014 verdict gate), the reviewer-subagent + `independent-review`
  machinery, the 049 claim/release logic, and the ADR-0015 worktree-aware
  reservation. A refactor workflow borrows these, not forks them.

And the same honesty constraint from
[ADR-0011](./adr-0011-spec-gate-model.md): an in-process gate sits inside
the agent's trust boundary. A refactor gate enforces **deliberateness and
evidence consistency**, not "this refactor is provably safe." For the
deterministic oracle jig can *machine-witness* green-before/green-after;
for the eval oracle jig can only attest that a baseline exists and a
comparison verdict was recorded (it does not run evals — see §5). Real
enforcement stays out-of-band (CI / branch protection / a human reading
the diff).

## Decision Options Considered

### Option A: Extend `jig:bug-fix` with a "refactor mode"

Add a `kind: refactor` to bug records and special-case the lifecycle in
`bug.py`.

- **Pros:** One sibling helper, shared record machinery.
- **Cons:** Wrong spine. A bug's backbone is *root-cause → prove →
  prevent regression*; a refactor's is *capture baseline → restructure →
  prove equivalence*. The distinctive gates are **inverted** (bug:
  red-then-green; refactor: green-then-still-green), `fix_class` /
  `regression_test` have no refactor analog, and the eval-oracle has no
  home in the bug schema. Bolting it on makes both harder to read — the
  same reasoning ADR-0016 used to reject "bug mode" inside `spec-workflow`.

### Option B: A judgment-only `jig:refactor` skill, no helper

Ship "capture a characterization baseline, keep it green" as skill prose,
no `.py` helper, no enforced gate.

- **Pros:** Fastest to ship; nothing new to maintain.
- **Cons:** Reproduces the gap. Nothing attests the baseline was captured
  *before* the change, nothing records the equivalence verdict, the
  pluggable-oracle decision degrades to a suggestion. jig's honesty
  lineage (ADR-0011/0014, spec 040) argues against a "gate" that gates
  nothing — and behaviour-preservation is precisely the claim most worth
  attesting.

### Option C: A refactor template inside `spec-workflow`

Treat a refactor as a spec with a special template.

- **Pros:** No new helper or lifecycle vocabulary.
- **Cons:** A refactor is not sliceable *new behaviour*; AC/DoD describe
  intended behaviour the refactor by definition does **not** change. The
  equivalence oracle (and especially the eval baseline) has no place in
  the spec state machine. Distorts SDD for a shape it was not built for.

### Option D: A parallel, first-class, teeth-gated refactor/migration lifecycle (recommended)

A new `jig:refactor` workflow — peer to `spec-workflow` and `jig:bug-fix`,
owning its orchestration — with a `refactor.py` helper (sibling of
`workflow.py` / `bug.py`, sharing `_common/`), a durable numbered record
(`docs/refactors/NNN-slug.md`), its own board, a **pluggable equivalence
oracle**, mechanized teeth gates, designed-in proportionality, and an
explicit **carve-out seam** that hands genuinely-new behaviour to
`spec-workflow`.

- **Pros:** Fits the preserve-behaviour spine without distorting SDD or
  bug-fix. The baseline-before-refactor and equivalence rules become real
  gates. Handles deterministic *and* non-deterministic units via one
  pluggable oracle. Reuses jig's machinery. Proportionality is
  first-class (the helper de-escalates trivial work). The refactor↔feature
  boundary the CWV analysis surfaced gets a first-class seam.
- **Cons:** A third lifecycle to learn (mitigated by an explicit routing
  rule in `docs/workflow.md` + the helper's de-escalation), a new
  helper + skill + reviewer-prompt variant to maintain, and an honest
  limit on the eval oracle (jig attests, it does not run evals — §5).

## Recommended Decision

**Option D.** A parallel, proportional, teeth-gated refactor/migration
lifecycle with a pluggable equivalence oracle and a carve-out seam to SDD.

### 1. Lifecycle and states

```
SCOPED → BASELINED → REFACTORING → REVIEWED → (EQUIVALENCE_CONFIRMED) → DONE
                └──────────────── carve-out → CARVED_OUT (→ spec NNN)
```

- **SCOPED** — the refactor boundary (which modules) and the
  *preservation invariant* (the externally-observable behaviour that must
  not change) are named.
- **BASELINED** — the equivalence **oracle** is declared and captured
  **green on the current, unmodified code**. This is the distinctive gate
  — the inverse of bug-fix's red→green. No structural edit may precede it.
- **REFACTORING** — restructure; the oracle stays green/at-baseline
  throughout.
- **REVIEWED** — review passes recorded and passing.
- **EQUIVALENCE_CONFIRMED** — the full oracle re-run clean *after* the
  change: deterministic oracle green, or eval oracle **score ≥ recorded
  baseline within the stated variance bound**. The crux of the workflow,
  not a gnarly-only extra (contrast bug-fix's optional `VERIFIED`).
- **DONE** — landed; learning + a behaviour-delta log captured.
- **CARVED_OUT** — terminal seam: part of the work is *not*
  behaviour-preserving (genuinely new behaviour, e.g. a new execution
  model). A spec is opened for that remainder; the refactor proper stays
  honest about what it preserved.

Back-edges (relax status, ungated): `REVIEWED → REFACTORING` (review
needs changes); a failed post-equivalence check routes back to
`REFACTORING` carrying the divergence forward as evidence.

### 2. The teeth gates

`refactor.py transition` enforces the following, mirroring
`workflow.py` / `bug.py transition` (ADR-0014). Each gate checks
**presence/shape and the oracle result**, never quality — quality is the
reviewer's job.

| Transition | Gate (what `refactor.py` enforces) | Mechanism |
|---|---|---|
| `→ SCOPED` | refactor boundary + preservation invariant declared | presence-check on record sections |
| `→ BASELINED` | `equivalence_oracle` declared **and** the baseline runs **green on unmodified code** | **deterministic:** shells to `tdd.py`, expects exit 0, stamps `baseline_confirmed_at`. **eval:** a baseline artifact (dataset + recorded score) is present and attested green |
| `→ REFACTORING` | code touched only after BASELINED (ordering enforced) | timestamp ordering check |
| `→ REVIEWED` | oracle still green/at-baseline + review prompt built | `tdd.py` exit 0, or eval score ≥ baseline |
| `→ EQUIVALENCE_CONFIRMED` | full oracle green / eval ≥ baseline within variance bound | `tdd.py` (machine-witnessed) or recorded eval-comparison verdict |
| `→ DONE` | required review verdicts pass + learning recorded + behaviour-delta log present | reuses ADR-0014 evidence gate + presence-check |

**The two distinctive gates** are the **baseline-before-refactor** gate
(`→ BASELINED`: capture-green-*first*, the anti-"I'll add tests after"
rule) and **`→ EQUIVALENCE_CONFIRMED`** (prove behaviour unchanged). A
deterministic baseline that is captured *after* edits already began does
not prove preservation, and the ordering check refuses it.

**Deliberateness, not safety proof** (ADR-0011 lineage). Each gate is
bypassable as a deliberate act: `JIG_REFACTOR_BASELINE_GATE=0` and
`JIG_REFACTOR_EQUIVALENCE_GATE=0` (two vars, independently relaxable). A
`tdd.py` env error (exit 2) **fails closed**. A missing eval baseline
**fails closed**.

### 3. The pluggable equivalence oracle — the distinctive lever

`equivalence_oracle` is declared at `→ BASELINED`, one of:

- **`deterministic`** — characterization / golden / contract tests run
  via `tdd.py`. Proof is *equality*: green before, green after. jig
  **machine-witnesses** both runs (real teeth, like bug-fix's red→green).
- **`eval`** — for non-deterministic / LLM-driven units. The baseline is
  a *recorded score* on a golden dataset (the EDD bar); proof is *score ≥
  baseline within a stated variance bound*, **not** equality. jig
  **cannot run the eval** (no eval harness in the pack), so the gate
  enforces **presence + a recorded comparison verdict** (baseline artifact
  + an attested "≥ baseline" result), the same trust-boundary posture as
  ADR-0011/0014. The actual eval run is delegated to the project's EDD
  tooling.

The gate dispatches on the declared oracle. A refactor may carry **both**
(a deterministic sub-oracle for the stable wire contract *and* an eval
oracle for the subjective output) — see the worked example.

### 4. Tiers — proportionality enforced *downward*

`refactor.py triage` classifies the change and, for the **trivial** tier,
**refuses to create a record** — it tells the caller to lean on the
existing test suite and just commit. De-escalation is the antidote to
ceremony (identical stance to ADR-0016 §3).

| Tier | Behaviour |
|---|---|
| **trivial** (rename, extract-variable, mechanical, IDE-safe) | No record. Existing suite + commit. The workflow bows out. |
| **standard** (reshape a module, dedupe, restructure within a layer) | Single-file record + baseline gate (deterministic) + equivalence gate + refactor-review + craft. |
| **gnarly** (cross-module, **execution-model change**, **non-deterministic oracle**, large migration) | Full rigor: eval oracle allowed, **behaviour-delta log mandatory**, conditional security + **conditional arch** pass, `--push` reserves the number on `origin/main`, **carve-out seam likely**. |

### 5. Record, artifact location, and board

One file per refactor: **`docs/refactors/NNN-slug.md`** (a sibling tree to
`docs/bugs/`, not a slice tree). Frontmatter carries the machine-checked
fields; the body is the human-readable plan + proof:

```yaml
---
status: BASELINED
tier: gnarly                 # trivial | standard | gnarly → gate strictness
claimed_by: <branch>         # reuses the 049 claim/release machinery
equivalence_oracle: eval     # deterministic | eval (may list both)
baseline_ref:                # test path(s), or dataset + dashboard link
baseline_confirmed_at:       # stamped by the → BASELINED gate
equivalence_confirmed_at:    # stamped by the → EQUIVALENCE_CONFIRMED gate
behaviour_delta: logged      # none | logged (gnarly: must be present)
carved_out_to:               # spec ref if the carve-out seam fired
security_surface: false      # gates the conditional security pass
arch_surface: false          # gates the conditional arch pass (NEW vs bug-fix)
---
## Scope / boundary        ## Preservation invariant   ## Baseline (oracle)
## Plan                    ## Behaviour delta          ## Proof
## Learning
```

Refactors get their **own board**, `docs/refactors/README.md`,
regenerated by `refactor.py status-board` (Notes column preserved across
regen, mirroring the spec and bug boards). Columns: ID / slug / tier /
oracle / status / baseline? / equivalence? / behaviour-delta / claimed_by
/ carved_out_to.

### 6. Reuse and module layout

`refactor.py` is a **sibling of `workflow.py` / `bug.py` that shares
`_common/`**, not a fork:

- `_common/review_evidence.py` — verdict artifact + validator, reused for
  the refactor-review pass (refactor-specific pass names).
- `_common/parsing.py` — `clear_frontmatter_field` (`--release`),
  `FRONTMATTER_TRUTHY` (`security_surface` / `arch_surface`).
- **049 claim/release** — `claimed_by`, local by default; `--push`/`--pr`
  reserve `NNN` on `origin/main` via the **ADR-0015** ephemeral-detached-
  worktree-pushed-by-SHA path. Inherits the deferred land-time backstop.
- `tdd.py` — the deterministic oracle's green-before/green-after teeth
  (reuses the targeted-test capability ADR-0016 adds; no new prerequisite).
- `independent-review` + reviewer subagent, `pr-review`,
  `security-review`, `arch-review`, `slice-land`, `memory-sync` — reused
  as steps.

### 7. Review passes

Two required + **two** conditional, validated by the ADR-0014 evidence
gate at `→ REVIEWED`:

- **refactor-review** (the "compliance" analog) — a refactor-tailored
  reviewer prompt: does the change preserve the declared invariant? Is the
  equivalence oracle *adequate* — does the baseline actually cover the
  touched surface, or is it green by omission? Is any behaviour delta
  honestly logged and justified? Did new behaviour sneak in that should be
  a carve-out spec (scope creep)?
- **craft** (`pr-review`) — unchanged; defers to a richer installed skill.
- **security** (`security-review`) — conditional on `security_surface: true`.
- **arch** (`arch-review`) — conditional on `arch_surface: true`. **This
  is the key divergence from ADR-0016**: bugs carry no design, so bug-fix
  has no arch pass; a refactor *can* carry design (an execution-model or
  module-boundary change), so the arch pass returns — conditionally,
  mirroring how `arch_review: true` gates it in SDD.

### 8. The carve-out seam (refactor ↔ feature)

`refactor.py carve-out` is the first-class answer to the boundary the CWV
analysis surfaced: an execution-model migration almost always carries a
*new-behaviour remainder* (e.g. cascade-triggering, sandboxed execution)
that is **not** behaviour-preserving and therefore does not belong in a
refactor. `carve-out` calls `workflow.py new`, stamps `carved_out_to: NNN`
on the refactor and "carved out from refactor NNN" on the new spec, and —
if the *entire* item turns out to be new behaviour — parks the refactor in
terminal **CARVED_OUT**. The refactor stays honest about exactly what it
preserved; the new behaviour gets SDD's slice/AC machinery where it
belongs.

### 9. Worked example: the CWV migration

The mysticat blackboard CWV migration (profile
`migration/profiles/cwv.md`) is the motivating real case and exercises
every distinctive feature:

- **Tier: gnarly** — cross-module, execution-model change (task-based
  flow → DAG-driven producers), non-deterministic output, large migration.
- **`equivalence_oracle: eval` (+ a deterministic sub-oracle).** The
  guidance is LLM-generated, so preservation is *not* string-equality —
  the baseline is the legacy flow's score on a 30–50-case golden dataset,
  and the proof is the producer scoring **≥ that baseline** (the migration
  plan's EDD Phase 2). The stable `CWVIssue[]` wire contract gets a
  *deterministic* sub-oracle (shape / `type` enum / `status` values /
  `cwvValue` ranges) as a floor.
- **`behaviour_delta: logged`** — any detection rules dropped or merged
  versus cwv-agent v2 are recorded with rationale (the plan's "do not
  silently 1:1 port" rule).
- **`arch_surface: true`** — the task→producer execution-model change is a
  design decision, so the conditional arch pass fires.
- **`carved_out_to: <spec>`** — the sandboxed-execution + cascade-triggering
  behaviour (platform dependency SITES-40591) is genuinely *new*, not
  preserved; it carves out to a spec rather than masquerading as part of
  the refactor.

Without the pluggable oracle this migration would have no honest
equivalence story (golden-string equality is impossible for LLM output);
without the carve-out seam its new-behaviour remainder would either
distort the refactor or get lost. Both features earn their place on this
one case.

## Consequences

**Becomes easier:**

- The routing question ("I'm restructuring / migrating, not adding
  behaviour — spec or no?") has a clear answer: `jig:refactor`,
  proportional to tier.
- "I preserved behaviour" is *attested*, not claimed — green-before/
  green-after (deterministic) or score-≥-baseline (eval) — and the
  baseline-before-edit ordering closes the most common refactor footgun.
- Non-deterministic / LLM-driven units finally have an equivalence story
  (the eval oracle), instead of being un-refactorable under jig's rigor.
- The new-behaviour remainder of a migration has a clean home via the
  carve-out seam, keeping the refactor honest.

**Becomes harder:**

- A third lifecycle to learn. Mitigated by an explicit routing rule in
  `docs/workflow.md`, the helper's de-escalation, and the deliberate
  symmetry with ADR-0016 (same architecture, different backbone).
- A new helper + skill + reviewer-prompt variant to maintain.
- The eval oracle's honest limit: jig attests a baseline exists and a
  comparison verdict was recorded — it does **not** run evals or prove the
  score is real (ADR-0011 trust boundary). The deterministic oracle is the
  only machine-witnessed one.

## Scope

**In scope:** the refactor lifecycle, the `refactor.py` helper (`new` /
`triage` / `transition` / `carve-out` / `status-board` / `--release`), the
baseline + equivalence gates with the pluggable oracle, the record schema
+ board, the refactor-review prompt, the conditional arch/security reuse,
and the `jig:refactor` skill. Reuses `tdd.py`'s targeted-test capability
(no new prerequisite beyond what ADR-0016 adds).

**Deferred enhancements (named, no slice reserved):**

- **Eval-harness integration** — jig running evals itself / a defined
  interface to common EDD tools. Trigger: ≥2 eval-oracle refactors where
  the attest-only posture proves too loose.
- **Characterization-test generation** — scaffolding a baseline suite for
  code that has none. Trigger: repeated "no baseline exists yet" friction.
- **Oracle-adequacy check** (e.g. mutation testing) — proving the
  deterministic baseline actually covers the touched surface, not just
  that it is green. Trigger: a refactor ships a regression past a green
  baseline.
- **Land-time collision backstop** for refactor numbers — same deferral as
  051-03 for specs / ADR-0016 for bugs.

**Out of scope:** running evals; proving a refactor is semantically safe
beyond the declared oracle; CI consumption; automatic detection of which
tier a change is.

## Relationship to other decisions

- **[ADR-0016](./adr-0016-bug-fix-lifecycle.md) (bug-fix lifecycle).** The
  direct sibling — same parallel-proportional-teeth-gated *architecture*,
  a different backbone (preserve-behaviour vs root-cause). The gates are
  deliberately *inverted* (green-then-still-green vs red-then-green), and
  refactor restores the conditional arch pass that bug-fix drops.
- **[ADR-0011](./adr-0011-spec-gate-model.md) (spec-gate model).** Both
  gates are deliberateness gates inside the agent's trust boundary,
  env-bypassable — not safety proofs. The eval oracle's attest-only
  posture is the same honesty stance.
- **[ADR-0014](./adr-0014-review-evidence-model.md) (review-evidence
  model).** The refactor-review pass reuses the durable verdict artifact +
  `_common/review_evidence.py` validator and the transition-gate pattern.
- **[ADR-0015](./adr-0015-worktree-aware-reservation.md) / spec 049.**
  Refactor numbering + `claimed_by` reuse the local-by-default,
  `--push`-reserves-on-origin/main machinery, including the deferred
  land-time backstop.
- **[ADR-0017](./adr-0017-scaffolded-code-health.md) / spec 060
  (code-health).** Complementary: `code-health` *detects* debt;
  `jig:refactor` *disciplines paying it down*. A code-health finding is a
  natural trigger for a refactor record.
- **Spec 057 (thin-orchestrator).** `refactor.py` could emit a
  `session-plan`-style dispatch plan for its lifecycle, reusing the
  turn-count lever.

## Open questions

- **Authoring a baseline that doesn't exist yet.** If a project has no
  characterization tests for the touched surface, does `→ BASELINED`
  permit authoring them *as part of the gate*? Lean: yes, provided they
  run green on the **unmodified** code and are committed before the first
  structural edit (the ordering check still applies).
- **How thin is "attest-only" for the eval oracle?** Is a recorded
  baseline-score + comparison verdict enough, or should jig define a
  minimal interface to EDD tooling now? Lean: schema-only; integrate on
  signal (deferred above).
- **Trivial-tier bow-out vs a one-line log.** Mirror ADR-0016's answer
  (bow out entirely; no record). Revisit if "I wish I'd recorded that
  rename" friction appears.
- **Naming.** `jig:refactor` vs `jig:refactor-workflow` — lean
  `jig:refactor` (distinct trigger, parallels `jig:bug-fix`); confirm it
  does not collide with a common user skill.
