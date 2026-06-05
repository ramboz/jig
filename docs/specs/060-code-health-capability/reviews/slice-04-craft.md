---
slice: 060-04 — Duplication: native-first, `npx jscpd` fallback
pass: craft
verdict: pass
reviewer: jig:reviewer (pr-review, re-review after fix)
reviewed_at: 2026-06-05T20:59:54Z
prompt_source: review.py implementation docs/specs/060-code-health-capability/spec.md 060-04 <deliverables> (craft pass, re-review)
---

VERDICT: pass

REASONING:
The temp-dir leak blocker is fully resolved: the runner now owns the temp dir via a `with tempfile.TemporaryDirectory(...)` whose __exit__ guarantees teardown on the subprocess-raises path, the module global _LAST_JSCPD_OUTPUT_DIR is gone, and WorkdirLifecycleTests proves no leak via before/after globbing including the OSError-injected raise case. The uniform-signature change is back-compatible — complexity/prettier ignore the new workdir arg, stay silent when unavailable, and needs_workdir=False makes the runner pass None. The deviation log is now honest about the original false "never leaks" claim and accurately describes the fix and its locking tests.

SCOPE: Craft re-review of the single temp-dir-leak blocker fix in slice 060-04; verified leak resolution + no regression.

NITS:
- health.py:606 — every needs_workdir probe run creates+tears-down a temp dir even when npx is absent (empty-dir churn). Cheap and correctly cleaned; not worth changing.

STRENGTHS:
- Eliminated the module global entirely rather than patching the finally — removes both leak and global-state smell (RAII via TemporaryDirectory).
- _run_one_probe cleanly isolates the per-probe try/except inside the with scope.
- test_workdir_cleaned_when_subprocess_raises reproduces the exact original failure mode and asserts both no-crash and no-leak — a true regression lock.
- Deviation log is candid: records the discarded first design and corrects the false "never leaks" claim.

PRIOR VERDICT: needs-changes (temp-dir leak blocker) — now resolved.
