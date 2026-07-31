---
status: FIXING
tier: standard
severity: low
claimed_by: claude/github-issue-140-63ae37
regression_test: skills/adr-workflow/test_adr.py::IndexNoSummaryTests
main_repro_checked_at: 2026-07-30
main_repro_ref: 00c3333
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at:
fix_class: local_patch
security_surface: false
escalated_to:
---

# Bug 020: adr-index-summary-degradation

> Reported as [issue #140](https://github.com/ramboz/jig/issues/140), which
> named **two** defects. Only the first is fixed here. The second — a curated
> summary being overwritten on regen — is **won't-fix by ruling**; see
> [Scope](#scope-one-of-the-two-reported-defects).

## Symptom

`adr.py index` derives each ADR's one-line index summary from the record's
first `## Context` paragraph. When that paragraph is a lead-in to a bulleted
list or a table, it contains no sentence-ending punctuation, so:

- a **short** lead-in was written out verbatim, ending in a colon —
  `jig has two scaffold topologies, selected by one axis in \`scaffold.py\`:`
- a **long** one was cut at 120 characters and given a trailing `…` —
  `jig now has a **family of three gated-evidence lifecycles**, all mirroring
  ADR-0014's transition-gate architecture and r…`

Both read like a decision summary. Neither is one, and neither says what was
decided. Four records on `main` carried such a line: ADR-0022, ADR-0023,
ADR-0041 and ADR-0046, plus ADR-0040 whose Context is still the template stub
(`_TODO: describe the situation, …`).

Nothing surfaced it. The index looked populated, so the only way to notice was
to read a bullet and realize it was a fragment.

## Scope: one of the two reported defects

Issue #140 also reported that a hand-written summary is destroyed on the next
regen, and proposed preserving it the way the spec status board preserves its
curated Notes column.

That half is **not** fixed, by maintainer ruling. On
[#151](https://github.com/ramboz/jig/pull/151) the same question was put as a
three-way choice — (a) fix the source ADR, (b) preserve hand-written
summaries the way the board preserves Notes, (c) accept the fragment — and
the ruling was **(a): the index stays a pure function of the ADR files**,
reaffirmed on [#154](https://github.com/ramboz/jig/pull/154) when the conflict
with this bug's original fix was raised. A summary written into the README is
still overwritten, deliberately.

This fix serves that ruling rather than working around it: under (a) the
remedy is to reword the ADR's own opening, and the thing that was missing was
any signal telling you *which* record needs it.

## Repro

Against a clean export of `origin/main` at `00c3333`:

```bash
cat > docs/decisions/adr-0999-list-lead-in.md <<'MD'
## Context

jig has two scaffold topologies, selected by one axis in `scaffold.py`:

- **plugin mode** - the lean default.
MD
python3 skills/adr-workflow/adr.py index docs/decisions
# → - [ADR-0999: …] — jig has two scaffold topologies, selected by one axis
#     in `scaffold.py`: (2026-07-30, Proposed)
# exit 0, no warning.
```

## Evidence

- `skills/adr-workflow/adr.py:_extract_description` truncated at the first
  `.` / `?` / `!` and, when there was none, fell through to
  `paragraph[:120].rstrip() + "…"`. The "no sentence boundary at all" case was
  treated as "one very long sentence" rather than as "not a sentence".
- The helper had no way to return *nothing*. Every input had to yield a
  string, so a paragraph that cannot be summarized still produced one.
- Live count on `main`: 5 of 46 index bullets were a fragment or a stub.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. -->
- [ ] H1: the sentence-boundary detector is too weak, and a better extractor
      (fall back to `## Recommended Decision`, or to the next Context
      paragraph) would produce a good summary for these records. Falsified
      against the four live cases: ADR-0023's Recommended Decision opens
      `**Option C.**` and ADR-0046's opens `Adopt **Option D**.` — complete
      sentences that say *less* than the fragment they would replace — and
      ADR-0040 has no prose anywhere to fall back to. A better guess is still
      a guess.
- [x] H2 (leading): the defect is the missing return value, not the heuristic.
      `_extract_description` is forced to answer even when the honest answer
      is "there is no summary in this paragraph", so a lead-in comes back
      dressed as a sentence. Confirmed by the fix: allowing `""` closes every
      live case, and the record that genuinely has no summary (ADR-0040) is
      reported instead of papered over.

## Root cause

`_extract_description` had no representation for "this paragraph contains no
summary". A list lead-in — text grammatically incapable of being a summary —
therefore came back as a colon-terminated fragment or a `…` stub, and the
renderer wrote it without question.

## Fix class

`local_patch` — one helper gains an "I don't know" return; the renderer
reports it instead of inventing.

## Fix

`skills/adr-workflow/adr.py`:

1. `_extract_description` returns `""` when the first `## Context` paragraph
   holds no complete sentence. The `paragraph[:120] + "…"` hard-truncation
   branch is gone. A paragraph that *ends* in a colon but opens with a real
   sentence is truncated to that sentence.
2. `_is_degenerate_description` guards the write path for the cases that do
   have a boundary but still are not summaries: a trailing `…`, and the
   template's `_TODO` / `_TBD` stub.
3. A record with no derivable summary gets `(no description)` plus a stderr
   warning naming the record and the reason — lead-in versus unwritten stub —
   and pointing at the source: reword that `## Context` opening. `index` still
   exits 0; this is a report, not a gate.
4. `_first_sentence_end` and `_context_paragraph` are extracted so the
   sentence scan and the paragraph read are each stated once.

Four ADR openings were reworded into standalone sentences under
[ADR-0006](../decisions/adr-0006-adr-accept-then-index-ordering.md)'s
Context-prose carve-out: ADR-0022, ADR-0023, ADR-0046, and ADR-0041 (restoring
the wording from #151, which #157 reverted wholesale). ADR-0040 is left at
`(no description)` — its record is an unwritten stub, so that is the honest
line, and the warning keeps nudging until someone writes it.

ADR-0006 gains an `## Amendments` entry: its decisions all stand, but the
preview pass it prescribes now has a signal to read.

## Already tried

An earlier version of this fix implemented issue #140's second half —
preserving curated summaries, modelled on `workflow.py:parse_existing_notes`.
It was built, reviewed twice, and dropped on the ruling above. Two findings
from those passes are worth keeping even though the code is gone: keying
preserved text by number alone mis-attributes it when a number is reused, and
a predicate that decides both "never write this" and "never keep this" has to
be documented as one set or the doc drifts from the code. Neither applies to
what shipped, because nothing is kept.

## Regression test

- `skills/adr-workflow/test_adr.py::ExtractDescriptionLeadInTests` — both live
  lead-in shapes yield no summary (the short/colon ADR-0041 shape and the
  long/hard-truncated ADR-0022 shape); a colon-terminated paragraph that opens
  with a real sentence still yields that sentence; the happy path is unchanged.
- `skills/adr-workflow/test_adr.py::IndexNoSummaryTests` — the bullet reads
  `(no description)`, the warning names the record, the template stub reports
  as a stub rather than as a lead-in, a summarizable record warns about
  nothing, and **rewording the Context updates the index** — the ruling's
  remedy has to actually work.
- `skills/adr-workflow/test_adr.py::RepoIndexQualityTests` — issue #140's own
  grep, run against jig's real `docs/decisions/README.md`.

## Proof

_Pending re-review of the reshaped fix._

## Learning

**A deterministic extractor needs a way to say "I don't know".** Forcing a
string out of every input is what turned "this paragraph is a lead-in to a
list" into a line that read like a decision summary. The failure was silent
precisely because the output was well-formed: a fragment and a summary are the
same shape.

**And the reporting is what makes a "fix it at the source" policy workable.**
The ruling here is that the index stays derived — so the tool cannot repair a
bad bullet, only the author can. That is a reasonable rule *provided the tool
says which record needs the author*. Before this, it silently produced
something plausible instead, which is the failure mode a derive-only policy
is least able to survive.
