---
slice: 113-05 — enforcing-hooks-and-permissions
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T17:53:42Z
prompt_source: review-113-05-compliance.txt (jig:reviewer subagent, Opus)
---

Compliance review on slice 113-05 (enforcing-hooks-and-permissions). Reviewer:
read-only jig:reviewer (Opus). VERDICT: pass.

All three acceptance criteria (AC3 as owner-reshaped) are met with rigorous,
non-vacuous tests:

- **AC1 (enforcing decision-schema)** — MET. `jig-spec-gate` + `jig-secret-scan`
  render as `preToolUse` hooks carrying the adapter `--enforce` flag (confirmed in
  build output `hosts/copilot/.github/hooks/jig-spec-gate.json`). The adapter's
  enforcing branch (`copilot_hook_adapter.py:273-316`) preserves the child exit
  code and emits a `permissionDecision: deny` body on non-zero; fails CLOSED on
  spawn error. Proven both directions: `test_spec_gate_denies_conventions_md_with_
  exit_2_and_a_deny_body` (deny) paired with `test_advisory_mode_stays_fail_open_
  for_the_same_blocked_edit` (same payload, no `--enforce` → exit 0).
- **AC2 (mapped-or-unmappable inventory)** — MET. `_JIG_HOOK_INVENTORY` contains
  all 19 hooks.json registrations (hand-counted) + the copilot-only floor; every
  entry carries status (SHIPPED/MAPPABLE/UNMAPPABLE) + notes. `HookInventoryCoverage
  Tests` cross-checks both directions structurally against the real hooks.json and
  asserts each SHIPPED entry is actually built — a real drift guard.
- **AC3 (permissions floor, owner-reshaped)** — MET. `copilot_permissions_floor.py`
  denies all 8 `_PERMISSIONS_DENY_DEFAULTS` patterns via exit 2, allows safe
  commands, fails-open on error, drift-guarded (`PatternsMatchCanonicalFloorTests`).
  Ships as a real enforcing `preToolUse` hook (`jig-permissions-floor.json`);
  `test_no_dead_settings_json_rendered` asserts no `.github/copilot/` dir exists.
- **113-04 schema correction** — verified on disk: floor, spec-gate, and the
  previously-nested advisory git-freshness hook all now use the flat
  `{version:1, hooks:{<camelCaseEvent>:[{matcher?, type, bash, timeoutSec}]}}` shape.

Test quality: all snapshot signals false; tests run the real adapter+scripts with
positive-confirmation assertions on exit codes and JSON bodies. No vacuous tests.

Non-blocking, carried to reconciliation:
1. **AC3 prose drift** — slice text (AC3, lines 51-54) still specifies
   `hosts/copilot/.github/copilot/settings.json` + `shell(git:*)`; shipped code
   deliberately does the opposite (enforcing preToolUse hook). Correct the AC3
   prose inline (IN_PROGRESS → live-prose fix) + log the reshape in the deviation
   log; the DoD "deviation log" box is correctly still unchecked.
2. **Unanchored `regex.search` divergence** — the floor blocks strictly more than
   Claude's prefix-anchored `permissions.deny` (a benign command merely containing
   e.g. `rm -rf` as a substring is denied). Documented + fail-safe (over-block),
   but an untested parity divergence — no test covers a safe command containing a
   destructive substring. Record as a deliberate, more-protective divergence.

Reconciliation notes:
- DoD requires the inventory be "written where a maintainer will find it
  (architecture.md and/or the slice record)". It currently lives only as
  `_JIG_HOOK_INVENTORY` (well-commented + tested); verify a maintainer-facing home.
- Confirm UNMAPPABLE residuals (Task/Skill/AskUserQuestion) + the unverified
  live-fire plugin-root path spelling are homed (113-06 or refinement-todo).
