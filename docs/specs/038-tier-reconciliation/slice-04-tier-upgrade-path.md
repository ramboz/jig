---
status: DRAFT
dependencies: [038-02]
last_verified:
arch_review: true
---

## Slice 038-04 — tier-upgrade-path

**Goal:** Make the **existing** `migrate.py copy-machinery` path
(spec 021) tier-aware so a project that scaffolded the Tier-0 floor can
later add Tier 1 (when tests / workflow appear) without re-scaffolding
or hand-copying. This is the capability ADR-0010 commits to — "Tier 0
is a starting point, not a ceiling" — and it builds on the path that
already copies machinery additively into a set-up project rather than
inventing a new entry point.

**DoR:**
- ✅ Slice 038-02 landed — `_copy_skills_and_agents` (and its
  `copy_machinery()` caller) is tier-aware and threads `installed_tiers`.
- ✅ ADR-0010 requires the upgrade *capability* and that it be
  *additive*; `copy-machinery` already bypasses the fresh-scaffold
  `AlreadyScaffoldedError` guard and copies additively, so the guard
  problem is already solved — this slice does not re-solve it.

**Existing-machinery audit (why this is small):**
- `migrate.py copy-machinery <project-dir>` → `scaffold.copy_machinery()`
  → `_copy_skills_and_agents` + hooks/settings. It is the sanctioned
  "copy into an already-set-up project" path and does **not** trip the
  greenfield guard.
- Gap to close: `copy_machinery` does **not** read the target's
  `scaffold.json` today (so it has no `installed_tiers` source), and
  there is no affordance to *raise* the installed tier.

**Decision to make in implementation (record in deviation log):**
the tier-bump affordance — a `--tiers` / `--add-tier` flag on
`copy-machinery` vs. a documented "edit `installed_tiers` in
`scaffold.json`, then re-run `copy-machinery`" flow. Either way,
`copy_machinery` must read `installed_tiers` from the target manifest.
Also decide whether this work **promotes / closes the deferred `update`
skill (016-04)** or leaves it deferred with copy-machinery as the
vehicle; reconcile the 016-04 status either way.

**Acceptance Criteria:**

1. **Additive upgrade works via copy-machinery.** A documented
   `copy-machinery` invocation upgrades an already-scaffolded Tier-0
   project to include Tier 1: the 7 Tier-1 skill dirs appear in
   `.claude/skills/`; pre-existing files (Tier-0 skills, CLAUDE.md,
   docs, user edits to retained files) are untouched.
2. **`copy_machinery` resolves tiers from the target manifest.** It
   reads `installed_tiers` from the target's existing `scaffold.json`
   (replacing slice 038-02's interim default), and the tier-bump
   affordance updates that manifest's `installed_tiers` + derived
   `installed_skills`. The manifest ↔ on-disk invariant (slice 038-02
   AC #3) holds after upgrade.
3. **No new guard path.** The upgrade reuses `copy-machinery`'s
   existing non-greenfield entry; `AlreadyScaffoldedError` is neither
   re-implemented nor newly tripped on the upgrade flow.
4. **Idempotent.** Running the upgrade when the project is already at
   the target tier is a safe no-op (no duplicate dirs, no error,
   manifest unchanged).

**DoD:**
- [ ] All ACs pass; full suite green.
- [ ] Tests cover: Tier-0 → Tier-0+1 upgrade; idempotent re-run;
      user-edited skill file preserved; guard still refuses an
      unintentional fresh re-scaffold.
- [ ] Reviewed by `reviewer` subagent.
- [ ] Implementation review passed.
- [ ] Arch-review pass (new entry point / re-run-guard contract change —
      `arch_review: true`).
- [ ] Deviation log produced (including the vehicle decision).
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated: if this slice promotes /
      supersedes the deferred `update` skill (016-04), reconcile that
      entry.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated.
- [ ] If this is the spec's last non-deferred slice, compress the spec's
      Active-specs entry per spec 025-01.

**Anti-horizontal-phasing check:** After this slice, a growing project
gains its Tier-1 machinery with a single command and an updated
manifest — observable, end-to-end value (the floor stops being a
one-way door).

### Deviation log (after reconciliation)

_TODO._
