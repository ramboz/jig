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


# ----------------------------------------------------------------------------
# Scaffold-mode checks (slice 016-03 AC #4)
# ----------------------------------------------------------------------------
#
# The plugin-mode checks above validate that jig's plugin install footprint
# is on disk (`.claude-plugin/...` etc.). When jig is installed via
# `scaffold-init` (default-on as of slice 016-03), the artifacts live under
# `<project>/.claude/` instead, with a `jig-` prefix to namespace them away
# from user-added project skills. The four scaffold-mode checks mirror the
# four plugin-mode checks (skills / agents / hook scripts / settings.json
# registration), but against the project tree.


_EXPECTED_HOOK_SCRIPTS = (
    "jig-boundary-change-warn.sh",
    "jig-context-check.sh",
    "jig-memory-scan.sh",
    "jig-post-edit-verify.sh",
    "jig-secret-scan.sh",  # slice 052-02 — secret-prevention floor (ADR-0013)
    "jig-spec-gate.sh",
    "jig-task-capture.sh",
    "jig-telemetry.sh",
)


def check_scaffold_skills_present(project_root: Path) -> CheckResult:
    """At least one `.claude/skills/jig-*/SKILL.md` exists under the
    project root."""
    skills_dir = project_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return False, f".claude/skills/ dir missing at {skills_dir}"
    skill_mds = list(skills_dir.glob("jig-*/SKILL.md"))
    if not skill_mds:
        return False, (
            f"no jig-prefixed skill SKILL.md files found under {skills_dir}"
        )
    return True, f"{len(skill_mds)} scaffolded skill SKILL.md file(s) present"


def check_scaffold_agents_present(project_root: Path) -> CheckResult:
    """All three jig-prefixed agent files are at the expected path."""
    agents_dir = project_root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return False, f".claude/agents/ dir missing at {agents_dir}"
    missing = [
        name for name in _REQUIRED_AGENTS
        if not (agents_dir / f"jig-{name}.md").is_file()
    ]
    if missing:
        return False, (
            f"missing scaffolded agent file(s): "
            f"{', '.join('jig-' + n + '.md' for n in missing)}"
        )
    return True, "all three scaffolded subagent definitions present"


def check_scaffold_hook_scripts_present(project_root: Path) -> CheckResult:
    """All expected jig hook scripts exist under `.claude/hooks/scripts/`."""
    scripts_dir = project_root / ".claude" / "hooks" / "scripts"
    if not scripts_dir.is_dir():
        return False, f".claude/hooks/scripts/ dir missing at {scripts_dir}"
    missing = [
        name for name in _EXPECTED_HOOK_SCRIPTS
        if not (scripts_dir / name).is_file()
    ]
    if missing:
        return False, f"missing hook script(s): {', '.join(missing)}"
    return True, (
        f"all {len(_EXPECTED_HOOK_SCRIPTS)} scaffolded hook scripts present"
    )


def check_scaffold_settings_registration(project_root: Path) -> CheckResult:
    """`.claude/settings.json` parses as JSON and has at least one
    jig-managed hook entry (`metadata.managed_by_jig: true`)."""
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return False, f"settings.json missing at {settings_path}"
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"settings.json is not valid JSON: {exc}"
    hooks = data.get("hooks") or {}
    jig_entries = [
        entry
        for entries in hooks.values()
        for entry in (entries or [])
        if bool((entry.get("metadata") or {}).get("managed_by_jig"))
    ]
    if not jig_entries:
        return False, (
            "settings.json has no jig-managed hook entries "
            "(metadata.managed_by_jig marker missing on every entry)"
        )
    return True, (
        f"settings.json registers {len(jig_entries)} jig-managed hook "
        "entry/entries"
    )


# ----------------------------------------------------------------------------
# Security-floor presence checks (slice 052-04 AC3, ADR-0013)
# ----------------------------------------------------------------------------
#
# The floor — secret-scan hook + conservative `permissions.deny` + secret-
# ignore `.gitignore` — is scaffolded by slices 052-02/03 and brought to
# existing projects by `migrate copy-machinery` (slice 052-04). These checks
# assert it is on disk so a scaffolded/migrated project missing any single
# floor artifact reports exactly which one (the spec-047 contract validator
# is DRAFT and not landed, so this is the minimal floor-presence check the
# DoR calls for — it does NOT block on 047). verify_install.py is stdlib-only
# and never imports scaffold.py, so the expected markers below are hardcoded
# with a source-of-truth pointer (the same precedent as `_EXPECTED_HOOK_SCRIPTS`).

# Source of truth: scaffold.py `_PERMISSIONS_DENY_DEFAULTS` (slice 052-03).
# A stable AC1-named representative SUBSET — force-push, hard-reset, rm -rf —
# checked with issubset so user-added deny entries are tolerated. The full
# defaults set is asserted in test_scaffold.py::PermissionsDenyTests; here we
# only confirm the floor's conservative guardrails survived the merge.
_EXPECTED_DENY_GLOBS = (
    "Bash(git push --force*)",
    "Bash(git reset --hard*)",
    "Bash(rm -rf*)",
)

# Source of truth: scaffold.py `_GITIGNORE_BLOCK_BEGIN` (slice 052-02) and a
# representative pair of `_GITIGNORE_SECRET_PATTERNS`.
_EXPECTED_GITIGNORE_MARKER = "# >>> jig secret-ignore >>>"
_EXPECTED_GITIGNORE_PATTERNS = (".env", "*.pem")

# Source of truth: scaffold.py hook registration — the secret-scan hook is
# registered against the `Edit|Write|MultiEdit` matcher with a jig marker.
_SECRET_SCAN_SCRIPT = "jig-secret-scan.sh"
_SECRET_SCAN_MATCHER = "Edit|Write|MultiEdit"


def check_scaffold_secret_scan_registered(project_root: Path) -> CheckResult:
    """`.claude/settings.json` registers the secret-scan hook: a jig-managed
    (`metadata.managed_by_jig`) `Edit|Write|MultiEdit` entry whose command
    references `jig-secret-scan.sh`. Stronger than the generic registration
    check — it pins the specific floor hook, not just *any* jig hook."""
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return False, f"settings.json missing at {settings_path}"
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"settings.json is not valid JSON: {exc}"
    pre = (data.get("hooks") or {}).get("PreToolUse") or []
    for entry in pre:
        if entry.get("matcher") != _SECRET_SCAN_MATCHER:
            continue
        if not bool((entry.get("metadata") or {}).get("managed_by_jig")):
            continue
        for h in entry.get("hooks", []):
            if _SECRET_SCAN_SCRIPT in (h.get("command") or ""):
                return True, (
                    "settings.json registers the secret-scan hook "
                    f"({_SECRET_SCAN_SCRIPT}) on a jig-managed "
                    f"{_SECRET_SCAN_MATCHER} entry"
                )
    return False, (
        f"settings.json has no jig-managed {_SECRET_SCAN_MATCHER} entry "
        f"referencing {_SECRET_SCAN_SCRIPT} (secret-scan hook not registered)"
    )


def check_scaffold_permissions_deny_floor(project_root: Path) -> CheckResult:
    """`.claude/settings.json` `permissions.deny` contains the conservative
    destructive-command guardrails (force-push / hard-reset / `rm -rf`).
    Subset (issubset) check, so user-added deny entries are tolerated."""
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return False, f"settings.json missing at {settings_path}"
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"settings.json is not valid JSON: {exc}"
    deny = set((data.get("permissions") or {}).get("deny") or [])
    missing = [g for g in _EXPECTED_DENY_GLOBS if g not in deny]
    if missing:
        return False, (
            "permissions.deny missing conservative guardrail(s): "
            f"{', '.join(missing)}"
        )
    return True, (
        f"permissions.deny carries all {len(_EXPECTED_DENY_GLOBS)} "
        "representative destructive-command guardrails"
    )


def check_scaffold_gitignore_secret_floor(project_root: Path) -> CheckResult:
    """`.gitignore` exists and carries the jig secret-ignore block (marker +
    at least the `.env` / `*.pem` patterns)."""
    gitignore = project_root / ".gitignore"
    if not gitignore.is_file():
        return False, f".gitignore missing at {gitignore}"
    text = gitignore.read_text()
    if _EXPECTED_GITIGNORE_MARKER not in text:
        return False, (
            f".gitignore is missing the jig secret-ignore marker "
            f"({_EXPECTED_GITIGNORE_MARKER!r})"
        )
    missing = [p for p in _EXPECTED_GITIGNORE_PATTERNS if p not in text]
    if missing:
        return False, (
            f".gitignore secret block missing pattern(s): {', '.join(missing)}"
        )
    return True, ".gitignore carries the jig secret-ignore floor"


_SCAFFOLD_CHECKS: list[tuple[str, Check]] = [
    ("skills", check_scaffold_skills_present),
    ("agents", check_scaffold_agents_present),
    ("hooks", check_scaffold_hook_scripts_present),
    ("settings", check_scaffold_settings_registration),
    # Slice 052-04 — security-floor presence (ADR-0013).
    ("secret-scan", check_scaffold_secret_scan_registered),
    ("permissions-deny", check_scaffold_permissions_deny_floor),
    ("gitignore-floor", check_scaffold_gitignore_secret_floor),
]


def run_all_scaffold_checks(project_root: Path) -> list[CheckResult]:
    """Run every scaffold-mode check; return list of (passed, message)."""
    return [check(project_root) for _, check in _SCAFFOLD_CHECKS]


def _looks_unscaffolded(project_root: Path) -> bool:
    """`.claude/` directory entirely absent → the project was never
    scaffolded with `--with-machinery` (default-on as of slice 016-03).
    Mirrors `_looks_uninstalled` semantics for plugin mode."""
    return not (project_root / ".claude").exists()


# ----------------------------------------------------------------------------
# Scaffold seed-presence check (slice 048-06 AC #3)
# ----------------------------------------------------------------------------
#
# The worked-example reference spec (slice 048-05) is emitted into a
# greenfield `docs/specs/` — `001-adopt-jig/` (spec + bootstrap slice),
# `002-first-spec/` (DRAFT stub), and a populated status board. The
# completion summary confirms the seed is present so a scaffold that
# dropped the worked example is reported as a failure (AC #3 / AC #4).
#
# The seed ships in BOTH `--with-machinery` and `--plugin-only` modes
# (docs are emitted in both), so this check is mode-independent. It is,
# however, greenfield-only: when `docs/specs/` already had user content
# the seed is deliberately skipped, and the caller must NOT run this check
# in that case (skipping a seed is not a failure — see `run_completion_summary`).


_EXPECTED_SEED_FILES = (
    "docs/specs/001-adopt-jig/spec.md",
    "docs/specs/001-adopt-jig/slice-01-bootstrap.md",
    "docs/specs/002-first-spec/spec.md",
    "docs/specs/README.md",
)


def check_scaffold_seed_present(project_root: Path) -> CheckResult:
    """The slice 048-05 worked-example seed is present under
    `docs/specs/`. A populated status board (`README.md`) plus the
    `001-adopt-jig` spec/slice and the `002-first-spec` stub must all
    exist; a scaffold missing any of them dropped the worked example."""
    missing = [
        rel for rel in _EXPECTED_SEED_FILES
        if not (project_root / rel).is_file()
    ]
    if missing:
        return False, (
            f"missing seed reference spec file(s): {', '.join(missing)}"
        )
    return True, (
        f"worked-example seed present "
        f"({len(_EXPECTED_SEED_FILES)} files under docs/specs/)"
    )


def run_completion_summary(
    project_root: Path,
    *,
    with_machinery: bool,
    seed_expected: bool,
    out=None,
) -> int:
    """Run the scaffold-completion verification and print a compact,
    human-readable summary (per-check PASS/FAIL + overall verdict) for
    the `scaffold-init` wizard's closing report (slice 048-06).

    Mode-awareness (the correctness nuance): the four machinery checks
    (`skills` / `agents` / `hooks` / `settings`) validate `.claude/`
    artifacts that exist ONLY in `--with-machinery` (in-repo) mode. In
    `--plugin-only` mode that machinery lives in the installed plugin,
    not the target, so running those checks would false-fail a perfectly
    good plugin-only scaffold. They are therefore included only when
    `with_machinery=True`. The seed/docs presence check (AC #3) runs in
    BOTH modes — but only when `seed_expected=True`; a non-greenfield
    scaffold legitimately skipped the seed and must not report it missing.

    Returns 0 when every applicable check passed, 1 otherwise — so a
    failed check is loud and actionable (AC #4), never a silent partial
    scaffold."""
    if out is None:
        out = sys.stdout

    mode_label = "in-repo (machinery)" if with_machinery else "plugin-only"

    checks: list[tuple[str, Check]] = []
    if with_machinery:
        checks.extend(_SCAFFOLD_CHECKS)
    if seed_expected:
        checks.append(("seed", check_scaffold_seed_present))

    out.write(f"\nScaffold verification — mode: {mode_label}\n")

    if not checks:
        # plugin-only + seed skipped (non-greenfield): nothing machinery-
        # specific to verify here. Still emit an explicit, non-silent line.
        out.write(
            "  (no scaffold-mode checks apply in this mode; machinery "
            "lives in the installed plugin)\n"
        )
        out.write("Scaffold complete and verified — 0/0 checks passed.\n")
        return 0

    failed = []
    for name, check in checks:
        passed, msg = check(project_root)
        marker = "PASS" if passed else "FAIL"
        out.write(f"  [{marker}] {name}: {msg}\n")
        if not passed:
            failed.append((name, msg))

    total = len(checks)
    passed_count = total - len(failed)
    if failed:
        out.write(
            f"SCAFFOLD VERIFICATION FAILED — {passed_count}/{total} checks "
            f"passed. Missing/broken:\n"
        )
        for name, msg in failed:
            out.write(f"  - {name}: {msg}\n")
        return 1

    out.write(
        f"Scaffold complete and verified — {passed_count}/{total} "
        "checks passed.\n"
    )
    return 0


def run_headless_scaffold(project_root: Path, out=None) -> int:
    """Run all scaffold-mode static checks; write one line per check +
    summary. Mirrors `run_headless`'s exit-code convention: 0 (all
    passed), 1 (at least one failed), 2 (project not scaffolded at all
    — actionable error)."""
    if out is None:
        out = sys.stdout
    if _looks_unscaffolded(project_root):
        out.write(
            f"FAIL — project not scaffolded at {project_root} "
            "(run `scaffold-init` to install jig into the project)\n"
        )
        return 2

    results = run_all_scaffold_checks(project_root)
    failed = 0
    for (name, _), (passed, msg) in zip(_SCAFFOLD_CHECKS, results):
        marker = "PASS" if passed else "FAIL"
        out.write(f"{marker} {name}: {msg}\n")
        if not passed:
            failed += 1

    total = len(results)
    out.write(f"summary: {total - failed}/{total} passed\n")
    return 0 if failed == 0 else 1


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
        description="verify that jig is installed (plugin or scaffold mode)",
    )
    p.add_argument(
        "--plugin-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="path to jig's plugin root (defaults to the script's repo root)",
    )
    p.add_argument(
        "--project-root",
        default=None,
        help="path to a scaffolded project root (used with --mode scaffold; "
             "defaults to the current working directory in scaffold mode)",
    )
    p.add_argument(
        "--mode",
        choices=("plugin", "scaffold"),
        default="plugin",
        help="install shape to verify: `plugin` checks the installed plugin "
             "footprint (today's default); `scaffold` checks the project's "
             "`.claude/` tree produced by scaffold-init (slice 016-03)",
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

    if ns.mode == "scaffold":
        # In scaffold mode, default the project root to the current working
        # directory when the user didn't pass --project-root. The plugin-root
        # default doesn't apply here — it's a separate concept.
        project_root = Path(
            ns.project_root if ns.project_root else Path.cwd()
        )
        return run_headless_scaffold(project_root)

    return run_headless(Path(ns.plugin_root))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
