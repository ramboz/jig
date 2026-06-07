---
status: DONE
dependencies: [065-01, 065-03]
last_verified: 2026-06-07
arch_review: true  # changes the public skill's input contract — adds a third
#                    mode and an explicit mode-precedence rule (a design-shaped
#                    concern: the precedence must not erode term mode's honest
#                    "absent term" signal).
---

## Slice 065-05 — `/jig:explain` passage mode (explain a pasted snippet)

**Goal:** Let a reader explain the thing that actually confused them — a chunk
of jig output they copy-pasted (a review `VERDICT:` envelope, a status-board row
like `IN_PROGRESS (wt-me)`, a hook's *"Unrecognized references in prompt…"*
message, a transition refusal, a `session-plan` block) — not just a single
lexicon term or a whole spec/ADR. Adds a **third mode** to `/jig:explain` that
turns today's dead-end "ambiguous argument → say what you tried and stop" branch
into a useful plain-language explanation of the pasted passage.

**DoR:**
- ✅ 065-01 landed — the merged lexicon is the source for the in-passage term
  scan ("which jig terms does this snippet use?").
- ✅ 065-03 landed — `/jig:explain` ships with term + artifact modes, the
  ephemeral contract, the judgment-only/no-`.py` shape, and the lexicon-load
  recipe this slice reuses verbatim. This slice **extends** that SKILL.md; it
  adds no new skill and no new registration surface.
- ✅ The "Words you'll need first" lexicon-scan mechanism (artifact mode, 065-03)
  is the proven primitive the passage scan reuses.

**Acceptance Criteria:**

1. **Passage mode is documented as the third mode.** `skills/explain/SKILL.md`
   gains a "Passage mode" section: when the argument (or a pasted block) is
   **neither a resolvable spec/ADR path nor a lexicon key**, the skill explains
   the snippet — it (a) scans the passage for jig lexicon terms and defines each
   inline (the 065-03 "Words you'll need first" primitive, reused), and (b) states
   in plain language **what the passage is** and **what — if anything — the reader
   should do** about it. When the passage contains **no recognizable jig
   vocabulary at all** (generic prose, or output from a non-jig tool), passage
   mode **explains it generically** — a plain-language read with no jig framing —
   rather than declining (clarify Q2); this does not conflict with the deferral
   clause, which only steps aside for a *richer installed* explanation skill. The
   description/SKILL.md declares passage mode alongside the existing two. A
   surface test asserts the section, the declaration, and the
   no-jig-vocabulary → explain-generically behavior.

2. **Explicit mode precedence — term mode's honesty is preserved, path
   ambiguity disambiguated.** SKILL.md documents the resolution order in one
   place: **path → artifact mode · exact / normalized lexicon key → term mode ·
   otherwise → passage mode.** Two carve-outs sit on top of that order:
   - **Term-mode honesty.** An unknown **single term** still routes to term mode
     and gets its honest *"that term isn't in the lexicon"* flag — it is **not**
     silently absorbed into a passage-mode guess. Passage mode is for multi-token
     snippets / pasted output, not a greedy catch-all that erodes the absent-term
     signal.
   - **Path-shaped-but-unresolvable input (clarify Q1).** When the argument
     **looks like a file path** (e.g. contains a `/` or a known doc extension,
     or matches `docs/specs|docs/decisions`) but **no file exists there**, the
     skill **asks the user whether they meant a file path or a snippet to
     explain** rather than silently falling through to passage mode — a likely
     typo/stale-path/wrong-repo shouldn't be answered as if the path string were
     prose.

   A test asserts the precedence order, the term-mode-honesty carve-out, and the
   path-disambiguation carve-out are all documented.

3. **Provenance is best-effort, never fabricated.** Passage mode best-effort
   names the jig surface that produced the snippet **when recognizable** (e.g. a
   review `VERDICT:` envelope, a `docs/specs/README.md` status-board row, a hook
   `additionalContext` message, a `workflow.py` transition refusal / claim
   message) and explains it accordingly — but when the source is **not**
   recognizable it says so plainly rather than inventing one. A test asserts the
   best-effort + no-fabrication framing.

4. **The honesty line holds (never invent).** Any jig-shaped token in the passage
   that is **not** in the merged lexicon is flagged as unrecognized rather than
   given a fabricated definition — consistent with term mode's never-invent rule
   (065-03 AC2) and the spec's honesty principle (a confident wrong answer is
   worse than an honest gap). A test asserts the never-invent framing extends to
   passage mode.

5. **Ephemeral, judgment-only, no new helper.** No `.py` is added; passage mode
   reuses the 065-01 loader + Read inline (the same recipe 065-03 ships). Output
   stays chat-only — no `--save`, no appended section, no file mutation. A test
   asserts `skills/explain/explain.py` still does not exist and the ephemeral
   contract is still stated.

6. **The existing two modes are unchanged.** Term mode and artifact mode keep
   their documented behavior and section shape (065-03); the only behavioral
   change is that the previously-documented **dead-end** ("If the argument is
   ambiguous … say what you tried rather than guessing") is **replaced** by the
   passage route. A test asserts the term + artifact sections are still present
   and that the bare dead-end phrasing no longer stands alone (it now routes to
   passage mode).

_Testability note (accepted gap, inherited from 065-03): ACs 1–6 are structural
and unit-tested at the SKILL.md surface (section present, precedence + honesty
documented, no helper, ephemeral contract, two existing modes intact). The
plain-language **quality** of a passage explanation is judgment exercised by the
skill prompt, not a unit test — the same accepted shape as term + artifact modes
and every judgment-only jig skill. Recorded in the spec's coverage summary._

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). (2363 tests, exit 0.)
- [x] Implementer test coverage: the passage-mode section is present; the mode
      precedence + term-honesty carve-out + path-disambiguation carve-out (Q1) are
      documented; the no-jig-vocabulary → explain-generically behavior (Q2) is
      documented; best-effort/no-fabricate provenance is stated; never-invent
      extends to passage mode; no `explain.py`; ephemeral contract intact; term +
      artifact sections still present.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Arch (arch-review) pass run (slice declares `arch_review: true` — the mode
      precedence is the load-bearing design call); blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (No
      decisions deferred; two accepted heuristic trade-offs named in the deviation
      log, not refinement-todo items.)

**Anti-horizontal-phasing check:** After this slice, a junior can paste a
confusing chunk of jig output — a `VERDICT:` envelope, a status-board row, a hook
message — into `/jig:explain` and get a plain-language explanation of what it
means and what to do: a complete, usable capability, not internal-only state.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column for the `/jig:explain`
      rows records: now **three** modes — term + artifact + passage (snippet),
      precedence path→artifact / key→term / else→passage, ephemeral, judgment-only.
- [x] `CLAUDE.md` hygiene per spec 025-01: update the `/jig:explain` Skills-table
      row to name the third (passage) mode + the precedence rule. Leave spec 065's
      Active-specs entry until the closing slice (compress only when all
      non-deferred 065 slices are DONE). _(065-04 still DRAFT — Active-specs entry
      left for its close-out.)_

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **Deliverables.** Extended `skills/explain/SKILL.md` (no new skill, no new
  registration surface — 065-03 already registered `/jig:explain`): added the
  third **Passage mode** section, rewrote **Inputs** into an explicit
  mode-precedence rule with the two carve-outs, added the passage-mode bullet to
  "What this skill does", refreshed the frontmatter description ("three modes" +
  two new trigger phrases), and updated the Gotchas. Extended
  `skills/explain/test_explain_skill_surface.py` from 27 → 39 surface tests
  (`DescriptionTests` passage assertions + a new `PassageModeTests` class). All
  four clarify resolutions (Q1 path-ask, Q2 generic-on-no-jig-vocab, Q3
  large-paste nudge, Q4 no-hard-cap) are reflected.

- **Built to spec; no scope deviations.** The six ACs map 1:1 to the documented
  surface; the implementation review (compliance) confirmed each.

- **Reconciliation fixes folded back from the review passes (all three returned
  `pass`):**
  1. **Arch — term-honesty carve-out un-bounded from word count.** The draft
     bounded the "still route to term mode" carve-out to "a one- or two-word
     argument," but real lexicon keys are 3+ words (`closed-spec drift policy`,
     `detect and drive`) — an unknown long phrase would have lost the honest
     absent-term flag. Reworded to distinguish **by shape, not word count**: a
     short single-line phrase is a term query; a multi-line / output-shaped paste
     is a passage.
  2. **Arch — path heuristic tightened.** The draft treated a bare `/` as
     path-shaped, which would over-trigger the "did you mean a file?" prompt on
     pasted command lines / URLs. Narrowed to "looks like a **repo** file path"
     (under `docs/`, or a doc/code extension), with an explicit note that a bare
     `/` alone is a passage.
  3. **Craft — `test_term_honesty_carveout` strengthened.** Replaced a
     trivially-true `"not" in body` conjunct with a pin on the distinctive
     negation phrase `silently absorbed into a passage-mode guess` (chosen to
     dodge the `**not**` bold markers `_normalize` leaves in place).
  4. **Craft — test-module docstring** updated to cover 065-05 (was scoped to
     065-03 only).
  5. **Compliance — `test_no_silent_dead_end` strengthened.** Added a positive
     assertion (the "no silent … dead-end" replacement is documented) alongside
     the existing negative (the original dead-end phrasing — which *did* exist in
     065-03's SKILL.md and was removed here — is gone). The compliance reviewer
     read the now-edited file and mis-took the negative as vacuous; the positive
     assertion removes the ambiguity.

- **Accepted trade-offs (named per the arch pass; no code change needed,
  consistent with the judgment-skill / best-effort framing).** (a) The
  term-vs-passage boundary is shape-heuristic, not exhaustive; (b) the path
  heuristic can still mildly over-trigger the disambiguation question on an
  ambiguous string — asking is the safe default. Both are within the spec's
  accepted "best-effort comprehension floor" stance.

## Clarifications

### Q1: When the argument looks like a file path but no file exists there (typo, wrong repo, stale path), what should `/jig:explain` do?
_(category: Edge Cases & Failure Modes)_

Ask which they meant — pause and ask the user whether they meant a file path
or a snippet to explain, rather than silently routing the path-like string to
passage mode.

### Q2: When a pasted passage contains no recognizable jig vocabulary at all (generic prose, or output from a non-jig tool), what should passage mode do?
_(category: Scope & Boundaries)_

Explain generically — explain it like a general assistant would, with no jig
framing.

### Q3: If someone pastes a very large block (e.g. an entire spec's text), should passage mode process it inline or nudge toward artifact mode?
_(category: Scope & Boundaries)_

Process + nudge if artifact-like — explain it, but if the block looks like a
whole spec/ADR, suggest `/jig:explain <path>` for the richer six-block
walkthrough with auto-pulled refs.

### Q4: Should passage mode cap how many distinct lexicon terms it defines inline? (The 065-02 hook caps at 5 to protect per-prompt context.)
_(category: Non-functional Requirements)_

No hard cap, stay lean — define the terms that matter for understanding the
passage; lean but not artificially limited. It's an explicit on-demand request,
not an always-on per-prompt nudge, so the hook's cap rationale doesn't apply.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Clear |
| Non-functional Requirements | Resolved |
| Edge Cases & Failure Modes | Resolved |
| Terminology Consistency | Clear |
