"""
codex_install_smoke.py — slice 059-03 (Codex install-contract smoke).

Builds jig's generated Codex plugin package, validates the Codex-specific
package footprint, installs role-agent TOML templates into an isolated agents
directory, and probes the local Codex CLI plugin surfaces when they are
available. Live Codex probes are deliberately isolated with a temporary
CODEX_HOME by default; missing CLI/surface support reports UNAVAILABLE rather
than pretending the live portion passed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
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

_JIG_PLUGIN_SELECTOR = "jig@jig"
_CODEX_MARKETPLACE_PATH = ".agents/plugins/marketplace.json"
_CODEX_TRUST_BYPASS_FLAG = "--dangerously-bypass-hook-trust"
_SKILL_VISIBILITY_PROMPT = (
    "Set up this project with jig, run spec workflow, run independent review, "
    "run tdd loop, review this PR, review this architecture, clarify and "
    "analyze this spec."
)
_LIVE_SKILL_SENTINELS = (
    "jig:scaffold-init",
    "jig:spec-workflow",
    "jig:independent-review",
    "jig:tdd-loop",
    "jig:pr-review",
    "jig:arch-review",
    "jig:clarify",
    "jig:analyze",
)
_SURFACE_UNAVAILABLE_MARKERS = (
    "unrecognized subcommand",
    "unrecognized option",
    "unknown command",
    "invalid subcommand",
    "no such command",
    "not a recognized",
)


@dataclass(frozen=True)
class SmokeResult:
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
    command = list(args)
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


def _validate_codex_marketplace(marketplace_root: Path, plugin_dir: Path) -> list[str]:
    path = marketplace_root / _CODEX_MARKETPLACE_PATH
    data, error = _load_json(path)
    if error:
        return [error]
    assert data is not None

    problems: list[str] = []
    if data.get("name") != "jig":
        problems.append(f"{path}: name must be 'jig'")
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        problems.append(f"{path}: plugins must be a non-empty array")
        return problems
    entry = plugins[0]
    if not isinstance(entry, dict):
        return [f"{path}: plugins[0] must be an object"]
    if entry.get("name") != "jig":
        problems.append(f"{path}: plugins[0].name must be 'jig'")
    source = entry.get("source")
    if not isinstance(source, dict):
        problems.append(f"{path}: plugins[0].source must be an object")
        return problems
    if source.get("source") != "local":
        problems.append(f"{path}: plugins[0].source.source must be 'local'")
    rel_path = source.get("path")
    if not isinstance(rel_path, str) or not rel_path:
        problems.append(f"{path}: plugins[0].source.path must be non-empty")
        return problems
    if Path(rel_path).is_absolute() or ".." in Path(rel_path).parts:
        problems.append(
            f"{path}: plugins[0].source.path must be relative within the "
            "marketplace root"
        )
        return problems
    resolved = (marketplace_root / rel_path).resolve()
    if resolved != plugin_dir.resolve():
        problems.append(
            f"{path}: plugins[0].source.path resolves to {resolved}, "
            f"expected {plugin_dir.resolve()}"
        )
    return problems


def _validate_generated_package(plugin_dir: Path, marketplace_root: Path) -> SmokeResult:
    problems: list[str] = []

    manifest, error = _load_json(plugin_dir / ".codex-plugin" / "plugin.json")
    if error:
        problems.append(error)
    elif manifest is not None:
        problems.extend(install_contract.validate_codex_plugin_manifest(manifest))

    hooks, error = _load_json(plugin_dir / "hooks" / "hooks.json")
    if error:
        problems.append(error)
    elif hooks is not None:
        problems.extend(
            install_contract.validate_hooks(hooks, plugin_dir / "hooks" / "scripts")
        )

    problems.extend(install_contract.missing_skills(plugin_dir))
    problems.extend(_validate_codex_marketplace(marketplace_root, plugin_dir))

    if problems:
        return SmokeResult(
            "generated-package",
            FAIL,
            "; ".join(problems),
        )
    return SmokeResult(
        "generated-package",
        PASS,
        (
            "Codex manifest, rendered skills, hook config, hook scripts, and "
            "local marketplace descriptor are coherent"
        ),
    )


def _install_and_validate_codex_agents(
    plugin_dir: Path,
    agents_dir: Path,
    *,
    runner: CommandRunner = _run_command,
    timeout: int = 30,
) -> SmokeResult:
    helper = plugin_dir / "skills" / "scaffold-init" / "scaffold.py"
    if not helper.is_file():
        return SmokeResult(
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
        plugin_dir,
        {},
        timeout,
    )
    if result.returncode != 0:
        return SmokeResult(
            "codex-agent-install",
            FAIL,
            f"helper exited {result.returncode}: {_combined_output(result).strip()}",
        )

    expected_files = {
        f"jig-{agent}.toml" for agent in install_contract.REQUIRED_AGENTS
    }
    actual_files = {path.name for path in agents_dir.glob("jig-*.toml")}
    missing = sorted(expected_files - actual_files)
    extra = sorted(actual_files - expected_files)
    problems: list[str] = []
    if missing:
        problems.append(f"missing Codex agent TOML file(s): {', '.join(missing)}")
    if extra:
        problems.append(f"unexpected Codex agent TOML file(s): {', '.join(extra)}")

    for filename in sorted(expected_files & actual_files):
        path = agents_dir / filename
        try:
            data = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as exc:
            problems.append(f"{path}: invalid TOML: {exc}")
            continue
        role = filename.removeprefix("jig-").removesuffix(".toml")
        if data.get("name") != f"jig-{role}":
            problems.append(f"{path}: name must be 'jig-{role}'")
        if not isinstance(data.get("developer_instructions"), str) or not data.get(
            "developer_instructions"
        ):
            problems.append(f"{path}: developer_instructions must be non-empty")
        if role == "reviewer" and data.get("sandbox_mode") != "read-only":
            problems.append(f"{path}: reviewer sandbox_mode must be read-only")

    if problems:
        return SmokeResult("codex-agent-install", FAIL, "; ".join(problems))
    return SmokeResult(
        "codex-agent-install",
        PASS,
        f"installed and parsed {len(expected_files)} jig-*.toml role agent(s)",
    )


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
) -> SmokeResult:
    output = _combined_output(result).strip()
    status = UNAVAILABLE if _looks_surface_unavailable(output) else FAIL
    return SmokeResult(name, status, f"Codex command exited {result.returncode}: {output}")


def _parse_installed_root(output: str, codex_home: Path) -> Path | None:
    match = re.search(r"Installed plugin root:\s*(.+)", output)
    if match:
        return Path(match.group(1).strip())
    cache_root = codex_home / "plugins" / "cache" / "jig" / "jig"
    if not cache_root.is_dir():
        return None
    versions = sorted(path for path in cache_root.iterdir() if path.is_dir())
    return versions[-1] if versions else None


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


def _validate_skill_visibility(prompt_json: str) -> SmokeResult:
    try:
        data = json.loads(prompt_json)
    except json.JSONDecodeError as exc:
        return SmokeResult(
            "codex-skill-visibility",
            FAIL,
            f"codex debug prompt-input did not emit JSON: {exc}",
        )
    joined = "\n".join(_prompt_input_texts(data))
    missing = [
        skill for skill in _LIVE_SKILL_SENTINELS if skill not in joined
    ]
    if missing:
        return SmokeResult(
            "codex-skill-visibility",
            FAIL,
            "prompt-input is missing visible skill(s): " + ", ".join(missing),
        )
    return SmokeResult(
        "codex-skill-visibility",
        PASS,
        (
            "prompt-input exposes representative jig skills; full 15-skill "
            "presence is covered by generated-package"
        ),
    )


def _validate_live_hook_config(installed_root: Path | None) -> SmokeResult:
    if installed_root is None:
        return SmokeResult(
            "codex-hook-config",
            FAIL,
            "could not determine Codex installed plugin root after plugin add",
        )
    hooks_json = installed_root / "hooks" / "hooks.json"
    hooks, error = _load_json(hooks_json)
    if error:
        return SmokeResult("codex-hook-config", FAIL, error)
    assert hooks is not None
    problems = install_contract.validate_hooks(
        hooks, installed_root / "hooks" / "scripts"
    )
    if problems:
        return SmokeResult("codex-hook-config", FAIL, "; ".join(problems))
    count = len(install_contract.parse_hook_script_names(hooks))
    return SmokeResult(
        "codex-hook-config",
        PASS,
        f"installed plugin cache exposes hooks/hooks.json with {count} script(s)",
    )


def _validate_hook_trust_surface(
    help_text: str,
    features_text: str,
    codex_home: Path,
) -> SmokeResult:
    if _CODEX_TRUST_BYPASS_FLAG not in help_text:
        return SmokeResult(
            "codex-hook-trust-state",
            UNAVAILABLE,
            (
                "Codex CLI help does not expose hook-trust enforcement "
                f"marker {_CODEX_TRUST_BYPASS_FLAG}"
            ),
        )
    if not _feature_is_listed(features_text, "plugin_hooks") or not _feature_is_listed(
        features_text,
        "hooks",
    ):
        return SmokeResult(
            "codex-hook-trust-state",
            UNAVAILABLE,
            "Codex features output does not expose hooks/plugin_hooks state",
        )

    config_text = (codex_home / "config.toml").read_text() if (
        codex_home / "config.toml"
    ).is_file() else ""
    if "trusted" in config_text.lower() and "hook" in config_text.lower():
        message = "isolated CODEX_HOME carries persisted hook trust metadata"
    else:
        message = (
            "hook trust enforcement surface is present; isolated config.toml "
            "has no persisted hook trust, so jig hooks remain pending /hooks review"
        )
    return SmokeResult("codex-hook-trust-state", PASS, message)


def _feature_is_listed(features_text: str, feature: str) -> bool:
    boundary = r"(?<![A-Za-z0-9_-]){}(?![A-Za-z0-9_-])"
    return re.search(boundary.format(re.escape(feature)), features_text) is not None


def _probe_live_codex(
    *,
    codex_bin: str,
    codex_home: Path,
    marketplace_root: Path,
    cwd: Path,
    runner: CommandRunner,
    timeout: int,
) -> list[SmokeResult]:
    codex_path = _resolve_codex(codex_bin)
    if codex_path is None:
        return [
            SmokeResult(
                "codex-cli",
                UNAVAILABLE,
                f"Codex CLI {codex_bin!r} was not found or is not executable",
            )
        ]

    codex_home.mkdir(parents=True, exist_ok=True)

    results: list[SmokeResult] = []
    version = _run_codex(
        codex_path, ["--version"], codex_home=codex_home, cwd=cwd,
        runner=runner, timeout=timeout,
    )
    if version.returncode != 0:
        return [_surface_failure_result("codex-cli", version)]
    results.append(
        SmokeResult("codex-cli", PASS, _combined_output(version).strip())
    )

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
        SmokeResult(
            "codex-marketplace-add",
            PASS,
            _combined_output(marketplace_add).strip(),
        )
    )

    plugin_list = _run_codex(
        codex_path,
        ["plugin", "list"],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if plugin_list.returncode != 0:
        results.append(_surface_failure_result("codex-plugin-list", plugin_list))
        return results
    if _JIG_PLUGIN_SELECTOR not in _combined_output(plugin_list):
        results.append(
            SmokeResult(
                "codex-plugin-list",
                FAIL,
                "codex plugin list did not show jig@jig after marketplace add",
            )
        )
        return results

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
        SmokeResult("codex-plugin-add", PASS, plugin_add_output.strip())
    )

    installed_root = _parse_installed_root(plugin_add_output, codex_home)
    results.append(_validate_live_hook_config(installed_root))

    prompt_input = _run_codex(
        codex_path,
        ["debug", "prompt-input", _SKILL_VISIBILITY_PROMPT],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if prompt_input.returncode != 0:
        results.append(_surface_failure_result("codex-skill-visibility", prompt_input))
    else:
        results.append(_validate_skill_visibility(prompt_input.stdout))

    help_result = _run_codex(
        codex_path,
        ["--help"],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    features_result = _run_codex(
        codex_path,
        ["features", "list"],
        codex_home=codex_home,
        cwd=cwd,
        runner=runner,
        timeout=timeout,
    )
    if help_result.returncode != 0:
        results.append(_surface_failure_result("codex-hook-trust-state", help_result))
    elif features_result.returncode != 0:
        results.append(_surface_failure_result("codex-hook-trust-state", features_result))
    else:
        results.append(
            _validate_hook_trust_surface(
                _combined_output(help_result),
                _combined_output(features_result),
                codex_home,
            )
        )

    return results


def run_smoke(
    *,
    source_root: Path = ROOT,
    work_root: Path,
    codex_home: Path,
    codex_bin: str = "codex",
    skip_live_codex: bool = False,
    require_live_codex: bool = False,
    runner: CommandRunner = _run_command,
    timeout: int = 30,
) -> list[SmokeResult]:
    source_root = source_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    marketplace_root = work_root / "codex-plugin"
    plugin_dir = marketplace_root / "plugins" / "jig"
    agents_dir = work_root / "codex-agents"

    build_code = build_codex_plugin.build(
        source_root=source_root,
        output_dir=plugin_dir,
    )
    results: list[SmokeResult] = []
    if build_code != 0:
        return [
            SmokeResult(
                "build-generated-package",
                FAIL,
                f"build_codex_plugin exited {build_code}",
            )
        ]
    results.append(
        SmokeResult(
            "build-generated-package",
            PASS,
            f"built Codex plugin package at {plugin_dir}",
        )
    )
    results.append(_validate_generated_package(plugin_dir, marketplace_root))
    results.append(
        _install_and_validate_codex_agents(
            plugin_dir, agents_dir, runner=runner, timeout=timeout
        )
    )

    if skip_live_codex:
        results.append(
            SmokeResult(
                "codex-live-surfaces",
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


def exit_code(results: Sequence[SmokeResult], *, require_live_codex: bool) -> int:
    if any(result.status == FAIL for result in results):
        return 1
    if require_live_codex and any(result.status == UNAVAILABLE for result in results):
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_install_smoke.py",
        description="build and smoke-test jig's generated Codex plugin package",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--codex-bin",
        default=os.environ.get("JIG_CODEX_SMOKE_CODEX_BIN", "codex"),
        help=(
            "Codex CLI executable to probe (default: "
            "JIG_CODEX_SMOKE_CODEX_BIN or 'codex')"
        ),
    )
    parser.add_argument(
        "--codex-home",
        default=os.environ.get("JIG_CODEX_SMOKE_CODEX_HOME"),
        help=(
            "isolated CODEX_HOME for live Codex probes (default: a temp dir; "
            "also read from JIG_CODEX_SMOKE_CODEX_HOME)"
        ),
    )
    parser.add_argument(
        "--skip-live-codex",
        action="store_true",
        default=os.environ.get("JIG_CODEX_SMOKE_SKIP_LIVE") == "1",
        help=(
            "skip live Codex CLI probes and report them as UNAVAILABLE "
            "(also enabled by JIG_CODEX_SMOKE_SKIP_LIVE=1)"
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
        work_root = Path(tempfile.mkdtemp(prefix="jig-codex-smoke-"))
        codex_home = explicit_home or (work_root / "codex-home")
        results = run_smoke(
            source_root=Path(ns.source_root),
            work_root=work_root,
            codex_home=codex_home,
            codex_bin=ns.codex_bin,
            skip_live_codex=ns.skip_live_codex,
            require_live_codex=ns.require_live_codex,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        sys.stdout.write(f"work-root: {work_root}\n")
        sys.stdout.write(f"CODEX_HOME: {codex_home}\n")
        return exit_code(results, require_live_codex=ns.require_live_codex)

    with tempfile.TemporaryDirectory(prefix="jig-codex-smoke-") as tmp:
        work_root = Path(tmp)
        codex_home = explicit_home or (work_root / "codex-home")
        results = run_smoke(
            source_root=Path(ns.source_root),
            work_root=work_root,
            codex_home=codex_home,
            codex_bin=ns.codex_bin,
            skip_live_codex=ns.skip_live_codex,
            require_live_codex=ns.require_live_codex,
            timeout=ns.timeout,
        )
        _print_results(results, sys.stdout)
        return exit_code(results, require_live_codex=ns.require_live_codex)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
