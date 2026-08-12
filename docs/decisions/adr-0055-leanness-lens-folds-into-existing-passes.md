---
status: Accepted
dependencies: []
last_verified: 2026-08-11
frame_review: true
---

# ADR-0055: Leanness lens folds into existing review passes, not a new gate

## Status

Accepted (2026-08-11)

## Context

Spec 109 adds a leanness / minimal-viable-architecture lens (over-engineering,
premature abstraction, speculative generality) to the **spec-workflow lifecycle's**
review surfaces — the retrospective half of a value SPIDR already carries at the
slice-splitting altitude but that never propagated into review. (The prospective
half — shaping new work lean before specs exist — lives in the sibling `shaper`
project, its ADR-0005.)

**Scope, stated up front (per this ADR's frame-critique).** The lens lands in the
arch pass and the reconciliation pass — the two surfaces where over-engineering
would surface *for a spec-workflow slice*. It does **not** reach jig's other
lifecycle families: the **bug-fix** lifecycle has **no arch pass** ("bugs carry
no design," [bug-fix/SKILL.md:299](../../skills/bug-fix/SKILL.md)) and no
reconciliation pass — its `→ REVIEWED` gate runs `bug-review` + `craft`
(+ optional `security`). So bug fixes — a real over-engineering site ("add a
configurable abstraction while I'm in here" instead of the smallest fix the
diagnosis supports) — get **zero** leanness coverage from this spec, not degraded
coverage. That gap is named here and weighed in Consequences; extending the lens
to bug-fix is a demand-gated follow-up ([docs/refinement-todo.md](../refinement-todo.md)),
not silently assumed away.

The question this ADR settles: **where does the leanness lens live, and does it
get its own enforcement machinery?** jig already has a precedent for adding a
review dimension as a *new, gated pass* with its own frontmatter flag and
evidence file — `code_health_review` (slice 060-05 / ADR-0017), which mirrors
`arch_review`. A future contributor could reasonably reach for that same shape
for leanness ("add a `leanness_review: true` flag, a `leanness` pass, and a
`slice-NN-leanness.md` evidence file"). This ADR exists so that reach is a
deliberate reversal, not an unwitting default.

## Decision Options Considered

### Option A: Fold the lens into the existing arch + reconciliation passes
Add leanness as directives inside `build_arch_review_prompt`'s `## Evaluate`
block + the `arch-review` SKILL.md Concerns bucket (109-01), and inside
`build_reconciliation_prompt` + the reconciliation checklist (109-02). No new
flag, pass, evidence file, or gate; findings ride the existing verdict
envelopes.
- **Pros:** Reuses passes that already run at zero marginal orchestration cost;
  no new gate to maintain; self-demonstrates the spec's own thesis (the leanest
  change that satisfies the need). Leanness is naturally an *architecture*
  concern (arch pass) and an *after-the-fact* concern (reconciliation), so it
  lands where reviewers already look.
- **Cons:** Two costs, one obvious and one load-bearing.
  - *Not independently gated* — a slice with `arch_review: false` gets no
    arch-pass leanness check (only the always-on reconciliation sweep covers
    it); leanness can't block `REVIEWED` on its own the way a dedicated pass
    could.
  - *Attention dilution (the real risk)* — the leanness directive competes for
    reviewer attention inside prompts that are **already multi-dimensional**.
    `build_arch_review_prompt`'s `## Evaluate` block already asks about module
    boundaries, contract sync, and unaddressed failure modes;
    `build_reconciliation_prompt` appends contract-surface, principles,
    practices, touched-files, and sweep checks before the over-build sentence.
    A directive folded into that density may get **boilerplate treatment** — a
    reviewer technically "covers" it without doing the harder counterfactual
    reasoning ("would a *simpler* architecture satisfy the ACs?") a dedicated
    pass, whose entire remit is that one question, would compel. If that
    happens, the exact failure spec 109 exists to fix — leanness never applied
    as a consistent standing lens — re-manifests silently. **This is the bet
    Option A makes; it is an assumption, recorded as A1 below, not a verified
    fact.**

### Option B: A new gated `leanness_review` pass
A dedicated pass with a `leanness_review: true` frontmatter flag, a
`review.py leanness` builder, a `slice-NN-leanness.md` evidence file, and a
`workflow.py leanness-review-needed` deriver — the `code_health_review` shape.
- **Pros:** Leanness becomes independently gateable and always-checkable
  regardless of `arch_review`; symmetric with code-health.
- **Cons:** Heavier — a new flag, builder, evidence file, deriver, gate wiring,
  and per-slice review cost (specs 055/057 context-cost discipline; the same
  cost ADR-0017 cites for gating code-health *off* by default). Adding gate
  machinery to enforce "don't over-build" would itself be the over-engineering
  the lens is meant to catch. No demonstrated need for independent leanness
  gating exists yet (rule-of-three: zero real cases).

## Recommended Decision

**Option A.** Fold the leanness lens into the arch pass and the reconciliation
review/checklist. Do not add a new flag, pass, evidence file, or gate.

The deciding principle is the lens's own: choose the smallest change that
satisfies the need. The need is "leanness is evaluated where reviewers already
look," and two existing passes already look there — the arch pass (architecture
concerns) and reconciliation (after-the-fact sweep). A new gate is speculative
generality until a real case shows folding-in is insufficient. Anchoring every
leanness directive to *still satisfying the acceptance criteria*
(leaner-that-still-passes) keeps the lens from being read as license to strip
required behavior.

**Mitigating the attention-dilution risk (A1).** Two design choices reduce it,
though neither proves it away: (1) each directive is given its **own prominent
line** — a bolded bullet in the arch `## Evaluate` list, a standalone bolded
paragraph in reconciliation — not buried in an existing sentence; (2) it poses
a **concrete counterfactual question** ("would a simpler architecture satisfy
the ACs?") rather than a vague "check for leanness," which is harder to satisfy
with boilerplate. These are mitigations, not evidence. They do **not** come with
a reliable way to detect A1 failing — the fidelity-side kill criterion below
names a best-effort signal but states plainly that it may never surface, so
Option A accepts a residual, possibly-undetected fidelity risk (see A1).

## Consequences

**Becomes easier:**
- Over-engineering is now a first-class, standing review concern instead of a
  value re-derived ad hoc inside individual ADRs.
- Zero new machinery to maintain; the change is additive prompt/checklist text.

**Becomes harder:**
- **Coverage is spec-workflow-only.** Because the lens rides the arch +
  reconciliation passes, it reaches spec-workflow slices only. The bug-fix
  lifecycle (no arch pass, no reconciliation) gets no leanness coverage at all —
  a real gap, since bug fixes over-engineer too. This is a *deliberate scope
  boundary of spec 109*, not a claim of full jig coverage: "leanness is a
  standing review lens in jig" is true for spec-workflow, overstated elsewhere.
  Extending it (e.g. folding the counterfactual into bug-fix's `craft`/`bug-review`
  prompt) is a demand-gated follow-up filed in `docs/refinement-todo.md`.
- Leanness is not independently gateable: a slice with `arch_review: false`
  relies solely on the always-on reconciliation sweep for its leanness check.
- The lens's efficacy rests on assumption A1 (reviewers give the folded-in
  directive genuine, not boilerplate, scrutiny). If A1 is wrong the failure is
  quiet — reviews stay green while over-engineering ships — and it may stay
  **effectively unmonitored**: the fidelity-side kill criterion names a signal
  but concedes it may never surface (detecting it is subject to the same
  attention limits as the review that missed it). This is an **accepted residual
  risk**, not a monitored one. This ADR is the record that the omission (no
  gate), the bet (A1), and the accepted exposure were all deliberate, not
  overlooked.

## Assumptions

- **A1 (load-bearing, unverifiable pre-hoc).** Folding the leanness directive
  into the existing arch + reconciliation prompts yields **enforcement fidelity
  comparable to a dedicated pass** — reviewers give it genuine counterfactual
  scrutiny, not boilerplate coverage, despite competing with other directives in
  a dense prompt. This cannot be verified before the lens runs in practice; it
  is the bet Option A makes. It is **mitigated** (prominence + concrete
  question) but **not reliably monitored** — the fidelity-side kill criterion
  below names a *signal*, not a working detector, and that signal is itself
  subject to the same attention limits as the review it backstops. Option A
  therefore **accepts a residual, possibly-never-detected fidelity risk** as the
  deliberate price of not building Option B's gate + rollup machinery. *Named
  explicitly so a future reader knows it was weighed and accepted, not
  overlooked.*
- **Grounded (not assumptions).** The precedent (`code_health_review` as a gated
  pass with flag + evidence file) and the two fold-in surfaces
  (`build_arch_review_prompt`, `build_reconciliation_prompt`) are verified in
  the spec 109 deliverables.

## Kill criteria

Two triggers would reverse this toward Option B — a **demand-side** one (which a
real case surfaces on its own) and a **fidelity-side** one (which, honestly, may
never surface — see the exposure statement below):

- **Demand-side.** A real, recurring case where a slice must be blocked on
  leanness *independently* of `arch_review` (the always-on reconciliation sweep
  is demonstrably too late or too weak for it).
- **Fidelity-side (A1 fails).** The observable signal is over-engineering that
  shipped through green arch + reconciliation reviews and was caught only
  *downstream* — in a code-health pass, a follow-up refactor spec, or a bug
  record — while the leanness dimension of those upstream reviews flagged
  nothing. **Detection is manual/opportunistic today, not automated — do not
  read this criterion as an existing safety net.** What exists in-tree is only
  the `[spec]`/`[impl]` self-classification in `review.py`; the rollup that
  would *tally* leanness-dimension findings over time is **unbuilt** — it is the
  `docs/refinement-todo.md` "Instrument the review→learnings→clarify loop
  *before building it*" item, **Deferred (2026-06-08)**. So the honest trigger
  is a maintainer noticing that downstream-caught-over-build pattern; building
  the automated count (or moving to Option B's dedicated pass) is the response
  **if the pattern recurs** — demand-gated, per jig's grow-by-signal principle.
  **The residual exposure, stated plainly:** noticing this signal is a
  voluntary, low-frequency, higher-effort retrospective act — trace a downstream
  over-build back to a *specific* prior review and conclude the *leanness*
  dimension (not another) missed it — and it is subject to the **same attention
  limits** that make A1 a risk in the first place. So a wrong A1 may go
  **undetected indefinitely**; this criterion is a best-effort signal, not a
  reliable channel, and Option A accepts that. The bet is that the cost of a
  missed over-build (caught later, in code-health/refactor/bug surfaces that
  already exist) is smaller than the standing cost of Option B's gate + rollup
  machinery on every slice — a trade this ADR makes deliberately, to be
  revisited if a missed leanness pattern ever does become visible.

## Open questions

None.
