---
status: DONE
tier: standard
severity: low
claimed_by: codex/issue-89-skill-contract
regression_test: scripts/test_verify_install.py::PluginModeSkillContractTests::test_unregistered_public_skill_fails_and_is_named
main_repro_checked_at: 2026-07-13
main_repro_ref: origin/main@a247f76a17804f702cdb9963b59bcb51774de7f7
main_repro_result: reproduces
red_confirmed_at: 2026-07-13
green_confirmed_at:
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 007: unregistered-plugin-skill-contract

## Symptom

The plugin/release install contract accepts a public `skills/<name>/SKILL.md`
directory that is absent from the authoritative `_TIER_SKILLS` table. Plugin
packaging ships that skill, while tier-gated scaffold copying skips it.

## Repro

Seed a complete temporary plugin root with every `EXPECTED_SKILLS` entry, add
`skills/unregistered/SKILL.md`, and run the install-contract skill validator.
The current validator returns no diagnostics.

## Evidence

- `scripts/install_contract.py:577-590` checks only for missing expected
  skills; it never enumerates unexpected public skill directories.
- `scripts/install_contract.py:538-568` and the host builders recursively
  package the public `skills/` tree.
- `skills/scaffold-init/scaffold.py:729-738` deliberately skips a public skill
  without a `_TIER_SKILLS` mapping during tier-gated copying.
- GitHub issue #89 records the resulting plugin/scaffold contract asymmetry.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: A host manifest or package builder filters skills to the tier-derived
  contract set, which would make the permissive validator harmless. Falsified
  by the recursive `skills/` packaging paths in both host builders.
- [x] H2 (leading): The shared install contract implements subset semantics
  (`EXPECTED_SKILLS ⊆ public skills`) rather than the intended exact-set
  invariant. Confirmed by `missing_skills()`, which only walks
  `EXPECTED_SKILLS` and never enumerates public skill directories.

## Root cause

The validation API was named and implemented as `missing_skills`, reflecting
spec 047's original one-way presence requirement. Later tier reconciliation
made `_TIER_SKILLS` the authoritative inventory, but the plugin contract was
never strengthened to compare the reverse direction. Because package builders
copy the whole `skills/` tree, an unregistered public directory becomes a
plugin-only skill by accident.

## Fix class

Guardrail: replace the one-way presence helper at validation call sites with
an exact public-skill-set validator. Private `_...` infrastructure and
directories without `SKILL.md` remain outside the public skill inventory.

## Fix

Added `install_contract.skill_contract_problems()` as the exact-set validator
for public skill directories. It preserves the existing missing-skill
diagnostics, rejects any additional direct `skills/*/SKILL.md` directory not
registered through the tier-derived contract, and excludes private `_...`
infrastructure. Claude package validation, Codex package smoke validation, and
installed-plugin verification now use the exact validator.

## Already tried

## Regression test

`scripts/test_verify_install.py::PluginModeSkillContractTests::test_unregistered_public_skill_fails_and_is_named`
constructs a complete contract-compliant plugin root, adds one unregistered
public skill, and proves installed-plugin verification rejects it with an
actionable `_TIER_SKILLS` diagnostic. Helper-level tests separately pin the
exact-set rule and the private-infrastructure exclusion.

## Proof

Red confirmed directly with:
`python3 -m unittest scripts.test_verify_install.PluginModeSkillContractTests.test_unregistered_public_skill_fails_and_is_named`
(`check_active_skills_present()` returned `True` on fresh main).

Green evidence:

- 204 focused install-contract, verifier, Codex smoke, Claude package, and
  release-zip tests pass.
- Full repository unit suite: 3,455 tests pass (6 skipped).
- Pyright 1.1.411: 25 files analyzed, 0 errors/warnings/information findings.
- Bug-review and craft-review verdicts: pass.

The `REVIEWED` transition used the deliberate `JIG_BUG_TEST_GATE=0` escape
after the evidence above was recorded. The repository's `.jig/test-command`
runs the full suite plus Pyright; its unit-test leg passed, but sandboxed
`uvx` could not read `~/.cache/uv`. Pyright was therefore rerun separately
outside that filesystem restriction and passed cleanly. No failing test or
type finding was bypassed.

## Learning

When a source tree is auto-packaged but a manifest gates a second install
surface, validating only `expected ⊆ present` creates accidental
surface-specific features. The contract must check the reverse direction too.

## Main recheck

- 2026-07-13 - `origin/main@a247f76a17804f702cdb9963b59bcb51774de7f7` -> reproduces: temporary complete plugin root plus skills/unregistered/SKILL.md; install_contract.missing_skills(root) returned []
