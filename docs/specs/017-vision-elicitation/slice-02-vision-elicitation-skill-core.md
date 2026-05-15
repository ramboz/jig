## Slice 017-02 — vision-elicitation-skill-core

**STATUS: DONE**

**Scope:** the elicitation skill itself, first-run only. Asks the
12 sections per Appendix A in order, writes captured answers into
the template slots created by 017-01. No re-run smarts yet — that's
017-03.

**SPIDR axis:** Interface — splits the work by adding the user-facing
trigger surface on top of 017-01's data scaffolding.

**Deliverables:**
- New `skills/vision-elicitation/SKILL.md` with frontmatter
  (`name: vision-elicitation`, judgment-only, no `.py` helper).
  Description includes a category-based deferral hint matching the
  pattern from `pr-review` (012-01) and `arch-review` (014-01).
- New `skills/vision-elicitation/questions.md` shipping the 12-section
  question set verbatim from Appendix A. Loaded on-trigger via
  progressive disclosure.
- New `skills/vision-elicitation/worked-example-jig.md` —
  annotated transcript that traces each section of the hand-seeded
  [docs/product-vision.md](../../product-vision.md) back to the
  elicitation questions that would have produced it.
- New `skills/vision-elicitation/worked-example-yarnfinder.md` —
  same for the YarnFinder pitch in `/Users/ramboz/Projects/CLAUDE.md`.
  Two project shapes (dev-tooling vs. consumer-product) keep the
  question set honest.
- SKILL.md body documents the per-section flow (per the Path SPIDR
  decision: each section is independently answerable, skippable,
  and re-runnable).
- On first run: writes answers into the unfilled-slot template
  produced by 017-01, transitioning each filled section's marker
  from `status: unfilled` to `status: filled`. Skipped sections
  transition to `status: skipped`.
- Also updates `docs/architecture.md` slots using the answers from
  Sections 6 (Repository structure) / 7 (Tech stack) / 8 (Module
  boundaries) / 9 (Data model) / 12 (Open questions). Each
  architecture slot maps 1:1 to its elicitation section, so a user
  can skip any individual slot without losing the others. The
  "What this project does" stanza no longer exists in the template
  (slice 017-01 reshape) — vision.md owns it.

**Acceptance criteria:**
1. `skills/vision-elicitation/SKILL.md` ships with the required
   frontmatter and a description that includes:
   (a) trigger phrases ("set up project vision", "elicit
   architecture", "define what we're building"),
   (b) explicit reference to the templates from slice 017-01 as the
   output shape,
   (c) category-based deferral hint (any user-installed skill whose
   description identifies it as handling vision elicitation,
   product discovery, or project framing wins).
2. `skills/vision-elicitation/questions.md` exists and contains the
   12 sections from Appendix A, with question text matching verbatim.
3. Both worked-example transcripts exist and walk through their
   respective pitches section by section, showing question →
   answer → rendered section heading + body.
4. **Structural-match dogfood (worked example #1):** the worked
   example transcript for the jig pitch produces an output document
   whose H2 section structure matches the **vision template**
   (`templates/docs/product-vision.md.template`) — i.e. the 9 H2s
   `Identity / Target users / Core problem / Competitive landscape /
   Scope / Stack / Design principles & constraints / How new work
   enters / Open questions`. The worked example MUST acknowledge
   the divergence from the hand-seeded `docs/product-vision.md`
   (which predates the template and uses bespoke H2 names like
   "Vision statement" / "Future scope" / "References") — annotating
   the content-to-slot mapping makes the divergence explicit.
5. **Structural-match dogfood (worked example #2):** the worked
   example transcript for the YarnFinder pitch produces an output
   document whose H2 section structure also matches the vision
   template's 9 H2s (same as AC #4 — the elicitation skill is
   template-driven, so all outputs have the same H2 shape regardless
   of project). The worked example MUST acknowledge how YarnFinder's
   bespoke concepts from `/Users/ramboz/Projects/CLAUDE.md` (Data
   sourcing, Recommended slice order, prioritized backlog, etc.)
   map to the template's slots — Data sourcing → How new work
   enters; prioritized backlog → Scope > Core features; Recommended
   slice order → Scope > (Tiers / phases or Out of scope as
   appropriate).
6. After a first run, the resulting `docs/product-vision.md` has
   every section marker transitioned away from `status: unfilled`
   (each is either `status: filled` or `status: skipped`).
7. The `docs/architecture.md` four elicitation slots (Repository
   structure / Tech stack / Module boundaries / Data model) are
   each filled from their corresponding Q&A section (6 / 7 / 8 / 9
   in the new 12-section question set). For each slot: if the user
   answered, the slot transitions from `status: unfilled` to
   `status: filled` and the body is rendered from the user's words;
   if the user skipped, the slot transitions to `status: skipped`
   and the existing placeholder/Deferred prose is retained
   verbatim.
8. Surface tests pin: frontmatter fields, description category-
   deferral phrasing, questions.md section structure, SKILL.md
   per-section flow markers. Anti-greediness `DescriptionBoundsTests`
   class (same shape as pr-review) pins the description against
   over-claim phrases like "best vision elicitation" or
   "comprehensive product discovery".
9. **Routing dogfood:** in a fresh session, an "elicit project
   vision" or "let's define what we're building" prompt triggers
   `/jig:vision-elicitation` (or defers to a user-installed
   category-equivalent if one is present). Like pr-review and
   arch-review, this dogfood lands as a post-merge close-out item;
   AC #9 fallback (`disable-model-invocation: true`) is held in
   reserve.

**Definition of Done:**
- [x] All ACs 1–8 green pre-merge; AC #9 deferred to post-merge close-out.
- [x] New surface tests green; no regression in existing suite. (659 → 695 total green; +36 from `VisionElicitationSkillSurfaceTests`.)
- [x] Implementation review passed. _(auto-ticks on IN_PROGRESS → REVIEWED)_
- [x] Deviation log written.
- [x] Reconciliation review passed. _(auto-ticks on REVIEWED → RECONCILED)_
- [x] Spec status board updated.

### Close-out (post-DONE)
- [ ] Routing-dogfood verification (AC #9) in a fresh session — does an "elicit project vision" prompt trigger `/jig:vision-elicitation`?
- [x] CLAUDE.md hot-cache row for the new skill.

### Deviation log (017-02)

**1. AC #4 and AC #5 reworded mid-implementation (template-shape ground truth).**
The original ACs claimed the worked examples would match the
hand-seeded `docs/product-vision.md` byte-for-byte in H2 structure.
While drafting the jig worked example, the implementer discovered
the hand-seeded file uses bespoke H2 names ("Vision statement",
"The core problem", "Future scope", "References") that diverge
from the vision **template**'s H2 names ("Identity", "Core problem",
"Stack", "Open questions" — slice 017-01 deliverable). Because the
elicitation skill is template-driven (it reads the template's H2s
and writes between them), its output can only match the template,
not the hand-seeded file. **The original AC was unachievable as
written.** Reworded both ACs to require template-shape output +
explicit acknowledgment of the divergence + (for YarnFinder) a
concept-to-slot mapping table. The reworded ACs improved the slice
— the worked-example-yarnfinder.md concept-to-template mapping
table is more useful guidance for the 017-03 implementer than a
byte-for-byte structural-match check would have been.

**2. Implementation reviewer caught a stale "byte-for-byte" claim
in SKILL.md that contradicted the AC #4 reword.**
Third instance (after 017-01 §5(a) and 017-01 §8) of the
"reshape/reword didn't propagate to all consuming sentences"
pattern. SKILL.md:177 claimed the jig worked example "Produces
output matching the hand-seeded `docs/product-vision.md`
byte-for-byte in H2 section structure" — that's the pre-reword
text. The actual worked-example-jig.md correctly produces
template-shaped output and annotates the divergence. **Fixed
inline**: SKILL.md rewritten to describe template-shaped output
with explicit hand-seeded divergence acknowledgment. **New
regression test landed**:
`test_worked_examples_section_acknowledges_template_shape` pins
the worked-examples section against the recurrence — must mention
"template", must NOT contain "byte-for-byte". Test count: 35 → 36
in the vision-elicitation surface suite; 694 → 695 overall.

**3. Test file renamed: `test_skill_surface.py` → `test_vision_elicitation_skill_surface.py`.**
Mirrors arch-review's precedent (`test_arch_review_skill_surface.py`).
The unprefixed name collided with pr-review's same-named test file
at unittest-discover time (pytest discovery would also fail).
Asymmetry: pr-review still uses the unprefixed `test_skill_surface.py`
— a follow-up consistency rename is a plausible refinement-todo
entry but is correctly out of scope for this slice. Reviewer noted
the rename was principled.

**4. Implementer was the main agent, not the real `jig:implementer` subagent.**
Mirrors slice 017-01 §1 and the broader pattern across 013-01,
007-01, etc. Work was done in the main session under the
implementer convention (TDD: red → green) but without the fresh-
context guarantee that spawning the real subagent would provide.
Implementation review (§5 below) WAS spawned as a real subagent,
so the independent-evaluation half of the spec lifecycle held.

**5. Implementation review used `general-purpose` subagent, not real `jig:reviewer`.**
This worktree is not installed as a jig plugin (`review.py
subagent-type implementation` returns `general-purpose`). Per
slice 011-02's fallback design, this is the documented degraded
mode. Review returned `VERDICT: needs-changes` with one specific
issue (the SKILL.md stale claim — §2) and three reconciliation
notes (template-shape principle worth recording — addressed via
§1; rename principled — §3; pr-review consistency rename worth a
refinement-todo entry — see §6 below). All findings addressed
before requesting reconciliation review.

**6. Refinement-todo candidate: pr-review test file rename for consistency.**
Reviewer surfaced (in reconciliation notes) that pr-review still
uses the unprefixed `test_skill_surface.py` while arch-review and
now vision-elicitation use the `test_<skill_name>_skill_surface.py`
shape. A follow-up consistency rename of pr-review's file is
plausible but out of scope for this slice. **Not recording in
refinement-todo.md inside this slice's deliverable surface** (would
expand the diff beyond slice scope and require gate approval since
`docs/conventions.md`-adjacent files share the gate); the entry
should land in a follow-up commit if and when a real friction
appears (e.g. a third same-named test file is added).

