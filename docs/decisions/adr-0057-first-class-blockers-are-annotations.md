---
status: Accepted
dependencies: []
last_verified: 2026-08-15
frame_review: true
---

# ADR-0057: First-class blockers are an annotation on in-flight slices, not a lifecycle state

## Status

Accepted (2026-08-15)

## Context

jig has no first-class way to record that a slice is actionable but stuck, so a
project's live blocker count can only be approximated from unrelated proxies.

jig tracks lifecycle **state** (`DRAFT → … → DONE`, plus `DEFERRED` / `ABANDONED`)
and ordering **dependencies** (`dependencies:` on each slice), but it has **no
first-class notion of "this work is started and cannot proceed, and here is what
it is waiting on."** Downstream consumers that want to answer *"how many blockers
does this project have right now?"* — the motivating case is the Gauge portfolio
dashboard's "blocked" count — must approximate it from a grab-bag of proxies:

- `DEFERRED` slices carrying a `**Resolution trigger:**` line,
- deferred decisions in `docs/refinement-todo.md`,
- unmet slice `dependencies:`,
- the legacy Compass narrative `blockers` array (only present for
  legacy-Compass sources).

Every one of these conflates *parked-by-choice* (`DEFERRED`) or *not-yet-started
ordering* (`dependencies:`) with *a live work item that is stuck*. A slice can be
`IN_PROGRESS`, actively claimed, and waiting on an owner decision — and today
nothing records that distinctly. The dashboard is forced to render an
approximate, hand-labelled count.

Grounding — what already exists (probed 2026-08-15, `skills/spec-workflow/workflow.py`):
- Body-line annotations are read by regex extractors keyed to a `**Label:**`
  convention: `_extract_resolution_trigger` (`workflow.py:1544-1554`,
  `**Resolution trigger:**`) and `_extract_abandonment_reason`
  (`workflow.py:1557-1568`, `**Abandonment reason:**`).
- Per-slice frontmatter fields are read in `collect_slices`
  (`workflow.py:2063-2117`): it already returns a 7-tuple carrying `status`,
  `resolution_trigger`, `kind`, `claimed_by`, `abandonment_reason` — `claimed_by`
  (`workflow.py:2112`) is exactly the shape a new `blocked_by:` field would take.
- The status board renders parked work in dedicated sections via
  `render_deferred_table` (`## Deferred slices`, `workflow.py:2231`) and
  `render_abandoned_table` (`## Abandoned slices`, `workflow.py:2271`), each a
  `| Spec | Slice | <context> |` table appended after the active table.

So both candidate mechanisms — an annotation *or* a state — are cheap to build
on the existing patterns. The decision is which one is *correct*, because it is a
convention other tools will depend on and is therefore expensive to reverse.

## Decision Options Considered

### Option A: A blocker is a new lifecycle **state** (`BLOCKED`)
A slice moves `IN_PROGRESS → BLOCKED` and back, like `DEFERRED`.
- **Pros:** Symmetric with `DEFERRED` / `ABANDONED`; the state machine makes
  "blocked" mutually exclusive with other states, so a count is a trivial state
  filter; transitions give a natural audit point.
- **Cons:** A blocked slice is still *in progress and claimed* — modelling it as a
  distinct state fights that reality. It would need new transition edges, new
  FROM-state gate rules (like `DEFERRED`'s outbound restriction), and a decision
  about what happens to the `claimed_by:` claim and the review-evidence gates
  while "blocked." It also forces a slice to be *either* making-progress *or*
  blocked, when the honest state is "in progress, and one thing is stuck." High
  blast radius on the lifecycle graph and every helper that switches on `status`,
  to record one advisory fact.

### Option B: A blocker is an **annotation on an actionable slice**
A `blocked_by:` frontmatter field (names what it is blocked on) plus a
`**Blocked:**` body line (human prose naming the unblock condition), valid on any
slice in an **actionable** state — one whose next step is real work that is
currently prevented: `READY_FOR_IMPLEMENTATION` (ready to start) or a working
state (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`, started).
Clearing it is removing the annotation.
- **Pros:** Additive — the lifecycle graph, transition edges, gate predicates,
  and claim model are all untouched. Mirrors the two conventions jig already has
  (`claimed_by:` frontmatter + `**Resolution trigger:**` / `**Abandonment
  reason:**` body lines), so it reuses `collect_slices` + a `render_*_table` with
  no new concepts. It records the honest state ("actionable **and** stuck on X")
  rather than overwriting progress with a blocked flag. A count is
  "actionable-state slices with a non-empty `blocked_by:`" (see the Recommended
  Decision for the authoritative state set).
- **Cons:** Not enforced — nothing *stops* work on a slice marked blocked, and
  nothing *requires* the annotation be removed when the blocker clears; it relies
  on author diligence (the same trust model as `claimed_by:` and the
  `**Resolution trigger:**` conventions). No transition-time audit event.

## Recommended Decision

**Option B — a blocker is an annotation on an actionable slice, not a lifecycle
state.**

- **`blocked_by:`** — an optional frontmatter field on a slice in an
  **actionable** state: `READY_FOR_IMPLEMENTATION` **or** a working state
  (`READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` / `RECONCILED`). Its value is a
  short free-text string naming what the slice is blocked on (an owner decision,
  another slice id, an external dependency, a review). It is the machine-readable
  signal.
- **`**Blocked:**`** — a body line (same shape as `**Resolution trigger:**`)
  carrying the human explanation and, by convention, the condition that would
  clear it.
- **Blocked count** = the number of actionable-state slices with a non-empty
  `blocked_by:`. The status board surfaces them in a `## Blocked slices` section
  (mirroring `## Deferred slices`), which is the committed consumer.
- **Clearing** = remove the annotation. No separate trigger machinery (unlike
  `DEFERRED`, which is a whole state that must *resurface*); a blocker is a
  transient fact about would-be-actionable work.

**Why the boundary is "actionable," not "started."** The motivating question is
*"how many blockers does this project have right now?"* — which honestly includes
a slice that is **ready to start but cannot** (e.g. a `READY_FOR_IMPLEMENTATION`
slice waiting on an owner decision or an external gate), not only started-and-stuck
work. So the scope is every state whose *next step is real work that is now
prevented*. It deliberately **excludes**: `DRAFT` (its next step is shaping, which
is always available — not blocked), `DONE` (finished), and `DEFERRED` /
`ABANDONED` (parked or dropped *by choice* — see below). `blocked_by:` is
independent of `claimed_by:`: a `READY_FOR_IMPLEMENTATION` blocker is unclaimed
(the pickup-queue state releases the claim), and that is fine — the annotation
records "this would be pickable but is stuck," which is exactly the count's intent.

A blocker is deliberately distinct from its neighbours: **`DEFERRED`** is
parked-by-choice (we chose not to prioritise it — *not* that we are prevented);
**`dependencies:`** is not-yet-started slice-id *ordering*; a **blocker** is
*actionable-but-prevented, waiting on a named thing we would act on now.* This is
what lets the count retire the four proxies rather than re-approximate the
ready-but-stuck class from them.

The typed-reason question (a closed vocabulary for `blocked_by:` —
owner / dependency / external / review) is **deferred**: v1 is free-text, and a
typed vocabulary can be grown additively later without breaking the count.

## Consequences

**Becomes easier:**
- A downstream dashboard (Gauge) can read a clean, honest blocked count from one
  named board section instead of approximating from four proxies — *including*
  the ready-but-stuck class (a `READY_FOR_IMPLEMENTATION` slice waiting on a
  decision), which the "actionable" boundary covers and the started-only boundary
  would have left to the proxies.
- The distinction between *parked*, *ordered*, and *stuck* becomes recordable.
- The convention rides existing machinery (`collect_slices`, a `render_*_table`,
  a `**Label:**` extractor), so the implementation is small and low-risk.

**Becomes harder:**
- Nothing enforces the annotation's accuracy — a stale `blocked_by:` left on a
  slice whose blocker cleared will over-count until an author removes it. This is
  the accepted trust model; the mitigation is a `spec_lint` nudge (a `blocked_by:`
  on a **non-actionable** state — `DRAFT` / `DONE` / `DEFERRED` / `ABANDONED` —
  is almost certainly a misfiled dependency/deferral), not a gate.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

- **A1 — jig has no existing `Blocked` / `blocked_by` convention (grounded by
  enumeration, 2026-08-15).** Two searches close the set. (1) *Text convention:*
  `grep -rIn 'blocked_by'` and `grep -rIn '\*\*Blocked'` across `docs/specs/**`,
  `skills/**`, `scripts/**` return **empty** (excluding this ADR and spec 111) —
  no slice or helper carries the field or the body line today. (2) *Recognized
  frontmatter keys:* the set of frontmatter fields the lifecycle code reads is
  closed by syntax — every key flows through a `fm_fields.get("<key>")` /
  `fields.get(CLAIM_FIELD)` call in `workflow.py`, and enumerating them yields
  exactly `status`, `frame_review`, `arch_review`, `code_health_review`,
  `design_review`, `dependencies`, `kind`, and `claimed_by` (`CLAIM_FIELD`,
  `workflow.py:4173`) — **not** `blocked_by`. So the pre-existing blocker-shaped
  tokens are only `**Resolution trigger:**` (on `DEFERRED` slices),
  `**Abandonment reason:**`, refinement-todo deferred decisions, `dependencies:`,
  and the legacy Compass narrative `blockers` array — `blocked_by:` is genuinely
  new, not a redefinition.
- **A2 — the consumer's "blocked count" includes ready-but-stuck work, not only
  started-and-stuck (assumption, not grounded).** The motivating question ("how
  many blockers now?") is read at face value: a slice that is ready to start but
  prevented counts as blocked. Gauge's exact count semantics were **not** probed
  (its source is a separate consumer repo). The "actionable" boundary
  (`READY_FOR_IMPLEMENTATION` + working states) is chosen to satisfy that
  face-value reading. **Kill condition:** if Gauge (or another primary consumer)
  turns out to want a *started-only* count, narrow the boundary to the working
  states; if it wants *all* stuck items including `DRAFT`/`DEFERRED`, that is a
  different signal and argues for revisiting the taxonomy, not just the boundary.

## Kill criteria

- If a real consumer needs *enforcement* — work must actually stop on a blocked
  slice, or the blocker must gate a transition — the annotation model is
  insufficient and this decision should be revisited toward a state (Option A) or
  a gate.
- If, in practice, stale `blocked_by:` annotations make the count untrustworthy
  often enough that the `spec_lint` nudge does not fix it, revisit toward a
  transition-anchored mechanism that clears the annotation automatically.

## Open questions

- The typed-reason vocabulary for `blocked_by:` (owner / dependency / external /
  review) is deferred to a later additive refinement — recorded here so the v1
  free-text shape does not foreclose it.
