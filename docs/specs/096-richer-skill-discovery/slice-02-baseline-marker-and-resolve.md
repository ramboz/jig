---
status: RECONCILED
dependencies: [096-01]
last_verified: 2026-07-28
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
- [x] All ACs pass; full test suite green (no regressions). 3632 tests OK; ruff
      clean; host-package drift in sync.
- [x] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases listed above are covered explicitly (56 `_common` tests).
- [x] Hermetic tests — all scope roots are injectable; no test reads the
      developer's real `~/.claude` or `~/.agents`.
- [x] Host packages regenerated + `--check` drift gate green (no marker adopted;
      review.py + skill_discovery + review_config changes propagated).
- [x] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [x] Implementation review passed. Arch pass passed (`arch_review: true`).
      (A blocker — `is_jig_baseline_path` matching `jig` anywhere — was caught by
      compliance+craft+arch, fixed, and re-passed.)
- [x] Deviation log produced under this slice heading.
- [x] Reconciliation sweep produced under this slice heading.
- [x] Reconciliation review passed.
- [x] `docs/refinement-todo.md` updated — the project-scope detection entry is
      resolved by AC5; ADR-0040 OQ4 recorded as resolved by AC4.

### Deviation log (after reconciliation)

Original ACs preserved. Implementation notes + decisions:

- **OQ4 resolved: NO marker adopted.** The plugin is named `jig` on both hosts
  (`hosts/codex/plugins/jig/`, Claude `plugin.json` `"name": "jig"`), so jig's
  admin/plugin-scope baselines are identifiable by a `jig` path segment — a pure
  path test, same class as the project-scope `jig-` prefix. `is_jig_baseline_path`
  handles both. So **no `jig_baseline: true` frontmatter marker ships**, there is
  **no host-package regeneration for a marker**, and ADR-0039 OQ4 (no migration)
  is *mooted* — with no marker there is nothing to migrate. This is the cheaper
  resolution the frame-critique pointed at.
- **AC6 VERIFIED by live probe (not deferred).** A real `jig:reviewer` subagent
  Read a SKILL.md at project scope AND at an absolute admin/plugin path outside
  the project — both succeeded, returning the fixture `description`. So the
  multi-scope resolver's paths are reviewer-readable; no scope is withheld. The
  spec `## Assumptions` entry is updated VERIFIED (extends spec 053's user-scope
  confirmation to project + admin/plugin). **Note:** this is an *attestation*
  (a recorded live-probe result), not a hermetic test result reproducible from
  the tree — AC6 explicitly calls for a live probe precisely because a Python
  test cannot exercise a subagent's sandbox reach.
- **New module `_common/skill_discovery.py`** (the arch-relevant boundary): the
  home for scope roots (per host), `resolve_skill_path` (exclusion-aware,
  multi-scope), `resolve_skill_path_any_host` (config bare-name convenience),
  `is_jig_baseline_path`, and a tolerant `parse_skill_frontmatter`
  (plain/folded/literal scalars). Distinct from `review_config` (scaffold.json
  config); 096-03's enumeration/candidate channel composes it.
- **Config bare-name resolution upgraded to multi-scope/host** (closes the
  096-01 Codex bare-name seam the 096-01 frame-critique flagged): `review_config`
  now delegates bare-name resolution to `skill_discovery.resolve_skill_path_any_host`
  (project → user → admin, Claude then Codex), with exclusion OFF (AC7 — config
  overrides the discovery filter). Explicit paths still used as-is. The 096-01
  user-scope tests still pass (user scope is still searched).
- **AC8 docstring correction:** `detect_richer_skill`'s "indistinguishable by
  path" claim is corrected inline (ADR-0010 live-prose policy) — the premise is
  false; the `jig-` prefix discriminator + `skill_discovery` are the correction.
  (The code-health builder's stale docstring was already corrected in 096-01;
  `build_frame_critique_prompt`'s "no established richer frame-critique reviewer"
  is correct never-defer prose, untouched.)
- **`detect_richer_skill` retained, not removed** (AC): it stays as the legacy
  last-fallback until 096-03 removes it via the full explicit-candidate chain.
- **Review-driven blocker fix (compliance + craft + arch all flagged it):**
  `is_jig_baseline_path`'s admin/plugin test originally matched a `jig` segment
  *anywhere* in the ancestor path — a **fail-closed false positive** that would
  wrongly exclude a genuine richer skill at project scope inside any `jig`-named
  path (jig's own repo while dogfooding, or a checkout under `.../misc/jig/...`,
  or this very worktree). Fixed to **anchor the `jig` match to a `plugins/`
  ancestor** (`.../plugins/**/jig/**/skills/...`). Added tests:
  false-positive prevention (genuine skill under a `jig`-named project root
  resolves in discovery mode), `jig`-before-`plugins` not matched, the symlinked
  skill-dir edge case, and `_default_claude_admin_roots`' plugin glob. Also
  corrected `review_config`'s "stdlib only" module docstring (it now imports the
  sibling `skill_discovery`), documented the Claude-then-Codex cross-host
  precedence tiebreak, and refreshed the `docs/architecture.md` `_common` list.
  A second re-review round fixed a stale `review_config` module-docstring
  paragraph (still described bare-name resolution as user-scope-only,
  contradicting the now-multi-scope code), dropped `review_config` from
  `skill_discovery`'s "stdlib-only mirror" set, and anchored a *relative*
  explicit config path to `project_dir` (not CWD — scaffold.json is a committed
  project-relative manifest).

**Known gaps carried to 096-03** (the slice that actually wires discovery
exclusion — here exclusion runs only in unit tests; config uses
`exclude_jig_baselines=False`):

- **Codex admin-scope exclusion is unproven.** `is_jig_baseline_path` catches a
  Claude admin baseline via its `plugins/**/jig/**` path, but a jig baseline
  installed directly under Codex's `/etc/codex/skills/<skill>/` has neither a
  `jig-` prefix nor a `plugins/jig` ancestor, so it would slip the path test.
  AC5's "every scope, both hosts" is proven for project scope (both hosts) +
  Claude admin scope; Codex admin-scope exclusion is a 096-03 obligation.
- **OQ4 path test fails OPEN and couples to a host-internal layout.** The admin
  arm keys on the host's plugin-cache dir shape (`plugins/.../jig/...`), which
  jig does not own. If a host changes its plugin-dir scheme, a jig baseline
  could be offered back as "richer" — the fail direction is *open* (a marker
  would fail closed). Accepted here because config precedence (096-01) is the
  guaranteed floor and no exclusion-on consumer ships in this slice; 096-03
  inherits this as a known risk.
- **`parse_skill_frontmatter` minor fidelity:** drops embedded blank lines in
  literal (`|`) scalars and requires a trailing newline after the closing
  `---`. Fine for name/description extraction; flag if 096-03 needs faithful
  multi-paragraph descriptions.

### Reconciliation sweep

- **Deviation log** — updated (above).
- **`docs/refinement-todo.md`** — the "project-scope richer-skill detection"
  entry marked RESOLVED, linking this slice; OQ4 mitigation (marker idea)
  recorded superseded. `updated`.
- **`docs/specs/.../spec.md` `## Assumptions`** — reviewer-read item flipped
  ASSUMED → VERIFIED. `updated`.
- **`detect_richer_skill` docstring** (`review.py`) — corrected inline (AC8).
  `updated`.
- **Host packages** (`hosts/claude`, `hosts/codex`) — regenerated (review.py +
  new `skill_discovery.py` + `review_config.py` propagated;
  `test_skill_discovery.py` correctly excluded); drift `--check` green. `updated`.
- **`docs/architecture.md`** — `updated` (mechanical: the `_common` list refreshed
  to add `project_layout.py`, `review_config.py`, `skill_discovery.py`). No
  module-boundary or public-contract change beyond what ADR-0040 D2 already
  governs — `skill_discovery` is a new leaf `_common` module mirroring the
  documented shared-helper convention — so no new ADR (ADR-0040 governs; this
  implements D2).
- **`docs/conventions.md`** — no-op.
- **`docs/inbox.md`** — swept; nothing resolved.
- **Lightweight decisions** — none.
- **Memory** — the "path-prefix beats frontmatter marker for baseline exclusion"
  + "reviewer can read admin-scope absolute paths" lessons; folded into
  `/jig:memory-sync` at session close.

### Close-out (post-DONE)

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
- [ ] Resolve the "project-scope richer-skill detection in `review.py`"
      refinement-todo entry, linking this slice.
