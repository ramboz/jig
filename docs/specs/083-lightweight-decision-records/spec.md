---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-06-25
use_cases: []
frame_review: true  # Phase 2 widens the load-bearing premise (recall vs scan) —
#                   # frame-critique the new premise before READY_FOR_REVIEW (ADR-0020).
---

# Spec 083 — Capturing decisions settled mid-session

## Overview

**Reframed (2026-06-25, after food-log adopter report — see Phase 2 below).**
The original problem statement scoped this to *small non-architectural* decisions
("UI strings get lost"). The food-log pilot surfaced that the real failure mode
is broader: **decisions settled mid-session get lost regardless of size, because
capture relies on the agent recalling them at reconcile.** Two real decisions in
a single food-log session — a load-bearing design choice with rejected
alternatives (ADR-worthy) and a user correction reversing a default — were both
lost, because neither the reconcile checklist nor memory-sync *remembered* to ask.
Size was never the issue; **recall-dependence** is.

This reframes the spec into two layers:
1. **Routing** (size-aware): each captured decision goes to the right home —
   ADR (load-bearing, rejected alternatives), lightweight record (settled, local,
   bounded), `refinement-todo.md` (still open), or dropped (ephemeral).
2. **Capture** (size-agnostic): a *scan* replaces recall — surface candidate
   decisions from the session automatically, then triage.

Adopter projects accumulate shipped decisions that fall outside spec slices but
carry durable rationale: brand/icon swaps, UI string/translation choices, scoped
visual decisions, *and* larger design calls made off-spec. They get lost because
no existing home fits **and** because capture depends on memory:

| Home | Why it doesn't fit |
|---|---|
| ADR | Too heavy for *local* calls — full architectural framing, drivers, options |
| `refinement-todo.md` | For *unresolved* decisions with a resolution trigger — not shipped ones |
| Per-slice deviation log | Only exists under a spec; many decisions are deliberately out-of-spec |
| Memory | Not browsable by humans or future agents without explicit recall |
| Git history / commit messages | Forensic — requires knowing what to search for |

**Phase 1 (shipped, slices 083-01..03)** added
`docs/decisions/lightweight-decisions.md` (the browsable home + routing
heuristic), scaffold seeding, and reconcile/memory-sync *nudges*. **Phase 2
(slices 083-04..07, below)** replaces the recall-dependent nudge with a
deterministic session-end **scan** and adds helper-backed routing.

**Status:** ADOPTED (2026-06-25), Phase 2 in design (slices 083-04..07 DRAFT).
Originally drafted as a pilot convention (shared with food-log, 2026-06-23). The
maintainer adopted Phase 1 (slices 083-01..03 — convention, scaffold seeding,
nudges) rather than wait for the three-adopter promotion trigger.

**Phase-2 trigger — food-log adopter report (2026-06-25):** food-log evaluated
Phase 1 against a real session and reported that the *nudge* layer is
insufficient because capture is **recall-dependent** — two decisions in one
session (one ADR-worthy with rejected alternatives, one a user correction
reversing a default) were lost since nothing *remembered* to ask at reconcile or
session-end. The report proposed a session **scan** (replace recall), a routing
**rubric** + write helper, and a companion widening of the reconciliation ADR
trigger. This spec adopts that direction as Phase 2, with one correction: the
scan runs in a **Stop hook** (jig-native, zero orchestrator-token cost — see the
Phase 2 design-decision note), not as an agent-driven transcript read.

## SPIDR analysis

**Phase 1** was Rules-axis only (what belongs in the file + when to write).
**Phase 2** adds two more axes:

- **R — Rules:** lightweight vs. ADR-worthy; the routing rubric; the widened
  reconciliation ADR trigger (083-05/083-06, single-sourced wording).
- **I — Interface:** the scan's signal patterns and candidate output shape, and
  the `decisions.py add-lightweight` helper contract (083-04/083-05).
- **Data/Path** splits stay out: the scan reuses the existing Stop-hook payload
  path (`jig-task-capture.sh`); no new data source.

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

**Routing note:** the reconcile prompt converts informal review feedback
(a loss point) into a durable record *when the decision is made during a
spec slice*. The re-review of 083-01 found this covers only the minority
case: lightweight decisions are explicitly for *out-of-spec* work, which has
no reconciliation phase. The session-end memory-sync prompt (083-03) is the
forcing function for the majority case.

### Slice 083-02 — Scaffold seeds the empty template (OQ3)

`jig:scaffold-init` seeds `docs/decisions/lightweight-decisions.md` on
greenfield scaffold, carrying the header, routing heuristic, and template
with a "no entries yet" placeholder. Drops in via the existing recursive
`templates/docs/**/*.md.template` copy — no scaffold wiring change beyond the
new template file and its test-coverage entry.

**Deliverables:**

1. `templates/docs/decisions/lightweight-decisions.md.template` — empty
   template (header + routing heuristic + field template + "no entries yet").
2. `skills/scaffold-init/test_scaffold.py` — add the new file to the
   expected-scaffolded-files assertion.

### Slice 083-03 — Memory-sync session-end prompt (OQ1)

`/jig:memory-sync` gains a candidate-item category for non-spec shipped
decisions, prompting the writer to record them in
`docs/decisions/lightweight-decisions.md`. **Conditional** (per OQ1's noise
concern): only surfaces when the session touched UI strings, visual choices,
translation corrections, or other out-of-spec product changes — not every
session end. Prose nudge in `memory-sync/SKILL.md`; no new `memory.py` helper
(the file lives in `docs/decisions/`, not `docs/memory/`, and is hand-edited).

**Deliverables:**

1. `skills/memory-sync/SKILL.md` — add the conditional candidate-item
   category + a one-line "when to invoke" note.

---

## Phase 2 — scan-triage-route (slices 083-04..07, DRAFT)

Phase 1 left capture **recall-dependent**: an agent must *remember* to record a
decision at reconcile or session-end. The food-log report (below) shows that
fails for exactly the decisions worth keeping. Phase 2 replaces recall with a
**deterministic scan**, then routes each candidate by size.

### Design decision — scan in a Stop hook, not an agent-driven transcript read

The food-log proposal framed the scan as `decisions.py scan-session <transcript>`
invoked by the agent, and flagged "long transcripts cost tokens to scan" as a
risk. **jig resolves this differently, and the risk dissolves:** jig already
ships [`hooks/scripts/jig-task-capture.sh`](../../../hooks/scripts/jig-task-capture.sh)
— a **Stop hook** that scans the completed session (regex, in Python over the
hook's stdin payload) for *task*-capture language ("we should also", "TODO:",
"don't forget") and surfaces hits as `additionalContext` for next-turn triage.
The decision-scan is its **sibling**: same Stop-hook pattern, different patterns,
different routing. Running the scan **in the hook** (out-of-band bash/python)
means only the small candidate list enters orchestrator context — never the full
transcript — so the token-cost objection does not apply, and it honors
[principle #1 (hooks deterministic / skills judgment)](../../product-vision.md)
and [context-cost discipline (spec 055/057)](../055-context-cost-discipline/spec.md).
The `decisions.py` helper still exists (083-05) for the **write** side
(`add-lightweight`), where determinism is wanted; the *read/scan* side is the hook.

### Design constraints (locked in, all phases)

- **Owner-gated writes.** The scan *proposes*; nothing is written without
  confirmation — identical to `jig-task-capture.sh` and memory-sync. A noisy
  scan is acceptable only because it never auto-writes.
- **Provenance mandatory.** Every surfaced candidate carries *who decided*
  (user vs agent) **and** the quoted evidence line. In the food-log session the
  key call was the *user's* correction, not the agent's — a log that blurs that
  is worth less.
- **Precision over recall on the filter.** Better to miss a marginal decision
  than bury real ones under "let's do X" chatter. The dedup-against-recorded
  step keeps repeat runs quiet.

### Slice 083-04 — Session decision scan (Stop hook)

A `jig-decision-capture.sh` Stop hook modeled on `jig-task-capture.sh`, scanning
the session for decision signals (highest-precision first):
1. **AskUserQuestion answers** — explicit user picks.
2. **User corrections / overrides** — "X should not be the default", "do A instead".
3. **Agent statements of settled choices** — "chose A over B", "rejected because".
4. **Reversed defaults.**

Output: candidate list, each with a quoted evidence line, turn reference, and
*who decided*. Dedups against already-recorded decisions (existing ADRs,
`lightweight-decisions.md`, `refinement-todo.md`) so triaged-away items don't
re-surface. The scan logic may live in `decisions.py scan-session` invoked **by
the hook** (testable in isolation) rather than inline bash.

**AC:** over a transcript fixture containing a representative session, it
surfaces the load-bearing design choice, the chosen-alternative decision, and the
reversed-default correction; it does **not** surface ephemera ("let me run the
tests"). Provenance (who + quote) present on every candidate.

### Slice 083-05 — Routing rubric + `decisions.py add-lightweight` helper

The triage step deciding where each candidate lands:

| Route | Criterion |
|---|---|
| **ADR** | load-bearing design choice with rejected alternatives, OR boundary/contract/policy change |
| **lightweight record** | settled, local, bounded (screen/component/string), no real alternatives |
| **refinement-todo** | still unresolved |
| **drop** | ephemeral / trivial |

Ships `decisions.py add-lightweight` (idempotent append in the template format,
like `memory.py`'s helpers) so Phase 1's nudge-only file gains the helper-backed
determinism the rest of jig has. The ADR-branch criterion **must use the same
wording** as the 083-06 reconciliation trigger so they agree by construction.

### Slice 083-06 — Companion: widen the reconciliation ADR trigger (needs its own ADR)

Today the reconcile checklist asks *"did module boundaries or public contracts
change?"* to trigger an ADR. Widen it to **also** ask *"was a load-bearing design
choice with rejected alternatives made, even if no boundary changed?"* — the
clause that would have caught food-log's lost ADR-worthy decision at reconcile.
Touches `docs/workflow.md` + `skills/spec-workflow/SKILL.md` reconcile checklists.

Because this changes a **load-bearing lifecycle policy** (when an ADR is
required), it warrants **its own ADR** — reserve the number via `adr.py new` at
implementation time (do **not** mint a number from a stale local tree). The ADR's
trigger wording and 083-05's rubric ADR-branch are the *same sentence*, single-sourced.

### Slice 083-07 — In-flight decision stubs (DEFERRED)

The most robust capture: a hook on AskUserQuestion answers and on user override
of a stated default writes a one-line stub to a session scratch log *the moment
the decision settles*; triage reads the scratch log, depending on neither recall
nor a perfect transcript scan. **DEFERRED** — adds in-flight overhead, and
083-04's session-end scan may be sufficient. **Resolution trigger:** pilot
evidence that the 083-04 scan misses in-flight decisions (e.g. a decision made
and then talked-past in the same session that the end-of-session regex doesn't
catch).

## Assumptions

- Adopter projects that have a `docs/decisions/` directory (i.e. are
  jig-scaffolded past the seed stage) are the primary target. Projects
  without that directory are out of scope for this spec.
- The file does not need machine-readable structure at this stage —
  markdown prose with a consistent section template is sufficient.
- The reconcile prompt does not need to be enforced by `workflow.py` at
  this stage (no gate, no blocking). It's a checklist nudge, not a
  transition gate.
- **(Phase 2)** The Stop-hook stdin payload exposes enough session content to
  scan for decision signals. **Grounding:** `jig-task-capture.sh` already reads
  `messages[].content` from that payload today — 083-04 reuses the same source.
  *Risk if false:* a host whose Stop payload omits message bodies would degrade
  the scan; 083-04 must verify the payload shape per host (Claude + Codex) and
  fall back to the nudge (Phase 1) where unavailable.

## Risks (Phase 2 — from the food-log report, honestly carried)

- **Scan noise.** Many "let's do X" lines aren't durable decisions. Mitigated by
  precision-first patterns, dedup-against-recorded, and the owner-gate (never
  auto-writes). Not a hard guarantee.
- **Token cost of scanning.** Real *if the agent reads the transcript* — which is
  why the scan runs in the Stop hook out-of-band (only the candidate list reaches
  context). This is the design correction over the food-log proposal.
- **ADR/lightweight boundary still needs judgment.** The rubric (083-05) narrows
  it but doesn't eliminate the judgment call; the owner-gate is the backstop.
- **In-flight decisions talked-past in one session** may evade an end-of-session
  scan — the explicit resolution trigger for the DEFERRED 083-07 stub capture.

## Open questions (resolved 2026-06-25)

All four resolved by maintainer decision when jig elected to adopt the
convention now rather than wait for pilot evidence.

**OQ1 — memory-sync noise → RESOLVED: yes, prompt (conditionally).**
`/jig:memory-sync` prompts for missed non-spec shipped decisions at session
end, but **only when the session touched UI strings, visual choices,
translation corrections, or out-of-spec product changes** — not every session
end. This is the load-bearing forcing function: the reconcile-checklist prompt
(083-01) only fires during a spec slice's reconciliation, but lightweight
decisions are *for out-of-spec work*, which has no reconciliation phase.
Shipped in slice **083-03**.

**OQ2 — template fields → RESOLVED: keep `Commit`, mark optional.** The
field stays in the template, reframed as *"optional — git SHA or PR; may be
added retroactively."* Value when present (links decision → diff for
archaeology) is high; cost when blank is zero. Pilot data from food-log may
still drop it later if it proves universally blank — a cheap reversal.
`Scope` remains the key ADR differentiator (local, not architectural).

**OQ3 — scaffold seeding → RESOLVED: yes, scaffold seeds it.**
`jig:scaffold-init` seeds the empty template on greenfield scaffold (header +
routing heuristic + field template + "no entries yet"). A small always-present
file is cheaper than a broken first-write, and it makes the convention
discoverable. Shipped in slice **083-02**.

**OQ4 — routing rule → RESOLVED: adopt the proposed heuristic.**
*Lightweight iff (a) it doesn't change a module boundary, public contract, or
cross-cutting policy AND (b) a future agent or maintainer would need to know
it to avoid undoing it.* ADR if (a) fails; refinement-todo if the decision is
still open; nothing if already obvious from the code. Baked verbatim into the
"When to write here vs. an ADR" section of
`docs/decisions/lightweight-decisions.md` (slice 083-01, tightened in the
083-02/03 sweep).
