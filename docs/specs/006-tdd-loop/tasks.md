# Tasks: Slice 006-01 — tdd-helper

## Ordered tasks (TDD)

- [ ] **T1** — Read `skills/scaffold-init/scaffold.py:_detect_tests` + the current `scaffold.json` schema so AC #5's path is decided before code lands.
- [ ] **T2** — Write `skills/tdd-loop/test_tdd.py` with failing tests for `DetectTests` + `RunTests` + `SkillSurfaceTests`.
- [ ] **T3** — Implement `skills/tdd-loop/tdd.py` (detect + run subcommands).
- [ ] **T4** — Write `skills/tdd-loop/SKILL.md` (active frontmatter; references `tdd.py` + `agents/implementer.md`).
- [ ] **T5** — If `scaffold.json` schema supports a Tier-1 install list, wire the entry in `scaffold.py`. Otherwise log the deferred decision in the deviation log.
- [ ] **T6** — Run full suite (`python3 -m pytest skills/`). Confirm 191 + new tests green; no regressions.
- [ ] **T7** — Dogfood: `tdd.py detect .` (expect `pytest`); `tdd.py run skills/` (expect exit 0).
- [ ] **T8** — Transition spec status DRAFT → IN_PROGRESS → REVIEWED via `workflow.py transition`.
- [ ] **T9** — Build implementation-review prompt via `review.py`; spawn reviewer.
- [ ] **T10** — Write deviation log under slice 006-01.
- [ ] **T11** — Build reconciliation-review prompt; spawn reviewer.
- [ ] **T12** — Transition REVIEWED → RECONCILED → DONE.
- [ ] **T13** — Regen `docs/specs/README.md` via `workflow.py status-board`.
- [ ] **T14** — Update `CLAUDE.md` hot cache + Skills table.
- [ ] **T15** — Commit: `feat(tdd-loop): introduce skill (slice 006-01)`.

## AC → test mapping

| AC | Test class |
|---|---|
| #1 `detect` subcommand + priority rules | `DetectTests` |
| #2 `run` subcommand + exit-code normalization | `RunTests` |
| #3 SKILL.md frontmatter + body | `SkillSurfaceTests` |
| #4 Test coverage exists | enforced by the test file itself (existence of test classes) |
| #5 scaffold-init wiring (or documented deferral) | Verified by reading `scaffold.py`; no new test if schema doesn't support tier_1_skills |
| #6 Helper duplication acknowledged | Recorded in deviation log, not in tests |

## Deliverable paths

```
skills/tdd-loop/SKILL.md
skills/tdd-loop/tdd.py
skills/tdd-loop/test_tdd.py
docs/specs/006-tdd-loop/{spec,plan,tasks}.md
docs/specs/README.md
CLAUDE.md
(maybe) skills/scaffold-init/scaffold.py
```

## Verification commands

```bash
# Detection on jig itself
python3 skills/tdd-loop/tdd.py detect .
# expect: pytest

# Run jig's own suite via the helper
python3 skills/tdd-loop/tdd.py run skills/
# expect: exit 0; 191 + new tests green

# Empty dir → exit 2
mkdir -p /tmp/empty && python3 skills/tdd-loop/tdd.py detect /tmp/empty
# expect: exit 2; stderr "no test runner detected at /tmp/empty"

# Full suite
python3 -m pytest skills/
```
