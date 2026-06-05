"""
build_claude_plugin.py — slice 061-01 (committed Claude package + repoint
marketplace).

Materializes jig's runtime-only **Claude plugin package** at `hosts/claude/`
from canonical source. Per ADR-0018 the repository root stays canonical source
and the committed `hosts/claude/` tree is the clean, runtime-only install
payload the root `.claude-plugin/marketplace.json` pointer resolves to — so a
remote `claude /plugin marketplace add ramboz/jig` installs the package, not
the whole repo (`scripts/`, `docs/`, tests, fixtures).

This is the Claude sibling of `build_codex_plugin.py`: same `_validate_output_dir`
safe-output guards and atomic `shutil.rmtree`+recreate replace. The runtime
include/exclude *subset* is **reused from** `build_release_zip` (its
`_is_excluded_dir` / `_is_excluded_file` predicates and the deterministic
sorted walk) rather than restated — the only Claude-package-specific delta is
the include set: it omits `.codex-plugin` (host-specific) and the root
`.claude-plugin/marketplace.json` is excluded because the remote-install
pointer stays at the repo root, not inside the package.

Usage:
    python3 scripts/build_claude_plugin.py [--source-root <root>] [--output-dir <dir>]

Default output: <source-root>/hosts/claude
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_release_zip  # noqa: E402

# Reuse the release-zip runtime exclusion predicates verbatim (AC #1: reuse,
# don't restate). The same `test_*.py` / `fixtures/` / cache / junk rules the
# release zip applies govern the committed package.
_is_excluded_dir = build_release_zip._is_excluded_dir
_is_excluded_file = build_release_zip._is_excluded_file

# Runtime directory roots the Claude package ships. This is the release-zip
# `_INCLUDE_ROOTS` set minus `.codex-plugin` (the Claude package is
# host-specific and must not carry Codex content — AC #2).
_INCLUDE_ROOTS: tuple[str, ...] = tuple(
    name
    for name in build_release_zip._INCLUDE_ROOTS
    if name != ".codex-plugin"
)

# Optional top-level files copied when present (parity with the release-zip
# builder: missing → warn, build anyway).
_INCLUDE_FILES: tuple[str, ...] = build_release_zip._INCLUDE_FILES

# A Claude package never carries the remote-install pointer: it stays at the
# repo root resolving the plugin to ./hosts/claude (AC #2 / AC #3).
_EXCLUDE_RELATIVE_PATHS: frozenset[str] = frozenset(
    {".claude-plugin/marketplace.json"}
)


def _iter_package_files(source_root: Path):
    """Yield every source-relative file path destined for the package.

    Walks `_INCLUDE_ROOTS` recursively (reusing the release-zip exclusion
    predicates) and yields any present `_INCLUDE_FILES`. Sorted for a
    deterministic, repeatable build."""
    seen: list[Path] = []
    for root_name in _INCLUDE_ROOTS:
        root_dir = source_root / root_name
        if not root_dir.is_dir():
            continue
        for path in root_dir.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(source_root)
            if any(_is_excluded_dir(part) for part in rel.parts[:-1]):
                continue
            if _is_excluded_file(rel.name):
                continue
            if rel.as_posix() in _EXCLUDE_RELATIVE_PATHS:
                continue
            seen.append(rel)

    for file_name in _INCLUDE_FILES:
        if (source_root / file_name).is_file():
            seen.append(Path(file_name))

    return sorted(seen, key=lambda p: p.as_posix())


def _warn_missing_optional_files(source_root: Path, out) -> None:
    for file_name in _INCLUDE_FILES:
        if not (source_root / file_name).is_file():
            out.write(
                f"WARN: optional file {file_name!r} not found at source root; "
                "the Claude package will be built without it.\n"
            )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_output_dir(source_root: Path, output_dir: Path) -> tuple[bool, str]:
    """Refuse unsafe output dirs (mirrors build_codex_plugin's guards): the
    source root itself, any source-owned runtime path, or an ancestor of the
    source root. An output inside the source tree is allowed only under
    `hosts/` or `dist/` (the committed-package / release-zip homes)."""
    if output_dir == source_root:
        return False, "output directory must not be the source root"
    if source_root in output_dir.parents:
        source_owned_roots = {
            source_root / ".claude-plugin",
            source_root / ".codex-plugin",
            source_root / "agents",
            source_root / "hooks",
            source_root / "skills",
            source_root / "templates",
            source_root / "scripts",
            source_root / "docs",
            source_root / ".github",
        }
        if not (
            _is_relative_to(output_dir, source_root / "hosts")
            or _is_relative_to(output_dir, source_root / "dist")
        ):
            return (
                False,
                "output directory inside the source tree must be under "
                "hosts/ or dist/",
            )
        if output_dir in source_owned_roots or any(
            root in output_dir.parents for root in source_owned_roots
        ):
            return False, "output directory must not be a source-owned runtime path"
    if output_dir in source_root.parents:
        return False, "output directory must not be an ancestor of the source root"
    return True, ""


def build(source_root: Path, output_dir: Path, out=None) -> int:
    """Build the runtime-only Claude package at `output_dir` from `source_root`.

    Returns 0 on success, 1 on failure (missing manifest / unsafe output)."""
    if out is None:
        out = sys.stdout
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()

    manifest = source_root / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        out.write(f"ERROR: missing {manifest}\n")
        return 1

    valid_output, reason = _validate_output_dir(source_root, output_dir)
    if not valid_output:
        out.write(f"ERROR: unsafe output directory: {reason}: {output_dir}\n")
        return 1

    _warn_missing_optional_files(source_root, out)

    entries = _iter_package_files(source_root)

    # Atomic-enough replace for a repeatable build: wipe a stale tree fully so
    # it is replaced, not merged (mirrors build_codex_plugin).
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for rel in entries:
        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((source_root / rel).read_bytes())

    out.write(
        f"OK: built Claude plugin at {output_dir} ({len(entries)} files)\n"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_claude_plugin.py",
        description="materialize jig's runtime-only Claude plugin package",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="output package directory (default: <source-root>/hosts/claude)",
    )
    return parser


def main(argv: list[str]) -> int:
    ns = _build_parser().parse_args(argv[1:])
    source_root = Path(ns.source_root)
    output_dir = (
        Path(ns.output_dir)
        if ns.output_dir
        else source_root / "hosts" / "claude"
    )
    return build(source_root=source_root, output_dir=output_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
