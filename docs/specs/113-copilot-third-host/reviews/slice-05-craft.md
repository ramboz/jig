---
slice: 113-05 — enforcing-hooks-and-permissions
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-09-16T17:53:42Z
prompt_source: review-113-05-craft.txt (jig:reviewer subagent, Opus)
substrate: non-interactive
---

Craft review on slice 113-05 (enforcing-hooks-and-permissions). Reviewer:
read-only jig:reviewer (Opus). VERDICT: pass.

The craft is strong and correct across all five focus areas.

- `copilot_permissions_floor.py::_pattern_to_regex()` (lines 111-120) derives each
  regex mechanically from the duplicated pattern string via `re.escape` on literals
  + `*`→`.*`, so it is injection-safe and has no false-negatives relative to the
  canonical floor. Unanchored `search` makes it a strict SUPERSET of Claude's
  prefix-anchored semantics (broader = more denials, never fewer). All 8 patterns —
  including the two mid-string force-push variants and `rm -rf` — are covered and
  tested end-to-end. Reads `tool_input["command"]` robustly; fails open on error.
- `copilot_hook_adapter.py` `--enforce` mode + `_interpreter_for` correctly preserve
  the child exit code, emit the deny JSON, pick `python3` for the `.py` floor, and
  keep the fail-open (advisory) vs fail-closed (enforcing spawn) asymmetry.
- Drift-guard + deny tests are non-vacuous: they run the REAL adapter in `--enforce`
  in front of the UNMODIFIED floor script with real camelCase payloads and assert
  exit 2 + deny body for destructive commands, with genuine safe-command negative
  controls.

Strengths:
- [strength][impl] `_pattern_to_regex` keeps the regex a transparent function of
  the duplicated pattern string; `PatternToRegexTests` escaping case is non-vacuous.
- [strength][impl] `EnforcingEndToEndTests` (test:206-302) is genuine positive-
  confirmation through the real adapter+floor with paired allow/deny controls;
  mid-string force-push cases exercised end-to-end — the capability justifying a
  Python floor over Copilot's prefix-only `shell()` syntax.
- [strength][impl] the standalone-ship duplication of `_PERMISSIONS_DENY_DEFAULTS`
  is appropriately scoped (matches the established `_COPILOT_TO_CLAUDE_TOOL_NAME`
  idiom), pinned by exact-tuple + coverage-set drift guards; not over-built.

Nits (non-blocking, carried to reconciliation):
- [nit][impl] `copilot_permissions_floor.py:130-136` — unanchored `regex.search`
  means a non-invoking mention (e.g. `echo "how to rm -rf a dir"`) is denied.
  Documented as intentional/"more protective"; acceptable for a fail-open,
  out-of-band-bypassable deliberateness gate. Flagging only so the broadening past
  Claude's prefix-anchored semantics is a conscious, logged choice.
- [nit][spec] slice-05 AC3 (lines 51-54) prose still prescribes rendering into
  `.github/copilot/settings.json` with `shell(git:*)`, but implementation was
  owner-reshaped to the enforcing `jig-permissions-floor.json` preToolUse hook.
  Reconcile the AC text (or add an amendment) so the record stops drifting.
