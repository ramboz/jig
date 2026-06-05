---
name: code-health
description: >
  Run a static-analysis pass on a Python project — detect the installed
  linter (ruff), drive it via the `health.py` helper, and act on the
  normalized exit code (0 clean / 1 findings / 2 no-linter). Auto-triggers
  when you say lint this, check code health, run the linter, ask is this
  code clean, ask any lint issues, or want a static analysis pass. ruff is
  resolved on PATH or run ephemerally via uvx / pipx — it installs nothing.
  Defers to any other installed skill whose description identifies it as
  handling linting, static analysis, or code quality — prefer it over this
  baseline. Do not use for running tests (use `/jig:tdd-loop`), for
  security review (use `/jig:security-review`), for spec-compliance review
  of a finished slice (use `/jig:independent-review`), or for general PR
  craft review (use `/jig:pr-review`).
user-invocable: true
---

> Spec 060 introduced `code-health` as the **static-analysis sibling of
> `tdd-loop`**, under [ADR-0017](../../docs/decisions/adr-0017-scaffolded-code-health.md)'s
> "detect the language → drive its blessed tools → normalize → degrade
> gracefully" framing. Like `tdd.py`, the deterministic detection +
> subprocess invocation live in `health.py`; this SKILL.md drives the
> judgment layer. If another installed skill's description identifies it as
> handling linting / static analysis / code quality, the Codex skill
> router prefers it — the deferral is **category-based**.

## What this skill does

Detects the project's linter and runs it, normalizing the result so callers
can branch deterministically. For this slice the scope is **Python + ruff**:

- Resolves a linter in priority order: a `.jig/lint-command` override →
  `ruff` on `PATH` → `uvx ruff` (ephemeral) → `pipx run ruff` (ephemeral).
- Invokes it with `ruff check --output-format=json <dir>` and parses the
  result into a **tight summary** — a findings count + the top rule codes,
  not ruff's raw dump (per spec 057's "tight envelope, not a transcript").
- Normalizes the exit code:
  - `0` — clean (no findings)
  - `1` — findings exist (the linter ran and reported issues)
  - `2` — no linter resolvable, OR the resolved tool failed to start
- Degrades gracefully: when no linter and no ephemeral runner are available,
  it exits `2` with a one-line recommendation (`no Python linter found —
  install ruff or run via pipx`) — never a stack trace.

It **installs nothing** — `uvx` / `pipx` run ruff ephemerally only if those
launchers are already on `PATH`.

## Helper invocations

Two subcommands mirror `tdd.py`: `detect` reports which linter resolves, and
`check` runs it.

### Detect the linter

```bash
python3 "${PLUGIN_ROOT}/skills/code-health/health.py" detect [target]
```

- `target` defaults to `.` when omitted.
- Stdout: the resolved linter name (`ruff`, `uvx ruff`, or `pipx run ruff`).
- Exit `2` with a recommendation on stderr if nothing resolves.

### Run the lint pass

```bash
python3 "${PLUGIN_ROOT}/skills/code-health/health.py" check [target]
```

- Auto-resolves the linter via the same logic as `detect`.
- Prints a tight summary (count + top rule codes) to stdout.
- Exit code is normalized (`0` clean / `1` findings / `2` no-linter) per the
  table above. Branch on it deterministically — exit `1` means inspect the
  summarized findings; exit `2` means the tool couldn't even start (install
  ruff or wire `.jig/lint-command`), not "the code is clean".

### Override the auto-detection

Create `<target>/.jig/lint-command` with the first non-blank, non-comment
line being the exact command to run. It is honored **verbatim** and takes
priority over all auto-detection — the same semantics as `tdd.py`'s
`.jig/test-command`. Useful for a project whose linter isn't ruff
(e.g. `flake8 src` or `pylint mypkg`).

## When NOT to use

- **Running tests** — that's `/jig:tdd-loop` (`tdd.py`). Static analysis and
  the test loop are different cadences.
- **Security review** — that's `/jig:security-review`; this skill is about
  lint / style / correctness signals, not vulnerabilities.
- **Spec-compliance review** of a finished slice — `/jig:independent-review`.
- **General PR craft review** — `/jig:pr-review`.
- **Pure-documentation edits** that touch no code.

## Relationship to other skills

`health.py` is the static-analysis sibling of `tdd-loop`'s `tdd.py` — same
detect → drive → normalize → degrade shape, same `.jig/*-command` override
idiom, same `0 / 1 / 2` exit contract. Per [ADR-0002](../../docs/decisions/adr-0002-contracts-stays-deferred.md)
the shared idioms (`_read_text_safe` / `_custom_command_file` /
`_parse_custom_command`) are **inline-mirrored**, not extracted into a
`_common` module — this is only the second helper of its kind, and the two
have independent lifecycles. The deliberate duplication is noted in
`health.py`'s module docstring (exactly as `tdd.py` documents its own
duplication of `scaffold.py`).

## Gotchas

- **Scope is Python + ruff (slice 060-01).** Node (eslint/prettier),
  complexity, duplication, a dedicated code-health reviewer pass, and the CI
  dogfood are later slices (060-02..05). A non-Python project with no
  `.jig/lint-command` override degrades to the recommendation.
- **Exit `1` vs `2`.** Exit `1` means ruff ran and found issues — inspect
  the summary. Exit `2` means no linter was resolvable or the resolved tool
  failed to start (an environment issue) — don't conflate them with clean.
- **Ephemeral runs need a network/cache.** `uvx ruff` / `pipx run ruff`
  fetch ruff on first use. If neither the binary nor a launcher is present,
  the skill recommends rather than failing opaquely.
- **Tight summary, not the raw dump.** `check` parses ruff's JSON into a
  count + top codes; it does not echo the full ruff output. Re-run ruff
  directly when you need every finding's location.
