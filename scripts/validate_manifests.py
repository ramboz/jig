"""
validate_manifests.py — slice 013-01 (ci-baseline);
strengthened in slice 047-01 (plugin-release-contract-validator).

Validates that the three top-level JSON manifests in jig's repo are present,
well-formed, and satisfy the install contract. Designed to run in CI before
release-please or zip packaging touches them, so a malformed manifest is
caught at PR review time instead of breaking the release pipeline.

Files checked (slice 047-01 routes the first two through `install_contract`
so the manifest contract lives in one place):
    .claude-plugin/plugin.json       — name + version + description
    .claude-plugin/marketplace.json  — name, owner.name, non-empty plugins[]
                                       (each name/source/description with a
                                       relative source path)
    hooks/hooks.json                 — parseable JSON; command shape is
                                       validated by verify_install's
                                       hook-contract check, which needs the
                                       on-disk scripts to resolve references

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
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_contract  # noqa: E402  — the plugin/release install contract


# A field-level validator takes the parsed manifest data and returns a list
# of human-readable problem strings (empty == valid). Routing plugin.json and
# marketplace.json through `install_contract` keeps the manifest contract in
# one testable place (AC #1) and gives path-specific diagnostics (AC #4).
ContractValidator = Callable[[dict], "list[str]"]


@dataclass(frozen=True)
class ManifestSpec:
    relative_path: str
    required_fields: tuple[str, ...] = ()
    validator: ContractValidator | None = None


_MANIFESTS: tuple[ManifestSpec, ...] = (
    ManifestSpec(
        ".claude-plugin/plugin.json",
        validator=install_contract.validate_plugin_manifest,
    ),
    ManifestSpec(
        ".claude-plugin/marketplace.json",
        validator=install_contract.validate_marketplace_manifest,
    ),
    ManifestSpec("hooks/hooks.json"),
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

    # Bare required-field check (retained for any spec that uses it).
    missing = [
        f for f in spec.required_fields
        if not isinstance(data, dict) or f not in data
    ]
    if missing:
        fields = ", ".join(missing)
        return False, f"FAIL {name}: missing required field(s): {fields}"

    # Full contract validation (plugin.json / marketplace.json). Each problem
    # already names the offending field/path and the rule, so the FAIL line
    # is actionable (AC #4).
    if spec.validator is not None:
        problems = spec.validator(data)
        if problems:
            return False, f"FAIL {name}: " + "; ".join(problems)

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
