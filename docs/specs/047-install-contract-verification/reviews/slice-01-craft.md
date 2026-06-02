---
slice: 047-01 - plugin-release-contract-validator
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-02T18:29:50Z
prompt_source: skills/independent-review/review.py pr-review 047-01
---

VERDICT: pass

REASONING:
This is a well-shaped, stdlib-only contract module with pure `(ok, [diagnostics])` helpers, genuinely actionable diagnostics, and a thoughtful "restate-plus-consistency-test" pattern that pins every duplicated constant (`EXPECTED_SKILLS`, `REQUIRED_AGENTS`, `_EXPECTED_HOOK_SCRIPTS`, exclusion predicate) against its real source of truth so the contract cannot silently drift. Tests exercise behavior (not just line coverage), cover each AC's failure mode with a named-diagnostic assertion, and integrate against both synthetic fixtures and the live repo. No blockers and no correctness/security concerns — the path-traversal handling in the marketplace source validator is the security-relevant surface and it is conservative and correct. Only minor polish nits remain.

SPECIFIC ISSUES:
- [strength] `scripts/install_contract.py:44-70` — "restate here, pin equal in the test" convention applied consistently and documented inline at every duplication point. Right call given the stdlib-only constraint forbidding a `scaffold.py` import; consistency tests make the duplication safe rather than fragile.
- [strength] `scripts/install_contract.py:221-264` — `_validate_source_path` handles real-world `source` polymorphism (bare string vs `git-subdir` object), rejects absolute and `..`-escaping paths, tolerates the legitimate object-without-path case, and uses `Path(path).parts` membership rather than a brittle substring check.
- [strength] `scripts/install_contract.py:97-117` / `143-184` — `_iter_hook_commands` / `validate_hooks` tolerate malformed `hooks.json` substructures (diagnostic instead of `KeyError`). The drift-fix angle is exactly the bug class this spec set out to prevent; `test_verify_install.py:367-375` locks it.
- [nit] `scripts/install_contract.py:178` — `is_excluded_release_path` excludes `.pytest_cache`/`.mypy_cache`, but the consistency test (`test_install_contract.py:69-88`) only asserts agreement with `build_release_zip` for `fixtures`/`__pycache__`. Extend the loop to the full excluded-dir set.
- [nit] `scripts/install_contract.py:143-159` — `validate_hooks` re-checks the `hooks` shape already guarded inside `_iter_hook_commands`. Defensible (early-return-with-diagnostic) but slightly redundant.
- [nit] `scripts/install_contract.py:331-348` — exclusion predicate re-implemented vs `build_release_zip._is_excluded_file`; could be a shared import (both under `scripts/`). Consistency test makes the current dup safe — optional cleanup.
- [nit] `scripts/test_install_contract.py:48-49` — test mutates `sys.path` without restoring it. Harmless but a `try/finally` would be tidier.

RECONCILIATION NOTES:
No blockers; craft-ready for REVIEWED. Nits to log (none blocking): (1) extend the exclusion consistency test to assert agreement on `.pytest_cache`/`.mypy_cache`; (2) consider a single shared `test_*.py`/`.pyc`/`.DS_Store` predicate between `install_contract` and `build_release_zip` (optional); (3) restore `sys.path` in `test_expected_skills_matches_tier_skills_union`. Strength worth repeating: the "restate constant + pin-equal consistency test" pattern is a clean answer to the stdlib-only/no-cross-import constraint.

— reviewer: jig:reviewer (read-only, fresh context); craft pass via file-read dispatch to ~/.claude/skills/pr-review/SKILL.md.
