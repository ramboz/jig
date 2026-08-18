---
status: Accepted
dependencies: [adr-0016, adr-0014, adr-0011, adr-0052]
last_verified: 2026-08-18
frame_review: true
---

# ADR-0037: Bug-fix repository closure evidence

## Status

Accepted (2026-08-18)

## Context

The bug lifecycle proves diagnose-before-fix, fresh-main reproduction, and a
red-to-green regression test. Its review prompt asks about blast radius, but
the workflow does not require the implementer to inventory equivalent logic,
inspect the history that introduced it, or close every affected call site
before coding. That omission is observable: a Mystique change duplicated an
existing URL-identity helper and fixed one lookup path while missing another
path with the same contract. TDD passed because the local behavior was covered;
the repository-level closure question was never made durable evidence.

This is a process defect, not a request to mandate one search product. Semantic
indexes can make discovery cheaper, but the lifecycle must remain correct with
targeted text search and git history alone.

## Decision Options Considered

### Option A: Leave repository closure to the review passes
- **Pros:** No new record fields or transition gates.
- **Cons:** The *reuse decision* — the one judgment that must precede code to
  matter — is never forced before the patch is written, so duplicated logic has
  already shaped the change by the time anyone asks; and reviewers cannot
  distinguish a completed inventory from an unrecorded assumption, because
  nothing durable records which search was run. (Note the contrast is narrower
  than "evidence arrives too late": under Option B the *quality* judgment still
  runs at `bug-review`, i.e. after the fix. What moves earlier is the author's
  recorded search and reuse decision, plus the artifact that makes the later
  review checkable.)

### Option B: Require pre-fix inventory and post-fix call-site closure
- **Pros:** Makes reuse, history, and blast-radius reasoning explicit before
  code is written; gives reviewers concrete evidence; remains tool-neutral.
- **Cons:** Adds a small evidence burden to standard and gnarly bugs and needs
  a compatibility rule for existing records.

### Option C: Require a semantic-index provider for standard bugs
- **Pros:** Strong discovery capability when the provider is healthy.
- **Cons:** Couples lifecycle correctness to optional infrastructure, excludes
  offline/public users, and still does not prove that the search was complete.

## Recommended Decision

Choose **Option B**. Before `ROOT_CAUSED -> FIXING`, standard and gnarly bug
records must contain a repository-closure inventory: equivalent/convergent
logic searched, relevant history inspected, affected call sites identified,
and an explicit reuse decision. Before `-> REVIEWED`, the record must contain
call-site closure evidence explaining how every identified site was changed,
tested, or intentionally left alone.

**What the gate does and does not prove.** The transition helper is a
*deliberateness* gate in the [ADR-0011](adr-0011-spec-gate-model.md) lineage,
not a discovery guarantee. It enforces that the four evidence prompts are
present and substantively answered; it cannot verify that the author's search
was *complete*. An author who does not know a convergent helper exists can run
the prompted search, find nothing, and write a truthful-from-their-view "no
equivalent logic found" inventory — the shape passes while the miss survives.
We accept this limit deliberately, because jig has already been burned by
treating a prose-shape check as if it proved substance:
[bug 005](../bugs/005-diagnose-gate-list-shape.md) records the diagnose gate
"green-lighting for the wrong reason" when indentation-blind matching counted
sub-bullets as hypotheses. The lesson is not "add more prose gates," it is
"do not let the parser gate masquerade as the quality judge." So the split is
explicit: **the helper enforces presence and shape; `bug-review` is the
discovery-quality backstop** — it reads *what search was actually run*, presses
on convergent-name variants and untried paths, and judges whether the recorded
"nothing found" is credible, exactly as it already judges the local regression
test. The durable inventory exists to give that reviewer something concrete to
interrogate; converting a silent omission into a recorded, falsifiable claim is
the gain over Option A, whose own con — "reviewers cannot distinguish a
completed inventory from an unrecorded assumption" — is what this records answer.

**What `bug-review` actually adds — and what it does not.** The backstop is not
a claim that the reviewer out-searches the author; a reviewer running the same
name-based tools with *less* domain context has no superior discovery power, and
we do not assert one. Its edge is a **burden shift already accepted in
[ADR-0052](adr-0052-grounding-enumeration-for-universal-claims.md)**: "no
equivalent logic exists" is a *negative, universal* claim, and under ADR-0052 a
claim of that shape is established only by an enumeration whose set-closure the
author must state — "the bug-review pass treats an empty search as *un*grounded
until you have shown what closes the set" (`skills/bug-fix/SKILL.md:224-226`).
That converts an unfalsifiable "I looked and found nothing" into a checkable
artifact: the recorded search terms and the stated reason the set is closed. A
reviewer cannot conjure the unknown helper, but it *can* see that the search was
name-anchored on one spelling, that nothing closes the set, and that ORM
indirection / codegen / a differently-named synonym escapes it — and refuse the
claim on those grounds.

**Delineation against ADR-0052 (overlap is real and bounded).** ADR-0052 already
governs universal/negative claims at the `## Root cause` step, which overlaps
this decision's *affected call sites* prompt. This ADR adds what ADR-0052 does
not cover: a **pre-fix reuse and history inventory** — does an equivalent
implementation already exist, what does its history say, and is the explicit
decision to reuse or duplicate recorded — plus a **post-fix disposition** for
each identified site. Where the two touch, ADR-0052's enumeration rule is the
governing standard; 091 must reuse it rather than restate a weaker parallel one.

**What satisfies the equivalent-logic prompt when the set cannot be closed.**
This is the delta prompt, and it is definitionally in ADR-0052's *unclosable*
class — a differently-named implementation is not bounded by any syntax a
`grep` can close. ADR-0052's remedy for an unclosable set is to weaken the claim
and record it under assumptions, and that remedy **applies here unchanged**: an
author may honestly conclude "the set is not closable by name search." That
disposition **satisfies this gate as to the *claim*** — we do not require a
completeness proof no search can deliver, and any gate demanding one would be
unsatisfiable and route authors straight to boilerplate or `*_GATE=0` bypass.

What it does **not** do is discharge the *protocol*. This gate is an
**effort-and-protocol standard, not a completeness standard**: the record must
show the search that was actually run — which behavioural/contract terms were
tried (not merely one spelling of the symbol name), what `git log` / `git blame`
on the touched surface returned, and which sibling call paths were inspected —
and *then* may record the residual as an assumption. A bare "no equivalent logic
found," and an unadorned "not closable, recorded as assumption" with no executed
protocol behind it, both fail. What a reviewer refuses is a *missing or
threadbare protocol*, not a candid statement of irreducible uncertainty.

This keeps the gate satisfiable and keeps the honest answer cheap, which is what
prevents the bug-005 dynamic (a gate green-lighting on shape) from recurring one
level up. The gain is bounded and we state it as such: a recorded protocol makes
*thin searching* visible and challengeable. It does not make the unknown helper
appear.

**Residual gap, stated plainly.** The inventory is capability-neutral: a
semantic index is preferred when available, with targeted search plus
`git log`/`git blame` as the baseline. That baseline is name-based and therefore
weakest precisely against differently-named convergent logic — the Mystique
case. This decision **reduces** that class (by forcing the search before coding
and making its completeness challengeable) but does **not** close it; closing it
is a discovery-capability problem that Option C addresses and this process does
not. We accept a partial remedy with a falsifiable kill criterion over a
capability mandate that would exclude offline and public users. Existing bug records remain readable
and can transition under a documented compatibility rule keyed to a schema
marker (not an enumerated record range); newly created records carry the new
schema.

## Consequences

**Becomes easier:**
- Catching duplicate implementations before they land.
- Reviewing whether a fix closes the repository-wide behavior rather than one
  symptom or call site.
- Learning from earlier project decisions and landed helpers.

**Becomes harder:**
- Bug authors must record a bounded inventory for non-trivial fixes.
- The gate parser and templates need version-aware compatibility tests.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

_Load-bearing factual claims about runnable surfaces (library/API capability,
version/perf behavior, behavior of existing code) must be backed by an executed
probe (run a command, read source/`node_modules`) or a citation — or listed
here explicitly as an assumption. Never assert an unverified claim as fact._

_Risk-gated: omit this section (or write "None") when the decision has no
unverified load-bearing assumptions — do not pad with boilerplate._

- **A recorded, `bug-review`-interrogated inventory catches materially more
  convergent-logic omissions than the review-time blast-radius question alone,
  without turning every bug into an architecture review.** This is the
  load-bearing bet, and it is *not* the stronger claim that the parser gate
  proves closure — that claim is explicitly disowned above. The gain is
  attentional and reviewable: the author must run and record a search before
  coding (rather than answer a blast-radius question after the narrow patch has
  shaped the change), and a fresh reviewer gets a concrete inventory to press
  on. The retrospective Mystique replay motivates the shape but cannot validate
  sufficiency (the replayer already knows the answer); the honest validation is
  forward usage, gated by the kill criterion below. If a convergent-path miss
  lands on a bug whose inventory passed the gate, this assumption has failed and
  the decision is wrong as stated.

## Kill criteria

_What would make this decision wrong? List the conditions that, if observed,
should reverse or shelve it. Risk-gated like Assumptions — write "None" or omit
when there is no meaningful kill condition; do not invent ceremonial ones._

- **Leading indicator — vacuity (watch this first).** The lagging criterion
  below depends on someone later rediscovering a missed helper, which against
  jig's bug volume is plausibly a multi-year signal and cannot falsify the bet
  before the cost is sunk. So the near-term watch is *vacuity*, not misses:
  sample accepted inventories and classify each equivalent-logic answer as a
  real executed protocol (terms tried, history inspected) versus boilerplate or
  a bare "none / assumption" with no protocol behind it. If a majority of
  accepted inventories are vacuous, the prompts are producing paperwork rather
  than search and this decision has failed on its own terms — reverse or
  re-shape toward capability rather than adding further prose fields. This is
  observable from the records themselves, without waiting for a defect.
- **Leading indicator — effect (pair it with vacuity).** Vacuity measures author
  effort, but the bet is about *outcome*, and a diligent-but-blind protocol
  scores as healthy on effort alone. So also count how often a recorded
  inventory **changed the fix**: a reuse decision that actually reused an
  existing implementation, or a call site touched because the inventory surfaced
  it. This is per-record observable on the same sampling pass. Inventories that
  are consistently well-executed *and* consistently change nothing mean the
  mechanism is producing diligence without discovery — the same reversal
  trigger as vacuity, detected without waiting for the multi-year miss signal.
- **Primary miss (the outcome this ADR exists to prevent):** a convergent-path
  or duplicate-logic defect lands on a bug whose repository-closure inventory
  *passed* the gate and was accepted by `bug-review`. One such case is a
  warning; a second means the evidence prompts plus the name-based baseline are
  not moving discovery outcomes, and the decision should be reversed or
  re-shaped toward capability (Option C-style tooling), not defended with more
  prose fields.
- If usage data shows standard bugs routinely bypassing the gate because it is
  disproportionate, keep it mandatory for gnarly bugs and make standard-tier
  enforcement advisory.

## Open questions

None.
