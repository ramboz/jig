# Plan: Slice 006-01 — tdd-helper

## Approach

Same shape as `workflow.py` / `memory.py` / `scaffold.py` / `review.py` /
`adr.py`: deterministic Python 3 helper for the parts that don't need
judgment (runner detection, subprocess invocation, exit-code
normalization), SKILL.md for when / why and what to do with the result.

Two subcommands, one helper:

- `detect [target]` — print the detected runner name (`pytest` /
  `vitest` / `jest`) or exit 2 with stderr "no test runner detected".
- `run [target] [--test-path PATH]` — auto-detect, subprocess-invoke
  the runner, stream output through, normalize exit code (0 green /
  1 red / 2 detection-or-binary-missing).

## `tdd.py` CLI surface

```bash
python3 tdd.py detect [target]
python3 tdd.py run [target] [--test-path PATH]
```

Both subcommands:
- `target` defaults to `.` when omitted.
- Use `pathlib` consistently with the other helpers.
- Exit 0 on success, 1 on red tests, 2 on user errors / detection
  failure / missing binary.
- Print to stdout for primary output, stderr for errors / messages
  that should not be confused with runner output.

## Detection logic

Replicate `scaffold.py:_detect_tests`, but return the runner *name*
instead of a bool. Priority: **pytest > vitest > jest** (the order in
which we check; first hit wins).

```python
def detect_runner(target: Path) -> str | None:
    if _is_pytest(target):
        return "pytest"
    if _is_vitest(target):
        return "vitest"
    if _is_jest(target):
        return "jest"
    return None
```

### `_is_pytest`
- `target / "pytest.ini"` is file → yes
- `target / "conftest.py"` is file → yes
- `[tool.pytest` substring in `target / "pyproject.toml"` → yes
- Any `test_*.py` or `*_test.py` file at root OR in any direct
  subdirectory → yes (shallow scan only; max depth 2 levels)

### `_is_vitest`
- Any of `vitest.config.{ts,js,mjs}` → yes
- `"vitest" in package.json deps/devDeps` → yes

### `_is_jest`
- Any of `jest.config.{ts,js,json}` → yes
- `"jest" in package.json deps/devDeps` → yes

## Run logic

```python
def run(target: Path, test_path: Path | None) -> int:
    runner = detect_runner(target)
    if runner is None:
        print("no test runner detected at " + str(target), file=sys.stderr)
        return 2
    cmd = _build_command(runner, test_path or target)
    try:
        result = subprocess.run(cmd, cwd=target)
    except FileNotFoundError:
        print(f"{cmd[0]}: binary not found (is {runner} installed?)", file=sys.stderr)
        return 2
    return 0 if result.returncode == 0 else 1
```

### Command construction
- pytest → `["python3", "-m", "pytest", str(path)]`
- vitest → `["npx", "vitest", "run", str(path)]` (note `run` —
  prevents watch mode)
- jest → `["npx", "jest", str(path)]`

### Exit-code normalization
The runner's own exit codes vary (pytest uses 0/1/2/3/4/5; vitest/jest
use 0/1). We collapse to:
- 0 → all tests passed
- 1 → at least one red test (any non-zero exit from a runner that
  successfully started)
- 2 → could not detect runner, OR the runner binary was missing
  (`FileNotFoundError` on `subprocess.run`)

This lets Claude branch deterministically: 0 = move on, 1 = inspect
output, 2 = environment problem.

## Files to create

| Path | Purpose |
|---|---|
| `skills/tdd-loop/SKILL.md` | Active skill body. |
| `skills/tdd-loop/tdd.py` | Helper. |
| `skills/tdd-loop/test_tdd.py` | Unit + integration tests. |

## Files to modify

| Path | Change |
|---|---|
| `docs/specs/006-tdd-loop/spec.md` | DRAFT → IN_PROGRESS → DONE (via `workflow.py transition`). |
| `docs/specs/README.md` | Regen via `workflow.py status-board`. |
| `CLAUDE.md` | Add 006 to Active specs hot-cache; promote tdd-loop in Skills table. |
| `skills/scaffold-init/scaffold.py` (maybe) | AC #5 — verify the Tier-1 install path is live, not dangling. If `scaffold.json`'s schema doesn't currently list Tier-1 skills, log under deviation rather than invent schema. |

## Coupling note (the fourth duplication moment)

`tdd.py`'s `detect_runner` and `scaffold.py:_detect_tests` will check
the same signals. The two functions diverge in return type (`str |
None` vs. `bool`), so the *body* duplicates but the *signature*
doesn't.

Three prior decisions are relevant:

- **ADR-0002** (contracts deferred) named "three callers needing the
  shared helper" as one resolution trigger. We have three callers of
  the substring-match pattern (workflow / review / adr) and now a
  fourth conceptual duplication here (test-signal detection). But the
  duplication is *across patterns*, not *within one*.
- **Slice 004-01 deviation log** chose duplication for the
  substring-match. Reasoning: small function, stable regex.
- **Slice 005-01 deviation log** chose duplication again, even though
  the third caller fired the named trigger. Reasoning: the three
  call-sites use different regexes; the shared abstraction would be a
  thin wrapper around `[h for h in headings if frag.lower() in h.lower()]`.

For 006-01: **duplicate again**, with the same rationale. The
signal-detection body is ~40 lines split across three runner-specific
helpers; the abstraction would couple scaffold-init (one-shot
detection) and tdd-loop (live-session detection) for marginal benefit.
The two are *intentionally* independent — scaffold-init runs once at
project setup; tdd-loop runs every time Claude wants to test something.

The deviation log will tally this as the *fourth* duplication
moment and re-evaluate.

## Test strategy

### `DetectTests`
For each runner, build a tmp dir with the minimum signal file
(e.g. just `pytest.ini`) and assert `detect_runner(tmp) == "pytest"`.
Then a priority test: `pytest.ini + jest.config.js` → `pytest`.
Then a no-signal test: empty dir → returns `None`; CLI exits 2 with
the expected stderr.

```
DetectTests.test_pytest_via_pytest_ini
DetectTests.test_pytest_via_conftest
DetectTests.test_pytest_via_pyproject
DetectTests.test_pytest_via_test_file
DetectTests.test_pytest_via_test_suffix_file
DetectTests.test_vitest_via_config
DetectTests.test_vitest_via_package_json
DetectTests.test_jest_via_config
DetectTests.test_jest_via_package_json
DetectTests.test_priority_pytest_over_jest
DetectTests.test_priority_pytest_over_vitest
DetectTests.test_no_runner_returns_none
DetectTests.test_cli_no_runner_exits_2
DetectTests.test_cli_default_target_dot
```

### `RunTests`
Real subprocess invocation. Build a tmp dir with `pytest.ini` + two
test files: one that asserts `True` (pass), one that asserts `False`
(fail). Run `tdd.py run <tmp>` and observe:
- Two-test mix → exit 1
- One-test pass-only → exit 0
- Empty dir → exit 2 (no runner)

Skip JS-side run tests in this slice — vitest/jest require `npx` and
node_modules, not assumable in the jig dev env. Detection-only tests
are sufficient for vitest/jest.

```
RunTests.test_pytest_real_run_all_green
RunTests.test_pytest_real_run_one_red
RunTests.test_no_runner_exits_2
RunTests.test_missing_binary_exits_2  # via PATH manipulation
```

### `SkillSurfaceTests`
- Frontmatter has no `disable-model-invocation`.
- `user-invocable: true`.
- Description contains the auto-trigger phrases.
- Body references `tdd.py detect` and `tdd.py run`.
- Body references `agents/implementer.md` (linkage to the existing
  discipline encoder).

```
SkillSurfaceTests.test_frontmatter_active
SkillSurfaceTests.test_description_has_trigger_phrases
SkillSurfaceTests.test_body_references_subcommands
SkillSurfaceTests.test_body_references_implementer_agent
```

## Dogfood plan

After tests pass:
1. Run `python3 skills/tdd-loop/tdd.py detect .` against jig itself.
   Expected output: `pytest`.
2. Run `python3 skills/tdd-loop/tdd.py run skills/` against jig
   itself. Expected: exit 0 (all 191 + new tests green).
3. Build implementation-review prompt via `review.py`.
4. Spawn reviewer subagent.
5. Reconcile, second reviewer pass.

## Risks

- **AC #5 (scaffold.py update) is conditional.** If the current
  `scaffold.json` schema does NOT have a `tier_1_skills` list,
  AC #5 reduces to "verify no regression." The implementer should
  read `scaffold.py` first to determine which path applies and
  document the chosen path in the deviation log.
- **`npx` invocation in tests.** Tests only run pytest live. Vitest /
  jest live runs are out of scope; detection tests are sufficient.
  Document this in SKILL.md gotchas so users know JS-side run
  failures could be environment issues (no `node_modules`, no `npx`,
  etc.).
- **Shallow scan depth for `test_*.py` files.** Spec 001's
  signal-detection findings say "no recursion deeper than 2 levels."
  `_is_pytest`'s test-file
  scan walks root + direct subdirs only. Deep test trees (`tests/unit/`,
  `tests/integration/`) will miss — but the `pyproject.toml` /
  `pytest.ini` / `conftest.py` checks catch them anyway. Documented
  in gotchas.

## Out of scope

- `ac-coverage` subcommand → slice 006-02.
- Pre-commit hook → slice 006-03.
- rspec / `go test` / `cargo test` detection — no live signal in jig.
- Watch-mode integration — orthogonal to the discipline this slice
  codifies.
- Output parsing (number-of-tests, time elapsed, etc.) — streams
  through; consumers parse if they care.
