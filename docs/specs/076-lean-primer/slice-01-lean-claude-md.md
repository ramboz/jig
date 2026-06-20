---
status: DONE
dependencies: []
last_verified: 2026-06-20
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 076-01 — relocate + compress the Hot Cache

**Goal:** Re-partition `CLAUDE.md`'s Hot Cache — relocate definitional
ADR-prose entries to `docs/memory/glossary.md` / `_common/lexicon.json`
(reachable via `/jig:explain`), compress the remainder to a one-line
index, and add a budget-guard test — so jig's always-loaded primer stops
paying per-turn tokens for reference prose the agent only needs on demand.

**DoR:**
- ✅ spec 065 (`/jig:explain` + lexicon loader + `glossary.md` overlay)
  is DONE — the on-demand home exists.
- ✅ Budget anchor chosen: **≤ 70 lines / ≤ 14KB** (see AC #4). The DRAFT
  `AGENTS.md`-parity calibration was dropped — `AGENTS.md` does not exist
  on this branch (it ships with spec 033-02 on `v2`); the budget is an
  absolute cap tied to spec-055's dumb-zone framing instead.

**Acceptance Criteria:**

1. **Every Hot Cache entry is classified** by this explicit rule (recorded
   here + in the deviation log, not left implicit):
   - **Behavioral guard** — an unprompted *don't-do-X / must-do* directive
     the agent must obey without first looking it up (e.g. PARKED-don't-
     re-propose, extract-only-at-third-transition, do-not-modify-
     `conventions.md`, the hook/path/compress-on-close constraints). A
     guard is **push, not pull** — `/jig:explain` is pull, so a relocated
     guard stops guarding. **Guards stay inline** in `CLAUDE.md` as a claim.
   - **Definitional reference** — what a term/decision *means*, needed only
     when the agent touches that subsystem. **Body relocated** to
     `glossary.md`; a one-line claim + link stays inline.
   - In all cases the canonical full detail lives in the entry's ADR/spec,
     linked from both the inline index line and the glossary entry.
2. **No information is *unrecoverable*.** This is lossy editorial
   compression for the always-loaded copy, not byte-lossless relocation —
   the index line and the glossary entry are both *summaries*. The
   guarantee is recoverability, in two hops: (a) every relocated term
   resolves via `/jig:explain <term>` against the merged lexicon
   (`lexicon.json` + `glossary.md`) — a test asserts each relocated key is
   resolvable by the loader; and (b) each relocated entry preserves its
   load-bearing claim AND links to its canonical ADR/spec, which remains
   the source of truth and loses nothing — a test asserts each relocated
   glossary entry carries at least one such link.
   *(Frame-critique caught the original AC's "no information is lost" as
   conflating key-resolvability with information preservation — see the
   deviation log.)*
3. **`CLAUDE.md` Hot Cache is the index shape** — no entry's body exceeds
   the agreed one-line-plus-link form; the dense multi-sentence ADR
   paragraphs are gone from the always-loaded file.
4. **A budget guard fails CI when `CLAUDE.md` regrows** past the cap:
   **≤ 70 lines AND ≤ 14KB (14336 bytes)**. The caps are constants with a
   comment citing spec 055's dumb-zone rationale. (Necessarily this
   compresses the heavy `## Skills in this repo` table too — at 14KB it
   alone exceeds the whole-file budget, and it duplicates the per-skill
   descriptions the host already injects every session.)
5. **Keep-inline set preserved — the *complete* behavioral-guard set**, not
   a sample: active-work / v2 branch routing; the PARKED-don't-re-propose
   guard; the extract-only-at-third-`transition` rule; do-not-modify-
   `conventions.md`; the reviewer-is-read-only constraint; the
   `${CLAUDE_PLUGIN_ROOT}` hook-path + no-jq rules; the ADR/slice path
   conventions; and the compress-on-spec-close rule. A test asserts each is
   present in `CLAUDE.md` **as its full directive** (e.g. "MERGING main→v2
   (not rebase)", not the bare word "v2"), so relocating the directive fails
   CI. *Honest scope:* this is a whitelist backstop for the **known** guards —
   it cannot prove an unlisted guard wasn't relocated; completeness rests on
   AC #1's classification rule + review (see `## Assumptions`).

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Coverage exercises each AC with ≥1 fixture (relocated-term
      resolves; over-budget `CLAUDE.md` fails the guard; keep-inline set
      present).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] Deferrals tracked: `CLAUDE.md`⇄`AGENTS.md` sync → slice 076-02 (v2);
      `usage.py` token-delta follow-up → `docs/inbox.md`. No new
      refinement-todo decision entry needed.

**Implementation notes (non-binding):**
- This edits `CLAUDE.md` (not `docs/conventions.md`), so the spec-gate
  hook does not fire. Confirm before assuming.
- Measure the before/after orchestrator-token delta with spec 056
  (`usage.py`) on a representative session and cite it in the deviation
  log as evidence the change paid off.

### Close-out (post-DONE)
- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `CLAUDE.md` hygiene per spec 025-01 — **not applicable**: 076-02
      follows, so this slice does not close the spec.

**Anti-horizontal-phasing check:** After this slice, anyone opening a jig
session loads a materially lighter `CLAUDE.md` and can still recover any
relocated definition via `/jig:explain` — observable, end-to-end, without
076-02.

### Deviation log (after reconciliation)

**Outcome / evidence.** `CLAUDE.md` went **109 lines / 27,802 bytes →
65 lines / 7,082 bytes** (−40% lines, −75% bytes) — re-read every session,
every turn, so the saving compounds with turn count (the spec-055/057 cost
model). Full suite green; `ruff` + `spec_lint` clean. The non-binding
`usage.py` per-session token-delta measurement (implementation note) is left
as a follow-up — it needs a representative post-merge session to attribute;
the always-loaded byte delta is the direct, deterministic proof the change
pays off.

**AC #1 — classification applied (guard = inline / definitional = relocated):**
- *Behavioral guards kept inline* (push directives): branch-routing
  "MERGING main→v2 (not rebase)"; PARKED-don't-re-propose (servo oracle
  boundary); extract-only-at-third-`transition`; do-not-modify-
  `conventions.md`; reviewer-is-read-only; `${CLAUDE_PLUGIN_ROOT}` hook
  path + "never bare names" + "never jq"; ADR/slice path conventions;
  compress-on-spec-close. Each pinned by `KEEP_INLINE_MARKERS` as its full
  directive.
- *Definitional bodies relocated* to `docs/memory/glossary.md` (one-line
  claim + link kept inline): Lifecycle-family spine, Closed-spec drift,
  Spec-gate model, Security floor, Review-evidence gate, Worktree-aware
  reservation, Context-cost discipline, Thin-orchestrator, Token-usage
  tracking, Slice-claim on IN_PROGRESS, Solo→team re-detection, Vocabulary
  barrier / lexicon, Status board.
- *Skills table relocated to a pointer:* the `## Skills in this repo` table
  (14.4KB — larger than the whole-file budget) was replaced by a short
  pointer, because the host injects every skill's description each session
  (EngTip #23 duplication); helper-`.py` mappings kept inline.

**Deviations from the DRAFT frame** (all surfaced by frame-critique; see
`reviews/slice-01-frame-critique.md`):
1. **AGENTS.md premise was false.** DRAFT claimed "`AGENTS.md` is already
   the lean target"; it does not exist on this branch (ships with spec
   033-02 on `v2`). Budget re-anchored to an **absolute ≤70 lines / ≤14KB**
   (spec-055 dumb-zone), not AGENTS.md parity. Decided with the user.
2. **AC #2 reframed.** "No information is lost" → recoverability-in-two-hops
   (key-resolvability via `/jig:explain` + each entry links its canonical
   ADR/spec). Frame-critique showed the original conflated key-resolvability
   with information preservation; one concrete loss (Review-evidence gate
   dropped the `PASSES` enum / `adr.py accept` gating) was restored to the
   glossary.
3. **AC #5 hardened + honestly scoped.** Keep-inline markers strengthened to
   full directives (a bare word like "v2" wouldn't catch relocating the
   directive); the spec's "CI makes guard-relocation impossible" overclaim
   was softened to a whitelist *backstop* for known guards, with completeness
   carried by AC #1 + review.
4. **Loader-truncation guard added.** `lexicon._first_paragraph` recovers
   only the first paragraph; `test_relocated_entries_are_single_paragraph`
   pins every relocated entry to one paragraph so `/jig:explain` recovery
   stays lossless.
5. **Index↔key alignment.** Index term "Thin-orchestrator" was renamed in
   the glossary (was "…discipline") so the term a reader copies from the
   index resolves; a test now ties each relocated term to its verbatim
   `**bold**` index entry.

**Closest classification call (frame-critique R4 note):** the worktree-
reservation caveat "pushing from the temp worktree breaks relative-origin
repos" was relocated wholly to the glossary — defensible because it is a
helper-internal invariant the agent never executes by hand, not a push
directive. Recorded here for the record.

**Consequential edit to a closed spec's test.** `skills/explain/
test_explain_skill_surface.py` `ClaudeMdRowTests` was *relaxed, not deleted*
(065-era) from "assert a `/jig:explain` table row" → "assert `/jig:explain`
stays discoverable", because the heavy Skills table it pinned was removed.
Rationale documented in the test docstring.

**Craft nits** (from `reviews/slice-01-craft.md`): `import re` placement and
the RELOCATED_PROSE_FRAGMENTS sampling comment were addressed post-review;
`_glossary_sections` H2-walk duplication left as-is (reviewer judged
extraction not worth it). Suite stayed green after the polish.
