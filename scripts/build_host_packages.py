"""
build_host_packages.py — slice 061-02 (unified host-package build entry point).

Builds BOTH committed host packages from canonical source in one invocation:

  - the Claude package at `hosts/claude/`   (via build_claude_plugin.build)
  - the Codex package at  `hosts/codex/...` (via build_codex_plugin.build)

Per ADR-0018 the repository root stays canonical source and each `hosts/<host>/`
tree is the clean, runtime install payload its host's marketplace pointer
resolves to.

Slice 061-03 adds a regenerate-and-diff **drift guard** so the committed
packages are safe to keep in git: `--check` rebuilds into a scratch dir and
diffs against the committed `hosts/` tree (read-only — it never mutates it),
exiting non-zero with an actionable summary that names each stale path and the
regenerate command. CI runs the guard so a PR that edits source without
regenerating cannot merge silently.

Contributor loop: edit source -> `python3 scripts/build_host_packages.py` ->
commit `hosts/` (see docs/workflow.md).

Usage:
    # rebuild both committed packages in place:
    python3 scripts/build_host_packages.py [--source-root <root>] [--hosts-root <dir>]
    # drift guard (no in-place rebuild; exits non-zero when stale):
    python3 scripts/build_host_packages.py --check

Default hosts root: <source-root>/hosts
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import build_claude_plugin  # noqa: E402
import build_codex_plugin  # noqa: E402


def build_all(source_root: Path, hosts_root: Path, out=None) -> int:
    """Build the Claude and Codex committed packages under `hosts_root`.

    Returns 0 only if BOTH builders succeed; the first non-zero builder exit
    code otherwise. Both builders are invoked regardless so a single run
    reports every problem rather than stopping at the first."""
    if out is None:
        out = sys.stdout
    source_root = source_root.resolve()
    hosts_root = hosts_root.resolve()

    claude_out = hosts_root / "claude"
    codex_out = hosts_root / "codex" / "plugins" / "jig"

    claude_code = build_claude_plugin.build(
        source_root=source_root, output_dir=claude_out, out=out
    )
    codex_code = build_codex_plugin.build(
        source_root=source_root, output_dir=codex_out
    )
    if codex_code == 0:
        out.write(f"OK: built Codex plugin at {codex_out}\n")
    else:
        out.write(f"ERROR: Codex package build exited {codex_code}\n")

    return claude_code or codex_code


REGEN_COMMAND = "python3 scripts/build_host_packages.py"


def _is_ephemeral(rel: Path) -> bool:
    """True for paths the builders never emit but a test/import run may leave
    behind in a committed tree (Python bytecode caches). Excluding them keeps
    the drift compare deterministic: CI runs the test suite *before* the guard,
    and importing a module out of `hosts/` would otherwise seed a `__pycache__`
    that the freshly-built scratch tree lacks, spuriously reading as drift."""
    return "__pycache__" in rel.parts or rel.suffix == ".pyc"


def _file_map(root: Path) -> dict[str, bytes]:
    """Map every file under `root` to its bytes, keyed by posix relpath.

    Empty when `root` is absent so a missing committed tree reads as a fully
    drifted (every-file-stale) package rather than an error. Ephemeral bytecode
    caches are skipped (see `_is_ephemeral`) so the compare matches what the
    builders actually emit (they exclude `__pycache__`)."""
    result: dict[str, bytes] = {}
    if not root.is_dir():
        return result
    for path in sorted(root.rglob("*")):
        if path.is_file() and not _is_ephemeral(path.relative_to(root)):
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _diff_packages(expected_root: Path, committed_root: Path) -> list[str]:
    """Return sorted posix relpaths that differ between a freshly-built tree
    (`expected_root`) and the committed tree (`committed_root`): files that are
    modified, missing from the committed tree, or extra in it."""
    expected = _file_map(expected_root)
    committed = _file_map(committed_root)
    drifted = set()
    for rel, data in expected.items():
        if committed.get(rel) != data:
            drifted.add(rel)
    for rel in committed:
        if rel not in expected:
            drifted.add(rel)
    return sorted(drifted)


def check_drift(source_root: Path, hosts_root: Path, out=None) -> int:
    """Regenerate both packages into a scratch dir and diff against the
    committed `hosts_root`. Returns 0 when in sync; 1 with an actionable
    summary (naming each stale path + the regenerate command) when they drift.

    The committed tree is never mutated — the rebuild lands in a tempdir that is
    removed before returning (drift check is read-only against `hosts_root`)."""
    if out is None:
        out = sys.stdout
    source_root = source_root.resolve()
    hosts_root = hosts_root.resolve()

    scratch = Path(tempfile.mkdtemp(prefix="jig-host-drift-"))
    try:
        # Swallow the builders' progress chatter — the drift summary is the
        # only signal a `--check` caller (CI, contributors) needs.
        sink = type("_Sink", (), {"write": staticmethod(lambda *_a, **_k: None)})()
        code = build_all(source_root=source_root, hosts_root=scratch, out=sink)
        if code != 0:
            out.write(
                "ERROR: could not regenerate host packages for the drift "
                f"check (build exited {code}).\n"
            )
            return 1

        drifted = _diff_packages(scratch, hosts_root)
        if not drifted:
            out.write("OK: committed host packages are in sync with source.\n")
            return 0

        out.write(
            "ERROR: committed host packages are stale relative to source.\n"
            f"  {len(drifted)} path(s) differ under {hosts_root}:\n"
        )
        for rel in drifted:
            out.write(f"    - hosts/{rel}\n")
        out.write(
            "Regenerate and commit the host packages:\n"
            f"    {REGEN_COMMAND}\n"
            "    git add hosts/\n"
        )
        return 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_host_packages.py",
        description="materialize jig's committed Claude and Codex packages",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--hosts-root",
        default=None,
        help="root for committed host packages (default: <source-root>/hosts)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "drift guard: regenerate into a scratch dir and diff against the "
            "committed hosts/ tree, exiting non-zero (without mutating it) "
            "when they differ — does not rebuild in place"
        ),
    )
    return parser


def main(argv: list[str]) -> int:
    ns = _build_parser().parse_args(argv[1:])
    source_root = Path(ns.source_root)
    hosts_root = (
        Path(ns.hosts_root) if ns.hosts_root else source_root / "hosts"
    )
    if ns.check:
        return check_drift(source_root=source_root, hosts_root=hosts_root)
    return build_all(source_root=source_root, hosts_root=hosts_root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
