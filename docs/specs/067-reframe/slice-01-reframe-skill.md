---
status: DONE
dependencies: [adr-0024]
last_verified: 2026-07-02
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
   `install_contract.py`, `scaffold_contract.py` — Tier-1), stays **discoverable
   from the root `CLAUDE.md` primer** (a named `/jig:reframe` mention — post
   [spec 076](../076-lean-primer/spec.md) the heavy per-skill "Skills in this repo"
   table was replaced by the host-surfaces-skills pointer + the hot-cache index, so
   discoverability is a *named mention*, not a table row), and passes
   `validate_manifests.py`. Its description declares both invocation styles (auto +
   explicit) and that it re-baselines the corpus onto a moved load-bearing
   reference.
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
   `reaffirm` / `amend` / `supersede` / `retire-draft` / `retrofit` / `rewrite`
   (the last for live non-record prose), each routing to the named existing
   operation per [ADR-0024](../../decisions/adr-0024-reference-reframe.md) §3.
   `retire-draft` items are surfaced **first** (drafts on the dead premise mint
   dead-premise work). Net-new forward work the reframe *spawns* (not a
   disposition of an existing artifact) is recorded in a separate
   **`## Emergent work`** section, not forced into a disposition row.
5. **The manifest carries a two-level coverage floor.** The SKILL.md requires the
   keystone ADR's coverage statement to take the form of a **coverage floor**
   ([ADR-0024](../../decisions/adr-0024-reference-reframe.md) §2–§3), not free
   text: **(L1)** a per-class walk of the corpus's deterministically-listable
   **top-level artifact classes** (`docs/decisions/`, `docs/specs/`, live-prose
   docs under the docs root, `skills/*/SKILL.md`, the root primer(s), `README`),
   each marked `scanned` or `excused (reason)`; **(L2)** for each class the
   reference actually **touches**, an **artifact-level** enumeration of that class
   plus the **method** used to decide which artifacts encode the dead premise; plus
   the overall **residual uncertainty**. L1 makes a whole-class drop visible; L2
   makes an **intra-class** miss visible (the motivating failure's shape — a
   dead-premise file inside a class L1 alone would mark `scanned`). The floor is
   *asserted, not assumed*: an omission must be written down as a visible per-class
   (and, for touched classes, per-artifact) fate, so the human confirms coverage at
   the `accept` frame-critique gate rather than rubber-stamping a silent omission.
   The SKILL.md states plainly that the floor **reduces and surfaces** the
   enumeration risk but does **not** eliminate it (untouched-class misscoping;
   within-class miss; rubber-stamped `excused`), with T1 (ADR-0024 §7) the
   backstop. (This is the slice's binding risk; see `frame_review`.)
6. **Judgment-only, no helper.** No `.py` is added for reframe; the corpus read
   and drafting happen via Read + the existing `adr.py` / `workflow.py`
   scaffolding.
7. **Defers to a richer installed skill.** Per the jig baseline pattern, the
   description defers to any installed skill that identifies itself as project
   re-baselining / migrating-onto-a-new-reference — preferring it over this
   baseline (and not the generic built-in).

_Testability note (accepted gap): ACs 1, 6, 7 and the **shape** assertions of
3–5 (the SKILL.md specifies the keystone-ADR-via-`adr.py new` flow, the
disposition vocabulary, and the two-level coverage-floor requirement — L1's
top-level classes named + L2's within-touched-class artifact read) are structural
and unit-tested. The **quality** of the corpus read (AC2) and the honesty of a
given coverage floor (the substance of AC5) are judgment, exercised by the skill
prompt and the `accept` frame-critique gate — not a unit test (the same accepted
shape as every judgment-only jig skill). The slice's `frame_review` pass is the
pre-implementation pressure-test on that coverage framing._

**DoD:**
- [x] All ACs pass; full test suite green (manifest validation included). — 3135
      tests, OK (9 skipped); ruff clean (whole repo, ruff==0.15.16).
- [x] Coverage: `validate_manifests.py` passes with the new skill; a test asserts
      the SKILL.md declares the operation, the keystone-ADR-via-`adr.py new`
      flow, the disposition vocabulary, the two-level coverage-floor requirement
      (L1 top-level classes named + L2 within-touched-class read), the no-helper
      contract, and the deferral language; `/jig:reframe` stays discoverable in the
      root `CLAUDE.md` primer (post-spec-076: a named mention, not a per-skill
      table row — see AC1); the three tier tables + the pinned-tier-set guards are
      updated. — `skills/reframe/test_reframe_skill_surface.py` (33 tests).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Frame-critique pass recorded **pre-implementation** (slice declares
      `frame_review: true`); gates READY_FOR_REVIEW per spec 064-03; verdict at
      `reviews/slice-01-frame-critique.md`. — verdict: pass.
- [x] Implementation (compliance) review passed. — verdict: pass.
- [x] Craft (pr-review) pass run; blockers addressed. — verdict: pass; 2 nits
      folded in (below).
- [x] Arch (arch-review) pass run (slice declares `arch_review: true`); blockers
      addressed. — verdict: pass; 1 nit folded in (below).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed. — verdict: pass; the one finding (stale README
      Tier-1 subtotal) was fixed during reconciliation (deviation-log #8).
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. — no new
      deferrals (systematic detection already parked in ADR-0024 §7 / spec 067).

**Anti-horizontal-phasing check:** After this slice, a user with a moved
load-bearing reference runs `/jig:reframe <reference>` and gets a complete,
accept-ready keystone ADR — new reference authoritative, old premise superseded,
every affected artifact dispositioned, coverage stated — a usable re-baseline
primitive a competent session can execute by hand, not a stub.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`. Notes
      column records: `/jig:reframe` = corpus-read → keystone reframe-ADR
      (manifest + 6-disposition vocab incl. `rewrite` + two-level coverage floor)
      via `adr.py new`; judgment-only, Tier-1; frame-critique-gated keystone.
- [ ] `CLAUDE.md` hygiene per spec 025-01: keep `/jig:reframe` discoverable in the
      primer — post-[spec 076](../076-lean-primer/spec.md) that is a **named
      hot-cache-index mention**, not a per-skill Skills-table row (spec 076 removed
      that table). Leave the Active-specs entry until the closing slice (067-03).

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

1. **ADR-0024 was hardened before acceptance (frame-critique-driven).** The
   keystone ADR this slice depends on took **two rounds of `needs-changes`**
   before `pass`: round 1 re-scoped the coverage statement from "owns the risk"
   to a **coverage floor** + "reduces and surfaces"; round 2 made the floor
   **two-level** (L1 class + L2 within-touched artifact) to catch the
   *intra-class* miss (the motivating failure's shape), gave **T1** a
   two-pronged evidence source (accept-time floor **or** post-reframe
   discovery), and marked the *correction > noticing* ordering an explicit n=1
   assumption with a kill criterion. Spec 067 + slice-01 (Goal #4, Design notes,
   AC5, testability note) were propagated to match the **accepted** ADR *before*
   the slice frame-critique ran — so the slice frame-critique (pass) evaluated a
   frame already consistent with the ratified decision.

2. **AC1 was corrected for the post-spec-076 world (the plan pre-dated the lean
   primer).** The original AC1 + Close-out required a "row in the root CLAUDE.md
   'Skills in this repo' table." [Spec 076](../076-lean-primer/spec.md) removed
   that per-skill table (the host surfaces every skill each session; CLAUDE.md is
   capped at 70 lines / 14 KiB). Discoverability was therefore delivered as a
   **named hot-cache-index mention** — extending the existing catch-all index line
   in **both** `CLAUDE.md` and `AGENTS.md` (parity; each stays within budget) — plus
   a `docs/memory/glossary.md` **Reframe** entry so `/jig:explain reframe`
   resolves. AC1 and the Close-out were corrected to describe this. *Dogfood
   note:* the stale "Skills table" AC is itself a small instance of the
   reference-moved / spec-encodes-the-old-shape problem `/jig:reframe` exists to
   fix.

3. **Open questions resolved as-planned (confirmations, not deviations).**
   (a) the re-baselining manifest lives **inline** in the keystone ADR (spec
   Open-questions lean); (b) `/jig:reframe` is **draft-on-invoke only** — no
   report-only mode shipped; not-locatable → refuse + ask; no-op → "nothing to
   re-baseline" (Clarification Q1). Both are documented in the SKILL.md.

4. **Frame-critique non-blocking note folded in.** The slice frame-critique
   (pass) flagged that the L1 class list is *jig-corpus-shaped*; a one-line
   maintenance note was added to the SKILL.md (revisit L1 if a downstream corpus
   grows a new top-level class or uses a configurable docs root — adjacent to the
   T2 trigger and [ADR-0033](../../decisions/adr-0033-configurable-docs-root.md)).

5. **Reviewer nits folded in (all three passes `pass`, no blockers).**
   Arch [nit]: added a one-line clarification that L1 covers the
   **authority-bearing corpus**, not the code tree (shipped code → `retrofit`
   specs). Craft [nit]s: corrected the slice Close-out "5-disposition" →
   "6-disposition (incl. `rewrite`)" and the stale "Skills table row" reference.
   Log-only nits (no change needed): the long frontmatter description (a
   deliberate jig auto-trigger convention, required by the trigger-phrase /
   deferral / do-not-use test assertions) and the forward-references to unbuilt
   sibling slices 067-02 / 067-03 (standard jig cross-slice linking).

6. **All registration surfaces updated (the spec 065-03 "miss one surface"
   lesson).** `reframe` added to: `scaffold._TIER_SKILLS` (source of truth),
   `install_contract.EXPECTED_SKILLS`, `scaffold_contract._TIER_SKILLS`,
   `test_scaffold.EXPECTED_TIER_1`, `test_migrate.TIER1`, `product-vision.md`
   (12 Tier 1 / 19 skills + item 19), the `vision-elicitation` worked-example tier
   line, `docs/memory/glossary.md` (Tier-1 roster + a Reframe entry), `README.md`
   (19 skills), and the `CLAUDE.md` + `AGENTS.md` hot-cache index. `hosts/`
   regenerated via `build_host_packages.py`; `--check` reports in sync.

7. **Plan adherence.** Judgment-only, **no `reframe.py`** (AC6, pinned by
   `test_no_reframe_py`). Vertical slice: a user with a moved reference gets a
   complete, accept-ready keystone ADR (manifest + 6-disposition vocabulary +
   two-level coverage floor). Pre-implementation frame-critique + compliance +
   craft + arch all `pass`. Full suite green (3135 tests, OK/9 skipped); ruff
   clean (whole repo, `ruff==0.15.16`).

8. **Reconciliation review caught a missed count.** The reconciliation reviewer
   flagged that `README.md:33` still read "7 Tier 0 + 11 more (Tier 1)" after this
   slice made Tier 1 = 12 — an internal contradiction with README's own "all 19
   skills" (7 + 11 = 18). Fixed the subtotal to **12** and regenerated the
   `hosts/claude/README.md` mirror (`--check` back in sync). The reviewer's other
   note — now-stale status prose in the `docs/inbox.md` `reframe/occurrence-3`
   entry ("067-01 is DRAFT … ADR-0024 still Proposed") — is legitimately deferred
   to spec close (067-03) per the sweep's inbox disposition, not silent drift.

### Reconciliation sweep

Drift-prone surfaces checked (`updated` / `no-op` / `deferred`):

- **Tier-registration surfaces** — `updated`. Source table + both mirror contracts
  + both pinned-tier guards + product-vision inventory/count + worked-example tier
  line all carry `reframe`; lockstep tests green.
- **Host packages (`hosts/claude`, `hosts/codex`)** — `updated`. Regenerated;
  `build_host_packages.py --check` in sync.
- **Root primers (`CLAUDE.md`, `AGENTS.md`)** — `updated`. Reframe added to the
  hot-cache index line in **both** (parity), each within the spec-076 budget.
- **`docs/memory/glossary.md`** — `updated`. Tier-1 roster + a `## Reframe` term
  entry (so `/jig:explain reframe` resolves).
- **`docs/product-vision.md` / `worked-example-jig.md` / `README.md`** — `updated`
  (counts + inventory). *Reconciliation review caught* a stale README Tier-1
  subtotal (line 33 "11 more" → **12**; it contradicted "all 19 skills") — fixed,
  `hosts/claude/README.md` mirror regenerated (deviation-log #8).
- **`docs/decisions/README.md` (ADR index)** — `updated` (reindexed on ADR-0024
  `accept`).
- **`docs/architecture.md`** — `no-op`. No module-boundary change: reframe adds no
  `.py`, no subagent, no hook (arch review confirmed boundaries preserved).
- **`docs/workflow.md`** — `deferred` to slice **067-03** (the noticing-nudge
  standing practice is 067-03's deliverable).
- **`docs/refinement-todo.md`** — `no-op`. No new deferrals; systematic detection
  is already parked in [ADR-0024](../../decisions/adr-0024-reference-reframe.md) §7
  (triggers T1/T2/T3).
- **`docs/inbox.md`** — `deferred` to spec close (067-03). The three
  `reframe/occurrence-*` entries are the **live T1/T2/T3 trigger-watch evidence
  ledger** (n=1 Android / n=2 servo / n=3 ASV) and the "demand-pull to accept
  ADR-0024 + build 067-01" meta-signal being satisfied here — they stay as
  evidence, not struck.
- **Lightweight decisions (`docs/decisions/lightweight-decisions.md`)** — `no-op`.
  No non-spec UI/visual/brand decisions were settled.
- **`docs/conventions.md`** — `no-op`. No rule introduced or changed.
- **Memory-sync** — a session learning (the frame-critique-driven two-level-floor
  hardening) is captured in this deviation log; no new glossary/lexicon term beyond
  the Reframe entry already added.
