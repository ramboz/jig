# Tasks: Slice 001-02 — doc-content

## Ordered tasks (TDD discipline)

- [ ] **T1** — Extend `test_scaffold.py` with failing tests for new ACs (DocContentTests + TeamDetectionTests)
- [ ] **T2** — Add Hook Strictness Profiles section to `workflow.md.template`
- [ ] **T3** — Restructure `conventions.md.template` with starter rules in Rule/Why/How format
- [ ] **T4** — Substitute `{{PROJECT_NAME}}` in `CLAUDE.md.template` codenames section
- [ ] **T5** — Add `detect_team()` to `scaffold.py`
- [ ] **T6** — Create `templates/docs/memory/people.md.template`
- [ ] **T7** — Wire `detect_team()` into scaffold path so people.md is conditional
- [ ] **T8** — Run tests, fix issues
- [ ] **T9** — Spawn reviewer subagent
- [ ] **T10** — Reconcile, second reviewer pass, commit

## Deliverable paths (for `.claude/review-queue.json`)

```
templates/docs/workflow.md.template
templates/docs/conventions.md.template
templates/CLAUDE.md.template
templates/docs/memory/people.md.template
skills/scaffold-init/scaffold.py
skills/scaffold-init/test_scaffold.py
```

## AC → test mapping

| AC | Test method | Notes |
|---|---|---|
| #2 workflow has lifecycle + strictness | `test_workflow_has_strictness_section` | grep for section + Deferred marker |
| #3 conventions Rule/Why/How throughout | `test_conventions_uses_format` | count `**Why:**` and `**How to apply:**` markers |
| #7 Hot Cache populated with project name | `test_claude_md_codename_includes_project_name` | assert `{{PROJECT_NAME}}` value appears in codenames bullet |
| #8 people.md only on team | `test_people_md_absent_on_solo` (covered by 001-01 test) + `test_people_md_present_on_team` (new) | new test uses `git init` + 2 author commits |
