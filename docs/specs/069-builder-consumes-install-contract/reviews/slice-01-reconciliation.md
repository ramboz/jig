---
slice: 069-01 — builder-consumes-install-contract
pass: reconciliation
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-06-11T20:28:01Z
prompt_source: review.py reconciliation docs/specs/069-builder-consumes-install-contract/spec.md 069-01
---

VERDICT: pass

REASONING:
All six deviation-log claims match the code on disk. The builder (`build_release_zip.py`) defines none of its former include/exclude constants and consumes `install_contract.iter_release_files` via the same non-circular `sys.path.insert` + `import install_contract` pattern `verify_install` uses; the enumerator applies the single `is_excluded_release_path` predicate; the stale `scaffold.py` comment now points at `install_contract.RELEASE_INCLUDE_SCRIPT_FILES`; the redundant guard is gone; historical references in closed records are preserved per ADR-0010; and no ADR/conventions/refinement-todo files were touched. The artifact-equality numbers (91 entries, 89 byte-identical) aren't statically re-runnable, but the supporting reasoning is sound and honestly scoped — `install_contract.py` is genuinely in the runtime-scripts allowlist, so its shipped bytes necessarily change. The deviation log is honest, complete, and appropriately scoped.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- Deviation #4 abbreviates the removed builder constants to `_EXCLUDE_*`; the spec names them explicitly (`_EXCLUDE_DIR_NAMES` / `_EXCLUDE_FILE_SUFFIXES` / `_EXCLUDE_FILE_NAMES`). The abbreviation is faithful — the builder verifiably retains none — so this is a wording note, not a discrepancy.
- Deviation #1's 91/89-entry figures are asserted, not reconstructable from the static tree (they depend on a pre-refactor HEAD build + the golden digest `218f39fb…`); the logical guarantee (identical entry set / order / mtime; every non-edited file byte-identical) holds given `install_contract.py` ships inside the zip. Recording for the trail.
- Principles + engineering-practices checks clean: single-source consolidation reduces duplication, scope held to the four named deliverables plus the one justified collateral comment fix, ADR correctly judged unnecessary (borrows servo's single-source principle, not its JSON format), nothing parked.
