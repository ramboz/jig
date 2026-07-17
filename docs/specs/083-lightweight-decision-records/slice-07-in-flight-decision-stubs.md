---
status: DONE
dependencies: [083-04]
last_verified: 2026-06-26
frame_review: true  # host-grounding assumptions (PostToolUse on AskUserQuestion
#                   # fires + payload shape; UserPromptSubmit override capture) —
#                   # Claude-side here; Codex parity is 083-08 (deferred).
---

## Slice 083-07 — In-flight decision stubs

**Goal:** Harden the Tier-1 deterministic floor by capturing the structured
decision subset (AskUserQuestion answers, user default-overrides) **at decision
time**, to a durable per-session scratch log, so it survives even when the
end-of-session scan can't. The 083-04 Stop scan already extracts Tier-1 from the
Stop `messages` payload recall-free; this slice's marginal value is **resilience**
— it does NOT depend on the Stop payload retaining the AskUserQuestion tool
blocks (a documented scan risk), and it persists *before* Stop so a decision
survives an abnormal session end. The 083-04 triage reads the scratch log, merges
it with the scan, and dedups so a decision settled both ways surfaces once.

> **Honest scope (frame-critique correction).** This slice does **not** "shrink
> the recall residue" — the discursive load-bearing decision (the actual residue)
> is explicitly untouched, owned by 083-06's judgment prompts, and the Tier-1
> subset is *already* caught recall-free by the 083-04 scan when the payload is
> intact. 083-07 is a **robustness** layer over that cell (payload-loss / abnormal
> termination / earlier capture), not a new coverage cell.

**DoR:**
- ✅ 083-04 shipped the Stop-hook triage seam: `jig-decision-capture.sh`,
  `lib/decision_scan.py` (`scan`/`dedup`/`render_summary`/`Candidate`/
  `normalize_tokens`), and `lib/read_attribution.append_additional_context_event`.
- ✅ Hook-wiring pattern grounded: thin `.sh` wrapper + Python over stdin in
  `hooks/scripts/`; reusable logic in `hooks/scripts/lib/` with co-located
  `test_*.py`; registration in `hooks/hooks.json` (PreToolUse/PostToolUse/
  UserPromptSubmit/Stop matchers already present).
- ✅ Session-state convention grounded: per-session ephemeral state lives under
  `.jig/` and is git-ignored (e.g. `.jig/spec-ref`).

**Acceptance Criteria:**

1. **AskUserQuestion answer → in-flight stub.** On `PostToolUse` for
   `AskUserQuestion`, the hook appends a stub to
   `.jig/decision-scratch/<session>.log` carrying provenance: `who=user`, the
   quoted answer, a `source` tag, and a timestamp — written **at decision time**,
   before session end. Observable via the scratch file.
2. **User default-override → in-flight stub.** On `UserPromptSubmit`, if the
   user's message matches the override/correction patterns (reusing
   `decision_scan`'s Tier-2 markers — "should not", "instead", "override … default",
   "actually", …), the hook appends a stub with `who=user`, the quoted message,
   and a `source` tag.
3. **Ephemera produce no stub.** A blank/whitespace AskUserQuestion answer and a
   UserPromptSubmit message with no override marker append nothing.
4. **End-of-session triage dedups stubs vs scan (no double-surface).** The Stop
   hook reads the scratch stubs, merges them with `scan()` candidates, and a
   decision captured **both** in-flight and by the scan surfaces **once**
   (token-containment dedup), still owner-gated. Stubs with no scan twin still
   surface.
5. **Lifecycle: re-surface until recorded, then pruned (durability parity with
   the scan).** On each Stop the scratch is pruned of stubs whose decision is now
   recorded; an **un-recorded** stub persists and re-surfaces on the next Stop —
   exactly as a scan candidate does (the scan re-reads the transcript until the
   decision is recorded). The file is removed when empty. Per-session;
   git-ignored (jig repo) so it never commits. *(This corrects an earlier
   clear-after-one-surface design, which made an in-flight-only stub — the slice's
   unique-value case — strictly **less** durable than a scan-visible decision.)*
6. **Fail-open.** Any error in either hook leaves the session unaffected
   (exit 0, no output) — matching every other jig hook.

**Host note (Claude-side; Codex parity = 083-08, deferred):** AC1 depends on
`PostToolUse` firing for `AskUserQuestion` with the answer in the payload, and
AC2 on `UserPromptSubmit` exposing the prompt text — verified for Claude. Where a
host lacks these points, in-flight capture degrades to the 083-04 scan +
judgment prompts (no regression). 083-08 records the Codex capability cells.

**DoD:**
- [x] All ACs pass; full suite green (3007 tests OK, pyright clean); `uvx ruff check .` clean.
- [x] `lib/decision_scratch.py` unit-tested (append/read/write/prune/clear,
      stub→Candidate, dedup-vs-scan, answer extraction, override match, fail-open)
      + hook tests with synthetic PostToolUse / UserPromptSubmit / Stop payloads.
- [x] Reviewed by `reviewer` subagent (frame-critique + compliance + craft).
- [x] Deviation log + reconciliation sweep under this slice heading.
- [x] Hooks registered in `hooks.json`; scratch dir git-ignored; host packages
      rebuilt; `build_host_packages.py --check` green.

### Deviation log

- **Frame-critique R1 over-claim → honest reframe (load-bearing).** The slice
  originally claimed in-flight capture "most shrinks the recall residue." The
  frame-critique showed the 083-04 scan **already** extracts the Tier-1
  AskUserQuestion/override subset recall-free from the Stop payload, and the
  discursive residue is untouched. Reframed (slice Goal + `spec.md` honesty-note +
  083-07 section) to scope 083-07 as a **resilience** layer over the already-
  covered Tier-1 cell (survives Stop-payload tool-block loss; persists before Stop
  for abnormal termination; earlier capture) — not residue-shrink, not a new
  coverage cell.
- **Durability-asymmetry fix → re-surface-until-recorded (AC5 redesign).** The
  first design cleared the scratch after one surface, making an in-flight-only
  stub *less* durable than a scan candidate. Reworked the Stop hook to **prune
  only recorded stubs and persist un-recorded ones** (`prune_recorded_stubs` +
  `write_stubs`), so an un-recorded stub re-surfaces on the next Stop — parity
  with the scan. AC5 reworded; lifecycle tests added.
- **`decisions.py scan-session` → two libs (carried from 083-04).** Per 083-04's
  deviation, the read/scan side is `lib/decision_scan.py`; 083-07 adds the
  in-flight write/triage side as `lib/decision_scratch.py` (sibling lib, co-located
  test), invoked by the thin `jig-decision-inflight.sh` wrapper.
- **Added public seams to `decision_scan.py`** (`is_user_override`, `clip`) so the
  in-flight hook reuses the *exact* Tier-2 markers + quote-clipping the scan uses
  — no pattern drift. Inline correction to a DONE-slice module (ADR-0010: live
  code corrected inline).
- **Hook count 11 → 12.** Restated constants updated: `verify_install._EXPECTED_HOOK_SCRIPTS`
  + `test_install_contract` (the deliberate drift guards fired and were updated).
- **Craft nits addressed inline:** added the `_DEDUP_MIN_TOKENS` floor to
  `dedup_scan_against_stubs` (parity with sibling dedup paths); removed a
  redundant `except FileNotFoundError`. **Deferred (low value, → refinement):**
  stub `turn=-1` discards the real decision-time turn; multi-question
  AskUserQuestion answers concatenate into one stub quote.

### Reconciliation sweep

- `hooks/scripts/lib/decision_scratch.py` + `test_decision_scratch.py` — **updated** (new lib + 23 tests).
- `hooks/scripts/jig-decision-inflight.sh` + `test_jig_decision_inflight.py` — **updated** (new hook + 7 tests).
- `hooks/scripts/jig-decision-capture.sh` + `test_jig_decision_capture.py` — **updated** (Stop merge/prune/dedup + lifecycle tests).
- `hooks/scripts/lib/decision_scan.py` — **updated** (public `is_user_override` + `clip` seams).
- `hooks/hooks.json` — **updated** (PostToolUse `AskUserQuestion` + UserPromptSubmit registration, `async: true`).
- `.gitignore` — **updated** (`.jig/decision-scratch/`).
- `scripts/verify_install.py`, `scripts/test_install_contract.py` — **updated** (12-hook restated constants).
- `docs/specs/.../spec.md` — **updated** (honesty-note + 083-07 section honest-scope correction).
- `hosts/claude/**`, `hosts/codex/**` — **updated** (rebuilt; `--check` green).
- `docs/architecture.md` — **updated** (the hook-spine inventory hardcodes a count
  + per-hook diagram — a restated constant like `_EXPECTED_HOOK_SCRIPTS`; bumped
  "11 hooks"→"12", added the `decision-inflight` node, and recategorized it as the
  async write-only hook in the prose. *(Reconciliation-review catch: originally
  mis-dispositioned as no-op.)*)
- `docs/refinement-todo.md` — **deferred** (the two low-value nits above are candidates; not logged as blocking).
- `CLAUDE.md` / `docs/specs/README.md` — board updated at close-out; primer Active-specs entry stays (spec 083 still open via 083-08, deferred).

## Amendments

### 2026-07-16 — AC5 lifecycle inverted by bug 011 (prune → flag)

**AC5 ("Lifecycle: re-surface until recorded, then pruned") no longer describes
shipped behaviour.** Amendment record, not an AC edit, per
[ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md).

`prune_recorded_stubs` mirrored `decision_scan.dedup`'s containment rule — by
design, so the two surfaces agreed — and therefore inherited the same defect
found in [bug 011](../../bugs/011-decision-dedup-suppresses-reversals.md): an
in-flight user override that *reverses* a recorded decision overlaps it heavily
and was silently pruned, on the highest-fidelity capture surface there is. The
maintainer extended the fix to this path in the same exchange.

Effective behaviour as of bug 011:

- `prune_recorded_stubs()` → `flag_recorded_stubs()`. A stub whose decision
  looks recorded is flagged `possible_duplicate` and **kept**; nothing is pruned
  against the recorded corpus.
- Stubs therefore persist for the life of the session and re-surface on every
  Stop, recorded or not — durability parity with a scan candidate is preserved,
  and the "then pruned" half of AC5 is withdrawn.
- Consequence worth naming: `clear_scratch` is no longer reachable for a
  populated scratch log, so a per-session log now outlives its session on disk.
  Parked in [refinement-todo.md](../../refinement-todo.md); it is bounded
  (append-only, 240-char clip, git-ignored) and no one has reported it.

AC4's `dedup_scan_against_stubs` (scan-vs-stub, no-double-surface) is
**unchanged** and still drops: it collapses one decision captured both ways into
a single line, which is duplication with no triage value.
