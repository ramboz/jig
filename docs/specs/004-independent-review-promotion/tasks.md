# Tasks: Slice 004-01 — review-helper

## Ordered tasks (TDD)

- [ ] **T1** — Create `skills/independent-review/test_review.py` with failing tests
- [ ] **T2** — Implement `skills/independent-review/review.py` (implementation + reconciliation modes)
- [ ] **T3** — Promote `skills/independent-review/SKILL.md` from stub to active
- [ ] **T4** — Run tests; dogfood by constructing a prompt for slice 004-01 itself
- [ ] **T5** — Reviewer subagent (using the freshly-promoted skill)
- [ ] **T6** — Reconcile, second reviewer pass, commit

## AC → test mapping

| AC | Test |
|---|---|
| #1 implementation prompt shape | `ImplementationPromptTests` (multiple) |
| #2 reconciliation prompt shape | `ReconciliationPromptTests` (multiple) |
| #3 helper refuses bad input | `HelperErrorTests` |
| #4 helper doesn't spawn Task itself | enforced by design — script has no `subprocess` or Task invocation |
| #5 SKILL.md frontmatter promoted | `test_skill_frontmatter_no_disable_invocation` |
| #6 SKILL.md body references helper | `test_skill_references_review_helper` |

## Deliverable paths

```
skills/independent-review/review.py
skills/independent-review/test_review.py
skills/independent-review/SKILL.md
docs/specs/004-independent-review-promotion/{spec,plan,tasks}.md
docs/specs/README.md
```
