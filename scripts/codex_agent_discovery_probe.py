"""
codex_agent_discovery_probe.py - slice 059-06.

Builds jig's Codex plugin into a temporary marketplace, installs it with an
isolated CODEX_HOME, and probes whether plugin-bundled agent TOML files are
discoverable as Codex custom agents without running --install-codex-agents.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_codex_plugin  # noqa: E402
import install_contract  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
UNAVAILABLE = "UNAVAILABLE"

ROLE_AGENT_NAMES = tuple(
    f"jig-{agent}" for agent in install_contract.REQUIRED_AGENTS
)
UNSUPPORTED_AGENT_MANIFEST_FIELDS = (
    "agents",
    "agent",
    "custom_agents",
    "customAgents",
)
DISCOVERY_PROMPT = (
    "Probe whether installed plugin custom agents are available. "
    "Do not infer agent availability from this user prompt."
)
_JIG_PLUGIN_SELECTOR = "jig@jig"
_SURFACE_UNAVAILABLE_MARKERS = (
    "unrecognized subcommand",
    "unrecognized option",
    "unknown command",
    "invalid subcommand",
    "no such command",
    "not a recognized",
)


@dataclass(frozen=True)
class DiscoveryResult:
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


def _surface_failure_result(
    name: str,
    result: subprocess.CompletedProcess[str],
) -> DiscoveryResult:
    output = _combined_output(result).strip()
    status = UNAVAILABLE if _looks_surface_unavailable(output) else FAIL
    return DiscoveryResult(
        name,
        status,
        f"Codex command exited {result.returncode}: {output}",
    )


def _load_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return None, f"{path}: missing"
    except json.JSONDecodeError as exc:
        return None, f"{path}: invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, f"{path}: expected a JSON object"
    return data, None


def _validate_generated_agent_shape(plugin_dir: Path) -> DiscoveryResult:
    problems: list[str] = []
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest, error = _load_json(manifest_path)
    if error:
        problems.append(error)
    elif manifest is not None:
        for field in UNSUPPORTED_AGENT_MANIFEST_FIELDS:
            if field in manifest:
                problems.append(
                    f"{manifest_path}: unsupported plugin custom-agent "
                    f"field {field!r} must not be emitted"
                )

    expected = {f"{name}.toml" for name in ROLE_AGENT_NAMES}
    actual = {path.name for path in (plugin_dir / "agents").glob("jig-*.toml")}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        problems.append("missing agent TOML template(s): " + ", ".join(missing))
    if extra:
        problems.append("unexpected agent TOML template(s): " + ", ".join(extra))

    if problems:
        return DiscoveryResult(
            "generated-plugin-agent-shape",
            FAIL,
            "; ".join(problems),
        )
    return DiscoveryResult(
        "generated-plugin-agent-shape",
        PASS,
        (
            "plugin bundles jig-*.toml agent templates while leaving "
            ".codex-plugin/plugin.json free of unsupported agent fields"
        ),
    )


def _parse_installed_root(output: str, codex_home: Path) -> Path | None:
    marker = "Installed plugin root:"
    for line in output.splitlines():
        if marker in line:
            return Path(line.split(marker, 1)[1].strip())
    cache_root = codex_home / "plugins" / "cache" / "jig" / "jig"
    if not cache_root.is_dir():
        return None
    versions = sorted(path for path in cache_root.iterdir() if path.is_dir())
    return versions[-1] if versions else None


def _validate_plugin_cache_agent_templates(
    installed_root: Path | None,
) -> DiscoveryResult:
    if installed_root is None:
        return DiscoveryResult(
            "codex-plugin-cache-agent-templates",
            FAIL,
            "could not determine Codex installed plugin root after plugin add",
        )
    expected = {f"{name}.toml" for name in ROLE_AGENT_NAMES}
    actual = {path.name for path in (installed_root / "agents").glob("jig-*.toml")}
    missing = sorted(expected - actual)
    if missing:
        return DiscoveryResult(
            "codex-plugin-cache-agent-templates",
            FAIL,
            "installed plugin cache is missing agent TOML template(s): "
            + ", ".join(missing),
        )
    return DiscoveryResult(
        "codex-plugin-cache-agent-templates",
        PASS,
        "installed plugin cache carries jig-*.toml agent templates",
    )


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


def _validate_prompt_agent_discovery(prompt_json: str) -> DiscoveryResult:
    try:
        data = json.loads(prompt_json)
    except json.JSONDecodeError as exc:
        return DiscoveryResult(
            "codex-plugin-agent-discovery",
            FAIL,
            f"codex debug prompt-input did not emit JSON: {exc}",
        )
    joined = "\n".join(_prompt_input_texts(data))
    visible = [name for name in ROLE_AGENT_NAMES if name in joined]
    missing = [name for name in ROLE_AGENT_NAMES if name not in joined]
    if visible:
        missing_suffix = (
            ""
            if not missing
            else "; missing expected role(s): " + ", ".join(missing)
        )
        return DiscoveryResult(
            "codex-plugin-agent-discovery",
            PASS,
            (
                "plugin-native custom-agent discovery observed for "
                + ", ".join(visible)
                + missing_suffix
                + "; add a follow-up adapter slice before removing the "
                "explicit install helper"
            ),
        )
    return DiscoveryResult(
        "codex-plugin-agent-discovery",
        PASS,
        (
            "plugin-bundled agent templates were not exposed as custom "
            "agents by debug prompt-input; explicit --install-codex-agents "
            "helper remains the current contract"
        ),
    )


def _probe_live_codex(
    *,
    codex_bin: str,
    codex_home: Path,
    marketplace_root: Path,
    cwd: Path,
    runner: CommandRunner,
    timeout: int,
) -> list[DiscoveryResult]:
    codex_path = _resolve_codex(codex_bin)
    if codex_path is None:
        return [
            DiscoveryResult(
                "codex-cli",
                UNAVAILABLE,
                f"Codex CLI {codex_bin!r} was not found or is not executable",
            )
        ]

    codex_home.mkdir(parents=True, exist_ok=True)
    results: list[DiscoveryResult] = []

    version = _run_codex(
        codex_path,
        ["--version"],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if version.returncode != 0:
        return [_surface_failure_result("codex-cli", version)]
    results.append(DiscoveryResult("codex-cli", PASS, _combined_output(version).strip()))

    marketplace_add = _run_codex(
        codex_path,
        ["plugin", "marketplace", "add", str(marketplace_root)],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if marketplace_add.returncode != 0:
        results.append(_surface_failure_result("codex-marketplace-add", marketplace_add))
        return results
    results.append(
        DiscoveryResult(
            "codex-marketplace-add",
            PASS,
            _combined_output(marketplace_add).strip(),
        )
    )

    plugin_add = _run_codex(
        codex_path,
        ["plugin", "add", _JIG_PLUGIN_SELECTOR],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if plugin_add.returncode != 0:
        results.append(_surface_failure_result("codex-plugin-add", plugin_add))
        return results
    plugin_add_output = _combined_output(plugin_add)
    results.append(
        DiscoveryResult("codex-plugin-add", PASS, plugin_add_output.strip())
    )

    installed_root = _parse_installed_root(plugin_add_output, codex_home)
    results.append(_validate_plugin_cache_agent_templates(installed_root))

    prompt_input = _run_codex(
        codex_path,
        ["debug", "prompt-input", DISCOVERY_PROMPT],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if prompt_input.returncode != 0:
        results.append(
            _surface_failure_result("codex-plugin-agent-discovery", prompt_input)
        )
    else:
        results.append(_validate_prompt_agent_discovery(prompt_input.stdout))
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
) -> list[DiscoveryResult]:
    source_root = source_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    marketplace_root = work_root / "codex-plugin"
    plugin_dir = marketplace_root / "plugins" / "jig"

    build_code = build_codex_plugin.build(
        source_root=source_root,
        output_dir=plugin_dir,
    )
    results: list[DiscoveryResult] = []
    if build_code != 0:
        return [
            DiscoveryResult(
                "build-generated-package",
                FAIL,
                f"build_codex_plugin exited {build_code}",
            )
        ]
    results.append(
        DiscoveryResult(
            "build-generated-package",
            PASS,
            f"built Codex plugin package at {plugin_dir}",
        )
    )
    results.append(_validate_generated_agent_shape(plugin_dir))

    if skip_live_codex:
        results.append(
            DiscoveryResult(
                "codex-live-agent-discovery",
                UNAVAILABLE,
                "skipped by --skip-live-codex",
            )
        )
    else:
        results.extend(
            _probe_live_codex(
                codex_bin=codex_bin,
                codex_home=codex_home,
                marketplace_root=marketplace_root,
                cwd=source_root,
                runner=runner,
                timeout=timeout,
            )
        )
    return results


def _print_results(results: Sequence[DiscoveryResult], out) -> None:
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


def exit_code(
    results: Sequence[DiscoveryResult],
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
        prog="codex_agent_discovery_probe.py",
        description="probe whether Codex plugins expose bundled custom agents",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("JIG_CODEX_AGENT_DISCOVERY_CODEX_BIN", "codex"),
        help=(
            "Codex CLI executable to probe (default: "
            "JIG_CODEX_AGENT_DISCOVERY_CODEX_BIN or 'codex')"
        ),
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("JIG_CODEX_AGENT_DISCOVERY_CODEX_HOME"),
        help=(
            "isolated CODEX_HOME for live Codex probes (default: temp dir; "
            "also read from JIG_CODEX_AGENT_DISCOVERY_CODEX_HOME)"
        ),
    )
    parser.add_argument(
        "--skip-live-codex",
        action="store_true",
        default=os.environ.get("JIG_CODEX_AGENT_DISCOVERY_SKIP_LIVE") == "1",
        help=(
            "skip live Codex CLI probes and report them as UNAVAILABLE "
            "(also enabled by JIG_CODEX_AGENT_DISCOVERY_SKIP_LIVE=1)"
        ),
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
        work_root = Path(tempfile.mkdtemp(prefix="jig-codex-agent-discovery-"))
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

    with tempfile.TemporaryDirectory(prefix="jig-codex-agent-discovery-") as tmp:
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
