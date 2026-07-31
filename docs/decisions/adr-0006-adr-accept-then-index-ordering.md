---
dependencies: []
last_verified:
---

# ADR-0006: adr.py accept-then-index ordering

## Status

Accepted (2026-05-15)

## Context

`adr.py` ships four subcommands: `new`, `accept`, `index`,
`resolve-todo`. The SKILL.md end-to-end recipe documents the
order `new → edit → accept → index`. The Gotchas section adds:

> If an ADR's index entry is truncated mid-abbreviation, edit the
> ADR's first Context sentence and re-run `adr.py index`.

The two pieces of guidance conflict in a real case. The "edit
the first Context sentence" remedy implies the ADR is still
mutable. But after `accept`, the ADR is supposed to be immutable
(Nygard convention: never edit an accepted ADR; supersede
instead). The recipe says to run `index` AFTER `accept`, so the
moment you discover a truncated index entry, the ADR is already
accepted.

This bit jig when accepting [ADR-0004](adr-0004-decisions-folder-naming.md)
(2026-05-12). The first Context sentence contained `e.g.` and the
index entry truncated as `... files as NNNN-<slug>.md (e.g.` —
visible only after `index`, which ran after `accept`. The fix at
the time was to edit the Context sentence anyway and rationalize
it as "Context cosmetic edits are not decision-content, so the
immutability rule doesn't apply." That worked but left the
contradiction unresolved.

ADR-0006 settles the lifecycle.

Separate from the lifecycle question, the truncation itself
([refinement-todo "sentence-end detector mishandles abbreviations"](../refinement-todo.md))
was addressed in parallel by extending `_extract_description` to
skip an explicit allowlist of abbreviations (`e.g.`, `i.e.`,
`etc.`, `Mr.`, `Dr.`, …). That patch reduces the frequency at
which the conflict bites; the lifecycle question still needs an
answer because the patch is heuristic, not exhaustive.

## Decision Options Considered

### Option A: Document the canonical order as `new → edit → index (preview) → accept → index (final)`

- **Pros:**
  - The preview pass surfaces a truncated entry BEFORE accept,
    when the ADR is still mutable. The author can iterate the
    Context sentence freely until the index entry looks right.
  - Explicit: no implicit "the immutability rule has exceptions"
    carve-out is needed.
- **Cons:**
  - Two `index` invocations per ADR for everyone, even when the
    truncation never happens (which is most of the time now that
    the abbreviation allowlist landed).
  - The current SKILL.md recipe and `adr-workflow` worked
    examples all use the single-`index` order; documentation and
    tests would need an update pass.

### Option B: Make `accept` automatically run `index` so the two are atomic

- **Pros:**
  - Single command for the common path; the user never has to
    remember `index` after `accept`.
  - The README index never goes stale relative to accepted ADRs.
- **Cons:**
  - Still doesn't fix the conflict — a truncated entry STILL
    surfaces only after acceptance (during the auto-`index`
    step), and the ADR is now immutable.
  - Couples two operations the SKILL.md intentionally keeps
    separate: `accept` mutates one file, `index` mutates the
    README. The status-board regen pattern elsewhere in jig
    (`workflow.py status-board`) keeps the equivalent operation
    explicit; consistency suggests we should too.

### Option C: Treat Context cosmetic edits as not-decision-content; carve out an immutability exception

- **Pros:**
  - Zero workflow change; codifies what we already did for
    ADR-0004.
  - Recognizes that Nygard's rule is about the **decision**, not
    the prose around it. Editing the Recommended Decision or
    Consequences post-accept changes the substance; rewording
    the Context first sentence to be index-friendly does not.
- **Cons:**
  - Introduces a fuzzy line: which sections are "decision-
    content"? Today we know Recommended Decision and Consequences
    are; Context, Status, Open questions are ambiguous.
  - Easy to abuse — someone could rationalize "this is just
    cosmetic" for a meaningful change.

### Option D: Status quo (do nothing; bite this every time)

- **Pros:** No work to do.
- **Cons:**
  - Real friction every time we accept an ADR whose Context
    sentence contains an abbreviation or runs >120 chars in a way
    the truncator dislikes. Already hit twice (ADR-0004, then
    nearly again here).
  - The contradiction in SKILL.md remains for the next reader.

## Recommended Decision

**Option A + Option C, with Option A as the procedural answer and
Option C as the codified narrow exception.**

The canonical lifecycle is:

```
new → edit → index (preview) → accept → index (final)
```

The preview pass is the front-line fix: it surfaces a truncated
index entry while the ADR is still mutable, so 95% of
abbreviation-in-Context cases are caught and resolved before
acceptance. Single-`index` runs still work for well-behaved
ADRs (and most are; the abbreviation allowlist that landed
alongside this ADR removes the most common trigger).

For the residual cases where a truncation is only visible after
acceptance (newly-discovered edge cases the abbreviation allowlist
doesn't cover), Option C applies: **edits to the Context section's
prose to fix index-rendering are not decision-content and do not
violate the immutability rule**. Edits to Status, Recommended
Decision, or Consequences DO violate immutability and require a
superseding ADR.

Option B (auto-`index` on `accept`) is rejected because it would
couple two distinct operations and still wouldn't fix the
contradiction — `accept` would auto-run `index`, find the
truncation, and the ADR would still be immutable. The lifecycle
problem is structural, not ergonomic.

## Consequences

**Becomes easier:**

- The SKILL.md end-to-end example is unambiguous: preview-then-
  accept is the documented order, with the single-`index` short-
  cut available for known-clean Context paragraphs.
- The Gotchas section keeps its truncation-recovery remedy but
  attaches it to a defined immutability exception, not an
  implicit one.
- Future contributors don't have to re-derive the same answer.

**Becomes harder:**

- The single-`index` short-cut requires authors to know their
  Context paragraph is "well-behaved" (no abbreviation outside
  the allowlist, fits in one short sentence). Authors who skip
  the preview will hit the same surprise as ADR-0004 did.
- SKILL.md needs a pass to update the worked example and add a
  brief "index preview" subsection. This ADR's acceptance commits
  us to that pass.

**Implementation status:**

- This ADR codifies the lifecycle decision. The actual SKILL.md
  prose update is a small follow-up; it is in scope for the same
  PR that lands this ADR. See the same PR's diff against
  [skills/adr-workflow/SKILL.md](../../skills/adr-workflow/SKILL.md)
  for the recipe + Gotchas changes.
- The abbreviation allowlist in `_extract_description` (resolved
  separately under refinement-todo) reduces but does not eliminate
  the truncation trigger. Both fixes (allowlist + lifecycle ADR)
  are complementary.

## Open questions

None. The lifecycle is fixed, the cosmetic-edit carve-out is
scoped to the Context section's prose explicitly, and the
abbreviation allowlist that handles the common truncation case
landed in parallel.

## Amendments

- **2026-07-31 — the preview pass now has a signal to read
  ([bug 020](../bugs/020-adr-index-summary-degradation.md) /
  [issue #140](https://github.com/ramboz/jig/issues/140)).** This ADR's
  Context notes that the abbreviation allowlist "reduces the frequency at
  which the conflict bites" but is "heuristic, not exhaustive". One case was
  worse than heuristic: a `## Context` opening that is a lead-in to a list or
  table has *no* complete sentence, so the generator emitted the lead-in
  verbatim — colon and all — or cut it at 120 characters with a trailing `…`.
  Both read like a summary, so the preview pass this ADR prescribes had
  nothing to catch: the line looked fine. `index` now writes
  `(no description)` for that case and warns on stderr naming the record and
  the reason, which makes the preview actionable rather than decorative.
  Every decision here stands unchanged — the `new → edit → index (preview) →
  accept → index (final)` order, and the narrow carve-out that Context-prose
  edits made for index-rendering are not decision-content. The remedy is
  still to reword the ADR's own opening; four records needed it (ADR-0022,
  ADR-0023, ADR-0041, ADR-0046) and were reworded under that carve-out.
