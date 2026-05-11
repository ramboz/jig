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
import sys
from datetime import datetime, timezone
from pathlib import Path


# Schema version for scaffold.json
JIG_VERSION = "0.1.0"
DEFAULT_TIERS = ["tier-0", "tier-1"]


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

    project_name = target.name
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    subs = {
        "PROJECT_NAME": project_name,
        "JIG_VERSION": JIG_VERSION,
        "TIMESTAMP": timestamp,
    }

    # 1. CLAUDE.md from the top-level template
    copy_template(template_root / "CLAUDE.md.template", target / "CLAUDE.md", subs)

    # 2. docs/ structure from templates/docs/*.md.template (recursive)
    docs_template_root = template_root / "docs"
    for src in docs_template_root.rglob("*.md.template"):
        rel = src.relative_to(docs_template_root)
        dst_name = rel.with_suffix("")  # strip .template, leaves .md
        dst = target / "docs" / dst_name
        copy_template(src, dst, subs)

    # 3. Directories that should exist (even if empty for now)
    (target / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)

    # 4. scaffold.json install-state manifest. scaffold.py is the single source
    # of truth for installed_tiers — the template carries a placeholder.
    manifest_template = (template_root / "scaffold.json.template").read_text()
    rendered = render(manifest_template, subs)
    manifest = json.loads(rendered)
    manifest["installed_tiers"] = DEFAULT_TIERS
    (target / "scaffold.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # 5. Solo-project default: no people.md (signal detection lives in slice 001-03)
    # Explicit non-action — documenting it here for clarity.


def main(argv: list[str]) -> int:
    args = argv[1:]
    force = False
    if "--force" in args:
        force = True
        args = [a for a in args if a != "--force"]

    if len(args) != 1:
        sys.stderr.write("usage: scaffold.py [--force] <target-dir>\n")
        return 2

    target = Path(args[0])
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
