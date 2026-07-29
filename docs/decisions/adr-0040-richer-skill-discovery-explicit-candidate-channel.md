---
status: Accepted
dependencies: [adr-0039]
last_verified: 2026-07-28
frame_review: true
---

# ADR-0040: Explicit candidate channel for richer-skill discovery

## Status

Accepted (2026-07-28)
Supersedes ADR-0039

Supersedes [ADR-0039](adr-0039-richer-skill-discovery.md) on three points
(D1–D3 below). **D3 additionally makes explicit — rather than silently reversing
— ADR-0039's recall/precision division: `candidates` prints the full recall set,
tiered, so precision continues to govern the anomaly and never the pick.**
Everything else in ADR-0039 — the problem framing, the
config-first precedence chain, the never-defer set, the read-only-reviewer
constraint, and the auditability-not-enforcement posture — is **carried forward
unchanged** and remains the governing rationale.

## Context

[ADR-0039](adr-0039-richer-skill-discovery.md) was Accepted 2026-07-27 and
[spec 096](../specs/096-richer-skill-discovery/spec.md) decomposed it into five
slices. Running the spec through the frame-critique gate — the pass that runs
**before** implementation precisely to catch a wrong frame while it is cheap —
returned `needs-changes` on **all five slices**, and three of the findings were
verified directly against this tree rather than taken on the reviewers' word.
The evidence is recorded at
[`docs/specs/096-richer-skill-discovery/reviews/`](../specs/096-richer-skill-discovery/reviews/).

Three load-bearing premises of ADR-0039 are false or unsupported:

**1. "The five extensible passes are all `review.py` prompt-builders."**
`review.py` defines builders for pr-review (:617), arch-review (:755),
code-health (:858), and design-review (:1094) — and **no security builder at
all**; `subagent-type` (:1724) enumerates no security mode.
`skills/security-review/SKILL.md:71-72` states the mechanism outright: "The
deferral is a **router hint, not a filesystem probe**."
`skills/bug-fix/SKILL.md:232` states there is "**no** `review.py pr-review`
call" for a bug. So a `scaffold.json` key consumed by `review.py` reaches four
builders, not five — and only three of those are semantically extensible (D1
excludes `design_review`). The remaining surfaces could only honor it through
orchestrator prose — the inert-prose class ADR-0039 §3 rule 2 itself forbids,
citing spec 031's dead option (a).

**2. "A scaffolded jig baseline is indistinguishable *by path* from a richer
skill."** This was inherited from a stale
[refinement-todo](../refinement-todo.md) entry **and from live prose in shipped
code** — `review.py:565-569`, `detect_richer_skill`'s own docstring, states that
a project-scope skill "may be jig's OWN baseline … indistinguishable by path".
Per [ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md) that docstring
is live prose and must be corrected **inline** when D2 lands, or the false
premise is re-inherited by the next reader of `review.py`. (A *second* inline
correction is owed when D1 lands: `build_code_health_review_prompt`'s docstring
at `review.py:887-890` says richer-skill deferral is "intentionally NOT wired
here … there is no established 'richer code-health reviewer' skill category" —
stale live prose, since `code-health/SKILL.md:12-14` advertises exactly that
category deferral and D1 *includes* `code_health`. Correct it inline, same
policy.) The path-indistinguishability claim is false:
`skills/scaffold-init/scaffold.py:742` writes every user-facing skill to
`.claude/skills/jig-<name>/`. The invariant the prefix test actually depends on
is **"any unprefixed project-scope skill dir carries no `SKILL.md`"** — which
holds for both unprefixed writers: the `_`-prefixed shared-module copy at :726,
and the Codex-mode logical-name alias at :1485-1489, which passes
`include_skill_md=False`. Neither is a discovery candidate. So the safe rule is
not "exclude `jig-*`" alone but "a project-scope candidate must carry a
`SKILL.md`, and `jig-`-prefixed ones are jig's own" — `migrate.py:287` already
ships `entry.name.startswith("jig-")` as exactly this discriminator. The premise
that justified a new cross-cutting frontmatter marker does not hold.

**3. "The orchestrator selects from the enumerated candidate set."** Spec 096-03
builds an enumerator but wires it to no consumer, while ADR-0039's own Option D
rationale rests on the *ambient* surface — "costs ~nothing in orchestrator
context (spec 057) **since the descriptions are already loaded**" (ADR-0039
:159-161). Those are two different substrates, and the difference is
load-bearing: ADR-0039 :296-307 requires the anomaly to fire only against "the
candidate set the orchestrator was **actually shown and declined**", which an
ambient pick cannot produce. It also requires that "**matcher precision
therefore still matters**" — a precision matcher the spec's decomposition
allocates to no slice.

The through-line: ADR-0039 chose a mechanism whose observability requirement its
own substrate cannot satisfy, and whose Codex viability it then had to gate on
an unverified premise about another vendor's prompt assembly (OQ6).

## Decision Options Considered

### Option A: Amend ADR-0039 in place

- **Pros:** Cheapest; keeps one document as the single reference for the
  feature; the three changes could be read as open-question resolutions.
- **Cons:** These are **decision-content** changes, not OQ resolutions — the
  extensible set, the exclusion mechanism, and the selection substrate are all
  choices with rejected alternatives. [ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md)
  reserves in-place amendment for records and live prose, and requires a new ADR
  when the decision itself changes. Amending would also erase the reasoning
  trail that a frame-critique caught this pre-implementation, which is the most
  reusable thing here.

### Option B: Supersede ADR-0039 wholesale and re-decide the feature

- **Pros:** One clean current document.
- **Cons:** Disproportionate and wasteful. ADR-0039's problem framing,
  precedence chain, never-defer set, and honesty notes survived critique intact
  — three of its own claims were already withdrawn under an earlier
  frame-critique, so the document is battle-tested where it isn't being changed.
  Re-deciding settled parts invites re-litigating them.

### Option C: Narrow superseding ADR on the three falsified axes (recommended)

- **Pros:** Matches the actual scope of what changed. Keeps ADR-0039 readable as
  the governing rationale and this ADR as the delta, with an explicit
  carry-forward clause. Preserves the evidence trail.
- **Cons:** A reader must hold two documents. Mitigated by the carry-forward
  clause above and a `Superseded-by` pointer on ADR-0039.

## Recommended Decision

**Option C.** Three decisions follow.

### D1 — The extensible set is three passes; security and bug-fix become named follow-up work, and design-review joins the never-defer set

`review.<category>_skill` governs **`pr_review`, `arch_review`, and
`code_health`** — the categories that both have a real `review.py`
prompt-builder *and* are semantically extensible, where config resolution is
mechanized end-to-end and the applied skill can actually be recorded.

**`design_review` is explicitly excluded, correcting an error inherited from
ADR-0039 §1.** A builder-exists test is *mechanical*; ADR-0039 §2's membership
test is *semantic* — never-defer for passes whose value **is** being
jig-canonical. `design_review` fails the semantic test, and its own shipped
builder says so (`review.py:1114-1116`): "**NO** richer-skill detection (unlike
pr-review / arch-review): there is no established external 'design-review' skill
category to defer to — this pass attests jig's OWN eval evidence, so the builder
is self-contained." It is an attest-only pass under
[ADR-0022](adr-0022-pluggable-oracle-boundary.md) (`review.py:1104-1112`) —
"servo runs and scores; jig attests". Handing its read-only attestor a
user-supplied "design review" rubric to read-and-apply is either meaningless or
is exactly the laundering ADR-0022 forbids: an honesty gate overridden by a judge
the audited party chose. `design_review` therefore joins `independent-review` and
`frame-critique` in the **never-defer set**.

ADR-0039's Consequences claimed design-review "advertise[s] (or should advertise)
deferral … both now honor it"; the shipped builder flatly contradicts that, and
this ADR ratified the claim unverified through four revisions before checking it.

`security-review` and `bug-fix`'s craft/security passes are an **explicit,
named non-goal** of spec 096, not a silent omission. Their deferral remains a
router hint today. Making them config-honoring requires deciding *how* an
orchestrator-invoked judgment skill receives configuration without reintroducing
inert prose — a real design question, entangled with
[ADR-0013](adr-0013-security-floor-policy.md)'s scanner orchestration and with
ADR-0039 Option B's own objection that a richer security skill assumes
`gh`/Bash/WebFetch, which the read-only reviewer cannot be granted without
ceasing to be independent.

**This is the honest cost of D1, stated plainly.** Two parts, both user-visible:

- **Security is not fixed.** It is the category ADR-0039's Context §3 named as
  "the asymmetry the user flagged as the real concern". Three guaranteed
  surfaces beat five nominal ones, but the gap is real and is tracked, not
  buried — see Open questions.
- **Config becomes surface-dependent within a category, not just
  lifecycle-dependent.** `review.pr_review_skill` is honored in spec-workflow's
  craft pass and silently ignored in bug-fix's, even though
  `bug-fix/SKILL.md:229-231` already promises that pass "defers to a richer
  installed `pr-review` skill on disk". **And the same is true of the
  user-invocable skills:** `/jig:pr-review`, `/jig:arch-review`, and
  `/jig:code-health` defer only via the Claude router
  (`pr-review/SKILL.md:16`, `arch-review/SKILL.md:18`,
  `code-health/SKILL.md:12-18, :26-28`), so a configured key is ignored there
  too — on exactly the router-only, Codex-inert surfaces ADR-0039 Context §3
  named as the original concern.

  So "three guaranteed surfaces" counts **passes, not categories**: within a
  category, the orchestrated review pass honors config and the interactive
  skill invocation does not. That is a real seam, and closing it is the same
  unsolved problem as OQ1 (how an orchestrator-invoked judgment skill receives
  configuration). All four SKILL.mds — `bug-fix`, `pr-review`, `arch-review`,
  `code-health` — must say so in prose when 096-01 lands, rather than leaving a
  user to discover it.

**Rejected:** building a security prompt-builder inside spec 096 (scope
explosion into ADR-0013 territory, on a surface whose tool requirements
contradict the read-only reviewer). **Rejected:** shipping prose-only config for
the three surfaces (the mechanism ADR-0039 §3 rule 2 forbids; its recorded
outcome would be unreachable).

### D2 — Baseline exclusion uses the existing `jig-` path prefix at project scope; no new frontmatter marker

A discovery query excludes any project-scope skill directory whose name starts
with `jig-` — reusing the discriminator `migrate.py:287` already ships and
tests.

**The primary argument is cost, and it does not depend on the size of the
installed base.** The prefix test reuses a discriminator that already ships and
is already tested; the marker requires a new cross-cutting frontmatter contract
on every shipped baseline, a CI test to defend it, and host-package
regeneration. Cheaper, with no new contract, is sufficient grounds on its own.

**The installed-base argument is secondary and carries an unresolved tension
with the parent ADR**, stated rather than glossed: ADR-0039 :334-338 — carried
forward — asserts "machinery-scaffolded projects are not yet expected to exist
in the field", while `migrate.py:107-118` documents jig routinely retrofitting a
real population. One of the two is wrong, and this ADR does not settle it. D2
holds either way on the cost argument above; the installed-base point only
*adds* force if the parent's denial is mistaken. Under the marker, every project
scaffolded before the feature lands keeps
`.claude/skills/jig-pr-review/SKILL.md` with untouched frontmatter
(`scaffold.py:701` — "The frontmatter is left untouched") whose description is
the single strongest lexical match for the `pr-review` category, unmarked, at
the **winning** precedence scope. Zero-config discovery would then hand jig's own
baseline back as "richer" — the exact failure the marker existed to prevent —
and the 096-05 anomaly would be blind to it, because a skill *was* applied.

Consequently ADR-0039's **OQ4 is moot rather than resolved**: with no marker
there is nothing to migrate, so "no migration for already-scaffolded projects"
stops being a limitation and becomes a property of the mechanism.

**Retained from ADR-0039, on a corrected basis:** a `jig_baseline: true` marker
still has a genuine job at **plugin/admin scope**, where jig's shipped skills are
*unprefixed* and a path test cannot see them. It is adopted there only, argued on
that basis, and is no longer load-bearing for project-scope safety.

**Rejected:** marker plus a backfill migration (reverses OQ4, keeps a
cross-cutting frontmatter contract and two host-package regenerations, and still
needs the prefix test for pre-backfill projects). **Rejected:** forward-only
marker as specced (leaves the entire installed base exposed).

### D3 — Selection runs over an explicitly printed candidate list, not ambient host context

The zero-config path is a declared channel:

1. `review.py candidates <category> <spec> <slice> --pass <pass>` enumerates
   non-baseline candidates, **prints** `name` + `description` for each, **and
   writes that exact printed set to a sidecar** keyed to `(slice, pass)`. It
   takes the slice identity because it must produce its own key — a
   category-only signature could not. The printed list is the **declared
   selection substrate**, and the sidecar is written by the *act of showing it*.
2. The orchestrator picks one and passes it back as `--richer-skill <name|none>`
   (required argument, per ADR-0039 §3 rule 2, carried forward).
3. The prompt-building call **records the pick into the existing sidecar**. It
   does **not** re-enumerate and does not author the candidate set. Later,
   `record-review` **reads that sidecar** and stamps the evidence artifact from
   it, rather than accepting the candidate set as an orchestrator-typed flag.
   Two distinct writers, one reader: `candidates` writes the shown set, the
   prompt-build call writes the pick, `record-review` only reads.

   **A sidecar carrying candidates but no pick** — the state produced by the
   cheapest defection path (run `candidates`, skip the builder, call
   `record-review` directly, as `bug-fix/SKILL.md:229-234` prescribes today) —
   is stamped `substrate: shown` with the applied skill recorded as `unknown`,
   and **is anomaly-eligible**. It must not read as a clean decline: candidates
   were shown and no pick was ever recorded.

**`substrate:` is a closed vocabulary *derived* by `review.py` from observable
state — config presence and sidecar presence — rather than asserted by the
orchestrator.** The one exception is `non-interactive`, which is necessarily a
caller declaration; that is why it is anomaly-ineligible but still *aggregated*
by kill criterion 1, and why reaching for it is named in Assumptions as the
residual unmitigated escape. Exactly one of:

| value | meaning | anomaly eligible? |
|---|---|---|
| `config` | `review.<category>_skill` present; resolution ended before enumeration (ADR-0039 §3 rule 1: config "ends resolution — no enumeration") | no — the user chose deliberately |
| `shown` | sidecar present; candidates were printed and one was picked or declined | **yes** |
| `non-interactive` | caller explicitly declared no orchestrator (documented CI value) | no — nothing was shown to anyone |
| `not-shown` | no sidecar, no config, no declared `non-interactive` — the selection step did not happen | **yes, and it is the defect signal** |
| `n/a` | the pass is not one of D1's three extensible categories | no |
| *(field absent)* | artifact predates this ADR, or was written outside the channel | no — absence is not evidence of an anomaly |

**Computation is scoped by `(category ∈ {pr_review, arch_review, code_health})
AND (keying mode == slice)`.** `record-review` writes evidence for all nine
passes (`_common/review_evidence.py:61-62`) across three keying modes (slice /
`--adr` / `--bug`), including the never-defer set (`compliance`,
`reconciliation`, `frame-critique`) and the bug lifecycle D1 scopes out.
Computing `substrate:` uniformly would stamp `not-shown` — the defect signal —
on passes that never run a `candidates` step, so the aggregate would read
"habitual defection" from day one: the revision-2 error again (an instrument
whose failure reading is manufactured by its own success state).

**The keying-mode half is load-bearing, not the category half alone.** `craft`
is a *single shared pass token*: bug REVIEWED requires `["bug-review", "craft"]`
(`review_evidence.py:259-263`), and `bug-fix/SKILL.md:229` runs that `craft`
pass *as the `pr-review` category* — i.e. in-category, yet with no `candidates`
call because D1 scopes bug-fix out. A category-only scope would therefore stamp
`not-shown` on every bug ever fixed. The rule must exclude it by **keying mode**:
`substrate:` is computed only for slice-keyed evidence in the three categories;
everything else — `--bug`, `--adr`, and the never-defer passes — is stamped
`n/a`.

**`config` is a third, named blind spot — not a fully-observed state.**
`substrate: config` is derived from config *presence*, not from evidence the
configured skill was actually applied, and it is anomaly-ineligible by design
(the user chose deliberately, ADR-0039 §3 rule 1). Because `--prompt-source` is
unvalidated freeform, an orchestrator in a config-set project can skip the
builder entirely and still produce a clean-looking `config` artifact — and once
096-01 ships as the recommended floor, `config` is the **modal** state. So the
anomaly is deliberately blind exactly where the guaranteed layer lives. This is
defensible (config is the deterministic escape the whole chain falls back to)
but it is a real silencer sitting beside the two named ones, and it belongs in
the ADR-0039 "known blind spot" family — recorded, not papered over. It is the
reason D1's config path, not the anomaly, remains the layer jig can actually
*guarantee*.

**`record-review` is the chokepoint, and it *computes* `substrate:` rather than
accepting it.** This is the load-bearing placement decision, and it is not the
prompt-build call. `record-review` is the artifact writer, it is independently
invokable, and its `--prompt-source` is an unvalidated freeform string
(`review.py:1667-1689`) — so the cheapest defection is not the
`non-interactive` escape but **never calling the builder at all**: spawn a
reviewer off jig's baseline prose and call `record-review` directly. That path
is not hypothetical — `bug-fix/SKILL.md:229-234` prescribes it today. Any
enforcement living in the builder is therefore bypassable by the exact route a
cost-pressured orchestrator would take. Placing the computation in
`record-review` narrows it as far as this design honestly can: every artifact
written *through the documented flow* passes that call, and it derives
`substrate:` from config plus sidecar presence without the orchestrator typing
anything.

**"Narrows", not "closes" — stated precisely, because two earlier revisions
overclaimed exactly here.** `parse_verdict_file`
(`_common/review_evidence.py:276-356`) validates freeform frontmatter with no
provenance binding to any writer, and `substrate:` is deliberately kept out of
the gate. So an artifact hand-written with the required fields still clears
`validate_evidence` and simply carries no `substrate:` — the *(field absent)*
row above. This is the **honest-actor chokepoint**, consistent with the
auditability-not-enforcement posture carried forward from ADR-0039: it makes the
documented path record the truth and makes the undocumented path visibly
different, which is all a non-blocking record can do.

**This does not touch ADR-0014 §3.** The transition gate stays a one-line
predicate on `verdict:` alone; `substrate:` is *recorded*, never gated on. A
`not-shown` artifact still reaches REVIEWED — it is visible, not blocking,
consistent with the auditability-not-enforcement posture carried forward from
ADR-0039.

The prompt-build call **additionally** exits non-zero when invoked with no
sidecar, no config, and no `non-interactive` declaration — a fail-fast for the
orchestrated path, in the same arity-class as ADR-0039 §3 rule 2's "omission is
a visible error". It is a convenience, **not** the guarantee; the guarantee is
the computed `substrate:` at `record-review`.

*Three earlier revisions of this ADR got this wrong, recorded here rather than
quietly dropped.* Revision 3 placed the enforcement in the prompt-build call and
claimed "a skipped step cannot produce an artifact at all" — false, since
`record-review` writes artifacts independently and `bug-fix` already calls it
without any builder. Revision 1 had the prompt-build call write the sidecar from
its own enumeration — a writer that re-derives the set records a
**re-enumeration, not an act of showing**, so a skipped step 1 would be
byte-identical to a genuine decline. Revision 2 fixed the writer but treated
**sidecar absence** as the skipped-step signal; that was also wrong, and in a
more instructive way: config (rule 1) and CI both produce absence legitimately,
so a "high absence rate" reading would have fired *precisely when config was
working* — an instrument whose failure reading is manufactured by its own
success state. The closed vocabulary above exists because absence had three
producers and only one of them was defection.

**`candidates` prints the full recall set, tiered — it does not filter.** This
is D3's fourth decision and it is stated explicitly because it would otherwise
supersede ADR-0039 by accident. Output carries two tiers:

- **high-confidence** — candidates the matcher affirmatively classifies for the
  category, printed with `name` + `description`;
- **speculative** — everything else enumeration nominated, printed as **names
  only** (no descriptions).

The orchestrator may pick from **either** tier. The anomaly fires only against
the **high-confidence** tier.

**The print format is load-bearing for cost, not cosmetic.** D3 re-injects skill
descriptions into orchestrator context that ADR-0039 leaned on being "already
loaded" (:159-161) — on the spike's 26-skill corpus that is a non-trivial
per-pass payload against spec 055/057's context×turns discipline. Printing
descriptions only for the (small) high-confidence tier and bare names for the
speculative tail bounds the re-injection to what the pick actually needs. This is
the second half of D3's honest cost (the first being the extra turn); both are
booked in Consequences.

**An off-list pick is handled, not left undefined.** If the orchestrator passes
`--richer-skill <name>` for a skill absent from *both* printed tiers, the
prompt-build call **rejects it and falls back to jig's baseline**, recording the
rejection (096-05) — it does not silently accept an off-list name, which would
make "the declared substrate" a fiction. Config remains the escape for a skill
the matcher never nominated at all. This is the "unhandled off-list pick" state
D3 rejects the hybrid over — here made explicit rather than left open.

This resolves a dilemma earlier revisions walked into without naming. Printing a
*precision-filtered* list would make the deterministic matcher the gate on what
the model can pick at all — reversing ADR-0039 rule 3 ("recall, not precision …
a model, not a regex, does the choosing", :254-258) and reinstating the exact
defect the recorded owner override rejected Option C over: a matcher "overfit by
construction … each new miss requires a regex edit shipped in a jig release"
(ADR-0039 :150-156, :339-350). Printing a *raw recall* list instead would leave
the anomaly uncalibrated — a legitimate `none` while `morning-github` was shown
would still trip it, the very problem ADR-0039 :296-307 exists to solve.
Tiering takes neither horn: the model keeps its classification advantage over
the whole set, and the anomaly keeps a calibrated reference class.

**Consequently precision governs the anomaly's false-positive rate only — never
the pick.** That is exactly the division ADR-0039 :304-307 settled, and it is
carried forward rather than reversed. A matcher miss demotes a candidate to
`speculative`, where it is still visible and still pickable; it does not
disappear.

**One enumeration code path, not two.** The tiering that decides what
`candidates` prints is the same function whose output is written to the sidecar
— by construction, since printing and writing happen in one call. Nothing may
re-derive the set downstream, or the recorded set can drift from the shown set.

Three problems dissolve together. The enumerator gains a real runtime consumer.
The anomaly gains a producer that is **not the agent it audits** — closing the
omission escape whereby an orchestrator passes `--richer-skill none`, leaves the
candidate fields empty, and produces an artifact byte-identical to a machine with
nothing installed. And Codex selection becomes host-portable: an agent picking
from text it was just shown needs no router and no hidden-prompt injection.

**Therefore ADR-0039's OQ6 stops gating anything.** Host-injected skill metadata
was a *cost* optimization — "the descriptions are already loaded" — that
ADR-0039 promoted to a capability gate. Under D3 the candidate list is shown
explicitly on both hosts because the calibration requirement demands it anyway,
so whether the host *also* preloads descriptions is a turn-cost question, not a
feasibility one.

**Honest cost:** D3 spends one extra orchestrator turn per gated pass (the
`candidates` call) against spec 057's turn-count discipline. That is the price
of an auditable record, and it is the correct trade — ADR-0039 offers
auditability as its entire value proposition, and an unauditable version of it is
worth less than the turn it saves.

**Rejected:** ambient selection (anomaly self-reported by the audited agent;
omission stays a zero-cost escape; Codex stays gated on OQ6). **Rejected:**
hybrid ambient-pick-with-recorded-set (an orchestrator may name a skill the
enumerator never nominated, an unhandled state, and the recorded set still would
not be what was actually shown).

## Consequences

**Becomes easier:**

- The anomaly record becomes trustworthy: its input is produced by
  `review.py`, not typed by the orchestrator being audited.
- Codex reaches zero-config parity without a spike into another vendor's prompt
  assembly — 096-04 loses its blocking premise.
- Already-scaffolded projects are safe from baseline self-nomination on day one,
  with **no migration and no project-scope marker**. (Host-package regeneration
  is *not* avoided — see "Becomes harder": the marker is retained at
  plugin/admin scope and still flows through `hosts/claude/` and
  `hosts/codex/`.)
- The precision-matcher requirement (ADR-0039 :304-307) becomes **allocatable**:
  precision governs what `candidates` prints, and — because printing and sidecar
  writing are one call (D3) — the printed set and the recorded set cannot
  diverge. Placement is not allocation, so the slice that ships `candidates`
  owns the filter, names its calibration corpus, and inherits the spike's
  `morning-github` false positive as a required regression case.

**Becomes harder:**

- One extra orchestrator turn per gated pass (see D3's honest cost).
- Two documents to read for the full rationale.
- **Host-package regeneration is still required.** D2 removes the marker's
  *project-scope* job, not the marker: jig's shipped skills are unprefixed at
  plugin/admin scope, so stamping them still flows through `hosts/claude/` and
  `hosts/codex/plugins/jig/` and still trips the drift gate (the cost
  ADR-0039 :418-420 booked). Only half of that cost is avoided.
- Security parity is explicitly deferred, so the originally-flagged asymmetry
  persists until the follow-up lands.
- The sidecar is new shared state between two `review.py` invocations; it needs a
  defined lifetime, a collision story for concurrent passes, and defensive
  parsing.

## Assumptions

- **VERIFIED (2026-07-27, direct read of this tree):** `review.py` has no
  security prompt-builder and `subagent-type` enumerates no security mode;
  `security-review/SKILL.md:71-72` and `bug-fix/SKILL.md:232` describe
  router-hint and no-`pr-review`-call mechanisms respectively. Grounds D1.
- **VERIFIED (2026-07-27, direct read):** `scaffold.py:742` prefixes every
  user-facing scaffolded skill with `jig-`; `:726` leaves only `_`-prefixed
  shared modules unprefixed; `migrate.py:287` already uses the prefix as a
  discriminator. Grounds D2.
- **VERIFIED (2026-07-27 spike, carried forward from ADR-0039):** Codex exposes
  an enumerable skill surface at `$HOME/.agents/skills`, repo `.agents/skills`,
  and `/etc/codex/skills`, with `SKILL.md` frontmatter identical in shape to
  Claude's. Grounds D3's host-portability claim.
- **PARTIALLY VERIFIED (2026-07-28, spec 096-04 probe — status update, not a
  decision change):** that an orchestrator reliably executes the `candidates` →
  pick → `--richer-skill` sequence when instructed in SKILL.md prose. This is the
  residual prose-compliance risk D3 does **not** eliminate — it moves the risk
  from *which set is selected from* to *whether the step is run at all*, **the
  most likely failure mode of the whole design.** Spec 096-04's behavioral probe
  (`scripts/orchestrator_selection_probe.py`) settled it as a *reachability floor
  test*: **Claude PASS** (the agent ran the stub `candidates` and emitted the
  correct pick on a non-empty tiered list AND `none` on an empty-tier control),
  **Codex INCONCLUSIVE** (host unauthenticated in the probe environment; re-run
  after `codex login`). Reachability is confirmed on Claude; *durability under
  mid-slice cost pressure* still rests on the `substrate:` aggregate (Kill
  criterion 1), exactly as this ADR framed it.

  Stated precisely, because revision 1 overclaimed here: requiredness of
  `--richer-skill` does **not** mitigate it. Requiredness constrains the *pass*
  call's arity; the step at risk is the *`candidates`* call, on which
  requiredness has no purchase — ADR-0039 :320-325, carried forward unchanged,
  says so outright ("`--richer-skill none` satisfies it and reproduces the
  original failure byte-for-byte"). The mitigation is D3's **refusal**: with no
  sidecar, no config, and no declared `non-interactive`, the pass exits non-zero.
  That converts a silent skip into a hard stop — prevention at the point of
  failure, not merely instrumentation after it. What remains unmitigated is the
  orchestrator reaching for `--non-interactive` to silence the refusal, which is
  a visible choice in the evidence rather than a silent one.

  **Spec 096-04 is re-aimed at this and re-sequenced ahead of 096-03** —
  replacing the retired OQ6 question with the jig-side one: can an orchestrator
  (on each host) reliably run the select-and-pass sequence against jig's own
  prose? The probe is **stub-based** — a fake `candidates` script plus the real
  SKILL.md recipe is sufficient to observe compliance — so it does *not* depend
  on 096-03 shipping. **A green probe does not license the durability claim:** a
  dedicated probe session (short context, single task, the recipe as the point of
  the session) measures *reachability*, not compliance under the mid-slice cost
  pressure that is the actual risk (ADR-0039 :329-331, "a standing spec-057 cost
  incentive"). It gates "is this recipe followable at all"; durability rests
  entirely on the `substrate:` aggregate. Sequencing it after 096-03 (as
  originally drafted) would
  probe the design's self-declared most likely failure mode only after the
  machinery it would kill had shipped, inverting ADR-0039 §6's carried-forward
  "guaranteed layer first" discipline.
- **ASSUMED (cheap to verify during implementation):** the read-only reviewer can
  `Read` a `SKILL.md` at project and admin scope. Spec 053's live probe confirmed
  only user scope (`~/.claude`). If false, multi-scope resolution returns paths
  the consumer cannot read, producing a silent baseline fallback that looks like
  a successful resolve. Must be probed by the slice that ships resolution.

## Kill criteria

- **The `candidates` step is routinely skipped.** Instrumented by the recorded
  `substrate:` value, which is why it had to land in the artifact rather than in
  a non-zero exit: a refusal writes nothing to disk and would be structurally
  unobservable. `workflow.py status-board` aggregates `not-shown` and
  `non-interactive` counts. If either becomes the habitual value on interactive
  hosts, D3's channel is inert prose in a new costume — fall back to config-only
  (D1's `scaffold.json` keys), which needs none of this machinery.

  **Note the consumer constraint this reflects.** `check_reviews`
  (`review.py:1514-1535`) is per-slice, per-stage, and binary — diagnostics then
  `return 2`, else `return 0`. It has no non-blocking warning channel and no
  aggregation, and giving it one would either start blocking (contradicting
  ADR-0039's carried-forward "deliberately not a gate" and ADR-0014 §3's
  one-line `verdict:` predicate) or require an aggregator. So the counts go where
  ADR-0039 :292-294 already put the anomaly — `workflow.py status-board` — and
  `check-reviews` keeps its existing contract unchanged.
- **The printed list is consistently ignored.** If orchestrators select skills
  absent from the printed set, the declared substrate is a fiction and the
  anomaly is again measuring something the orchestrator did not use.
- **Sidecar merge proves fragile** (concurrent passes, stale files, cross-slice
  bleed) such that the anomaly's false-positive rate exceeds its signal — then
  record the applied skill only, drop the shown-set claim, and say plainly that
  jig offers no way to distinguish "nothing installed" from "declined".
- **The extra turn is judged not worth it** under spec 055/057 review — then
  config-only remains the shipped floor and zero-config is abandoned rather than
  half-built.

## Open questions

- **OQ1 — How does an orchestrator-invoked judgment skill (`security-review`,
  `bug-fix`'s passes) receive configuration without inert prose?** Deferred out
  of spec 096 by D1; entangled with ADR-0013. Needs its own ADR before any
  security-parity work starts. **Tracked in
  [refinement-todo](../refinement-todo.md).**
- **OQ2 — Sidecar lifetime, absence, and collision semantics.** Where it lives,
  when it is cleaned up, what happens when two passes for the same slice run
  concurrently — and, load-bearingly, **how absence is distinguished from
  staleness**. Kill criterion 1 rests entirely on `record-review` computing
  `substrate: not-shown` when and only when step 1 never ran; a sidecar left
  behind by a previous run, or cleaned up too eagerly between step 1 and
  `record-review`, would corrupt that signal in either direction. Note the
  window is now wider than in earlier revisions — the sidecar must survive from
  `candidates` through the reviewer spawn to `record-review`, not just to the
  prompt-build call. Settle it in the slice that ships the sidecar, and treat it
  as a correctness requirement rather than an implementation detail.
- **OQ3 — Does the "unprefixed ⇒ no `SKILL.md`" invariant hold as a contract?**
  D2 depends on it across *both* unprefixed project-scope writers
  (`scaffold.py:726` shared modules, `:1485-1489` Codex logical-name alias), not
  just on the `jig-` prefix. It is load-bearing now, so it wants a test asserting
  the invariant directly — that no unprefixed project-scope skill dir a scaffold
  writes carries a `SKILL.md` — rather than resting on current behavior of one
  writer.
- **OQ4 — Is the retained plugin/admin-scope marker needed at all?** D2 keeps
  `jig_baseline: true` there because jig's shipped skills are unprefixed at that
  scope — and that retention is the *sole* source of the host-package
  regeneration cost booked in Consequences. But jig's plugin directory is itself
  named `jig` (`hosts/codex/plugins/jig/skills/…`), so a plugin-directory test
  may cover it without any frontmatter contract. Rule this out explicitly before
  committing to a cross-cutting marker plus a CI test plus two host-package
  regenerations; if it holds, D2 drops the marker entirely and the regeneration
  cost goes to zero.
- **Inherited from ADR-0039 and unchanged:** whether jig's `security-review`
  baseline is "too deep" for a shallow default (against ADR-0013) remains
  tracked separately in [refinement-todo](../refinement-todo.md).
