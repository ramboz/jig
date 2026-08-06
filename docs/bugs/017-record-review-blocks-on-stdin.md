---
status: DONE
tier: standard
severity: high
claimed_by: claude/bug-017-stdin-fix
regression_test: skills/independent-review/test_review.py::Bug017RecordReviewStdinTests
main_repro_checked_at: 2026-07-30
main_repro_ref: origin/main@00c3333
main_repro_result: reproduces
red_confirmed_at: 2026-07-30
green_confirmed_at: 2026-07-30
fix_class: structural_fix
security_surface: false
escalated_to:
---

# Bug 017: record-review-blocks-on-stdin

> **Numbering note:** 015 and 016 are taken by
> [#143](https://github.com/ramboz/jig/pull/143), unmerged at the time of
> filing. `bug.py new` on a main-rooted worktree would have re-allocated 015,
> so this record was numbered by hand.

## Symptom

`review.py record-review` **hangs forever** when `--summary-file` is omitted
and stdin is a pipe rather than a terminal.

Because a test fixture inside `scripts/run_tests.py` invokes `record-review`
that way, the consequence is bigger than one command: **jig's whole test suite
hangs** under any agent harness or CI runner. Observed 13+ minutes on what
should be a single targeted test (`bug.py transition` → `tdd.py run` →
`run_tests.py`), against ~100s when it completes.

The defining property, and the reason this went unexplained for weeks: **it
never reproduces by hand.** Run interactively, it is always fine.

## Repro

The pipe's **write end must stay open** — that is the whole condition. Note in
particular that `subprocess.run(stdin=subprocess.PIPE)` does *not* reproduce it:
`run()` closes stdin immediately, the child sees EOF, and it exits cleanly. A
first attempt at this repro made exactly that mistake and appeared to disprove
the bug.

```python
import os, subprocess, sys, tempfile, pathlib
REVIEW = str(pathlib.Path("skills/independent-review/review.py").resolve())
d = pathlib.Path(tempfile.mkdtemp())
(d / "docs" / "decisions").mkdir(parents=True)
(d / "docs" / "decisions" / "adr-0001-x.md").write_text(
    "---\nstatus: Proposed\n---\n\n# ADR-0001: X\n\n## Status\n\nProposed\n")

cmd = [sys.executable, REVIEW, "record-review", "--adr", "0001",
       "--pass", "frame-critique", "--verdict", "pass",
       "--reviewer", "r", "--prompt-source", "p"]      # note: no --summary-file

r_fd, w_fd = os.pipe()                 # we hold w_fd open => child never sees EOF
p = subprocess.Popen(cmd, stdin=r_fd, cwd=d)
os.close(r_fd)
p.wait(timeout=8)                      # -> subprocess.TimeoutExpired
```

Observed on `main@bde9dfc`:

| stdin handed to the child | outcome |
|---|---|
| terminal | exits (guard skips the read) |
| `subprocess.DEVNULL` / `< /dev/null` | exits rc=0 immediately |
| `subprocess.run(stdin=PIPE)` | exits rc=0 — `run()` closes it |
| **pipe with the write end held open** | **hangs indefinitely** |

Whole-suite form — the one that actually bites:

```bash
python3 scripts/run_tests.py              # hangs under an agent harness / CI
python3 scripts/run_tests.py < /dev/null  # ~100s, green
```

## Evidence

Diagnosed by walking the process tree of a hung run down to the leaf:

```
bug.py transition 015 FIXING
└── tdd.py run … --test …CodexScaffoldAdapterTests::test_…
    └── scripts/run_tests.py …
        └── review.py record-review --bug /tmp/jig-rev-bugev-…/docs/bugs/001-cache-race.md
            --pass bug-review --verdict pass --reviewer reviewer
            --prompt-source "review.py bug-review docs/bugs/001-cache-race.md"
```

Note the leaf command carries **no `--summary-file`**.

`sample` on the parent showed it parked in `select`/`poll` — waiting on a
child, not spinning.

The mechanism is in `skills/independent-review/review.py`, in the helper that
resolves the freeform verdict body:

```python
if args.summary_file:
    ...
# Fall back to stdin. An empty body is allowed (the frontmatter carries
if not sys.stdin.isatty():
    return sys.stdin.read()
```

`isatty()` is being used as a proxy for "stdin has content", and it is not one.
It distinguishes *terminal* from *not-terminal*, which splits three real cases
into two:

| stdin | `isatty()` | `read()` |
|---|---|---|
| terminal | `True` | skipped — **fine** |
| closed / `< /dev/null` | `False` | returns `""` immediately — **fine** |
| open pipe, never closed | `False` | **blocks forever** |

An agent harness and most CI runners hand a child an open pipe. A human at a
terminal never does. That is the entire explanation for "works for me".

## Hypotheses

- [ ] H1: the hang is git-lock contention between concurrent `run_tests.py`
  runs (the standing suspicion, recorded in the flaky-drift-guard notes).
  Falsify: the hang reproduces with a **single** run and no concurrency, the
  `jig-locks/` directory is empty during it, and the stuck leaf is a
  `record-review` subprocess rather than any git command. **Falsified.**
- [ ] H2: `record-review` is slow / doing heavy work. Falsify: `sample` shows
  it parked in `poll`, not consuming CPU, indefinitely. **Falsified.**
- [x] H3 (leading): `record-review` falls back to `sys.stdin.read()` guarded
  only by `isatty()`, so an open-but-never-closed pipe blocks forever.
  **Confirmed** twice over: (a) closing stdin (`< /dev/null`) makes the
  identical command complete immediately, with no other change; and (b) a
  direct single-variable repro — same command, same project, stdin the only
  difference — hangs with the pipe's write end held open and exits rc=0 the
  moment it is closed.

## Root cause

`isatty()` is used to decide whether stdin *has* input. It only reports whether
stdin is a terminal. For the third case — an open pipe with no writer and no
EOF — the guard passes and `sys.stdin.read()` blocks until EOF that never
comes.

The bug is not the fallback itself; it is that its guard tests the wrong
property.

## Fix class

`structural_fix` — the implicit stdin read is removed, not bounded. Nothing in
`_read_summary` branches on whether stdin is a terminal any more, so the class
of failure ("behaviour depends on what stdin happens to be") is gone rather
than made faster to fail.

## Fix

Direction chosen by @ramboz on
[#144](https://github.com/ramboz/jig/pull/144): candidate 1 — *"I'd lean
towards forcing a body when non-interactive. I don't see the point of a review
without a body. So would enforce it."*

Implemented in `skills/independent-review/review.py::_read_summary`:

- **stdin is never read implicitly.** `--summary-file -` (the usual Unix
  spelling) is now the only path to it, so a blocking read is always something
  the caller asked for.
- **`record-review` requires a body** — omitting `--summary-file` is a clean
  exit-2 naming the option. This is the "enforce it" half, and it applies
  uniformly rather than only when stdin is not a terminal: the `isatty()` fork
  *is* the bug, so keeping one for the enforcement rule would preserve the same
  "works by hand, hangs in CI" asymmetry.
- **A blank body is refused the same way.** Added after review pointed out that
  enforcing the *option* rather than the *body* still let
  `--summary-file /dev/null` record an empty verdict — which would have made
  the docs' "a verdict with no body is refused" untrue.
- **`code-health` keeps its graceful degrade** (`required=False`): omitting
  `--summary-file` still builds the prompt with the "(no health.py summary
  provided …)" note, per spec 060-05 AC2. Only the implicit stdin read is gone.
  Recorded as an amendment on
  [slice 060-05](../specs/060-code-health-capability/slice-05-codehealth-reviewer.md#amendments);
  the optional-body claim in
  [slice 045-02](../specs/045-review-lifecycle-gates/slice-02-review-artifact-recorder.md#amendments)
  is amended there.

Callers updated: the `BugReviewEvidenceRecorderTests` fixture — the leaf that
hung the suite — now passes `--summary-file`; the five test helpers that piped
a body in now say `--summary-file -`; SKILL.md / workflow.md examples updated,
along with `record-review --help`'s own description and the copy-pasteable
command in `adr.py`'s accept-gate refusal (both still advertised the old
implicit-stdin contract; the second would have exited 2 if followed verbatim).

**Contract change, worth stating plainly:** `record-review` now requires a body
on all three targets (slice, `--adr`, `--bug`). That is wider than "stop the
hang" — an out-of-tree caller that recorded a verdict with no body will now get
a clean exit 2. It is the enforcement @ramboz asked for, and it fails loudly and
immediately rather than silently.

The enforcement deliberately does **not** fork on `isatty()`, though the
direction was phrased as "when non-interactive". A rule that only applies when
stdin is not a terminal reproduces the exact asymmetry that made this bug
invisible for weeks — passes by hand, bites in CI. Uniform enforcement is the
same rule with the terminal-dependence removed.

**The interim workaround still works and is worth knowing** regardless of this
fix, for any helper that shells out:

```bash
python3 scripts/run_tests.py < /dev/null
```

## Already tried

Nothing discarded. H1 and H2 were falsified by observation before any edit; no
fix has been attempted.

## Regression test

`skills/independent-review/test_review.py::Bug017RecordReviewStdinTests` — four
tests:

1. `test_terminates_when_stdin_is_a_pipe_nobody_closes` — the one with teeth.
   `os.pipe()` with the write end **held open by the test**,
   `subprocess.Popen(stdin=read_fd)`, `communicate(timeout=15)` asserting no
   `TimeoutExpired`.
2. `test_missing_body_errors_and_names_the_option` — no body source → exit 2,
   stderr names `--summary-file`, and no verdict file is left behind.
3. `test_blank_body_is_refused_like_a_missing_one` — a whitespace-only summary
   file → exit 2, so the enforcement is on the body, not on the option.
4. `test_explicit_dash_reads_the_body_from_stdin` — `--summary-file -` still
   pipes a body through.

Two shapes that would pass against the unfixed helper and prove nothing, both
easy to reach for and deliberately avoided:

- `subprocess.run(..., stdin=subprocess.PIPE)` — `run()` closes stdin, the
  child sees EOF, and it exits. This is the trap; it cost one wrong repro here.
- calling the resolver directly with a closed or `DEVNULL` stdin — also exits.

## Proof

- **Red, witnessed by the `→ FIXING` gate** (`red_confirmed_at: 2026-07-30`).
  Run by hand before the fix: the three tests that existed at that point all
  failed, the pipe one via `TimeoutExpired` after 15s — i.e. the hang
  reproduced inside the suite. (The fourth, `test_blank_body_is_refused_like_a
  _missing_one`, was added later, in response to the craft review; it is red
  against the unfixed helper too — that path recorded a verdict and exited 0.)
- **Green, witnessed by the `→ REVIEWED` gate** (`green_confirmed_at`). All
  four pass in well under a second: 15s-of-hang → immediate exit.
- **Fresh-main recheck** before the fix: the `os.pipe()` repro run in a
  detached worktree at `origin/main@00c3333` still hung (`TimeoutExpired`
  after 8s), so this was not already fixed on trunk.
- **Whole suite**, the thing the bug actually broke: `run_tests.py` green,
  and — the point of the fix — green *without* `< /dev/null`.

## Learning

Recorded in `docs/memory/learnings.md` under bug 017: **`isatty()` answers
"is this a terminal", never "is there input waiting".** Using it as a
has-input guard is correct for a human at a prompt and wrong for every
automated caller — the failure mode is an indefinite hang, in exactly the
context (CI, agent harness) where nobody is watching to interrupt it. The
"never reproduces by hand" signature is itself the tell: a bug that only
appears when a human is *not* driving points at a terminal-shaped assumption.

## Main recheck

- 2026-07-30 - `origin/main@00c3333` -> reproduces: os.pipe() repro from the record's Repro section, run in a detached worktree at origin/main@00c3333: record-review --adr 0001 (no --summary-file) with the pipe's write end held open -> subprocess.TimeoutExpired after 8s (no exit).
