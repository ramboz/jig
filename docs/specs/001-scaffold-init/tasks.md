# Tasks: Slice 001-05 — wizard-qa

## Ordered tasks (TDD)

- [ ] **T1** — Extend `test_scaffold.py` with failing `WizardQATests`
- [ ] **T2** — Replace scaffold.py's hand-rolled arg parsing with argparse; add 5 flag groups
- [ ] **T3** — Plumb overrides through to `scaffold()` → `detect_signals()`
- [ ] **T4** — Add `project_runtime` to scaffold.json (only when --runtime is passed)
- [ ] **T5** — Update SKILL.md with Q&A flow section
- [ ] **T6** — Run tests, fix issues
- [ ] **T7** — Spawn reviewer subagent
- [ ] **T8** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| 3–5 questions covering runtime/team/CI/tests/AI | All 5 flag groups exercised |
| User answers override filesystem | `test_no_tests_overrides_filesystem`, `test_solo_flag_suppresses_people_md` |
| Questions skippable | `test_no_flags_matches_inference_baseline` |
| All-skipped = inference mode | `test_no_flags_matches_inference_baseline` |

## Deliverable paths

```
skills/scaffold-init/scaffold.py
skills/scaffold-init/test_scaffold.py
skills/scaffold-init/SKILL.md
docs/specs/001-scaffold-init/{spec,plan,tasks}.md
docs/specs/README.md
```
