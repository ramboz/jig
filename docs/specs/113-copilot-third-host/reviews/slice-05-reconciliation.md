---
slice: 113-05 — enforcing-hooks-and-permissions
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T18:05:39Z
prompt_source: reconciliation review (jig:reviewer subagent, Opus) — deviation-log + sweep verification
---

Reconciliation review on slice 113-05 (enforcing-hooks-and-permissions).
Reviewer: read-only jig:reviewer (Opus). VERDICT: pass.

Every load-bearing deviation-log + reconciliation-sweep claim verified against the
code/docs on disk — faithful, no silent gaps. Seven verification areas confirmed:

1. **AC3 reshape** — the dead `settings.json` render path is gone (only explanatory
   comments remain); the floor is a real enforcing `preToolUse` deny-hook
   (`jig-permissions-floor.json` + `copilot_permissions_floor.py`); the AC3 prose was
   corrected inline to describe the hook (not settings.json).
2. **Enforcing adapter mode** — `--enforce` preserves the child exit code (exit 2 →
   deny), emits `{permissionDecision:"deny", permissionDecisionReason}`, and fails
   CLOSED on spawn error, while advisory stays fail-open. Exhaustively test-pinned:
   `EnforcingModeTests` deny paths + advisory-stays-fail-open + a dedicated
   `EnforcingModeSpawnFailureTests.test_spawn_exception_denies_with_exit_2`.
3. **113-04 schema fix (folded)** — all six rendered `hosts/copilot/.github/hooks/*.json`
   use the FLAT `{version, hooks:{<event>:[...]}}` schema; no leftover nested shape.
4. **Anywhere-match divergence pin** — `test_anywhere_match_is_a_deliberate_divergence_
   from_claude_anchoring` exists and is non-vacuous (asserts a benign command
   containing a destructive substring IS matched — only passes under unanchored search).
5. **preToolUse single-sourcing** — `render_permissions_floor_hook` now uses
   `cls.copilot_event_name("PreToolUse")`, not a hardcoded string.
6. **Inventory-home blocker fix** — slice-06 carries a real AC6 (renders remaining
   MAPPABLE hooks, flips MAPPABLE→SHIPPED, test asserts none remain); the DoR is
   corrected; every inventory note reworded (no "homed to 113-06" remains).
7. **Sweep accuracy** — architecture.md host-adapter section updated with the enforcing
   gates + floor reshape + `_JIG_HOOK_INVENTORY`; refinement-todo genuinely carries the
   path-rewrite entry ("already homed" accurate); the 113-04 `## Amendments` note is
   correctly deferred to owner approval — 113-04's record has NO unauthorized amendment
   (respects the spec-102 amendment-authorization guardrail).

Strengths: enforce-mode spawn-failure fail-closed is not just implemented but pinned;
`test_no_dead_settings_json_rendered` is non-vacuous; the 113-04 amendment respects the
authorization guardrail.

One nit (non-blocking): the sweep's "hosts/ `--check` clean" claim can't be
independently confirmed under read-only/no-build constraints; the mirror artifacts are
present + consistent, and the DoD honestly flags full-suite confirmation as "in flight
before the DONE transition." Residual-verification note, not a defect. (Orchestrator
note: `build_host_packages.py --check` was run directly and returned "in sync" before
this review.)
