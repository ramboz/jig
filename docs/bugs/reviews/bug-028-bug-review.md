---
bug: 028
pass: bug-review
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-02T07:48:27Z
prompt_source: review.py bug-review docs/bugs/028-scaffold-gitignore-runtime-state.md skills/scaffold-init/scaffold.py skills/scaffold-init/test_scaffold.py (+2 reconciliation re-confirms)
---

Bug-review pass — VERDICT: pass (re-confirmed after two reconciliation rounds).

The source fix addresses the documented root cause (missing propagation of jig's
runtime-state ignore list into the scaffolder) narrowly and honestly: a second
marker-delimited managed block reusing the existing idempotent
`_upsert_marked_block`, written on all three paths (`copy_codex_machinery`,
`copy_machinery`, `scaffold()` --plugin-only), keeping `.jig/` file-scoped and
not duplicating the secret-block semantic-index/servo-hint entries. The named
regression test is red-before/green-after, with companion tests covering
plugin-only, marker-delimiting, non-duplication, idempotency, and
pre-existing-line preservation.

Reconciliation rounds resolved before this verdict:
1. Shipped host packages were stale — regenerated via
   `scripts/build_host_packages.py`, drift `--check` clean.
2. Live prose (ADR-0041 105/257, status board README.md:230) referenced the
   renamed function — corrected inline per ADR-0010; historical closed
   spec/review records left as-is.
3. The full-suite green check caught `test_review_queue_cleanup`: the runtime
   list had blind-copied `.claude/review-queue.json`, a removed-feature (spec
   039) path jig self-ignores only defensively and whose literal is guarded
   against live-code references. Dropped from the runtime list (documented, bare
   filename used in comments/tests); the list is now "jig's runtime state minus
   the dead-feature path" — more faithful to intent than a blind copy.
