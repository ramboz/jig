---
slice: 095-01 — claude-scaffold-templates
pass: reconciliation
verdict: pass
reviewer: jig:reviewer (fresh context)
reviewed_at: 2026-07-17T06:21:26Z
prompt_source: review.py reconciliation
---

PASS WITH FINDINGS on first read; all findings actioned, re-verified below.

What it confirmed by spot-checking the claims easiest to overstate: all three
`copy-machinery` contract surfaces genuinely name templates; bug 012 is amended,
not rewritten (its `## Remaining risk` preserved verbatim, ADR-0010); §7's
load-bearing test-reach claim is true at source (`load_tests` returns an empty
suite below 3.11, and it is defined *after* `unittest.main()`, so the direct-run
verification really does bypass it); the three inbox entries describe real work;
the §9↔§7 self-indictment is accurate and against interest; the recorded verdicts
are evidence rather than self-congratulation.

Findings, all fixed:
- **ADR/index/todo three-way disagreement.** Read mid-flight: `status: Proposed`
  vs an index saying Accepted vs a struck-through refinement-todo entry that
  `resolve-todo` refuses for a non-Accepted ADR. The reviewer's diagnosis was
  exact — reverting the hand-stamped status did not undo what it had enabled, and
  §7b narrated the intended order as if it had run. Now actually run:
  frame-critique passed (round 4) → verdict recorded → `adr.py accept` → `adr.py
  index`. Recorded as §7c, including that the index does not self-heal by
  mechanism.
- **Stale "four helpers" on three surfaces** (`refinement-todo.md`,
  `architecture.md`, and the *Codex render* of the migrate contract) after
  compliance established five — the source→render drift class §8 exists to fix,
  reintroduced one level down. Swept; recorded as §7d.
- **`test_workflow.py`'s `SelfDefiningReminderInRenderersTests`** documented "a
  scaffolded project, where `slice-template.md` is NOT copied" as its rationale —
  a premise this slice falsified, unaccounted for by any record. Re-premised; the
  invariant it pins is unchanged and still earns its place.
- **`hosts/` mirrors** carried pre-fix ordinals (canonical edit landed after the
  last rebuild). Rebuilt; drift guard green in isolation.
- **"[x] Reconciliation review passed" was ticked before any verdict existed.**
  Fair catch, and the only finding about the records claiming something untrue
  about themselves. This file is that verdict.
