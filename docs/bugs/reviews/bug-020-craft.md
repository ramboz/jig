---
bug: 020
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-31T01:05:56Z
prompt_source: pr-review skill craft pass (re-review after follow-up 24ea814)
---

Re-review of the follow-up commit, against `skills/pr-review/SKILL.md`.
Supersedes the earlier craft verdict recorded in this file (ADR-0014 §4). The
three reconciliation items below were applied after this verdict was returned,
in the reconciliation sweep that follows review.

The follow-up closes the blocker at its root rather than moving it:
`_is_degenerate_description` is now `not text or _is_template_stub(text)`, and
I checked all four ways the guard can fire against all three branches of
`_no_summary_reason` — they now agree in every case, and the fallback comment's
invariant ("everything reaching here failed `_first_sentence_end`") is provably
true rather than aspirational. The unreachable `":"` / `(no description)`
conditions are gone with them, so the extractor's post-condition is once again
the only definition of "not a summary" in the file. Every nit was addressed at
the level it was raised — `_is_template_stub` as single owner, the required
`warnings` parameter, `_NO_SUMMARY_REMEDY` once per run after the per-record
lines, the ADR-0040 worked example matching real output byte for byte, the
checklist distinguishing a written record from a stub, the corrected amendment
date — and the two weak tests are now real. The new `## Proof` is unusually
good: it names three behaviour changes beyond the reported symptom, including
the one nobody asked about (scaffolded projects will start seeing stderr on
every regen).

VERDICT: pass

## Reasoning

### Blockers

None.

### Nits

- `RepoIndexQualityTests` still checked `desc.endswith("…")`, encoding the
  belief this round rejected: that a trailing ellipsis in a rendered summary is
  damage. The new test and the guard docstring now say the opposite — an
  ellipsis is the author's own prose and survives intact. The two cannot
  collide on today's corpus, but the first author who ends a short Context
  opening with `…` would get a bullet the tool deliberately blessed and a red
  suite saying "degenerate index summaries on disk", with nothing in the ADR to
  fix. The check still has regression value against reintroduced hard
  truncation, so the fix is not deletion — it is a comment saying which of the
  two a failure means, and a message that distinguishes them.
  **Applied in the sweep.**
- The once-per-run remedy line was the change made in response to the "policy
  tail repeated per record" nit, and nothing pinned it. No test had two
  degenerate records, so moving the write back inside the loop would have left
  the whole suite green. **Applied in the sweep**, with the two-record
  assertion and a mutation check.
- The record stated three counts of the same population that a reader could not
  reconcile — Symptom's four records, Evidence's "5 of 46 index bullets", and
  Proof's three grep hits. The explanation is real: ADR-0041's README row was
  stale and did not match its own source, so the grep sees three of the four.
  But the record never said so, and the numbers read as carelessness in the one
  section whose job is to be checkable. **Applied in the sweep** — and worth
  writing, because "the generated README was out of sync with its sources" is
  itself evidence for the derive-only ruling.

### Strengths

- The blocker was resolved by narrowing the predicate rather than by adding a
  fourth truncation trigger, and the choice is documented where the next person
  will hit it, in the house form — the counterfactual and the reason it was
  rejected, not just the rule. That docstring is the strongest single artifact
  in the change.
- `_no_summary_reason`'s fallback comment went from asserting a false invariant
  to asserting a true one, and I verified it by exhaustion over the guard's
  inputs rather than taking it on trust: the guard can only fire with an empty
  description or a stub, the stub case is intercepted above, so everything
  reaching the fallback did fail `_first_sentence_end`. That is a comment a
  reader can rely on.
- `test_a_partly_written_stub_is_still_a_stub` asserts its precondition before
  asserting the guard fires, so it cannot silently degrade into a test of the
  empty-string path if the extractor changes. Same discipline in the reword
  test's new precondition. This is the pattern the earlier vacuous assertion
  lacked, applied consistently.
- The Proof's "behaviour changes beyond the reported symptom" section
  volunteers the colon-truncation change and the new stderr traffic in
  scaffolded projects — neither was reported, neither would have been noticed,
  and both are the kind of thing that surfaces as a support question six months
  later. Naming them unprompted is the habit worth repeating.
- Doc consolidation landed as more than a deletion: section 4 is the single
  home, the `index` bullet and the gotcha cross-reference it with a working
  anchor, and the worked example uses the one record that actually warns today
  with its real reason string and the real once-per-run remedy line — I diffed
  it against the f-strings in `adr.py` and it matches.
- The frontmatter is correctly *not* over-claimed: `green_confirmed_at` is
  still blank with the suite green, which is right — `bug.py` stamps it on the
  → REVIEWED transition, after the verdicts.
