---
slice: 069-01 — builder-consumes-install-contract
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-11T20:22:32Z
prompt_source: review.py implementation docs/specs/069-builder-consumes-install-contract/spec.md 069-01 <4 deliverables>
---

VERDICT: pass

REASONING:
All five ACs are met. `install_contract.py` now owns the release include roots/files + runtime-scripts allowlist as data plus a pure, side-effect-free `iter_release_files` enumerator with the rationale comments carried over (AC1); `build_release_zip.py` defines no include/exclude lists of its own and builds its entry set from the contract via the same import pattern `verify_install.py` uses (AC2); the redundant `test_exclusion_predicate_matches_build_release_zip` guard is gone with a docstring explaining why (AC3); entry-set stability is exercised by new synthesized-tree tests plus the existing idempotency/fixtures tests, and the orchestrator confirmed byte-identity except the intended `install_contract.py` delta (AC4); no removed builder symbols remain referenced anywhere in `scripts/*.py` (AC5 wiring is consistent). The enumerator preserves exact prior semantics — file-level filtering via `is_excluded_release_path` yields the same set a dir-pruning walk would, the `fixtures/`-at-any-depth rule is the predicate's component check, and the runtime-scripts-only allowlist is the explicit per-file yield. No design-principle violation.

SPECIFIC ISSUES:
- skills/scaffold-init/scaffold.py:1594 — (Medium) Stale code comment references `build_release_zip.py::_INCLUDE_SCRIPT_FILES`, a symbol this slice removed (now `install_contract.RELEASE_INCLUDE_SCRIPT_FILES`). Not a correctness break (it's a comment; the runtime `import verify_install` still works), but points a reader at a non-existent symbol — the cross-module drift this spec exists to eliminate. One-line fix during reconciliation.

RECONCILIATION NOTES:
- The artifact has one intended, logically necessary delta: `scripts/install_contract.py` ships in the runtime trio and now carries the enumerator, so its bytes differ from the pre-refactor build while all other 90 entries (namelist, order, mtime, contents) are byte-identical. Record this in the deviation log as the before/after entry-set equality evidence the DoD requires.
- Historical-record mentions of the old builder symbols (docs/specs/035, 013, 047; docs/memory/learnings.md:387) are closed-record prose governed by ADR-0010 — leave as historical. The live scaffold.py:1594 comment is inline-correctable.
- No ADR expected (`adr_required: false`) and none needed. No new deferred decisions for docs/refinement-todo.md.
