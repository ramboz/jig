"""SessionStart git-freshness nudge — spec 103-01 / ADR-0048.

At `SessionStart`, tell the agent when `HEAD` is behind the branch's
**integration base** — before it forms any premise from repo state. This is
the earlier tripwire ADR-0048 records: `bug 001` already warns at
`land.py prepare`/transition time, but only if the session reaches those
commands; this hook fires at time-zero.

``evaluate()`` is the tested surface; the thin ``jig-git-freshness.sh``
wrapper handles stdin, ``additionalContext`` printing, and the auditable
trace. Everything is fail-open: any error returns ``None`` (silent), never
raises, never blocks.

**The smart-target resolution rule (ADR-0048 § Upstream semantics — load-
bearing, get it exactly right)**, in order:

1. ``@{upstream}`` iff it resolves AND is NOT this branch's own remote
   (``origin/<current-branch>``) — a tracking upstream pointing elsewhere is
   a real integration base (git-flow ``origin/develop``, fork
   ``upstream/main``, an explicit ``set-upstream-to`` a base).
2. else ``origin/main``, then ``origin/master`` — the trunk base. This is
   jig's own case: a pushed task branch's ``@{upstream}`` is
   ``origin/<branch>`` (its own remote), excluded by rule 1's own-remote
   guard, so it falls here.
3. else silent (not a work tree, or nothing resolves).

The own-remote guard in rule 1 is load-bearing: without it, a pushed task
branch would compare ``HEAD..origin/<branch>`` (own-branch advancement, ~0
for a solo branch) instead of measuring whether the *base* drifted — going
silent on exactly the #105-shaped incident.

Python 3.9 compatible (``from __future__ import annotations`` for
annotation unions only).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional

# Opt-out token set — mirrors the widened token set the sibling hooks use
# (entry_gate._DISABLE_VALUES / _common.parsing.ENV_FALSEY).
_DISABLE_VALUES = {"0", "false", "off", "no"}

_DEFAULT_TIMEOUT = 5.0

# Hard ceiling on the per-subprocess timeout. The hook-level timeout in
# hooks.json is 10s; keeping every git subprocess strictly under that
# (AC4: "subprocess timeout strictly less than the hook-level timeout") is an
# invariant we enforce by construction, not by trusting the operator's
# JIG_GIT_FRESHNESS_TIMEOUT value — an oversized override is clamped, not obeyed.
_MAX_TIMEOUT = 8.0

# Trunk fallback order (rule 2) once no non-own upstream resolves (rule 1).
_TRUNK_CANDIDATES = ("origin/main", "origin/master")


def _resolve_timeout(env) -> float:
    """Read ``JIG_GIT_FRESHNESS_TIMEOUT`` from `env`, falling back to the
    default. Mirrors context_fill.py's env-parsing shape: a non-positive or
    non-numeric value silently falls back so a typo never crashes the hook.
    The result is clamped to ``_MAX_TIMEOUT`` so an oversized override can
    never breach the AC4 subprocess-under-hook-budget invariant."""
    raw = (env.get("JIG_GIT_FRESHNESS_TIMEOUT") or "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return _DEFAULT_TIMEOUT
    if value <= 0:
        return _DEFAULT_TIMEOUT
    return min(value, _MAX_TIMEOUT)


def _run_git(args, project_dir, timeout) -> Optional["subprocess.CompletedProcess"]:
    """Run a bounded git subprocess. Returns the CompletedProcess, or `None`
    on ANY failure (missing git, timeout, offline, non-repo) — the caller
    degrades rather than raising."""
    try:
        return subprocess.run(
            ["git"] + list(args), cwd=str(project_dir),
            capture_output=True, text=True, check=False, timeout=timeout,
        )
    except Exception:
        return None


def _current_branch(project_dir, timeout) -> Optional[str]:
    result = _run_git(["branch", "--show-current"], project_dir, timeout)
    if result is None or result.returncode != 0:
        return None
    branch = (result.stdout or "").strip()
    return branch or None


def _upstream(project_dir, timeout) -> Optional[str]:
    result = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        project_dir, timeout,
    )
    if result is None or result.returncode != 0:
        return None
    upstream = (result.stdout or "").strip()
    return upstream or None


def _ref_exists(ref, project_dir, timeout) -> bool:
    result = _run_git(
        ["rev-parse", "--verify", "--quiet", ref], project_dir, timeout,
    )
    return result is not None and result.returncode == 0


def resolve_target(project_dir, timeout) -> Optional[str]:
    """The smart-target resolution rule (module docstring / ADR-0048).
    Returns the integration-base ref (e.g. ``origin/main``,
    ``origin/develop``), or `None` when nothing resolves."""
    branch = _current_branch(project_dir, timeout)
    own_remote = "origin/" + branch if branch else None

    upstream = _upstream(project_dir, timeout)
    if upstream and upstream != own_remote:
        return upstream

    for candidate in _TRUNK_CANDIDATES:
        if _ref_exists(candidate, project_dir, timeout):
            return candidate

    return None


def _fetch(base, project_dir, timeout) -> None:
    """Best-effort timeout-guarded fetch of the resolved base (AC4). ANY
    failure (timeout, offline, missing git, non-zero exit) is swallowed by
    ``_run_git`` — the caller falls through to comparing against the
    last-known ref."""
    if "/" not in base:
        return
    remote, branch = base.split("/", 1)
    _run_git(["fetch", remote, branch], project_dir, timeout)


def _behind_count(base, project_dir, timeout) -> Optional[int]:
    result = _run_git(
        ["rev-list", "--count", "HEAD.." + base], project_dir, timeout,
    )
    if result is None or result.returncode != 0:
        return None
    try:
        return int((result.stdout or "").strip())
    except ValueError:
        return None


def _nudge_text(behind: int, base: str) -> str:
    return (
        f"HEAD is {behind} commit(s) behind `{base}`. The repo-state premise "
        "formed this session may be stale — sync before trusting it or "
        "forming conclusions. Review the incoming commits with "
        f"`git log HEAD..{base} --oneline`, then sync with `git fetch && "
        f"git merge {base}` (or `git rebase {base}` to replay local work on "
        "top)."
    )


def evaluate(payload: dict, project_dir, env: Optional[dict] = None) -> Optional[str]:
    """Return the freshness nudge text for a behind branch, or `None`.

    Fail-open: any error returns `None` (the caller stays silent). Reads the
    opt-out + timeout env internally (via `env`, defaulting to
    `os.environ`) so the wrapper stays thin.
    """
    try:
        if env is None:
            env = os.environ
        if (env.get("JIG_GIT_FRESHNESS") or "").strip().lower() in _DISABLE_VALUES:
            return None
        if not isinstance(payload, dict):
            return None
        # AC7: skip the fetch + check on mid-session compaction (best-effort
        # degradation — an absent/unknown `source` runs normally).
        if payload.get("source") == "compact":
            return None

        timeout = _resolve_timeout(env)
        project_dir = Path(project_dir)

        base = resolve_target(project_dir, timeout)
        if not base:
            return None

        _fetch(base, project_dir, timeout)

        behind = _behind_count(base, project_dir, timeout)
        if not behind:
            return None

        return _nudge_text(behind, base)
    except Exception:
        return None
