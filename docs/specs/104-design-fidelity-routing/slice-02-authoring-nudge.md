---
status: DONE
dependencies: [adr-0049, 104-01]
last_verified: 2026-08-03
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
- [x] All ACs pass; full test suite green (no regressions) — `scripts/run_tests.py`
      (`Ran 3996 tests … OK (skipped=7)`, pyright clean).
- [x] A test asserts the authoring nudge (design-values-into-ACs + the
      `design_review`/servo rail + the graduated tiers) is present in
      `spec-workflow` SKILL.md, and fails when the nudge text is removed.
- [x] A test asserts the enriched slice-template comment references the authoring
      action (AC3), and confirms AC4 — no new flag deriver was added to
      `workflow.py`.
- [x] `uvx ruff check` clean on changed files; `spec_lint.py` clean on spec 104;
      host packages regenerated (`hosts/**/spec-workflow/SKILL.md` + slice-template mirrors).
- [x] Reviewed by `reviewer` subagent (compliance) + `pr-review` (craft).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred (n/a — none deferred).

### Deviation log (after reconciliation)

Original ACs preserved above; this records what changed during implementation
and why.

- **Placement as sub-step `5a`.** The nudge was inserted as step `5a` in the
  "Creating a new spec" numbered flow (between slice-authoring step 5 and
  grounding step 6), matching the existing `1a`/`2a` house style — rather than
  renumbering the whole flow. It carries an explicit "adds no new mechanism —
  teeth stay anchored to the existing `design_review` flag" disclaimer so the
  guidance doesn't over-claim enforcement (AC4).
- **Craft nits (non-blocking; recorded, not fixed this slice).** The craft pass
  returned `pass` with three `[nit][impl]` items, all on the AC4 guard test's
  robustness, none affecting behavior: (1) `test_no_visual_design_keyword_detector_added`
  matches only function names containing `visual`/`fidelity`, so a
  differently-named detector (`slice_has_mockup`) could slip past — and, to be
  precise, `test_review_flag_deriver_set_unchanged` would *not* catch that name
  either (it pins only the `slice_needs_*_review` set, so it catches a fourth
  `*_review` deriver, not an arbitrarily-named detector); (2) the exact
  single-line signature assertion for `slice_needs_design_review` is brittle to
  a future reflow; (3) some asserts couple to verbatim phrasing (the repo's
  established surface-test style). Left as-is — AC4's real teeth are that no new
  derived flag/gate is added and `workflow.py` logic is untouched (both
  verified); the name-regex test is a narrow heuristic on top, not a complete
  guard, and the rest is proportionate to jig's existing surface-test convention.
- **Host packages regenerated.** SKILL.md + slice-template changes were mirrored
  into `hosts/claude` + `hosts/codex` via `scripts/build_host_packages.py` (the
  committed host tree is drift-checked in CI).

### Reconciliation sweep

Drift-prone surfaces checked (`updated` / `no-op` / `deferred`):

- **`hosts/claude` + `hosts/codex` skill/template mirrors — `updated`.**
  Regenerated from source; the committed-package drift check passes
  (`test_build_codex_committed_package.py`, `test_claude_install_smoke.py`).
- **`docs/workflow.md` "Post-implementation review" / spec-authoring prose —
  `no-op`.** The nudge lives in the `spec-workflow` SKILL flow (the authoring
  hot-path); workflow.md's routing rule already gained its design-fidelity
  pointer in slice 104-01. No second home needed.
- **Scaffold seed slice templates (`templates/docs/specs/seed/…`) — `no-op`.**
  Those are worked-example slices, not the generic slice template; they carry no
  `design_review:` comment to enrich. Only the generic
  `templates/docs/specs/slice-template.md` is the authoring surface (updated).
- **`CLAUDE.md` primer — `no-op` (kept lean, spec 055/057).** 104 is a small
  routing ruling closed in-session; it was never in Active-specs, so there is
  nothing to compress. The ruling's homes are ADR-0049 + the bug-fix/spec-workflow
  read-surfaces + `docs/workflow.md`; captured additionally via memory-sync and
  the status-board Notes rather than the hot cache.
- **`docs/architecture.md` — `no-op`.** No module boundary or public contract
  changed (workflow.py logic untouched; the nudge is prose + a template comment).
- **`docs/inbox.md` design-eval items — `no-op` (not resolved; cross-referenced
  in 104-01's sweep).**
