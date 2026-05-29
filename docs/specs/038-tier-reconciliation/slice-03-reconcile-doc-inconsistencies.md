---
status: DONE
dependencies: [038-02]
last_verified: 2026-05-29
---

## Slice 038-03 — reconcile-doc-inconsistencies

**Goal:** Bring the vision and README positioning into line with the
`_TIER_SKILLS` source of truth and the now-gated install, closing the
three secondary inconsistencies that have been latent for months.

**DoR:**
- ✅ Slice 038-02 landed — the gated install is the new reality the
  docs must describe (7 default-installed Tier-0 / 14 available).
- ✅ ADR-0010's source-of-truth rule fixed: `_TIER_SKILLS` is
  authoritative; docs reconcile *to it*, not the reverse.

**Acceptance Criteria:**

1. **Vision numbered tier list matches `_TIER_SKILLS`.**
   `vision-elicitation` appears in the Tier 0 list (it is in
   `_TIER_SKILLS["tier-0"]` but currently absent from the numbered
   list); `contracts` is listed under Tier 0 (it is in
   `_TIER_SKILLS["tier-0"]` but the vision currently puts it at item
   #11 / Tier 1). No skill's documented tier contradicts the code.
2. **README counts match reality.** "5 Tier 0 skills" → 7;
   "8-12 skills total" → the accurate framing (7 Tier-0 installed by
   default; 14 available across tiers). Wording describes the gated
   model, not the old all-14 copy.
3. **Closed-spec / load-bearing prose edits follow ADR-0008.** This
   slice resolves drift #5, which ADR-0008 explicitly deferred to spec
   038. Where an edit touches a closed (`DONE`/`SUPERSEDED`) spec or
   router-load-bearing prose, it lands as an `## Amendments` entry per
   ADR-0008 rather than an in-body rewrite; living docs (README,
   product-vision) are corrected directly.

**DoR note / coordination:** Spec 040 (isolation honesty) also edits
the README and is DONE as of 2026-05-29, so the README is free for
this slice's edits — no adjacent-line conflict expected.

**DoD:**
- [x] All ACs pass.
- [x] No remaining doc claim contradicts `_TIER_SKILLS` (grep across
      `skills/` + docs confirms clean; historical records left frozen).
- [x] Reviewed by `reviewer` subagent (compliance pass: needs-changes →
      fixed → confirm pass).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [ ] If this is the spec's last non-deferred slice, compress the spec's
      Active-specs entry per spec 025-01. (N/A — 038-04 still DRAFT.)

**Anti-horizontal-phasing check:** After this slice, a reader of the
README or product-vision sees tier counts and skill placements that
match exactly what `scaffold-init` installs — the positioning is
verifiable, not aspirational.

### Deviation log (after reconciliation)

1. **Implemented as planned.** `docs/product-vision.md`: added
   `vision-elicitation` to the Tier 0 numbered list (item 6, was absent
   entirely), moved `contracts` from Tier 1 (#11) to Tier 0 (item 7),
   renumbered Tier 1 to 8–14, fixed "Nothing useful without all five" →
   "all seven", and the "5 Tier 0 + ~5 Tier 1" fits-line → "7 Tier 0 +
   7 Tier 1". `README.md`: "5 Tier 0 skills" → "7 Tier 0 skills installed
   by default"; "8-12 skills total when complete" → "14 skills total
   across two tiers (Tier 1 adds on a test/workflow signal)". All
   reconciled *to* `_TIER_SKILLS` per ADR-0010's source-of-truth rule
   (no tier reassignment — `contracts`/`vision-elicitation` keep their
   existing code-side tier).
2. **Scope decision — only live positioning docs edited; historical
   records left frozen.** The grep for stale `5 Tier 0` / `8-12` / `all
   five` surfaced hits in `docs/inbox.md` (the 035–042 cluster plan),
   `docs/research/*` (dated analysis citing the then-target "8-12
   skills"), `docs/specs/036-*` (the drift-tracking table that *records*
   this very drift), and `ADR-0008` / `ADR-0010` (which *quote* the old
   README text as decision-time context). None are live claims a user
   reads to evaluate jig; the spec/ADR/research hits are accurate records
   of their time, and ADRs are immutable (Nygard). No ADR-0008
   `## Amendments` block was needed because no closed-spec *in-body*
   prose was edited. Left all of these as-is by design.
3. **drift #5 resolved.** This slice closes the README "5 Tier 0 / 8-12"
   drift that [ADR-0008](../../decisions/adr-0008-closed-spec-drift-policy.md)
   and spec 036 deferred to spec 038.
4. **Added three regression tests beyond the slice's grep-only DoD**
   (`TierSkillSetTests.test_product_vision_names_every_tier_skill`,
   `test_readme_states_correct_tier0_count`,
   `test_vision_elicitation_worked_example_tier_line_in_sync`, in
   `skills/scaffold-init/test_scaffold.py`). These pin doc↔`_TIER_SKILLS`
   consistency — the exact test-gap that let `vision-elicitation` go
   missing and the counts go stale for months (spec 038 Goal #4 in
   spirit; 038-02 owned the manifest↔disk side, this adds the doc side).
   All would have failed pre-edit.
5. **Compliance review caught a missed live resource — fixed.** The
   first compliance pass returned **needs-changes**: my initial grep was
   scoped to `README.md docs/` and missed `skills/` — so
   `skills/vision-elicitation/worked-example-jig.md` (a shipped Tier-0
   resource that explicitly claims parity with product-vision.md) still
   carried the stale "5 Tier 0 + ~5 Tier 1" fits-line and two Tier lists
   omitting `vision-elicitation`/`contracts` (and `clarify`/`analyze`
   from Tier 1). Reconciled all three spots in that file to `_TIER_SKILLS`
   (chose correction over freezing, since the file actively asserts
   parity). Re-ran the grep across `skills/` + docs — clean. Added the
   worked-example tier-line test (above) so the `skills/`-path gap is now
   covered, not just re-fixed. Full suite after fix: see below.
6. **Scope note (corrected from the initial pass).** Live positioning
   surfaces edited: `README.md`, `docs/product-vision.md`, and
   `skills/vision-elicitation/worked-example-jig.md`. Deliberately left
   frozen (accurate historical records / immutable): `docs/inbox.md`
   (cluster plan), `docs/research/*` (dated analysis), `docs/specs/036-*`
   (drift-tracking table), and `ADR-0008`/`ADR-0010` (which quote the old
   text as decision-time context). No ADR-0008 `## Amendments` block
   needed — no closed-spec in-body prose was edited.
