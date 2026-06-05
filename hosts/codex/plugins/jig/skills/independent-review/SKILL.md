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
> by `review.py`; Codex owns the Task invocation.

## What this skill does

Constructs the standardized reviewer-subagent prompt and tells Codex when /
how to spawn the Task. The skill has four modes, matching the review passes
every slice may run:

- **Implementation review** — after the implementer writes the deliverable to
  disk. The reviewer evaluates each acceptance criterion against the actual
  files; returns `pass | fail | needs-changes`. This is the **compliance
  pass** in spec-workflow's multi-pass flow.
- **Pr-review (craft pass)** — slice 031-01. After the compliance pass
  returns, the orchestrator runs a craft-pass review that produces the
  four-bucket output (scope / blockers / nits / strengths) the
  `jig:pr-review` skill emits, wrapped in the same verdict envelope as the
  compliance pass. SPECIFIC ISSUES entries are tagged `[blocker]` / `[nit]`
  / `[strength]` so the workflow can decide what blocks the REVIEWED
  transition vs. what becomes a reconciliation-log entry.
- **Arch-review (architecture pass — on-demand)** — slice 031-02. After
  the craft pass returns, the orchestrator queries the slice's
  `arch_review:` frontmatter flag via `workflow.py arch-review-needed`;
  when `true`, it runs an arch pass producing the four-bucket output
  (summary / strengths / concerns / open questions) the
  `jig:arch-review` skill emits, in the same verdict envelope. Slice
  authors set `arch_review: true` in the slice's frontmatter when the
  slice changes module boundaries, public contracts, or
  architecture-shaped concerns; the slice template at
  `templates/docs/specs/slice-template.md` ships the field commented
  out as a discoverability nudge.
- **Reconciliation review** — after the deviation log is written. The
  reviewer verifies the doc changes match reality; does NOT re-review the ACs.

`review.py` builds the prompt text; `agents/reviewer.md` defines the agent's
tool restrictions and persistent system rules.

## How to use

### Implementation review

After the implementer has written the deliverable to disk:

```bash
PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  implementation \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path-1>" "<deliverable-path-2>" ...)
SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type implementation)
```

Then feed `$PROMPT` to the `Task` tool with `subagent_type: "$SUBAGENT"`.
The helper resolves `$SUBAGENT` deterministically — `reviewer` when jig is
installed as a plugin (the real filesystem-based agent is reachable),
`general-purpose` when running from source. Wait for the verdict. Address
any `fail`/`needs-changes` findings; rerun the helper + Task as needed
until `pass`.

### Pr-review (craft pass — slice 031-01)

After the compliance pass returns `pass`, run the craft pass:

```bash
PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  pr-review \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path-1>" "<deliverable-path-2>" ...)
SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type pr-review)
```

Feed `$PROMPT` to `Task` with `subagent_type: "$SUBAGENT"`. The prompt
points the reviewer at the most-specific `pr-review` SKILL.md reachable
in the environment — Codex's skill router resolves user > project >
`jig:pr-review` precedence via the skill description hints. The pass
returns the canonical four output buckets (scope / blockers / nits /
strengths) wrapped in the same verdict envelope as the compliance
pass. SPECIFIC ISSUES entries are tagged `[blocker]` / `[nit]` /
`[strength]`; only `[blocker]` entries block the REVIEWED transition.

### Arch-review (architecture pass — slice 031-02, on-demand)

The arch pass runs only when the slice's frontmatter declares
`arch_review: true`. Query the flag via `workflow.py arch-review-needed`
before spawning:

```bash
# Capture the helper exit code — a non-zero exit means the slice lookup
# failed, not "no arch pass needed." Surface the error rather than
# silently skipping the pass.
if ! NEED_ARCH=$(python3 "${PLUGIN_ROOT}/skills/spec-workflow/workflow.py" \
    arch-review-needed \
    "docs/specs/NNN-<slug>/spec.md" \
    "<slice-fragment>"); then
  echo "arch-review-needed failed — aborting" >&2
  exit 2
fi
if [ "$NEED_ARCH" = "true" ]; then
  PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    arch-review \
    "docs/specs/NNN-<slug>/spec.md" \
    "<slice-fragment>" \
    "<deliverable-path-1>" "<deliverable-path-2>" ...)
  SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
    subagent-type arch-review)
fi
```

When `$NEED_ARCH` is `true`, feed `$PROMPT` to `Task` with
`subagent_type: "$SUBAGENT"`. The prompt routes via the same
prose-based dispatch as `pr-review` to the most-specific `arch-review`
SKILL.md reachable. The pass returns the canonical four arch output
buckets (summary / strengths / concerns / open questions). Tag and
block semantics match the craft pass: `[blocker]` entries block the
REVIEWED transition; `[nit]` entries and `needs-changes` become
reconciliation-log items.

Slice authors set `arch_review: true` in the slice file's frontmatter
when the slice changes module boundaries, public contracts, or
architecture-shaped concerns. The slice template ships the field
commented out as a discoverability nudge.

### Reconciliation review

After the deviation log subsection has been added under the slice in
`spec.md`:

```bash
PROMPT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  reconciliation \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>")
SUBAGENT=$(python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type reconciliation)
```

Feed `$PROMPT` to `Task` with `subagent_type: "$SUBAGENT"`. The prompt
explicitly tells the reviewer NOT to re-evaluate against ACs — it only
verifies the deviation log matches reality.

### Recording and checking review evidence (slice 045-02)

A review pass is durable evidence, not ephemeral chat. After a pass
returns a verdict, record it as a file beside the slice it grades, at
`docs/specs/NNN-<slug>/reviews/slice-NN-<pass>.md` (ADR-0014 §1). The
schema (`pass ∈ {compliance, craft, arch, reconciliation}`,
`verdict ∈ {pass, fail, needs-changes}`, plus `reviewer`, `reviewed_at`,
`prompt_source`) lives in `skills/_common/review_evidence.py` so the
slice 045-03 transition gate validates the same shape.

Record a verdict (the freeform body comes from `--summary-file` or stdin):

```bash
python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  record-review \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  --pass compliance \
  --verdict pass \
  --reviewer jig:reviewer \
  --prompt-source "review.py implementation ..." \
  --summary-file verdict.md
```

Re-recording the same `(slice, pass)` **overwrites in place** — git
history is the audit trail, there is no append (ADR-0014 §4). A
`fail`/`needs-changes` that has not been overwritten by a later `pass`
therefore still blocks the gate, which is exactly the "superseded
without a later pass" case.

Validate the evidence set for a slice at a transition stage:

```bash
python3 "${PLUGIN_ROOT}/skills/independent-review/review.py" \
  check-reviews \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  --stage REVIEWED   # or RECONCILED
```

`check-reviews` exits `0` when the required passes for the stage all
clear (`REVIEWED` → compliance + craft, plus arch iff the slice declares
`arch_review: true`; `RECONCILED` → reconciliation), or `2` with
actionable diagnostics for missing files, malformed frontmatter, unknown
pass/verdict values, non-clearing (superseded-only) verdicts, and invalid
slice targets. The gate rule is uniform: a pass clears iff `verdict: pass`
(ADR-0014 §3). **Code-staleness** (a `pass` artifact predating a later
deliverable change) is deliberately NOT checked — it is a deferred
enhancement (ADR-0014 Scope).

**The full enforced flow.** build prompt (`review.py implementation` /
`pr-review` / `arch-review`) → spawn reviewer → `record-review` the
verdict → `check-reviews` (optional preflight) → `workflow.py transition
… REVIEWED` (or `RECONCILED` / `DONE`). The transition imports the same
validator `check-reviews` uses, so the gate and this skill agree by
construction. A refused transition names the missing/invalid artifact and
the `record-review` command to produce it; a deliberate out-of-band flow
bypasses the gate with `JIG_REVIEW_EVIDENCE_GATE=0`. **Recovering from a
failed review:** address the findings, re-run the pass, `record-review`
again (overwrites the earlier file for that `(slice, pass)` in place — git
history is the audit trail), then re-run the transition; with every
required pass now `pass`, the gate clears.

### What gets put in the prompt automatically

- Standard preamble ("You are seeing this work for the first time")
- The slice's full label (helper looks it up from the spec)
- "What you must NOT do" block (no prior reasoning, no soften, no file writes,
  no `docs/memory/` writes)
- Canonical output format (`VERDICT | REASONING | SPECIFIC ISSUES | RECONCILIATION NOTES`)

## Context isolation pattern

Implementer writes deliverable to disk → `review.py` builds a self-contained
prompt → Codex spawns the reviewer Task with that prompt → reviewer reads
only what the prompt points at. This is imperfect (parent context is
technically accessible to subagents — see GitHub issue #20304), but works
reliably when the prompt is sharp.

## Gotchas

- **`review.py` does not spawn the Task.** It only constructs the prompt
  string. Codex is responsible for invoking the `Task` tool with the prompt
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
