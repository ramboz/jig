---
status: DONE
dependencies: [065-01]
last_verified: 2026-06-07
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
- [x] All ACs pass; full test suite green (manifest validation included).
- [x] Coverage: `validate_manifests.py` passes with the new skill; a test asserts
      the SKILL.md declares term + artifact modes, the ephemeral contract, and the
      deferral language; the CLAUDE.md skills-table row is present.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Craft (pr-review) pass run; blockers addressed.
- [x] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers addressed.
- [x] Deviation log produced under this slice heading.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. (No decisions
      deferred; one non-blocking follow-up noted in the deviation log.)

**Anti-horizontal-phasing check:** After this slice, a junior can run
`/jig:explain docs/specs/062-refactor-workflow/spec.md` and get a plain-language
walkthrough with linked ADRs pulled in — a complete, usable capability, not a
stub.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records: `/jig:explain`
      = term + artifact modes, ephemeral, defers to richer installed skill.
- [x] `CLAUDE.md` hygiene per spec 025-01: add the `/jig:explain` row to the
      Skills table; leave the Active-specs entry until the closing slice.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **Deliverables.** `skills/explain/SKILL.md` (the judgment-skill prompt, no
  `.py` helper) + `skills/explain/test_explain_skill_surface.py` (27 structural
  surface tests). Registered across the three tier tables —
  `skills/scaffold-init/scaffold.py` `_TIER_SKILLS["tier-1"]` (source of truth),
  `scripts/install_contract.py` `EXPECTED_SKILLS`, `scripts/scaffold_contract.py`
  `_TIER_SKILLS["tier-1"]` — plus the `/jig:explain` row in the root `CLAUDE.md`
  Skills table.

- **AC1 phrasing vs. jig's actual discovery mechanism (no behavior change).**
  AC1 says the skill must be "listed in the plugin manifest (passing
  `validate_manifests.py`)". jig does **not** enumerate skills in a manifest —
  skills are directory-auto-discovered, and the install contract carries them via
  `scaffold._TIER_SKILLS` (source of truth) + the two restated mirror tables
  (`install_contract.EXPECTED_SKILLS`, `scaffold_contract._TIER_SKILLS`, pinned
  equal by the consistency tests). `validate_manifests.py` validates the three
  JSON manifests (plugin/marketplace/hooks — still passing) but does not list
  skills. The implementation satisfies AC1's **intent** (registered +
  discoverable, install contract carries it) through those real registration
  surfaces; the test (`TierRegistrationTests`) asserts the actual surfaces, not a
  literal manifest entry. Flagged independently by all three reviewers.

- **Term-mode recipe made layout-agnostic (reconciliation fix).** All three
  review passes raised the same non-blocking nit: the inline `python3 -c` lexicon
  recipe in term mode hardcoded `sys.path.insert(0, 'skills/_common')` with the
  scaffolded `.claude/skills/_common` path only in a prose aside — not
  copy-paste-safe in a scaffolded project, and not auto-corrected by the 046-01
  rewrite policer (which targets `${CLAUDE_PLUGIN_ROOT}/skills/...` helper paths,
  not relative `python3 -c` snippets). Fixed during reconciliation: the recipe
  now probes both `skills/_common` and `.claude/skills/_common` and inserts the
  one that exists. Surface tests re-run green (27/27).

- **Open, non-blocking follow-up (not deferred — no decision needed).** The
  craft pass noted `TierRegistrationTests` mutate `sys.path` via `insert(0, …)`
  without cleanup. Harmless for the current suite (the inserted dirs host
  uniquely-named jig-internal modules), left as-is to match the existing
  surface-test idiom; a future sweep could wrap them in `try/finally`. No
  refinement-todo entry — it's a test-hygiene nicety, not an undefined decision.

- **Pinned-tier-set guards + tier-inventory docs updated (by design).** Adding
  `explain` to tier-1 tripped jig's deliberate "tier addition → update the
  pinned set / docs" guards, all updated to include it:
  `test_scaffold.TierSkillSetTests.test_tier_1_is_pinned` (`EXPECTED_TIER_1`) +
  `test_migrate.TierUpgradeTests` (`TIER1`) pin the scaffolded/migrated tier-1
  set; `test_product_vision_names_every_tier_skill` forced the
  `docs/product-vision.md` Tier-1 inventory entry (#17) + its "7 Tier 0 + 10
  Tier 1" headline count; `test_vision_elicitation_worked_example_tier_line_in_sync`
  forced the same count + skill-list updates in
  `skills/vision-elicitation/worked-example-jig.md`. These are exactly the
  deliberate-update guards firing, distinct from the `TierRegistrationTests`
  that pin the three source tables equal.

- **All three review passes (compliance / craft / arch) returned `pass`**;
  verdict artifacts recorded under `reviews/slice-03-{compliance,craft,arch}.md`;
  reconciliation pass `pass` at `reviews/slice-03-reconciliation.md`.
