"""
verify_install.py — slice 011-01 (local-plugin-install)

Two modes, picked via subcommand:

- **headless (default):** static checks that the install footprint is
  present at `--plugin-root` (or the script's own repo root). Runs in
  `python3 -m unittest`; exits 0 (all passed), 1 (at least one check
  failed), or 2 (environment error — plugin not installed at all).

- **probe:** print the capability-probe prompt for one of the three
  subagent types (reviewer / implementer / architect) to a temp path
  the caller chose. Used by the live-verify runbook in CONTRIBUTING.md
  — the runbook tells Claude to spawn each subagent with this prompt
  and check whether the temp file was created (`reviewer` should
  refuse / fail; `implementer` and `general-purpose` should succeed).

The script never spawns subagents itself; the Task tool is Claude-driven.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

class VerifyError(RuntimeError):
    """Raised when verify_install is called with an unknown agent type."""


# ----------------------------------------------------------------------------
# Static checks
# ----------------------------------------------------------------------------

CheckResult = tuple[bool, str]
Check = Callable[[Path], CheckResult]


def check_marketplace_descriptor(plugin_root: Path) -> CheckResult:
    """`.claude-plugin/marketplace.json` exists, parses, lists 'jig'."""
    path = plugin_root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return False, f"marketplace.json missing at {path}"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"marketplace.json is not valid JSON: {exc}"
    plugins = data.get("plugins") or []
    names = [p.get("name") for p in plugins if isinstance(p, dict)]
    if "jig" not in names:
        return False, f"marketplace.json does not list 'jig' (got {names!r})"
    return True, "marketplace.json present and lists 'jig'"


def check_plugin_manifest(plugin_root: Path) -> CheckResult:
    """`.claude-plugin/plugin.json` exists, parses, declares name 'jig'."""
    path = plugin_root / ".claude-plugin" / "plugin.json"
    if not path.is_file():
        return False, f"plugin.json missing at {path}"
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"plugin.json is not valid JSON: {exc}"
    if data.get("name") != "jig":
        return False, f"plugin.json name is {data.get('name')!r}, expected 'jig'"
    return True, "plugin.json present and well-formed"


_REQUIRED_AGENTS = ("implementer", "reviewer", "architect")


def check_agents_present(plugin_root: Path) -> CheckResult:
    """All three agent definition files are at the expected path."""
    agents_dir = plugin_root / "agents"
    if not agents_dir.is_dir():
        return False, f"agents/ dir missing at {agents_dir}"
    missing = [
        name for name in _REQUIRED_AGENTS
        if not (agents_dir / f"{name}.md").is_file()
    ]
    if missing:
        return False, f"missing agent file(s): {', '.join(missing)}"
    return True, "all three subagent definitions present"


def check_active_skills_present(plugin_root: Path) -> CheckResult:
    """At least one skill with a SKILL.md exists under skills/."""
    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        return False, f"skills/ dir missing at {skills_dir}"
    skill_mds = list(skills_dir.glob("*/SKILL.md"))
    if not skill_mds:
        return False, f"no skill SKILL.md files found under {skills_dir}"
    return True, f"{len(skill_mds)} skill SKILL.md file(s) reachable"


_CHECKS: list[tuple[str, Check]] = [
    ("marketplace", check_marketplace_descriptor),
    ("manifest", check_plugin_manifest),
    ("agents", check_agents_present),
    ("skills", check_active_skills_present),
]


def run_all_checks(plugin_root: Path) -> list[CheckResult]:
    """Run every static check; return list of (passed, message)."""
    return [check(plugin_root) for _, check in _CHECKS]


def _looks_uninstalled(plugin_root: Path) -> bool:
    """Distinguish 'plugin not installed at all' from 'install is broken'.

    If neither plugin.json nor marketplace.json nor agents/ exists, the
    plugin clearly isn't installed; emit a clear actionable error per
    AC #5 (exit 2) instead of cascading per-check failures.
    """
    return not (
        (plugin_root / ".claude-plugin" / "plugin.json").exists()
        or (plugin_root / ".claude-plugin" / "marketplace.json").exists()
        or (plugin_root / "agents").exists()
    )


def run_headless(plugin_root: Path, out=None) -> int:
    """Run all static checks; write one line per check + summary."""
    if out is None:
        out = sys.stdout
    if _looks_uninstalled(plugin_root):
        out.write(
            f"FAIL — jig plugin not installed at {plugin_root} "
            "(see CONTRIBUTING.md for setup)\n"
        )
        return 2

    results = run_all_checks(plugin_root)
    failed = 0
    for (name, _), (passed, msg) in zip(_CHECKS, results):
        marker = "PASS" if passed else "FAIL"
        out.write(f"{marker} {name}: {msg}\n")
        if not passed:
            failed += 1

    total = len(results)
    out.write(f"summary: {total - failed}/{total} passed\n")
    return 0 if failed == 0 else 1


# ----------------------------------------------------------------------------
# Live-mode probe prompts
# ----------------------------------------------------------------------------


_PROBE_TEMPLATE = """\
You are being invoked by the jig plugin's verify-install procedure as a
**{agent_type}** subagent. Your job for this probe is a single capability
test — do exactly this, nothing more:

1. Attempt to write the string `jig-verify-ok` to the file at:
   {temp_path}

2. Report back, in this exact shape (one line each):
   write_attempted: yes|no
   write_succeeded: yes|no
   refusal_reason: <empty if not refused, else one short sentence>

Do not read other files. Do not respond beyond the three lines above.
A real `reviewer` subagent (read-only tools — Read/Glob/Grep) is expected
to either refuse the write or report it failed. A real `implementer`
subagent (has Write) is expected to succeed. The `general-purpose`
fallback is expected to succeed. The verify-install runbook will check
the temp file's existence on disk and your reported lines to determine
the subagent_type that actually resolved.
"""


def probe_prompt(agent_type: str, temp_path: str) -> str:
    """Return the capability-probe prompt for `agent_type`."""
    if agent_type not in _REQUIRED_AGENTS:
        raise VerifyError(
            f"unknown agent type {agent_type!r}; "
            f"expected one of {_REQUIRED_AGENTS}"
        )
    return _PROBE_TEMPLATE.format(agent_type=agent_type, temp_path=temp_path)


# ----------------------------------------------------------------------------
# CLI plumbing
# ----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verify_install.py",
        description="verify that jig is installed as a local Claude Code plugin",
    )
    p.add_argument(
        "--plugin-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="path to jig's plugin root (defaults to the script's repo root)",
    )

    sub = p.add_subparsers(dest="command")

    sub.add_parser(
        "headless",
        help="run static checks on the install footprint (default)",
    )

    pp = sub.add_parser(
        "probe",
        help="print the capability-probe prompt for an agent type",
    )
    pp.add_argument(
        "agent_type",
        choices=list(_REQUIRED_AGENTS),
        help="which subagent type to probe",
    )
    pp.add_argument(
        "--temp-path",
        required=True,
        help="absolute path the subagent should attempt to write",
    )

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv[1:])

    if ns.command == "probe":
        sys.stdout.write(probe_prompt(ns.agent_type, ns.temp_path))
        return 0

    return run_headless(Path(ns.plugin_root))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
