# Worked example — SPIDR splitting

One applied example per axis, then a jig-native dogfood case where
spec 017 used three different axes across its three slices.

## Why SPIDR exists

The goal of SPIDR is **vertical slicing**: every slice crosses all
layers (data, logic, interface) and delivers something a user can
observe end-to-end. AI's default failure mode is **horizontal
phasing** — "phase 1: schema, phase 2: API, phase 3: UI" — which
delays end-to-end feedback and creates large rework when integration
reveals problems. The five SPIDR techniques are five different ways
to split a story so each slice stays vertical.

Priority order when picking an axis: try **P / I / D / R first**;
reach for **S (Spike)** only when none of the other four apply.

## P — Path (happy path first)

**Story.** "User uploads a video."

**Naive horizontal split.** Phase 1: upload pipeline. Phase 2:
progress UI. Phase 3: error handling. — Phase 1 has nothing the user
can use.

**Path-axis split.**
1. **Happy path.** Valid file, network works, single user. End-to-end
   from form submit to "upload complete" message.
2. **Error paths.** Network failure, file too large, unsupported
   codec.
3. **Concurrent uploads.** Progress UI handles multiple in flight.

**Why it works.** Each slice delivers something a real user can do.
After slice 1, a real user uploads a real video and sees real
success — even if the system is brittle to edge cases.

## I — Interface (minimal first)

**Story.** "User can search products."

**Interface-axis split.**
1. **Plain HTML form, text results.** Typed query, server-rendered
   list, no filters, no autocomplete.
2. **Filters.** Facet sidebar (category, price range).
3. **Suggestions.** Autocomplete dropdown.

**Why it works.** The simplest interface still exercises the full
search pipeline. Polish layers stack on top of an already-shipping
system.

## D — Data (less data first)

**Story.** "Support video uploads in any format."

**Data-axis split.**
1. **MP4 only.** Codec gate refuses anything else with a clear error
   message.
2. **MP4 + WebM.** Codec list grows; same pipeline.
3. **All 17 supported formats.** Full table-driven decoder dispatch.

**Why it works.** The pipeline shape is the same for every codec; the
codec list is data. Shipping MP4 first proves the pipeline; the rest
is filling in a table.

## R — Rules (simple rules first)

**Story.** "US sales-tax calculation supports all 50 states."

**Rules-axis split.**
1. **Flat-rate states** (e.g. CA, TX). Single rate per state.
2. **Tiered states.** State rate + county rate.
3. **Cities with overrides.** State + county + city rate.

**Why it works.** The engine, data model, and UI are all in place
after slice 1; later slices add rules to an already-shipping system.

## S — Spike (last resort)

**When to use.** You can't make a P / I / D / R call because you
don't yet know enough about the problem space. Example: "Should we
use commercial captioning software or build our own?" There's no way
to split that into vertical slices until you've evaluated the
alternatives.

**What a spike delivers.** A written conclusion and a decision —
not code. If you're writing implementation, you're past the spike.

**Anti-pattern.** Spiking instead of splitting. "Let me research
this first" is often horizontal phasing in a trench coat — the agent
intends to follow up with "now let me build it" as a single slab.
That's the failure mode the priority rule guards against.

## Jig-native dogfood — spec 017's three-axis split

Spec 017 (`/jig:vision-elicitation`) shipped three active slices,
each labeled with a distinct SPIDR axis. This is the clearest
in-repo example of one spec using multiple axes intentionally.

- [**slice-01** — Data axis](../../docs/specs/017-vision-elicitation/slice-01-vision-template-and-architecture-slots.md).
  Template surgery: the elicitation slots in `architecture.md` and
  the new `product-vision.md` artifact. **What data the workflow
  produces** was the deliverable.
- [**slice-02** — Interface axis](../../docs/specs/017-vision-elicitation/slice-02-vision-elicitation-skill-core.md).
  The user-facing skill: SKILL.md + questions.md + worked examples.
  **How the user interacts** with the elicitation flow was the
  deliverable.
- [**slice-03** — Rules axis](../../docs/specs/017-vision-elicitation/slice-03-re-runnable-with-edit-detection.md).
  Re-run mechanics: hash-based edit detection + per-section refresh.
  **New behavior over the existing artifact + interface** was the
  deliverable.

Each slice delivered end-to-end user value on its own. After 01 the
user has a populated template. After 02 they can fill it via the
skill. After 03 they can re-run and have the skill skip
already-edited sections. **None** of the slices was "build the
infrastructure for the next slice" — that is what avoiding
horizontal phasing looks like in practice.

## Anti-patterns to flag during review

- **Slice 1 = "set up the database schema."** Horizontal phasing.
  Re-split: which user-facing thing reads from this schema first?
- **Slice 1 = "research the right library."** Spike masquerading as
  a feature slice. Either it's a real spike (with a written decision
  as the deliverable) or it's pre-work that belongs inside the first
  real slice.
- **All five slices use the same axis.** You found one axis and
  stopped — the work probably has more than one. Re-check.
- **Spike first, build later.** Inverts the SPIDR priority. Try P /
  I / D / R first; reach for Spike only if all four genuinely don't
  apply.
