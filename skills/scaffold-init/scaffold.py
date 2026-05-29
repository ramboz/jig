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
import hashlib
import json
import os
import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common.atomic_io import atomic_write_text


# Schema version for scaffold.json
JIG_VERSION = "0.1.0"
MANAGED_FILES_SCHEMA_VERSION = 1

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
    ],
    "tier-2": [],  # no Tier 2 skills land in jig yet
}


def plugin_root(host: str = "claude") -> Path:
    """Locate the jig runtime root for the selected scaffold host."""
    if host == "claude":
        env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if env_root:
            return Path(env_root).resolve()
    # Fallback: scaffold.py lives at <plugin-root>/skills/scaffold-init/scaffold.py
    # for the source/Claude tree and at <project>/.codex/skills/jig-scaffold-init/
    # scaffold.py for a Codex-scaffolded runtime.
    return Path(__file__).resolve().parents[2]


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


def copy_template(src: Path, dst: Path, substitutions: dict) -> None:
    """Read a `.template` file, render placeholders, write to dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rendered = render(src.read_text(), substitutions)
    atomic_write_text(dst, rendered)


class AlreadyScaffoldedError(RuntimeError):
    """Raised when target already has a scaffold.json — refuses to overwrite."""


class UnmanagedHooksError(RuntimeError):
    """Raised by slice 016-02 when `.claude/settings.json` already exists with
    hooks present, but no jig-managed marker on any of them. Same safety
    stance as AlreadyScaffoldedError — refuses to merge silently. `--force`
    is the documented escape hatch."""


class ExistingPrimerError(RuntimeError):
    """Raised when target has user-owned primer instructions that scaffold
    would otherwise overwrite."""


class ManagedFileConflictError(RuntimeError):
    """Raised when a managed file was edited since the last scaffold run."""


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
# jig-partial state (crashed mid-scaffold, no scaffold.json) from a
# user's pre-existing project instructions. Slice 032-02: used by
# `_is_jig_partial_state` to short-circuit `_looks_already_spec_driven`
# during recovery from an interrupted scaffold.
_JIG_CLAUDE_MD_WATERMARK = "> Generated by [jig]("


def _has_jig_watermark(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        with path.open(encoding="utf-8", errors="ignore") as fh:
            head = fh.read(4096)
        return any(
            line.startswith(_JIG_CLAUDE_MD_WATERMARK)
            for line in head.splitlines()
        )
    except OSError:
        return False


def _is_jig_partial_state(target: Path) -> bool:
    """Return True iff `target` looks like a previously-interrupted jig
    scaffold (a primer exists with the jig watermark, but scaffold.json
    is absent). Slice 032-02: distinguishes a crashed mid-scaffold from
    a user's pre-existing spec-driven project, so the recovery re-run
    can proceed without `--force`.

    Reads primer files best-effort — any I/O failure returns False (the
    safer side: if we can't confirm a jig watermark, fall through to
    `_looks_already_spec_driven` and route to /jig:migrate)."""
    return (
        _has_jig_watermark(target / "AGENTS.md")
        or _has_jig_watermark(target / "CLAUDE.md")
    )


def _check_primer_safety(
    target: Path, *, force: bool = False,
    primer_names: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md"),
) -> None:
    for name in primer_names:
        primer = target / name
        if not primer.exists():
            continue
        if force or _has_jig_watermark(primer):
            continue
        raise ExistingPrimerError(
            f"{primer} already exists and does not look jig-managed - "
            "refusing to overwrite project-owned agent instructions. "
            "Move or merge the file first, or pass --force to overwrite."
        )


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


@dataclass(frozen=True)
class ManagedFileSpec:
    """One scaffold-managed file to record in scaffold.json."""

    path: str
    source: str
    host_renderer: str
    metadata: str = "scaffold.json"


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _managed_file_policy() -> dict:
    return {
        "default": "manifest-only",
        "inline_markers": [
            {
                "path": ".claude/settings.json",
                "marker": "hooks.*.metadata.managed_by_jig",
                "reason": "Claude hook merge safety needs per-entry ownership.",
            },
            {
                "path": ".codex/hooks.json",
                "marker": "metadata.managed_by_jig",
                "reason": "Codex hook safety uses a top-level ownership marker.",
            }
        ],
        "conflict_behavior": (
            "force reruns refuse when an existing managed file's content_hash "
            "differs from scaffold.json; missing managed files may be "
            "regenerated"
        ),
    }


def _resolve_managed_path(target: Path, rel_path: str) -> Path | None:
    candidate = (target / rel_path).resolve()
    try:
        candidate.relative_to(target.resolve())
    except ValueError:
        return None
    return candidate


def _managed_file_entry(target: Path, spec: ManagedFileSpec) -> dict | None:
    path = _resolve_managed_path(target, spec.path)
    if path is None or not path.is_file():
        return None
    return {
        "path": spec.path,
        "source": spec.source,
        "jig_version": JIG_VERSION,
        "host_renderer": spec.host_renderer,
        "metadata": spec.metadata,
        "content_hash": _sha256_file(path),
    }


def _managed_files_manifest(target: Path,
                            specs: list[ManagedFileSpec]) -> dict:
    by_path: dict[str, dict] = {}
    for spec in specs:
        entry = _managed_file_entry(target, spec)
        if entry is not None:
            by_path[entry["path"]] = entry
    return {
        "schema_version": MANAGED_FILES_SCHEMA_VERSION,
        "policy": _managed_file_policy(),
        "files": [by_path[path] for path in sorted(by_path)],
    }


def _check_managed_file_conflicts(target: Path, manifest: dict) -> None:
    managed = manifest.get("managed_files") or {}
    files = managed.get("files") if isinstance(managed, dict) else []
    conflicts = []
    for entry in files or []:
        rel_path = entry.get("path")
        expected = entry.get("content_hash")
        if not rel_path or not expected:
            continue
        path = _resolve_managed_path(target, rel_path)
        if path is None or not path.exists():
            continue
        if not path.is_file():
            conflicts.append(rel_path)
            continue
        actual = _sha256_file(path)
        if actual != expected:
            conflicts.append(rel_path)
    if conflicts:
        formatted = "\n  - ".join(sorted(conflicts))
        raise ManagedFileConflictError(
            "managed file changed since the last scaffold run; refusing to "
            "overwrite edited generated output:\n"
            f"  - {formatted}\n\n"
            "Move or merge the edit before re-running scaffold with --force."
        )


def _detect_llm_agent(target: Path) -> bool:
    """High-confidence signals only — see Spike 001a."""
    # File / directory presence at root
    agents_md = target / "AGENTS.md"
    if agents_md.is_file() and not _has_jig_watermark(agents_md):
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
    """True iff `git log` in target shows ≥2 unique author emails.
    Solo is the safe default — returns False on non-git dirs, missing binary,
    any git failure, or when target is inside a parent repo (avoids monorepo
    misdetection: scaffolding a fresh subdir of a multi-author repo would
    otherwise count the parent's authors).
    Uses `--use-mailmap` so one person with multiple emails counts once."""
    try:
        # Refuse to climb to a parent repo: target itself must be the repo root.
        toplevel = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if toplevel.returncode != 0:
            return False
        if Path(toplevel.stdout.strip()).resolve() != Path(target).resolve():
            return False

        out = subprocess.run(
            ["git", "-C", str(target), "log", "--use-mailmap", "--format=%aE"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return False
    if out.returncode != 0:
        return False
    authors = {line.strip().lower() for line in out.stdout.splitlines() if line.strip()}
    return len(authors) >= 2


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
    """Host adapter boundary for scaffold-mode materialization.

    The shared scaffold flow owns signal detection, docs rendering, brief
    rendering, and scaffold manifest writing. A renderer owns the logical
    adapter operations documented in spec 033: primers, skills, agents,
    hooks, hook protocol translation, path binding, managed metadata, and
    verification fixtures.
    """

    name = "host"

    def __init__(self, plugin: Path, target: Path, *, force: bool = False):
        self.plugin = plugin
        self.target = target
        self.force = force

    @abstractmethod
    def render_primers(self, template_root: Path, substitutions: dict) -> None:
        raise NotImplementedError

    @abstractmethod
    def prepare_project_dirs(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_skills(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_agents(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def install_hooks(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def translate_hook_protocol(self, logical_result: dict) -> dict:
        raise NotImplementedError

    @abstractmethod
    def bind_paths(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def managed_file_metadata(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def primer_managed_file_specs(self) -> list[ManagedFileSpec]:
        raise NotImplementedError

    @abstractmethod
    def runtime_managed_file_specs(self) -> list[ManagedFileSpec]:
        raise NotImplementedError

    @abstractmethod
    def verification_fixtures(self) -> dict:
        raise NotImplementedError

    def install_runtime(self) -> None:
        self.prepare_project_dirs()
        self.install_skills()
        self.install_agents()
        self.install_hooks()


class ClaudeScaffoldRenderer(HostRenderer):
    """Claude Code scaffold renderer.

    This is the only place that knows Claude's scaffold paths:
    `.claude/skills/`, `.claude/agents/`, `.claude/hooks/scripts/`, and
    `.claude/settings.json`.
    """

    name = "claude"

    # Pattern: ${CLAUDE_PLUGIN_ROOT}/skills/<name>/ — captures <name>.
    # Bash `${...}` syntax in SKILL.md bash recipes is the only place this
    # token appears. The substitution rewrites every such occurrence to the
    # project-scoped Claude equivalent.
    SKILL_PATH_RE = re.compile(
        r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/([A-Za-z0-9_-]+)/"
    )
    SKILL_PATH_REPLACEMENT = (
        r"${CLAUDE_PROJECT_DIR}/.claude/skills/jig-\1/"
    )

    SKILL_DIR_EXCLUDES: frozenset[str] = frozenset({"__pycache__", "fixtures"})

    # Per-skill allow-list of `test_*.py` files to RETAIN despite the general
    # "test files are not shipped to scaffolded projects" rule. Keyed by the
    # source skill directory name (the directory under `skills/`, NOT the
    # `jig-`-prefixed scaffolded destination name).
    RETAINED_TEST_FILES: dict[str, frozenset[str]] = {
        "tdd-loop": frozenset({"test_quality.py"}),
    }

    HOOK_MARKER = {"managed_by_jig": True}
    PLUGIN_HOOK_SCRIPT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/"
    PROJECT_HOOK_SCRIPT_PREFIX = (
        "${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/"
    )

    def render_primers(self, template_root: Path, substitutions: dict) -> None:
        copy_template(
            template_root / "AGENTS.md.template",
            self.target / "AGENTS.md",
            substitutions,
        )
        copy_template(
            template_root / "CLAUDE.md.template",
            self.target / "CLAUDE.md",
            substitutions,
        )

    def prepare_project_dirs(self) -> None:
        (self.target / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)

    def install_runtime(self) -> None:
        self.check_hooks_safety()
        self.prepare_project_dirs()
        self.install_skills()
        self.install_agents()
        self.install_hooks()

    def install_skills(self) -> None:
        """Install Claude project-scoped skills.

        Copies `plugin/skills/<name>/` to
        `target/.claude/skills/jig-<name>/`. Private `_`-prefixed shared
        modules are copied unprefixed under `.claude/skills/`.
        """
        skills_src = self.plugin / "skills"
        skills_dst = self.target / ".claude" / "skills"

        if skills_src.is_dir():
            skills_dst.mkdir(parents=True, exist_ok=True)
            for skill_dir in sorted(skills_src.iterdir()):
                if not skill_dir.is_dir():
                    continue
                if skill_dir.name.startswith("_"):
                    # Private shared module — copy unprefixed so the
                    # helpers' `from _<name>.x import ...` resolves.
                    self.copy_skill_dir(skill_dir, skills_dst / skill_dir.name)
                    continue
                if not (skill_dir / "SKILL.md").is_file():
                    continue
                dst_dir = skills_dst / f"jig-{skill_dir.name}"
                self.copy_skill_dir(skill_dir, dst_dir)

    def install_agents(self) -> None:
        """Install Claude project-scoped agents."""
        agents_src = self.plugin / "agents"
        agents_dst = self.target / ".claude" / "agents"

        if agents_src.is_dir():
            agents_dst.mkdir(parents=True, exist_ok=True)
            for agent in sorted(agents_src.glob("*.md")):
                dst = agents_dst / f"jig-{agent.name}"
                dst.write_bytes(agent.read_bytes())

    def copy_skills_and_agents(self) -> None:
        """Compatibility helper for the old combined Claude install step."""
        self.install_skills()
        self.install_agents()

    @classmethod
    def rewrite_skill_md_paths(cls, body: str) -> str:
        """Rewrite Claude plugin skill paths to Claude project skill paths."""
        return cls.SKILL_PATH_RE.sub(cls.SKILL_PATH_REPLACEMENT, body)

    @classmethod
    def skill_source_files(cls, src: Path) -> list[Path]:
        """Return the files from a source skill directory that ship."""
        retained = cls.RETAINED_TEST_FILES.get(src.name, frozenset())
        files: list[Path] = []
        for entry in src.rglob("*"):
            rel = entry.relative_to(src)
            if any(part in cls.SKILL_DIR_EXCLUDES for part in rel.parts):
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

    def copy_skill_dir(self, src: Path, dst: Path) -> None:
        """Copy one skill directory with Claude-specific path rewriting."""
        dst.mkdir(parents=True, exist_ok=True)
        for entry in self.skill_source_files(src):
            rel = entry.relative_to(src)
            target_path = dst / rel
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if entry.name == "SKILL.md":
                text = entry.read_text()
                fm, body = _split_frontmatter(text)
                rewritten = fm + self.rewrite_skill_md_paths(body)
                atomic_write_text(target_path, rewritten)
            else:
                target_path.write_bytes(entry.read_bytes())

    @classmethod
    def rewrite_hook_command(cls, command: str) -> str:
        """Rewrite Claude plugin hook script dispatch to project-local path."""
        return command.replace(
            cls.PLUGIN_HOOK_SCRIPT_PREFIX,
            cls.PROJECT_HOOK_SCRIPT_PREFIX,
        )

    def build_hook_entries(self) -> dict:
        """Build Claude Code `.claude/settings.json` hook entries."""
        source = json.loads((self.plugin / "hooks" / "hooks.json").read_text())
        out: dict = {}
        for event, entries in (source.get("hooks") or {}).items():
            new_entries = []
            for entry in entries:
                new_inner = []
                for h in entry.get("hooks", []):
                    rewritten = dict(h)
                    if "command" in rewritten:
                        rewritten["command"] = self.rewrite_hook_command(
                            rewritten["command"]
                        )
                    new_inner.append(rewritten)
                new_entry = {}
                if "matcher" in entry:
                    new_entry["matcher"] = entry["matcher"]
                new_entry["hooks"] = new_inner
                new_entry["metadata"] = dict(self.HOOK_MARKER)
                new_entries.append(new_entry)
            out[event] = new_entries
        return out

    @classmethod
    def merge_settings(cls, existing: dict, jig_hooks: dict) -> dict:
        """Merge jig's hook registration into a Claude settings dict."""
        merged: dict = dict(existing) if existing else {}
        hooks = dict(merged.get("hooks") or {})
        for event, fresh_entries in jig_hooks.items():
            current = hooks.get(event) or []
            survivors = [e for e in current if not _is_jig_managed(e)]
            hooks[event] = survivors + fresh_entries
        merged["hooks"] = hooks
        return merged

    def check_hooks_safety(self) -> dict:
        """Refuse to merge into unmanaged Claude hook settings unless forced."""
        settings_path = self.target / ".claude" / "settings.json"
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
        if has_any_hook and not has_jig_marker and not self.force:
            raise UnmanagedHooksError(
                f"{settings_path} already has hooks but none carry the "
                "jig-managed marker — refusing to merge to avoid clobbering "
                "third-party hook configuration. Pass --force to append "
                "jig hooks alongside the existing entries, or remove the "
                "file and re-run."
            )
        return existing

    def install_hooks(self) -> None:
        """Install Claude hook scripts and `.claude/settings.json`."""
        src_scripts = self.plugin / "hooks" / "scripts"
        settings_path = self.target / ".claude" / "settings.json"

        existing = self.check_hooks_safety()

        dst_scripts = self.target / ".claude" / "hooks" / "scripts"
        dst_scripts.mkdir(parents=True, exist_ok=True)
        if src_scripts.is_dir():
            for script in sorted(src_scripts.glob("jig-*.sh")):
                dst = dst_scripts / script.name
                dst.write_bytes(script.read_bytes())
                os.chmod(dst, 0o755)

            src_lib = src_scripts / "lib"
            if src_lib.is_dir():
                dst_lib = dst_scripts / "lib"
                dst_lib.mkdir(exist_ok=True)
                for py in sorted(src_lib.glob("*.py")):
                    if py.name.startswith("test_"):
                        continue
                    (dst_lib / py.name).write_bytes(py.read_bytes())

        jig_hooks = self.build_hook_entries()
        merged = self.merge_settings(existing, jig_hooks)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(settings_path, json.dumps(merged, indent=2) + "\n")

    def copy_hooks_and_register(self) -> None:
        """Compatibility helper for the old Claude hook install step."""
        self.install_hooks()

    def translate_hook_protocol(self, logical_result: dict) -> dict:
        """Translate jig-level hook result keys to Claude hook protocol.

        Claude warning hooks emit JSON with `additionalContext`; blocking
        hooks communicate refusal by printing a reason to stderr and exiting
        with status 2.
        """
        translated: dict = {}
        if "continue" in logical_result:
            translated["continue"] = logical_result["continue"]
        if "additional_context" in logical_result:
            translated["additionalContext"] = logical_result[
                "additional_context"
            ]
        if "block_reason" in logical_result:
            translated["exit_code"] = 2
            translated["stderr"] = logical_result["block_reason"]
        return translated

    def bind_paths(self) -> dict[str, str]:
        """Expose Claude's project/runtime path bindings."""
        return {
            "project_root_env": "CLAUDE_PROJECT_DIR",
            "runtime_root": "${CLAUDE_PROJECT_DIR}/.claude",
            "plugin_root_env": "CLAUDE_PLUGIN_ROOT",
        }

    def managed_file_metadata(self) -> dict:
        """Expose Claude metadata markers currently used by scaffold mode."""
        return {
            "policy": _managed_file_policy(),
            "hook_entry": dict(self.HOOK_MARKER),
        }

    def primer_managed_file_specs(self) -> list[ManagedFileSpec]:
        return [
            ManagedFileSpec(
                "AGENTS.md", "templates/AGENTS.md.template", self.name,
            ),
            ManagedFileSpec(
                "CLAUDE.md", "templates/CLAUDE.md.template", self.name,
            ),
        ]

    def runtime_managed_file_specs(self) -> list[ManagedFileSpec]:
        specs: list[ManagedFileSpec] = []

        skills_src = self.plugin / "skills"
        skills_dst = self.target / ".claude" / "skills"
        if skills_src.is_dir():
            for skill_dir in sorted(skills_src.iterdir()):
                if not skill_dir.is_dir():
                    continue
                if skill_dir.name.startswith("_"):
                    dst_dir = skills_dst / skill_dir.name
                else:
                    if not (skill_dir / "SKILL.md").is_file():
                        continue
                    dst_dir = skills_dst / f"jig-{skill_dir.name}"
                for src_file in self.skill_source_files(skill_dir):
                    rel = src_file.relative_to(skill_dir)
                    specs.append(ManagedFileSpec(
                        (dst_dir / rel).relative_to(self.target).as_posix(),
                        src_file.relative_to(self.plugin).as_posix(),
                        self.name,
                    ))

        agents_src = self.plugin / "agents"
        agents_dst = self.target / ".claude" / "agents"
        if agents_src.is_dir():
            for agent in sorted(agents_src.glob("*.md")):
                dst = agents_dst / f"jig-{agent.name}"
                specs.append(ManagedFileSpec(
                    dst.relative_to(self.target).as_posix(),
                    agent.relative_to(self.plugin).as_posix(),
                    self.name,
                ))

        src_scripts = self.plugin / "hooks" / "scripts"
        scripts_dst = self.target / ".claude" / "hooks" / "scripts"
        if src_scripts.is_dir():
            for script in sorted(src_scripts.glob("jig-*.sh")):
                dst = scripts_dst / script.name
                specs.append(ManagedFileSpec(
                    dst.relative_to(self.target).as_posix(),
                    script.relative_to(self.plugin).as_posix(),
                    self.name,
                ))
            src_lib = src_scripts / "lib"
            if src_lib.is_dir():
                for py in sorted(src_lib.glob("*.py")):
                    if py.name.startswith("test_"):
                        continue
                    dst = scripts_dst / "lib" / py.name
                    specs.append(ManagedFileSpec(
                        dst.relative_to(self.target).as_posix(),
                        py.relative_to(self.plugin).as_posix(),
                        self.name,
                    ))

        settings = self.target / ".claude" / "settings.json"
        if settings.is_file():
            specs.append(ManagedFileSpec(
                settings.relative_to(self.target).as_posix(),
                "hooks/hooks.json",
                self.name,
            ))

        return specs

    def verification_fixtures(self) -> dict:
        """Expose the stable Claude generated-tree fixture surface."""
        return {
            "primers": ["AGENTS.md", "CLAUDE.md"],
            "skills_dir": ".claude/skills",
            "agents_dir": ".claude/agents",
            "hook_scripts_glob": ".claude/hooks/scripts/jig-*.sh",
            "settings": ".claude/settings.json",
        }


class CodexScaffoldRenderer(ClaudeScaffoldRenderer):
    """Codex scaffold renderer.

    Current Codex project-local surfaces use `AGENTS.md` for primer
    instructions, Markdown agent prompts, and JSON hook registration. The
    renderer keeps runtime artifacts under `.codex/` so a Codex scaffold can
    be generated without also creating Claude-only files.
    """

    name = "codex"
    SKILL_PATH_REPLACEMENT = (
        r"${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-\1/"
    )
    PROJECT_HOOK_SCRIPT_PREFIX = "${CODEX_PROJECT_DIR:-$PWD}/.codex/hooks/scripts/"
    CODEX_HOOK_MARKER = {"managed_by_jig": True}

    CODEX_AGENT_NOTE = (
        "# jig {name} agent\n\n"
        "Codex adapter note: this file describes the intended jig agent "
        "role for Codex. Codex cannot enforce the same per-agent tool "
        "isolation declared by Claude frontmatter here; treat those "
        "capabilities as operating instructions, and rely on the active "
        "Codex thread/subagent runtime for actual enforcement.\n\n"
    )

    def render_primers(self, template_root: Path, substitutions: dict) -> None:
        copy_template(
            template_root / "AGENTS.md.template",
            self.target / "AGENTS.md",
            substitutions,
        )

    def prepare_project_dirs(self) -> None:
        for rel in (
            ".codex/skills",
            ".codex/agents",
            ".codex/hooks/scripts",
            ".codex/templates",
        ):
            (self.target / rel).mkdir(parents=True, exist_ok=True)

    def install_runtime(self) -> None:
        self.check_hooks_safety()
        self.prepare_project_dirs()
        self.install_templates()
        self.install_skills()
        self.install_skill_compatibility_aliases()
        self.install_agents()
        self.install_hooks()

    def install_templates(self) -> None:
        templates_src = self.plugin / "templates"
        templates_dst = self.target / ".codex" / "templates"

        if templates_src.is_dir():
            templates_dst.mkdir(parents=True, exist_ok=True)
            for entry in sorted(templates_src.rglob("*")):
                if entry.is_dir():
                    continue
                rel = entry.relative_to(templates_src)
                dst = templates_dst / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(entry.read_bytes())

    def install_skills(self) -> None:
        skills_src = self.plugin / "skills"
        skills_dst = self.target / ".codex" / "skills"

        if skills_src.is_dir():
            skills_dst.mkdir(parents=True, exist_ok=True)
            for skill_dir in sorted(skills_src.iterdir()):
                if not skill_dir.is_dir():
                    continue
                if skill_dir.name.startswith("_"):
                    self.copy_skill_dir(skill_dir, skills_dst / skill_dir.name)
                    continue
                if not (skill_dir / "SKILL.md").is_file():
                    continue
                self.copy_skill_dir(
                    skill_dir,
                    skills_dst / self.codex_skill_dir_name(skill_dir.name),
                )

    def install_skill_compatibility_aliases(self) -> None:
        """Install non-discoverable unprefixed helper aliases.

        Some existing helpers self-locate through `<runtime>/skills/<name>/...`
        when loaded from a materialized runtime. Codex's discoverable skill
        directories stay `jig-<name>`, so these aliases intentionally omit
        `SKILL.md` to provide helper paths without registering duplicate
        skills.
        """
        skills_src = self.plugin / "skills"
        skills_dst = self.target / ".codex" / "skills"
        if not skills_src.is_dir():
            return
        for skill_dir in sorted(skills_src.iterdir()):
            if (
                not skill_dir.is_dir()
                or skill_dir.name.startswith("_")
                or not (skill_dir / "SKILL.md").is_file()
            ):
                continue
            alias_dir = skills_dst / self.original_skill_dir_name(skill_dir.name)
            copied_any = False
            for entry in self.skill_source_files(skill_dir):
                if entry.name == "SKILL.md":
                    continue
                rel = entry.relative_to(skill_dir)
                target_path = alias_dir / rel
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_bytes(entry.read_bytes())
                copied_any = True
            if copied_any:
                continue
            if alias_dir.exists() and not any(alias_dir.iterdir()):
                alias_dir.rmdir()

    @staticmethod
    def codex_skill_dir_name(name: str) -> str:
        return name if name.startswith("jig-") else f"jig-{name}"

    @staticmethod
    def original_skill_dir_name(name: str) -> str:
        return name.removeprefix("jig-")

    @classmethod
    def rewrite_skill_md_paths(cls, body: str) -> str:
        body = body.replace(
            "- `CLAUDE.md` (Claude Code adapter that imports `AGENTS.md`)\n",
            "",
        )
        body = body.replace(" or `CLAUDE.md`", "")
        body = body.replace(
            ", and\n  `templates/CLAUDE.md.template` is the Claude adapter",
            "",
        )
        out = cls.SKILL_PATH_RE.sub(cls.SKILL_PATH_REPLACEMENT, body)
        out = out.replace(
            "${CLAUDE_PLUGIN_ROOT}/templates/",
            "${CODEX_PROJECT_DIR:-$PWD}/.codex/templates/",
        )
        out = out.replace(
            "${CLAUDE_PLUGIN_ROOT}",
            "${CODEX_PROJECT_DIR:-$PWD}/.codex",
        )
        out = out.replace(
            "${CLAUDE_PROJECT_DIR}",
            "${CODEX_PROJECT_DIR:-$PWD}",
        )
        out = out.replace("CLAUDE_PLUGIN_ROOT", "CODEX_PROJECT_DIR")
        out = out.replace("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")
        out = out.replace(".claude/", ".codex/")
        out = out.replace("CLAUDE.md", "AGENTS.md")
        out = out.replace("Claude Code", "Codex")
        out = out.replace("Claude", "Codex")
        out = cls.restore_claude_only_migrate_copy_machinery(out)
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
    def restore_claude_only_migrate_copy_machinery(body: str) -> str:
        """Keep migrate copy-machinery honest in Codex skill prose.

        The operation delegates to Claude scaffold machinery today. The rest
        of migrate remains useful in Codex, but this subcommand must not be
        blanket-rewritten into a Codex contract.
        """
        if "copy-machinery" not in body:
            return body
        out = body
        if "name: migrate" in out:
            out = out.replace(
                "user-invocable: true\n---\n",
                "user-invocable: true\n---\n\n"
                "> Codex adapter note: `report`, `rename-decisions`, and "
                "`split-slices` run from the copied Codex helper path. "
                "`copy-machinery` remains Claude-only until migrate grows a "
                "host-aware machinery-copy path. Cross-reference rewrites in "
                "`rename-decisions` still use the helper's Claude-shaped "
                "scan scope.\n",
                1,
            )
        out = out.replace(
            "added `copy-machinery` (copy jig's skills + agents + hooks +\n"
            "  settings.json into the target's `.codex/`, reusing scaffold-mode's\n"
            "  helpers).",
            "added `copy-machinery` (Claude-only: copy jig's skills + agents "
            "+ hooks +\n  settings.json into the target's `.claude/`, "
            "reusing Claude scaffold-mode's\n  helpers).",
        )
        out = out.replace(
            "the same `.codex/` shape `/jig:scaffold-init` produces by default for\n"
            "greenfield projects (per spec 016-03).",
            "the same `.claude/` shape Claude `/jig:scaffold-init` produces "
            "by default for\ngreenfield projects (per spec 016-03). "
            "In Codex-scaffolded installs this subcommand is still "
            "Claude-only.",
        )
        out = out.replace(
            "installed plugin under `${CODEX_PROJECT_DIR:-$PWD}/.codex`",
            "installed plugin under `${CLAUDE_PLUGIN_ROOT}`",
        )
        out = out.replace(
            "when the verdict is `adoptable` or `partial` AND the target's\n"
            "`.codex/skills/` has no pre-existing `jig-*` skill dir.",
            "when the verdict is `adoptable` or `partial` AND the target's\n"
            "`.claude/skills/` has no pre-existing `jig-*` skill dir.",
        )
        out = out.replace(
            "```bash\n"
            'python3 "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-migrate/migrate.py" \\\n'
            "  copy-machinery <project-dir>\n"
            "```",
            "```bash\n"
            "# Claude-only operation; requires an installed Claude jig plugin.\n"
            'python3 "${CLAUDE_PLUGIN_ROOT}/skills/migrate/migrate.py" \\\n'
            "  copy-machinery <project-dir>\n"
            "```",
        )
        out = out.replace(
            "```bash\n"
            'python3 "${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-migrate/migrate.py" \\\n'
            "  copy-machinery <project-dir> --force\n"
            "```",
            "```bash\n"
            "# Claude-only operation; requires an installed Claude jig plugin.\n"
            'python3 "${CLAUDE_PLUGIN_ROOT}/skills/migrate/migrate.py" \\\n'
            "  copy-machinery <project-dir> --force\n"
            "```",
        )
        out = out.replace(
            "Cross-reference rewrites in text files under `docs/`, `AGENTS.md`,\n"
            "   and `.codex/`.",
            "Cross-reference rewrites in text files under `docs/`, `CLAUDE.md`,\n"
            "   and `.claude/` (Claude-shaped scan scope; Codex host-aware\n"
            "   cross-reference rewriting is not implemented yet).",
        )
        out = out.replace(
            "`AGENTS.md` is",
            "`CLAUDE.md` is",
        )
        out = out.replace(
            '"AGENTS.md is',
            '"CLAUDE.md is',
        )
        out = out.replace(
            "| `AGENTS.md` |",
            "| `CLAUDE.md` |",
        )
        out = out.replace(
            "- **AGENTS.md references to old slice paths are NOT rewritten.**",
            "- **CLAUDE.md references to old slice paths are NOT rewritten.**",
        )
        out = out.replace(
            "- **AGENTS.md size is reported as a tripwire, not migrated.**",
            "- **CLAUDE.md size is reported as a tripwire, not migrated.**",
        )
        out = out.replace(
            "in\n  AGENTS.md / milestone summaries / etc.",
            "in\n  CLAUDE.md / milestone summaries / etc.",
        )
        out = out.replace(
            "Within\n  scope it only touches `docs/`, `AGENTS.md`, and `.codex/`;",
            "Within\n  scope it only touches `docs/`, `CLAUDE.md`, and `.claude/`;",
        )
        out = out.replace(
            "The\n  validator's 59KB AGENTS.md",
            "The\n  validator's 59KB CLAUDE.md",
        )
        out = out.replace(
            "- **The report scans `docs/` and `.codex/` only.**",
            "- **The report scans `docs/` and `.claude/` only.**",
        )
        out = out.replace(
            "Importing AGENTS.md content into jig's Hot Cache template.",
            "Importing CLAUDE.md content into jig's Hot Cache template.",
        )
        out = out.replace(
            "1. Copies `<plugin-root>/skills/<name>/` → `<project>/.codex/skills/\n"
            "   jig-<name>/`, rewriting every plugin-root path string in SKILL.md\n"
            "   bodies to the `${CODEX_PROJECT_DIR:-$PWD}/.codex/skills/jig-<name>/`\n"
            "   equivalent.",
            "1. Copies `<plugin-root>/skills/<name>/` → `<project>/.claude/skills/\n"
            "   jig-<name>/`, rewriting every plugin-root path string in SKILL.md\n"
            "   bodies to the `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/`\n"
            "   equivalent.",
        )
        out = out.replace(
            "2. Copies `<plugin-root>/agents/*.md` →\n"
            "   `<project>/.codex/agents/jig-*.md` byte-identically.",
            "2. Copies `<plugin-root>/agents/*.md` →\n"
            "   `<project>/.claude/agents/jig-*.md` byte-identically.",
        )
        out = out.replace(
            "3. Copies `<plugin-root>/hooks/scripts/jig-*.sh` →\n"
            "   `<project>/.codex/hooks/scripts/`, pinning each script's mode to",
            "3. Copies `<plugin-root>/hooks/scripts/jig-*.sh` →\n"
            "   `<project>/.claude/hooks/scripts/`, pinning each script's mode to",
        )
        out = out.replace(
            "4. Generates or merges `<project>/.codex/settings.json` with hook\n"
            "   entries registered against `${CODEX_PROJECT_DIR:-$PWD}/.codex/hooks/\n"
            "   scripts/jig-*.sh` paths.",
            "4. Generates or merges `<project>/.claude/settings.json` with hook\n"
            "   entries registered against `${CLAUDE_PROJECT_DIR}/.claude/hooks/\n"
            "   scripts/jig-*.sh` paths.",
        )
        out = out.replace(
            "If `.codex/settings.json` already exists",
            "If `.claude/settings.json` already exists",
        )
        out = out.replace(
            "the resulting `.codex/` shape is\nbyte-identical",
            "the resulting `.claude/` shape is\nbyte-identical",
        )
        out = out.replace(
            "machinery under `${CODEX_PROJECT_DIR:-$PWD}/.codex/`",
            "machinery under `${CLAUDE_PROJECT_DIR}/.claude/`",
        )
        out = out.replace(
            "machinery under\n`${CODEX_PROJECT_DIR:-$PWD}/.codex`",
            "machinery under\n`${CLAUDE_PLUGIN_ROOT}`",
        )
        return out

    def copy_skill_dir(self, src: Path, dst: Path) -> None:
        """Copy one skill directory with Codex-specific path rewriting."""
        dst.mkdir(parents=True, exist_ok=True)
        for entry in self.skill_source_files(src):
            rel = entry.relative_to(src)
            target_path = dst / rel
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if entry.name == "SKILL.md":
                atomic_write_text(
                    target_path,
                    self.rewrite_skill_md_paths(entry.read_text()),
                )
            else:
                target_path.write_bytes(entry.read_bytes())

    def install_agents(self) -> None:
        agents_src = self.plugin / "agents"
        agents_dst = self.target / ".codex" / "agents"

        if agents_src.is_dir():
            agents_dst.mkdir(parents=True, exist_ok=True)
            for agent in sorted(agents_src.glob("*.md")):
                dst = agents_dst / self.codex_agent_file_name(agent.name)
                atomic_write_text(dst, self.render_codex_agent(agent))

    @staticmethod
    def codex_agent_file_name(name: str) -> str:
        return name if name.startswith("jig-") else f"jig-{name}"

    @classmethod
    def render_codex_agent(cls, agent: Path) -> str:
        body = agent.read_text()
        if "Codex adapter note" not in body:
            body = cls.rewrite_agent_body(body)
            name = agent.stem.removeprefix("jig-")
            body = cls.CODEX_AGENT_NOTE.format(name=name) + body
        if not body.endswith("\n"):
            body += "\n"
        return body

    @staticmethod
    def rewrite_agent_body(body: str) -> str:
        out = body.replace(".claude", ".codex")
        out = out.replace("CLAUDE.md", "AGENTS.md")
        out = out.replace("Claude Code", "Codex")
        out = out.replace("Claude", "Codex")
        return out

    def build_hook_entries(self) -> dict:
        """Build Codex `.codex/hooks.json` hook entries.

        The registration mirrors `hooks/hooks.json` while rebasing commands
        from plugin-local dispatch to project-local `.codex/hooks/scripts/`.
        """
        source = json.loads((self.plugin / "hooks" / "hooks.json").read_text())
        out: dict = {}
        for event, entries in (source.get("hooks") or {}).items():
            new_entries = []
            for entry in entries:
                new_inner = []
                for h in entry.get("hooks", []):
                    rewritten = dict(h)
                    if "command" in rewritten:
                        rewritten["command"] = self.rewrite_hook_command(
                            rewritten["command"]
                        )
                    new_inner.append(rewritten)
                new_entry = {}
                if "matcher" in entry:
                    new_entry["matcher"] = entry["matcher"]
                new_entry["hooks"] = new_inner
                new_entries.append(new_entry)
            out[event] = new_entries
        return out

    @classmethod
    def rewrite_hook_script_body(cls, body: str) -> str:
        """Rewrite copied hook scripts for Codex project-local runtime."""
        out = body.replace("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")
        out = out.replace("CLAUDE_PLUGIN_ROOT", "CODEX_HOME")
        out = out.replace(".claude", ".codex")
        out = out.replace("Claude", "Codex")
        out = out.replace(
            "os.environ.get('CODEX_PROJECT_DIR', '.')",
            "os.environ.get('CODEX_PROJECT_DIR') or os.getcwd()",
        )
        return out

    def install_hooks(self) -> None:
        src_scripts = self.plugin / "hooks" / "scripts"
        dst_scripts = self.target / ".codex" / "hooks" / "scripts"
        hooks_path = self.target / ".codex" / "hooks.json"

        dst_scripts.mkdir(parents=True, exist_ok=True)
        if src_scripts.is_dir():
            for script in sorted(src_scripts.glob("jig-*.sh")):
                dst = dst_scripts / script.name
                atomic_write_text(
                    dst,
                    self.rewrite_hook_script_body(script.read_text()),
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

        source_hooks = self.plugin / "hooks" / "hooks.json"
        if source_hooks.is_file():
            raw_hooks = self.target / ".codex" / "hooks" / "hooks.json"
            raw_hooks.parent.mkdir(parents=True, exist_ok=True)
            raw_hooks.write_bytes(source_hooks.read_bytes())

        payload = {
            "metadata": dict(self.CODEX_HOOK_MARKER),
            "hooks": self.build_hook_entries(),
        }
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(hooks_path, json.dumps(payload, indent=2) + "\n")

    def check_hooks_safety(self) -> dict:
        hooks_path = self.target / ".codex" / "hooks.json"
        existing: dict = {}
        if not hooks_path.is_file():
            return existing
        try:
            existing = json.loads(hooks_path.read_text())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{hooks_path} exists but is not valid JSON: {exc}"
            ) from exc
        has_hooks = bool(existing.get("hooks"))
        has_jig_marker = bool(
            (existing.get("metadata") or {}).get("managed_by_jig")
        )
        if has_hooks and not has_jig_marker and not self.force:
            raise UnmanagedHooksError(
                f"{hooks_path} already has hooks but no jig-managed marker - "
                "refusing to overwrite user-owned Codex hook configuration. "
                "Pass --force to replace it, or move/merge the file first."
            )
        return existing

    def translate_hook_protocol(self, logical_result: dict) -> dict:
        """Translate jig-level hook result keys to Codex hook protocol.

        Current Codex hook handling accepts the same soft warning payload
        (`additionalContext`) and exit-2 blocking convention used by jig's
        Claude hooks.
        """
        return super().translate_hook_protocol(logical_result)

    def bind_paths(self) -> dict[str, str]:
        return {
            "project_root_env": "CODEX_PROJECT_DIR",
            "runtime_root": "${CODEX_PROJECT_DIR:-$PWD}/.codex",
            "plugin_root_env": "CODEX_HOME",
        }

    def managed_file_metadata(self) -> dict:
        return {"policy": _managed_file_policy()}

    def primer_managed_file_specs(self) -> list[ManagedFileSpec]:
        return [
            ManagedFileSpec(
                "AGENTS.md", "templates/AGENTS.md.template", self.name,
            ),
        ]

    def runtime_managed_file_specs(self) -> list[ManagedFileSpec]:
        specs: list[ManagedFileSpec] = []

        skills_src = self.plugin / "skills"
        skills_dst = self.target / ".codex" / "skills"
        if skills_src.is_dir():
            for skill_dir in sorted(skills_src.iterdir()):
                if not skill_dir.is_dir():
                    continue
                if skill_dir.name.startswith("_"):
                    dst_dir = skills_dst / skill_dir.name
                else:
                    if not (skill_dir / "SKILL.md").is_file():
                        continue
                    dst_dir = skills_dst / self.codex_skill_dir_name(
                        skill_dir.name
                    )
                for src_file in self.skill_source_files(skill_dir):
                    rel = src_file.relative_to(skill_dir)
                    specs.append(ManagedFileSpec(
                        (dst_dir / rel).relative_to(self.target).as_posix(),
                        src_file.relative_to(self.plugin).as_posix(),
                        self.name,
                    ))

            for skill_dir in sorted(skills_src.iterdir()):
                if (
                    not skill_dir.is_dir()
                    or skill_dir.name.startswith("_")
                    or not (skill_dir / "SKILL.md").is_file()
                ):
                    continue
                alias_dir = skills_dst / self.original_skill_dir_name(
                    skill_dir.name
                )
                for src_file in self.skill_source_files(skill_dir):
                    if src_file.name == "SKILL.md":
                        continue
                    dst = alias_dir / src_file.relative_to(skill_dir)
                    if not dst.is_file():
                        continue
                    specs.append(ManagedFileSpec(
                        dst.relative_to(self.target).as_posix(),
                        src_file.relative_to(self.plugin).as_posix(),
                        self.name,
                    ))

        templates_src = self.plugin / "templates"
        templates_dst = self.target / ".codex" / "templates"
        if templates_src.is_dir():
            for entry in sorted(templates_src.rglob("*")):
                if entry.is_dir():
                    continue
                dst = templates_dst / entry.relative_to(templates_src)
                specs.append(ManagedFileSpec(
                    dst.relative_to(self.target).as_posix(),
                    entry.relative_to(self.plugin).as_posix(),
                    self.name,
                ))

        agents_src = self.plugin / "agents"
        agents_dst = self.target / ".codex" / "agents"
        if agents_src.is_dir():
            for agent in sorted(agents_src.glob("*.md")):
                dst = agents_dst / self.codex_agent_file_name(agent.name)
                specs.append(ManagedFileSpec(
                    dst.relative_to(self.target).as_posix(),
                    agent.relative_to(self.plugin).as_posix(),
                    self.name,
                ))

        src_scripts = self.plugin / "hooks" / "scripts"
        scripts_dst = self.target / ".codex" / "hooks" / "scripts"
        if src_scripts.is_dir():
            for script in sorted(src_scripts.glob("jig-*.sh")):
                dst = scripts_dst / script.name
                specs.append(ManagedFileSpec(
                    dst.relative_to(self.target).as_posix(),
                    script.relative_to(self.plugin).as_posix(),
                    self.name,
                ))
            src_lib = src_scripts / "lib"
            if src_lib.is_dir():
                for py in sorted(src_lib.glob("*.py")):
                    if py.name.startswith("test_"):
                        continue
                    dst = scripts_dst / "lib" / py.name
                    specs.append(ManagedFileSpec(
                        dst.relative_to(self.target).as_posix(),
                        py.relative_to(self.plugin).as_posix(),
                        self.name,
                    ))

        hooks_json = self.target / ".codex" / "hooks.json"
        if hooks_json.is_file():
            specs.append(ManagedFileSpec(
                hooks_json.relative_to(self.target).as_posix(),
                "hooks/hooks.json",
                self.name,
            ))
        raw_hooks_json = self.target / ".codex" / "hooks" / "hooks.json"
        if raw_hooks_json.is_file():
            specs.append(ManagedFileSpec(
                raw_hooks_json.relative_to(self.target).as_posix(),
                "hooks/hooks.json",
                self.name,
            ))

        return specs

    def verification_fixtures(self) -> dict:
        return {
            "primers": ["AGENTS.md"],
            "skills_dir": ".codex/skills",
            "agents_dir": ".codex/agents",
            "hook_scripts_glob": ".codex/hooks/scripts/jig-*.sh",
            "settings": ".codex/hooks.json",
        }


def _claude_renderer(
    plugin: Path, target: Path, *, force: bool = False
) -> ClaudeScaffoldRenderer:
    return ClaudeScaffoldRenderer(plugin, target, force=force)


def _renderer_for_host(
    host: str, plugin: Path, target: Path, *, force: bool = False
) -> HostRenderer:
    if host == "claude":
        return ClaudeScaffoldRenderer(plugin, target, force=force)
    if host == "codex":
        return CodexScaffoldRenderer(plugin, target, force=force)
    raise ValueError(f"unsupported scaffold host: {host}")


def _copy_skills_and_agents(plugin: Path, target: Path) -> None:
    """Compatibility facade for tests/migrate; delegates to Claude renderer."""
    _claude_renderer(plugin, target).copy_skills_and_agents()


def _rewrite_skill_md_paths(body: str) -> str:
    """Compatibility facade for tests; delegates to Claude renderer."""
    return ClaudeScaffoldRenderer.rewrite_skill_md_paths(body)


def _copy_skill_dir(src: Path, dst: Path) -> None:
    """Compatibility facade for tests; delegates to Claude renderer."""
    _claude_renderer(Path("."), Path(".")).copy_skill_dir(src, dst)


def _is_jig_managed(entry: dict) -> bool:
    """An entry counts as jig-managed iff its `metadata.managed_by_jig` is
    truthy. Stable across re-runs."""
    return bool((entry.get("metadata") or {}).get("managed_by_jig"))


def _rewrite_hook_command(command: str) -> str:
    """Compatibility facade for tests; delegates to Claude renderer."""
    return ClaudeScaffoldRenderer.rewrite_hook_command(command)


def _build_jig_hook_entries(plugin: Path) -> dict:
    """Compatibility facade for tests; delegates to Claude renderer."""
    return _claude_renderer(plugin, Path(".")).build_hook_entries()


def _merge_settings(existing: dict, jig_hooks: dict) -> dict:
    """Compatibility facade for tests; delegates to Claude renderer."""
    return ClaudeScaffoldRenderer.merge_settings(existing, jig_hooks)


def _check_hooks_safety(target: Path, *, force: bool = False) -> dict:
    """Compatibility facade for tests; delegates to Claude renderer."""
    return _claude_renderer(Path("."), target, force=force).check_hooks_safety()


def _copy_hooks_and_register(plugin: Path, target: Path, *,
                             force: bool = False) -> None:
    """Compatibility facade for tests; delegates to Claude renderer."""
    _claude_renderer(plugin, target, force=force).copy_hooks_and_register()


def copy_machinery(plugin: Path, target: Path, *,
                   force: bool = False) -> None:
    """Copy jig's runtime machinery (skills + agents + hooks + settings.json)
    from `plugin` into `target/.claude/`.

    Public facade introduced by slice 021-01 so that `migrate.py
    copy-machinery` can reuse exactly the same logic `scaffold-init` uses
    when `--with-machinery` is in effect. Since slice 033-03, this delegates
    to the Claude renderer boundary, which internally performs:

      1. `check_hooks_safety()` — pre-flight safety
         check (inbox 2026-05-15): ensures we refuse BEFORE any filesystem
         mutation when settings.json is unmanaged. Closes the partial-
         state-on-refuse gap noted in spec 016-03 deviation §7.
      2. `copy_skills_and_agents()` — slice 016-01.
      3. `copy_hooks_and_register()` — slice 016-02.

    Safety guarantees:
    - Executable bit pinned to 0o755 on copied hook scripts.
    - Marker-based merge in `.claude/settings.json` (replace-in-place by
      `metadata.managed_by_jig`, non-jig entries survive).
    - UnmanagedHooksError fires BEFORE any filesystem mutation, so a
      refused call leaves no partial state — including no copied
      skills/agents (this is the gap inbox 2026-05-15 closes)."""
    _claude_renderer(plugin, target, force=force).install_runtime()


def scaffold(target: Path, plugin: Path, *, force: bool = False,
             overrides: Overrides = None,
             with_machinery: bool = True,
             host: str = "claude") -> None:
    """Run the greenfield scaffold against `target`. Refuses to overwrite an
    already-scaffolded directory unless `force=True`. `overrides` carries the
    Q&A wizard answers from slice 001-05; None fields fall back to filesystem
    inference. Plugin templates live at `plugin/templates/`.

    When `with_machinery=True` (slice 016-01; default-on as of slice 016-03),
    also copies host-local runtime artifacts into the target, rewriting
    SKILL.md path placeholders. The CLI's `--plugin-only` flag sets this to
    `False` to preserve the pre-016-03 docs-only behavior."""
    target = target.resolve()
    template_root = plugin / "templates"
    renderer = _renderer_for_host(host, plugin, target, force=force)

    if not template_root.exists():
        raise FileNotFoundError(f"Template root not found: {template_root}")

    existing_manifest = _read_json_safe(target / "scaffold.json")

    if (target / "scaffold.json").exists() and not force:
        raise AlreadyScaffoldedError(
            f"{target} is already scaffolded (scaffold.json present). "
            "Pass --force to overwrite."
        )
    if force and existing_manifest:
        _check_managed_file_conflicts(target, existing_manifest)

    # Slice 008-05: detect projects that look spec-driven without a
    # scaffold.json — route them to `/jig:migrate` instead of polluting
    # the tree. `scaffold.json`-check above takes precedence; this fires
    # only when scaffold.json is absent.
    #
    # Slice 032-02: skip this check when the target is a jig partial
    # state (primer file with jig watermark + no scaffold.json) — that's a
    # crashed-mid-scaffold recovery, not a user's spec-driven project.
    # With `scaffold.json` now written LAST (the completion sentinel),
    # a crash leaves docs/* + primer files but no scaffold.json; the next
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

    _check_primer_safety(
        target,
        force=force,
        primer_names=tuple(spec.path for spec in renderer.primer_managed_file_specs()),
    )

    # Detect signals BEFORE writing any scaffold files — otherwise wizard-generated
    # docs would self-trigger detectors (e.g. *.prompt.md, copilot-instructions.md).
    signals = detect_signals(target)
    if overrides is not None:
        signals = overrides.apply_to(signals)
    installed_tiers, offered_tiers = _select_tiers(signals)
    hook_profile = _hook_profile(signals)

    project_name = target.name
    timestamp = (
        existing_manifest.get("timestamp")
        if force and existing_manifest.get("timestamp")
        else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    subs = {
        "PROJECT_NAME": project_name,
        "JIG_VERSION": JIG_VERSION,
        "TIMESTAMP": timestamp,
    }
    managed_specs: list[ManagedFileSpec] = []

    # 1. Host renderer owns project primer files.
    renderer.render_primers(template_root, subs)
    managed_specs.extend(renderer.primer_managed_file_specs())

    # 2. docs/ structure from templates/docs/*.md.template (recursive).
    # people.md is conditional — generated only when team is detected.
    docs_template_root = template_root / "docs"
    for src in docs_template_root.rglob("*.md.template"):
        rel = src.relative_to(docs_template_root)
        dst_name = rel.with_suffix("")  # strip .template, leaves .md
        if dst_name.name == "people.md" and not signals.is_team:
            continue
        dst = target / "docs" / dst_name
        copy_template(src, dst, subs)
        managed_specs.append(ManagedFileSpec(
            dst.relative_to(target).as_posix(),
            (Path("templates") / "docs" / rel).as_posix(),
            renderer.name,
        ))

    # 3. brief.md — human-readable summary of detection results
    brief_template = (template_root / "brief.md.template").read_text()
    brief = _render_brief(brief_template, signals, installed_tiers, offered_tiers, subs)
    atomic_write_text(target / "brief.md", brief)
    managed_specs.append(ManagedFileSpec(
        "brief.md", "templates/brief.md.template", renderer.name,
    ))

    # 4. Slice 016-01 + 016-02: copy skills/, agents/, hook scripts, and
    # write/merge .claude/settings.json when --with-machinery is on
    # (default since 016-03). `force` propagates so that --force also
    # overrides the unmanaged-hooks safety check (same escape hatch as
    # AlreadyScaffoldedError). Slice 021-01 lifted the two-call sequence
    # behind a public `copy_machinery()` facade so `migrate.py
    # copy-machinery` can reuse the exact same logic without depending
    # on the underscored helpers.
    #
    # Slice 032-02: machinery copy runs BEFORE scaffold.json so that an
    # UnmanagedHooksError refusal leaves no scaffold.json behind — the
    # next run treats the directory as un-scaffolded and re-attempts
    # without `--force`.
    if with_machinery:
        renderer.install_runtime()
        managed_specs.extend(renderer.runtime_managed_file_specs())

    # 5. scaffold.json install-state manifest — the COMPLETION SENTINEL
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
    # leaves machinery under the installed host/plugin runtime; "in-repo"
    # copies machinery into the selected host's project-local runtime.
    manifest["scaffold_mode"] = "in-repo" if with_machinery else "plugin-only"
    manifest["host_renderer"] = renderer.name
    manifest["managed_files"] = _managed_files_manifest(target, managed_specs)
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
    p.add_argument("target", help="target directory")
    p.add_argument(
        "--host", choices=("claude", "codex"), default="claude",
        help="host scaffold renderer to use (default: claude)",
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
        help="copy skills/, agents/, and hooks/ into the host-local project "
             "runtime so the dev owns and can edit the runtime artifacts "
             "(default-on as of "
             "slice 016-03; flag is now redundant but kept for symmetry)",
    )
    machinery.add_argument(
        "--plugin-only", dest="with_machinery",
        action="store_false",
        help="opt out of scaffold-mode: only scaffold primer files and docs/ "
             "into the target; leave skills/ and agents/ under the installed "
             "host/plugin runtime",
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

    target = Path(ns.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    overrides = Overrides(
        is_team=ns.is_team,
        has_ci=ns.has_ci,
        has_tests=ns.has_tests,
        has_llm_agent_files=ns.has_llm_agent_files,
        runtime=ns.runtime,
    )

    try:
        scaffold(target, plugin_root(ns.host), force=ns.force, overrides=overrides,
                 with_machinery=ns.with_machinery, host=ns.host)
    except AlreadyScaffoldedError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except LooksAlreadySpecDrivenError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except ExistingPrimerError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except ManagedFileConflictError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except UnmanagedHooksError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except Exception as exc:
        sys.stderr.write(f"scaffold failed: {exc}\n")
        return 1

    print(f"scaffolded {target.name} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
