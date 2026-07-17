---
status: IN_PROGRESS  # 083-08 (Codex host-validation handoff) remains DRAFT —
#                    # deferred to the maintainer on Codex (spec stops at 083-07
#                    # for the Claude-side build).
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
2. **Capture** — a **three-way coverage map** (corrected over two frame-critique
   rounds, 2026-06-25). No single mechanism covers the space; each owns a cell:

   | Decision is… | …made **in-spec** (slice exists) | …made **out-of-spec** (no slice) |
   |---|---|---|
   | **lexically detectable** (AskUserQuestion answer, explicit user correction) | **083-04 scan** | **083-04 scan** |
   | **load-bearing, no trigger phrase** (discursive ADR-worthy reasoning) | **083-06** reconciliation ADR-trigger (judgment) | **083-03/083-06** session-end memory-sync judgment prompt |

   The scan (083-04) runs every session and catches what a regex *can* see,
   in-spec or out. The two **judgment** prompts catch what a regex cannot — and
   they are split by *which session-end surface fires*: reconciliation only
   exists for spec slices, so the **memory-sync session-end prompt is the only
   judgment owner for out-of-spec load-bearing decisions** (the spec's own
   founding case).

> **Why three, not two (two frame-critique findings).** (1) A lexical scan is
> structurally biased to catch lightweight decisions and miss ADR-worthy ones —
> the *more* load-bearing a decision, the *less* likely it carries a trigger
> phrase — so the scan cannot own the load-bearing case. (2) Re-anchoring that
> case solely on the *reconciliation* trigger (083-06) re-opened the crack: the
> spec's target sessions are **out-of-spec, which have no reconciliation phase**,
> so that owner never fires for them. The out-of-spec load-bearing decision is
> therefore owned by the **session-end memory-sync judgment prompt**, whose
> trigger must be a *judgment escape hatch* ("a load-bearing decision a future
> agent would need to know to avoid undoing it"), **not** only the enumerated
> surface list (UI strings/visual/translation) — an enumerated list is itself a
> surface gate that re-imports the detectability bias. See
> [reviews/slice-04-frame-critique.md](reviews/slice-04-frame-critique.md).

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
(slices 083-04..07, below)** adds a deterministic session-end **scan** and
helper-backed routing.

> **Honest scope of the promise (frame-critique round 3).** Phase 2 does **not**
> "eliminate recall." It delivers a **two-tier** capture: *deterministic* capture
> for **lexically/structurally detectable** decisions (AskUserQuestion answers,
> explicit user corrections — the scan, Tiers 1–2), and *recall-reduced-not-
> eliminated* capture for **load-bearing** decisions, which remain owned by
> **judgment prompts** because no regex can see a trigger-phrase-free design
> choice. The judgment prompts (reconciliation + memory-sync) are attention
> prompts — they widen *what* the agent is asked to consider, but still depend on
> the agent attending at session end. The Tier-1 structured subset (AskUserQuestion
> answers / default-overrides) is **already** captured recall-free by the 083-04
> scan (structured extraction off the Stop payload, no agent attention);
> **in-flight structured capture (083-07, now ACTIVE)** *hardens* that subset —
> it persists the decision at decision time so it survives a Stop payload that
> drops the tool blocks or a session that ends abnormally (a **resilience** layer,
> not a new coverage cell, and not a shrink of the discursive residue). What stays
> recall-reduced-not-eliminated is the **discursive** load-bearing decision
> (no structured answer, no trigger phrase), owned by the judgment prompts. This is
> a sound architecture — a deterministic floor (lexical scan **+ in-flight Tier-1
> hardening**) plus a judgment ceiling — stated honestly.

**Status:** ADOPTED (2026-06-25), Phase 2 in design (slices 083-04..08 DRAFT).
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
  load-bearing-decision judgment trigger (083-05/083-06, single-sourced wording).
- **I — Interface:** the scan's signal patterns and candidate output shape, the
  `decisions.py add-lightweight` helper contract, and the in-flight stub shape
  (083-04/083-05/083-07).
- **P — Platform:** Claude vs Codex host parity for the hooks — split into its own
  validation slice (083-08) because the payload/hook shapes can only be confirmed
  on the actual Codex runtime, and jig is dual-host (ADR-0018).
- **Data/Path** splits stay out: the scan reuses the existing Stop-hook payload
  path (`jig-task-capture.sh`); the in-flight stub adds one per-session scratch
  log, not a new external data source.

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
  than bury real ones under "let's do X" chatter. This locks the *trigger
  patterns* only. It once also licensed suppressing candidates that matched a
  recorded decision; bug 011 withdrew that, because overlap cannot tell a
  restatement from a reversal. Repeat runs are noisier as a result.

### Slice 083-04 — Session decision scan (Stop hook)

A `jig-decision-capture.sh` Stop hook modeled on `jig-task-capture.sh`, scanning
the session for decision signals. **The scan claims only the tiers it can
reliably detect** (frame-critique correction):

- **Tier 1 — AskUserQuestion answers** (structured payload) and **Tier 2 —
  explicit user corrections** ("X should not be the default", "do A instead").
  These are discrete turns / structured data — reliably detectable. **This is
  what 083-04 commits to catching.**
- **Tier 3 — agent statements of settled choices** ("chose A over B", "rejected
  because") and reversed defaults: **best-effort only.** A genuinely load-bearing
  design choice is usually discursive reasoning with no stock phrase, so the
  regex will miss it. **083-04 does not promise to catch load-bearing decisions —
  083-06's judgment prompt owns that case.**

Output: candidate list, each with a quoted evidence line, turn reference, and
*who decided*. **Provenance requires per-role tracking** — unlike
`jig-task-capture.sh`, which flattens all content into one string (line 35) and
so cannot say *who* decided; 083-04 must preserve message role/turn boundaries.
Candidates overlapping an already-recorded decision (existing ADRs,
`lightweight-decisions.md`, `refinement-todo.md`) are matched by an explicit
strategy (normalized-substring / title match — stated in the slice, not
assumed) and **flagged for triage, never dropped**: bug 011 removed the
suppression, because overlap cannot tell a restatement from a reversal. Repeat
runs are consequently noisier, not quiet. The scan logic lives in
`decisions.py scan-session` invoked **by the hook** (testable in isolation).

**Per-host grounding task:** verify the Stop payload exposes the **AskUserQuestion
answer shape** (Tier 1), not just `messages[].content` bodies, on both Claude and
Codex; fall back to the Phase-1 nudge where unavailable.

**AC (adversarial — must be ungameable):** over a transcript fixture, the scan
(1) surfaces the AskUserQuestion answer and the user-correction (Tiers 1–2) with
correct who-decided provenance; (2) does **not** surface ephemera ("let me run
the tests"); and (3) **the fixture must include one load-bearing design choice
phrased with NO literal trigger pattern** — the scan is asserted to *honestly
miss* it (or surface it only as a low-confidence best-effort hit). The spec
documents that this decision is caught instead by a **judgment** prompt, and
**which** prompt depends on context (frame-critique round 2): an *in-spec*
load-bearing decision is owned by 083-06's reconciliation trigger; an
*out-of-spec* one (no reconciliation phase) is owned by the session-end
memory-sync judgment prompt (083-03 widened in 083-06). The AC must assert the
correct owner per fixture context — it cannot be satisfied by writing
regex-matching fixture lines, **nor** by claiming reconciliation catches an
out-of-spec decision.

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
wording** as the 083-06 judgment prompts. **Single-sourcing mechanism**
(frame-critique residual): the ADR-trigger sentence lives in **one** canonical
place — the 083-06 ADR — and all four consumers quote it (this rubric, the two
reconcile checklists, and the memory-sync prompt); a unit test asserts the exact
string appears in all four sites, so drift fails CI rather than silently
accumulating.

### Slice 083-06 — Companion: widen the load-bearing-decision judgment prompt in BOTH session-end surfaces (needs its own ADR)

**This slice owns the load-bearing-decision case** (frame-critique correction) —
not the 083-04 scan. The same judgment clause is added to **both** session-end
judgment surfaces so there is no out-of-spec gap (frame-critique round 2):

1. **Reconciliation** (`docs/workflow.md` + `skills/spec-workflow/SKILL.md`): the
   reconcile checklist asks *"did module boundaries or public contracts change?"*;
   widen it to **also** ask *"was a load-bearing design choice with rejected
   alternatives made, even if no boundary changed?"* — fires for in-spec slices.
2. **Session-end memory-sync** (`skills/memory-sync/SKILL.md`, widening the
   083-03 condition): the 083-03 prompt currently fires only on an *enumerated
   surface list* (UI strings/visual/translation). Add the **same** judgment
   clause as an escape hatch so it fires on **any** load-bearing decision a
   future agent would need to know to avoid undoing — **this is the only judgment
   owner for out-of-spec load-bearing decisions**, which have no reconciliation
   phase. Without it, the spec's founding case (an off-spec ADR-worthy decision
   with no trigger phrase) has no owner at all.

Both are **judgment** prompts — no trigger phrase needed — so they catch the
discursive ADR-worthy decisions the regex scan structurally cannot.

Because this changes a **load-bearing lifecycle policy** (when an ADR is
required), it warrants **its own ADR** — reserve the number via `adr.py new` at
implementation time (do **not** mint a number from a stale local tree). The ADR's
trigger sentence is the **single canonical source**; 083-05's rubric ADR-branch,
both reconcile checklists, and the memory-sync prompt all **quote** it, and a unit
test asserts the exact string appears in all **four** sites so drift fails CI.

### Slice 083-07 — In-flight decision stubs (ACTIVE)

**Promoted from DEFERRED (maintainer decision, 2026-06-25)** — this **hardens**
the Tier-1 structured cell of the deterministic floor. A hook on **AskUserQuestion
answers** and on **user override of a stated default** writes a one-line stub to a
session scratch log *the moment the decision settles*; the 083-04 triage merges it
with the scan and dedups so a decision settled both ways surfaces once.

> **Honest scope (frame-critique correction).** The Tier-1 subset is **already**
> captured recall-free by the 083-04 scan (structured extraction off the Stop
> `messages` payload). 083-07's marginal value is **resilience**, not residue-
> shrink or a new coverage cell: (1) it does not depend on the Stop payload
> retaining the AskUserQuestion tool blocks (a documented scan risk — see
> Assumptions); (2) it persists *before* Stop, so a decision survives an abnormal
> session end; (3) every stub re-surfaces until the owner triages it — bug 011
> withdrew the narrower "until recorded" (durability parity with the scan). It
> does **not** touch the discursive load-bearing residue, which stays owned by
> 083-06's judgment prompts.

**Deliverables:**

1. A capture hook (PreToolUse/PostToolUse on `AskUserQuestion`, plus a
   user-override signal) appending `{timestamp, who, quoted decision, turn}`
   stubs to a per-session scratch log (e.g. `.jig/decision-scratch/<session>.log`).
2. Triage reads the scratch log at session-end (feeds the same owner-gated
   surfacing as 083-04), and the scratch log is deduped against it so a decision
   isn't surfaced twice (in-flight stub + end-of-session scan).
3. Scratch-log lifecycle: created per session; since bug 011 nothing is pruned,
   so a populated log is rewritten rather than cleared (parked in refinement-todo).

**AC:** an AskUserQuestion answer and a user default-override each produce a
scratch-log stub with correct provenance (who + quote) at decision time, before
session end; the end-of-session surfacing dedups in-flight stubs against scan
hits (no double-surface); ephemera produce no stub.

**Relationship to 083-04:** 083-04's scan remains the catch-all for sessions
where the in-flight hook didn't fire (or the host lacks the hook point); 083-07
is the deterministic fast path for the structured Tier-1 subset. They compose;
083-07 does **not** remove the discursive-load-bearing residue (still owned by
the 083-06 judgment prompts).

### Slice 083-08 — Codex host validation (HANDOFF — completed on Codex)

Phase 2's deterministic mechanisms (the 083-04 Stop-hook scan and the 083-07
in-flight capture) depend on **host-specific** surfaces that are verified for
Claude but **unproven on Codex**: the Stop-payload shape, whether
`AskUserQuestion` (or its Codex analog) is a hookable tool with a structured
answer in the payload, and whether the scratch-log hook points exist. jig is
dual-host ([ADR-0018](../../decisions/adr-0018-dual-host-generated-plugin-artifacts.md)),
so a mechanism that silently works only on Claude is a half-shipped feature.

This slice is the **explicit Codex-side validation + parity harness**, authored
here as the jig-side contract and **completed on Codex** by the maintainer (who
has that host environment):

**Deliverables:**

1. A host-parity fixture/test asserting, on Codex: (a) the Stop payload exposes
   the session content the scan reads; (b) the decision-signal patterns fire on a
   Codex transcript fixture; (c) the in-flight hook point for the structured
   answer exists (or is documented absent → fall back to scan + judgment prompts).
2. A documented **host-capability matrix** (Claude vs Codex) for each Phase-2
   mechanism: `supported` / `degraded-to-nudge` / `unsupported`, so adopters know
   the guarantee level per host.
3. Any Codex host-transform adjustments to the hooks (mirroring the standard
   `CLAUDE.md→AGENTS.md` / `CLAUDE_PLUGIN_ROOT→PLUGIN_ROOT` transforms applied by
   `build_host_packages.py`).

**AC:** the parity harness runs green on Codex (or honestly records
`degraded`/`unsupported` cells with the fallback wired); the capability matrix is
committed; `build_host_packages.py --check` stays green with the Codex hook copies.

**Why a separate slice, not folded in:** the validation needs the *actual* Codex
runtime to confirm payload/hook shapes — it cannot be proven from the Claude side
by inspection. Keeping it discrete lets the maintainer own the Codex-side
completion without blocking the Claude-side Phase-2 build.

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

- **Discursive load-bearing decisions remain recall-dependent (the residue,
  narrowed).** With 083-07 active, the **Tier-1 structured** load-bearing subset
  (AskUserQuestion answers, default-overrides) is captured *deterministically
  in-flight* — recall-free. What remains recall-dependent is the **discursive**
  load-bearing decision (a design choice reasoned out in prose, no structured
  answer, no trigger phrase): its only owner is the memory-sync session-end
  judgment escape hatch — an *attention* prompt, not deterministic capture. An
  agent that doesn't attend to it at session end still loses it. The owner-gate
  and OQ4 rubric are *quality* backstops, not *capture* guarantees. This residue
  is real but smaller than before 083-07 was promoted; closing it further would
  require semantic (LLM-judged) in-flight detection, explicitly out of scope.
- **Scan noise.** Many "let's do X" lines aren't durable decisions. Mitigated by
  precision-first patterns and the owner-gate (never auto-writes). Not a hard
  guarantee — and deliberately noisier since bug 011: overlap with a recorded
  decision now flags for triage rather than suppressing, because suppressing it
  silently dropped reversals.
- **Token cost of scanning.** Real *if the agent reads the transcript* — which is
  why the scan runs in the Stop hook out-of-band (only the candidate list reaches
  context). This is the design correction over the food-log proposal.
- **ADR/lightweight boundary still needs judgment.** The rubric (083-05) narrows
  it but doesn't eliminate the judgment call; the owner-gate is the backstop.
- **Per-host parity (Codex).** The deterministic mechanisms (083-04 scan, 083-07
  in-flight capture) are proven only for Claude; their Codex behavior is unproven
  until 083-08's parity harness runs on that host. Until then, the Codex guarantee
  level is *unknown* — 083-08 must record it honestly (`supported` /
  `degraded-to-nudge` / `unsupported`) rather than assume parity.

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
