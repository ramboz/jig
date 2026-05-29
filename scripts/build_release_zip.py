"""
build_release_zip.py — slice 013-03 (release-zip-artifact).

Builds a runtime-only zip of jig's plugin tree for release distribution.

Usage:
    # Build a release zip:
    python3 scripts/build_release_zip.py --version 1.0.0 [--output <path>]

    # Smoke-test an existing zip by extracting it and running
    # `verify_install.run_headless` against the extracted tree:
    python3 scripts/build_release_zip.py --smoke-test <path-to-zip>

The zip is produced flat at the root (no wrapping `jig/` directory), so it
is directly drag-and-droppable into Claude Code Desktop's `/plugin` UI,
loadable via `claude --plugin-dir <zip>`, and usable as the source payload
for Codex plugin packaging.

Exit codes:
    0  zip built successfully and validates / smoke-test passed
    1  build failed (I/O, source-tree issue) / smoke-test failed
    2  version mismatch between --version and the source plugin.json
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Iterable

# Files / directories to include in the zip, relative to the source root.
# Directories are walked recursively; individual files are copied as-is.
_INCLUDE_ROOTS: tuple[str, ...] = (
    ".claude-plugin",
    ".codex-plugin",
    "agents",
    "skills",
    "hooks",
    "templates",
)

_INCLUDE_FILES: tuple[str, ...] = (
    "README.md",
    "LICENSE",
)

# Directories anywhere in the tree to skip outright. Limited to truly
# defensive exclusions (caches, VCS artifacts) — top-level dev-only dirs
# (`scripts/`, `docs/`, `.github/`, `.git/`, `.jig/`, `.claude/`) are
# already excluded by virtue of not being listed in `_INCLUDE_ROOTS`,
# so we don't need to name them here. Naming them would also exclude
# nested same-named dirs that ARE runtime — e.g. `hooks/scripts/`
# (the actual hook scripts) and `templates/docs/` (scaffold-init's
# project template).
_EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    # `fixtures/` is reserved as test-data (spec 035): any-depth match
    # per Q1, no escape hatch per Q4. Future skills needing runtime
    # sample data must use a different name (`samples/`, `examples/`,
    # `data/`, etc.).
    "fixtures",
})

# File-name patterns to skip (matched against the basename).
_EXCLUDE_FILE_SUFFIXES: tuple[str, ...] = (
    ".pyc",
)

_EXCLUDE_FILE_NAMES: frozenset[str] = frozenset({
    ".DS_Store",
})


def _is_excluded_dir(name: str) -> bool:
    return name in _EXCLUDE_DIR_NAMES


def _is_excluded_file(name: str) -> bool:
    if name in _EXCLUDE_FILE_NAMES:
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    for suffix in _EXCLUDE_FILE_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def _iter_files(source_root: Path) -> Iterable[Path]:
    """Yield every file path (relative to source_root) destined for the zip.

    Walks each entry in `_INCLUDE_ROOTS` recursively, skipping excluded
    directories/files. Also yields the top-level `_INCLUDE_FILES` if present.
    """
    for root_name in _INCLUDE_ROOTS:
        root_dir = source_root / root_name
        if not root_dir.is_dir():
            continue
        for path in root_dir.rglob("*"):
            if path.is_dir():
                continue
            # Skip if any parent directory along the relative path is excluded.
            rel = path.relative_to(source_root)
            if any(_is_excluded_dir(part) for part in rel.parts[:-1]):
                continue
            if _is_excluded_file(rel.name):
                continue
            yield rel

    for file_name in _INCLUDE_FILES:
        file_path = source_root / file_name
        if file_path.is_file():
            yield Path(file_name)


def _warn_missing_optional_files(source_root: Path, out) -> None:
    """Emit a warning per missing top-level file that the AC marks optional."""
    for file_name in _INCLUDE_FILES:
        if not (source_root / file_name).is_file():
            out.write(
                f"WARN: optional file {file_name!r} not found at source root; "
                "the zip will be built without it.\n"
            )


# A fixed timestamp for every zip entry so two builds produce bit-identical
# bytes. 2026-01-01 00:00:00 UTC is well after the zip-format minimum (1980)
# and a stable choice for jig's release timeline.
_DETERMINISTIC_MTIME = (2026, 1, 1, 0, 0, 0)


def _add_entry(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(filename=arcname, date_time=_DETERMINISTIC_MTIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    # 0o644 for files. The high two bytes of external_attr encode unix mode;
    # shifting by 16 places mode bits into the right position.
    info.external_attr = (0o644 & 0xFFFF) << 16
    # Pin create_system to 3 (Unix) so a zip built on macOS and a zip built
    # on Linux CI agree byte-for-byte. Otherwise ZipInfo.create_system
    # defaults to the host platform and the same source produces different
    # bytes on different OSes.
    info.create_system = 3
    zf.writestr(info, data)


def _validate_output(zip_path: Path, expected_version: str, out) -> int:
    """Validate that the produced zip contains the expected plugin.json shape.

    Returns 0 on success, 2 on version mismatch (per AC #4).
    """
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for plugin_json_path in (
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
        ):
            if plugin_json_path not in names:
                out.write(f"FAIL: zip is missing {plugin_json_path} at root\n")
                return 1
            with zf.open(plugin_json_path) as f:
                data = json.loads(f.read())

            actual_version = data.get("version")
            if actual_version != expected_version:
                out.write(
                    f"FAIL: version mismatch — requested {expected_version!r} "
                    f"but {plugin_json_path} declares {actual_version!r}. "
                    "Refusing to produce a mislabeled artifact.\n"
                )
                return 2

    return 0


def build(
    source_root: Path,
    version: str,
    output_path: Path,
    out=None,
) -> int:
    """Build a release zip from source_root targeting version, write to output_path.

    Returns 0 on success, 2 on version mismatch, 1 on other failure.
    """
    if out is None:
        out = sys.stdout

    # Pre-check the source plugin.json version so we fail fast before any
    # I/O, rather than producing a mislabeled zip and detecting the
    # mismatch after the fact.
    for plugin_json_src in (
        source_root / ".claude-plugin" / "plugin.json",
        source_root / ".codex-plugin" / "plugin.json",
    ):
        if not plugin_json_src.is_file():
            out.write(f"FAIL: source plugin.json missing at {plugin_json_src}\n")
            return 1
        src_data = json.loads(plugin_json_src.read_text())
        if src_data.get("version") != version:
            out.write(
                f"FAIL: version mismatch — requested {version!r} "
                f"but {plugin_json_src} declares {src_data.get('version')!r}. "
                "Refusing to produce a mislabeled artifact.\n"
            )
            return 2

    _warn_missing_optional_files(source_root, out)

    # Collect + sort all entries up-front so the zip layout is deterministic.
    entries = sorted(_iter_files(source_root), key=lambda p: p.as_posix())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in entries:
            arcname = rel.as_posix()
            data = (source_root / rel).read_bytes()
            _add_entry(zf, arcname, data)

    rc = _validate_output(output_path, version, out)
    if rc != 0:
        return rc

    out.write(f"OK: built {output_path} ({len(entries)} entries, version {version})\n")
    return 0


def smoke_test(zip_path: Path, out=None) -> int:
    """Extract `zip_path` to a tempdir and run verify_install.run_headless.

    Returns the underlying verify-install exit code (0/1/2). Used by both
    the local smoke-test command (AC #7) and the CI `package` job's
    smoke-test step (AC #6).
    """
    import tempfile

    if out is None:
        out = sys.stdout

    if not zip_path.is_file():
        out.write(f"FAIL: zip not found at {zip_path}\n")
        return 1

    # Defer the verify_install import so this script stays usable when
    # invoked from a directory where verify_install.py is unreachable
    # (the import only fires when --smoke-test is requested).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import verify_install  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="jig-smoke-") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        return verify_install.run_headless(tmp_path, out=out)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_release_zip.py",
        description="build (or smoke-test) a release zip of jig's plugin runtime",
    )
    p.add_argument(
        "--version",
        default=None,
        help="release version (must match .claude-plugin/plugin.json's version) "
             "— required in build mode",
    )
    p.add_argument(
        "--output",
        default=None,
        help="output zip path (default: dist/jig-v<version>.zip)",
    )
    p.add_argument(
        "--source-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="path to jig's source root (default: the script's repo root)",
    )
    p.add_argument(
        "--smoke-test",
        metavar="ZIP",
        default=None,
        help="instead of building, extract the named zip and run "
             "verify_install.run_headless against the extracted tree",
    )
    return p


def main(argv: list) -> int:
    ns = _build_parser().parse_args(argv[1:])

    if ns.smoke_test:
        return smoke_test(Path(ns.smoke_test))

    if not ns.version:
        sys.stderr.write("ERROR: --version is required unless --smoke-test is given\n")
        return 2

    source_root = Path(ns.source_root)
    output = (
        Path(ns.output)
        if ns.output
        else source_root / "dist" / f"jig-v{ns.version}.zip"
    )
    return build(source_root=source_root, version=ns.version, output_path=output)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
