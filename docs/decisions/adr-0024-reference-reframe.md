---
dependencies: [docs/decisions/adr-0023-lifecycle-family-spine.md, docs/decisions/adr-0020-spec-frame-hardening.md, docs/decisions/adr-0010-amendment-scope-records-vs-live-prose.md, docs/decisions/adr-0019-refactor-workflow.md]
last_verified: 2026-06-09
frame_review: true
---

# ADR-0024: Reframe on a load-bearing reference shift — a lightweight correction capability over the spine

## Status

Proposed (2026-06-09)

## Context

jig is built to keep work **consistent with prior decisions**. Every spec and
ADR is a durable record; new work reads the accepted corpus as authoritative and
builds on it. That is jig's core strength — and its blind spot when a
**load-bearing premise of the project changes from outside the system.**

The motivating failure: a team scaffolded an Android app with jig and let the
agent choose the UI. After a few slices landed they disliked the result,
generated a proper design with a separate tool, and dropped that design artifact
into the repo intending to retrofit the project onto it. jig and the agent kept
building on the **old** design and only patched at the edges. Several specs,
ADRs, and a backlog of future-work drafts had already encoded the old design as
settled truth; the new artifact entered as an **inert file with no authority**,
so the consistency machinery faithfully carried the dead premise forward.

The pattern generalizes well beyond design. A **load-bearing reference** is any
authoritative external input the corpus is premised on: a design system, a
test-infrastructure choice, a vendor / API contract, a compliance regime, a
target platform, **a product-positioning / strategic-vision shift** (the n=2
servo case — §3).

When such a reference moves, **two distinct things fail — and they are not the
same gap:**

- **Correction.** Once someone *recognizes* the shift, there is no operation that
  *re-baselines* the corpus. `adr.py supersede` is 1:1 and decision-scoped;
  `migrate` brings a project *into* jig; `jig:refactor`
  ([ADR-0019](./adr-0019-refactor-workflow.md)) preserves behaviour. With no
  re-baseline primitive, the agent does the locally-rational thing — patch at the
  edges. That is the motivating failure exactly: the team *intended* to retrofit
  onto the new design, but jig/the agent kept building on the old one.
  **This is the gap this ADR closes.**
- **Noticing.** Silent drift — a reference moving without anyone flagging it —
  goes unsurfaced. This is a *different* gap: a user who can *invoke* a command
  has, by definition, already noticed. jig's `stale` notion tracks time /
  dependency aging, not premise invalidation. The motivating case did **not**
  actually hit this (the team noticed); the general failure mode includes it.

One tempting shortcut does **not** work, and the reason is instructive. You might
detect a shift by scanning each artifact's declared `## Assumptions` for conflict
with the new reference. But the `## Assumptions` ledger is **risk-gated**
([ADR-0020](./adr-0020-spec-frame-hardening.md)): it logs only *unverified,
contested* assumptions worth an adversarial pre-implementation read, default-off
on the common case. **A settled premise everyone agreed on is the opposite of a
contested assumption — so it is never in the ledger.** The dead design that bit
the motivating team was *settled truth* in decisions and prose, not a flagged
risk. Settled premises are invisible to the ledger **for the same reason they
silently steer the model: they are unquestioned ground.** So systematic
blast-radius detection is not a cheap ledger trick — it is a genuine project-scope
corpus read. This ADR therefore **parks** detection (see Scope) and ships the
cheaper, higher-leverage half — correction — first.

A reference shift is **not** a member of ADR-0019's behaviour-change taxonomy
(add new / restore correct / restructure-preserving-behaviour). It sits one level
up: the *premise* moves, then *spawns* behaviour-change work that flows through
the lifecycles already in place. So the need is not a fourth backbone; it is a
**capability that elevates the new reference to authoritative and routes the
fallout into the existing ADR and spec lifecycles** — exactly
[ADR-0023](./adr-0023-lifecycle-family-spine.md) §4's "consumes the spine
substrate without its own state machine" category.

Three forces bound the design:

- **The model won't self-trigger a pivot, and shouldn't.** Abandoning a premise
  is a direction call the human owns. The capability makes the re-baselining
  *expressible* — it does not decide it.
- **Don't build the heavy version ahead of demand.** There is one real case
  (n=1). jig's own discipline ([ADR-0002](./adr-0002-contracts-stays-deferred.md)
  / [ADR-0003](./adr-0003-extract-find-slice-section.md) rule-of-three; ADR-0019's
  "extract on demand"; [ADR-0022](./adr-0022-pluggable-oracle-boundary.md)'s
  parked oracle) says: ship the cheap, high-leverage half and **park** systematic
  detection behind explicit triggers.
- **Reuse where it's real; build nothing speculative.** Correction rides
  `adr.py`, `workflow.py`, and model judgment — no detection engine, no
  corpus-walking helper, no `references:` tagging in the recommended build (all
  parked).

## Decision Options Considered

### Option A: Nudge only

A reminder to "consider whether the premise moved," with no re-baseline operation.

- **Pros:** zero machinery.
- **Cons:** leaves the *correction* gap wide open — the new reference stays inert
  beyond a prompt, and the agent still patches. This is closest to what already
  failed.

### Option B: A new gated lifecycle member + auto-execution

`reframe` as a fourth ADR-0023 member with its own `transition` / states / gates,
plus a `reframe.py` that batch-supersedes and auto-generates retrofit work.

- **Pros:** most powerful; one coordinated, atomic re-baselining.
- **Cons:** premature at n=1. A reframe has no distinct *intake→DONE backbone*, so
  a state machine fights ADR-0023 §4; a concrete `reframe.py transition` would be
  the **third** implementation and mis-trigger the §3 `_common/lifecycle.py`
  extraction off a speculative member. And B needs **everything the cheaper option
  needs plus** a lifecycle and an execution engine. Heavy, and the wrong shape.

### Option C: A lightweight `/jig:reframe` correction skill + a best-effort nudge; detection parked (recommended)

A judgment-only `/jig:reframe` skill that, given a new reference, reads the corpus
and drafts the **keystone reframe-ADR** + **retrofit spec drafts** + per-artifact
**dispositions**; a competent session executes through the existing ADR/spec
lifecycles. Plus a best-effort, practice-backed **noticing nudge**. **Systematic
blast-radius detection** (project-scope corpus read / `references:` tagging /
spec 024-02 helper) is **parked behind triggers**.

- **Pros:** closes the *correction* gap — the part that actually bit — with the
  least machinery (a judgment skill + existing lifecycles; nothing clever to
  mis-build); structurally correct (no backbone → no state machine, no extraction
  trigger); honest about *noticing* (soft nudge + practice now, systematic
  detection parked); the cheapest path to value at n=1.
- **Cons:** detection is the session's read, so thoroughness rests on the session
  (the un-park trigger is the backstop); the nudge is best-effort, not a reliable
  silent-drift detector (parked); execution leans on session competence.

## Recommended Decision

**Option C (lightweight).** Reframe is a *correction capability over the spine*
(ADR-0023 §4): a judgment skill that re-baselines once a shift is recognized, plus
a best-effort nudge. Systematic detection is parked with triggers (§7).

### 1. The organizing concept — a load-bearing reference

A **load-bearing reference** is a named authoritative external input the corpus
depends on (design system, test infra, vendor / API contract, compliance regime,
target platform, product-positioning / strategic-vision shift). A **reframe**
re-anchors the corpus to one that has *moved*.
This abstraction covers every motivating case and is what makes reframe distinct
from refactor (which preserves behaviour against a *fixed* reference).

### 2. The correction skill — `/jig:reframe`

`/jig:reframe` is a dedicated, **judgment-only** skill (its own SKILL.md, for
visibility — a reference shift is a deliberate, named operation a user reaches
for). Given a new reference, it **reads the corpus (decisions + prose) against
it** and drafts the re-baselining artifacts (§3). The "detection" here is the
model's read *as part of drafting* — **not** a built engine, **not** a
`## Assumptions` sweep (risk-gated; structurally blind to settled premises — see
Context), **not** a corpus-walking helper (parked, §7). There is **no `.py`
helper**: lookups and drafting are model judgment over the existing `adr.py` /
`workflow.py` scaffolding.

Its value over "just ask the agent to retrofit" is three concrete things the
motivating failure lacked: **(a)** a *named operation*, so the agent
re-baselines instead of patching; **(b)** the *keystone ADR*, which elevates the
new reference from an inert file to an authoritative decision; **(c)** the
*disposition discipline*, which forces every affected artifact to a deliberate
fate instead of silent omission.

But (a)–(c) are necessary, not sufficient. The skill's correctness rests on the
**completeness of that corpus read** — and finding every artifact that encodes a
*settled* premise is the hard part the systematic engine is parked for (§7). The
minimal version does **not** pretend to solve enumeration; it **surfaces** it: the
skill states *what it scanned and how*, and the keystone manifest carries an
explicit **coverage statement** (§3) so the human reviewing the reframe confronts
"did we catch everything?" deliberately — turning the silent omission that caused
the motivating failure into a checked, human-gated decision. This is the
load-bearing risk, owned (Assumptions §4), not assumed away.

### 3. The artifacts it drafts — keystone ADR + retrofit specs + dispositions

- **The keystone reframe-ADR** (rides the existing ADR lifecycle, so it is
  frame-critique-gated at `accept` — *probed:* `adr.py`'s `_gate_frame_critique()`
  refuses the Proposed→Accepted flip without a passing verdict): declares the new
  reference *authoritative as of `<date>`*, supersedes the old premise, and
  carries the **re-baselining manifest** — a table of every affected artifact with
  an explicit disposition (no `TBD`), **plus a coverage statement**: what corpus
  was scanned, by what method, and the residual uncertainty. Coverage is
  *asserted, not assumed* — and confirmed by the human at `accept` (the
  frame-critique gate is the natural checkpoint for "did the read miss anything?").
- **Retrofit spec draft(s)** (ride `spec-workflow`): one slice per `retrofit`
  disposition, each goaled "bring `<artifact/code>` in line with `<reference>`."
  Their `## Assumptions` cite the new reference so future frame-critique is
  anchored correctly.
- **Emergent-work section** *(added 2026-06-27 from the n=2 servo reframe)*: a
  reframe can *spawn* net-new forward specs/ADRs the new reference **reveals** —
  work that did not exist before and is distinct from `retrofit` (which fixes
  *existing* code). The keystone manifest records these in a separate
  `## Emergent work` section, **not** forced into a per-artifact disposition row
  (a disposition is the fate of an *already-affected* artifact; spawned work has
  no prior artifact to dispose of). The servo reframe minted 3 ADRs + 4 specs
  this way.

Per-artifact **dispositions**, each routing to an operation that already exists:

| Disposition | Meaning | Routes to |
|---|---|---|
| `reaffirm` | premise survives the new reference | refresh `last_verified` + note the reframe |
| `amend` | closed record, still valid, needs a pointer | `## Amendments` ([ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md)) |
| `supersede` | decision now wrong | `adr.py supersede` / superseding spec |
| `retire-draft` | future-work on the dead premise | DEFERRED or discard — **do first; drafts mint dead-premise work** |
| `retrofit` | shipped code must change | a slice in the retrofit spec |
| `rewrite` *(added 2026-06-27, n=2)* | **live, non-record prose** whose framing must change — not a closed record (`amend`), a decision (`supersede`), or code (`retrofit`) | rewrite in place, citing the keystone ADR |

The `rewrite` disposition closes a gap the n=2 servo reframe exposed:
a *documentation-shaped* reframe is mostly live-prose rewrites (vision /
architecture / README), which the original five dispositions did not fit.

### 4. The noticing nudge — best-effort, not a detector

Closing the *noticing* gap fully requires systematic detection (parked, §7). The
cheap version ships **defense-in-depth, not a detector**: a standing practice in
`docs/workflow.md` ("bringing in a new load-bearing reference — design, vendor,
test-infra — run `/jig:reframe` before building on it") plus a soft, best-effort
reminder. It *reduces* silent drift; a *reliable* automated trigger needs
`references:` tagging or detection, both parked. This matches jig's other soft
nudges (context-check, team-check) and ADR-0011 / ADR-0013's defense-in-depth
posture: jig recommends, the human acts.

### 5. Why a capability, not a member

A reframe has **no native gated transitions of its own.** Its arc (recognize →
decide dispositions → execute) *orchestrates* existing lifecycles: every gate it
relies on belongs to the ADR or spec lifecycle it spawns (frame-critique on the
keystone ADR; the review passes on the retrofit specs). Under ADR-0023 §4 that
places reframe in the **"consumes the spine substrate, not a member"** category.
It adds **no concrete `transition`** and does **not** advance the §3 rule-of-three
count. Shipping as its own skill is a *user-facing-surface* choice, not a
lifecycle one — a skill is not a state machine.

### 6. Execution is session-driven by design

A competent session, handed the accepted keystone ADR + retrofit spec drafts,
executes the reframe with existing tools. The capability *drafts*; the session
*executes*. Deliberate n=1 scope.

### 7. Parked work and its triggers

**Parked — systematic blast-radius detection:** a project-scope agentic corpus
read against the reference (optionally `references:` frontmatter tagging for
determinism, sharing the deferred **spec 024-02** corpus-walking helper).
**Un-park when ANY of:**

- **T1 — the human-checked coverage proves the manual read under-catches:** on a
  real reframe, the §3 coverage statement (confirmed at `accept`) reveals the
  model's single-pass read materially missed artifacts. This is gated at the
  **first** reframe — not deferred to a second miss — because at n=1 the first use
  is the only evidence the manual read suffices; a demonstrated under-catch pulls
  in the systematic engine.
- **T2 — the corpus outgrows a reliable single-pass read:** the spec/ADR corpus is
  large enough that an agentic read can't reliably or affordably cover it in one
  pass (the [spec 055](../specs/055-context-cost-discipline/spec.md) context-cost /
  dumb-zone threshold) — a systematic walker + `references:` index then earns its
  keep.
- **T3 — a second consumer pulls the same infrastructure:** 024-02 (project-scope
  analyze) or another feature independently needs corpus-walking / `references:`
  tagging — build it once, demand-pulled, and reframe adopts it.

**Graduation to a gated lifecycle member (Option B)** is a separate, higher bar:
if reframe-execution repeatedly drifts *even with good drafts in hand* (the
correction recipe itself is insufficient), propose reframe as a full ADR-0023
member (distinct-backbone + C1–C7). If it is the third concrete `transition`, it
also triggers the §3 extraction. Not before.

## Consequences

**Becomes easier:**

- The *correction* gap closes cheaply — a named re-baseline operation replaces
  edge-patching; the new reference becomes authoritative via the keystone ADR.
- Future-work drafts on a dead premise are surfaced and retired *first*.
- Least machinery: a judgment skill + existing lifecycles, nothing new to build
  or maintain.

**Becomes harder:**

- Detection thoroughness rests on the session's read (T1 is the backstop); a
  large or sprawling corpus may be under-covered until detection is un-parked.
- *Noticing* is only partially addressed — the nudge is best-effort, not a
  silent-drift detector; that half stays open until T-triggers fire.
- Execution quality rests on the session, not enforced gates.

**Neutral:** no detection engine, no corpus helper, no `references:` tagging, no
`.py` for reframe; analyze is untouched; no state machine, no `transition`, no
extraction trigger.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **ADR-0023 §4 admits a "capability over the lifecycles" that is not a member.**
  *Grounded:* §4 read in full.
- **`adr.py accept` enforces the frame-critique gate.** *Probed:*
  `_gate_frame_critique()` refuses the Proposed→Accepted flip without a passing
  verdict (bypass `JIG_REVIEW_EVIDENCE_GATE=0`, gated on truthy `frame_review`).
- **Detection must NOT be built on the `## Assumptions` ledger.** *Grounded:* the
  ledger is risk-gated (ADR-0020 + this ADR's own scaffold template) and
  structurally excludes settled premises — the exact thing a reframe must catch.
  Recorded here so it is not re-proposed; it is why detection is parked, not
  faked.
- **The binding risk is enumeration completeness over *settled* ground — and it
  is owned, not assumed.** A reframe re-baselines correctly only if the corpus
  read finds the artifacts encoding the dead premise; but settled premises are
  *invisible* (Context), so a single-pass model read may miss some — and a
  faithfully-executed but *partial* manifest would reproduce the motivating
  failure under a keystone ADR. The minimal version therefore does **not** assume
  the read is complete (which would mis-diagnose the failure as a mere
  vocabulary/authority gap). It **surfaces** coverage: the manifest's coverage
  statement (§3) is human-confirmed at `accept`, and a demonstrated under-catch
  un-parks the systematic engine at the *first* reframe (T1). The other pieces —
  named operation, keystone authority, disposition discipline — are grounded
  (model judgment over existing lifecycles); the nudge is best-effort (*degrades*,
  not *misdirects*). The residual — a human who rubber-stamps a weak coverage
  statement — is a real but **bounded and visible** risk, not a silent one.

## Kill criteria

- If reframes drift *even with good drafts in hand* → the correction recipe is
  insufficient → graduate to a gated lifecycle member (Option B).
- If a reframe's human-checked coverage shows the manual read **under-catches**
  (T1) → un-park systematic detection.
- If real reframes **always** decompose to a single `adr supersede` + one spec →
  the capability is over-built → demote to a documented recipe in
  `docs/workflow.md`.

## Scope

**In scope:** the load-bearing-reference abstraction; a dedicated, judgment-only
**`/jig:reframe`** correction skill (reads the corpus against a reference; drafts
the keystone reframe-ADR + retrofit specs + dispositions); the keystone-ADR shape
(with the re-baselining manifest); the retrofit spec-draft shape; the disposition
vocabulary; a best-effort, practice-backed **noticing nudge**; positioning as a
capability over the spine.

**Parked (with triggers T1/T2/T3, §7):** systematic blast-radius detection — a
project-scope agentic corpus read, `references:` frontmatter tagging, and the
spec 024-02 corpus-walking helper.

**Deferred (named, no slice):** auto-scaffolding of the drafts (vs draft-on-invoke
only); graduation to a gated lifecycle member (Option B).

**Out of scope / rejected on principle:** detection via the `## Assumptions`
ledger (risk-gated; blind to settled premises); heavy auto-execution; changes to
`/jig:analyze`'s behaviour.

## Relationship to other decisions

- **[ADR-0023](./adr-0023-lifecycle-family-spine.md)** §4 — supplies the
  "capability over the lifecycles, not a member" category; reframe consumes C1 /
  C3 / C5 substrate through the ADR + specs it spawns, adds no concrete
  `transition`.
- **[ADR-0020](./adr-0020-spec-frame-hardening.md)** — the `## Assumptions` ledger
  is *risk-gated*, which is precisely why detection cannot sweep it for settled
  premises; reframe is frame-critique's project-scope counterpart in *spirit*, not
  by reusing the ledger as an index.
- **spec 024 (`/jig:analyze`) / 024-02** — reframe does **not** build the
  project-scope corpus helper now (parked, §7); if detection is un-parked (T3), it
  builds/adopts 024-02. Reuse of analyze is *conceptual* (the six-category model),
  not code — analyze is judgment-only.
- **[ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md)** — the
  `amend` disposition.
- **[ADR-0019](./adr-0019-refactor-workflow.md) /
  [ADR-0016](./adr-0016-bug-fix-lifecycle.md)** — the behaviour-change taxonomy
  reframe is explicitly *not* part of; reframe spawns work into them.
- **[ADR-0014](./adr-0014-review-evidence-model.md)** — the keystone ADR and
  retrofit specs inherit its gates for free.
- **[ADR-0002](./adr-0002-contracts-stays-deferred.md) /
  [ADR-0003](./adr-0003-extract-find-slice-section.md)** — cheap-now,
  heavier-on-demand; the T-triggers are the rule-of-three applied to detection.

## Open questions

- **Where does the re-baselining manifest live — inline in the keystone ADR or a
  sibling file?** Lean: inline, unless a blast radius is large enough to warrant
  its own file.
- **Does `/jig:reframe` draft the artifacts on invocation, or also offer a
  report-only mode?** Lean: draft-on-invoke (the drafts are the point); a
  read-only preview is a cheap add if wanted.
- **Resolved (this ADR):** skill, not an analyze-mode (analyze has no reusable
  code); judgment-only, no `.py`; detection *parked*, and when un-parked it is a
  project-scope corpus read, **never** a `## Assumptions` sweep.
