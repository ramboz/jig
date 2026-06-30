"""Shared project-layout helper — the single home for spec 084's configurable
`docs_root` (ADR-0033).

jig assumes project artifacts live under `<project_dir>/docs/…`. This module
lets a project redefine that **docs root** via `layout.docs_root` in
`<project_dir>/scaffold.json`, so jig can be adopted track-local inside a larger
repo (e.g. a subproject with `docs_root="."`, putting specs directly at
`<project_dir>/specs/` rather than forcing a second `docs/` layer). Default
remains `"docs"` — absent scaffold.json or absent layout block resolves to it,
so every existing project (and jig's own repo, which has no scaffold.json) is
unaffected.

What this module owns (slice 084-01):
  - `docs_root(project_dir) -> str` — reads + validates the configured root.
  - `specs_dir` / `decisions_dir` / `workflow_path` / `architecture_path` /
    `memory_dir` / `refinement_todo_path` — derived artifact paths, with
    `docs_root="."` collapsing the docs layer.
  - `project_root_for(path, *, fallback)` — sentinel-anchored project-root
    discovery (ADR-0033 §5a): the single resolver replacing both the
    `docs/`-marker up-walk and the `parents[3]` depth arithmetic.
  - `LayoutError` — raised on an invalid / malformed layout config.

Validation is load-bearing (ADR-0033 §3): a `docs_root` is the only barrier
between config and an arbitrary-write primitive, so an absolute path or a `..`
escape is rejected. Normalization is purely **lexical** (`os.path.normpath`,
no filesystem access) — a `docs_root` that is itself a symlink pointing outside
`project_dir` is a documented known-limit, NOT caught here.

`_common` is a LEAF: this module imports only stdlib (mirrors
`scaffold_state.py`'s import discipline). JSON via the `json` stdlib — no
`tomllib` (the supported floor is Python 3.9).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

# The completion sentinel + config home: written at the project root by
# scaffold-init (spec 063 / ADR-0011). It is read to DISCOVER docs_root, so it
# can never live under docs_root.
_SCAFFOLD_SENTINEL = "scaffold.json"

# Default docs root — the historical, hardcoded `<project_dir>/docs/…` layout.
_DEFAULT_DOCS_ROOT = "docs"


class LayoutError(ValueError):
    """Invalid or malformed layout config — an absolute / escaping
    `docs_root`, or a scaffold.json that is unparseable or carries a
    wrong-typed `layout` / `docs_root`. Subclass of `ValueError` so callers
    that already catch `ValueError` keep working (ADR-0033 §3)."""


def _read_raw_docs_root(project_dir: Path) -> str:
    """Read `layout.docs_root` from `<project_dir>/scaffold.json`.

    Returns the default `"docs"` when scaffold.json is absent, has no `layout`
    block, or `docs_root` is absent / empty-string. Raises `LayoutError` when
    the JSON is unparseable or a wrong type appears (fail loud — distinct from
    the documented "absent → default" path)."""
    sentinel = Path(project_dir) / _SCAFFOLD_SENTINEL
    if not sentinel.is_file():
        return _DEFAULT_DOCS_ROOT
    try:
        data = json.loads(sentinel.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers JSONDecodeError
        raise LayoutError(
            f"malformed scaffold.json at {sentinel}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise LayoutError(
            f"malformed scaffold.json at {sentinel}: top level must be an object"
        )
    layout = data.get("layout")
    if layout is None:
        return _DEFAULT_DOCS_ROOT
    if not isinstance(layout, dict):
        raise LayoutError(
            f"malformed scaffold.json at {sentinel}: 'layout' must be an object"
        )
    raw = layout.get("docs_root")
    if raw is None or raw == "":
        return _DEFAULT_DOCS_ROOT
    if not isinstance(raw, str):
        raise LayoutError(
            f"malformed scaffold.json at {sentinel}: "
            f"'layout.docs_root' must be a string, got {type(raw).__name__}"
        )
    return raw


def _validate_docs_root(raw: str) -> str:
    """Lexically validate + normalize a raw `docs_root` (ADR-0033 §3).

    Rejects an absolute path or one whose normalized form escapes
    `project_dir`. Returns the normalized relative root (`"."`, `"docs"`,
    `"docs/internal"`, …). Purely lexical — no filesystem access."""
    if os.path.isabs(raw):
        raise LayoutError(f"docs_root must be relative, got absolute: {raw!r}")
    norm = os.path.normpath(raw)
    if norm == ".." or norm.startswith(".." + os.sep):
        raise LayoutError(
            f"docs_root escapes project_dir: {raw!r} (normalizes to {norm!r})"
        )
    return norm


def docs_root(project_dir: Path) -> str:
    """The configured (or default) docs root for `project_dir`, validated.

    `"docs"` by default (absent / no-layout / empty); `"."` collapses the docs
    layer. Raises `LayoutError` on an absolute / escaping root or a malformed
    scaffold.json."""
    return _validate_docs_root(_read_raw_docs_root(project_dir))


def _docs_base(project_dir: Path) -> Path:
    """`<project_dir>/<docs_root>`, collapsing to `<project_dir>` when
    `docs_root` is `"."` (no trailing `./` segment)."""
    root = docs_root(project_dir)
    base = Path(project_dir)
    if root == ".":
        return base
    return base / root


def specs_dir(project_dir: Path) -> Path:
    """`<docs_root>/specs`."""
    return _docs_base(project_dir) / "specs"


def decisions_dir(project_dir: Path) -> Path:
    """`<docs_root>/decisions`."""
    return _docs_base(project_dir) / "decisions"


def workflow_path(project_dir: Path) -> Path:
    """`<docs_root>/workflow.md`."""
    return _docs_base(project_dir) / "workflow.md"


def architecture_path(project_dir: Path) -> Path:
    """`<docs_root>/architecture.md`."""
    return _docs_base(project_dir) / "architecture.md"


def memory_dir(project_dir: Path) -> Path:
    """`<docs_root>/memory`."""
    return _docs_base(project_dir) / "memory"


def refinement_todo_path(project_dir: Path) -> Path:
    """`<docs_root>/refinement-todo.md`."""
    return _docs_base(project_dir) / "refinement-todo.md"


def project_root_for(path: Path, *, fallback: Callable[[Path], Path]) -> Path:
    """Resolve the project root for `path` — sentinel-anchored (ADR-0033 §5a).

    Walks up from `path` (resolved) and returns the nearest ancestor (incl.
    `path` itself when it is a directory) that contains `scaffold.json`. When NO
    sentinel is found on the up-walk, calls `fallback(path)` (the ORIGINAL,
    un-resolved path) and returns its result — the per-caller legacy behavior
    (`parents[3]` depth arithmetic, `.git` anchor, or `docs/`-marker up-walk).
    Any exception raised by `fallback` propagates unchanged.

    This is the single resolver that replaces every structure-derived discovery
    site, so a subtree adopter (`docs_root="."`) never resolves its root into an
    enclosing repo: the sentinel branch dominates for any scaffolded project,
    while the fallback fires only for sentinel-less paths (jig's own repo, test
    fixtures) where today's behavior is correct."""
    resolved = Path(path).resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / _SCAFFOLD_SENTINEL).is_file():
            return candidate
    return fallback(Path(path))
