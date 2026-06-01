---
status: DONE
dependencies: []
last_verified: 2026-06-01
---

## Slice 048-05 — seed-reference-spec

**Goal:** Make a freshly scaffolded project open with a complete,
`DONE` worked-example spec so the model has a faithful pattern to
imitate from turn one. Closes the **cold-start cliff**: jig enforces
almost nothing via hooks, so a blank scaffold gives the model neither
enforcement *nor* an example to follow, and it skips the workflow. A
seeded reference spec supplies the example.

**DoR:**
- ✅ Scaffold-init already emits the docs tree, `CLAUDE.md`, and an
  (empty) `docs/specs/README.md` status board.
- ✅ Slice template (`templates/docs/specs/slice-template.md`) and the
  status-board template are the source shapes to mirror.
- ✅ Coordinated with spec 046 (scaffold artifact fidelity) — the seed
  must not leak `${CLAUDE_PLUGIN_ROOT}` or source-checkout paths; it is
  scaffold-mode output that reads correctly inside the target tree.

**Acceptance Criteria:**

1. **A complete worked-example spec is emitted.** Scaffold-init produces
   `docs/specs/001-adopt-jig/spec.md` and
   `docs/specs/001-adopt-jig/slice-01-bootstrap.md`, with the slice at
   `status: DONE` and carrying the full slice shape: Goal, DoR,
   Acceptance Criteria (that assert the scaffold artifacts exist), DoD,
   anti-horizontal-phasing check, and a short, real deviation log
   (e.g. "Tier 2 offered but declined; `people.md` not created — solo").
   **Greenfield-only (per Clarification Q1):** the seed is emitted only
   when `docs/specs/` is otherwise empty; if any spec already exists
   (migrate path, `--force` re-scaffold), the seed is skipped silently
   and never overwrites the user's work. The emitted `001-adopt-jig` is
   real, permanent project history (per Q3), not a labelled-deletable
   example.
2. **The DoD is honest by construction.** Every ticked box is true of a
   deterministic scaffold. Review-related boxes are satisfied by the
   **deterministic scaffold-completion check** (slice 048-06 /
   `verify_install.py` scaffold checks) and are explicitly annotated as
   such — e.g. `[x] Verified by scaffold-completion check (deterministic
   template output; first subagent review is your spec 002)`. The seed
   **must not** contain a fabricated `reviewer` subagent verdict, because
   no subagent review of deterministic output occurred. Reviewing
   template copies with a subagent would be rubber-stamp theater and
   would teach the exact box-ticking-without-evidence behavior this spec
   exists to prevent.
3. **The seed lints clean.** `python3 scripts/spec_lint.py --all` passes
   on a freshly scaffolded project including the seed. The worked example
   must satisfy jig's own structural rules — a malformed seed would teach
   malformed specs.
4. **The status board is populated, not empty.** The emitted
   `docs/specs/README.md` contains a real row for `001-01 — bootstrap`
   marked `DONE`, with a Notes entry flagging it as a worked example
   ("review boxes satisfied by deterministic completion check").
5. **A next-step hand-off exists and is honest.** Scaffold-init emits
   `docs/specs/002-first-spec/spec.md` as a `DRAFT` stub that clearly
   reads "replace this with your first real spec — run
   `/jig:spec-workflow`; spec 001 above shows the shape." It is `DRAFT`,
   **not** `READY_FOR_IMPLEMENTATION`: an empty placeholder is not ready,
   and marking it ready would repeat the dishonesty this spec opposes.
   The stub lints clean as a DRAFT.
6. **The seed stays out of always-loaded context.** The worked example
   lives under `docs/specs/` (read on demand). `templates/CLAUDE.md.template`
   gains at most a one-line Active-specs pointer to `001-adopt-jig`, never
   the seed body — same prompt-load discipline as slice 048-03.
7. **Tests cover the emitted seed.** Scaffold fixtures (new or extended)
   assert: the two `001-adopt-jig` files exist with `status: DONE` on the
   slice; the slice's review-pass line references the deterministic check
   and contains no fabricated subagent verdict string; the `002-first-spec`
   stub exists at `status: DRAFT`; the status board row is present; and
   the freshly scaffolded tree passes `spec_lint.py`.

**Deferred to a follow-up slice (out of scope for 048-05, per Clarification Q4):**

- **Seed ADR demonstrating the ADR form.** Emitting
  `docs/decisions/adr-0001-adopt-jig.md` (`Accepted`) plus a decisions
  index row would give a new project a worked ADR shape too — but it is
  not part of the core "land 1 reference spec" need. Park it for a
  follow-up slice if signal warrants; do not build it here.

**DoD:**

> **Anti-pre-tick reminder.** Only `workflow.py transition` auto-ticks
> the two review-passed boxes (slice 003-04). Every other box is ticked
> only after its evidence exists.

- [x] All ACs pass; full test suite green (no regressions). _(1445 tests,
      OK, 3 skipped; 8 new seed tests.)_
- [x] Implementer test coverage exercises each AC with at least one
      fixture. The honesty pin (AC #2) and the lint pin (AC #3) are
      covered explicitly.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`. _(Compliance verdict: pass; two non-blocking findings.)_
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred
      during implementation. _(No new deferrals — the seed ADR was already
      parked in this slice's body per Clarification Q4.)_

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      _(Notes column carries the greenfield-only + honesty-pin invariants.)_
- [x] `CLAUDE.md` hygiene per spec 025-01 rule. _(N/A — spec 048 is still
      in flight, 048-01…04/06 not DONE; no Active-specs entry to compress.)_

**Anti-horizontal-phasing check:** After this slice lands, a developer
who runs `/jig:scaffold-init` opens a project that already contains a
complete `DONE` worked example *and* a clear next step — so the model
imitates the spec-driven loop from the first turn instead of coding
straight past it. End-to-end observable; one slice.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Seed templates live under `templates/docs/specs/seed/`** and are
   emitted by a dedicated `_emit_seed_spec()` in `scaffold.py`, excluded
   from the generic doc rglob so the greenfield guard can gate them. The
   guard (`_specs_dir_has_content`) keys on any `*/spec.md` under the
   target `docs/specs/` and errs toward "has content" (skip the optional
   seed) rather than risk overwriting a real user spec. Emitted in both
   default and `--plugin-only` modes (docs ship in both).

2. **`test_draft_markers` adjusted (approach deviation).** The pre-existing
   test asserted every scaffolded `docs/**/*.md` carries the
   `Status: Draft (wizard-generated)` marker. The seed's `001-adopt-jig`
   (DONE) and `002-first-spec` (a DRAFT spec, not a wizard-draft doc)
   intentionally omit that marker — dressing the DONE worked example as a
   draft would violate AC #2's honesty pin. The two seed dirs were
   excluded from that test; all other docs + the status-board README still
   carry the marker. No production behavior changed beyond seed emission.

3. **Craft nit (a) — fixed.** The bootstrap template's DoD boxes 3 and 4
   originally read identically. Reworded so box 3 ("reviewer-subagent
   review — not applicable") and box 4 ("implementation review — satisfied
   by the scaffold-completion check") differ while both stay honest. The
   honest framing — that no subagent reviewed deterministic output — is
   preserved; a "Reviewed by reviewer subagent [x]" claim was deliberately
   NOT restored, as it would reintroduce the dishonesty the slice opposes.

4. **Craft nit (b) — fixed.** The seed's AC #5 previously instructed
   `python3 scripts/spec_lint.py --all`, but scaffolded projects do not
   ship `spec_lint.py`. Reworded to state the seed is well-formed and was
   validated at scaffold time, noting structural linting runs in jig's
   dev/CI environment. Removes a command that would not resolve in the
   target (overlaps spec 046's "commands must resolve in scaffold mode").

5. **AC #3 interpretation (reviewer reconciliation note).** "Passes
   `spec_lint.py` from inside a freshly scaffolded project" was
   implemented as "the seed *content* satisfies spec_lint's rules,"
   verified by running the source `spec_lint.py --all` with `cwd` pointed
   at a scaffolded tree (exit 0). The verb-shipping question (should the
   scaffolded project be able to run the linter itself?) is routed to
   spec 046/047, not this slice.

6. **Open findings carried forward (non-blocking):**
   - **Re-scaffold board overwrite (reviewer Low, pre-existing).** On a
     `--force` re-scaffold of a non-greenfield project, the generic empty
     `README.md.template` is copied before the seed guard returns early,
     so it overwrites an existing status board. Predates this slice; the
     seed guard correctly preserves an already-seeded `001-adopt-jig`.
     Filed to `docs/inbox.md` as a `scaffold/force-rescaffold/board-overwrite`
     watch-item rather than fixed here.
   - **Fabricated-verdict test guard is a brittle string match (reviewer
     Medium).** `test_scaffold.py` forbids four hard-coded `…: pass`
     phrasings; a differently-worded fabricated verdict could slip past.
     Adequate for the current clean template; filed to `docs/inbox.md` as
     `scaffold/test/verdict-guard-robustness`.

## Clarifications

### Q1: What should the seed do if the target already has `docs/specs/` content (e.g. a migrate path or `--force` re-scaffold)?
_(category: Edge Cases & Failure Modes)_

Skip if specs exist. Only emit the seed into an empty `docs/specs/`. If
any spec already exists, skip the seed silently — never overwrite the
user's work. Greenfield-only, matches scaffold-init's existing refusal
posture.

### Q2: The seed annotates its review box as "verified by the completion check." Should slice 048-05 formally depend on 048-06?
_(category: Dependencies & Blockers)_

Self-contained, no hard dep. The seed's annotation references existing
`verify_install.py` scaffold checks (which already ship), so 048-05 can
land before 048-06. Keeps the two slices independently shippable.

### Q3: Is the seeded `001-adopt-jig` permanent project history, or a labeled example the user is expected to delete?
_(category: Scope & Boundaries)_

Permanent honest history. Scaffolding genuinely was the first unit of
work, so `001-adopt-jig` stays as real project history. Maximizes
lasting momentum; nothing to clean up.

### Q4: Is the seed ADR-0001 (optional AC #8) in scope for slice 048-05, or split to a follow-up?
_(category: Scope & Boundaries)_

Split to a follow-up. Keep 048-05 focused on the reference spec +
hand-off. Seed ADR demonstrates the ADR form but isn't part of the core
"land 1 reference spec" need — defer to a follow-up slice if signal
warrants.

### Coverage summary

| Category | Status |
|---|---|
| Scope & Boundaries | Resolved (Q3, Q4) |
| Acceptance Criteria Testability | Clear |
| Dependencies & Blockers | Resolved (Q2) |
| Non-functional Requirements | Clear |
| Edge Cases & Failure Modes | Resolved (Q1) |
| Terminology Consistency | Clear |
