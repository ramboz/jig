---
status: DRAFT
dependencies: [096-01]
last_verified:
frame_review: true
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

## Slice 096-02 — baseline-exclusion-and-resolve

**Goal:** A skill *name* resolves to a concrete SKILL.md path deterministically
across every scope on the active host, and jig's own shipped baselines are
machine-identifiable so they can never be offered back as "richer" — the two
deterministic primitives the zero-config layer needs. Exclusion uses the
existing **`jig-` path prefix / "unprefixed ⇒ no SKILL.md" invariant** at project
scope (ADR-0040 D2), not a new frontmatter marker.

**Why `arch_review: true`:** this adds a new shared resolution + exclusion helper
consumed by three passes across two host packages, and touches the
`detect_richer_skill` boundary — a module-boundary and public-contract change.

**DoR:**
- ✅ 096-01 DONE (config precedence exists; this generalizes its resolver).
- ✅ Codex scope list verified (spec `## Assumptions`): `$HOME/.agents/skills`,
  `.agents/skills`, `/etc/codex/skills`.
- ✅ ADR-0040 D2 verified in-tree: `scaffold.py:742` prefixes user-facing skills
  `jig-`; the two unprefixed writers (`:726`, `:1485-1489`) omit `SKILL.md`;
  `migrate.py:287` ships the discriminator.
- ✅ `scripts/build_codex_plugin.py` + the host-package drift gate are understood
  as the surfaces that must regenerate *iff* the plugin/admin-scope marker (AC3,
  OQ4-gated) is adopted.

**Acceptance Criteria:**

1. **Name → path resolution across all scopes, per host.** A helper resolves a
   bare skill name to an existing `SKILL.md` searching, in precedence order:
   project scope, user scope, then admin/plugin scope — Claude
   (`.claude/skills`, `~/.claude/skills`, plugin dirs) and Codex
   (`.agents/skills`, `$HOME/.agents/skills`, `/etc/codex/skills`). Returns
   `None` when unresolvable. Conservative on every error (never raises on a
   `stat`/permissions failure); honors `$HOME` so it is hermetically testable.
2. **Frontmatter parsing is shared and tolerant.** One parser extracts `name`
   and `description` from a SKILL.md, handling plain, folded (`>`), and literal
   (`|`) YAML scalars — the shapes both hosts' skills actually use. Malformed /
   absent frontmatter yields `None`, never an exception.
3. **Project-scope exclusion uses the `jig-` prefix / "unprefixed ⇒ no SKILL.md"
   invariant** (ADR-0040 D2, replacing the forward-only marker). A discovery
   query for a *richer* skill at **project scope** excludes any dir whose name
   starts with `jig-` (jig's own scaffolded copies), reusing the discriminator
   `migrate.py:287` already ships. This covers old *and* new scaffolds with no
   frontmatter contract and no migration. A test asserts the load-bearing
   invariant directly: **no unprefixed project-scope skill dir a scaffold writes
   carries a `SKILL.md`** (holds for both unprefixed writers — `scaffold.py:726`
   shared modules and `:1485-1489` the Codex logical-name alias).
4. **Plugin/admin-scope marker is OQ4-gated, not assumed.** jig's shipped skills
   are *unprefixed* at plugin/admin scope, where a path test cannot see them.
   **Before** adopting a `jig_baseline: true` marker there, this slice rules out
   a plugin-directory test (jig's plugin dir is itself named `jig`:
   `hosts/codex/plugins/jig/skills/…`). If a plugin-dir test suffices, **no
   marker ships** and there is no host-package regeneration. If it does not, the
   marker is adopted *at plugin/admin scope only*, stamped on shipped baselines,
   and the drift check (`--check`) must be green after regeneration. The
   decision + rationale is recorded (resolving OQ4).
5. **A scaffolded jig baseline is never a discovery candidate.** With AC3 (+ AC4
   if adopted), a resolver query for a *richer* skill excludes jig's own
   baselines at every scope — including a scaffolded project-scope copy, and
   including *already-scaffolded* projects (the population the forward-only
   marker could not reach). Closes the
   [deferred refinement-todo entry](../../refinement-todo.md).
6. **The read-only reviewer can Read a resolved SKILL.md at project and admin
   scope** (spec `## Assumptions`, moved here to be probed). Because a hermetic
   Python test exercises only the *resolver's path logic* — not a *subagent's*
   Read/Glob/Grep sandbox reach into `/etc/codex/skills` or a plugin dir — the
   admin/plugin-scope claim **requires a documented live probe** (a real reviewer
   subagent reading a path at that scope); the hermetic test alone is
   insufficient for it. Project + user scope may be covered hermetically (spec
   053 already confirmed user scope readable). If the reviewer cannot read
   admin/plugin scope, the finding is recorded and the resolver scoped to what
   the reviewer can actually read.
7. **Explicit config still overrides exclusion.** A user who configures a jig
   baseline path in `scaffold.json` (096-01) gets it — exclusion filters
   *discovery*, never *configuration*.
8. **The stale docstrings are corrected inline** (ADR-0010 live-prose policy).
   `detect_richer_skill`'s "indistinguishable by path" docstring
   (`review.py:565-569`) and `build_code_health_review_prompt`'s "no established
   richer code-health reviewer category" docstring (`review.py:887-890`) are both
   corrected inline — the first is falsified by D2, the second by D1's inclusion
   of `code_health`.

**Edge cases to cover explicitly:**
- A skill directory with no `SKILL.md` → skipped, not an error.
- A symlinked skill directory → resolved through (the documented unblock for the
  reported bug is `ln -s`).
- Same skill name present at two scopes → most-specific wins, deterministically.
- `/etc/codex/skills` absent (the common case) → skipped silently.
- A user's own skill legitimately prefixed `jig-*` at project scope → excluded;
  documented as an accepted, rare cost of the prefix rule (jig owns the `jig-`
  namespace in `.claude/skills/`).
- An already-scaffolded project (pre-096) with `.claude/skills/jig-pr-review/` →
  excluded by AC3 with no migration.

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly.
- [ ] Hermetic tests — all scope roots are injectable; no test reads the
      developer's real `~/.claude` or `~/.agents`.
- [ ] Host packages regenerated + `--check` drift gate green **iff** the AC4
      marker is adopted; a no-op otherwise (recorded).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed. Arch pass passed (`arch_review: true`).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated — the project-scope detection entry is
      resolved by AC5; ADR-0040 OQ4 recorded as resolved by AC4.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Resolve the "project-scope richer-skill detection in `review.py`"
      refinement-todo entry, linking this slice.
