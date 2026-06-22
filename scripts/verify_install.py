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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_contract  # noqa: E402  — the plugin/release install contract
import scaffold_contract  # noqa: E402  — the scaffold-target install contract


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


# The three subagent role definitions the plugin ships. Mirrored by
# install_contract.REQUIRED_AGENTS (pinned equal by the contract's
# consistency test) — kept defined here too because the probe CLI and the
# scaffold-mode checks reference it directly.
_REQUIRED_AGENTS = install_contract.REQUIRED_AGENTS


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
    """Every skill in the install contract has a SKILL.md under skills/.

    Slice 047-01 (AC #3): tightened from "at least one skill" to the full
    declared set (`install_contract.EXPECTED_SKILLS`). Any missing skill is
    named with the expected rule (AC #4)."""
    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        return False, f"skills/ dir missing at {skills_dir}"
    missing = install_contract.missing_skills(plugin_root)
    if missing:
        return False, "; ".join(missing)
    return True, (
        f"all {len(install_contract.EXPECTED_SKILLS)} contract skills present"
    )


def check_hook_contract(plugin_root: Path) -> CheckResult:
    """`hooks/hooks.json` exists, parses, and every hook command follows the
    jig convention (`bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>`) and
    points at a script that exists under `hooks/scripts/`.

    Slice 047-01 (AC #2): plugin mode validated NO hooks before this slice.
    Routes through `install_contract.validate_hooks` so the registration
    source of truth (hooks.json) is checked against the on-disk scripts.
    Each failure names the offending entry and the expected rule (AC #4)."""
    hooks_json = plugin_root / "hooks" / "hooks.json"
    if not hooks_json.is_file():
        return False, f"hooks.json missing at {hooks_json}"
    try:
        data = json.loads(hooks_json.read_text())
    except json.JSONDecodeError as exc:
        return False, f"hooks.json is not valid JSON: {exc}"
    problems = install_contract.validate_hooks(
        data, plugin_root / "hooks" / "scripts"
    )
    if problems:
        return False, "; ".join(problems)
    referenced = install_contract.parse_hook_script_names(data)
    return True, (
        f"hooks.json registers {len(referenced)} hook script(s), all "
        "well-formed and present"
    )


_CHECKS: list[tuple[str, Check]] = [
    ("marketplace", check_marketplace_descriptor),
    ("manifest", check_plugin_manifest),
    ("agents", check_agents_present),
    ("skills", check_active_skills_present),
    # Slice 047-01 (AC #2) — hooks.json command shape + script existence.
    ("hooks", check_hook_contract),
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


# Source of truth: hooks/hooks.json (the registration manifest). This
# restated tuple is pinned equal to the hooks.json-derived set by
# test_verify_install.py::HookScriptDriftConsistencyTests so it cannot drift
# (slice 047-01 item 5 caught it missing `jig-skill-trace.sh` — the Skill
# PreToolUse trace hook — which hooks.json has registered since spec 030).
_EXPECTED_HOOK_SCRIPTS = (
    "jig-boundary-change-warn.sh",
    "jig-context-check.sh",
    "jig-memory-scan.sh",
    "jig-post-edit-verify.sh",
    "jig-secret-scan.sh",  # slice 052-02 — secret-prevention floor (ADR-0013)
    "jig-semantic-index.sh",  # slice 080-02 — semantic-index activation
    "jig-skill-trace.sh",  # Skill PreToolUse trace hook (registered in hooks.json)
    "jig-spec-gate.sh",
    "jig-task-capture.sh",
    "jig-telemetry.sh",
)


def check_scaffold_skills_present(project_root: Path) -> CheckResult:
    """At least one `.claude/skills/jig-*/SKILL.md` exists under the
    project root.

    This stays the shallow base-presence check; slice 047-02 adds the deeper
    `check_scaffold_skill_closure` (tier-gated expected set + copied-helper
    closure + stale plugin-root-path detection) as a separate check so each
    reports its own focused diagnostic."""
    skills_dir = project_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return False, f".claude/skills/ dir missing at {skills_dir}"
    skill_mds = list(skills_dir.glob("jig-*/SKILL.md"))
    if not skill_mds:
        return False, (
            f"no jig-prefixed skill SKILL.md files found under {skills_dir}"
        )
    return True, f"{len(skill_mds)} scaffolded skill SKILL.md file(s) present"


def check_scaffold_skill_closure(project_root: Path) -> CheckResult:
    """Slice 047-02 (AC #1) — the copied scaffold skills form a coherent,
    closed local install: the tier-gated expected skill set (read from
    `scaffold.json`) is present, every local helper a copied SKILL.md
    references resolves on disk (incl. cross-skill references), and no copied
    SKILL.md still carries a stale `${CLAUDE_PLUGIN_ROOT}/skills/...` helper
    path (spec 046-01 rewrites those to local paths). Delegates to
    `scaffold_contract.scaffold_skill_problems`; each diagnostic names the
    offending skill/helper + the rule (AC #4)."""
    problems = scaffold_contract.scaffold_skill_problems(project_root)
    if problems:
        return False, "; ".join(problems)
    return True, "copied scaffold skills are present and helper-closed"


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


# Slice 057-02 — the active-compaction trigger ships in the copied
# hooks/scripts/lib/context_fill.py (the UserPromptSubmit branch of
# jig-context-check.sh delegates to it). The behavior is keyed on the
# JIG_CONTEXT_COMPACT_PCT knob; its presence in the copied helper is the
# scaffold-side assertion that the trigger flowed through (AC #5).
_COMPACT_TRIGGER_HELPER = "context_fill.py"
_COMPACT_TRIGGER_MARKER = "JIG_CONTEXT_COMPACT_PCT"


def check_scaffold_compaction_trigger(project_root: Path) -> CheckResult:
    """The copied `hooks/scripts/lib/context_fill.py` carries the active-
    compaction trigger (slice 057-02): the `JIG_CONTEXT_COMPACT_PCT` band knob
    the UserPromptSubmit branch of `jig-context-check.sh` delegates to. The
    whole helper is copied verbatim by scaffold-init, so a content marker is
    the right granularity — it confirms the *behavior* shipped, not merely that
    a file with the right name exists."""
    helper = (project_root / ".claude" / "hooks" / "scripts"
              / "lib" / _COMPACT_TRIGGER_HELPER)
    if not helper.is_file():
        return False, (
            f"context-fill helper missing at {helper} "
            "(active-compaction trigger cannot have shipped)"
        )
    text = helper.read_text()
    if _COMPACT_TRIGGER_MARKER not in text:
        return False, (
            f"{_COMPACT_TRIGGER_HELPER} is missing the active-compaction band "
            f"knob ({_COMPACT_TRIGGER_MARKER!r}) — the 057-02 trigger did not "
            "flow to this install"
        )
    return True, (
        "context-fill helper carries the active-compaction trigger "
        f"({_COMPACT_TRIGGER_MARKER})"
    )


def check_scaffold_settings_registration(project_root: Path) -> CheckResult:
    """`.claude/settings.json` is coherent for a scaffolded target (slice
    047-02 AC #2): present + valid JSON, carries at least one jig-managed
    hook entry, and every jig-managed hook command uses the scaffold-mode
    invocation shape (`bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/
    <name>`) pointing at a copied script that exists under
    `.claude/hooks/scripts/`.

    Strengthened from the pre-047-02 'at least one jig-managed entry exists'
    check: it now also pins the command shape + script existence, so a
    scaffold with a registered-but-dangling hook command fails (the
    anti-horizontal-phasing target). Delegates to
    `scaffold_contract.validate_scaffold_settings`; each diagnostic names the
    offending entry/script + the rule (AC #4)."""
    problems = scaffold_contract.validate_scaffold_settings(project_root)
    if problems:
        return False, "; ".join(problems)
    return True, "settings.json registers coherent jig-managed hook entries"


def check_scaffold_manifest(project_root: Path) -> CheckResult:
    """Slice 047-02 (AC #3) — `scaffold.json` carries the metadata
    scaffold-mode consumers rely on: a non-empty `jig_version` (spec 046-02,
    not an unrendered `{{...}}` placeholder), `project_name`, `scaffold_mode`,
    an `installed_tiers` list, and (if present) an `installed_skills` list
    whose tier prefixes are all installed (the ADR-0007 invariant). Delegates
    to `scaffold_contract.validate_scaffold_manifest`; each diagnostic names
    the field + the file (AC #4)."""
    manifest_path = project_root / "scaffold.json"
    if not manifest_path.is_file():
        return False, (
            f"scaffold.json missing at {manifest_path} "
            "(scaffold install-state manifest absent)"
        )
    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return False, f"scaffold.json is not valid JSON: {exc}"
    problems = scaffold_contract.validate_scaffold_manifest(data)
    if problems:
        return False, "; ".join(problems)
    return True, "scaffold.json metadata is present and coherent"


def check_scaffold_docs(project_root: Path) -> CheckResult:
    """Slice 047-02 (AC #4) — smoke-check the scaffolded target's docs +
    copied SKILL.md bodies for broken local helper commands (a referenced
    `${CLAUDE_PROJECT_DIR}/.claude/skills/...` helper that doesn't exist) and
    dangling local Markdown links in the project's own docs (`docs/**`,
    `CLAUDE.md`). Delegates to `scaffold_contract.scaffold_doc_problems`; each
    diagnostic names the offending doc, the missing target, and the rule."""
    problems = scaffold_contract.scaffold_doc_problems(project_root)
    if problems:
        return False, "; ".join(problems)
    return True, "scaffolded docs/commands resolve locally"


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
    # Slice 047-02 (AC #1) — copied-skill helper closure + tier-gated set +
    # stale plugin-root-path detection.
    ("skill-closure", check_scaffold_skill_closure),
    ("agents", check_scaffold_agents_present),
    ("hooks", check_scaffold_hook_scripts_present),
    # Slice 057-02 — the active-compaction trigger flowed to this install.
    ("compaction-trigger", check_scaffold_compaction_trigger),
    # Slice 047-02 (AC #2) — settings.json coherence (strengthened: command
    # shape + script existence, not just 'an entry exists').
    ("settings", check_scaffold_settings_registration),
    # Slice 047-02 (AC #3) — scaffold.json metadata (incl. jig_version).
    ("manifest", check_scaffold_manifest),
    # Slice 047-02 (AC #4) — local command/link smoke checks.
    ("docs", check_scaffold_docs),
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

    Mode-awareness (the correctness nuance): the machinery checks (`skills` /
    `skill-closure` / `agents` / `hooks` / `settings` / `manifest` + the
    security-floor trio) validate `.claude/` artifacts that exist ONLY in
    `--with-machinery` (in-repo) mode. In `--plugin-only` mode that machinery
    lives in the installed plugin, not the target, so running those checks
    would false-fail a perfectly good plugin-only scaffold. They are therefore
    included only when `with_machinery=True`. The seed presence check (AC #3)
    runs in BOTH modes — but only when `seed_expected=True`; a non-greenfield
    scaffold legitimately skipped the seed and must not report it missing.

    Slice 047-02 mode-awareness: the `docs` smoke check (AC #4) is ALSO gated
    on `seed_expected`. The scaffolded `CLAUDE.md` / `docs/adoption-readiness
    .md` templates carry relative links INTO the worked-example seed
    (`docs/specs/001-adopt-jig/...`). Those links resolve iff the seed was
    emitted, so when the seed is skipped (non-greenfield) they legitimately
    dangle and must not be reported — exactly the same reasoning that gates
    the seed check itself. (The standalone `--mode scaffold` verifier —
    `run_headless_scaffold` — runs `docs` unconditionally; it targets a real
    greenfield scaffold where the seed, and thus the links, are present.)

    Returns 0 when every applicable check passed, 1 otherwise — so a
    failed check is loud and actionable (AC #4), never a silent partial
    scaffold."""
    if out is None:
        out = sys.stdout

    mode_label = "in-repo (machinery)" if with_machinery else "plugin-only"

    checks: list[tuple[str, Check]] = []
    if with_machinery:
        # The `docs` check is seed-coupled (its scaffolded docs link into the
        # seed), so it is added below under the `seed_expected` gate — not in
        # the always-run machinery set.
        checks.extend(
            (name, check)
            for name, check in _SCAFFOLD_CHECKS
            if name != "docs"
        )
    if seed_expected:
        if with_machinery:
            # Seed present → the scaffolded docs' links into the seed resolve,
            # so the doc/command smoke check is meaningful here.
            checks.append(("docs", check_scaffold_docs))
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
    for (name, _), (passed, msg) in zip(_SCAFFOLD_CHECKS, results, strict=True):
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
    for (name, _), (passed, msg) in zip(_CHECKS, results, strict=True):
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
