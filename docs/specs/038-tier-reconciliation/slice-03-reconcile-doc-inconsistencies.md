---
status: DRAFT
dependencies: [038-02]
last_verified:
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
- [ ] All ACs pass.
- [ ] No remaining doc claim contradicts `_TIER_SKILLS` (grep the tier
      counts + the two named skills to confirm).
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] If this is the spec's last non-deferred slice, compress the spec's
      Active-specs entry per spec 025-01.

**Anti-horizontal-phasing check:** After this slice, a reader of the
README or product-vision sees tier counts and skill placements that
match exactly what `scaffold-init` installs — the positioning is
verifiable, not aspirational.

### Deviation log (after reconciliation)

_TODO._
