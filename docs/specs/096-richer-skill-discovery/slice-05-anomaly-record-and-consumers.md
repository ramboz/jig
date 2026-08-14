---
status: DONE
dependencies: [096-03]
last_verified: 2026-08-14
frame_review: true
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 096-05 — anomaly-record-and-consumers

**Goal:** Make "a richer skill was available and was not applied" **visible**,
with a producer that is **not the audited agent** (ADR-0040 D3). `record-review`
*derives* a closed `substrate:` vocabulary from observable state (config presence
+ sidecar presence) and records the applied skill plus the shown-and-declined
set; at least one committed consumer surfaces the anomaly — so "did deferral
actually work?" is answerable after the fact.

**Why this exists:** every fallback path in the precedence chain converges on
jig's baseline, which is exactly the reported bug's terminal state. Requiredness
of `--richer-skill` enforces arity, not correctness. Auditability — not
enforcement — is what ADR-0040 can honestly offer, so it must actually be built.

**DoR:**
- ✅ 096-03 DONE (the `candidates` sidecar + selection exist, so there is a shown
  set and a pick to record).
- ✅ ADR-0014's evidence-artifact shape understood — this slice **extends** the
  frontmatter; it must **not** change the gate predicate (`verdict:` only).
- ✅ ADR-0040 D3 `substrate:` vocabulary + `record-review` chokepoint understood.

**Acceptance Criteria:**

1. **`record-review` derives a closed `substrate:` from observable state**
   (ADR-0040 D3) — never accepting it as an orchestrator-typed flag. Exactly one
   of: `config` (config key present), `shown` (sidecar present with candidates +
   a pick), `not-shown` (no sidecar, no config, no `--non-interactive`),
   `non-interactive` (caller-declared), `n/a` (out of scope). It also records the
   applied skill (or `none`) and the shown-and-declined candidate set read from
   the sidecar. Recording the choice alone is insufficient — it cannot
   distinguish "nothing installed" from "three shown, none applied".
2. **Computation is scoped by `(category ∈ {pr_review, arch_review, code_health})
   AND (keying mode == slice)`** (ADR-0040 D3, the keying-mode fix). Everything
   else — `--bug`, `--adr`, and the never-defer passes (`compliance`,
   `reconciliation`, `frame-critique`, `design-review`) — is stamped `n/a`.
   Critically, `craft` is a shared pass token and `bug-fix` runs it in-category,
   so a category-only scope would stamp `not-shown` on every bug fixed — the
   scope MUST exclude by keying mode. A test asserts a bug-keyed `craft` artifact
   is `n/a`, not `not-shown`.
3. **The anomaly is calibrated, not raw.** It fires only against the
   **high-confidence** tier of the shown-and-declined set (ADR-0040 D3), plus the
   **shown-but-no-pick** state (a `shown` sidecar with candidates and no recorded
   pick — the cheapest-defection artifact — recorded applied=`unknown`,
   anomaly-eligible). It never fires on the speculative tier or the raw
   nomination list. On the probed corpus a legitimate `none` must not trip it via
   `morning-github` (which lands speculative).
4. **The anomaly does NOT block.** `transition … REVIEWED` behaves identically
   with and without an anomaly present. ADR-0014's gate stays a one-line
   predicate on `verdict:`; `substrate:` is recorded, never gated on. A test
   asserts a `not-shown` / anomaly artifact with `verdict: pass` still reaches
   REVIEWED.
5. **At least two committed consumers surface it.** `check-reviews` emits a
   **non-blocking stderr warning** naming the declined high-confidence candidates
   (and the shown-but-no-pick state) — its **exit-code contract is unchanged**
   (still 0 clean / 2 on evidence-gate failure; the warning never flips the exit
   or blocks, per ADR-0014 §3 and ADR-0040's "check-reviews keeps its existing
   contract"). `status-board` renders aggregate `not-shown` + `non-interactive`
   counts — the kill-criterion-1 aggregator (ADR-0040), which is where all
   aggregation lives (`check-reviews` does not aggregate). `status-board` alone
   satisfies the "≥1 committed consumer" floor; the `check-reviews` advisory is
   additive.
6. **Backward compatibility.** Evidence artifacts written before this slice (no
   `substrate:` / no candidate fields) parse without error, are treated as
   *(field absent)*, and produce no anomaly — absence of data is not evidence of
   an anomaly. A hand-written artifact carrying only the required fields is the
   same *(field absent)* state (the honest-actor chokepoint's residual, named in
   ADR-0040, not papered over).
7. **The `config` and recall blind spots are documented, not solved.**
   `substrate: config` is derived from presence and is anomaly-blind exactly
   where the guaranteed layer lives; and if enumeration nominates nothing, no
   anomaly fires and a recall failure is invisible. Both are recorded in prose
   (spec + `docs/skill-routing-verification.md`) as accepted gaps whose
   mitigation is config precedence (096-01), not as solved problems.

**Edge cases to cover explicitly:**
- Anomaly + `verdict: pass` → transition succeeds, warning emitted.
- Config-selected skill (096-01) → `substrate: config`, no anomaly, even when
  other candidates exist (the user chose deliberately).
- `--richer-skill none` with zero candidates shown → no anomaly (nothing declined).
- `shown` sidecar with candidates but no recorded pick → anomaly-eligible
  (applied=`unknown`); must not read as a clean decline.
- Bug-keyed / ADR-keyed / never-defer-pass artifact → `substrate: n/a`, never
  counted.
- Malformed / partial candidate data in an artifact → parsed defensively, no
  crash in `check-reviews` or `status-board`.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one fixture
      (SubstrateRecordAndConsumerTests, SubstrateAnomalyTest, StatusBoardTests
      audit cases). Edge cases covered.
- [x] An explicit test asserts the ADR-0014 gate predicate is **unchanged**
      (`test_not_shown_artifact_still_clears_gate`).
- [x] An explicit test asserts the keying-mode scope (AC2): a bug-keyed `craft`
      artifact is `n/a` (`test_bug_keyed_craft_has_no_substrate`).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
      _(post-hoc close-out; verdicts in `reviews/slice-05-{compliance,craft}.md`.)_
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred — no new
      deferrals.

### Deviation log (after reconciliation)

Original ACs preserved. Implementation notes:

- **`record-review` is the substrate chokepoint (AC1).** `_substrate_lines`
  derives the closed vocabulary from observable state: config (096-01) →
  `--non-interactive` (caller-declared, the one sanctioned declaration) →
  `shown` (a 096-03 candidates sidecar exists — read + CONSUMED here, completing
  AC9's "staleness impossible by construction") → `not-shown` (the defect
  signal). Records `applied_skill` + `shown_candidates` (name:tier).
- **Scope = keying-mode + category (AC2).** Only `record_review`'s slice-keyed
  path calls the deriver; `--bug` / `--adr` use separate recorders that never
  stamp a substrate (so a bug-keyed `craft` is `n/a`, NOT `not-shown` — the exact
  keying-mode fix ADR-0040 D3 required). Never-defer / uncategorized passes get
  no stamp (field absent = `n/a`).
- **The anomaly is calibrated (AC3).** `review_evidence.substrate_anomaly` fires
  only on `substrate: shown`, against the **high-confidence** tier of the shown
  set; `shown`-but-`applied: unknown` (no pick recorded — cheapest defection)
  counts all high-confidence as declined. Never fires on speculative / config /
  not-shown / non-interactive / absent.
- **Gate untouched (AC4).** `verdict_clears` is unchanged (a `verdict:`-only
  predicate) with an explicit comment that `substrate:` is never consulted; a
  test asserts a `not-shown` + anomaly artifact with `verdict: pass` still clears
  REVIEWED.
- **Two consumers (AC5).** `check-reviews` emits a **non-blocking** stderr
  advisory (exit-code contract unchanged); `status-board` renders a regen-managed
  **"Richer-skill selection audit"** section aggregating `not-shown` +
  `non-interactive` counts + the shown-and-declined anomalies (the
  kill-criterion-1 aggregator). The section is omitted entirely on a clean corpus
  (no noise for quiet projects).
- **Backward compatibility (AC6).** Pre-096-05 / hand-written artifacts have no
  `substrate` field → `substrate_anomaly` returns `[]`, `status-board` skips
  them, and the gate is unaffected — absence of data is never an anomaly.
- **Blind spots documented, not solved (AC7).** `config` is anomaly-blind (the
  guaranteed layer isn't audited); a recall failure is invisible (nothing shown →
  no anomaly). Recorded in `spec.md` Goal 3 + `docs/skill-routing-verification.md`
  as accepted gaps whose mitigation is config precedence (096-01).
- **AC1 wording vs implementation (compliance-review note):** AC1 phrases the
  `config` trigger as "config key present"; `_substrate_lines` stamps `config`
  only when the key is present AND **resolvable** on this machine (mirroring
  `_resolve_richer_for_pass`'s "config wins iff resolvable" precedence). A
  present-but-unresolvable key falls through to `shown`/`not-shown`. Intentional
  and consistent with the resolver; a present-but-unresolvable config is the
  096-01 "recorded, not errored" runtime-absence case.
- **`n/a` is never written (compliance-review note):** the vocabulary member
  `n/a` is represented as the substrate field being *absent* (out-of-scope pass
  or pre-096 artifact), not a literal `substrate: n/a`. Commented at
  `review_evidence.SUBSTRATE_VALUES`.

### Reconciliation sweep

- **Deviation log** — updated (above).
- **`skills/independent-review/review.py`** — `_substrate_lines` deriver +
  consume; `record-review --non-interactive`; `check-reviews` advisory. `updated`.
- **`skills/_common/review_evidence.py`** — `substrate_anomaly` +
  `SUBSTRATE_VALUES`; `verdict_clears` comment (gate unchanged). `updated`.
- **`skills/spec-workflow/workflow.py`** — `_substrate_audit_section` wired into
  `regenerate_status_board`. `updated`.
- **`docs/skill-routing-verification.md`** — the substrate record + the two
  blind spots added. `updated`.
- **`docs/specs/.../spec.md`** — Goal 3 blind-spots note. `updated`.
- **Host packages** — regenerated (review.py + review_evidence.py + workflow.py
  propagated); drift `--check` green. `updated`.
- **`docs/architecture.md` / `docs/conventions.md` / `docs/inbox.md`** — no-op.
- **Lightweight decisions** — none.
- **Memory** — the "substrate DERIVED at the record chokepoint + consume-on-read
  closes staleness; config is deliberately anomaly-blind" lesson; folded into
  `/jig:memory-sync` at session close.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `docs/skill-routing-verification.md` updated with the substrate record as
      the answer to "how do I verify deferral worked?", including the `config`
      and recall blind spots. _(done during implementation; verified present.)_
- [x] CLAUDE.md Active-specs entry compressed per the spec 025 close-out rule
      if this closes the spec. _(spec 096 now fully DONE; primer already carried
      no 096 Active-specs entry — nothing to compress.)_
