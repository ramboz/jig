# Plan: Slice 003-01 — lifecycle-helper

## Approach

Two-part deliverable, both wrapped by a single SKILL.md promotion:

1. **`workflow.py` helper** — same pattern as `scaffold.py` and `memory.py`: deterministic CLI, argparse, exit-code semantics, idempotent where it can be.
2. **SKILL.md rewrite** — flip from stub-describing-future to active-driving-now. Keep the integration content from slice 002-04 (reconciliation checklist, memory-sync gate) intact; add concrete invocation instructions.

## `workflow.py` CLI surface

```bash
python3 workflow.py transition <spec.md> <slice-name> <new-status>
python3 workflow.py status-board <project-dir>
```

### `transition`

- Parses the target `spec.md`. Locates the `## Slice <slice-name>` H2 (case-insensitive substring match on slice-name to be lenient — `001-01` matches `## Slice 001-01 — greenfield-scaffold`).
- Finds the `**STATUS: <old>**` line within that slice's section.
- Replaces with `**STATUS: <new>**`.
- Refuses with exit 2 if:
  - slice not found
  - `new-status` not in the valid set (DRAFT, READY_FOR_REVIEW, READY_FOR_IMPLEMENTATION, IN_PROGRESS, REVIEWED, RECONCILED, DONE)
  - multiple matching slice headers
- Otherwise exit 0 and print `transitioned <slice-name>: <old> → <new>`.

### `status-board`

- Globs `docs/specs/*/spec.md` under the target.
- For each, extracts spec dir name, then walks slice sections, collecting (slice-name, status).
- Builds a fresh `docs/specs/README.md` table from the collected data.
- **Preserves the README header (preamble before the table)** and replaces only the table itself.
- Idempotent: if the regenerated table equals what's already on disk, no write occurs (no churn).

## SKILL.md rewrite

Frontmatter changes:
- Remove `disable-model-invocation: true` so it auto-triggers
- Keep `user-invocable: true`
- Refine the `description` to be triggering-friendly (verb-led, when/when-not clauses)

Body restructure:
1. **"What this skill does"** — present tense, not "when implemented"
2. **"How to use" section** — concrete commands and decision points
3. **"Lifecycle states"** — keep
4. **"Reconciliation checklist"** — keep (slice 002-04's contribution, important for memory-sync integration)
5. **"Gotchas"** — keep

## Files to create

| Path | Purpose |
|---|---|
| `skills/spec-workflow/workflow.py` | The helper |
| `skills/spec-workflow/test_workflow.py` | Unit tests |

## Files to modify

| Path | Change |
|---|---|
| `skills/spec-workflow/SKILL.md` | Frontmatter + body promoted from stub to active |
| `docs/specs/003-spec-workflow-promotion/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Add spec 003 rows |

## Test strategy

`TransitionTests`:
- Round-trip on a synthetic spec.md: write a slice with `**STATUS: DRAFT**`, run `transition X 001-01 IN_PROGRESS`, read back, verify
- Invalid status name → exit 2
- Slice not found → exit 2
- Ambiguous slice (two slices with same name) → exit 2

`StatusBoardTests`:
- Scaffolds a project, runs `status-board`, verifies the regenerated table contains rows for the scaffolded specs (none yet — should produce an empty body)
- Creates synthetic spec.md files with mixed statuses, runs `status-board`, verifies the table matches expected
- Idempotent on re-run (no churn)

`SkillPromotionTests`:
- `skills/spec-workflow/SKILL.md` no longer contains `disable-model-invocation: true`
- Frontmatter parses cleanly (YAML)
- The integration with `memory-sync` (slice 002-04) is still intact — `IntegrationTests` in `test_memory.py` must continue to pass (no regression)

## Out of scope

- Slice 003-02 (anti-horizontal-phasing check) and 003-03 (new-spec scaffolding) — deferred per the spec.
- Automating reviewer-subagent spawn → that's an LLM-driven decision, stays in SKILL.md.
- Hook-based gate enforcement of state transitions → out of scope; could be a future slice.
