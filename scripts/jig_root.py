#!/usr/bin/env python3
"""Print the absolute path of jig's runtime root for GitHub Copilot CLI.

Bug 036. Claude exposes `${CLAUDE_PLUGIN_ROOT}` and Codex `${PLUGIN_ROOT}`;
Copilot exposes no plugin-root environment variable at all. Skill bodies
therefore spell their helper invocations `python3 "$JIG_ROOT/skills/..."`,
and this locator is what resolves `$JIG_ROOT` in a fresh shell (jig's
`SessionStart` hook publishes the same value into session context, so the
common path needs no shell work).

Resolution order:

1. **In-repo mode** — the project owns the machinery, so a `.github/skills/`
   tree next to the caller wins. Nothing installed can be more authoritative
   than the copy the project deliberately vendored.
2. **Plugin mode** — scan Copilot's install roots for a plugin whose
   `.plugin/plugin.json` declares `"name": "jig"`. The marketplace path
   segment is user-controlled (`jig/jig`, `_direct/ramboz--jig--hosts-copilot`,
   ...), so the manifest is the only stable identifier. When several installs
   match, the highest `version` wins, ties broken by mtime, so the answer is
   deterministic rather than filesystem-order dependent.

Prints the resolved root to stdout and exits 0; exits 1 with a diagnostic on
stderr when no jig runtime can be found. Pure stdlib.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PLUGIN_NAME = "jig"
_SENTINEL = Path(".github") / "skills" / "spec-workflow" / "workflow.py"


def _is_runtime(root: Path) -> bool:
    """A jig runtime root is one that actually carries the helpers."""
    return (root / "skills" / "spec-workflow" / "workflow.py").is_file()


def _in_repo_root(start: Path) -> Path | None:
    """Return `<project>/.github` when the project vendored the machinery."""
    for candidate in (start, *start.parents):
        if (candidate / _SENTINEL).is_file():
            return candidate / ".github"
    return None


def _version_key(manifest: dict) -> tuple:
    """Sort key for `version`, numeric-aware so 2.10.0 > 2.9.0."""
    raw = str(manifest.get("version", "") or "")
    parts = []
    for chunk in raw.replace("-", ".").split("."):
        parts.append((1, int(chunk)) if chunk.isdigit() else (0, 0))
    return tuple(parts)


def _install_roots() -> list[Path]:
    home = Path(os.environ.get("COPILOT_HOME") or Path.home() / ".copilot")
    base = home / "installed-plugins"
    if not base.is_dir():
        return []
    found = []
    for marketplace in sorted(base.iterdir()):
        if not marketplace.is_dir():
            continue
        for plugin in sorted(marketplace.iterdir()):
            manifest = plugin / ".plugin" / "plugin.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            # A manifest is only usable as an identity key when it is an
            # object; a valid-JSON array/scalar would blow up on `.get`.
            if not isinstance(data, dict) or data.get("name") != PLUGIN_NAME:
                continue
            root = plugin / ".github"
            if _is_runtime(root):
                found.append((_version_key(data), root.stat().st_mtime, root))
    found.sort(key=lambda item: (item[0], item[1]))
    return [root for _, _, root in found]


def resolve(start: Path | None = None) -> Path | None:
    start = (start or Path.cwd()).resolve()
    in_repo = _in_repo_root(start)
    if in_repo is not None:
        return in_repo
    roots = _install_roots()
    return roots[-1] if roots else None


def main(argv: list[str]) -> int:
    start = Path(argv[1]) if len(argv) > 1 else None
    root = resolve(start)
    if root is None:
        sys.stderr.write(
            "jig_root: no jig runtime found. Install the plugin "
            "(`copilot plugin install jig@jig`) or run from a project that "
            "vendored the machinery with `--in-repo`.\n"
        )
        return 1
    sys.stdout.write(str(root) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
