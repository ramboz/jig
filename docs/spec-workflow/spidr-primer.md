# SPIDR primer

> Five techniques for splitting a story into vertical slices. The "S"
> axis (Spike) is the last resort — try Path / Interface / Data / Rules
> first. This primer is the canonical reference; the live worked example
> per axis lives at
> [`skills/spec-workflow/worked-example-spidr-split.md`](../../skills/spec-workflow/worked-example-spidr-split.md).

## The five axes

| Axis | What it splits | First-slice rule of thumb |
|---|---|---|
| **S — Spike** | An unknown that prevents picking any of the other four axes | Last resort. See "When to use a spike" below. |
| **P — Path** | Alternative paths through the story | Happy path first; error / edge paths later. |
| **I — Interface** | UI / platform / channel surfaces | Minimal interface first; polish later. |
| **D — Data** | Data subsets or formats | Less data first; broaden coverage later. |
| **R — Rules** | Business rules / branching logic | Simplest rule first; edge rules later. |

Each slice must be **vertical**: touches every layer (data → logic →
interface) and delivers something a user can observe end-to-end.
Horizontal phasing ("phase 1: schema, phase 2: API, phase 3: UI") is
the default AI failure mode — every slice must dodge it.

## When the S axis fires: `kind: spike`

When SPIDR's S axis fires during decomposition — i.e., none of P / I /
D / R apply because the team doesn't yet know enough to pick — the
resulting slice **must be marked `kind: spike`** in its frontmatter.
This is the machine-readable signal that lets tooling (`spec_lint.py`
enum validation, status-board markers, future helpers) treat the slice
as research, not feature work.

A `kind: spike` slice carries four extra labelled blocks alongside the
standard Goal / DoR / AC / DoD scaffolding:

```markdown
**Question:** _One sentence stating the open question. Set at DRAFT._

**Time-box:** _Explicit budget — e.g., "1 day", "4 hours". Set at DRAFT._

**Findings:** _Bullet evidence collected during the spike. Filled
during IN_PROGRESS._

**Outcome:** _One of: `ADR-NNNN created` / `spec NNN-NN unblocked` /
`abandoned (reason)`. Multiple outcomes separated by `;`
(e.g., `ADR-0007 created; spec 030-02 unblocked`). Set at DONE._
```

`spec_lint.py` validates the `kind:` enum (allowed values: `spike`,
`feature`) as a hard error, and soft-warns when a `kind: spike` slice
is missing any of the four labels. Mid-flight spikes legitimately have
empty Findings / Outcome — the warning names the missing labels so the
author knows what's still pending; it never blocks landing.

### Always nested, never standalone

Spike slices live **inside a real spec** — never as a standalone
`docs/spikes/` artifact. The 1-slice-spec case ("we have an
investigation but no clear downstream spec yet") collapses to
"spawn a normal spec where the only slice is `kind: spike`." This
forces the investigator to articulate the downstream change up front
and keeps jig's numbered-family count at two (specs+slices, ADRs).

See [`skills/spec-workflow/SKILL.md`](../../skills/spec-workflow/SKILL.md)
(Spike slices subsection) for the always-nested rule plus the
abandoned-outcome manual-reshape failure mode.

### Worked example

A short illustrative spike from a plausible spec, showing the four
labels filled end-to-end:

> **Question:** Should the new captioning pipeline use commercial
> service X or build on the open-source stack Y?
>
> **Time-box:** 1 day.
>
> **Findings:**
> - X bills per minute of audio and forbids on-prem; Y self-hosts but
>   needs a GPU class our deploy targets don't all carry.
> - X's accuracy on the validation set is 4 WER points better than Y's
>   default configuration; Y closes most of the gap after a domain LM
>   fine-tune, but the fine-tune is a 2-week project.
>
> **Outcome:** ADR-0007 created (selects service X for v1; revisits if
> per-minute costs exceed the projected ceiling).

This spike's deliverable is the ADR, not code. If the same session
produces an implementation slice, that's a separate slice — spikes
output decisions, features output behavior.

## Priority order

Reach for axes in this order:

1. **R / D / I / P** (any of the four) — split before spiking.
2. **S — Spike** — only when none of the four apply.

AI agents default to spiking too eagerly. The bias to resist is "let
me research this first" as a prelude to "now let me build it as one
big slab" — that's horizontal phasing in a trench coat. If the spike
would conclude with "now ship the implementation," the implementation
is the slice, and the research goes inside slice 1.

## Anti-horizontal-phasing rule

Every slice must touch the user-facing layer and deliver end-to-end
value. A slice that touches only the database, only the parser, or
only the API is horizontal phasing — re-split along a vertical axis.
The `Anti-horizontal-phasing check:` line in the slice template asks
the author to state, in one sentence, what end-to-end observable value
a user gets after this slice lands. If the answer is "intermediate
state for the next slice," the slice is mis-shaped.
