---
dependencies: [docs/decisions/adr-0014-review-evidence-model.md, docs/decisions/adr-0016-bug-fix-lifecycle.md, docs/decisions/adr-0019-refactor-workflow.md]
last_verified: 2026-06-09
frame_review: true
---

# ADR-0022: Pluggable oracle boundary — bind the lifecycle oracle to servo

## Status

Proposed (2026-06-09)

**PARKED — deliberately not pursued to Accepted.** An independent frame-critique
([`docs/decisions/reviews/adr-0022-frame-critique.md`](./reviews/adr-0022-frame-critique.md),
verdict `needs-changes`) found this ADR is **ahead of demand**:

- **ADR-0019's own trigger is demand-side, and is unmet.** ADR-0019 gates
  "define an EDD/eval interface" on *"≥2 eval-oracle refactors where the
  attest-only posture proves too loose."* No such real case exists yet — the
  one worked example (the CWV migration) is external/hypothetical and uses the
  **eval** path. servo *existing* is a **supply** signal, not the **demand**
  signal ADR-0019 named.
- **The consumers don't exist.** `bug.py` / `refactor.py` (ADR-0016 / ADR-0019)
  are still Proposed and unbuilt — there is nothing to *activate* an
  `oracle: servo` binding in.
- **The eval/AC layer on servo's side is DRAFT** (servo spec 006), so the
  motivating non-deterministic path is unbacked regardless.

This ADR is therefore kept as **captured design intent**, not an active
decision. **Revisit when any of:** (a) a real eval-oracle refactor/bug strains
ADR-0019's attest-only posture (the demand trigger), (b) `bug.py` / `refactor.py`
are implemented (a consumer exists), or (c) servo spec 006 ships (the eval/AC
backing lands). Until then, ADR-0019's schema-only deferral stands. The body
below is the design as drafted; treat its value claims as *prospective*.

**Note (2026-06-12) — the spec-gate Open Question was resolved separately.** The
third Open Question below (*does `servo` belong in spec-workflow's gate?*) was
answered independently of Option D by [spec 071](../specs/071-design-review-pass/spec.md):
a generic, attest-only **`design_review`** review pass on the existing ADR-0014
rails — a reviewer attests an external eval's frozen verdict; jig never
machine-reads servo's exit code, never re-derives the score, and gains no servo
coupling. That is the *loosest* possible integration, and it is the live answer
to ADR-0019's OQ2 ("how thin is attest-only?"): **as thin as a review pass.**
**Option D itself (the tight exit-code binding for bug/refactor, §2–§5) remains
PARKED** on the demand trigger above — spec 071 deliberately did not build it.

**Note (2026-06-13) — servo rebased; the separable `slice-land` pull-hint is now
being built (spec 072).** servo's `ADR-0008` (*rebase agent-loop onto
/goal+/background+Routines*) was Accepted 2026-06-12, retiring the hand-rolled
loop — so the long-planned jig→servo `slice-land` pull-hint (the reciprocal
servo's README asserts as *"the entirety of the coupling"* but jig never built;
see Scope + Assumptions) now has a stable, current artifact shape to point at.
That *separable* dependency is being built under
[spec 072](../specs/072-servo-pull-hint/spec.md) as **advisory text only** (a
filesystem probe in `land.py prepare`; no servo invocation, no exit-code read) —
even looser than spec 071's `design_review` pass. Its re-engagement is sanctioned
by this ADR's own Status triggers (servo 006 DONE; a built consumer in
`/servo:design-eval`). **Option D's tight bug/refactor exit-code binding (§2–§5)
is untouched and stays PARKED** — its demand trigger (≥2 real eval refactors) and
consumers (`bug.py`/`refactor.py`) remain unmet; spec 072 builds the discovery
pull-hint, not the oracle binding.

## Context

jig now has a **family of three gated-evidence lifecycles**, all mirroring
ADR-0014's transition-gate architecture and reusing `_common/`:

| Work shape | Backbone | Workflow | Verification gate |
|---|---|---|---|
| Add behaviour | specify intent → slices | `spec-workflow` | review evidence (ADR-0014) |
| Restore behaviour | root-cause → prove → prevent regression | `jig:bug-fix` ([ADR-0016](./adr-0016-bug-fix-lifecycle.md)) | red→green teeth + optional `VERIFIED` (original repro) |
| Preserve behaviour | baseline → restructure → prove equivalence | `jig:refactor` ([ADR-0019](./adr-0019-refactor-workflow.md)) | `BASELINED` + `EQUIVALENCE_CONFIRMED` |

Each ends in a *verification* gate that asks "did the change do what it
claims?" The hardest of these is **non-deterministic verification**.
[ADR-0019 §3](./adr-0019-refactor-workflow.md) already split the
equivalence oracle into:

- **`deterministic`** — characterization/golden/contract tests via `tdd.py`;
  jig **machine-witnesses** green-before / green-after. Real teeth.
- **`eval`** — for LLM-driven / non-deterministic units; proof is *score ≥
  baseline within a variance bound*, not equality. **Attest-only**: ADR-0019
  states plainly that *"jig cannot run the eval (no eval harness in the
  pack)"* and delegates the run to *"the project's EDD tooling."*

ADR-0019 then left this open (OQ2): *"How thin is 'attest-only' for the eval
oracle? … should jig define a minimal interface to EDD tooling now? Lean:
schema-only; integrate on signal."* — where ADR-0019's *deferred-enhancements*
section names the signal precisely: **"≥2 eval-oracle refactors where the
attest-only posture proves too loose."** That is the demand trigger this ADR
is parked on (see Status). ADR-0016's optional `VERIFIED` gate ("original
reported repro re-run clean", attested) is the same shape.

**The *supply* side is now available** (the *demand* side is the separate,
unmet question above). [servo](https://github.com/ramboz/servo) — jig's
autonomous sibling plugin — now exists, and the oracle is its entire reason to
be. Verified from servo's README / architecture / agent specs / `gate.py`
source — being precise about **what is shipped vs DRAFT**:

- **Shipped (servo specs 001/002/003/007 DONE):** `oracle.sh` is a composite
  of `score_<name>` components (each scoring `[0.0, 1.0]`), weighted-averaged
  and gated against `THRESHOLD`, with a **stable normalized exit contract:
  `0` (composite ≥ THRESHOLD) / `1` (< THRESHOLD) / `2` (environment error)**.
  `/servo:quality-gate` (`gate.py`) runs it at runtime and emits
  `gate.py --json` → `schema_version` / `exit_code` / `status`
  (`pass` | `below_threshold` | `env_error`) / `composite` / `threshold` /
  `missing` (names of env-errored components). **This is a single composite
  score — there is no per-component score map.** servo's `judge` agent emits a
  machine-parseable `PASS / FAIL / INCONCLUSIVE + score`.
- **DRAFT (servo spec 006, all five slices):** `/servo:spec-oracle` — the
  piece that would compile a spec/slice's acceptance criteria into AC-mapped
  checks + an installable `oracle.sh` component. servo 006's own **Non-goals**
  disclaim "No universal semantic judge / No deep natural-language proof /
  Deterministic checks remain the source of truth." So the **eval/AC scoring
  layer is not yet shipped.**
- **servo's project-vs-core split:** the project owns `oracle.sh` content,
  weights, threshold, and *eval/AC policy*; servo owns the template, the
  normalized exit codes, and the orchestration. So a project's eval scorer
  (e.g. mystique's `evaluate-agent-offline`) is a **project-authored `score_`
  component that servo runs but does not write** — it is "the project's EDD
  tooling" ADR-0019 delegated to, hosted inside servo's composite.

So the binding *design* below is recordable now — but, per Status, it is
**parked** until the demand trigger / a consumer / servo 006 makes it timely.
It is a cross-plugin architectural boundary (it shapes the coupling of two
repos and is costly to undo), which is why it is captured as an ADR.

Three constraints bound the design:

- **Honesty (ADR-0011 / ADR-0014 lineage), now across a plugin boundary.**
  jig's gate can only *attest that a verdict was recorded*; the thing that
  *ran and scored* is servo's (and the eval `score_` is the project's). The
  boundary must not let jig claim it "verified" what servo actually did, and
  must not credit the binding with a *shipped* eval backing that is still
  servo-DRAFT.
- **No hard dependency — fixed on both sides.** servo's own coupling rule
  (servo README; servo ADR-0001 "reuse jig's test detector"; ADR-0003 "fresh
  subagent roster") is: sibling plugins, **filesystem-only hints**, no
  cross-plugin registration. The coupling that **exists today is
  one-directional**: servo reuses jig's `tdd.py detect` by probing
  `${CLAUDE_PLUGIN_ROOT}/jig/...`. servo's README *anticipates* a reciprocal —
  jig's `slice-land prepare` emitting soft pull-hints for servo artifacts —
  but **that pull-hint is not yet implemented in jig** (a grep of jig's
  `skills/` on 2026-06-09 finds no servo reference outside docs). It is a
  *planned* reciprocal, not an existing behavior. jig-without-servo (today's
  supervised default) and servo-without-jig must both keep working.
- **Don't grow jig into an eval runner.** ADR-0019's Out-of-scope is explicit:
  *"running evals."* This ADR must not walk that back. jig orchestrates and
  attests; servo (or the project's `oracle.sh`) runs.

## Decision Options Considered

### Option A: jig grows its own oracle / eval runner

Give jig a first-party eval/scoring engine so the `eval` oracle is
machine-witnessed like the deterministic one.

- **Pros:** One tool; jig's gate could prove the score, not just attest it.
- **Cons:** Directly contradicts ADR-0019 ("no eval harness in the pack" /
  Out-of-scope "running evals"). Duplicates servo's entire reason to exist and
  re-merges the supervised/unattended scope split servo was deliberately
  carved out to keep separate (servo product-vision, "Why servo exists").
  Bloats jig's always-loaded supervised surface with unattended-scoring
  machinery. Rejected.

### Option B: keep ADR-0019's abstract attest-only oracle; never name servo

Status quo — the dev hand-wires "the project's EDD tooling" each time.

- **Pros:** Zero coupling; nothing new to maintain.
- **Cons:** Leaves the dev re-soldering the same wire on every project, with
  **no normalized result to attest and no discovery** — the scar servo's
  shipped exit contract *could* remove. **Note (the parking rationale):**
  ADR-0019's "integrate on signal" trigger is *demonstrated demand* (≥2 real
  eval refactors straining attest-only), which is unmet — so on the demand
  axis, "keep deferring" (Option B's posture) is the honest status quo until a
  real case appears. This ADR records Option D's *design* for that moment
  without activating it.

### Option C: hard-wire jig → servo (import / require servo)

Make servo a dependency of jig's refactor/bug lifecycles.

- **Pros:** Tight, discoverable integration; no probing.
- **Cons:** Breaks jig's standalone install (its current default), violates
  servo's own filesystem-only-coupling rule, and chains two release cadences.
  A jig user who never wanted unattended ops is forced to carry servo.
  Rejected.

### Option D: a soft, filesystem-hinted oracle binding (the recorded design)

jig's pluggable oracle gains **`servo`** as a recognized binding alongside
`deterministic` / `eval`. jig discovers a servo oracle by probing the target's
`.servo/install.json` (+ `oracle.sh`) — the same shape servo uses to probe
jig's `tdd.py`. When present, jig shells to `/servo:quality-gate` / reads
`gate.py`'s exit code as the oracle result; the AC/eval-scoring path is wired
through `/servo:spec-oracle` **when servo 006 ships**. No hard dependency;
**soft-degrade** to ADR-0019 behaviour when servo is absent; jig still only
*attests*.

- **Pros:** Gives the **deterministic composite** verification gate a real,
  normalized backing, and gives the **eval** path a *defined home* for when
  servo 006 lands — without jig shipping an eval runner. The win over Option B
  is the **normalized + discoverable + attestable contract** (exit codes +
  `.servo/install.json` + soft-degrade), not eval authorship. Keeps the
  supervised/unattended split intact; both plugins stay independently
  installable.
- **Cons:** Two plugins to install for the full story. A misconfigured / empty
  servo oracle fails closed (exit 2) — safe but can surprise. jig still cannot
  prove the score is real. **The eval-scoring ergonomics are not shipped yet**
  (track servo 006). **And for a purely deterministic check, routing through
  servo is *weaker* than jig's existing `tdd.py` path** (attest-only vs
  machine-witnessed) — see Consequences. These cons are exactly why this ADR
  is parked rather than accepted.

## Recommended Decision

**Option D as the recorded design — parked, not accepted** (see Status). The
details below describe how the binding *would* work when the parking triggers
are met; nothing here is active.

### 1. The boundary, stated once

jig owns the **lifecycle, the gate, and the evidence record** (the *when* and
the attestation). servo owns **oracle execution and scoring** (the
*what-score*); for an eval component, the *project* owns the scorer servo
runs. The verdict jig records points at the oracle run; **jig never re-runs or
re-derives the score.** This is the ADR-0011 / ADR-0014 trust boundary,
restated across the plugin line.

### 2. The interface contract = servo's existing exit codes

The binding would ride servo's already-stable, already-shipped exit contract —
no new wire format:

| servo result | jig gate behaviour |
|---|---|
| `oracle.sh` / `gate.py` exit `0` (composite ≥ THRESHOLD) | oracle-pass → gate clears |
| exit `1` (< THRESHOLD) | oracle-fail → gate blocks |
| exit `2` (environment error) | **fail-closed** → gate *not* satisfied |

The exit-2 fail-closed rule is identical to how ADR-0016 / ADR-0019 already
treat a `tdd.py` exit 2. jig would consume what servo already emits, the same
way servo consumes jig's `tdd.py detect`. Optionally, jig may capture
`gate.py --json`'s `composite` / `threshold` / `status` into the record for the
reviewer (see Open questions) — but the **exit code is what gates**.

### 3. Oracle declaration gains a `servo` value

In the refactor record (`equivalence_oracle`) and the bug record (the
`VERIFIED` gate), the oracle may be declared **`servo`** — and may still list a
`deterministic` sub-oracle alongside it (ADR-0019's both-oracles case).
`servo` means: the equivalence/verification baseline is a servo `oracle.sh`
composite, which can itself contain an eval `score_<name>` component
(**project-authored — servo runs it, does not write it**; e.g. mystique's
`evaluate-agent-offline`). **The variance-band semantics ADR-0019 defined for
`eval` live inside servo's `THRESHOLD` + component weighting — jig does not
re-implement them.**

### 4. `/servo:spec-oracle` is the AC → evidence bridge (tracks servo 006)

Where the oracle needs a baseline compiled from acceptance criteria or a
refactor's preservation invariant, jig points at `/servo:spec-oracle` to
generate the installable oracle component, rather than jig growing an
AC-compiler. **`/servo:spec-oracle` is DRAFT (servo 006) — so this bridge
tracks 006; the §2/§3 exit-code binding does not depend on it** and would ship
independently. (This is also the natural future bridge for spec-workflow's own
ACs → runnable evidence — noted, not decided here.)

### 5. Discovery + soft-degrade

jig would probe for a servo oracle exactly as servo probes for jig's test
detector: presence of `.servo/install.json` (+ `oracle.sh`) at the target root.

- **Present** → the bug/refactor helper *offers* `servo` as an oracle value and
  emits a pull-hint. **(This jig→servo pull-hint is the *planned reciprocal*
  servo's README anticipates — it is not yet implemented in jig; building it is
  part of activating this ADR.)** Filesystem hints only, no registration, no
  import.
- **Absent** → no servo mention; the oracle falls back to ADR-0019's
  `deterministic` / `eval` (attest-only) and ADR-0016's attested `VERIFIED`,
  **unchanged**. jig-without-servo is fully intact.

### 6. Honesty stays explicit

jig's gate clearing on a servo exit-0 would mean *"a servo oracle run was
recorded as passing,"* not *"jig verified the behaviour."* For the eval path,
jig attests the servo verdict exists; servo's `oracle.sh` / `judge` is the
runner and the project's `score_` is the scorer; none of it proves a human
reviewed it (out-of-band, per ADR-0011). The deterministic `tdd.py` sub-oracle
remains the only path jig itself machine-witnesses — which is why (see
Consequences) the deterministic case should stay on `tdd.py`, not move to
servo.

## Consequences

**Becomes easier (prospective — gated on the parking triggers):**

- For a **composite of many signals** (tests + lint + coverage + project
  checks), a refactor/bug lifecycle could declare `oracle: servo` and attest a
  single normalized, discoverable composite result instead of hand-rolling
  one. The win over Option B is the *normalized + discoverable + attestable
  contract* (exit codes + `.servo/install.json` + soft-degrade) — **not** that
  servo authors the eval.
- For **non-deterministic / eval** units, ADR-0019's `eval` oracle and
  ADR-0016's `VERIFIED` gate would get a *defined home* (when servo 006 ships)
  rather than a shipped backing today: an eval `score_` component is
  project-authored (servo runs it, does not write it). So the
  un-refactorable-under-rigor gap ADR-0019 named gets a *delegation path*, not
  closure — and only once a real case + servo 006 exist.

**Becomes harder / honest limits (the reasons it is parked):**

- **For a purely deterministic check, `oracle: servo` is *weaker* than the
  status quo.** jig today shells to `tdd.py` and **machine-witnesses**
  green-before/green-after (real teeth); routing the same tests through servo's
  composite makes jig **attest-only**. So the deterministic path should stay on
  `tdd.py`; servo earns its place only for *composite* or (post-006) *eval*
  signals, not as a replacement for witnessed tests.
- **The eval-scoring ergonomics are not shipped** (track servo 006), and **no
  real demand case exists yet** (ADR-0019's trigger) — the two facts that make
  this ADR premature to accept.
- Two plugins to install for the full story; a misconfigured/empty servo oracle
  fails closed (exit 2); jig still cannot prove a score is real.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **servo's exit-code + JSON contract is stable and shipped.** Verified by
  reading servo's README ("Exit codes (servo contract)" — 0/1/2) and servo's
  `skills/quality-gate/gate.py` `_emit_summary`: `gate.py --json` carries
  `schema_version` / `exit_code` / `status` (`pass` | `below_threshold` |
  `env_error`) / `composite` / `threshold` / `missing` — a single composite
  score, **no per-component score map**. The README states the 0/1/2 codes are
  "stable across servo's runtime skills."
- **`.servo/install.json` is servo's durable per-project manifest.** Verified
  in servo `architecture.md` ("the analog of jig's `scaffold.json`").
- **`/servo:spec-oracle` is DRAFT (servo spec 006, all five slices), and servo
  006 disclaims a semantic judge.** Verified in servo's product-vision /
  README / `docs/specs/006-spec-oracle/` (incl. its Non-goals).
- **The jig→servo coupling is NOT yet implemented (corrected).** An earlier
  draft asserted jig's `slice-land prepare` "already emits servo pull-hints"
  and called it verified — **false**: a grep of jig's `skills/` on 2026-06-09
  finds no servo reference outside `docs/` (the only `land.py` "hint" is a
  git-rebase recovery message). The coupling that exists today is **one-way**:
  servo→jig (`tdd.py detect` reuse, servo ADR-0001). The jig→servo pull-hint is
  a *planned reciprocal* described by servo's README, and building it is part
  of activating this ADR.
- **The demand trigger (ADR-0019: ≥2 real eval refactors straining
  attest-only) is unmet.** No such case is recorded; this is the primary
  reason for the PARKED status.

## Kill criteria

- servo changes or abandons the 0/1/2 exit contract → §2 is invalid; revisit
  the interface.
- `/servo:spec-oracle` is cut from servo or lands with an incompatible shape →
  §4 (the AC bridge) and the eval-scoring ergonomics lose their backing; the
  exit-code binding (§2/§3) still stands.
- servo 006 ships but its eval/AC scoring proves too weak for real
  non-deterministic units (its own Non-goals bite) → the `eval`-via-servo value
  does not materialize; `oracle: servo` stays a *composite* gate and the eval
  oracle reverts to ADR-0019 attest-only.
- A real need emerges for jig to *prove* (not attest) an eval score in the
  supervised loop → reopen Option A's trade-off, which this ADR rejects on
  scope grounds.

## Scope

**In scope (as captured design):** recognizing `servo` as an oracle binding in
the bug/refactor records; the exit-code interface contract (§2); discovery via
`.servo/install.json`; soft-degrade; the `/servo:spec-oracle` pointer (gated on
servo 006); the honesty posture. When activated, implementation rides
ADR-0016 / ADR-0019's helpers (`bug.py` / `refactor.py` gain `oracle: servo`
dispatch) plus the not-yet-built jig→servo pull-hint.

**Deferred / parking dependencies (named, no slice reserved):**

- **The whole ADR is parked** on the demand trigger / a consumer / servo 006
  (see Status).
- **Build the jig→servo `slice-land` pull-hint** — the planned reciprocal
  servo's README asserts. **Now being built as
  [spec 072](../specs/072-servo-pull-hint/spec.md)** (072-01 present-case
  advisory pointing at the post-`ADR-0008` artifact shape, implementation-ready;
  072-02 missing-case suggestion, decision-gated on §5 — see Open Questions).
  Advisory text only — distinct from, and not a prerequisite of, §5's
  oracle-binding *discovery* (offering `servo` as an oracle value in
  bug/refactor records), which stays parked with the rest of Option D.
- **Extract a shared `_common/lifecycle.py` transition-gate engine** across
  `spec-workflow` / `bug.py` / `refactor.py` (ADR-0002 / ADR-0003
  rule-of-three) — governed by ADR-0023; triggered by the third concrete
  `transition` implementation, not yet reached.
- **spec-workflow ACs → `/servo:spec-oracle` evidence overlay** — tracks servo
  006.
- **A reciprocal servo-side ADR** — servo's call; noted for coordination.
- **Go-live / production-readiness checklist** — a milestone-level DoD over
  this boundary, not part of this ADR.

**Out of scope (unchanged from ADR-0019):** jig running evals; a hard
jig→servo dependency; proving a score is real or human-reviewed; CI
consumption.

## Relationship to other decisions

- **[ADR-0019](./adr-0019-refactor-workflow.md) (refactor workflow).** This ADR
  records the *design* that would resolve its OQ2 — but defers to ADR-0019's
  own demand trigger (≥2 real eval refactors), which is why it is parked.
- **[ADR-0016](./adr-0016-bug-fix-lifecycle.md) (bug-fix lifecycle).** Its
  attested `VERIFIED` gate would bind to servo by the same contract.
- **[ADR-0014](./adr-0014-review-evidence-model.md) / [ADR-0011](./adr-0011-spec-gate-model.md).**
  The attest-not-prove trust boundary, extended across the plugin line.
- **[ADR-0002](./adr-0002-contracts-stays-deferred.md) / [ADR-0003](./adr-0003-extract-find-slice-section.md)
  (rule-of-three / extract to `_common`).** The existing precedent is
  servo→jig (`tdd.py detect` reuse); a jig→servo `slice-land` pull-hint is a
  *planned* reciprocal (not yet implemented).
- **[ADR-0023](./adr-0023-lifecycle-family-spine.md) (lifecycle-family
  spine).** Encodes this pluggable-oracle boundary as spine contract clause
  **C5**; C5 stands as design intent and is unaffected by this ADR being
  parked.

## Open questions

- **Exit code vs `--json` for the gate?** The bare exit code (0/1/2) is
  simplest and matches `tdd.py`; `gate.py --json` adds `composite` /
  `threshold` / `status` / `missing` (the *composite* score + which components
  env-errored — **not** a per-component score map). Lean: the exit code gates;
  optionally capture `composite`/`threshold` for the reviewer. A true
  per-component breakdown would require a servo-side `gate.py --json` extension
  — a coordination ask, not a shipped capability.
- **Both oracles declared — which gates?** When a `deterministic` sub-oracle
  *and* a `servo` composite are both declared, do both gate (deterministic the
  cheap, witnessed floor; servo the richer signal) or does servo subsume? Lean:
  both must pass — and per Consequences, the deterministic floor stays on
  `tdd.py` for its stronger teeth.
- **Does `servo` belong only in refactor/bug,** or also spec-workflow's DONE
  gate? — **RESOLVED (2026-06-12, [spec 071](../specs/071-design-review-pass/spec.md)).**
  Yes for spec-workflow — but via the *loosest* path, not Option D's machine
  binding: a generic, attest-only **`design_review`** review pass on the existing
  ADR-0014 rails (a `reviews/slice-NN-design-review.md` verdict). A read-only
  reviewer attests the external eval's frozen verdict (e.g. servo's
  `.servo/design-eval/` composite ≥ threshold, non-stale, `env_error` ≠ pass) and
  records pass/fail; jig never machine-reads servo's exit code, never re-derives
  the score, and gains no servo discovery/coupling for the spec gate. This
  answers ADR-0019's OQ2 ("how thin is attest-only for the eval oracle?")
  empirically — **as thin as a review pass.** Option D's tight bug/refactor
  exit-code binding (§2–§5) stays PARKED on its own demand trigger; spec 071
  deliberately did not build it.
- **Design-conformance is a concrete instance of the spec-DONE-gate question
  above (added 2026-06-11).** Verifying a built UI matches its Claude Design
  baseline (surfaced exploring SymPill — a jig-scaffolded Android/Compose app) is a
  *spec-slice* DONE-gate oracle, not refactor/bug — so it instantiates "does
  `servo` belong … also spec-workflow's DONE gate?". Its ladder splits: the
  deterministic rungs (token-lint vs the design system; semantic UI assertions) are
  an ordinary servo composite — or even a jig `tdd.py`/AC check — needing nothing
  new; only the **visual** rung pulls this binding, and needs servo **ADR-0005
  extended to multimodal eval input**. Still demand-gated (one exploratory
  consumer, not the ≥-real trigger); captured as the first candidate consumer for
  the spec-gate side. See jig inbox 2026-06-11. — **RESOLVED 2026-06-12 (spec
  071):** the spec-gate side shipped as the attest-only `design_review` pass (see
  the resolved Open Question above); its first real consumer is food-log's servo
  design-fidelity eval. The **visual** rung still needs servo **ADR-0005 extended
  to multimodal input**, but the jig-side spec-gate *integration* is no longer
  demand-gated — it rides the generic review-evidence rails, no servo coupling.
