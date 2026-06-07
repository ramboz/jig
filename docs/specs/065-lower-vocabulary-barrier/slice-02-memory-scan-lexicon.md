---
status: DRAFT
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
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC: a term match yields a def; no
      match yields the prior behavior; the cap holds; a broken lexicon fails open.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a developer typing a jig
term into any prompt gets its plain-language definition surfaced automatically —
an observable end-to-end behavior, not internal plumbing.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records: hook surfaces
      lexicon defs, bounded + fail-open.
- [ ] `CLAUDE.md` hygiene per spec 025-01 (spec still in flight — leave the entry).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
