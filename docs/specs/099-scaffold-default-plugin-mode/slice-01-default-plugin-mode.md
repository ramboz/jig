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
  note) — no floor work is in this slice. **Superseded during implementation:**
  the maintainer folded `permissions.deny` in
  ([#136](https://github.com/ramboz/jig/pull/136), ADR-0041 OQ1), so floor work
  *is* in this slice — a settings-only write on the Claude plugin-mode path.
  This DoR line records what was true at authoring time; see deviation §7.

**Acceptance Criteria:**

1. **A content-only / no-flag scaffold produces plugin mode.** Running
   `scaffold.py <dir>` (no machinery flag, either host) writes **no** copied
   machinery: no `.claude/skills/`, no `.claude/agents/`, no
   `.claude/hooks/scripts/` (and the Codex equivalents under `.codex/`).
   `scaffold.json.scaffold_mode == "plugin-only"`.
   **Amended during implementation (ADR-0041 OQ1):** this AC originally also
   required *no `.claude/settings.json`*. The maintainer's call to seed
   `permissions.deny` on the plugin-mode path makes that requirement wrong —
   a settings.json IS written on the Claude host, carrying `permissions` and
   **no** `hooks` block. What the AC is really pinning is "no copied
   machinery", and a permissions-only settings file is not machinery.
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
     permissions. Flagged for a follow-up decision. **RESOLVED (round 3):**
     maintainer chose to fold it in; `_write_permissions_deny_floor` now seeds
     it on the plugin-only path — settings-only, no hooks block, and it does
     not run the unmanaged-hooks refusal (that guard protects hook config this
     write never touches). ADR-0041 OQ1; floor table row flipped to ✅.
   - **Codex plugin mode renders docs with `.codex/skills/…` paths.** The Codex
     doc rewrite is unconditional (`scaffold.py`, `host == "codex"` branch), so a
     Codex plugin-mode project's docs name a runtime directory that was not
     created. **Probed, not inferred:** `scaffold.py --host codex --solo <dir>`
     leaves no `.codex/skills/`, yet the generated `AGENTS.md` and
     `docs/workflow.md` both cite `.codex/skills/jig-*` paths. Pre-existing, but
     the flip makes it the default Codex experience. Not in this slice's ACs;
     needs its own decision (either a mode-gated Codex rewrite or a Codex
     plugin-root path), so it is surfaced here and to the maintainer rather than
     patched in passing. **RESOLVED (round 3):** mode-gated, not skipped.
     Skipping the rewrite outright was *measured*, not assumed, and is strictly
     worse — a Codex project's docs would then read `CLAUDE.md`, "Claude Code",
     and `${CLAUDE_PLUGIN_ROOT}` (an unset variable **and** the wrong host).
     Plugin mode instead names the installed plugin via Codex's own
     `${PLUGIN_ROOT}`, already load-bearing in the packaged `hooks/hooks.json`.
     The shared translation lives in one parameterized `_rewrite_host_paths`, so
     host vocabulary cannot drift between modes. ADR-0041 OQ3.

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

**11. Round 3 — the frame-critique found the cost this slice had not priced: a
silent empty scaffold on jig's own README install path.**

The record and this slice both framed plugin-less callers as exotic — CI, cloud
agents, plugin-less teammates, archival repos. The frame-critique named the one
that is not exotic: **two of README's four install recipes are
`git clone … && python3 …/scaffold.py <project>`, with no plugin anywhere.**
Under the in-repo default those recipes worked, because the copy *was* the
install. The flip broke them, and broke them silently — exit 0, and a summary
asserting jig runs from the installed plugin.

The mechanism behind the miss is the same one deviations §4 and §8 named, at a
higher altitude. Those were about grepping for a *claim* rather than visiting
files expected to hold it. This one is about **who**: the population was taken
from the reporter (a jig contributor, plugin installed) and never widened to the
install paths the project itself publishes. A "who is the modal caller" claim is
load-bearing exactly like a behavioural one, and it was the single claim absent
from the ADR's own "probed, not asserted" list — which probed three assumptions,
all of which *confirmed* the chosen direction. **Directional probing is the
defect**: the two claims that could have falsified the direction are the two that
went unprobed.

Three things changed as a result:

- `invoked_from_installed_plugin()` + an advisory note on the plugin-mode path.
  Deliberately a *confirmation*, not a detection: the host sets its plugin-root
  variable only when it drives the run, so `set` proves a plugin while `unset`
  proves nothing (a terminal invocation by someone who *has* the plugin also
  lands there). That asymmetry is why it is a note and not a refusal or a
  default-switch — a one-sided signal may say "cannot confirm", but must never
  silently pick a topology for someone who just used a terminal.
- README's two scaffold recipes now pass `--in-repo` (see the sweep row).
- ADR-0041's kill-criteria detector was rewritten. It had been "repeated reports
  of plugin-mode scaffolds in plugin-less environments" — a **detector that
  cannot fire on the failure it was written for**, because the failure emits
  nothing and nobody reports "nothing happened". It is now in-band and
  scaffold-time.

Also corrected: code comments citing "ADR-0041 Q2" for the Codex fix used the
PR conversation's numbering, not the record's. The record's OQ2 is a different
question entirely, so the citation pointed at a decision the record did not
carry. The Codex call is now OQ3 in the record and the comments say `OQ3` —
a citation is only worth writing if it resolves.

**12. Round 4 — the detector was honest about its mechanism but not its
coverage.** Deviation §11 replaced an env-var heuristic with positive detection
of the clone-and-run shape and treated that as closing the silent-empty-scaffold
risk. The next frame-critique showed it closes a *slice* of it: the signal
detects a **topology** (jig source checkout), not the **condition** (no plugin
installed). Three populations reach the same empty scaffold and trip nothing —
an unzipped **release package** run directly (that tree is `hosts/claude`
repackaged, and `docs/adoption-readiness.md` names the zip as an acquisition
route peer to the marketplace), a hand-copied plugin tree, and a **cross-host**
run (`--host codex` from an installed Claude plugin).

The mechanism is the one §11 named, a third time and one level finer: the
population was again taken from the cases a reviewer had listed — the two README
recipes — rather than from the set of ways a user reaches the failing state.
Round 1 missed a population; round 2 used a mechanism that could not
discriminate; round 3 built a sound mechanism and then **overclaimed its
extent**. Recurring lesson: after fixing a detector, state what it does *not*
detect, in the same breath.

Fixed by scoping honestly rather than by adding heuristics — the reviewer's own
prescription, and the right one, since each extra heuristic would have widened
the same overclaim:

- `scaffolding_from_source_checkout()` documents the three shapes it misses, and
  that a quiet result is **not** proof jig will work.
- ADR-0041 OQ2 prices the residual; the kill criterion now states both limits —
  coverage (clone-and-run only) and audience (the note reaches the adopter's
  terminal, never jig, while the criterion is a population-level claim; by
  helping the user self-serve it further suppresses the reports channel).
- The floor table's ✅ rows carry their precondition (*iff the plugin is
  installed for the target host*), in the ADR and in `spec.md`.

Two flattenings corrected in the same pass. `permissions.deny` was marked ✅ for
in-repo without a host axis — **probed:** a `--host codex --in-repo` scaffold
writes no `settings.json` and no `permissions` at all, so Codex lacks ADR-0013
part 3 in *both* modes, a gap this slice does not introduce and does not close.
And "a set plugin-root variable positively proves a plugin host is driving" was
true for Claude and unsupported for Codex by this record's own argument; it is
now stated as suppression-in-the-safe-direction, not proof. (Corrected in the
code comment here; **the ADR's own copy of the claim survived this pass** and was
only removed in round 6 — see §14.)

Also tightened: `_is_jig_source_checkout` keyed on `hosts/` + `scripts/`, two
directory names common enough that an unrelated monorepo vendoring jig would
trip the walk-up. It now requires `scripts/build_host_packages.py`, a dev-only
builder the release zip deliberately excludes
(`install_contract.RELEASE_INCLUDE_SCRIPT_FILES` ships four files; not this one).

**13. Round 5 — the recurring lesson, finally stated at the right altitude:
correct the claim in the artifact the *user* reads, in the same pass.**

Rounds 1–4 each fixed a claim in the record and lagged one artifact behind:
§4 `product-vision.md`, §8 `learnings.md`, §12 `README.md` — and round 4 itself
scrupulously scoped the detector in its docstring, the ADR and the spec, while
leaving the **printed strings** carrying the overclaim it had just retracted.
The note told the user "not an installed plugin, so the project has jig's docs
but none of its runtime" — asserting the *condition* from a signal that only
establishes a *topology*, and telling a contributor with the plugin installed
that their project was broken, then advising the 79-file mode this ADR exists to
de-default. §12's lesson ("state what a detector does not detect") was right and
still insufficient: the docs are not where the claim lands.

The round also surfaced the better fix hiding behind the residual accounting.
The mode line prints **unconditionally**, so its wording binds every population
including the undetectable ones — and it asserted "jig runs from the installed
plugin", which for a plugin-less run is an *affirmative false statement*, worse
than the silence it replaced. Making that one sentence conditional costs nothing,
needs no detection, and covers exactly the residual OQ2 had priced as unclosable
pending a two-sided probe. **Pricing a risk as unclosable can hide the cheap
mitigation**: the reachable fix was wording, not machinery. The note is now a
nudge on top of a mode line that is true on its own.

Two smaller corrections in the same pass, both retracted-claim residue: the
kill criterion listed only false negatives and audience, omitting the
false-positive class that had killed the *previous* detector (now limit (b));
and "a set plugin-root variable positively proves a plugin host is driving" —
withdrawn in the code comment — still stood in a test docstring and in
`spec.md`/the sweep as "a probe that does not exist", which OQ2 had already
narrowed to "considered and declined to pay for". (This entry originally claimed
the withdrawal covered the ADR too. It did not; see §14.)

**14. Round 6 — the deviation log asserted a disposition the work did not have.**

§12 and §13 both recorded "a set plugin-root variable positively proves a plugin
host is driving" as withdrawn **in the ADR**. It was withdrawn in the code
comment, the test docstring, and `spec.md` — but the ADR's own copy survived,
leaving OQ2 self-contradictory six lines apart: it argued `PLUGIN_ROOT` is
undocumented for skill subprocesses on Codex, then justified the override by
saying the variable *proves* a plugin host is driving. The log did not merely
lag the fix; it claimed the fix.

**Root cause, and it is mechanical, not judgement.** The round-4 edit applied the
correction with a `str.replace()` whose target string did not match (a line-wrap
difference), and **without asserting the target was present** — so it silently
no-opped while a similarly-worded passage elsewhere in the same file was fixed,
making the edit look successful. Every other correction in that pass asserted
first and therefore landed. This is the same family as §8's glob-level sweep rows
— a disposition recorded from intent rather than from the resulting file — but
the fix here is narrower and mechanical: **assert the target exists before
replacing, and grep for the retracted claim afterwards**, in the file you just
edited. §13's lesson (correct the claim where the user reads it) was necessary;
this adds that you must then *verify* it is gone rather than trust the edit.

Also corrected in this pass: ADR Context and Consequences still credited the
advisory *note* with naming both exits. Round 5 moved that to the unconditional
mode line, which is the stronger placement precisely because it reaches the
populations no detector catches. Stale attribution, the inverse of §13's finding
— there the record was corrected and the strings lagged; here the strings were
corrected and the record lagged.

**Recorded because it is now load-bearing in the frame's favour:** the population
claim at the heart of this ADR — that the modal caller has the plugin installed —
remains *asserted*, not probed, and is deliberately absent from the `##
Assumptions` list. It stays unprobed because after round 5 it is **no longer
load-bearing**: the mode line is unconditional and true for every population, so
if the claim is wrong the cost is one truthful sentence and a re-run with a flag,
not misdirected work. That is the actual reason five rounds of critique converged
— not that the population was finally established, but that the design stopped
depending on it.

**15. Round 6 (PASS) — two residues fixed rather than logged.**

The frame-critique passed: the load-bearing assumption has been made
non-load-bearing by design, ADR ↔ spec ↔ slice ↔ code ↔ tests agree. Two
below-the-frame residues were offered as "record, don't block". Both were
one-line fixes in the same defect family this slice has been chasing, so they
were fixed:

- `scripts/verify_install.py` printed "machinery lives in the installed plugin"
  on the plugin-mode, no-checks branch — the *same* unconditional assertion about
  the user's machine that §13 removed from the mode line, surviving in a file
  whose comments the sweep had already touched. Now states where the machinery is
  *expected to come from*. (Pre-existing to this slice, from 048-06; fixed here
  because leaving it would have re-seeded the exact claim the slice retracted.)
- The mode line's recovery advice, "re-run with `--in-repo`", was one flag short
  of executable: the directory is scaffolded by then, so a re-run hits
  `AlreadyScaffoldedError`. It now names `migrate.py copy-machinery` — the
  designed conversion route for an existing project — and notes that re-running
  the scaffold needs `--in-repo --force`. Advice that does not run is a smaller
  version of the same problem as prose that is not true.

**16. Round 7 — compliance and craft, and the artifact that had drifted was the
skill's own contract.**

Both passes returned `needs-changes` and converged on the same finding from
different directions: `skills/scaffold-init/SKILL.md`'s Output section listed
what plugin mode produces and **omitted `.claude/settings.json`** — the file the
OQ1 fold-in had made the default path write, carrying the ADR-0013
destructive-command floor. The contract understated a security-relevant artifact
of its own default path.

That is §13's lesson again ("correct the claim where the user reads it"), and it
landed in the most-read artifact of all: the skill description is what the host
loads every session. Two rounds of frame critique, a compliance pass and a craft
pass all read past it, because everyone was looking at `scaffold.py`.

It is also the same AC the compliance pass flagged as the **only one with no
test fixture**, contrary to the DoD. Those two facts are one fact: AC #4 was
prose-only, so nothing could fail when the prose went stale. Now pinned by
`test_skill_md_documents_the_machinery_axis`, which asserts the Output section
names `settings.json` and does not claim the old default. **Where an AC is
satisfied by prose, the fixture is a grep — cheap, and the only thing that
notices when the prose stops being true.**

Other findings, all applied:

- **A `--force` that defeated its own test.** `test_default_mode_permissions_
  write_preserves_user_settings` passed `--force`, which also overrides the
  unmanaged-hooks refusal — so the test could not prove the property
  `_write_permissions_deny_floor`'s docstring claims ("plugin mode stays
  refusal-free"). Dropped; the test now proves it.
- **A class docstring contradicting the first test inside it.** `DefaultPluginModeTests`
  still said plugin mode writes no `settings.json`, three lines above a test
  asserting it does.
- **Comment archaeology.** ~110 lines of prose in `scaffold.py` had accumulated,
  including a verbatim third copy of deviation §11–§13 and contrasts against
  strings that no longer exist. The repo's house style is comment-heavy but
  cites slices and ADRs, not *review rounds* — no reader can resolve "round 2".
  Scope and limits kept (a caller genuinely must know what the detector misses);
  history reduced to an ADR pointer.
- Stale `(Proposed)` for ADR-0041 in spec live prose; `verify_install.py`
  repeating the retracted "machinery lives in the installed plugin"; a seed
  template asserting the same machine fact; a bare local literal where every
  sibling mode-varying value is a named constant; and three tests pinning one
  fact in `test_symmetric_install_docs.py`.

**Known and left open**, recorded rather than quietly carried: `migrate.py
copy-machinery` — which the mode line now recommends as the recovery route —
neither flips `scaffold.json`'s `scaffold_mode` to `in-repo` nor re-renders the
already-emitted docs, so a converted project ends with working machinery under
`.claude/skills/` and a manifest and `docs/workflow.md` still describing plugin
mode. §15 fixed "advice that does not run"; this is the residual "advice that
runs but leaves the project inconsistent". It needed its own record rather than
a widening of this slice, and now has one: **bug 018**, filed in
[#145](https://github.com/ramboz/jig/pull/145). Note the record lives on that
branch, **not this one** — `main` is PR-only, so a bug filed mid-slice cannot
appear in this tree. Stated explicitly because "filed" is otherwise
unverifiable from here, which is the same unverifiable-disposition problem
§8 and §14 name.

**17. Round 8 — the fix for the understated security artifact created an
overstated one on the other host.**

§16 corrected `SKILL.md`'s Output section, which had omitted the
`settings.json` carrying the ADR-0013 deny floor. That correction named the
host: *"Claude host only; Codex has no equivalent project-scoped permission
surface."*

`SKILL.md` bodies are **machine-translated per host**. `_rewrite_host_paths`
replaces `Claude` → `Codex` and `.claude/` → `.codex/` wholesale, so the shipped
Codex contract read:

> `.codex/settings.json` — permissions only: the ADR-0013 destructive-command
> deny floor … **Codex host only; Codex has no equivalent project-scoped
> permission surface.**

Self-contradictory, and worse than the bug it replaced: it *promises* a Codex
project the destructive-command floor that `scaffold()` never writes there
(`_write_permissions_deny_floor` is gated `host == "claude"`). The same sentence
also mis-stated the in-repo side — Codex registers hooks in `.codex/hooks.json`,
not a settings file. Both compliance and craft caught it independently, in the
artifact the host loads every session.

**The rule this makes concrete:** in a machine-translated body, a host named
inside a *conditional* does not merely leak — it **inverts**. `docs/conventions.md`
already required host-neutrality; this is the first case where breaking it
produced a false *factual* claim rather than a stylistic wart, and a
security-shaped one. Fixed by removing host names *and* host-specific paths from
the conditional: the bullet now says "a project-scoped permissions file, on
hosts that provide one", points at `scaffold.json` for what a given project
actually got, and carries a note explaining why it is worded that way — so the
next editor does not "improve" it by naming the host again.

**The fixture gap that let it ship**, which is the more useful lesson:
`test_skill_md_documents_the_machinery_axis` asserted against the **source**
`SKILL.md`, where the sentence read fine. Nothing asserted the *rendered* text.
Added `test_skill_md_output_survives_the_codex_translation`, pinned against the
**shipped** `hosts/codex/.../SKILL.md` rather than a re-render, so it also fails
if the host build goes stale. Verified to have teeth: restoring the wording that
shipped turns it red. **Where source is transformed before shipping, a test on
the source is not a test of the contract.**

Two nits folded in: `--plugin-only`'s `--help` still described the pre-OQ1 path
(docs + primer only), and `_write_permissions_deny_floor` had grown a
byte-identical read/parse/raise block — including the error string — alongside
`_check_hooks_safety`; both now share `_read_settings_json`.

**18. Round 9 — the status board asserted the retracted claim, in the one file
built to be read instead of the spec.**

Compliance round 3 found `docs/specs/README.md`'s Notes cell still saying the
`permissions.deny` gap was "deliberately out of scope — ADR-0041 Open
questions". OQ1 closed that; `_write_permissions_deny_floor` implements it;
`spec.md` says "Pulled INTO scope". The board said otherwise.

The Notes column exists precisely so a reader can skip the spec — which is what
makes a stale claim there cost more than the same claim buried in a slice. And
the sweep row for that file read `updated`, honestly, because it *was* updated
by this slice; it just was not updated *enough*. **A disposition of `updated` is
not a claim that the file is now correct** — that is the §8 lesson at one more
remove, and the third distinct artifact this slice has had to chase the same
retracted claim through (`product-vision.md` §4, `learnings.md` §8, `README.md`
§12, the printed strings §13, the Codex render §17, now the status board).

The corrected cell also carries the host asymmetry, which the board had never
stated: `permissions.deny` is Claude-only in **both** modes, because Codex has
no project-scoped permission surface. A reader who only ever sees the board
would otherwise infer the floor is universal.

Also corrected: §16 still read "It needs its own record", with no pointer, and
bug 018 lives on [#145](https://github.com/ramboz/jig/pull/145) rather than in
this tree (`main` is PR-only, so a bug filed mid-slice *cannot* appear here).
Now stated explicitly — "filed" is otherwise unverifiable from this branch,
which is the same problem in a new costume.

**Carried forward, not fixed here — and this entry was itself wrong on its
first writing, which is worth leaving visible.** It claimed
`verify_install.py`'s `run_completion_summary` "runs **zero** checks in plugin
mode". Compliance round 4 falsified that by probing: a greenfield plugin-mode
scaffold reports `1/1 checks passed`, because the `seed` check is appended
whenever `seed_expected` is true, which is the modal new project. The
`if not checks` branch fires only for plugin-only **and** non-greenfield.

I wrote a gap-report from reading the gate rather than running the command —
the exact move this slice's deviation log keeps faulting elsewhere. Corrected
rather than quietly deleted, because an over-claimed gap and an over-claimed
guarantee are the same failure.

The real gap is narrower: the **floor** checks — `permissions-deny` and
`gitignore-floor` — live in `_SCAFFOLD_CHECKS`, which is gated on
`with_machinery`, while both artifacts are now written in plugin mode. Probed:
a default scaffold produces `.claude/settings.json` and two `jig
secret-ignore` blocks in `.gitignore`, and neither is verified. Note the
`.gitignore` half is **not** new — it has been written on the plugin-only path
since 052-02, so this predates the OQ1 fold-in and is not a gap this slice
opened. Left out because widening the completion report's check set is a
behaviour change no AC asks for.

**19. Round 9 craft — PASS, with the sweep's blind spot named: the test suite's
own prose.**

Nits applied: an orientation comment that pointed "above" at constants sitting
below it; an assertion in the source-checkout note test that held whether or not
the note fired (it pinned a mode-line string, implying the note offers the
`--in-repo` remedy, which it does not — it points at the mode line); a remedy
that named a bare `migrate.py` with a placeholder disagreeing with migrate's own
canonical `<project-dir>`; and a `SKILL.md` note whose first sentence was
authoring guidance for a future editor, shipped in an artifact the host loads
every session — its enforcement lives in a test and its rationale in §17, so
only the runtime-useful half stays.

The finding worth carrying: **the reconciliation sweep never reaches the test
suite's own prose.** `PluginOnlyOptOutTests` and its section banner still framed
`--plugin-only` as an *opt-out* from an in-repo default — true under 016-03,
false the moment 099-01 flipped the default back, at which point the flag opts
out of nothing. The in-body comments had been updated; the class name, docstring
and banner had not. Same class as the `migrate/SKILL.md` "default since slice
016-03" row already in the sweep table, but the sweep table enumerates *docs*,
and a stale name in a test file is doc-truth too — arguably worse, since the
name is what the next contributor reads first. Renamed to `PluginOnlyFlagTests`,
docstring re-framed to say what it is relative to now and what did not change.

**Deferred with rationale**, so a later slice picks it up instead of
re-discovering it: `rewrite_skill_md_paths` is named for an artifact while its
sibling `rewrite_doc_paths_plugin_mode` is named for a mode, and at the call
site both are the doc rewrite. Not renamed here — `rewrite_skill_md_paths` is a
pre-existing public override of `ClaudeScaffoldRenderer`'s classmethod,
referenced from `scripts/build_codex_plugin.py` and ADR-0038, so the rename is
cross-cutting and does not belong in a slice about a default flag.

**20. Round 10 — the gap-report I wrote to be honest about a gap was itself
over-claimed.**

§18 stated `verify_install.py`'s completion summary "runs **zero** checks in
plugin mode" and therefore "verifies nothing" on the new default path.
Compliance round 4 falsified it by *running the command*: a greenfield
plugin-mode scaffold prints `1/1 checks passed`, because the `seed` check is
appended whenever `seed_expected` is true — the modal new project. The silent
branch fires only for plugin-only **and** non-greenfield.

I had read the `with_machinery` gate and reported from it, without running the
thing. That is the same move this log faults elsewhere — §14's "verify the edit
landed, don't trust the echo", §11's directional probing — arriving this time in
a *deviation entry*, the artifact whose entire job is to be the honest account.
**An over-claimed gap and an over-claimed guarantee are the same failure**, and
a wrong gap-report is the more insidious of the two because it reads as candour.
Corrected in place rather than deleted, so the correction is visible.

The real gap is narrower and now stated as such: the two **floor** checks
(`permissions-deny`, `gitignore-floor`) sit inside the `with_machinery`-gated
`_SCAFFOLD_CHECKS` while both artifacts are written in plugin mode — and the
`.gitignore` half has been written on that path since **052-02**, so this
predates the OQ1 fold-in and is not a gap this slice opened.

Also corrected: the `docs/refinement-todo.md` sweep row still said "no decision
was deferred", while §18 deferred a completion-report change and §19 deferred
the renderer rename. Both lived only in a closing slice's deviation log — the
same undiscoverability that filing bug 018 fixed for §16. Three entries are now
in `refinement-todo.md`, each with a resolution trigger; the third (the seed
template's `.claude/` leak) is written to **re-probe first**, since bug 015's
pre-substitution fix may already cover it and the observation predates that
merge. A deferral that asserts a symptom it has not re-checked is how this log
got into trouble in the first place.

Last stale framing: `DefaultOffMachineryTests`' docstring still called plugin
mode "the dormant copy path". It was 016-01's default, dormant under 016-03, and
is the default again — §19's lesson (the sweep does not reach the test suite's
own prose) one class further down the same file.

**21. Round 11 — the Q2 fix was a no-op on the only path that ships.**

OQ3 was recorded RESOLVED, the ADR claimed "the two hosts end up symmetric", and
every Codex test passed. All of it was true *of the source tree*, and false of
the shipped plugin.

`build_codex_plugin.py` pre-rewrote the packaged `templates/**/*.md.template`
through the **in-repo** transform at build time. `scaffold()`'s mode gate keys on
`${CLAUDE_PLUGIN_ROOT}/skills/` — already gone from a pre-rewritten template — so
the gate matched nothing and the project-local shape survived. **Probed:** a
plugin-mode scaffold run from `hosts/codex/plugins/jig/` emits
`docs/workflow.md` citing `${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-*` while
`.codex/skills/` is absent — precisely the defect §7 recorded and OQ3 claimed
closed, still live on the one path a real Codex user takes.

The Claude package does not have this problem because it ships templates
**canonical** and lets `scaffold()` transform them per mode. The Codex build was
transforming them *twice* — once at build time (mode-blind, and therefore wrong)
and again in `_copy_codex_templates` at scaffold time (mode-aware, and correct).
Fix: drop the build-time rewrite. The transform is not lost, it moves to where it
can tell the modes apart.

**This is the third instance in one slice of the same shape:** source is
transformed before shipping, so a test on the source is not a test of the
contract. §13 found it in the printed strings, §17 in `SKILL.md` bodies, and now
§21 in `templates/`. Each time the source read correctly. Each time the fixture
had to move to the shipped artifact to have teeth — `test_codex_docs_correct_
when_scaffolded_from_the_shipped_package` scaffolds from
`hosts/codex/plugins/jig/` in both modes and asserts the cited tree matches the
tree actually created. Verified red against the packaging that shipped.

**The generalisable rule, now earned rather than asserted:** wherever a build
step rewrites an artifact, the *build output* is the contract. A test that reads
the repo copy is testing an intermediate. Everything jig ships to Codex goes
through such a step, so this will keep recurring until Codex fixtures default to
the package.

**22. The AC #4 fixture was itself vacuous — the fixture added to close a
vacuous-coverage finding.**

§16 added `test_skill_md_documents_the_machinery_axis` because AC #4 was the one
AC with no fixture, and prose-only ACs cannot fail. The test asserted
`--in-repo` appears in `SKILL.md` — which the invocation example already
guarantees, several sections above the question it was meant to pin. Deleting
the entire sixth Q&A question left the test green. It pinned the Output half of
AC #4 properly and the question half not at all.

Now asserts the question's own heading (`^6\. \*\*Machinery vs. plugin\*\*`),
that it states what it asks, and which way skipping resolves. Verified by
deleting the question: red, then green on restore — the check §16 itself
prescribed ("would this still pass if the feature were deleted?") and did not
run on its own work.

Worth stating because it is the sharper version of §16's lesson: **a fixture
added to close a coverage gap needs the vacuity check more than ordinary tests
do**, because it is written to satisfy a finding rather than to express a
belief about behaviour, and "it passes" is precisely the outcome that makes it
look finished.

### Reconciliation sweep

| Artifact | Disposition | Rationale |
|----------|-------------|-----------|
| `README.md` | `updated` | **Round-3 correction — the earlier `no-op` was wrong.** Its rationale ("install docs point at the plugin") held for 2 of the 4 recipes; the other two are `git clone … && python3 …/scaffold.py <project>` with no plugin at all. Under the old default those recipes *were* the install; the flip silently emptied them. Both now pass `--in-repo` and are labelled self-contained, plus a note contrasting the two families. Grepping for `--with-machinery`/`scaffold_mode` missed it because the file states the premise by *demonstrating* it — the same class of miss as deviations §4/§8, a third time. |
| `docs/specs/README.md` | `updated` | Regenerated by `workflow.py status-board`; Notes column carries the reversal, the both-hosts scope, the `scaffold()`-default-in-step invariant, the `--in-repo` test contract, and the `permissions.deny` gap. |
| `docs/product-vision.md` | `updated` | **Two edits.** Dated amendment under the 2026-05 positioning-recovery history, *and* standing **principle #7** rewritten — it asserted scaffolded mode as the default (caught in review round 1; the file had been half-updated). |
| `docs/philosophy.md` | `updated` | "Own the scaffolding; don't rent the plugin" principle re-premised on the opt-in (caught in review round 1; absent from the original sweep table). |
| `docs/architecture.md` | `no-op` | Checked: no module-boundary or public-contract drift. No new module, no changed helper seam — the change is one argparse default plus a print. |
| Primer surfaces: `CLAUDE.md` / `AGENTS.md` / scaffold templates | `updated` | `CLAUDE.md` Active-specs entry names spec 099 + ADR-0041. Scaffold seed templates (`001-adopt-jig` spec + slice) corrected — they claimed `.claude/` machinery every new project now may not have. |
| `skills/scaffold-init/SKILL.md` | `updated` | The sixth Q&A question + invocation example (AC #4), **and** the Output section — which round-5 review found still listed plugin mode's artifacts *without* `.claude/settings.json`, months after OQ1 made the default path write it. A skill contract that understates a security-relevant artifact is worse than one that omits the topic. Now pinned by `test_skill_md_documents_the_machinery_axis`; AC #4 previously had no fixture, contrary to the DoD. |
| `docs/adoption-readiness.md` | `updated` | Names `--in-repo`, a flag that did not exist before this slice. Absent from the first sweep table entirely — the mirror of §8, where a row over-claimed; here an updated file had no row at all. |
| `scripts/verify_install.py` | `updated` | Two things: the plugin-only completion line asserted "machinery lives in the installed plugin" (the same unconditional machine-fact claim §13 removed from the mode line), and its docstring repeated it. Both now say *expected to come from*. |
| `scripts/test_symmetric_install_docs.py` | `updated` | The two README scaffold recipes now pin `--in-repo` (see the `README.md` row). A third test asserting the same fact was removed as redundant; the rationale moved onto the two assertions that already pinned it. |
| `skills/migrate/SKILL.md` | `updated` | "(default since slice 016-03)" was a stale default claim in a skill contract; now names `--in-repo` as the opt-in and bounds 016-03→099-01 as the interval it *was* the default. Mirrored in both packaged copies. |
| `docs/inbox.md` | `no-op` | Checked: no parked item resolved or contradicted by this slice. |
| `docs/refinement-todo.md` | `updated` | Three deferrals from this slice now have entries, because a deferral recorded only in a closing slice's deviation log is undiscoverable — the same problem filing bug 018 fixed for §16: the plugin-mode floor-check gap (§18), the `rewrite_skill_md_paths` naming asymmetry (§19), and the seed template's `.claude/` host leak. Previously marked `no-op` on the rationale that nothing was deferred *into* refinement-todo, which was true of the first sweep and false by §18. One WAS deferred out of it, and now has a record rather than a claim: the `migrate.py copy-machinery` gap §16 named is filed as **bug 018** ([#145](https://github.com/ramboz/jig/pull/145)) — round-2 compliance correctly flagged that §16 said "needs its own record" while no record existed, the same disposition-asserted-from-intent defect as §8/§14. The open questions live in ADR-0041 (§Open questions), which is their proper home. Of the three, OQ1 and OQ3 are now RESOLVED and implemented here; only OQ2 (a *detected* default) stays open — it needs a two-sided plugin-presence probe that jig **considered and declined to pay for** (path fragility across scopes), not one that cannot be built; OQ2 retracts the earlier "does not exist" wording. |
| `docs/memory/glossary.md` | `updated` | "Scaffolded install / scaffold mode" entry re-premised: opt-in, the four reasons plugin mode is the default, and when to choose in-repo. |
| `docs/memory/learnings.md` | `updated` | "Scaffold doc templates render into two install shapes" gotcha said "the default in-repo scaffold"; now names plugin mode as the default and bounds in-repo to the 016-03→099-01 interval. Missed in the first sweep — see deviation §8. |
| `docs/decisions/README.md` / ADR index | `updated` | ADR-0041 added to the index. Index row and ordering re-resolved after the merge with `main` (ADR-0039/spec 096 landed there meanwhile); both conflicts were additive, so both sides were kept and numeric order restored **by hand** — regenerating via `adr.py index` overwrites the hand-written ADR-0041 summary with the record's first sentence. |
| `hosts/claude/**`, `hosts/codex/**` | `updated` | Rebuilt via `scripts/build_host_packages.py`; drift guard clean. Verified both packaged `scaffold.py` + `SKILL.md` carry the change. |
