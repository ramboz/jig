# Frame critique — spec 084 / ADR-0033 (configurable docs root)

Date: 2026-06-29 · Gate: pre-`READY_FOR_REVIEW` (ADR-0020, `frame_review: true`).
Method: challenge the founding premises against code, not the prose. Findings
graded; HIGH/MEDIUM folded back into the artifacts (see "Disposition").

## Premises under test

- P1: The configured offset jig needs is `project_dir → docs_root`.
- P2: Artifact placement and git anchoring are cleanly separable, so v1 can ship
  "local mode works / push mode deferred."
- P3: `scaffold.json` at the project root resolves the discovery chicken-egg.
- P4: The change is "replace `project_dir / 'docs' / x` construction sites."
- P5: Default output / behavior is unchanged.
- P6: Adoption happens via greenfield `scaffold-init`.

## Findings

### A — Discovery is a second, worse failure category (HIGH) — P4 false as stated

The spec framed the change as rewiring path **construction**. But jig also does
project-root **discovery** by walking *up* for a `docs/` marker:
`_find_project_root` ([review.py:167](../../../skills/independent-review/review.py))
returns the first ancestor with `docs/architecture.md`. Under `docs_root="."`
the marker is at `<project_dir>/architecture.md`, so the walk:

- misses at the subproject level, and
- keeps climbing — resolving to an **ancestor that happens to have
  `docs/architecture.md`** (the enclosing monorepo). That is silent
  **cross-project bleed**, strictly worse than a missing-file: the reviewer
  prompt would read the *big repo's* architecture.

The no-stray-`"docs"`-literal guard (084-02 AC6) targets construction and would
not catch a discovery walker that legitimately needs *some* marker. Correct
marker under `"."` is the **sentinel** (`scaffold.json`), not `docs/`. This
promotes "scaffold.json is the project-root marker" to a first-class premise and
adds a discovery-site inventory + a cross-project-bleed AC.

### B — "Local mode" is not git-anchor-free (HIGH) — P2 mis-stated

`reserve_spec` commits even with `--no-push`: off-main+`--no-push` →
`_reserve_local_on_current_branch` (a commit on the current branch); on-main →
commit on local main; both run `_current_branch()` / `_refuse_if_dirty()`
against `project_dir` ([workflow.py:3015-3026](../../../skills/spec-workflow/workflow.py)).
In a subtree, `git -C project_dir` resolves to the **enclosing repo**, so local
reservation:

- refuses when the **whole monorepo** working tree is dirty (anywhere),
- routes on the **big repo's** branch (rarely `main` in a monorepo), and
- commits to the big repo's current branch.

So the real cleavage is **artifact placement** (this spec fixes) vs **git
anchoring** (deferred for *all* modes, local included) — not "local works / push
deferred." Local mode is *tolerable* (its side-effects are local/recoverable)
but has a real rough edge (whole-repo dirty refusal). Must be documented, not
shipped silently.

### C — Push-mode-in-subtree may be a category error, not a deferral (MEDIUM) — P2

Reserving against a monorepo's shared `origin/main` via an ephemeral worktree,
and PR-shaped land opening a PR on the whole org repo, may be **undesirable by
design**, not merely unbuilt. "Tracked for a follow-up" over-promises. Reframe:
revisit only with a concrete multi-project reservation model; until then it is
refused, full stop.

### D — Adoption entry-point gap (MEDIUM) — P6 unstated

"Inside a larger repo" can be greenfield (`scaffold-init`) or existing
(`migrate`). The spec only adds `--docs-root` to `scaffold-init`;
`migrate.py` has no layout entry point. State the assumption (v1 adoption =
greenfield `scaffold-init`) and make migrate-into-subtree an explicit non-goal.

### E — `docs_root` is a mild misnomer at `"."` (LOW) — P1

When the value is `"."` there is no docs *root*; the key really toggles "insert a
`docs/` layer or not." Pragmatically fine; renaming the key buys nothing and
costs compatibility. Keep `layout.docs_root`; note it here.

### F — Guard precision (LOW) — P4

The no-stray-literal guard must separate construction literals (catch) from the
legitimately-retained pre-sentinel detector literals **and** discovery markers
(allowlist). Feasible; needs an explicit, documented allowlist (already in AC6,
reinforced).

## Disposition

| Finding | Grade | Action |
|---|---|---|
| A discovery / cross-project bleed | HIGH | ADR §structural + new premise; 084-02 inventory + new AC (sentinel-based discovery, bleed guard). |
| B local mode not git-free | HIGH | ADR + spec reframed to placement-vs-anchoring; 084-03 AC notes whole-repo dirty caveat. |
| C push = possible category error | MEDIUM | ADR/spec soften "follow-up" → "revisit only with a real model." |
| D adoption entry point | MEDIUM | spec non-goal + assumption added. |
| E naming | LOW | recorded; keep key. |
| F guard precision | LOW | reinforced in 084-02 AC6. |

P3 and P5 hold unchanged. Premise P1 stands (one knob is right); E is cosmetic.

## Independent pass (jig:reviewer, round 1) — verdict: needs-changes

A fresh `jig:reviewer` (no impl-conversation context) confirmed findings A/B and
the placement-vs-anchoring cleavage, then found a **third discovery category the
author and this pre-critique both missed**:

### G — Depth-arithmetic root derivation (HIGH) — extends finding A

`_project_root_for_spec` (workflow.py:992-1008) and the bare `parents[3]` at
`_record_spec_ref` (workflow.py:981) and the DONE-dependency check
(workflow.py:1149) derive the project root by **depth arithmetic** assuming
`docs/specs/<dir>/spec.md` (root = `parents[3]`), with a `.git` fallback that
also climbs to the enclosing repo. Under `docs_root="."` a real spec is at
`<project_dir>/specs/<dir>/spec.md`, so `parents[3]` resolves to the **enclosing
repo** — the same cross-project bleed as A, in the *post-`new` lifecycle*
(transition / slice-claim `claimed_by` / DONE-dependency / `.jig/spec-ref`),
which slice 084-02's `status-board`/`new`/`adr` ACs never exercise.

**Reframe:** finding A's "switch the `docs/` marker for the sentinel" was too
narrow. The real invariant is **project-root discovery is sentinel-anchored,
never structure-derived** — covering BOTH the marker up-walk AND the depth
arithmetic via one `project_root_for(path)` resolver (ADR-0033 §5a, new in
slice 084-01).

### Secondary (round 1) — push-refusal guard well-definedness (MEDIUM)

Slice 084-03 AC5's subtree test `repo_root != project_dir` only fires if
`project_dir` is the subproject root; if a host passes the enclosing repo root
the guard silently never fires. Disposition: pinned `project_dir` resolution to
the sentinel anchor (ADR-0033 git-anchoring scope-out; slice 084-03 AC5).

### Disposition (round 1)

| Finding | Grade | Action |
|---|---|---|
| G depth-arithmetic discovery | HIGH | ADR §5a reframed (sentinel-anchored, two categories); `project_root_for` added to slice 084-01; slice 084-02 inventory + AC7 + bleed guard extended to the lifecycle path. |
| push-guard well-definedness | MEDIUM | `project_dir` resolution pinned to the sentinel (ADR + slice 084-03 AC5). |

Round 2 (independent re-critique) pending; canonical verdict recorded at
`docs/decisions/reviews/adr-0033-frame-critique.md` once it clears.
