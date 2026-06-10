---
status: DRAFT
dependencies: [adr-0024]
last_verified:
arch_review: true   # adds a new public skill — a new external surface in the
#                     plugin (tier tables + CLAUDE.md Skills table).
frame_review: true  # the binding risk (ADR-0024 §Assumptions §4) is enumeration
#                     completeness over *settled* premises; the pre-implementation
#                     pass pressure-tests whether the SKILL.md makes a weak
#                     coverage statement visible rather than rubber-stampable.
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 067-01 — The `/jig:reframe` skill: keystone ADR + dispositions

**Goal:** A user who has recognized that a load-bearing reference moved can run
`/jig:reframe <new-reference>` and get a drafted **keystone reframe-ADR** — the
new reference declared authoritative as of `<date>`, the old premise superseded,
and a **re-baselining manifest** assigning every affected artifact a deliberate
disposition plus an explicit **coverage statement** — so the corpus is
re-baselined through one named operation instead of patched at the edges.

**DoR:**
- ✅ [ADR-0024](../../decisions/adr-0024-reference-reframe.md) **accepted**
  (Proposed→Accepted) — the capability is ratified before it is built.
- ✅ The judgment-skill pattern is proven (`/jig:clarify`, `/jig:explain` —
  SKILL.md, no `.py` helper).
- ✅ `adr.py new` reserves + scaffolds an ADR that rides the frame-critique-gated
  `accept` flow (*probed:* `_gate_frame_critique()` refuses Proposed→Accepted
  without a passing verdict).
- ✅ The disposition vocabulary + keystone-ADR / manifest shape are specified in
  ADR-0024 §3.
- ✅ The registration surfaces are known (three tier tables + CLAUDE.md Skills
  row + the pinned-tier-set guards — spec 065-03 lesson; see the spec's Design
  notes).

**Acceptance Criteria:**

1. **The skill is registered and discoverable.** `skills/reframe/SKILL.md`
   exists, is wired into the three tier tables (`scaffold.py`,
   `install_contract.py`, `scaffold_contract.py` — Tier-1), has a row in the root
   `CLAUDE.md` "Skills in this repo" table, and passes `validate_manifests.py`.
   Its description declares both invocation styles (auto + explicit) and that it
   re-baselines the corpus onto a moved load-bearing reference.
2. **It takes a new reference and reads the corpus against it.** The SKILL.md
   specifies the input (a named/located new reference — e.g. a dropped-in design
   artifact, a new contract) and that the skill reads the **accepted corpus
   (decisions + prose)** against it as the basis for drafting. It states
   explicitly that this is **not** a `## Assumptions` sweep (risk-gated; blind to
   settled premises) and **not** a built corpus-walker (parked, ADR-0024 §7).
3. **It drafts the keystone reframe-ADR through the real ADR lifecycle.** The
   SKILL.md specifies the skill reserves + scaffolds the keystone ADR via
   `adr.py new` (so it inherits the frame-critique `accept` gate) and authors its
   body: the new reference declared **authoritative as of `<date>`**, the old
   premise **superseded**, and the **re-baselining manifest**.
4. **The manifest assigns every affected artifact a disposition — no `TBD`.** The
   SKILL.md specifies the manifest is a table of affected artifacts, each tagged
   `reaffirm` / `amend` / `supersede` / `retire-draft` / `retrofit`, each routing
   to the named existing operation (ADR-0024 §3). `retire-draft` items are
   surfaced **first** (drafts on the dead premise mint dead-premise work).
5. **The manifest carries an explicit coverage statement.** The SKILL.md requires
   the keystone ADR to state **what corpus was scanned, by what method, and the
   residual uncertainty** — asserted, not assumed. The framing makes a weak
   statement *visible* (it must name scan scope + method + what was **not**
   covered), so the human confirms coverage at the `accept` frame-critique gate
   rather than rubber-stamping a silent omission. (This is the slice's binding
   risk; see `frame_review`.)
6. **Judgment-only, no helper.** No `.py` is added for reframe; the corpus read
   and drafting happen via Read + the existing `adr.py` / `workflow.py`
   scaffolding.
7. **Defers to a richer installed skill.** Per the jig baseline pattern, the
   description defers to any installed skill that identifies itself as project
   re-baselining / migrating-onto-a-new-reference — preferring it over this
   baseline (and not the generic built-in).

_Testability note (accepted gap): ACs 1, 6, 7 and the **shape** assertions of
3–5 (the SKILL.md specifies the keystone-ADR-via-`adr.py new` flow, the
disposition vocabulary, and the coverage-statement requirement) are structural
and unit-tested. The **quality** of the corpus read (AC2) and the honesty of a
given coverage statement (the substance of AC5) are judgment, exercised by the
skill prompt and the `accept` frame-critique gate — not a unit test (the same
accepted shape as every judgment-only jig skill). The slice's `frame_review` pass
is the pre-implementation pressure-test on that coverage framing._

**DoD:**
- [ ] All ACs pass; full test suite green (manifest validation included).
- [ ] Coverage: `validate_manifests.py` passes with the new skill; a test asserts
      the SKILL.md declares the operation, the keystone-ADR-via-`adr.py new`
      flow, the disposition vocabulary, the coverage-statement requirement, the
      no-helper contract, and the deferral language; the CLAUDE.md Skills-table
      row is present; the three tier tables + the pinned-tier-set guards are
      updated.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Frame-critique pass recorded **pre-implementation** (slice declares
      `frame_review: true`); gates READY_FOR_REVIEW per spec 064-03; verdict at
      `reviews/slice-01-frame-critique.md`.
- [ ] Implementation (compliance) review passed.
- [ ] Craft (pr-review) pass run; blockers addressed.
- [ ] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers
      addressed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice, a user with a moved
load-bearing reference runs `/jig:reframe <reference>` and gets a complete,
accept-ready keystone ADR — new reference authoritative, old premise superseded,
every affected artifact dispositioned, coverage stated — a usable re-baseline
primitive a competent session can execute by hand, not a stub.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`. Notes
      column records: `/jig:reframe` = corpus-read → keystone reframe-ADR
      (manifest + 5-disposition vocab + coverage statement) via `adr.py new`;
      judgment-only, Tier-1; frame-critique-gated keystone.
- [ ] `CLAUDE.md` hygiene per spec 025-01: add the `/jig:reframe` row to the
      Skills table. Leave the Active-specs entry until the closing slice
      (067-03).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape, reviewer
findings folded back in, doc updates, plan adherence._
