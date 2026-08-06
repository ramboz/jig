---
status: Accepted
dependencies: [docs/decisions/adr-0020-spec-frame-hardening.md]
last_verified: 2026-07-31
frame_review: true
---

# ADR-0052: Grounding rule: universal/negative claims require enumeration

## Status

Accepted (2026-07-31)

## Context

jig's grounding requirement accepts a single citation as sufficient evidence for
any factual claim, but a citation of one positive example cannot establish a
universal or negative claim.

[ADR-0020](adr-0020-spec-frame-hardening.md) §1 established that grounding
requirement: a factual claim in a spec/ADR about a runnable surface must be
backed by "a **verifiable artifact**: preferentially an *executed probe* …
falling back to a citation," and anything not verifiable must be marked as an
assumption. That rule has a hole in its *content*, not just its scope: it treats
"a citation" as sufficient grounding for *any* claim. But a **citation of one
positive example cannot establish a universal or negative claim.** These are
claims whose truth quantifies over a whole set:

- "the **only** such import"
- "**nothing** reads this column"
- "dependency direction is **one-way**"
- "**never** written by v1.0"
- "otherwise **clean**"

One true example says nothing about the rest of the set. A claim of this shape
is established only by **enumeration** — a search you can show returns the
*complete* set — not by a single citation. But enumeration itself only works
when the set is **bounded by the search**: imports in a package or call-sites in
a repo are closed by syntax, so a `grep` provably yields every member. Some of
the claims above are *not* so bounded — "nothing reads this column" is defeated
by dynamic/ORM/reflective access and external consumers a search never sees;
"never written by v1.0" is a historical claim no current-tree search bounds;
"otherwise clean" has no set at all until "clean" is defined. For those, an
empty search result is **absence of evidence, not a complete enumeration** — and
mistaking one for the other would rebuild the very false-confidence failure this
rule exists to kill, with more authority than the honest citation it replaces.

**This is grounded in a concrete failure, not a hypothetical.** While
reconciling SymPill slice 008-17 ([issue #132](https://github.com/ramboz/jig/issues/132)),
an author wrote that a Compose `Color` import was "the **only** such import" in
a package and the layer was "otherwise **clean**." The claim carried a real,
correct `file:line` citation (`TodayRailBuilder.kt:3`) — the citation was true.
The *claim* was false: the package imported six types from the UI layer and the
dependency ran **both ways** — a package cycle, not a stray import. The claim
technically **satisfied** ADR-0020 §1 and survived **two** review rounds
precisely because it *looked* grounded. The real check — `grep` over every
import in the package — takes seconds and would have returned the full set.

Two properties make this worth a decision rather than a footnote:

1. **Universal/negative claims are the highest-value claims in a frame.** They
   are exactly what a future reader relies on to decide something is safe to
   change ("nothing reads this, so I can drop it"). A false one here is more
   dangerous than a false positive-existence claim.
2. **The failure is invisible to the existing rule.** The grounding gate is
   satisfied, the citation is genuine, the frame-critique reviewer sees a
   grounded claim. Nothing in the current wording tells author or reviewer that
   *this shape of claim needs a different kind of evidence.*

The maintainer approved the fix and asked to extend it to the bug workflow
([issue #132](https://github.com/ramboz/jig/issues/132) comment): a root-cause
claim of the same shape ("nothing else calls this", "only this path writes it")
has the identical defect.

## Decision Options Considered

### Option A: Do nothing — rely on the frame-critique reviewer to catch it

- **Pros:** No rule change; the adversarial frame-critique pass (ADR-0020 §3)
  is already charged with attacking the load-bearing assumption.
- **Cons:** The SymPill claim *did* pass review twice. The reviewer has no
  prompt telling it that a universal claim demands enumeration rather than a
  citation, so it evaluates "is this grounded?" and sees a true citation. The
  gap is in the *rule's content*; leaving it unstated leaves the reviewer
  without the lever.

### Option B (Recommended): Add an enumeration clause to the grounding rule

State explicitly that a **universal or negative** claim requires an
**enumeration** — a search whose output is the complete set — not a single
positive citation; if it cannot be enumerated, the claim must be weakened or
moved to `## Assumptions`. Refine ADR-0020 §1's content, mirror the clause in
the live operational prose authors and reviewers actually read
(`spec-workflow` step 6 and, per the maintainer, `bug-fix`'s diagnosis step).

- **Pros:** Closes the content gap at its source. Gives the frame-critique
  reviewer and the author the same explicit test. Costs nothing on the common
  case — a spec with no universal claims is unaffected. Highest-value claims get
  the strongest evidence standard.
- **Cons:** One more thing for an author to internalize. Risk of over-literal
  keyword-hunting ("did you say 'only'?") if it hardens into a lexical gate —
  mitigated by keeping it a judgment rule in prose, never a keyword-matching
  check (consistent with jig's standing distrust of lexical-marker gates).

### Option C: Build a lint that flags universal-claim keywords

Add an advisory lint that greps spec/ADR prose for "only / never / always /
one-way" and nudges the author to enumerate.

- **Pros:** Mechanical reminder; a real red→green-testable artifact.
- **Cons:** A keyword lint over natural-language prose is exactly the
  brittle-marker mechanism jig has repeatedly declined — it fires on quoted
  text, negated forms, and prose that happens to use the word, and stays silent
  on the same claim phrased without a trigger word. It trains authors to launder
  the wording rather than enumerate. The judgment belongs with the reviewer and
  the author, not a regex.

## Recommended Decision

**Option B — add an enumeration clause to the grounding rule.**

Extend ADR-0020 §1's grounding standard with the clause below — recorded **in
this ADR**, not by editing ADR-0020 (immutable; see the routing note after the
rule) — and land it in the operative prose of `spec-workflow` step 6 and
`bug-fix`'s diagnosis step:

> A **universal or negative** claim ("the only", "never", "always", "one-way",
> "nothing reads", "otherwise clean") is established by **enumeration** — a
> search you can show returns the *complete* set — not by a single positive
> citation. To claim enumeration you must **state why the search is exhaustive**:
> what closes the set so that nothing escapes the search. Some sets are closed by
> syntax and this is easy to show (imports in a package, call-sites in a repo).
> Many are not: a "nothing reads this" search misses dynamic / reflective / ORM /
> string-built / config-wired / codegen'd / cross-repo access — and that list is
> **illustrative, not a checklist to clear**; the burden is to show the search
> captures every member, not to rule out named escape routes. A "never" or
> historical claim, or "otherwise clean" before "clean" is defined, has no set a
> current-tree search can close at all. When you cannot show the search is
> exhaustive, an **empty result is absence of evidence, not an enumeration**:
> weaken the claim, tighten the boundary until the search genuinely closes the
> set, or move it to `## Assumptions`. Never dress an empty search as an
> enumeration. The **frame-critique reviewer attacks the "why exhaustive"
> claim** — treating "I ran a search and it was empty" as *un*grounded until the
> author has shown what closes the set — so the completeness judgment is not left
> to author self-assessment alone.

The **shift from "classify the set" to "show the search is exhaustive" is the
load-bearing move,** and it exists because the bounded/unbounded call is
*harder* than the citation-vs-enumeration call authors already fail. The
dangerous claims are the ones that *look* `grep`-bounded but are not — a column
written through an ORM or reflection that a `grep` seems to enumerate. Asking an
overconfident author to self-certify "bounded vs unbounded" would just relocate
the original overconfidence one level up. Instead the rule (a) puts a positive
burden on the author to articulate *why* nothing escapes the search, which is
far easier to falsify than a bare "it's bounded," and (b) routes that
articulation to the external frame-critique reviewer, who is charged with
attacking it. The recorded incident (#132) is the base case — a genuinely
bounded set where the author simply did not run the available search; the
"empty search laundered as enumeration" failure is a distinct risk this rule
must not *create* while fixing the first, and how common each proves is
unverified (see `## Assumptions`).

This **refines ADR-0020 §1; it does not supersede ADR-0020.** ADR-0020's three
mechanisms (grounding, assumptions/kill-criteria, frame-critique) all stand
unchanged; this decision adds one evidence standard for one shape of claim
within mechanism 1. Per [ADR-0010](adr-0010-amendment-scope-records-vs-live-prose.md),
the decision-content change is recorded in this new ADR (ADRs are superseded,
never amended), and the operative guidance lands as **inline edits** to the two
SKILL.md files (live operational prose, git-history audit trail).

The rule stays a **judgment rule in prose**, read by the author while grounding
and by the frame-critique reviewer while attacking the frame — never a
keyword-matching gate (Option C rejected on jig's standing distrust of
lexical-marker enforcement).

## Consequences

**Becomes easier:**

- Catching the highest-value frame errors — false "only/never/one-way" claims —
  at authoring and frame-critique time, where correction is cheapest.
- Giving the frame-critique reviewer an explicit test to apply to a
  universal claim, rather than accepting a true-but-insufficient citation.

**Becomes harder:**

- Authoring a spec/ADR that makes a universal claim now costs the enumeration
  (the `grep`-the-whole-set step) or an honest downgrade to an assumption. This
  is the intended cost — it is seconds of work on exactly the claims that most
  need it.

## Assumptions

- **The external frame-critique reviewer can catch a "why exhaustive"
  justification that is wrong — a search that *looks* like it closes the set but
  does not** (an ORM / reflective / codegen'd write the author's `grep` never
  saw). *Unverified, and load-bearing.* The whole mitigation for author
  overconfidence routes the completeness judgment to the reviewer; if the
  reviewer is fooled by the same surface the author was, the rule still lets a
  laundered empty search through — now stamped "enumeration reviewed." The
  mitigation is that a *positive articulation* of why nothing escapes is far
  easier to falsify than a bare "it's bounded," so the reviewer has a concrete
  target; whether that is enough in practice is what the kill criteria watch.
- **The unbounded "empty-search-as-enumeration" failure is a material risk, not
  merely theoretical.** *Unverified.* The one recorded incident
  ([#132](https://github.com/ramboz/jig/issues/132)) is the *bounded* case — a
  `grep`-able set where the author did not run the available search. That
  authors will *also* mis-read empty results on *unbounded* claims is inferred
  from how the grounding rule reads, not observed. If it proves negligible the
  unbounded half is harmless but over-weighted in prose — trim it then; the
  bounded half stands on the recorded incident regardless.

Beyond these, the ADR's factual claims were checked, not assumed: the ADR-0020
§1 wording was read from the file, and the #132 incident, the maintainer's
approval, and the bug-workflow extension are on the issue thread. This is not a
claim that *no* unverified assumption remains — only that these were the ones
found.

## Kill criteria

Reverse or revisit this rule if, in practice:

- it hardens into a lexical keyword hunt (reviewers flagging the *word* "only"
  rather than the unenumerated *claim*), or authors reword universal claims to
  dodge the trigger rather than enumerating them — the marker-gate failure mode
  Option C was rejected to avoid; or
- the reviewer check on "why exhaustive" proves no better than author
  self-assessment — laundered empty searches keep passing frame-critique because
  the reviewer is fooled by the same look-bounded-but-isn't surface. That would
  falsify the load-bearing assumption above and mean the completeness judgment
  needs a stronger check than a reviewer read (or the rule should stop promising
  one).

## Open questions

- Does routing the "why exhaustive" justification to the frame-critique reviewer
  actually catch look-bounded-but-isn't sets, or does the reviewer inherit the
  author's blind spot? Only real frame-critique runs on universal claims will
  tell; the kill criteria above are the watch.
