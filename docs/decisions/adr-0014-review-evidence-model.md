---
dependencies: []
last_verified: 2026-06-01
---

# ADR-0014: Review-evidence model — durable verdict artifacts gate the lifecycle

## Status

Accepted (2026-06-01)

## Context

jig's workflow documentation presents post-implementation review and
reconciliation as load-bearing gates. The mechanics do not back the
claim:

- `docs/workflow.md` (lines 43–44) states "The Stop hook blocks
  completion if reconciliation hasn't happened." The only `Stop` hook is
  `hooks/scripts/jig-task-capture.sh`, which greps the transcript for
  TODO-language and emits a soft `additionalContext` nudge. It blocks
  nothing, and it is not a reconciliation gate.
- `skills/spec-workflow/workflow.py transition` validates status
  membership, the `DEFERRED` re-open restriction, and `DONE`
  dependencies. It reads **no** review evidence.
- `skills/independent-review/review.py` builds standardized reviewer
  prompts and, by design (slice 004-01), does not spawn a subagent or
  record a result.
- `agents/implementer.md` (line 34) still tells the implementer to
  "Update spec status to `REVIEWED`" directly.

So the lifecycle *claims* are stronger than the lifecycle *mechanics*.
That matters because jig is a workflow product: if the gates are ritual
text rather than checks, users learn to trust the prose instead of the
evidence. This is the same framing-vs-enforcement gap that
[spec 040](../specs/040-isolation-honesty/spec.md) closed for reviewer
"isolation" and that [ADR-0011](./adr-0011-spec-gate-model.md) closed for
the conventions gate — describe what the mechanism actually does, and
make the load-bearing part real.

Two constraints bound the fix:

- **No portable subagent API.** The host does not expose a scriptable
  way to spawn the reviewer, so a helper cannot *perform* the review. It
  can only *record and validate* a verdict the reviewer flow produced.
  (Spec 045 non-goal: no automatic subagent spawning.)
- **No human-authentication claim.** Per ADR-0011, an in-process check
  sits inside the agent's trust boundary; it cannot prove a human
  personally approved a verdict. The gate enforces *evidence
  consistency*, not *human sign-off*.

Within those bounds, the design move is: **turn each review pass into a
durable, schema-checkable artifact, and make `workflow.py transition`
refuse the review/reconciliation status moves unless the required
artifacts exist and pass.** The reviewer judgment stays human/agent-
authored; the helper validates shape and declared verdict, never
quality.

Existing policy already fixes most of the semantics — this ADR makes
them machine-checkable rather than inventing new ones:

- `docs/workflow.md` (lines 75–99) defines three passes — **compliance**
  (`jig:independent-review`, always), **craft** (`pr-review`, always),
  **arch** (`arch-review`, only when the slice frontmatter declares
  `arch_review: true`) — and states "all required passes must `pass` for
  the IN_PROGRESS → REVIEWED transition." Spec 031 made the craft pass
  unconditional.
- The verdict envelope is already VERDICT / REASONING / SPECIFIC ISSUES /
  RECONCILIATION NOTES, with craft/arch issues tagged `[blocker]` /
  `[nit]` / `[strength]`. Compliance blocks on `fail`/`needs-changes`;
  craft/arch block only on a `[blocker]` finding (nits become
  reconciliation-log items).

The genuinely open question this ADR settles is **where the evidence
lives and how the verdict is represented** so both `review.py` (writer)
and `workflow.py` (gate) can rely on it.

## Decision Options Considered

The slice (045-01 AC1) requires comparing at least three storage models
against reviewability, merge-conflict risk, scaffold-mode portability,
and future CI use.

### Option A: Per-spec `reviews/` directory, one file per (slice, pass)

`docs/specs/NNN-slug/reviews/slice-NN-<pass>.md`, where `<pass>` ∈
{`compliance`, `craft`, `arch`, `reconciliation`}. The file lives beside
the slice files it concerns, under the spec directory scaffold already
manages.

- **Pros:** Highest reviewability — a verdict shows up in the PR diff as
  plain markdown next to the slice it grades. Lowest merge-conflict risk
  — distinct (slice, pass) pairs are distinct files, so concurrent slices
  never contend. Matches jig's established slice-per-file convention
  (spec 018: sibling files under the spec dir). Cleanest future CI and
  gate checks — per-pass file existence + frontmatter parse is a trivial,
  unambiguous assertion. Scaffold-portable for free: it rides
  `docs/specs/`, which every install shape already has.
- **Cons:** More files (up to four per slice). Supersession needs a
  convention (resolved below: overwrite-in-place, git history is the
  audit trail).

### Option B: Single per-slice review file

One `docs/specs/NNN-slug/slice-NN-reviews.md` per slice holding every
pass as a section.

- **Pros:** Fewer files; one place to read a slice's whole review story.
  Still under `docs/specs/`, so reviewable and scaffold-portable.
- **Cons:** All passes for a slice share one file. Passes are recorded
  sequentially so contention is low, but a re-review plus a fresh pass
  can still collide. Coarser CI/gate checks — the validator must parse
  and locate sections within a file rather than test for a file, which is
  more fragile and a larger surface for malformed input.

### Option C: Repo-level `.jig/reviews/` ledger

A centralized machine-state ledger under `.jig/` (alongside
`scaffold.json`, `skill-usage.jsonl`).

- **Pros:** One known location; easy to enumerate all evidence at once.
- **Cons:** Lowest reviewability — `.jig/` is machine territory (install
  manifest, append-only telemetry), is not where a reviewer looks, and is
  plausibly git-ignored in some adopters. Highest merge-conflict risk —
  every slice's every pass writes into one subtree. Needs extra scaffold
  plumbing to create/seed the directory. Divorces the evidence from the
  spec it grades, so a PR reviewer can't see the verdict beside the work.

| Model | Reviewability | Merge-conflict risk | Scaffold portability | Future CI |
|---|---|---|---|---|
| **A — per-spec `reviews/` dir** | High (PR diff, beside slice) | Low (distinct files) | High (rides `docs/specs/`) | Clean (per-pass file check) |
| B — single per-slice file | Medium | Medium (passes share a file) | High | Coarser (section parse) |
| C — `.jig/reviews/` ledger | Low (machine territory) | High (single subtree) | Needs plumbing | Greppable but opaque |

## Recommended Decision

**Option A — per-spec `reviews/` directory, one file per (slice, pass).**
It wins on every criterion the slice names, and it is continuous with
jig's existing slice-per-file convention.

The full decision, beyond storage:

### 1. File layout and naming

```
docs/specs/NNN-slug/reviews/slice-NN-<pass>.md
```

`<pass>` ∈ {`compliance`, `craft`, `arch`, `reconciliation`}. One file
per (slice, pass). Example:
`docs/specs/045-review-lifecycle-gates/reviews/slice-02-compliance.md`.

### 2. Verdict schema

YAML frontmatter carries the machine-checkable fields; the body carries
the human-readable verdict envelope already in use.

```markdown
---
slice: 045-02
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-02T14:30:00Z
prompt_source: review.py implementation docs/specs/045-review-lifecycle-gates/spec.md 045-02 skills/_common/review_evidence.py
---

## VERDICT
pass

## REASONING
<why>

## SPECIFIC ISSUES
- [nit] <...>          # craft/arch tag entries [blocker]/[nit]/[strength]

## RECONCILIATION NOTES
<carry-forward items>
```

Required frontmatter fields: `slice`, `pass`, `verdict`, `reviewer`
(source — e.g. `jig:reviewer`, `general-purpose`, `pr-review`),
`reviewed_at` (ISO-8601 timestamp — provenance), `prompt_source` (the
command that built the reviewer prompt — reproducibility). The body
mirrors the existing envelope so recorded evidence is continuous with
today's review output.

### 3. Verdict vocabulary, authoring rule, and the gate rule

Allowed `verdict:` values: `pass`, `fail`, `needs-changes`.

**Authoring rule** (how a reviewer maps findings to a verdict — preserves
the existing per-pass block semantics):

- **Compliance:** `pass` only when clean; `needs-changes`/`fail`
  otherwise (both block).
- **Craft / Arch:** `pass` when clean *or* only `[nit]`/`[strength]`
  findings (nits flow to the reconciliation log, they do not block);
  `needs-changes`/`fail` when any `[blocker]` finding is present.

**Gate rule** (what `workflow.py transition` checks — deliberately
uniform): a required pass *clears* the gate iff its file exists, its
frontmatter parses, `pass`/`verdict` are in-vocabulary, and
`verdict: pass`. Anything else (`fail`, `needs-changes`, missing,
malformed) blocks. The per-pass nuance ("nits don't block") lives in the
*authoring* rule — a nits-only craft review is recorded as `pass` — not
in gate-parsing complexity. This keeps the gate a one-line predicate and
keeps the nit/blocker distinction in the artifact's audit trail.

### 4. Supersession

One file per (slice, pass) means a re-review **overwrites in place** with
a fresh `reviewed_at`. The current file always holds the operative
verdict; prior verdicts live in **git history**. This is the
[ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md) posture:
review verdicts are *live operational artifacts*, not closed records, so
they are corrected inline with git history as the audit trail (no
`## Amendments` block). A `fail`/`needs-changes` that has not been
overwritten by a later `pass` therefore blocks — exactly "superseded
without a later pass."

This fully covers the "superseded without a later pass" failure mode the
slices require (slice 045-02 AC2, slice 045-03 AC1): it reduces to
`verdict != pass`, which the uniform gate (§3) already blocks — no
separate "superseded" state or marker is needed. The *only* part
deferred (Scope) is the distinct case of a `pass` artifact that predates
a later change to the slice's deliverable — **stale-but-passing** — which
needs deliverable-vs-`reviewed_at` comparison the gate does not do today.
"Stale/superseded-only evidence" in slice 045-02 AC2 thus splits: the
superseded-only half is enforced here; the stale half is the deferred
warning.

### 5. Transition map

| Transition | Required evidence (in addition to existing checks) |
|---|---|
| → `REVIEWED` | `compliance` = pass **and** `craft` = pass **and** (`arch` = pass iff slice frontmatter `arch_review: true`) |
| → `RECONCILED` | deviation log present in the slice file **and** `reconciliation` = pass |
| → `DONE` | existing dependency check **and** the full required set above re-validated = pass |

"Deviation log present" reuses jig's **existing** notion — `land.py`'s
`check_deviation_log` (slice 007-01), a heading-presence check
(`^###\s+deviation\s+log\b`). 045-03 should share that predicate (a
`_common` move is a reasonable refactor, not a mandate) rather than
invent a second one. Heading-presence is deliberately the *only*
mechanical log check: whether the log is real prose vs. the template's
`_TODO.` stub is **attested by the reconciliation verdict** — that is
precisely what the reconciliation reviewer evaluates — not re-derived by
a brittle placeholder string-match in the gate. So the log is separate
from the verdict (the log is implementer/reconciler prose; the
reconciliation file is the independent verdict on it), and both are
required to reach `RECONCILED`.

`DONE` re-validates the whole set (cheap) so a hand-edited status can't
walk past gates that an earlier transition enforced. **Ungated
transitions keep current behavior**: → `DRAFT`, → `READY_FOR_REVIEW`,
→ `READY_FOR_IMPLEMENTATION`, → `IN_PROGRESS`, → `DEFERRED`, and the
`DEFERRED` → `DRAFT` re-open. The two **review back-edges** in the
`docs/workflow.md` state diagram — `REVIEWED` → `IN_PROGRESS`
(needs-changes) and `RECONCILED` → `IN_PROGRESS` (reconciliation fails) —
also stay ungated: they *relax* status to re-enter the loop, so there is
nothing to gate; re-reaching `REVIEWED`/`RECONCILED` re-runs the gate
against the (now overwritten) evidence. `DONE` is terminal; re-opening it
is out of scope.

### 6. Hook and docs stance

**The transition gate is the enforcement mechanism — not a hook.** Per
ADR-0011, an in-process hook shares the agent's trust boundary and a
`Stop` hook cannot reliably block completion. So:

- The false claim in `docs/workflow.md` ("The Stop hook blocks
  completion…") is **corrected** to describe the deterministic
  transition gate as the real mechanism.
- `hooks/scripts/jig-task-capture.sh` keeps its actual job (task-capture
  nudge). We stop mis-citing it as a reconciliation gate. No hook logic
  changes in this spec.
- A *soft* `Stop`-hook reconciliation nudge (additionalContext: "slice X
  is REVIEWED but not RECONCILED") is a **deferred enhancement** (Scope),
  consistent with ADR-0011's soft-nudge-not-hard-gate philosophy.

**Files later slices (045-04) must align**, named here per AC4:
`docs/workflow.md`, `agents/implementer.md`,
`skills/spec-workflow/SKILL.md`, `skills/independent-review/SKILL.md`,
`README.md`, `templates/CLAUDE.md.template` + scaffold-generated docs,
and the project `CLAUDE.md` skills table.

### 7. Module layout (guidance for slices 045-02/03)

The schema is needed by two callers — `review.py` (writer) and
`workflow.py transition` (gate). Per
[ADR-0003](./adr-0003-extract-find-slice-section.md) (two callers of the
same helper → extract to `skills/_common/`), the schema, parse/serialize,
`required_passes(slice)`, path resolution, and the gate predicate live in
a new **`skills/_common/review_evidence.py`**. `review.py` gains the
evidence CLI (`record-review` to write, `check-reviews` to validate);
`workflow.py transition` imports the shared validator directly rather
than shelling out. This is recommendation, not mandate — the slices may
refine subcommand homes during implementation.

## Consequences

**Becomes easier:**

- The lifecycle claim is true. "Review gates the transition" is now a
  deterministic check a contributor (or CI) can run and trust.
- Review verdicts are durable and reviewable in the PR diff, beside the
  slice they grade — recoverable history instead of ephemeral chat.
- A blocked transition is self-explanatory: the gate names the missing or
  non-passing artifact and the command to produce it.

**Becomes harder:**

- A passing review now has a recording step. The cost is one
  `record-review` call per pass; the payoff is the gate. The recorder
  must be ergonomic enough that it is not skipped (slice 045-02 concern).
- The gate cannot prove *who* authored a verdict (ADR-0011 trust-boundary
  limit). It enforces evidence consistency, not human sign-off; teams
  needing the latter use the out-of-band channel (CODEOWNERS / CI /
  branch protection). Stated plainly so the gate is not over-trusted.

**Implementation status:**

- **045-02** — `skills/_common/review_evidence.py` (schema + validate +
  gate predicate) and the `review.py` evidence CLI
  (`record-review` / `check-reviews`); scaffold parity if needed.
- **045-03** — `workflow.py transition` imports the validator and
  enforces the transition map above; specific refusal diagnostics;
  ungated transitions unchanged.
- **045-04** — align the docs/agent/hook files named in §6.

## Scope

**In scope:** the evidence contract (storage, schema, verdict vocabulary,
supersession), the transition map for `REVIEWED`/`RECONCILED`/`DONE`, and
the docs/hook stance.

**Deferred enhancements (named, no slice reserved):**

- **Code-staleness hard-gating.** Hard-blocking a transition when passing
  evidence predates a later change to the slice's deliverable (reusing the
  `workflow.py stale` git-log/mtime machinery from slice 015-03). For now
  the gate checks existence + parse + `verdict: pass`; staleness is at
  most a validator *warning*. Trigger: a real incident where stale-but-
  passing evidence let a changed slice through.
- **Soft `Stop`-hook reconciliation nudge** (additionalContext, like
  `jig-boundary-change-warn`). Trigger: observed forgotten-reconciliation
  cases.
- **CI consumption** of `check-reviews`. Trigger: a CI redesign (spec 045
  non-goal — local helpers stay the source of truth).

**Out of scope:** automatic subagent spawning; proving human approval;
rewriting the broader spec lifecycle.

## Relationship to other decisions

- **[ADR-0011](./adr-0011-spec-gate-model.md) (spec-gate model).** Supplies
  the hook stance: hooks are deliberateness signals inside the agent's
  trust boundary, not hard gates. This ADR puts the *hard* enforcement in
  `workflow.py transition` (a check the agent runs as part of the
  lifecycle) and keeps hooks soft — and corrects the workflow.md claim
  that over-stated a Stop hook.
- **[ADR-0010](./adr-0010-amendment-scope-records-vs-live-prose.md)
  (amendment scope).** Supplies the supersession posture: verdicts are
  live operational artifacts, corrected inline with git history as the
  audit trail — no `## Amendments` block.
- **[ADR-0003](./adr-0003-extract-find-slice-section.md) (extract to
  `_common`).** Supplies the module rule: two callers of the verdict
  schema → `skills/_common/review_evidence.py`.
- **[Spec 040](../specs/040-isolation-honesty/spec.md) (isolation honesty)
  / honesty lineage.** Same theme: claims about what jig's mechanisms
  guarantee should match what they enforce.
- **Spec 031 (unconditional craft pass) / slice 003-04 (auto-tick).** Spec
  031 makes craft a required pass; 003-04 already auto-ticks the
  review-passed DoD boxes on the gating transition. This ADR makes the
  *evidence* behind those boxes a precondition, closing the gap between
  the tick and the work.

## Open questions

- **Should `reviewer:` be validated against an allowlist** (`jig:reviewer`
  / `general-purpose` / `pr-review` / `arch-review`) or stay freeform?
  Lean freeform with a documented convention; revisit if garbage
  provenance values appear in practice.
- **Does the recorder need to enforce that `reviewed_at` post-dates the
  slice's last change** at write time? Folded into the deferred
  code-staleness item rather than blocking this ADR.
