---
status: DRAFT
dependencies: [128-01, 124-03]
last_verified: 2026-11-21
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 128-03 — scenarios-name-the-verify-skill

**Goal:** when a project has a `verify` skill, the slice template,
spec-workflow's authoring step and the compliance review all point runtime
evidence at it, and a verification scenario says whether its evidence came
through it.

**Decision:** [ADR-0073](../../decisions/adr-0073-repo-verify-skill-contract.md)
point 5 — reference, not gate. Stays inside spec 118's non-goals: no
frontmatter field, parser or gate; the new line is optional body text the
reviewer reads. The same line is what earns ADR-0069's `Verified-by: verify`
token (ADR-0073 point 5); this slice adds that rule to spec 124's renderer
(AC5).

**DoR:**
- ⬜ 128-01 DONE (the contract and its folders are fixed).
- ⬜ 124-03 DONE (the stamp renderer and its token slots exist).
- ✅ spec 118's surfaces exist: the template's scenario section
  (`templates/docs/specs/slice-template.md:56-79`), spec-workflow step 5c
  (`skills/spec-workflow/SKILL.md:336-347`), the compliance block
  (`skills/independent-review/review.py:426-439`, wired only into the
  implementation prompt at `:697`), and the 1,400-character bound
  (`skills/spec-workflow/test_behavioral_verification.py:158`).

**Acceptance Criteria:**

1. **The scenario says where its evidence came from.** The slice template's
   Verification scenario section gains an optional `**Produced via:**` line:
   "`verify` skill (`<path>`, `verify-command` exit code)" or "other:
   `<tool>` — `<why not the verify skill>`". The section stays optional, and
   a missing line alone is not a blocker (spec 118 BR-3).
2. **Authoring points at the skill.** spec-workflow step 5c names the
   project's `verify` skill as the first place to boot and drive the app for a
   scenario, and says to update the skill — not only the slice — when a
   scenario finds a new boot or drive step or a flaky step, so the know-how
   lands in one place.
3. **The compliance reviewer checks the link.** `_behavioral_verification_check_block`
   adds: when a scenario says it was produced via the `verify` skill, check
   the named path exists and that the recorded outcomes match the command's
   exit code (`0` pass, `1` fail, `2` environment-error); when the project has
   a `verify` skill and a runtime scenario did not use it, note it without
   blocking. The block, with its marker, stays at or under 1,400 characters;
   the craft, frame, reconciliation and design-review prompts are unchanged
   (spec 118 AC6).
4. **Live docs and packages.** `docs/workflow.md` ("Behavioral contracts and
   runtime evidence") and `templates/docs/workflow.md.template` each gain one
   sentence naming the `verify` skill; host packages are rebuilt and
   `build_host_packages.py --check` passes.
5. **The stamp renderer earns `verify`.** Spec 124-03's token renderer gains
   ADR-0073 point 5's rule: it emits `verify` when the slice's verification
   scenario has a `Produced via:` line naming the `verify` skill, at least one
   parsed step, every step `pass`, and a `Code revision / dirty-change
   identity:` revision equal to the commit `Verified-at` names. 124-01 AC4
   deliberately skips the scenario's revision; this slice adds that check for
   the `verify` value only, so the Test plan row and BR-6's `scenario` token
   are unchanged. `verify` takes the slot 124-03 AC1 reserves after
   `scenario` (`tests`, `review`, `scenario`, `verify`; `none` alone). The
   rule reuses the renderer's existing scenario reading; no new parser.

**Edge cases to cover explicitly:**
- A legacy slice with no scenario: the implementation prompt is unchanged
  apart from the block's new sentence.
- A scenario claiming `verify` skill evidence whose path does not exist: the
  reviewer reports it as unverified evidence, the same as any missing
  evidence reference today.
- A project with no `verify` skill: no note about bypassing it.
- A scenario produced via the `verify` skill, every step `pass`, whose
  revision is missing or differs from `Verified-at`: no `verify` token.

### Behavioral rules (optional)

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | Review a scenario | Compliance reviewer | Scenario says "Produced via: verify skill" | Check path exists and outcomes match exit code | Evidence has a source a reader can re-run | 3 |
| BR-2 | Review a scenario | Compliance reviewer | Project has a `verify` skill; scenario used another tool | Note, not a blocker | Keep the know-how in one place without adding a gate | 3 |
| BR-3 | Review a slice | Compliance reviewer | No scenario, or no `Produced via` line | No blocker for absence alone | Spec 118 BR-3 stands | 1, 3 |
| BR-4 | Render the stamp | `land.py` (124-03 renderer) | Scenario produced via the `verify` skill, every step `pass`, revision equal to `Verified-at` | `verify` token present | ADR-0073 point 5; ADR-0069 §4 reserved it | 5 |
| BR-5 | Render the stamp | `land.py` (124-03 renderer) | Produced another way, a step not `pass`, or revision missing or different | No `verify` token | Only fresh evidence from the skill earns it | 5 |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec**, check `CLAUDE.md`, `AGENTS.md`, and scaffold templates, then
      compress the spec's Active-specs entry.

**Anti-horizontal-phasing check:** after this slice, an author writing a
verification scenario is sent to the project's `verify` skill, the
compliance reviewer can tell whether the evidence came from it, and a landing
whose fresh scenario came from it is stamped `verify`.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO_ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO: `templates/docs/workflow.md.template` is `updated` by AC4._ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
