# Tasks: Slice 001-01 — greenfield-scaffold

## Ordered tasks (TDD discipline: tests first where reasonable)

- [ ] **T1** — Write `skills/scaffold-init/test_scaffold.py` with failing tests for each AC
- [ ] **T2** — Create `templates/docs/*.md.template` files (architecture, workflow, conventions, refinement-todo, inbox, specs/README, adrs/README)
- [ ] **T3** — Create `templates/docs/memory/*.md.template` files (glossary, learnings, tooling)
- [ ] **T4** — Create `templates/scaffold.json.template` defining manifest schema
- [ ] **T5** — Write `skills/scaffold-init/scaffold.py` to make tests pass
- [ ] **T6** — Write `hooks/scripts/jig-spec-gate.sh`
- [ ] **T7** — Wire spec-gate hook into `hooks/hooks.json` (PreToolUse on Edit|Write)
- [ ] **T8** — Update `skills/scaffold-init/SKILL.md` body with wizard instructions and script invocation
- [ ] **T9** — Run `test_scaffold.py` end-to-end, verify all ACs pass
- [ ] **T10** — Update spec status DRAFT → IN_PROGRESS → REVIEWED (after reviewer pass)
- [ ] **T11** — Spawn reviewer subagent against spec + deliverables
- [ ] **T12** — Reconcile: deviation log + reconciliation review + commit

## Deliverable paths (for `.claude/review-queue.json`)

```
skills/scaffold-init/scaffold.py
skills/scaffold-init/test_scaffold.py
skills/scaffold-init/SKILL.md
templates/docs/architecture.md.template
templates/docs/workflow.md.template
templates/docs/conventions.md.template
templates/docs/refinement-todo.md.template
templates/docs/inbox.md.template
templates/docs/memory/glossary.md.template
templates/docs/memory/learnings.md.template
templates/docs/memory/tooling.md.template
templates/docs/specs/README.md.template
templates/docs/adrs/README.md.template
templates/scaffold.json.template
hooks/scripts/jig-spec-gate.sh
hooks/hooks.json
```

## AC → test mapping

| AC | Test method |
|---|---|
| #1 Full tree produced | `test_creates_full_tree` — assert each path exists |
| #2 scaffold.json schema | `test_scaffold_json_schema` — parse, assert keys |
| #3 Draft markers | `test_draft_markers` — grep each .md for the marker |
| #4 Memory stubs seeded | `test_memory_stubs` — assert non-empty + has expected sections |
| #5 inbox.md header | `test_inbox_header` — assert purpose explanation present |
| #6 CLAUDE.md from template + Hot Cache | `test_claude_md_hot_cache` — assert Hot Cache section + project name |
| #7 No people.md (solo) | `test_no_people_md` — assert file absent |
| #8 Spec-gate active post-completion | `test_conventions_gate_blocks` — direct hook invocation test |
