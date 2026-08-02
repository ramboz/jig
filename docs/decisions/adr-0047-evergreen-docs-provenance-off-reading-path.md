---
status: Accepted
dependencies: []
last_verified:
frame_review: true
---

# ADR-0047: Evergreen docs carry provenance off the reading path

## Status

Accepted (2026-08-02)

## Context

jig's front-door docs — `product-vision.md`, `architecture.md`, `workflow.md`,
`philosophy.md`, `adoption-readiness.md` — are meant to read as **evergreen
prose**: a newcomer opens them to learn what jig is and how it works *today*,
not how it got here.

In practice they had accreted a dense layer of inline provenance. Every spec or
ADR that touched a doc left a citation behind — `(spec 083-07)`, `(ADR-0045)`,
`(bug 014)`, `(EngTip #23)` — plus `## Amendment` / "as amended by" addendums
patched mid-prose. This is a natural byproduct of the reconciliation sweep:
ADR-0010 keeps live prose inline-correct, and the habit of stamping the
originating record beside each correction turned every edit into a footnote in
the body text. Measured density on the three worst offenders:

| Doc | Lines | spec refs | ADR refs | other |
|---|---|---|---|---|
| `product-vision.md` | 270 | 14 | 18 | — |
| `workflow.md` | 654 | 13 | 24 | 2 bug, 2 EngTip |
| `architecture.md` | 379 | 15 | 15 | — |

The cost is onboarding friction. The reader must parse a citation trail to
extract the evergreen claim; run-on sentences carry two or three spec numbers;
some passages exist *only* as provenance (e.g. a "self-coherence note (spec
022-02)" explaining why a doc slot is shaped the way it is). The prose reads
like a changelog of its own edits rather than a description of the system.

Provenance is not worthless — it is simply **not evergreen content**. It belongs
to the records that own it: the ADR index, the spec status board, the bug board,
and `/jig:explain`, which already exist to answer "which decision established
this?" on demand and off the hot path.

This is a decision about jig's own constitutional docs — load-bearing, with
rejected alternatives a future session would need to know about to avoid
re-patching the prose — so it is recorded rather than applied silently.

## Decision Options Considered

### Option A: Drop inline provenance; lean on the indexes (chosen)
Evergreen docs state what is true now in plain prose. Inline spec / ADR / bug /
EngTip citations are removed from the reading path. Provenance stays reachable
through the ADR index, the spec and bug status boards, `/jig:explain`, and git
history. Navigational cross-document links (`see architecture.md`,
`see product-vision.md § Design principles`) are kept — those orient the
reader and are not provenance.
- **Pros:** cleanest prose; lowest onboarding barrier; no duplicated map to
  drift; the indexes are already the canonical provenance surface.
- **Cons:** you can no longer trace an individual sentence to its originating
  spec by reading the doc alone; recovery is via the indexes / `/jig:explain` /
  git blame.

### Option B: Per-doc "Provenance / further reading" footnote trailer
Keep the prose clean but append a claim → spec/ADR map at the foot of each doc.
- **Pros:** preserves the direct sentence → decision link off the reading path.
- **Cons:** duplicates the ADR/spec indexes, which already are that map; a
  second copy drifts and re-introduces the maintenance burden the reconciliation
  sweep already carries. Trades one patching habit for another.

### Option C: Keep light navigational links only (status quo minus the worst)
Strip the addendum notes and double/mid-sentence citations but leave a
scattering of inline links.
- **Pros:** least disruptive.
- **Cons:** the line between "navigational" and "provenance" citation is fuzzy,
  so the docs stay partially patched and drift straight back to the status quo.

## Recommended Decision

**Option A.** Evergreen docs carry no inline provenance; they read as prose about
the current system. Provenance lives in the records and indexes that own it.

Scope — the five evergreen docs: `product-vision.md`, `architecture.md`,
`workflow.md`, `philosophy.md`, `adoption-readiness.md`. This ADR does **not**
touch specs, ADRs, bug records, the status boards, `refinement-todo.md`,
`inbox.md`, or the memory files — there, provenance *is* the content and stays.

Kept in the prose: cross-document navigational links, and links to the canonical
indexes/boards themselves (those are the reachability mechanism, not inline
citations).

## Consequences

**Becomes easier:**
- Reading the front-door docs cold — the evergreen claim is the sentence, not a
  claim wrapped in citations.
- Keeping the docs honest: prose describes current reality, and there is one
  obvious place (the indexes) for "how did we get here."

**Becomes harder:**
- Tracing a single sentence back to its originating spec from the doc alone.
  Recovered via the ADR index, the status boards, `/jig:explain <artifact>`, and
  git blame.
- The reconciliation sweep's doc-update step must now correct the prose *without*
  stamping a citation into it. The originating spec/ADR already links forward to
  the surfaces it changed; that forward link plus the indexes carry the
  provenance the inline citation used to.

## Assumptions

None load-bearing — this is an editorial/structural convention over prose we
control, verified by reading the affected docs, not a claim about a runnable
surface.

## Kill criteria

- If a reader genuinely needs per-sentence provenance often enough that the
  indexes and `/jig:explain` prove insufficient, revisit Option B (a footnote
  trailer) for the specific doc where the need is real.

## Open questions

None.
