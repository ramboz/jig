---
bug: 020
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-31T01:05:56Z
prompt_source: review.py bug-review docs/bugs/020-adr-index-summary-degradation.md skills/adr-workflow/adr.py skills/adr-workflow/test_adr.py skills/adr-workflow/SKILL.md docs/decisions/README.md (re-review after follow-up 24ea814)
---

Re-review after the follow-up. Supersedes the `needs-changes` verdict recorded
earlier in this file (git history is the audit trail, ADR-0014 §4). The two
reconciliation items below were applied after this verdict was returned, in
the reconciliation sweep that follows review.

All six findings from the previous pass are closed, verified against the files
on disk rather than the diff alone. The `…` guard branch is gone, so the
false-warning path that blocked cannot fire: `_extract_description` returns the
whole paragraph for `We tried the shared oracle. It did not hold…` and
`_is_degenerate_description` (now `not text or _is_template_stub(text)`)
accepts it, and both halves are pinned by
`test_an_authored_trailing_ellipsis_is_not_treated_as_truncation` — the test
fails if either the extractor starts truncating or the guard starts blanking,
so the resolution is locked, not just asserted in prose. The unreachable `:`
and `(no description)` branches are dropped; the surviving `_TODO` branch now
has a real justification and a real test (`_TODO: fill this in. Notes below._`
does carry a boundary at `in.`, so the extractor returns it and only the guard
catches it), which retires the earlier "delete all three non-empty branches and
the suite stays green" objection.

VERDICT: pass

## Reasoning

### On the `…` question, asked directly: the craft pass was right and my proposal was the weaker of the two

Three reasons, in order of weight.

First, my own example argues against me. Truncating `We tried the shared
oracle. It did not hold…` yields `We tried the shared oracle.` — which discards
the outcome and keeps only the setup. The trailing clause is the more
informative half. A rule whose first concrete case makes the summary worse is
not a good rule.

Second, the colon trigger I wanted to generalize does not generalize. A
colon-terminated paragraph is syntactically pointing at content that is *not in
the paragraph* — the list or table below it — so the text after the last
sentence is unusable by construction. An ellipsis has no such property; nothing
structural follows it, and the elision is the author's own writing. Extending
the colon rule to `…` would treat two unrelated shapes as one, and would leave
the extractor firing on `…` but not on a paragraph ending in `—` or a comma,
which signal incompleteness just as much.

Third, blast radius. Their fix removes a guard branch that could only ever
blank an entire authored summary. Mine would have changed
`_extract_description`'s output for every input ending in `…`, including
multi-sentence paragraphs where the elision was deliberate. Both close the
defect; theirs closes it with strictly less machinery and no new special case.

### Findings from the previous pass

1. **`…` branch makes the warning lie** — closed. The docstring documents why
   the branch is absent, and the reasoning is correct rather than asserted.
2. **`:` and `(no description)` unreachable** — closed. Two conditions, both
   reachable.
3. **`_TODO` justification untrue for the shipped stub** — closed and correctly
   relocated. The docstring scopes the branch to a *partly written* stub, which
   is the only shape that reaches it, and a test covers exactly that shape. I
   confirmed the extractor returns the full `_TODO: fill this in. Notes below._`
   for it (single line, 33 chars, no colon ending, boundary at `in.`), so the
   assertion is non-vacuous and the mutation check is credible.
4. **Duplicated stub definition** — closed. `_is_template_stub` is the single
   owner; both call sites use it.
5. **Amendment dated a day ahead** — closed.
6. **`## Proof` placeholder** — closed. It now carries the original repro
   re-run, per-class red-before/green-after, the mutation check, the suite
   result, and three behaviour changes beyond the reported symptom.

### Did the fixes break anything?

No. Making `warnings` required is safe — `cmd_index` is the only caller and no
test calls the helper directly. The re-shaped warning satisfies every existing
assertion: the record-name and `Context` checks are met by the reason text, the
`template stub` check by the stub branch, and the two empty-stderr assertions by
the remedy printing only `if warnings`. `Optional` is still imported and used.
The SKILL.md cross-reference resolves. Host copies carry the new symbols at the
same occurrence count as source.

Three test edits are strict improvements that close vacuity rather than add
coverage theatre: the colon assertion that could never fail was replaced with a
check that the lead-in text is absent; the reword test gained a precondition so
it cannot pass without first having been broken; and the repo-quality guard
asserts the parse succeeded, so a bullet the regex fails to parse no longer
sails through as an empty string.

## Reconciliation notes

- The once-per-run remedy line was not pinned by any assertion — deleting both
  lines, or moving the write back inside the loop, would have left the suite
  green. The record's Proof and Learning both rest on the warning being
  *actionable*, and the "how to fix" half was the one part with no test behind
  it. **Applied in the sweep**, with a two-record case and a mutation check.
- The record stated three counts of the same population that a reader could not
  reconcile: Symptom said four records, Evidence said "5 of 46 index bullets",
  Proof said the grep returned three. The accurate figure is four defective
  bullets of 45 — three `…`-truncated plus ADR-0040's stub — against five
  affected *records*; ADR-0041 is the fifth at record level only, because its
  bullet still held prose from #136 while its own Context had regressed when
  #157 reverted the #151 rewording. **Applied in the sweep**, including the
  reason, which is itself evidence for the derive-only ruling.
