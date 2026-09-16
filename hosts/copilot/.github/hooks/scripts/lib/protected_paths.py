"""Protected-path nudge — slice 106-01 / ADR-0051.

A soft, fail-open `PostToolUse` nudge: when an `Edit`/`Write`/`MultiEdit` lands
on a **governance-protected path** (from `scaffold.json.protected_paths`),
return one agent-facing reminder — "this is governance-protected; open an
ADR/spec (surface-and-stop, spec 102), don't self-edit; enforcement is
out-of-band". Never a gate (ADR-0011): CODEOWNERS + branch protection enforce
out-of-boundary; this only nudges in-boundary.

`evaluate()` is the tested surface. Slice 106-01 made **`jig-boundary-change-warn.sh`
the single owner** of this nudge (its governance-nudge sibling): it calls
`evaluate()`, folds the result into its one merged `additionalContext` object, and
`jig-entry-gate.sh` deliberately does NOT emit it — so an edit to a protected path
nudges exactly once even though both hooks share the `PostToolUse
Edit|Write|MultiEdit` matcher. Everything is fail-open: any error → None.

Mirrors `lib/entry_gate.py` (Python 3.9, opt-out env). The `**`-aware matcher is
kept INLINE here — hooks import only `_common`, never a skill module like
`governance.py`. A behavioral parity test
(`test_protected_paths.GlobMatcherParityTests`) pins this inline matcher in sync
with `governance.path_matches_glob` (the source-of-truth) so the two cannot drift.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

# Opt-out token set — mirrors _common/parsing.ENV_FALSEY and the sibling gates,
# kept inline so this gate gains no cross-import failure mode.
_DISABLE_VALUES = {"0", "false", "off", "no"}


def _glob_to_regex(glob: str) -> str:
    import re

    out: List[str] = ["^"]
    i, n = 0, len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if i + 1 < n and glob[i + 1] == "*":
                out.append(".*")  # `**` crosses `/`
                i += 2
                continue
            out.append("[^/]*")  # `*` within a segment
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    out.append("$")
    return "".join(out)


def _path_matches_glob(rel_path: str, glob: str) -> bool:
    """True iff project-relative posix `rel_path` matches `glob` (`**`/`*`).

    INLINE copy of governance.path_matches_glob — hooks never import skill
    modules. A behavioral parity test (test_protected_paths.GlobMatcherParityTests)
    pins the two in sync."""
    import re

    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    glob = glob.replace("\\", "/")
    if glob.endswith("/**") and rel == glob[: -len("/**")]:
        return True
    return re.match(_glob_to_regex(glob), rel) is not None


def read_protected_paths(project_dir) -> List[str]:
    """Return `scaffold.json.protected_paths` for `project_dir`, or `[]` on any
    error (no manifest / unreadable / missing / wrong-typed field)."""
    try:
        manifest = Path(project_dir) / "scaffold.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        paths = data.get("protected_paths")
        if isinstance(paths, list):
            return [p for p in paths if isinstance(p, str)]
        return []
    except Exception:
        return []


def _rel_posix(project_dir: Path, file_path: str) -> str:
    """Normalize `file_path` to a project-relative posix path (best-effort)."""
    p = Path(file_path)
    root = Path(project_dir)
    try:
        if p.is_absolute():
            rel = p.resolve().relative_to(root.resolve())
        else:
            rel = Path(file_path)
        return rel.as_posix()
    except Exception:
        return Path(file_path).as_posix()


def match_protected_path(project_dir, file_path: str) -> Optional[str]:
    """Return the first protected glob that `file_path` matches, else None."""
    try:
        globs = read_protected_paths(project_dir)
        if not globs:
            return None
        rel = _rel_posix(Path(project_dir), file_path)
        for glob in globs:
            if _path_matches_glob(rel, glob):
                return glob
        return None
    except Exception:
        return None


def nudge_text(file_path: str, matched: str) -> str:
    return (
        f"{file_path} is a governance-protected path (matched `{matched}`). A "
        f"change here should open an ADR/spec (surface-and-stop, spec 102), not "
        f"a self-edit. Enforcement is out-of-band (CODEOWNERS + branch "
        f"protection); this nudge is informational, not a gate."
    )


def evaluate(payload: dict, project_dir) -> Optional[str]:
    """Return the protected-path nudge for an in-boundary edit, or None.

    Fail-open: any error returns None. Opt-out via `JIG_PROTECTED_PATHS` in
    {0,false,off,no}. Only `Edit`/`Write`/`MultiEdit` with a `file_path`."""
    try:
        if (os.environ.get("JIG_PROTECTED_PATHS") or "").strip().lower() in _DISABLE_VALUES:
            return None
        if not isinstance(payload, dict):
            return None
        if payload.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
            return None
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            return None
        file_path = tool_input.get("file_path") or ""
        if not file_path:
            return None
        matched = match_protected_path(project_dir, file_path)
        if not matched:
            return None
        return nudge_text(file_path, matched)
    except Exception:
        return None
