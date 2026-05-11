# Plan: Slice 001-03 — signal-detection

## Approach

Wire the spike's signal-detection findings into `scaffold.py`. Detection produces a `Signals` record; the scaffold pipeline uses it to populate `scaffold.json`, select tiers, and write a human-readable `brief.md`.

**Design constraint** from the spike: detection is permissive in offering, conservative in installing.

| Signal category | Effect |
|---|---|
| LLM/agent files present | Tier 2 **offered** (not installed). `brief.md` mentions it. |
| CI files present | `scaffold.json.hook_profile = "strict"` (data only — dispatch deferred). |
| Test framework present | Tier 1 `tdd-loop` **installed** (added to `installed_tiers`). |
| ≥2 git authors (existing) | `people.md` generated (already implemented in 001-02). |

Tier 1 (`tdd-loop`) is added to `installed_tiers` only when test signals are present. Default install (no signals) drops back to `["tier-0"]` only. **This changes the slice 001-01 contract**: previously `installed_tiers` was hard-coded `["tier-0", "tier-1"]`; now Tier 1 is gated on signals. Deviation logged.

## Files to create/modify

| Path | Change |
|---|---|
| `skills/scaffold-init/scaffold.py` | Add `detect_signals()` returning `Signals` dataclass; use it for tier selection and brief.md generation |
| `templates/brief.md.template` | Brief-summary template at project root |
| `skills/scaffold-init/test_scaffold.py` | New tests for signal detection per category + brief.md content + tier selection |
| `docs/specs/001-scaffold-init/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Status update |

## detect_signals() shape

```python
@dataclass
class Signals:
    has_llm_agent_files: bool
    has_ci: bool
    has_tests: bool
    is_team: bool

def detect_signals(target: Path) -> Signals:
    return Signals(
        has_llm_agent_files=_detect_llm_agent(target),
        has_ci=_detect_ci(target),
        has_tests=_detect_tests(target),
        is_team=detect_team(target),
    )
```

Each `_detect_*` is a small pure function returning bool. They walk the project root and immediate subdirs only (per spike: no recursive deeper than 2 levels). Skip `node_modules`, `.git`, `dist`, `build`, `target`, `__pycache__`, `.venv`, `venv`.

## brief.md content

Single-page summary at the scaffolded project root. Includes:
- What scaffold-init detected (signals)
- What tiers got installed
- What was OFFERED but not installed (Tier 2)
- What was deferred (link to refinement-todo.md)
- Immediate next steps

## Test strategy

For each signal category, two tests:
- positive — create the signal file, run scaffold, assert detection
- negative — bare directory, assert no detection

Plus integration tests:
- `brief.md` exists at target root after scaffold
- `installed_tiers` includes `tier-1` when test signals present, only `tier-0` when not
- `scaffold_signals` fields in `scaffold.json` match `Signals` values
- AC #5: bare `git init` repo produces no false positives

## Out of scope

- Q&A wizard interaction (slice 001-05)
- Actually installing/enforcing Tier 2 — it's just offered
- Hook strictness dispatch logic — `hook_profile` is recorded but inert (deferred per refinement-todo)
