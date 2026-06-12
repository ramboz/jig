"""
jig scaffold-init — slice 001-01 greenfield-scaffold

Generates an AI-native dev workspace from `templates/` into a target directory.
Reads CLAUDE_PLUGIN_ROOT to locate the plugin's template dir.

Usage:
    python3 scaffold.py <target-dir>

The script is deterministic: no network, no user prompts. Q&A interaction
is a later slice (001-05); signal detection is 001-03.
"""

import argparse
import json
import os
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.atomic_io import atomic_write_text

# Team-signal detection + the .jig/no-people-md marker contract live in
# _common per ADR-0002's rule-of-three (slice 050-02): scaffold-init,
# memory-sync, and workflow.py stale are the three callers. Re-exported
# here so scaffold's existing public names (`count_team_contributors`,
# `detect_team`, the marker helpers) keep resolving for callers and tests.
from _common.team_signal import (  # noqa: F401  (re-export)
    NO_PEOPLE_MD_RELPATH,
    count_team_contributors,
    no_people_md_marker_path,
    people_md_path,
    team_signal_fires,
    write_no_people_md_marker,
)

# Tier 0 always installs. Tier 1 is gated on test signals (per Spike 001a:
# "default for most projects" = "most projects have tests, so most install tier-1").
# Tier 2 is offered, never auto-installed.
LLM_LIBRARIES = {
    "openai", "anthropic", "langchain", "llamaindex",
    "@anthropic-ai/sdk", "@anthropic-ai/claude-code",
}
TEST_LIBRARIES_NPM = {"vitest", "jest", "mocha", "ava"}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "target",
    "__pycache__", ".venv", "venv", ".tox", ".pytest_cache",
}

# Per-tier skill inventory (ADR-0007). The per-skill `installed_skills`
# field in scaffold.json is derived from this table plus the tier-
# selection logic. Adding a new skill to a tier means a one-line edit
# here; the manifest, brief.md, and verify_install all pick it up.
# Order within each tier is stable to keep `scaffold.json` diffs minimal.
_TIER_SKILLS = {
    "tier-0": [
        "scaffold-init",
        "memory-sync",
        "spec-workflow",
        "independent-review",
        "migrate",
        "vision-elicitation",
        "contracts",  # deliberate stub per ADR-0002 — still copied
    ],
    "tier-1": [
        "adr-workflow",
        "tdd-loop",
        "slice-land",
        "pr-review",
        "arch-review",
        "clarify",
        "analyze",
        "security-review",
        "code-health",  # spec 060 / ADR-0017 — Tier-1 detect-and-drive linter
        "explain",  # spec 065-03 — on-demand vocabulary/artifact explainer
    ],
    "tier-2": [],  # no Tier 2 skills land in jig yet
}

# Reverse lookup skill-name → tier, derived once from the single
# source-of-truth table above. `_enumerate_skills` walks `_TIER_SKILLS`
# forward (tier → skills); the tier-gated copy needs the inverse
# (skill → tier). Built at module load so the two traversals can't drift
# (slice 038-04 reconciliation — replaces an inline rebuild in
# `_copy_skills_and_agents`).
_SKILL_TO_TIER = {
    skill: tier
    for tier, skills in _TIER_SKILLS.items()
    for skill in skills
}


def plugin_root(host: str = "claude") -> Path:
    """Locate the jig runtime root, falling back to this script's parents."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if host == "claude" and env_root:
        return Path(env_root).resolve()
    # Fallback: scaffold.py lives at <plugin-root>/skills/scaffold-init/scaffold.py
    return Path(__file__).resolve().parents[2]


class PluginManifestError(RuntimeError):
    """Raised when `.claude-plugin/plugin.json` cannot yield a release version
    (absent, malformed JSON, or missing/empty `version`). Slice 046-02 reads
    the scaffold's recorded `jig_version` from this manifest — the single
    source of truth — so a bad manifest must fail loudly rather than let
    scaffold output record an invented version."""


def _read_plugin_version(plugin: Path) -> str:
    """Return the release version from `plugin/.claude-plugin/plugin.json`.

    This is the canonical source for `scaffold.json.jig_version` (spec 046,
    AC #1) — no production code hard-codes the release version. Raises
    `PluginManifestError`, naming the manifest path and the problem, when the
    manifest is absent, is malformed JSON, or lacks a non-empty `version`.
    Callers read this before the first scaffold file write so a bad manifest
    fails fast and leaves no partial scaffold (AC #3)."""
    manifest_path = plugin / ".claude-plugin" / "plugin.json"
    try:
        raw = manifest_path.read_text()
    except FileNotFoundError as exc:
        raise PluginManifestError(
            f"plugin manifest not found: {manifest_path} — cannot derive the "
            "jig version for scaffold metadata."
        ) from exc
    try:
        manifest = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PluginManifestError(
            f"plugin manifest {manifest_path} is not valid JSON: {exc}"
        ) from exc
    version = manifest.get("version")
    if not version:
        raise PluginManifestError(
            f"plugin manifest {manifest_path} has no non-empty 'version' "
            "field — cannot derive the jig version for scaffold metadata."
        )
    return version


class UnrenderedPlaceholderError(RuntimeError):
    """Raised when a template contains placeholders no substitution covered."""


def render(template_text: str, substitutions: dict) -> str:
    """Replace `{{KEY}}` placeholders. Raises if any remain — silent leftovers
    indicate a template/scaffold-code mismatch and should fail loudly."""
    out = template_text
    for key, value in substitutions.items():
        out = out.replace(f"{{{{{key}}}}}", value)
    leftover = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", out)))
    if leftover:
        raise UnrenderedPlaceholderError(
            f"unrendered placeholders: {leftover}"
        )
    return out


def copy_template(src: Path, dst: Path, substitutions: dict,
                  post_render=None) -> None:
    """Read a `.template` file, render `{{KEY}}` placeholders, write to dst.

    `post_render` (slice 046-01) is an optional `str -> str` transform
    applied to the rendered body before writing. The greenfield in-repo
    scaffold passes `_rewrite_skill_md_paths` here so documented
    `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` helper paths become the copied
    `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/` paths — the same
    rewrite SKILL.md bodies already get, now applied to rendered docs so
    the commands they document actually run inside the scaffolded target.
    `--plugin-only` passes `None` (no rewrite — the plugin-root path is
    correct when machinery is NOT copied locally)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rendered = render(src.read_text(), substitutions)
    if post_render is not None:
        rendered = post_render(rendered)
    atomic_write_text(dst, rendered)


class AlreadyScaffoldedError(RuntimeError):
    """Raised when target already has a scaffold.json — refuses to overwrite."""


class UnmanagedHooksError(RuntimeError):
    """Raised by slice 016-02 when `.claude/settings.json` already exists with
    hooks present, but no jig-managed marker on any of them. Same safety
    stance as AlreadyScaffoldedError — refuses to merge silently. `--force`
    is the documented escape hatch."""


class CodexAgentInstallConflictError(RuntimeError):
    """Raised when Codex agent install would overwrite user-owned content."""


class CodexAgentRoleError(RuntimeError):
    """Raised when a Codex agent role lacks an explicit sandbox mapping."""


class LooksAlreadySpecDrivenError(RuntimeError):
    """Raised when target has no scaffold.json but ≥3 of the four migrate
    triggers (specs-or-slices, decisions-or-adrs, workflow.md,
    architecture.md). Slice 008-05 introduced this to route users to
    `/jig:migrate` instead of polluting their tree.

    The `triggers` attribute is the list of trigger paths actually found
    (Path objects relative to target), so CLI surfaces can render them
    verbatim in the user-facing message."""

    def __init__(self, message: str, triggers: list):
        super().__init__(message)
        self.triggers = triggers


# Watermark embedded in scaffolded primer templates — its presence means
# "this primer was generated by jig", which is how we distinguish a
# jig-partial state (crashed mid-scaffold, no scaffold.json) from a user's
# pre-existing spec-driven project. Slice 032-02: used by
# `_is_jig_partial_state` to short-circuit `_looks_already_spec_driven` during
# recovery from an interrupted scaffold.
_JIG_CLAUDE_MD_WATERMARK = "Generated by [jig]"


def _is_jig_partial_state(target: Path) -> bool:
    """Return True iff `target` looks like a previously-interrupted jig
    scaffold (a host primer exists with the jig watermark, but scaffold.json
    is absent). Slice 032-02: distinguishes a crashed mid-scaffold from a
    user's pre-existing spec-driven project, so the recovery re-run can
    proceed without `--force`.

    Reads known primer files best-effort — any I/O failure for one primer is
    ignored. If no jig watermark is confirmed, the safer side is to fall
    through to `_looks_already_spec_driven` and route to /jig:migrate."""
    for primer_name in ("CLAUDE.md", "AGENTS.md"):
        primer = target / primer_name
        if not primer.is_file():
            continue
        try:
            if _JIG_CLAUDE_MD_WATERMARK in primer.read_text():
                return True
        except OSError:
            continue
    return False


def _looks_already_spec_driven(target: Path) -> tuple:
    """Check whether `target` already has a spec-driven layout that
    `migrate.py` would recognize as adoptable.

    Returns `(triggered, triggers)` where `triggers` is a list of
    relative-path strings of detected artifacts. `triggered` is True iff
    ≥3 of the four trigger categories are present.

    Approximates `migrate.py`'s `compute_verdict` heuristic — broader,
    because this check fires before scaffold pollutes the tree, so a
    false positive (route to /jig:migrate when the user meant greenfield)
    is recoverable via --force, while a false negative (silently scaffold
    over real specs) is destructive. Specifically: this check treats
    `docs/specs/` and `docs/slices/` as triggers even when empty; the
    migrate verdict only counts them when they contain content. The
    safer side to err on is False-positive-routes-to-migrate."""
    triggers = []
    # 1. spec-or-slice dir
    if (target / "docs" / "specs").is_dir():
        triggers.append("docs/specs/")
    elif (target / "docs" / "slices").is_dir():
        triggers.append("docs/slices/")
    # 2. decisions-or-adrs dir
    if (target / "docs" / "decisions").is_dir():
        triggers.append("docs/decisions/")
    elif (target / "docs" / "adrs").is_dir():
        triggers.append("docs/adrs/")
    # 3. workflow doc
    if (target / "docs" / "workflow.md").is_file():
        triggers.append("docs/workflow.md")
    # 4. architecture doc
    if (target / "docs" / "architecture.md").is_file():
        triggers.append("docs/architecture.md")
    return (len(triggers) >= 3, triggers)


@dataclass
class Signals:
    """Detected project signals. Per Spike 001a (docs/spikes/spike-001a-signal-detection.md)."""
    has_llm_agent_files: bool
    has_ci: bool
    has_tests: bool
    is_team: bool


@dataclass
class Overrides:
    """Q&A wizard answers (slice 001-05). None = unset (defer to filesystem inference).
    True/False = explicit user answer that overrides the corresponding detector."""
    is_team: bool = None  # type: ignore[assignment]
    has_ci: bool = None  # type: ignore[assignment]
    has_tests: bool = None  # type: ignore[assignment]
    has_llm_agent_files: bool = None  # type: ignore[assignment]
    runtime: str = None  # type: ignore[assignment]

    def apply_to(self, signals: Signals) -> Signals:
        """Return a new Signals with overrides applied. None fields pass through."""
        return Signals(
            has_llm_agent_files=(self.has_llm_agent_files
                                 if self.has_llm_agent_files is not None
                                 else signals.has_llm_agent_files),
            has_ci=(self.has_ci if self.has_ci is not None else signals.has_ci),
            has_tests=(self.has_tests if self.has_tests is not None else signals.has_tests),
            is_team=(self.is_team if self.is_team is not None else signals.is_team),
        )


def _read_json_safe(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _read_text_safe(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return ""


def _detect_llm_agent(target: Path) -> bool:
    """High-confidence signals only — see Spike 001a."""
    # File / directory presence at root
    if (target / "AGENTS.md").is_file():
        return True
    if (target / ".cursor").is_dir():
        return True
    if (target / ".github" / "copilot-instructions.md").is_file():
        return True
    # *.prompt.md or *.system-prompt.md at root (shallow — no recursion)
    for entry in target.iterdir():
        if entry.is_file() and (entry.name.endswith(".prompt.md")
                                or entry.name.endswith(".system-prompt.md")):
            return True

    # package.json deps
    pkg = _read_json_safe(target / "package.json")
    if pkg:
        deps = set()
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            deps.update((pkg.get(key) or {}).keys())
        if deps & LLM_LIBRARIES:
            return True

    # requirements.txt
    reqs = _read_text_safe(target / "requirements.txt").lower()
    if reqs:
        for lib in LLM_LIBRARIES:
            # match at line-start, optionally with version pin
            if re.search(rf"(?im)^{re.escape(lib)}\b", reqs):
                return True

    # pyproject.toml — lightweight regex match (we don't pull in a TOML parser).
    # Require the lib to appear in dependency-style position to avoid
    # description-string false positives ("openai integration helper" etc.).
    pyproject = _read_text_safe(target / "pyproject.toml")
    if pyproject:
        for lib in LLM_LIBRARIES:
            esc = re.escape(lib)
            # Quoted list entry: "lib>=1.0", "lib", "lib", "x"
            # Either followed by a version-pin op, OR closing quote then `,` or `]` (list context)
            quoted = rf'["\']{esc}(?:[><=~^!]|["\']\s*[,\]])'
            # Poetry table key: ^  lib = "..."
            table_key = rf'(?im)^\s*{esc}\s*=\s*["\']'
            if re.search(quoted, pyproject) or re.search(table_key, pyproject):
                return True

    return False


def _detect_ci(target: Path) -> bool:
    """High-confidence CI files only — see Spike 001a. Makefiles excluded."""
    workflows = target / ".github" / "workflows"
    if workflows.is_dir() and any(workflows.iterdir()):
        return True
    if (target / "Jenkinsfile").is_file():
        return True
    if (target / ".circleci").is_dir():
        return True
    if (target / ".travis.yml").is_file():
        return True
    if (target / ".gitlab-ci.yml").is_file():
        return True
    return False


def _detect_tests(target: Path) -> bool:
    """High-confidence test-framework signals — see Spike 001a."""
    # Python
    if (target / "pytest.ini").is_file():
        return True
    if (target / "conftest.py").is_file():
        return True
    pyproject = _read_text_safe(target / "pyproject.toml")
    if "[tool.pytest" in pyproject:
        return True

    # JS/TS — vitest / jest config files
    for cfg in ("vitest.config.ts", "vitest.config.js", "vitest.config.mjs",
                "jest.config.ts", "jest.config.js", "jest.config.json"):
        if (target / cfg).is_file():
            return True
    # package.json dev/regular deps
    pkg = _read_json_safe(target / "package.json")
    if pkg:
        deps = set()
        for key in ("dependencies", "devDependencies"):
            deps.update((pkg.get(key) or {}).keys())
        if deps & TEST_LIBRARIES_NPM:
            return True

    # Go — shallow scan for *_test.go at root only (per spike: ≤2 levels deep)
    for entry in target.iterdir():
        if entry.is_file() and entry.name.endswith("_test.go"):
            return True

    return False


def detect_signals(target: Path) -> Signals:
    """Compose all detectors. Each is independent and exception-safe internally."""
    if not target.exists():
        return Signals(False, False, False, False)
    return Signals(
        has_llm_agent_files=_detect_llm_agent(target),
        has_ci=_detect_ci(target),
        has_tests=_detect_tests(target),
        is_team=detect_team(target),
    )


def detect_team(target: Path) -> bool:
    """True iff `target`'s git history shows >= the team threshold of distinct
    mailmap-normalized author emails. Solo is the safe default. Thin wrapper
    over `_common.team_signal.team_signal_fires` — the count logic, the
    threshold, and the fail-soft + monorepo-guard behavior all live in the
    shared module (ADR-0002 rule-of-three, slice 050-02); this name is kept
    because `detect_signals` and `_render_brief` reference it."""
    return team_signal_fires(target)


def _select_tiers(signals: Signals) -> tuple[list, list]:
    """Map signals to (installed_tiers, offered_tiers). Per Spike 001a:
    permissive offer, conservative install."""
    installed = ["tier-0"]
    if signals.has_tests:
        installed.append("tier-1")
    offered = []
    if signals.has_llm_agent_files:
        offered.append("tier-2")
    return installed, offered


def _enumerate_skills(installed_tiers: list) -> list:
    """ADR-0007 — given the installed tiers, return the flat list of
    `<tier>/<skill>` strings that scaffold-init will install. Invariant:
    `set(s.split("/")[0] for s in result) == set(installed_tiers)`.
    """
    out = []
    for tier in installed_tiers:
        for skill in _TIER_SKILLS.get(tier, []):
            out.append(f"{tier}/{skill}")
    return out


# ---------- Slice 038-04: post-scaffold tier upgrade (ADR-0012) ----------
# These let `migrate.py copy-machinery` resolve and raise the installed
# tier of an already-scaffolded project from its `scaffold.json`, so a
# Tier-0 floor install can additively gain Tier 1 without re-scaffolding.

def read_installed_tiers(target: Path) -> "list | None":
    """Return `installed_tiers` from `target/scaffold.json`, or None when no
    manifest exists / is unreadable / lacks the field. None signals "tiers
    unknown" — callers treat it as copy-all (the spec-021 migrate default
    for a project that was never scaffold-init'd)."""
    manifest = target / "scaffold.json"
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    tiers = data.get("installed_tiers")
    return tiers if isinstance(tiers, list) else None


def plan_installed_tiers(target: Path, add_tiers: list) -> tuple:
    """Validate `add_tiers` against the target's `scaffold.json` and compute
    the post-upgrade tier set — **without writing anything**. Returns
    `(old_tiers, new_tiers, newly_added)`, where `new_tiers` is the union in
    canonical `_TIER_SKILLS` order and `newly_added` is the delta (empty when
    every requested tier is already installed).

    Compute-only so the caller can copy the delta skills BEFORE committing
    the manifest (`write_installed_tiers`) — a copy failure then leaves the
    manifest untouched rather than claiming tiers whose skills never landed.

    Raises `FileNotFoundError` if there is no `scaffold.json` (the project
    was never scaffolded — no tier baseline to raise), and `ValueError` if
    any requested tier is not a known `_TIER_SKILLS` key."""
    manifest_path = target / "scaffold.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"no scaffold.json at {target} — run scaffold-init first to "
            f"establish a tier baseline before upgrading"
        )
    unknown = [t for t in add_tiers if t not in _TIER_SKILLS]
    if unknown:
        raise ValueError(
            f"unknown tier(s): {', '.join(unknown)} "
            f"(valid: {', '.join(_TIER_SKILLS)})"
        )
    data = json.loads(manifest_path.read_text())
    old = list(data.get("installed_tiers", []))
    union = set(old) | set(add_tiers)
    # Re-order by the canonical tier sequence so diffs stay minimal.
    new = [t for t in _TIER_SKILLS if t in union]
    added = [t for t in new if t not in old]
    return old, new, added


def write_installed_tiers(target: Path, new_tiers: list) -> None:
    """Commit `new_tiers` to `target/scaffold.json`: rewrite `installed_tiers`
    and re-derive `installed_skills` (ADR-0007), preserving all other manifest
    fields. Atomic. Call AFTER the corresponding skills have been copied, so a
    copy failure never leaves the manifest ahead of disk."""
    manifest_path = target / "scaffold.json"
    data = json.loads(manifest_path.read_text())
    data["installed_tiers"] = list(new_tiers)
    data["installed_skills"] = _enumerate_skills(new_tiers)
    atomic_write_text(manifest_path, json.dumps(data, indent=2) + "\n")


def _hook_profile(signals: Signals) -> str:
    """CI present → strict; otherwise standard. Inert until dispatch ships."""
    return "strict" if signals.has_ci else "standard"


def _render_brief(template_text: str, signals: Signals, installed: list,
                  offered: list, subs: dict) -> str:
    """Build the dynamic blocks for brief.md."""
    detected_lines = []
    if signals.has_llm_agent_files:
        detected_lines.append(
            "- **LLM/agent files** — Tier 2 (`eval-harness`, `e2e-testing`, etc.) is offered."
        )
    if signals.has_ci:
        detected_lines.append(
            "- **CI configuration** — hook profile set to `strict` (dispatch deferred)."
        )
    if signals.has_tests:
        detected_lines.append(
            "- **Test framework** — Tier 1 (`tdd-loop` and friends) auto-installed."
        )
    if signals.is_team:
        detected_lines.append(
            "- **Multiple git contributors** — `docs/memory/people.md` was created."
        )
    if not detected_lines:
        detected_lines.append("- _(none — solo greenfield project)_")

    installed_lines = [f"- **{t}**" for t in installed]
    offered_lines = [f"- **{t}**" for t in offered] if offered else ["- _(none)_"]

    next_hint = (
        "Review the Tier 2 offer in `scaffold.json` and install if relevant."
        if offered else "Add a Tier 2 skill when you start LLM/agent work."
    )

    return render(template_text, {
        **subs,
        "DETECTED_BLOCK": "\n".join(detected_lines),
        "INSTALLED_BLOCK": "\n".join(installed_lines),
        "OFFERED_BLOCK": "\n".join(offered_lines),
        "HOOK_PROFILE": _hook_profile(signals),
        "NEXT_STEP_HINT": next_hint,
    })


def _copy_skills_and_agents(
    plugin: Path, target: Path, installed_tiers: "list | None" = None,
) -> None:
    """Copy `plugin/skills/<name>/` → `target/.claude/skills/jig-<name>/` and
    `plugin/agents/*.md` → `target/.claude/agents/jig-<name>.md`. Also copies
    `_`-prefixed private shared modules (e.g. `_common/`) into
    `target/.claude/skills/<name>/` (no `jig-` prefix) so helpers'
    `from _common.parsing import ...` resolves at scaffold-mode runtime —
    helpers do `sys.path.insert(0, parent.parent)` which lands on
    `.claude/skills/`, making `_common/` a sibling.

    Slice 016-01 (scaffold-mode); shared-module copy added 2026-05-20.

    Slice 038-02 (tier gating, ADR-0012): `installed_tiers` filters which
    user-facing skills are copied so the on-disk set matches the
    `scaffold.json` manifest (whose `installed_skills` is derived from the
    same tiers per ADR-0007). A skill is copied only when its tier (per
    `_TIER_SKILLS`) is in `installed_tiers`. When `installed_tiers is None`
    every tier is copied — the standing "tiers unknown → copy-all" contract
    for callers that cannot resolve a tier set (e.g. `migrate.py
    copy-machinery` against a project with no `scaffold.json`; slice 038-04
    sources tiers from the manifest when one exists). A skill dir with no
    `_TIER_SKILLS` entry has no tier to gate on; under gating it is skipped
    with a diagnostic (silently shipping it would reopen the manifest↔disk
    gap), but it is still copied under the copy-all default.

    Infrastructure is never gated: `_`-prefixed private shared modules and
    `agents/*.md` are always copied (they are runtime plumbing, not
    tier-scoped skills).

    Skips (regardless of tier):
      - skill dirs that don't have a `SKILL.md` (not user-facing);
      - `test_*.py` files anywhere under a skill dir (helper-only files
        bloat the user's tree and aren't load-bearing at runtime);
      - `__pycache__` directories.

    For each copied SKILL.md, rewrites every
    `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` literal in the body to
    `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`. The frontmatter is
    left untouched (AC #5). Helper .py files (non-test) are copied
    verbatim — their `plugin_root()` fallback handles self-location at
    runtime (AC #6).

    Agent .md files are copied byte-identically with a `jig-` filename
    prefix (audit confirmed agents have zero plugin-root references)."""
    skills_src = plugin / "skills"
    agents_src = plugin / "agents"
    skills_dst = target / ".claude" / "skills"
    agents_dst = target / ".claude" / "agents"

    # Gate set; None means "copy all tiers". Skill→tier map is the shared
    # module-level `_SKILL_TO_TIER` (single source of truth, no inline rebuild).
    gate = set(installed_tiers) if installed_tiers is not None else None

    if skills_src.is_dir():
        skills_dst.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("_"):
                # Private shared module — copy unprefixed so the
                # helpers' `from _<name>.x import ...` resolves.
                # Never tier-gated (infrastructure, not a skill).
                _copy_skill_dir(skill_dir, skills_dst / skill_dir.name)
                continue
            if not (skill_dir / "SKILL.md").is_file():
                continue
            if gate is not None:
                tier = _SKILL_TO_TIER.get(skill_dir.name)
                if tier is None:
                    # No tier to gate on — skip rather than silently ship.
                    print(
                        f"jig scaffold: skipping skill '{skill_dir.name}' "
                        f"— not in _TIER_SKILLS, cannot tier-gate",
                        file=sys.stderr,
                    )
                    continue
                if tier not in gate:
                    continue
            dst_dir = skills_dst / f"jig-{skill_dir.name}"
            _copy_skill_dir(skill_dir, dst_dir)

    if agents_src.is_dir():
        agents_dst.mkdir(parents=True, exist_ok=True)
        for agent in sorted(agents_src.glob("*.md")):
            dst = agents_dst / f"jig-{agent.name}"
            dst.write_bytes(agent.read_bytes())


# Pattern: ${CLAUDE_PLUGIN_ROOT}/skills/<name>/ — captures <name>.
# Bash `${...}` syntax in SKILL.md bash recipes is the only place this
# token appears (verified by the spec 016 audit; 24 occurrences across 7
# SKILL.md files at the time of writing). The substitution rewrites every
# such occurrence to the project-scoped equivalent.
_PLUGIN_SKILL_PATH_RE = re.compile(
    r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([A-Za-z0-9_-]+)/"
)


_SKILL_DIR_EXCLUDES: frozenset[str] = frozenset({"__pycache__", "fixtures"})

# Per-skill allow-list of `test_*.py` files to RETAIN despite the general
# "test files are not shipped to scaffolded projects" rule. Keyed by the
# source skill directory name (the directory under `skills/`, NOT the
# `jig-`-prefixed scaffolded destination name).
#
# Why retain anything? Spec 043-04 wires `quality.py`'s YAML snapshot
# into the implementation-review prompt; `test_quality.py` is the test
# surface for that helper. Scaffolded adopters need it reachable so a
# fresh-scaffold project can exercise the snapshot wiring end-to-end
# without having to re-clone the source repo. The allow-list is
# deliberately narrow — only `test_quality.py` is retained; the rest of
# the test suite (e.g. `test_tdd.py`) stays excluded.
_RETAINED_TEST_FILES: dict[str, frozenset[str]] = {
    "tdd-loop": frozenset({"test_quality.py"}),
}


def _rewrite_skill_md_paths(body: str) -> str:
    """Replace every `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` with
    `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`.

    Operates on the SKILL.md body only — the frontmatter must be carved off
    by the caller before calling here (AC #5).

    String substitution, not AST: SKILL.md is markdown + bash, no parsing
    needed. The Known-constraint #1 fallback (substitute absolute paths if
    `${CLAUDE_PROJECT_DIR}` is unreachable from skill bash) is a one-line
    change inside this function — left for a future slice to flip if the
    env-var path turns out to be unreachable in practice."""
    return _PLUGIN_SKILL_PATH_RE.sub(
        r"${CLAUDE_PROJECT_DIR}/.claude/skills/jig-\1/",
        body,
    )


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split a SKILL.md into (frontmatter_with_fences, body). If the file
    has no YAML frontmatter, returns ('', text)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return ("", text)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            fm = "".join(lines[: i + 1])
            body = "".join(lines[i + 1:])
            return (fm, body)
    # No closing fence found — treat as no frontmatter to stay defensive
    # (the source SKILL.md files all have well-formed fences; this branch
    # is a guard against authoring mistakes, not normal operation).
    return ("", text)


class HostRenderer(ABC):
    """Small host-adapter surface for scaffold/runtime materialization."""

    name = "host"

    def __init__(self, plugin: Path, target: Path, *, force: bool = False):
        self.plugin = plugin
        self.target = target
        self.force = force

    @abstractmethod
    def translate_hook_protocol(self, logical_result: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def bind_paths(self) -> dict[str, str]:
        raise NotImplementedError


class ClaudeScaffoldRenderer(HostRenderer):
    """Claude Code scaffold renderer metadata and path rewrites."""

    name = "claude"
    SKILL_PATH_RE = _PLUGIN_SKILL_PATH_RE
    SKILL_PATH_REPLACEMENT = (
        r"${CLAUDE_PROJECT_DIR}/.claude/skills/jig-\1/"
    )
    PLUGIN_HOOK_SCRIPT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
    PROJECT_HOOK_SCRIPT_PREFIX = "${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/"

    @classmethod
    def rewrite_skill_md_paths(cls, body: str) -> str:
        return cls.SKILL_PATH_RE.sub(cls.SKILL_PATH_REPLACEMENT, body)

    @classmethod
    def rewrite_hook_command(cls, command: str) -> str:
        return command.replace(
            cls.PLUGIN_HOOK_SCRIPT_PREFIX,
            cls.PROJECT_HOOK_SCRIPT_PREFIX,
        )

    def translate_hook_protocol(self, logical_result: dict) -> dict:
        translated: dict = {}
        if "continue" in logical_result:
            translated["continue"] = logical_result["continue"]
        if "additional_context" in logical_result:
            translated["additionalContext"] = logical_result["additional_context"]
        if "block_reason" in logical_result:
            translated["exit_code"] = 2
            translated["stderr"] = logical_result["block_reason"]
        return translated

    def bind_paths(self) -> dict[str, str]:
        return {
            "project_root_env": "CLAUDE_PROJECT_DIR",
            "runtime_root": "${CLAUDE_PROJECT_DIR}/.claude",
            "plugin_root_env": "CLAUDE_PLUGIN_ROOT",
        }


class CodexScaffoldRenderer(ClaudeScaffoldRenderer):
    """Codex scaffold/plugin renderer metadata and TOML agent materializer."""

    name = "codex"
    SKILL_PATH_REPLACEMENT = (
        r"${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-\1/"
    )
    PROJECT_HOOK_SCRIPT_PREFIX = "${CODEX_PROJECT_DIR:-$PWD}/.codex/hooks/scripts/"
    CODEX_AGENT_MANAGED_MARKER = "# Generated by jig. managed_by_jig: true\n"
    CODEX_AGENT_SANDBOX_BY_ROLE = {
        "architect": "read-only",
        "implementer": "workspace-write",
        "reviewer": "read-only",
    }
    CODEX_AGENT_NOTE = (
        "Codex adapter note: this custom agent is rendered from jig's "
        "canonical Markdown role prompt. The TOML sandbox_mode is the "
        "closest Codex-native posture for the role; treat any remaining "
        "Claude-specific capability language as operating intent.\n\n"
    )

    @classmethod
    def rewrite_skill_md_paths(cls, body: str) -> str:
        out = cls.SKILL_PATH_RE.sub(cls.SKILL_PATH_REPLACEMENT, body)
        out = out.replace(
            "${CLAUDE_PLUGIN_ROOT}/templates/",
            "${CODEX_PROJECT_DIR:-$PWD}/.codex/templates/",
        )
        out = out.replace("${CLAUDE_PLUGIN_ROOT}", "${CODEX_PROJECT_DIR:-$PWD}/.codex")
        out = out.replace("${CLAUDE_PROJECT_DIR}", "${CODEX_PROJECT_DIR:-$PWD}")
        out = out.replace("CLAUDE_PLUGIN_ROOT", "CODEX_PROJECT_DIR")
        out = out.replace("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")
        out = out.replace(".claude/", ".codex/")
        out = out.replace("CLAUDE.md", "AGENTS.md")
        out = out.replace("Claude Code", "Codex")
        out = out.replace("Claude", "Codex")
        out = cls.finalize_codex_migrate_skill(out)
        out = cls.rewrite_skill_override_guidance(out)
        scaffold_invocation = (
            'python3 "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/'
            'jig-scaffold-init/scaffold.py" \\\n'
        )
        if scaffold_invocation in out and "--host codex" not in out:
            out = out.replace(
                scaffold_invocation,
                scaffold_invocation + "     --host codex \\\n",
            )
        return out

    @staticmethod
    def rewrite_skill_override_guidance(body: str) -> str:
        """Keep richer-skill deferral prose aligned with Codex locations.

        Canonical jig skills remain Claude-compatible at source. Codex
        renderers rewrite that prose to the documented skill locations:
        user skills under `$HOME/.agents/skills`, repo skills under
        `.agents/skills`, and installable distribution through plugins.
        """
        out = re.sub(
            r"`~/\.codex/skills/([A-Za-z0-9_-]+)/`",
            r"`$HOME/.agents/skills/\1/`",
            body,
        )
        out = out.replace(
            "Common location:\n  `$HOME/.agents/skills/",
            "Codex user location:\n  `$HOME/.agents/skills/",
        )
        out = re.sub(
            r"Common location:\s+(`\$HOME/\.agents/skills/[A-Za-z0-9_-]+/`)",
            r"Codex user location: \1",
            out,
        )
        out = out.replace(
            "the\n"
            "> Codex skill router prefers",
            "Codex\n"
            "> can prefer",
        )
        out = out.replace(
            "the Codex skill router prefers",
            "Codex can prefer",
        )
        out = out.replace(
            "The Codex skill router should route to the\n"
            "  more specific skill automatically; if you want to be sure, explicitly\n"
            "  invoke it.",
            "Codex can select the\n"
            "  more specific skill by description; if you want to be sure, explicitly\n"
            "  invoke that skill.",
        )
        out = out.replace(
            "The Codex skill router should route\n"
            "  to the more specific skill automatically; if you want to be sure,\n"
            "  explicitly invoke it.",
            "Codex can select\n"
            "  the more specific skill by description; if you want to be sure,\n"
            "  explicitly invoke that skill.",
        )
        out = out.replace(
            "Jig's\n"
            "  description tells the Codex router",
            "Jig's\n"
            "  description tells Codex",
        )
        out = out.replace(
            "Jig's description tells the Codex router",
            "Jig's description tells Codex",
        )
        out = out.replace(
            "If the router consistently picks jig's\n"
            "  baseline over such a skill",
            "If Codex consistently picks jig's\n"
            "  baseline over such a skill",
        )
        out = out.replace(
            "**This router-based deferral applies to _interactive_ use only.**",
            "**This richer-skill deferral applies to _interactive_ use only.**",
        )
        out = out.replace(
            "**This router-based deferral applies to _interactive_ use\n"
            "  only.**",
            "**This richer-skill deferral applies to _interactive_ use\n"
            "  only.**",
        )
        out = re.sub(
            r"there\s+"
            r"`review\.py` does explicit file-read dispatch \(detects\n"
            r"  `\$HOME/\.agents/skills/([A-Za-z0-9_-]+)/` and points the "
            r"reviewer at it\)\.",
            "there\n"
            "  `review.py` uses a host-specific file-read fallback outside "
            "this Codex-rendered skill-selection path. Codex-rendered "
            "guidance keeps "
            "richer-skill deferral to interactive skill selection or "
            "explicit invocation.",
            out,
        )
        out = out.replace(
            "so it cannot use the router at all",
            "so it cannot use interactive skill selection",
        )
        out = re.sub(
            r"scope and the router will prefer\s+it\.",
            "scope and Codex can prefer it.",
            out,
        )
        return out

    @staticmethod
    def replace_rendered_section(body: str, start: str, end: str,
                                 replacement: str) -> str:
        start_idx = body.find(start)
        if start_idx == -1:
            return body
        end_idx = body.find(end, start_idx)
        if end_idx == -1:
            return body
        return body[:start_idx] + replacement + body[end_idx:]

    @staticmethod
    def finalize_codex_migrate_skill(body: str) -> str:
        """Keep the rendered migrate skill honest for Codex paths."""
        if "copy-machinery" not in body:
            return body
        out = body
        if "name: migrate" in out and "Codex adapter note" not in out:
            out = out.replace(
                "user-invocable: true\n---\n",
                "user-invocable: true\n---\n\n"
                "> Codex adapter note: `rename-decisions` and "
                "`copy-machinery` are host-aware. Use `--host codex` when "
                "running them from Codex-facing docs or source checkouts; "
                "helpers copied under `.codex/skills/` infer Codex by "
                "default.\n",
                1,
            )
        out = CodexScaffoldRenderer.replace_rendered_section(
            out,
            "`migrate.py` exposes four subcommands:",
            "## How to use",
            "`migrate.py` exposes four subcommands:\n\n"
            "- `report` — strictly read-only inventory + plan.\n"
            "- `rename-decisions` — applies ADR-0004's rename. Idempotent; "
            "refuses on conflict; has a `--dry-run` mode; use "
            "`--host codex` when running from Codex-facing source or plugin "
            "paths.\n"
            "- `split-slices` — extracts embedded slice sections into "
            "sibling slice files.\n"
            "- `copy-machinery` — copies jig runtime machinery into the "
            "target's Codex scaffold runtime under `.codex/`; use "
            "`--host codex` from source or plugin paths.\n\n",
        )
        out = CodexScaffoldRenderer.replace_rendered_section(
            out,
            "Host selection:",
            "How to run it:",
            "Host selection:\n\n"
            "- Use `--host codex` when invoking from Codex-facing source "
            "or plugin docs.\n"
            "- `--host auto` infers Codex only when this helper itself runs "
            "under `.codex/skills/`; from source or plugin paths, pass "
            "`--host codex` explicitly.\n\n",
        )
        out = CodexScaffoldRenderer.replace_rendered_section(
            out,
            "What it does:",
            "### Refusal: unmanaged hooks",
            "What it does:\n\n"
            "1. Copies Codex skills into `.codex/skills/jig-<name>/`, "
            "rewriting helper paths in SKILL.md bodies to that runtime.\n"
            "2. Copies non-discoverable helper aliases under "
            "`.codex/skills/<name>/` so peer helper imports continue to "
            "resolve without duplicate discoverable skills.\n"
            "3. Copies Codex agents into `.codex/agents/jig-*.toml`.\n"
            "4. Copies hook scripts into `.codex/hooks/scripts/`, pinning "
            "each script's mode to `0o755`.\n"
            "5. Generates or merges Codex hook registration in "
            "`.codex/hooks.json`, with a top-level jig-managed metadata "
            "marker.\n\n"
            "Subsequent runs are idempotent: re-running `copy-machinery` "
            "overwrites copied runtime files in place and regenerates "
            "jig-managed `.codex/hooks.json` as a whole.\n\n",
        )
        out = re.sub(
            r"If the host hook configuration already exists.*?"
            r"`scaffold-init` enforces\.",
            "If `.codex/hooks.json` already exists without top-level "
            "`metadata.managed_by_jig: true`, `copy-machinery` exits "
            "non-zero (exit code 3) and emits the `UnmanagedHooksError` "
            "refuse-message to stderr — no filesystem writes occur. This "
            "matches the same safety stance `scaffold-init` enforces.",
            out,
            flags=re.DOTALL,
        )
        out = re.sub(
            r"With `--force`, `--host claude`.*?has been backed up\.",
            "With `--force`, Codex replaces an unmanaged `.codex/hooks.json` "
            "with jig's generated hook registration. Use this only when you "
            "are sure the existing hook config should be replaced or has "
            "been backed up.",
            out,
            flags=re.DOTALL,
        )
        out = out.replace(
            "**`migrate.py` is read-only EXCEPT for `rename-decisions`.",
            "**`migrate.py report` is read-only; migration operations are "
            "bounded mutators.",
        )
        out = CodexScaffoldRenderer.replace_rendered_section(
            out,
            "- **`rename-decisions` is bounded by `<project-dir>`.",
            "- **Always `--dry-run` first.",
            "- **`rename-decisions` is bounded by `<project-dir>`.** It "
            "never reads or writes outside the directory passed on the CLI. "
            "With `--host codex`, it scans shared `docs/` plus `AGENTS.md` "
            "and `.codex/`. Well-known skip paths (`.git`, `node_modules`, "
            "`.venv`, `__pycache__`, `dist`, `build`, etc.) are excluded "
            "from cross-reference scanning.\n",
        )
        out = out.replace(
            "rename-decisions <project-dir> --dry-run",
            "rename-decisions <project-dir> --host codex --dry-run",
        )
        out = out.replace(
            "copy-machinery <project-dir> --force",
            "copy-machinery <project-dir> --host codex --force",
        )
        out = out.replace(
            "rename-decisions <project-dir>\n",
            "rename-decisions <project-dir> --host codex\n",
        )
        out = out.replace(
            "copy-machinery <project-dir>\n",
            "copy-machinery <project-dir> --host codex\n",
        )
        out = out.replace(
            "copy-machinery <project-dir>`",
            "copy-machinery <project-dir> --host codex`",
        )
        return out

    @staticmethod
    def restore_claude_only_migrate_copy_machinery(body: str) -> str:
        """Backward-compatible alias for older callers."""
        return CodexScaffoldRenderer.finalize_codex_migrate_skill(body)

    @staticmethod
    def codex_agent_file_name(name: str) -> str:
        stem = Path(name).stem.removeprefix("jig-")
        return f"jig-{stem}.toml"

    @classmethod
    def render_codex_agent(cls, agent: Path) -> str:
        return cls.render_codex_agent_toml(agent)

    @classmethod
    def render_codex_agent_toml(cls, agent: Path) -> str:
        source = agent.read_text()
        frontmatter, body = _split_frontmatter(source)
        role = agent.stem.removeprefix("jig-")
        name = f"jig-{role}"
        description = cls.agent_frontmatter_value(frontmatter, "description", role)
        sandbox_mode = cls.codex_agent_sandbox_mode(role)
        instructions = cls.CODEX_AGENT_NOTE + cls.rewrite_agent_body(body)
        if not instructions.endswith("\n"):
            instructions += "\n"
        return (
            cls.CODEX_AGENT_MANAGED_MARKER
            + f"name = {cls.toml_string(name)}\n"
            + f"description = {cls.toml_string(description)}\n"
            + f"sandbox_mode = {cls.toml_string(sandbox_mode)}\n"
            + "developer_instructions = "
            + f"{cls.toml_multiline_literal(instructions)}\n"
        )

    @classmethod
    def codex_agent_sandbox_mode(cls, role: str) -> str:
        try:
            return cls.CODEX_AGENT_SANDBOX_BY_ROLE[role]
        except KeyError as exc:
            raise CodexAgentRoleError(
                f"No Codex sandbox mapping configured for agent role: {role}"
            ) from exc

    @staticmethod
    def agent_frontmatter_value(frontmatter: str, key: str, default: str) -> str:
        for line in frontmatter.splitlines():
            match = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
            if match:
                return match.group(1).strip().strip("\"'") or default
        return default

    @staticmethod
    def toml_string(value: str) -> str:
        return json.dumps(value)

    @staticmethod
    def toml_multiline_literal(value: str) -> str:
        if "'''" not in value:
            return "'''" + value + "'''"
        return json.dumps(value)

    @staticmethod
    def rewrite_agent_body(body: str) -> str:
        out = body.replace(".claude", ".codex")
        out = out.replace("CLAUDE.md", "AGENTS.md")
        out = out.replace("Claude Code", "Codex")
        out = out.replace("Claude", "Codex")
        return out

    @classmethod
    def rewrite_hook_command(cls, command: str) -> str:
        return command.replace(
            cls.PLUGIN_HOOK_SCRIPT_PREFIX,
            cls.PROJECT_HOOK_SCRIPT_PREFIX,
        )

    @classmethod
    def rewrite_hook_script_body(cls, body: str) -> str:
        out = body.replace("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")
        out = out.replace("CLAUDE_PLUGIN_ROOT", "CODEX_HOME")
        out = out.replace(".claude", ".codex")
        out = out.replace("Claude", "Codex")
        return out

    def bind_paths(self) -> dict[str, str]:
        return {
            "project_root_env": "CODEX_PROJECT_DIR",
            "runtime_root": "${CODEX_PROJECT_DIR:-$PWD}/.codex",
            "plugin_root_env": "PLUGIN_ROOT",
        }


def _copy_skill_dir(src: Path, dst: Path) -> None:
    """Copy a single skill directory. SKILL.md gets path-substitution on
    its body; other .py files (excluding test_*.py) are copied verbatim;
    everything else under the skill dir is mirrored verbatim too. Skips
    `__pycache__`, `fixtures/` (test data, never runtime — per spec 035),
    and `test_*.py` — except for the narrow per-skill allow-list in
    `_RETAINED_TEST_FILES` (spec 043-04 retains `test_quality.py` so
    scaffolded projects can exercise the quality.py snapshot wiring)."""
    retained = _RETAINED_TEST_FILES.get(src.name, frozenset())
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        # Skip excluded dir trees at any depth. `__pycache__` is build
        # artifact; `fixtures/` is reserved as test data, never runtime
        # (spec 035: any-depth match per Q1, no escape hatch per Q4 —
        # future skills needing runtime sample data must use `samples/`,
        # `examples/`, `data/`, etc., not `fixtures/`).
        if any(part in _SKILL_DIR_EXCLUDES for part in rel.parts):
            continue
        if entry.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        # Exclude test files anywhere in the tree, unless the per-skill
        # allow-list explicitly retains this filename. Per spec 043-04:
        # tdd-loop ships `test_quality.py` to scaffolded projects so the
        # quality.py snapshot wiring is exercisable end-to-end.
        if (
            entry.name.startswith("test_")
            and entry.name.endswith(".py")
            and entry.name not in retained
        ):
            continue
        target_path = dst / rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if entry.name == "SKILL.md":
            text = entry.read_text()
            fm, body = _split_frontmatter(text)
            rewritten = fm + _rewrite_skill_md_paths(body)
            atomic_write_text(target_path, rewritten)
        else:
            target_path.write_bytes(entry.read_bytes())


def _iter_skill_runtime_files(src: Path) -> list[Path]:
    """Return runtime files from a skill directory using scaffold exclusions."""
    retained = _RETAINED_TEST_FILES.get(src.name, frozenset())
    files: list[Path] = []
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        if any(part in _SKILL_DIR_EXCLUDES for part in rel.parts):
            continue
        if entry.is_dir():
            continue
        if (
            entry.name.startswith("test_")
            and entry.name.endswith(".py")
            and entry.name not in retained
        ):
            continue
        files.append(entry)
    return sorted(files)


def _copy_codex_skill_dir(src: Path, dst: Path, *, include_skill_md: bool = True) -> None:
    """Copy a skill directory into Codex runtime shape."""
    copied_any = False
    for entry in _iter_skill_runtime_files(src):
        if entry.name == "SKILL.md" and not include_skill_md:
            continue
        rel = entry.relative_to(src)
        target_path = dst / rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if entry.name == "SKILL.md":
            atomic_write_text(
                target_path,
                CodexScaffoldRenderer.rewrite_skill_md_paths(entry.read_text()),
            )
        else:
            target_path.write_bytes(entry.read_bytes())
        copied_any = True
    if copied_any:
        dst.mkdir(parents=True, exist_ok=True)


def _copy_codex_templates(plugin: Path, target: Path) -> None:
    templates_src = plugin / "templates"
    templates_dst = target / ".codex" / "templates"
    if not templates_src.is_dir():
        return
    for entry in sorted(templates_src.rglob("*")):
        if entry.is_dir():
            continue
        rel = entry.relative_to(templates_src)
        dst = templates_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(entry.read_bytes())


def _copy_codex_skills(plugin: Path, target: Path,
                       installed_tiers: "list | None" = None) -> None:
    skills_src = plugin / "skills"
    skills_dst = target / ".codex" / "skills"
    if not skills_src.is_dir():
        return
    selected_tiers = set(installed_tiers) if installed_tiers is not None else None
    skills_dst.mkdir(parents=True, exist_ok=True)
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("_"):
            _copy_codex_skill_dir(skill_dir, skills_dst / skill_dir.name)
            continue
        logical_name = skill_dir.name.removeprefix("jig-")
        if not (skill_dir / "SKILL.md").is_file():
            continue
        tier = _SKILL_TO_TIER.get(logical_name)
        if selected_tiers is not None and tier not in selected_tiers:
            continue
        _copy_codex_skill_dir(skill_dir, skills_dst / f"jig-{logical_name}")
        # Non-discoverable alias for helpers that resolve peer paths by the
        # original skill directory name. Omit SKILL.md to avoid duplicate skills.
        _copy_codex_skill_dir(
            skill_dir,
            skills_dst / logical_name,
            include_skill_md=False,
        )


def _copy_codex_agents(plugin: Path, target: Path) -> None:
    agents_src = plugin / "agents"
    agents_dst = target / ".codex" / "agents"
    if not agents_src.is_dir():
        return
    agents_dst.mkdir(parents=True, exist_ok=True)
    for agent in sorted(agents_src.glob("*.md")):
        dst = agents_dst / CodexScaffoldRenderer.codex_agent_file_name(agent.name)
        atomic_write_text(dst, CodexScaffoldRenderer.render_codex_agent_toml(agent))


# Marker stamped on every jig-managed hook entry in `.claude/settings.json`.
# Used by both the idempotent re-run path (replace-in-place rather than
# duplicate) and the AC #4 safety check (an existing settings.json with hooks
# but no jig marker is "managed by someone else" — refuse to merge without
# --force).
_JIG_HOOK_MARKER = {"managed_by_jig": True}

# Source-of-truth hook events for the project-scoped registration.
# Mirrors hooks/hooks.json shape exactly, with only the command-path rewrite.
_PLUGIN_HOOK_SCRIPT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
_PROJECT_HOOK_SCRIPT_PREFIX = "${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/"

# Slice 052-03 — conservative `permissions.deny` defaults scaffolded into
# `.claude/settings.json` (the security floor's destructive-command guardrail,
# ADR-0013 part 3). Canonical Claude Code permission-rule shape is
# `Bash(<pattern with * wildcards>)`. The set covers the documented dangerous
# forms — force-push, hard-reset, recursive-force `rm` — plus their common
# flag permutations (`-f`, `* --force`, `--force-with-lease`, `rm -fr`,
# `rm -r -f`) so the prefix globs catch the usual orderings.
#
# HONEST FRAMING (AC #3, per ADR-0013): these deny-globs are
# DEFENSE-IN-DEPTH, NOT A FIREWALL. Glob prefixes inherently miss flag
# permutations — e.g. `git push origin main --force` is NOT matched by the
# `Bash(git push --force*)` prefix, which is why the `Bash(git push * --force*)`
# wildcard form is also listed — but coverage is still not exhaustive, and a
# permission rule lives inside the agent's own trust boundary (it can be
# relaxed). The PRIMARY control therefore stays behavioral + out-of-band: CI,
# server-side git hooks, and branch protection. "Deny rules are
# defense-in-depth, not a firewall." (guidelines `04-configuration/permissions.md`).
_PERMISSIONS_DENY_DEFAULTS = (
    "Bash(git push --force*)",
    "Bash(git push -f *)",
    "Bash(git push * --force*)",
    "Bash(git push *--force-with-lease*)",
    "Bash(git reset --hard*)",
    "Bash(rm -rf*)",
    "Bash(rm -fr*)",
    "Bash(rm -r -f*)",
)


def _is_jig_managed(entry: dict) -> bool:
    """An entry counts as jig-managed iff its `metadata.managed_by_jig` is
    truthy. Stable across re-runs."""
    return bool((entry.get("metadata") or {}).get("managed_by_jig"))


def _rewrite_hook_command(command: str) -> str:
    """Rewrite a single hook command's `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/`
    prefix to `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`. Hooks scripts
    themselves use `$CLAUDE_PROJECT_DIR` internally (audit-confirmed), so
    only the dispatch path needs rewriting."""
    return command.replace(_PLUGIN_HOOK_SCRIPT_PREFIX,
                           _PROJECT_HOOK_SCRIPT_PREFIX)


_CODEX_HOOK_STATUS_MESSAGES = {
    "jig-boundary-change-warn.sh": "jig: warn on boundary changes",
    "jig-context-check.sh": "jig: check context budget",
    "jig-memory-scan.sh": "jig: scan memory references",
    "jig-post-edit-verify.sh": "jig: verify edit landed",
    "jig-secret-scan.sh": "jig: scan for secrets",
    "jig-skill-trace.sh": "jig: record skill usage",
    "jig-spec-gate.sh": "jig: enforce spec gate",
    "jig-task-capture.sh": "jig: capture follow-up tasks",
    "jig-telemetry.sh": "jig: record task telemetry",
}


def _codex_hook_status_message(command: str) -> str:
    match = re.search(r"(jig-[A-Za-z0-9-]+\.sh)", command)
    if not match:
        return "jig: run hook"
    script = match.group(1)
    if script in _CODEX_HOOK_STATUS_MESSAGES:
        return _CODEX_HOOK_STATUS_MESSAGES[script]
    stem = script.removeprefix("jig-").removesuffix(".sh").replace("-", " ")
    return f"jig: {stem}"


def _build_codex_hooks_from_source(source: dict, command_rewriter=None) -> dict:
    """Render source hooks into Codex-compatible hook entries.

    The canonical hook source is still Claude-compatible, where async command
    hooks are valid. Codex currently skips handlers with ``async: true`` and
    renders unnamed handlers as "Hook N", so the Codex adapter strips async
    metadata and supplies stable status messages for command hooks.
    """
    if command_rewriter is None:
        command_rewriter = lambda command: command

    out: dict = {}
    for event, entries in (source.get("hooks") or {}).items():
        new_entries = []
        for entry in entries:
            new_inner = []
            for h in entry.get("hooks", []):
                rewritten = dict(h)
                rewritten.pop("async", None)
                command = rewritten.get("command")
                if isinstance(command, str):
                    rewritten["command"] = command_rewriter(command)
                    rewritten.setdefault(
                        "statusMessage",
                        _codex_hook_status_message(rewritten["command"]),
                    )
                new_inner.append(rewritten)
            new_entry = {}
            if "matcher" in entry:
                new_entry["matcher"] = entry["matcher"]
            new_entry["hooks"] = new_inner
            new_entries.append(new_entry)
        out[event] = new_entries
    return out


def render_codex_plugin_hooks(source: dict) -> dict:
    """Render a Codex plugin ``hooks/hooks.json`` payload from source hooks."""
    return {"hooks": _build_codex_hooks_from_source(source)}


def _build_jig_hook_entries(plugin: Path) -> dict:
    """Read `plugin/hooks/hooks.json` and produce a dict keyed by event name
    of hook entries with:
      - command paths rewritten to `${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/`
      - a `metadata: {managed_by_jig: true}` marker on every entry
      - matchers, timeouts, async flags, and inner shape carried over verbatim
    """
    source = json.loads((plugin / "hooks" / "hooks.json").read_text())
    out: dict = {}
    for event, entries in (source.get("hooks") or {}).items():
        new_entries = []
        for entry in entries:
            new_inner = []
            for h in entry.get("hooks", []):
                rewritten = dict(h)
                if "command" in rewritten:
                    rewritten["command"] = _rewrite_hook_command(rewritten["command"])
                new_inner.append(rewritten)
            new_entry = {}
            if "matcher" in entry:
                new_entry["matcher"] = entry["matcher"]
            new_entry["hooks"] = new_inner
            new_entry["metadata"] = dict(_JIG_HOOK_MARKER)
            new_entries.append(new_entry)
        out[event] = new_entries
    return out


def _merge_permissions_deny(existing_perms: dict) -> dict:
    """Slice 052-03 — merge jig's conservative `permissions.deny` defaults
    into a (possibly pre-existing) `permissions` block.

    Marker = SET-MEMBERSHIP. `permissions.deny` is a plain array of strings,
    so it cannot carry a per-entry `metadata.managed_by_jig` marker the way
    hook entries do. jig-ownership of a deny entry is therefore identified by
    membership in `_PERMISSIONS_DENY_DEFAULTS` — the faithful adaptation of
    the hooks block's metadata-marker mechanism for a string array (AC #2:
    "same jig-managed marker mechanism").

    Strategy: keep every existing deny entry that is NOT in jig's set (so
    user-added denies survive verbatim and in order), then append jig's full
    set. This is idempotent (re-running yields the same set, no duplicates)
    and never drops user entries. `allow`, `ask`, and any other
    `permissions.*` keys are preserved untouched — only `deny` is
    jig-managed. Returns a new dict; does not mutate `existing_perms`."""
    perms: dict = dict(existing_perms) if existing_perms else {}
    current_deny = list(perms.get("deny") or [])
    jig_set = set(_PERMISSIONS_DENY_DEFAULTS)
    user_deny = [d for d in current_deny if d not in jig_set]
    perms["deny"] = user_deny + list(_PERMISSIONS_DENY_DEFAULTS)
    return perms


def _merge_settings(existing: dict, jig_hooks: dict) -> dict:
    """Merge jig's hook registration into a (possibly pre-existing) settings
    dict. Strategy: append-with-marker.

    - Non-hook top-level fields pass through untouched.
    - Per event: keep all non-jig-managed entries verbatim; replace any
      jig-managed entries with the fresh set (idempotent re-run).
    - `permissions.deny` gains jig's conservative destructive-command
      defaults via `_merge_permissions_deny` (slice 052-03); `permissions`'s
      other keys (`allow` / `ask` / …) are preserved untouched. Because this
      function is on the shared copy path, BOTH greenfield `scaffold()` and
      `migrate copy-machinery` emit the deny defaults.
    - Returns a new dict; does not mutate `existing`."""
    merged: dict = dict(existing) if existing else {}
    hooks = dict(merged.get("hooks") or {})
    for event, fresh_entries in jig_hooks.items():
        current = hooks.get(event) or []
        survivors = [e for e in current if not _is_jig_managed(e)]
        hooks[event] = survivors + fresh_entries
    merged["hooks"] = hooks
    merged["permissions"] = _merge_permissions_deny(merged.get("permissions"))
    return merged


def _check_hooks_safety(target: Path, *, force: bool = False) -> dict:
    """Inbox 2026-05-15 — extract the settings.json safety check so callers
    that orchestrate multiple copy steps (`copy_machinery`) can run it
    BEFORE any filesystem mutation, eliminating the partial-state-on-refuse
    rough edge spec 016-03 deviation §7 noted.

    Returns the parsed `existing` settings dict (empty if no settings.json
    is present). Raises `UnmanagedHooksError` if settings.json has hook
    entries but none carry the jig-managed marker and `force` is False.
    Raises `RuntimeError` if settings.json exists but is invalid JSON.
    """
    settings_path = target / ".claude" / "settings.json"
    existing: dict = {}
    if not settings_path.is_file():
        return existing
    try:
        existing = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{settings_path} exists but is not valid JSON: {exc}"
        ) from exc
    existing_hooks = existing.get("hooks") or {}
    has_any_hook = any(
        (entries or []) for entries in existing_hooks.values()
    )
    has_jig_marker = any(
        _is_jig_managed(entry)
        for entries in existing_hooks.values()
        for entry in (entries or [])
    )
    if has_any_hook and not has_jig_marker and not force:
        raise UnmanagedHooksError(
            f"{settings_path} already has hooks but none carry the "
            "jig-managed marker — refusing to merge to avoid clobbering "
            "third-party hook configuration. Pass --force to append "
            "jig hooks alongside the existing entries, or remove the "
            "file and re-run."
        )
    return existing


def _copy_hooks_and_register(plugin: Path, target: Path, *,
                             force: bool = False) -> None:
    """Slice 016-02 — copy hook scripts + write/merge `.claude/settings.json`.

    - Copies every `plugin/hooks/scripts/jig-*.sh` to
      `target/.claude/hooks/scripts/`, preserving the executable bit (0o755).
    - Generates or merges `target/.claude/settings.json` with the jig
      hooks registered against project-relative paths (the set discovered
      by globbing `plugin/hooks/scripts/jig-*.sh`, not a hard-coded count).

    Refuses (`UnmanagedHooksError`) when a pre-existing settings.json has
    hook entries but none carry the jig marker, unless `force=True`. The
    safety check fires BEFORE any filesystem mutation so a refused scaffold
    leaves no partial state behind (no copied scripts, no created dirs).
    Originally introduced in slice 016-02; reordering landed as a 016-03
    follow-up after the reviewer flagged the partial-state rough edge."""
    src_scripts = plugin / "hooks" / "scripts"
    settings_path = target / ".claude" / "settings.json"

    # AC #4 (016-02) safety check — extracted to `_check_hooks_safety` so
    # callers that orchestrate multiple copy steps can run it BEFORE any
    # mutation. Inside this function, the check still runs first.
    existing = _check_hooks_safety(target, force=force)

    # Safety check passed (or settings.json doesn't exist). Now mutate.
    dst_scripts = target / ".claude" / "hooks" / "scripts"
    dst_scripts.mkdir(parents=True, exist_ok=True)
    if src_scripts.is_dir():
        for script in sorted(src_scripts.glob("jig-*.sh")):
            dst = dst_scripts / script.name
            dst.write_bytes(script.read_bytes())
            # AC #5 — executable bit set. We don't trust the umask; pin to
            # 0o755 explicitly so the scaffolded tree behaves identically
            # across umasks (e.g. 0o022 vs. 0o077).
            os.chmod(dst, 0o755)

        # Slice 026-01 — hooks/scripts/lib/ ships beside the .sh files
        # so jig-context-check.sh can import its helper after a scaffold
        # install. Copy .py files only (no __pycache__, no test_*.py —
        # the scaffolded install carries runtime modules, not tests).
        src_lib = src_scripts / "lib"
        if src_lib.is_dir():
            dst_lib = dst_scripts / "lib"
            dst_lib.mkdir(exist_ok=True)
            for py in sorted(src_lib.glob("*.py")):
                if py.name.startswith("test_"):
                    continue
                (dst_lib / py.name).write_bytes(py.read_bytes())

    jig_hooks = _build_jig_hook_entries(plugin)
    merged = _merge_settings(existing, jig_hooks)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(settings_path, json.dumps(merged, indent=2) + "\n")


def _check_codex_hooks_safety(target: Path, *, force: bool = False) -> None:
    hooks_path = target / ".codex" / "hooks.json"
    if not hooks_path.is_file():
        return
    try:
        existing = json.loads(hooks_path.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{hooks_path} exists but is not valid JSON: {exc}"
        ) from exc
    if force:
        return
    if (existing.get("metadata") or {}).get("managed_by_jig"):
        return
    raise UnmanagedHooksError(
        f"{hooks_path} already exists and is not jig-managed. Pass --force "
        "to replace it, or move/merge the file first."
    )


def _build_codex_hook_entries(plugin: Path) -> dict:
    source = json.loads((plugin / "hooks" / "hooks.json").read_text())
    return _build_codex_hooks_from_source(
        source,
        command_rewriter=CodexScaffoldRenderer.rewrite_hook_command,
    )


def _copy_codex_hooks_and_register(plugin: Path, target: Path, *,
                                   force: bool = False) -> None:
    _check_codex_hooks_safety(target, force=force)
    src_scripts = plugin / "hooks" / "scripts"
    dst_scripts = target / ".codex" / "hooks" / "scripts"
    dst_scripts.mkdir(parents=True, exist_ok=True)
    if src_scripts.is_dir():
        for script in sorted(src_scripts.glob("jig-*.sh")):
            dst = dst_scripts / script.name
            atomic_write_text(
                dst,
                CodexScaffoldRenderer.rewrite_hook_script_body(script.read_text()),
            )
            os.chmod(dst, 0o755)
        src_lib = src_scripts / "lib"
        if src_lib.is_dir():
            dst_lib = dst_scripts / "lib"
            dst_lib.mkdir(exist_ok=True)
            for py in sorted(src_lib.glob("*.py")):
                if py.name.startswith("test_"):
                    continue
                (dst_lib / py.name).write_bytes(py.read_bytes())

    source_hooks = plugin / "hooks" / "hooks.json"
    if source_hooks.is_file():
        raw_hooks = target / ".codex" / "hooks" / "hooks.json"
        raw_hooks.parent.mkdir(parents=True, exist_ok=True)
        raw_hooks.write_bytes(source_hooks.read_bytes())

    payload = {
        "metadata": {"managed_by_jig": True},
        "hooks": _build_codex_hook_entries(plugin),
    }
    hooks_path = target / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(hooks_path, json.dumps(payload, indent=2) + "\n")


def copy_codex_machinery(plugin: Path, target: Path, *,
                         force: bool = False,
                         installed_tiers: "list | None" = None) -> None:
    """Copy jig runtime machinery into target-local Codex paths."""
    _check_codex_hooks_safety(target, force=force)
    _copy_codex_templates(plugin, target)
    _copy_codex_skills(plugin, target, installed_tiers)
    _copy_codex_agents(plugin, target)
    _copy_codex_hooks_and_register(plugin, target, force=force)
    _write_gitignore_secret_block(target)


def install_codex_agents(plugin: Path, agents_dir: Path, *,
                         force: bool = False) -> list[Path]:
    """Install generated Codex custom-agent TOML files into `agents_dir`."""
    agents_src = plugin / "agents"
    if not agents_src.is_dir():
        raise FileNotFoundError(f"Agents source not found: {agents_src}")
    agents_dir = agents_dir.expanduser().resolve()
    payloads = [
        (
            CodexScaffoldRenderer.codex_agent_file_name(agent.name),
            CodexScaffoldRenderer.render_codex_agent_toml(agent),
        )
        for agent in sorted(agents_src.glob("*.md"))
    ]
    if not payloads:
        raise FileNotFoundError(f"No Codex agent sources found in {agents_src}")

    if agents_dir.exists() and not force:
        for name, text in payloads:
            dst = agents_dir / name
            if not dst.exists():
                continue
            existing = dst.read_text()
            if existing != text and not existing.startswith(
                CodexScaffoldRenderer.CODEX_AGENT_MANAGED_MARKER
            ):
                raise CodexAgentInstallConflictError(
                    f"{dst} exists and is not jig-managed. Pass --force to "
                    "replace it, or choose a different --codex-agents-dir."
                )

    agents_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []
    for name, text in payloads:
        dst = agents_dir / name
        atomic_write_text(dst, text)
        installed.append(dst)
    return installed


def copy_machinery(plugin: Path, target: Path, *,
                   force: bool = False,
                   installed_tiers: "list | None" = None,
                   host: str = "claude") -> None:
    """Copy jig's runtime machinery into the target's host-local runtime.

    Public façade introduced by slice 021-01 so that `migrate.py
    copy-machinery` can reuse exactly the same logic `scaffold-init` uses
    when `--with-machinery` is in effect. Internally calls, in order:

      1. `_check_hooks_safety(target, force=force)` — pre-flight safety
         check (inbox 2026-05-15): ensures we refuse BEFORE any filesystem
         mutation when settings.json is unmanaged. Closes the partial-
         state-on-refuse gap noted in spec 016-03 deviation §7.
      2. `_copy_skills_and_agents(plugin, target, installed_tiers)` —
         slice 016-01; tier-gated since slice 038-02.
      3. `_copy_hooks_and_register(plugin, target, force=force)` — slice
         016-02; the safety check inside this call is now redundant but
         kept so the function still works correctly when called directly.

    `installed_tiers` (slice 038-02) is forwarded to
    `_copy_skills_and_agents` to gate which skills are copied. `None`
    copies every tier — the standing "tiers unknown → copy-all" contract
    (e.g. a `migrate.py copy-machinery` run against a project with no
    `scaffold.json`). The greenfield `scaffold()` caller passes its
    `_select_tiers` result; `migrate.py copy-machinery` passes the tiers it
    resolves from / raises in the target manifest (slice 038-04).

    `host` defaults to `claude`, preserving the original `.claude/` output
    and settings merge. `host="codex"` routes through the Codex scaffold
    adapter and writes `.codex/` skills, agents, hook scripts, templates, and
    hook registration instead.

    Safety guarantees:
    - Executable bit pinned to 0o755 on copied hook scripts.
    - Marker-based merge in `.claude/settings.json` (replace-in-place by
      `metadata.managed_by_jig`, non-jig entries survive).
    - UnmanagedHooksError fires BEFORE any filesystem mutation, so a
      refused call leaves no partial state — including no copied
      skills/agents (this is the gap inbox 2026-05-15 closes).

    Slice 052-04 (ADR-0013): the security floor's `.gitignore` secret block
    is written here too, so `migrate copy-machinery` brings it to an
    existing jig project (the secret-scan hook + `permissions.deny` defaults
    already flow through `_copy_hooks_and_register` / `_merge_settings`).
    The write is ungated infra — never tier-scoped (AC2) — and idempotent,
    so the greenfield `scaffold()` caller can rely on it for the
    `--with-machinery` path and only writes the floor itself on the
    `--plugin-only` branch (where `copy_machinery` is not called)."""
    if host == "codex":
        copy_codex_machinery(
            plugin, target, force=force, installed_tiers=installed_tiers,
        )
        return
    if host != "claude":
        raise ValueError(f"unsupported scaffold host: {host}")
    _check_hooks_safety(target, force=force)
    _copy_skills_and_agents(plugin, target, installed_tiers)
    _copy_hooks_and_register(plugin, target, force=force)
    _write_gitignore_secret_block(target)
    # Spec 065-04: refresh the self-defining-vocabulary convention block into
    # the project's docs/workflow.md (the only path that reaches an EXISTING
    # project — copy-machinery does not otherwise touch docs/). Idempotent.
    _ensure_self_defining_convention_block(target)


def _specs_dir_has_content(target: Path) -> bool:
    """Greenfield guard for the seed reference spec (slice 048-05,
    Clarification Q1). True iff `target/docs/specs/` already contains a
    user spec — i.e. any `*/spec.md` under it.

    The empty status board (`docs/specs/README.md`) that the generic doc
    copy emits is NOT spec content, so its presence does not block the
    seed. Only a `<spec-dir>/spec.md` counts. Erring toward "has content"
    is the safe side: a false positive merely skips the (optional) seed,
    while a false negative would overwrite a real user spec."""
    specs_dir = target / "docs" / "specs"
    if not specs_dir.is_dir():
        return False
    for child in specs_dir.iterdir():
        if child.is_dir() and (child / "spec.md").is_file():
            return True
    return False


def _emit_seed_spec(template_root: Path, target: Path, subs: dict) -> None:
    """Emit the worked-example reference spec (slice 048-05) into a
    greenfield `docs/specs/`:

      - `001-adopt-jig/spec.md` + `slice-01-bootstrap.md` (status: DONE),
      - `002-first-spec/spec.md` (status: DRAFT hand-off stub),
      - a populated `docs/specs/README.md` status board.

    Greenfield-only (Clarification Q1): if `docs/specs/` already has spec
    content, the seed is skipped silently and never overwrites the user's
    work. The seed templates carry only the `{{PROJECT_NAME}}` substitution
    and never leak `${CLAUDE_PLUGIN_ROOT}` or source-checkout paths — they
    read correctly inside the target tree (coordinated with spec 046)."""
    if _specs_dir_has_content(target):
        return
    seed_root = template_root / "docs" / "specs" / "seed"
    if not seed_root.is_dir():
        return
    specs_dst = target / "docs" / "specs"
    for src in sorted(seed_root.rglob("*.md.template")):
        rel = src.relative_to(seed_root)
        dst_name = rel.with_suffix("")  # strip .template, leaves .md
        # The seed's README.md.template overwrites the empty status board
        # emitted by the generic doc copy (step 2); the spec/slice files
        # land in their 001-adopt-jig / 002-first-spec subdirs.
        dst = specs_dst / dst_name
        copy_template(src, dst, subs)


# ---------- Slice 052-02: secret-ignore .gitignore floor (ADR-0013) ----------
# Marker-delimited block so a re-run REPLACES the block in place (idempotent,
# no duplicates) while any pre-existing user content is preserved. Kept a
# standalone function because slice 052-04 reuses it for `migrate
# copy-machinery`.
_GITIGNORE_BLOCK_BEGIN = "# >>> jig secret-ignore >>>"
_GITIGNORE_BLOCK_END = "# <<< jig secret-ignore <<<"

# Conservative high-confidence secret-file patterns (ADR-0013 part 1). These
# git-ignore the files that most often carry secrets so an accidental `git add`
# can't stage them. Not exhaustive by design — the floor, not the ceiling.
_GITIGNORE_SECRET_PATTERNS = (
    ".env",
    ".env.*",
    # Re-include the placeholder templates the floor *wants* committed: the
    # secret-scan hook tells users to "commit a placeholder in a *.example
    # file" and skips these suffixes when scanning, so `.env.*` above must
    # not ignore them. Git negations only take effect after the matching
    # ignore line, so these must follow `.env.*`.
    "!.env.example",
    "!.env.sample",
    "!.env.template",
    "!.env.dist",
    "*.pem",
    "*.key",
    "secrets/",
    "credentials/",
)


def _render_gitignore_block() -> str:
    """The marker-delimited jig secret-ignore block, including a one-line
    honesty/intent comment. Trailing newline included."""
    lines = [
        _GITIGNORE_BLOCK_BEGIN,
        "# jig secret-prevention floor (ADR-0013) — git-ignore common secret",
        "# files so they can't be staged by accident. Edit above/below the",
        "# markers; this block is regenerated by jig and re-runs are idempotent.",
        *_GITIGNORE_SECRET_PATTERNS,
        _GITIGNORE_BLOCK_END,
    ]
    return "\n".join(lines) + "\n"


def _write_gitignore_secret_block(target: Path) -> None:
    """Write or merge the marker-delimited jig secret-ignore block into
    `target/.gitignore` (slice 052-02, AC #1).

    - No existing `.gitignore` → create it with just the jig block.
    - Existing `.gitignore` without the markers → APPEND the block (a blank
      line first if the file doesn't already end on one), preserving every
      pre-existing line verbatim.
    - Existing `.gitignore` WITH the markers → REPLACE the delimited region in
      place, leaving content before/after the markers untouched. This makes
      re-runs idempotent (no duplicate blocks).

    Atomic write via `atomic_write_text`, consistent with the other scaffold
    writes."""
    gitignore = target / ".gitignore"
    block = _render_gitignore_block()

    if not gitignore.exists():
        atomic_write_text(gitignore, block)
        return

    existing = gitignore.read_text()
    begin = existing.find(_GITIGNORE_BLOCK_BEGIN)
    if begin != -1:
        end_marker = existing.find(_GITIGNORE_BLOCK_END, begin)
        if end_marker != -1:
            # Replace from the begin marker through the end-marker's line
            # (including its trailing newline, if present).
            after = end_marker + len(_GITIGNORE_BLOCK_END)
            if after < len(existing) and existing[after] == "\n":
                after += 1
            merged = existing[:begin] + block + existing[after:]
            if merged != existing:
                atomic_write_text(gitignore, merged)
            return
        # Begin marker without a matching end marker — fall through and append
        # a fresh, well-formed block rather than corrupt the half-block.

    # Append, ensuring exactly one blank line separates prior content from
    # the jig block. Three cases for the existing file's tail:
    #   ends with "\n\n" → already blank-terminated, add nothing;
    #   ends with "\n"    → one newline short of a blank line, add "\n";
    #   no trailing "\n"  → mid-line, add "\n\n" for the blank separator.
    if existing.endswith("\n\n"):
        sep = ""
    elif existing.endswith("\n"):
        sep = "\n"
    else:
        sep = "\n\n"
    atomic_write_text(gitignore, existing + sep + block)


# --- Self-defining-vocabulary convention block (spec 065-04) --------------
#
# A marker-delimited managed block injected into a project's
# `docs/workflow.md`, mirroring the `.gitignore` secret-floor block above
# (ADR-0013 precedent: a managed block written by BOTH `scaffold()` and
# `copy_machinery()`). This is how the soft "self-defining vocabulary"
# authoring convention reaches a project — including an already-scaffolded
# one, on its next `copy-machinery` run (the live `docs/workflow.md` is not
# otherwise touched by copy-machinery). The block is HTML-comment delimited
# so the markers render invisibly in the doc.
_WORKFLOW_BLOCK_BEGIN = "<!-- >>> jig self-defining-vocabulary >>> -->"
_WORKFLOW_BLOCK_END = "<!-- <<< jig self-defining-vocabulary <<< -->"


def _render_self_defining_block() -> str:
    """Render the marker-delimited self-defining-vocabulary convention block
    (spec 065-04 AC1/AC4). Soft, forward-only, explicitly NOT a gate."""
    return "\n".join((
        _WORKFLOW_BLOCK_BEGIN,
        "## Self-defining vocabulary (authoring convention)",
        "",
        "**Soft, forward-only, not a gate.** When you author a spec or slice,",
        "expand each acronym on first use and link the term to the project",
        "glossary (`docs/memory/glossary.md`) or jig's lexicon, in plain words —",
        "so the *next* artifact is readable without a decoder ring. This stops",
        "the dense-jargon pile from growing; it does **not** retrofit existing",
        "specs, and **nothing lints or blocks a transition** on an undefined",
        "acronym (the barrier is lowered by convention, not enforced by a gate).",
        "",
        "On demand, `/jig:explain <term>` defines a single term and",
        "`/jig:explain <spec-or-adr-path>` walks a whole artifact through plain",
        "language — the back-catalogue escape hatch this convention complements.",
        _WORKFLOW_BLOCK_END,
        "",
    ))


def _ensure_self_defining_convention_block(target: Path) -> None:
    """Create / append / replace-in-place the self-defining-vocabulary block in
    `target/docs/workflow.md` (spec 065-04 AC3). Idempotent and
    non-clobbering, mirroring `_write_gitignore_secret_block`:

    - No `docs/workflow.md` → create it (parents included) with a minimal
      header + the block.
    - Exists without the markers → APPEND the block (one blank-line separator),
      preserving every pre-existing line verbatim.
    - Exists WITH the markers → REPLACE the delimited region in place, leaving
      content before/after untouched (re-runs are no-ops once current).

    Called by both `scaffold()` (fresh projects) and `copy_machinery()`
    (existing projects' next copy-machinery / tier upgrade)."""
    workflow = target / "docs" / "workflow.md"
    block = _render_self_defining_block()

    if not workflow.exists():
        workflow.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(workflow, "# Workflow\n\n" + block)
        return

    existing = workflow.read_text()
    begin = existing.find(_WORKFLOW_BLOCK_BEGIN)
    if begin != -1:
        end_marker = existing.find(_WORKFLOW_BLOCK_END, begin)
        if end_marker != -1:
            after = end_marker + len(_WORKFLOW_BLOCK_END)
            if after < len(existing) and existing[after] == "\n":
                after += 1
            merged = existing[:begin] + block + existing[after:]
            if merged != existing:
                atomic_write_text(workflow, merged)
            return
        # Begin marker without a matching end — fall through and append a
        # fresh, well-formed block rather than corrupt the half-block.

    if existing.endswith("\n\n"):
        sep = ""
    elif existing.endswith("\n"):
        sep = "\n"
    else:
        sep = "\n\n"
    atomic_write_text(workflow, existing + sep + block)


def scaffold(target: Path, plugin: Path, *, force: bool = False,
             overrides: Overrides = None,
             with_machinery: bool = True,
             host: str = "claude") -> None:
    """Run the greenfield scaffold against `target`. Refuses to overwrite an
    already-scaffolded directory unless `force=True`. `overrides` carries the
    Q&A wizard answers from slice 001-05; None fields fall back to filesystem
    inference. Plugin templates live at `plugin/templates/`.

    When `with_machinery=True` (slice 016-01; default-on as of slice 016-03),
    also copies host-local runtime machinery into the target, rewriting
    SKILL.md path placeholders. The CLI's `--plugin-only` flag sets this to
    `False` to preserve the pre-016-03 docs-only behavior."""
    if host not in {"claude", "codex"}:
        raise ValueError(f"unsupported scaffold host: {host}")

    target = target.resolve()
    template_root = plugin / "templates"

    if not template_root.exists():
        raise FileNotFoundError(f"Template root not found: {template_root}")

    if (target / "scaffold.json").exists() and not force:
        raise AlreadyScaffoldedError(
            f"{target} is already scaffolded (scaffold.json present). "
            "Pass --force to overwrite."
        )

    # Slice 008-05: detect projects that look spec-driven without a
    # scaffold.json — route them to `/jig:migrate` instead of polluting
    # the tree. `scaffold.json`-check above takes precedence; this fires
    # only when scaffold.json is absent.
    #
    # Slice 032-02: skip this check when the target is a jig partial
    # state (CLAUDE.md with jig watermark + no scaffold.json) — that's a
    # crashed-mid-scaffold recovery, not a user's spec-driven project.
    # With `scaffold.json` now written LAST (the completion sentinel),
    # a crash leaves docs/* + CLAUDE.md but no scaffold.json; the next
    # run should re-attempt without `--force`.
    if not force and not _is_jig_partial_state(target):
        triggered, triggers = _looks_already_spec_driven(target)
        if triggered:
            triggers_list = "\n  - ".join(triggers)
            raise LooksAlreadySpecDrivenError(
                f"{target} looks already-spec-driven "
                f"({len(triggers)} migrate triggers detected, no "
                f"scaffold.json present):\n  - {triggers_list}\n\n"
                "Run `/jig:migrate` to adopt jig over the existing layout, "
                "or preview the plan first with:\n"
                f"    python3 ${{CLAUDE_PLUGIN_ROOT}}/skills/migrate/migrate.py "
                f"report {target}\n\n"
                "Pass --force to scaffold over the existing structure "
                "anyway (NOT recommended — overwrites docs).",
                triggers,
            )

    # Detect signals BEFORE writing any scaffold files — otherwise wizard-generated
    # docs would self-trigger detectors (e.g. *.prompt.md, copilot-instructions.md).
    signals = detect_signals(target)
    if overrides is not None:
        signals = overrides.apply_to(signals)
    installed_tiers, offered_tiers = _select_tiers(signals)
    hook_profile = _hook_profile(signals)

    project_name = target.name
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Slice 046-02: derive the version from the plugin manifest (single
    # source of truth) here — before the first file write below — so a
    # missing/malformed manifest fails fast and leaves no partial scaffold.
    jig_version = _read_plugin_version(plugin)
    subs = {
        "PROJECT_NAME": project_name,
        "JIG_VERSION": jig_version,
        "TIMESTAMP": timestamp,
    }

    # Slice 046-01: in scaffold (in-repo) mode the runtime machinery is
    # copied to `target/.claude/skills/jig-*`, so rendered docs must point
    # at THOSE paths, not `${CLAUDE_PLUGIN_ROOT}/skills/...` (the env var is
    # unset in a scaffolded project). Reuse the exact transform SKILL.md
    # bodies already get (`_rewrite_skill_md_paths`). In `--plugin-only`
    # mode the machinery stays under the plugin root, so the plugin-root
    # path is correct and we pass no transform (None = leave docs verbatim).
    if host == "codex":
        doc_rewrite = (
            CodexScaffoldRenderer.rewrite_skill_md_paths
            if with_machinery else None
        )
    else:
        doc_rewrite = _rewrite_skill_md_paths if with_machinery else None

    # 1. Host primer from the top-level template.
    if host == "codex":
        copy_template(
            template_root / "AGENTS.md.template",
            target / "AGENTS.md",
            subs,
            post_render=doc_rewrite,
        )
    else:
        copy_template(template_root / "CLAUDE.md.template", target / "CLAUDE.md",
                      subs, post_render=doc_rewrite)

    # 2. docs/ structure from templates/docs/*.md.template (recursive).
    # people.md is conditional — generated only when team is detected.
    # The seed reference spec (templates/docs/specs/seed/, slice 048-05) is
    # excluded here and emitted separately by `_emit_seed_spec` so the
    # greenfield-only guard (Clarification Q1) can gate it.
    docs_template_root = template_root / "docs"
    seed_root = docs_template_root / "specs" / "seed"
    for src in docs_template_root.rglob("*.md.template"):
        if seed_root in src.parents:
            continue
        rel = src.relative_to(docs_template_root)
        dst_name = rel.with_suffix("")  # strip .template, leaves .md
        if dst_name.name == "people.md" and not signals.is_team:
            continue
        dst = target / "docs" / dst_name
        copy_template(src, dst, subs, post_render=doc_rewrite)

    # 2b. Slice 048-05: emit the seed reference spec (001-adopt-jig +
    # 002-first-spec stub + populated status board) into a greenfield
    # docs/specs/. Greenfield-only (Clarification Q1): skipped silently
    # when any spec already exists, so a migrate path / --force re-scaffold
    # never overwrites the user's work.
    _emit_seed_spec(template_root, target, subs)

    # 2c. Slice 050-01: an EXPLICIT `--solo` (overrides.is_team is False)
    # writes the tracked `.jig/no-people-md` opt-out marker so memory-sync's
    # team-recheck never re-nudges a deliberate solo project. Critically,
    # this fires ONLY on the explicit override — an *inferred* solo
    # (overrides absent, or is_team is None) must NOT write the marker, or a
    # solo-scaffolded project that later grows past one contributor would be
    # permanently suppressed (resolved OQ#3 — explicit-only).
    if overrides is not None and overrides.is_team is False:
        write_no_people_md_marker(target)

    # 3. Directories that should exist (even if empty for now)
    if host == "codex":
        (target / ".codex" / "hooks").mkdir(parents=True, exist_ok=True)
    else:
        (target / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)

    # 4. brief.md — human-readable summary of detection results
    brief_template = (template_root / "brief.md.template").read_text()
    brief = _render_brief(brief_template, signals, installed_tiers, offered_tiers, subs)
    atomic_write_text(target / "brief.md", brief)

    # 5. Slice 016-01 + 016-02: copy skills/, agents/, hook scripts, and
    # write/merge host hook configuration when --with-machinery is on
    # (default since 016-03). `force` propagates so that --force also
    # overrides the unmanaged-hooks safety check (same escape hatch as
    # AlreadyScaffoldedError). Slice 021-01 lifted the two-call sequence
    # behind a public `copy_machinery()` façade so `migrate.py
    # copy-machinery` can reuse the exact same logic without depending
    # on the underscored helpers.
    #
    # Slice 032-02: machinery copy runs BEFORE scaffold.json so that an
    # UnmanagedHooksError refusal leaves no scaffold.json behind — the
    # next run treats the directory as un-scaffolded and re-attempts
    # without `--force`.
    if with_machinery:
        # Slice 038-02: gate the on-disk skill set to the same tiers the
        # manifest records (installed_skills is derived from these per
        # ADR-0007), so disk == manifest.
        #
        # Slice 052-04: copy_machinery now also writes the secret-ignore
        # .gitignore floor (so `migrate copy-machinery` brings it too), which
        # covers the --with-machinery path here. The --plugin-only branch
        # below writes it directly since copy_machinery is not called there.
        copy_machinery(plugin, target, force=force,
                       installed_tiers=installed_tiers, host=host)
    else:
        # 5b. Slice 052-02 (ADR-0013): write/merge the secret-ignore
        # .gitignore floor on the --plugin-only path (with-machinery gets it
        # via copy_machinery above — slice 052-04). Runs BEFORE the
        # scaffold.json completion sentinel so a crash before the manifest
        # leaves a re-runnable partial state. Idempotent + append-not-clobber,
        # so --force re-scaffold and a pre-existing user .gitignore are safe.
        _write_gitignore_secret_block(target)
        # Spec 065-04: --with-machinery gets the convention block via
        # copy_machinery above; the --plugin-only path writes it here (the
        # docs/workflow.md template was already rendered earlier in scaffold()).
        _ensure_self_defining_convention_block(target)

    # 6. scaffold.json install-state manifest — the COMPLETION SENTINEL
    # (slice 032-02). Written LAST so a crash before this point leaves
    # no scaffold.json; the next run treats the partial state as
    # un-scaffolded and re-attempts. scaffold.py is the single source of
    # truth for installed_tiers — the template carries a placeholder.
    manifest_template = (template_root / "scaffold.json.template").read_text()
    rendered = render(manifest_template, subs)
    manifest = json.loads(rendered)
    manifest["installed_tiers"] = installed_tiers
    # ADR-0007 — derive the per-skill list from `installed_tiers` and the
    # `_TIER_SKILLS` table. Invariant:
    #   set(s.split("/")[0] for s in installed_skills) == set(installed_tiers)
    manifest["installed_skills"] = _enumerate_skills(installed_tiers)
    manifest["scaffold_signals"] = asdict(signals)
    manifest["hook_profile"] = hook_profile
    if offered_tiers:
        manifest["offered_tiers"] = offered_tiers
    # project_runtime is recorded only when the wizard explicitly captured an answer.
    # `is not None` rather than truthy — empty string "" is still an explicit answer
    # the wizard chose to record, not the same as "skipped".
    if overrides is not None and overrides.runtime is not None:
        manifest["project_runtime"] = overrides.runtime
    # Slice 016-01: record which install shape was used. "plugin-only"
    # leaves machinery under the installed plugin/runtime; "in-repo" is set
    # when machinery was copied into the target's host-local runtime.
    manifest["scaffold_mode"] = "in-repo" if with_machinery else "plugin-only"
    manifest["host_renderer"] = host
    atomic_write_text(
        target / "scaffold.json",
        json.dumps(manifest, indent=2) + "\n",
    )


def _build_parser() -> argparse.ArgumentParser:
    """CLI surface for scaffold.py — used both by main() and tests."""
    p = argparse.ArgumentParser(
        prog="scaffold.py",
        description="jig scaffold-init — generate an AI-native dev workspace",
    )
    p.add_argument("target", nargs="?", help="target directory")
    p.add_argument(
        "--host", choices=("claude", "codex"), default="claude",
        help="host scaffold renderer to use (default: claude)",
    )
    p.add_argument(
        "--install-codex-agents", action="store_true",
        help="install jig's Codex custom-agent TOML files and exit",
    )
    p.add_argument(
        "--codex-agents-dir",
        default="~/.codex/agents",
        help="target directory for --install-codex-agents",
    )
    p.add_argument("--force", action="store_true",
                   help="overwrite an already-scaffolded directory")
    # Slice 016-03 flipped the default ON. The two flags are mutually
    # exclusive: --with-machinery is now redundant (default) but kept for
    # documentation symmetry and back-compat with explicit slice 016-01/02
    # invocations; --plugin-only is the new opt-out for users who want the
    # old docs-only behavior.
    machinery = p.add_mutually_exclusive_group()
    machinery.add_argument(
        "--with-machinery", dest="with_machinery",
        action="store_true", default=True,
        help="copy skills/, agents/, and hooks/ into the target's host-local "
             "runtime so the dev owns and can edit the runtime artifacts "
             "(default-on as of slice 016-03; flag is now redundant but kept "
             "for symmetry)",
    )
    machinery.add_argument(
        "--plugin-only", dest="with_machinery",
        action="store_false",
        help="opt out of scaffold-mode: only scaffold docs/ and the host "
             "primer into the target; leave skills/ and agents/ under the "
             "installed plugin runtime (pre-016-03 default behavior)",
    )
    p.add_argument("--runtime", default=None,
                   help="runtime/language answer from the Q&A wizard "
                        "(stored in scaffold.json.project_runtime)")
    for flag_name, attr in [
        ("team", "is_team"),
        ("ci", "has_ci"),
        ("tests", "has_tests"),
        ("ai", "has_llm_agent_files"),
    ]:
        group = p.add_mutually_exclusive_group()
        if flag_name == "team":
            # --team / --solo (asymmetric)
            group.add_argument("--team", dest=attr, action="store_const", const=True,
                               help="force is_team=true (overrides git-author detection)")
            group.add_argument("--solo", dest=attr, action="store_const", const=False,
                               help="force is_team=false")
        elif flag_name == "ai":
            group.add_argument("--plans-ai", dest=attr, action="store_const", const=True,
                               help="force has_llm_agent_files=true (offers tier-2)")
            group.add_argument("--no-ai", dest=attr, action="store_const", const=False)
        else:
            group.add_argument(f"--has-{flag_name}", dest=attr,
                               action="store_const", const=True,
                               help=f"force has_{flag_name}=true")
            group.add_argument(f"--no-{flag_name}", dest=attr,
                               action="store_const", const=False)
    return p


def main(argv: list[str]) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        # argparse exits 2 on usage errors; bubble through
        return int(exc.code) if exc.code is not None else 2

    if ns.install_codex_agents:
        agents_dir = Path(ns.codex_agents_dir).expanduser()
        try:
            installed = install_codex_agents(
                plugin_root("codex"),
                agents_dir,
                force=ns.force,
            )
        except CodexAgentInstallConflictError as exc:
            sys.stderr.write(f"{exc}\n")
            return 3
        except Exception as exc:
            sys.stderr.write(f"codex agent install failed: {exc}\n")
            return 1
        print(f"installed {len(installed)} Codex agent(s) → {agents_dir}")
        return 0

    if not ns.target:
        parser.error("target is required unless --install-codex-agents is used")

    target = Path(ns.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    overrides = Overrides(
        is_team=ns.is_team,
        has_ci=ns.has_ci,
        has_tests=ns.has_tests,
        has_llm_agent_files=ns.has_llm_agent_files,
        runtime=ns.runtime,
    )

    # Slice 048-06: capture seed-eligibility BEFORE scaffold() writes the
    # seed. The worked-example seed (slice 048-05) is greenfield-only — it
    # is emitted only when docs/specs/ had no prior spec content. We sample
    # that condition now so the post-scaffold completion verification can
    # tell "seed missing because the scaffold dropped it" (a failure) apart
    # from "seed legitimately skipped because the project wasn't greenfield"
    # (not a failure).
    seed_expected = not _specs_dir_has_content(target)

    try:
        scaffold(target, plugin_root(ns.host), force=ns.force, overrides=overrides,
                 with_machinery=ns.with_machinery, host=ns.host)
    except AlreadyScaffoldedError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except LooksAlreadySpecDrivenError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except UnmanagedHooksError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except Exception as exc:
        sys.stderr.write(f"scaffold failed: {exc}\n")
        return 1

    print(f"scaffolded {target.name} → {target}")

    if ns.host == "codex":
        return 0

    # Slice 048-06: run the scaffold-completion verification as the closing
    # report. Reuses verify_install.py's scaffold-mode checks (AC #2) — no
    # second definition of "a complete scaffold". A failed check makes the
    # exit status unmistakable (AC #4): we surface a non-zero exit so the
    # wizard never reports a silent partial scaffold as success.
    #
    # The verifier modules (verify_install + install_contract +
    # scaffold_contract) live under `scripts/`, which is dev-only EXCEPT for
    # these three — `build_release_zip.py::_INCLUDE_SCRIPT_FILES` re-includes
    # them so they ship in the plugin install (they were absent before, which
    # crashed this self-check on every packaged install). The import is still
    # guarded: if a future packaging regression drops them, the *scaffold has
    # already succeeded and printed* above — degrade to a one-line notice
    # rather than crashing on the closing report. A genuine verification
    # FAIL (verdict != 0) is NOT swallowed; only a missing verifier is.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    try:
        import verify_install  # noqa: E402
    except ImportError:
        print(
            "note: scaffold-completion self-check skipped "
            "(verifier not bundled in this install)"
        )
        return 0

    verdict = verify_install.run_completion_summary(
        target,
        with_machinery=ns.with_machinery,
        seed_expected=seed_expected,
    )
    if verdict != 0:
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
