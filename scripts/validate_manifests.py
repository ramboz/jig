"""
validate_manifests.py — slice 013-01 (ci-baseline).

Validates that the three top-level JSON manifests in jig's repo are present,
well-formed, and contain required fields. Designed to run in CI before
release-please or zip packaging touches them, so a malformed manifest is
caught at PR review time instead of breaking the release pipeline.

Files checked:
    .claude-plugin/plugin.json       — required field: "name"
    .claude-plugin/marketplace.json  — required field: "name"
    hooks/hooks.json                 — parseable JSON; no field requirement

Exit codes:
    0  all manifests valid
    1  at least one manifest failed validation
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ManifestSpec:
    relative_path: str
    required_fields: tuple[str, ...]


_MANIFESTS: tuple[ManifestSpec, ...] = (
    ManifestSpec(".claude-plugin/plugin.json", ("name",)),
    ManifestSpec(".claude-plugin/marketplace.json", ("name",)),
    ManifestSpec("hooks/hooks.json", ()),
)


def _check_one(root: Path, spec: ManifestSpec) -> tuple[bool, str]:
    """Return (passed, message) for a single manifest."""
    path = root / spec.relative_path
    name = Path(spec.relative_path).name
    if not path.is_file():
        return False, f"FAIL {name}: missing at {path}"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"FAIL {name}: invalid JSON ({exc.msg} at line {exc.lineno})"

    missing = [
        field for field in spec.required_fields
        if not isinstance(data, dict) or field not in data
    ]
    if missing:
        fields = ", ".join(missing)
        return False, f"FAIL {name}: missing required field(s): {fields}"

    return True, f"PASS {name}: well-formed"


def run(root: Path, out=None, manifests: Iterable[ManifestSpec] = _MANIFESTS) -> int:
    """Validate every manifest under `root`. Returns 0 on success, 1 on failure."""
    if out is None:
        out = sys.stdout
    specs = tuple(manifests)
    failed = 0
    for spec in specs:
        passed, msg = _check_one(root, spec)
        out.write(msg + "\n")
        if not passed:
            failed += 1
    total = len(specs)
    out.write(f"summary: {total - failed}/{total} manifest(s) valid\n")
    return 0 if failed == 0 else 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate_manifests.py",
        description="validate jig's top-level JSON manifests",
    )
    p.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="path to jig's repo root (defaults to the script's repo root)",
    )
    return p


def main(argv: list) -> int:
    ns = _build_parser().parse_args(argv[1:])
    return run(Path(ns.root))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
