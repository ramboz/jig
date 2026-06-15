---
slice: 073-02 — writer stamps frontmatter status
pass: compliance
verdict: pass
reviewer: general-purpose
reviewed_at: 2026-06-15T18:18:29Z
prompt_source: review.py implementation
---

VERDICT: pass

REASONING:
All six ACs (073-02) are met and backed by meaningful tests. The synchronized-write lock (AC5) is genuinely pinned both by paired frontmatter+prose assertions and structurally — `set_frontmatter_field` is a pure text transform and each of new/accept/supersede performs exactly one `atomic_write_text`, so prose and frontmatter cannot diverge (the ADR-0026 drift vector is closed at the mechanism level). AC6 drives the real 073-01 reader (`_lookup_adr_accepted`) reading from frontmatter, and the reader is left untouched (empty diff). No backfill of legacy ADRs; the template supplies `status: Proposed` so new ADRs inherit it in the single render write.

SPECIFIC ISSUES:
(none)

RECONCILIATION NOTES:
- The 12 full-suite failures are pre-existing and environment-only: Python 3.9.6 here vs. the `zip(strict=True)` (3.10+) used in scripts/verify_install.py, scripts/build_release_zip.py, and skills/scaffold-init/test_scaffold_mode.py. None of those files are touched by this slice and neither adr.py nor test_adr.py uses `zip(strict=)`. The slice suite (test_adr.py, 131 tests) is green.
- The implementer deliberately did NOT re-stamp status in `_render_adr_content` (unlike frame_review), instead inheriting `status: Proposed` from the template frontmatter — keeps new's status in the same single write; documented at adr.py:140-143.
- docs/conventions.md:67 references the frontmatter status/dependencies/last_verified template contract; the template now satisfies it (test_template_frontmatter_carries_status_proposed guards against drift). No conventions edit needed.

Reviewer: general-purpose subagent running the review.py `implementation` (compliance) prompt. Independent context.
