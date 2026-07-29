---
status: RECONCILED
dependencies: [adr-0040]
last_verified: 2026-07-28
frame_review: true
kind: feature
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 096-01 — config-precedence

**Goal:** A project can name its richer review skill per category in
`scaffold.json` (`review.<category>_skill`), and the **three** extensible review
passes (`pr-review`, `arch-review`, `code-health`) read-and-apply that skill's
SKILL.md instead of jig's baseline — closing the reported bug deterministically,
on both hosts, with no enumeration and no marker.

**Why this slice is first:** it is the only resolution path ADR-0040 can
*guarantee*, and the destination every kill criterion falls back to. Shipping it
before the zero-config layer means a later abandonment degrades to a working
feature rather than a half-built one (ADR-0040 D1, carried from ADR-0039 §6).

**Scope note (ADR-0040 D1):** the extensible set is **three** categories, not
five. `design_review` is in the never-defer set (its builder refuses richer-skill
detection; ADR-0022 attest-only). `security-review` + `bug-fix` config-honoring is
a named follow-up (ADR-0040 OQ1) — no key ships for either here.

**DoR:**
- ✅ [ADR-0040](../../decisions/adr-0040-richer-skill-discovery-explicit-candidate-channel.md) Accepted.
- ✅ `skills/_common/project_layout.py` exists as the precedent for reading a
  typed, validated block out of `scaffold.json` (spec 084 / ADR-0033).
- ✅ The three extensible passes exist in `review.py`: `build_pr_review_prompt`,
  `build_arch_review_prompt`, `build_code_health_review_prompt`. (Verified:
  there is no security builder; `build_design_review_prompt` exists but is
  never-defer.)

**Acceptance Criteria:**

1. **A `review` block in `scaffold.json` resolves a skill by name or path.**
   A helper (sibling of `project_layout.docs_root`) reads
   `review.<category>_skill` for each of the **three** categories
   (`pr_review_skill`, `arch_review_skill`, `code_health_skill`). A bare name
   resolves against the known scopes; a path is used as-is. Absent block / absent
   key / empty string → `None` (jig's baseline), no error. No key is read for
   `security` or `design` (out of scope, ADR-0040 D1). **Scope seam:** this slice
   resolves config names against user scope + explicit paths (spec 053 confirmed
   the reviewer can read user scope). The *general* multi-scope precedence
   resolver + the reviewer-read-at-admin/plugin-scope probe are **096-02's job**
   (AC1/AC6 there) — 096-01 does not ship admin/plugin-scope name resolution
   ahead of that probe, so no unreadable-path fallback window opens here.
2. **Malformed config refuses loudly; runtime absence falls back quietly**
   (ADR-0040 D1, fixing an ADR-0039-era over-strict AC). A non-object `review`
   or a non-string `<category>_skill` raises a typed error naming the offending
   key and value — an *authoring* mistake. But a **well-formed name that
   resolves to no SKILL.md on this machine** falls back to jig's baseline and is
   *recorded* (096-05), NOT errored: `scaffold.json` is committed and
   team-shared, so a teammate or CI runner lacking a user-scope install must not
   have every review pass hard-fail. This preserves `review.py`'s documented
   "never block the craft/arch pass" posture (`review.py:571`) and ADR-0039 §3
   rule 4 (unresolvable → baseline, not error).
3. **The three passes honor it.** With `pr_review_skill` configured, the craft
   pass prompt names that concrete path and instructs read-and-apply
   (superseding the inlined baseline buckets); likewise arch and code-health with
   their own keys. Each still normalizes findings into the shared
   `VERDICT / REASONING / SPECIFIC ISSUES / RECONCILIATION NOTES` envelope.
4. **Config wins over the legacy exact-name lookup.** When both a configured
   skill and a `~/.claude/skills/<category>/` install are present, the configured
   one is used. (`detect_richer_skill`'s legacy behavior is retained as a
   fallback in this slice and is not yet removed — 096-03 supersedes it via the
   full chain.)
5. **Host-portable.** Resolution reads only the filesystem + frontmatter; no
   router, no `Skill` tool, no Claude-only path. Codex-rendered SKILL.md prose
   describes the same mechanism with Codex scopes
   (`$HOME/.agents/skills`, `.agents/skills`, `/etc/codex/skills`).
6. **The configured skill is recorded, with a `config` substrate.**
   `record-review` writes which skill was applied (or `none`) plus
   `substrate: config` when a config key is present (ADR-0040 D3 vocabulary).
   This is the minimum viable half of the auditability requirement; the tiered
   candidate set and the anomaly land in 096-05.
7. **The lifecycle-dependence caveat is documented, not discovered by a user**
   (ADR-0040 D1 honest cost). A configured `review.<category>_skill` is honored
   in the orchestrated review pass but silently ignored on the router-only
   interactive skill invocation (`/jig:pr-review`, `/jig:arch-review`,
   `/jig:code-health`) and in `bug-fix`'s craft pass. This slice adds a prose
   note to all four SKILL.mds (`bug-fix`, `pr-review`, `arch-review`,
   `code-health`) stating that config honoring is currently orchestrated-pass
   only, pointing at OQ1.

**Edge cases to cover explicitly:**
- `scaffold.json` absent entirely (jig's own repo) → `None`, no error. **Dogfood
  caveat:** because jig's own repo has no `scaffold.json`, 096-01 ships zero
  behavior change here — it is exercisable only in a scaffolded project. State
  this in the slice, don't leave it to be inferred.
- Well-formed configured name not installed on this machine → baseline +
  recorded, NOT an error (AC2).
- Configured `review` block *structurally* malformed (non-object / non-string
  value) → typed error (AC2).
- Configured skill is jig's own baseline path → allowed (explicit user intent
  overrides the discovery filter; the exclusion is a *discovery* filter, not a
  config filter).
- `docs_root = "."` projects — config discovery is sentinel-anchored the same way
  `project_layout` is, not docs-root-relative.

**DoD:**
- [x] All ACs pass; full test suite green (no regressions). 3593 tests OK; ruff
      clean; host-package drift in sync.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [x] Hermetic tests — config resolution honors `$HOME` / `--project-dir`, never
      reads the developer's real `~/.claude`.
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed. (compliance + craft both `pass`.)
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated if any decisions were deferred during
      implementation. (No new deferrals — the seams below are already tracked by
      096-02 / 096-05 / ADR-0040 OQ1.)

### Deviation log (after reconciliation)

Original ACs above are preserved. Implementation deviations + review-driven
changes:

- **`applied_skill` records the portable configured identifier, not the resolved
  absolute path.** Both review passes flagged that stamping a machine-specific
  `$HOME` path into a committed evidence artifact (ADR-0014 audit trail) is
  non-portable. Reconciliation added `review_config.configured_value` (the raw
  bare-name/path as written in scaffold.json) and switched `_config_substrate_lines`
  to record that; the resolved absolute path is used only in-memory for the
  read-and-apply prompt. Regression tests assert `applied_skill` carries no
  `$HOME` / no `/SKILL.md` for a bare-name config. (An *explicit* path a user
  writes in scaffold.json is recorded verbatim — that is the user's own
  committed value, not one jig injected; the portability guarantee is about not
  synthesizing a machine-specific path from a portable bare name.)
- **AC6 narrowed from literal "when a config key is present" to "when the
  configured skill also resolves on this machine."** A config key that is present
  but names an uninstalled skill produces NO `substrate` stamp here — the honest
  "record what was applied" reading. The config-declared-but-not-installed audit
  case is 096-05's to record (it needs the sidecar/anomaly machinery). Both
  reviewers accepted this as consistent with the "minimum viable half" framing.
- **`_config_substrate_lines` swallows `ReviewConfigError` (records nothing)
  whereas `_resolve_richer_skill` propagates it.** Deliberate: a structural
  config mistake already surfaces loudly at prompt-build time (when the pass is
  constructed); deriving the substrate at record time must never be the thing
  that fails a recording.
- **Stale builder docstrings corrected.** The `build_pr_review_prompt` /
  `build_arch_review_prompt` docstrings + the module-header comment described
  dispatch as `detect_richer_skill`-only; updated to the config-first
  `_resolve_richer_skill` precedence (the code-health docstring was already
  updated in the initial implementation). A craft-pass nit.
- **`code_health` gained a richer-dispatch path (net-new).** Before this slice
  `build_code_health_review_prompt` had no richer dispatch at all; ADR-0040 D1
  makes `code_health` an extensible category, so config-first dispatch + a
  read-and-apply routing paragraph were added and its "NOT wired here" docstring
  corrected.

**Documented scope seams (tracked, not fixed here):**

- **Codex bare-name resolution.** A bare `review.<category>_skill` name resolves
  only against `~/.claude/skills` in this slice (a mild AC5 tension); Codex
  bare-name + full multi-scope resolution arrive with **096-02**. Explicit paths
  are host-portable today.
- **Interactive / bug-fix config honoring.** A configured key is honored only in
  the orchestrated review pass, not on `/jig:<skill>` interactive invocation nor
  in `bug-fix`'s craft pass (AC7 prose notes state this) — **ADR-0040 OQ1**.

### Reconciliation sweep

- **Deviation log** — updated (above).
- **`review.py` builder docstrings + module header** — updated (config-first
  precedence now documented on all three builders).
- **Host packages** (`hosts/claude`, `hosts/codex`) — updated; drift `--check`
  green (review.py + review_config.py + four SKILL.md notes propagated;
  `test_review_config.py` correctly excluded as a test file).
- **`docs/architecture.md`** — no-op. No module boundary or public contract
  changed at the architecture level: `review_config` is a new leaf `_common`
  helper mirroring the existing `project_layout` pattern; no ADR trigger beyond
  ADR-0040 which already governs.
- **`docs/conventions.md`** — no-op. No new authoring rule.
- **`docs/refinement-todo.md`** — no-op. No new deferral; existing seams are
  owned by 096-02 / 096-05 / ADR-0040 OQ1.
- **`docs/inbox.md`** — swept; nothing resolved by this slice.
- **Spec 053 `## Amendments`** — deferred to Close-out (post-DONE), per the
  slice's own close-out list.
- **Lightweight decisions** — none (no UI strings / visual / brand calls).
- **Memory** — one candidate: the `_common` config-helper pattern + the
  portable-identifier-in-committed-evidence lesson; folded into `/jig:memory-sync`
  at session close, not a per-slice memory write.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Spec 053 gets a dated `## Amendments` entry recording that its exact-name /
      user-scope-only resolution is superseded (ADR-0010 — records get
      amendments, live prose is corrected inline).
- [x] Prose note added to `bug-fix`, `pr-review`, `arch-review`, `code-health`
      SKILL.mds re: orchestrated-pass-only config honoring (AC7). (Done in
      implementation, not post-DONE — verified present in all four + propagated
      to host packages.)
