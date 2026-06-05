"""
build_host_packages.py — slice 061-02 (unified host-package build entry point).

Builds BOTH committed host packages from canonical source in one invocation:

  - the Claude package at `hosts/claude/`   (via build_claude_plugin.build)
  - the Codex package at  `hosts/codex/...` (via build_codex_plugin.build)

Per ADR-0018 the repository root stays canonical source and each `hosts/<host>/`
tree is the clean, runtime install payload its host's marketplace pointer
resolves to. Slice 061-03 wraps this single entry point in a regenerate-and-diff
drift guard; this slice just provides the entry point so both packages are
regenerated in one step.

Usage:
    python3 scripts/build_host_packages.py [--source-root <root>] [--hosts-root <dir>]

Default hosts root: <source-root>/hosts
"""

from __future__ import annotations

import argparse
import sys
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
    return parser


def main(argv: list[str]) -> int:
    ns = _build_parser().parse_args(argv[1:])
    source_root = Path(ns.source_root)
    hosts_root = (
        Path(ns.hosts_root) if ns.hosts_root else source_root / "hosts"
    )
    return build_all(source_root=source_root, hosts_root=hosts_root)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
