# Worked example: shallow-validator M1 slice-to-spec migration

This document records the end-to-end migration of one milestone (M1
"EDS thin E2E", 6 slices) of the aso-shallow-validator project from
flat `docs/slices/slice-01..06-*.md` files into jig's nested
file-per-slice layout. Ran 2026-05-15 as the dogfood for spec 020.

## Source: shallow-validator's slice shape (pre-migration)

`docs/slices/slice-01-service-skeleton-async-endpoints.md`:

```markdown
# Slice 01 — Service skeleton + async-by-default endpoint shells

- **Status:** Done
- **Milestone:** M1
- **Depends on:** ADR-004 (async-by-default REST), ADR-014 (Node/TS), ADR-006 (verdicts + scalar), ADR-005 (reason codes), ADR-017 (domain-plugged)
- **Estimated size:** M (1–3 days)
- **Closed:** 2026-05-05 — all 10 ACs verified via 39 unit/E2E tests + live curl smoke against `node dist/index.js`.

## Context

We need the service skeleton before any business logic can plug in.
...
```

Diagnostic observations:

- Heading is `# Slice NN — Title` (H1, single number, no spec
  prefix).
- Status is a prose field, 4-state (`Draft/Ready/In Progress/Done`),
  not in frontmatter.
- Milestone tag is in a prose field.
- File lives in flat `docs/slices/`.

The 6 slices for M1 are `slice-01..06`, all sharing `Milestone: M1`.

## Naming the target spec

Read `docs/milestones/m1-summary.md`:

```markdown
# M1 — EDS thin E2E (Closed 2026-05-05)

**Scope:** End-to-end EDS path on one URL, one patch shape
(`edsBlocks`). Async-by-default REST contract. CDP-based
measurement. CWV oracle + verdict. Per ADR-013.
```

Headline title is "EDS thin E2E". Slug: `eds-thin-e2e`.

Spec number: `001` (M1 is the chronologically-first milestone).

Target folder: **`docs/specs/001-m1-eds-thin-e2e/`**.

## Transform: per-slice

For `slice-01-service-skeleton-async-endpoints.md`:

**Before** (heading + prose status):

```markdown
# Slice 01 — Service skeleton + async-by-default endpoint shells

- **Status:** Done
- **Milestone:** M1
- ...
```

**After** (frontmatter + jig-shape H2 heading + preserved prose):

```markdown
---
status: DONE
dependencies: []
last_verified:
---

## Slice 001-01 — service-skeleton-async-by-default-endpoint-shells

- **Status:** Done
- **Milestone:** M1
- ...
```

Notes:

- New filename: `slice-01-service-skeleton-async-endpoints.md`
  (unchanged — keeps original shortname so cross-references resolve).
- Heading slug-form is derived from the original title, lowercase,
  hyphenated, special chars dropped.
- The original `- **Status:** Done` prose line stays in the body —
  harmless, and preserves the human-readable context.

State translations applied to the 6 slices: all were `Done` → `DONE`.

## Synthesize `spec.md`

`docs/specs/001-m1-eds-thin-e2e/spec.md`:

```markdown
---
status: DONE
skill:
tier: 1
---

# Spec 001: M1 — EDS thin E2E

> Migrated from `docs/slices/slice-01..06` + `docs/milestones/m1-summary.md`
> on 2026-05-15 via dogfood of jig spec 020 (slice-to-spec).

## Overview

End-to-end EDS path on one URL, one patch shape (`edsBlocks`).
Async-by-default REST contract. CDP-based measurement. CWV oracle
+ verdict. Per ADR-013.

## Decomposition

M1's six slices grouped by `Milestone: M1` per the original
slice frontmatter prose. Each slice retains its original filename
(unchanged), heading numbering re-shaped to `## Slice 001-NN — <slug>`
to match jig's spec-slice fragment convention.

## Slices

- [001-01 — service-skeleton-async-endpoints](slice-01-service-skeleton-async-endpoints.md)
- [001-02 — baseline-stability-preflight](slice-02-baseline-stability-preflight.md)
- [001-03 — source-ingestion-eds-tier-0-gates](slice-03-source-ingestion-eds-tier-0-gates.md)
- [001-04 — passthrough-builder-edsblocks](slice-04-passthrough-builder-edsblocks.md)
- [001-05 — cdp-router-puppeteer-measurement](slice-05-cdp-router-puppeteer-measurement.md)
- [001-06 — cwv-oracle-verdict-feedback](slice-06-cwv-oracle-verdict-feedback.md)
```

## Verify

After writing the 7 files (1 spec.md + 6 slice files), confirm jig's
helpers see them correctly:

```text
$ python3 -c "import sys; sys.path.insert(0, 'skills/_common'); \
    from parsing import iter_slices; \
    [print(l.label) for l in iter_slices('docs/specs/001-m1-eds-thin-e2e/spec.md')]"
001-01 — service-skeleton-async-by-default-endpoint-shells
001-02 — baseline-stability-preflight-structural-hash-known-signals
001-03 — source-ingestion-eds-marker-detection-eds-tier-0-gates
001-04 — passthrough-builder-for-edsblocks-patch-shape
001-05 — cdp-fulfilment-router-puppeteer-measurement-runner
001-06 — cwv-oracle-verdict-assembly-evidence-payload-feedback-endpoint

$ python3 scripts/spec_lint.py docs/specs/001-m1-eds-thin-e2e/spec.md
...
✓ No AC contradictions detected.
✓ No AC contradictions detected.
✓ No AC contradictions detected.
✓ No AC contradictions detected.
✓ No AC contradictions detected.
✓ No AC contradictions detected.

$ python3 skills/spec-workflow/workflow.py status-board .
regenerated status board: 6 slice(s) across 1 spec(s)
```

Resulting `docs/specs/README.md` row:

```markdown
| Spec | Slice | Status | Notes |
|------|-------|--------|-------|
| [001-m1-eds-thin-e2e](001-m1-eds-thin-e2e/spec.md) | 001-01 — service-skeleton-async-by-default-endpoint-shells | **DONE** |  |
| [001-m1-eds-thin-e2e](001-m1-eds-thin-e2e/spec.md) | 001-02 — baseline-stability-preflight-structural-hash-known-signals | **DONE** |  |
...
```

## Transition round-trip

To confirm the write-side of `workflow.py transition` lands in the
slice file (not spec.md):

```text
$ python3 skills/spec-workflow/workflow.py transition \
    docs/specs/001-m1-eds-thin-e2e/spec.md 001-01 IN_PROGRESS
transitioned 001-01 — service-skeleton-async-by-default-endpoint-shells: DONE → IN_PROGRESS

$ head -6 docs/specs/001-m1-eds-thin-e2e/slice-01-service-skeleton-async-endpoints.md
---
status: IN_PROGRESS
dependencies: []
last_verified:
---
```

Frontmatter updates correctly. Round-trip back to `DONE` for cleanup.

## What was NOT done

- **Original `docs/slices/slice-01..06-*.md` files NOT deleted.** They
  stay as the historical source. Caller decides when to remove
  them and rewrite the dangling `CLAUDE.md` / milestone summary
  cross-references.
- **`dependencies:` left empty.** The original "Depends on" prose
  (e.g. "ADR-004, ADR-014, ADR-006, ADR-005, ADR-017") was not
  parsed into structured frontmatter. Per-slice work for the
  caller if they want validated dependency gates on DONE
  transitions.
- **No `### Deviation log` synthesized.** Pre-jig slices never had
  one. `land.py prepare --no-deviation-log` (spec 019-01) is the
  enabler for landing them retroactively.

## Total cost

- 6 slice files transformed
- 1 spec.md synthesized
- 1 status-board regen
- Roughly 5 minutes of mechanical work + judgment calls

Pattern is repeatable for each remaining milestone (M2..M5.7 in
shallow-validator's case, 40 more slices).
