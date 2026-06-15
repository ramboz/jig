---
status: DONE
dependencies: [adr-0014]
last_verified: 2026-06-15
arch_review: true  # adds a public review-pass surface + gate wiring (ADR-0014)
---

## Slice 071-01 — design-review-pass

**Goal:** Add a `design_review`-gated review pass that, at REVIEWED, has a
read-only reviewer ATTEST an external non-deterministic eval's frozen verdict
(servo's design-fidelity composite) — reading the eval's ledger/threshold and
recording pass/fail, never re-deriving the score — exactly mirroring the
ADR-0014 gated REVIEWED-pass pattern (`arch` / `code-health`). Resolves
ADR-0022 OQ2: attest-only, schema-only, no bespoke servo interface.

**DoR:**
- ✅ ADR-0014 (review-evidence model) Accepted — the gated-pass pattern exists.
- ✅ ADR-0022 (pluggable oracle boundary) Proposed/Parked — OQ2 ("how thin is
      attest-only") is the question this slice answers with code.
- ✅ Pattern confirmed: `design-review` mirrors `arch` (031-02) at the REVIEWED
      stage exactly — `build_design_review_prompt` ≈ `build_arch_review_prompt`;
      add `design-review` to `review_evidence.PASSES`; `_design_review_flag` ≈
      `_arch_review_flag`; `required_passes` gains a `design_review` kwarg
      appending `design-review` to the REVIEWED set. **No new stage** (unlike
      064-03's frame-critique, which gated READY_FOR_REVIEW).

**Acceptance Criteria:**

1. **`review.py design-review` builds an attest-only prompt** directing the
   read-only reviewer to confirm the external eval ran and is non-stale/honest
   (frozen definition, `env_error ≠ pass`, composite ≥ the eval's own threshold)
   and to RECORD that verdict — explicitly *not* to re-run or re-derive the
   eval. Distinct, observable prompt text. No richer-skill detection (no standard
   external "design-review" category — it attests jig's own eval evidence).
2. **`design_review` is a recognized per-slice/spec frontmatter flag** following
   the `arch_review` / `code_health_review` truthy convention (`true`/`yes`/`on`/`1`,
   case-insensitive); `design-review` joins the `PASSES` set in
   `review_evidence.py`, and `record-review` / `check-reviews` handle it (the
   `--pass` choices include it via `PASSES`).
3. **The pass is gated at REVIEWED** — a `REVIEWED` transition requires the
   `design-review` verdict **iff** the slice/spec declares a truthy
   `design_review`; default-off slices are unaffected (existing specs see no
   change); re-validated at DONE (DONE re-runs the REVIEWED set). Provable by
   transitioning a flagged vs unflagged slice.
4. **A verdict artifact** is written at the ADR-0014 path/shape
   (`reviews/slice-NN-design-review.md`) with the standard frontmatter + VERDICT
   envelope (the existing slice-based `record-review` / `check-reviews` path).

**DoD:**
- [x] All ACs pass; the new tests and the affected suites are green —
      `scripts/run_tests.py` (uv 3.12). The only failures are pre-existing,
      environmental E2Es in the git-reservation / linked-worktree area
      (`ReserveSpec` / `AdrFromLinkedWorktreeE2E` / `NewSpecScaffoldsFilePerSlice`);
      **which subset fails is machine-dependent** — it turns on the local git's
      stderr wording and the sandbox's `origin` setup — so the exact count/names
      are not load-bearing. None touch this slice's code path, and this change
      adds **zero new failures**.
- [x] New tests cover: prompt builder text (attest-only, "do NOT re-derive"),
      flag truthy-token recognition, gated/ungated REVIEWED transition, verdict
      artifact round-trip — mirroring the arch (031-02) / frame (064-03) tests.
- [x] `uvx ruff check` clean on changed files + `spec_lint.py` clean on the 071
      spec. (manifests: n/a — no manifest surface touched.)
- [x] design-review recorded where the **live** pass set lives —
      `review_evidence.PASSES` comment + CLAUDE.md PASSES enumeration +
      `independent-review` SKILL.md — per the code-health (060-05) /
      frame-critique (064-03) precedent. ADR-0014's body stays the original
      record (ADR-0010 records-vs-prose); it is **not** amended for this pass.
- [x] ADR-0022 spec-gate Open Question resolved (the attest-only design-review
      pass is the integration; Option D stays parked).
- [x] The *why* is captured by this spec + ADR-0022's resolved OQ (not an
      ADR-0014 edit).
- [x] Formal REVIEWED gate (compliance/craft/arch verdicts on THIS slice) —
      recorded **retroactively** 2026-06-15 after the work was found merged
      (PR #52) while still IN_PROGRESS with no evidence. Three independent
      read-only `jig:reviewer` passes (compliance/craft/arch) all `pass`;
      evidence at `reviews/slice-01-{compliance,craft,arch}.md`; gate cleared
      IN_PROGRESS → REVIEWED.
- [x] Deviation log produced under this slice heading (see below; extended at
      the 2026-06-15 reconciliation).

**Anti-horizontal-phasing check:** After this slice, flagging a slice
`design_review: true` and transitioning it to REVIEWED requires — and a recorded
attest verdict clears — an actual `design-review` verdict on disk. End-to-end
usable by food-log 002-01 even before any auto-discovery of servo's oracle.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

- **Mirrored the `arch` (031-02) sibling exactly at the REVIEWED stage** —
  `design-review` → `review_evidence.PASSES`; `required_passes` gained a
  `design_review` kwarg appending `design-review` to the REVIEWED set only (no
  new stage, unlike 064-03's frame-critique); `_design_review_flag` ≈
  `_arch_review_flag` (shared `FRONTMATTER_TRUTHY`); `validate_evidence` reads
  the flag itself (spawner/gate no-drift); `workflow.py` gained
  `slice_needs_design_review` + a `design-review-needed` CLI + a `session_plan`
  phase; `review.py` gained `build_design_review_prompt` + a `design-review` CLI;
  `record-review --pass` accepts it automatically (choices derive from `PASSES`).
- **Three genuine departures from `arch` (recorded, not silent):**
  1. **No richer-skill detection** — `build_arch_review_prompt` calls
     `detect_richer_skill("arch-review")`; design-review omits it (no external
     "design-review" skill category — it attests jig's *own* eval evidence;
     same rationale as code-health / frame-critique).
  2. **Attest-only prompt + dedicated `_DESIGN_REVIEW_OUTPUT_FORMAT`** (buckets:
     summary / eval-ran / non-stale / threshold-met / verdict; no
     reconciliation-notes) with an explicit "ATTEST — do not re-derive" body.
     This is the ADR-0022 honesty boundary made observable: servo runs/scores,
     jig attests; an `env_error` ≠ pass ≠ 0.0; composite ≥ the eval's *own*
     frozen threshold.
  3. **`session_plan` routes the pass to `jig:independent-review`**, not an
     `arch-review`-style external skill (there is none).
- **ADR-0014 deliberately NOT amended.** Its body is the original closed record;
  the later code-health (060-05) and frame-critique (064-03) passes were added
  the same way — extend `PASSES` + record in CLAUDE.md/SKILL.md, leave the ADR
  (ADR-0010 records-vs-prose). The *why* lives in this spec + ADR-0022's resolved
  spec-gate OQ (which also answers ADR-0019 OQ2: "how thin is attest-only?" —
  *as thin as a review pass*). Option D (the tight servo exit-code binding for
  bug/refactor) stays PARKED — this slice did not build it.
- **Runtime:** `scripts/run_tests.py` + the jig helpers require Python ≥3.10;
  this machine's system `python3` is 3.9.6 (produces spurious `zip()` / scaffold
  errors). Ran the suite via `~/.local/bin/uv run --python 3.12`; under 3.12 only
  the pre-existing, environmental git-reservation / linked-worktree E2E failures
  remain (the failing subset is machine-dependent — see the DoD note).
- **jig-main is not a git repo** in this workspace — these changes are edited in
  place and need **upstreaming** to the real jig repo separately (alongside the
  Phase-4 servo `capture.mjs` fix and the Phase-6-prep servo `score.py` CLI
  transport on the servo side).
  **UPDATE 2026-06-15:** the upstreaming happened — this code merged to the jig
  repo as PR #52 (commit `1d23958`). The note above is preserved as the original
  implementation record; it no longer describes current state.
- **First consumer:** food-log slice 002-01 (servo design-fidelity eval) — a
  slice there can now set `design_review: true` and the REVIEWED gate will
  require an attested `reviews/slice-NN-design-review.md` verdict.

#### Reconciliation addendum — 2026-06-15 (retroactive close-out)

This slice was found **merged (PR #52) while still IN_PROGRESS with no review
evidence on disk** — it never went through jig's lifecycle gate because the work
was authored in a vendored jig copy (servo/food-log workspace) and upstreamed via
a manual PR, a path that bypasses both the ADR-0014 transition gate and the
`land.py` readiness gate (root-cause diagnosis captured in the user's memory note
`jig-review-gate-offpath-bypass`; the out-of-band CI/branch-protection prevention
fix is parked pending user direction). Closed out properly here:

- **Three independent review passes** (compliance/craft/arch, all `pass`) recorded
  at `reviews/slice-01-{compliance,craft,arch}.md`; gate cleared IN_PROGRESS →
  REVIEWED → RECONCILED → DONE.
- **Nit-fixes applied at reconciliation** (surfaced by those passes):
  1. `skills/independent-review/SKILL.md` — corrected a blockquote copied from
     frame-critique that wrongly claimed slice 064-04 derives `design_review`
     "mechanically". `design_review` is **hand-set** (no derive trigger, unlike
     `frame_review`); the caveat now says so.
  2. `skills/spec-workflow/test_workflow.py` — added the `design_review` kwarg to
     `_GateFixture.write_slice` and a blocked/clears/ignores **REVIEWED-gate test
     triad** for `design-review` (mirroring the arch / code-health siblings).
     This makes AC#2's "gated/ungated REVIEWED transition" coverage claim
     **literally true** (it was only transitively covered before) and satisfies
     AC3's "provable by transitioning a flagged vs unflagged slice".
- **Parked nit:** the four near-identical `_*_review_flag` helpers — parametrize
  on the fifth gated pass (`docs/refinement-todo.md`).
- **Dependency correction (for DONE):** the frontmatter `dependencies:` was
  `[adr-0014, adr-0022]`, which blocked DONE because **ADR-0022 is deliberately
  PARKED** (Proposed, frame-critique `needs-changes`, ahead of demand). But
  ADR-0022's own body states this slice's integration question was *"answered
  independently of Option D … on the existing ADR-0014 rails"* — so 071-01's
  load-bearing dependency is **ADR-0014** (the review-evidence model it extends),
  and ADR-0022 is *resolved-by* this slice (OQ2), **not** depended-on. Corrected
  to `dependencies: [adr-0014]`. This fixes a mis-modeled dependency; it does not
  bypass any review gate. ADR-0022 stays parked under its own demand triggers.
