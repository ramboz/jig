---
status: Proposed
dependencies: []
last_verified: 2026-07-06
frame_review: true
---

# ADR-0034: Lower the interaction altitude for non-expert adopters

## Status

Proposed (2026-07-06)

## Context

A recurring, multi-source signal says jig is too much mental burden for some
non-expert adopters. Three converging observations:

- Peers who scaffolded jig have **passively refused to onboard** — the reported
  friction is "ADR / formal spec sound like things I'm not qualified to write."
- The user added **jargon-reduction rules to their user-global `~/.claude/CLAUDE.md`**
  independently of jig.
- A separate colleague is exploring a **"manager move"** to reduce the technical
  **level** of chat output.

An earlier draft of this ADR read those signals as a **nomenclature** problem
and proposed a display-only vocabulary overlay (rename *spec / slice / ADR* to
*plan / task / decision* at the surface). A frame-critique (2026-07-06,
`needs-changes`) rejected that framing, and it was right to:

- **All three signals describe *altitude*, not the nouns.** "ADR sounds like
  something I'm not qualified to write" is an impostor-response to the **act of
  authoring a formal gated artifact**, not to the string "ADR." The user's own
  fix was jargon-*reduction*; the colleague's move is about the technical
  *level* of *output*. Renaming `spec.md`'s display label to "plan" leaves it a
  formal artifact with acceptance criteria, SPIDR, and reconciliation — the
  refuser won't author a "task" any more than a "slice."
- **A display-only rename is partial by design and risks a *worse*, inconsistent
  barrier.** Canonical terms (`NNN-MM`, `spec.md`, `## Slice`, parser-read
  headers) unavoidably remain in the file tree, git, and PRs. A user intimidated
  by "spec" but told the chat says "plan" now holds two vocabularies at once —
  trading one *consistent* barrier for an *inconsistent* one.

So the load-bearing reframe: **the barrier is the technical *altitude* of the
jig interaction — how technical and formal the whole experience feels — not the
specific names of artifacts.** Nomenclature is at most a minor facet of altitude,
and the weakest, least-grounded lever against it.

This is the **vocabulary/altitude** companion to [ADR-0027](adr-0027-host-native-phase-modes.md),
which already decided the *process* half (plan-then-build via native Plan mode,
`mode-aware not mode-dependent`) and left its open question #4 — whether artifacts
should carry friendlier surface names — for a later decision. This ADR answers
that: not as a primary lever.

Two existing patterns supply the invariant this ADR preserves:

- **[ADR-0021](adr-0021-lexicon-home-and-overlay.md)** — jig-canonical vocabulary
  and a friendlier project surface **coexist deliberately** (shipped lexicon vs.
  project glossary, fail-soft). A canonical-inside / adjustable-surface split is
  established practice.
- **[ADR-0033](adr-0033-configurable-docs-root.md)** — the template for a
  config-selectable presentation dimension: one knob, one leaf helper,
  default-unchanged, validated at the boundary; and the warning that a naive
  "make it configurable" can hide a token that is doing two jobs at once.

A 2026-07-06 coupling audit fixed where the canonical/machine layer lives (and
therefore what any altitude lever must **not** touch): path/filename globs
(`*/spec.md`, `slice-*.md`, `adr-*.md`), heading/marker regexes (`## Slice
NNN-MM`, `**STATUS: …**`), frontmatter keys, dependency tokens (`NNN-MM` resolved
to paths), and the `parents[3]` depth arithmetic. The human-facing surface (chat
output, SKILL prompt wording, rendered primers, `_render_stub_*` template prose,
printed output, hook `additionalContext`) is loose and re-skinnable — with the
bounded exception of template section headers a parser reads.

## Decision Options Considered

### Option A: Ship the display-only vocabulary overlay as the primary fix
Rename *spec/slice/ADR* → *plan/task/decision* at the surface; build
`vocabulary.py`, the friendly↔canonical map, and the boundary plumbing.
- **Pros:** matches the literal "make it feel less like specs" intuition; small,
  localized change.
- **Cons:** the frame-critique's core finding — attacks the *noun*, which the
  evidence says is not the barrier; leaves the formal artifact, the technical
  output, and the upfront-authoring burden untouched; and creates a
  partial-by-design veneer that can worsen the barrier. Optimizes the weakest,
  least-grounded lever. **Rejected as the primary fix** (retained as a deferred,
  gated lever below).

### Option B: Do nothing new — rely on `/jig:explain` + the lexicon
- **Pros:** zero code; on-demand definitions already ship (spec 065 / ADR-0021).
- **Cons:** teaching a term is not lowering altitude. Spec 065 already chose
  "explain"; the converging signal is evidence that *explain is not enough* — the
  passive-refuser will not invoke it. Leaves the barrier standing. **Rejected.**

### Option C: Treat *presentation altitude* as an adjustable surface over the fixed canonical core
Adopt "lower the interaction altitude" as the frame. Pursue the **grounded**
levers first (how technical the interaction *feels*), keep the canonical machine
layer fixed, and demote the vocabulary rename to a deferred, evidence-gated lever.
- **Pros:** attacks what the evidence actually names (altitude); extends the
  canonical-inside / adjustable-surface invariant (ADR-0021/0033) from naming to
  altitude generally; honors ADR-0027 §1/§4 (artifacts stay canonical); avoids
  committing mechanism to an un-isolated cause (the frame-critique's meta-lesson).
- **Cons:** "altitude" is broader and its best mechanism is less obvious than a
  rename; *which* lever moves adoption is not yet isolated, so mechanism must stay
  evidence-gated rather than fully committed here.

## Recommended Decision

**Adopt Option C.** The barrier is altitude; jig will treat **presentable
altitude as an adjustable surface over a fixed canonical core.**

**Invariant (unchanged by any lever).** The canonical machine layer — filenames,
`## Slice` headings, frontmatter keys, `NNN-MM` dependency tokens, `**STATUS:**`
markers, path arithmetic — is never altered to lower altitude. Altitude is
adjusted only at presentation surfaces (chat output, template prose, rendered
primers), never in parsers. (Honors ADR-0027 §1/§4; same shape as ADR-0021/0033.)

**Levers, in priority order by grounding and directness:**

1. **Interaction-output altitude — primary, best-grounded** (2 of 3 signals: the
   jargon-reduction rules + the "manager move"). Reduce how much low-level jig
   mechanism (ADR numbers, frontmatter, gate internals, SPIDR/state-machine
   jargon) leaks into chat output for non-expert adopters — a configurable
   "presentation altitude" for how jig *talks*, summarizing at the reader's level
   while keeping the detail one step away. This is **orthogonal to the artifacts**
   and does not touch the canonical layer at all.

2. **Plain-language templates — secondary, grounded** (signal 1: the authoring
   act). Make the artifact *body* read like a normal dev's checklist — section
   prompts as plain questions ("What could bite us later?" not "Consequences") —
   so authoring stops triggering the "not qualified" response. Bounded by the
   coupling audit: relabel only display-safe section prose; any header a parser
   reads (`## Slice`, `**STATUS:**`, `**Acceptance Criteria:**` where `spec_lint`
   matches it) stays canonical, enforced by a guard test (as in ADR-0033).

3. **Process rhythm — already decided *and shipped*, and broader than this ADR
   ([ADR-0027](adr-0027-host-native-phase-modes.md) + spec 074, all slices
   DONE).** Routing work through native Plan mode (plan-then-build) is a
   **standalone, universal, already-shipped** jig capability: spec 074 ships the
   portable phase vocabulary, `session-plan` host-mode hints, and host-native
   primer substitutions for both Claude and Codex. Its value is the spec 057
   thin-orchestrator win — front-load planning in Plan mode, commit the plan into
   specs/slices, dispatch compactly — which applies to **all** users, expert
   included, not just altitude reduction. It *also* lowers the
   upfront-formal-authoring burden, so it is listed here as an altitude lever —
   but it must **not** be scoped to, or gated on, this ADR or the non-expert
   cohort. This ADR neither owns nor re-decides it.

4. **Display vocabulary rename — weakest, deferred.** *spec→plan / slice→task /
   ADR→decision* as a display overlay. Per the frame-critique, nomenclature is a
   minor facet of altitude and a display-only rename is partial-by-design (§
   Context). **Not built** unless an isolating datapoint shows a user stopped at
   the *word itself*, not the formality — and even then, only after weighing the
   inconsistent-vocabulary risk.

**jig's own repo is unaffected.** With no `scaffold.json` (ADR-0033 §5), jig
resolves the default full/expert altitude — maintainers keep the precise
vocabulary and full-detail output; lowered altitude is an **adopter-only**
affordance.

**Mechanism stays evidence-gated.** This ADR fixes the *frame* and *direction*;
it does **not** commit a specific mechanism. The build is a **new spec** that
extends spec 074's already-shipped host-adapter rendering / phase-mode machinery,
reserved when demand is proven, **starting with lever 1** (best grounded,
canonical-layer-free). Trigger: **≥2 concrete adopter datapoints** — and,
per the frame-critique, each datapoint should try to **isolate which altitude
lever the friction attaches to** (output density vs. authoring formality vs. the
noun), so jig builds the load-bearing lever, not the most visible one. Log them
with an auditable `altitude-friction:` tag (the inbox counting idiom). The three
converging signals are the founding evidence; the "manager move" exploration and
the user's global jargon-reduction rules are prior art for lever 1.

## Consequences

**Becomes easier:**
- Effort is aimed at what the evidence names (altitude), starting with the lever
  that is both best-grounded and free of canonical-layer risk (output altitude).
- A clean graduation story: altitude is a presentation setting, so a project (or
  a maturing team member) raises it toward full/expert detail with **zero
  migration** — the artifacts never changed.
- Slots beside ADR-0027 (process) as the altitude companion; together they cover
  both halves of the onboarding barrier without weakening any gate.

**Becomes harder:**
- "Altitude" is broader than a rename; each lever needs its own design and its
  own evidence that it helps — more discipline, less shovel-ready.
- Lowered-altitude output must keep an easy path to the detail, or it trades a
  jargon barrier for an opacity one.
- Any presentation surface that ignores the altitude setting renders mixed
  altitude (a completeness risk, as in ADR-0033); mitigated because a missed
  surface degrades to the honest full-detail default.

## Assumptions

- **The barrier is altitude, broadly** — grounded by three converging signals.
  This is now the frame, not a deferred assumption. (The earlier noun-centric
  assumption was tested and rejected by the frame-critique.)
- **Which altitude lever moves adoption is not yet isolated.** We commit to the
  direction but gate each lever's *build* on evidence it helps — this is what
  keeps the frame-critique's meta-lesson (don't commit mechanism to an
  un-isolated cause) honored rather than merely restated.
- **Reducing output altitude does not starve non-experts of information they
  need.** If a manager-altitude summary hides detail a reader needed to decide
  well, it swaps one barrier for another; the detail must stay one step away.
- The coupling audit's canonical/machine-layer map holds (re-verify before
  editing helpers for lever 2).

## Kill criteria

- If lowered-altitude output leads non-experts to worse decisions (they needed
  the hidden detail), revert or rebalance the default.
- If, after building the grounded levers, adoption still doesn't move, the
  barrier is elsewhere (tooling, trust, process) — stop investing in altitude.
- The vocabulary rename (lever 4) stays un-built unless noun-isolating evidence
  appears; if shipped and it produces the inconsistent-vocabulary confusion the
  frame-critique predicted, drop it (default reverts to canonical).

## Open questions

- **Mechanism for lever 1:** a `scaffold.json` altitude preset, a rendered-primer
  directive, or a host output-style/persona? (Prior art: the "manager move"
  exploration and the user's global jargon-reduction rules.)
- **Granularity:** one `expert | plain` altitude preset, or per-surface control?
- **Lever 2 guard:** confirm the parser-safe template-header filter as a guard
  test before relabeling any template prose.
- **Home:** a standalone new spec, or a broadening of spec 074's
  **already-shipped** host-adapter rendering / `phase_mode_substitutions()`
  machinery? Decide at reservation time.
- **Lexicon tie-in:** if lever 4 is ever built, does its friendly↔canonical map
  live in ADR-0021's lexicon so `/jig:explain` can teach "a *plan* is jig's
  *spec*" from one source?

## Frame-critique history

- **2026-07-06 — `needs-changes` → reframed.** The original draft framed the
  barrier as nomenclature and adopted a display-only vocabulary overlay (Option
  A) as the primary fix. An independent frame-critique found the load-bearing
  assumption ("relabeling the noun removes the barrier") contradicted by the very
  signals cited (all describe altitude/technical level), and flagged that the
  overlay is partial-by-design and risks an inconsistent-vocabulary barrier. This
  ADR was rewritten to make altitude the frame, demote the rename to the weakest
  deferred lever, and keep mechanism evidence-gated.
