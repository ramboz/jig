---
status: DRAFT
dependencies: []
last_verified:
use_cases: []
---

# Spec 083 — Lightweight decision records for non-spec UI/product changes

## Overview

Adopter projects accumulate small shipped decisions that fall outside spec
slices but carry durable rationale: brand/icon swaps, cosmetic CSS polish,
UI string or translation choices, scoped visual decisions, and
"future mockups should/should not override this" notes. These decisions
get lost across sessions because no existing home fits them well:

| Home | Why it doesn't fit |
|---|---|
| ADR | Too heavy — full architectural framing, decision drivers, options considered |
| `refinement-todo.md` | For *unresolved* decisions with a resolution trigger — not shipped ones |
| Per-slice deviation log | Only exists under a spec; many UI/product decisions are deliberately out-of-spec |
| Memory | Not browsable by humans or future agents without explicit recall |
| Git history / commit messages | Forensic — requires knowing what to search for |

**This spec adds `docs/decisions/lightweight-decisions.md`** as a
browsable, project-local file for small shipped decisions. Markdown-only
convention; no Python helper yet. The reconcile checklist gains an
explicit prompt to capture missed decisions.

**Status:** DRAFT — shared with an adopter project (food-log, 2026-06-23)
to pilot the convention before jig formally adopts it. Trigger for
promotion: two more independent adopter reports (three total) where
non-spec decisions are lost, OR one jig dogfooding incident where a
resolved decision is forgotten and causes rework.

## SPIDR analysis

Single small spec — Rules axis only (what belongs in the file + when to
write to it). No Path or Interface splits warranted at this scale.

**R — Rules:** what makes a decision lightweight vs. ADR-worthy? When
does the reconcile step prompt? What fields does the file carry?

## Slices

### Slice 083-01 — Convention + seed file + reconcile prompt

One vertical slice: the convention itself (markdown template), the seed
file for adopters, and a reconcile-checklist addition that prompts for
missed decisions. These are inseparable — the convention without the
prompt is easy to forget; the prompt without a destination has nowhere
to send writers.

**Deliverables:**

1. `docs/decisions/lightweight-decisions.md` — seeded as an example
   file for the pilot project; the jig scaffold template gets the empty
   template in a follow-on slice (see open questions).
2. `docs/decisions/README.md` — a brief entry linking to the new file
   and explaining what lightweight decisions are.
3. `docs/workflow.md` Reconciliation checklist — a new item:
   *"Lightweight decisions — did this session's review or implementation
   settle any non-spec decisions (UI strings, visual choices, translation
   corrections, scoped brand/icon calls)? If yes, record them in
   `docs/decisions/lightweight-decisions.md`."*

**Routing note:** the reconcile prompt is the load-bearing mechanism.
It's what converts informal review feedback (the current loss point)
into a durable record. Without it, the file exists but writers have no
forcing function.

## Assumptions

- Adopter projects that have a `docs/decisions/` directory (i.e. are
  jig-scaffolded past the seed stage) are the primary target. Projects
  without that directory are out of scope for this spec.
- The file does not need machine-readable structure at this stage —
  markdown prose with a consistent section template is sufficient.
- The reconcile prompt does not need to be enforced by `workflow.py` at
  this stage (no gate, no blocking). It's a checklist nudge, not a
  transition gate.

## Open questions (park for after pilot evidence)

**OQ1 — memory-sync noise:** should `/jig:memory-sync` prompt for
missed non-spec shipped decisions at session end, in addition to the
reconcile-checklist prompt? Risk: adds noise to every session end, even
when no UI/product work happened. Lean: only prompt when the session
touched UI strings, visual choices, or out-of-spec changes. Defer until
pilot generates evidence on whether the reconcile prompt alone is enough.

**OQ2 — template fields:** the suggested minimal set is:

```markdown
### [Date] — [Short title]
**Decision:** _what was decided_
**Context:** _why — constraint, user feedback, design call_
**Scope:** _which screen / component / string / asset — not product-wide_
**Commit:** _git SHA or PR, if available_
```

`Scope` is the key differentiator from ADRs — it marks the decision as
local, not architectural. Pilot data from food-log should validate
whether `Commit` is worth the friction or gets left blank.

**OQ3 — scaffold seeding:** should `jig:scaffold-init` create an empty
`docs/decisions/lightweight-decisions.md` on greenfield scaffold? Or
should it be created only on first use (when a writer would otherwise
have to create it manually)? Lean: scaffold seeds it — an empty file
with the template and a "no entries yet" placeholder is cheaper than
a broken first-write. But this adds a file to every scaffolded project
even when never used. Defer to after pilot.

**OQ4 — routing rule:** what makes a decision lightweight vs. ADR-worthy?
Proposed heuristic: *lightweight iff (a) it doesn't change a module
boundary, public contract, or cross-cutting policy AND (b) a future
agent or maintainer would need to know it to avoid undoing it.* ADR if
(a) fails. Refinement-todo if the decision is still open. Nothing if
it's already obvious from the code. Validate against pilot examples.
