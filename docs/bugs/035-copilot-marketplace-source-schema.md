---
status: DONE
tier: standard
severity: high
claimed_by: literate-disco
regression_test: scripts
main_repro_checked_at: 2026-09-17
main_repro_ref: origin/main@2d7971cf43449397246ad09589202fd1f305e988
main_repro_result: reproduces
red_confirmed_at:
green_confirmed_at:
fix_class: structural_fix
security_surface: false
escalated_to:
closure_schema: 1
---

# Bug 035: copilot-marketplace-source-schema

## Symptom

`copilot plugin marketplace add ramboz/jig` fails with:

```text
Invalid marketplace.json: plugins.0.source: Invalid input
```

Users must know the direct subdirectory install
`copilot plugin install ramboz/jig:hosts/copilot`, unlike the documented
marketplace-first flows for Claude and Codex.

## Repro

From any directory with Copilot CLI installed:

```bash
copilot plugin marketplace add ramboz/jig
```

The same failure reproduces locally against the repository root:

```bash
copilot plugin marketplace add .
```

## Evidence

Copilot CLI reports that it searches `marketplace.json`,
`.plugin/marketplace.json`, `.github/plugin/marketplace.json`, then
`.claude-plugin/marketplace.json`. This repository had no Copilot-specific
descriptor, so Copilot fell through to Claude's descriptor. That descriptor
uses Claude's `git-subdir` object:

```json
{"source": "git-subdir", "url": "...", "path": "hosts/claude"}
```

Copilot rejects that source dialect. An isolated live probe with
`.github/plugin/marketplace.json` and `"source": "./hosts/copilot"` succeeded
through marketplace add, browse, plugin install, and plugin list.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: Copilot cannot install a plugin from a repository subdirectory via a
  marketplace; falsified by an isolated live probe using the official relative
  string source form (`"./hosts/copilot"`), which installed successfully.
- [x] H2 (leading): Copilot falls through to the existing Claude marketplace
  descriptor and rejects Claude's `git-subdir` source object; confirmed by the
  CLI's manifest search order, the exact `plugins.0.source` validation error,
  and the successful higher-precedence `.github/plugin/marketplace.json`
  probe.

## Root cause

The repository implemented host-specific marketplace descriptors for Claude
(`.claude-plugin/marketplace.json`) and Codex
(`.agents/plugins/marketplace.json`) but omitted Copilot's recognized
`.github/plugin/marketplace.json`. Copilot therefore parsed the Claude
descriptor as a compatibility fallback, but Copilot and Claude accept different
object-source dialects. The README documented only direct Copilot installation,
so the missing marketplace route was neither promised nor contract-tested.
## Repository closure inventory

<!-- Spec 091 / ADR-0037: pre-fix repository closure. Standard & gnarly
     bugs gate ROOT_CAUSED -> FIXING on substantive answers below. This
     is an effort-and-protocol standard, NOT a completeness proof: show
     the search you actually ran. A bare "none found" fails; record
     residual uncertainty as an assumption WITH the protocol behind it,
     applying the same enumeration standard as `## Root cause` (ADR-0052).
     Prefer a configured semantic index; the portable floor is targeted
     search + `git log`/`git blame`. -->

**Equivalent / convergent logic searched:**

Searched all `*marketplace*.json` files and the install-contract, host-package,
install-smoke, and symmetric-install-doc tests for `marketplace`, `source`,
`git-subdir`, and `local`. The complete descriptor set before the fix was
Claude root, Codex root, and Codex packaged; no Copilot descriptor existed.
Checked Copilot CLI help and the official `github/copilot-plugins`
`.github/plugin/marketplace.json` for accepted locations/source shapes.

**Relevant history inspected:**

Read README's three-host install matrix and repository-structure section plus
the merged spec 113 package shape. Spec 113 added direct Copilot subdirectory
installation but did not add a marketplace descriptor or marketplace command.

**Affected call sites:**

- Root host-dispatch metadata: `.github/plugin/marketplace.json` (missing).
- README Copilot install commands and repository-structure descriptor list.
- `scripts/test_symmetric_install_docs.py` host install/descriptor guards.
- Shared `validate_marketplace_manifest` contract plus a Copilot-specific
  wrapper that preserves the shared checks and rejects object source dialects.
- `scripts/validate_manifests.py` CI inventory (extended to route the Copilot
  descriptor through the Copilot-specific validator).

**Reuse decision:**

Reuse the existing generic marketplace validator behind a Copilot-specific
source-shape guard, plus the symmetric install-doc test module. Add a
host-specific descriptor at Copilot's documented higher-precedence path; do not
modify Claude or Codex descriptors or attempt a single cross-host source
object, because their accepted source dialects differ.

## Fix class

structural_fix

## Fix

Added `.github/plugin/marketplace.json` pointing `jig` at the committed
`./hosts/copilot` package with Copilot's accepted relative string source.
Updated README to make marketplace add/install the recommended Copilot flow,
retain the direct subdirectory install as an alternative, and document the
new descriptor in the repository layout.

## Call-site closure

<!-- Spec 091 / ADR-0037: before REVIEWED, account for every site named
     in the inventory above as changed, tested, or intentionally left
     alone. Accounting, not mandatory widening. -->

**Disposition per affected site:**

- `.github/plugin/marketplace.json`: added and validated live.
- README: marketplace-first Copilot commands and direct-install fallback
  documented; repository structure now names all three host descriptors.
- `scripts/test_symmetric_install_docs.py`: added descriptor target and both
  Copilot command guards; updated the structural matrix to cover all five
  supported host/mode command sets.
- `scripts/validate_manifests.py`: added the Copilot descriptor to the standard
  CI inventory using a Copilot-specific source-shape validator;
  `scripts/test_validate_manifests.py` covers valid, missing, and incompatible
  object-source cases.
- Claude/Codex descriptors: intentionally unchanged; each remains selected by
  its own host-specific path and schema.

## Already tried

- Existing direct install `copilot plugin install ramboz/jig:hosts/copilot`
  works but does not satisfy marketplace parity.
- Replacing Codex's root descriptor source was rejected: Copilot does not read
  `.agents/plugins/marketplace.json` locally, and changing it would break
  Codex's schema.

## Regression test

`scripts/test_symmetric_install_docs.py` asserts the Copilot descriptor exists,
contains one `jig` entry with source `./hosts/copilot`, and README carries
`copilot plugin marketplace add ramboz/jig` plus
`copilot plugin install jig@jig`.

## Proof

- Red: the three focused tests failed with one missing-file error and two
  missing-command assertions.
- Green: the same three tests pass.
- `validate_copilot_marketplace_manifest` returns `[]` for the new descriptor
  and rejects Claude's object-source dialect.
- Isolated live Copilot probe against the working tree:
  marketplace add succeeded, browse returned `jig`, install enabled `jig@jig`,
  and plugin list showed v2.15.1 loaded live from `hosts/copilot`.

## Learning

A multi-host repository needs separate marketplace discovery files when hosts
recognize different paths and source dialects. A fallback-compatible manifest
location can make an omitted host descriptor fail as a misleading schema error
rather than as “marketplace not found.”

## Main recheck

- 2026-09-17 - `origin/main@2d7971cf43449397246ad09589202fd1f305e988` -> reproduces: copilot plugin marketplace add ramboz/jig rejects plugins.0.source because origin/main has no .github/plugin/marketplace.json and falls through to Claude's git-subdir source
