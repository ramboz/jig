---
status: Accepted
dependencies: []
last_verified: 2026-07-29
frame_review: true
---

# ADR-0046: Frontmatter status is authoritative; prose Status is best-effort

## Status

Accepted (2026-07-29)
Supersedes ADR-0026

> **Numbering note — this record was drafted as ADR-0039, and landed as 0046.**
> The maintainer's approval reads *"I approve ADR-0039"*
> ([PR #139](https://github.com/ramboz/jig/pull/139), 2026-07-30) and refers
> to **this** decision. The approval was **not** given for the
> [ADR-0039](./adr-0039-richer-skill-discovery.md) that now exists on `main`
> (host-portable richer-skill discovery) — that is a different decision, and it
> was already Accepted when the comment was written.
>
> The number moved twice while this PR was open:
>
> - **0039 → 0043.** ADR-0039 and
>   [ADR-0040](./adr-0040-richer-skill-discovery-explicit-candidate-channel.md)
>   landed on `main` via [PR #141](https://github.com/ramboz/jig/pull/141),
>   taking both; 0041 and 0042 were claimed by open PRs
>   [#136](https://github.com/ramboz/jig/pull/136) and
>   [#137](https://github.com/ramboz/jig/pull/137), leaving 0043 as the next
>   free number.
> - **0043 → 0046.** 0043 was not free after all.
>   [PR #138](https://github.com/ramboz/jig/pull/138) was independently
>   renumbered off the same `main` collision and picked 0043 too, because this
>   branch's claim existed only in unpushed local commits and was invisible to
>   a scan of open PRs. Both records carried
>   `docs/decisions/reviews/adr-0043-frame-critique.md` at an identical path —
>   an add/add conflict that cannot be resolved by choosing a side. Rather than
>   arbitrate between two Accepted decisions, both moved: #138 took 0045 and
>   this record took 0046, ordered by PR number since merge order was not
>   fixed. **0043 is deliberately left unused.**
>
> The decision itself never changed across either move. The lesson is recorded
> where it can act: a number is only safely claimed once the reservation is
> pushed, so `max(NNNN)+1` over `main` plus a sweep of open PRs is still not
> sufficient — unpushed local claims are invisible to both.

## Context

[ADR-0026](./adr-0026-adr-status-frontmatter.md) made frontmatter `status:`
the canonical home for ADR lifecycle state and cast the prose `## Status`
section as a **synchronized** mirror. Every `adr.py` status mutation writes
both representations in one atomic write, and a test locks the pairing so
"prose and frontmatter cannot silently diverge."

That invariant is only reachable if the writer can always rewrite the prose
line — which means the writer must *recognize* it. `cmd_accept` therefore
gates on an exact prose shape:

```python
_STATUS_PROPOSED_RE = re.compile(
    r"(?m)^(Proposed)[ \t]*\(([0-9]{4}-[0-9]{2}-[0-9]{2})\)[ \t]*$"
)
```

[Issue #123](https://github.com/ramboz/jig/issues/123) / [bug
013](../bugs/013-adr-accept-strict-prose-gate.md): an ADR whose Status line
reads `Proposed (2026-07-22) — awaiting owner acceptance.` is refused, with
an error that never names the trailing clause as the cause. The ADR *is*
Proposed; only its prose is non-canonical. The regex's own comment claims
trailing content is supported, so comment and code also disagree.

Three facts frame the fix (verified by inspection, not assumed):

1. **`accept` is the lone strict reader.** `_classify_status`,
   `_extract_status_and_date`, `cmd_supersede`'s gate and the index all
   already tolerate a Status line with trailing text and classify it
   correctly as Proposed. `cmd_accept` is strict because it does two jobs
   with one regex: *gating* the flip and *rewriting* the line.
2. **Loosening the regex in place would corrupt content.** The rewrite is
   `sub(lambda _m: f"Accepted ({_today()})", …)`. A pattern that matched
   trailing text would drop it; preserving it yields the
   self-contradictory `Accepted (2026-07-23) — awaiting owner acceptance`.
   The reporter hit exactly that shape.
3. **Scaffolded ADRs are unaffected.** The template emits a bare
   `Proposed ({{DATE}})`, so `new` → `accept` always works. This only bites
   a hand-edited Status line — a natural thing to edit, because the line
   reads like prose.

The maintainer's position on the issue ([comment
thread](https://github.com/ramboz/jig/issues/123)) sets the frame this ADR
records: *status should be strictly tracked only in the frontmatter
properties, since we can enforce a strict format there; keep the prose
flexible so projects can use any template they want. We can mutate prose
status by regex where it is present, but that is brittle, so leave the rest
to the LLM and only deterministically flip the frontmatter.*

That is a different data model from ADR-0026's. Under ADR-0026 the two
representations are equal partners kept in lockstep; under the maintainer's
frame the frontmatter is the machine's surface and the prose is the
project's, deterministically touched only when it happens to be canonical.
The strictness in `cmd_accept` is a *consequence* of ADR-0026's model, not
an independent defect — so changing it is a decision change, not a bug fix,
and per [ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md) it
takes a new superseding ADR rather than an amendment.

## Decision Options Considered

### Option A: Keep the strict gate; fix only the comment and the error message
- **What:** The issue's own recommendation. Drop the false "(or with extra
  trailing content)" comment; make the refusal say *"Status line must be
  exactly `Proposed (YYYY-MM-DD)` — found trailing text after the date."*
  ADR-0026's synchronized-mirror invariant survives untouched.
- **Pros:** Smallest change. Zero new behaviour, zero divergence, no ADR
  strictly required. The diagnosis cost that motivated the issue — a
  refusal that does not name its cause — is fully paid off.
- **Cons:** Keeps the prose format load-bearing for a *machine gate*, which
  is exactly what the maintainer rejects: projects cannot template the
  Status line freely, because a decorated line blocks `accept`. Leaves
  `accept` as the one strict reader among five lenient ones — the
  inconsistency stays, and the next hand-edited ADR hits the same wall with
  a better error message.

### Option B: Loosen the regex to match trailing content and rewrite the whole line
- **What:** What the misleading comment implies is already happening.
- **Pros:** One-character-class change; `accept` stops refusing.
- **Cons:** **Silently destroys authored prose** (drops the trailing
  clause) or produces self-contradictory text if it preserves it. Rejected
  on the issue's own evidence — the reporter had to hand-clean exactly this
  output.

### Option C: Gate leniently, but refuse when the prose is not canonical
- **What:** Classify the state from frontmatter (prose as legacy fallback),
  and refuse the flip with a clear, actionable message when the prose line
  is not canonical — *"frontmatter says Proposed, but the prose Status line
  carries trailing text; make it `Proposed (YYYY-MM-DD)` before
  accepting."* Nothing ever diverges.
- **Pros:** Preserves ADR-0026's no-divergence invariant exactly. Error is
  actionable, unlike today's. No new reader surface required — every
  consumer can keep reading either representation, because they always
  agree.
- **Cons:** Still makes the prose format a hard machine gate; the project
  cannot template the line freely, which is the constraint the maintainer
  is trying to remove. The human is required to hand-edit prose to satisfy
  a tool whose authoritative field is elsewhere.

### Option D: Frontmatter authoritative, prose best-effort (CHOSEN)
- **What:** Split the two jobs the regex does today. Gate on the
  *classified* state (frontmatter first, lenient prose classifier as the
  legacy fallback), flip frontmatter unconditionally, and rewrite the prose
  line **only when it is canonical**; otherwise leave it untouched and
  print a note that it needs a touch-up. Frontmatter and prose may be
  briefly out of step; the agent reconciles the prose.
- **Pros:** Matches the maintainer's frame: strict where the format is
  enforceable (frontmatter), flexible where it is authored (prose).
  Deterministic tooling never rewrites prose it does not fully understand,
  and never destroys authored text. `accept` stops being the odd strict
  reader out.
- **Cons:** **Reverses ADR-0026's cannot-diverge invariant** and the test
  that locks it. Divergence, once possible, must be handled by *every*
  status reader — so this option is only sound if all of them are made
  frontmatter-first in the same change (see ruling 3). A prose line left
  stale is a real, visible wrong state until something reconciles it.

## Recommended Decision

Adopt **Option D**. Frontmatter `status:` is authoritative. The prose
`## Status` section is a human-readable, best-effort mirror that
deterministic tooling touches only when it is canonical.

**Why not Option A**, the cheap one. A is a correct *bug fix* and would
close issue #123's stated symptom. We reject it because the symptom is not
the point: the strict gate makes an authored prose format a precondition
for a machine operation whose source of truth is a different field. That is
the thing the maintainer asked to remove, and A preserves it.

**Why not Option C**, the conservative one. C is genuinely attractive — it
buys a clear error message and keeps the no-divergence invariant, which is
the single biggest safety property ADR-0026 bought. We reject it because it
still ends with a human hand-editing prose to unblock a frontmatter flip.
The maintainer's call on the issue was explicit: *"ok with the temporary
divergence. let's see how that plays out concretely in the project."* This
ADR records that as a deliberate, observed trade — not an oversight — and
the Kill criteria below name what would send us back to C.

**The honest residual in that argument** (surfaced by this ADR's
frame-critique, and the reason D's advantage over C is narrower than it
first reads): D does not *eliminate* the prose hand-edit — it **defers**
it. Ruling 2 leaves a decorated line untouched, so the ADR never acquires
a canonical `Accepted (YYYY-MM-DD)` line on its own; ruling 5 then refuses
`supersede` for want of that anchor. If nothing acts on `accept`'s stderr
note, the same hand-edit resurfaces later, on a different command, in a
worse position: the acceptance date is no longer in the prose at all, so
the edit becomes a reconstruction rather than a correction. D is still the
right call **given the maintainer's explicit acceptance of the temporary
divergence**, but the residual is bounded less than one would like, and it
is worth being exact about how much.

What genuinely bounds it: `accept` names the exact line to write **at the
moment the divergence is created**, when the acceptance date is trivially
at hand. That is the cheap window, and it is the one the workflow should
aim at.

What does *not* bound it: anything later. Once that window closes the record
no longer holds the acceptance date — the prose date belongs to the
pre-acceptance state, and `last_verified` is a freshness field, not an
acceptance date (see ruling 3). `supersede`'s refusal therefore cannot hand
back a value; the best it can do is name where to recover one (the accept
commit) and say plainly that the metadata is not the answer. So the honest
statement of the trade is: **reconcile the prose at `accept` time, or pay a
`git log` archaeology cost later.** Not *no hand-edit vs. a hand-edit*, and
not *a supplied value vs. a guess*. The Kill criteria and Open questions
below carry this residual forward rather than burying it.

**Standing challenge to this decision — unresolved, and the maintainer's to
settle.** Three rounds of adversarial frame-critique argued *twice* that
Option C is the better choice on this ADR's own accounting, and the
strongest form of that argument is not answered here. It runs: (a) the
pre-fix gate already tolerated a canonical first line with free prose below
it, so what D newly unlocks is only same-line trailing text and an
unparseable first line (see Consequences); (b) in both of those, ruling 5
ends up demanding jig's single canonical line anyway; (c) so D preserves the
very "authored prose format as a machine precondition" that Option A was
rejected for, while additionally paying a diverged window, a lost
machine-readable acceptance date, a standing frontmatter-first discipline,
and an inverted no-divergence invariant — whereas C demands the same
canonical line at the cheapest possible moment, with the date at hand.

That argument is recorded, not adopted. **D stands because the maintainer
ruled on it explicitly** — *"ok with the temporary divergence, let's see how
that plays out concretely in the project"* — and because a decision this ADR
exists to record should not be reversed by the implementer mid-flight. But
the choice is now better-informed than when it was made, and if the narrowed
benefit changes the maintainer's view, superseding this ADR with Option C
costs one ADR and a gate change, not a rewrite: rulings 1, 3, 4 and 5 all
survive that move unchanged; only ruling 2 flips back to "refuse rather than
diverge". Recorded so the option stays cheap.

Concretely, Option D means:

1. **Frontmatter `status:` is authoritative** (carried forward from
   ADR-0026). Where frontmatter carries a `status:` field it decides the
   ADR's lifecycle state, full stop. ADRs without one (every ADR authored
   before spec 073) continue to grandfather through the prose classifier.

2. **Prose is best-effort, not synchronized** (*changes* ADR-0026 ruling
   2). Status writers flip frontmatter unconditionally, in the same single
   atomic write as before. They rewrite the prose Status line only when it
   matches the canonical `<State> (YYYY-MM-DD)` shape. When it does not,
   the prose is left **exactly** as authored — never truncated, never
   half-rewritten — and the command emits a note on stderr naming the file
   and the line that needs a touch-up. Reconciling the prose is the agent's
   job, not the helper's.

   **Precision, because this ADR exists to fix an over-claiming comment:**
   the canonicality check is a `search` over the whole `## Status` body, not
   a match on its first line (pre-existing behaviour — see the narrowed
   benefit under Consequences). So "left exactly as authored" is guaranteed
   for a section containing *no* canonical line. A contrived section holding
   a decorated first line **and** a canonical `Proposed (date)` line further
   down gets that lower line rewritten, leaving two contradictory status
   lines and no stderr note. No ADR in this corpus has that shape and
   `adr.py new` cannot produce it, so it is not a cost this decision pays in
   practice — but the guarantee is "the canonical line, wherever it sits, is
   the one that moves", not "a non-canonical first line is always safe".

3. **Every status reader is frontmatter-first** (new — the cost of ruling
   2). Because prose can now lag, no code path may take an ADR's lifecycle
   state from prose while a `status:` field exists. This covers the
   `accept` gate, the `supersede` gate, `resolve-todo`'s Accepted check,
   and the README index rendering. Prose is consulted only as the legacy
   fallback. This is what makes divergence *temporary and cosmetic* rather
   than behaviour-changing.

   **A diverged ADR publishes no date.** Ruling 3 governs the state, but the
   README index publishes a *state and a date* together, and the prose date
   belongs to whichever state the prose records. So when frontmatter and
   prose disagree, pairing the frontmatter state with the prose date would
   advertise a combination that never existed (`Accepted` as of the day it
   was *proposed*). For the diverged case the index therefore renders the
   state alone and **omits the date**; when the two agree, the prose date is
   used as before.

   There is deliberately **no substitute date**, and this is the part worth
   reading twice. `last_verified` is the obvious candidate and the wrong
   one: it is a *freshness* field, not an acceptance date.
   [ADR-0024](./adr-0024-reference-reframe.md)'s `reaffirm` disposition
   refreshes it, and `workflow.py`'s staleness check reads it as "verified N
   days ago" — so on any reaffirmed ADR it is simply a later date that would
   read as a genuine acceptance date. Ruling 1 also makes frontmatter
   hand-editable, so a hand-flipped `status: Accepted` may carry no
   `last_verified` at all. A plausible wrong date published in the index —
   or written into an immutable record by a well-meant repair — is strictly
   worse than an absent one, because nothing about it looks wrong. Where the
   acceptance date is genuinely needed (repairing a stale prose line before
   `supersede`), it is recovered from the accept commit; `supersede`'s
   refusal prints the `git log` invocation.

4. **Superseded is not Accepted for dependency purposes** — carried forward
   from ADR-0026 ruling 3, unchanged.

5. **`supersede` still requires a canonical prose `Accepted (date)`
   anchor.** Unlike `accept`, `supersede` does not rewrite a line — it
   *inserts* the `Superseded by [ADR-NNNN](…) (date)` link after the
   Accepted line, and that link is load-bearing (both `_classify_status`
   and human navigation read it). When frontmatter says Accepted but no
   canonical prose anchor exists, `supersede` refuses with a message naming
   the fix. Dropping the link silently would be a real loss of information,
   which ruling 2's best-effort licence does not extend to.

This decision **supersedes [ADR-0026](./adr-0026-adr-status-frontmatter.md)**,
carrying forward its rulings 1 and 3 verbatim and replacing ruling 2. It
does not touch [ADR-0004](./adr-0004-decisions-folder-naming.md) (naming) or
[ADR-0006](./adr-0006-adr-accept-then-index-ordering.md) (accept-then-index
ordering); as under ADR-0026, flipping `status:` remains the one mutable
surface on an otherwise immutable ADR.

## Consequences

**Becomes easier:**
- A project whose ADRs carry frontmatter `status:` can put same-line
  trailing text on its prose `## Status` line — the reported repro — without
  blocking `adr.py accept`.

  **This benefit is narrower than "template the line however you like", and
  the difference matters** (frame-critique round 3). The pre-fix gate was
  `_STATUS_PROPOSED_RE.search(section_body)` — a `search` over the *whole*
  `## Status` body, not a match on its first line. So a project template
  carrying a canonical `Proposed (YYYY-MM-DD)` line **plus any amount of
  free prose below it** already passed the old gate and needed nothing from
  this ADR. What ruling 2 newly unlocks is exactly two shapes: same-line
  trailing text, and a first line jig cannot parse at all. In both, the
  surviving prose reads `Proposed` while frontmatter reads `Accepted` — so
  the honest description of the win is *`accept` no longer blocks, and the
  human-facing section is temporarily wrong instead*, not *projects gain a
  free-form status format*. "Translated" in particular is unsupportable: a
  translated line survives `accept` only to block `supersede` under ruling 5
  until someone writes jig's canonical English line.

  **Scope limit:** for an ADR with *no* `status:` field, state still comes
  from the prose classifier, which needs a recognisable `<State> (` opener.
  Every ADR scaffolded by `adr.py new` carries `status:`, so this bites the
  pre-073 corpus and hand-authored files (see Open questions — backfill).
- `accept` refuses on **status** for exactly one reason: the ADR is not in
  Proposed state, and the refusal names the state it actually found, so the
  diagnosis cost that produced issue #123 does not recur. (`accept` still
  refuses for reasons that are not about status at all — a missing
  frame-critique verdict, a missing `## Status` heading, an ambiguous ADR
  number. Ruling 2 removes prose *formatting* from the status gate; it does
  not make `accept` single-cause.)
- Deterministic tooling no longer rewrites prose it cannot fully parse, so
  no authored text is destroyed or made self-contradictory.
- `accept` joins the four already-lenient readers; the strict/lenient split
  inside `adr.py` disappears.

**Becomes harder:**
- **Frontmatter and prose can disagree.** A non-canonical prose line
  survives `accept` and still says `Proposed` while frontmatter says
  `Accepted`. A reader who trusts the prose is misled until the divergence
  is reconciled — the stderr note and the agent are the only things closing
  that window.
- Every current *and future* status reader must be frontmatter-first.
  Ruling 3 converts a class of would-be silent misreads into a standing
  discipline that a future contributor can break.
- ADR-0026's sync-lock test is inverted: what was a guarantee becomes an
  explicitly permitted state, so the regression guard protecting it is
  replaced rather than kept.
- `supersede` and `accept` now behave differently on a non-canonical prose
  line (refuse vs. proceed-with-a-note). The asymmetry is principled
  (rewrite vs. insert a load-bearing link) but it is one more rule to hold.
- **An unreconciled ADR is a blocked ADR.** Rulings 2 and 5 compose into a
  standing trap: an ADR accepted with decorated prose never gains a
  canonical `Accepted (date)` line by itself, so `supersede` on it refuses
  until a human or agent writes that line. The block is loud and atomic, and
  the refusal names where to recover the acceptance date — but the date is
  no longer *in* the record, and the block may land months after the
  divergence was created, in a downstream repo, where the `accept` note that
  would have prevented it is long gone. Reconciling the prose is therefore
  not cosmetic housekeeping — it is the price of ruling 2, and skipping it
  defers a cost rather than avoiding one.
- **The acceptance date is no longer a machine-readable fact for a diverged
  ADR.** Under ADR-0026 the prose Status line always carried it. Ruling 2
  ends that guarantee and no field replaces it: `last_verified` is
  freshness, not acceptance (ADR-0024 `reaffirm` refreshes it). So the
  README index shows no date for a diverged ADR, and any consumer that wants
  one must read git history. Adding an `accepted_on:` frontmatter field
  would close this properly and is **not** done here — see Open questions.

## Assumptions

- **`accept` was the only strict prose gate *for the `Proposed` state*.**
  Verified by reading `_classify_status`, `_extract_status_and_date`,
  `cmd_supersede`'s precondition block and `_render_index_entries` in
  `skills/adr-workflow/adr.py`. **Correction (frame-critique round 3):** the
  leniency is not symmetric. `_classify_status` tests
  `_STATUS_ACCEPTED_RE`, which is anchored `…\)[ \t]*$`, so a *decorated
  `Accepted` line* classifies `Unknown`, and
  `_extract_prose_status_and_date` recovers the state via a first-word
  fallback while silently dropping the date. Consequence: for a legacy ADR
  with no frontmatter and a decorated `Accepted` line, `cmd_supersede`
  refuses through the `not Accepted (got Unknown)` branch — **not** through
  ruling 5's anchor message — so it prints neither the ruling-5 reference
  nor the date-recovery command. Kill criterion 4 accounts for this.
- **No test exercises a Status line with trailing content.** Verified
  across `skills/adr-workflow/test_adr.py` — every seeded ADR uses the bare
  `<State> (date)` form. The misleading comment's promise has never been
  executed, which is why the disagreement survived.
- **Superseding ADR-0026 breaks no live dependency.** Slices 073-01 and
  073-02 declare `dependencies: [adr-0026]`; both are DONE, and the
  dependency check runs only at transition time, so ruling 4's
  Superseded ≠ Accepted rule has no effect on them. No other artifact
  declares a dependency on ADR-0026.
- **The scaffolded copy is byte-identical to the source.** The reporter
  hit this in a downstream project scaffolded from jig, so the fix reaches
  downstream users through the normal scaffold copy — no separate
  migration.

## Kill criteria

- If a diverged ADR (frontmatter Accepted, prose still Proposed) is
  observed misleading a human or a tool **in practice**, the temporary
  divergence was not worth its cost — fall back to Option C: keep the
  lenient gate but refuse the flip when the prose is not canonical, so
  nothing ever diverges.
- If a status reader is found taking state from prose while a `status:`
  field exists (a ruling 3 violation shipping as a real misread), the
  discipline is not holding on its own and needs a mechanical guard — a
  single shared accessor that no code path can bypass.
- If projects never actually exercise the flexible prose format this ADR
  buys, the divergence risk was taken for nothing; revert to ADR-0026's
  synchronized model with Option A's better error message. **This criterion
  has no observer inside jig** — jig cannot see downstream ADR prose, and
  nothing durable records that `accept` took the best-effort path. Treat it
  as a question to ask at the next real downstream contact, not as a signal
  that will arrive on its own.
- **If a `supersede` is observed blocked by ruling 5** — an ADR that
  `accept` let through with decorated prose, reaching supersession time
  still unreconciled — then reconciliation is not happening on its own and
  the deferred hand-edit has become a real cost, not a theoretical one. Two
  escalations, in order of preference: give `supersede` a prose-independent
  anchor (insert the link at the head of the `## Status` section when no
  canonical line exists), or ship an explicit repair command
  (`adr.py fix-prose-status`) so the reconciliation is deterministic rather
  than entrusted to an agent reading stderr. Falling back to Option C is
  the third answer, not the first — the block proves reconciliation is
  unreliable, not that flexible prose was the wrong goal.
  **Observer — and the honest limit on it** (frame-critique round 3): all 41
  live ADRs in this repo carry a canonical `<State> (YYYY-MM-DD)` first line
  and `adr.py new` emits one, so the divergence ruling 2 permits **cannot
  arise here** except by a deliberate same-line hand-edit. Its real home is
  downstream scaffolds — which is exactly where bug 013 came from — and jig
  cannot see downstream ADR prose. So the observer is *a downstream report*,
  the same channel that filed this bug, and the honest statement is that the
  loop is slow, not that it is tight. Two consequences to hold: the signal
  may be a `not Accepted (got Unknown)` refusal rather than ruling 5's
  anchor message (see Assumptions — the leniency is `Proposed`-only), and
  `accept`'s stderr note leaves **no durable trace**, so nothing accumulates
  evidence between reports. If this criterion needs to fire on evidence
  rather than on a report, that trace has to be built first.

## Open questions

- **Backfill of pre-073 ADRs.** Still open from ADR-0026, and now slightly
  more load-bearing: every ADR without a `status:` field is decided by its
  prose, so the flexible-prose licence in ruling 2 does not fully apply to
  it. A cosmetic pass stamping `status:` across the existing corpus would
  close the gap. Out of scope here.
- **Who reconciles the stale prose, and when?** This ADR assigns it to the
  agent that ran `accept`, prompted by the stderr note. Whether that should
  become an explicit lifecycle step (or a lint) is left to the first time
  it is observed being missed. This is the *only* thing standing between
  ruling 2 and the ruling-5 block described under Consequences, so it is
  the weakest link in the chosen option — named here rather than assumed
  away.
- **Should there be an `accepted_on:` frontmatter field?** Ruling 2 removes
  the guarantee that the prose Status line carries the acceptance date, and
  ruling 3 declines to substitute `last_verified` for it (that field means
  freshness — ADR-0024's `reaffirm` refreshes it — so reusing it would
  publish a plausible wrong date). The gap that leaves is real but narrow:
  the index shows no date for a diverged ADR, and repairing a stale prose
  line before `supersede` means a `git log` lookup. A dedicated
  `accepted_on:` field, stamped once by `accept` and never refreshed, would
  close both cleanly. It is **not** taken here because it adds a frontmatter
  field to every ADR — a corpus-wide change with its own backfill question —
  to serve a case that has not yet been observed. **Trigger:** the first time
  the `git log` recovery is actually performed, or a second consumer needs a
  machine-readable acceptance date.
- **Should `supersede` need a prose anchor at all?** Ruling 5 says yes
  because the `Superseded by …` link is load-bearing and there is nowhere
  else to put it. An alternative was not enumerated as a full option and is
  left to the maintainer: insert the link immediately after the `## Status`
  heading when no canonical `Accepted (date)` line exists. `_classify_status`
  finds the link by searching the section body, not by position, so the link
  would stay readable, and ruling 5's refusal — the last hard prose gate in
  the module — would disappear. It is deliberately **not** taken here: it
  changes where a load-bearing link lives on an immutable record, which is a
  decision of its own rather than an implementation detail of this one.
