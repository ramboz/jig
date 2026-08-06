---
status: DONE
tier: standard
severity: medium
claimed_by: claude/bug-023-advisory-host
regression_test: skills/migrate/test_migrate.py::CrossHostAdvisoryTests
main_repro_checked_at: 2026-07-30
main_repro_ref: base claude/bug-018-close-out@5087ff6 (origin/main@af8184c predates it)
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at: 2026-07-30
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 023: copy-machinery-advisory-host-from-invocation

## Symptom

`migrate.py copy-machinery` converts a plugin-mode project to in-repo and then
warns about the project docs that still cite the now-unset plugin-root
variable (bug 018, half two). It picks the variable to look for from the
**invocation** host — `_resolve_host()`, which infers the host from where
`migrate.py` itself lives, or from `--host`.

The project already records the answer. `scaffold.py` writes `host_renderer`
into `scaffold.json` at scaffold time (`_scaffold_manifest`), naming the
renderer that actually produced the docs.

So when the two disagree — a Codex-installed helper run against a
Claude-scaffolded project, or the reverse — the scan looks for a token those
docs never contained, finds nothing, and prints nothing. The manifest flip
still happens, so the run reports success while the docs half is silently
skipped. That is bug 018's own reported failure mode, one layer over: the
advisory the SKILL.md promises the user does not appear, and nothing says so.

## Repro

Claude-scaffolded plugin-mode project, Codex-host invocation:

```
python3 skills/scaffold-init/scaffold.py --no-tests --host claude --plugin-only proj
python3 skills/migrate/migrate.py copy-machinery proj --host codex
```

Observed (exit 0):

```
copied machinery into proj/.codex
scaffold_mode: plugin-only -> in-repo
```

`proj/scaffold.json` says `host_renderer: claude`, and `proj/docs/workflow.md`
still contains 4 `${CLAUDE_PLUGIN_ROOT}` citations. No advisory.

Control — same fixture, matching invocation (`--host claude`) — fires
correctly:

```
warning: 2 file(s) still cite ${CLAUDE_PLUGIN_ROOT}, which is unset in a project that now owns its machinery:
  - docs/decisions/lightweight-decisions.md (1)
  - docs/workflow.md (4)
```

Mirror direction reproduces too: `--host codex --plugin-only` scaffold,
`copy-machinery --host claude` → silence, with 4 `${PLUGIN_ROOT}` citations
left in `docs/workflow.md`.

## Evidence

- `skills/migrate/migrate.py:2058` — `resolved_host = _resolve_host(host)`.
- `skills/migrate/migrate.py:2119-2123` — the advisory's token and offered
  replacement are both derived from `resolved_host`.
- `skills/migrate/migrate.py:50-61` — `_infer_host_from_runtime()` reads the
  helper's **own** path (`.codex/skills/...` → codex), i.e. a property of the
  installation, not of the target project.
- `skills/scaffold-init/scaffold.py:2680` — `manifest["host_renderer"] = host`,
  written once at scaffold time and never rewritten by `copy-machinery`.
- Repro above: manifest `host_renderer: claude`, invocation host `codex`, 4
  stale Claude citations on disk, empty advisory.

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. Any Markdown
     list works (-, *, +, or 1.); the gate counts top-level items only
     (indented sub-bullets are notes, not hypotheses). -->
- [ ] H1: the scan's scope is wrong — the configured docs root or the skip-dir
  pruning drops `docs/workflow.md` on this fixture. Falsify by running the
  *same* project with a matching `--host claude`: if the file is named there,
  scope is fine and the host is the variable. **FALSIFIED** — the control run
  names `docs/workflow.md (4)`.
- [ ] H2: the renderers' tokens overlap, so detection should have matched
  regardless of which host was resolved. Falsify by grepping a Claude-rendered
  `docs/workflow.md` for a standalone `${PLUGIN_ROOT}`. **FALSIFIED** — the
  Claude render carries only `${CLAUDE_PLUGIN_ROOT}`; `CodexScaffoldRenderer`
  rewrites it to `${PLUGIN_ROOT}`, and bug 018's own premise guard
  (`test_baseline_codex_docs_cite_the_codex_plugin_root`) pins that the two
  are disjoint.
- [x] H3 (leading): the advisory asks the wrong source. The token describes
  **the project's rendered docs**, but it is resolved from the invocation.
  Confirm by scaffolding `--host claude --plugin-only` and invoking
  `copy-machinery --host codex`: the manifest flips, the docs keep their
  Claude citations, and the advisory prints nothing. **CONFIRMED** — see
  `## Repro`.

## Root cause

`copy_machinery` answers two different questions from one variable.

1. *Where does the machinery go?* — a property of **this invocation**. The
   invocation host is the right source, and it is used correctly
   (`scaffold_mod.copy_machinery(..., host=resolved_host)`, and the
   `.claude`/`.codex` runtime dir named in the summary).
2. *What variable do this project's docs cite?* — a property of **the
   project**, decided when its docs were rendered. The invocation cannot know
   this; `scaffold.json`'s `host_renderer` records it. (Precisely: the field
   records the host the manifest was written for. For a scaffolded project
   that *is* the renderer that produced the docs. For one adopted via
   `adopt-layout` the docs are user-authored and no renderer produced them —
   there is nothing better to read, and the field is still the project's own
   claim rather than a passing helper's. `read_host_renderer`'s docstring
   carries the same caveat.)

`resolved_host` is fed to both. When the two hosts agree — the overwhelmingly
common case, and every case bug 018's tests cover — the wrong source returns
the right answer, so the defect is invisible. It surfaces only when they
disagree, and then it fails silently, because "no stale citations" and "I
searched for a string these docs could never contain" produce identical
output.

Same class as bug 018: a read that goes to a plausible-looking source instead
of the authoritative one. Bug 018's fix moved the *spellings* to their
authoritative source (the renderer). It left the *host selection* pointing at
the invocation.

## Fix class

structural_fix

## Fix

Split the two questions and give each its own source.

- `scaffold.py` gains `read_host_renderer(target)` — the read accessor for the
  `host_renderer` field, shaped like its siblings `read_scaffold_mode` and
  `read_installed_tiers` (same manifest, same degrade-to-`None`-on-anything-
  unreadable contract). It returns `None` for a project with no manifest, an
  unreadable one, a missing or wrong-typed field, or a host no renderer exists
  for — so a malformed manifest can never fail a copy that already succeeded.
- `migrate.copy_machinery` resolves an **advisory host** =
  `read_host_renderer(project_dir) or resolved_host`, and scans with that
  host's token. The invocation host is unchanged everywhere else.
- The offered in-repo replacement path keeps coming from the **invocation**
  host, deliberately: after `--host codex` the skills are under
  `<proj>/.codex/skills/`, and `<proj>/.claude/skills/` does not exist. Naming
  the project host's path there would print a directory that is not on disk —
  swapping one false statement for another.

So the warning reads correctly in both halves: *your docs cite `X`* (the
project's renderer said so) and *the in-repo form is `Y`* (this run put the
machinery there).

Two more deliverables came out of the review passes (full narrative in
`## Proof`):

- `skills/migrate/SKILL.md`'s advisory section documents the split, and it
  must stay **free of host-specific spellings** — host names, runtime
  directories, and host variables alike. `build_codex_plugin.py` rewrites
  Claude spellings to Codex ones, so a host named inside a cross-host
  contrast inverts into a self-contradiction in the shipped Codex package;
  and a *Codex* spelling typed into the source is not rewritten at all, so it
  ships verbatim to Claude readers. The section now says "one host" / "the
  other" and carries an editor warning **inside** it (host-neutral, so it
  obeys its own rule and the guard covers it).
  `test_codex_render_of_the_split_does_not_invert` pins both directions:
  an absence check whose forbidden set is **parsed out of the builder**
  (`host_specific_spellings()` — both sides of each single-line substitution
  pair, compared case-insensitively, plus the bare host names as a floor
  against a partial builder restructure), and section identity on top for
  anything the builder
  rewrites that is not a bare literal. Neither half alone is sufficient; the
  guard took four attempts to get there, and `## Proof` records what each of
  the three weaker versions let through.
- `docs/refinement-todo.md` gains a tracked home for
  `renderer_for_host`'s unknown-host fallback to Claude. `read_host_renderer`
  deliberately does *not* ride that default and cites it as open, so the
  question needed somewhere to live other than a closed bug-018 review file.

## Already tried

Nothing discarded. H1 and H2 were falsified by the control runs recorded under
`## Repro` / `## Hypotheses` before H3 was pursued.

## Deviations

Raised by the review passes and accepted deliberately; recorded here so a
later reader does not have to reconstruct them from the verdict files.

- **`main_repro_result: reproduces` does not describe `origin/main`.** The
  defect lives only in code PR [#150](https://github.com/ramboz/jig/pull/150)
  introduces, and this branch is based on that PR rather than on trunk. The
  repro was run on `origin/main@af8184c` and the advisory *fires* there —
  main's detection token is still a hard-coded Claude literal, so a
  Claude-rendered project matches whatever host the invocation names. Main is
  **pre-defect, not fixed**, and it carries the converse silence #150 fixes.
  `bug.py` accepts only `reproduces` / `resolved-on-main`, so there is no
  vocabulary for "introduced by an unlanded PR"; the caveat rides in
  `main_repro_ref` and in `## Main recheck`. The gate's intent — do not
  re-fix something already solved on trunk — is satisfied. A vocabulary
  follow-up on `VALID_MAIN_REPRO_RESULTS` belongs to `bug.py`, not here.
- **`docs/refinement-todo.md` gained an entry**, which is scope beyond the
  code fix. Justified: `read_host_renderer`'s docstring cites
  `renderer_for_host`'s unknown-host fallback as an open question, and it had
  no tracked home — it lived only in a closed bug-018 review file.
- **`_HOST_RENDERERS` is new structure in a bug-018 deliverable.** It exists
  so `read_host_renderer` can ask "is this a host we have a renderer for"
  without restating the host list; `renderer_for_host` reads the same
  registry, so this is one structure with two readers, not a second list. Its
  only behavioural delta is on an unhashable `host` (raises instead of
  defaulting) and is unreachable — every caller validates first.
- **The learning is applied only at the call site.** It says "when a helper
  takes a `host` argument, say whose it is". `_plugin_root_token` and
  `_in_repo_skill_path` still take a bare `host:` — deliberately, since they
  are genuinely host-generic and answer for whichever host they are handed.
  Knowingly partial.
- **The doc guard covers the advisory section only**, from its heading down —
  not the rest of `skills/migrate/SKILL.md`, which contains host literals
  throughout by design.
- **The learning was written during the fix rather than by `memory-sync` at
  reconciliation.** Content matches the record; the ordering is the
  deviation.
- **A bug-018 regression test was rewritten by this work.**
  `test_skill_documents_the_ask_before_editing_step` asserted against a fixed
  2000-character window and broke when this fix added ~450 characters above
  it. It now uses the shared `advisory_section()` helper, so its assertions
  are coupled to the section's content rather than its length. Touching
  another bug's regression test is a blast-radius event and belongs here, not
  only in the `## Proof` narrative. The test's intent is unchanged and its
  three assertions are untouched.
- **The editor warning ships into scaffolded user projects.**
  `copy-machinery` copies this SKILL.md, so the comment travels with it. It
  is host-neutral and states only the rule — the earlier draft also cited an
  internal test path, which means nothing in a user's repo and has been
  removed. A jig-maintenance note living in a user-facing file is a real if
  small cost, accepted so the warning sits where an editor is actually
  typing.
- **Cycle numbering.** `## Proof` narrates the work in cycles of *change*
  (code fix, then documentation cycles); the review passes ran more often
  than that. The verdict files under `docs/bugs/reviews/` are the per-pass
  record; `## Proof` groups by what changed, not by pass.
- **The doc guard's enforced scope is narrower than "nothing
  host-specific".** It bans exactly what `build_codex_plugin.py` names as a
  string literal — host names and the runtime directories, variables and
  filenames in its substitution table. Anything host-specific it does *not*
  name passes: `settings.json`, a vendor name, or a path one of the
  `scaffold.py` delegates rewrites behind a prefix. Deliberate: the forbidden
  set is derived from the translator, and extending it by hand would be
  attempt 3 again — the version attempt 4 replaced.
- **The empty-set assertion catches a total builder restructure, not a
  partial one.** If `build_codex_plugin.py`'s substitutions were folded into
  a table or a loop, the AST walk finds no string-literal pairs and the test
  fails loudly. If only *some* pairs moved, the set silently shrinks and the
  test still passes. A back-reference comment now sits in the builder so a
  refactor there is not a surprise landing in a migrate test.
- **`## Evidence` line numbers are as-of-diagnosis.** The fix moved the code
  it cites (`migrate.py:2058` is now ~2066, and so on). Left as the
  coordinates the diagnosis was made against rather than silently
  re-anchored to the post-fix tree.
- **The guard's history was mis-numbered, and the correction took three
  passes to finish.** `## Proof` originally collapsed two versions into one
  and then called "the middle attempt" a hand-written list, which matched
  neither; `docs/memory/learnings.md` carried a third, incompatible
  ordering. The corrections went:
  - **pass 6** found it; fixed `## Proof` and `learnings.md` — two sites;
  - **pass 7** found the old count still live in `## Fix` and in two
    docstrings in `skills/migrate/test_migrate.py` (`host_specific_spellings`
    and the guard's own). Those two matter most: they are the guard's
    explanation to whoever next changes it, sitting right next to the code
    they describe. (They do not ship — `test_*.py` is excluded from both host
    packages; an earlier draft of this bullet claimed otherwise and was
    wrong.)
  - **pass 8** found a sixth — in the scope bullet a few entries above this
    one, while this bullet was busy asserting every site now agreed.

  Six sites now agree, and `## Proof` is the single canonical statement the
  others point at rather than restate. Recorded as a correction, not an
  accepted departure: the lesson each version teaches was right; only the
  ordinals were wrong.

  The pattern is the point, and it is this bug's own defect class one more
  time: **a fact restated in six places gets corrected in two, then four,
  then six — and the last stale copy was in the log documenting the
  correction.** Restating beats referencing right up until the restatement
  drifts, which is exactly what `host_specific_spellings()` stopped doing to
  the builder's table.

## Regression test

`skills/migrate/test_migrate.py::CrossHostAdvisoryTests`

## Proof

**Red, witnessed before any production line changed** —
`CrossHostAdvisoryTests`: 4 failures + 7 errors.

Failures (the defect):

- `test_claude_project_is_scanned_with_the_claude_token_under_codex` —
  `'still cite' not found in 'copied machinery into .../proj/.codex\n
  scaffold_mode: plugin-only -> in-repo\n'`
- `test_codex_project_is_scanned_with_the_codex_token_under_claude` — same
  silence, mirror direction.
- `test_replacement_path_follows_the_invocation_host` — no advisory at all, so
  no replacement path to check.
- `test_stale_docs_are_still_not_rewritten_across_hosts` — its
  "advisory fired" precondition. Written without that precondition it passed
  on the buggy build for the wrong reason (nothing detected → nothing
  touched); the craft pass on bug 018 flagged exactly that shape, so it was
  added before the red run was recorded.

Errors (7): `read_host_renderer` did not exist yet —
`AttributeError: module '_scaffold_module_for_test' has no attribute
'read_host_renderer'` across `test_read_host_renderer_reports_what_the_
manifest_records` (1) and `test_read_host_renderer_returns_none_when_it_
cannot_answer` (6 — five `subTest` cases plus the no-manifest assertion after
the loop).

`red_confirmed_at: 2026-07-30` was stamped by the `→ FIXING` gate, which runs
the suite itself.

**Green (cycle 1)** — `CrossHostAdvisoryTests` 11 OK at this point; the
shipped-package guard that makes it 12 arrives in the next cycle. The three
bug-018 classes
(`PluginModeConversionTests`, `CodexPluginModeConversionTests`,
`CopyMachineryStaleScanScopeTests`) 28 OK, unchanged.

**End-to-end, all four host combinations** (project host × invocation host),
each exiting 0:

| project | invocation | searched for | offered |
|---|---|---|---|
| claude | codex | `${CLAUDE_PLUGIN_ROOT}` | `${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-<name>/` |
| codex | claude | `${PLUGIN_ROOT}` | `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` |
| claude | claude | `${CLAUDE_PLUGIN_ROOT}` | `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` |
| codex | codex | `${PLUGIN_ROOT}` | `${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-<name>/` |

Both mixed rows name 2 real files each; before the fix both printed nothing.
The two matching rows are byte-identical to their pre-fix output — the common
case is untouched.

### The documentation cycles — the review passes found this bug's own defect class, repeatedly, in this fix's docs

The code fix passed every pass from cycle 1 onward. What kept failing was the
**documentation** of it — and both times with the defect this bug is about: a
statement that reads correctly at its source and is false where it is
consumed.

`SKILL.md`'s new paragraph explained the split with a cross-host example
naming both hosts. `scripts/build_codex_plugin.py` rewrites every `Claude` to
`Codex` wholesale, so the shipped Codex package read:

> run a Codex-installed helper against a **Codex**-scaffolded project and each
> half still names something real

— contradicting the clause immediately before it, and erasing the only
scenario this bug exists for, for the audience it was written for. Zero
occurrences of `Claude` survive in that rendered file, so *any* phrasing with
a host literal inside the contrast was guaranteed to invert.

Precedent for the exact failure: `test_scaffold_mode.py::
test_skill_md_output_survives_the_codex_translation`, which pins a
host-conditional in scaffold-init's SKILL.md against the same substitution.

Fixed by phrasing the contrast host-neutrally ("a helper installed for one
host against a project scaffolded for the other") — no literal left for the
builder to rewrite — and witnessed red→green by a new test asserting the
**shipped** package: `test_codex_render_of_the_split_does_not_invert`.

The guard took **four** attempts, and each failure is the same mistake in a
smaller form. (An earlier draft of this record collapsed attempts 2 and 3
into one and then referred to "the middle attempt" as a hand-written list,
which described neither. Review pass 6 caught the contradiction; the
corrected sequence is below and `docs/memory/learnings.md` matches it.)

**Attempt 1 — ban the two sentences that failed.** Useless: every *other*
host-literal wording stays green ("installed for Claude against a project
scaffolded for Codex" renders "for Codex … for Codex" and matches no list).

**Attempt 2 — section identity**, source vs Codex render. Better, and it
covers Claude spellings nobody enumerated, because the section renders
differently the moment the build touches anything in it. But the translation
runs **one way**: `build_codex_plugin.py` rewrites Claude spellings to Codex
ones and never the reverse, so a *Codex* spelling typed into the source is
invisible to identity — both renders match — and ships verbatim to Claude
readers. The record claimed identity held "iff nothing in the section is
host-specific". That was false in exactly that direction.

**Attempt 3 — identity, plus a hand-written list for the blind direction:**
`("Codex", ".codex/", "CODEX_")`. This is the one worth naming. Restating
another module's spellings from memory is *precisely* the defect bug 018 was
filed for, reproduced inside the guard written to stop this bug's version of
it — and it failed the same way, letting `${PLUGIN_ROOT}`, `AGENTS.md`,
lowercase `--host codex` / `--host claude` (the builder is case-sensitive)
and unslashed `.codex` straight through. The Codex spellings the build
*produces* are exactly what such a list forgets, because those strings never
appear in the file you are looking at.

**Attempt 4 — ask the builder.** The forbidden set is now parsed out of
`build_codex_plugin.py` itself (`host_specific_spellings()`: an AST walk over
its string-literal `.replace()` calls, taking **both** sides of each
single-line pair — the Claude spelling it consumes *and* the Codex spelling
it produces; multi-line block edits are document surgery rather than
spellings and are skipped — precisely, any literal with an *interior*
newline; `.strip()` runs first, so a whole-line deletion survives into the
set, which is stricter than needed and never weaker). The comparison is
case-insensitive on both
sides, which is what catches lowercase `--host codex` in prose; the bare host
names are appended on top for a different reason — as a floor against a
*partial* builder restructure, where the `Claude`/`Codex` pairs move into a
table while others stay, so the parsed set shrinks without the empty-set
assertion noticing. Section identity stays on top of both, for anything the
builder rewrites that is not a bare literal (a regex substitution, a
sentence-level deletion, a future rule).

**What the guard enforces, exactly:** the host names, runtime directories,
and host variables that `build_codex_plugin.py` itself names as string
literals — the rule the editor comment states. **Not** "nothing
host-specific". Anything host-specific the builder does not name as a literal
passes both assertions and would ship to the other host's readers:

- a host-only *filename* (`settings.json`, which only one host has);
- a path the builder rewrites via a **delegate** rather than a literal —
  `scaffold.py`'s `rewrite_skill_override_guidance` and
  `finalize_codex_migrate_skill` own spellings the AST walk never sees, and
  where their rewrite is prefix-gated, section identity does not fire either;
- a vendor name.

That boundary is deliberate. The forbidden set is derived from the
translator, so it covers what the translator knows about; extending it to
arbitrary filenames, vendor names, or the delegates' tables would mean
hand-writing a list again — attempt 3, which is what this version replaced.
The editor comment states the wider rule in prose for the cases the machine
cannot check.

Mutation-checked. Every escape the review passes named is caught:
`${PLUGIN_ROOT}`, `AGENTS.md`, `--host codex`, `--host claude`, and `.codex`
without a trailing slash — all five of which **attempt 3** let through. Also
caught: the original inverted sentence (attempt 1 caught this one too, by
construction — it was the sentence attempt 1 banned) and a Claude literal
added elsewhere in the section (attempt 1 missed it; attempt 2 caught it).

An editor warning now sits **inside** the section, phrased with no host name,
so it obeys the rule it states and the guard covers it. The first version
named both hosts and shipped inverted — the very defect it was warning
about, two lines above the section it guarded — and cited an internal test
path that means nothing in a scaffolded user's repo (`copy-machinery` copies
this SKILL.md into their project). Both are gone.

Scope, stated precisely: the guard covers the advisory section only, from its
heading down — not the rest of `skills/migrate/SKILL.md`, which names hosts
throughout by design. Within that section its identity half *does* catch a
source edit that was never rebuilt, so it partially overlaps the drift guard;
it is not a general staleness check
(`scripts/test_build_host_packages.py::DriftCheckTests` owns that).

Adding that comment then broke a bug-018 test, and the *way* it broke is
worth recording: `test_skill_documents_the_ask_before_editing_step` asserted
against `body.split(marker)[1][:2000]` — a fixed character window, not the
section. Inserting ~450 characters near the top pushed its last phrase out of
the window, so it failed for a reason unrelated to what it checks. Class-only
runs did not show it; the full suite did. Fixed at the cause: the window is
now a real section boundary (`advisory_section()`, shared with the new
guard), so the assertions are coupled to the section's *content* rather than
its *length*.

Also from the craft passes across these two cycles: the call-site comment
trimmed from 22 lines to the asymmetry it has to protect, with the reasoning
moved into `_stale_docs_warning`'s own docstring (a callee's contract should
not require reading one caller's inline comment); the mirror-direction test
extended to pin the replacement half too — it checked only the token, so a
"fix" moving *both* halves to the project host would have stayed green;
`read_host_renderer` moved to sit with `read_scaffold_mode` /
`read_installed_tiers`, which deleted the two navigation paragraphs its
remote placement had needed; the section-extraction helper made
fence-aware and same-or-higher-level terminated, and given a named failure
when the heading is missing rather than a bare `ValueError`; and the
`renderer_for_host` unknown-host fallback given a tracked home in
`docs/refinement-todo.md` instead of being cited from a docstring as "open"
with nowhere to look.

### Suite

**Full suite** — `python3 scripts/run_tests.py`, exit code read from a
redirected file (never through a pipe):

| cycle | result | |
|---|---|---|
| 1 (code fix) | `Ran 3846 tests`, `OK (skipped=7)` | exit 0 — bug 018's 3835 plus this record's 11 |
| 2 (SKILL.md reworded, shipped-package guard added) | `Ran 3847 tests`, `OK (skipped=7)` | exit 0 |
| 3 (identity guard added, accessor moved) | `Ran 3847 tests` | **exit 1** — the fixed-window regression below |
| 3, after that fix | `Ran 3847 tests`, `OK (skipped=7)` | exit 0 |
| 4 (forbidden set parsed from the builder; comment reworded) | `Ran 3847 tests`, `OK (skipped=7)` | exit 0 — **the code as it now stands** |

The cycle-3 failure is recorded rather than quietly re-run: a green number
that replaced a red one without explanation is exactly the evidence this
workflow exists to prevent. No test count changes in cycle 4 — the guard was
strengthened in place, not added to.

Host packages rebuilt (`scripts/build_host_packages.py`) and committed in
sync; `CrossHostAdvisoryTests` 12 OK standalone, and the four
advisory-touching classes (`CrossHostAdvisoryTests`,
`PluginModeConversionTests`, `CodexPluginModeConversionTests`,
`CopyMachineryStaleScanScopeTests`) 40 OK together.

The suite's output contains `ERROR: committed host packages are stale…`. That
is *expected output* from `scripts/test_build_host_packages.py::DriftCheckTests`,
which induces drift in a temp tree on purpose to assert the message shape; the
exit code is 0 and it was read from a redirected file, not through a pipe (bug
018's `## Learning`).

## Learning

**A read whose source is "whatever variable is in scope" is a guess wearing a
variable's name.** `resolved_host` was in scope, correct for the copy, and
plausible for the advisory. Nothing at the call site distinguished "the host
running this command" from "the host that rendered these docs", so one name
served both and the second answer was right only by coincidence.

**Corollary: the same-host case is not coverage.** Bug 018 shipped 28 tests
across two hosts and every one of them scaffolded and invoked the same host,
so all 28 would have passed against a constant. A test that varies two inputs
together cannot tell you which one the code is reading.

**And this is the second recurrence in the same function.** Bug 018's own
recorded learning was "a caller widened a contract the callee was never told
about". Its fix moved the *spellings* to their authoritative source (the
renderer) and left the *host selection* pointing at the invocation — fixing
the value while leaving the question unasked. Writing the learning into the
record did not stop the next instance a few lines away, twice. What
generalises is not "check the renderer" but: **when a helper takes a `host`
argument, say in the signature or the comment whose host it is.**

## Main recheck

- 2026-07-30 - `base claude/bug-018-close-out@5087ff6 (origin/main@af8184c predates it)` -> reproduces: Ran the repro in a detached worktree at origin/main@af8184c: the advisory FIRES there, because main's detection token is still the hard-coded Claude literal, so a Claude-rendered project matches whatever host the invocation names. main is therefore not fixed, it is pre-defect: it predates PR #150, which made detection host-sourced and thereby exposed the invocation-vs-project host confusion. main DOES carry the converse silence (Codex project, Claude token) that #150 fixes. Same repro on this branch's base, claude/bug-018-close-out@5087ff6 (the code that will land): 'copied machinery into proj/.codex / scaffold_mode: plugin-only -> in-repo' and no advisory, with 4 stale CLAUDE_PLUGIN_ROOT citations left in proj/docs/workflow.md. Nothing on trunk to duplicate.
