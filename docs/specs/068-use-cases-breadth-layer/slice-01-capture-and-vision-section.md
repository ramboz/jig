---
status: DONE
dependencies: [adr-0025]
last_verified: 2026-06-10
frame_review: true
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section. -->

## Slice 068-01 — capture-and-vision-section

**Goal:** At init, the project vision gains a `## Use cases` section, and the
`vision-elicitation` wizard runs a conversational capture loop — any-shape input
→ single normalize pass → human-confirm — that writes goal-level
`"[actor] can [goal]"` entries into it. Nothing is written without confirmation;
unstated use cases are never silently inferred. This is the **prerequisite**:
slices 02–03 are inert without the section existing and being fillable.

The init capture is a **seed, not the final set.** Slice 01 deliberately stops at
capture — it does **not** assume the full behavior set is knowable at init, and it
does **not** add a growth mechanism of its own. *Growing* the set as behaviors
surface, and *prompting* that growth where they actually surface (spec-drafting),
is **slice 02's** scope (see the spec's `## Assumptions` — knowability-at-init).
The section is a normal `vision-elicitation` slot, so the wizard's existing
skip / hash / `--section` mechanics apply to it like any other; slice 01's single
normalize-and-confirm pass governs the initial capture session.

**DoR:**
- ✅ [ADR-0025](../../decisions/adr-0025-use-cases-breadth-layer.md) records the
  home (B1) + capture (B2) decisions.
- ✅ Vision template located: `templates/docs/product-vision.md.template` (9 H2
  slots; each opens with `<!-- elicited: PENDING / status: unfilled -->`).
- ✅ Capture host located: `skills/vision-elicitation/SKILL.md` (judgment-only
  Q&A; per-section skip; hash-based re-run detection; no `.py` helper).
- ✅ Marker/hash convention known (`docs/conventions.md` — `<!-- elicited: … -->`
  + `hash:` on fill).

**Acceptance Criteria:**

1. **The vision template carries a `## Use cases` H2 section** with the standard
   `<!-- elicited: PENDING / status: unfilled -->` marker and goal-level guidance
   — the `"[actor] can [goal]"` form, a concrete example
   (e.g. *"a user can resume a draft offline"*), and an explicit
   *"goal-level, not spec-level"* caution. Observable by reading
   `templates/docs/product-vision.md.template`; a freshly scaffolded
   `docs/product-vision.md` contains the section with its marker.
2. **The capture loop accepts any-shape input and loops to exhaustion.** The
   `vision-elicitation` flow accepts behaviors entered incrementally *or* as a
   bulk paste, and loops on "anything else?" until the user signals done.
   Observable in the SKILL.md flow + a worked example.
3. **A single normalize pass is confirm-gated before any write.** After capture,
   one normalize pass (dedupe, split compound entries, rephrase to goal-level
   form) presents the normalized set for **confirm/edit**, and **nothing is
   written** to the vision until the user confirms. Observable: the flow writes
   the section body only on confirmation; an edit round-trips before write.
4. **No silent inference.** A use case the user did not state is **never**
   auto-added. A candidate the wizard suspects is surfaced as a *question*
   ("you didn't mention X — intentional?") and added only on an explicit yes.
   Observable in the flow + a worked example that shows the question, not an
   auto-fold.
5. **Overridable.** Per-section skip writes the `skipped` marker (no use cases
   captured) and the section may be left empty — consistent with the wizard's
   existing skip mechanic; re-run detects hand-edits via the existing hash
   mechanic. Observable: skipping yields a `status: skipped` marker and no body.
   *(Additive growth of the set as behaviors surface — and prompting it — is
   **slice 02's** scope, not slice 01's; see the Goal and the spec's
   `## Assumptions` (knowability-at-init). Slice 01 ships a pure seed.)*

**DoD:**
- [x] All ACs pass; full test suite green (2533 tests OK, ruff clean — no regressions).
- [x] Coverage: a template-presence assertion (scaffold renders the `## Use
      cases` section + marker) and a `vision-elicitation` skill-surface test
      (the capture-loop / normalize / confirm / **no-infer** prose is present),
      mirroring `skills/analyze/test_analyze_skill_surface.py`. (vision-elicitation
      is judgment-only — no `.py` helper — so the testable surface is the
      template + the SKILL.md contract.)
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] **Frame-critique passed** (`frame_review: true`) — the adversarial
      pre-implementation pass attacks the thin-evidence premise (does
      capture-at-init reduce divergence, or is breadth modeling ceremony? — and is
      a useful behavior set even *knowable* at init, the distinct *incompleteness*
      facet apart from §A2's coarseness?) before the capture loop is built. Gates
      DRAFT → READY_FOR_REVIEW. *(Iterated: an initial pass surfaced
      knowability-at-init and a candidate grow-mechanism; per the team decision the
      grow mechanism + spec-draft prompting were moved to **slice 02** (capture
      stays a pure seed here), and slice 01's frame was re-validated under that
      split. See `reviews/slice-01-frame-critique.md`.)*
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation. *(N/A — no decisions deferred during implementation.)*

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (spec still in flight — leave the
      Active-specs entry until 068-03 closes it).

**Anti-horizontal-phasing check:** After this slice, a user running init is asked
for use cases and sees them normalized + written (on confirm) into a `## Use
cases` vision section — an observable, end-to-end capture flow, independent of
slices 02–03.

### Deviation log (after reconciliation)

1. **Capture is a distinct conversational loop, not a 14th rigid Q&A "Section".**
   `questions.md` was left at its 13 numbered Q&A sections; the `## Use cases`
   capture contract lives in `SKILL.md` as its own `## Use cases capture` section.
   Rationale: the normalize-and-confirm loop is fundamentally different from the
   per-section Q&A's "write the user's words verbatim, no looping" shape — folding
   it in as a 14th Q&A section would have misrepresented it. Consistent with the
   slice framing ("a normal vision slot" for skip/hash, but with its own capture
   session). Net counts now: **10 template H2s / 13 Q&A sections / capture loop** —
   three distinct layers, kept explicit in `SKILL.md` (the craft reviewer verified
   the 5+5+1+2=13 arithmetic and the layering are internally consistent).
2. **Placement: `## Use cases` after `## Scope`, before `## Stack`** (template
   index 5). The slice named "after Scope" as natural — behaviors follow from
   scope; keeps the breadth-frame sections adjacent. All other sections retain
   their order.
3. **Template-shape invariant honored over a carve-out.** Extending
   `EXPECTED_TEMPLATE_H2S` to include `Use cases` made the existing
   `test_output_matches_vision_template_h2s` require the H2 in *both* worked
   examples; rather than weaken that single-source-of-truth invariant, a rendered
   `## Use cases` block was added to both (full capture-loop demo in
   `worked-example-yarnfinder.md`; brief block in `worked-example-jig.md`).
4. **Reconciliation doc-hygiene (review nits).** Both review passes flagged stale
   `9 H2` counts left by the 9→10 template growth — fixed in reconciliation:
   `test_vision_elicitation_skill_surface.py` docstring + comment, **three spots**
   (AC#4 bullet ~line 9, AC#5 bullet ~line 15, and the
   `test_output_matches_vision_template_h2s` comment ~line 336 — the line-wrapped
   AC#4 "the 9 / H2s" instance was caught by the reconciliation review),
   `worked-example-rerun.md` **two spots** (setup "all 9 → 10 H2 sections" at
   ~line 14, AND the section-walk range "Sections 4–9 → 4–10" at ~line 114 — the
   en-dash range was caught by the second reconciliation review; the walk now
   matches the setup's 10-section claim), and a clarifying note added to
   `worked-example-yarnfinder.md`'s concept→template mapping table (the 10th H2,
   `## Use cases`, has no YarnFinder-named source — it is filled by the capture
   loop; `yarnfinder.md`'s "names 9 sections" is YarnFinder's own source-concept
   count, correctly left as-is). An exhaustive numeric-range + standalone-`9` sweep
   across all `vision-elicitation` files confirms no stale H2/section count
   remains. No behavior/assertion changed; full suite stayed green.
5. **No new decisions parked / no ADR / no conventions change.** `docs/conventions.md`
   was untouched (its `<!-- elicited: … -->` marker convention already covers the
   new slot, per the slice DoR). No new ADR — ADR-0025 already records the home
   (B1) + capture (B2) decisions. Nothing parked to `docs/inbox.md`;
   `docs/refinement-todo.md` unchanged (no decisions deferred during implementation).
