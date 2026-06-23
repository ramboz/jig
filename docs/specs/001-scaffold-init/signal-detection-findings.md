---
status: DONE
resolves: slice 001-03 (signal-detection)
historical_id: Spike 001a
---

# Signal Detection Findings

This is the historical Spike 001a record relocated under spec 001. New spike
work lives as `kind: spike` slices inside a spec, not as standalone
`docs/spikes/` artifacts.

**Question:** What file-pattern heuristics reliably indicate LLM/agent work,
CI presence, and test framework presence, with a low false-positive rate?

**Output:** A reference document consumed by slice 001-03. The investigation
was DONE when this document had a filled-in Findings section and a
false-positive handling decision.

## Findings

### LLM/agent signals (offer Tier 2)

Detection is "any one of these returns True":

| Signal | Confidence | Notes |
|---|---|---|
| `AGENTS.md` at project root | High | Increasingly adopted convention; rarely a coincidence. |
| Any `*.prompt.md` or `*.system-prompt.md` file | High | The `.prompt.md` suffix is purpose-specific. |
| `.cursor/` directory | High | Cursor IDE config; strong intent signal. |
| `.github/copilot-instructions.md` | High | Copilot-specific config file. |
| `openai`, `anthropic`, `langchain`, `llamaindex` in `package.json` deps | High | Library dependency means active integration. |
| `openai`, `anthropic`, `langchain` in `requirements.txt` / `pyproject.toml` | High | Same for Python. |

**Deliberately excluded:**

- `.claude/` directory: too ambiguous. Many users have `.claude/` for Claude
  Code config without doing AI work in the project itself. The detector asks
  whether the project is an AI project, not whether the user runs Claude.
- Vague keyword matches in source files (`import openai`-style grep):
  over-broad, and the package-manifest checks above already cover real
  installs.

### CI signals (default `hook_profile = strict`)

| Signal | Confidence | Notes |
|---|---|---|
| `.github/workflows/` directory exists | High | Definitive GitHub Actions setup. |
| `Jenkinsfile` at root | High | Definitive. |
| `.circleci/` directory | High | Definitive. |
| `.travis.yml` | High | Definitive, though Travis is legacy. |
| `.gitlab-ci.yml` | High | Definitive. |
| `Makefile` with a `test:` or `ci:` target | Low | Many Makefiles have a `test` target without CI involvement. Not used. |

**Decision:** Require at least one high-confidence CI signal. Makefile targets
are not used because they are too noisy.

### Test framework signals (install Tier 1 `tdd-loop`)

| Signal | Confidence | Notes |
|---|---|---|
| `vitest.config.*` OR `vitest` in `package.json` (deps or devDeps) | High | |
| `jest.config.*` OR `jest` in `package.json` | High | |
| `pytest.ini` OR `[tool.pytest]` in `pyproject.toml` OR `conftest.py` | High | |
| Any `*_test.go` file | High | Go's convention is unambiguous. |
| `spec/` directory at root | Medium | Could be RSpec, could be API specs such as OpenAPI. Disambiguate by presence of `Gemfile` with `rspec` gem, OR `.rspec` config. |

**Decision:** Rely on high-confidence signals only for `tdd-loop` install.
The `spec/`-without-Gemfile case is a false-positive risk we will not chase.

### Team signals (generate `docs/memory/people.md`)

Already implemented in slice 001-02. `detect_team()` returns True iff:

- target is a git repo root, not a parent or subdir
- `git log --use-mailmap --format=%aE` shows at least two unique authors

No changes needed; slice 001-03 reuses the existing function.

## Decision: False-positive handling

**Default stance: permissive offer, conservative install.**

- **LLM/agent signals -> Tier 2 OFFERED, not auto-installed.** Recorded as
  `scaffold_signals.has_llm_agent_files = true` and surfaced in `brief.md`.
  The user opts in via a follow-up step (slice 001-05 wizard, or by manually
  editing `scaffold.json` for now).
- **CI signals -> `hook_profile = strict` set in `scaffold.json`.** This is
  data, not behavior; it influences future hook dispatch. Setting strict on a
  false positive is harmless until dispatch ships.
- **Test signals -> Tier 1 `tdd-loop` AUTO-INSTALLED.** Tier 1 is the default
  for most projects anyway, so a false positive here is essentially free.
- **Team signal -> `people.md` GENERATED.** Already implemented;
  mailmap-aware to minimize false positives.

**Single-signal sufficiency.** Each category fires on any one matching signal.
Multiple confirmations are not required. The signals chosen are individually
high-confidence; demanding intersection would mostly punish legitimate
projects with one obvious indicator.

**Stop conditions for the detector.** Walk the project root and immediate
subdirs only; no recursive globs deeper than two levels. Skip large dirs
(`node_modules`, `.git`, `dist`, `build`, `target`, `__pycache__`, `.venv`,
`venv`). Time-box the scan to 3 seconds; on timeout, return whatever was
detected so far.

## Output consumed by

Slice 001-03, signal-detection. The detector returns a structured result the
wizard uses to populate `scaffold.json.scaffold_signals`, decide which tiers to
install, and write `brief.md`.

```python
@dataclass
class Signals:
    has_llm_agent_files: bool
    has_ci: bool
    has_tests: bool
    is_team: bool  # from existing detect_team()
```
