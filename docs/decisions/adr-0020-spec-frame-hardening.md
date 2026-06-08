---
dependencies: [docs/decisions/adr-0011-spec-gate-model.md, docs/decisions/adr-0014-review-evidence-model.md, docs/decisions/adr-0002-rule-of-three-before-extraction.md]
last_verified: 2026-06-07
---

# ADR-0020: Spec/ADR Frame-Hardening: Grounding + Adversarial Frame-Critique

## Status

Accepted (2026-06-07)

## Context

jig's reviewer subagents (compliance / craft / arch / code-health, per
[ADR-0014](adr-0014-review-evidence-model.md)) all validate that an
*implementation conforms to its spec/ADR*. They reduce **variance** around a
given frame. None of them validates **the frame itself**.

So a hallucinated, shallow, or wrongly-assumed ADR — e.g. a false claim about a
library's capability, a misread of existing-code behavior, an unstated
load-bearing assumption — propagates downstream and gets *executed with
discipline*. The very rigor of the workflow then **masks** the error rather than
catching it: clean tests, passing reviews, a tidy deviation log, all built on a
wrong premise. This is a **bias** problem at the decision layer, not a variance
problem at the implementation layer, and jig currently has no mechanism aimed at
it.

**How often does this actually bite jig?** This is the load-bearing factual
claim of this ADR, and per the grounding standard below it must be marked
honestly: **it is an assumption, not a measured fact** (see Assumptions §A1).
The retro spike (spec 064-01) is its kill-criterion test. Two *known* in-repo
instances are documented, not asserted:

- **[ADR-0011](adr-0011-spec-gate-model.md) honesty gap** — the spec-gate was
  built on the frame "the `JIG_CONVENTIONS_APPROVED=1` env var enforces
  human-only approval." That frame was false (any shell, incl. the agent, can
  set the var). It propagated until caught during a later honesty review and
  required a superseding correction. A frame-critique pass at READY_FOR_REVIEW
  would have attacked exactly that assumption.
- **Spec 055 pricing** — hand-rolled Opus token pricing was asserted (~3× too
  high) rather than probed; spec 056 now mandates "price via `npx ccusage`,
  never hand-roll." A grounding-by-probe requirement would have forced the
  number to be measured, not asserted.

Both were eventually caught by jig's reconciliation / honesty culture — *late*,
where cost-of-error is highest. The opportunity is to catch the same class
**early**, at spec/ADR authoring time, where correction is cheapest.

Two constraints shape the design:

1. **jig auto-triggers by default.** A review pass nobody remembers to turn on
   is a dead loop. The trigger must be *derived*, not a per-author judgment call
   that a less-experienced contributor can't make consistently.
2. **Recent direction is leaner, not heavier.** Specs 055/057 spent effort
   *removing* front-loaded ceremony and orchestrator cost. A mandatory
   grounding + assumptions + kill-criteria + gate on *every* spec would run
   directly against that arc. Whatever we add must default-off on the common
   case (inline-mirror / refactor / docs work) and fire only where there is a
   frame to get wrong.

## Decision Options Considered

### Option A: Do nothing — rely on existing reconciliation / honesty review

- **Pros:** Zero added ceremony; preserves the 055/057 lean arc; the two known
  instances *were* eventually caught this way.
- **Cons:** Catches frame errors **late** (post-implementation), where
  cost-of-error is highest; relies on the same model that authored the frame
  noticing its own blind spot during reconciliation, with no prompt forcing an
  adversarial stance; offers nothing to a less-experienced contributor whose
  spec the human reviewer "only catches so much" of.

### Option B (Recommended): Grounding-by-probe + assumptions/kill-criteria + a derived-trigger adversarial frame-critique pass

Three coordinated, mostly-soft mechanisms:

1. **Grounding requirement.** Factual claims in a spec/ADR about *runnable*
   surfaces — library/API capability, version behavior, performance, behavior of
   existing code — must be backed by a **verifiable artifact**: preferentially an
   *executed probe* (a command that ran, a snippet from source/`node_modules`),
   falling back to a citation. Anything not verifiable must be **explicitly
   marked as an assumption**, never stated as fact.
2. **Assumptions + kill-criteria as first-class sections.** A spec/ADR
   enumerates its load-bearing assumptions and (where meaningful) explicit kill
   criteria — "what would make this decision wrong." This section is *optional /
   risk-gated*, not mandatory boilerplate on every artifact (see the trigger).
3. **Adversarial frame-critique reviewer pass.** A new gated review pass
   (`frame_review` frontmatter flag, mirroring `arch_review` /
   `code_health_review` per ADR-0014) whose reviewer's *only* job is to find the
   single load-bearing assumption most likely to be wrong — **not** to check
   conformance. It runs at **READY_FOR_REVIEW on the spec/ADR itself**, before
   implementation, where cost-of-error is lowest.

   **The trigger is derived from grounding, not chosen.** Set `frame_review:
   true` when grounding leaves **≥1 unverified load-bearing assumption**, OR the
   artifact is an ADR (or a spec that will spawn one — hard-to-reverse by
   definition), OR it introduces a new external dependency / asserts external
   library/API/version/perf behavior. Otherwise default-off. The spec-author /
   `clarify` step sets the flag mechanically from its own grounding output, so a
   junior contributor never has to *decide* whether the pass is "needed" — the
   assumptions they surfaced decide for them. The pass cannot fire on nothing:
   it only runs when there is literally an unverified assumption on the table to
   attack.

- **Pros:** Attacks **bias** (the gap Option A leaves) and does it **early**;
  the probe form of grounding is the only mechanism here with genuine
  real-world contact; the derived trigger keeps it from being a dead loop *and*
  default-off on jig's common case, honoring the 055/057 lean arc; reuses the
  existing gated-review-pass machinery (low net-new surface, ADR-0014 pattern);
  helps less-experienced authors flesh out specs without relying on a human
  reviewer to catch everything.
- **Cons:** When the same model authors the spec *and* runs the frame-critique,
  they share blind spots — correlated, like best-of-N (see Option C). The pass
  is therefore a *real improvement*, not a *cure* (see Consequences + Assumptions
  §A2); "kill criteria" risks becoming ceremony theater on artifacts where it's
  artificial (mitigated by making §2 risk-gated, not mandatory); adds authoring
  cost on the (minority of) artifacts that do trigger.

### Option C (Deferred — documented, not built): Tier 2 "deep reasoning" — parallel best-of-N spec/ADR drafts + reconciliation

Generate N independent spec/ADR drafts and reconcile them into one.

- **Pros:** In principle surfaces alternatives a single draft misses.
- **Cons (why deferred):** It addresses **variance, not bias** — the exact gap
  this ADR targets. Same-model samples produce **correlated hallucinations and
  shared blind-spot assumptions**, so reconciliation can manufacture *false
  consensus* and launder away uncertainty (a confidently-agreed wrong frame
  reads as a validated one). It also costs ~4× on the most expensive step
  (spec/ADR authoring), against the 055/057 cost direction.
- **Revisit trigger:** Reconsider **only once** (a) grounding + frame-critique
  (Option B) exist and are in use, **AND** (b) there is a **grounded,
  generator-independent verifier** (e.g. the frame-critique pass runs on a
  *different model* than authored the draft — see Consequences) **AND** (c) the
  N drafts can be given **forced-orthogonal objectives** so the samples are not
  correlated. Absent (b) and (c), best-of-N manufactures false confidence and is
  net-negative.

## Recommended Decision

Adopt **Option B**, sequenced behind a gating retrospective:

- **Gate (spec 064-01, a `kind: spike`):** retro over jig's existing specs/ADRs
  — do frame errors occur, and would grounding / frame-critique have caught
  them? This is the empirical grounding for §A1 and the go/no-go for the rest.
- **If go:** ship grounding (the probe-first form), the risk-gated
  assumptions/kill-criteria section, and the derived-trigger frame-critique pass.
- **Defer Option C** with the revisit trigger above; capture it here so the
  analysis isn't lost.

Scope is deliberately tight: **do not** pull Tier 2 into implementation; **do
not** make any piece a hard blocking gate (advisory / deliberateness-signal
only, per [ADR-0011](adr-0011-spec-gate-model.md)); **do not** mandate the
assumptions section on every artifact.

## Consequences

**Becomes easier:**
- Catching wrong-premise specs/ADRs *before* implementation spends effort on
  them.
- A less-experienced author gets an independent adversarial read of their frame
  without depending on a human reviewer to catch every gap.
- Factual claims in specs/ADRs become probe-backed by default, reducing the
  "asserted number that's 3× wrong" failure mode (spec 055 lesson).

**Becomes harder:**
- Authoring a *triggering* spec/ADR costs more (enumerate + ground assumptions,
  absorb one more review pass). Bounded to artifacts that actually have an
  unverified frame.
- Honest framing of value: the frame-critique pass runs as a fresh **subagent**,
  so it already gets **fresh-context independence** (the author's reasoning trace
  is not shared) — same as every other review pass, and free in 064-03. But a
  subagent is *not* a different model: a **same-model** critique still **shares
  the author's training-baked blind spots**, so a confident hallucination tends
  to reproduce across instances (the correlated-samples property that also sinks
  Option C). Fresh context does not break that correlation. The pass's leverage
  therefore comes from (a) the adversarial prompt forcing a different stance,
  (b) probe contact with reality, (c) fresh context, (d) the human reading its
  output — **not** from generator independence. There is a value ladder:
  1. **Fresh-context subagent** — free, built into 064-03.
  2. **Different *Claude version* subagent** (via the subagent `model` override)
     — cheap config; *partial* generator independence, but same family / same
     training lineage, so still correlated.
  3. **Genuinely different (non-Claude) model** — *real* generator independence;
     depends on whether the harness can route there. This is the actual future
     knob, and it is also precondition (b) for revisiting Option C.

  **Model policy for frame-critique:** it runs **equal-or-stronger** than the
  author; **never downgrade it for cost.** A same-family downgrade (e.g.
  Opus author → Sonnet critique) is *not* generator independence — same training
  lineage, correlated blind spots — and it sacrifices the reasoning depth the
  pass exists for, since spotting a subtle wrong premise is the hardest pass in
  the set and a weaker model is *less* likely to catch what a stronger author
  missed. Cost-driven model downgrades, if adopted, apply to the **conformance
  passes only** (compliance / craft / code-health), never to frame-critique.

## Scope

- **In:** grounding requirement (probe-first); risk-gated assumptions/
  kill-criteria section; `frame_review`-gated adversarial frame-critique pass at
  READY_FOR_REVIEW; mechanical/derived trigger set by the author/`clarify` step.
- **Out (this ADR):** Tier 2 best-of-N (Option C, deferred w/ trigger);
  cross-model frame-critique (noted, not built); any hard blocking gate;
  mandatory assumptions section on non-triggering artifacts.

## Assumptions

> Per this ADR's own grounding standard, its load-bearing assumptions are listed
> rather than stated as fact.

- **A1 — bad-frame errors recur in jig at a rate that justifies the machinery.**
  ~~*Unverified.*~~ **RESOLVED (2026-06-07) — weakly confirmed → GO.** The gating
  retro (spec 064-01; [census](../specs/064-spec-frame-hardening/retro.md))
  examined 33 artifacts and found **4 catchable frame errors (~12%)**, 3 caught
  late and 1 shipped-until-fixed, two of them in hard-to-reverse ADRs. The kill
  criterion ("no catchable frame errors → shelve") is therefore **not** met. The
  corpus is cleaner than this assumption feared (corroborating the user's "not
  noticing this much"), and the retro **inverts the lever priority**:
  grounding-by-probe is the load-bearing half (4/4 catchable), the
  frame-critique pass the weaker, kill-criterion-watched bet (2/4 clean). Scope
  (Option B) is unchanged; only emphasis shifts — 064-02 leads with grounding,
  064-03 ships its pass default-off/gated as already designed. *(Original
  unverified framing preserved above the strikethrough for the audit trail.)*
- **A2 — a same-model adversarial pass catches a non-trivial fraction of frame
  errors despite shared blind spots.** *Unverified.* Plausible via stance-forcing
  + probe contact, but unquantified. The retro should sample whether an
  adversarial read would plausibly have flagged the known instances.
- **A3 — the derived trigger fires on roughly the right set** (rare enough to
  honor the lean arc, frequent enough not to be dead). *Unverified;* depends on
  how often jig specs carry unverified load-bearing assumptions. Measurable post-
  ship via the 056 usage / routing instrumentation.
- **A4 — the gated-review-pass machinery (ADR-0014) extends to a fifth pass at
  READY_FOR_REVIEW with low net-new surface.** *Probe-able now* (read
  `review.py` / `review_evidence.py`); to be confirmed in the interface slice,
  not assumed.

## Kill criteria

- **Kills the whole ADR:** the retro (064-01) finds no frame errors in jig's
  history that grounding/critique would plausibly have caught → premise §A1
  false → abandon or shelve.
- **Kills the frame-critique pass specifically:** post-ship, triggered passes
  produce ≥ ~majority no-finding / nit-only verdicts over a meaningful sample →
  it's a dead loop adding cost without catching bias → remove or move behind
  cross-model independence.
- **Kills the kill-criteria section:** if it consistently fills with ceremonial
  boilerplate on triggering artifacts → drop §2, keep grounding + critique.

## Relationship to other decisions

- [ADR-0014](adr-0014-review-evidence-model.md) — frame-critique is a new gated
  review pass; reuses the per-slice flag + verdict-artifact pattern
  (`arch_review` / `code_health_review` siblings).
- [ADR-0011](adr-0011-spec-gate-model.md) — every mechanism here is advisory /
  deliberateness-signal, **not** a hard enforcement gate; real enforcement stays
  out-of-band. (ADR-0011 is also a documented bad-frame instance.)
- [ADR-0002](adr-0002-rule-of-three-before-extraction.md) — if grounding-probe
  or trigger logic ends up mirrored across author + reviewer + clarify steps,
  the rule-of-three governs extraction into `_common/`.

## Open questions

> Flagged for the human rather than guessed; load-bearing.

1. **OQ1 — retro depth.** Full census of ~60 specs/ADRs, or a representative
   sample (e.g. all ADRs + a stratified spec sample)? Sample is cheaper and
   probably sufficient for a go/no-go; full census is more defensible.
2. **OQ2 — frame-critique placement.** READY_FOR_REVIEW only, or also re-run on
   ADRs at the `adr.py accept` step? This ADR assumes READY_FOR_REVIEW only.
3. **OQ3 — should ADRs default `frame_review: true`** unconditionally (they're
   hard-to-reverse by definition), or still gate ADRs on the
   unverified-assumption signal like specs? Current draft: ADRs always trigger.
4. **OQ4 — generator independence.** The pass runs as a subagent regardless
   (fresh context, rung 1 — free, built into 064-03). Rung 2 (a *different Claude
   version* via the `model` override) is only meaningful when it's *equal-or-
   stronger* than the author; for an **Opus-authored** spec (the common case
   here) the only different versions are weaker, which the model policy forbids
   — so **rung 2 collapses for an Opus author** and is not a lever. That leaves
   rung 3 (a genuinely different, non-Claude family) as the only real
   independence step — harness-dependent and precondition (b) for Option C.
   **Question:** defer rung 3, accepting that 064-03 ships rung-1 independence
   only (stance + probes + fresh context + human)? Current draft defers rung 3.
   *(See the separate model-routing follow-up in `docs/inbox.md` for the
   orthogonal "downgrade conformance passes to Sonnet for cost" question.)*

## Amendments

> Per [ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md): this ADR is
> a closed (Accepted) record, so post-acceptance decision refinements are
> recorded here rather than rewriting the prose above. The original Open
> questions are preserved verbatim.

**2026-06-07 — Open questions OQ1–OQ4 resolved with the human** (gating the
064-03/04 implementation):

- **OQ1 (retro depth) → stratified sample.** Resolved before the 064-01 spike;
  the gating retro returned **GO** (see §A1 above + [retro.md](../specs/064-spec-frame-hardening/retro.md)).
- **OQ2 (placement) → specs @ READY_FOR_REVIEW + ADRs @ `adr.py accept`.** Each
  artifact's pre-commitment checkpoint (specs have an RFR lifecycle state; ADRs
  do not — their pre-commitment moment is acceptance). One run per artifact, at
  the cheapest catch point. The gate is a **soft / bypassable deliberateness
  signal** (`JIG_REVIEW_EVIDENCE_GATE=0`, ADR-0011), not hard enforcement —
  consistent with the other review-evidence gates (ADR-0014).
- **OQ3 (ADR default) → ADRs always-on** (`frame_review: true` unconditionally);
  specs stay derived from the unverified-assumption signal (064-04). Rationale:
  ADRs are hard-to-reverse and rare (~20 in jig's life → always-on is cheap in
  aggregate), and the 064-01 retro's two *clean* frame-critique wins were both
  ADRs (ADR-0008, ADR-0011). Gating ADRs on a surfaced-assumption signal would
  miss the exact ADR-0011 failure mode (a confidently-wrong frame that surfaces
  *no* assumption to trigger on).
- **OQ4 (generator independence) → ship rung-1, defer rung-3.** 064-03 ships
  fresh-context-subagent independence (stance + probes + fresh context + human
  read) and encodes the **equal-or-stronger model policy** (never downgrade the
  critique for cost). Rung-3 (a genuinely different, non-Claude family) is
  **deferred** to `docs/refinement-todo.md` with the documented revisit trigger
  (it is also Option C precondition (b)); rung-2 collapses for an Opus author
  (the only different Claude versions are weaker, which the policy forbids).

These resolutions narrow 064-03/04 to scope; they do **not** change the core
decision (Option B), only settle the deferred-to-human knobs. The 064-01 retro's
emphasis (lead with grounding; frame-critique is the weaker, kill-criterion-
watched bet) stands — these OQ answers keep frame-critique gated/default-off on
specs and reserve always-on only for the low-volume, high-stakes ADR class.
