---
status: DONE
dependencies: [065-01]
last_verified: 2026-06-07
arch_review: true  # extends migrate copy-machinery's contract — it now writes a
#                    managed block into a project's docs/ (non-`.claude/`), an
#                    arch-shaped behavior change (lineage: ADR-0013's security
#                    floor already does this for the .gitignore block).
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
- ✅ The **managed-block** precedent exists: ADR-0013's security floor writes a
  marker-delimited `.gitignore` block via `_write_gitignore_secret_block`,
  called by **both** `scaffold()` and `copy_machinery()`. This slice mirrors
  that helper for `docs/workflow.md`.

> **Design decision (user direction, 2026-06-07):** an earlier draft assumed the
> convention would reach existing projects because `docs/workflow.md` + the
> templates are "copied by copy-machinery." Implementation found that false —
> `copy-machinery` copies **only `.claude/` machinery**; it never touches `docs/`
> or `templates/`, and `slice-template.md` is jig-internal (not distributed).
> Resolution (chosen over rewrite-AC-to-reality and defer): **extend
> copy-machinery to refresh the convention into the project's `docs/workflow.md`
> via a marker-delimited managed block**, mirroring the ADR-0013 `.gitignore`
> precedent (idempotent: create / append-if-absent / replace-in-place; never
> clobbers content outside the markers).

**Acceptance Criteria:**

1. **An authoring convention is documented.** `docs/workflow.md` gains a
   "Self-defining vocabulary" section: when authoring a spec/slice, expand every
   acronym on first use and link the lexicon/glossary, in plain terms. A
   doc-presence test asserts the section exists with its load-bearing phrasing
   (parity with 055-01 / 057-01).
2. **The author meets the reminder where they write.** A one-line authoring
   reminder (an HTML comment) pointing at the convention + the glossary/lexicon
   is present in (a) the slice template `templates/docs/specs/slice-template.md`,
   and (b) the **distributed** `workflow.py` spec/slice renderers (`_render_stub_spec`
   + the inline slice fallback `_render_starter_slice`) — so the reminder reaches
   an author in a scaffolded project too, where the template file is not copied
   and `workflow.py new` falls back to the inline renderer. A test asserts the
   reminder is present in both.
3. **It flows — including to existing projects — via a managed block.** A
   marker-delimited convention block is injected into `docs/workflow.md` by a
   shared helper `_ensure_self_defining_convention_block(target)` (mirroring
   `_write_gitignore_secret_block`), called by **both** `scaffold()` (fresh
   projects) **and** `copy_machinery()` (existing projects, on their next
   `copy-machinery` / tier upgrade). The helper is idempotent: it creates the
   file/section when absent, appends the block when the markers are absent, and
   replaces in place when they are present (never clobbering content outside the
   markers). Tests assert: fresh scaffold contains the block; `copy-machinery` on
   an existing project **without** the block appends it; a second run is a no-op
   (idempotent); pre-existing non-jig `docs/workflow.md` content is preserved.
4. **Soft, forward-only, no gate.** The convention is advisory: nothing lints or
   blocks a transition on undefined acronyms (clarify Q4), and existing dense
   specs are left untouched. The block text states the forward-only, non-blocking
   intent explicitly.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). (2379 tests, exit 0.)
- [x] Implementer test coverage: the workflow.md section is present + reachable;
      the template reminder is present; the guidance is within the copied set;
      no gate/lint was added.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Arch (arch-review) pass run (slice declares `arch_review: true` —
      copy-machinery's contract now extends to a managed block in `docs/`);
      blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (No
      decisions deferred; the AC3 redesign was resolved in-session by user
      direction and recorded in the deviation log, not parked.)

**Anti-horizontal-phasing check:** After this slice, an author drafting the next
spec is reminded — at the template and in workflow.md — to define jargon on first
use, so the very next artifact is more readable: observable end-to-end value, not
internal-only state.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records: self-defining
      generation = soft convention, forward-only, no gate.
- [x] `CLAUDE.md` hygiene per spec 025-01: **closing slice** — spec 065 had no
      Active-specs entry to compress (it was "(none)"); added one concise Hot
      Cache key-term ("Vocabulary barrier / lexicon") for the now-shipped
      cross-cutting capability, and migrated per-slice invariants to the status
      board Notes column.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **AC3 redesigned mid-implementation (user direction, 2026-06-07) — the
  load-bearing deviation.** The original AC3 assumed the convention reaches
  existing projects because `docs/workflow.md` + templates are "copied by
  copy-machinery." Implementation found that **false**: `copy-machinery` copies
  only `.claude/` machinery; `slice-template.md` is jig-internal (never
  distributed). Presented three options (implement-to-reality+rewrite-AC /
  extend-copy-machinery / defer); the user chose **extend copy-machinery**. So
  `copy_machinery()` now injects a marker-delimited convention block into the
  project's `docs/workflow.md` via `_ensure_self_defining_convention_block`,
  mirroring the **ADR-0013 `_write_gitignore_secret_block` precedent** (a managed
  block already written by both `scaffold()` and `copy_machinery()`). The slice
  body's "Design decision" block + updated AC3 record this; `arch_review` was
  flipped to `true` and the arch pass run.

- **copy-machinery's contract widened to `docs/`.** Previously copy-machinery
  touched `.claude/` + the project-root `.gitignore` floor; it now also writes a
  managed block into `docs/workflow.md`. This rides ADR-0013's already-crossed
  boundary (copy-machinery already writes outside `.claude/`) rather than a new
  ADR. Mitigations against the "silently mutates a user-owned doc" concern: it's
  an explicit opt-in op (not a hook), the block is self-describing as
  soft/forward-only, HTML-comment markers render invisibly, and content outside
  the markers is never touched (idempotent replace-in-place; non-clobber pinned
  by `test_copy_machinery_appends_convention_block`).

- **AC2 helper-name correction.** AC2(b) named the inline slice fallback
  `_render_starter_slice`; the real function is `_render_stub_slice`. A naming
  guess in the AC — the behavior (reminder in the distributed `_render_stub_spec`
  + the `_render_stub_slice` inline fallback) is delivered.

- **Single source of truth for the block text.** `_render_self_defining_block()`
  is the sole source; jig's own `docs/workflow.md` dogfoods the *same managed
  block* (regenerated in place by the helper, not a parallel hand-copy), so there
  is no drift surface. Guarded by `DogfoodBlockMatchesHelper` (byte-identity
  cross-check, mirroring the spec 050 people.md precedent) — added during
  reconciliation per the arch-pass nit.

- **Reconciliation fix from the review nits (all three passes returned
  `pass`).** `test_slice_inline_fallback_carries_reminder` originally asserted
  the fallback via a source-text grep; rewritten to **exercise the real
  `OSError` fallback branch** (patches `Path.read_text` to raise, then asserts
  the rendered inline body carries the reminder + applies substitutions) — the
  shared compliance+craft nit.

- **Deliverables.** Helper + render + two wiring call sites in
  `skills/scaffold-init/scaffold.py`; reminders in
  `skills/spec-workflow/workflow.py` (`_render_stub_spec` + `_render_stub_slice`
  fallback); the dogfooded managed block in `docs/workflow.md`; the reminder in
  `templates/docs/specs/slice-template.md`; tests in
  `scripts/test_self_defining_convention.py` (AC1/2a/4 + drift guard),
  `skills/spec-workflow/test_workflow.py` (AC2b renderers),
  `skills/scaffold-init/test_scaffold.py` (AC3 fresh scaffold),
  `skills/migrate/test_migrate.py` (AC3 copy-machinery append/idempotent/
  preserve). Full suite green at 2379 tests.
