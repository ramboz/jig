---
status: DONE
dependencies: [adr-0049]
last_verified: 2026-08-03
---

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 104-01 — triage-disambiguation

**Goal:** Disambiguate `bug-fix`'s "design-gap" tier so an agent triaging a
design complaint routes correctly: a design **malfunction** is a bug; a pure
visual **fidelity gap** against an agreed mockup is spec-shaped work on the spec
spine — the originating spec when one exists, a **new** spec when none does (the
mockup-first / rebuild case) — never `bug-fix` (ADR-0049).

**DoR:**
- ✅ ADR-0049 drafted (Proposed) — the routing decision + triage test + rejected
  "new work-type" alternative are recorded.
- ✅ Mis-routing surface located: `skills/bug-fix/SKILL.md:71` lists "design-gap"
  in the gnarly tier as a bug tier that "may escalate to a spec" (verified).
- ✅ No cross-artifact triage/taxonomy section in `docs/conventions.md` (verified
  grep) — so the operative homes are the `bug-fix` read-surface + ADR-0049; no
  approval-gated `conventions.md` edit is required.

**Acceptance Criteria:**

1. **The `bug-fix` "design-gap" tier is disambiguated in place.** The gnarly-tier
   entry at `skills/bug-fix/SKILL.md` no longer presents "design-gap" as an
   undifferentiated bug tier: it distinguishes a design **malfunction** (a
   control that looks active but isn't; overlap that makes content unreadable →
   a bug) from a pure visual **fidelity gap** against an agreed mockup (→ the
   spec spine, per ADR-0049). Observable: the tier text names both cases and their
   different routes.
2. **A discoverable triage rule states the test and both fidelity routes —
   including the no-originating-spec branch.** A short, findable note in
   `skills/bug-fix/SKILL.md` (e.g. adjacent to the tiers or the "Do not use for"
   boundary in the description) states the canonical test — *a design issue is
   `bug-fix` only when the UI malfunctions; a pure visual gap against an agreed
   mockup is fidelity work on the spec spine* — and names **both** routing
   branches so an agent facing a mockup-first rebuild is not dead-ended: an
   **originating spec exists** → continue/follow-up under it; **no originating
   spec** → open a **new** spec via `spec-workflow` with the mockup as
   design-value ACs. Points to `spec-workflow` + ADR-0049. Observable: the rule
   text, both branches, and the pointers are present.
3. **The fidelity-vs-refinement test is stated and actionable.** The note gives
   the operative test from ADR-0049 §3 — *does the visual target itself change?*
   If the mockup is still the agreed target and the build hasn't reached it →
   fidelity (carry the existing mockup forward as the AC); if we now want a
   different look → a genuine refinement (a new target). Observable: the
   target-change test is present, not just the "not a refinement" assertion.
   The note also carries ADR-0049 §2's **ambiguous-case tie-breaker** — an
   ambiguous-but-functional gap (behaves correctly, only looks off) defaults to
   the spine; reserve `bug-fix` for a confirmed behavioral malfunction.
   Observable: the tie-breaker is present so the malfunction test doesn't
   dead-end on the "looks broken, maybe just mis-styled" case.
4. **The routing is prose/judgment, not a keyword gate — `bug.py` behavior is
   unchanged.** No new tier token, classifier branch, or CLI behavior is added to
   `skills/bug-fix/bug.py`; the triage test is a judgment an agent applies, not a
   mechanical match (ADR-0049: "a judgment, not a keyword gate"). Observable:
   `bug.py` has no new design/fidelity/mockup token or tier and its existing
   tests are unchanged.
5. **The disambiguation is self-consistent across the `bug-fix` surface.** The
   SKILL `description`'s existing "Do not use for spec-shaped work" boundary and
   the new tier/triage text agree — a fidelity gap is named as spec-shaped, not
   as a bug the tier absorbs. Observable: no surface still routes a pure visual
   fidelity gap into `bug-fix`.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions) — `scripts/run_tests.py`.
- [x] A test asserts the routing rule is present and the malfunction-vs-fidelity
      distinction is stated on the `bug-fix` surface (presence/drift test), and is
      shown to fail when the rule text is removed (capable of failing, not
      vacuously green).
- [x] A test (or the existing `bug.py` suite, unchanged) confirms AC4 — no new
      tier/token was added to `bug.py`.
- [x] `uvx ruff check` clean on changed files; `spec_lint.py` clean on spec 104.
- [x] Reviewed by `reviewer` subagent (compliance) + `pr-review` (craft).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred (n/a — none deferred).

### Deviation log (after reconciliation)

Original ACs preserved above; this records what changed during implementation
and why.

- **A second undifferentiated surface, beyond the DoR-located one.** The DoR
  located the mis-routing at the gnarly-tier table only (`SKILL.md:71`). The
  craft + compliance passes found the term "design-gap" also lived in the
  **de-escalation** bullet ("Reach for gnarly only for … design-gap bugs") and
  the `description` frontmatter. Compliance returned `needs-changes` on AC5
  (self-consistency across the *whole* surface). Fix: disambiguated all three
  surfaces (tier row → "design **malfunction**"; de-escalation → likewise;
  description → names a design-fidelity gap as spec-shaped), and **added a
  whole-surface guard test** `test_no_undifferentiated_design_gap_surface`
  (`assertNotIn("design-gap")`) so the class of miss (any surface reverting)
  fails the suite. Re-review: compliance `pass`.
- **Section placement.** The `### Design-fidelity triage` subsection was placed
  immediately after the Tiers section (adjacent to the disambiguated gnarly
  tier it refines) — the "below" the description's cross-reference points to.
- **Craft nits, all addressed pre-REVIEWED (none blocking).** (1) the pointer
  test was scoped to the `###` heading section so an incidental "spec-workflow"
  elsewhere can't satisfy it; (2) the module docstring gained a 104-01 note.
- **Process note (honest record).** During a capable-of-failing check the
  *uncommitted* `SKILL.md` deliverable was discarded by a `git checkout` on the
  tracked file (working-tree checkout is unrecoverable via git). It was
  reconstructed faithfully from context and re-reviewed fresh (compliance
  re-review `pass`, all 5 ACs). Byte-identity was not required — the tests
  assert normalized presence and the reviewers judged content. Follow-up
  discipline: never `git checkout` a tracked file carrying uncommitted work;
  use a filesystem copy for mutate-and-restore checks (captured to memory).

### Reconciliation sweep

Drift-prone surfaces checked (`updated` / `no-op` / `deferred`):

- **`docs/workflow.md` — canonical "Routing: spec-shaped vs bug-shaped" rule —
  `updated`.** bug-fix's SKILL bookend explicitly defers to this doc as
  canonical; leaving it silent while the SKILL grew a triage section would be
  the exact cross-surface inconsistency AC5 targets. Added a concise
  design-fidelity paragraph (spec-shaped, routes to the spec spine, links
  ADR-0049, points to the triage section). Proportionate, not a second detailed
  home.
- **`docs/specs/071-design-review-pass/spec.md` — overview Slices table —
  `updated` (closed-spec drift, [ADR-0010](../../decisions/adr-0010-amendment-scope-records-vs-live-prose.md)).**
  Surfaced during grounding: the table showed `071-01` `IN_PROGRESS` while the
  spec frontmatter and the slice file both read `DONE`. Corrected the stale
  derived-status cell inline (git history is the audit trail); not a decision
  change, so no amendment record.
- **bug-fix `## Routing — bug-shaped vs spec-shaped` bookend — `no-op`.** It
  points to `docs/workflow.md` as canonical and stays general; the new
  `### Design-fidelity triage` section is the detailed home, so no duplication
  is added here.
- **`docs/inbox.md` design-eval items — `no-op` (not resolved; cross-referenced).**
  The parked `design-conformance / visual-oracle` (2026-06-11) and `jobs`
  (2026-06-10) entries are the *measurement / eval* siblings to this *routing*
  ruling; ADR-0049 explicitly leans on that rail (spec 071 + servo `design-eval`)
  but does not resolve those parked shapes. Left in place.
- **`docs/architecture.md` — `no-op`.** No module boundary or public contract
  changed; the decision is recorded in ADR-0049.
- **`docs/conventions.md` — `no-op`.** No convention rule introduced; the ruling
  lives in the ADR + the bug-fix read-surface (and conventions edits are
  approval-gated regardless).
