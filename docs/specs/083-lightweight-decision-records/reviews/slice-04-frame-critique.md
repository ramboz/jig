---
slice: "083-04"
pass: frame-critique
verdict: needs-changes
reviewer: jig:reviewer (Opus)
reviewed_at: 2026-06-25
verdict_history: "round1 needs-changes → round2 needs-changes → round3 needs-changes (framing); all fixes applied; architecture sound, premise honestly framed"
prompt_source: "frame-critique (ADR-0020 / spec 064-03) on spec 083 Phase 2 recall→scan premise, THREE rounds; prompt authored by orchestrator (review.py slice-resolution requires a `## Slice` file, which Phase-2 DRAFT slices do not yet have)"
---

# Frame-critique — spec 083 Phase 2 (recall→scan premise)

**Note on scope:** this gates the Phase-2 premise (slices 083-04..07) at the
spec level. Recorded against `083-04` as the keystone slice. **Three adversarial
rounds were run (all Opus). R1/R2 found design holes; R3 found a framing
over-claim and was *stabilizing* (explicitly "not a wrong premise — fix the
prose"), signalling convergence. All fixes applied; iteration stopped at R3.**

## Round 1

VERDICT: needs-changes

## Load-bearing assumption attacked

That a lexical/regex Stop-hook scan (modeled on `jig-task-capture.sh`) can
reliably surface the **high-value, ADR-worthy** decisions — the exact class the
reframe was built to catch — not merely the easy decisions that carry a
recognizable trigger phrase.

## The case against it

1. **The motivating example is the worst case for a lexical scan.** food-log's
   loss was "a load-bearing design choice with rejected alternatives." But the
   more load-bearing a decision, the less likely it is announced with a stock
   phrase ("chose A over B", "rejected because") — those tidy phrases describe
   *small, already-clear* choices. `jig-task-capture.sh` flattens all message
   text and runs `re.findall` over literal patterns (zero semantics). A
   precision-first lexical filter is therefore structurally biased to catch
   lightweight decisions and miss ADR-worthy ones — the inverse of the goal.
2. **"Precision over recall" guarantees the miss.** The filter can't distinguish
   "marginal-and-lexically-clean" from "load-bearing-and-lexically-quiet"; it
   sheds whatever lacks a trigger phrase, and load-bearing decisions are
   disproportionately in that set.
3. **The hook-native correction severed two coupled risks.** Running the scan
   out-of-band dissolves *token cost* but also removes the only faculty
   (semantic judgment from an agent reading the transcript) that could catch the
   trigger-phrase-free load-bearing case. The spec presented this as a pure win.
4. **083-04's AC was unfalsifiable-by-construction:** the fixture author writes
   evidence lines containing the patterns the regex looks for, so it passes by
   intent, not detection power.

## Recommended reframe / fix (ALL APPLIED to spec.md, 2026-06-25)

- **Tier the capture claim.** Tiers 1–2 (AskUserQuestion answers; explicit user
  corrections) are structurally/lexically detectable — the deterministic win.
  Tier 3 (agent-internal settled-choice reasoning) is **best-effort, not relied
  on** for load-bearing decisions.
- **Re-anchor the load-bearing safety net on 083-06** (the widened
  reconciliation ADR-trigger — a *judgment* prompt needing no trigger phrase),
  not the regex scan. 083-04 stops over-promising the ADR-worthy case.
- **Make 083-04's AC adversarial:** the fixture must phrase ≥1 load-bearing
  decision with NO literal pattern; assert the scan honestly misses it and the
  case is owned by 083-06.
- **AskUserQuestion = in-flight structured capture (083-07) is the more robust
  form** than end-of-session prose reconstruction; recorded as a sharpened note.

## Residual risks (recorded in spec Risks / slice notes)

- Provenance (who-decided) needs **per-role tracking**; `jig-task-capture.sh`
  flattens content into one string (line 35), destroying role boundaries — a
  real divergence from the "modeled on" hook.
- Per-host Stop payload must expose the **AskUserQuestion answer shape**
  specifically, not just `messages[].content` bodies.
- Dedup-against-recorded needs an explicit fuzzy-matching strategy.
- Single-sourcing the ADR-trigger wording across a `.py` rubric + two markdown
  checklists needs a stated mechanism, or drift is the default.

## Round 2 (after applying Round-1 fixes)

VERDICT: needs-changes

**Load-bearing assumption attacked:** that 083-04 (scan) and 083-06
(reconciliation judgment trigger) *together partition the decision space with no
gap*. They do not.

**The case against it:** Round 1's fix re-anchored the load-bearing case on
083-06 — but 083-06 widens the **reconciliation** checklist, and the spec states
in three places that out-of-spec work has **no reconciliation phase** (the very
sessions this spec serves). So a load-bearing decision that is (a) off-spec AND
(b) phrased with no trigger phrase is missed by 083-04 (by its own adversarial
AC) **and** never reaches 083-06 (no reconciliation). The repair relabeled the
crack from "the regex can't see it" to "the prompt never runs" — the same
decision (the food-log founding case) still falls through. Coverage *does* exist
in 083-03's session-end memory-sync judgment prompt (fires regardless of
reconciliation), but the Phase-2 partition never named it as the out-of-spec
owner, and its trigger is gated on an *enumerated surface list* (UI/visual/
translation) that re-imports the detectability bias.

**Fixes applied (2026-06-25):**
1. Overview now states an explicit **three-way coverage map** (table): scan
   owns lexically-detectable (any session); reconciliation judgment owns in-spec
   load-bearing; **memory-sync session-end judgment owns out-of-spec
   load-bearing**.
2. **083-06 rescoped** to widen the load-bearing judgment clause in **both**
   session-end surfaces (reconciliation + memory-sync), single-sourced across
   four sites with a CI string-match test. The memory-sync condition gains a
   **judgment escape hatch** ("any load-bearing decision a future agent would
   need to know to avoid undoing"), not just the enumerated surface list.
3. **083-04's AC** now asserts the correct judgment owner *per fixture context*
   (in-spec → reconciliation; out-of-spec → memory-sync) — it cannot be
   satisfied by claiming reconciliation catches an out-of-spec decision.

**Residual (Round 2):** the memory-sync escape-hatch is still a judgment call an
agent could under-apply; the owner-gate + the OQ4 rubric wording are the backstop.
A Round-3 confirmation pass is advisable before DRAFT → READY_FOR_REVIEW, given
each round so far surfaced a real deeper flaw.

## Round 3 (after applying Round-2 fixes) — CONVERGENCE

VERDICT: needs-changes (framing) — **stabilizing, not a wrong premise.**

**Load-bearing assumption attacked:** that the three-way coverage map
*eliminates* recall-dependence for the decisions worth keeping (the spec's
headline promise), rather than quietly re-introducing recall under a new name.

**The case against it:** the partition is exhaustive (no empty cell) but **not
homogeneous in mechanism class**. Two of the three owners (reconciliation +
memory-sync judgment prompts) are *attention/recall* mechanisms — the very
faculty the Overview condemns. The Round-2 "judgment escape hatch" for the
out-of-spec load-bearing cell relocates recall-dependence; it does not remove it.
Meanwhile the Overview still sold "Phase 2 replaces recall with a deterministic
scan." So the **founding promise over-claimed relative to the delivered
mechanism** — the deterministic part covers only the lexical tier; the
load-bearing tier got a *widened judgment prompt*, not determinism. Reviewer
explicitly: "not a wrong premise (so not `fail`)… the architecture is fine — a
deterministic floor plus a judgment ceiling — the defect is that the spec must
honestly downgrade its own promise."

**Fixes applied (2026-06-25):**
1. **Overview "Honest scope of the promise" note** — Phase 2 is now stated as a
   **two-tier** claim: deterministic capture for lexical Tiers 1–2;
   recall-*reduced-not-eliminated* for load-bearing decisions owned by judgment
   prompts. Removed the "replaces recall" over-claim from the Phase-1/2 paragraph.
2. **Recall-residue promoted to the first-billed Phase-2 Risk** — the memory-sync
   escape hatch is an attention prompt, not a capture guarantee; only 083-07
   in-flight capture is recall-free, and only for the Tier-1 subset.
3. **083-07 resolution trigger tightened** — pull Tier-1 in-flight capture
   forward as soon as the per-host grounding fails OR pilot shows judgment prompts
   under-firing, not only on observed end-of-session misses.

**Convergence read:** R1→R2 moved the load-bearing decision between blind/judgment
owners (real holes). R3 found no new hole — it found the spec *overselling a sound
architecture*. That is the design floor: a deterministic floor (lexical scan) +
an honestly-labelled judgment ceiling. **Iteration stopped here**; further rounds
would re-evaluate an honestly-framed, sound architecture. Remaining items
(per-host payload grounding, dedup fixtures, single-source string test guards
spelling-not-behaviour) are **implementation-time** concerns, not premise flaws.

## Post-critique maintainer decisions (2026-06-25)

- **083-07 promoted DEFERRED → ACTIVE** — implements R3's strengthening
  recommendation directly (in-flight Tier-1 structured capture is the only
  recall-free path for a load-bearing decision). This narrows the recall residue
  to *discursive* load-bearing decisions; the Overview honest-scope note and the
  first-billed Risk were updated to match.
- **083-08 added — Codex host validation (handoff)** — the deterministic
  mechanisms are proven only for Claude; R1's "per-host grounding" residual and
  R3's per-host note are elevated to a discrete dual-host parity slice the
  maintainer completes on the Codex runtime (payload/hook shapes can't be
  confirmed by Claude-side inspection). Honest host-capability matrix required.
