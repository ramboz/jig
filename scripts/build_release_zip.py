"""
build_release_zip.py — host-explicit release zips (slice 061-04).

Builds ONE release zip per host, archived from the committed host packages
(`hosts/<host>/`, slice 061-02/03) rather than from a host-neutral walk of the
source root. Each zip is the clean install payload its host loads natively.

Usage:
    # Build the flat Claude plugin zip (drag-droppable / --plugin-dir):
    python3 scripts/build_release_zip.py --host claude --version 1.10.0 [--output <path>]

    # Build the Codex marketplace bundle (extract-then-add — NOT a directly
    # installable plugin zip):
    python3 scripts/build_release_zip.py --host codex --version 1.10.0 [--output <path>]

    # Smoke-test an existing zip (host required so the report names the host):
    python3 scripts/build_release_zip.py --host claude --smoke-test <path-to-zip>
    python3 scripts/build_release_zip.py --host codex  --smoke-test <path-to-zip>

Shapes:
    - Claude zip: archives `hosts/claude/` with arcnames relative to that root,
      so `.claude-plugin/plugin.json` lands at the zip root — flat and directly
      drag-droppable into Claude Code Desktop / loadable via `--plugin-dir`.
    - Codex zip: archives `hosts/codex/` with arcnames relative to that root, so
      the zip root holds `.agents/plugins/marketplace.json` and
      `plugins/jig/.codex-plugin/plugin.json`. Codex has no direct zip-drop;
      this is an extract-then-add marketplace bundle (extract, then
      `codex plugin marketplace add <extracted-dir>`).

Exit codes:
    0  zip built successfully / smoke-test passed
    1  build or smoke-test failed (I/O, missing package, validation)
    2  version mismatch between --version and the host's committed manifest
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_contract  # noqa: E402

HOSTS = ("claude", "codex")

# Relative path (within each `hosts/<host>/` package) to the manifest whose
# `version` field is the version-coherence source of truth for that host.
_HOST_MANIFEST_REL: dict[str, str] = {
    "claude": ".claude-plugin/plugin.json",
    "codex": "plugins/jig/.codex-plugin/plugin.json",
}

# ---------------------------------------------------------------------------
# Source-walk runtime contract (shared with the committed-package builders).
#
# These constants/predicates describe the runtime include/exclude *subset* of
# canonical SOURCE that the committed host packages are built from. They are
# delegated to `install_contract` rather than restated here. Slice 061-04
# archives zips from the already-filtered committed `hosts/` tree, but
# `build_claude_plugin.py` still imports these compatibility aliases while
# the contract itself stays single-sourced in `install_contract.py`.
# ---------------------------------------------------------------------------

_INCLUDE_ROOTS: tuple[str, ...] = install_contract.RELEASE_INCLUDE_ROOTS
_INCLUDE_FILES: tuple[str, ...] = install_contract.RELEASE_INCLUDE_FILES


def _is_excluded_dir(name: str) -> bool:
    return install_contract.is_excluded_release_path(f"{name}/placeholder")


def _is_excluded_file(name: str) -> bool:
    return install_contract.is_excluded_release_path(name)


def host_package_root(hosts_root: Path, host: str) -> Path:
    """The committed package root the zip is archived from, for `host`."""
    return hosts_root / host


def default_output_path(source_root: Path, host: str, version: str) -> Path:
    """Default zip output path: dist/jig-<host>-v<version>.zip."""
    return source_root / "dist" / f"jig-{host}-v{version}.zip"


def _iter_files(package_root: Path) -> Iterable[Path]:
    """Yield every file under `package_root` (relative to it) for the zip.

    Walks the whole committed package recursively, skipping defensive
    excludes. Arcnames are the returned relative paths, so e.g. the Claude
    package's `.claude-plugin/plugin.json` lands at the zip root.
    """
    for path in package_root.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(package_root)
        if install_contract.is_excluded_release_path(rel.as_posix()):
            continue
        yield rel


# A fixed timestamp for every zip entry so two builds produce bit-identical
# bytes. 2026-01-01 00:00:00 UTC is well after the zip-format minimum (1980).
_DETERMINISTIC_MTIME = (2026, 1, 1, 0, 0, 0)


def _add_entry(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(filename=arcname, date_time=_DETERMINISTIC_MTIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    # 0o644 for files. The high two bytes of external_attr encode unix mode.
    info.external_attr = (0o644 & 0xFFFF) << 16
    # Pin create_system to 3 (Unix) so macOS and Linux CI agree byte-for-byte.
    info.create_system = 3
    zf.writestr(info, data)


def _read_manifest_version(package_root: Path, host: str) -> tuple[str | None, str | None]:
    """Return (version, error). `error` is a human message when unreadable."""
    manifest = package_root / _HOST_MANIFEST_REL[host]
    if not manifest.is_file():
        return None, (
            f"committed {host} package manifest missing at {manifest}; "
            "run python3 scripts/build_host_packages.py"
        )
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as exc:
        return None, f"{manifest}: invalid JSON: {exc}"
    return data.get("version"), None


def build(
    host: str,
    hosts_root: Path,
    version: str,
    output_path: Path,
    out=None,
) -> int:
    """Archive the committed `hosts/<host>/` package into `output_path`.

    Returns 0 on success, 2 on version mismatch (a stale / mislabeled
    package), 1 on other failure. The version-coherence check reads the host's
    OWN committed manifest, so a `hosts/` tree built before the release bump
    fails here rather than shipping a mislabeled artifact.
    """
    if out is None:
        out = sys.stdout

    if host not in HOSTS:
        out.write(f"FAIL: unknown host {host!r}; expected one of {HOSTS}\n")
        return 1

    package_root = host_package_root(hosts_root, host)
    if not package_root.is_dir():
        out.write(
            f"FAIL: committed {host} package not found at {package_root}; "
            "run python3 scripts/build_host_packages.py\n"
        )
        return 1

    # Version coherence: the host's committed manifest must match --version.
    pkg_version, error = _read_manifest_version(package_root, host)
    if error:
        out.write(f"FAIL: {error}\n")
        return 1
    if pkg_version != version:
        out.write(
            f"FAIL: version mismatch — requested {version!r} but the committed "
            f"{host} package declares {pkg_version!r}. "
            "Refusing to produce a mislabeled artifact.\n"
        )
        return 2

    entries = sorted(_iter_files(package_root), key=lambda p: p.as_posix())
    if not entries:
        out.write(f"FAIL: committed {host} package at {package_root} is empty\n")
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in entries:
            data = (package_root / rel).read_bytes()
            _add_entry(zf, rel.as_posix(), data)

    if host == "claude":
        out.write(
            f"OK: built claude zip {output_path} ({len(entries)} entries, "
            f"version {version}) — flat, drag-droppable Claude plugin "
            "(.claude-plugin/plugin.json at the root; loadable via "
            "--plugin-dir).\n"
        )
    else:  # codex
        out.write(
            f"OK: built codex zip {output_path} ({len(entries)} entries, "
            f"version {version}) — an extract-then-add marketplace bundle: "
            "extract, then `codex plugin marketplace add <extracted-dir>`. "
            "Codex has no zip-drop install; do not treat this as a plugin "
            "zip you load in place.\n"
        )
    return 0


def _smoke_claude(extracted: Path, out) -> int:
    """Validate the extracted flat Claude plugin tree.

    Reuses install_contract.validate_claude_package — the single source of
    truth for the committed Claude install-tree shape (spec 061-01 / 047):
    `.claude-plugin/plugin.json` + every expected skill/agent, and NO
    marketplace.json (the remote-install pointer stays at the repo root) and NO
    `.codex-plugin/` content. verify_install.run_headless is the WRONG validator
    here: it requires `.claude-plugin/marketplace.json`, which the committed
    Claude package deliberately omits.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import install_contract  # noqa: E402

    problems = install_contract.validate_claude_package(extracted)
    if problems:
        out.write(
            "FAIL smoke[claude]: extracted flat Claude plugin "
            "(drag-droppable) FAILED validation — " + "; ".join(problems) + "\n"
        )
        return 1
    out.write(
        "PASS smoke[claude]: extracted flat Claude plugin (drag-droppable) "
        "validated — .claude-plugin/plugin.json at root, all skills/agents "
        "present.\n"
    )
    return 0


def _smoke_codex(extracted: Path, out) -> int:
    """Validate the extracted Codex marketplace bundle.

    Reuses codex_install_smoke._validate_generated_package against the
    extracted marketplace root + its plugin dir. The full live-CLI probe is
    deferred to slice 061-06/07; package validation is enough here.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import codex_install_smoke  # noqa: E402

    marketplace_root = extracted
    plugin_dir = extracted / "plugins" / "jig"
    result = codex_install_smoke._validate_generated_package(
        plugin_dir=plugin_dir, marketplace_root=marketplace_root
    )
    passed = result.status == codex_install_smoke.PASS
    marker = "PASS" if passed else "FAIL"
    out.write(
        f"{marker} smoke[codex]: extract-then-add marketplace bundle "
        f"(extract, then `codex plugin marketplace add`) — {result.message}\n"
    )
    return 0 if passed else 1


def smoke_test(host: str, zip_path: Path, out=None) -> int:
    """Extract `zip_path` and validate it for `host`. Names the host in output.

    Claude: extract + install_contract.validate_claude_package on the flat tree
            (NOT verify_install.run_headless — the committed Claude package omits
            the marketplace.json that run_headless requires; see _smoke_claude).
    Codex:  extract + codex_install_smoke._validate_generated_package on the
            extracted marketplace bundle.
    """
    import tempfile

    if out is None:
        out = sys.stdout

    if host not in HOSTS:
        out.write(f"FAIL smoke[{host}]: unknown host {host!r}; expected one of {HOSTS}\n")
        return 1

    zip_path = Path(zip_path)
    if not zip_path.is_file():
        out.write(f"FAIL smoke[{host}]: zip not found at {zip_path}\n")
        return 1

    with tempfile.TemporaryDirectory(prefix=f"jig-smoke-{host}-") as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_path)
        if host == "claude":
            return _smoke_claude(tmp_path, out)
        return _smoke_codex(tmp_path, out)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_release_zip.py",
        description="build (or smoke-test) a host-explicit release zip from the "
                    "committed hosts/ packages",
    )
    p.add_argument(
        "--host",
        required=True,
        choices=HOSTS,
        help="which committed host package to archive / smoke-test "
             "(claude = flat plugin zip; codex = extract-then-add marketplace bundle)",
    )
    p.add_argument(
        "--version",
        default=None,
        help="release version (must match the host package's committed manifest) "
             "— required in build mode",
    )
    p.add_argument(
        "--output",
        default=None,
        help="output zip path (default: dist/jig-<host>-v<version>.zip)",
    )
    p.add_argument(
        "--source-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="path to jig's source root (default: the script's repo root)",
    )
    p.add_argument(
        "--hosts-root",
        default=None,
        help="root of the committed host packages (default: <source-root>/hosts)",
    )
    p.add_argument(
        "--smoke-test",
        metavar="ZIP",
        default=None,
        help="instead of building, extract the named zip and validate it for --host",
    )
    return p


def main(argv: list) -> int:
    ns = _build_parser().parse_args(argv[1:])

    if ns.smoke_test:
        return smoke_test(ns.host, Path(ns.smoke_test))

    if not ns.version:
        sys.stderr.write("ERROR: --version is required unless --smoke-test is given\n")
        return 2

    source_root = Path(ns.source_root)
    hosts_root = Path(ns.hosts_root) if ns.hosts_root else source_root / "hosts"
    output = (
        Path(ns.output)
        if ns.output
        else default_output_path(source_root, ns.host, ns.version)
    )
    return build(
        host=ns.host,
        hosts_root=hosts_root,
        version=ns.version,
        output_path=output,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
