# Retro: frame-error census (spec 064-01)

> Census artifact for the [064-01 gating spike](slice-01-retro-frame-error-census.md).
> Tests [ADR-0020](../../decisions/adr-0020-spec-frame-hardening.md) §A1 (does this
> error class recur, would grounding/frame-critique have caught it early?) and the
> kill criterion ("no catchable frame errors → shelve the ADR").

**OQ1 resolution (with the human, 2026-06-07):** stratified sample — all 19
non-driving ADRs (every ADR except this spike's own ADR-0020) + 14
design-/decision-weighted specs (incl. both ADR-0020 known-instance specs
042/055 + a spike 044 + early foundational ones + honest negative controls).
See **Scope examined** below for the count reconstruction.

**Scope examined:** 33 distinct artifacts — **19 ADRs** (every ADR except this
spike's own driving ADR-0020; there is no ADR-0018) + **14 specs**. To make the
count reconstructible: the three ADR-paired specs (042→ADR-0011, 051→ADR-0015,
044→ADR-0009) are counted on the **ADR side** (their table rows are shared), so
the 14 specs are the non-paired ones — an 11-spec stratified sample (001, 003,
005, 015, 016, 028, 029, 045, 055, 056, 057) plus 3 surfaced opportunistically
by the cross-cutting grep (008, 037, 050). Reading delegated to a
read-only subagent (055 discipline); the three most load-bearing claims
(ADR-0008→Superseded-by-0010, the ADR-0010 narrowing, the spec-056
nested-transcript correction) were **probe-verified** against the repo before
recording — dogfooding this spec's own grounding standard.

## Census table

| Artifact | Class | Frame issue (1 line) | (a) grounding catch? | (b) critique catch? |
|---|---|---|---|---|
| **ADR-0008** (closed-spec drift) | **caught-late** | Assumed an `## Amendments` block on *live router-read prose* (SKILL.md `description:`) fixes drift — but the router reads frontmatter, not the body, so the fix left the defect live; superseded by ADR-0010 after propagating through the 036-02 sweep. | **Partial.** Probing "where does the router read the description from?" shows frontmatter ≠ body. | **Yes.** Adversary: "does the consumer read the body?" → no. Clean stance-forcing catch. |
| **ADR-0011 / spec 042** (spec-gate) *(KNOWN — calibration)* | **caught-late** | "`JIG_CONVENTIONS_APPROVED` enforces human-only approval" — any shell (incl. the agent) sets it. | Partial — probing "can the agent set this var?" confirms trivially. | **Yes.** The textbook frame-critique target; ADR-0020's motivating case. |
| **ADR-0015 / spec 051** (worktree reservation; seeded in 003-03) | **shipped→fixed** | Reserve-on-main carried the unstated assumption "run from `main`" (the `HEAD==main` precondition is dead code in the worktree flow it serves); plus the **B1** misread that pushing from the temp worktree works with relative-`origin` repos. | **Yes (both).** Running `workflow.py new` from a linked worktree surfaces the refusal; pushing from the temp worktree surfaces B1. Pure runnable-surface errors. | Partial — an adversary on 003-03 *could* flag "assumes invocation from main," but the worktree norm made it non-obvious pre-fact. |
| **spec 056** finding #2 (subagent transcripts) | **caught-late** | A by-hand analysis globbed `…/*.jsonl` one level deep, missed the nested `subagents/` dirs, and wrongly concluded `toolUseResult` was the only subagent record → drove a "proxy factor 0.7" design. Caught at 056-01 review. | **Yes — strongest case.** One `ls -R` of the transcript tree refutes it. | Partial — a critique could ask "sure subagent usage isn't logged elsewhere?", but a probe is the decisive instrument. |
| **spec 055** pricing *(KNOWN — calibration)* | **none (at artifact layer)** | Hand-rolled Opus pricing ~3× high — but the error lived in the *pre-spec analysis*; spec.md already cited ccusage figures. Codified in spec 056. | (Probe would have caught the original mis-estimate.) | (n/a at the spec-artifact layer.) |
| spec 037 Q3 | none (self-caught) | Body claimed slice 007-02 DEFERRED; verification showed DONE. Corrected in the clarify pass. | Probe-caught by the author's own "Verification 2026-05-26" — exactly what a grounding requirement mandates. | — |
| spec 050-02 AC4 | none (caught at review) | AC4 assumed `stale` exits non-zero; it has always exited 0 (015-03 contract). Resolved to intent. | Probe (read the dispatch) refutes it. | Caught anyway by compliance review. |
| spec 008 DoR | none (caught at review) | DoR asserted "typed exception → exit 2"; sibling returns exit 3. Misread of own code, fixed in reconciliation. | **Yes** — reading the sibling handler refutes it. | Low-stakes. |
| spec 001-01 (`detect_team`) | none (impl-layer) | Assumed scaffold target == repo root; walked into parent monorepo git. Real, but an *implementation* bug below the decision layer; caught + regression-tested. | Yes (a probe in a monorepo subdir). | Marginal — below the frame layer. |
| ADR-0009 / spec 044 (RTK spike) | none | **Negative control done right:** the whole spike is grounding-by-probe (measured v0.42.0, 54-command audit) — refuted the marketing 60–90% claim empirically. *(Counted ADR-side.)* | — | — |
| spec 045 (review gates) | none | **Negative control done right:** "Current state verified 2026-05-27" probed every claim (the Stop hook is task-capture, etc.). | — | — |
| spec 057 (thin-orchestrator) | none | Explicitly honest about evidence (n=25, heuristic attribution, list-price proxies); *falsified* cache-TTL as a lever via data. | — | — |
| spec 003 (workflow-promotion) | none (seeded 051) | 10 deviations, all spec-internal AC-vs-example mismatches except #9 (reserve-on-main never dogfooded live) → that thread became the 051 frame error. | — | — |
| spec 005 / 015 / 016 / 028 / 029 | none | Deviations are rule-of-three / AC-wording / regex-shape calls, not falsified external premises. | — | — |
| ADR-0001/0002/0003/0004/0005/0006/0007/0012/0013/0014/0016/0017/0019/0021 | none | Mechanical/structural decisions; no falsified external claim. | — | — |
| ADR-0010 | none | (the *correction* artifact for ADR-0008.) | — | — |

## Counts

- **Total examined:** 33 distinct artifacts (19 ADRs + 14 specs — see Scope for the count reconstruction; ADR-paired specs 042/051/044 counted ADR-side)
- **No frame issue:** 29
- **Frame issue caught late:** 3 (ADR-0008; ADR-0011/042; spec 056 #2)
- **Frame issue shipped (live until a later fix):** 1 (ADR-0015/051 — `HEAD==main`, seeded in 003-03)
- **Genuine frame errors: 4 of 33 (~12%).** Catchable by **(a) grounding-by-probe: 4/4**; by **(b) adversarial frame-critique: 2/4 cleanly** (+2 partial); **by either: 4/4; by neither: 0**.
- Spec 055 pricing (2nd known instance) does **not** count at the spec-artifact layer — already ccusage-corrected by authoring time; the error lived upstream.

## Surprises

1. **The lever ranking is inverted vs ADR-0020's framing.** Every one of the 4
   errors touches a *runnable surface*, so **grounding-by-probe is the
   load-bearing half (4/4)**; the adversarial-critique pass is a clean win on
   only the 2 architectural-judgment ADR cases (the minority). ADR-0020 leads
   with the critique pass as the headline mechanism; the data says lead with
   grounding.
2. **Part of the value is already captured informally.** Specs 037/042/044/045
   show jig's existing **"Current state (verified …)" discipline *is*
   grounding-by-probe done by hand** — they probed and either got it right or
   self-caught the false premise at authoring/clarify (the exact early catch
   ADR-0020 wants). The proposal's value is making it **mandatory + derived**
   rather than reliant on author diligence.
3. **No "neither-catches" frame error appeared** (good for the design — no blind
   spot beyond the two it targets), but n=4 is small; don't over-read it.
4. **The corpus is cleaner than §A1 feared** (~12%, not pervasive rot) —
   corroborating the user's "haven't noticed this much across ~60 specs."

## Outcome → go/no-go

**GO (qualified).** ADR-0020's kill criterion ("no catchable frame errors →
shelve") is **not** met: 4 catchable frame errors, two in hard-to-reverse ADRs,
one (ADR-0008) propagating through an implemented sweep before ADR-0010 caught
it — a genuinely expensive late catch. Premise §A1 is **weakly confirmed**: the
class recurs, propagates, and is caught late where cost is highest.

The evidence **reshapes priority within Option B** (it does not expand scope):

- **Lead with grounding-by-probe (064-02).** Strongest empirical support (4/4),
  lowest novelty risk, codifies a discipline jig already half-practices.
- **Ship the frame-critique pass (064-03) gated / kill-criterion-watched, not as
  the headline.** 2/4 clean on this corpus, and §A2's own caveat (same-model
  shared blind spots) applies. The existing slice design *already* matches this:
  064-03 is `frame_review`-gated and **default-off**, and 064-04's derived
  trigger fires rarely — so no slice rework is needed, only a priority/emphasis
  note carried into reconciliation. Watch ADR-0020's "kills the frame-critique
  pass" criterion post-ship via 056/routing instrumentation.

**Decision: `spec 064-02 unblocked (go)`** — with the grounding-first emphasis
recorded above.
