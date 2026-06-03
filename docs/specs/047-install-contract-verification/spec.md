---
status: DONE
skill: release-pipeline, scaffold-init
tier: release infrastructure
adr_required: false
---

# Spec 047: Install contract verification

## Overview

jig's release and install checks currently prove that a package contains
some skills, some agents, some hooks, and a manifest. They do not yet
prove the install contract: every advertised skill is present, hook
entries point at real scripts with the expected invocation shape,
generated settings are coherent, release zip contents exclude test-only
fixtures, and documented command surfaces resolve in the install shape.

That is why a release zip and a scaffolded project can pass verification
while still containing stale commands or shallow manifest errors. This
spec turns verification from "there is something there" into "the
declared contract is internally consistent."

## Goals

1. **Define explicit plugin and scaffold install contracts.** Expected
   skill directories, agent files, hook scripts, settings entries,
   manifest fields, marketplace fields, and excluded paths should be
   stated in one validator-facing place.
2. **Strengthen manifest and hook validation.** `validate_manifests.py`
   and/or `verify_install.py` should catch missing required metadata,
   malformed hook entries, non-existent hook scripts, and bare hook
   command names that violate jig's conventions.
3. **Strengthen release zip smoke tests.** A built zip should be
   extracted and checked against the full contract, not just minimal
   existence counts.
4. **Strengthen scaffold smoke tests.** A scaffolded target should be
   checked against the scaffold contract, including copied skill helper
   closure and settings coherence.
5. **Keep verification fast and stdlib-only.** These checks should run
   in local dev and CI without adding network or package-manager
   dependencies.

## Non-goals

- **No packaging format change.** The release zip shape stays the same
  unless validation reveals a contract violation.
- **No deep semantic review of skill prose.** This spec checks presence,
  links, command paths, metadata, and hook shape. It does not judge
  whether a skill is well-written.
- **No duplicate of spec 046.** Spec 046 fixes known scaffold artifact
  fidelity bugs. This spec adds the contract checks that would catch
  similar bugs next time.

## Current state verified 2026-05-27

- `scripts/verify_install.py` plugin mode checks that at least one skill
  exists, agents exist, hooks exist, and plugin/marketplace manifests
  exist.
- `scripts/validate_manifests.py` only requires minimal `name` metadata
  for plugin and marketplace files.
- `scripts/test_build_release_zip.py` checks that a release zip contains
  at least one skill and at least one hook script.
- The release smoke test extracts the zip and calls the same shallow
  install verifier.

## Decomposition

**Suggested SPIDR axis: Data.** The main missing piece is a crisp data
contract for what a valid install contains.

### Slices

1. **`047-01 plugin-release-contract-validator`** - Define and enforce
   the plugin/release contract for manifest fields, skills, agents,
   hooks, hook commands, and excluded paths.
2. **`047-02 scaffold-contract-validator`** - Define and enforce the
   scaffold contract for copied skills, helper closure, generated
   settings, generated metadata, and local command/link coherence.

## Dependencies / coordination

- Slice 047-02 should run after or alongside spec 046 so validation can
  encode the intended scaffold output rather than the known-broken one.
- Spec 035's fixture-exclusion work is treated as part of the release
  contract once it is present in the checkout.

## References

- [scripts/verify_install.py](../../../scripts/verify_install.py)
- [scripts/validate_manifests.py](../../../scripts/validate_manifests.py)
- [scripts/test_build_release_zip.py](../../../scripts/test_build_release_zip.py)
- [scripts/build_release_zip.py](../../../scripts/build_release_zip.py)
