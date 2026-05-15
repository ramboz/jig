## Slice 017-01 — vision-template-and-architecture-slots

**STATUS: DONE**

**Scope:** pure template surgery. No skill yet. Lands the named-but-
empty *slots* into the templates so `scaffold-init` already produces
a project with a recognizable vision/architecture shape that a dev
can hand-fill even before 017-02 ships.

**SPIDR axis:** Data — splits the work by what artifact changes.

**Deliverables:**
- New `templates/docs/product-vision.md.template` with the 9 named
  sections (per Appendix A). Each section starts with the
  marker `<!-- elicited: PENDING / status: unfilled -->`. Section
  bodies are placeholder prose (one or two lines) plus named
  sub-bullets that make the expected shape legible to a dev who
  reads them without running the skill.
- **Reshaped** `templates/docs/architecture.md.template` to mirror
  the proven structure of jig's own
  [docs/architecture.md](../../architecture.md) — the slimmed-down
  version produced in this same session. Four elicitation slots
  (Repository structure / Tech stack / Module boundaries / Data
  model), each carrying `<!-- elicited: PENDING / status: unfilled -->`
  above placeholder prose. Two un-markered sections (Core
  architecture decisions for ADR-driven content; Open questions
  as a footer pointing to `refinement-todo.md`). A top-of-doc pointer
  to `product-vision.md` replaces the old "What this project does"
  stanza entirely — vision.md owns that question. *Why a reshape and
  not just adding markers to the old 3 stanzas: the old template was
  asking the wrong questions. "What this project does" duplicated
  vision.md; "Module boundaries" being fully deferred was the wrong
  default (every project has top-level concerns on day 1); the
  template lacked Repository structure and Data model entirely.
  Filling in jig's own arch.md proved the better shape.*
- Updated `templates/CLAUDE.md.template`: line 8 ("What this project
  does → Deferred") rewritten to reference `docs/product-vision.md`
  rather than carrying its own stub.
- New short section in `docs/conventions.md` documenting the
  elicitation marker convention (3 states: `unfilled` / `filled` /
  `skipped`; date format; hash field deferred to 017-03).

**Acceptance criteria:**
1. `templates/docs/product-vision.md.template` exists and parses as
   valid Markdown.
2. The template contains exactly 9 H2 sections in this order:
   `Identity` / `Target users` / `Core problem` /
   `Competitive landscape` / `Scope` / `Stack` /
   `Design principles & constraints` / `How new work enters` /
   `Open questions`.
3. Each H2 section's first line is the unfilled marker comment.
4. `templates/docs/architecture.md.template` is **reshaped** to four
   elicitation slots — `Repository structure` / `Tech stack` /
   `Module boundaries` / `Data model` — each carrying
   `<!-- elicited: PENDING / status: unfilled -->` immediately after
   the H2 heading. Two un-markered sections survive: `Core
   architecture decisions` (one H3 per decision, populated by ADRs
   over time) and `Open questions` (footer pointing to
   `refinement-todo.md`). The previous "What this project does"
   stanza is removed entirely; a top-of-doc preamble points to
   `product-vision.md` instead. `Tech stack` and `Module
   boundaries` retain the `> **Deferred — …**` fallback prose;
   `Repository structure` and `Data model` get positive
   placeholder prose (their "no signal" answer is rarely honest —
   every project has a layout and some state on day 1).
5. `templates/CLAUDE.md.template` line 8 references
   `docs/product-vision.md` and no longer carries a `Deferred — no
   signal` stub for project description.
6. `docs/conventions.md` documents the marker convention with the
   three states and the date format. The `hash` field is named as
   "added in 017-03" so 017-01 doesn't promise machinery it doesn't
   ship.
7. Running `scripts/scaffold.py` (or equivalent dogfood path)
   against a temp dir produces a project where
   `docs/product-vision.md` exists with the 9 unfilled-marker
   sections (per AC #2) and `docs/architecture.md` exists with the
   four unfilled slots (per AC #4 — Repository structure / Tech
   stack / Module boundaries / Data model).
8. New tests pin the section structure of both templates: parse,
   assert exact H2 list, assert marker presence on each section.

**Definition of Done:**
- [x] All ACs green.
- [x] New tests added; existing 593 still pass. (640 → 643 total green after reviewer-driven tightening.)
- [x] No regression in existing `scaffold-init` tests.
- [x] Implementation review passed. _(auto-ticks on IN_PROGRESS → REVIEWED)_
- [x] Deviation log written.
- [x] Reconciliation review passed. _(auto-ticks on REVIEWED → RECONCILED)_
- [x] Spec status board updated.

### Close-out (post-DONE)
- [x] CLAUDE.md hot-cache row for 017-01 updated.

### Deviation log (017-01)

**1. Implementer was the main agent, not the real `jig:implementer` subagent.**
Mirrors slice 013-01 §1 — work was done in the main session under
the implementer convention (TDD: red → green) but without the fresh-
context guarantee that spawning the real subagent would provide.
Implementation review (§2 below) WAS spawned as a real subagent, so
the independent-evaluation half of the spec lifecycle held.

**2. Implementation review used `general-purpose` subagent, not real `jig:reviewer`.**
This worktree is not installed as a jig plugin (`subagent-type
implementation` returned `general-purpose`). Per slice 011-02's
fallback design, this is the documented degraded mode. Review returned
`VERDICT: pass` with 5 specific issues + 4 reconciliation notes, all
addressed below.

**3. AC #4 underwent mid-implementation reshape (3 stanzas → 4 slots + 2 non-marker sections).**
After the initial template surgery landed (markers added to the old
three Deferred stanzas: "What this project does" / "Tech stack" /
"Module boundaries"), a user-led step-back surfaced that the
template itself was structurally wrong — its three placeholders
asked the wrong questions. Specifically: "What this project does"
duplicated `product-vision.md`'s job; the "Module boundaries"
Deferred default was the wrong abstraction (every project has
top-level concerns on day 1); the template lacked "Repository
structure" and "Data model" entirely. Filling in jig's own
[docs/architecture.md](../../architecture.md) earlier in the same
session proved the better shape. **The reshape replaced AC #4
wholesale**: removed the old "What this project does" stanza
(a top-of-doc pointer to vision.md does the job), kept Tech stack +
Module boundaries as elicitation slots with Deferred fallback,
added Repository structure + Data model as new elicitation slots
with positive placeholders (because "no signal" is rarely an honest
answer for those), and added a `## Core architecture decisions`
no-marker section for ADR-driven content. Spec text + tests + the
template were all updated together to keep them consistent.

**4. AC #6 (conventions.md) required the documented `JIG_CONVENTIONS_APPROVED=1` escape.**
The `jig-spec-gate` hook + Claude Code's auto-mode classifier both
refused the convention-file edit until the user gave explicit
in-the-moment approval. This is the gate working as designed — slice-
level approval ("yes, implement 017-01") does not cascade to
convention-level approval. The edit landed once the user authorized
the documented bypass. No deviation in the *outcome*; recording the
*path* in case the gate pattern recurs.

**5. Reviewer-driven test tightening (4 specific findings addressed).**
The implementation reviewer flagged (a) AC #7 spec text was stale
("three unfilled slots" — pre-reshape phrasing); (b) the
conventions.md test was substring-only and didn't pin the rule body;
(c) the scaffold-dogfood test only covered the vision side, missing
architecture.md; (d) no test pinned exact-marker-count, so a
duplicated marker or marker on a wrong section would pass. All four
addressed before requesting reconciliation: spec text corrected in
AC #7, `test_conventions_md_documents_marker_convention` rewritten
to anchor on the rule heading + assert the three states + marker
prefix + 017-03 hash reference appear *inside* the rule block,
`test_scaffold_produces_product_vision_md` extended to also verify
the scaffolded architecture.md has all 4 markers + all 4 named
slots present, and new `test_architecture_template_has_exactly_four_markers`
pins the count. Test count: 640 → 643.

**6. Appendix A heading-name drift fixed.**
Reviewer also flagged that Appendix A's "Produces:" lines named
section headings that didn't match the vision template's actual
H2s ("## Vision statement" vs template's `## Identity`; "## The
core problem" vs template's `## Core problem`; "## Core features
(prioritized), ### MVP scope, ..." vs template's `## Scope` with
4 H3 sub-sections; "## Design principles" vs template's
`## Design principles & constraints`). Out of slice 017-01's
strict scope but fixed inline — leaving the drift would have
trapped the 017-02 implementer. Vision template wasn't touched
(scope was arch template only).

**7. Vision template's Stack section is currently un-mapped to any Q&A section.**
Side-effect of the AC #4 reshape: Q&A Section 7 (Tech stack) now
produces *only* arch.md's Tech stack slot. The vision template's
`## Stack` H2 (unchanged from the original 9-section design)
has no elicitation producer. **Intentional, not a defect** — Stack
content varies between vision (high-level platform framing) and
arch (concrete runtime/db). Future work in 017-02 may either
(a) have Section 7 dual-write to both slots, or (b) reshape vision
template to drop the Stack section. Not blocking this slice; logged
here so the 017-02 designer sees the choice point.

**8. Reconciliation reviewer caught stale stanza list in conventions.md.**
The first reconciliation review returned `VERDICT: needs-changes`
flagging that the "Elicitation slots" rule's "How to apply:" line in
`docs/conventions.md:81` still named the **pre-reshape** stanza list
("The three Deferred stanzas in `templates/docs/architecture.md.template`
(What this project does / Tech stack / Module boundaries)"). The rule
that 017-01 *introduces* was inconsistent with the deliverable that
017-01 *ships* — the very kind of self-contradiction the slice's own
reshape was supposed to eliminate. Same flavor of staleness the
implementation reviewer caught at AC #7 (§5(a)) on the spec-doc side,
but on the conventions-doc side. **Fixed inline** before requesting a
second reconciliation review: the line now reads "The four elicitation
slots in `templates/docs/architecture.md.template` (Repository
structure / Tech stack / Module boundaries / Data model) each carry
the same marker; two sibling sections (Core architecture decisions,
Open questions) deliberately carry no marker — they're populated by
ADRs over time and by `refinement-todo.md` references, respectively."
The tightened `test_conventions_md_documents_marker_convention` (§5)
continues to pass — it anchors on rule heading + 3 lifecycle states
+ marker prefix + 017-03 hash reference, none of which the stanza-
list rewrite affects.

