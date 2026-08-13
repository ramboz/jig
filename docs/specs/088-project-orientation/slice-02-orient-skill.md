---
status: DONE
dependencies: []
last_verified: 2026-08-11
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
- [x] Architecture review passed (`arch_review: true`) — recorded verdict `pass`, `reviews/slice-02-arch.md` (the #90 review was informal; this is the gated evidence artifact).
- [x] Reconciliation sweep + deviation log produced after review (below).
- [x] `docs/refinement-todo.md` updated if any decisions were deferred (none — no decisions deferred).

**Anti-horizontal-phasing check:** After this slice lands, a user can invoke
`/jig:orient` and immediately receive a grounded, readable project briefing seeded by
the deterministic headline — a complete command-to-guidance behavior, not a partial
layer.

### Deviation log (after reconciliation)

Original ACs preserved above. The slice's deliverable shipped and evolved across
three PRs (#90 adoption, #122 spec 101-01 collaboration survey, #190 bug 031
freshness) but was never formally driven through the review→reconcile→DONE
lifecycle; this close-out produces the missing gated evidence rather than
re-implementing anything.

- **Retrospective close-out (no behaviour change).** All seven ACs were verified
  met against the current on-disk deliverable by three fresh, context-isolated
  reviewer passes — compliance / craft / arch — all `pass` (`reviews/slice-02-{compliance,craft,arch}.md`).
  The arch pass was required because the slice declares `arch_review: true`; the
  original DoD noted it as "under review on #90" (informal), and the recorded
  `reviews/slice-02-arch.md` verdict is the gated evidence that box now points at.
- **Test coverage widened (compliance finding, applied).** The compliance pass
  flagged that AC4 (zero-write) and AC5 (correct handoff) were pinned by no test —
  a future edit deleting the "Orient writes nothing" section or the
  `jig:spec-workflow` handoff would fail nothing. Added `Orient088CoreContractTests`
  (two body-scoped, non-vacuous assertions) to `test_orient_skill_surface.py` and
  corrected that file's module docstring, which mislabelled its entire provenance as
  slice 101-01 / bug 031 (all three reviewers flagged the mislabel). Surface suite
  now 16 tests, green.
- **Craft nit applied.** `SKILL.md` Section 3 example used `__…__` double-underscore
  bold inconsistent with the `**…**` idiom the prime directive mandates; changed to
  underscore-italic-outer + asterisk-bold-inner (`_**…**_`) to satisfy the idiom
  without marker collision inside the italic blockquote.
- **Craft nit NOT applied (deferred, rationale).** The zero-write invariant is stated
  three times (dedicated section + judgment bullet + gotcha). Left as-is: it is the
  skill's single most load-bearing contract on an always-surfaced skill, and the two
  new tests now pin the dedicated-section statement — deleting the repetition would
  weaken the guard the compliance pass asked for. Logged, not silently dropped.
- **Primer hygiene (spec 025 compress-on-close).** Spec 088's last live slice (088-02)
  closes here, so the `CLAUDE.md` / `AGENTS.md` active-specs line — which still read
  "088-02 — `/jig:orient` skill (adopting contributed `compass`; arch review on #90)"
  — was compressed to "none in-flight (088 shipped + closed)". This also removes the
  last `compass` reference from the primer surface (AC1's intent, beyond its literal
  plugin/host-package scope).
- **Host-package drift correction (honesty note).** The sweep first recorded host
  packages as a `no-op` on the reasoning "body-only change, frontmatter unchanged" — and
  the reconciliation review shared that mental model and passed it. The pre-commit
  `build_host_packages.py --check` then **failed**: host packages embed the entire
  `SKILL.md`, so the idiom nit did drift both host copies. Regenerated and re-verified in
  sync; the sweep's Host-packages disposition above is corrected to `updated`. No
  behaviour change — the two host `SKILL.md` copies now match source byte-for-byte.

### Reconciliation sweep

Drift-prone surfaces checked, with dispositions:

- **Review evidence** — `updated`: recorded compliance/craft/arch verdicts under
  `docs/specs/088-project-orientation/reviews/slice-02-*.md` (the REVIEWED gate's
  evidence set).
- **`CLAUDE.md` / `AGENTS.md` active-specs primer** — `updated`: compressed the closed
  088 entry; dropped the stale `compass`/`#90` framing (compress-on-close).
- **`skills/orient/test_orient_skill_surface.py`** — `updated`: added AC4/AC5 coverage;
  fixed provenance docstring.
- **`skills/orient/SKILL.md`** — `updated`: bold-idiom nit only; no behaviour change.
- **`docs/refinement-todo.md`** — `no-op`: no decisions were deferred by this close-out.
- **`docs/inbox.md`** — `no-op`: nothing 088-related parked.
- **Lightweight / ADR decisions** — `no-op`: no new load-bearing decision with rejected
  alternatives; no module boundary or public contract changed (arch pass confirmed the
  layer-on-`workflow.py orient` boundary is preserved). No ADR warranted.
- **`docs/conventions.md`** — `no-op`: no rule introduced or changed.
- **Host packages** — `updated`: the pre-commit host-drift check
  (`build_host_packages.py --check`) **corrected an earlier wrong `no-op` claim here**.
  The host packages embed the *full* `SKILL.md`, not just its frontmatter, so even a
  body-only idiom nit drifts the two copies (`hosts/claude/skills/orient/SKILL.md`,
  `hosts/codex/plugins/jig/skills/orient/SKILL.md`). Regenerated via
  `python3 scripts/build_host_packages.py`; `--check` now reports in sync. (See the
  deviation-log correction below — this is the local-green ≠ CI-green gap the check exists
  to close.)
- **Status board Notes** — `deferred`: no load-bearing per-slice invariant to migrate
  (orient is a self-describing judgment skill); the board row flips to DONE on regen.
- **Spotted, out of scope (`deferred`)** — `AGENTS.md` records spec 106 as `Proposed`
  while `CLAUDE.md` records it `Accepted`/built; a pre-existing primer drift unrelated
  to 088, left for a governance-plane reconciliation to resolve.
