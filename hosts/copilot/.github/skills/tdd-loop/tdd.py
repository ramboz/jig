"""
jig tdd-loop helper — slices 006-01, 006-04, 006-05

Deterministic test-runner detection + subprocess-driven invocation, with
normalized exit codes so Claude can branch deterministically on the result.

Two subcommands:
  - `detect [target]`               : print detected runner name (or exit 2).
  - `run [target] [--test-path P]`
    `run [target] [--test SELECTOR]`: invoke the runner, stream output, exit
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

from __future__ import annotations

import argparse
import importlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

# Signal sets — kept in module scope so tests can introspect if needed.
VITEST_DEPS = {"vitest"}
JEST_DEPS = {"jest"}
NODE_TEST_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
NODE_TEST_IMPORT_RE = re.compile(
    r"(?:from\s+[\"']node:test[\"']|require\(\s*[\"']node:test[\"']\s*\))"
)
NODE_TEST_SCRIPT_RE = re.compile(r"\bnode\b[^|&]*--test\b")
SHALLOW_SCAN_SKIP_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}

# Bug 021: selector capability for custom commands is an explicit opt-in —
# a {test} argv token in .jig/test-command marks where a selector belongs.
CUSTOM_SELECTOR_PLACEHOLDER = "{test}"


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


def _pkg_test_script(target: Path) -> str:
    pkg = _read_json_safe(target / "package.json")
    scripts = pkg.get("scripts") if isinstance(pkg, dict) else {}
    if not isinstance(scripts, dict):
        return ""
    test_script = scripts.get("test")
    return test_script if isinstance(test_script, str) else ""


def _has_test_files_shallow(target: Path) -> bool:
    """Look for `test_*.py` or `*_test.py` at root OR in any DIRECT subdir.
    Shallow scan only (max depth 2) — per spec 001's "no recursion deeper
    than 2 levels" signal-detection rule. Deep test trees (`tests/unit/`) miss here, but the
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


def _file_imports_node_test(path: Path) -> bool:
    if path.suffix not in NODE_TEST_EXTENSIONS:
        return False
    return NODE_TEST_IMPORT_RE.search(_read_text_safe(path)) is not None


def _has_node_test_import_shallow(target: Path) -> bool:
    try:
        for entry in target.iterdir():
            if entry.is_file() and _file_imports_node_test(entry):
                return True
            if entry.is_dir() and entry.name not in SHALLOW_SCAN_SKIP_DIRS:
                try:
                    for sub in entry.iterdir():
                        if sub.is_file() and _file_imports_node_test(sub):
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


def _parse_custom_command(cmd_file) -> str | None:
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


def _is_node(target: Path) -> bool:
    if NODE_TEST_SCRIPT_RE.search(_pkg_test_script(target)):
        return True
    if _has_node_test_import_shallow(target):
        return True
    return False


def detect_runner(target: Path):
    """Return the detected runner name, or None.

    Priority: custom (.jig/test-command) > pytest > vitest > jest > node."""
    cmd_file = _custom_command_file(target)
    if cmd_file is not None and _parse_custom_command(cmd_file) is not None:
        return "custom"
    if _is_pytest(target):
        return "pytest"
    if _is_vitest(target):
        return "vitest"
    if _is_jest(target):
        return "jest"
    if _is_node(target):
        return "node"
    return None


def _split_test_selector(selector: str | None) -> tuple[str | None, str | None]:
    """Split a test selector into optional path + optional test-name parts.

    The shared selector convention is pytest-like: `path::test_name`. For
    vitest/jest the path narrows the file set and the name maps to `-t`.
    A selector without `::` is treated as a runner-native atom: pytest gets
    it verbatim; JS runners treat path-looking strings as files and everything
    else as a test-name filter.
    """
    if selector is None:
        return None, None
    if "::" in selector:
        path_part, name_part = selector.split("::", 1)
        return path_part or None, name_part or None
    if (
        "/" in selector
        or "\\" in selector
        or selector.endswith((".py", ".js", ".jsx", ".ts", ".tsx"))
    ):
        return selector, None
    return None, selector


def _build_command(
    runner: str,
    path: Path,
    test_selector: str | None = None,
    *,
    explicit_path: bool = False,
) -> list:
    """Map runner name to argv. pytest goes via `python3 -m pytest` to avoid
    PATH-dependent shims; vitest + jest go via `npx` because we don't assume
    a local `vitest`/`jest` binary."""
    selector_path, selector_name = _split_test_selector(test_selector)
    if runner == "pytest":
        if test_selector:
            return [sys.executable, "-m", "pytest", test_selector]
        return [sys.executable, "-m", "pytest", str(path)]
    if runner == "vitest":
        cmd = ["npx", "vitest", "run", selector_path or str(path)]
        if selector_name:
            cmd.extend(["-t", selector_name])
        return cmd
    if runner == "jest":
        cmd = ["npx", "jest", selector_path or str(path)]
        if selector_name:
            cmd.extend(["-t", selector_name])
        return cmd
    if runner == "node":
        cmd = ["node", "--test"]
        if selector_name:
            cmd.extend(["--test-name-pattern", selector_name])
        if selector_path:
            cmd.append(selector_path)
        elif explicit_path:
            cmd.append(str(path))
        return cmd
    raise ValueError(f"unknown runner: {runner}")


def _selector_missed(runner: str, returncode: int, output: str) -> bool:
    """Return True when a targeted run failed because the selector found no test."""
    if runner == "node" and returncode == 0:
        lines = (line.strip().lower() for line in output.splitlines())
        return any(line in {"1..0", "# tests 0"} for line in lines)
    if returncode == 0:
        return False
    if runner == "pytest" and returncode in {4, 5}:
        return True
    if runner == "pytest":
        return False
    no_match_prefixes = (
        "no test found",
        "no tests found",
        "no matching tests",
        "your test suite must contain at least one test",
    )
    lines = (line.rstrip().lower() for line in output.splitlines())
    return any(
        any(line.startswith(prefix) for prefix in no_match_prefixes)
        for line in lines
    )


def _run_streaming(cmd: list[str], target: Path) -> tuple[int, str]:
    """Run a command while streaming combined output and retaining it for checks."""
    proc = subprocess.Popen(
        cmd,
        cwd=str(target),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_parts = []
    if proc.stdout is not None:
        for line in proc.stdout:
            output_parts.append(line)
            sys.stdout.write(line)
    return proc.wait(), "".join(output_parts)


def _run_command(cmd: list[str], target: Path, runner: str, test_selector: str | None) -> int:
    """Run the test command and normalize runner exit status."""
    try:
        if test_selector:
            returncode, output = _run_streaming(cmd, target)
            if _selector_missed(runner, returncode, output):
                sys.stderr.write(f"unresolved selector: {test_selector}\n")
                return 2
        else:
            result = subprocess.run(cmd, cwd=str(target))
            returncode = result.returncode
    except FileNotFoundError:
        # The runner binary itself is missing (e.g. `npx` not on PATH, or
        # `python3` shim absent). Normalize to 2 (env error) so callers
        # don't confuse "binary missing" with "tests failed".
        sys.stderr.write(
            f"{cmd[0]}: binary not found (is {runner} installed?)\n"
        )
        return 2
    return 0 if returncode == 0 else 1


def cmd_detect(target: Path) -> int:
    """`detect` subcommand. Prints runner name to stdout; exit 2 on miss."""
    runner = detect_runner(target)
    if runner is None:
        sys.stderr.write(f"no test runner detected at {target}\n")
        return 2
    sys.stdout.write(runner + "\n")
    return 0


def cmd_run(
    target: Path,
    test_path: Path | None,
    test_selector: str | None = None,
) -> int:
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
        # Bug 021: targeting is opt-in — a {test} token declares where the
        # selector belongs. Refusing beats silently running the whole suite,
        # which consumers (bug.py's red→green teeth) would misread as a
        # verdict on the named test.
        if test_selector and CUSTOM_SELECTOR_PLACEHOLDER not in argv:
            sys.stderr.write(
                "custom test command does not accept a test selector: add a "
                f"{CUSTOM_SELECTOR_PLACEHOLDER} placeholder to "
                ".jig/test-command where the selector belongs (refusing to "
                f"run the whole suite as a stand-in for {test_selector!r})\n"
            )
            return 2
        if test_selector:
            argv = [
                test_selector if tok == CUSTOM_SELECTOR_PLACEHOLDER else tok
                for tok in argv
            ]
            try:
                returncode, output = _run_streaming(argv, target)
            except (FileNotFoundError, OSError):
                sys.stderr.write(f"{argv[0]}: command failed to start\n")
                return 2
            if _selector_missed("custom", returncode, output):
                sys.stderr.write(f"unresolved selector: {test_selector}\n")
                return 2
            return 0 if returncode == 0 else 1
        argv = [tok for tok in argv if tok != CUSTOM_SELECTOR_PLACEHOLDER]
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

    cmd = _build_command(
        runner,
        test_path or target,
        test_selector,
        explicit_path=test_path is not None,
    )
    return _run_command(cmd, target, runner, test_selector)


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
    pr.add_argument("--test", default=None,
                    help="optional test selector, e.g. path::test_name")

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
            return cmd_run(target, test_path, ns.test)
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"tdd.py failed: {exc}\n")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
