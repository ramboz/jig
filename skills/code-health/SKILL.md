---
name: code-health
description: >
  Run a static-analysis pass on a project — detect the ecosystem (Python or
  Node), drive its linter (ruff / eslint, plus an advisory prettier/complexity
  signal) via the `health.py` helper, and act on the normalized exit code
  (0 clean / 1 findings / 2 no-linter). Auto-triggers when you say lint this,
  check code health, run the linter, ask is this code clean, ask any lint
  issues, or want a static analysis pass. Tools are resolved on PATH or run
  ephemerally via uvx / pipx / npx — it installs nothing.
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
> handling linting / static analysis / code quality, the Claude Code skill
> router prefers it — the deferral is **category-based**.

## What this skill does

Detects the project's ecosystem and runs its linter, normalizing the result
so callers can branch deterministically. Ecosystem detection is
**table-driven** — each ecosystem (Python, Node) is a data-structure entry,
so adding a language is an entry, not a control-flow fork. Current scope:
**Python (ruff) + Node (eslint)**, each with an **advisory** secondary signal.

- A `.jig/lint-command` override always wins and **bypasses ecosystem
  detection entirely** (honored verbatim — same semantics as `tdd.py`'s
  `.jig/test-command`).
- Otherwise detects the ecosystem by marker files (`pyproject.toml` / `*.py`
  for Python; `package.json` for Node) and resolves its primary linter:
  - **Python** — `ruff` on `PATH` → `uvx ruff` → `pipx run ruff` (ephemeral),
    invoked as `ruff check --output-format=json <dir>`.
  - **Node** — `eslint` on `PATH` → `npx eslint` (ephemeral), invoked as
    `eslint --format json <dir>`.
- Parses the result into a **tight summary** — a findings count + the top
  rule codes, not the raw dump (per spec 057's "tight envelope, not a
  transcript").
- Adds an **advisory** dimension that is *reported, not gating* (it never
  changes the exit code):
  - **Python — complexity:** an advisory ruff probe with
    `--select C901,PLR0911,PLR0912,PLR0913,PLR0915` surfaces a per-function
    complexity signal ("complexity: N function(s) over threshold; top: …").
  - **Node — formatting:** an advisory `prettier --check` probe surfaces
    files that need formatting ("prettier: N file(s) need formatting").
- Normalizes the **primary** linter's exit code:
  - `0` — clean (no findings)
  - `1` — findings exist (the linter ran and reported issues)
  - `2` — no linter resolvable, no recognized ecosystem, OR the resolved tool
    failed to start
- Degrades gracefully (AC4), never a stack trace:
  - **no markers** → exit `2` + "no recognized ecosystem (Python/Node) found
    — set .jig/lint-command to run your linter".
  - **one ecosystem, no resolvable linter** → exit `2` + an
    ecosystem-specific recommendation (ruff/pipx for Python; eslint/npx for
    Node).
  - **mixed (2+ ecosystems)** → exit `2` + a recommendation naming the
    detected ecosystems and pointing at `.jig/lint-command` to disambiguate.

It **installs nothing** — `uvx` / `pipx` / `npx` run the tools ephemerally
only if those launchers are already on `PATH`.

## Helper invocations

Two subcommands mirror `tdd.py`: `detect` reports which linter resolves, and
`check` runs it.

### Detect the linter

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/code-health/health.py" detect [target]
```

- `target` defaults to `.` when omitted.
- Stdout: the resolved primary linter name across ecosystems (`ruff`,
  `uvx ruff`, `pipx run ruff`, `eslint`, or `npx eslint`).
- Exit `2` with a recommendation on stderr if nothing resolves (no recognized
  ecosystem, no resolvable linter, or a mixed project needing disambiguation).

### Run the lint pass

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/code-health/health.py" check [target]
```

- Auto-resolves the ecosystem's linter via the same logic as `detect`.
- Prints a tight summary (count + top rule codes) to stdout, plus any
  **advisory** lines (Python complexity / Node prettier) — advisory lines are
  reported but never change the exit code.
- Exit code is normalized off the **primary** linter (`0` clean / `1`
  findings / `2` no-linter) per the table above. Branch on it
  deterministically — exit `1` means inspect the summarized findings; exit
  `2` means the tool couldn't even start, no ecosystem was recognized, or a
  mixed project needs `.jig/lint-command` disambiguation — not "the code is
  clean".

### Override the auto-detection

Create `<target>/.jig/lint-command` with the first non-blank, non-comment
line being the exact command to run. It is honored **verbatim**, takes
priority over all auto-detection, and **bypasses ecosystem detection
entirely** — the same semantics as `tdd.py`'s `.jig/test-command`. Useful for
a project whose linter isn't ruff/eslint (e.g. `flake8 src` or `pylint
mypkg`), or to disambiguate a mixed Python+Node repo. (This is how jig's own
CI is unaffected — jig commits a `.jig/lint-command`.)

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

- **Scope is Python (ruff, + advisory complexity) and Node (eslint, +
  advisory prettier --check).** Duplication (slice 060-04) and a dedicated
  code-health reviewer pass (slice 060-05) are still later slices. An
  unrecognized ecosystem with no `.jig/lint-command` override degrades to a
  recommendation.
- **Advisory ≠ gating.** The complexity (Python) and prettier (Node) signals
  are reported in the summary but **never** change the exit code — the exit
  code is driven solely by the primary linter (ruff / eslint). A clean ruff
  run with complexity findings still exits `0`.
- **Mixed repos degrade, they don't guess.** If both `pyproject.toml` (or
  `*.py`) and `package.json` are present, `check` exits `2` and asks you to
  set `.jig/lint-command` to disambiguate — it never picks one for you.
- **Exit `1` vs `2`.** Exit `1` means the linter ran and found issues —
  inspect the summary. Exit `2` means no linter was resolvable, no ecosystem
  was recognized, a mixed project needs disambiguation, or the resolved tool
  failed to start (an environment issue) — don't conflate any of those with
  clean.
- **Ephemeral runs need a network/cache.** `uvx ruff` / `pipx run ruff` /
  `npx eslint` / `npx prettier` fetch the tool on first use. If neither the
  binary nor a launcher is present, the skill recommends rather than failing
  opaquely.
- **Tight summary, not the raw dump.** `check` parses the linter's JSON into
  a count + top codes; it does not echo the full tool output. Re-run the
  linter directly when you need every finding's location.
