---
status: DONE
dependencies: []
last_verified: 2026-06-02
---

## Slice 041-03 — deferral-verification-doc

**Goal:** A short `docs/skill-routing-verification.md` walks a reader through
the manual reproduction recipe for confirming that an installed user-skill
takes precedence over jig's baseline — distinguishing the two distinct
delegation paths (interactive skill-router vs. the spec-workflow craft/arch
pass) and how each is verified.

> **Record note (closed retroactively).** This slice shipped *ahead of* its
> formal lifecycle transitions (committed in `734e424`) and was **not**
> independently reviewed. It is recorded here as an honest closed record per
> the spec 041 reconciliation note and ADR-0010. See the deviation log. —
> 2026-06-02

**DoR:**
- ✅ The routing trace exists (slice 041-01) so Path A has something concrete
  to read.

**Acceptance Criteria:**

1. **Two-path framing.** `docs/skill-routing-verification.md` distinguishes
   Path A (interactive: Claude's skill router picks by description) from Path B
   (the spec-workflow craft/arch pass, which spawns a read-only `reviewer`
   subagent with no `Skill` tool — the router is unreachable there).
2. **Path A recipe.** Gives a deterministic per-run verification: read
   `.claude/skill-usage.jsonl`, filter `event == "skill_invoked"`, and read
   off whether `pr-review` (richer) or `jig:pr-review` (baseline) fired.
3. **Path B recipe.** Documents the file-read dispatch (`detect_richer_skill()`
   in `review.py`, shipped under the separate spec 053 craft-pass work) and how
   to inspect the built reviewer prompt to confirm which skill it points at.
4. **Honest limits.** Notes the hook sees only the *main agent's* Skill calls;
   typed `/slash` commands expand via `UserPromptExpansion` (not `PreToolUse`),
   and a subagent's own Skill calls are not guaranteed to surface.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions).
- [~] Implementer test coverage — **N/A**: prose deliverable. Its on-disk
      presence and link health are covered by the repo's docs checks
      (`scripts/test_docs_reading_path.py`).
- [ ] Reviewed by `reviewer` subagent — **not performed** (shipped ahead of
      formal slicing; see deviation log §1).
- [ ] Implementation review passed — **not performed** (see §1).
- [x] Deviation log produced under this slice heading.
- [ ] Reconciliation review passed — **not performed** (see §1).
- [x] `docs/refinement-todo.md` updated — handled at spec close (slice 041-02).

**Anti-horizontal-phasing check:** End-to-end value: a reader who wants to
confirm "did my richer `pr-review` win over jig's baseline?" has a concrete,
deterministic recipe — and knows which of the two delegation paths they are on
(the recipe differs per path).

### Deviation log (after reconciliation)

The original drafted plan (spec 041 Goal 3) is preserved above. Notes:

**§1 — Not independently reviewed.** As with slice 041-01, this already-shipped
docs deliverable is recorded as a closed record rather than retro-fitted with
fabricated review evidence (spec 041 close-out decision). Acceptance rests on
the doc's presence + the repo's docs-link checks.

**§2 — Path B documents a *separately-shipped* fix.** The doc's Path B section
describes `review.py`'s file-read dispatch (`detect_richer_skill()`), which
belongs to the spec 053 craft-pass work, NOT spec 041. Spec 041's
"No filesystem detection in `review.py`" non-goal was scoped to
detection-*for-observability* and still holds — the verification doc merely
*describes* the craft-pass dispatch so a reader understands both delegation
paths in one place.
