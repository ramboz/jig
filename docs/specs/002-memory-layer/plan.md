# Plan: Slice 002-03 — auto-detect-hooks

## Approach

The two hooks (`jig-memory-scan.sh` on `UserPromptSubmit`, `jig-task-capture.sh` on `Stop`) were stubbed back in the starting move and have been firing on every session since — but **they were never tested with mock stdin**. This slice writes deterministic tests, fixes any bugs surfaced, tightens the heuristics, and verifies the JSON output format.

## What we already have

Both hook scripts use the `python3 -c` stdin pattern (fixed in slice 001-01). The scaffold is sound:

- `jig-memory-scan.sh` — scans the user prompt for capitalized references not in the hot cache or glossary, emits `{"continue": true, "additionalContext": "..."}` listing unrecognized terms.
- `jig-task-capture.sh` — scans the completed session for task-capture language patterns ("we should also", "TODO:", etc.), emits triage prompt.

Both exit 0 unconditionally (non-blocking, per AC #3).

## What needs to happen

1. **Deterministic tests** — pipe mock hook payloads in via stdin and assert on stdout JSON / stderr / exit code.
2. **Heuristic improvements for `jig-memory-scan`** — currently scans the entire prompt as a flat string. False-positive surfaces:
   - File paths (`/Users/ramboz/Projects` contains `Users`, `Projects`)
   - URLs (`https://Foo.com`)
   - Code blocks (` ```python\nclass MyClass\n``` `)
   - **Mitigation**: strip code blocks, fenced and inline, before scanning. Strip URL hosts. Skip absolute paths.
3. **`additionalContext` JSON format verification** — per the original plan review, the format for `UserPromptSubmit` and `Stop` hooks was deferred for empirical verification. The two formats we know are:
   - `PreToolUse` style: `{"hookSpecificOutput": {"hookEventName": "X", "additionalContext": "..."}}`
   - Other events: `{"continue": true, "additionalContext": "..."}`
   Our hooks use the latter. We document this clearly and add a test that the JSON is at minimum *valid* and contains the expected keys. Empirical verification (does Claude Code actually inject the context?) remains a runtime concern; we cannot fully test it in CI but we can guarantee the output JSON is well-formed.
4. **Firing-rate dogfooding (AC #5)** — we don't have telemetry data yet (the hooks have been firing but the project has no `.claude/skill-usage.jsonl` for hooks themselves, only for Task spawns). The healthier interpretation: tune the heuristic in this slice based on what we KNOW about the kind of prompts that hit it during development, and document the firing-rate target as a refinement-todo item for actual measurement.

## Files to modify

| Path | Change |
|---|---|
| `hooks/scripts/jig-memory-scan.sh` | Tighten heuristic: strip code blocks, URLs, absolute paths |
| `hooks/scripts/jig-task-capture.sh` | Minor: ensure regex matches typed-curly-quote variants |
| `skills/memory-sync/test_hooks.py` | NEW test file for both hook scripts |
| `docs/refinement-todo.md` | Add post-2-week firing-rate measurement item |
| `docs/specs/002-memory-layer/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## Test strategy

`MemoryScanHookTests` (against `hooks/scripts/jig-memory-scan.sh`):
- `test_silent_on_no_capitalized`
- `test_silent_on_known_terms_in_hot_cache`
- `test_silent_on_known_terms_in_glossary`
- `test_flags_unknown_acronym`
- `test_flags_unknown_camelcase`
- `test_skips_common_acronyms` — `API`, `JSON`, `LLM`, etc.
- `test_strips_code_blocks_before_scanning` — `` `MyClass` `` and ` ```...``` ` don't trigger
- `test_strips_urls` — `https://Anthropic.com` doesn't trigger on `Anthropic`
- `test_skips_absolute_paths` — `/Users/foo` doesn't trigger on `Users`
- `test_output_is_well_formed_json`
- `test_exits_0_always`

`TaskCaptureHookTests`:
- `test_silent_on_no_capture_patterns`
- `test_flags_we_should_also`
- `test_flags_todo_marker`
- `test_flags_remind_me_to`
- `test_flags_dont_forget`
- `test_output_is_well_formed_json`
- `test_exits_0_always`

## Out of scope

- Runtime verification that Claude Code injects `additionalContext` correctly → empirical, not testable in CI. Refinement-todo if needed.
- Persistent firing-rate counters → requires a tracking file the hooks write to; out of scope here.
- Auto-tuning the heuristic based on telemetry → manual tuning only.
