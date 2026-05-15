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
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path


# Schema version for scaffold.json
JIG_VERSION = "0.1.0"

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


def plugin_root() -> Path:
    """Locate the jig plugin root via CLAUDE_PLUGIN_ROOT, falling back to this script's parents."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # Fallback: scaffold.py lives at <plugin-root>/skills/scaffold-init/scaffold.py
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
    dst.write_text(rendered)


class AlreadyScaffoldedError(RuntimeError):
    """Raised when target already has a scaffold.json — refuses to overwrite."""


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


def _copy_skills_and_agents(plugin: Path, target: Path) -> None:
    """Copy `plugin/skills/<name>/` → `target/.claude/skills/jig-<name>/` and
    `plugin/agents/*.md` → `target/.claude/agents/jig-<name>.md`.

    Slice 016-01 (scaffold-mode). Skips:
      - `skills/_common` and any other `_`-prefixed private skill dir
        (mirrors the convention in `scripts/run_tests.py`);
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

    if skills_src.is_dir():
        skills_dst.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith("_"):
                continue
            if not (skill_dir / "SKILL.md").is_file():
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


def _copy_skill_dir(src: Path, dst: Path) -> None:
    """Copy a single skill directory. SKILL.md gets path-substitution on
    its body; other .py files (excluding test_*.py) are copied verbatim;
    everything else under the skill dir is mirrored verbatim too. Skips
    `__pycache__` and `test_*.py`."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        # Skip __pycache__ trees wholesale
        if any(part == "__pycache__" for part in rel.parts):
            continue
        if entry.is_dir():
            (dst / rel).mkdir(parents=True, exist_ok=True)
            continue
        # Exclude test files anywhere in the tree
        if entry.name.startswith("test_") and entry.name.endswith(".py"):
            continue
        target_path = dst / rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if entry.name == "SKILL.md":
            text = entry.read_text()
            fm, body = _split_frontmatter(text)
            rewritten = fm + _rewrite_skill_md_paths(body)
            target_path.write_text(rewritten)
        else:
            target_path.write_bytes(entry.read_bytes())


def scaffold(target: Path, plugin: Path, *, force: bool = False,
             overrides: Overrides = None,
             with_machinery: bool = False) -> None:
    """Run the greenfield scaffold against `target`. Refuses to overwrite an
    already-scaffolded directory unless `force=True`. `overrides` carries the
    Q&A wizard answers from slice 001-05; None fields fall back to filesystem
    inference. Plugin templates live at `plugin/templates/`.

    When `with_machinery=True` (slice 016-01), also copies `plugin/skills/*`
    and `plugin/agents/*` into `target/.claude/skills/jig-*/` and
    `target/.claude/agents/jig-*.md` respectively, rewriting SKILL.md path
    placeholders. Default-off; flips to default-on in slice 016-03."""
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
    if not force:
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
    subs = {
        "PROJECT_NAME": project_name,
        "JIG_VERSION": JIG_VERSION,
        "TIMESTAMP": timestamp,
    }

    # 1. CLAUDE.md from the top-level template
    copy_template(template_root / "CLAUDE.md.template", target / "CLAUDE.md", subs)

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

    # 3. Directories that should exist (even if empty for now)
    (target / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)

    # 4. scaffold.json install-state manifest. scaffold.py is the single source
    # of truth for installed_tiers — the template carries a placeholder.
    manifest_template = (template_root / "scaffold.json.template").read_text()
    rendered = render(manifest_template, subs)
    manifest = json.loads(rendered)
    manifest["installed_tiers"] = installed_tiers
    manifest["scaffold_signals"] = asdict(signals)
    manifest["hook_profile"] = hook_profile
    if offered_tiers:
        manifest["offered_tiers"] = offered_tiers
    # project_runtime is recorded only when the wizard explicitly captured an answer.
    # `is not None` rather than truthy — empty string "" is still an explicit answer
    # the wizard chose to record, not the same as "skipped".
    if overrides is not None and overrides.runtime is not None:
        manifest["project_runtime"] = overrides.runtime
    # Slice 016-01: record which install shape was used. Default is
    # "plugin-only" (today's behavior — machinery lives under
    # ${CLAUDE_PLUGIN_ROOT}); "in-repo" is set when --with-machinery was
    # passed (machinery copied into target/.claude/).
    manifest["scaffold_mode"] = "in-repo" if with_machinery else "plugin-only"
    (target / "scaffold.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 5. brief.md — human-readable summary of detection results
    brief_template = (template_root / "brief.md.template").read_text()
    brief = _render_brief(brief_template, signals, installed_tiers, offered_tiers, subs)
    (target / "brief.md").write_text(brief)

    # 6. Slice 016-01: copy skills/ and agents/ into .claude/ when
    # --with-machinery was passed. Default-off; flips to default-on in
    # slice 016-03. Hooks are 016-02's job.
    if with_machinery:
        _copy_skills_and_agents(plugin, target)


def _build_parser() -> argparse.ArgumentParser:
    """CLI surface for scaffold.py — used both by main() and tests."""
    p = argparse.ArgumentParser(
        prog="scaffold.py",
        description="jig scaffold-init — generate an AI-native dev workspace",
    )
    p.add_argument("target", help="target directory")
    p.add_argument("--force", action="store_true",
                   help="overwrite an already-scaffolded directory")
    p.add_argument("--with-machinery", action="store_true",
                   help="also copy skills/ and agents/ into target/.claude/ "
                        "so the dev owns and can edit the runtime artifacts "
                        "(slice 016-01; default-off until 016-03)")
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
        scaffold(target, plugin_root(), force=ns.force, overrides=overrides,
                 with_machinery=ns.with_machinery)
    except AlreadyScaffoldedError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except LooksAlreadySpecDrivenError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except Exception as exc:
        sys.stderr.write(f"scaffold failed: {exc}\n")
        return 1

    print(f"scaffolded {target.name} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
