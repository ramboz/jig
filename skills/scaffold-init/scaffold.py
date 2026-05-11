"""
jig scaffold-init — slice 001-01 greenfield-scaffold

Generates an AI-native dev workspace from `templates/` into a target directory.
Reads CLAUDE_PLUGIN_ROOT to locate the plugin's template dir.

Usage:
    python3 scaffold.py <target-dir>

The script is deterministic: no network, no user prompts. Q&A interaction
is a later slice (001-05); signal detection is 001-03.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
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


@dataclass
class Signals:
    """Detected project signals. Per Spike 001a (docs/spikes/spike-001a-signal-detection.md)."""
    has_llm_agent_files: bool
    has_ci: bool
    has_tests: bool
    is_team: bool


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


def scaffold(target: Path, plugin: Path, *, force: bool = False) -> None:
    """Run the greenfield scaffold against `target`. Refuses to overwrite an
    already-scaffolded directory unless `force=True`. Plugin templates live at
    `plugin/templates/`."""
    target = target.resolve()
    template_root = plugin / "templates"

    if not template_root.exists():
        raise FileNotFoundError(f"Template root not found: {template_root}")

    if (target / "scaffold.json").exists() and not force:
        raise AlreadyScaffoldedError(
            f"{target} is already scaffolded (scaffold.json present). "
            "Pass --force to overwrite."
        )

    # Detect signals BEFORE writing any scaffold files — otherwise wizard-generated
    # docs would self-trigger detectors (e.g. *.prompt.md, copilot-instructions.md).
    signals = detect_signals(target)
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
    (target / "scaffold.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 5. brief.md — human-readable summary of detection results
    brief_template = (template_root / "brief.md.template").read_text()
    brief = _render_brief(brief_template, signals, installed_tiers, offered_tiers, subs)
    (target / "brief.md").write_text(brief)


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = False
    if "--force" in args:
        force = True
        args = [a for a in args if a != "--force"]

    if len(args) != 1:
        sys.stderr.write("usage: scaffold.py [--force] <target-dir>\n")
        return 2

    target = Path(args[0]).resolve()
    target.mkdir(parents=True, exist_ok=True)

    try:
        scaffold(target, plugin_root(), force=force)
    except AlreadyScaffoldedError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except Exception as exc:
        sys.stderr.write(f"scaffold failed: {exc}\n")
        return 1

    print(f"scaffolded {target.name} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
