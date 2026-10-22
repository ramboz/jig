---
status: DONE
skill: independent-review
use_cases: [UC-4, UC-7, UC-15]
---

# Spec 120: Generic design attestation

Jig will check preserved design evidence for different kinds of interfaces
through its existing review lifecycle. The producer still owns measurement and
the overall verdict; Jig checks that the evidence belongs to the approved
source and currently delivered build. The tradeoff is an intentionally bounded
supported static profile, not an arbitrary-provider framework.

## Overview

The owner authorized replacement of the unmerged proof-of-concept interfaces
from effort PRs 242–245 with reusable product code. This is prospective work on
default `main`, not a merge of those branches or an amendment of their records.
The original union is commit `43fcc30216cafc8caa8ee01b1688d6f86dff2666`.

Current-state probes: that tree's `skills/_common/design_bindings.py:133–274`
contains a bounded read/hash reader; `static_design_bindings.py:31–48,282–854`
checks the Vellum 0.2 / Servo static profile, including native overall authority
and independent current delivery; `review_evidence.py:523–529,586–595` wires
freshness into the existing checker. Its pilot validator and live preparation
instructions are not reusable. The clean base contains the existing
`record-review`, `check-reviews`, REVIEWED and DONE rails
(`skills/independent-review/review.py`, `skills/_common/review_evidence.py`,
`skills/spec-workflow/workflow.py`), so no new lifecycle or pass is needed.

## Scope and ownership

Keep `jig/static-design-freshness/1`, `vellum-confirmed-source/0.2`,
`static-css-subset/1`, and `static-source-contract-app/1` meanings. External
native overall `gate_result/2` is authority, not a measurement fraction.
Jig never imports, invokes, re-scores or repairs producer evidence. Public
selection and attested bindings stay explicit fenced blocks on the existing
review rail. Source approval and current build/delivery are selected
independently of result rows.

Vellum's generic transitive source files are `confirmed_source.py`,
`capture_confirmed.py`, `design_input.py`, `redline_intake.py`,
`resolve_redline.py`, and `validate_redline.py`. Servo's static observer uses
`static_contract.py`, `static_snapshot.py`, `evidence_io.py`, and
`evidence_runtime.py`, not the former card helpers. Pin actual new runtime
bytes: old approved tooling cannot be relabelled as a new approved epoch.

Retire `jig/design-freshness/1` / `vellum-design-input/0.1-pilot` selections with
actionable refusal. Keep unselected historical scalar design-review behavior
and unflagged users unchanged. Retired evidence is neither migrated nor
downgraded automatically. Old pull requests, worktrees and proof records are
historical and untouched.

Non-goals: arbitrary provider/build argv support; mixed quality profiles beyond
the supported producer contract; registries; query languages; browsers,
evaluators or model runs in Jig; real-app approval or completion; proof exports,
transcripts, absolute private roots, or pilot packages in product payloads.

## Assumptions

None.

## Decomposition

SPIDR (Spike, Path, Interface, Data, Rules): choose **Data**. One vertical
slice replaces the supported evidence subset end-to-end through prompt,
recording, reuse and lifecycle. Splitting reader extraction from public
refusal/validation would leave an intermediate product boundary and is not a
useful separate slice. A spike is unnecessary: retained code and the
owner-confirmed producer contract establish the implementation boundary.

## Slices

- [120-01 — attest generic static evidence](slice-01-generic-static-evidence.md)

## Record identity

Local-only helpers initially allocated 119 / ADR-0065 from the clean main
view. Before drafting, these provisional stubs were moved to 120 / ADR-0066
to avoid aliasing historical unmerged effort records. No reservation or claim
was pushed to main.
