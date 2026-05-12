# Tasks: Slice 007-01 — land-prepare

## Ordered tasks (TDD)

- [ ] **T1** — Write `skills/slice-land/test_land.py` with failing tests for all six AC test classes (`PrepareReportTests`, `ModeTests`, `PrBodyTests`, `ErrorTests`, `SafetyTests`, `SkillSurfaceTests`).
- [ ] **T2** — Implement `skills/slice-land/land.py` (single `prepare` subcommand via argparse).
- [ ] **T3** — Write `skills/slice-land/SKILL.md` (active frontmatter; six trigger phrases; references `land.py prepare` + `--mode`).
- [ ] **T4** — Run full suite (`python3 -m unittest discover skills/`). Confirm no regressions across 216 existing tests + new tests.
- [ ] **T5** — Self-dogfood: `python3 skills/slice-land/land.py prepare docs/specs/007-slice-land/spec.md "007-01" --mode direct`. The first real run is on its own slice.
- [ ] **T6** — Transition status DRAFT → IN_PROGRESS → REVIEWED.
- [ ] **T7** — Build implementation-review prompt via `review.py`; spawn reviewer.
- [ ] **T8** — Write deviation log under slice 007-01.
- [ ] **T9** — Transition REVIEWED → RECONCILED.
- [ ] **T10** — Build reconciliation-review prompt; spawn reviewer.
- [ ] **T11** — Transition RECONCILED → DONE.
- [ ] **T12** — Regen status board AFTER the DONE transition (006-01 lesson).
- [ ] **T13** — Update `CLAUDE.md` (hot cache + Skills table; align all three mentions to DONE — 006-01 lesson).
- [ ] **T14** — Commit: `feat(slice-land): introduce skill (slice 007-01)`.
- [ ] **T15** — **Use the new skill to land this commit.** Run `land.py prepare ... --mode direct`, follow the produced commands manually.

## AC → test mapping

| AC | Test class |
|---|---|
| #1 `prepare` produces four-section report | `PrepareReportTests` |
| #2 `--mode direct` and `--mode pr` next-steps | `ModeTests`, `PrBodyTests` |
| #3 Exit codes 0 / 1 / 2 | `PrepareReportTests` + `ErrorTests` |
| #4 No destructive git/gh subprocess calls | `SafetyTests` |
| #5 SKILL.md surface | `SkillSurfaceTests` |
| #6 Test coverage exists | enforced by the test file itself |

## Deliverable paths

```
skills/slice-land/SKILL.md
skills/slice-land/land.py
skills/slice-land/test_land.py
docs/specs/007-slice-land/{spec,plan,tasks}.md
docs/specs/README.md
CLAUDE.md
```

## Verification commands

```bash
# Unit tests
python3 -m unittest discover skills/slice-land/

# Full suite — no regressions
python3 -m unittest discover skills/

# Self-dogfood (after DONE)
python3 skills/slice-land/land.py prepare \
  docs/specs/007-slice-land/spec.md "007-01" --mode direct
# Expect: four green readiness items + Next-steps section.

# Error cases
python3 skills/slice-land/land.py prepare /nonexistent.md "x" ; echo $?
# Expect: 2

python3 skills/slice-land/land.py prepare \
  docs/specs/007-slice-land/spec.md "007-01" --mode foo ; echo $?
# Expect: 2
```
