---
slice: 088-02 — the `/jig:orient` judgment skill
pass: compliance
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-12T04:24:43Z
prompt_source: review.py implementation docs/specs/088-project-orientation/spec.md 088-02
---

Independent compliance review of slice 088-02 (the `/jig:orient` judgment skill) against its seven acceptance criteria.

**Verdict: pass.** All seven ACs are met on the static evidence:

- **AC1 (name / no compass):** ships as `skills/orient/SKILL.md` as `/jig:orient`; no `compass` metaphor in the plugin skill or either host package (historical references in adr-0045 / bug 014 are documentary and out of AC1 scope).
- **AC2 (layered, not re-derived):** SKILL.md starts from the `workflow.py orient` `jig hint:` line and layers judgment on top; no second lifecycle-focus algorithm.
- **AC3 (trigger boundary):** `evals/cases/orient.json` encodes positive project-level cases + negative route-away cases (bare "what's next?" → tdd-loop / spec-workflow).
- **AC4 (zero-write):** SKILL.md states the skill writes no file (no docs/, no .jig/ cache, no history log).
- **AC5 (correct handoffs):** "implement a ready slice" routes through `jig:spec-workflow`; names that there is no invocable `jig:implementer`.
- **AC6 (Tier-1 registration):** present in `scaffold._TIER_SKILLS`, both `scaffold_contract.py` copies, `install_contract.py`, `TierSkillSetTests.EXPECTED_TIER_1`, and product prose (13 Tier 1 / 20 total). Verified independently green.
- **AC7 (suite/routing):** not runnable read-only; orchestrator confirmed the 14 surface tests pass and registration is intact out-of-band.

**Medium findings (non-blocking — reconciliation items):**
1. `skills/orient/test_orient_skill_surface.py` — AC4 (zero-write) and AC5 (handoff) are pinned by no test; a future edit deleting the "Orient writes nothing" section or the `jig:spec-workflow` handoff would fail nothing. Two surface assertions would close the gap.
2. `CLAUDE.md:13` / `AGENTS.md:13` — residual `compass` mention in the active-specs hot-cache line ("adopting contributed `compass`"); not an AC1 violation (scoped to plugin/host-packages) but should be compressed on close-out per the spec-025 convention.

Reviewer: jig:reviewer (read-only, context-isolated). Prompt source: review.py implementation docs/specs/088-project-orientation/spec.md 088-02.
