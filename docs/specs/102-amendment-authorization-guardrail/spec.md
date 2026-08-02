---
status: IN_PROGRESS
skill: spec-workflow
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 102: Amendment-authorization guardrail

> Reserved on 2026-08-02 via `workflow.py new`. Resolves the two guardrails
> the maintainer approved on
> [issue #125](https://github.com/ramboz/jig/issues/125).

## Overview

**jig tells an agent _how_ to amend a closed record but never _who authorises_
it.** [Issue #125](https://github.com/ramboz/jig/issues/125) reports the gap:
jig ranks artifacts as canon ([ADR-0010](../../docs/decisions/adr-0010-amendment-scope-records-vs-live-prose.md)
gives records a dated `## Amendments` mechanism; the reconciliation checklist
step points at it), but nothing sits between "an agent discovers two canon
artifacts disagreeing" and "the agent writes its own resolution into the
record." The closed-spec-drift checklist step reads as an instruction to go
ahead and write the amendment.

Two failures happened in one downstream session, and jig guards neither:

- **Approval of a behaviour was treated as authority over the record.** The
  owner approved *what the app does* ("match the design"); the agent treated
  that as approval to *rewrite what the specification says*, declaring an
  acceptance criterion superseded. Deciding behaviour and amending the record
  are separate grants.
- **The contradiction did not exist.** The agent asserted "AC3 contradicts the
  approved behaviour" after reading AC3 in isolation; a sibling criterion (AC9)
  already mandated the same affordance, so nothing was lost. For a cross-cutting
  question the unit of reading is the whole criteria block, not the one item
  that appears to speak to it.

The maintainer
[ruled on the issue thread](https://github.com/ramboz/jig/issues/125#issuecomment-5072602687):
address proposals **1 and 2** (prose edits in the skills) and **defer 3** (a
`PreToolUse` hook on `docs/decisions/**`) "until we see it explicitly hitting
ADRs in a recurrent way." This spec implements the two approved prose
guardrails and nothing else.

## Decision (maintainer's, not this spec's)

Recorded from the issue thread:

| # | Proposed change | Ruling | This spec |
|---|---|---|---|
| 1 | Authorization rule at the ADR-0010 step in `spec-workflow/SKILL.md` | **Yes — simple prose edit** | Slice 102-01 |
| 2 | `analyze` output contract states findings are surfaced, never auto-resolved | **Yes — simple prose edit** | Slice 102-01 |
| 3 | `PreToolUse` hook denying `Write`/`Edit` on `docs/decisions/**` | **Defer** until it recurrently hits ADRs | *out of scope* |

The maintainer's own framing bounds scope: item 3 is deferred, and the issue
itself notes the hook "**cannot** cover the actual case" (amendments live inside
slice files that agents edit legitimately and constantly, so the failure is not
expressible as a path match). So both approved changes are checklist/contract
**rules that depend on the agent reading them** — deliberately advisory, in the
agent's trust boundary, consistent with the
[spec-gate model (ADR-0011)](../../docs/decisions/adr-0011-spec-gate-model.md).

This is the authorization sibling of spec 097 (issue #124), which hardened
*faithful recording* of amendments; this spec hardens *authorization to* amend.

## Assumptions

None.

_Both edit sites were read directly before drafting and the host-package mirror is regenerated deterministically with a CI drift guard, so there is no unverified load-bearing claim about a runnable surface — the 064-04 frame-critique trigger stays default-off._

## Decomposition

**SPIDR axis: Rules.** One governance rule (an amendment to a closed record
requires explicit owner approval; surface-and-stop; read the whole criteria
block) applied at its two points of use — the reconciliation checklist step
that authorises the amendment, and the drift detector whose output could be
mistaken for a mandate to resolve. The two edits are one guardrail; splitting
them would ship half a rule. A single vertical slice delivers the end-to-end
value: an agent walking the ceremony now meets surface-and-stop before it can
self-adjudicate, and the drift detector's contract says it hands off rather than
amends.

No Spike (both sites read, no open question), no Path/Interface/Data split (one
rule, two co-delivered surfaces).

## Slices

- [102-01 — surface-and-stop-authorization-rule](slice-01-surface-and-stop-authorization-rule.md)
