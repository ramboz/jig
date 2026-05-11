---
status: DRAFT
resolves: slice 001-03 (signal-detection)
---

# Spike 001a: Signal Detection Algorithm

**Question:** What file-pattern heuristics reliably indicate LLM/agent work, CI presence, and test framework presence — with a low false-positive rate?

**Output:** A reference document consumed by Slice 001-03. The spike is DONE when this document has a filled-in Findings section and a False-positive handling decision.

---

## Findings

### LLM/agent signals
- [ ] `.claude/` directory exists
- [ ] `AGENTS.md` exists at repo root
- [ ] Any `*.prompt.md` or `*.system-prompt.md` file
- [ ] `openai`, `anthropic`, `langchain`, `llamaindex` in `package.json` dependencies
- [ ] `openai`, `anthropic`, `langchain` in `requirements.txt` or `pyproject.toml`
- [ ] `.cursor/` directory exists (Cursor IDE)
- [ ] `.github/copilot-instructions.md` exists

### CI signals
- [ ] `.github/workflows/` directory exists
- [ ] `Jenkinsfile` at repo root
- [ ] `.circleci/` directory exists
- [ ] `.travis.yml` at repo root
- [ ] `Makefile` with a `test` or `ci` target

### Test framework signals
- [ ] `vitest.config.*` or `vitest` in `package.json`
- [ ] `jest.config.*` or `jest` in `package.json`
- [ ] `pytest.ini`, `pyproject.toml [tool.pytest]`, or `conftest.py`
- [ ] `go test` implied by `*_test.go` files
- [ ] `RSpec` implied by `spec/` directory (Ruby)

### Team signals (for people.md generation)
- [ ] `git log --format='%ae' | sort -u | wc -l` returns ≥ 2 unique author emails

---

## Decision: False-positive handling

> **TODO (fill in during spike execution)**
>
> Key question: what's the minimum signal confidence before we offer a tier?
> Should any single signal be enough, or do we require 2+?

---

## Output consumed by

Slice 001-03 — signal-detection
