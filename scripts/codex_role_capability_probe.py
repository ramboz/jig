"""
codex_role_capability_probe.py - slice 059-05 (Codex role capability dogfood).

Builds a scratch Codex scaffold, validates jig's three custom-agent TOML files,
and probes local Codex CLI surfaces that are deterministic enough to automate.
Interactive named-agent spawning is intentionally reported as UNAVAILABLE when
the CLI debug surface does not expose it; the docs carry the manual command.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


ROOT = Path(__file__).resolve().parent.parent

PASS = "PASS"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"

ROLE_SANDBOX = {
    "jig-implementer": "workspace-write",
    "jig-reviewer": "read-only",
    "jig-architect": "read-only",
}

ROLE_SURFACE_PROMPT = "Exercise generated role capability diagnostics."

_SURFACE_UNAVAILABLE_MARKERS = (
    "unrecognized subcommand",
    "unrecognized option",
    "unknown command",
    "invalid subcommand",
    "no such command",
    "not a recognized",
)

_READ_ONLY_DENIAL_MARKERS = (
    "operation not permitted",
    "permissionerror",
    "read-only file system",
    "deny",
)

_SANDBOX_SETUP_FAILURE_MARKERS = (
    "sandbox_apply",
    "default_permissions requires",
    "unknown permissions profile",
)


@dataclass(frozen=True)
class ProbeResult:
    name: str
    status: str
    message: str


CommandRunner = Callable[
    [Sequence[str], Path | None, Mapping[str, str], int],
    subprocess.CompletedProcess[str],
]


def _run_command(
    args: Sequence[str],
    cwd: Path | None,
    env: Mapping[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    command = [str(arg) for arg in args]
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=stdout,
            stderr="\n".join(
                part for part in (stderr, f"command timed out after {timeout}s")
                if part
            ),
        )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _looks_surface_unavailable(text: str) -> bool:
    folded = text.lower()
    return any(marker in folded for marker in _SURFACE_UNAVAILABLE_MARKERS)


def _looks_read_only_denial(text: str) -> bool:
    folded = text.lower()
    return any(marker in folded for marker in _READ_ONLY_DENIAL_MARKERS)


def _looks_sandbox_setup_failure(text: str) -> bool:
    folded = text.lower()
    return any(marker in folded for marker in _SANDBOX_SETUP_FAILURE_MARKERS)


def _resolve_codex(codex_bin: str) -> str | None:
    if os.sep in codex_bin:
        path = Path(codex_bin)
        return str(path) if path.is_file() and os.access(path, os.X_OK) else None
    return shutil.which(codex_bin)


def _codex_env(codex_home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    env.setdefault("NO_COLOR", "1")
    env.setdefault("TERM", "dumb")
    return env


def _run_codex(
    codex_path: str,
    args: Sequence[str],
    *,
    codex_home: Path,
    cwd: Path,
    runner: CommandRunner,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return runner([codex_path, *args], cwd, _codex_env(codex_home), timeout)


def _install_codex_agents(
    *,
    source_root: Path,
    agents_dir: Path,
    runner: CommandRunner,
    timeout: int,
) -> ProbeResult | None:
    helper = source_root / "skills" / "scaffold-init" / "scaffold.py"
    if not helper.is_file():
        return ProbeResult(
            "codex-agent-install",
            FAIL,
            f"{helper}: missing --install-codex-agents helper",
        )
    result = runner(
        [
            sys.executable,
            str(helper),
            "--install-codex-agents",
            "--codex-agents-dir",
            str(agents_dir),
        ],
        source_root,
        {},
        timeout,
    )
    if result.returncode != 0:
        return ProbeResult(
            "codex-agent-install",
            FAIL,
            f"helper exited {result.returncode}: {_combined_output(result).strip()}",
        )
    return None


def _validate_agent_toml(agents_dir: Path) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    actual = {path.name for path in agents_dir.glob("jig-*.toml")}
    expected = {f"{role}.toml" for role in ROLE_SANDBOX}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        problems = []
        if missing:
            problems.append("missing " + ", ".join(missing))
        if extra:
            problems.append("unexpected " + ", ".join(extra))
        return [ProbeResult("codex-agent-roster", FAIL, "; ".join(problems))]

    results.append(
        ProbeResult(
            "codex-agent-roster",
            PASS,
            "found jig-implementer, jig-reviewer, and jig-architect TOML files",
        )
    )
    for role, expected_sandbox in ROLE_SANDBOX.items():
        path = agents_dir / f"{role}.toml"
        try:
            data = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as exc:
            results.append(ProbeResult(role, FAIL, f"{path}: invalid TOML: {exc}"))
            continue
        problems: list[str] = []
        if data.get("name") != role:
            problems.append(f"name must be {role!r}")
        if data.get("sandbox_mode") != expected_sandbox:
            problems.append(f"sandbox_mode must be {expected_sandbox!r}")
        instructions = data.get("developer_instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            problems.append("developer_instructions must be non-empty")
        elif "Codex adapter note" not in instructions:
            problems.append("developer_instructions must include Codex adapter note")
        if problems:
            results.append(ProbeResult(role, FAIL, "; ".join(problems)))
            continue
        write_semantics = (
            "can write inside the workspace boundary"
            if expected_sandbox == "workspace-write"
            else "cannot write without approval; read-only sandbox should block writes"
        )
        results.append(
            ProbeResult(
                role,
                PASS,
                f"sandbox_mode={expected_sandbox}; {write_semantics}",
            )
        )
    return results


def _prompt_input_texts(data: object) -> list[str]:
    texts: list[str] = []
    if isinstance(data, dict):
        if data.get("type") == "input_text" and isinstance(data.get("text"), str):
            texts.append(data["text"])
        for value in data.values():
            texts.extend(_prompt_input_texts(value))
    elif isinstance(data, list):
        for value in data:
            texts.extend(_prompt_input_texts(value))
    return texts


def _probe_agent_prompt_surface(
    *,
    codex_path: str,
    codex_home: Path,
    project_dir: Path,
    runner: CommandRunner,
    timeout: int,
) -> ProbeResult:
    result = _run_codex(
        codex_path,
        ["-C", str(project_dir), "debug", "prompt-input", ROLE_SURFACE_PROMPT],
        codex_home=codex_home,
        cwd=project_dir,
        runner=runner,
        timeout=timeout,
    )
    if result.returncode != 0:
        output = _combined_output(result).strip()
        status = UNAVAILABLE if _looks_surface_unavailable(output) else FAIL
        return ProbeResult(
            "codex-agent-prompt-surface",
            status,
            f"codex debug prompt-input exited {result.returncode}: {output}",
        )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return ProbeResult(
            "codex-agent-prompt-surface",
            FAIL,
            f"codex debug prompt-input did not emit JSON: {exc}",
        )
    joined = "\n".join(_prompt_input_texts(data))
    missing = [role for role in ROLE_SANDBOX if role not in joined]
    if missing:
        return ProbeResult(
            "codex-agent-prompt-surface",
            UNAVAILABLE,
            (
                "debug prompt-input did not expose custom-agent entries "
                f"({', '.join(missing)} absent); use an interactive subagent "
                "prompt and /agent to inspect named role threads"
            ),
        )
    return ProbeResult(
        "codex-agent-prompt-surface",
        PASS,
        "debug prompt-input exposes all generated jig custom-agent names",
    )


def _sandbox_subcommand(platform_name: str) -> str | None:
    if platform_name == "Darwin":
        return "macos"
    if platform_name == "Linux":
        return "linux"
    if platform_name == "Windows":
        return "windows"
    return None


def _probe_sandbox_profiles(
    *,
    codex_path: str,
    codex_home: Path,
    project_dir: Path,
    platform_name: str,
    runner: CommandRunner,
    timeout: int,
) -> list[ProbeResult]:
    sandbox_cmd = _sandbox_subcommand(platform_name)
    if sandbox_cmd is None:
        return [
            ProbeResult(
                "codex-sandbox-read-only-write-block",
                UNAVAILABLE,
                f"Codex sandbox probe is not implemented for {platform_name}",
            )
        ]

    read_only = _run_codex(
        codex_path,
        [
            "sandbox",
            sandbox_cmd,
            "--permissions-profile",
            ":read-only",
            "-C",
            str(project_dir),
            sys.executable,
            "-c",
            "from pathlib import Path; Path('blocked.txt').write_text('nope')",
        ],
        codex_home=codex_home,
        cwd=project_dir,
        runner=runner,
        timeout=timeout,
    )
    read_only_output = _combined_output(read_only).strip()
    if read_only.returncode == 0:
        read_result = ProbeResult(
            "codex-sandbox-read-only-write-block",
            FAIL,
            "read-only profile allowed a write to blocked.txt",
        )
    elif _looks_sandbox_setup_failure(read_only_output):
        read_result = ProbeResult(
            "codex-sandbox-read-only-write-block",
            UNAVAILABLE,
            f"read-only sandbox setup failed before write probe: {read_only_output}",
        )
    elif _looks_surface_unavailable(read_only_output):
        read_result = ProbeResult(
            "codex-sandbox-read-only-write-block",
            UNAVAILABLE,
            f"read-only sandbox probe unavailable: {read_only_output}",
        )
    elif _looks_read_only_denial(read_only_output):
        read_result = ProbeResult(
            "codex-sandbox-read-only-write-block",
            PASS,
            f"read-only write was blocked: {read_only_output.splitlines()[-1]}",
        )
    else:
        read_result = ProbeResult(
            "codex-sandbox-read-only-write-block",
            UNAVAILABLE,
            f"read-only sandbox probe exited {read_only.returncode}: {read_only_output}",
        )

    workspace = _run_codex(
        codex_path,
        [
            "sandbox",
            sandbox_cmd,
            "--permissions-profile",
            ":workspace",
            "-C",
            str(project_dir),
            sys.executable,
            "-c",
            "from pathlib import Path; Path('allowed.txt').write_text('ok')",
        ],
        codex_home=codex_home,
        cwd=project_dir,
        runner=runner,
        timeout=timeout,
    )
    workspace_output = _combined_output(workspace).strip()
    if workspace.returncode == 0 and (project_dir / "allowed.txt").is_file():
        workspace_result = ProbeResult(
            "codex-sandbox-workspace-write",
            PASS,
            "workspace profile allowed a write inside the scratch project",
        )
    elif _looks_sandbox_setup_failure(workspace_output):
        workspace_result = ProbeResult(
            "codex-sandbox-workspace-write",
            UNAVAILABLE,
            f"workspace sandbox setup failed before write probe: {workspace_output}",
        )
    elif _looks_surface_unavailable(workspace_output):
        workspace_result = ProbeResult(
            "codex-sandbox-workspace-write",
            UNAVAILABLE,
            f"workspace sandbox probe unavailable: {workspace_output}",
        )
    else:
        workspace_result = ProbeResult(
            "codex-sandbox-workspace-write",
            FAIL,
            f"workspace sandbox probe exited {workspace.returncode}: {workspace_output}",
        )
    return [read_result, workspace_result]


def _probe_live_codex(
    *,
    codex_bin: str,
    codex_home: Path,
    project_dir: Path,
    platform_name: str,
    runner: CommandRunner,
    timeout: int,
) -> list[ProbeResult]:
    codex_path = _resolve_codex(codex_bin)
    if codex_path is None:
        return [
            ProbeResult(
                "codex-cli",
                UNAVAILABLE,
                f"Codex CLI {codex_bin!r} was not found or is not executable",
            )
        ]
    codex_home.mkdir(parents=True, exist_ok=True)
    version = _run_codex(
        codex_path,
        ["--version"],
        codex_home=codex_home,
        cwd=project_dir,
        runner=runner,
        timeout=timeout,
    )
    if version.returncode != 0:
        output = _combined_output(version).strip()
        return [
            ProbeResult(
                "codex-cli",
                FAIL,
                f"codex --version exited {version.returncode}: {output}",
            )
        ]
    results = [
        ProbeResult("codex-cli", PASS, _combined_output(version).strip()),
        _probe_agent_prompt_surface(
            codex_path=codex_path,
            codex_home=codex_home,
            project_dir=project_dir,
            runner=runner,
            timeout=timeout,
        ),
    ]
    results.extend(
        _probe_sandbox_profiles(
            codex_path=codex_path,
            codex_home=codex_home,
            project_dir=project_dir,
            platform_name=platform_name,
            runner=runner,
            timeout=timeout,
        )
    )
    return results


def run_probe(
    *,
    source_root: Path = ROOT,
    work_root: Path,
    codex_home: Path,
    codex_bin: str = "codex",
    skip_live_codex: bool = False,
    runner: CommandRunner = _run_command,
    timeout: int = 30,
    platform_name: str | None = None,
) -> list[ProbeResult]:
    source_root = source_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    project_dir = work_root / "codex-role-project"
    agents_dir = project_dir / ".codex" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    results: list[ProbeResult] = []
    install_error = _install_codex_agents(
        source_root=source_root,
        agents_dir=agents_dir,
        runner=runner,
        timeout=timeout,
    )
    if install_error is not None:
        return [install_error]
    results.extend(_validate_agent_toml(agents_dir))

    if skip_live_codex:
        results.append(
            ProbeResult(
                "codex-live-role-surfaces",
                UNAVAILABLE,
                "skipped by --skip-live-codex",
            )
        )
    else:
        results.extend(
            _probe_live_codex(
                codex_bin=codex_bin,
                codex_home=codex_home,
                project_dir=project_dir,
                platform_name=platform_name or platform.system(),
                runner=runner,
                timeout=timeout,
            )
        )
    return results


def _print_results(results: Sequence[ProbeResult], out) -> None:
    for result in results:
        out.write(f"{result.status} {result.name}: {result.message}\n")
    counts = {
        PASS: sum(result.status == PASS for result in results),
        FAIL: sum(result.status == FAIL for result in results),
        UNAVAILABLE: sum(result.status == UNAVAILABLE for result in results),
    }
    out.write(
        "summary: "
        f"{counts[PASS]} passed, {counts[UNAVAILABLE]} unavailable, "
        f"{counts[FAIL]} failed\n"
    )


def exit_code(
    results: Sequence[ProbeResult],
    *,
    require_live_codex: bool,
) -> int:
    if any(result.status == FAIL for result in results):
        return 1
    if require_live_codex and any(result.status == UNAVAILABLE for result in results):
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_role_capability_probe.py",
        description="probe jig's generated Codex role-agent capability semantics",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("JIG_CODEX_ROLE_CODEX_BIN", "codex"),
        help="Codex CLI executable to probe (default: env or 'codex')",
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("JIG_CODEX_ROLE_CODEX_HOME"),
        help="isolated CODEX_HOME for live probes (default: temp dir)",
    )
    parser.add_argument(
        "--skip-live-codex",
        action="store_true",
        default=os.environ.get("JIG_CODEX_ROLE_SKIP_LIVE") == "1",
        help="skip live Codex CLI probes and report them as UNAVAILABLE",
    )
    parser.add_argument(
        "--require-live-codex",
        action="store_true",
        help="return exit 2 if any live Codex probe is UNAVAILABLE",
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
    explicit_home = Path(ns.codex_home).expanduser() if ns.codex_home else None

    if ns.keep_work:
        work_root = Path(tempfile.mkdtemp(prefix="jig-codex-role-"))
        codex_home = explicit_home or (work_root / "codex-home")
        results = run_probe(
            source_root=Path(ns.source_root),
            work_root=work_root,
            codex_home=codex_home,
            codex_bin=ns.codex_bin,
            skip_live_codex=ns.skip_live_codex,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        sys.stdout.write(f"work-root: {work_root}\n")
        sys.stdout.write(f"CODEX_HOME: {codex_home}\n")
        return exit_code(results, require_live_codex=ns.require_live_codex)

    with tempfile.TemporaryDirectory(prefix="jig-codex-role-") as tmp:
        work_root = Path(tmp)
        codex_home = explicit_home or (work_root / "codex-home")
        results = run_probe(
            source_root=Path(ns.source_root),
            work_root=work_root,
            codex_home=codex_home,
            codex_bin=ns.codex_bin,
            skip_live_codex=ns.skip_live_codex,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        return exit_code(results, require_live_codex=ns.require_live_codex)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
