---
status: DONE
tier: standard
severity: medium
regression_test: skills/tdd-loop/test_tdd.py::Bug021CustomCommandSelectorContractTests
main_repro_checked_at: 2026-08-31
main_repro_ref: origin/main@b45c762
main_repro_result: reproduces
red_confirmed_at: 2026-08-31
green_confirmed_at: 2026-08-31
fix_class: structural_fix
security_surface: false
escalated_to:
claimed_by: claude/bug-021-jig-ceremony-f88124
---

# Bug 021: custom-test-command-drops-selector

> Filed from a side-observation while fixing
> [bug 020](020-adr-index-summary-degradation.md) /
> [issue #140](https://github.com/ramboz/jig/issues/140) as a record only;
> diagnosed and fixed 2026-08-31.

## Symptom

`tdd.py run <target> --test <selector>` silently runs the **whole suite** when
the project uses a custom `.jig/test-command` whose command does not accept a
selector argument — which is jig's own configuration. Nothing reports that the
selector was dropped.

`bug.py transition <id> FIXING` then reads that whole-suite exit code as a
statement about the named regression test:

- **Red gate (`FIXING`)** — "the regression test fails without a fix, so it
  captures the bug". In fact **any** failure anywhere in the suite satisfies
  it. The gate stamps `red_confirmed_at` on evidence that may have nothing to
  do with the test.
- **Green gate (`REVIEWED`)** — requires the *whole suite* to pass. Stricter
  than intended, so not unsafe, but it makes the gate fail for unrelated
  reasons and pushes sessions toward the `JIG_BUG_TEST_GATE=0` escape.

Observed live on 2026-07-30 during bug 020: the FIXING transition passed while
the named regression test was already **green** (the fix was in place). The
non-zero exit came from `uvx pyright` flagging type errors in the new code.
The record was stamped with a red that the gate had not actually witnessed.

## Repro

In the jig repo itself (`.jig/test-command` is `python3 scripts/run_tests.py`):

```bash
# Pick any single passing test class. The selector is ignored — this runs all
# ~3700 tests, takes ~2 minutes, and never mentions the selector.
python3 skills/tdd-loop/tdd.py run . --test "skills/adr-workflow/test_adr.py::SomeClass" < /dev/null

# Confirm what actually got spawned (from another shell while it runs):
ps -o command= -p $(pgrep -f run_tests.py | head -1)
# → python3 scripts/run_tests.py skills/adr-workflow/test_adr.py::SomeClass
#   ...the argument is present and ignored.
```

Gate consequence: with a green regression test and any unrelated failure in the
suite, `bug.py transition <id> FIXING` succeeds and stamps `red_confirmed_at`.

## Evidence

Three sites, verified on `origin/main@af8184c` and re-verified on
`origin/main@b45c762` (2026-08-31, this session — line numbers unchanged):

- `skills/tdd-loop/tdd.py:363` — the custom-command branch appends the selector
  unconditionally: `argv = [*argv, test_selector]`. There is no check that the
  command supports one, and no warning when it cannot be honored.
- `scripts/run_tests.py:162` — `main()` takes no arguments and never reads
  `sys.argv`; it always builds the full suite. The appended selector is
  discarded without an error.
- `skills/bug-fix/bug.py:582` (`_run_tdd`) and `:690` — the transition gates
  interpret the resulting exit code as a verdict on the *named* test.

`skills/tdd-loop/SKILL.md` documents `.jig/test-command` as "the exact command
to run" and names `python3 scripts/run_tests.py` (jig itself) as the example.
It never states that the command must also accept a trailing selector, so this
is an undocumented requirement rather than a mis-configuration — every
downstream project whose custom command is a whole-suite script inherits the
same hole.

**Diagnosis evidence (2026-08-31, `origin/main@b45c762`):**

- **The auto-detect path already has the missing signal; the custom path
  bypasses it.** `tdd.py:310-329` (`_run_command`) wraps auto-detected runners
  with `_selector_missed` (`tdd.py:269`): a selector that resolves to no test
  exits 2 ("unresolved selector"). The custom-command branch
  (`tdd.py:354-369`) returns before `_run_command` is ever reached — it has no
  equivalent check, no capability contract, and only two failure modes
  (non-zero → 1, spawn failure → 2). "Could not target" is unrepresentable.
- **The gate discards the only channel that could explain an exit 2.**
  `bug.py:799-807` (`_run_tdd`) captures stdout/stderr, but the FIXING gate's
  exit-2 arm (`bug.py:923-926`) raises a bare "tdd.py environment error" and
  the REVIEWED failure arm (`bug.py:952-964`) records only the exit code —
  tdd.py's stderr never reaches the operator.
- **Live repro re-witnessed:** `tdd.py run . --test
  "skills/adr-workflow/test_adr.py::IndexNoSummaryTests" < /dev/null` spawned
  `python3 scripts/run_tests.py skills/adr-workflow/test_adr.py::IndexNoSummaryTests`
  (ps-verified mid-run) — the selector rides argv into a `main()` that reads
  no argv (`scripts/run_tests.py:162-165`), and the full ~3700-test suite +
  pyright runs instead of the one named class. Nothing on stdout/stderr
  mentions the selector.

**Observed twice before and never recorded as a defect:**

- `docs/bugs/004-terminal-status-legibility.md:181` — Learning section, tooling
  note: "the `.jig/test-command` runner ignores the appended selector and runs
  the full suite + `uvx pyright`, so the red→green gate here is repo-wide."
- `docs/bugs/007-unregistered-plugin-skill-contract.md:102` — that session
  reached `REVIEWED` via the deliberate `JIG_BUG_TEST_GATE=0` escape because the
  whole-suite command failed for an unrelated reason (`uvx` sandbox).

## Hypotheses

<!-- Anti-anchoring: >=2 candidates, mark the leading one. -->
- [ ] H1: this is a configuration problem in jig's own repo, not a jig defect —
      `.jig/test-command` should point at a selector-aware command and the
      helpers are fine. Weak: it does not explain downstream projects, since
      `tdd.py` appends a selector to *any* custom command and `SKILL.md` never
      requires the command to accept one. Falsify by scaffolding a project whose
      custom command is a whole-suite script and checking whether anything warns.
      **FALSIFIED (2026-08-31):** `_parse_custom_command` (`tdd.py:144`)
      accepts any command line; the custom branch appends the selector to it
      unconditionally (`tdd.py:362-363`) with no capability check and no
      warning path anywhere in the branch; `SKILL.md:181-184` documents the
      file as "the exact command to run" and offers jig's own whole-suite
      script as the canonical example. The configuration follows the
      documentation — the defect is in the helper contract, and every
      downstream project with a whole-suite custom command inherits it.
- [x] H2 (leading): the defect is a missing signal, not a missing feature —
      `tdd.py` returns an exit code that cannot distinguish "the named test is
      red" from "the runner could not target and something else is red", and
      `bug.py` consumes it as though it could. Confirm by checking whether any
      code path reports targeted-vs-full-suite; if none exists, the gate has
      never been able to make the distinction it claims.
      **CONFIRMED (2026-08-31):** no such code path exists for custom
      commands — see Root cause for the enumeration that closes the claim.

## Root cause

The custom-command branch of `cmd_run` (`tdd.py:354-369`) has **no concept of
selector capability**. It appends the requested selector to whatever argv
`.jig/test-command` yields (`tdd.py:362-363`), runs it, and can only report
"command exited non-zero" (1) or "command failed to start" (2). Whether the
command *honored* the selector is unrepresentable in its exit contract — the
branch returns before `_run_command`/`_selector_missed` (`tdd.py:310/269`),
the only targeting-miss detection in the file, is ever reached.

`bug.py`'s red/green teeth then consume that exit code as a machine-attestation
about the *named* regression test (`_run_tdd` calls at `bug.py:917/953`):
FIXING stamps `red_confirmed_at` on any non-zero suite exit, REVIEWED demands a
whole-suite zero — and both discard the captured stderr that could have
explained a refusal. On a project whose custom command is a whole-suite script
(jig itself), the gate therefore attests "the named test was witnessed red"
from evidence that may be any failure anywhere in the suite — observed live in
bug 020, where pyright errors on unrelated code stamped a red while the named
test was already green.

**Grounding for the universal claim** ("no code path reports
targeted-vs-full-suite for custom commands"), per ADR-0052: the custom-command
branch is a single early-return block (`tdd.py:354-369` — parse, append, run,
return; read in full), so the branch-local set is closed by inspection. The
consumer set is closed by repo-wide text search for the helper's invocation
shape (`tdd.py.*run`, `_run_tdd`, `JIG_TDD_HELPER` — tdd.py is invoked by
path as a CLI, not imported, so textual search closes repo-internal callers):
`bug.py:_run_tdd` (selector-bearing, the affected consumer),
`land.py:_check_tests` (`land.py:310-327`, no selector — unaffected),
`quality.py`/`health.py` (mirror the shape, never pass `--test`), and the
SKILL.md docs. External projects reach tdd.py only through the documented CLI
contract — which is exactly the contract found defective.

## Repository closure inventory

> Voluntary — this is a legacy (pre-091) record, exempt from the closure gate.
> Recorded anyway (ADR-0037 discipline; searches run 2026-08-31 @ `b45c762`).

- **Equivalent / convergent logic searched.** Terms tried:
  `_selector_missed` / "unresolved selector" (tdd.py only — the auto-detect
  targeting-miss check, reused conceptually, not literally: it parses
  runner-specific output, which custom commands don't have);
  `{test}` / placeholder / `format(` over `skills/` (no existing placeholder
  or template-substitution convention in any helper — this fix introduces the
  first one); `test-command` repo-wide (writers: none — hand-authored, tracked;
  readers: tdd.py `_custom_command_file`/`_parse_custom_command`,
  gitignore-comment references in scaffold.py, docs in tdd-loop SKILL.md +
  adoption-readiness template). No convergent implementation found —
  grounded by the searches above, not claimed exhaustively.
- **Relevant history.** `git log -S` on tdd.py: the custom-command branch
  arrived 2026-05-14 (`91d6724`, slice 006-05). The `--test` selector and
  `_selector_missed` arrived six weeks later, 2026-06-23 (`bf7f2e5`,
  "feat(tdd-loop): add targeted test selector" — landed *with* the ADR-0016
  bug-fix-lifecycle work, i.e. the selector exists precisely to serve the
  red→green gates). The custom branch was never retrofitted with the
  targeting-miss distinction that commit introduced for auto-detected
  runners — an evolution seam, not a design decision (no ADR covers it).
- **Affected call sites** (enumeration in Root cause): `bug.py:_run_tdd`
  (both gates — selector-bearing, must surface targeting refusals);
  `land.py:_check_tests` (no selector — unaffected, must stay unaffected);
  `quality.py`/`health.py` (no `--test` — unaffected); `tdd-loop/SKILL.md`
  (documents the contract — must document the placeholder);
  `docs/adoption-readiness.md.template` (names `.jig/test-command` — checked
  at fix time for contract-drift).
- **Reuse decision.** Reuse the *exit-code contract* (2 = "could not run as
  asked", already fail-closed in bug.py) rather than inventing a new channel;
  introduce the `{test}` placeholder as a new, documented capability
  declaration (nothing to reuse — first of its kind here). Duplicating
  `_selector_missed`'s output-parsing for custom commands was considered and
  rejected: custom commands have no output contract to parse.

## Fix class

`structural_fix` — the load-bearing change is a contract change: targeting a
custom command becomes an explicit, declared capability (a `{test}` placeholder
in `.jig/test-command`), "could not target" becomes representable (exit 2 with
a one-line reason), and `bug.py`'s gates surface that reason instead of a bare
exit code. Composed with a supporting `local_patch` (`scripts/run_tests.py`
accepts an optional selector so jig's own configuration can declare the
placeholder) — recorded under the primary class per the frontmatter's
single-value field.

## Fix

Four pieces, matching the filing's direction (2026-08-31):

1. **`tdd.py` — the structural half.** Selector capability for a custom
   command is now an explicit opt-in: a `{test}` argv token
   (`CUSTOM_SELECTOR_PLACEHOLDER`) in `.jig/test-command` marks where the
   selector is substituted (dropped when no selector is passed). Without the
   token, a targeted run is **refused** — exit 2 with "custom test command
   does not accept a test selector" — instead of silently widening to the
   whole suite. With the token, the targeted run streams through
   `_run_streaming` and applies `_selector_missed("custom", …)`, so output
   reporting no matching tests maps to exit 2 (`unresolved selector`) —
   parity with the auto-detect runners. An honored red run stays exit 1.
2. **`bug.py` — the gate half.** New `_tdd_failure_detail()` surfaces the
   one-line tail of a failed tdd.py run in the FIXING exit-2/unexpected-exit
   errors and in the REVIEWED green-check failure (BugError + `## Already
   tried` entry) — the refusal is now legible, not a bare exit code. The
   exit-2 arm's message states explicitly that exit 2 is "not evidence of
   red". (The REVIEWED arm's pre-existing routing of *any* non-zero — env
   errors included — back to DIAGNOSING is deliberately untouched: re-runnable,
   and out of this bug's scope.)
3. **`scripts/run_tests.py` — the local patch.** `main()` now accepts
   optional `path[::Class[::method]]` selectors: builds a targeted suite
   (location-based import — skill dirs are hyphenated), skips pyright
   (targeted runs answer "does this named test pass?"; repo-wide gates stay
   with the full run), and reports unresolved selectors as
   `no matching tests: <sel>` + exit 1, which tdd.py maps to exit 2. Name
   resolution walks the attribute chain explicitly — `loadTestsFromName`'s
   miss behaviour is version-dependent (3.9 raises, newer returns a synthetic
   red `_FailedTest`), and a typo'd selector must be *unresolved*, never red.
4. **Configuration + contract docs.** jig's `.jig/test-command` becomes
   `python3 scripts/run_tests.py {test}`; `skills/tdd-loop/SKILL.md`
   documents the placeholder contract (the previously undocumented
   requirement is now an explicit, checkable declaration).

Effect on this repo's own ceremony: the red/green gates now run the *named*
test in seconds (witnessed below: 2.4s vs 443s) and cannot stamp verdicts
from unrelated suite failures.

## Already tried

Nothing — filed on first observation.

## Regression test

Named (gate-witnessed): `skills/tdd-loop/test_tdd.py::Bug021CustomCommandSelectorContractTests`
— a custom command without a `{test}` placeholder refuses a targeted run
(exit 2, command never spawned); with the placeholder the selector is
substituted (and dropped when absent); a targeted run reporting
"no matching tests" maps to exit 2 (unresolved selector), not red; an honored
red targeted run stays exit 1.

Both halves the filing asked for are covered — the second half rides in the
same suite:

- `skills/bug-fix/test_bug.py::Bug021GateSurfacesTargetingRefusalTests` — the
  FIXING gate refuses a tdd.py exit-2 targeting refusal (no `red_confirmed_at`
  stamped) and surfaces tdd.py's own report in the error; the REVIEWED
  green-check failure carries the report into the error + `## Already tried`.
- `scripts/test_run_tests.py::Bug021TargetedSelectorTests` — the local half:
  `run_tests.py` honors `path::Class[::method]` selectors (targeted suite, no
  pyright), reports unresolved selectors as "no matching tests" (exit 1, which
  tdd.py maps to 2).

## Call-site closure

> Voluntary (legacy record — the gate exempts it); every site the inventory
> named, accounted for:

- `skills/tdd-loop/tdd.py` custom branch — **changed** (placeholder contract,
  refusal, unresolved-selector mapping); covered by
  `Bug021CustomCommandSelectorContractTests`.
- `skills/bug-fix/bug.py` `_run_tdd` consumers (FIXING + REVIEWED arms) —
  **changed** (failure detail surfaced); covered by
  `Bug021GateSurfacesTargetingRefusalTests`. The REVIEWED arm's
  route-back-to-DIAGNOSING-on-env-error behaviour **intentionally left
  alone** (pre-existing, re-runnable, out of scope — noted in ## Fix).
- `scripts/run_tests.py` — **changed** (selector support); covered by
  `Bug021TargetedSelectorTests`.
- `skills/slice-land/land.py` `_check_tests` — **intentionally left alone**:
  never passes a selector, so the no-selector path (placeholder token dropped,
  behaviour otherwise identical) is the only one it sees; whole-suite green
  before landing remains its correct contract.
- `skills/tdd-loop/quality.py` / `skills/code-health/health.py` —
  **intentionally left alone**: mirror tdd.py's CLI shape but never pass
  `--test`.
- `skills/tdd-loop/SKILL.md` — **changed** (contract documented);
  `templates/docs/adoption-readiness.md.template` — **intentionally left
  alone**: its test-command mention is a readiness checklist item with no
  selector semantics, so no drift.
- `.jig/test-command` (jig's own) — **changed** (declares `{test}`).
- Host packages (`hosts/claude`, `hosts/codex`) — **regenerated** via
  `scripts/build_host_packages.py`; `--check` clean.

## Proof

Post-fix, same machine, same worktree (2026-08-31):

- Targeted run through the full fixed pipeline —
  `tdd.py run . --test "skills/tdd-loop/test_tdd.py::Bug021CustomCommandSelectorContractTests"`
  → `Ran 5 tests in 1.751s / OK`, wall clock 2.4s (pre-fix: the same shape ran
  4514 tests in 443s). The REVIEWED green gate ran this same targeted path.
- Unresolved selectors through the real repo config: ghost class and ghost
  path both → `unresolved selector` / `no matching tests` + exit 2 (witnessed
  above the gates as designed — never red).
- Named regression class red→green witnessed by the gates:
  `red_confirmed_at` stamped by the pre-fix FIXING transition (necessarily a
  whole-suite run — the un-fixed machinery cannot target; the new tests were
  the intended red and were also witnessed red directly, class-level, before
  the transition); `green_confirmed_at` stamped by the REVIEWED transition's
  post-fix **targeted** run of the named class (see frontmatter for both
  dates — the stamps are the gate's attestation, not this section's).
- Full suite + pyright green post-fix (CI parity), ruff clean, host-package
  drift check clean.

**Residual accepted risks (surfaced by the review passes):**

- A human running the `.jig/test-command` line verbatim passes a literal
  `{test}` to `run_tests.py` → `no matching tests: {test}`, exit 1 — fails
  safe and self-describing; only tdd.py strips the token.
- The placeholder must be a standalone shlex token; embedded forms
  (`--sel={test}`) are not recognized and produce the targeting refusal —
  fails safe (refusal, never a silent whole-suite run).
- A custom command that exits 0 having matched nothing reads as green —
  parity with the auto-detect JS runners' existing heuristic; the recognized
  no-match report lines are documented in SKILL.md as part of the contract.
- The REVIEWED green gate in this repo now attests the *named test* green
  (targeted, no pyright); whole-suite green + pyright + board integrity are
  the landing bar (slice-land / CI). This narrowing is the intended contract
  per this record's Symptom section.

## Learning

A gate that consumes a process exit code inherits every assumption that code
makes. `tdd.py`'s exit code answered "did the command succeed?", while the bug
lifecycle asks "did this named test fail?" — two different questions with the
same numeric answer, which is how a teeth-not-trust gate ended up attesting
something it never checked. The repair is to make the narrower question
*representable* at the boundary (targeting as a declared capability; "could
not target" as a distinct outcome) and to make the refusal legible to the
consumer (surface the reason, not the number). Corollaries: (1) capability by
silent convention — "the command probably accepts a trailing selector" — is a
contract nobody wrote and nobody checks; an explicit token (`{test}`) turns it
into one that can be refused, tested, and documented. (2) The symptom was
*observed and annotated twice* (bugs 004, 007) before being *filed* once —
tooling friction that every session works around is a defect record waiting to
exist. (3) Full expansion in `docs/memory/learnings.md` (bug 021 entry),
including the stdlib gotcha: `loadTestsFromName`'s miss behaviour is
version-dependent, so resolve names explicitly when "unresolved" must differ
from "red".

## Release log

- 2026-08-31 - released claim from claude/bug-021-tdd-selector-gate: claim branch claude/bug-021-tdd-selector-gate no longer exists locally or on origin; record never left REPORTED

## Main recheck

- 2026-08-31 - `origin/main@b45c762` -> reproduces: Documented repro re-run 2026-08-31 on a clean worktree at origin/main@b45c762 (HEAD == origin/main): 'tdd.py run . --test skills/adr-workflow/test_adr.py::IndexNoSummaryTests < /dev/null' spawned 'python3 scripts/run_tests.py skills/adr-workflow/test_adr.py::IndexNoSummaryTests' (ps-witnessed argv, selector appended+ignored), ran 4514 tests in 443s instead of the one named green class, never mentioned the selector, and exited 1 (red) from 3 failures unrelated to the named class (2x board-integrity red from this session's own in-flight record edits + 1 machine-local scout-daemon fixture flake) — live demonstration of the gate consequence: red_confirmed_at would be stamped for a green named test.
