"""
Run all jig tests: one test per skill directory + the scripts directory.

Usage:
    python3 scripts/run_tests.py

This is the command pointed to by .jig/test-command, so:
    python3 skills/tdd-loop/tdd.py run .
...runs this script instead of trying to invoke pytest directly.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Ensure namespace-package imports (e.g. `from skills.migrate import migrate`) work.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_PYRIGHT_ARGS = ["--outputjson"]


def build_suite(root: Path = ROOT) -> unittest.TestSuite:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for skill_dir in sorted((root / "skills").iterdir()):
        if not skill_dir.is_dir():
            continue
        # Pycache and other dot-dirs only — `_common` IS a real test home
        # (shared parser tests). Slice 018-01 surfaced that the original
        # `_`-prefix skip silently dropped `skills/_common/test_parsing.py`.
        if skill_dir.name.startswith(".") or skill_dir.name == "__pycache__":
            continue
        # Python 3.11's unittest.discover raises ImportError on a dir with no
        # Python files (Python 3.12 silently returns an empty suite). Skip skill
        # dirs that have no test_*.py to keep both versions happy.
        if not any(skill_dir.glob("test_*.py")):
            continue
        # Skill directories use hyphens in their names (e.g.
        # `independent-review`) which are not valid Python module identifiers.
        # Python 3.11's unittest.discover rejects such directories as "not
        # importable" unless `top_level_dir == start_dir`, in which case the
        # importability check is skipped. Python 3.12 is more lenient. Pin
        # `top_level_dir` to make both versions behave identically.
        suite.addTests(loader.discover(
            start_dir=str(skill_dir),
            pattern="test_*.py",
            top_level_dir=str(skill_dir),
        ))

    suite.addTests(loader.discover(
        start_dir=str(root / "scripts"),
        pattern="test_*.py",
        top_level_dir=str(root / "scripts"),
    ))

    # Slice 026-01 — hook-helper and hook-integration tests under
    # hooks/scripts/{,lib}/. Same pattern as the skills loop: pin
    # top_level_dir per directory because the dir name contains a hyphen
    # in the parent path (`.claude/worktrees/…`), and so unittest needs an
    # explicit anchor for the importability check.
    for hook_test_dir in (root / "hooks" / "scripts", root / "hooks" / "scripts" / "lib"):
        if not hook_test_dir.is_dir():
            continue
        if not any(hook_test_dir.glob("test_*.py")):
            continue
        suite.addTests(loader.discover(
            start_dir=str(hook_test_dir),
            pattern="test_*.py",
            top_level_dir=str(hook_test_dir),
        ))

    return suite


def _resolve_pyright_gate() -> list[str] | None:
    """Resolve the jig-local pyright gate: PATH -> uvx -> pipx."""
    if shutil.which("pyright"):
        return ["pyright", *_PYRIGHT_ARGS]
    if shutil.which("uvx"):
        return ["uvx", "pyright", *_PYRIGHT_ARGS]
    if shutil.which("pipx"):
        return ["pipx", "run", "pyright", *_PYRIGHT_ARGS]
    return None


def _format_pyright_diagnostics(stdout: str, root: Path) -> str:
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, TypeError, ValueError):
        return "pyright: findings reported (unparseable output)"

    if not isinstance(report, dict):
        return "pyright: findings reported (unexpected output)"

    raw_summary = report.get("summary")
    summary = raw_summary if isinstance(raw_summary, dict) else {}
    errors = int(summary.get("errorCount", 0) or 0)
    warnings = int(summary.get("warningCount", 0) or 0)
    infos = int(summary.get("informationCount", 0) or 0)
    lines = [
        f"pyright: {errors} error(s), {warnings} warning(s), "
        f"{infos} information(s)"
    ]

    diagnostics = report.get("generalDiagnostics")
    if not isinstance(diagnostics, list):
        return "\n".join(lines)

    for diag in diagnostics[:10]:
        if not isinstance(diag, dict):
            continue
        raw_file = diag.get("file") or "<unknown>"
        try:
            path = Path(str(raw_file)).resolve().relative_to(root.resolve())
        except ValueError:
            path = Path(str(raw_file))
        start = diag.get("range", {}).get("start", {})
        line = int(start.get("line", 0) or 0) + 1
        rule = diag.get("rule") or diag.get("severity") or "diagnostic"
        message = str(diag.get("message") or "").splitlines()[0]
        lines.append(f"  {path}:{line}: {rule}: {message}")

    if len(diagnostics) > 10:
        lines.append(f"  ... {len(diagnostics) - 10} more diagnostic(s)")
    return "\n".join(lines)


def run_pyright_gate(root: Path = ROOT) -> bool:
    argv = _resolve_pyright_gate()
    if argv is None:
        sys.stderr.write(
            "pyright: no type checker found (install pyright, uvx, or pipx)\n"
        )
        return False

    try:
        result = subprocess.run(
            argv, cwd=str(root), capture_output=True, text=True,
        )
    except (FileNotFoundError, OSError) as exc:
        sys.stderr.write(f"pyright: failed to start ({exc})\n")
        return False

    if result.returncode == 0:
        sys.stderr.write("pyright: clean\n")
        return True

    sys.stderr.write(_format_pyright_diagnostics(result.stdout, root) + "\n")
    if result.stderr.strip():
        sys.stderr.write(result.stderr.strip() + "\n")
    return False


def main() -> int:
    result = unittest.TextTestRunner(verbosity=1).run(build_suite())
    pyright_ok = run_pyright_gate()
    return 0 if result.wasSuccessful() and pyright_ok else 1


if __name__ == "__main__":
    sys.exit(main())
