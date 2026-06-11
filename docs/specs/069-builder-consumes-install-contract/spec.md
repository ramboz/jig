---
status: DRAFT
skill: release-pipeline
tier: release infrastructure
adr_required: false
---

# Spec 069: Builder consumes the install contract

## Overview

jig's release-zip *builder* and its install *contract* describe the same
thing twice. `scripts/install_contract.py` (spec 047) is the
validator-facing single source of truth for what a valid plugin/release
install contains — including which paths must never leak into a release
zip. But `scripts/build_release_zip.py` still hardcodes its own
include/exclude rules as module-level constants (`_INCLUDE_ROOTS`,
`_INCLUDE_FILES`, `_INCLUDE_SCRIPT_FILES`, `_EXCLUDE_DIR_NAMES`,
`_EXCLUDE_FILE_SUFFIXES`, `_EXCLUDE_FILE_NAMES`), and a consistency test
(`test_exclusion_predicate_matches_build_release_zip`) pins the two equal.

So drift is *prevented* but the duplication is *real*: the build-time list
and the verify-time contract are two definitions kept in lockstep by a
test. Slice 047-01's deviation log recorded consolidating them as a cosmetic
cleanup and deliberately left it. This spec does that consolidation now, to
converge on the single-source pattern servo adopted — one
`.claude-plugin/install-contract.json` consumed by builder, verifier, and
scaffolder alike — while **keeping jig's Python-as-data contract** (with its
pure helpers and rationale comments), not servo's JSON form.

This is the jig-side half of a 2026-06-11 servo↔jig release/CI alignment
review. The servo side is servo specs 009–010; servo's data-driven contract
is the reference pattern this spec borrows the *principle* from.

## Goals

1. **One source for the release-zip file set.** `install_contract.py`
   becomes the single declarative owner of the release include roots/files
   and the exclude rules, exposed as data plus a small pure enumerator
   helper in its existing stdlib-only, side-effect-free style.
2. **The builder consumes it.** `build_release_zip.py` derives its
   include/exclude from `install_contract.py` instead of its own constants;
   no parallel list remains in the builder.
3. **Retire the redundant guard.** The consistency test that pinned the two
   lists equal is removed or repurposed — there is nothing left to keep in
   sync; real behavior stays covered by the build + smoke tests.
4. **No change to the artifact.** The built zip is the identical set of
   entries as before, with deterministic mtime / order / contents
   preserved. This is a refactor, not a packaging change.

## Non-goals

- **No JSON externalization.** jig's contract is Python-as-data on purpose
  (it carries pure `(ok, [diagnostics])` helpers and rationale comments a
  flat JSON array cannot). Convergence with servo is on the *principle*
  (single source consumed by builder + verifier), not the *format*. Do not
  convert `install_contract.py` into a JSON file.
- **No change to what ships.** The include/exclude *content* is unchanged;
  only its single home moves. Deliberate oddities (e.g. the three runtime
  `scripts/*.py` modules that ship despite `scripts/` being excluded) stay,
  with their rationale comments carried onto the contract.
- **No verifier contract change.** `verify_install.py` and
  `validate_manifests.py` already read `install_contract.py`; their behavior
  is untouched.
- **No release-flow change.** `.github/workflows/release.yml` and the smoke
  test are unaffected.

## Current state verified 2026-06-11

- `scripts/install_contract.py` (047-01) owns expected skills/agents,
  hook-entry shape, manifest validators, and the exclusion surface —
  `_EXCLUDED_DIR_NAMES` (line 325) + `is_excluded_release_path`.
- `scripts/build_release_zip.py` hardcodes `_INCLUDE_ROOTS`,
  `_INCLUDE_FILES`, `_INCLUDE_SCRIPT_FILES`, `_EXCLUDE_DIR_NAMES`,
  `_EXCLUDE_FILE_SUFFIXES`, `_EXCLUDE_FILE_NAMES` and walks them directly.
- `scripts/test_install_contract.py::test_exclusion_predicate_matches_build_release_zip`
  asserts `install_contract._EXCLUDED_DIR_NAMES ==
  build_release_zip._EXCLUDE_DIR_NAMES` — the guard this spec makes
  unnecessary.
- 047-01's deviation log (craft-nit #2) records the consolidation as a
  deferred cosmetic cleanup.

## Decomposition

**Suggested SPIDR axis: Interface.** The change is to the boundary between
the contract module and the builder — move the include/exclude definition
behind one interface and have the builder call it.

### Slices

1. **`069-01 builder-consumes-install-contract`** — Extend
   `install_contract.py` to own the release include roots/files + exclude
   rules as data with a builder-facing enumerator; refactor
   `build_release_zip.py` to consume it and drop its own constants; retire
   the now-redundant consistency test; prove the built zip is unchanged.

## Dependencies / coordination

- Builds on spec 047 (install-contract verification), which is DONE.
- Coordinate with spec 035's fixture-exclusion rules if that work is in
  flight — the exclusion set is exactly what this spec re-homes.
- Origin: 2026-06-11 servo↔jig release/CI alignment review (servo specs
  009–010 are the servo-side half).

## References

- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
- [scripts/install_contract.py](../../../scripts/install_contract.py)
- [scripts/test_build_release_zip.py](../../../scripts/test_build_release_zip.py)
- [scripts/test_install_contract.py](../../../scripts/test_install_contract.py)
- [Spec 047 — install-contract-verification](../047-install-contract-verification/spec.md)
