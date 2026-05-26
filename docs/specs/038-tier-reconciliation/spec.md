---
status: DRAFT
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

### Slices (TBD until clarify runs)

1. **`038-01 policy-adr`** — ADR with two options spelled out (real
   tier vs. informational tier), recommendation, consequences.
   Accept before slice 2.
2. **`038-02 align-implementation`** — under the accepted policy:
   - (a): `_copy_skills_and_agents` filters by `installed_tiers`;
     wizard's `--has-tests` gates Tier 1; manifest ↔ on-disk
     regression test added.
   - (b): `_TIER_SKILLS` becomes informational; manifest records
     tiers but doesn't gate copy; README/vision reword; wizard
     drops the test-presence question (or repurposes it).
   Vertical: end-to-end "manifest and on-disk reality match"
   in one slice.
3. **`038-03 reconcile-secondary-inconsistencies`** —
   `vision-elicitation` + `contracts` tier assignment fixed in
   both `_TIER_SKILLS` and the vision numbered list. README's
   "5 Tier 0 / 8-12 total" line fixed to match post-slice-2 reality.

Slices 2 and 3 may collapse into one if the policy makes them
trivially related.

## Open questions for `/jig:clarify`

- **Q1.** If (a) wins, what's the upgrade story for projects that
  already scaffolded all 14 skills? Lean: no automatic uninstall;
  users keep what they have or manually `rm`. Tied to
  `refinement-todo`'s `update` skill (slice 016-04).
- **Q2.** Does the dumb-zone positioning actually hinge on this?
  Worth answering with numbers: 14 SKILL.md files vs. 7 — what's
  the actual context cost? If it's noise relative to the user's
  own code, (b) is cheaper and equally honest. If it's load-bearing,
  (a) is necessary.
- **Q3.** Anti-horizontal-phasing — slice 2 in either option
  crosses manifest-write, copy-logic, and verify-install. Three
  layers, but all three deliver one end-to-end "install matches
  manifest" outcome. Confirm defensible.

## Dependencies / coordination

- **Should run after spec 036** (closed-spec drift policy) so the
  vision/README edits this spec produces follow whatever amendment
  convention 036 establishes.
- **Coordinate with spec 040** (isolation honesty) — both edit the
  README. Land in series, not parallel, to avoid adjacent-line
  conflicts.
- **Picks up drift #5** from spec 036 (README "5 Tier 0 / 8-12")
  — that line is deferred from 036's sweep to this spec.

## References

- External review brief: [`brief-01-tier-reconciliation.md`](../../external-review/brief-01-tier-reconciliation.md)
- Verification 2026-05-26: `_copy_skills_and_agents` confirmed
  tier-blind; `verify_install` claim in brief corrected (asserts
  `>= 1`, not 14).
