# Brief: A test-scope vocabulary for coverage (EngTip #21's five test types)

> The most speculative brief in the bundle — read the "consider inbox
> instead" note first. EngTip #21 ("Obtaining Better Code Coverage")
> argues that "good coverage?" is unanswerable without a shared
> vocabulary of test *scope* (unit / component / seam-integration /
> system-integration / e2e). jig reports *artifact* coverage (use-cases,
> spec 068) but has no notion of test *scope* coverage.

## Problem

jig's coverage story is one-dimensional. `workflow.py coverage` (spec
068 / ADR-0025) does a bidirectional use-case ↔ spec set-difference —
useful, but it answers "is every use case implemented?", not "is every
contract tested at the right scope?"

EngTip #21's point: a component fully covered by single-operation unit
tests can still ship with broken multi-operation behavior, and the
classic escape — "unit tests pass, e2e flaky, contract mismatch hides in
the seam" — happens precisely because teams lack a name for the missing
seam-integration test. Without a vocabulary, "do we have enough tests?"
has no answerable form.

jig's own suite illustrates the gap: it is heavy on unit + subprocess/git
integration + `*_skill_surface.py` prose-assertion tests, with no
labelled seam layer across helper boundaries and no shared vocabulary in
`docs/conventions.md` or the reviewer prompts. The reviewer passes
(compliance/craft/arch) never ask "which *scope* of test should cover
this contract, and is it present?"

## Scope

This brief is deliberately small and **doc/judgment-first**, not a new
deterministic tool — the taxonomy is a thinking aid, and over-tooling it
would violate jig's "grow by signal" rule.

1. **ADR the vocabulary** — adopt EngTip #21's five types (or a justified
   subset) as jig's shared test-scope vocabulary, with one-line
   definitions and the "which type catches what" mapping. Record it where
   reviewers and spec authors will see it.
2. **Wire it into the reviewer prompt** (`review.py`) as a *judgment*
   nudge in the compliance/craft pass: "For each contract this slice
   adds, name the test scope that should cover it; flag any contract with
   only an e2e/integration test where a cheaper seam or unit test would
   pinpoint failure." No new gate, no new artifact — a question the
   reviewer already-capable-of-judgment now asks.
3. **Add a `docs/conventions.md` note** (human-approved) defining the
   vocabulary so "we need an integration test here" becomes a
   clarifiable statement.
4. *(Optional, defer hard)* a `coverage --tests` advisory that maps
   declared contract surfaces to present test scopes — **only** if a real
   escaped defect motivates it. Almost certainly out of scope for v1.

## Non-goals

- **No coverage-percentage metric.** EngTip #21's whole argument is that
  a single number is gameable and meaningless. jig must not ship one.
- **No new gating.** This is vocabulary + a reviewer judgment nudge, not
  a blocker. Mirrors `analyze` / `clarify` (advisory, judgment-only).
- **No reclassification of the existing suite.** Don't relabel hundreds
  of existing tests; apply the vocabulary forward.
- **No `*_skill_surface.py` overhaul.** (See the separate concern below —
  those are arguably brittle per EngTip #11, but that's a different
  brief if anyone wants it.)

## Suggested SPIDR axis

**R (Rules)** primary — the deliverable is a shared definition (a rule
for how the team names and reasons about test scope).

## Sketch of slices

1. **test-scope-vocabulary-adr** — ADR adopting the five-type taxonomy
   (or subset), with the catches-what mapping and the rationale (cite
   EngTip #21, #12, #15, #17). Accept before slice 2.
2. **wire-into-review-and-conventions** — add the reviewer-prompt
   judgment nudge in `review.py` + the `docs/conventions.md` definition
   (human-approved edit, so it goes through the spec-gate flow). Tests:
   the reviewer prompt contains the scope question; the conventions note
   is present.

## Dependencies

- **Light coupling with `docs/conventions.md`** — slice 2 edits it, so it
  needs the human-approval flow (`JIG_CONVENTIONS_APPROVED`). Sequence
  accordingly.
- Independent of the other four briefs.

## Notes for clarify / SPIDR

- **Strong clarify candidate: "is this worth a spec at all, or an inbox
  note + a glossary entry?"** Be honest. If the answer is "no real
  coverage-gap defect has bitten us," the right outcome may be a
  `docs/inbox.md` entry + a `glossary.md` definition of the five types,
  reachable via `/jig:explain`, and *no* reviewer-prompt change yet. The
  ADR can still record the vocabulary cheaply. Don't build the optional
  `coverage --tests` tool on speculation.
- Likely clarify question: "five types or fewer?" jig's helpers have few
  true system boundaries; *unit / component / seam / e2e* (dropping
  system-integration) may be the honest subset. Let the ADR decide.
- Related but separate: the `*_skill_surface.py` tests assert on exact
  SKILL.md prose (`assertIn("spec-compliance review", …)`). Defensible
  *if* those tokens are load-bearing routing contract (the description IS
  what Claude reads to route), brittle if they target phrasing. Worth its
  own audit; flag to inbox, don't fold in here.
