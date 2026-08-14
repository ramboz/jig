---
slice: 096-05 — anomaly-record-and-consumers
pass: compliance
verdict: pass
reviewer: jig:reviewer (independent, post-hoc close-out)
reviewed_at: 2026-08-14T20:09:56Z
prompt_source: review.py implementation (096-05)
---

## Compliance verdict — slice 096-05 (anomaly-record-and-consumers)

**Verdict: pass.** Independent read-only `jig:reviewer` pass over the on-disk
implementation (merged via PR #194), run during lifecycle close-out because the
slice shipped as WIP/IN_PROGRESS and never received its reviewer passes.

All seven ACs are met and exercised by non-vacuous tests:
- **AC1** `_substrate_lines` (review.py:786-809) derives the closed vocabulary
  (config / non-interactive / shown / not-shown) from observable state and
  consumes the 096-03 sidecar; records `applied_skill` + `shown_candidates`.
- **AC2** scope = `PASS_TO_CATEGORY` ∩ slice keying-mode; `--bug` / `--adr` use
  separate recorders that never stamp a substrate (bug-keyed `craft` → `n/a`,
  not `not-shown` — the load-bearing keying-mode fix). Asserted by
  `test_bug_keyed_craft_has_no_substrate`.
- **AC3** anomaly calibrated to the high-confidence tier + shown-but-no-pick
  (`unknown`); never fires on speculative/config/not-shown/non-interactive/absent.
- **AC4** `verdict_clears` unchanged (verdict-only predicate, explicit comment);
  `test_not_shown_artifact_still_clears_gate` confirms an anomaly artifact with
  `verdict: pass` still reaches REVIEWED.
- **AC5** two committed consumers — non-blocking `check-reviews` stderr advisory
  (exit contract unchanged) + `status-board` aggregate audit section.
- **AC6** pre-096 / hand-written artifacts (no substrate field) → `[]`, parse
  without error, defensive against malformed candidate data.
- **AC7** both blind spots (config anomaly-blindness; invisible recall failure)
  documented in `docs/skill-routing-verification.md` + spec, as accepted gaps.

**Non-blocking:** AC1's prose says "config key present" while the code stamps
`config` only when present AND resolvable (mirroring `_resolve_richer_for_pass`);
this is intentional and already disclosed in the slice deviation log ("AC1
wording vs implementation" note) — a documented deviation, not a gap. No code
change required.
