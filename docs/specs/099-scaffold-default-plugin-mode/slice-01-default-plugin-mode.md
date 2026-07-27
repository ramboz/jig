---
status: IN_PROGRESS
dependencies: []
last_verified: 2026-07-24
---

<!-- jig self-defining vocabulary (soft, forward-only): expand each acronym on
     first use and link the term to docs/memory/glossary.md (or jig's lexicon).
     See docs/workflow.md "Self-defining vocabulary". -->

<!-- jig grounding (spec 064-02 / ADR-0020): ground factual claims about
     runnable surfaces by probe first (run it / read source) or a citation,
     else mark them as assumptions in the spec's `## Assumptions` section —
     never assert an unverified claim as fact. -->

## Slice 099-01 — default-plugin-mode

**Goal:** A no-flag `scaffold.py <dir>` produces a lean plugin-mode project
(no copied machinery); copying jig's machinery in-repo is the deliberate
`--in-repo` opt-in; and the operator can see and choose the axis (a sixth Q&A
question + a summary line that names the mode and why). Applies to both hosts.

**DoR:**
- ✅ [ADR-0041](../../decisions/adr-0041-scaffold-defaults-to-plugin-mode.md)
  records the decision (Proposed) and the rejected alternatives.
- ✅ The off-switch (`--plugin-only`, `dest=with_machinery`, `store_false`) and
  both code paths (`copy_machinery` vs the plugin-only branch) already exist in
  `scaffold.py` — this slice flips the group default and renames the opt-in.
- ✅ The plugin registers every gate globally in `hooks/hooks.json`, so plugin
  mode keeps the security floor minus `permissions.deny` (spec §Security-floor
  note) — no floor work is in this slice.

**Acceptance Criteria:**

1. **A content-only / no-flag scaffold produces plugin mode.** Running
   `scaffold.py <dir>` (no machinery flag, either host) writes **no** copied
   machinery: no `.claude/skills/`, no `.claude/agents/`, no
   `.claude/hooks/scripts/`, no `.claude/settings.json` (and the Codex equivalents
   under `.codex/`). `scaffold.json.scaffold_mode == "plugin-only"`.
2. **in-repo is opt-in via an explicit flag.** `--in-repo` copies the machinery
   and sets `scaffold_mode == "in-repo"`, producing the same tree the old default
   produced. `--with-machinery` and `--copy-machinery` are accepted aliases of
   `--in-repo` (identical result). `--plugin-only` still selects plugin mode, and
   passing a plugin-mode flag together with an in-repo flag is a usage error
   (mutually exclusive, exit 2).
3. **The wizard summary names the chosen mode and why.** After a successful
   scaffold, stdout carries a line stating the mode: for plugin mode, that the repo
   stays lean and jig runs from the installed plugin, and that `--in-repo` copies
   machinery in for CI / cloud agents / plugin-less teammates; for in-repo mode,
   that the machinery was copied and the project is self-contained. The line is
   present for **both** hosts and matches the mode actually produced.
4. **The skill surfaces the axis.** `skills/scaffold-init/SKILL.md` Q&A flow gains
   a sixth question on the machinery-vs-plugin axis (skippable → plugin mode
   default), maps a "yes" to `--in-repo`, and the documented invocation example and
   Output section reflect the new default (plugin mode by default; in-repo when
   opted in).

**DoD:**
- [ ] All ACs pass; full test suite green on Python 3.9 (no regressions).
- [ ] Implementer test coverage exercises each AC with at least one fixture.
      Edge cases covered: alias equivalence (`--in-repo` == `--with-machinery`),
      mutual-exclusivity error, both hosts, and the summary text per mode.
- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by `review.py`.
- [ ] Implementation review passed (compliance + craft; +frame — this reverses a
      recorded default).
- [ ] Deviation log produced under this slice heading.
- [ ] Reconciliation sweep produced under this slice heading.
- [ ] Reconciliation review passed.
- [ ] `docs/refinement-todo.md` updated if any decisions were deferred.

**Anti-horizontal-phasing check:** After this slice lands, a user running
`scaffold.py <dir>` gets a lean plugin-mode project, sees a summary explaining the
mode, and can opt into in-repo with one obvious flag — a complete, observable
end-to-end change in the default scaffold experience, not an intermediate state.

### Deviation log (after reconciliation)

The original spec is preserved above. Implementation notes:

**1. No deviation from the planned code shape.** The flag surface, the summary
line, and the Q&A question landed as specified. The off-switch already existed,
so the change is: `--in-repo` added as the `store_true` opt-in (with
`--with-machinery` / `--copy-machinery` as aliases on the same action, so they are
aliases by construction rather than by duplicated logic), `default=False` on the
group, `--plugin-only` retained as `store_false`.

**2. `scaffold()`'s parameter default was flipped too, beyond the literal ACs.**
The ACs describe CLI behavior; leaving the function default at `True` would have
made the API disagree with the CLI and quietly re-introduce the old default for
every in-process caller. Flipped in step and noted in the docstring as an
invariant to keep. Probed: no non-test caller passes it positionally.

**3. Test updates are re-targets, not loosenings.** Every test that now passes
`--in-repo` is one whose assertions are *about* the copied tree (skills/agents/
hook scripts, `settings.json`, `permissions.deny`, tier-on-disk == manifest, the
in-repo doc rewrite, skill-closure contract). Two behavioral notes discovered
while doing this, both worth keeping:
   - `UnmanagedHooksError` only fires during the machinery copy, so the
     refusal/recovery test is meaningless in plugin mode and must stay in-repo.
   - `test_default_includes_machinery` (016-03's pin on the old default) was
     **inverted** into `test_default_is_plugin_mode` rather than deleted, so the
     new default is pinned exactly where the old one was.

**4. Review round 1 found four doc surfaces still asserting the old default**,
including one this slice had already half-edited — `docs/product-vision.md`, where
the *history* section was amended but standing **principle #7** still read
"scaffolded mode is the default because positioning matters." Also stale:
`docs/philosophy.md`'s "Own the scaffolding; don't rent the plugin" principle,
`skills/migrate/SKILL.md`'s "(default since slice 016-03)", and a now-inverted
comment in `scaffold.py`. All corrected inline per ADR-0010 (live prose, not
records). Lesson: a half-updated file is worse than an untouched one — grep the
whole file for the claim being reversed, not just the section you came to edit.

**5. Review round 1 also caught a user-facing seed defect.** The worked-example
seed spec emitted into *every* greenfield project
(`templates/docs/specs/seed/001-adopt-jig/`) told the adopter they had received
"the runtime machinery under `.claude/`" — false on the new default path, in the
first artifact a new project reads. Reworded to be true in both modes, with a
pointer to `scaffold.json`'s `scaffold_mode` as the authority. No new template
placeholder was introduced (that would have meant threading a substitution
through `_emit_seed_spec` for prose that reads fine mode-agnostically).

**6. Test coverage gaps closed after review.** The DoD named "both hosts", but the
Codex suite injects `--in-repo` for its machinery assertions, so the Codex
*default* path was exercised nowhere; added `test_codex_default_is_plugin_mode`
and `test_codex_summary_names_the_mode`. The exclusivity test asserted only
`returncode != 0` where AC #2 names exit 2 — tightened to assert 2, across all
three in-repo aliases.

**7. Known limitations, deliberately not fixed here** (both pre-existing to the
`--plugin-only` path, both now on the *default* path, so they are recorded rather
than silently inherited):
   - **`permissions.deny` is absent from the default scaffold.** Accepted by
     ADR-0041 (§Open questions) — a plugin cannot write project `settings.json`
     permissions. Flagged for a follow-up decision.
   - **Codex plugin mode renders docs with `.codex/skills/…` paths.** The Codex
     doc rewrite is unconditional (`scaffold.py`, `host == "codex"` branch), so a
     Codex plugin-mode project's docs name a runtime directory that was not
     created. **Probed, not inferred:** `scaffold.py --host codex --solo <dir>`
     leaves no `.codex/skills/`, yet the generated `AGENTS.md` and
     `docs/workflow.md` both cite `.codex/skills/jig-*` paths. Pre-existing, but
     the flip makes it the default Codex experience. Not in this slice's ACs;
     needs its own decision (either a mode-gated Codex rewrite or a Codex
     plugin-root path), so it is surfaced here and to the maintainer rather than
     patched in passing.

**8. Review round 2: the sweep table repeated the defect it was written to fix.**
Round 1 faulted the table for claiming dispositions that did not match reality.
The corrected table then carried a `docs/memory/**` row marked `updated` when only
`glossary.md` had been touched — and `learnings.md`, inside that same glob, still
called in-repo "the default in-repo scaffold". The glob asserted coverage the work
did not have, which is exactly how the miss stayed invisible: the row *looked*
discharged. Both fixed. Two process lessons, in order of usefulness:
   - **Sweep rows should name files, not globs.** A glob can be marked `updated`
     while most of what it matches is untouched; a named file cannot. Rows here are
     now file-level wherever the disposition is `updated`.
   - **Reversing a claim means grepping for the claim, not visiting the files you
     expect to hold it.** Round 1's misses (product-vision principle #7, the seed
     templates) and round 2's (`learnings.md`) all had this shape. What finally
     worked was a repo-wide grep for the *assertion being reversed* ("default
     since 016-03", "by default jig copies", "scaffolded mode is the default", …),
     which also turned up two stale `verify_install.py` comments no reviewer had
     named.

**9. One unexplained test flake, recorded rather than waved off.** A single
whole-repo `pytest -q` run failed 4 × `migrate/test_migrate.py::TierUpgradeTests`
("manifest installed_skills must equal on-disk skill set after upgrade"). It does
not reproduce — identical command on the same tree, the file alone, and
`run_tests.py` all pass, and nothing behavioural changed in between (only docs,
comments, tests). Two wrong diagnoses were floated before the right answer
("stale host packages" — impossible, that file's `_SCAFFOLD_PY` points at *source*
`scaffold.py`; "random test order" — pytest-randomly is not installed), so the
honest state is **cause unknown, order/state-dependent, not attributable to this
slice**. Kept out of the DoD's "suite green" claim by naming the runner: green
under `run_tests.py` (3502 tests, pyright clean). To settle it next time, capture
the assertion diff — which skills mismatched and in which direction — which
separates "copy didn't finish" from "manifest written ahead of disk". Same family
as the known intermittent host-drift-guard flake.

**10. Not changed: ADR-0007's "by default" phrasing.** `adr-0007`'s Context
describes 016-03's flip in unbounded present tense. Left alone deliberately —
ADRs are immutable records of a decision at a point in time (ADR-0010), and
correcting their Context prose is how a record stops being a record. ADR-0041 is
the forward pointer for anyone reading 0007 today.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `no-op` | Checked: no mention of the machinery axis, `--with-machinery`, `--plugin-only`, or `scaffold_mode`. Install docs point at the plugin, which is now the default — nothing to correct. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`; Notes column carries the reversal, the both-hosts scope, the `scaffold()`-default-in-step invariant, the `--in-repo` test contract, and the `permissions.deny` gap. |
| `docs/product-vision.md` | `updated` | **Two edits.** Dated amendment under the 2026-05 positioning-recovery history, *and* standing **principle #7** rewritten — it asserted scaffolded mode as the default (caught in review round 1; the file had been half-updated). |
| `docs/philosophy.md` | `updated` | "Own the scaffolding; don't rent the plugin" principle re-premised on the opt-in (caught in review round 1; absent from the original sweep table). |
| `docs/architecture.md` | `no-op` | Checked: no module-boundary or public-contract drift. No new module, no changed helper seam — the change is one argparse default plus a print. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | `CLAUDE.md` Active-specs entry names spec 099 + ADR-0041. Scaffold seed templates (`001-adopt-jig` spec + slice) corrected — they claimed `.claude/` machinery every new project now may not have. |
| `skills/migrate/SKILL.md` | `updated` | "(default since slice 016-03)" was a stale default claim in a skill contract; now names `--in-repo` as the opt-in and bounds 016-03→099-01 as the interval it *was* the default. Mirrored in both packaged copies. |
| `docs/inbox.md` | `no-op` | Checked: no parked item resolved or contradicted by this slice. |
| `docs/refinement-todo.md` | `no-op` | No decision was deferred *by* this slice. The two open questions live in ADR-0041 (§Open questions), which is their proper home — a Proposed ADR's open questions are not refinement-todo items. |
| `docs/memory/glossary.md` | `updated` | "Scaffolded install / scaffold mode" entry re-premised: opt-in, the four reasons plugin mode is the default, and when to choose in-repo. |
| `docs/memory/learnings.md` | `updated` | "Scaffold doc templates render into two install shapes" gotcha said "the default in-repo scaffold"; now names plugin mode as the default and bounds in-repo to the 016-03→099-01 interval. Missed in the first sweep — see deviation §8. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0041 added to the index (Proposed, dated). |
| `hosts/claude/**`, `hosts/codex/**` | `updated` | Rebuilt via `scripts/build_host_packages.py`; drift guard clean. Verified both packaged `scaffold.py` + `SKILL.md` carry the change. |
