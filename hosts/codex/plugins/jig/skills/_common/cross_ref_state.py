"""Ref-aware lifecycle-state primitive (ADR-0058 / spec 112-01).

`identifier_state_on_ref(identifier, ref, repo_root=None)` reads the
lifecycle marker (`DONE`, `Accepted`, another status token, or the
`ABSENT` sentinel) of a slice (`NNN-MM`) or ADR (`NNNN`) identifier AS
COMMITTED ON A GIVEN GIT REF — not the current checkout. This is the read
side of ADR-0058's fix for "the current checkout is not the whole truth":
a stale on-disk marker (e.g. `DRAFT`) can coexist with the same identifier
already `DONE` on `origin/main` or a sibling branch.

Matches on the identifier's NUMBER, not its filename — a renamed slug
survives (`docs/specs/112-old-slug/` and `docs/specs/112-new-slug/` both
resolve identifier `112-01`). Reads via `git show <ref>:<path>` (a content
read, distinct from ADR-0053's filename-only `--name-only` scan this module
reuses the enumeration shape of). Best-effort by construction: ANY git
failure (ref unreachable, not a git repo, git not on PATH) returns `None`
("unknown") rather than raising — callers (e.g. `land.py prepare`'s
Class-A blocker) degrade `None` to a non-blocking warning, mirroring
`_branch_freshness_warning`'s posture.

Status parsing reuses `_common.parsing.status_marker_from_section` (slice
status) and `_common.parsing.parse_frontmatter` (ADR status) — the same
readers `land.py` / `adr.py` use — so a cross-ref read can never diverge
from what a normal checkout-local read would report for the identical
content.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional

from . import project_layout
from .parsing import (
    SliceLookupError,
    find_slice_section,
    parse_frontmatter,
    status_marker_from_section,
)

# Sentinel: the identifier's file/section is not present on the given ref
# (normal case for un-landed work — never a blocker). Distinct from `None`
# ("unknown" — a git/ref error, degrades to an advisory, never a blocker
# either, but for a different reason).
ABSENT = "absent"

_SLICE_ID_RE = re.compile(r"^(\d{3})-(\d{2})$")
_ADR_ID_RE = re.compile(r"^(\d{4})$")

_DEFAULT_SPECS_RELPATH = "docs/specs"
_DEFAULT_DECISIONS_RELPATH = "docs/decisions"


def _git(argv: list, cwd: Path) -> tuple:
    """Same shape as `_common.reservation._git` — a private, module-local
    git runner (not imported cross-module: that helper is underscore-private
    to its own module). Never raises; an OSError (e.g. git missing) becomes
    a non-zero return code with the exception text as stderr."""
    try:
        result = subprocess.run(
            argv, cwd=str(cwd), capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        return 1, "", str(exc)
    return result.returncode, result.stdout or "", result.stderr or ""


def _relpath(base: Path, root: Path) -> str:
    try:
        return base.relative_to(root).as_posix()
    except ValueError:
        return base.as_posix()


def _specs_relpath(repo_root: Path) -> str:
    try:
        return _relpath(project_layout.specs_dir(repo_root), repo_root)
    except project_layout.LayoutError:
        return _DEFAULT_SPECS_RELPATH


def _decisions_relpath(repo_root: Path) -> str:
    try:
        return _relpath(project_layout.decisions_dir(repo_root), repo_root)
    except project_layout.LayoutError:
        return _DEFAULT_DECISIONS_RELPATH


def _ls_tree(git, repo_root: Path, ref: str, relpath: str):
    """`git ls-tree --name-only <ref> -- <relpath>/`. Returns (rc, entries)
    where `entries` is a list of basenames (directory prefix stripped)."""
    rc, out, _err = git(
        ["git", "ls-tree", "--name-only", ref, "--", relpath.rstrip("/") + "/"],
        repo_root,
    )
    if rc != 0:
        return rc, []
    prefix = relpath.rstrip("/") + "/"
    entries = []
    for line in out.splitlines():
        name = line.strip()
        if not name:
            continue
        if name.startswith(prefix):
            name = name[len(prefix):]
        entries.append(name.rstrip("/"))
    return rc, entries


def _show(git, repo_root: Path, ref: str, relpath: str):
    """`git show <ref>:<relpath>`. Returns (rc, content)."""
    return git(["git", "show", f"{ref}:{relpath}"], repo_root)[:2]


def _slice_state(git, repo_root: Path, ref: str,
                  spec_num: str, slice_num: str) -> Optional[str]:
    specs_rel = _specs_relpath(repo_root)
    rc, entries = _ls_tree(git, repo_root, ref, specs_rel)
    if rc != 0:
        return None  # ref/repo unreadable — unknown, not absent

    spec_dir = None
    for name in entries:
        m = re.match(r"^(\d{3})-", name)
        if m and m.group(1) == spec_num:
            spec_dir = name
            break
    if spec_dir is None:
        return ABSENT

    spec_dir_rel = f"{specs_rel}/{spec_dir}"
    rc, files = _ls_tree(git, repo_root, ref, spec_dir_rel)
    if rc != 0:
        return None

    slice_file = None
    for name in files:
        m = re.match(r"^slice-(\d{2})-", name)
        if m and m.group(1) == slice_num:
            slice_file = name
            break

    if slice_file is not None:
        rc, content = _show(git, repo_root, ref, f"{spec_dir_rel}/{slice_file}")
        if rc != 0:
            return None
        status = status_marker_from_section(content)
        return status or ABSENT

    # Fall back to an embedded `## Slice NNN-MM ...` section in spec.md.
    rc, content = _show(git, repo_root, ref, f"{spec_dir_rel}/spec.md")
    if rc != 0:
        return ABSENT  # no per-slice file AND no spec.md on this ref
    try:
        start, end, _label = find_slice_section(content, f"{spec_num}-{slice_num}")
    except SliceLookupError:
        return ABSENT
    status = status_marker_from_section(content[start:end])
    return status or ABSENT


def _adr_state(git, repo_root: Path, ref: str, adr_num: str) -> Optional[str]:
    decisions_rel = _decisions_relpath(repo_root)
    rc, entries = _ls_tree(git, repo_root, ref, decisions_rel)
    if rc != 0:
        return None

    adr_file = None
    for name in entries:
        m = re.match(r"^adr-(\d{4})-.*\.md$", name)
        if m and m.group(1) == adr_num:
            adr_file = name
            break
    if adr_file is None:
        return ABSENT

    rc, content = _show(git, repo_root, ref, f"{decisions_rel}/{adr_file}")
    if rc != 0:
        return None
    fm_fields, _ = parse_frontmatter(content)
    status = str(fm_fields.get("status", "")).strip()
    return status or ABSENT


def identifier_state_on_ref(identifier: str, ref: str,
                            repo_root: Optional[Path] = None,
                            *, run=None) -> Optional[str]:
    """Return the lifecycle marker for `identifier` as committed on `ref`.

    `identifier` is a slice id (`NNN-MM`, e.g. `112-01`) or an ADR id
    (`NNNN`, e.g. `0058`) — matched by NUMBER against `docs/specs/NNN-*` /
    `docs/decisions/adr-NNNN-*.md` on `ref`, so a renamed slug still
    resolves. `repo_root` defaults to `Path.cwd()`.

    Returns:
      - the raw status string (`"DONE"`, `"Accepted"`, `"IN_PROGRESS"`, …)
        when the identifier's file/section is present on `ref` and a status
        marker was found;
      - `ABSENT` ("absent") when `ref` is readable but the identifier's
        file is not present on it (the normal not-yet-landed case);
      - `None` when `ref` (or git itself) could not be read — offline, no
        remote, unreachable ref, not a git repo, git missing. Best-effort:
        never raises.

    `run` is an optional `(argv, cwd) -> (rc, stdout, stderr)` callable
    (mirrors `_common.reservation.scan_max_reserved_number`'s `run` param)
    so tests can intercept git without a real repository.
    """
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    git = run if run is not None else _git

    identifier = identifier.strip()
    m = _SLICE_ID_RE.match(identifier)
    if m:
        return _slice_state(git, repo_root, ref, m.group(1), m.group(2))
    m = _ADR_ID_RE.match(identifier)
    if m:
        return _adr_state(git, repo_root, ref, m.group(1))
    return None  # unrecognized identifier shape — best-effort unknown
