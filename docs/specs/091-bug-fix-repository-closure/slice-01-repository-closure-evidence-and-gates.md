---
status: REVIEWED
dependencies: []
last_verified:
# arch_review: true  # set to true when this slice changes module
#                    # boundaries, public contracts, or architecture-
#                    # shaped concerns (triggers arch-review pass).
# design_review: true  # set true when this slice ships UI gated by an external
#                      # design-fidelity eval (attest-only; ADR-0014/0022).
claimed_by: claude/spec-091-repository-closure
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 091-01 — repository-closure evidence and gates

**Goal:** Make repository-wide reuse/history discovery and call-site closure a
durable, reviewable part of every newly created standard or gnarly bug fix.

**DoR:**
- ✅ ADR-0037 is accepted.
- ✅ Legacy (pre-schema) bug-record compatibility behavior is covered by
  fixtures — keyed to an explicit creation-time `closure_schema:` frontmatter
  marker, not to section presence/absence and not to an enumerated record range.

**Acceptance Criteria:**

1. **New records carry closure evidence sections.** `bug.py new` emits prompts
   for equivalent logic, history, affected call sites, reuse decision, and
   post-fix call-site disposition.
2. **The fixing gate requires the pre-fix inventory.** New standard/gnarly
   records cannot transition from `ROOT_CAUSED` to `FIXING` until each prompt
   has substantive evidence. "New" vs "legacy" is decided by an explicit
   creation-time frontmatter marker (a `closure_schema:` field stamped by
   `bug.py new`), **never** by section presence/absence — so a new record that
   omits the closure headings still fires the gate (evasion-by-omission is not
   exempt), while an unmarked pre-schema record follows the legacy compatibility
   path and remains transitionable.
3. **The reviewed gate requires closure.** Each affected call site is accounted
   for as changed, tested, or intentionally unchanged before `REVIEWED`.
4. **Review judges repository closure.** The bug-review prompt checks reuse,
   history, missed convergent paths, and the recorded disposition—not merely
   the local regression test.
5. **The skill is tool-neutral.** Guidance prefers a configured semantic index
   but provides targeted search and git-history commands as the portable floor.
6. **The equivalent-logic prompt is an effort-and-protocol standard, not a
   completeness standard.** A record satisfies it by showing the search actually
   run — which behavioural/contract terms were tried (more than one spelling),
   what `git log`/`git blame` on the touched surface returned, which sibling
   paths were inspected — and *may then* record the residual as an assumption
   when the set is not closable by name search. Consistent with
   [ADR-0052](../../decisions/adr-0052-grounding-enumeration-for-universal-claims.md),
   that assumption disposition **is accepted** for the claim; what fails the
   gate is a bare "none found" or an "assumption" with no executed protocol
   behind it. Where the inventory makes a *closable* negative claim (call sites
   of a known symbol), ADR-0052's enumeration rule governs unchanged and the
   guidance **reuses** its existing wording
   ([`SKILL.md` grounding section](../../../skills/bug-fix/SKILL.md)) rather
   than restating a weaker variant — a drift test pins them to one source.
   Tests must cover both: a protocol-bearing assumption answer **passes**, a
   bare "none found" **fails**.
7. **Vacuity is observable.** The recorded inventory is machine-samplable well
   enough to classify an equivalent-logic answer as protocol-bearing versus
   bare/boilerplate, so ADR-0037's leading kill indicator can be evaluated from
   the records without waiting for a missed-defect signal. The sampler keys on
   the `closure_schema:` marker (AC2), not section presence, so it never
   mistakes an unmarked legacy record for a vacuous new one.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [x] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### For `kind: spike` slices

When the slice's frontmatter has `kind: spike`, the body carries four
extra labelled blocks alongside the standard Goal / DoR / AC / DoD
scaffolding. Spike slices are timeboxed investigation, not feature
work — they reduce an unknown before committing to a design.

```markdown
**Question:** _One sentence stating the open question. Set at DRAFT._

**Time-box:** _Explicit budget — e.g., "1 day", "4 hours". Set at DRAFT._

**Findings:** _Bullet evidence collected during the spike. Filled
during IN_PROGRESS._

**Outcome:** _One of: `ADR-NNNN created` / `spec NNN-NN unblocked` /
`abandoned (reason)`. Multiple outcomes separated by `;`
(e.g., `ADR-0007 created; spec 030-02 unblocked`). Set at DONE._
```

`spec_lint.py` validates the `kind:` enum (allowed values: `spike`,
`feature`) and soft-warns when a `kind: spike` slice is missing any of
the four labels. Mid-flight spikes legitimately have empty Findings /
Outcome, so this is a warning, not a hard error.

See `skills/spec-workflow/SKILL.md` (Spike slices subsection) and
`docs/spec-workflow/spidr-primer.md` for the always-nested rule (spike
slices live inside a real spec, never as standalone `docs/spikes/`
artifacts) and the abandoned-outcome manual-reshape failure mode.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry — drop facts derivable from the
      spec dir + status board, migrate load-bearing per-slice
      invariants to the status board Notes column, keep at most a
      one-liner only for cross-cutting facts. If the spec is still
      in flight (other slices DRAFT / READY / IN_PROGRESS), leave
      the entry. If this slice introduces a new skill, add or
      update its row in the Skills table.

**Anti-horizontal-phasing check:** After this slice, a bug cannot move from
diagnosed to reviewed without durable evidence that existing logic and every
identified call site were considered.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **Frame-critique reshaped the ADR and spec before any code.** ADR-0037 went
   through four independent frame-critique passes (three `needs-changes`, then
   `pass`); the spec slice through two (one `needs-changes`, then `pass`). The
   substance of the decision (Option B) was preserved, but the *frame* was
   materially strengthened: the parser gate was reframed as a deliberateness
   gate (ADR-0011 lineage) with `bug-review` as the discovery-quality backstop
   grounded in ADR-0052's burden shift; the compatibility marker was moved from
   "section-absence = legacy" (self-defeating) to an explicit creation-time
   `closure_schema:` frontmatter field; and paired leading kill indicators
   (vacuity + effect) were added. The recorded verdicts live in
   `docs/decisions/reviews/adr-0037-frame-critique.md` and
   `reviews/slice-01-frame-critique.md`. This is the intended pre-implementation
   value of the frame pass, not a deviation from plan — but it did enlarge the
   spec's ACs (6 and 7 were added mid-critique).

2. **Compatibility keyed to a stamped marker, not the enumerated range.** The
   original spec said "bugs 001-010"; the corpus had already grown to 001-033.
   Rekeyed to `closure_schema:` presence (additive — verified no record 001-033
   carries any schema field and `bug.py`'s template emitted none), so
   legacy-by-omission is distinguishable from evasion-by-omission.

3. **AC6 realised as an effort-and-protocol floor.** The parser rejects only a
   *bare* negative verdict (`_is_bare_negative`); an honest "not closable —
   assumption" WITH a recorded protocol passes. The completeness judgment lives
   in `build_bug_review_prompt`, not the parser — honouring ADR-0037's explicit
   "parser enforces presence, reviewer judges quality" split and avoiding the
   bug-005 shape-gate trap.

4. **AC7 satisfied via module-level helpers, not a new CLI.** "Machine-samplable"
   was met by factoring the parsing into named module-level helpers
   (`_is_closure_schema_record` / `_labeled_blocks` / `_is_bare_negative`) and
   demonstrating a marker-keyed vacuity/effect sampler built only from them in
   `Spec091VacuitySamplingTests`. These stay **underscore-prefixed and private
   to `bug.py`** — no new public API or module boundary — which is why the
   architecture sweep row is a `no-op`. No `usage.py`-style sampler command was
   shipped; the kill indicator is computable from records with these helpers,
   and promoting them to a public surface is deferred until a real sampler
   consumer exists.

5. **Reviewer findings folded back.** Compliance + craft both returned `pass`.
   Their converged non-blocking nits were applied post-review: a comment noting
   the REVIEWED gate is deliberately not tier-scoped (trivial records don't
   persist past triage); the bare-negative floor widened to strip trailing
   punctuation; and two robustness tests (decorated-verdict, inner-bold-label).

6. **Reconciliation review corrected two sweep dispositions.** The first sweep
   draft claimed `docs/specs/README.md` was already `updated` ("regenerated to
   091-01 → DONE") — structurally impossible, since board regen is a post-DONE
   close-out step and the board still read DRAFT at sweep time; corrected to
   `deferred (close-out)`. It also marked `docs/refinement-todo.md` a blanket
   `no-op` after checking only the leanness item, missing a now-stale
   "ADR-0037 … Proposed, not built" cross-reference in the unlanded-work-defect
   entry; corrected inline per the ADR-0010 live-prose norm and the row changed
   to `updated`. Recording this because the failure mode generalises: a sweep
   must not mark a not-yet-run close-out action as done, and a blanket `no-op`
   on a doc means *the whole doc* was checked, not one item in it.

   A second reconciliation pass caught three more, all folded in: `AGENTS.md`
   was named in an `updated` primer row but never actually edited (the host-
   neutral primer is kept lockstep with `CLAUDE.md`, and still asserted "ADR
   Proposed, gates don't exist yet"); spec 091's **own** overview banner still
   read "recorded, not yet built" with no sweep row covering it; and the
   deviation log described the AC7 sampler helpers as "public" while the
   architecture row justified `no-op` by calling them private. **Close-out
   ordering is now consistent:** the two *derived* surfaces — the status board
   and the glossary — are both `deferred (close-out)` and regenerate after
   `RECONCILED → DONE`, while *live prose* (primers, spec banner,
   refinement-todo cross-reference) is corrected inline now, per ADR-0010. The
   earlier draft mixed the two, deferring the board while eagerly claiming the
   primer.

7. **Plan adherence.** No drift from the single-vertical-slice shape. Host
   packages regenerated (`bug.py` / `SKILL.md` / `review.py` ship to both Claude
   and Codex hosts); drift check clean. The pre-existing flaky `plugin.json`
   host-drift (bug 008 / issue #95) surfaced once during a suite run and is
   unrelated to this change.

### Reconciliation sweep

Record the drift-prone surfaces checked during reconciliation. The transition
gate only requires this subsection to exist; the reconciliation reviewer judges
whether coverage and rationales are honest.

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Root README is product-facing; the bug-fix closure gate is internal lifecycle behavior — no front-door change. |
| `docs/specs/README.md` | `deferred (close-out)` | Status-board regen is a post-DONE close-out step; at sweep time the slice is REVIEWED and the board still reads DRAFT. Regenerated by `workflow.py status-board` after the final `RECONCILED → DONE` transition, not before. |
| `docs/product-vision.md` | `no-op` | No scope/positioning change; this deepens an existing lifecycle gate, does not add a product surface. |
| `docs/architecture.md` | `no-op` | No module-boundary or public-contract change; new helpers are private to `bug.py`, the gate reuses the existing `transition_bug` env-gate pattern. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | **Both** primers updated in lockstep (`CLAUDE.md:13` and `AGENTS.md:13`): 091 moved from "recorded, not yet built / ADR Proposed" to shipped, kept **compressed** per spec 025-01 — the per-slice invariants (marker-keyed exemption, the two gate points, the effort-and-protocol floor) live in the status-board Notes column, not the primer. `templates/CLAUDE.md.template` unaffected (scaffold source, not project state). The remaining `CLAUDE.md`/`AGENTS.md` divergence on line 13 is pre-existing and unrelated to this slice. |
| `docs/specs/091-bug-fix-repository-closure/spec.md` (own overview) | `updated` | The overview banner still read "Status: recorded, not yet built … ADR-0037 is Proposed … Left DRAFT deliberately" — stale live prose once the slice shipped; corrected to "Status: built" naming what 091-01 delivered (ADR-0010 live-prose norm). |
| `docs/memory/glossary.md` | `deferred (close-out)` | The primer introduces **Bug-fix repository closure** as a bold term, and the primer's contract is that full definitions live in the glossary. The glossary entry is written at close-out via `/jig:memory-sync` together with the board regen, so both derived surfaces move once, after DONE. |
| `docs/inbox.md` | `no-op` | No parked item resolved by this slice. |
| `docs/refinement-todo.md` | `updated` | The "leanness lens" item is a distinct concern, not resolved here. But the "how to encode a defect introduced by unlanded work" item cross-referenced ADR-0037 as "Proposed, not built" — now stale live prose since this slice built it; corrected inline to "Accepted; shipped via spec 091-01" (ADR-0010 live-prose norm). No new deferral introduced. |
| `docs/memory/**` | `no-op` | `learnings.md` gets no new dead-end; the frame-critique reshape is captured in the deviation log + ADR, not a learning. `/jig:memory-sync` run at session close. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0037 flipped Proposed → Accepted and re-indexed (`adr.py index`); dependencies widened to include ADR-0011 and ADR-0052. |
| `docs/bugs/**` (records + board) | `no-op` | No existing bug record edited; existing records 001-033 are legacy (unmarked) and remain transitionable by construction. The template change only affects records created after this lands. |
| Additional live prose / generated templates touched by this slice | `updated` | `hosts/claude/**` and `hosts/codex/**` regenerated for `bug.py` / `SKILL.md` / `review.py`; drift check clean. |
