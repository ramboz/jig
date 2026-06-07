---
status: DRAFT
dependencies: [065-01]
last_verified:
# arch_review: true  # not set — docs + templates, no module boundary change.
---

## Slice 065-04 — Self-defining generation convention

**Goal:** Stop the dense-jargon pile from growing: a soft authoring convention
so that **newly** generated specs expand each acronym and link the lexicon on
first use — making future artifacts readable without retrofitting the old ones.

**DoR:**
- ✅ 065-01 landed — the lexicon is the link target the convention points new
  specs at.
- ✅ The soft-mechanism doc pattern is established (055-01 / 057-01 added
  guidance sections to `docs/workflow.md` reachable from the hot-cache pointer).
  Both are DONE and referenced here as a **doc-pattern precedent, not a build
  dependency** — hence `dependencies: [065-01]` only (065-01 supplies the link
  target this convention points authors at).
- ✅ Spec + slice templates exist (`templates/docs/specs/`) and flow via
  `scaffold-init` / `migrate copy-machinery`.

**Acceptance Criteria:**

1. **An authoring convention is documented.** `docs/workflow.md` gains a
   "self-defining vocabulary" section: when authoring a spec/slice, expand every
   acronym on first use and link the lexicon/glossary, in plain terms. A
   doc-presence test asserts the section exists and is reachable from the existing
   context-discipline / hot-cache pointer (parity with 055-01 / 057-01).
2. **The templates carry the reminder.** The spec and slice templates
   (`templates/docs/specs/*.template`) include a one-line authoring reminder
   (e.g. an HTML comment) pointing at the convention + the glossary/lexicon, so an
   author meets the rule where they write. A test asserts the reminder is present.
3. **It flows to existing projects.** Because the guidance rides in
   `docs/workflow.md` + the spec/slice templates — both inside trees copied by
   `migrate copy-machinery` — an already-scaffolded project receives the
   convention on its next `copy-machinery` / tier upgrade. Asserted against the
   migrate manifest / copied set.
4. **Soft, forward-only, no gate.** The convention is advisory: nothing lints or
   blocks a transition on undefined acronyms (clarify Q4), and existing dense
   specs are left untouched. The doc text states the forward-only, non-blocking
   intent explicitly.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage: the workflow.md section is present + reachable;
      the template reminder is present; the guidance is within the copied set;
      no gate/lint was added.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, an author drafting the next
spec is reminded — at the template and in workflow.md — to define jargon on first
use, so the very next artifact is more readable: observable end-to-end value, not
internal-only state.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records: self-defining
      generation = soft convention, forward-only, no gate.
- [ ] `CLAUDE.md` hygiene per spec 025-01: **if this is the closing slice**,
      compress spec 065's Active-specs entry per the rule; migrate load-bearing
      per-slice invariants to the status board Notes column.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
