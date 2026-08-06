---
status: DONE
dependencies: [adr-0051]
last_verified: 2026-08-06
arch_review: true  # governance plane touches scaffold output + hook contracts.
frame_review: true  # slice carries env-specific identity-signal assumptions.
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 106-01 — scaffold the protected plane and the identity-separation gate

**Goal:** A freshly scaffolded repo ships with the scaffoldable half of the
out-of-band protection of its governing artifacts (CODEOWNERS + protected-path CI
+ a `<docs>/governance.md` documenting the branch-protection arming step that
makes them enforce + a `protected_paths` config the soft hooks read), and jig can
determine whether the repo satisfies the identity/capability-separation
precondition for autonomy.

**DoR:**
- ✅ [ADR-0051](../../decisions/adr-0051-autonomy-governance-plane.md) is the governing record.
- ✅ Confirmed current `scaffold-init` output surface + `scaffold.json` schema
  (probed 2026-08-06): `scaffold()` writes docs/primer/`.gitignore` floor/
  `permissions.deny`/`settings.json`, then `scaffold.json` LAST as the completion
  sentinel; the manifest is assembled by `_scaffold_manifest` (computed keys
  injected there, e.g. `installed_tiers`); new scaffold-output writers slot in
  beside `_write_permissions_deny_floor` / `_write_gitignore_managed_blocks` on
  BOTH the machinery and plugin-only paths. Neither `entry-gate` nor
  `boundary-warn` currently reads a protected-path list — they fire on
  `PostToolUse Edit|Write|MultiEdit`; `scaffold.json` is the runtime source of
  truth a new shared reader consumes.
- ✅ Pinned the identity signal (probed 2026-08-06): jig **cannot observe GitHub
  merge permissions in-process** (no local "who can merge this branch"). The
  check is deterministic **over supplied/attested inputs** — run-identity
  (`JIG_RUN_IDENTITY` / `git config user.email`) and the merge-capability of that
  identity (`JIG_MERGE_IDENTITY` and/or an attested `merge_capable` flag). It
  keys on **capability, not identity name**, and reports **not-ready when the
  capability input is unavailable** (fail-safe). servo 023 derives the capability
  input from the GitHub API and feeds it in.

**Acceptance Criteria:**

1. **CODEOWNERS scaffolded.** `scaffold-init` writes a `CODEOWNERS` naming the
   protected paths (`docs/conventions.md`, `docs/decisions/**`, `oracle.sh`,
   frozen `.servo/**/config.json`, and the governance plane's own files —
   `.github/workflows/**` and `CODEOWNERS` itself, so the self-reference holds by
   construction) to an owner distinct from the autonomous agent. Observable: the
   file exists with those entries after a scaffold into a fixture repo.
2. **Protected-path CI scaffolded.** A `.github/workflows/` job is written that
   **fails a PR whose diff touches a protected path without owner approval**.
   Observable: on a fixture PR diff touching a protected path, the job's logic
   evaluates to failure; on a diff that does not, it passes. (The workflow file is
   itself a protected path — the self-reference must hold.) **The scaffolded
   material must state plainly that this CI job is inert until branch protection
   is armed** (require-this-status-check + require-Code-Owner-review +
   forbid-bypass) — the job is only a blocking gate once those server-side
   settings, which scaffold-init cannot commit, are on. Observable: the scaffolded
   governance material carries the branch-protection arming checklist and the
   "inert until armed" statement.
3. **`protected_paths` in `scaffold.json`.** The key is written and is the single
   source of truth; `entry-gate` / `boundary-warn` read it to nudge when an edit
   lands in-boundary. Observable: a hook fixture reads the list and nudges on an
   in-boundary edit; CI (AC 2) enforces out-of-boundary.
4. **Identity/capability-separation precondition.** A deterministic check
   (deterministic **over its supplied/attested inputs** — jig does not observe
   GitHub merge permissions in-process) reports whether the principal that would
   run the loop can merge its own output / edit branch protection. The safety fact
   is **merge capability, not identity name**:
   - single identity (run-identity == merge-identity, e.g. a personal PAT) →
     **not** autonomy-ready (says why);
   - a **distinct** run-identity that is nonetheless attested `merge_capable`
     (over-privileged bot) → **not** autonomy-ready (distinct name is necessary
     but not sufficient);
   - a distinct, least-privilege (not merge-capable) run-identity →
     autonomy-ready w.r.t. this precondition;
   - the capability input **unavailable** → **not** autonomy-ready (fail-safe;
     jig never asserts an unverified "ready").

   Observable: the check returns `ready` only for the distinct-and-not-capable
   fixture, and `not-ready` (with a distinct reason) for each of the single-
   identity, distinct-but-capable, and unknown-capability fixtures; it exposes a
   machine-readable verdict (JSON + exit code) that the servo readiness gate
   (servo 023) subprocess-invokes to return `unsafe_for_autonomy`.
5. **Governance-proposal routing + arming step are documented as scaffolded
   policy.** The scaffolded material states that (a) a change to a protected
   artifact must open an ADR/spec (surface-and-stop, spec 102), never a self-edit,
   and (b) the CODEOWNERS + CI files are inert until the operator arms branch
   protection (the checklist from AC2). Observable: the scaffolded
   CODEOWNERS/CI/README material carries both rules.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). — 4172 tests OK, pyright clean.
- [x] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [x] Each new test has been shown to fail when its feature is removed. — incl. the
      behavioral `GlobMatcherParityTests`.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed (+ arch-review — this slice is arch-shaped). —
      frame-critique (ADR + slice), compliance, craft, arch all `pass` (craft + arch
      after two hook-wiring blockers were fixed).
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred. — two items
      (copy_machinery backfill; CI-YAML matcher parity).

### Close-out (post-DONE)

- [x] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [x] Primer hygiene per spec 025-01: this slice closes the spec — `CLAUDE.md`
      Active-specs line compressed (106 → built) and a **Governance plane** key-term
      added; `docs/architecture.md` records the new scaffold-output + hook-read surfaces.

**Anti-horizontal-phasing check:** After this slice lands, running `scaffold-init`
produces a repo whose governing artifacts carry scaffolded CODEOWNERS + protected-
path CI (with a documented arming checklist that turns them from advice into an
enforced gate) and whose autonomy-readiness w.r.t. identity/capability separation
is a concrete yes/no — end-to-end value for anyone setting up an unattended repo.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**Frame reframe before build (frame-critique, 2026-08-06).** The pre-implementation
frame-critique pass (on both ADR-0051 and this slice) returned `needs-changes`
twice and forced two honest reframes applied to the ADR + spec + this slice
*before* any code:
1. **Inert-until-armed.** The original ADR overclaimed CODEOWNERS + CI as "real
   enforcement." They are inert until branch protection is armed (a server-side
   setting scaffold-init cannot commit). AC2/AC5 now require the scaffolded
   material to state this and carry the arming checklist; the CI job only *flags*
   protected-path touches (fails the check to signal "owner review required") —
   actual approval enforcement is branch protection.
2. **Capability, not name.** AC4 originally tested identity-*name* distinctness.
   Reframed to key on merge *capability* over supplied/attested inputs (jig does
   not observe GitHub merge permissions in-process), with distinct-name as
   necessary-but-not-sufficient and fail-safe (not-ready) when the capability
   signal is unavailable. The protected-paths set now includes `.github/workflows/**`
   and `CODEOWNERS` itself so the self-reference the ADR Kill criteria demand holds
   by construction.

**Implementation deviations:**
- **Single-hook ownership of the protected-path nudge.** AC3 names "`entry-gate` /
  `boundary-warn`" as the readers. Implemented in **`jig-boundary-change-warn.sh`
  only** (the governance-nudge hook), NOT both: both hooks fire on the same
  `PostToolUse Edit|Write|MultiEdit` matcher, so wiring both produced a duplicate
  nudge + double attribution and could emit two JSON objects in one invocation
  (single-object stdout contract violation) — two `[blocker]`s the craft + arch
  passes caught. boundary-warn now collects all applicable nudges and emits
  exactly ONE merged JSON object; entry-gate is unchanged. AC3's observable ("a
  hook reads the list and nudges on an in-boundary edit") is satisfied. The two
  nudges keep **independent opt-outs** (`JIG_PROTECTED_PATHS` for governance,
  `JIG_BOUNDARY_CHECK` for the contract nudge).
- **Deterministic-over-inputs identity check.** `governance.check_identity_separation`
  is deterministic over supplied inputs (run-identity + attested `merge_capable`);
  a distinct-name-without-attestation returns not-ready (a name mismatch does not
  prove non-capability). CLI `identity-check` exits `0` ready / `3` not-ready /
  `2` usage; stdout JSON `ready` is authoritative. servo 023 derives and feeds the
  capability input.
- **scaffold.py import shim.** `import governance` is preceded by a self-adding
  `sys.path` line so the `importlib` loaders in `migrate.py` / `build_codex_plugin.py`
  resolve the sibling module across all load shapes (script / namespace / importlib).
- **`test_scaffold.py::test_draft_markers` exemption.** The new scaffolded
  `governance.md` is authoritative policy, not a wizard-generated draft — exempted
  from the draft-marker enumeration (same rationale as the seed-dir exemption),
  registering the new non-draft scaffold output without weakening the assertion.
- **Matcher duplication (intentional).** The `**`-aware glob matcher exists in
  `governance.path_matches_glob` (source of truth), inline in
  `protected_paths.py` (hooks import only `_common`, never a skill module), and
  hand-embedded in the CI-workflow YAML (must be self-contained for the Actions
  runner). `test_protected_paths.GlobMatcherParityTests` behaviorally pins the
  hook copy against the source of truth.

**Deferred (see `docs/refinement-todo.md`):**
- **`copy_machinery` does not write `scaffold.json.protected_paths`.** The key is
  written by `_scaffold_manifest` at `scaffold()` completion only; a pre-106
  project upgraded via `migrate copy-machinery` gets CODEOWNERS + CI + `governance.md`
  but the soft hooks read `[]` until a re-scaffold. CI still enforces
  out-of-boundary. Backfill deferred.
- **CI-workflow-embedded (third) glob-matcher copy is not parity-pinned.** Only the
  hook copy is pinned to the source of truth; the YAML-embedded copy can drift.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`; 106-01 currently at REVIEWED, regenerated again at close when it transitions DONE (spec 106 then rolls up DONE). |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0051 flipped Proposed → Accepted (2026-08-06) after its frame-critique cleared; index regenerated. |
| `docs/decisions/adr-0051-*.md` + `spec.md` | `updated` | Reframed (inert-until-armed; capability-not-name; self-reference) at frame-critique, before build. |
| `docs/architecture.md` | `updated` | New scaffold-output surface (CODEOWNERS + `.github/workflows/jig-governance.yml` + `<docs>/governance.md`), new `governance.py` module, and the `protected_paths` hook-read contract recorded. |
| Primer: `CLAUDE.md` | `updated` | Spec 106 compressed out of the "recorded, not built" Active-specs line (spec 025-01 close-out); Governance-plane term indexed. |
| `docs/refinement-todo.md` | `updated` | Two deferred items recorded (copy_machinery backfill; CI-YAML matcher parity). |
| `docs/memory/glossary.md` | `updated` | "Autonomy governance plane" term added via memory-sync. |
| `scaffold.json.template` | `no-op` | `protected_paths` is a computed key injected by `_scaffold_manifest`, not a template field (mirrors `installed_tiers`). |
