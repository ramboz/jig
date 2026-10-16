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

> **Working posture ([ADR-0056](../../docs/decisions/adr-0056-adversarial-register-quarantine.md)).**
> Adversarial review is a *named, bounded operation.* The skeptical,
> flaw-hunting register this skill builds belongs *inside* the review passes —
> they run in isolated reviewer subagents whose context is discarded. Outside a
> review, default to collaborative and solution-forward; don't carry the
> adversarial stance into ordinary conversation.

> Spec 004 promoted this skill from stub to active. The prompt is constructed
> by `review.py`; Claude owns the Task invocation.

## What this skill does

Constructs the standardized reviewer-subagent prompt and tells Claude when /
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
- **Design-review (attest-only pass — on-demand)** — slices 071-01/119-01,
  ADR-0022/ADR-0065. After the craft (+ arch) passes, the orchestrator queries the
  slice's `design_review:` flag via `workflow.py design-review-needed`;
  when `true`, it runs an **attest-only** pass: the read-only reviewer
  attests the explicitly selected external policy and its frozen evidence.
  Rich/mixed evidence requires the installed overall gate-payload verdict,
  including quality, complete required outcomes and source/config/delivery
  bindings; a component pass or high composite is insufficient. No evaluator
  execution or rescoring. Gates REVIEWED like arch; the slice body/deliverables
  must name the contract and separate comparison/evidence references below.
- **Reconciliation review** — after the deviation log is written. The
  reviewer verifies the doc changes match reality; does NOT re-review the ACs.

`review.py` builds the prompt text; `agents/reviewer.md` defines the agent's
tool restrictions and persistent system rules.

## How to use

### Task telemetry tags

When you feed a `review.py` prompt to the `Task` tool, prefix the prompt with
the compact attribution tags that `jig-telemetry.sh` records:

```text
[jig:phase=<phase>] [jig:spec=NNN] [jig:slice=NNN-NN]

<review.py prompt body>
```

Use `compliance` for `review.py implementation`, `craft` for `pr-review`,
`arch` for `arch-review`, `code-health` for `code-health`,
`frame-critique` for frame critique, and `reconciliation` for
reconciliation review. These tags make later token reports price the workflow
phase, not just the subagent type.

> **Always pass `spec.md`, in every recipe below.** The helper resolves which
> file actually holds the named slice — a sibling `slice-NN-<short>.md` under
> the file-per-slice layout, or the `## Slice` section of `spec.md` under the
> embedded one — and points the reviewer at that file, with `spec.md` trailing
> as context. Do not hand-substitute the slice path (bug 019).

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

Then feed `[jig:phase=compliance] [jig:spec=NNN]
[jig:slice=NNN-NN]\n\n$PROMPT` to the `Task` tool with
`subagent_type: "$SUBAGENT"`. The helper resolves `$SUBAGENT`
deterministically — `reviewer` when jig is installed as a plugin (the real
filesystem-based agent is reachable), `general-purpose` when running from
source. Wait for the verdict. Address any `fail`/`needs-changes` findings;
rerun the helper + Task as needed until `pass`.

### Pr-review (craft pass — slice 031-01)

After the compliance pass returns `pass`, run the craft pass:

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  pr-review \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path-1>" "<deliverable-path-2>" ...)
SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type pr-review)
```

Feed `[jig:phase=craft] [jig:spec=NNN] [jig:slice=NNN-NN]\n\n$PROMPT` to
`Task` with `subagent_type: "$SUBAGENT"`. The prompt points the reviewer at
the most-specific `pr-review` SKILL.md reachable in the environment —
Claude's skill router resolves user > project > `jig:pr-review` precedence
via the skill description hints. The pass returns the canonical four output
buckets (scope / blockers / nits / strengths) wrapped in the same verdict
envelope as the compliance pass. SPECIFIC ISSUES entries are tagged
`[blocker]` / `[nit]` / `[strength]`; only `[blocker]` entries block the
REVIEWED transition.

### Arch-review (architecture pass — slice 031-02, on-demand)

The arch pass runs only when the slice's frontmatter declares
`arch_review: true`. Query the flag via `workflow.py arch-review-needed`
before spawning:

```bash
# Capture the helper exit code — a non-zero exit means the slice lookup
# failed, not "no arch pass needed." Surface the error rather than
# silently skipping the pass.
if ! NEED_ARCH=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/spec-workflow/workflow.py" \
    arch-review-needed \
    "docs/specs/NNN-<slug>/spec.md" \
    "<slice-fragment>"); then
  echo "arch-review-needed failed — aborting" >&2
  exit 2
fi
if [ "$NEED_ARCH" = "true" ]; then
  PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
    arch-review \
    "docs/specs/NNN-<slug>/spec.md" \
    "<slice-fragment>" \
    "<deliverable-path-1>" "<deliverable-path-2>" ...)
  SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
    subagent-type arch-review)
fi
```

When `$NEED_ARCH` is `true`, feed `[jig:phase=arch] [jig:spec=NNN]
[jig:slice=NNN-NN]\n\n$PROMPT` to `Task` with
`subagent_type: "$SUBAGENT"`. The prompt routes via the same prose-based
dispatch as `pr-review` to the most-specific `arch-review` SKILL.md
reachable. The pass returns the canonical four arch output buckets (summary /
strengths / concerns / open questions). Tag and block semantics match the
craft pass: `[blocker]` entries block the REVIEWED transition; `[nit]`
entries and `needs-changes` become reconciliation-log items.

Slice authors set `arch_review: true` in the slice file's frontmatter
when the slice changes module boundaries, public contracts, or
architecture-shaped concerns. The slice template ships the field
commented out as a discoverability nudge.

### Frame-critique (adversarial pass — slice 064-03 / ADR-0020, on-demand)

Unlike every other pass, frame-critique runs **PRE-implementation** — it
gates the `DRAFT → READY_FOR_REVIEW` transition of a spec/slice (or, once
[064-05](../../docs/specs/064-spec-frame-hardening/slice-05-adr-accept-gate.md)
lands, an ADR at `adr.py accept`), before any code exists. Its job is
**adversarial**, not conformance: a fresh reviewer hunts the single
load-bearing assumption most likely to be **wrong** and argues why, so a
bad *premise* is caught at authoring time (the cheapest point) rather than
executed with discipline. It runs only when the artifact declares a truthy
`frame_review` flag.

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  frame-critique \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path>" ...)
SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type)
```

Feed `[jig:phase=frame-critique] [jig:spec=NNN]
[jig:slice=NNN-NN]\n\n$PROMPT` to `Task` with
`subagent_type: "$SUBAGENT"`.

Record the verdict as the `frame-critique` pass (below); the
`READY_FOR_REVIEW` gate requires it iff `frame_review` is truthy
(default-off artifacts transition freely). **Model policy (ADR-0020):**
run frame-critique **equal-or-stronger** than the artifact's author —
**never downgrade it for cost** (the one pass whose value is adversarial
depth). 064-03 ships rung-1 (fresh-context subagent) independence;
cross-model (rung-3) is deferred (`docs/refinement-todo.md`).

### Design-review (attest-only pass — ADR-0022 / ADR-0065, on-demand)

The producer runs/scores; Jig **attests** preserved evidence, whether
deterministic or mixed. Run only for a truthy `design_review` flag. In the
slice body/deliverables, explicitly name the supported producer contract,
approval, frozen effective policy/config, **independently selected current
delivery**, overall result and subordinate evidence references. No new
frontmatter, automatic contract discovery or guessed version mapping.

For a rich/mixed contract, require **all** of:

- Readable separately pinned Vellum input-contract, Servo overall gate-payload,
  design-evidence-envelope and design-eval configuration (when used).
- An identifiable, completed honest run. Preserve invocation/acquisition
  claim/receipt and served response/output closure; `env_error`/infra failure
  is not pass or a 0.0 score.
- Matching currently approved source snapshot/target and approval authority;
  frozen effective policy/config, inventory, checks/evaluator and judge
  settings; evaluated/served build versus independent delivery enumeration
  and bytes. Compare source revision **and dirty-input digest**, effective
  build/runtime inputs, config, assets and dependencies under the build-owner's
  declared closure/digest domains. A Git SHA, URL, timestamp, or the result's
  own `current_delivery` assertion is insufficient.
- The installed overall gate-payload policy verdict explicitly passes,
  including quality. Check every required condition against the **pinned policy
  inventory**, not just present result rows. Required missing/unknown/not-run/
  inconclusive/environment-error outcomes, unavailable comparisons, unsupported
  versions and contradictions cannot clear. Optional outcomes follow the
  approved producer policy, not an extra Jig veto.
- Gate/component/envelope/complete output-tree run and raw-byte digest
  consistency. A deterministic component pass with overall quality failure,
  or an overall pass contradicting required/quality failure, is non-clearing.
  Never average away a failure or repair a contradiction by rescoring.

**Pinned pilot seam (producer-owned, not a Jig schema):**
[Servo 036 plan at 6cc759e807cab5411363b44c19c58e7a457b3715](https://github.com/ramboz/servo/blob/6cc759e807cab5411363b44c19c58e7a457b3715/docs/specs/036-deterministic-design-evidence/plan.md).
The supported combination is `vellum-design-input/0.1-pilot`, overall
`gate_result` integer `schema_version: 2`, `required_component_result` v1,
`command_result_artifacts` v1, subordinate `design_evidence` v1, and separately
pinned design-eval configuration revision 2 when used.
Read `.servo/required-policy.json` and its approved installed pin. The overall
`components[].result.{path,hash}` binds exact component bytes; the component's
raw `evidence[].result_artifact` binds the envelope and complete capture tree.
Check the command artifact record's run-scoped root, manifest and complete
sorted inventory. Artifact references use **raw-byte SHA-256**, not reserialized
JSON; semantic identities retain their separate producer digest domains.
The final installed `oracle.sh` execution wrapper is part of the approved
evaluator-artifact closure; compare its exact bytes and the independently
selected raw approved checks. Follow every declared nested runtime file,
not just its manifest hash. Prepared-definition and staged-driver approval
records precede the separately pinned final approved installation.
Approved normal/open C1 packages are at
[Vellum 55dd18007cd5664be17c1e7c4666fd1f00dd93d6](https://github.com/PinkException/vellum/tree/55dd18007cd5664be17c1e7c4666fd1f00dd93d6/plugin/skills/build-to-redline/fixtures/approved-card/c1/release-r3/).
[119's checkpoint](../../docs/specs/119-mixed-design-evidence-attestation/plan.md#pinned-producer-evidence-contract)
preserves the release/approval byte pins and fixture-scoped approval limits;
source approval is not candidate-delivery acceptance.

Reading/hashing (or reading a preserved pure read/hash audit with its invocation
and digest domains) is allowed; invoking/importing the evaluator, recapturing,
rescoring, recomputing weighted scores or inventing thresholds is not.
Unsigned local hashes establish consistency, not honest execution against an
actor able to rewrite all records. Compliance remains independent.

Only an **explicitly selected legacy threshold-only policy** uses the original
higher-is-better composite ≥ its own frozen threshold, with honest execution
and the same source/config/delivery bindings for new attestations. Historical
records and unflagged/default behavior stay unchanged. Missing rich fields
never select a scalar fallback; component-envelope v1 is not legacy
gate-payload v1. Unsupported/ambiguous or unbound evidence needs renewal.

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  design-review \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>" \
  "<deliverable-path>" ...)
```

Record the verdict as the `design-review` pass; the `REVIEWED` gate requires it
iff `design_review` is truthy; DONE rechecks the recorded verdict alongside
the other required reviews. The generated envelope preserves named versions,
gate/component run IDs, paths/raw digests, both sides of all three identity
comparisons, policy inventory/outcomes and producer refusal reasons. Keep
these in the `record-review` body, including on `fail`/`needs-changes`; only
`pass` clears. Compliance/craft/conditional reviews/reconciliation still apply.
For the explicitly selected rich freshness contract (119-02), put a finite
`jig-design-selection` JSON fence in the slice body and a reviewer-authored
`jig-design-bindings` JSON fence in the existing verdict body. Follow the
[exact grammar and record/revalidation recipe](design-bindings.md).
The writer refuses an inconsistent selected `pass`; REVIEWED and DONE re-read
the pinned pre-result context, exact raw references and complete closed
inventories, including nested runtime and independently mutable candidate
input/build-output/delivery trees. Missing bindings cannot downgrade selection.
No producer, evaluator, judge, browser, network or quality recomputation calls.
Changes require fresh producer evidence and independent attestation; restoring
exact bytes can restore consistency. Documentation outside the declared app
closure is not invalidated solely by HEAD. Unselected historical evidence and
unflagged slices keep their existing behavior; legacy expansion is separate.

This controlled sealed local bundle links served-response hashes to selected
delivery bytes, not arbitrary HTTP servers or hostile hosts. Root authorization,
initial semantic comparisons and inventory completeness remain trusted-local
reviewer decisions; the recorder never discovers or approves them. Unsigned
records are not forgery-proof. **No richer-skill detection** — there is no
external "design-review" skill category.

> The `design_review` flag is set **by hand** on a slice/spec whose deliverable
> is validated by an external design-fidelity eval — there is **no** mechanical
> derivation (unlike `frame_review`, which slice 064-04 derives from the spec's
> grounding). Once set, `workflow.py session-plan` surfaces the pass on the
> dispatch plan so it isn't a dead loop.

### Reconciliation review

After the deviation log subsection has been added under the slice — in its
`slice-NN-<short>.md` file, or under the `## Slice` section in `spec.md` in the
embedded layout:

```bash
PROMPT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  reconciliation \
  "docs/specs/NNN-<slug>/spec.md" \
  "<slice-fragment>")
SUBAGENT=$(python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
  subagent-type reconciliation)
```

Feed `[jig:phase=reconciliation] [jig:spec=NNN]
[jig:slice=NNN-NN]\n\n$PROMPT` to `Task` with
`subagent_type: "$SUBAGENT"`. The prompt explicitly tells the reviewer NOT to
re-evaluate against ACs — it only verifies the deviation log matches reality.

### Recording and checking review evidence (slice 045-02)

A review pass is durable evidence, not ephemeral chat. After a pass
returns a verdict, record it as a file beside the slice it grades, at
`docs/specs/NNN-<slug>/reviews/slice-NN-<pass>.md` (ADR-0014 §1). The
schema (`pass ∈ {compliance, craft, arch, code-health, frame-critique,
reconciliation}`,
`verdict ∈ {pass, fail, needs-changes}`, plus `reviewer`, `reviewed_at`,
`prompt_source`) lives in `skills/_common/review_evidence.py` so the
slice 045-03 transition gate validates the same shape.

Record a verdict. The freeform body is **required** and comes from
`--summary-file PATH`, or from stdin with `--summary-file -` — a verdict
with no body is refused. `record-review` never reads stdin unless asked
(bug 017: the old implicit fallback blocked forever on a pipe nobody
closed, hanging CI and agent harnesses):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
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
python3 "${CLAUDE_PLUGIN_ROOT}/skills/independent-review/review.py" \
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
