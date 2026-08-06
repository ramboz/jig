---
slice: 106-01 — scaffold the protected plane and the identity-separation gate
pass: arch
verdict: pass
reviewer: jig:reviewer
reviewed_at: 2026-08-06T05:40:59Z
prompt_source: review.py arch-review docs/specs/106-autonomy-governance-plane/spec.md 106-01 <deliverables>
---

Architecture review of slice 106-01 — VERDICT: pass (re-review after fixes). Slice declared
arch_review: true (scaffold output + hook contracts).

The first arch pass returned needs-changes with three [blocker]s: (1) protected-path nudge
duplicated across two co-firing hooks; (2) two concatenated JSON objects per invocation;
(3) a docstring asserted a matcher-sync test that did not exist (3 matcher copies unguarded).
All three fixed and re-verified: boundary-warn is the single owner emitting one merged object,
entry-gate reverted, and GlobMatcherParityTests now behaviorally pins the hook's inline matcher
against governance.path_matches_glob.

Architecture assessed clean: module boundaries preserved (hooks import only _common/lib, never
the governance skill module); PROTECTED_PATHS is the single source of truth mirrored into
scaffold.json via _scaffold_manifest; _write_governance_plane follows the _write_gitignore
dual-wiring precedent; the servo cross-repo contract (JSON `ready` authoritative; exit 0/3/2)
is documented and pinned by CliTests.

Nits addressed: opt-out coupling fixed (independent JIG_BOUNDARY_CHECK / JIG_PROTECTED_PATHS).
Deferred to refinement-todo (recorded in the deviation log): (a) copy_machinery writes the
governance files but not scaffold.json.protected_paths, so a migrate-upgraded project reads []
until re-scaffold; (b) the CI-workflow-embedded (third) matcher copy is not parity-pinned.
