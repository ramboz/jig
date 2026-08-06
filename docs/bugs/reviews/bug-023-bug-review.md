---
bug: 023
pass: bug-review
verdict: pass
reviewer: jig:reviewer subagent
reviewed_at: 2026-07-30T22:44:50Z
prompt_source: review.py bug-review builder (9 rounds; verdict from the final pass)
---

Re-review after eight rounds. The code fix passed from the first pass; every
subsequent round found defects in the documentation built around it, all now
closed.

**Root cause vs. symptom — addressed at the cause.** `copy_machinery`
answered two different questions from one variable. It now resolves
`advisory_host = read_host_renderer(project_dir) or resolved_host` for the
detection token and keeps `resolved_host` for the offered replacement path.
Both halves of the warning are independently true: the token is what the
project's docs actually cite, the path is where this run actually put the
machinery.

**Regression test.** `CrossHostAdvisoryTests`, 12 methods. Four fail pre-fix
for their stated reasons — the two host tokens are genuinely disjoint
(`${PLUGIN_ROOT}` is not a substring of `${CLAUDE_PLUGIN_ROOT}`), so the
pre-fix advisory is empty and each first assertion trips. Two more error on
the missing accessor (7 error entries: 1 + 5 subTests + 1 post-loop),
matching the recorded red count of 4 failures + 7 errors. Five cannot fail
pre-fix — two premise guards and three degrade paths where project host
equals invocation host — and the record does not claim they do.

**Blast radius.** `renderer_for_host`'s conversion from an inline ternary to
a `_HOST_RENDERERS.get()` lookup is behaviour-preserving for every reachable
caller; both `migrate._resolve_host` and scaffold's `--host` choices validate
first. The only delta is on an unhashable `host` (raises instead of
defaulting), unreachable through every validated path, and the
`isinstance`-before-membership ordering in `read_host_renderer` prevents it
there. Mirrors under `hosts/claude/` and `hosts/codex/` are byte-identical to
their sources at every changed line.

**Scope.** Two additions beyond the call-site change, both logged as
deliberate: `_HOST_RENDERERS` as one registry with two readers rather than a
second host list, and a `docs/refinement-todo.md` entry giving
`renderer_for_host`'s unknown-host fallback a tracked home, since
`read_host_renderer`'s docstring cites it as open.

**Documentation guard.** The advisory section of `skills/migrate/SKILL.md`
is pinned by `test_codex_render_of_the_split_does_not_invert`, which asserts
against the shipped package. The forbidden set is parsed out of
`build_codex_plugin.py` by an AST walk over its string-literal `.replace()`
pairs, taking both sides, rather than restated — the same structural move
bug 018's fix made for the spellings themselves. It took four attempts; the
sequence and what each weaker version let through are recorded in `## Proof`.
All five escapes attempt 3 allowed (`${PLUGIN_ROOT}`, `AGENTS.md`, lowercase
`--host codex` / `--host claude`, unslashed `.codex`) are caught,
mutation-verified.

**Record honesty.** `main_repro_result: reproduces` does not describe
`origin/main` and the record says so plainly: the defect exists only in code
PR #150 introduces, main is pre-defect rather than fixed, and `bug.py` has no
vocabulary for that case. The gate's intent — do not re-fix what trunk
already solved — is satisfied. `## Deviations` carries eleven entries
covering the vocabulary gap, the two scope additions, the partially applied
learning, the guard's enforced scope and its empty-set limit, the rewritten
bug-018 regression test, the user-facing editor comment, the as-of-diagnosis
`## Evidence` line numbers, the cycle-vs-pass numbering, and the guard-history
mis-numbering that took three rounds to finish correcting.

Fixed since the last pass: the claim that two test docstrings "ship in the
plugin" — they do not, `test_*.py` is excluded from both host packages — and
the newline-filter description, which now says *interior* newline since
`.strip()` runs first.

Full suite 3847 tests, OK (skipped=7), exit 0, read from a redirected file.

No defects remain.
