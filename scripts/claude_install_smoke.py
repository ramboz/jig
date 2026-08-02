"""
claude_install_smoke.py — slice 061-06 (Claude install-contract smoke).

The Claude-side sibling of `codex_install_smoke.py`. It proves the committed
`hosts/claude/` package and the `jig-claude-vX.Y.Z.zip` release archive install
and run correctly, independent of Codex:

  - the committed package is Claude-shaped (validates via install_contract,
    plus a guard that no dev-only dirs — scripts/docs/tests — leak in);
  - the repo-root `.claude-plugin/marketplace.json` resolves the `jig` plugin to
    `hosts/claude` (NOT `path: "."`);
  - the built release zip extracts to the expected FLAT Claude shape and passes
    the same contract;
  - a scaffold-helper invocation from inside the committed package executes
    (deterministic substitute proof the package runs);
  - when a real `claude` CLI is present, the smallest safe read-only probe
    (`claude plugin validate <path>`) is exercised on the package, the root
    marketplace manifest, and the extracted zip. Live probes deliberately use
    ONLY `plugin validate` (read-only); they never run `marketplace add` /
    `plugin install`, which mutate global Claude config. A missing or
    auth-blocked CLI reports UNAVAILABLE rather than pretending the live portion
    passed.

Every SmokeResult.name is `claude-…` and every failure message names the Claude
package/archive/CLI under test so it cannot be mistaken for a Codex failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_release_zip  # noqa: E402
import install_contract  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"

# Dev-only directories that must never appear inside a runtime Claude package
# (the committed hosts/claude/ tree is runtime-only — AC1). `scripts/` is NOT
# in this set: the runtime-scripts allowlist (install_contract.
# RELEASE_INCLUDE_SCRIPT_FILES) legitimately ships under it so
# `${CLAUDE_PLUGIN_ROOT}/scripts/…` resolves (bug 024/#167). A dedicated check
# below asserts `scripts/` carries ONLY that allowlist — no dev-only tooling.
_DEV_ONLY_DIRS: tuple[str, ...] = ("docs", "tests")

_SURFACE_UNAVAILABLE_MARKERS = (
    "unrecognized subcommand",
    "unrecognized option",
    "unknown command",
    "invalid subcommand",
    "no such command",
    "not a recognized",
    "command not found",
    "not logged in",
    "authentication",
    "unauthorized",
)


@dataclass(frozen=True)
class SmokeResult:
    name: str
    status: str
    message: str


# NB: this is a runtime type-alias *assignment*, so `from __future__ import
# annotations` does not stringify it — `Path | None` (PEP 604) would evaluate
# at import and raise on Python 3.9. Use Optional[Path] for the 3.9 floor.
CommandRunner = Callable[
    [Sequence[str], Optional[Path], Mapping[str, str], int],
    subprocess.CompletedProcess[str],
]


def _run_command(
    args: Sequence[str],
    cwd: Path | None,
    env: Mapping[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    command = list(args)
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=dict(env) if env else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_msg = f"command timed out after {timeout}s"
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=stdout,
            stderr="\n".join(part for part in (stderr, timeout_msg) if part),
        )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _looks_surface_unavailable(text: str) -> bool:
    folded = text.lower()
    return any(marker in folded for marker in _SURFACE_UNAVAILABLE_MARKERS)


# ---------------------------------------------------------------------------
# AC1 — committed package is Claude-shaped
# ---------------------------------------------------------------------------
def _validate_committed_package(plugin_root: Path) -> SmokeResult:
    problems = list(install_contract.validate_claude_package(plugin_root))
    for dev_dir in _DEV_ONLY_DIRS:
        if (plugin_root / dev_dir).exists():
            problems.append(
                f"{dev_dir}/: dev-only directory must NOT appear in the runtime "
                "Claude package (the package is install-only)"
            )
    # `scripts/` may exist, but only to carry the runtime-scripts allowlist
    # (bug 024/#167). Anything else under it is dev-only leakage.
    scripts_dir = plugin_root / "scripts"
    if scripts_dir.is_dir():
        shipped = {
            p.relative_to(plugin_root).as_posix()
            for p in scripts_dir.rglob("*")
            if p.is_file()
        }
        stray = sorted(shipped - set(install_contract.RELEASE_INCLUDE_SCRIPT_FILES))
        if stray:
            problems.append(
                "scripts/: only the runtime-scripts allowlist may ship; "
                f"unexpected file(s): {stray}"
            )
    if problems:
        return SmokeResult(
            "claude-committed-package",
            FAIL,
            f"committed Claude package at {plugin_root} FAILED contract — "
            + "; ".join(problems),
        )
    return SmokeResult(
        "claude-committed-package",
        PASS,
        f"committed Claude package at {plugin_root} is Claude-shaped "
        "(.claude-plugin/plugin.json, all skills/agents, no marketplace.json, "
        "no .codex-plugin/, no dev-only dirs)",
    )


# ---------------------------------------------------------------------------
# AC2 — remote-install pointer
# ---------------------------------------------------------------------------
def _jig_source_path(data: dict) -> str | None:
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        return None
    for entry in plugins:
        if isinstance(entry, dict) and entry.get("name") == "jig":
            source = entry.get("source")
            if isinstance(source, dict):
                path = source.get("path")
                return path if isinstance(path, str) else None
            if isinstance(source, str):
                return source
    return None


def _validate_remote_pointer(repo_root: Path) -> SmokeResult:
    manifest = repo_root / ".claude-plugin" / "marketplace.json"
    if not manifest.is_file():
        return SmokeResult(
            "claude-remote-pointer",
            FAIL,
            f"Claude remote-install pointer missing at {manifest}",
        )
    try:
        data = json.loads(manifest.read_text())
    except (ValueError, OSError) as exc:
        return SmokeResult(
            "claude-remote-pointer",
            FAIL,
            f"Claude marketplace.json at {manifest} is unreadable/invalid: {exc}",
        )
    if not isinstance(data, dict):
        return SmokeResult(
            "claude-remote-pointer",
            FAIL,
            f"Claude marketplace.json at {manifest}: top-level must be an object",
        )

    problems = install_contract.validate_marketplace_manifest(data)
    if problems:
        return SmokeResult(
            "claude-remote-pointer",
            FAIL,
            f"Claude marketplace.json at {manifest} FAILED contract — "
            + "; ".join(problems),
        )

    resolved = _jig_source_path(data)
    if resolved != "hosts/claude":
        return SmokeResult(
            "claude-remote-pointer",
            FAIL,
            f"Claude remote-install pointer resolves jig to {resolved!r}, "
            "expected 'hosts/claude' (must not be '.')",
        )
    return SmokeResult(
        "claude-remote-pointer",
        PASS,
        "Claude remote-install pointer resolves jig to 'hosts/claude' "
        "(not '.')",
    )


# ---------------------------------------------------------------------------
# AC3 — release archive
# ---------------------------------------------------------------------------
def _smoke_zip(zip_path: Path) -> SmokeResult:
    """Extract `zip_path` and assert the FLAT Claude shape + contract."""
    with tempfile.TemporaryDirectory(prefix="jig-claude-zip-") as tmp:
        extracted = Path(tmp)
        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extracted)
        except (zipfile.BadZipFile, OSError) as exc:
            return SmokeResult(
                "claude-release-archive",
                FAIL,
                f"Claude release zip {zip_path} could not be extracted: {exc}",
            )

        if not (extracted / ".claude-plugin" / "plugin.json").is_file():
            return SmokeResult(
                "claude-release-archive",
                FAIL,
                f"Claude release zip {zip_path} is not FLAT — "
                ".claude-plugin/plugin.json is not at the extract root",
            )

        problems = install_contract.validate_claude_package(extracted)
        if problems:
            return SmokeResult(
                "claude-release-archive",
                FAIL,
                f"extracted Claude release zip {zip_path} FAILED contract — "
                + "; ".join(problems),
            )
    return SmokeResult(
        "claude-release-archive",
        PASS,
        f"Claude release zip {zip_path} extracts FLAT "
        "(.claude-plugin/plugin.json at root) and passes the package contract",
    )


def _validate_release_archive(*, source_root: Path, work_root: Path) -> SmokeResult:
    hosts_root = source_root / "hosts"
    manifest = hosts_root / "claude" / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text()).get("version")
    except (ValueError, OSError) as exc:
        return SmokeResult(
            "claude-release-archive",
            FAIL,
            f"could not read committed Claude package version from {manifest}: {exc}",
        )
    if not version:
        return SmokeResult(
            "claude-release-archive",
            FAIL,
            f"committed Claude package manifest at {manifest} has no version",
        )

    work_root.mkdir(parents=True, exist_ok=True)
    zip_path = work_root / f"jig-claude-v{version}.zip"
    out = _CaptureOut()
    code = build_release_zip.build(
        host="claude",
        hosts_root=hosts_root,
        version=version,
        output_path=zip_path,
        out=out,
    )
    if code != 0:
        return SmokeResult(
            "claude-release-archive",
            FAIL,
            f"building Claude release zip failed (exit {code}): {out.text.strip()}",
        )
    return _smoke_zip(zip_path)


class _CaptureOut:
    def __init__(self) -> None:
        self.text = ""

    def write(self, chunk: str) -> None:
        self.text += chunk


# ---------------------------------------------------------------------------
# AC5 — scaffold-helper execution (deterministic substitute proof)
# ---------------------------------------------------------------------------
def _validate_scaffold_helper(
    plugin_root: Path,
    *,
    runner: CommandRunner = _run_command,
    timeout: int = 30,
) -> SmokeResult:
    helper = plugin_root / "skills" / "scaffold-init" / "scaffold.py"
    if not helper.is_file():
        return SmokeResult(
            "claude-scaffold-helper",
            FAIL,
            f"Claude package scaffold helper missing at {helper}",
        )
    result = runner([sys.executable, str(helper), "--help"], plugin_root, {}, timeout)
    if result.returncode != 0:
        return SmokeResult(
            "claude-scaffold-helper",
            FAIL,
            f"Claude package scaffold helper {helper} exited "
            f"{result.returncode}: {_combined_output(result).strip()}",
        )
    return SmokeResult(
        "claude-scaffold-helper",
        PASS,
        f"Claude package scaffold helper executes from {helper} (--help exit 0)",
    )


# ---------------------------------------------------------------------------
# AC4 — live Claude probe (read-only `plugin validate`)
# ---------------------------------------------------------------------------
def _resolve_claude(claude_bin: str) -> str | None:
    if os.sep in claude_bin:
        path = Path(claude_bin)
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(claude_bin)


def _claude_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.setdefault("TERM", "dumb")
    return env


def _validate_surface_result(
    name: str,
    target: Path,
    result: subprocess.CompletedProcess[str],
) -> SmokeResult:
    output = _combined_output(result).strip()
    if result.returncode == 0:
        return SmokeResult(
            name,
            PASS,
            f"`claude plugin validate {target}` passed: {output}",
        )
    status = UNAVAILABLE if _looks_surface_unavailable(output) else FAIL
    return SmokeResult(
        name,
        status,
        f"`claude plugin validate {target}` (Claude package) exited "
        f"{result.returncode}: {output}",
    )


def _probe_live_claude(
    *,
    claude_bin: str,
    source_root: Path,
    zip_extract_dir: Path | None,
    runner: CommandRunner,
    timeout: int,
) -> list[SmokeResult]:
    claude_path = _resolve_claude(claude_bin)
    if claude_path is None:
        return [
            SmokeResult(
                "claude-cli",
                UNAVAILABLE,
                f"Claude CLI {claude_bin!r} was not found or is not executable; "
                "ran the deterministic substitute instead",
            )
        ]

    env = _claude_env()
    results: list[SmokeResult] = []

    version = runner([claude_path, "--version"], source_root, env, timeout)
    if version.returncode != 0:
        output = _combined_output(version).strip()
        status = UNAVAILABLE if _looks_surface_unavailable(output) else FAIL
        return [
            SmokeResult(
                "claude-cli",
                status,
                f"Claude CLI `--version` exited {version.returncode}: {output}",
            )
        ]
    results.append(
        SmokeResult("claude-cli", PASS, _combined_output(version).strip())
    )

    package = source_root / "hosts" / "claude"
    pkg_result = runner(
        [claude_path, "plugin", "validate", str(package)], source_root, env, timeout
    )
    results.append(
        _validate_surface_result("claude-validate-package", package, pkg_result)
    )

    mp_result = runner(
        [claude_path, "plugin", "validate", str(source_root)], source_root, env, timeout
    )
    results.append(
        _validate_surface_result("claude-validate-marketplace", source_root, mp_result)
    )

    if zip_extract_dir is not None and zip_extract_dir.is_dir():
        zip_result = runner(
            [claude_path, "plugin", "validate", str(zip_extract_dir)],
            source_root,
            env,
            timeout,
        )
        results.append(
            _validate_surface_result(
                "claude-validate-archive", zip_extract_dir, zip_result
            )
        )
    return results


def run_smoke(
    *,
    source_root: Path = ROOT,
    work_root: Path,
    claude_bin: str = "claude",
    skip_live_claude: bool = False,
    require_live_claude: bool = False,
    runner: CommandRunner = _run_command,
    timeout: int = 30,
) -> list[SmokeResult]:
    source_root = source_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    package = source_root / "hosts" / "claude"
    results: list[SmokeResult] = [
        _validate_committed_package(package),
        _validate_remote_pointer(source_root),
        _validate_release_archive(source_root=source_root, work_root=work_root),
        _validate_scaffold_helper(package, runner=runner, timeout=timeout),
    ]

    # Extract the built zip once so the live probe can validate it too (AC4).
    zip_extract_dir: Path | None = None
    zip_path = next(work_root.glob("jig-claude-v*.zip"), None)
    if zip_path is not None:
        zip_extract_dir = work_root / "extracted-claude-zip"
        try:
            shutil.rmtree(zip_extract_dir, ignore_errors=True)
            zip_extract_dir.mkdir(parents=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(zip_extract_dir)
        except (zipfile.BadZipFile, OSError):
            zip_extract_dir = None

    if skip_live_claude:
        results.append(
            SmokeResult(
                "claude-live-surfaces",
                UNAVAILABLE,
                "skipped by --skip-live-claude; deterministic substitute is the "
                "pass/fail basis",
            )
        )
    else:
        results.extend(
            _probe_live_claude(
                claude_bin=claude_bin,
                source_root=source_root,
                zip_extract_dir=zip_extract_dir,
                runner=runner,
                timeout=timeout,
            )
        )
    return results


def _print_results(results: Sequence[SmokeResult], out) -> None:
    for result in results:
        out.write(f"{result.status} {result.name}: {result.message}\n")
    counts = {
        PASS: sum(1 for result in results if result.status == PASS),
        FAIL: sum(1 for result in results if result.status == FAIL),
        UNAVAILABLE: sum(1 for result in results if result.status == UNAVAILABLE),
    }
    out.write(
        "summary: "
        f"{counts[PASS]} passed, {counts[UNAVAILABLE]} unavailable, "
        f"{counts[FAIL]} failed\n"
    )


def exit_code(results: Sequence[SmokeResult], *, require_live_claude: bool) -> int:
    if any(result.status == FAIL for result in results):
        return 1
    if require_live_claude and any(
        result.status == UNAVAILABLE for result in results
    ):
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="claude_install_smoke.py",
        description="smoke-test jig's committed Claude plugin package and release zip",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--claude-bin",
        default=os.environ.get("JIG_CLAUDE_SMOKE_CLAUDE_BIN", "claude"),
        help=(
            "Claude CLI executable to probe (default: "
            "JIG_CLAUDE_SMOKE_CLAUDE_BIN or 'claude')"
        ),
    )
    parser.add_argument(
        "--skip-live-claude",
        "--no-live",
        dest="skip_live_claude",
        action="store_true",
        default=os.environ.get("JIG_CLAUDE_SMOKE_SKIP_LIVE") == "1",
        help=(
            "skip the live Claude CLI probe and report it as UNAVAILABLE "
            "(also enabled by JIG_CLAUDE_SMOKE_SKIP_LIVE=1)"
        ),
    )
    parser.add_argument(
        "--require-live-claude",
        action="store_true",
        help="return exit 2 if any live Claude probe is UNAVAILABLE",
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="keep the temporary work directory and print its path",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="timeout in seconds for each subprocess probe",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    ns = _build_parser().parse_args(list(argv)[1:])

    if ns.keep_work:
        work_root = Path(tempfile.mkdtemp(prefix="jig-claude-smoke-"))
        results = run_smoke(
            source_root=Path(ns.source_root),
            work_root=work_root,
            claude_bin=ns.claude_bin,
            skip_live_claude=ns.skip_live_claude,
            require_live_claude=ns.require_live_claude,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        sys.stdout.write(f"work-root: {work_root}\n")
        return exit_code(results, require_live_claude=ns.require_live_claude)

    with tempfile.TemporaryDirectory(prefix="jig-claude-smoke-") as tmp:
        results = run_smoke(
            source_root=Path(ns.source_root),
            work_root=Path(tmp),
            claude_bin=ns.claude_bin,
            skip_live_claude=ns.skip_live_claude,
            require_live_claude=ns.require_live_claude,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        return exit_code(results, require_live_claude=ns.require_live_claude)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
