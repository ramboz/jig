"""
Run the same checks as GitHub CI, in the same order.

Usage:
    python3 scripts/ci_check.py

This is intentionally broader than scripts/run_tests.py. The test wrapper is
the fast unit-test gate; this script is the before-push gate that also runs the
spec linter, manifest validator, code-health floor, and host package drift
guard.
"""

from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TextIO

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class CheckStep:
    name: str
    argv: tuple[str, ...]


def ci_steps(python: str = sys.executable) -> tuple[CheckStep, ...]:
    return (
        CheckStep("Run test suite", (python, "scripts/run_tests.py")),
        CheckStep("Lint specs", (python, "scripts/spec_lint.py", "--all")),
        CheckStep("Validate manifests", (python, "scripts/validate_manifests.py")),
        CheckStep(
            "Code-health floor",
            (python, "skills/code-health/health.py", "check", "."),
        ),
        CheckStep(
            "Host-package drift guard",
            (python, "scripts/build_host_packages.py", "--check"),
        ),
    )


def lint_command_launcher(root: Path = ROOT) -> str | None:
    path = root / ".jig" / "lint-command"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            argv = shlex.split(stripped)
        except ValueError:
            return None
        return argv[0] if argv else None
    return None


def dependencies_available(
    root: Path = ROOT,
    which: Callable[[str], str | None] = shutil.which,
    stderr: TextIO = sys.stderr,
) -> bool:
    launcher = lint_command_launcher(root)
    if launcher is None:
        return True
    if which(launcher):
        return True
    stderr.write(
        "missing local CI dependency: .jig/lint-command starts with "
        f"{launcher!r}, but {launcher!r} is not on PATH\n"
        "Install it before running the CI-equivalent local gate. This repo "
        "uses pipx to run the pinned ruff version used by code-health.\n"
    )
    return False


def run_steps(
    steps: tuple[CheckStep, ...],
    root: Path = ROOT,
    run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
) -> int:
    for step in steps:
        print(f"\n==> {step.name}", flush=True)
        result = run(step.argv, cwd=str(root))
        if result.returncode != 0:
            return result.returncode
    return 0


def main() -> int:
    if not dependencies_available():
        return 2
    return run_steps(ci_steps())


if __name__ == "__main__":
    sys.exit(main())
