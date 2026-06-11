---
slice: 069-01 — builder-consumes-install-contract
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review rubric)
reviewed_at: 2026-06-11T20:22:33Z
prompt_source: review.py pr-review docs/specs/069-builder-consumes-install-contract/spec.md 069-01 <4 deliverables>
---

VERDICT: pass

REASONING:
A clean, well-executed Interface-axis refactor. The new `iter_release_files` enumerator is a faithful behavioral equivalent of the old walk: same include roots recursed, the single `is_excluded_release_path` predicate applied (already covering dir-names, `test_*.py`, `*.pyc`, `.DS_Store`), then present top-level files and the runtime-scripts allowlist appended — with `sorted(...)` still owned by the builder so deterministic order/mtime/bytes are preserved. The cross-module import mirrors the established `verify_install.py` pattern exactly, is non-circular, and the retired guard's coverage is genuinely redundant — there is no second list to pin, and the surviving build/smoke/enumerator tests assert the real behavior. Test quality is high (behavior-named, regression-guarding, isolated).

SPECIFIC ISSUES:
- [nit] skills/scaffold-init/scaffold.py:1594 — Stale cross-reference: comment cites `build_release_zip.py::_INCLUDE_SCRIPT_FILES`, which this slice removed; allowlist now at `install_contract.RELEASE_INCLUDE_SCRIPT_FILES`. Outside the four deliverable files, but the refactor created the dangling reference. Update the pointer.
- [strength] scripts/install_contract.py:413-447 — `iter_release_files` is a textbook consolidation: single exclusion predicate reused for the walk, `is_dir()` skip + `relative_to` + `as_posix()` keeps yields POSIX-relative and stdlib-pure, `is_file()` guards preserve the old "yield only present optional/script files" behavior. Docstring states purity + contract.
- [strength] scripts/build_release_zip.py:32-42 — Import block explains *why* the `sys.path.insert` is needed and matches the sibling `verify_install.py` convention rather than inventing a new one.
- [strength] scripts/test_build_release_zip.py:160-178 — `test_runtime_scripts_only` is the load-bearing regression guard that makes retiring the old consistency test safe (pins `scripts/` entries == exactly the allowlist).
- [strength] scripts/test_install_contract.py:111-122 — `test_iter_release_files_is_pure` asserts the disk is byte-for-byte unchanged before/after enumeration — directly defends the side-effect-free claim.

RECONCILIATION NOTES:
- Correct the stale scaffold.py:1594 comment inline (live operational prose / code comment — ADR-0010 says fix inline with git history as the audit trail). [nit], not a blocker.
- Confirm the before/after namelist (ideally byte) equality evidence lands in the deviation log per DoD item 2.
