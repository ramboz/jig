# Plan: Slice 004-01 — review-helper

## Approach

Same shape as workflow.py / memory.py / scaffold.py: deterministic helper for
the bits that don't need judgment (prompt construction), SKILL.md for when/why
to invoke and what to do with the result.

The helper builds two prompt variants from a shared template (most content is
identical; only the "job" framing and evaluation guidance differ).

## `review.py` CLI surface

```bash
python3 review.py implementation <spec.md> <slice-fragment> <deliverable-path>...
python3 review.py reconciliation <spec.md> <slice-fragment>
```

Both subcommands:
- Validate spec.md exists; refuse with exit 2 if not
- Locate the slice section (same lenient substring matching as workflow.py)
- Refuse with exit 2 on slice miss or ambiguous fragment
- Print the constructed prompt to stdout
- Exit 0 on success

`implementation` mode additionally:
- Takes 1+ deliverable paths
- Lists them in a numbered "What to read" section

`reconciliation` mode:
- Takes no deliverable paths (the reviewer reads the spec to find the deviation log)
- Frames the job as verifying deviation-log accuracy, NOT re-reviewing ACs

## Prompt template anatomy

Both variants share:
- "You are an independent reviewer. You are seeing this work for the first time."
- A "What you must NOT do" block (refer to prior, soften, write files, write docs/memory/)
- Output format: `VERDICT | REASONING | SPECIFIC ISSUES | RECONCILIATION NOTES`

Variants differ in:
- The "Your job" paragraph (implementation: evaluate against ACs; reconciliation: verify deviation log)
- The "What to read" section (impl lists deliverables; recon points at the deviation log)
- The "Evaluate" guidance

## Files to create

| Path | Purpose |
|---|---|
| `skills/independent-review/review.py` | Prompt-construction helper |
| `skills/independent-review/test_review.py` | Unit tests |

## Files to modify

| Path | Change |
|---|---|
| `skills/independent-review/SKILL.md` | Frontmatter + body promoted from stub to active |
| `docs/specs/004-independent-review-promotion/spec.md` | Status: DRAFT → IN_PROGRESS → DONE |
| `docs/specs/README.md` | Add spec 004 row(s) |

## Coupling concern (and the decision)

`review.py` needs slice-locating logic identical to `workflow.py`'s
`find_slice_section`. Three options:

- **A:** Import from `workflow.py` — couples two skills to each other.
- **B:** Duplicate the ~15-line function — short and stable, easy to keep in sync.
- **C:** Extract to a shared `skills/_common/parsing.py` — adds infrastructure
  before there's clear need.

**Decision: B** (duplicate). The function is small, the regex is stable, and
the test in each skill guards its own usage. If a third skill ever needs it,
revisit with option C. Document this in the deviation log.

## Test strategy

`ImplementationPromptTests`:
- Standard preamble present
- Spec path appears
- Slice fragment appears
- All deliverable paths appear, in order
- "What you must NOT do" block contains: prior reasoning, soften, write files, docs/memory/
- Output format block contains VERDICT/REASONING/SPECIFIC ISSUES/RECONCILIATION NOTES

`ReconciliationPromptTests`:
- Same preamble
- Frames as "RECONCILIATION REVIEW"
- Explicitly states "NOT re-reviewing against original ACs"
- Points at the "Deviation log" subsection
- Same output format

`HelperErrorTests`:
- Refuses missing spec.md (exit 2)
- Refuses unknown slice fragment (exit 2)
- Refuses ambiguous slice fragment (exit 2)
- `implementation` mode requires at least one deliverable path

`SkillPromotionTests`:
- Frontmatter no longer has `disable-model-invocation: true`
- Body has no "Status: DRAFT — not yet implemented" banner
- SKILL.md references `review.py`

## Out of scope

- Hook-based gate that blocks commits without a passing review → could be a future slice.
- Auto-spawning the reviewer Task (vs. just printing the prompt) → Claude's job; keeps the helper deterministic.
- Storing review verdicts in `scaffold.json` or a similar audit file → out of scope.
