---
status: Accepted
dependencies: [adr-0011, adr-0031]
last_verified: 2026-07-24
frame_review: true
---

# ADR-0042: Route ADR-vs-lightweight by skill-prompted judgment at revision, not a lexical write-gate

## Status

Accepted (2026-07-24)

Records the maintainer's direction, given on
[#121](https://github.com/ramboz/jig/issues/121) on 2026-07-24.

## Context

[ADR-0031](adr-0031-load-bearing-decision-adr-trigger.md) fixed the *wording* of
the Architectural Decision Record (ADR) trigger and single-sourced it as
`decisions.py:ADR_TRIGGER`. Four consumer sites quote it verbatim and
`test_decisions.py::SingleSourceDriftTests` fails CI if any drifts.

**Nothing applies it.** `decisions.py` exposes one subcommand, `add-lightweight`,
which reads four text fields and appends; `ADR_TRIGGER` is a string it renders,
never evaluated. [#121](https://github.com/ramboz/jig/issues/121) reports the
consequence: a decision recorded as lightweight, later re-priced by an
adversarial review into a module-boundary change with rejected alternatives,
revised **by hand**, and never re-routed. The revised entry lists its rejected
alternatives while the rubric's lightweight criterion reads *"with no real
rejected alternatives"* — the record disqualified itself in the same file whose
header states the rule.

Two facts frame the decision:

1. **The failure is at revision, not first write.** #121's own closing claim —
   that a first-write check would have caught it — does not survive a read of the
   code: step 3 was a hand-edit that never called the helper, and a same-title
   re-record hits the idempotency no-op (`decisions.py:272-273`) before any check
   could fire. The moment that matters is the **update**.
2. **The project distrusts lexical pattern-matching.** The maintainer, on #121:
   a keyword-marker approach is *"likely brittle… we've seen this pattern failing
   repeatedly already in the project."* A gate that *blocks a write* on a brittle
   signal is the worst case — a false positive trains the operator to reach for
   the escape hatch, and a gate everyone waves through also launders the cases it
   should have caught.

   **Scoped deliberately: this argument is about gates built on *brittle
   signals*, not about [ADR-0011](adr-0011-spec-gate-model.md)'s
   deliberateness-gate model as such.** Left unscoped it would generalise
   against every escape-hatched gate jig has, `jig-spec-gate.sh` included, which
   is not the claim and not this ADR's call to make. ADR-0011's model stands; what
   this ADR says is that a *lexical* signal is not sound enough to sit under one.

This ADR decides **where the routing judgement lives and what mechanism makes
it**, not the rule (ADR-0031 owns the rule).

## Decision Options Considered

### Option A: Lexical write-gate on `add-lightweight`

Scan the decision text for markers and refuse on a hit, with an escape hatch.
Two shapes were prototyped: a flat keyword list (#121's literal suggestion) and a
two-signal rule derived from the rubric's own two criteria (`BOUNDARY` alone, or
`ALTERNATIVES ∧ LOAD_BEARING`).

- **Pros:** Deterministic; runs with no model in the loop; the two-signal variant
  passed both cases that mattered (jig's illustrative UI-copy entry did not flag;
  #121's reported case did).
- **Cons:** It is exactly the brittle lexical pattern the maintainer rejected. The
  flat list fires on jig's own illustrative UI-copy entry; even the tuned
  two-signal rule needed a mid-implementation narrowing (bare `interface` →
  `public interface`) after it refused an ordinary "user interface" copy
  decision — a live demonstration of the brittleness, found only because the
  false-positive corpus was jig's own file. And it gates the wrong moment: first
  write, when #121's failure is at revision.

### Option B: Skill-prompted judgement at revision (chosen)

Do not gate the helper. Put the routing judgement in the memory-sync skill's
written guidance: **when a lightweight decision is being updated, the assistant
first evaluates — using the already-single-sourced `ADR_TRIGGER` — whether it now
warrants promotion to an ADR, and if so routes it via `promote` instead of
revising in place.** The judgement is made by the model already in the loop,
reading the actual decision, not by a regex.

- **Pros:** Uses judgement where a lexical rule is brittle, which is the
  maintainer's stated preference. Targets the revision moment, which is where
  #121 actually broke. Adds no failure mode to the deterministic helper.
- **Cons:** Not enforced — an agent that skips the guidance, or calls the CLI
  directly, is not stopped. Mitigated, not closed, by the advisory lint (below)
  and by `update`/`promote` existing at all, which give the guidance concrete
  commands to attach to.
- **The precedent argument cuts both ways, and is recorded as a risk rather than
  a Pro.** "The rest of jig's load-bearing-decision routing already works this
  way" is true — the reconcile checklists and the session-end prompt are all
  judgement prompts quoting `ADR_TRIGGER`, not matchers. But those four surfaces
  predate #121 and did not fire. A fifth prompt of the same kind is not
  self-evidently different; what makes this one different has to be *where* it
  sits, which is why the guidance went into the always-loaded skill description
  and the reconcile checklists rather than a skill body alone. See Assumptions.

### Option C: Helper-side model call

Have `decisions.py` itself call a model to judge each decision.

- **Pros:** Deterministic entry point, judgement-quality signal.
- **Cons:** Puts a non-deterministic, host- and network-dependent call on a
  tier-0 helper that is deliberately self-contained and importable. Option B gets
  the same judgement from the model that is *already* reading the conversation,
  without making the helper depend on one.

### Option D: Lexical warning, never blocking

Keep the marker scan but only print, never refuse.

- **Pros:** No false-positive cost on the write path.
- **Cons:** A warning in a batch of recorded decisions reproduces #121's original
  failure — a routing signal that sat in prose and nobody acted on. If the signal
  is worth computing, it belongs somewhere an operator will actually read it,
  which is the advisory lint, not a line of stdout mid-batch.

## Recommended Decision

**Option B**, with one carve-out for the lexical machinery.

The routing judgement is made by the assistant, prompted by memory-sync's
`SKILL.md`, at the moment a lightweight decision is **updated** (and reinforced at
record time). It reuses `ADR_TRIGGER` as the criterion — the same
single-sourced sentence the reconcile checklists already quote — so the "when is
an ADR required?" policy still cannot drift across surfaces. When the judgement
says "promote", the assistant uses `decisions.py promote` (this spec's 100-03),
which moves the entry to an ADR and leaves a forward-linking stub.

**The lexical evaluator survives in exactly one place: the advisory `lint`
(100-04).** A lint is a low-stakes, offline, report-only sweep over records
*already on disk* — the one surface where a brittle signal is acceptable, because
a false positive costs a glance and a false negative is no worse than today. It
never blocks a write and never edits a file. This is the honest home for
pattern-matching in a project that has learned not to trust it on gate paths.

Rejected, therefore: the write-gate on `add-lightweight` (Option A) — the
mechanism #121 first proposed and this spec first built, then removed on the
maintainer's steer.

## Consequences

**Becomes easier:**
- The routing question is asked by something that can actually read the decision,
  at the moment the decision changes weight — which is where #121 failed.
- The deterministic helper gains no new refusal path, so every documented
  `add-lightweight` command block keeps working unchanged.
- Pattern-matching lives only where its brittleness is cheap; the project stops
  betting a write-gate on a signal it already knows is unreliable.

**Becomes harder:**
- Enforcement is softer. Guidance can be skipped; a direct CLI caller that never
  loads `SKILL.md` gets no prompt. The lint backstops this for records on disk,
  but there is no hard stop at write time. This is the accepted cost of not
  shipping a gate the maintainer would not trust.
- The judgement quality now depends on the prompt wording carrying `ADR_TRIGGER`
  faithfully — so the guidance site joins the set of surfaces
  `SingleSourceDriftTests` must cover.

## Assumptions

**Load-bearing and UNVERIFIED — the whole option rests on it:** *the routing
guidance is in the acting agent's context at the moment a recorded lightweight
entry is revised.* Named here because the frame-critique pass was right that an
earlier draft claimed "None unverified" while resting on exactly this.

The counter-evidence is real and must be recorded with it:

- jig already ships **four** judgement prompts quoting `ADR_TRIGGER`
  (`docs/workflow.md:303`, `spec-workflow/SKILL.md:684`,
  `memory-sync/SKILL.md`, the rubric), live since ADR-0031 —
  **and [#121](https://github.com/ramboz/jig/issues/121) happened anyway.** So
  "this extends an existing pattern" is not only a Pro; it also cites the
  mechanism whose miss produced the ticket.
- [ADR-0031](adr-0031-load-bearing-decision-adr-trigger.md) explicitly declines
  to claim that a judgement prompt lifts attention, and routes the deterministic
  floor elsewhere. This ADR leans on the claim ADR-0031 refused to make.

What that changes here, rather than being noted and ignored:

- The guidance moved into memory-sync's **skill description** — the surface the
  host loads every session — not only the skill body, which may never load on
  the trajectory #121 describes (a revision during an adversarial-review
  session, not during a memory-sync run). The maintainer's ask was literally "a
  better skill description"; the first implementation put it in the body only.
- The two reconcile checklists that already quote `ADR_TRIGGER` gain the
  revision clause, so a spec session carries it too.
- **Option B would not have caught #121 on its own either.** The revision there
  was a hand-edit that never reached any helper. `update`/`promote` supply a
  compliant path (necessary); the prompt supplies the trigger (not sufficient
  alone). Stating this keeps Option A's disqualification honest rather than
  asymmetric.

Code facts, each probed on this worktree:

- `ADR_TRIGGER` is defined at `decisions.py:41-45` and read by no other line —
  rendered, never applied.
- jig's existing load-bearing-decision routing is already judgement-prompted, not
  matched: `docs/workflow.md:303`, `spec-workflow/SKILL.md:684`,
  `memory-sync/SKILL.md:94` are prose prompts quoting `ADR_TRIGGER`. Option B
  extends that pattern rather than introducing a new one.
- The two-signal lexical rule was built and then removed within this spec's
  history; its narrowing incident (bare `interface`) is recorded here as evidence
  for the brittleness the maintainer cited, not as a live mechanism.

## Kill criteria

Rewritten to be *observable*. The frame-critique pass was right that the first
draft's criteria could not trip: neither had a corpus or a signal behind it, and
a soft mechanism whose only safety valve cannot fire is not backstopped.

- **The guidance does not reach the moment.** Observable at reconciliation: for
  each spec that revised a recorded decision, did the session route through
  `update`/`promote`, or hand-edit? Two hand-edits after this ships means the
  prompt is not landing where revisions happen, and a *deterministic,
  non-lexical* backstop (e.g. a structural check that an entry gained
  rejected-alternatives content since its last recorded state) has to be
  revisited.
- **The lint misses what it exists to catch.** The honest risk is **false
  negatives**, not noise: ADR-0031 already found that a lexical scan "is biased
  to catch *lightweight* decisions and miss *load-bearing* ones — the more
  load-bearing a decision, the less likely it carries a stock trigger phrase",
  and slice 100-04 narrowed the markers further, trading recall for precision in
  exactly that direction. Observable: when a misfiled entry is found by a human
  or a review, re-run `lint` against it. If the lint would not have flagged it,
  that is one strike; on the second, the evaluator is decorative and should be
  dropped rather than tuned. This also means **"mitigated by the advisory lint"
  is materially weaker than it sounds** — recorded here rather than left to be
  rediscovered.
- **Lint noise.** If findings on a real downstream corpus are mostly false
  positives, drop the evaluator rather than tune it — the brittleness verdict
  would then extend even to the advisory surface. Watch this second; the
  narrowing in 100-04 already optimised against it.

## Open questions

- **Should record-time (not just update-time) get the same guidance?** The
  reported failure is at update, so the guidance is anchored there; record-time
  already has the session-end memory-sync judgement prompt. Whether `add-lightweight`
  should carry an inline reminder too is left to implementation.
- **Should `lint` ever become a gate?** Deliberately not now: jig has no corpus of
  real lightweight entries (its own file has zero), so there is no evidence base
  for making it blocking — and doing so would re-introduce the very thing this
  ADR removed.
