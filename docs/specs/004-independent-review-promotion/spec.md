---
status: DRAFT
skill: independent-review
---

# Spec 004: independent-review promotion

## Overview

Promote `independent-review` from `disable-model-invocation: true` stub to a
real Tier 0 skill. This is the most-used pattern in jig — every slice runs it
twice (implementation review + reconciliation review). Currently the prompt is
reconstructed by hand each time; codifying it ensures consistency and saves the
"what should this prompt contain again?" moment.

## Why now

- 26+ reviewer invocations across specs 001/002/003 — pattern is fully stable.
- Each invocation's prompt has the same shape: preamble, paths to read,
  prohibitions, evaluation guidance, output format. Manual reconstruction
  is consistent today but won't be in 6 months.
- `spec-workflow` (just promoted) tells Claude to "spawn the reviewer subagent
  with a fresh prompt." Right now that prompt is implicit; `independent-review`
  should be where it's explicit.

## SPIDR analysis

| Technique | Question | Decision |
|---|---|---|
| P — Path | Implementation review and reconciliation review are two distinct paths through the same skill. | Both covered by one slice (they share 80% of the prompt template). |
| I — Interface | Helper script vs. pure SKILL.md instructions? | Helper script (`review.py`) for consistency — matches the scaffold.py / memory.py / workflow.py pattern across Tier 0. |
| D — Data | What goes in the prompt: bare path references, or pre-loaded slice content? | Bare paths. Pre-loading couples the prompt to file-state at invocation time and shortcircuits the reviewer's own reading (which is its job). |
| R — Rules | Standard "what you must NOT do" list is the same across all reviewer invocations. | Encode it once in the helper template; SKILL.md just describes when to call. |
| S — Spike | None required — pattern is fully stable from dogfooding. | — |

## Ordered slices

## Slice 004-01 — review-helper

**STATUS: DONE**

**Goal:** `review.py` helper that constructs the standardized reviewer-subagent prompt for either an implementation review or a reconciliation review. SKILL.md promoted from stub to active.

**DoR:** No prior slice dependency. The existing reviewer agent definition at `agents/reviewer.md` is intact (the helper builds prompts for that agent — it does not redefine it).

**Acceptance Criteria:**
1. `review.py implementation <spec.md> <slice-fragment> <deliverable-path>...` prints a properly-formatted reviewer prompt to stdout. The prompt:
   - Opens with "You are an independent reviewer. You are seeing this work for the first time."
   - Names the spec path and slice fragment
   - Lists each deliverable path
   - Includes the standard "What you must NOT do" prohibitions (no prior context, no soften, no file writes, no `docs/memory/` writes)
   - Includes the canonical output format (VERDICT / REASONING / SPECIFIC ISSUES / RECONCILIATION NOTES)
2. `review.py reconciliation <spec.md> <slice-fragment>` prints a reconciliation-review prompt. The prompt:
   - Explicitly states "You are NOT re-reviewing against original ACs"
   - Points at the slice's "Deviation log" subsection
   - Uses the same output format
3. Both subcommands refuse with exit 2 if the spec path doesn't exist OR the slice fragment can't be located in the spec.
4. The helper does NOT spawn the subagent itself — it produces the prompt for Claude to feed into the Task tool. Claude owns the actual `Task` invocation.
5. `skills/independent-review/SKILL.md` no longer has `disable-model-invocation: true`. Body restructured from "when implemented" to active instructions.
6. SKILL.md explains the two prompt modes (implementation vs. reconciliation) and gives the exact bash invocation pattern.

**DoD:** Same as 001-01. All checked.
- [x] All 6 ACs pass (25 tests, all green)
- [x] Implementer test coverage across both prompt modes + error paths + SKILL.md promotion gates
- [x] Reviewed by `reviewer` subagent — dogfooded: the prompt was built by the very `review.py` this slice introduces. Verdict: pass, no blocking issues.
- [x] Deviation log produced (see below)
- [x] Reconciliation review pass

**Anti-horizontal-phasing check:** ✅ End-to-end: implementer finishes → SKILL.md tells Claude to run `review.py implementation` → constructed prompt is fed to Task → reviewer subagent returns verdict → Claude acts on it.

### Deviation log (after reconciliation)

The original spec is preserved above.

**Design choices logged:**

1. **`find_slice_label` is duplicated from `workflow.py`'s `find_slice_section`** rather than imported. Both functions use the same regex (`(?im)^##\s+Slice\s+([^\n]+)$`), the same lowercase-substring match, and the same not-found / ambiguous semantics. The only difference: `review.py` captures the label (for the prompt); `workflow.py` doesn't (it only needs the bounds). Plan documented this as option B (duplicate) with the rationale: small function, stable regex, and option C (shared utility) is overkill for two callers. **If a third helper ever needs this lookup, that's the trigger to extract `skills/_common/parsing.py`.**

2. **The helper does not spawn the Task itself** — it only constructs the prompt. This was a deliberate split: Claude owns the LLM-invoking layer; `review.py` is the deterministic prompt-builder. Same pattern as `workflow.py`, `memory.py`, `scaffold.py`. Tests enforce this implicitly — `review.py` has no `Task` invocation surface in its imports.

3. **Two prompt modes share ~70% of the template** (preamble + prohibitions + output format) via Python string constants (`_PREAMBLE`, `_PROHIBITIONS`, `_OUTPUT_FORMAT`). The mode-specific bits (job framing, what-to-read, evaluation guidance) are inlined per builder function. Reviewer confirmed the divergence is in the right places.

**Dogfooding note:**

4. **The slice was reviewed using its own deliverable.** The implementation-review prompt fed to the reviewer subagent was built by the same `review.py` this slice introduces. This is the cleanest possible dogfood: if the helper builds a bad prompt, the reviewer's verdict on the helper would itself be unreliable, and the bug would surface in the review's output. The verdict came back `pass`, indicating the prompt was coherent enough to drive a useful evaluation. **The first review run of `review.py` was generated by `review.py`.**

**Reviewer-flagged minor notes (accepted as-is):**

5. **Implementation-prompt label is full ("001-01 — greenfield-scaffold")**, but the corresponding test asserts only the fragment ("001-01"). The actual behavior is correct (full label appears in the prompt); the test surface is just narrower than the behavior. Acceptable — the test guards the load-bearing contract (fragment present), and the full label is incidental UX. Could be tightened in a future slice if useful.

6. **SKILL.md mentions `subagent_type: "reviewer"`** as an option for users who have `agents/reviewer.md` loaded. The DoR explicitly stated the agent definition is intact (not part of this slice's scope), so this reference is correct but not verified by 004-01's tests. The existing `IntegrationTests` in `test_memory.py` (from slice 002-04) verify the reviewer agent definition's anti-memory-write prohibition — that test continues to pass.

**Doc updates from this slice:**

- `skills/independent-review/SKILL.md`: full rewrite from stub. Frontmatter `disable-model-invocation: true` removed. Body restructured into "What this skill does / How to use (Implementation review + Reconciliation review) / What gets put in the prompt automatically / Context isolation pattern / Gotchas" with explicit bash invocations.
- No `architecture.md` changes (helper colocated with its skill — same pattern as workflow.py / memory.py / scaffold.py).
- No ADR required.
- No `learnings.md` entry. The "dogfood the helper to review the helper" moment is a nice anecdote but not a generalizable lesson — it falls out naturally from the design.
