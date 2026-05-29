---
status: DONE
dependencies: [038-02]
last_verified: 2026-05-29
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
- [x] All ACs pass; full suite green. 1442 tests, OK (3 skipped).
- [x] Tests cover: Tier-0 → Tier-0+1 upgrade; idempotent re-run;
      user-edited skill file preserved; precondition (no scaffold.json) +
      unknown-tier rejected. (Fresh-re-scaffold refusal is unchanged
      `AlreadyScaffoldedError` behavior, covered by existing scaffold
      tests — not re-tested here since this slice doesn't touch it.)
- [x] Reviewed by `reviewer` subagent.
- [x] Implementation review passed.
- [x] Arch-review pass (new entry point / re-run-guard contract change —
      `arch_review: true`).
- [x] Deviation log produced (including the vehicle decision).
- [x] Reconciliation review passed.
- [x] 016-04 reconciled: no `docs/refinement-todo.md` entry exists for it
      (it is tracked on the status board's Deferred table); its
      resolution-trigger note is narrowed there to record that
      tier-upgrade is now handled by `copy-machinery --add-tier`.

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated.
- [x] Spec's last non-deferred slice — spec 038 closed. CLAUDE.md
      "Active specs" already reads "(none)" (nothing to compress);
      per-slice invariants live in the status-board Notes column; the
      migrate Skills-table row updated to note `--add-tier`.

**Anti-horizontal-phasing check:** After this slice, a growing project
gains its Tier-1 machinery with a single command and an updated
manifest — observable, end-to-end value (the floor stops being a
one-way door).

### Deviation log (after reconciliation)

1. **Built on `copy-machinery`, no new entry point** (as ADR-0010 /
   the slice intended). Added `migrate.py copy-machinery --add-tier TIER`
   (repeatable) + two manifest helpers in `scaffold.py`
   (`read_installed_tiers`, `bump_installed_tiers`). 8 new tests
   (`TierUpgradeTests`). Full suite 1442 green (3 skipped).
2. **Vehicle decision: a `--add-tier` flag, not the manual
   "edit-scaffold.json-then-rerun" flow.** The flag is discoverable,
   validates the tier name, and bumps `installed_tiers` +
   `installed_skills` atomically — no chance of a hand-edited manifest
   drifting from disk. (Both options were left open by ADR-0010; chose
   the flag.)
3. **Additive = copies only the *delta* tier.** An upgrade copies just
   the newly-added tier's skills; existing tiers (and local edits to
   their files) are untouched — pinned by
   `test_upgrade_preserves_existing_tier0_and_user_files`. Plain
   `copy-machinery` (no `--add-tier`) refreshes the full manifest tier
   set (reads `installed_tiers`; `None`/no-manifest → copy-all, the
   spec-021 default). This makes the plain migrate path tier-aware too,
   closing 038-02's interim.
4. **Resolved 038-02's two reviewer follow-ups.** (a) Extracted the
   inline skill→tier reverse map to a module-level `_SKILL_TO_TIER`
   constant (arch-review nit) — single source of truth, no rebuild. (b)
   `scaffold.copy_machinery(installed_tiers=None)` = copy-all is now an
   intentional, permanent contract (copy-all when tiers are unknown,
   used by the no-manifest migrate case), **not** a time-boxed shim —
   resolving the principle-#6 watch.
5. **016-04 (`update` skill) reconcile — stays DEFERRED, scope
   narrowed.** `--add-tier` covers the *tier-upgrade* use case ADR-0010
   committed to, additively and without clobbering existing-tier edits.
   It does **not** supersede 016-04's core trigger ("I scaffolded jig N
   versions ago and want to update cleanly without overwriting my
   edits") — a plain `copy-machinery` refresh still overwrites jig-*
   files for the tiers it copies. 016-04's remaining justification is
   that version-refresh-without-clobbering case; its status-board
   resolution-trigger note is updated to record that tier-upgrade is now
   handled here.
6. **AC #3 (no new guard) honored.** The upgrade reuses copy-machinery's
   existing non-greenfield entry; `AlreadyScaffoldedError` is untouched.
   The one new precondition — `--add-tier` requires an existing
   `scaffold.json` (`plan_installed_tiers` raises `FileNotFoundError` →
   `MigrateError`) — is a flag-specific check, not that guard, and is
   tested (`test_add_tier_requires_scaffold_json`).
7. **Reviewer-driven hardening (both passes PASS, no blockers).** Arch
   review flagged a write-ordering window: the original
   `bump_installed_tiers` rewrote the manifest *before* the copy, so a
   copy failure (e.g. `UnmanagedHooksError`) would leave the manifest
   claiming a tier whose skills never landed — the exact invariant
   inversion this spec exists to prevent. Split into compute-only
   `plan_installed_tiers` + post-copy `write_installed_tiers`, and
   reordered the migrate flow to **plan → copy delta → commit manifest**.
   A copy refusal now leaves `scaffold.json` untouched. Also (compliance
   review) refreshed the two `_copy_skills_and_agents` / `copy_machinery`
   docstrings that still read "interim … until slice 038-04" (now a
   standing "tiers unknown → copy-all" contract), and actually applied
   the 016-04 status-board scope-narrowing note that this log referenced.
