# Tasks: Slice 001-03 — signal-detection

## Ordered tasks (TDD)

- [ ] **T1** — Extend `test_scaffold.py` with failing tests for signal detection + brief.md + tier selection
- [ ] **T2** — Implement `_detect_llm_agent()`, `_detect_ci()`, `_detect_tests()` helpers in scaffold.py
- [ ] **T3** — Add `Signals` dataclass and `detect_signals()` function
- [ ] **T4** — Create `templates/brief.md.template`
- [ ] **T5** — Wire signal-driven tier selection into scaffold flow (replace hardcoded DEFAULT_TIERS)
- [ ] **T6** — Generate brief.md from template populated with detected signals
- [ ] **T7** — Run tests, fix issues
- [ ] **T8** — Spawn reviewer subagent
- [ ] **T9** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 LLM/agent files → Tier 2 offered | `test_llm_agent_signals_record_offer` |
| #2 CI present → strict default | `test_ci_signals_set_strict_profile` |
| #3 Existing tests → tdd-loop auto-installed | `test_test_signals_install_tier_1` |
| #4 brief.md produced | `test_brief_md_exists_and_summarizes` |
| #5 No false positives on bare repo | `test_bare_repo_no_false_positives` |

## Deliverable paths (for `.claude/review-queue.json`)

```
skills/scaffold-init/scaffold.py
skills/scaffold-init/test_scaffold.py
templates/brief.md.template
docs/specs/001-scaffold-init/spec.md
docs/specs/001-scaffold-init/plan.md
docs/specs/001-scaffold-init/tasks.md
docs/specs/README.md
```
