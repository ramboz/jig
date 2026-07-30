---
status: ROOT_CAUSED
tier: standard
severity: high
claimed_by:
regression_test:
main_repro_checked_at: 2026-07-29
main_repro_ref: bde9dfc
main_repro_result: reproduces
red_confirmed_at:
green_confirmed_at:
fix_class:
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

## Fix

Not fixed — filed for triage.

Candidate directions, in rough order of preference:

1. **Require an explicit body in non-interactive use.** If `--summary-file` is
   absent and stdin is not a tty, either error with a clear message naming
   `--summary-file`, or accept an empty body without reading. Turns an
   indefinite hang into either a fast failure or correct behaviour.
2. **Poll stdin for readiness before reading** (`select.select([sys.stdin], …,
   0)`), treating "not ready" as an empty body. Preserves piped-in bodies
   (`... | record-review`) while never blocking.
3. **Read with a timeout.** Weakest — still slow, and picks an arbitrary bound.

Whichever is chosen, the fixture in `scripts/run_tests.py` that invokes
`record-review` without `--summary-file` should also pass one (or `< /dev/null`),
so the suite does not depend on the fallback's behaviour at all.

**Interim workaround, and it is worth documenting for contributors regardless
of the fix:** run jig helpers with stdin closed.

```bash
python3 scripts/run_tests.py < /dev/null
```

This applies to anything that shells into these helpers — `bug.py transition`
(its red/green gates call `tdd.py run`), `spec-workflow` transitions,
`status-board`.

## Already tried

Nothing discarded. H1 and H2 were falsified by observation before any edit; no
fix has been attempted.

## Regression test

None yet. A test must assert that `record-review` **terminates** when handed a
pipe whose write end stays open, under a timeout.

Two ways to write it that would pass today and prove nothing, both easy to
reach for:

- `subprocess.run(..., stdin=subprocess.PIPE)` — `run()` closes stdin, the
  child sees EOF, and it exits. This is the trap; it cost one wrong repro here.
- calling the resolver directly with a closed or `DEVNULL` stdin — also exits.

The shape that has teeth is `os.pipe()` with the write end **held open** by the
test, `subprocess.Popen(stdin=r_fd)`, then `p.wait(timeout=...)` asserting no
`TimeoutExpired`. See the Repro section.

## Proof

## Learning

Recorded in `docs/memory/learnings.md` under bug 017: **`isatty()` answers
"is this a terminal", never "is there input waiting".** Using it as a
has-input guard is correct for a human at a prompt and wrong for every
automated caller — the failure mode is an indefinite hang, in exactly the
context (CI, agent harness) where nobody is watching to interrupt it. The
"never reproduces by hand" signature is itself the tell: a bug that only
appears when a human is *not* driving points at a terminal-shaped assumption.
