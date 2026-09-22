---
status: DRAFT
skill: scaffold-init
use_cases: []
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on first use and link the term to docs/memory/glossary.md (or jig's lexicon). See docs/workflow.md "Self-defining vocabulary". -->

# Spec 115: Autonomy-readiness checklist and agent-fix evidence separation

> Implements [ADR-0063](../../decisions/adr-0063-agent-fix-evidence-separation.md)
> (Proposed) and the doc-level adoption named in
> [R-001](../../research/R-001-cloudflare-adlc-assessment.md). Extends the
> governance plane of [ADR-0051](../../decisions/adr-0051-autonomy-governance-plane.md)
> / spec 106. **Status: recorded, not yet built.**

## Overview

Two additions to the scaffolded governance plane, both doc-shaped with a thin
skill-wording change:

1. **A readiness checklist for running a repo unattended.** The seven
   properties Cloudflare says every formerly-manual step must have before
   "you hand over the keys" (the post's own names: Programmatic, Horizontally
   scalable, Reproducible, Real-time push-based, Atomic, Permissioned,
   Self-improving) become a checklist in the scaffolded `<docs>/governance.md`
   beside the branch-protection arming steps, with jig's own coverage marked
   honestly: Atomic (the vertical slice) and Self-improving (the memory layer)
   covered; Permissioned partial (identity separation, no escalation path);
   Programmatic, Horizontally scalable, Reproducible, and Real-time push-based
   are the executor's, not jig's. jig's own `docs/adoption-readiness.md` gets
   the same section for this repo.
2. **The agent-fix evidence-separation invariant** (ADR-0063): a proposed fix
   lands on its own ref, the failure record stays red until a human merges,
   green is new evidence on the fix revision, evidence-modifying fixes are
   flagged. Stated in `governance.md`, worded into the `bug-fix` skill, and
   cross-linked from spec 105 so the quarantine freeze and this freeze share
   one semantics.

Per the servo↔jig coupling rule (ADR-0022 / ADR-0060) nothing here adds an
autonomy primitive to jig's always-on flow: the checklist is a document, the
invariant is a rule the existing lifecycle and reviewer enforce.

## Assumptions

<!-- Spec 064-02 / ADR-0020 — grounding-by-probe (risk-gated). -->

- **Probed 2026-09-22:** `render_governance_doc` in
  `skills/scaffold-init/governance.py` renders `<docs>/governance.md` as a
  single f-string with sections for protected paths, surface-and-stop routing,
  "inert until armed", the arming checklist, and identity separation; jig's own
  repo has no `docs/governance.md` (it predates spec 106's scaffold), so the
  self-hosted copy of the checklist goes to `docs/adoption-readiness.md`.
- **Verified 2026-09-22:** the seven-properties wording is taken from the
  post's full text (supplied by the owner after the authoring environment could
  not reach it) and recorded verbatim in [R-001](../../research/R-001-cloudflare-adlc-assessment.md);
  115-01 quotes from R-001, not from coverage.
- **Unverified, load-bearing for 115-02 AC 4:** whether an evidence-modifying
  fix can be detected mechanically (diff touching the regression-test path or a
  skip marker) reliably enough for a nudge; the slice probes before promising.

## Decomposition

Two slices, one per adopted idea, along the **Rules** axis with a thin
**Interface** (doc) surface:

- **115-01** — the seven-conditions checklist in the governance renderer + the
  self-hosted section, with jig's coverage table.
- **115-02** — the ADR-0063 invariant in the governance renderer, the
  `bug-fix` skill wording (fix ref, append-only evidence, evidence-modifying
  flag), and the spec 105 cross-link.

**Anti-horizontal-phasing.** Each slice leaves an adopter with something they
can act on alone: 115-01 a checklist to run before an unattended run; 115-02 a
rule the reviewer applies to the next bug fix.

## Slices

- [115-01 — seven-conditions-checklist](slice-01-seven-conditions-checklist.md) — readiness checklist in `governance.md` renderer + `docs/adoption-readiness.md`, with jig's coverage marked.
- [115-02 — fix-evidence-separation-rule](slice-02-fix-evidence-separation-rule.md) — ADR-0063 invariant in `governance.md`, `bug-fix` wording, spec 105 cross-link.
