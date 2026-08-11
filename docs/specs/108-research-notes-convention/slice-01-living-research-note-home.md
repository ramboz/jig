---
status: DONE
dependencies: [adr-0054]
last_verified: 2026-08-11
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 108-01 — living research-note home: template, index, hand-offs

**Goal:** Give the open-investigation phase a real home — a contributor can
create a research note from a template, register it in a hand-maintained index,
and promote it out to an ADR / spec / refinement-todo entry — with the existing
`docs/research/00`–`09` corpus formally declared frozen seed research.

**DoR:**
- ✅ [ADR-0054](../../decisions/adr-0054-research-notes-artifact-convention.md)
  Accepted (frame-critique passed, 2026-08-11).
- ✅ `docs/research/` verified to hold exactly `00-starter-prompt.md` + `01`–`09`
  (frozen prose, no status frontmatter) — the seed corpus this slice labels.
- ✅ No `research.py` / index-regen exists (this is a convention, not a helper) —
  deferred machinery is 108-02's concern, not a blocker here.

**Acceptance Criteria:**

1. **A research-note template exists at a jig-internal path** — `docs/research/TEMPLATE.md`
   (an uppercase meta-file beside `README.md`, deliberately **not** under
   `templates/`, which is the scaffold source that copies into adopter projects:
   shipping the template there would leak research-notes onto adopters, an
   ADR-0054 non-goal — the adopter-facing surface is deferred). It carries the
   ADR-0054 frontmatter keys — `status` (one of `OPEN` / `CONCLUDED` / `PARKED` /
   `ABANDONED`), `topic`, `created`, `related:` — and a body skeleton for the
   evolving investigation: question → sources/findings → pros/cons → open
   questions → conclusion, plus a `Promoted to:` line for the hand-off.
2. **`docs/research/README.md` exists and declares the seed boundary.** A top
   section formally labels `00-starter-prompt.md` … `09-addition-memory-layer.md`
   as **frozen seed research** (jig's founding corpus, not living notes),
   explicitly kept in place and unrenamed.
3. **The index lists living notes.** `docs/research/README.md` carries a
   living-notes table (id, topic, status, related / promoted-to) that starts
   empty (no synthetic seed note is fabricated — organic creation is what
   ADR-0054's kill criterion watches). The table is documented as
   **hand-maintained** (no regen helper).
4. **The naming + numbering convention is documented.** Living notes are
   `docs/research/R-NNN-<slug>.md`, numbered from `R-001`; the `R-` prefix is
   the boundary from the `00`–`09` seed corpus. Numbering is stated as
   **local-and-cheap** — collisions are a tolerated nuisance, *not*
   reservation-coordinated on origin/main (contrast specs/ADRs).
5. **Both hand-offs are documented in the README.** (a) *Inbox → note*: a thick
   investigation is captured as a one-line `docs/inbox.md` pointer to `R-NNN`,
   not swallowed inline. (b) *Note → decision/work*: on crystallization the note
   promotes into the right existing artifact (refinement-todo entry / ADR /
   spec) which cites `R-NNN` in its Context; the note flips to `CONCLUDED` with a
   `Promoted to:` line. The README states the **sequential** relationship to
   `refinement-todo` (open phase → named deferred decision) so the two are not
   read as competitors.
6. **The seed corpus is byte-unchanged.** `docs/research/00`–`09` are not
   renamed or edited by this slice (verified: their content/paths are identical
   to before).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture:
      `scripts/test_research_notes_convention.py` (the `scripts/` dir is a
      `run_tests.py` discovery root) asserting: `docs/research/TEMPLATE.md`
      exists with the required frontmatter keys + body sections; `docs/research/README.md`
      declares the `00`–`09` seed boundary; the README documents both hand-offs
      and the `R-NNN` local-numbering rule; the `00`–`09` filenames are intact;
      and that no research-note template leaked into `templates/`.
- [ ] Each new test has been shown to fail when its feature is removed — mutate
      the deliverable (drop a frontmatter key / the seed declaration), watch the
      test go red, restore.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [ ] Deviation log produced under this slice heading (carry the ADR-0054
      frame-critique demand-framing note verbatim — see spec `## Assumptions`).
- [ ] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation (the planned deferrals are 108-02's deliverable; note any
      *new* ones here).

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE` transition.
Slice-land's `check_dod` (slice 009-01) excludes them from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`. Notes
      column receives any load-bearing per-slice invariant (preserved across
      regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the spec** (it
      does not — 108-02 follows), leave the Active-specs entry. Add a glossary
      entry for the **research note** term during reconciliation memory-sync so
      `/jig:explain research note` resolves.

**Anti-horizontal-phasing check:** After this slice lands, a jig contributor can
file an open investigation as `docs/research/R-001-<slug>.md` from the template,
register it in the index, and knows exactly how to promote it out — a complete,
usable convention on its own, independent of 108-02's codification.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Plan adherence.** Implemented exactly as specced — three deliverables:
   `docs/research/TEMPLATE.md`, `docs/research/README.md`, and
   `scripts/test_research_notes_convention.py`. No `research.py` helper (deferred
   by ADR-0054). No structural deviation from the ACs.
2. **Spec refinement during authoring (pre-implementation).** Two corrections
   made while the slice was still DRAFT, before the implementer ran:
   (a) AC1's template location moved from `templates/docs/research/…` to the
   jig-internal `docs/research/TEMPLATE.md` — `templates/` is the scaffold source
   that copies into adopter projects (ADR-0038 / spec 095), so shipping the
   template there would have leaked research-notes onto adopters, an ADR-0054
   non-goal. (b) The spec's `## Assumptions` was reformed to the parser-clean
   `None.` + single italic-rationale shape so `frame-review-needed` correctly
   derives `false` (the frame was already critiqued at ADR-0054; these slices add
   no unverified runnable-surface assumption); the demand-framing note was
   relocated to a new `## Reconciliation carry-forward` section (it is a
   reconciliation instruction, not an assumption).
3. **Reviewer findings folded in (pre-REVIEWED).** Compliance (pass, 1 nit) +
   craft (pass, 2 strengths, 3 nits) — all nits addressed before the REVIEWED
   transition: (i) `test_documents_inbox_to_note_handoff` strengthened from a
   bare "inbox" word-check to the specific `inbox → note` label + a one-line
   `R-NNN` pointer regex; (ii) the `SeedCorpusIntact` docstring over-claim
   ("byte-unchanged") corrected — class renamed `SeedCorpusPresent`, docstring
   now states presence-only with byte-equality git-guarded; (iii) the
   single-hard-coded-path leak guard replaced with a name + content-signature
   scan across all of `templates/`. Test count 18 → 19, all green, ruff clean.
4. **Implementer judgment call (additive).** The README's note→decision hand-off
   also documents the `ABANDONED` + `Promoted to: n/a` path — additive
   documentation matching ADR-0054's status set, no scope change.
5. **Demand-framing carry-forward (verbatim, ADR-0054 frame-critique).** The
   decision to build this convention *now* is justified by the external ask
   (#196) + the existing frozen seed corpus + near-zero reversible cost, and
   explicitly **not** by demonstrated recurring internal open-phase demand
   (≈ n=0–1, unproven). ADR-0054's distinctness kill criterion is the tripwire;
   this work must not silently manufacture the demand it was meant to test.

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Project front door untouched; the convention is discoverable via `docs/research/README.md`, not the root README. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board` at close-out. |
| `docs/product-vision.md` | `no-op` | Internal convention; no behavior/scope drift. |
| `docs/architecture.md` | `no-op` | No module-boundary / public-contract change — docs + one template file, no code path. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | Spec still in flight (108-02 pending); primer compression deferred to the spec-closing slice per spec 025-01. |
| `docs/inbox.md` | `no-op` | No retro-migration (ADR-0054 non-goal); no existing inbox item is resolved by 108-01 alone (the #196 hand-off closes at 108-02). |
| `docs/refinement-todo.md` | `deferred` | The deferred-machinery entries are 108-02's deliverable, not this slice's. |
| `docs/memory/**` | `updated` | Added the **research note** glossary term (via memory-sync) so `/jig:explain research note` resolves. |
| `docs/decisions/README.md` / ADR index | `no-op` (for this slice) | Appears in the branch diff, but the change is ADR-0054's acceptance/index (a DoR precondition done earlier this session), not a 108-01 deliverable. |
| `docs/research/00`–`09` (seed corpus) | `no-op` | Verified present and unrenamed (AC6); byte-equality git-guarded. |
| Spec 108 + ADR-0054 authoring artifacts (`spec.md`, `slice-02-*.md`, `adr-0054-*.md`, `reviews/*`) | `updated` | Expected spec-workflow / adr-workflow authoring changes (spec.md reforms logged in deviation-log §2); not external drift surfaces. |
