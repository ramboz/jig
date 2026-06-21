---
status: Accepted
dependencies: []
last_verified: 2026-06-21
frame_review: true
---

# ADR-0029: Reconciliation sweep manifest

## Status

Accepted (2026-06-21)

## Context

Reconciliation is already the right phase for documentation cleanup: it runs
after implementation and review, when the agent knows what actually changed.
The current `spec-workflow` checklist says every reconciliation item is a gate,
including deviation logging, architecture impact, inbox triage, primer hygiene,
memory sync, and closed-spec drift handling. The deterministic transition gate,
however, only verifies recorded review evidence and the presence of a deviation
log subsection.

That split creates the drift pattern jig has now observed repeatedly:

- front-door summaries such as `README.md`, `docs/product-vision.md`, and
  `docs/architecture.md` can preserve stale live facts after the underlying
  spec or helper changed;
- hot primers such as `CLAUDE.md` and the v2 `AGENTS.md` can accumulate
  historical details that belong in specs, status-board notes, or memory;
- `docs/inbox.md` and `docs/refinement-todo.md` can retain entries that are
  already resolved by landed specs or by subsequent cleanup;
- reconciliation reviews verify the claims the implementer logged, but do not
  make omissions visible unless the implementer remembered to mention them.

The decision is not whether reconciliation owns cleanup. It does. The decision
is how to make that ownership cheap, inspectable, and hard to forget without
turning every doc file into a brittle hard gate.

## Decision Options Considered

### Option A: Keep the existing checklist only
- **Pros:** No new ceremony. Reconciliation remains mostly judgment-driven.
- **Cons:** The failure mode remains: omissions are invisible. A reviewer can
  honestly pass a deviation log that never mentioned stale front-door docs,
  stale queue entries, or primer bloat.

### Option B: Hard-gate every drift-prone artifact
- **Pros:** Maximum determinism. `transition … RECONCILED` could refuse unless
  every named file was touched or machine-proved current.
- **Cons:** Too rigid for documentation. Many slices legitimately do not affect
  `README.md`, product vision, architecture, inbox, refinement todo, or primers.
  A hard touch requirement would create no-op churn, and proving semantic
  freshness mechanically would be expensive and unreliable.

### Option C: Require a reconciliation sweep manifest and reviewer omission check
- **Pros:** Makes omissions visible while preserving judgment. The helper only
  checks that the manifest exists; the reviewer checks whether each
  `updated` / `no-op` / `deferred` rationale is credible. The manifest can
  cover both Claude-era and host-portable primers, and it gives queues a
  first-class cleanup pass.
- **Cons:** Adds a small required subsection to every reconciled slice. Poorly
  written manifests could become checkbox theater unless the reviewer prompt
  explicitly checks omissions.

### Option D: Generate an inventory and require evidence for each no-op
- **Pros:** Stronger independence. A helper could derive touched files from
  `git diff`, list core docs that always need a disposition, and require
  evidence commands for `no-op` rows.
- **Cons:** It front-loads a lot of mechanism before jig has measured whether
  the lighter control fails. It also risks brittle false positives: many
  documentation freshness checks are semantic, and a generated list can still
  miss related-but-untouched stale prose. The right first escalation is to make
  the reviewer compare the manifest against an independent checklist; only
  promote generated inventory to a gate if copied boilerplate or missed
  omissions persist.

## Recommended Decision

Adopt **Option C: require a reconciliation sweep manifest and reviewer omission
check**, with one explicit guard from Option D: the reviewer check is not a
blind attestation of the implementer's self-report. The reviewer prompt must
compare the sweep against (a) the canonical core surfaces below, (b) artifacts
touched by the slice, and (c) related generated/index files such as the status
board or ADR index when statuses or ADRs changed.

Every slice that transitions `REVIEWED → RECONCILED` should carry a
`### Reconciliation sweep` subsection adjacent to the deviation log. The sweep
is a compact ledger over the drift-prone surfaces:

- `README.md`
- `docs/specs/README.md`
- `docs/product-vision.md`
- `docs/architecture.md`
- `CLAUDE.md`, `AGENTS.md`, and their scaffold templates when present
- `docs/inbox.md`
- `docs/refinement-todo.md`
- `docs/memory/**`
- `docs/decisions/README.md` / ADR index when the slice touches ADRs
- any additional live prose or generated template the implementation touched

Each row records one disposition:

- `updated` — the slice changed the artifact and the manifest summarizes why;
- `no-op` — the artifact was checked and did not need a change;
- `deferred` — real drift or cleanup remains, with a target owner or trigger.

The deterministic transition gate should initially check only that the sweep
subsection exists, mirroring the deviation-log presence gate. It should not
parse or validate every row semantically. The reconciliation reviewer should be
updated to check whether the sweep has credible coverage, whether `no-op`
claims conflict with touched files or landed behavior, whether `deferred` rows
name an owner or trigger, and whether any obvious touched or related artifact is
missing. This is the cheap independence layer: the manifest records the
implementer's claim, but the reviewer has an explicit artifact-discovery
checklist to push against that claim.

For hot primers, use the broader term **primer hygiene** rather than
`CLAUDE.md hygiene`: `CLAUDE.md` remains the Claude adapter, while `AGENTS.md`
and related templates become the host-portable primer surfaces on the v2 path.

## Consequences

**Becomes easier:**
- Reconciliation reviews can catch omissions, not just false claims.
- Queue cleanup becomes routine: resolved `inbox` and `refinement-todo` items
  must be explicitly updated, retained, or deferred.
- Front-door docs get an inspectable freshness pass without forcing every
  slice to edit them.
- `CLAUDE.md` and `AGENTS.md` share one cleanup concept instead of diverging
  by host.

**Becomes harder:**
- Every reconciled slice has a little more close-out prose to write.
- Reviewers must learn to judge `no-op` and `deferred` rationales, not just
  code/spec deviations.
- Reviewer prompts become slightly more demanding: they must compare the sweep
  against core surfaces and touched/related artifacts, not merely read the
  manifest.
- The first implementation has to update the transition gate, prompt builder,
  templates, and documentation together so the new subsection is not optional
  by accident.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

_Load-bearing factual claims about runnable surfaces (library/API capability,
version/perf behavior, behavior of existing code) must be backed by an executed
probe (run a command, read source/`node_modules`) or a citation — or listed
here explicitly as an assumption. Never assert an unverified claim as fact._

_Risk-gated: omit this section (or write "None") when the decision has no
unverified load-bearing assumptions — do not pad with boilerplate._

None. The current gate and reviewer-prompt behavior was verified by reading
`skills/spec-workflow/workflow.py`, `skills/spec-workflow/SKILL.md`, and
`skills/independent-review/review.py` on 2026-06-21.

## Kill criteria

_What would make this decision wrong? List the conditions that, if observed,
should reverse or shelve it. Risk-gated like Assumptions — write "None" or omit
when there is no meaningful kill condition; do not invent ceremonial ones._

- Reconciliation manifests become mostly copied boilerplate and reviewers stop
  catching real omissions.
- Reviewers repeatedly miss omissions because there is no generated/touched-file
  inventory in the prompt; that is the trigger to promote Option D's inventory
  from deferred escalation to a deterministic helper.
- Manifest upkeep costs more than the drift it prevents across several landed
  specs.
- A later deterministic freshness audit can cheaply prove the same artifact
  set current without requiring human-written dispositions.

## Open questions

- Should `workflow.py transition` require only subsection presence, or also a
  minimum artifact list? This ADR recommends presence-only for the first slice;
  implementation may add a warning, but not a hard semantic parser, if tests
  show missing-core-surface mistakes are otherwise common.
- Should resolved `docs/inbox.md` entries be struck through, moved, or deleted?
  Existing practice allows strike-through or promotion to memory; spec 082
  should preserve that flexibility rather than inventing a new queue format.
