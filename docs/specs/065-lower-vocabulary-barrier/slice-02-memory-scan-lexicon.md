---
status: DONE
dependencies: [065-01]
last_verified:
# arch_review: true  # not set — extends an existing hook, no new boundary.
---

## Slice 065-02 — Hook surfaces lexicon definitions

**Goal:** When a prompt contains a jig term, `jig-memory-scan.sh` injects that
term's plain-language definition as `additionalContext`, so the assistant can
explain it to a junior in-line — definitions arrive just-in-time, not pushed at
everyone up front.

**DoR:**
- ✅ 065-01 landed — `_common/lexicon.py` + `lexicon.json` exist and are
  callable from a `python3 -c` hook environment.
- ✅ `jig-memory-scan.sh` already runs on `UserPromptSubmit`, already strips
  code/URLs/paths, and already emits `additionalContext` (the surface to extend).

**Acceptance Criteria:**

1. **Known lexicon terms get defined.** When the prompt contains a term present
   in the merged lexicon (e.g. "reconciliation", "SPIDR"), the hook's JSON
   output includes that term's `short` definition in `additionalContext`.
2. **Unchanged behavior for unknowns.** The existing unknown-reference surfacing
   (capitalized references not in CLAUDE.md / glossary → "ask the user") still
   fires; the two behaviors compose rather than replace each other.
3. **Bounded — negligible per-prompt cost.** At most **5** matched terms are
   surfaced, one line each (the first 5 by order of appearance), so the injection
   cannot balloon context (the 055/057 constraint). A test with >5 matches
   asserts exactly 5 are emitted. (5 is the fixed default; an env-knob override is
   out of scope for this slice — add only if signal emerges.)
4. **Reads the merged lexicon via 065-01.** The hook resolves definitions through
   `_common/lexicon.py` (shipped + project overlay, project wins) rather than
   re-parsing files itself.
5. **Fail-open.** A missing or malformed `lexicon.json` (or any error in the
   lookup) leaves the hook exiting 0 with the prompt proceeding — never blocks a
   turn. A test simulates a broken lexicon and asserts exit 0 + prompt passes.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). 28 tests in test_hooks.py; full suite green.
- [x] Implementer test coverage exercises each AC: a term match yields a def; no
      match yields the prior behavior; the cap holds; a broken lexicon fails open.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (None deferred.)

**Anti-horizontal-phasing check:** After this slice, a developer typing a jig
term into any prompt gets its plain-language definition surfaced automatically —
an observable end-to-end behavior, not internal plumbing.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records: hook surfaces
      lexicon defs, bounded + fail-open.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (spec still in flight — leave the entry).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **What shipped.** `hooks/scripts/jig-memory-scan.sh` gained a fail-open lexicon
   block (+~50 lines) that composes with the existing unknown-reference
   surfacing; `skills/memory-sync/test_hooks.py` gained a `MemoryScanLexiconTests`
   class (now 10 tests; 28 total in the file, suite exit 0). All 5 ACs met;
   `uvx ruff`, `spec_lint.py`, `validate_manifests.py` clean. Manual exercise
   confirmed the def surfaces and the **project-glossary overlay wins** end-to-end
   (065-01's `load()` applied).

2. **lexicon.py resolution from the hook.** Mirrors the `jig-context-check.sh`
   idiom: `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`, then
   `<SCRIPT_DIR>/../../skills/_common` is prepended to `sys.path` and `lexicon` is
   imported. Works in both the plugin (`hooks/scripts/` ↔ `skills/_common/`) and
   scaffolded (`.claude/…`) layouts. `project_dir` = `$CLAUDE_PROJECT_DIR`
   (fallback `.`) is passed to `load()` so the overlay applies.

3. **Matching / cap / compose.** Lowercase the (already code/URL/path-stripped)
   prompt; for each merged-lexicon key, `re.search` with `(?<![\w-])…(?![\w-])`
   word/phrase boundaries (blocks substrings like `adr` in `quadrant`, handles
   multi-word + hyphenated keys). Collect `(match_start, key, short)`, sort by
   first appearance, slice `[:5]`. The lexicon section and the unchanged
   unknown-reference message accumulate in a `sections` list joined into one
   `additionalContext`; silent when neither fires. The whole lexicon block is
   wrapped in its own `try/except` inside the outer one (double fail-open): any
   lexicon error degrades to unknown-only surfacing, `exit 0` unconditional.

4. **Review findings folded in.** Compliance + craft both PASS (recorded under
   `reviews/`). Applied the compliance nit: `test_silent_on_known_terms_in_glossary`
   had been loosened to a conditional `if out is not None:` assertion (could pass
   vacuously if both paths ever went silent); reconciliation tightened it to
   **assert the overlay def DID surface** (`a metamorphic rock`) *and* that the
   unknown-reference path stays quiet — restoring a non-vacuous guard.

5. **Deviations / judgment calls (reviewers confirmed legitimate).**
   - **Modified a pre-existing test.** `test_silent_on_known_terms_in_glossary`
     previously asserted *total silence* on a project-glossary term; AC4 now
     intentionally surfaces that term's definition, so total silence is no longer
     correct. The unknown-reference invariant (a glossary term is never flagged as
     *unknown*) is preserved and still asserted. Both reviewers verified this is a
     spec consequence, not a masked regression.
   - **`JIG_LEXICON_COMMON_DIR` override.** A narrow env seam (defaults to the
     `SCRIPT_DIR`-relative path) used by the fail-open test to inject a broken
     `lexicon.py`. Craft review judged it a clean test/override seam mirroring the
     `jig-context-check.sh` idiom, not test-concern leakage.
   - **O(terms) match (craft nit, no change).** One `re.search` per lexicon term —
     negligible at the current lexicon size; revisit (alternation / token
     pre-filter) only if the lexicon grows large.

6. **Plan adherence.** No scope deviations. The 5-cap env-knob was explicitly left
   out of scope (AC3). Nothing deferred.
