---
status: Proposed
dependencies: [adr-0016, adr-0014]
last_verified: 2026-07-15
frame_review: true
---

# ADR-0037: Bug-fix repository closure evidence

## Status

Proposed (2026-07-15)

## Context

The bug lifecycle proves diagnose-before-fix, fresh-main reproduction, and a
red-to-green regression test. Its review prompt asks about blast radius, but
the workflow does not require the implementer to inventory equivalent logic,
inspect the history that introduced it, or close every affected call site
before coding. That omission is observable: a Mystique change duplicated an
existing URL-identity helper and fixed one lookup path while missing another
path with the same contract. TDD passed because the local behavior was covered;
the repository-level closure question was never made durable evidence.

This is a process defect, not a request to mandate one search product. Semantic
indexes can make discovery cheaper, but the lifecycle must remain correct with
targeted text search and git history alone.

## Decision Options Considered

### Option A: Leave repository closure to the review passes
- **Pros:** No new record fields or transition gates.
- **Cons:** Evidence arrives after implementation, when duplicated logic and a
  narrow patch have already shaped the change; reviewers cannot distinguish a
  completed inventory from an unrecorded assumption.

### Option B: Require pre-fix inventory and post-fix call-site closure
- **Pros:** Makes reuse, history, and blast-radius reasoning explicit before
  code is written; gives reviewers concrete evidence; remains tool-neutral.
- **Cons:** Adds a small evidence burden to standard and gnarly bugs and needs
  a compatibility rule for existing records.

### Option C: Require a semantic-index provider for standard bugs
- **Pros:** Strong discovery capability when the provider is healthy.
- **Cons:** Couples lifecycle correctness to optional infrastructure, excludes
  offline/public users, and still does not prove that the search was complete.

## Recommended Decision

Choose **Option B**. Before `ROOT_CAUSED -> FIXING`, standard and gnarly bug
records must contain a repository-closure inventory: equivalent/convergent
logic searched, relevant history inspected, affected call sites identified,
and an explicit reuse decision. Before `-> REVIEWED`, the record must contain
call-site closure evidence explaining how every identified site was changed,
tested, or intentionally left alone.

The helper enforces presence and shape; `bug-review` judges quality. The
inventory is capability-neutral: a semantic index is preferred when available,
with targeted search plus `git log`/`git blame` as the baseline. Existing bug
records remain readable and can transition under a documented compatibility
rule; newly created records carry the new schema.

## Consequences

**Becomes easier:**
- Catching duplicate implementations before they land.
- Reviewing whether a fix closes the repository-wide behavior rather than one
  symptom or call site.
- Learning from earlier project decisions and landed helpers.

**Becomes harder:**
- Bug authors must record a bounded inventory for non-trivial fixes.
- The gate parser and templates need version-aware compatibility tests.

## Assumptions

<!-- Spec 064-02 / ADR-0020 §1–§2 — grounding-by-probe (risk-gated). -->

_Load-bearing factual claims about runnable surfaces (library/API capability,
version/perf behavior, behavior of existing code) must be backed by an executed
probe (run a command, read source/`node_modules`) or a citation — or listed
here explicitly as an assumption. Never assert an unverified claim as fact._

_Risk-gated: omit this section (or write "None") when the decision has no
unverified load-bearing assumptions — do not pad with boilerplate._

- The four evidence prompts are enough to expose the common omission without
  turning every bug into an architecture review. This is deliberately tested
  by dogfooding against the Mystique PR feedback case.

## Kill criteria

_What would make this decision wrong? List the conditions that, if observed,
should reverse or shelve it. Risk-gated like Assumptions — write "None" or omit
when there is no meaningful kill condition; do not invent ceremonial ones._

- If usage data shows standard bugs routinely bypassing the gate because it is
  disproportionate, keep it mandatory for gnarly bugs and make standard-tier
  enforcement advisory.

## Open questions

None.
