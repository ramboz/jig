---
status: READY_FOR_IMPLEMENTATION
dependencies: [096-01]
last_verified: 2026-07-22
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-02 — update-subcommand

**Goal:** `decisions.py update` revises an already-recorded entry through the
helper, re-running 096-01's routing check against the **revised** text. This is
the slice that closes the case #121 actually reported — a decision that was
bounded when written and load-bearing after it was re-priced.

**DoR:**
- ✅ 096-01 is DONE and exports the evaluator as an importable pure function
  (096-01 AC8).
- ✅ The gap is real and probed: `add_lightweight` is append-or-no-op keyed on
  normalized `(date, title)` (`decisions.py:272-273`); there is no edit, no
  delete, no `--force`. Revising means hand-editing markdown, which
  `SKILL.md:129-131` and `decision_scan.py:365` both tell the agent never to do.
- ✅ Spec 083's own OQ2 (`083/spec.md:467-471`) anticipated adding a
  `**Commit:**` SHA retroactively and left no way to do it. This slice supplies
  the path it assumed.

**Acceptance Criteria:**

1. **An entry can be revised in place.** `update --title "<existing>"` with any of
   `--decision`, `--context`, `--scope`, `--commit` rewrites those fields on the
   matching entry and leaves every other entry, the file's heading structure, the
   routing rubric, and the `## Template` fence byte-identical.
2. **Omitted fields are preserved, not blanked.** Passing only `--commit` leaves
   Decision / Context / Scope exactly as they were. This is OQ2's case, and a
   revision helper that silently drops the fields you did not mention is worse
   than the hand-edit it replaces.
3. **The routing check re-runs against the merged result.** The gate evaluates
   the entry as it will read *after* the update — existing fields plus new ones —
   not the new fields alone. A revision that adds rejected alternatives to a
   decision whose existing text is load-bearing must flag, which is exactly
   #121's step 3.
4. **A flagged update writes nothing and names `promote`.** Same refusal shape as
   096-01 (matched groups, `ADR_TRIGGER` verbatim, non-zero exit, no write) —
   but the remedy it names is `decisions.py promote` (096-03), because the entry
   already exists and re-routing it is a promotion, not a fresh `adr.py new`.
   Until 096-03 lands, the message names the manual route; the wording is
   revisited in 096-03 rather than shipped stale.
5. **`--confirm-lightweight` and `JIG_DECISION_ROUTING_GATE=0` behave exactly as
   in 096-01**, including the same one-event telemetry on the env-var path and
   none on the flag path. One gate, one contract, two call sites.
6. **A missing entry is a loud refusal.** `update --title` naming no existing
   entry exits non-zero, writes nothing, and says so — it must never silently
   append a new entry, which would turn a typo'd title into a duplicate record.
7. **Title matching reuses the existing normalization.** Case- and
   whitespace-insensitive, via the same `_normalize` the idempotency key already
   uses (`decisions.py:193-199`), so `update` and `add-lightweight` agree on what
   "the same entry" means. An optional `--date` disambiguates when one title was
   used on two dates.
8. **Ambiguous matches refuse rather than guess.** If `--title` (without
   `--date`) matches more than one entry, exit non-zero listing the matching
   dates and asking for `--date`.
9. **The illustrative example and the `## Template` fence are not addressable.**
   `update` must refuse to target the worked example at `:51-55` or the
   `### [Date] — [Short title]` line inside the fence — they are documentation,
   not records, and `_existing_keys` deliberately keys them
   (`decisions.py:202-215`).

**Edge cases covered explicitly:**

- An entry with no `**Commit:**` line gains one cleanly (field added, not
  replaced) — the OQ2 path.
- An entry that is the file's last block, and one that is followed by another
  entry: the rewrite must not swallow the following `### ` heading or the
  trailing newline.
- A `--decision` value containing markdown that looks like a heading must not
  corrupt the file's structure.
- An unchanged update (every supplied field already equal) is a reported no-op,
  not a rewrite — mirroring `add-lightweight`'s idempotency contract.

**Anti-horizontal-phasing check:** with 096-01 and this slice in, the four-step
sequence #121 reported is stopped at step 3 end-to-end: the revision goes
through the helper, the check sees the corrected text, and the operator is told
the entry no longer belongs where it is.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] A test replays #121's four-step sequence end-to-end (record bounded →
      revise with corrected cost and rejected alternatives → flagged) so the
      reported case has a named regression test.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`).
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
