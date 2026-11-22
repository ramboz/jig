---
status: DRAFT
dependencies: [adr-0073]
last_verified: 2026-11-21
kind: feature
arch_review: true
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 128-01 — scaffold-writes-verify-stub

**Goal:** a freshly scaffolded project gets a `verify` skill stub in its host's
project-skill folder, which the agent can find before committing and which
says `not-run` until the owner fills it in; jig never overwrites it.

**Decision:** [ADR-0073](../../decisions/adr-0073-repo-verify-skill-contract.md)
points 1–4 and 6.

**DoR:**
- ⬜ ADR-0073 Accepted.
- ⬜ Host-loader probe recorded in this slice: on Claude Code, Codex and
  Copilot CLI, a project `SKILL.md` carrying an extra `verify-command:` key
  loads and is listed (spec A2). If any host refuses it, settle ADR-0073's
  `metadata:` open question first and update AC2.
- ✅ The write point is known: `scaffold()` writes host primers, docs and the
  seed spec, then `scaffold.json` last as the completion sentinel
  (`skills/scaffold-init/scaffold.py:3995`, `:4087`). The stub is written
  before the sentinel, on both the plugin-only and in-repo paths.

**Acceptance Criteria:**

1. **Stub written on scaffold.** `scaffold()` writes `verify/SKILL.md` under
   `.claude/skills/` for `--host claude` and `--host copilot`, and under
   `.agents/skills/` for `--host codex`, in both plugin-only and in-repo
   modes. The scaffold completion output names the path written.
2. **Contract shape.** The stub's frontmatter has `name: verify`, a
   `description` saying when to use it (before committing a change that
   affects what the app does; when asked to verify, smoke-test or run the app;
   when a slice's verification scenario needs runtime evidence), and an empty
   `verify-command:` key with a one-line comment showing its form and exit
   codes (`0` pass, `1` fail, `2` environment error). The body has Boot,
   Drive, Inspect, Teardown and Known flaky sections and an optional Feature
   map section, each with one line of guidance, and a rule that while the
   stub is unfilled the agent reports runtime verification as `not-run`,
   never `pass`.
3. **Host-neutral bytes.** The stub is byte-identical across the three hosts
   and both modes for the same project name: it contains no
   `${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_ROOT}`, `jig:` skill name, `CLAUDE.md` or
   `AGENTS.md` reference, and is rendered with no host rewrite (only
   `{{PROJECT_NAME}}` is substituted).
4. **Never overwrites.** When a `verify/SKILL.md` already exists in
   `.claude/skills/` or `.agents/skills/` (a file, or a folder link), the
   scaffold writes nothing there, leaves its bytes unchanged, and the
   completion output says it kept the existing one. This holds under
   `--force`. `copy_machinery()` (and so `migrate copy-machinery`) never
   writes or updates the stub.
5. **Not a jig skill.** The stub ships as a template outside `templates/docs/`
   (so the docs walk does not render it) and is never a loadable `SKILL.md` in
   any host package: `hosts/claude`, `hosts/codex` and `hosts/copilot` contain
   no `verify/SKILL.md`, `build_host_packages.py --check` passes, and
   `scaffold._TIER_SKILLS` does not list `verify`.
6. **Discovery treats it as the project's own skill.** For a scaffolded
   project, `skill_discovery.is_jig_baseline_path` is `False` for the stub, and
   `enumerate_candidates` lists it as `speculative` for every review category
   (its description contains no `_CATEGORY_TRIGGERS` phrase,
   `skills/_common/skill_discovery.py:195-218`). The module docstring
   (`skill_discovery.py:23-29`) names the stub as the one user-owned,
   unprefixed skill a scaffold writes. A new test runs `scaffold()` end to end
   and asserts the only unprefixed project-scope `SKILL.md` it writes is
   `verify`; `ScaffoldExclusionInvariantTest` still passes unchanged.
7. **Docs.** `skills/scaffold-init/SKILL.md` lists the stub among scaffold
   outputs, and `templates/docs/adoption-readiness.md.template` gains one item:
   fill in the `verify` skill's Boot and Inspect sections.

**Edge cases to cover explicitly:**
- `--docs-root .` (track-local adoption): the stub still goes under the
  target's `.claude/skills/` or `.agents/skills/`; the docs root does not move
  it.
- A `verify` skill only at user scope (`~/.claude/skills/verify/`) does not
  stop the project stub being written.
- `.claude/skills/verify` is a link to `.agents/skills/verify`: counts as
  existing; nothing is written.
- A greenfield scaffold where `.claude/skills/` does not exist yet: the folder
  is created.

### Behavioral rules (optional)

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | Scaffold | Developer | No `verify` skill in either project folder | Stub written in the host's folder | One place to say how to run the app | 1, 2 |
| BR-2 | Scaffold or re-scaffold | Developer | A `verify` skill exists in either project folder | Nothing written; existing bytes unchanged | The project owns the skill | 4 |
| BR-3 | Run review discovery | Orchestrator | Stub present | Listed as `speculative`, never as a jig baseline | It is the project's skill, not a review skill | 6 |
| BR-4 | Use the skill | Agent | Stub unfilled | Reports `not-run` | Not-run is not a pass (spec 118) | 2 |

### Verification scenario (optional)

**Preconditions:** Python 3.9+, a temporary directory, the jig working tree;
no network.

**Invocation:** for each host in `claude`, `codex`, `copilot` and each mode
(plugin-only, in-repo), run `scaffold.py` into a fresh temporary project, read
the stub, then re-run with `--force` after editing the stub.

**Preserved behavior:** existing scaffold outputs are byte-identical apart from
the new file; `verify_install.py --mode scaffold` still passes.

**Code revision / dirty-change identity:** _recorded at execution._

| Step | AC | Expected | Observed | Outcome | Evidence |
|------|----|----------|----------|---------|----------|
| 1 | 1, 3 | Stub at the host's folder; bytes equal across all six runs | _at execution_ | _not-run_ | _at execution_ |
| 2 | 4 | Edited stub unchanged after `--force` re-scaffold | _at execution_ | _not-run_ | _at execution_ |
| 3 | 6 | `review.py candidates pr_review …` lists `verify` as `[speculative]` | _at execution_ | _not-run_ | _at execution_ |
| 4 | 5 | `build_host_packages.py --check` exits 0; no package has `verify/SKILL.md` | _at execution_ | _not-run_ | _at execution_ |

**DoD:**
- [ ] All ACs pass; full test suite green (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one
      fixture. Edge cases listed in the slice are covered explicitly.
- [ ] Each new test has been shown to fail when its feature is removed —
      the test is capable of failing, not vacuously green (mutate the
      feature, watch the test go red, restore).
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by
      `review.py`.
- [ ] Implementation review passed.
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were
      deferred during implementation.

### Close-out (post-DONE)

These items can only be ticked AFTER the final `RECONCILED → DONE`
transition. Slice-land's `check_dod` (slice 009-01) excludes them
from the count.

- [ ] `docs/specs/README.md` regenerated by `workflow.py status-board`.
      Notes column receives any load-bearing per-slice invariant
      (it's preserved across regen).
- [ ] Primer hygiene per spec 025-01 rule: **if this slice closes the
      spec** (all non-deferred slices DONE), check `CLAUDE.md`,
      `AGENTS.md`, and scaffold templates when present, then **compress**
      the spec's Active-specs entry. If the spec is still in flight, leave
      the entry.

**Anti-horizontal-phasing check:** after this slice, a new project's agent
finds a `verify` skill before committing that says how to run the app — or
says plainly that nobody has written that down yet, so it reports `not-run`.

### Deviation log (after reconciliation)

The original slice is preserved above. Implementation notes:

_TODO: numbered sections covering deviations from the planned shape,
reviewer findings folded back in, doc updates, plan adherence._

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | _TODO_ |
| `docs/specs/README.md` | `updated` | _TODO_ |
| `docs/product-vision.md` | `no-op` | _TODO_ |
| `docs/architecture.md` | `no-op` | _TODO: likely `updated` — scaffold outputs and the discovery invariant._ |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `no-op` | _TODO_ |
| `docs/inbox.md` | `no-op` | _TODO_ |
| `docs/refinement-todo.md` | `no-op` | _TODO_ |
| `docs/memory/**` | `no-op` | _TODO_ |
| `docs/decisions/README.md` / ADR index | `no-op` | _TODO_ |
| Additional live prose / generated templates touched by this slice | `deferred` | _TODO_ |
