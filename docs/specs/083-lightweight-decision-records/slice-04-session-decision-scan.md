---
status: DONE
dependencies: [083-01]
last_verified: 2026-06-25
frame_review: true  # premise frame-critiqued at spec level (3 rounds) — see
#                   # reviews/slice-04-frame-critique.md
---

## Slice 083-04 — Session decision scan (Stop hook)

**Goal:** Replace recall with a deterministic session-end **scan**. A
`jig-decision-capture.sh` Stop hook (sibling of `jig-task-capture.sh`) surfaces
candidate decisions from the completed session as owner-gated `additionalContext`
for next-turn triage — the scan runs out-of-band (only the candidate list enters
orchestrator context). The scan **claims only the tiers it can reliably detect**;
load-bearing discursive decisions are owned by 083-06's judgment prompt, not here.

**DoR:**
- ✅ Premise frame-critiqued at spec level over three Opus rounds
  (`reviews/slice-04-frame-critique.md`) — converged on the two-tier model.
- ✅ Pattern grounded: hooks are thin `.sh` wrappers; reusable logic lives in
  `hooks/scripts/lib/` with co-located `test_*.py` (`context_fill.py` precedent);
  `jig-task-capture.sh` is the Stop-hook model; `lib.read_attribution.append_
  additional_context_event` is the surfacing seam.
- ✅ Tiering + adversarial-AC requirements fixed by the frame-critique.

**Acceptance Criteria:**

1. **Tiered detection, honest about reach.** The scan detects, with explicit
   tier + confidence:
   - **Tier 1 — AskUserQuestion answers** (structured: an `AskUserQuestion`
     tool-use paired with its answer) — high confidence.
   - **Tier 2 — explicit user corrections** ("X should not be the default", "do A
     instead", "actually …", "instead of …") — high confidence.
   - **Tier 3 — agent settled choices** ("chose A over B", "rejected because",
     "going with") — **low** confidence, best-effort.

2. **Per-role provenance (who + quote).** Every candidate carries *who decided*
   (`user` vs `agent`) and the quoted evidence line + turn index. The scan
   **must not flatten** messages into one string (the divergence from
   `jig-task-capture.sh`, which does flatten and so cannot attribute).

3. **Ephemera excluded.** Operational chatter ("let me run the tests", "let me
   check") produces no candidate.

4. **Adversarial fixture (ungameable).** The test fixture includes one
   load-bearing design choice phrased with **no** Tier-1/2/3 trigger pattern; the
   scan is asserted to **honestly miss it** (not surface it), and the test
   documents that this case is owned by 083-06's reconciliation/memory-sync
   judgment prompt — not 083-04. The AC cannot be passed by writing
   regex-matching fixture lines.

5. **Dedup against recorded decisions.** Candidates matching an already-recorded
   decision (`lightweight-decisions.md`, ADRs, `refinement-todo.md`) via a
   stated normalized-substring strategy are suppressed, so repeat runs stay quiet.

6. **Owner-gated, out-of-band.** The hook never writes a decision; it only
   surfaces candidates as `additionalContext`. The scan runs in the hook
   (Python over stdin), never in orchestrator context.

7. **Fail-open.** Any error in the scan leaves the session unaffected (exit 0,
   no output) — matching every other jig hook.

---

### Deviation log

- **`decisions.py scan-session` realized as `hooks/scripts/lib/decision_scan.py`**
  (a lib module), not a standalone `decisions.py` CLI. Rationale: jig's
  established pattern puts reusable, unit-testable hook logic in
  `hooks/scripts/lib/` (`context_fill.py` + `test_context_fill.py`), and the
  spec's binding requirement is "testable in isolation" — which the lib module
  satisfies better than inline-heredoc python or a separate CLI. The user-facing
  `decisions.py` CLI (`add-lightweight`) remains 083-05's deliverable and will
  import the scan from this module. This is a load-bearing placement choice,
  logged here per the deviation mechanism.

**Craft-pass fixes (non-blocking nits applied):**
- Added `actually` as a Tier-2 user-correction marker — the craft reviewer's
  highest-value missing high-confidence signal; Tier 2 is user-role-only so its
  false-positive surface is small.
- Added a `_DEDUP_MIN_TOKENS` floor (3): a candidate with fewer meaningful tokens
  is never deduped away, preventing over-suppression of terse novel decisions
  (e.g. "Use Redis instead.") that trivially clear the containment threshold.
- Logged-not-fixed (cosmetic): the hook builds `recorded` via both paragraph-
  split and per-line extraction (harmless double-count under OR semantics);
  `%`-format vs `context_fill.py`'s f-strings (lib-tier stylistic drift).

**Install-contract drift caught by the suite (expected):** registering an 11th
hook required updating `scripts/verify_install.py::_EXPECTED_HOOK_SCRIPTS` and
`scripts/test_install_contract.py` (ten→eleven) — the trio drift-guards working
as designed.

### Reconciliation sweep

| Surface | Status | Notes |
|---|---|---|
| `hooks/scripts/lib/decision_scan.py` | updated | new — scan logic (tiered patterns, per-role provenance, dedup) |
| `hooks/scripts/lib/test_decision_scan.py` | updated | new — 15 unit tests incl. adversarial fixture + dedup floor |
| `hooks/scripts/jig-decision-capture.sh` | updated | new — thin Stop hook |
| `hooks/scripts/test_jig_decision_capture.py` | updated | new — 6 hook-integration tests |
| `hooks/hooks.json` | updated | register hook on Stop (alongside task-capture) |
| `scripts/verify_install.py` | updated | `_EXPECTED_HOOK_SCRIPTS` += jig-decision-capture.sh |
| `scripts/test_install_contract.py` | updated | hook-count assertion ten→eleven |
| `docs/architecture.md` | updated | hook-spine diagram + prose (ten→eleven; sibling Stop hooks) |
| `hosts/` (claude + codex) | updated | regenerated; hook + lib + verify_install ship in release zip; drift `--check` green |
| `docs/conventions.md` | no-op | no convention change |

## Amendments

### 2026-07-16 — AC5 inverted by bug 011 (dedup → flag)

**AC5 ("Dedup against recorded decisions … are suppressed, so repeat runs stay
quiet") no longer describes shipped behaviour.** This is an amendment record,
not an edit to the AC, per [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md).

[Bug 011](../../bugs/011-decision-dedup-suppresses-reversals.md) (reported as
[issue #109](https://github.com/ramboz/jig/issues/109)) found the suppression
silently dropped decisions that *reverse* a recorded one: containment measures
topical overlap, not agreement, and a reversal shares the record's component,
property and vocabulary, so it scores *high*. The mechanism was strongest
exactly where it was most wrong — the better a decision was recorded, the more
reliably its reversal was suppressed.

The maintainer's decision: drop suppression outright; flag instead and let the
owner triage. Effective behaviour as of bug 011:

- `dedup()` → `flag_duplicates()`. Nothing is dropped against the recorded
  corpus; overlap sets `Candidate.possible_duplicate`.
- `render_summary()` marks flagged items `possible duplicate` and asks the owner
  to check each, since overlap cannot tell a repeat from a reversal.
- Repeat runs are consequently **noisier**, not quiet — an accepted trade.
  AC5's "so repeat runs stay quiet" rationale is withdrawn.

The `_DUPLICATE_CONTAINMENT = 0.6` threshold and the `_DUPLICATE_MIN_TOKENS`
floor survive unchanged; only their consequence changed (flag, not drop).
