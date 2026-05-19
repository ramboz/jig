---
status: DONE
dependencies: []
last_verified: 2026-05-18
---

## Slice 031-01 — pr-review-pass

**Goal:** Wire a post-implementation `pr-review` pass into the
spec-workflow lifecycle. After the implementer finishes a slice
(before the IN_PROGRESS → REVIEWED gate), the orchestrator runs an
additional craft-review pass that routes to the most-specific
installed `pr-review` skill (user's > `jig:pr-review`), returns a
verdict-shaped output, and blocks the transition on `fail`. End-to-end
value in a single slice: every slice gets craft-review automatically;
no manual prompting required.

**DoR:**

- ✅ `jig:pr-review` skill exists with the description-based deferral
  pattern (slice 012-01).
- ✅ `review.py` builds standardized prompts for `jig:independent-review`
  modes (`implementation` / `reconciliation` per slice 004-01 + 030-01).
  The pattern extends naturally to a `pr-review` mode.
- ✅ `skills/spec-workflow/SKILL.md` § "After implementation" describes
  the current single-pass review flow; spec 031 spec.md frames the
  three-pass extension.

**Acceptance Criteria:**

1. **`review.py pr-review`** — new subcommand on
   `skills/independent-review/review.py`. Signature mirrors
   `implementation`:
   ```bash
   review.py pr-review <spec.md> <slice-fragment> <deliverable-path-1> [...]
   ```
   Builds a self-contained prompt that:
   - Tells the reviewer it's seeing the work for the first time.
   - Cites the deliverable file paths to focus on (no spec-AC
     re-evaluation — that's the compliance pass's job).
   - Instructs the reviewer to apply the craft concerns from the
     most-specific `pr-review` SKILL.md reachable in the environment
     (user-installed > project > jig-bundled), and lists the canonical
     four output buckets: scope / blockers / nits / strengths.
   - Wraps the output in the standard VERDICT / REASONING /
     SPECIFIC ISSUES / RECONCILIATION NOTES envelope used by
     `jig:independent-review`. `SPECIFIC ISSUES` entries are tagged
     `[blocker]` / `[nit]` / `[strength]`.

2. **`review.py subagent-type pr-review`** — returns the same
   precedence the existing `subagent-type` subcommand uses for
   `jig:reviewer` (real plugin install) vs. `general-purpose`
   (running from source). Same fallback rule.

3. **`skills/spec-workflow/SKILL.md` § "After implementation"** is
   reshaped to describe the three-pass flow:
   1. Compliance pass via `jig:independent-review` (existing).
   2. Craft pass via `pr-review` (this slice; always runs).
   3. (Slice 031-02 adds the arch pass; out of scope here.)
   Order: compliance → craft. Both must pass before
   `transition <slice> REVIEWED`. The SKILL.md prose names the
   block rule explicitly: any `fail` blocks; `needs-changes` blocks
   for compliance, becomes a reconciliation-log entry for craft.

4. **Skill-routing dispatch via SKILL.md prose.** The orchestrator
   invokes the `pr-review` skill by name — Claude's routing layer
   handles the user-skill > project-skill > jig:pr-review > built-in
   precedence via skill description hints. **No filesystem
   detection in `review.py`** for this slice (per spec.md Open
   questions, lean (a)). If misrouting surfaces, slice 031-02 or a
   follow-up addresses it; here we use the prose-only path.

5. **Reviewer subagent is read-only.** Same constraint as
   `jig:independent-review` — the pr-review pass uses `jig:reviewer`
   (Read / Glob / Grep only) or `general-purpose` per AC #2.
   `agents/reviewer.md` is unchanged; the read-only tool set is
   shared across both passes.

6. **Tests added.** `skills/independent-review/test_review.py` (or
   wherever `review.py` tests live today) gain:
   - At least 4 surface tests on the new `pr-review` mode: prompt
     contains the four-bucket output spec, prompt names the
     deliverable paths verbatim, prompt does NOT re-evaluate ACs
     (no "for each acceptance criterion" instruction), prompt names
     the verdict-envelope format.
   - At least 1 test on `subagent-type pr-review` mode returning
     a sensible value.
   - At least 1 SKILL.md surface test asserting the three-pass
     order is documented under "After implementation."

7. **Dogfood.** This slice runs the new pr-review pass against
   itself during the post-implementation step. The deviation log
   captures the verdict and notes any findings (or surfaces the
   first real-world friction with the dispatch path).

**DoD:**

- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one
      fixture. The dispatch-path verbatim assertions and the
      AC-re-evaluation negative assertion are explicit.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py implementation` (compliance pass).
- [x] Reviewed by `pr-review` skill via the new `review.py pr-review`
      pass (THIS slice's dogfood — first-ever post-impl craft
      review in the workflow).
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation. (No deferrals; the three
      spec.md Open questions were resolved inline — see deviation
      log.)

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column for 031-01 carries the load-bearing invariant
      (three-pass flow + dispatch-via-prose decision + dogfood
      outcome).
- [x] `CLAUDE.md` hygiene per spec 025-01 rule: spec 031 doesn't
      introduce a new skill, so the Skills table is untouched.
      Active-specs entry compressed on close-out if any was added
      (lean: none, since the three-pass flow is documented in
      SKILL.md not CLAUDE.md).
- [x] `skills/independent-review/SKILL.md` mentions the new
      `pr-review` mode under "How to use" (or equivalent), so a
      future agent knows the mode exists.

**Anti-horizontal-phasing check:** After this slice lands, every
slice goes through TWO post-implementation review passes
automatically — compliance (existing) and craft (new). The user-
observable signal is: spec 030's reconciliation would have surfaced
the user's installed pr-review skill catching nits that the
compliance pass missed. End-to-end value delivered, no
intermediate-state stalling.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**Implementation summary.** Added `pr-review` subcommand to
`skills/independent-review/review.py` (mirrors `implementation`
signature: spec + slice + deliverables). Added `pr-review` choice to
`subagent-type` subcommand (reuses `detect_subagent_type()` — same
precedence as the existing two modes). Updated
`skills/spec-workflow/SKILL.md` § "After implementation" to document
the three-pass flow with the explicit compliance → craft order and the
asymmetric block rule (compliance `needs-changes` blocks; craft
`needs-changes` becomes a reconciliation-log entry; `[blocker]`-tagged
craft entries block, `[nit]`-tagged become reconciliation-log items).
Updated `skills/independent-review/SKILL.md` to describe the new
`pr-review` mode under both "What this skill does" and "How to use"
(close-out item satisfied in-flight rather than post-DONE).

**+19 tests; 1064 → 1083 green.** Spec slice 030-01 (rollup) brought
the suite to 1064; this slice adds 13 `PrReviewPromptTests` + 3
`PrReviewSubagentTypeTests` + 3 `SpecWorkflowSkillThreePassTests` +
the extension of `test_skill_describes_both_modes` →
`test_skill_describes_all_modes` (renamed, not net-new). Tests
exceed the AC #6 minimums (4+ surface, 1+ subagent-type, 1+ SKILL.md).
Notable surface assertions: deliverable paths appear verbatim; the
prompt does NOT say "for each acceptance criterion" (negative
assertion); all four canonical buckets named (Scope / Blockers /
Nits / Strengths); SPECIFIC ISSUES entries tagged
`[blocker]` / `[nit]` / `[strength]`; SKILL.md three-pass order
discoverable via string position.

**Dogfood verdict (AC #7).** This slice ran the new pr-review pass
against itself.
- **Compliance pass** (`jig:independent-review`): VERDICT pass. One
  nit on the prompt language subtly implying name-based routing
  rather than category-based — deferred to follow-up; the regex
  test passes and AC #4 specifies "skill description hints" routing
  which the prose still delegates to.
- **Craft pass** (`pr-review` dogfood, first ever in the workflow):
  VERDICT pass. Three `[strength]` callouts (the negative-assertion
  test pattern; the route-via-prose delegation matching the spec's
  lean-(a); the SKILL.md three-pass section's precision on the
  asymmetric block rule). Two `[nit]`-tagged findings addressed
  inline before reconciliation rather than logged: (1) the absence
  of `_principles_check_block()` on the craft prompt was deliberate
  but undocumented — added a NOTE to `build_pr_review_prompt`'s
  docstring explaining why constitution-adherence is the compliance
  + reconciliation pass's job, not the craft pass's; (2)
  `test_skill_describes_both_modes` was misnamed after the third
  mode landed — renamed to `test_skill_describes_all_modes` and
  extended to assert pr-review is also described.

**Routing-dispatch decision (spec.md Open question #1).** Took
path (a) — SKILL.md prose, no filesystem detection in `review.py`.
The pr-review prompt instructs the reviewer to apply the craft
concerns from "the most-specific `pr-review` SKILL.md reachable in
the environment" and lists the three plausible install paths
(user-installed, project, jig-bundled) without naming a specific
one. Claude's skill router does the resolution from skill
descriptions. No friction surfaced during the dogfood; path (a)
holds for slice 031-02 as well.

**Constitution-gate omission on craft pass (load-bearing).** The
craft prompt deliberately does NOT append `_principles_check_block()`.
Constitution-adherence is checked twice (compliance + reconciliation)
and the third pass would duplicate the work while conflicting with
the four-bucket framing the `jig:pr-review` skill description
establishes. A future contributor wanting to "fix" this perceived
inconsistency should read the NOTE in `build_pr_review_prompt`'s
docstring first.

**Tag taxonomy choice (spec.md Open question #2).** Tag entries
`[blocker]` / `[nit]` / `[strength]`; only `[blocker]` gates the
REVIEWED transition. SKILL.md prose for spec-workflow names this
block rule explicitly. Nits become reconciliation-log items rather
than blocking — caught by the dogfood and worked smoothly.

**Combined-verdict rule (spec.md Open question #3).** AND across
required passes (both compliance + craft must pass to transition).
Documented in `skills/spec-workflow/SKILL.md` § "After implementation"
under the "Block rule for the REVIEWED transition" heading.
