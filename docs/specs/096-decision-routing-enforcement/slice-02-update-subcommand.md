---
status: READY_FOR_IMPLEMENTATION
dependencies: []
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 096-02 — update-subcommand

**Goal:** `decisions.py update` revises an already-recorded lightweight-decision
entry **through the helper**, instead of the hand-edit every surface forbids.
This is the code path the reported case never had — the moment a decision is
revised is where [#121](https://github.com/ramboz/jig/issues/121) actually broke,
and today there is no way to revise except by editing markdown the helper cannot
see.

`update` does **not** judge routing — that judgement is the assistant's, prompted
by 096-01's `SKILL.md` guidance, per
[ADR-0039](../../decisions/adr-0039-decision-routing-gate.md). This slice gives
that judgement a command to act through: revise here, or (when the decision has
grown ADR-worthy) `promote` (096-03). A code gate on this path was the rejected
mechanism.

**DoR:**
- ✅ The gap is real and probed: `add_lightweight` is append-or-no-op keyed on
  normalized `(date, title)` (`decisions.py:272-273`); there is no edit, no
  delete, no `--force`. Revising means hand-editing markdown, which
  `SKILL.md:129-131` and `decision_scan.py:365` both tell the agent never to do.
- ✅ Spec 083's own OQ2 (`083/spec.md:467-471`) anticipated adding a
  `**Commit:**` SHA retroactively and left no way to do it. This slice supplies
  the path it assumed.
- ✅ `render_entry` (`decisions.py:218`) is the canonical emitter this slice must
  round-trip against.

**Acceptance Criteria:**

1. **An entry can be revised in place.** `update --title "<existing>"` with any of
   `--decision`, `--context`, `--scope`, `--commit` rewrites those fields on the
   matching entry and leaves every other entry, the file's heading structure, the
   routing rubric, and the `## Template` fence byte-identical.
2. **Omitted fields are preserved, not blanked.** Passing only `--commit` leaves
   Decision / Context / Scope exactly as they were. This is OQ2's case, and a
   revision helper that silently drops the fields you did not mention is worse
   than the hand-edit it replaces.
3. **The rewrite round-trips `render_entry`.** The revised block is byte-identical
   to what `render_entry` would emit for the merged fields — one blank line
   between fields, `**Commit:**` only when present — so `add-lightweight` and
   `update` produce indistinguishable entries. A round-trip test
   (`render_entry` → parse → same fields) guards the parser.
4. **A missing entry is a loud refusal.** `update --title` naming no existing
   entry exits non-zero, writes nothing, and says so — it must never silently
   append a new entry, which would turn a typo'd title into a duplicate record.
5. **Title matching reuses the existing normalization.** Case- and
   whitespace-insensitive, via the same `_normalize` the idempotency key already
   uses (`decisions.py:193-199`), so `update` and `add-lightweight` agree on what
   "the same entry" means. An optional `--date` disambiguates when one title was
   used on two dates.
6. **Ambiguous matches refuse rather than guess.** If `--title` (without
   `--date`) matches more than one entry, exit non-zero listing the matching
   dates and asking for `--date`.
7. **The illustrative example and the `## Template` fence are not addressable.**
   `update` must refuse to target the worked example (`### 2026-01-15 —
   Onboarding CTA copy…`) or the `### [Date] — [Short title]` line inside the
   fence — they are documentation, not records. `_existing_keys` deliberately
   keys both (`decisions.py:202-215`), so a narrower "real entry" notion is
   needed here; introduce it cleanly (096-03 and 096-04 reuse it).
8. **No routing gate, no routing flag.** `update` refuses on *matching* grounds
   only (missing / ambiguous / documentation), never on the decision's content,
   and carries no `--confirm-lightweight`. Routing is the assistant's judgement
   (096-01) plus the advisory lint (096-04). This AC is a guard against a
   reviewer re-adding the rejected gate.

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

**Anti-horizontal-phasing check:** after this slice a recorded decision can be
revised through the helper end-to-end — the precondition both the judgement
guidance (096-01) and `promote` (096-03) rely on. It is not "a parser exists and
a later slice will call it".

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions) on Python 3.9.
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] Host packages regenerated (`scripts/build_host_packages.py`).
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.
