---
status: DONE
dependencies: []
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-02 — update-subcommand

**Goal:** `decisions.py update` revises an already-recorded lightweight-decision
entry **through the helper**, instead of the hand-edit every surface forbids.
This is the code path the reported case never had — the moment a decision is
revised is where [#121](https://github.com/ramboz/jig/issues/121) actually broke,
and today there is no way to revise except by editing markdown the helper cannot
see.

`update` does **not** judge routing — that judgement is the assistant's, prompted
by 096-01's `SKILL.md` guidance, per
[ADR-0039](../../decisions/adr-0039-decision-routing-gate.md). This slice gives
that judgement a command to act through: revise here, or (when the decision has
grown ADR-worthy) `promote` (096-03). A code gate on this path was the rejected
mechanism.

**DoR:**
- ✅ The gap is real and probed: `add_lightweight` is append-or-no-op keyed on
  normalized `(date, title)` (`decisions.py:272-273`); there is no edit, no
  delete, no `--force`. Revising means hand-editing markdown, which
  `SKILL.md:129-131` and `decision_scan.py:365` both tell the agent never to do.
- ✅ Spec 083's own OQ2 (`083/spec.md:467-471`) anticipated adding a
  `**Commit:**` SHA retroactively and left no way to do it. This slice supplies
  the path it assumed.
- ✅ `render_entry` (`decisions.py:218`) is the canonical emitter this slice must
  round-trip against.

**Acceptance Criteria:**

1. **An entry can be revised in place.** `update --title "<existing>"` with any of
   `--decision`, `--context`, `--scope`, `--commit` rewrites those fields on the
   matching entry and leaves every other entry, the file's heading structure, the
   routing rubric, and the `## Template` fence byte-identical.
2. **Omitted fields are preserved, not blanked.** Passing only `--commit` leaves
   Decision / Context / Scope exactly as they were. This is OQ2's case, and a
   revision helper that silently drops the fields you did not mention is worse
   than the hand-edit it replaces.
3. **The rewrite round-trips `render_entry`.** The revised block is byte-identical
   to what `render_entry` would emit for the merged fields — one blank line
   between fields, `**Commit:**` only when present — so `add-lightweight` and
   `update` produce indistinguishable entries. A round-trip test
   (`render_entry` → parse → same fields) guards the parser.
4. **A missing entry is a loud refusal.** `update --title` naming no existing
   entry exits non-zero, writes nothing, and says so — it must never silently
   append a new entry, which would turn a typo'd title into a duplicate record.
5. **Title matching reuses the existing normalization.** Case- and
   whitespace-insensitive, via the same `_normalize` the idempotency key already
   uses (`decisions.py:193-199`), so `update` and `add-lightweight` agree on what
   "the same entry" means. An optional `--date` disambiguates when one title was
   used on two dates.
6. **Ambiguous matches refuse rather than guess.** If `--title` (without
   `--date`) matches more than one entry, exit non-zero listing the matching
   dates and asking for `--date`.
7. **The illustrative example and the `## Template` fence are not addressable.**
   `update` must refuse to target the worked example (`### 2026-01-15 —
   Onboarding CTA copy…`) or the `### [Date] — [Short title]` line inside the
   fence — they are documentation, not records. `_existing_keys` deliberately
   keys both (`decisions.py:202-215`), so a narrower "real entry" notion is
   needed here; introduce it cleanly (096-03 and 096-04 reuse it).
8. **No routing gate, no routing flag.** `update` refuses on *matching* grounds
   only (missing / ambiguous / documentation), never on the decision's content,
   and carries no `--confirm-lightweight`. Routing is the assistant's judgement
   (096-01) plus the advisory lint (096-04). This AC is a guard against a
   reviewer re-adding the rejected gate.

**Edge cases covered explicitly:**

- An entry with no `**Commit:**` line gains one cleanly (field added, not
  replaced) — the OQ2 path.
- An entry that is the file's last block, and one that is followed by another
  entry: the rewrite must not swallow the following `### ` heading or the
  trailing newline.
- A `--decision` value containing markdown that looks like a heading must not
  corrupt the file's structure.
- An unchanged update (every supplied field already equal) is a reported no-op,
  not a rewrite — mirroring `add-lightweight`'s idempotency contract.

**Anti-horizontal-phasing check:** after this slice a recorded decision can be
revised through the helper end-to-end — the precondition both the judgement
guidance (096-01) and `promote` (096-03) rely on. It is not "a parser exists and
a later slice will call it".

**DoD:**
- [x] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Host packages regenerated (`scripts/build_host_packages.py`).
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.
      _(No deferred DECISIONS — the three deferred follow-ups are scoped work,
      not open questions, so they went to `docs/inbox.md` per the routing
      rubric: refinement-todo is for decisions with a resolution trigger.)_

### Reconciliation sweep

| Artifact | Disposition | Why |
|---|---|---|
| `skills/memory-sync/decisions.py` | **rewrite** | `update` + the entry parser (`_real_entries`/`_find_entry`), the `## Entries` section bound, and the line-initial-heading guard in `render_entry`. |
| `skills/memory-sync/test_decisions.py` | **rewrite** | `EntriesSectionBoundTests` (the data-loss regression), the round-trip guard, and the corrected inline-vs-line-initial heading pair. |
| `docs/decisions/lightweight-decisions.md` | **no-op** | Format unchanged — `update` re-renders through the existing `render_entry`, byte-identical to what `add-lightweight` emits. |
| `hosts/**` | **regenerate** | Helper mirror. |

See the spec-level `## Reconciliation sweep` for the full cross-slice table.

### Deviation log

The original slice text is preserved above. Implementation notes:

**§1 — `_real_entries` had no lower bound, and it destroyed data.** Found by the
craft review, reproduced before fixing. The `## Entries` section ran to
end-of-file, so the last entry's `**Scope:**` absorbed any following `## `
section — and because `update` rewrites exactly the span the parser reports, the
absorbed section was then **deleted**:

```
## Entries
### 2026-07-01 — First
**Decision:** d / **Context:** c / **Scope:** s

## Archive
Old decisions worth keeping.
```

`update --scope "new"` silently removed `## Archive` and everything under it.
Not reachable on jig's own file or the shipped template (`## Entries` is last in
both), but reachable for any adopter who keeps a section below their entries —
a shape `_foreign_format_error`'s own remedy ("add an `## Entries` heading to
the existing file") actively invites. Fixed by bounding the section at the next
`^## ` (`_NEXT_H2_RE`) and anchoring its start on a real heading line
(`_ENTRIES_HEADING_RE`) rather than a substring `find`, which a prose mention of
`## Entries` could otherwise shift. `EntriesSectionBoundTests` covers parse,
`update`, `promote`, `lint`, and the prose-mention case.

**§2 — a line-initial `### ` in a field value orphaned the entry.** The slice's
stated edge case ("a `--decision` value containing markdown that looks like a
heading") was covered by a test passing *inline* `### `, which the
`(?m)^### ` heading pattern can never match — so the test asserted a guarantee
it did not exercise, and the real case failed: a value carrying a line-initial
`### ` split its own entry, neither half parsed, and the entry vanished from
`update`, `promote` and `lint` with no error. Fixed by refusing such values at
`render_entry`, the single emitter both write paths funnel through. The old test
is kept (renamed to say it covers the *inline* case, which is legal and
preserved) and a real line-initial test added beside it.

**§3 — AC ordering renumbered.** The reframe (ADR-0039) removed the routing gate
from this slice, so the original AC3/AC4/AC5 (gate re-run, flagged-update
refusal, escape hatches) are gone and the remainder renumbered. AC8 is now a
*guard* AC — `update` must carry no routing gate — rather than a feature.

**§4 — refusal messages are shared, not distinct.** The slice anticipated a
separate "that's documentation" refusal for the illustrative example and the
`## Template` fence (AC7). The implementation folds them into the generic "no
entry titled …" refusal, since `_real_entries` simply does not surface them. A
user who targets the worked example is told the entry does not exist rather than
that it is documentation. Accepted: the outcome (not addressable) is correct and
the message is honest, and a second refusal path would need the parser to
retain what it deliberately filters out.
