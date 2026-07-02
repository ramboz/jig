---
slice: 067-02 — Retrofit spec drafts
pass: craft
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-07-02T17:06:16Z
prompt_source: review.py craft docs/specs/067-reframe/spec.md 067-02 <deliverables>
---

VERDICT: pass

REASONING:
067-02 extends the judgment-only reframe SKILL.md with a well-structured "Retrofit spec
drafts" section faithfully implementing all four ACs. The documented `workflow.py new <slug>`
matches the real CLI; prose is consistent with spec/ADR-0024; surface tests follow the
established sibling pattern. Craft is solid; only nits, no blockers.

SPECIFIC ISSUES:
- [strength] The retrofit section is exemplary: numbered flow (reserve → goal → anchor →
  close-the-loop), an explicit `deferred — <why>` escape hatch, and the "link each retrofit
  row to its drafted spec number" mapping reusing the coverage floor's "omissions must be
  visible" ethos; mirrors the keystone-ADR flow so spawned specs inherit gates for free.
- [strength] Cross-references are internally consistent (disposition row, retrofit section,
  Relationship-to-other-skills spec-workflow bullet all point at the same workflow.py new flow).
- [nit] test file docstring header reads "(slice 067-01)" and its AC index enumerates only
  067-01's ACs; not updated to note it now also pins 067-02's surface.
- [nit] test_goal_anchored_on_reference asserts only "in line with"; AC2 requires the full
  "bring <artifact/code> in line with <reference>" framing — strengthen to pin "bring" + the
  reference framing so it can't pass on unrelated prose.
- [nit] the `workflow.py new` example slug `retrofit-<artifact>-onto-<reference-slug>` is a
  template; workflow.py rejects `--` / non-[a-z0-9-]. Add a one-line slugify reminder.

RECONCILIATION NOTES:
- All three nits are cheap reconciliation folds (docstring, stronger AC2 assertion, slugify
  reminder), not scope deviations. SKILL.md prose already carries the full AC2 wording.
