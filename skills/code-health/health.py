"""
jig code-health helper — slice 060-01 (Python + ruff)

Deterministic linter detection + subprocess-driven invocation, with
normalized exit codes so Claude can branch deterministically on the result.
The static-analysis sibling of `tdd.py`: detect the ecosystem → drive its
installed linter → normalize → print a tight summary → degrade to a
recommendation when no tool is available.

Two subcommands (mirroring tdd.py's `detect` / `run` shape):
  - `detect [target]`: print the resolved linter name (or exit 2 on miss).
  - `check [target]` : resolve + invoke ruff, parse the result, exit
                       0 (clean) / 1 (findings) / 2 (no runner / env error).

Per ADR-0002 + tdd.py's own deviation note: the `_read_text_safe` /
`_custom_command_file` / `_parse_custom_command` idioms here intentionally
**duplicate** the equivalents in `skills/tdd-loop/tdd.py` rather than
extracting a shared `_common` module. This is only the 2nd detect-and-drive
helper of its kind (tests + lint); the two have independent lifecycles
(test runner vs. linter) and diverge in detail (ephemeral-runner resolution
is lint-specific). ADR-0002's extract-trigger is the *third* caller — inline
mirror until then, exactly as tdd.py documents its duplication of scaffold.py.

Scope (slice 060-01): Python + ruff only. Node / complexity / duplication /
the reviewer pass / CI dogfood are later slices (060-02..05).
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path


# How many distinct rule codes to surface in the tight summary (spec 057 —
# a count + the top codes, not the raw ruff dump).
TOP_CODES = 5

# Recommendation printed when no linter is resolvable (AC #3).
NO_LINTER_MSG = (
    "no Python linter found — install ruff or run via pipx "
    "(e.g. `pipx run ruff check .` / `uvx ruff check .`)"
)


def _read_text_safe(path: Path) -> str:
    """Read text, swallowing all errors and returning "". Same as tdd.py."""
    try:
        return path.read_text()
    except Exception:
        return ""


def _custom_command_file(target: Path):
    """Return <target>/.jig/lint-command if it exists, else None.

    Mirrors tdd.py's `_custom_command_file` (which reads `.jig/test-command`)
    — same semantics, lint-command path."""
    p = target / ".jig" / "lint-command"
    return p if p.is_file() else None


def _parse_custom_command(cmd_file) -> str:
    """Return the first non-blank, non-comment line from cmd_file, or None.

    Identical parsing semantics to tdd.py's `_parse_custom_command`."""
    for line in _read_text_safe(cmd_file).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def resolve_lint_command(target: Path):
    """Resolve the argv to run, or None if nothing is available.

    Resolution order (AC #1, AC #4):
      1. `.jig/lint-command` override (honored verbatim, mirrors tdd.py).
      2. `ruff` on PATH                → `ruff check --output-format=json <dir>`.
      3. `uvx` on PATH (ephemeral)     → `uvx ruff check --output-format=json …`.
      4. `pipx` on PATH (ephemeral)    → `pipx run ruff check … <dir>`.
      5. nothing                       → None (caller degrades — AC #3).
    """
    cmd_file = _custom_command_file(target)
    if cmd_file is not None:
        cmd_str = _parse_custom_command(cmd_file)
        if cmd_str is not None:
            return shlex.split(cmd_str)
        # Empty / comment-only override falls through to auto-detection.

    ruff_args = ["check", "--output-format=json", str(target)]
    if shutil.which("ruff"):
        return ["ruff", *ruff_args]
    if shutil.which("uvx"):
        return ["uvx", "ruff", *ruff_args]
    if shutil.which("pipx"):
        return ["pipx", "run", "ruff", *ruff_args]
    return None


def _resolved_name(argv: list) -> str:
    """Human-readable name of a resolved command (for `detect` + summaries)."""
    if argv and argv[0] in ("uvx", "pipx"):
        return " ".join(argv[:2 if argv[0] == "uvx" else 3])
    return argv[0] if argv else "?"


def _summarize_findings(stdout: str):
    """Parse ruff's JSON output into (count, top_codes). Robust to non-JSON
    (e.g. a custom override that emits plain text) — returns (None, []) then,
    so the summary falls back to a generic line rather than crashing."""
    try:
        findings = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None, []
    if not isinstance(findings, list):
        return None, []
    codes = Counter(
        f.get("code") for f in findings
        if isinstance(f, dict) and f.get("code")
    )
    top = [code for code, _ in codes.most_common(TOP_CODES)]
    return len(findings), top


def cmd_detect(target: Path) -> int:
    """`detect` subcommand. Prints the resolved linter name; exit 2 on miss.

    Mirrors tdd.py's `detect`."""
    argv = resolve_lint_command(target)
    if argv is None:
        sys.stderr.write(NO_LINTER_MSG + "\n")
        return 2
    sys.stdout.write(_resolved_name(argv) + "\n")
    return 0


def cmd_check(target: Path) -> int:
    """`check` subcommand. Resolve + invoke the linter, parse the result,
    normalize the exit code (0 clean / 1 findings / 2 no-runner / env error).

    ruff's native exit code is 0 (clean) / 1 (has findings); we map it
    straight through, but a FileNotFoundError / OSError when launching the
    process means the binary/module is genuinely unavailable → 2 (the exact
    lesson tdd.py encodes for pytest: distinguish "tool absent" from "tool
    ran and found issues")."""
    argv = resolve_lint_command(target)
    if argv is None:
        # AC #3 — graceful degradation: one-line recommendation, no trace.
        sys.stderr.write(NO_LINTER_MSG + "\n")
        return 2

    try:
        result = subprocess.run(argv, cwd=str(target),
                                capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        sys.stderr.write(
            f"{argv[0]}: linter failed to start (is it installed?)\n"
        )
        return 2

    count, top = _summarize_findings(result.stdout)
    name = _resolved_name(argv)

    if result.returncode == 0:
        sys.stdout.write(f"{name}: clean — no findings\n")
        return 0

    # Non-zero: findings (the common case) — print a tight summary.
    if count is None:
        # Override emitted non-JSON; we can't count, so report generically.
        sys.stdout.write(f"{name}: findings reported (non-zero exit)\n")
    elif count == 0:
        # Non-zero exit but no parseable findings — surface ruff's stderr tail.
        tail = (result.stderr or "").strip().splitlines()
        hint = tail[-1] if tail else "ruff exited non-zero with no findings"
        sys.stdout.write(f"{name}: {hint}\n")
    else:
        codes = ", ".join(top) if top else "(no rule codes)"
        sys.stdout.write(
            f"{name}: {count} finding(s); top rules: {codes}\n"
        )
    return 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="health.py",
        description="jig code-health helper (detect / check)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("detect",
                        help="print the resolved linter name")
    pd.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")

    pc = sub.add_parser("check",
                        help="run the resolved linter against target")
    pc.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")

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
        if ns.cmd == "check":
            return cmd_check(target)
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"health.py failed: {exc}\n")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
