# Plan: Slice 001-05 — wizard-qa

## Approach

Q&A interaction layer. The deterministic core stays in `scaffold.py`; the **question flow lives in SKILL.md** (Claude asks the user). User answers flow back to `scaffold.py` as CLI flags. Skipped questions = no flag = falls back to filesystem inference (the slice 001-03 behavior).

This split keeps the scaffold core testable and deterministic, while letting Claude handle the natural-language interaction.

## CLI interface

5 questions per AC, mapped to argparse flags:

| Question | Flag(s) | Semantics |
|---|---|---|
| Runtime/language? | `--runtime <name>` | Stored in `scaffold.json.project_runtime`; otherwise key absent. |
| Team setting? | `--team` / `--solo` | Forces `is_team` true/false, overriding `detect_team`. |
| Existing CI? | `--has-ci` / `--no-ci` | Forces `has_ci`, overriding `_detect_ci`. |
| Existing tests? | `--has-tests` / `--no-tests` | Forces `has_tests`, overriding `_detect_tests`. Affects tier-1 install. |
| LLM/agent work planned? | `--plans-ai` / `--no-ai` | Forces `has_llm_agent_files`, overriding `_detect_llm_agent`. Affects tier-2 offer. |

Boolean overrides are **mutually exclusive pairs** (e.g. `--team` and `--solo` can't both be passed). Both unset = inference fallback. Argparse `add_mutually_exclusive_group()` enforces this.

## Files to modify

| Path | Change |
|---|---|
| `skills/scaffold-init/scaffold.py` | Switch main() to argparse; pass overrides through to `scaffold()`; record `project_runtime` in manifest |
| `skills/scaffold-init/SKILL.md` | New Q&A section listing the 5 questions and the invocation pattern; mark questions as skippable |
| `skills/scaffold-init/test_scaffold.py` | New `WizardQATests` covering each flag override + skip-equivalence |
| `docs/specs/001-scaffold-init/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## SKILL.md Q&A flow

Claude's question-asking, in order. Each is independently skippable:

1. "What runtime/language is this project — Python, TypeScript, Go, Rust, mixed, or unsure?" → `--runtime`
2. "Solo project or team setting?" → `--team` / `--solo`
3. "Does the project already have CI configured?" → `--has-ci` / `--no-ci`
4. "Does the project already have a test suite?" → `--has-tests` / `--no-tests`
5. "Will this project involve LLM or agent work?" → `--plans-ai` / `--no-ai`

If the user answers "skip" / "I don't know" / "unsure" to any question, do not pass the flag — let filesystem inference handle it.

## Override semantics — clarification

The override is *one-way*: user says yes/no, signal is forced. There's no "ask only if filesystem is ambiguous" mode — the wizard always asks if invoked in Q&A mode. Skip is the only way to defer to filesystem.

If a user invokes scaffold-init non-interactively (no Q&A), the wizard runs in pure inference mode (slice 001-03 behavior, unchanged). The default behavior is therefore backwards-compatible.

## Test strategy

`WizardQATests`:
- `test_runtime_recorded`: `--runtime=python` writes `project_runtime: "python"` to scaffold.json
- `test_team_flag_forces_people_md`: bare repo + `--team` creates people.md anyway
- `test_solo_flag_suppresses_people_md`: team repo + `--solo` skips people.md
- `test_has_tests_forces_tier_1`: bare dir + `--has-tests` installs tier-1
- `test_no_tests_overrides_filesystem`: pytest.ini present + `--no-tests` does NOT install tier-1
- `test_no_flags_matches_inference_baseline`: no flags = identical scaffold.json scaffold_signals to slice 001-03 behavior
- `test_mutually_exclusive_flags_rejected`: `--team --solo` returns non-zero
- `test_plans_ai_forces_tier_2_offer`: bare dir + `--plans-ai` offers tier-2

## Out of scope

- Multi-language detection beyond a single runtime string → future (e.g. polyglot repos).
- Interactive prompts in scaffold.py itself (e.g. argparse-based `input()`) → SKILL.md owns interaction.
- Persisting answers for re-scaffolds → answers already recorded in scaffold.json, but re-scaffold UX (read back, re-ask) is deferred.
