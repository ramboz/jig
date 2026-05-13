# Tasks: Slice 005-01 — adr-helper

## Ordered tasks (TDD)

- [ ] **T1** — Add `templates/docs/decisions/adr-0000-template.md` (skeleton with `{{NUMBER}}` / `{{TITLE}}` / `{{DATE}}` placeholders).
- [ ] **T2** — Write `skills/adr-workflow/test_adr.py` with failing tests for all four subcommands + skill surface.
- [ ] **T3** — Implement `skills/adr-workflow/adr.py` (new / accept / index / resolve-todo).
- [ ] **T4** — Write `skills/adr-workflow/SKILL.md` (active, no `disable-model-invocation`).
- [ ] **T5** — Run full test suite; confirm no regressions in existing skills.
- [ ] **T6** — Sandbox dogfood: create a throwaway ADR in `/tmp/adr-sandbox/`, walk it through new → accept → index → resolve-todo.
- [ ] **T7** — Build implementation-review prompt with `review.py`; spawn reviewer subagent; address findings.
- [ ] **T8** — Transition spec status to REVIEWED via `workflow.py transition`.
- [ ] **T9** — Write deviation log under slice 005-01 in spec.md.
- [ ] **T10** — Build reconciliation-review prompt with `review.py`; spawn reviewer; address findings.
- [ ] **T11** — Transition spec status DRAFT → IN_PROGRESS → REVIEWED → RECONCILED → DONE (interleaved with the work above; `workflow.py transition` handles each step).
- [ ] **T12** — Regen `docs/specs/README.md` via `workflow.py status-board`.
- [ ] **T13** — Update `CLAUDE.md` hot cache (Active specs + Skills table).
- [ ] **T14** — Commit. Conventional Commits message: `feat(adr-workflow): promote from new to active (slice 005-01)`.

## AC → test mapping

| AC | Test class |
|---|---|
| #1 `new` subcommand shape + auto-number + slug collision | `NewTests` |
| #2 `accept` subcommand status flip + refusals | `AcceptTests` |
| #3 `index` regen + idempotency + preserves outside | `IndexTests` |
| #4 `resolve-todo` strikethrough + Resolved-by + refusals | `ResolveTodoTests` |
| #5 SKILL.md frontmatter active + body references | `SkillSurfaceTests` |
| #6 template file exists + has placeholders | `SkillSurfaceTests.test_template_exists` |
| #7 Test coverage exists | enforced by the test file itself (the existence of test classes above) |

## Deliverable paths

```
templates/docs/decisions/adr-0000-template.md
skills/adr-workflow/SKILL.md
skills/adr-workflow/adr.py
skills/adr-workflow/test_adr.py
docs/specs/005-adr-workflow/{spec,plan,tasks}.md
docs/specs/README.md
CLAUDE.md
```

## Verification commands

```bash
# Unit tests
python3 -m pytest skills/adr-workflow/

# Full suite — no regressions
python3 -m pytest skills/

# Sandbox dogfood
mkdir -p /tmp/adr-sandbox/docs/decisions
cp docs/decisions/README.md /tmp/adr-sandbox/docs/decisions/
python3 skills/adr-workflow/adr.py new test-decision \
  --title "Test Decision" \
  # ... cd into sandbox first; verify file shape, then accept + index.
```
