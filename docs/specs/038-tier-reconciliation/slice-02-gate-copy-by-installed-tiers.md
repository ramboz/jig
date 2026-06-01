---
status: DONE
dependencies: [038-01]
last_verified: 2026-05-29
arch_review: true
---

## Slice 038-02 — gate-copy-by-installed-tiers

**Goal:** Make `_copy_skills_and_agents` copy only the skills whose
tier is in `installed_tiers`, so a fresh scaffold's on-disk skill set
matches the `scaffold.json` manifest and the wizard's `--has-tests`
answer actually gates Tier 1 (today it copies all 14 regardless).

**DoR:**
- ✅ ADR-0012 accepted (slice 038-01) — gated-copy policy fixed.
- ✅ Wiring confirmed: `_select_tiers` maps `has_tests → tier-1` and
  `_enumerate_skills(installed_tiers)` already yields the gated
  `<tier>/<skill>` list used for the manifest (ADR-0007). The copy
  loop is the only side that ignores it.
- ✅ Caller audit: `_copy_skills_and_agents(plugin, target)` has **two**
  callers — `scaffold()` (greenfield, has `installed_tiers` from
  `_select_tiers`) and the `copy_machinery()` façade
  (`scaffold.py:781`, used by `migrate.py copy-machinery`). Both pass
  no tier argument today. Both must thread it through, or the gap just
  relocates to the migrate path.

**Acceptance Criteria:**

1. **Floor install is gated.** `scaffold-init` on a project with no
   test signal copies exactly the 7 Tier-0 skill dirs into
   `.claude/skills/` (as `jig-<skill>`); none of the 7 Tier-1 skill
   dirs are present.
2. **Tier-1 lands when its tier is installed.** `scaffold-init` with
   `--has-tests` (→ `installed_tiers` includes `tier-1`) copies all 14
   skill dirs.
3. **Manifest ↔ on-disk consistency (regression test).** For any
   invocation, `{dir.name without "jig-" prefix for dirs in
   .claude/skills/ if SKILL.md present}` equals
   `{skill for "<tier>/<skill>" in scaffold.json installed_skills}`.
   This is the test that today's independently-verified two sides let
   slip; it must fail against the pre-slice (tier-blind) copy and pass
   after.
4. **Infrastructure is never gated.** Private shared modules (`_<name>`
   dirs, copied unprefixed) and `agents/*.md` are copied regardless of
   which tiers are installed — the filter must not drop them.
5. **Both callers pass tiers.** `_copy_skills_and_agents` takes
   `installed_tiers` (or equivalent) as a parameter; `scaffold()`
   passes its selected tiers and `copy_machinery()` passes the tiers it
   resolves for the target. Neither caller falls back to the old
   copy-all-14 behavior. (How `copy_machinery` *sources* the tiers —
   reading the target manifest — is slice 038-04's concern; this slice
   only ensures the parameter is threaded and no caller is left
   tier-blind. A safe interim default for `copy_machinery` until 038-04
   lands must be pinned and tested, not left implicit.)

**Edge cases to cover explicitly:**
- A skill directory present on disk but absent from `_TIER_SKILLS`
  (decide + pin: fail-open copy vs. skip — recommend skip with a
  diagnostic, since an unmapped skill has no tier to gate on and
  silently shipping it reopens the gap).
- `contracts` (Tier-0 stub) still copied under the floor install.
- Idempotent re-copy semantics unchanged for the fresh-scaffold path
  (upgrade/re-run is slice 038-04's concern, not this one).

**DoD:**
- [x] All ACs pass; full suite green (no regressions). 1431 tests, OK (3 skipped).
- [x] Tests exercise both `installed_tiers` shapes (floor-only and
      floor+tier-1) and the infrastructure-not-gated case.
- [x] Reviewed by `reviewer` subagent (prompt built by `review.py`).
- [x] Implementation review passed.
- [x] Arch-review pass (this slice changes the copy-step contract —
      `arch_review: true`).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation review passed.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated; Notes column records the
      manifest↔on-disk invariant as load-bearing.

**Anti-horizontal-phasing check:** After this slice, a developer
scaffolding a no-tests project gets a genuine 7-skill floor that
matches what `scaffold.json` and the brief promise; a tests project
gets the full set. The difference is observable in `.claude/skills/`
and verified against the manifest — end-to-end "install matches
manifest" in one slice.

### Deviation log (after reconciliation)

1. **Implemented as planned; no shape deviations.** `_copy_skills_and_agents`
   gained an `installed_tiers` param (default `None` = copy-all); both
   callers thread it (`scaffold()` passes `_select_tiers` output;
   `copy_machinery()` forwards it). Skill→tier gate via a reverse lookup
   over `_TIER_SKILLS`. Infra (`_<name>` modules + `agents/`) kept on
   separate, ungated code paths. 9 new tests in `TierGatedCopyTests`;
   `WithMachineryTests.setUp` switched to `--has-tests` so its mechanics
   tests retain the full 14-skill set. Full suite: 1431 green (3 skipped).
2. **Migrate path remains intentionally tier-blind in this slice
   (handoff to 038-04).** `migrate.py copy-machinery` calls
   `scaffold.copy_machinery` without `installed_tiers`, so it defaults to
   `None` = copy-all — today's behavior, no regression. Real gating on the
   migrate path requires sourcing `installed_tiers` from the target's
   `scaffold.json`, which ADR-0012 and slice 038-04 own. Recorded so a
   future reader does not mistake the un-threaded migrate caller for a
   missed call site. (Both reviewers flagged this as the deferred concern,
   not a defect.)
3. **`installed_tiers=None` is a time-boxed interim, not a permanent
   shim (principle #6).** The default preserves the migrate path's
   copy-all behavior only until 038-04 makes the migrate caller resolve
   tiers. When 038-04 lands, revisit whether the `None` default should be
   removed or made required so it does not calcify into a back-compat
   shim. (Compliance reviewer note.)
4. **Nit — skill→tier reverse map duplicates `_enumerate_skills`'s
   traversal.** Both walk the single `_TIER_SKILLS` source-of-truth table
   (forward vs. reverse), so it is duplicated *iteration*, not data —
   low drift risk, not a boundary violation. Arch reviewer suggested
   extracting a shared `_skill_to_tier()` helper; deferred to 038-04 as a
   non-blocking cleanup (logged here rather than acted on, to keep this
   slice scoped to the gating change).
5. **`copy_machinery` docstring updated at reconciliation** to document
   the new `installed_tiers` param + `None` semantics (both reviewers
   flagged the original omission as cosmetic doc staleness). The sibling
   `migrate.py copy_machinery` docstring touch-up rides with 038-04 when
   that caller actually threads tiers.

**Review outcome:** compliance pass (jig:reviewer) → **PASS**; arch pass
(`arch_review: true`, jig:reviewer) → **PASS**. No blockers from either.
