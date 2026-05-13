# Tasks: Slice 009-01 — close-out-section-recognition

## Ordered tasks (TDD)

- [ ] **T1** — Write the failing regression test in `skills/slice-land/test_land.py`:
      `PrepareReportTests.test_close_out_boxes_excluded_from_dod_count`. Synthetic
      slice with 4 ticked DoD boxes + 2 unticked close-out boxes; expect
      `(True, 4, 4)` from `check_dod`.
- [ ] **T2** — Verify the test fails (because today's `check_dod` counts all 6).
- [ ] **T3** — Edit `skills/slice-land/land.py`: add `CLOSE_OUT_RE` and the
      truncation logic in `check_dod`.
- [ ] **T4** — Run `python3 -m unittest discover skills/slice-land/`. New test passes;
      31 existing pass.
- [ ] **T5** — Edit `skills/slice-land/SKILL.md`: add the close-out convention
      under a new heading (probably between "Test-check warnings" and "When to invoke").
- [ ] **T6** — Edit `docs/specs/008-migrate-existing-project/spec.md`: move two
      post-DONE DoD items into a new `### Close-out (post-DONE)` subsection. Leave
      the deviation log and anti-horizontal-phasing check unchanged.
- [ ] **T7** — Run `python3 skills/slice-land/land.py prepare
      docs/specs/008-migrate-existing-project/spec.md "008-01" --mode direct`.
      Expect: Status DONE-blocker still present (008-01 is RECONCILED, not DONE),
      DoD `6/6` ticked (no longer 6/8), exit code 1 (Status is still a blocker).
      That's the right state — DoD is unblocked, but DONE transition is the
      user's call.
- [ ] **T8** — Transition 009-01 IN_PROGRESS.
- [ ] **T9** — Run `land.py prepare docs/specs/009-dod-close-out-separation/spec.md
      "009-01" --mode direct`. Expect: Status IN_PROGRESS blocker (009-01 not yet
      DONE), DoD `0/6` (work just started, no boxes ticked yet). That's fine — it
      proves the new convention works on a slice using it.
- [ ] **T10** — Build implementation-review prompt via `review.py`; spawn reviewer.
- [ ] **T11** — Address findings.
- [ ] **T12** — Write deviation log under 009-01.
- [ ] **T13** — Transition REVIEWED → RECONCILED.
- [ ] **T14** — Build reconciliation-review prompt; spawn reviewer.
- [ ] **T15** — Transition RECONCILED → DONE.
- [ ] **T16** — Regen status board.
- [ ] **T17** — Update CLAUDE.md (hot-cache + sprint focus).
- [ ] **T18** — Commit: `feat(slice-land): exclude Close-out subsection from
      DoD count (slice 009-01)`.
- [ ] **T19** — Now close 008-01: run `land.py prepare` (expect 4/4 modulo the
      Tests `[?]` warning); transition 008-01 RECONCILED → DONE; regen status
      board; CLAUDE.md update; commit.
