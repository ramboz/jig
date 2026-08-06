---
status: Accepted
dependencies: [docs/specs/071-design-review-pass/spec.md, docs/decisions/adr-0022-pluggable-oracle-boundary.md]
last_verified: 2026-08-03
frame_review: true
---

# ADR-0049: Design-fidelity work routes through the spec spine (originating or new), not a new lifecycle vehicle

## Status

Accepted (2026-08-03)

Records the routing ruling for [issue #179](https://github.com/ramboz/jig/issues/179).
Implemented by [spec 104](../specs/104-design-fidelity-routing/spec.md).

## Context

Design feedback — "the built screen doesn't match the mockup" — had no clean
lifecycle home. Triage repeatedly stalled on "is this a bug or a spec?" and
**neither fit**. Issue #179 named three distinct work-shapes; jig has vehicles
for only two:

| What happened | Malfunction? | Vehicle today |
|---|---|---|
| Built to do/show X, doesn't do X | Yes | `bug-fix` |
| Built, works, but hasn't reached the agreed mockup | **No** | **— none —** |
| We now want a *different* target than the mockup | No | `spec-workflow` (refinement) |

The middle row is the reported hole. A visual gap against an agreed mockup is
**not a defect** (nothing malfunctions — the screen works) and **not a fresh
idea** (the target did not change). Forced into either existing frame, both
mislead:

- **As a bug** → `bug-fix` demands a root cause and a regression test. There is
  no defect mechanism to root-cause ("the pixels weren't finished" is not one),
  and a regression test for "looks right" is the wrong instrument. The confusion
  is not hypothetical: `bug-fix`'s gnarly tier already lists **"design-gap"** as
  a bug tier that "may escalate to a spec" (`skills/bug-fix/SKILL.md:71`,
  verified) — an active mis-routing surface.
- **As a fresh refinement** → implies the target changed when it didn't. It
  hides that this is *the same agreed goal, not yet reached*.

Two forces make the routing question worth a durable ruling rather than
per-complaint re-litigation:

1. The gap **feels** like a missing category, but it is better explained as an
   **unmet acceptance criterion** on the slice that built the screen: mockup
   fidelity *is* an AC of that slice; if it were written as a checkable AC, the
   slice was never `DONE`.
2. The fidelity AC is **non-deterministic** ("looks like the mockup" is a judge
   call, not an assertion), which is why authors avoid writing it as an AC and it
   ends up living only in a picture.

**The gap arrives in two provenances, and the ruling must serve both.** (a) It is
*discovered under an existing jig spec* — a slice built the screen, its written
ACs passed, but fidelity was never a written AC. (b) It arrives *mockup-first
with no jig spec at all* — the reported trigger for #179 was exactly this: a
mockup produced in Claude design was handed to Claude Code, which rebuilt the
screen for Android; there was **no originating slice** to continue. An early
frame-critique of this ADR flagged that an initial "route to the *originating*
spec" framing silently assumed provenance (a) and left provenance (b) — the very
case that provoked the issue — with a dead-end route. The decision below is
written to route both.

Both forces already have jig/servo rails:

- **[spec 071](../specs/071-design-review-pass/spec.md) — the attest-only
  `design_review` review pass** (a read-only reviewer attests an external
  design-fidelity eval's frozen verdict at `REVIEWED` without re-deriving the
  score). The load-bearing fact is that the pass exists **in code**: the deriver
  `slice_needs_design_review` is at `skills/spec-workflow/workflow.py:330`
  (verified this session). Its lifecycle state carries a known internal drift —
  spec 071's frontmatter and slice-01 file both read `DONE`, but the overview
  Slices table still shows `071-01` `IN_PROGRESS`; this ADR relies on the code
  rail, not on 071's headline status.
- **servo `design-eval` (verified — `servo/skills/design-eval/SKILL.md`)** — the
  non-deterministic oracle: it screenshots the running app against the reference,
  scores fidelity with a pinned, n-sampled vision judge, and installs a
  thresholded `score_design_fidelity` component; servo's agent-loop iterates the
  UI toward the mockup until the composite clears the threshold.

## Decision Options Considered

### Option A: A new "design-fidelity" work-type / parallel lifecycle vehicle (issue option 3)
A third top-level work type alongside bug-fix and spec-workflow, whose
definition-of-done is the eval threshold.
- **Pros:** gives the middle-row work an explicit named home and a finish line;
  makes the category visible.
- **Cons:** duplicates the spec spine for **zero new capability** — a spec slice
  carrying a `design_review` gate backed by a servo `design-eval` threshold
  already *is* exactly this. Adds a parallel lifecycle to build, gate, document,
  and maintain. Walks straight into the **"ahead of demand"** critique that
  PARKED [ADR-0022](./adr-0022-pluggable-oracle-boundary.md): building the
  vehicle before a real consumer strains it.

### Option B: Keep routing design gaps through `bug-fix` (status quo)
Treat "doesn't match the mockup" as the existing gnarly "design-gap" bug tier.
- **Pros:** no new machinery; a tier already exists.
- **Cons:** the bug lifecycle actively misfits — `bug-fix` gates on a root cause
  (`→ ROOT_CAUSED` needs ≥2 hypotheses + evidence) and a red→green regression
  test (`→ FIXING`/`→ REVIEWED`), neither of which a pure visual gap can honestly
  produce. Pure friction; the tier's presence is itself the reported confusion.

### Option C (chosen): Design-fidelity is spec-shaped work, carried on the spec spine
Name the middle row as an **unmet, non-deterministic fidelity AC** and route it
through spec-workflow — the *originating* spec when one exists, a *new* spec when
one doesn't — never `bug-fix`. Pair it with a triage test and lean on the
existing 071 + servo rails for the done-condition.
- **Pros:** no new lifecycle vehicle; reuses the spec spine that already models
  "unfinished work toward an agreed target." The non-determinism is handled the
  way 071 + servo already handle it — convert the fuzzy AC into a thresholded
  eval, and "iterate until it stabilizes" gets a real stopping condition. It
  serves **both provenances**: a gap discovered under an existing spec continues
  that spec (or a follow-up slice under it); a mockup-first rebuild with no spec
  opens a new one with the mockup as its design-value ACs. Either way it is
  spec-workflow, so no new machinery is paid for.
- **Cons:** relies on authors recognizing visual work needs a fidelity AC — a
  judgment jig can nudge but cannot fully mechanize (see Kill criteria). For
  provenance (b) the "unmet AC on the *originating* slice" story is a framing, not
  a mechanism — operationally it is ordinary greenfield spec-workflow (which is
  the point: still no new vehicle). Does not give the category a single named CLI
  verb.

## Recommended Decision

**Adopt Option C.** Design-fidelity work — "built, works, but not yet at the
agreed visual target" — is **spec-shaped work carried on the spec spine**, not a
new lifecycle vehicle and not a defect. Concretely:

1. **Routing — to a spec, originating or new.** A pure visual gap against an
   agreed mockup routes through spec-workflow, not `bug-fix`:
   - **An originating spec exists** (the gap surfaced under a spec whose slice
     built the screen) → continue that slice if still open, or open a follow-up
     slice **under the same spec**, carrying the mockup forward as design-value
     ACs.
   - **No originating spec exists** (a mockup-first / cross-platform rebuild that
     never entered spec-workflow — the #179 trigger) → open a **new spec** via
     spec-workflow's greenfield path, with the mockup + its extracted design
     values as the spec's design-value ACs. This is ordinary spec-workflow, not a
     new vehicle — which is the whole point of rejecting Option A.
2. **Triage test (a judgment, not a keyword gate).** A design issue is `bug-fix`
   only when the UI **malfunctions** — a control that looks active but isn't, a
   layout that overlaps so content is unreadable. A pure visual gap against an
   agreed mockup is **fidelity work on the spec spine** (per §1). **Tie-breaker
   for the ambiguous case** ("looks broken, but maybe just mis-styled" — e.g. a
   control that mis-signals its state, or overlap that only *might* block
   interaction): a quick behavioral check decides — does it actually *do* the
   wrong thing? An ambiguous-but-functional gap (it behaves correctly, only looks
   off) defaults to the **spine**, not `bug-fix`; reserve `bug-fix` for a
   confirmed behavioral malfunction.
3. **Fidelity vs. refinement — the operative test is whether the visual *target*
   changed.** If the mockup is still the agreed target and the build simply hasn't
   reached it, that is **fidelity** work: carry the *existing* mockup forward as
   the AC — do not re-decide the target. If we now want a *different* look than
   the mockup, that is a genuine **refinement** (a new target), authored as such.
   The distinction is not "different lifecycle" — both are spec slices — it is
   "don't re-litigate an unchanged target, and don't smuggle a target change in
   as mere unfinished work."
4. **Done-condition for the non-deterministic AC.** Where fidelity must gate,
   the fuzzy AC is converted into a servo `design-eval` threshold and attested
   through spec 071's `design_review` pass. The threshold **is** the AC; the
   iterate-until-it-passes loop is servo's.
5. **Division of labor.** **jig owns** routing (this ruling), the authoring
   nudge (design values → checkable ACs; flag `design_review` and point at the
   servo rail), and the attest gate (071). **servo owns** the non-deterministic
   measurement (`design-eval`) and the iterate-until-pass loop (agent-loop). jig
   never re-derives the score — the ADR-0022 attest-only boundary holds.

**Graduated, not mandatory.** Not every screen earns a frozen `design-eval`
(Playwright + config + a tuned judge/threshold is real cost). Low-stakes visual
polish is served by design-values-in-ACs plus attest-by-eyeball; the servo eval +
`design_review` gate is reserved for screens where fidelity must be a hard gate.
jig *offers* the rail; it never forces servo.

## Consequences

**Becomes easier:**
- Triaging a design complaint: one explicit ruling replaces per-complaint
  re-litigation of bug-vs-spec.
- Closing the loop on "doesn't match the mockup" — it has a home (the originating
  spec) and, when it matters, a measurable finish line (the eval threshold).

**Becomes harder:**
- Nothing net-new to maintain: this adds a ruling and an authoring nudge, not a
  lifecycle vehicle. The cost is the discipline of writing fidelity as an AC up
  front — which is the point.

**Follow-on:**
- `bug-fix`'s "design-gap" tier wording is disambiguated (spec 104-01): a design
  **malfunction** stays a bug; a pure visual **fidelity gap** routes to the spec
  spine, and the triage rule carries the no-originating-spec branch (→ new spec).
- spec-workflow gains an authoring nudge (spec 104-02): when a slice has visual
  design, extract the design values into ACs and, when fidelity should gate, flag
  `design_review` + wire a servo `design-eval`.

## Assumptions

- **servo `design-eval` is a separate plugin and may be absent in a target
  project.** Its presence is not guaranteed — asserted against
  `servo/skills/design-eval/SKILL.md` in a sibling repo, unverifiable from this
  worktree. This is *why* the rail is graduated and opt-in (see "Graduated, not
  mandatory"): the hard-gate path presupposes servo; the low-stakes path
  (design-values-in-ACs + attest-by-eyeball) needs neither servo nor a key. jig
  never mandates servo, so an absent eval degrades to eyeball attestation, not a
  broken route.
- The other cited rails were read this session, not assumed: the `design_review`
  deriver at `skills/spec-workflow/workflow.py:330`; the `bug-fix` "design-gap"
  tier at `skills/bug-fix/SKILL.md:71`. spec 071's headline `DONE` carries a known
  overview-table drift (noted in Context) — this ADR relies on the code rail, so
  the drift is not load-bearing here.

## Kill criteria

- **The spec spine genuinely can't carry the work** — a real case where neither
  "continue the originating spec" nor "open a new spec with the mockup as ACs"
  fits (the #179 rebuild case is *handled* by the new-spec branch, so it is not
  such a case) — then Option A (a dedicated vehicle) earns its demand trigger and
  this ruling is revisited.
- **The authoring nudge proves unreachable in practice** — design gaps keep
  arriving post-`DONE` with no fidelity AC despite the nudge — then a mechanical
  detector (or a harder gate tying visual-work signals to the `design_review`
  flag) is warranted over prose guidance.

## Open questions

None. The mechanism split (routing ruling + authoring nudge) is settled by spec
104; the tight servo exit-code binding stays PARKED under ADR-0022 and is out of
scope here.
