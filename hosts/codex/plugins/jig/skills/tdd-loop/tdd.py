"""
jig tdd-loop helper — slices 006-01, 006-04, 006-05

Deterministic test-runner detection + subprocess-driven invocation, with
normalized exit codes so Claude can branch deterministically on the result.

Two subcommands:
  - `detect [target]`             : print detected runner name (or exit 2).
  - `run [target] [--test-path P]`: invoke the runner, stream output, exit
                                    0 (green) / 1 (red) / 2 (env error).

Mirrors the shape of workflow.py / review.py / memory.py / scaffold.py /
adr.py. Helper is deterministic; SKILL.md drives the judgment layer.

Per slice 006-01 plan + ADR-0002 + slices 004-01 / 005-01 deviation logs:
detection logic intentionally **duplicates** the signal scan in
`scaffold.py:_detect_tests` rather than extracting a `_common/signals.py`.
The two helpers diverge in return type (`str | None` vs. `bool`) and have
independent lifecycles (one-shot install detection vs. live-session
runner detection).
"""

import argparse
import importlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

# Signal sets — kept in module scope so tests can introspect if needed.
VITEST_DEPS = {"vitest"}
JEST_DEPS = {"jest"}


def _read_json_safe(path: Path) -> dict:
    """Read JSON, swallowing all errors and returning {}. Same as scaffold.py."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return ""


def _pkg_deps(target: Path) -> set:
    """Union of dependencies + devDependencies from package.json, or empty."""
    pkg = _read_json_safe(target / "package.json")
    if not pkg:
        return set()
    deps = set()
    for key in ("dependencies", "devDependencies"):
        deps.update((pkg.get(key) or {}).keys())
    return deps


def _has_test_files_shallow(target: Path) -> bool:
    """Look for `test_*.py` or `*_test.py` at root OR in any DIRECT subdir.
    Shallow scan only (max depth 2) — per Spike 001a's "no recursion deeper
    than 2 levels" rule. Deep test trees (`tests/unit/`) miss here, but the
    pyproject / pytest.ini / conftest checks catch those projects anyway."""
    def _is_test_file(name: str) -> bool:
        return (name.startswith("test_") and name.endswith(".py")) \
               or name.endswith("_test.py")

    try:
        for entry in target.iterdir():
            if entry.is_file() and _is_test_file(entry.name):
                return True
            if entry.is_dir():
                try:
                    for sub in entry.iterdir():
                        if sub.is_file() and _is_test_file(sub.name):
                            return True
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError, FileNotFoundError):
        return False
    return False


def _is_module_importable(name: str) -> bool:
    """Return True if the named module can be imported; False otherwise."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def _custom_command_file(target: Path):
    """Return the Path to <target>/.jig/test-command if it exists, else None."""
    p = target / ".jig" / "test-command"
    return p if p.is_file() else None


def _parse_custom_command(cmd_file) -> str:
    """Return the first non-blank, non-comment line from cmd_file, or None."""
    for line in _read_text_safe(cmd_file).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def _is_pytest(target: Path) -> bool:
    if (target / "pytest.ini").is_file():
        return True
    if (target / "conftest.py").is_file():
        return True
    if "[tool.pytest" in _read_text_safe(target / "pyproject.toml"):
        return True
    if _has_test_files_shallow(target):
        return True
    return False


def _is_vitest(target: Path) -> bool:
    for cfg in ("vitest.config.ts", "vitest.config.js", "vitest.config.mjs"):
        if (target / cfg).is_file():
            return True
    if _pkg_deps(target) & VITEST_DEPS:
        return True
    return False


def _is_jest(target: Path) -> bool:
    for cfg in ("jest.config.ts", "jest.config.js", "jest.config.json"):
        if (target / cfg).is_file():
            return True
    if _pkg_deps(target) & JEST_DEPS:
        return True
    return False


def detect_runner(target: Path):
    """Return the detected runner name, or None.

    Priority: custom (.jig/test-command) > pytest > vitest > jest."""
    cmd_file = _custom_command_file(target)
    if cmd_file is not None and _parse_custom_command(cmd_file) is not None:
        return "custom"
    if _is_pytest(target):
        return "pytest"
    if _is_vitest(target):
        return "vitest"
    if _is_jest(target):
        return "jest"
    return None


def _build_command(runner: str, path: Path) -> list:
    """Map runner name to argv. pytest goes via `python3 -m pytest` to avoid
    PATH-dependent shims; vitest + jest go via `npx` because we don't assume
    a local `vitest`/`jest` binary."""
    if runner == "pytest":
        return [sys.executable, "-m", "pytest", str(path)]
    if runner == "vitest":
        return ["npx", "vitest", "run", str(path)]
    if runner == "jest":
        return ["npx", "jest", str(path)]
    raise ValueError(f"unknown runner: {runner}")


def cmd_detect(target: Path) -> int:
    """`detect` subcommand. Prints runner name to stdout; exit 2 on miss."""
    runner = detect_runner(target)
    if runner is None:
        sys.stderr.write(f"no test runner detected at {target}\n")
        return 2
    sys.stdout.write(runner + "\n")
    return 0


def cmd_run(target: Path, test_path: Path) -> int:
    """`run` subcommand. Auto-detects, subprocess-invokes, streams output,
    normalizes the exit code (0 green / 1 red / 2 env error).

    Stdout/stderr are NOT captured — they stream through to the caller's
    terminal so the user sees real test output, not a swallowed summary.
    (Per AC #2: "Streams the runner's stdout/stderr through to the caller".)
    """
    # Custom command (.jig/test-command) takes priority over auto-detection.
    cmd_file = _custom_command_file(target)
    if cmd_file is not None:
        cmd_str = _parse_custom_command(cmd_file)
        if cmd_str is None:
            sys.stderr.write(".jig/test-command is empty (no runnable command found)\n")
            return 2
        argv = shlex.split(cmd_str)
        try:
            result = subprocess.run(argv, cwd=str(target))
        except (FileNotFoundError, OSError):
            sys.stderr.write(f"{argv[0]}: command failed to start\n")
            return 2
        return 0 if result.returncode == 0 else 1

    runner = detect_runner(target)
    if runner is None:
        sys.stderr.write(f"no test runner detected at {target}\n")
        return 2

    # Pre-flight: verify module availability for module-based runners.
    # `python3 -m pytest` exits 1 with stderr "No module named pytest" when
    # the module is absent — indistinguishable from red tests without this check.
    if runner == "pytest" and not _is_module_importable("pytest"):
        sys.stderr.write("pytest module is not installed (try: pip install pytest)\n")
        return 2

    cmd = _build_command(runner, test_path or target)
    try:
        result = subprocess.run(cmd, cwd=str(target))
    except FileNotFoundError:
        # The runner binary itself is missing (e.g. `npx` not on PATH, or
        # `python3` shim absent). Normalize to 2 (env error) so callers
        # don't confuse "binary missing" with "tests failed".
        sys.stderr.write(
            f"{cmd[0]}: binary not found (is {runner} installed?)\n"
        )
        return 2
    return 0 if result.returncode == 0 else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tdd.py",
        description="jig tdd-loop helper (detect / run)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("detect",
                        help="print the detected test runner name")
    pd.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")

    pr = sub.add_parser("run",
                        help="invoke the detected test runner against target")
    pr.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")
    pr.add_argument("--test-path", default=None,
                    help="optional explicit test path (defaults to target)")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    target = Path(ns.target).resolve()
    if not target.is_dir():
        sys.stderr.write(f"target is not a directory: {target}\n")
        return 2

    try:
        if ns.cmd == "detect":
            return cmd_detect(target)
        if ns.cmd == "run":
            test_path = Path(ns.test_path).resolve() if ns.test_path else None
            return cmd_run(target, test_path)
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"tdd.py failed: {exc}\n")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
