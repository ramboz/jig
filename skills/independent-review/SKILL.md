---
name: independent-review
description: >
  Build the standardized prompt for a fresh reviewer subagent that evaluates
  implemented work against its spec without access to the implementation
  conversation. Use after an implementer subagent completes a spec slice (when
  the slice is ready for REVIEWED), or after a deviation log is written (for
  reconciliation review). Do not use for ad-hoc code review unrelated to a
  spec, or for reviewing a spec's authorship (that's the READY_FOR_REVIEW step
  in spec-workflow).
user-invocable: true
---

> Spec 004 promoted this skill from stub to active. The prompt is constructed
> by `review.py`; Claude owns the Task invocation.

## What this skill does

Constructs the standardized reviewer-subagent prompt and tells Claude when /
how to spawn the Task. The skill has two modes, matching the two review passes
every slice runs:

- **Implementation review** — after the implementer writes the deliverable to
  disk. The reviewer evaluates each acceptance criterion against the actual
  files; returns `pass | fail | needs-changes`.
- **Reconciliation review** — after the deviation log is written. The
  reviewer verifies the doc changes match reality; does NOT re-review the ACs.

`review.py` builds the prompt text; `agents/reviewer.md` defines the agent's
tool restrictions and persistent system rules.

## How to use

### Implementation review

After the implementer has written the deliverable to disk:

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  implementation \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path-1>" "<deliverable-path-2>" ...)
SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type implementation)
```

Then feed `$PROMPT` to the `Task` tool with `subagent_type: "$SUBAGENT"`.
The helper resolves `$SUBAGENT` deterministically — `reviewer` when jig is
installed as a plugin (the real filesystem-based agent is reachable),
`general-purpose` when running from source. Wait for the verdict. Address
any `fail`/`needs-changes` findings; rerun the helper + Task as needed
until `pass`.

### Reconciliation review

After the deviation log subsection has been added under the slice in
`spec.md`:

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  reconciliation \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>")
SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type reconciliation)
```

Feed `$PROMPT` to `Task` with `subagent_type: "$SUBAGENT"`. The prompt
explicitly tells the reviewer NOT to re-evaluate against ACs — it only
verifies the deviation log matches reality.

### What gets put in the prompt automatically

- Standard preamble ("You are seeing this work for the first time")
- The slice's full label (helper looks it up from the spec)
- "What you must NOT do" block (no prior reasoning, no soften, no file writes,
  no `docs/memory/` writes)
- Canonical output format (`VERDICT | REASONING | SPECIFIC ISSUES | RECONCILIATION NOTES`)

## Context isolation pattern

Implementer writes deliverable to disk → `review.py` builds a self-contained
prompt → Claude spawns the reviewer Task with that prompt → reviewer reads
only what the prompt points at. This is imperfect (parent context is
technically accessible to subagents — see GitHub issue #20304), but works
reliably when the prompt is sharp.

## Gotchas

- **`review.py` does not spawn the Task.** It only constructs the prompt
  string. Claude is responsible for invoking the `Task` tool with the prompt
  as the `prompt` parameter. This separation keeps `review.py` deterministic
  and testable.
- **Reviewer agent is read-only by definition.** `agents/reviewer.md` lists
  only `Read`, `Glob`, `Grep` in its tool set. No `Write` or `Edit`.
- **Reviewer must not write to `docs/memory/`.** Defining the glossary,
  capturing learnings, or modifying the hot cache is `memory-sync`'s job,
  not the reviewer's.
- **Reconciliation review never re-evaluates ACs.** That's done. The
  reconciliation prompt explicitly states this so the reviewer doesn't
  drift into AC-re-review.
- **Substring matching for slice fragments** is identical to `workflow.py` —
  `001-01` matches `## Slice 001-01 — greenfield-scaffold`. Ambiguous
  fragments are refused with exit 2.
