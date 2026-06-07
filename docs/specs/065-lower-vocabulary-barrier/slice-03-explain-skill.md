---
status: DRAFT
dependencies: [065-01]
last_verified:
arch_review: true  # adds a new public skill (a new external surface in the
#                    plugin manifest + CLAUDE.md skills table).
---

## Slice 065-03 — `/jig:explain` skill (term + artifact modes)

**Goal:** Give a junior an on-demand "explain it to me like I'm new here" command
— `/jig:explain <term>` defines a single term in plain language; `/jig:explain
<spec-or-adr-path>` produces a strong-handholding walkthrough of a dense
artifact, auto-pulling the ADRs/specs it links so the reader doesn't chase
references. Output is ephemeral (chat-only).

**DoR:**
- ✅ 065-01 landed — the merged lexicon is the source for term-mode definitions
  and for the "words you'll need" inventory in artifact mode.
- ✅ The judgment-skill pattern is proven (`/jig:clarify`, `/jig:pr-review`,
  `/jig:arch-review` — SKILL.md only, no `.py` helper).
- ✅ Plugin manifest + `validate_manifests.py` + the CLAUDE.md skills table are
  the registration surfaces a new skill must satisfy.

**Acceptance Criteria:**

1. **The skill is registered and discoverable.** `skills/explain/SKILL.md`
   exists, is listed in the plugin manifest (passing `validate_manifests.py`),
   and has a row in the CLAUDE.md "Skills in this repo" table. Its description
   declares both invocation styles (auto + explicit) and the two modes.
2. **Term mode.** The SKILL.md specifies that `/jig:explain <term>` returns the
   term's plain-language definition from the merged lexicon (065-01), with its
   example + see-also when present, and **flags** a term absent from the lexicon
   (rather than inventing a definition).
3. **Artifact mode — strong handholding.** The SKILL.md specifies that
   `/jig:explain <path-to-spec-or-adr>` produces a junior-grade walkthrough with a
   fixed shape: **In one sentence** / **Why it exists** / **Words you'll need
   first** (every jig term in the artifact, defined inline; gaps flagged) /
   **Walkthrough** (section by section, plain language) / **The decisions & why**
   (for ADRs: alternatives + trade-off) / **If you had to work on this**. It
   **auto-pulls linked ADRs/specs** so references are resolved for the reader.
4. **Ephemeral.** The skill writes nothing to disk — output is chat-only. The
   SKILL.md states this explicitly (no `--save`, no appended section), keeping the
   hot path clean (clarify Q3 / 055/057).
5. **Judgment-only, no helper.** No `.py` is added for this skill; section
   surgery / lookups happen inline via Read + the 065-01 loader.
6. **Defers to a richer installed skill.** Per the jig baseline pattern, the
   description defers to any other installed skill whose description identifies it
   as handling plain-language explanation / onboarding / artifact walkthroughs —
   prefer it over this slim baseline (and does not defer to the generic built-in).

_Testability note (accepted gap): ACs 1, 4, 5, 6 are structural and unit-tested
(manifest registration, ephemeral contract, no-helper, deferral language). ACs 2
and 3 govern output **quality**, which is judgment exercised by the skill prompt,
not a unit test — the same accepted shape as every judgment-only jig skill
(`/jig:clarify`, `/jig:pr-review`). Recorded in the spec's coverage summary._

**DoD:**
- [ ] All ACs pass; full test suite green (manifest validation included).
- [ ] Coverage: `validate_manifests.py` passes with the new skill; a test asserts
      the SKILL.md declares term + artifact modes, the ephemeral contract, and the
      deferral language; the CLAUDE.md skills-table row is present.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a junior can run
`/jig:explain docs/specs/062-refactor-workflow/spec.md` and get a plain-language
walkthrough with linked ADRs pulled in — a complete, usable capability, not a
stub.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated; Notes column records: `/jig:explain`
      = term + artifact modes, ephemeral, defers to richer installed skill.
- [ ] `CLAUDE.md` hygiene per spec 025-01: add the `/jig:explain` row to the
      Skills table; leave the Active-specs entry until the closing slice.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO._
