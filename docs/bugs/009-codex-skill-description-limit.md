---
status: DONE
tier: standard
severity: medium
claimed_by: detached
regression_test: python3 -m unittest scripts.test_install_contract.PresenceHelperTests scripts.test_install_contract.RealRepoContractTests
main_repro_checked_at: 2026-07-14
main_repro_ref: origin/main@2a5497fda331
main_repro_result: reproduces
red_confirmed_at: 2026-07-14
green_confirmed_at: 2026-07-14
fix_class: guardrail
security_surface: false
escalated_to:
---

# Bug 009: codex-skill-description-limit

## Symptom

Codex skips six jig skills at startup because each `description` in its
generated `SKILL.md` exceeds Codex's 1024-character limit. The skipped skills
are `explain`, `contracts`, `reframe`, `migrate`, `security-review`, and
`bug-fix`.

## Repro

Run the install-contract validation over the repository's public skills. It
currently reports no problems even though the six folded descriptions decode
to 1157–1800 characters and Codex rejects the generated package.

## Evidence

- The canonical source descriptions decode to these lengths: `explain` 1509,
  `contracts` 1157, `reframe` 1800, `migrate` 1278, `security-review` 1075,
  and `bug-fix` 1237 characters.
- Those are the only six public skills above 1024 characters, matching the
  user's six Codex warnings exactly.
- `scripts/install_contract.py::skill_contract_problems` validates only the
  exact public skill set; it never parses or bounds `description`.
- `scripts/codex_install_smoke.py::_validate_generated_package` delegates its
  skill validation to that incomplete helper, so the bad generated package
  passes jig's smoke test.
- Codex 0.133.0 sanitizes descriptions with
  `split_whitespace().join(" ")` before enforcing its 1024-character limit
  (`codex-rs/core-skills/src/loader.rs`), so jig's guard must measure that
  normalized value rather than raw YAML block-scalar whitespace.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: The Codex cache corrupted or duplicated otherwise-valid
  descriptions. Falsified because the canonical source files have the same
  six over-limit descriptions, and no other public skill exceeds the limit.
- [x] H2 (leading): Description prose grew beyond Codex's host limit while
  jig's install contract validated only skill presence. Confirmed by the
  exact source-length/warning match and the absence of any description-length
  check in `skill_contract_problems`.

## Root cause

Jig treats a public skill's existence as sufficient package validity. Its
canonical descriptions accumulated routing triggers, deferral language, and
negative routing guidance without a machine-enforced Codex size budget. The
Codex builder copied those source frontmatters unchanged, and the Codex smoke
test reused the presence-only contract, allowing an install artifact Codex
then refused to load.

## Fix class

guardrail

## Fix

- Shortened the six canonical descriptions while preserving their required
  trigger, deferral, and negative-routing contracts.
- Extended `skill_contract_problems` to parse and Codex-sanitize every public
  skill description, then reject normalized values over 1024 characters with
  an actionable path/observed-length diagnostic.
- Added 1024/1025 boundary coverage, including folded YAML and whitespace that
  must be normalized exactly like Codex.
- Regenerated the committed Claude and Codex host packages.

## Already tried

## Regression test

`python3 -m unittest scripts.test_install_contract.PresenceHelperTests scripts.test_install_contract.RealRepoContractTests`

## Proof

- Red: the focused contract suite failed because a 1025-character description
  produced no validation problem.
- Green: 458 focused contract, packaging, routing, and affected skill-surface
  tests pass; Pyright reports zero errors/warnings; the host-package drift
  check reports the committed packages are in sync.
- The final Codex package contract reports no problems. The six affected
  sanitized descriptions are 625–806 characters, safely below the limit.
- Independent bug-review and craft-review passes both returned `pass` with no
  blockers or nits after the final Codex-sanitization correction.

## Learning

Package validation must enforce host limits on the same normalized value the
host sees. For Codex skill descriptions, that means YAML extraction followed
by single-line whitespace sanitization before the 1024-character check; source
length or YAML chomping semantics alone are not the contract.

## Main recheck

- 2026-07-14 - `origin/main@2a5497fda331` -> reproduces: git show origin/main:skills/{explain,contracts,reframe,migrate,security-review,bug-fix}/SKILL.md; decoded lengths 1509,1157,1800,1278,1075,1237 (>1024)
