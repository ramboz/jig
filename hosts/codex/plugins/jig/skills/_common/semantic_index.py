"""Host-neutral semantic-index activation helper.

Slice 080-01: this module is intentionally stdlib-only so Claude and Codex
adapters can both call it from generated hook/prose surfaces. It owns only the
shared contract: project opt-in state, provider selection, bounded readiness,
worktree policy, and content-free telemetry. Host-specific rendering lives in
later slices.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

try:
    from .atomic_io import atomic_write_text
except ImportError:  # pragma: no cover - supports direct script-style imports.
    from atomic_io import atomic_write_text

STATE_RELATIVE_PATH = Path(".jig") / "semantic-index.json"
TELEMETRY_RELATIVE_PATH = Path(".jig") / "semantic-index-events.jsonl"
PUBLIC_DEFAULT_PROVIDER = "tokensave"
INTERNAL_OVERLAY_ENV = "JIG_SEMANTIC_INDEX_INTERNAL"
PUBLIC_PROVIDER_CANDIDATES = (
    "tokensave",
    "codebase-memory-mcp",
    "symdex",
    "cocoindex-code",
)


@dataclass(frozen=True)
class ActivationState:
    """Project-local semantic-index opt-in state."""

    auto_attach: bool = False
    provider: str = PUBLIC_DEFAULT_PROVIDER
    allowed_overlays: tuple[str, ...] = ()
    per_worktree_indexing: bool = False
    timeout_seconds: float = 5.0


@dataclass(frozen=True)
class ProviderMetadata:
    name: str
    profile: str
    executable: str
    overlay: str | None = None
    public_default: bool = False


@dataclass(frozen=True)
class RepoRoot:
    requested: Path
    canonical: Path
    selected: Path
    root_class: str


@dataclass(frozen=True)
class ActivationResult:
    provider: str | None
    provider_profile: str
    action: str
    outcome: str
    repo_root_class: str
    considered_root: str
    auto_attach: bool
    recommendation: str | None = None


class Provider:
    """Minimal provider-neutral contract consumed by host adapters."""

    metadata: ProviderMetadata

    def detect(self) -> bool:
        raise NotImplementedError

    def status(self, repo_root: Path, timeout_seconds: float) -> str:
        raise NotImplementedError

    def ensure_ready(self, repo_root: Path, timeout_seconds: float) -> str:
        raise NotImplementedError

    def recommendation(self, project_root: Path) -> str:
        return (
            f"Semantic index provider '{self.metadata.name}' is available. "
            f"Opt in by creating {STATE_RELATIVE_PATH} with auto_attach=true."
        )


Runner = Callable[[list[str], float], subprocess.CompletedProcess]


def _run_command(argv: list[str], timeout_seconds: float) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout_seconds,
    )


class CommandProvider(Provider):
    """Provider backed by small, bounded CLI status/attach commands."""

    def __init__(
        self,
        metadata: ProviderMetadata,
        *,
        status_args: Iterable[str] | None = None,
        attach_args: Iterable[str] | None = None,
        daemon_status_args: Iterable[str] | None = None,
        daemon_start_args: Iterable[str] | None = None,
        runner: Runner = _run_command,
    ) -> None:
        self.metadata = metadata
        self._status_args = tuple(status_args or ())
        self._attach_args = tuple(attach_args or ())
        self._daemon_status_args = tuple(daemon_status_args or ())
        self._daemon_start_args = tuple(daemon_start_args or ())
        self._runner = runner

    def detect(self) -> bool:
        return shutil.which(self.metadata.executable) is not None

    def _command(self, args: tuple[str, ...], repo_root: Path | None = None) -> list[str]:
        command = [self.metadata.executable]
        for arg in args:
            command.append(str(repo_root) if arg == "{repo_root}" else arg)
        return command

    def _ok(self, args: tuple[str, ...], repo_root: Path, timeout_seconds: float) -> bool:
        if not args:
            return False
        try:
            completed = self._runner(self._command(args, repo_root), timeout_seconds)
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
        return completed.returncode == 0

    def status(self, repo_root: Path, timeout_seconds: float) -> str:
        if not self.detect():
            return "provider_missing"
        if not self._status_args:
            return "status_unavailable"
        return "ready" if self._ok(self._status_args, repo_root, timeout_seconds) else "not_ready"

    def ensure_ready(self, repo_root: Path, timeout_seconds: float) -> str:
        current = self.status(repo_root, timeout_seconds)
        if current == "ready":
            return "ready"
        if current == "provider_missing":
            return current
        if self._daemon_status_args and not self._ok(
            self._daemon_status_args, repo_root, timeout_seconds
        ):
            if self._daemon_start_args and not self._ok(
                self._daemon_start_args, repo_root, timeout_seconds
            ):
                return "fallback_failed"
        if self._attach_args and self._ok(self._attach_args, repo_root, timeout_seconds):
            return "attach_started"
        return "not_ready"


def builtin_registry(
    *,
    allow_internal_overlays: bool = False,
    runner: Runner = _run_command,
) -> dict[str, Provider]:
    """Return providers available to public jig, plus overlays when allowed."""

    providers: dict[str, Provider] = {}
    for candidate in PUBLIC_PROVIDER_CANDIDATES:
        providers[candidate] = CommandProvider(
            ProviderMetadata(
                name=candidate,
                profile="public",
                executable=candidate,
                public_default=candidate == PUBLIC_DEFAULT_PROVIDER,
            ),
            status_args=("status", "{repo_root}"),
            attach_args=("index", "{repo_root}"),
            runner=runner,
        )
    if allow_internal_overlays:
        providers["scout"] = CommandProvider(
            ProviderMetadata(
                name="scout",
                profile="internal-overlay",
                executable="scout",
                overlay="scout",
            ),
            status_args=("status", "{repo_root}"),
            daemon_status_args=("daemon", "status"),
            daemon_start_args=("daemon", "start"),
            attach_args=("attach", "{repo_root}"),
            runner=runner,
        )
    return providers


def load_state(project_root: Path) -> ActivationState:
    path = project_root / STATE_RELATIVE_PATH
    if not path.is_file():
        return ActivationState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ActivationState()
    overlays = (
        raw["allowed_overlays"]
        if "allowed_overlays" in raw
        else raw.get("internal_overlays") or []
    )
    if isinstance(overlays, str):
        overlays = [overlays]
    timeout = raw.get("timeout_seconds", ActivationState.timeout_seconds)
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError):
        timeout_value = ActivationState.timeout_seconds
    return ActivationState(
        auto_attach=_json_bool(raw.get("auto_attach", False)),
        provider=str(raw.get("provider") or PUBLIC_DEFAULT_PROVIDER),
        allowed_overlays=tuple(str(item) for item in overlays),
        per_worktree_indexing=_json_bool(raw.get("per_worktree_indexing", False)),
        timeout_seconds=timeout_value,
    )


def _json_bool(value: object) -> bool:
    """Return True only for an explicit JSON boolean true."""

    return value is True


def write_state(project_root: Path, state: ActivationState) -> Path:
    path = project_root / STATE_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    payload["allowed_overlays"] = list(state.allowed_overlays)
    atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _git_output(project_dir: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def resolve_repo_root(project_dir: Path, *, per_worktree_indexing: bool = False) -> RepoRoot:
    requested = project_dir.resolve()
    worktree = _git_output(requested, ["rev-parse", "--show-toplevel"])
    common = _git_output(requested, ["rev-parse", "--git-common-dir"])
    current_root = Path(worktree).resolve() if worktree else requested
    canonical = current_root
    if common:
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = (requested / common_path).resolve()
        if common_path.name == ".git":
            canonical = common_path.parent.resolve()
    root_class = "canonical" if current_root == canonical else "worktree"
    selected = current_root if per_worktree_indexing else canonical
    if not worktree:
        root_class = "unknown"
        selected = requested
        canonical = requested
    return RepoRoot(
        requested=current_root,
        canonical=canonical,
        selected=selected,
        root_class=root_class,
    )


def _overlay_allowed(state: ActivationState, overlay: str | None) -> bool:
    if os.environ.get(INTERNAL_OVERLAY_ENV) == "1":
        return True
    if not overlay:
        return False
    return overlay in state.allowed_overlays


def _scout_overlay_allowed(state: ActivationState) -> bool:
    return _overlay_allowed(state, "scout")


def _select_provider(
    state: ActivationState, providers: dict[str, Provider]
) -> tuple[Provider | None, str | None]:
    requested = state.provider or PUBLIC_DEFAULT_PROVIDER
    provider = providers.get(requested)
    if provider is not None:
        overlay = _provider_overlay_name(requested, provider)
        if _provider_requires_overlay(requested, provider) and not _overlay_allowed(
            state, overlay
        ):
            return None, "overlay_disabled"
        return provider, None
    if requested == "scout":
        return None, "overlay_disabled"
    if requested == PUBLIC_DEFAULT_PROVIDER:
        return None, "provider_missing"
    return None, "provider_missing"


def _provider_requires_overlay(requested: str, provider: Provider) -> bool:
    metadata = provider.metadata
    return (
        requested == "scout"
        or metadata.name == "scout"
        or metadata.profile == "internal-overlay"
        or metadata.overlay is not None
    )


def _provider_overlay_name(requested: str, provider: Provider) -> str | None:
    if requested == "scout" or provider.metadata.name == "scout":
        return "scout"
    return provider.metadata.overlay or provider.metadata.name


def record_telemetry(
    project_root: Path,
    result: ActivationResult,
    *,
    host: str = "unknown",
    now: Callable[[], float] = time.time,
) -> None:
    """Append one content-free activation event. Fail open on all I/O errors."""

    event = {
        "timestamp": int(now()),
        "host": host,
        "provider": result.provider,
        "provider_profile": result.provider_profile,
        "action": result.action,
        "outcome": result.outcome,
        "repo_root_class": result.repo_root_class,
    }
    try:
        path = project_root / TELEMETRY_RELATIVE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    except Exception:
        pass


def activate(
    project_dir: Path,
    *,
    host: str = "unknown",
    providers: dict[str, Provider] | None = None,
    emit_telemetry: bool = True,
) -> ActivationResult:
    """Detect/recommend/ready the selected provider for ``project_dir``.

    This function never installs providers, downloads models, or blocks a host
    workflow. Missing providers, disabled overlays, command failures, timeouts,
    and telemetry write failures all return compact status instead.
    """

    project_root = project_dir.resolve()
    state = load_state(project_root)
    roots = resolve_repo_root(
        project_root, per_worktree_indexing=state.per_worktree_indexing
    )
    registry = (
        providers
        if providers is not None
        else builtin_registry(allow_internal_overlays=_scout_overlay_allowed(state))
    )
    provider, selection_error = _select_provider(state, registry)
    if provider is None:
        result = ActivationResult(
            provider=state.provider,
            provider_profile="internal-overlay" if state.provider == "scout" else "unknown",
            action="detect",
            outcome=selection_error or "provider_missing",
            repo_root_class=roots.root_class,
            considered_root=str(roots.selected),
            auto_attach=state.auto_attach,
        )
    elif not provider.detect():
        result = ActivationResult(
            provider=provider.metadata.name,
            provider_profile=provider.metadata.profile,
            action="detect",
            outcome="provider_missing",
            repo_root_class=roots.root_class,
            considered_root=str(roots.selected),
            auto_attach=state.auto_attach,
        )
    elif not state.auto_attach:
        result = ActivationResult(
            provider=provider.metadata.name,
            provider_profile=provider.metadata.profile,
            action="recommend",
            outcome="not_opted_in",
            repo_root_class=roots.root_class,
            considered_root=str(roots.selected),
            auto_attach=False,
            recommendation=provider.recommendation(project_root),
        )
    else:
        outcome = provider.ensure_ready(roots.selected, state.timeout_seconds)
        action = "ready" if outcome == "ready" else "attach"
        if outcome in {"fallback_failed", "not_ready"}:
            action = "fallback"
        result = ActivationResult(
            provider=provider.metadata.name,
            provider_profile=provider.metadata.profile,
            action=action,
            outcome=outcome,
            repo_root_class=roots.root_class,
            considered_root=str(roots.selected),
            auto_attach=True,
        )
    if emit_telemetry:
        record_telemetry(project_root, result, host=host)
    return result
