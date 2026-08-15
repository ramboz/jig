---
status: RECONCILED
dependencies: [111-01]
last_verified: 2026-08-15
kind: feature
claimed_by: claude/spec-first-class-blockers
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon). -->
<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation. -->

## Slice 111-02 — spec-lint-validation

**Goal:** `spec_lint.py` soft-warns when a slice carries a `blocked_by:` on a
**non-actionable** status (`DRAFT` / `DONE` / `DEFERRED` / `ABANDONED`), where the
annotation is almost certainly a misfiled dependency or deferral — catching the
stale/over-count failure mode ADR-0057 names, without ever hard-blocking.

**Decision:** [ADR-0057](../../decisions/adr-0057-first-class-blockers-are-annotations.md)
— the mitigation for annotation staleness is a `spec_lint` nudge, not a gate.

**DoR:**
- ✅ 111-01 DONE — the `blocked_by:` convention + the actionable-state set exist.
- ✅ `spec_lint.py` lives at `scripts/spec_lint.py` and **is shipped verbatim**
  into both host packages (slice 075-01 / bug 025 — listed in
  `install_contract.RELEASE_INCLUDE_SCRIPT_FILES` + `CODEX_INCLUDE_SCRIPT_FILES`,
  copied by `build_codex_plugin._copy_runtime_scripts`). So editing it **does**
  require regenerating `hosts/claude/scripts/spec_lint.py` +
  `hosts/codex/plugins/jig/scripts/spec_lint.py` via `build_host_packages.py`, or
  the CI host-drift gate fails. (Corrected during reconciliation — an earlier
  draft wrongly claimed it was not shipped.)
- ✅ The actionable-state set is grounded (`_CLAIM_WORKING_STATUSES` +
  `READY_FOR_IMPLEMENTATION`, `workflow.py:4204`).

**Assumptions:** None.

**Acceptance Criteria:**

1. **Warns on a misfiled `blocked_by:`.** Given a slice whose status is
   `DRAFT` / `DONE` / `DEFERRED` / `ABANDONED` and which has a non-empty
   `blocked_by:`, `spec_lint.py` emits one warning naming the spec + slice and
   stating that `blocked_by:` belongs on an actionable slice (and that this is
   likely a `dependencies:` or `DEFERRED` misfile).

2. **Silent on the valid case.** A `blocked_by:` on an actionable slice
   (`READY_FOR_IMPLEMENTATION` / `READY_FOR_REVIEW` / `IN_PROGRESS` / `REVIEWED` /
   `RECONCILED`) produces **no** warning.

3. **Silent when absent/empty.** A slice with no `blocked_by:`, or a
   whitespace-only value, produces no warning.

4. **Soft, never blocking.** The warning uses `spec_lint.py`'s existing
   **warning** severity, not error — it must not, on its own, flip the script's
   exit code to failure. (Grounded against `spec_lint.py`'s current warn-vs-error
   model during implementation.)

**Edge cases to cover explicitly:**
- `blocked_by:` on `DRAFT` → warns.
- `blocked_by:` on `IN_PROGRESS` → silent.
- `blocked_by:` on `DEFERRED` (which also has a `**Resolution trigger:**`) → warns
  (the blocker annotation is the misfile, independent of the trigger).
- Whitespace-only `blocked_by:` on any status → silent.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [x] Test coverage exercises each AC + edge case; each new test shown to fail
      when the rule is removed.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed.
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred.

**Non-goals:** validating the `**Blocked:**` body line's presence/format
(optional per ADR-0057); a typed-vocabulary check (deferred); making the warning
a hard error (ADR-0057: nudge, not gate).

### Deviation log

Original ACs preserved above. Notes:

- **`_extract_kind` generalized (ADR-0002 third-caller).** With `kind`, `status`,
  and `blocked_by` all reading a frontmatter scalar, `_extract_kind`'s body was
  lifted into `_extract_slice_frontmatter_scalar(section, field)` and `_extract_kind`
  kept as a thin wrapper — behaviour-preserving (the 74-test spec_lint suite stays
  green). This is the extract-on-third-caller trigger firing.
- **`_BLOCKER_ACTIONABLE_STATUSES` is an inline mirror of workflow.py's set.**
  spec_lint is a standalone repo CI script that deliberately imports only
  `_common/parsing`, not `workflow.py`, so the actionable-state set is duplicated
  as a `frozenset` literal with an explicit drift-warning comment (ADR-0002
  two-caller inline mirror). **Manual-sync contract:** if workflow.py's
  `_BLOCKER_ACTIONABLE_STATUSES` changes, update spec_lint's copy to match. Shape
  differs (frozenset vs. workflow's tuple concatenation) but content is identical.
- **AC1 attribution is contextual, and that is correct.** The warning string
  names neither spec nor slice; attribution comes from `render_report`'s
  `## Spec lint: <path>` + `### Slice <label>` headers — identical to how every
  other spec_lint warning (contradictions, `kind`/spike shape) is attributed. The
  `label` param on `check_blocked_annotation` is accepted for signature parallelism
  with `check_slice` / `check_kind_and_body_shape` (both also ignore it).
- **Craft/compliance nit addressed.** Strengthened `test_blocked_by_on_draft_warns`
  to assert the warning is *actionable* (mentions "actionable" + "ADR-0057"), not
  just that it contains the `blocked_by` substring.
- **Reconciliation review caught a real host-package error (NEEDS-CHANGES → fixed).**
  An earlier draft of this slice (DoR + sweep) claimed `spec_lint.py` is not
  shipped in the plugin tree, so it marked host packages `no-op`. That was
  **wrong**: `spec_lint.py` ships verbatim into both host packages (slice 075-01 /
  bug 025), and the committed copies were stale — the CI host-drift gate would
  have failed. Regenerated the host packages (`--check` now clean) and corrected
  the DoR + sweep. (The stale premise came from an out-of-date assumption that
  the reconciliation gate is designed to catch.)

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `scripts/spec_lint.py` | `updated` | `_extract_slice_frontmatter_scalar` generalization + `_extract_kind` wrapper; `_BLOCKER_ACTIONABLE_STATUSES` inline mirror; `check_blocked_annotation`; wired into `lint()`. |
| `scripts/test_spec_lint.py` | `updated` | New `BlockedAnnotationValidationTests` (11 tests: warn/silent per status, whitespace, soft-exit-0, strict-exit-1, actionable-message). |
| `hosts/claude/scripts/spec_lint.py` + `hosts/codex/plugins/jig/scripts/spec_lint.py` | `updated` | **Correction (reconciliation review NEEDS-CHANGES):** `spec_lint.py` IS shipped verbatim into both host packages (slice 075-01 / bug 025). An earlier sweep draft wrongly marked this `no-op`; regenerated via `build_host_packages.py`, `--check` now clean. |
| `docs/specs/README.md` | `deferred` | Regenerated at spec close-out (this slice closes spec 111). |
| `docs/architecture.md` / `docs/conventions.md` | `no-op` | No module-boundary or authoring-rule change (the rule is a lint nudge; the convention lives in ADR-0057 + the spec). |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / templates | `deferred` | Spec 111 closes with this slice — handled in the close-out below (glossary entry). |
| `docs/refinement-todo.md` | `no-op` | No new deferral (the NamedTuple one was logged under 111-01). |
| `docs/memory/**` + glossary | `deferred` | The **first-class blocker** term + the "annotation-not-state" lesson — folded into `/jig:memory-sync` at close-out. |
| `docs/decisions/` (ADR-0057) | `no-op` | Already Accepted + indexed. |
| `docs/inbox.md` | `no-op` | Nothing resolved or added. |

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Glossary/primer: **first-class blocker** entry (if this closes the spec).
