---
status: READY_FOR_IMPLEMENTATION
dependencies: [adr-0049, 104-01]
last_verified:
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 104-02 — authoring-nudge

**Goal:** Prevent the design-fidelity gap at authoring time: when a slice has
visual design, `spec-workflow` nudges the author to extract the design values
into checkable ACs and — when fidelity must gate — flag `design_review` and wire
a servo `design-eval`, so "doesn't match the mockup" has an agreed contract to
diff against instead of living only in a picture (ADR-0049; issue #179 option 2).

**DoR:**
- ✅ Slice 104-01 done — the triage rule + ADR-0049 vocabulary are in place, so
  the authoring nudge points at a settled route.
- ✅ Rails verified: spec 071's `design_review` pass is DONE and the deriver
  `slice_needs_design_review` reads the flag (`skills/spec-workflow/workflow.py:330`);
  the slice template already carries a `design_review:` comment
  (`templates/docs/specs/slice-template.md`); servo `design-eval` exists.

**Acceptance Criteria:**

1. **The spec-authoring flow carries a design-fidelity nudge.** `spec-workflow`'s
   "Creating a new spec" flow (`skills/spec-workflow/SKILL.md`) gains a step (or
   sub-step) directing that, when a slice has visual design, the author (a)
   extract the design values (colours, spacing, sizes, layout rules) into
   checkable ACs, and (b) when fidelity must **gate**, set `design_review: true`
   and wire a servo `design-eval` as the done-condition, citing spec 071 +
   ADR-0049. Observable: the step text and both pointers are present on the
   authoring hot-path (the numbered creating-a-new-spec flow), not a footnote.
2. **The guidance is graduated, not mandatory.** The nudge states the two tiers
   explicitly: low-stakes visual polish → design-values-in-ACs + attest-by-eyeball
   (no servo required); a hard fidelity gate → servo `design-eval` +
   `design_review`. Observable: both tiers named, and that jig "offers, never
   forces" servo.
3. **The slice template makes the prompt visible at the point of use.** The
   `design_review:` comment in `templates/docs/specs/slice-template.md` is
   enriched to name the authoring action (extract design values into ACs; wire a
   servo `design-eval`) — not just "set true when …". Observable: the template
   comment references extracting design values / the servo rail.
4. **Teeth stay anchored to the existing `design_review` flag — no new
   mechanical gate or auto-detector is introduced.** No new frontmatter flag,
   deriver, or keyword detector for "has visual design" is added
   (`workflow.py`'s derived-flag set is unchanged); the nudge is authoring
   guidance whose enforcement point remains the existing `design_review` pass
   (ADR-0049 non-goal). Observable: `workflow.py` gains no new flag deriver;
   `slice_needs_design_review` is unchanged.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) — `scripts/run_tests.py`.
- [ ] A test asserts the authoring nudge (design-values-into-ACs + the
      `design_review`/servo rail + the graduated tiers) is present in
      `spec-workflow` SKILL.md, and fails when the nudge text is removed.
- [ ] A test asserts the enriched slice-template comment references the authoring
      action (AC3), and confirms AC4 — no new flag deriver was added to
      `workflow.py`.
- [ ] `uvx ruff check` clean on changed files; `spec_lint.py` clean on spec 104;
      any skill/template content manifest re-synced if one covers these files.
- [ ] Reviewed by `reviewer` subagent (compliance) + `pr-review` (craft).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
