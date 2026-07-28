---
status: DRAFT
dependencies: [096-02]
last_verified:
frame_review: true
kind: spike
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 096-04 — orchestrator-selection-compliance

**Goal:** Settle whether an orchestrator reliably runs the
`candidates → pick → --richer-skill` sequence against jig's own prose — the
design's self-declared most likely failure mode (ADR-0040 Assumptions) — **before**
the zero-config machinery (096-03) is built. Re-aimed from ADR-0039's retired OQ6
(host-injected metadata) to this jig-side question, and re-sequenced ahead of
096-03 so it gates the machinery rather than following it.

**Question:** Given jig's SKILL.md recipe and a working `candidates` step, does
the orchestrating agent — on each host — actually run the sequence and pass a
valid `--richer-skill <name|none>` back? This is a **necessary-condition floor
test**: a stub probe inherently foregrounds the recipe, so a PASS establishes
*reachability* ("is the recipe followable at all"), not durability under
mid-slice cost pressure — durability rests on 096-05's `substrate:` aggregate
(ADR-0040 Assumptions). A FAIL is nonetheless a cheap, decisive kill of the
machinery before it ships.

**Time-box:** 4 hours. If unresolved at the box, record `abandoned
(inconclusive)` and the zero-config layer stays gated — Codex *and* Claude fall
back to config-only (096-01), a shipped working state, not a gap.

**Why a spike is justified here** (SPIDR's S is last-resort): P/I/D/R cannot
apply — there is no rule, path, interface, or data subset to split. The unknown
is a behavioral property of the orchestrating agent under cost pressure that no
decomposition resolves, and it is cheap to probe and expensive to assume. It is
sequenced *before* the machinery so a FAIL saves building it.

**Why this is probeable now (not blocked on 096-03):** the probe is **stub-based**
— a fake `candidates` script that prints a fixed tiered list plus the real (draft)
SKILL.md recipe is sufficient to observe whether the sequence is followed. It
does not need 096-03's real enumerator.

**DoR:**
- ✅ 096-02 DONE — name→path resolution + exclusion exist, so a stub `candidates`
  can print realistic names the pass can resolve.
- ✅ `codex-cli` installed locally (verified 0.133.0).
- ✅ Prior art to reuse: `scripts/codex_agent_discovery_probe.py` and
  `scripts/codex_role_capability_probe.py` build a temp marketplace and run
  Codex under an isolated `CODEX_HOME`; the first inspects the assembled prompt
  JSON via `codex debug prompt-input` (the direct instrument).

**Findings:** _(filled during IN_PROGRESS)_

- _TBD — record the probe method and the raw observation, not just the
  conclusion. Include the exact command, host, and version for each run._

**Outcome:** _(set at DONE — one of: `spec 096-03 unblocked (sequence reliably
followed)` / `abandoned (sequence not reliably followed — zero-config layer
shelved, config-only stands)` / `abandoned (inconclusive within time-box)`)_

**Acceptance Criteria:**

1. **A reproducible probe exists and has been run on both hosts.** Following the
   existing probe scripts' pattern (isolated home, temp marketplace), a probe
   installs jig's (draft) SKILL.md recipe + a stub `candidates` and observes,
   non-interactively, whether the agent runs the sequence and emits a valid
   `--richer-skill` value. Run against Claude and Codex.
2. **Both instruments are used; for this re-aimed question the behavioral run is
   ground truth.** The question is *compliance* (did the agent run the step?),
   not *visibility* (what was in the prompt) — so "did it emit a valid
   `--richer-skill`?" is the load-bearing observation, and context-inspection
   (`codex debug prompt-input`) is the supporting diagnostic that explains a
   negative (was the recipe even present?). This inverts the instrument priority
   inherited from the retired OQ6, which was a visibility question. A positive
   AND a negative control fixture are included, so a null is distinguishable from
   a mis-registered fixture. (`codex_role_capability_probe.py` already records
   that the debug surface under-reports — a null from either surface alone is not
   read as absence.)
3. **The result is recorded as evidence, not a claim.** Raw output in `Findings:`
   with commands + versions; a `PASS`/`FAIL`/`INCONCLUSIVE` outcome. The
   `INCONCLUSIVE` state is explicit and first-class — it does NOT collapse to
   FAIL, and no weak negative is laundered into a decision.
4. **The outcome decides a written next step.** On PASS: 096-03 is unblocked and
   proceeds. On FAIL: the zero-config layer is shelved and config-only (096-01)
   is confirmed as the shipped floor in prose — 096-03/096-05 are marked
   DEFERRED with a resolution trigger, not built on an unheld premise. On
   INCONCLUSIVE: same as FAIL for sequencing (096-03 DEFERRED), with the open
   question re-stated.

**DoD:**
- [ ] Probe script committed and runnable (or, if it cannot be automated, the
      manual procedure documented well enough to re-run) — for both hosts.
- [ ] `Findings:` and `Outcome:` filled per the `kind: spike` contract.
- [ ] Spec `## Assumptions` updated: the prose-compliance assumption marked
      VERIFIED / REFUTED / INCONCLUSIVE with a pointer to this slice.
- [ ] ADR-0040 given a dated note recording the outcome (an Assumptions/OQ
      status update, not a decision change — if the outcome changes the
      decision, write a superseding ADR).
- [ ] Downstream slices (096-03, 096-05) sequenced per AC4 (proceed / DEFERRED).
- [ ] Reviewed by `reviewer` subagent.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] On PASS, 096-03 moved to READY_FOR_IMPLEMENTATION; on FAIL/INCONCLUSIVE,
      096-03 + 096-05 moved to DEFERRED with a stated resolution trigger.
