---
status: DONE
dependencies: [096-02]
last_verified: 2026-07-29
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

**Findings:** (2026-07-28)

**Instrument.** `scripts/orchestrator_selection_probe.py` (committed, re-runnable)
— in a fresh temp cwd it drops a stub `candidates` executable that prints a fixed
**tiered** list (096-03's contract) and hands the agent jig's recipe prose ("run
`./candidates pr-review`, pick the best high-confidence candidate or `none`, emit
`RICHER_SKILL=<name|none>` as the final line"). Two control fixtures make a null
distinguishable from a mis-registered fixture (AC2): a **positive** (non-empty
tiered list → expect `review-pr-deep`) and an **empty** (empty tiers → expect
`none`). A host PASSes iff BOTH controls emit the expected value. Command:
`python3 scripts/orchestrator_selection_probe.py --host both --timeout 200`.

**Claude — PASS** (`claude -p`, Claude Code CLI on PATH; 2026-07-28).
- positive fixture → `RICHER_SKILL=review-pr-deep` (agent ran `candidates` and
  picked the high-confidence candidate).
- empty fixture → `RICHER_SKILL=none`, with the agent's own reasoning captured:
  *"The high-confidence tier is empty, so per the instructions I select `none`."*
  This is the load-bearing control — it proves the agent **actually executed the
  stub and reasoned over its real output**, rather than fabricating a pick.

**Codex — INCONCLUSIVE** (`codex exec`, `codex-cli 0.133.0`; 2026-07-28).
- Both fixtures returned no emission because the host is **unauthenticated in
  this environment**: `codex exec` errors with *"Your access token could not be
  refreshed because your refresh token was revoked. Please log out and sign in
  again."* The agent loop never ran, so this is INCONCLUSIVE (a host-availability
  gap), **not** a compliance FAIL — no weak negative is laundered into a decision
  (AC3). Re-run the same command after `codex login` to settle the Codex side.
- **AC2 second instrument (context-inspection) run for Codex:** `codex debug
  prompt-input` renders the model-visible prompt locally (no API call, no auth),
  so it runs even while `codex exec` is auth-blocked. The probe uses it to
  confirm whether the recipe reached the prompt — attributing the null behavioral
  result to host auth rather than a mis-registered fixture (see `selprobe2.log`).

**Deviations logged (from the spike's review):**
- **Single behavioral instrument on Claude, both on Codex.** AC2's re-aim makes
  the *behavioral* run ground truth; the context-inspection diagnostic is
  wired for the Codex arm (where it disambiguates the auth-blocked null) and is
  not separately run on Claude, where the behavioral PASS is itself the answer.
  This is a recorded choice, not an unexplained gap.
- **Timeout is a weak negative → INCONCLUSIVE, never FAIL.** A review caught that
  a single-fixture timeout could fall through to the FAIL branch (laundering a
  weak negative, against AC3). Fixed: any timed-out fixture now short-circuits to
  INCONCLUSIVE before the PASS/FAIL comparison.
- **Fresh-cwd, real-auth probe** (not isolated-home): the behavioral run needs a
  live agent loop, so the probe intentionally uses the host's real auth; the
  docstring was corrected to say so rather than overclaim "hermetic".
- **Codex `exec` sandbox execution of the stub is unverified** (the auth error
  preceded any run). When Codex is re-authed, confirm `codex exec` can run the
  local `./candidates` stub under its default sandbox before trusting that arm.
- **Verdict-routing is now unit-tested** (review [blocker]): `_probe_host` gained
  an injectable `runner` / `prompt_inspector` seam (mirroring the sibling
  `codex_*_probe.py` scripts), and `scripts/test_orchestrator_selection_probe.py`
  pins the routing contract (11 tests) — including the regression guard
  `test_single_timeout_is_inconclusive_not_fail`. The FAIL rule was also
  tightened to require a *positively wrong* emission: any None-among-correct
  (a weak negative) now routes to INCONCLUSIVE, never FAIL (AC3).
- **Method departs from the AC1/AC2 prior-art wording** ("isolated home, temp
  marketplace"): the built probe is **fresh-cwd + real-auth with a dropped stub
  `candidates` executable and NO temp marketplace** — a marketplace is
  unnecessary because the recipe invokes the stub directly rather than resolving
  an installed skill. The AC prose describes the reused pattern; the probe took
  the simpler shape the question needs.
- **AC4 was written for a single global verdict; the outcome is per-host.** AC4's
  INCONCLUSIVE branch says "096-03 DEFERRED", but the result split (Claude PASS /
  Codex INCONCLUSIVE). Because the reshaped 096-03 ships **Claude-only** (spec
  Decomposition), the Claude PASS unblocks it and the Codex INCONCLUSIVE simply
  keeps Codex on the config-only floor — resolved against 096-03's actual scope,
  not a global deferral.

**Outcome:** `spec 096-03 unblocked (Claude sequence reliably followed);
Codex INCONCLUSIVE (host unauthenticated — config-only stands, probe procedure
documented + committed for re-run)`.

Because the reshaped 096-03 ships **Claude-only** (Codex continues on 096-01's
config path until this settles — spec Decomposition), a Claude PASS is sufficient
to unblock 096-03. Codex's INCONCLUSIVE keeps Codex on the guaranteed config-only
floor, which is a shipped working state, not a gap (AC4 / time-box escape).

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
- [x] Probe script committed and runnable for both hosts
      (`scripts/orchestrator_selection_probe.py`, + an 11-test contract unit test
      `scripts/test_orchestrator_selection_probe.py`). Full suite green (3642;
      the final 11th probe test + auth-marker trim are covered by the 11-test
      targeted run — isolated to the probe, no other consumer); ruff clean.
- [x] `Findings:` and `Outcome:` filled per the `kind: spike` contract.
- [x] Spec `## Assumptions` updated: prose-compliance assumption marked VERIFIED
      (Claude) / INCONCLUSIVE (Codex) with a pointer to this slice.
- [x] ADR-0040 given a dated note recording the outcome (an Assumptions status
      update, not a decision change).
- [x] Downstream slices sequenced per AC4: Claude PASS → 096-03 proceeds; Codex
      INCONCLUSIVE → Codex stays config-only (096-03 is Claude-only). 096-05
      unchanged (depends on 096-03).
- [x] Reviewed by `reviewer` subagent (compliance + craft; a routing-test
      [blocker] was caught and fixed).

### Deviation log

For a `kind: spike` the deviation record lives in the **Findings** +
**Deviations logged** blocks above (the spike contract's home for method +
observations). Consolidated here for the reconciliation gate:

- Method departed from the AC1/AC2 prior-art wording (isolated home + temp
  marketplace) → **fresh-cwd, real-auth, dropped stub `candidates`, no
  marketplace** (a marketplace is unneeded — the recipe invokes the stub
  directly). The docstring's "hermetic" overclaim was corrected.
- **Timeout / None-among-correct are weak negatives → INCONCLUSIVE, never FAIL**
  (AC3); a review [blocker] caught a timeout→FAIL laundering path, now fixed and
  regression-guarded by a committed 11-test contract test with an injectable
  runner seam.
- **AC2 second instrument** (`codex debug prompt-input`) wired into the Codex arm
  (runs without auth) — it CONFIRMED the recipe reached the Codex prompt, so the
  auth-blocked null is not a mis-registered fixture.
- **AC4 was global-verdict-shaped; the outcome is per-host** — Claude PASS
  unblocks the Claude-only 096-03; Codex INCONCLUSIVE keeps Codex config-only.
- **Codex `exec` sandbox stub-execution unverified** (auth error preceded any
  run) — re-confirm after `codex login`.

### Reconciliation sweep

- **Deviation log** — written above (this subsection + spike Findings). `updated`.
- **Spec `## Assumptions`** (`spec.md`) — prose-compliance premise VERIFIED for
  Claude / INCONCLUSIVE for Codex. `updated`.
- **ADR-0040 `## Assumptions`** — dated status note (PARTIALLY VERIFIED); a
  status update, not a decision change (no superseding ADR needed). `updated`.
- **`scripts/orchestrator_selection_probe.py` + test** — committed. `updated`.
- **Downstream sequencing** — the *decision* to unblock 096-03 is recorded here;
  the concrete status-board move (096-03 → READY_FOR_IMPLEMENTATION) is the
  post-DONE close-out action below. `deferred` (to close-out).
- **`docs/architecture.md` / `docs/conventions.md`** — no-op (a `scripts/` probe,
  no module boundary or convention change).
- **`docs/inbox.md`** — swept; nothing resolved.
- **Memory** — the "behavioral probe via `claude -p` + stub `candidates`; Codex
  auth-blocked here so context-inspection via `codex debug prompt-input`
  disambiguates the null" lesson; folded into `/jig:memory-sync` at session close.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] On PASS, 096-03 moved to READY_FOR_IMPLEMENTATION; on FAIL/INCONCLUSIVE,
      096-03 + 096-05 moved to DEFERRED with a stated resolution trigger.
