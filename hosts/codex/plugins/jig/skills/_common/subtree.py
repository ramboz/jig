"""Track-local subtree detection (ADR-0033 §5a / spec 084-03).

A *track-local* jig project lives in a subdirectory of a larger git repo (e.g.
`docs/opportunities/cwv/` with `docs_root="."`). Push-mode reservation must
refuse there: the detached-worktree reconstruction would write to the enclosing
repo root and reserve against a shared `main` (ADR-0033 "scoped OUT — push-mode
in a subtree is refused loudly"). This is the SINGLE home for that detection so
every push-mode door (`workflow.py new`, `adr.py new`) shares one definition;
each caller raises its OWN error type, so this module stays a leaf with no
dependency on the skill-specific error classes.

`_common` is a LEAF: stdlib (`subprocess`/`pathlib`) + `_common` only — the same
discipline as `team_signal.py` (which also shells out to git)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from _common import project_layout


def git_toplevel(path: Path) -> Path | None:
    """The enclosing git work-tree root for `path` (`git -C path rev-parse
    --show-toplevel`), resolved, or None when `path` is not inside a git repo
    (or git is unavailable)."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    top = proc.stdout.strip()
    return Path(top).resolve() if top else None


def detect_subtree(project_dir: Path) -> "tuple[Path, Path] | None":
    """Return `(repo_root, subproject_root)` when `project_dir` is a track-local
    subproject inside a larger git repo — i.e. the git work-tree root differs
    from the sentinel-anchored subproject root — else `None`.

    `repo_root` = `git_toplevel(project_dir)`; `subproject_root` =
    `project_layout.project_root_for(project_dir, fallback=resolve)`. When
    `project_dir` is not in a git repo, returns `None` (nothing to refuse —
    other guards handle the no-remote case)."""
    repo_root = git_toplevel(project_dir)
    if repo_root is None:
        return None
    subproject_root = Path(
        project_layout.project_root_for(
            project_dir, fallback=lambda p: Path(p).resolve(),
        )
    ).resolve()
    if repo_root != subproject_root:
        return (repo_root, subproject_root)
    return None
