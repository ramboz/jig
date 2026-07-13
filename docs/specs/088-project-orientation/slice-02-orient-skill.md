---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-07-13
arch_review: true
code_health_review: false
---

## Slice 088-02 — the `/jig:orient` judgment skill

**Goal:** On top of the deterministic `workflow.py orient` headline (088-01), a
Tier-1 `/jig:orient` skill surveys the project's judgment-bearing artifacts and
renders one fixed, readable "where do things stand, what should I pick up?"
briefing — entirely read-only (it writes nothing): it renders the briefing to stdout,
which a scheduled job or dashboard can capture.

**Context:** Adopted from a contributed standalone skill (originally `compass`,
`Kyarha/compass`) into jig per review of
[#90](https://github.com/ramboz/jig/pull/90). This slice owns the work and records
the decisions accepted in that review. It layers on — and shares terminology with —
the `workflow.py orient` command shipped by slice 088-01.

**DoR:**
- ✅ The deterministic headline is available via
  `workflow.py orient --project-dir .` (088-01, DONE).
- ✅ The Tier-1 registration surface is known (`_TIER_SKILLS`, install/scaffold
  contracts, tier tests, routing eval, product prose, host packages).
- ✅ jig's per-checkout runtime dir `.jig/` is an established home for gitignored,
  non-tracked local state (e.g. `.jig/semantic-index-events.jsonl`).

**Acceptance Criteria:**

1. **Public name `orient`.** The skill ships at `skills/orient/SKILL.md` as
   `/jig:orient`, reusing the orientation vocabulary established by 088-01; no
   `compass` metaphor remains anywhere in the plugin or its host packages.
2. **Layered, not re-derived.** The skill starts from the `workflow.py orient`
   `jig hint:` line for the deterministic headline and layers judgment (Proposed
   ADRs, DEFERRED triggers, refinement-todo, release plans, inbox, standalone bugs)
   on top, rather than re-implementing a second lifecycle-focus algorithm.
3. **Trigger boundary.** Positive triggers are scoped to explicit project-level
   orientation intent (`/jig:orient`, "orient me to this project", "where do things
   stand"); a bare conversational "what's next?" inside an active implementation flow
   is a negative case (it continues the current slice). `evals/cases/orient.json`
   encodes both, and the full routing gate stays green.
4. **Zero-write; entirely read-only.** The skill never transitions lifecycle state,
   edits a spec, accepts an ADR, or writes any file (no `docs/` write, no `.jig/`
   cache, no history log). It renders the briefing to stdout, which a scheduled job
   or dashboard can capture. A machine-readable export / optional persistence
   contract is deferred to the dashboard-integration work in
   [#91](https://github.com/ramboz/jig/issues/91), not established in this MVP.
5. **Correct handoffs.** The skill routes "implement a ready slice" through
   `jig:spec-workflow` (which coordinates the `implementer` subagent), not a
   non-invocable `jig:implementer`. Optional handoffs to sibling plugins
   (servo / shaper / studio) are retained as best-effort.
6. **Registered as Tier 1.** `orient` is present in every pinned skill-set surface
   (`scaffold._TIER_SKILLS`, `scaffold_contract._TIER_SKILLS`,
   `install_contract.EXPECTED_SKILLS`, `TierSkillSetTests`, `TierUpgradeTests`),
   product-prose counts (13 Tier 1 / 20 total), and both regenerated host packages;
   the host drift check passes.
7. **Suite green.** Full `run_tests.py` passes with no regressions; the routing
   report exits 0 (60/60 positives within top_k, 0 collision hazards).

**Decisions recorded (from #90 review):**
- **Name:** `orient` (not `compass`) — reuse the 088 / `workflow.py orient`
  terminology instead of adding a new metaphor to jig's vocabulary.
- **Helper composition:** layer on `workflow.py orient`; do not duplicate the
  lifecycle-focus algorithm.
- **Zero-write MVP:** `/jig:orient` writes nothing; it renders to stdout for a
  scheduled job or dashboard to capture. Persistence / a machine-readable status
  export is deferred to the dashboard-integration design in
  [#91](https://github.com/ramboz/jig/issues/91), not established in this MVP
  (maintainer call, #90 review).
- **Sibling-plugin handoffs:** optional / best-effort to servo / shaper / studio.

**DoD:**
- [x] Skill authored; registration surface + host packages updated; full suite green.
- [x] Routing eval authored (positive + route-away cases); routing gate green.
- [ ] Architecture review passed (`arch_review: true`) — under review on #90.
- [ ] Reconciliation sweep + deviation log produced after review.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred (none so far).

**Anti-horizontal-phasing check:** After this slice lands, a user can invoke
`/jig:orient` and immediately receive a grounded, readable project briefing seeded by
the deterministic headline — a complete command-to-guidance behavior, not a partial
layer.
