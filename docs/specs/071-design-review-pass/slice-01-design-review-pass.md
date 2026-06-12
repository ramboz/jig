---
status: IN_PROGRESS
dependencies: [adr-0014, adr-0022]
last_verified: 2026-06-12
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
- [x] All ACs pass; full test suite green — `scripts/run_tests.py` (uv 3.12):
      **2635 tests, 2 failures**, both the pre-existing/environmental
      `ReserveSpec/AdrFromLinkedWorktreeE2E` git-stderr-wording E2Es (this git
      emits `'main' is already checked out at …` vs the asserted `already used
      by worktree`) — unrelated to this slice's code path.
- [x] New tests cover: prompt builder text (attest-only, "do NOT re-derive"),
      flag truthy-token recognition, gated/ungated REVIEWED transition, verdict
      artifact round-trip — mirroring the arch (031-02) / frame (064-03) tests.
- [x] `uvx ruff check` clean on changed files + `spec_lint.py` clean on the 070
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
- [ ] Formal REVIEWED gate (compliance/craft/arch verdicts on THIS slice) — the
      remaining lifecycle ceremony; out of Phase-5 scope (which was to build the
      pass), left for the orchestrator to run.
- [ ] Deviation log produced under this slice heading.

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
  the 2 environmental git-wording E2E failures remain.
- **jig-main is not a git repo** in this workspace — these changes are edited in
  place and need **upstreaming** to the real jig repo separately (alongside the
  Phase-4 servo `capture.mjs` fix and the Phase-6-prep servo `score.py` CLI
  transport on the servo side).
- **First consumer:** food-log slice 002-01 (servo design-fidelity eval) — a
  slice there can now set `design_review: true` and the REVIEWED gate will
  require an attested `reviews/slice-NN-design-review.md` verdict.
