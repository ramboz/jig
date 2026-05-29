---
status: DONE
skill: scaffold-init
tier: (none — dev infrastructure)
adr_required: true
---

# Spec 038: Tier system reconciliation — scaffold reality vs. manifest claims

## Overview

jig's positioning rests on "tier-gated installs" — the README and
vision docs claim Tier 0 is a small floor and Tier 1 is opt-in default.
The scaffold-init manifest reflects this claim. **The on-disk copy
ignores it.**

- `scaffold.py:_select_tiers` picks `installed_tiers = ["tier-0"]` by
  default, adds `"tier-1"` only if `signals.has_tests`.
- `_copy_skills_and_agents` iterates every skill dir with a `SKILL.md`
  and copies it — **no filter on `installed_tiers`**. All 14 skills
  land on disk regardless of flags.

Both invocations (with and without `--has-tests`) produce **byte-identical
skill sets**. The manifest field is effectively a metadata hint, not a
copy gate. The wizard's "Existing tests?" question (slice 001-05) is
a no-op for on-disk outcomes — it changes the manifest text only.

Three secondary inconsistencies compound the gap (all verified
2026-05-26):

- `vision-elicitation` is in `_TIER_SKILLS["tier-0"]` (scaffold.py:56)
  but **does not appear** in the vision document's numbered Tier 0
  list (items 1–5).
- `contracts` is in `_TIER_SKILLS["tier-0"]` (scaffold.py:57) but the
  vision puts it at **item #11 (Tier 1)**. The two are inconsistent.
- README still says "5 Tier 0 skills" (line 35) and "8-12 skills
  total" (line 38). Reality: 7 / 14.

This is a **positioning decision**. ADR-first.

## Why now

- **Touches the "stay below the dumb zone" pitch.** Anyone evaluating
  jig reads the Tier 0 floor as a promise: small, opinionated, won't
  overwhelm context. The current install delivers 14 skills regardless.
- **Wizard Q&A is a no-op.** The user is being asked to influence an
  outcome they cannot influence. Either the answer needs to start
  gating, or the question needs to go.
- **Three secondary inconsistencies have been latent for months.**
  They survive because no test asserts manifest ↔ on-disk consistency.

## Goals

1. **Decide the policy via ADR.** Two coherent options:
   - **(a) Tiering is real.** Tier 1 skills are not copied unless
     the tier is "installed." `_copy_skills_and_agents` filters by
     `installed_tiers`. README/vision positioning becomes accurate.
   - **(b) Tiering is informational.** All shipped skills always
     copy; `installed_tiers` records *workflow opt-in* rather than
     copy gating. README + vision get reworded: "14 skills ship;
     tiers are conceptual groupings." Wizard Q&A is reshaped or dropped.

2. **Reconcile the secondary inconsistencies.** Under whichever policy
   wins, `vision-elicitation` and `contracts` get a stable tier
   assignment in both `_TIER_SKILLS` and the vision numbered list.

3. **Implement the wizard's effect, or drop the question.** If (a)
   wins, the wizard's `--has-tests` answer must actually gate. If (b)
   wins, the question is removed (or repurposed for something it
   genuinely controls).

4. **Pin with a regression test** that asserts manifest ↔ on-disk
   consistency. Today's tests verify each side independently and
   miss the gap.

## Non-goals

- **No new Tier 2.** The vision's "Tier 2 stays empty until pain is
  reported" rule is upheld.
- **No tier reassignment of skills.** Whatever winds up in Tier 0 vs
  Tier 1 stays. This spec is about *which skills land on disk*, not
  *which skills should be in which tier*.
- **No per-skill opt-out.** Tier-level granularity only.
- **No migration tooling** for projects that scaffolded under the
  current behavior. Re-running scaffold-init or accepting the
  inflated install both work; cluster 4's deferred `update` skill
  (slice 016-04) would handle the upgrade story when it lands.
- **No rewrite of `verify_install.py`.** Brief 01 claimed the
  verifier asserts 14 skills under `--mode scaffold`; verification
  on 2026-05-26 showed it actually asserts `>= 1` (`check_scaffold_skills_present`
  at `scripts/verify_install.py:150`). No tier-aware rewrite needed
  in either path.

## Current state (verified 2026-05-26)

- `_TIER_SKILLS["tier-0"]` (scaffold.py:50): 7 skills — `scaffold-init`,
  `memory-sync`, `spec-workflow`, `independent-review`, `migrate`,
  `vision-elicitation`, `contracts`.
- `_TIER_SKILLS["tier-1"]` (scaffold.py:59): 7 skills — `adr-workflow`,
  `tdd-loop`, `slice-land`, `pr-review`, `arch-review`, `clarify`,
  `analyze`.
- `_copy_skills_and_agents` (scaffold.py:484): iterates every dir
  with a `SKILL.md`, copies all 14. No tier filter.
- `_select_tiers` (scaffold.py:382): manifest path; `has_tests` only
  affects the recorded tier list.
- Wizard apply (scaffold.py:222 / 423): `has_tests` flows into
  manifest + diagnostic line — never copy logic.
- README claim mismatch: lines 35 (`5 Tier 0`), 38 (`8-12 total`).
- Vision numbered list mismatch: items 1–5 are Tier 0; `contracts`
  at #11 conflicts with `_TIER_SKILLS["tier-0"]`; `vision-elicitation`
  is in `_TIER_SKILLS["tier-0"]` but absent from the numbered list.

## Decomposition

**Suggested SPIDR axis: R (Rules)** primary (rule = "tier means X"),
**P (Path)** secondary (option (a) vs option (b) are alternative
implementation paths).

### Slices (finalized 2026-05-29 — policy decided: option (a) real
gated tiers + first-class upgradeability; see ADR-0010)

1. **`038-01 policy-adr`** — ADR-0010 records the decision (real
   gated tiers vs. informational; recommendation; consequences;
   source-of-truth rule). Accept before slice 2.
2. **`038-02 gate-copy-by-installed-tiers`** —
   `_copy_skills_and_agents` filters by `installed_tiers`, and **both**
   its callers (`scaffold()` and the `copy_machinery()` façade behind
   `migrate.py copy-machinery`) thread tiers through — otherwise the
   gap just relocates to the migrate path. Because `_select_tiers`
   already maps `has_tests → tier-1`, this also makes the wizard's
   `--has-tests` answer gate Tier 1 with no separate wizard-wiring
   step. Manifest ↔ on-disk regression test added; infrastructure
   (`_<name>` modules, `agents/`) stays ungated. Vertical: end-to-end
   "install matches manifest" in one slice.
3. **`038-03 reconcile-doc-inconsistencies`** — vision numbered list +
   README counts reconciled to `_TIER_SKILLS` (the source of truth per
   ADR-0010): `vision-elicitation` added to the Tier 0 list,
   `contracts` placed at Tier 0, README "5 Tier 0 / 8-12 total" → 7 /
   14. Closed-spec or router-load-bearing edits follow ADR-0008's
   `## Amendments` rule (resolves ADR-0008's deferred drift #5).
4. **`038-04 tier-upgrade-path`** — additive post-scaffold upgrade so a
   Tier-0 project can add Tier 1 later without re-scaffolding (the
   capability ADR-0010 commits to). Builds on the **existing**
   `migrate.py copy-machinery` path (spec 021), which already copies
   machinery additively into a set-up project and bypasses the
   fresh-scaffold guard — the work is making `copy_machinery` read
   `installed_tiers` from the target manifest + a tier-bump affordance,
   not a new entry point. Vehicle detail (a `--add-tier` flag vs.
   manifest-edit-then-rerun; whether this promotes the deferred `update`
   skill, 016-04) decided in implementation. **Added per the
   maintainer's decision** ("make sure we can update to higher tiers
   later as the project evolves") — beyond the spec's original
   three-slice sketch.

Note: the original sketch's combined `038-02 align-implementation`
narrowed because option (a) won — wizard-gating falls out of the copy
filter for free, so 038-02 is the single gating slice with no separate
wizard handling.

## Slices

- [038-01 — policy-adr](slice-01-policy-adr.md)
- [038-02 — gate-copy-by-installed-tiers](slice-02-gate-copy-by-installed-tiers.md)
- [038-03 — reconcile-doc-inconsistencies](slice-03-reconcile-doc-inconsistencies.md)
- [038-04 — tier-upgrade-path](slice-04-tier-upgrade-path.md)

## Open questions for `/jig:clarify`

_All resolved 2026-05-29 by the maintainer's policy decision + the
Q2 context-cost measurement. Retained for audit trail._

- **Q1 — RESOLVED.** Upgrade story for already-scaffolded projects: no
  automatic uninstall (legacy all-14 installs keep what they have).
  Going forward, post-scaffold tier *upgrade* is first-class and
  additive — slice 038-04. Tied to the deferred `update` skill (016-04),
  which 038-04 may promote.
- **Q2 — RESOLVED.** The dumb-zone positioning does **not** hinge on
  this: all-14 descriptions cost ≈ 2,674 always-in-context tokens
  (gating saves ≈ 1,218 ≈ 0.6% of a 200K window; bodies load only on
  invocation). Option (a) was chosen on promise-integrity, wizard-
  correctness, and routing-surface grounds — not token budget. See
  ADR-0010 "What the numbers say about the dumb-zone rationale."
- **Q3 — RESOLVED.** Anti-horizontal-phasing confirmed defensible: the
  gating slice (038-02) crosses manifest + copy-logic but delivers one
  end-to-end "install matches manifest" outcome. The `verify_install`
  layer is unaffected (it asserts `>= 1`, per the spec's non-goals), so
  the slice is narrower than the original three-layer concern.

## Dependencies / coordination

- **Should run after spec 036** (closed-spec drift policy) so the
  vision/README edits this spec produces follow whatever amendment
  convention 036 establishes.
- **Coordinate with spec 040** (isolation honesty) — both edit the
  README. Land in series, not parallel, to avoid adjacent-line
  conflicts.
- **Picks up drift #5** from spec 036 (README "5 Tier 0 / 8-12")
  — that line is deferred from 036's sweep to this spec.
- **Builds on spec 021** (migrate `copy-machinery`) — the existing
  additive machinery-copy path is slice 038-04's upgrade vehicle. Both
  it and greenfield `scaffold()` share `_copy_skills_and_agents`, so
  slice 038-02's gating must cover both callers.

## References

- Policy decision: [ADR-0010 — Scaffold-init tiers gate which skills
  install](../../decisions/adr-0010-scaffold-tier-gated-install.md)
- External review brief: [`brief-01-tier-reconciliation.md`](../../external-review/brief-01-tier-reconciliation.md)
- Verification 2026-05-26 (re-confirmed 2026-05-29 at HEAD `b7117c5`):
  `_copy_skills_and_agents` confirmed tier-blind; `verify_install`
  claim in brief corrected (asserts `>= 1`, not 14).
