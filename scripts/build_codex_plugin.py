"""
build_codex_plugin.py — slice 033-06 (Codex plugin packaging).

Materializes a Codex-native plugin tree from jig's canonical source tree.
The checked-in source remains Claude-compatible at root; this builder rewrites
only the staged plugin copy so Codex users get Codex-shaped skill prose and
plugin-root command paths without forking source skills.

Per slice 061-02 / ADR-0018, the default output is the committed peer at
`hosts/codex/plugins/jig` (sibling of `hosts/claude/`), so Claude and Codex sit
as parallel committed packages built from canonical source. The marketplace
descriptor lands at `hosts/codex/.agents/plugins/marketplace.json` with a
package-relative `source.path` of `./plugins/jig`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "scaffold-init"))
sys.path.insert(0, str(ROOT / "scripts"))

import install_contract  # noqa: E402
import scaffold as scaffold_mod  # noqa: E402

_CODEX_PLUGIN_HOOK_SCRIPT_PREFIX = "${PLUGIN_ROOT}/hooks/scripts/"

_ROOT_DIRS: tuple[str, ...] = (
    ".codex-plugin",
    "agents",
    "hooks",
)

_ROOT_FILES: tuple[str, ...] = (
    "README.md",
    "LICENSE",
    # README logo asset — the packaged README references `./jig.jpg`, so it
    # must ship in the Codex package too or the logo renders broken.
    "jig.jpg",
)

_EXCLUDE_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "fixtures",
})

_EXCLUDE_FILE_NAMES: frozenset[str] = frozenset({
    ".DS_Store",
})

_EXCLUDE_FILE_SUFFIXES: tuple[str, ...] = (
    ".pyc",
)


def _is_excluded(path: Path) -> bool:
    if any(part in _EXCLUDE_DIR_NAMES for part in path.parts[:-1]):
        return True
    if path.name in _EXCLUDE_FILE_NAMES:
        return True
    if path.name.startswith("test_") and path.suffix == ".py":
        return True
    return any(path.name.endswith(suffix) for suffix in _EXCLUDE_FILE_SUFFIXES)


def _copy_tree(src_root: Path, dst_root: Path) -> None:
    for entry in sorted(src_root.rglob("*")):
        if entry.is_dir():
            continue
        rel = entry.relative_to(src_root)
        if _is_excluded(rel):
            continue
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(entry.read_bytes())


def render_codex_plugin_skill_body(body: str) -> str:
    """Render a root SKILL.md body for Codex plugin mode.

    Codex plugin mode is central-install like Claude plugin mode, so helper
    paths stay plugin-root based. Host wording and scaffold defaults are
    Codex-shaped, and migrate's host-aware command examples are finalized
    after the broad wording rewrite.
    """
    out = body.replace(
        "- `CLAUDE.md` (Claude Code adapter that imports `AGENTS.md`)\n",
        "",
    )
    out = out.replace(" or `CLAUDE.md`", "")
    out = out.replace(
        ", and\n  `templates/CLAUDE.md.template` is the Claude adapter",
        "",
    )
    out = scaffold_mod.ClaudeScaffoldRenderer.SKILL_PATH_RE.sub(
        r"${PLUGIN_ROOT}/skills/\1/",
        out,
    )
    # NOTE: `test_migrate.host_specific_spellings()` walks THIS WHOLE FILE with
    # `ast`, collects every two-string-literal `.replace("<from>", "<to>")`
    # call, and bans both sides from migrate SKILL.md's stale-citation advisory
    # section (bug 023) rather than keeping its own copy of the table. Two
    # consequences worth knowing before you edit here: moving ALL these pairs
    # into a loop or lookup makes the walk find nothing, which fails loudly by
    # design, while moving only SOME shrinks the set silently; and any new
    # two-constant `.replace()` anywhere in this file joins the forbidden set,
    # so an unrelated one could ban legitimate prose in that section.
    out = out.replace("${CLAUDE_PLUGIN_ROOT}/templates/", "${PLUGIN_ROOT}/templates/")
    out = out.replace("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}")
    out = out.replace("${CLAUDE_PROJECT_DIR}", "${CODEX_PROJECT_DIR:-$PWD}")
    out = out.replace("CLAUDE_PLUGIN_ROOT", "PLUGIN_ROOT")
    out = out.replace("CLAUDE_PROJECT_DIR", "CODEX_PROJECT_DIR")
    out = out.replace(".claude/", ".codex/")
    out = out.replace("CLAUDE.md", "AGENTS.md")
    out = out.replace("Claude Code", "Codex")
    out = out.replace("Claude", "Codex")
    out = scaffold_mod.CodexScaffoldRenderer.finalize_codex_migrate_skill(out)
    out = scaffold_mod.CodexScaffoldRenderer.rewrite_skill_override_guidance(out)
    scaffold_invocation = 'python3 "${PLUGIN_ROOT}/skills/scaffold-init/scaffold.py" \\\n'
    if scaffold_invocation in out and "--host codex" not in out:
        out = out.replace(
            scaffold_invocation,
            scaffold_invocation + "     --host codex \\\n",
        )
    return out


def _copy_skills(source_root: Path, output_dir: Path) -> None:
    skills_src = source_root / "skills"
    skills_dst = output_dir / "skills"
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        dst_dir = skills_dst / skill_dir.name
        for entry in sorted(skill_dir.rglob("*")):
            if entry.is_dir():
                continue
            rel = entry.relative_to(skill_dir)
            if _is_excluded(rel):
                continue
            dst = dst_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if entry.name == "SKILL.md":
                dst.write_text(
                    render_codex_plugin_skill_body(entry.read_text()),
                    encoding="utf-8",
                )
            else:
                dst.write_bytes(entry.read_bytes())


def _write_codex_hooks(source_root: Path, output_dir: Path) -> None:
    source_hooks = source_root / "hooks" / "hooks.json"
    if not source_hooks.is_file():
        return
    hooks = json.loads(source_hooks.read_text())
    dst = output_dir / "hooks" / "hooks.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(
        json.dumps(
            scaffold_mod.render_codex_plugin_hooks(
                hooks,
                command_rewriter=lambda command: command.replace(
                    scaffold_mod.ClaudeScaffoldRenderer.PLUGIN_HOOK_SCRIPT_PREFIX,
                    _CODEX_PLUGIN_HOOK_SCRIPT_PREFIX,
                ),
            ),
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def _rewrite_codex_hook_scripts(output_dir: Path) -> None:
    scripts_dir = output_dir / "hooks" / "scripts"
    if not scripts_dir.is_dir():
        return
    for script in sorted(scripts_dir.glob("jig-*.sh")):
        script.write_text(
            scaffold_mod.CodexScaffoldRenderer.rewrite_hook_script_body(
                script.read_text()
            ),
            encoding="utf-8",
        )
    lib_dir = scripts_dir / "lib"
    if lib_dir.is_dir():
        for helper in sorted(lib_dir.glob("*.py")):
            helper.write_text(
                scaffold_mod.CodexScaffoldRenderer.rewrite_hook_script_body(
                    helper.read_text()
                ),
                encoding="utf-8",
            )


def _copy_runtime_scripts(source_root: Path, output_dir: Path) -> None:
    """Copy the host-neutral runtime-scripts subset into the Codex package.

    `install_contract.CODEX_INCLUDE_SCRIPT_FILES` (`spec_lint.py` only) ships
    verbatim so `${PLUGIN_ROOT}/scripts/spec_lint.py` — the pre-implementation
    structural gate the rendered Codex `migrate`/`analyze` skills invoke —
    resolves in an installed Codex plugin (bug 025 / #167). The Claude-only
    trio (`verify_install` / `scaffold_contract`) is excluded: it validates a
    `.claude/` install tree and no Codex skill references it. These modules are
    host-neutral Python and carry no `${CLAUDE_PLUGIN_ROOT}`/`.claude/` tokens,
    so they are copied byte-for-byte with no host rewrite."""
    for rel_name in install_contract.CODEX_INCLUDE_SCRIPT_FILES:
        src = source_root / rel_name
        if not src.is_file():
            continue
        dst = output_dir / rel_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def _copy_templates(source_root: Path, output_dir: Path) -> None:
    templates_src = source_root / "templates"
    templates_dst = output_dir / "templates"
    if not templates_src.is_dir():
        return
    for entry in sorted(templates_src.rglob("*")):
        if entry.is_dir():
            continue
        rel = entry.relative_to(templates_src)
        if _is_excluded(rel):
            continue
        dst = templates_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Templates ship Codex-NATIVE. Two consumer sets read them, and only
        # one goes through `scaffold()`: `decisions.py` (lightweight-decisions
        # seed), `adr.py`, `memory.py` and `workflow.py` read the packaged
        # template at runtime and copy it verbatim, with no transform of their
        # own. Shipping canonical here would hand a Codex project a
        # `${CLAUDE_PLUGIN_ROOT}` it can never resolve. Slice 099-01 briefly did
        # exactly that; the plugin-mode doc problem it was chasing is fixed in
        # `_rewrite_host_paths` instead, which can tell the modes apart.
        if entry.name.endswith(".md.template"):
            dst.write_text(
                scaffold_mod.CodexScaffoldRenderer.rewrite_skill_md_paths(
                    entry.read_text()
                ),
                encoding="utf-8",
            )
        else:
            dst.write_bytes(entry.read_bytes())


def _render_codex_agent_templates(source_root: Path, output_dir: Path) -> None:
    agents_src = source_root / "agents"
    agents_dst = output_dir / "agents"
    if not agents_src.is_dir():
        return
    agents_dst.mkdir(parents=True, exist_ok=True)
    for agent in sorted(agents_src.glob("*.md")):
        dst = agents_dst / scaffold_mod.CodexScaffoldRenderer.codex_agent_file_name(
            agent.name
        )
        dst.write_text(
            scaffold_mod.CodexScaffoldRenderer.render_codex_agent_toml(agent),
            encoding="utf-8",
        )


def _marketplace_root_for(output_dir: Path) -> Path:
    if output_dir.parent.name == "plugins":
        return output_dir.parent.parent
    return output_dir.parent


def _write_marketplace(output_dir: Path) -> None:
    marketplace_root = _marketplace_root_for(output_dir)
    try:
        rel_plugin_path = output_dir.relative_to(marketplace_root).as_posix()
    except ValueError:
        rel_plugin_path = output_dir.name
    payload = {
        "name": "jig",
        "interface": {"displayName": "jig"},
        "plugins": [
            {
                "name": "jig",
                "source": {
                    "source": "local",
                    "path": f"./{rel_plugin_path}",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Engineering",
            }
        ],
    }
    path = marketplace_root / ".agents" / "plugins" / "marketplace.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_output_dir(source_root: Path, output_dir: Path) -> tuple[bool, str]:
    if output_dir == source_root:
        return False, "output directory must not be the source root"
    if source_root in output_dir.parents:
        canonical_host_output = source_root / "hosts" / "codex" / "plugins" / "jig"
        source_owned_roots = {
            source_root / ".codex-plugin",
            source_root / ".claude-plugin",
            source_root / "agents",
            source_root / "hooks",
            source_root / "skills",
            source_root / "templates",
            source_root / "scripts",
            source_root / "docs",
            source_root / ".github",
        }
        under_hosts = _is_relative_to(output_dir, source_root / "hosts")
        under_dist = _is_relative_to(output_dir, source_root / "dist")
        if not (under_hosts or under_dist):
            return (
                False,
                "output directory inside the source tree must be under "
                "hosts/ or dist/",
            )
        if under_hosts and output_dir != canonical_host_output:
            return (
                False,
                "output directory under hosts/ must be hosts/codex/plugins/jig",
            )
        if output_dir in source_owned_roots or any(
            root in output_dir.parents for root in source_owned_roots
        ):
            return False, "output directory must not be a source-owned runtime path"
    if output_dir in source_root.parents:
        return False, "output directory must not be an ancestor of the source root"
    return True, ""


def build(source_root: Path, output_dir: Path) -> int:
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()

    manifest = source_root / ".codex-plugin" / "plugin.json"
    if not manifest.is_file():
        sys.stderr.write(f"ERROR: missing {manifest}\n")
        return 1

    valid_output, reason = _validate_output_dir(source_root, output_dir)
    if not valid_output:
        sys.stderr.write(f"ERROR: unsafe output directory: {reason}: {output_dir}\n")
        return 1

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for root_name in _ROOT_DIRS:
        src = source_root / root_name
        if src.is_dir():
            _copy_tree(src, output_dir / root_name)

    _write_codex_hooks(source_root, output_dir)
    _rewrite_codex_hook_scripts(output_dir)
    _copy_templates(source_root, output_dir)
    _copy_skills(source_root, output_dir)
    _copy_runtime_scripts(source_root, output_dir)
    _render_codex_agent_templates(source_root, output_dir)

    for file_name in _ROOT_FILES:
        src = source_root / file_name
        if src.is_file():
            (output_dir / file_name).write_bytes(src.read_bytes())

    _write_marketplace(output_dir)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_codex_plugin.py",
        description="materialize jig's Codex plugin package",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="output plugin directory (default: hosts/codex/plugins/jig)",
    )
    return parser


def main(argv: list[str]) -> int:
    ns = _build_parser().parse_args(argv[1:])
    source_root = Path(ns.source_root)
    output_dir = (
        Path(ns.output_dir)
        if ns.output_dir
        else source_root / "hosts" / "codex" / "plugins" / "jig"
    )
    code = build(source_root=source_root, output_dir=output_dir)
    if code == 0:
        print(f"OK: built Codex plugin at {output_dir}")
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
