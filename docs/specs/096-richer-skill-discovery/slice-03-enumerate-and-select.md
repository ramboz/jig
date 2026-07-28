---
status: DRAFT
dependencies: [096-04]
last_verified:
frame_review: true
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 096-03 — enumerate-and-select

**Goal:** Absent config, jig picks up a richer skill with **zero configuration**
over an **explicit printed candidate channel** (ADR-0040 D3):
`review.py candidates <category> <spec> <slice> --pass <pass>` enumerates
non-baseline candidates, prints them **tiered**, and **writes the shown set to a
sidecar**; the orchestrator selects from the printed list; the pass takes
`--richer-skill` and the pick is recorded into the same sidecar. No ambient-context
assumption, no router.

**Why `arch_review: true`:** introduces a new CLI contract (`candidates`
subcommand + `--richer-skill` on the three passes), a new shared-state artifact
(the sidecar), and moves a resolution responsibility to an explicit channel — a
public-contract and boundary change.

**Why `dependencies: [096-04]`:** the whole channel rests on the orchestrator
actually running the sequence. 096-04 probes that premise first; this slice is
built only on a PASS (else it stays DEFERRED per 096-04 AC4).

**DoR:**
- ✅ 096-02 DONE (name→path resolution + exclusion exist).
- ✅ 096-04 PASS (the orchestrator reliably runs `candidates → pick →
  --richer-skill`). On FAIL/INCONCLUSIVE this slice is DEFERRED.
- ✅ Spike evidence recorded: naive substring matching over-nominates
  (`morning-github`), so tiering — not a hard filter — carries precision.

**Acceptance Criteria:**

1. **`candidates` prints the full recall set, tiered — it does not filter**
   (ADR-0040 D3). `review.py candidates <category> <spec> <slice> --pass <pass>`
   enumerates all non-baseline skills across scopes and prints two tiers:
   **high-confidence** (matcher-classified for the category, with
   `name` + `description`) and **speculative** (everything else nominated, as
   **names only**). Deterministic and order-stable. It MAY over-offer into
   speculative; it MUST NOT be the thing that picks. The print format bounds
   context cost (descriptions only for high-confidence).
2. **`candidates` writes the shown set to a sidecar** keyed to `(slice, pass)`,
   in the same call that prints it — the sidecar is written by the *act of
   showing*, and nothing downstream re-enumerates. This is the sole writer of the
   candidate set (ADR-0040 D3 — one enumeration code path).
3. **`--richer-skill <name|none>` is a required argument on the three passes.**
   `review.py pr-review …` (and arch, code-health) refuse with a non-zero exit
   and a clear message when the flag is absent. Requiredness is load-bearing
   (ADR-0039 §3 rule 2): a silent default would decay this into inert prose.
4. **A supplied name is validated deterministically before use.** The name is
   resolved via 096-02 and used only when it resolves to an existing,
   non-baseline SKILL.md **present in one of the two printed tiers**. An
   **off-list** name (not in either tier) → falls back to baseline and is
   recorded, NOT accepted (accepting it would make "the declared substrate" a
   fiction). An unresolvable or baseline-marked name likewise falls back without
   erroring the pass. The pick is written into the existing sidecar; the pass does
   not author the candidate set.
5. **`--richer-skill none` is honored and yields the baseline** without error.
   Explicitly supported: the user may legitimately want no richer skill applied.
6. **A fail-fast guards the orchestrated path.** When a pass is invoked with no
   sidecar present, no config, and no `--non-interactive` declaration, it exits
   non-zero naming the missing `candidates` step (ADR-0040 D3). This is a
   convenience, not the guarantee — the guarantee is 096-05's `record-review`
   substrate. `--non-interactive` is the documented CI/no-orchestrator escape.
7. **Precedence holds end-to-end.** Config (096-01) wins over any supplied
   selection; the supplied selection wins over the legacy exact-name lookup;
   baseline is last. `detect_richer_skill`'s exact-name/user-scope-only behavior
   is **removed** in this slice, superseded by the chain (and 096-05 ships the
   record alongside, so no window of un-recorded baseline fallback opens).
8. **The orchestrator is instructed to select, in the skill prose.**
   `spec-workflow` / `bug-fix` SKILL.md recipes tell the orchestrator to run
   `candidates`, pick the single best candidate from the printed tiers, and pass
   it — including the multiple-candidates rule (pick one, do not refuse) and the
   honest framing that the pick is a heuristic, overridable by config.
9. **Sidecar lifetime, absence, and staleness are defined — this is a
   correctness requirement, not an implementation detail** (ADR-0040 OQ2, which
   this slice owns because it ships the sidecar). The sidecar must survive from
   `candidates` through the reviewer spawn to `record-review`. The slice defines:
   where it lives, when it is cleaned up, what a *concurrent* pass for the same
   `(slice, pass)` does, and — load-bearingly — how **absence** (step never ran)
   is distinguished from **staleness** (a leftover from a prior run). A stale
   sidecar must not read as a clean `shown`; an over-eager cleanup must not read
   as `not-shown`. 096-05's entire anomaly rests on this distinction being
   honest, so it is tested here. The sidecar schema **retains per-candidate tier
   membership** (high-confidence vs speculative), which 096-05's anomaly reads.

**Edge cases to cover explicitly:**
- Zero candidates enumerated → `candidates` prints an empty set, sidecar written
  empty; `none` is the correct selection; baseline applies; no anomaly (096-05).
- Multiple genuine candidates → orchestrator picks one; alternatives are the
  shown-and-declined set carried into the sidecar for 096-05. Tiering never
  tiebreaks by lexical order (the spike showed that elevates a false positive).
- A supplied name at a scope the reviewer cannot read (096-02 AC6) → falls back
  to baseline, recorded.
- CI / no-orchestrator run → `--non-interactive`; config remains the
  CI-reproducible path.
- Off-list pick (name absent from both tiers) → baseline + recorded (AC4).
- Stale sidecar from a prior run → not read as a fresh `shown` (AC9).
- Concurrent pass for the same `(slice, pass)` → defined, non-corrupting (AC9).

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] A regression test asserts the **originating bug** is fixed: a richer skill
      installed at user scope under a non-matching name (`review-pr-deep`) is
      enumerated and appears in a printed tier for the `pr-review` category.
- [ ] A regression test asserts the **spike's false positive** is not silently
      elevated: a briefing-style skill mentioning "stage draft PR reviews" lands
      in **speculative**, not high-confidence, and is never auto-selected by
      enumeration alone.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed. Arch pass passed (`arch_review: true`).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] `docs/skill-routing-verification.md` updated — the documented answer to
      "how do I verify deferral worked?" changes shape in this slice.
