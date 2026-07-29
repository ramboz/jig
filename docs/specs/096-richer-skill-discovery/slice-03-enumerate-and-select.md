---
status: RECONCILED
dependencies: [096-04]
last_verified: 2026-07-29
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
- [x] All ACs pass; full test suite green (no regressions).
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases covered (CandidateChannelTests, test_candidate_sidecar,
      enumerate tests).
- [x] A regression test asserts the **originating bug** is fixed
      (`test_originating_bug_richer_under_nonmatching_name_enumerated`).
- [x] A regression test asserts the **spike's false positive** is not silently
      elevated (`test_spike_false_positive_lands_in_speculative`).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed. Arch pass passed (`arch_review: true`).
      (compliance + craft + arch all `pass`; review-driven fixes folded in.)
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred — no new
      deferrals (the Codex admin-exclusion + `parse_skill_frontmatter` gaps from
      096-02 are still owned there; bug-fix candidates flow stays OQ1).

### Deviation log (after reconciliation)

Original ACs preserved. Implementation notes + decisions:

- **Module boundary (arch-relevant):** the tiered enumeration/matcher lives in
  `_common/skill_discovery.py` (`enumerate_candidates` + `_classify_for_category`
  + per-category trigger/incidental tables) — it is discovery logic. The sidecar
  is a new leaf `_common/candidate_sidecar.py` (stdlib + `atomic_io`). The
  `candidates` subcommand + `--richer-skill` wiring + the resolver chain live in
  `review.py`. Three clean seams.
- **Sidecar lifetime = consume-on-read (AC9):** `candidates` is the sole writer
  of the set; the pass records the pick; `record-review` **consumes** (reads +
  deletes). **Sequencing (arch-review nit):** the write + record halves ship in
  096-03; the *consume* half is **wired by 096-05** (it must delete + record the
  shown set together). So "staleness impossible by construction" is fully
  realized only once 096-05 lands; in the 096-03-only window, staleness is
  prevented by the always-run-`candidates` recipe + the atomic fresh-overwrite
  (a re-review re-runs `candidates`, replacing any leftover). The
  `consume`/absence semantics are shipped + tested here so 096-05 only wires the
  call. Concurrency: atomic writes; distinct passes are distinct keys;
  same-`(slice,pass)` racing is last-writer-wins (documented pathological). Tier
  membership is retained for 096-05.
- **Sidecar never committed (arch-review nit):** `docs/specs/*/reviews/.candidates/`
  is `.gitignore`d — a transient, un-consumed sidecar carries a machine-specific
  `applied_path`, which must not leak into the otherwise-portable, committed
  `reviews/` evidence tree.
- **`candidates` coherence check (arch-review nit):** the `<category>` positional
  must agree with `--pass` (else the sidecar would be keyed under one pass while
  holding another category's candidates) — refused with exit 2.
- **The matcher governs TIERING, never the pick (AC1 / ADR-0040 D3):**
  per-category trigger phrases put a skill in `high-confidence`; an incidental
  briefing/digest marker (`stage draft`, `briefing`, `summariz`, …) demotes it
  to `speculative` — domain-general signals, not corpus-specific names. A miss
  only demotes (still visible + pickable); the orchestrator picks.
- **`detect_richer_skill` REMOVED (AC7):** the legacy user-scope exact-name
  lookup is gone; the resolver chain is config → validated-pick → baseline.
  `RicherSkillFileReadDispatchTests` was rewritten to pin the *removal* (a bare
  user-scope skill is no longer auto-detected → baseline). ~46 pre-096 CLI tests
  were updated for the now-**required** `--richer-skill` (defaulting to the
  CI-reproducible `--richer-skill none --non-interactive` baseline path).
- **AC8 lands in `spec-workflow` SKILL.md only; `bug-fix` is out of scope.**
  The candidates→pick recipe (run `candidates`, pick the best high-confidence,
  multiple-candidates rule, config-overrides framing, CI escape) was added to
  `spec-workflow`'s craft/arch/code-health recipes. `bug-fix`'s craft pass makes
  **no** `review.py pr-review` call (D1 scoped it out), so it cannot take
  `--richer-skill`; it stays disk/router-based, tracked as ADR-0040 OQ1 (already
  noted in `bug-fix/SKILL.md` from 096-01).
- **Off-list pick → baseline, not error (AC4):** a `--richer-skill <name>` not
  present in either printed tier falls back to jig's baseline (so "the declared
  substrate" is never a fiction) without erroring the pass.
- **Pick resolves via the sidecar's stored path, not a name re-resolution
  (compliance-review fix):** `_validate_pick_against_sidecar` looks the pick up
  in the shown set and uses that candidate's recorded `path` (re-checking
  existence + non-baseline), rather than re-resolving `<name>` by directory
  name. This closes a silent-baseline-fallback hole for a skill whose
  frontmatter `name` diverges from its directory name (the name is what
  enumeration recorded + the orchestrator picked) — the exact bug class this
  spec exists to fix. Regression test:
  `test_pick_resolves_via_stored_path_when_name_diverges_from_dir`.
- **Machinery + recipe are identical on both hosts; Codex's config-only posture
  is behavioral, not a code/recipe difference (compliance + reconciliation
  note):** the `candidates`/`--richer-skill` machinery *and* the candidates→pick
  recipe ship byte-identically in both host packages (the Codex-rendered
  `spec-workflow` SKILL.md carries the full step). Codex is "config-only **in
  practice**" solely because 096-04's behavioral probe was **INCONCLUSIVE for
  Codex** (host unauthenticated — the orchestrator was never verified to follow
  the recipe), not because any code path or recipe omits the step on Codex. Once
  Codex is re-probed (re-auth) and passes, its zero-config path is already fully
  shipped. This is the intended 096-04 outcome (Claude PASS / Codex
  INCONCLUSIVE), not a defect.

### Reconciliation sweep

- **Deviation log** — updated (above).
- **`skills/independent-review/review.py`** — `candidates` subcommand,
  `--richer-skill`/`--non-interactive` on three passes, resolver chain,
  `detect_richer_skill` removed, docstrings updated. `updated`.
- **`skills/spec-workflow/SKILL.md`** — craft/arch/code-health recipes carry the
  candidates→pick step (AC8). `updated`.
- **Host packages** — regenerated (skill_discovery + candidate_sidecar +
  review.py + spec-workflow SKILL.md propagated; test files excluded); drift
  `--check` green. `updated`.
- **`docs/skill-routing-verification.md`** — `updated` (brought forward from
  Close-out on the reconciliation reviewer's live-prose note): the stale
  `detect_richer_skill` user-scope-detection section is corrected inline to the
  096-03 candidate channel (config → tiered `candidates` + `--richer-skill` pick
  → baseline; jig baselines excluded by path).
- **`docs/architecture.md`** — `updated` (add `candidate_sidecar.py` to the
  `_common` list; no new ADR — ADR-0040 D3 governs).
- **`docs/conventions.md`** — no-op.
- **`docs/inbox.md`** — swept; nothing resolved.
- **Lightweight decisions** — none.
- **Memory** — the "tiered candidates + consume-on-read sidecar makes staleness
  impossible; matcher governs tiering not the pick" lesson; folded into
  `/jig:memory-sync` at session close.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] `docs/skill-routing-verification.md` updated — done during reconciliation
      (the `detect_richer_skill` section corrected inline to the 096-03 candidate
      channel; the "did deferral work?" answer now points forward to 096-05's
      `substrate:` record).
