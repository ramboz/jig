"""
install_contract.py — slice 047-01 (plugin-release-contract-validator).

The single validator-facing description of jig's **plugin / release-zip**
install contract: which skills ship, which agents are required, what shape a
valid `hooks.json` entry takes, what fields the two manifests must carry, and
which paths must never leak into a release zip.

Before this module the expected sets were scattered across
`verify_install.py`, `validate_manifests.py`, `build_release_zip.py`, and
their tests, each restating "what a valid install looks like" in its own
shallow way. This module consolidates the *plugin/release* contract as data
plus small pure helpers so the validators (`validate_manifests.py`,
`verify_install.py`) and the release smoke test
(`test_build_release_zip.py`) all check against one source of truth.

Design constraints (mirrors `verify_install.py`):

- **stdlib-only.** No third-party imports, no network, fast enough for CI
  and the local TDD loop.
- **Pure.** The helpers take already-parsed data (or a root `Path`) and
  return `(ok, [diagnostics])` — they never print, never exit. Callers own
  I/O and exit codes.
- **Actionable diagnostics (AC #4).** Every failure names the offending path
  (or manifest field / hook entry) AND the expected rule, so a reader can
  fix it without reading the validator source.

The *scaffold-target* contract (copied-helper closure, settings.json
coherence, scaffold.json metadata, local link checks) is slice 047-02 and
deliberately NOT modeled here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Skills the plugin ships
# ---------------------------------------------------------------------------
#
# Source of truth: scaffold._TIER_SKILLS (skills/scaffold-init/scaffold.py,
# the per-tier skill inventory per ADR-0007). This module is intentionally
# stdlib-only and does NOT import scaffold.py (which pulls in
# `_common.atomic_io` and is not on `scripts/`'s import path), so the union
# across tiers is restated here. `test_install_contract.py` imports
# scaffold._TIER_SKILLS directly and pins this tuple equal to that union, so
# the two cannot drift — the same restate-plus-consistency-test convention
# `verify_install._EXPECTED_HOOK_SCRIPTS` / `_EXPECTED_DENY_GLOBS` already use.
EXPECTED_SKILLS: tuple[str, ...] = (
    # tier-0 (always installed)
    "scaffold-init",
    "memory-sync",
    "spec-workflow",
    "independent-review",
    "migrate",
    "vision-elicitation",
    "contracts",
    # tier-1
    "adr-workflow",
    "tdd-loop",
    "slice-land",
    "pr-review",
    "arch-review",
    "clarify",
    "analyze",
    "security-review",
    "code-health",
    "explain",
    "bug-fix",
    "reframe",
    "compass",
)


# ---------------------------------------------------------------------------
# Agents the plugin requires
# ---------------------------------------------------------------------------
#
# Source of truth: verify_install._REQUIRED_AGENTS (kept in lockstep — the
# two are pinned equal by test_install_contract.py). Three subagent role
# definitions ship at `agents/<name>.md`.
REQUIRED_AGENTS: tuple[str, ...] = ("implementer", "reviewer", "architect")


# ---------------------------------------------------------------------------
# Hook contract
# ---------------------------------------------------------------------------
#
# `hooks/hooks.json` is the registration source of truth. Every hook command
# jig ships MUST be of the exact shape
#     bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>
# (per docs/conventions.md and CLAUDE.md: "Hook commands use
# `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` — never bare names"), and
# `<name>` must exist as a file under `hooks/scripts/`.

_HOOK_COMMAND_PREFIX = "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"


def _iter_hook_commands(hooks_data: dict) -> Iterable[tuple[str, str]]:
    """Yield (event, command) for every hook command in a parsed hooks.json.

    The hooks.json shape is `{"hooks": {<event>: [ {"hooks": [ {"command":
    ...}, ... ]}, ... ]}}`. Tolerant of missing/empty sub-structures so a
    malformed entry produces a diagnostic, not a KeyError.
    """
    hooks = (hooks_data or {}).get("hooks") or {}
    if not isinstance(hooks, dict):
        return
    for event, entries in hooks.items():
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            for h in entry.get("hooks") or []:
                if not isinstance(h, dict):
                    continue
                command = h.get("command")
                if isinstance(command, str):
                    yield event, command


def parse_hook_script_names(hooks_data: dict) -> set[str]:
    """Return the set of `hooks/scripts/<name>` basenames referenced by a
    parsed hooks.json, regardless of whether each command is well-formed.

    Used as the registration-derived source of truth a restated
    `_EXPECTED_HOOK_SCRIPTS` constant is pinned against. A command that does
    not contain the `hooks/scripts/` segment contributes nothing here (its
    *shape* is caught by `validate_hooks`)."""
    names: set[str] = set()
    marker = "hooks/scripts/"
    for _event, command in _iter_hook_commands(hooks_data):
        idx = command.find(marker)
        if idx == -1:
            continue
        tail = command[idx + len(marker):].strip()
        # The basename is the first whitespace-delimited token after the
        # segment (commands are single-token script paths today, but guard
        # against trailing args anyway).
        name = tail.split()[0] if tail else ""
        if name:
            names.add(name)
    return names


def validate_hooks(
    hooks_data: dict,
    scripts_dir: Path,
    *,
    command_prefix: str = _HOOK_COMMAND_PREFIX,
) -> list[str]:
    """Validate every hook command in a parsed hooks.json against the jig
    convention and confirm each referenced script exists under `scripts_dir`.

    Returns a list of diagnostics (empty == valid). Each diagnostic names the
    offending hook entry and the expected rule (AC #2 / AC #4):

    - a command not starting with
      `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/` (bare name, wrong env var,
      wrong path) → shape diagnostic;
    - a well-shaped command whose `<name>` file is missing under
      `scripts_dir` → dangling-reference diagnostic.
    """
    problems: list[str] = []
    hooks = (hooks_data or {}).get("hooks")
    if not isinstance(hooks, dict):
        return ["hooks.json: missing or malformed top-level 'hooks' object"]

    for event, command in _iter_hook_commands(hooks_data):
        if not command.startswith(command_prefix):
            problems.append(
                f"hooks.json {event} entry {command!r}: command must invoke "
                f"'{command_prefix}<name>' "
                "(no bare script names, no other path/env var)"
            )
            continue
        name = command[len(command_prefix):].strip()
        # Reject a command that smuggles a nested path or extra args after
        # the scripts/ segment — the contract is a single bare basename.
        if not name or "/" in name or " " in name:
            problems.append(
                f"hooks.json {event} entry {command!r}: expected a single "
                f"'{command_prefix}<name>' basename"
            )
            continue
        if not (scripts_dir / name).is_file():
            problems.append(
                f"hooks.json {event} entry {name!r}: references a hook script "
                f"that does not exist at {scripts_dir / name} "
                "(dangling hook-script reference)"
            )
    return problems


# ---------------------------------------------------------------------------
# Manifest requirements
# ---------------------------------------------------------------------------
#
# plugin.json — the package manifest a marketplace / CLI reads. Requires the
# fields a package manager and users rely on: a name, a version, and a
# human-readable description (AC #1).
PLUGIN_REQUIRED_FIELDS: tuple[str, ...] = ("name", "version", "description")

# .codex-plugin/plugin.json — the Codex package manifest. This is a sibling
# install contract, not a forked source tree: the manifest must point at the
# shared `skills/` root and carry the interface metadata Codex surfaces in its
# plugin UI.
CODEX_PLUGIN_REQUIRED_FIELDS: tuple[str, ...] = (
    "name",
    "version",
    "description",
    "author",
    "skills",
    "interface",
)
CODEX_INTERFACE_REQUIRED_FIELDS: tuple[str, ...] = (
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "defaultPrompt",
)

# marketplace.json — the marketplace descriptor. Requires a name, an owner
# with a name, and a non-empty plugins[] whose entries each carry
# name/source/description with a relative source path (AC #1).
MARKETPLACE_TOP_FIELDS: tuple[str, ...] = ("name",)
MARKETPLACE_PLUGIN_FIELDS: tuple[str, ...] = ("name", "source", "description")


def validate_plugin_manifest(data: dict) -> list[str]:
    """Validate a parsed plugin.json. Returns diagnostics (empty == valid).

    Requires `name`, `version`, `description` — the metadata the package
    manager and `/plugin` UI surface (AC #1). Each missing field names itself
    and the file (AC #4)."""
    if not isinstance(data, dict):
        return ["plugin.json: top-level value must be a JSON object"]
    problems: list[str] = []
    for field in PLUGIN_REQUIRED_FIELDS:
        value = data.get(field)
        if field not in data or value is None or value == "":
            problems.append(
                f"plugin.json: missing/empty required field {field!r}"
            )
    return problems


def validate_codex_plugin_manifest(data: dict) -> list[str]:
    """Validate a parsed .codex-plugin/plugin.json.

    Requires the Codex plugin metadata used by install/discovery plus a
    host-specific `interface` object. Diagnostics name the Codex manifest
    path because this repo now carries both Claude and Codex `plugin.json`
    files."""
    if not isinstance(data, dict):
        return [".codex-plugin/plugin.json: top-level value must be a JSON object"]

    problems: list[str] = []
    where = ".codex-plugin/plugin.json"
    for field in CODEX_PLUGIN_REQUIRED_FIELDS:
        value = data.get(field)
        if field not in data or value is None or value == "":
            problems.append(
                f"{where}: missing/empty required field {field!r}"
            )

    author = data.get("author")
    if not isinstance(author, dict) or author.get("name") in (None, ""):
        problems.append(
            f"{where}: 'author.name' is required and must be non-empty"
        )

    skills = data.get("skills")
    if skills != "./skills/":
        problems.append(
            f"{where}: 'skills' must be './skills/' so the Codex package "
            "uses the shared rendered skill tree"
        )

    interface = data.get("interface")
    if not isinstance(interface, dict):
        problems.append(
            f"{where}: 'interface' is required and must be a JSON object"
        )
        return problems

    for field in CODEX_INTERFACE_REQUIRED_FIELDS:
        value = interface.get(field)
        if field not in interface or value is None or value == "":
            problems.append(
                f"{where}: interface.{field!r} is required and must be non-empty"
            )

    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        problems.append(
            f"{where}: interface.capabilities must be a non-empty array"
        )
    elif any(not isinstance(value, str) or value == "" for value in capabilities):
        problems.append(
            f"{where}: interface.capabilities entries must be non-empty strings"
        )

    default_prompt = interface.get("defaultPrompt")
    if not isinstance(default_prompt, list) or not default_prompt:
        problems.append(
            f"{where}: interface.defaultPrompt must be a non-empty array"
        )
    elif len(default_prompt) > 3:
        problems.append(
            f"{where}: interface.defaultPrompt must contain at most 3 prompts"
        )
    elif any(not isinstance(value, str) or value == "" for value in default_prompt):
        problems.append(
            f"{where}: interface.defaultPrompt entries must be non-empty strings"
        )

    return problems


def _validate_source_path(where: str, source: object) -> list[str]:
    """Validate a marketplace plugin entry's `source`.

    A source may be a bare string (Claude accepts a relative path string) or
    an object (`git-subdir` etc.). When the source is an object carrying a
    `path`, that path must be **relative** — not absolute and not escaping
    the repo via `..` (AC #1 / AC #4). The string form is accepted as-is
    (its resolution is the CLI's concern), but an absolute string is still
    rejected since it can never resolve inside the package."""
    problems: list[str] = []
    if isinstance(source, str):
        if source and (Path(source).is_absolute() or source.startswith("/")):
            problems.append(
                f"{where}.source {source!r} is an absolute path; expected a "
                "path relative to the marketplace root"
            )
        return problems
    if isinstance(source, dict):
        path = source.get("path")
        if path is None:
            # An object source without a path (e.g. a pure git url) is fine —
            # there is no relative path to police.
            return problems
        if not isinstance(path, str) or path == "":
            problems.append(
                f"{where}.source.path must be a non-empty string"
            )
            return problems
        if Path(path).is_absolute() or path.startswith("/"):
            problems.append(
                f"{where}.source.path {path!r} is not relative "
                "(absolute paths are rejected)"
            )
        elif ".." in Path(path).parts:
            problems.append(
                f"{where}.source.path {path!r} escapes the marketplace root "
                "with '..' (path must stay within the package)"
            )
        return problems
    problems.append(
        f"{where}.source must be a relative path string or an object; "
        f"got {type(source).__name__}"
    )
    return problems


def validate_marketplace_manifest(data: dict) -> list[str]:
    """Validate a parsed marketplace.json. Returns diagnostics (empty == valid).

    Requires (AC #1):
      - a top-level `name`;
      - an `owner` object carrying a `name`;
      - a non-empty `plugins[]` array;
      - each plugins[] entry carries `name`, `source`, `description`;
      - each entry's `source` resolves via a *relative* path (no absolute,
        no `..`-escape).
    Every diagnostic names the offending field/index and the rule (AC #4)."""
    if not isinstance(data, dict):
        return ["marketplace.json: top-level value must be a JSON object"]

    problems: list[str] = []
    for field in MARKETPLACE_TOP_FIELDS:
        if field not in data or data.get(field) in (None, ""):
            problems.append(
                f"marketplace.json: missing/empty required field {field!r}"
            )

    owner = data.get("owner")
    if not isinstance(owner, dict) or owner.get("name") in (None, ""):
        problems.append(
            "marketplace.json: 'owner.name' is required and must be non-empty"
        )

    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        problems.append(
            "marketplace.json: 'plugins' must be a non-empty array"
        )
        return problems

    for i, entry in enumerate(plugins):
        where = f"marketplace.json: plugins[{i}]"
        if not isinstance(entry, dict):
            problems.append(f"{where} must be a JSON object")
            continue
        for field in MARKETPLACE_PLUGIN_FIELDS:
            if field not in entry or entry.get(field) in (None, ""):
                problems.append(
                    f"{where}: missing/empty required field {field!r}"
                )
        if "source" in entry and entry.get("source") not in (None, ""):
            problems.extend(_validate_source_path(where, entry["source"]))
    return problems


# ---------------------------------------------------------------------------
# Excluded-path predicate (release-zip contract)
# ---------------------------------------------------------------------------
#
# Mirrors build_release_zip's exclusion rules (the release contract): a
# release zip must never carry test-only or junk paths. Stated here as a
# single predicate so the smoke test can scan a *built* zip for leaks using
# the same rule the builder applies while constructing it.

_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {"fixtures", "__pycache__", ".pytest_cache", ".mypy_cache"}
)
_EXCLUDED_FILE_NAMES: frozenset[str] = frozenset({".DS_Store"})


def is_excluded_release_path(rel_path: str) -> bool:
    """Return True if `rel_path` (a zip arcname / POSIX-style relative path)
    must NOT appear in a release zip.

    Matches (AC #3): any `fixtures/` component at any depth, `__pycache__`,
    `.pytest_cache`, `.mypy_cache`, a `test_*.py` basename, a `*.pyc`
    basename, and `.DS_Store`. Used by the smoke test's leaked-path scan."""
    parts = Path(rel_path).parts
    if any(part in _EXCLUDED_DIR_NAMES for part in parts):
        return True
    name = parts[-1] if parts else rel_path
    if name in _EXCLUDED_FILE_NAMES:
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith(".pyc"):
        return True
    return False


# ---------------------------------------------------------------------------
# Included-path set (release-zip contract) + builder-facing enumerator
# ---------------------------------------------------------------------------
#
# This module is the single source of truth for the release-zip file set:
# the EXCLUDE side above (`is_excluded_release_path`) and the INCLUDE side
# here. `build_release_zip.py` consumes `iter_release_files` instead of
# restating its own include/exclude constants (spec 069-01), so there is one
# definition the builder and the verify-time smoke test share.

# Files / directories to include in the zip, relative to the source root.
# Directories are walked recursively; individual files are copied as-is.
RELEASE_INCLUDE_ROOTS: tuple[str, ...] = (
    ".claude-plugin",
    ".codex-plugin",
    "agents",
    "skills",
    "hooks",
    "templates",
)

# Top-level files copied into the release/package when present (optional:
# missing → warn, build anyway). `jig.jpg` is the README logo asset — the
# packaged README references it (`![jig](./jig.jpg)`), so it must ship
# alongside README.md or the logo renders broken on install.
RELEASE_INCLUDE_FILES: tuple[str, ...] = (
    "README.md",
    "LICENSE",
    "jig.jpg",
)

# Individual files under `scripts/` that must ship in the release zip.
# `scripts/` is otherwise excluded by virtue of not being in
# `RELEASE_INCLUDE_ROOTS` (it holds dev/CI tooling — build_release_zip,
# run_tests, usage, validate_manifests — which has no place in a user's
# plugin install). Two reasons land specific scripts here:
#
#   1. The runtime trio — `verify_install` + `install_contract` +
#      `scaffold_contract`. scaffold-init's closing completion self-check
#      (slice 048-06) imports `verify_install` from `<plugin-root>/scripts/`
#      at runtime, and that module pulls in the other two. Without all three
#      the self-check crashes on every plugin install (the release zip never
#      carried `scripts/`). They check the *target's* `.claude/` tree
#      (nothing is copied into the user's repo — they run from the plugin
#      install dir).
#   2. The spec-lint validator — `spec_lint` (slice 075-01). Several shipped
#      skills (migrate, analyze) instruct the agent to run it as part of the
#      spec-driven workflow, so it must resolve at
#      `${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py` in a consuming project.
#      Unlike the runtime trio it is pure-stdlib (argparse/re/sys/pathlib
#      only — it does NOT import `_common`), so it ships with zero
#      dependency drag.
#
# All ship under their original `scripts/` path so the importing path in
# scaffold.py needs no change. This is an allowlist on purpose: the dev-only
# scripts stay out, and the contract is pinned by
# test_build_release_zip.py::test_runtime_scripts_only.
RELEASE_INCLUDE_SCRIPT_FILES: tuple[str, ...] = (
    "scripts/verify_install.py",
    "scripts/install_contract.py",
    "scripts/scaffold_contract.py",
    "scripts/spec_lint.py",
)

# (The directory-name exclusions live in `_EXCLUDED_DIR_NAMES` above. They are
# limited to truly defensive exclusions — caches, VCS artifacts — plus the
# reserved `fixtures/` name: top-level dev-only dirs (`scripts/`, `docs/`,
# `.github/`, `.git/`, `.jig/`, `.claude/`) are already excluded by virtue of
# not being listed in `RELEASE_INCLUDE_ROOTS`, so we don't name them in the
# dir-name set — the allowlisted modules under `scripts/` that the plugin
# needs at runtime are re-included file-by-file via
# `RELEASE_INCLUDE_SCRIPT_FILES`; the rest of `scripts/` stays out. Naming the
# top-level dirs in the dir-name set
# would also exclude nested same-named dirs that ARE runtime — e.g.
# `hooks/scripts/` (the actual hook scripts) and `templates/docs/`
# (scaffold-init's project template). `fixtures/` is reserved as test-data
# (spec 035): any-depth match per Q1, no escape hatch per Q4 — future skills
# needing runtime sample data must use a different name (`samples/`,
# `examples/`, `data/`, etc.).)


def iter_release_files(source_root: Path) -> Iterable[Path]:
    """Yield every file path (relative to source_root) destined for the zip.

    Walks each entry in `RELEASE_INCLUDE_ROOTS` recursively, skipping any path
    excluded by `is_excluded_release_path` (the single exclusion rule). Then
    yields the present top-level `RELEASE_INCLUDE_FILES` and the runtime
    `scripts/*.py` modules in `RELEASE_INCLUDE_SCRIPT_FILES`.

    Pure / stdlib-only / side-effect-free: it only reads the source tree and
    yields relative POSIX-style `Path`s (matches the rest of this module).
    """
    for root_name in RELEASE_INCLUDE_ROOTS:
        root_dir = source_root / root_name
        if not root_dir.is_dir():
            continue
        for path in root_dir.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(source_root)
            if is_excluded_release_path(rel.as_posix()):
                continue
            yield rel

    for file_name in RELEASE_INCLUDE_FILES:
        file_path = source_root / file_name
        if file_path.is_file():
            yield Path(file_name)

    # Runtime modules under scripts/ that scaffold-init imports at install
    # time (see RELEASE_INCLUDE_SCRIPT_FILES). Yielded individually so the
    # rest of dev-only scripts/ stays out of the release.
    for rel_name in RELEASE_INCLUDE_SCRIPT_FILES:
        file_path = source_root / rel_name
        if file_path.is_file():
            yield Path(rel_name)


# ---------------------------------------------------------------------------
# Skill / agent presence helpers (operate on a plugin root)
# ---------------------------------------------------------------------------


def missing_skills(plugin_root: Path) -> list[str]:
    """Return diagnostics for any EXPECTED skill missing its SKILL.md under
    `plugin_root/skills/`. Empty == every expected skill present (AC #3)."""
    skills_dir = plugin_root / "skills"
    problems: list[str] = []
    for skill in EXPECTED_SKILLS:
        skill_md = skills_dir / skill / "SKILL.md"
        if not skill_md.is_file():
            problems.append(
                f"skills/{skill}: missing SKILL.md "
                "(expected per install contract)"
            )
    return problems


def missing_agents(plugin_root: Path) -> list[str]:
    """Return diagnostics for any REQUIRED agent missing under
    `plugin_root/agents/`. Empty == all present (AC #4-style messages)."""
    agents_dir = plugin_root / "agents"
    problems: list[str] = []
    for agent in REQUIRED_AGENTS:
        if not (agents_dir / f"{agent}.md").is_file():
            problems.append(
                f"agents/{agent}.md: missing agent definition "
                "(expected per install contract)"
            )
    return problems


# ---------------------------------------------------------------------------
# Claude install-tree contract (committed hosts/claude package — spec 061-01)
# ---------------------------------------------------------------------------
#
# Per ADR-0018 the repository root is canonical source; the *installable*
# Claude payload is the committed, runtime-only `hosts/claude/` package. That
# package carries `.claude-plugin/plugin.json`, the runtime skill/agent/hook
# subset, and (optionally) README/LICENSE. It deliberately does NOT carry the
# remote-install pointer (`.claude-plugin/marketplace.json` stays at the repo
# root, resolving the plugin to `./hosts/claude`) and never carries any Codex
# (`.codex-plugin/`) content. This helper validates a directory *as* a Claude
# install tree so a single source of truth governs what the package must (and
# must not) contain — the validators no longer assume the Claude artifact is
# the source root or that both host manifests co-exist in one tree.


def validate_claude_package(plugin_root: Path) -> list[str]:
    """Validate `plugin_root` as a committed Claude install tree (spec 061-01).

    Requires (AC #5):
      - `.claude-plugin/plugin.json` present and satisfying the plugin
        manifest contract;
      - every EXPECTED skill and REQUIRED agent present;
      - NO `.claude-plugin/marketplace.json` (the remote-install pointer lives
        at the repo root, not inside the package);
      - NO `.codex-plugin/` content (the Claude package is runtime-only and
        host-specific).

    Returns diagnostics (empty == valid); each names the offending path and
    the rule (AC #4-style)."""
    problems: list[str] = []

    plugin_json = plugin_root / ".claude-plugin" / "plugin.json"
    if not plugin_json.is_file():
        problems.append(
            f".claude-plugin/plugin.json: missing at {plugin_json} "
            "(a Claude package must carry its source manifest)"
        )
    else:
        try:
            data = json.loads(plugin_json.read_text())
        except (ValueError, OSError) as exc:
            problems.append(
                f".claude-plugin/plugin.json: unreadable/invalid JSON ({exc})"
            )
        else:
            problems.extend(validate_plugin_manifest(data))

    if (plugin_root / ".claude-plugin" / "marketplace.json").exists():
        problems.append(
            ".claude-plugin/marketplace.json: must NOT live inside the Claude "
            "package (the remote-install pointer stays at the repo root, "
            "resolving the plugin to ./hosts/claude)"
        )

    if (plugin_root / ".codex-plugin").exists():
        problems.append(
            ".codex-plugin/: must NOT appear in the Claude package "
            "(the package is host-specific and runtime-only)"
        )

    problems.extend(missing_skills(plugin_root))
    problems.extend(missing_agents(plugin_root))
    return problems
