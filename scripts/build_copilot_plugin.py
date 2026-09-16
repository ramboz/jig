"""
build_copilot_plugin.py — slice 113-02 (renderer-and-skeleton).

Materializes jig's **Copilot CLI plugin package** at `hosts/copilot/` from
canonical source. Per ADR-0061 (extending ADR-0018's tri-host pattern to a
third committed host) the repository root stays canonical source and
`hosts/copilot/` is the clean, directly-installable payload:
`copilot plugin install ramboz/jig:hosts/copilot` — a repo-subdirectory
install, no build step and no separate marketplace (spike 113-01 AC1).

Scope note (113-02 shipped a **walking skeleton**; 113-03 grows it by one
thing — custom agents): skills, the plugin manifest, and now `agents/*.md`
(rendered to `.github/agents/<name>.agent.md`) ship here. Hook translation
(`.github/hooks/*.json`, 113-04/05) and the release zip (113-06) are still
deliberately NOT built — `CopilotScaffoldRenderer` inherits
`translate_hook_protocol`/`bind_paths` unexercised from
`ClaudeScaffoldRenderer` until those slices verify Copilot's plugin-root env
var and hook schema. Skill bodies (and agent prompt bodies) still ship
Claude-native (no path rewriting) — the same documented, deliberate gap
113-02 opened, not an oversight.

113-02 review fix (owner decision): the package does NOT ship a
pre-rendered `.github/copilot-instructions.md` either. Parity ruling:
Claude/Codex builders ship `templates/CLAUDE.md.template` UNRENDERED rather
than a rendered project-instructions file, and a `/plugin` install must not
impose instructions on the consuming repo. Shipping `templates/` (unrendered,
matching Claude/Codex) is 113-06 full-package-parity scope, not this
skeleton.

Loader-compat invariant (ADR-0061 / spike 113-01 AC2): Copilot's skill loader
rejects a `name:` containing `:` and a `description:` over 1024 characters.
jig source names are already colon-free; this builder enforces the length
limit in the RENDER layer only, via `CopilotScaffoldRenderer.loader_safe_description`
— a compliant skill's SKILL.md ships byte-for-byte from source, and only a
skill whose description would exceed the limit gets its frontmatter
shortened, with the full original text preserved in the body. Claude and
Codex packages are built from the same canonical source, untouched by this
transform.

Usage:
    python3 scripts/build_copilot_plugin.py [--source-root <root>] [--output-dir <dir>]

Default output: <source-root>/hosts/copilot
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

import build_codex_plugin  # noqa: E402
import install_contract  # noqa: E402
import scaffold as scaffold_mod  # noqa: E402

# Reused verbatim from the Codex builder (same exclusion rules: no
# test_*.py, no fixtures/, no bytecode/tool caches, no .DS_Store) — this is
# the same "reuse, don't restate" convention build_claude_plugin.py already
# applies to build_release_zip's predicates.
_is_excluded = build_codex_plugin._is_excluded

_COPILOT_DESCRIPTION = (
    "Spec-driven, review-enforced, hook-gated AI-native development workflow "
    "for GitHub Copilot CLI"
)

# YAML block-scalar header markers a `description:` field may use (folded
# `>`/`>-`/`>+` or literal `|`/`|-`/`|+`). Mirrors
# `install_contract._read_skill_description`'s own marker list so the two
# stay in lockstep about what counts as "the value continues on later lines".
_DESCRIPTION_BLOCK_MARKERS = (">", "|", ">-", "|-", ">+", "|+")


def _replace_description_field(fm_text: str, new_value: str) -> str:
    """Replace a frontmatter's `description:` field (inline or a folded/
    literal block scalar) with a single inline line carrying `new_value`,
    leaving every other frontmatter line — order, fences, other fields —
    untouched. `fm_text` includes both `---` fences."""
    lines = fm_text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    replaced = False
    while i < len(lines):
        line = lines[i]
        if not replaced and line.startswith("description:"):
            # `ensure_ascii=False`: install_contract._read_skill_description
            # (the re-measurement loader_safe_description's budget is meant
            # to bind) does not decode YAML/JSON escapes — it only strips
            # surrounding quotes — so an escaped non-ASCII character (e.g.
            # the letter e-acute, 1 char, escaping to a 6-char backslash-u
            # sequence) would inflate the re-measured
            # length past what was actually intended, and past what a real
            # YAML-aware loader would see once it decodes the escape back.
            # Writing the raw UTF-8 character keeps both consistent.
            out.append(f"description: {json.dumps(new_value, ensure_ascii=False)}\n")
            value_part = line[len("description:"):].strip()
            i += 1
            if not value_part or value_part in _DESCRIPTION_BLOCK_MARKERS:
                while i < len(lines) and (
                    lines[i].strip() == "" or lines[i][:1] in (" ", "\t")
                ):
                    i += 1
            replaced = True
            continue
        out.append(line)
        i += 1
    return "".join(out)


def render_copilot_skill_md(text: str) -> str:
    """Render one skill's SKILL.md for Copilot's loader-compat invariant.

    Returns `text` byte-for-byte unchanged when its description already fits
    Copilot's 1024-character skill-loader limit — the common case today, and
    the guarantee that a compliant skill's Copilot rendering matches its
    Claude/Codex source exactly. Otherwise rewrites the frontmatter
    `description:` field to a <=1024-character summary
    (`CopilotScaffoldRenderer.loader_safe_description`) and prepends the full
    original description to the body so no routing/trigger content is lost.

    Always asserts the skill's `name:` is namespace-safe (no `:`) — a
    render-layer guard (spike 113-01 AC2 / ADR-0061), not a transform."""
    fm, body = scaffold_mod._split_frontmatter(text)
    name = scaffold_mod.CopilotScaffoldRenderer.agent_frontmatter_value(fm, "name", "")
    scaffold_mod.CopilotScaffoldRenderer.assert_namespace_safe_name(name)

    original_description = install_contract._read_skill_description(text)
    safe_description = scaffold_mod.CopilotScaffoldRenderer.loader_safe_description(
        original_description
    )
    if safe_description == original_description:
        return text

    new_fm = _replace_description_field(fm, safe_description)
    note = (
        "> **Full description** (Copilot's skill loader caps a frontmatter "
        "`description` at 1024 characters; the summary above is shortened — "
        "this is the complete original text, preserved so no routing/trigger "
        "guidance is lost):\n"
        ">\n"
        f"> {original_description}\n\n"
    )
    return new_fm + note + body


def _copy_skills(source_root: Path, output_dir: Path) -> None:
    """Copy every `skills/*` directory (public skills AND shared private
    infra such as `skills/_common`, which other skills' Python imports
    depend on) into `.github/skills/`, applying the loader-compat render only
    to `SKILL.md` files. Mirrors `build_codex_plugin._copy_skills`'s
    unfiltered directory walk."""
    skills_src = source_root / "skills"
    skills_dst = output_dir / ".github" / "skills"
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
                    render_copilot_skill_md(entry.read_text(encoding="utf-8")),
                    encoding="utf-8",
                )
            else:
                dst.write_bytes(entry.read_bytes())


def _render_agents(source_root: Path, output_dir: Path) -> None:
    """Render jig's 3 canonical `agents/*.md` role prompts into Copilot's
    committed custom-agent form (slice 113-03): `.github/agents/<name>.
    agent.md`, mirroring `_copy_skills`'s "read canonical source, render, and
    write into the Copilot-shaped tree" pattern. Reuses the SAME source
    `agents/` directory the Claude/Codex builders read — no forked agent
    source, matching `_render_codex_agent_templates`'s own precedent."""
    agents_src = source_root / "agents"
    if not agents_src.is_dir():
        return
    agents_dst = output_dir / ".github" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    for agent in sorted(agents_src.glob("*.md")):
        dst = agents_dst / scaffold_mod.CopilotScaffoldRenderer.copilot_agent_file_name(
            agent.name
        )
        dst.write_text(
            scaffold_mod.CopilotScaffoldRenderer.render_copilot_agent(agent),
            encoding="utf-8",
        )


def _write_manifest(output_dir: Path, version: str) -> None:
    """Write `.plugin/plugin.json` — the minimal manifest shape spike 113-01
    AC1 verified against the shipped Copilot CLI: `{name, version,
    description[, mcpServers]}` (jig ships no MCP server, so that key is
    omitted). Mirrors `plugins/computer-use/.plugin/plugin.json`'s observed
    shape."""
    payload = {
        "name": "jig",
        "version": version,
        "description": _COPILOT_DESCRIPTION,
    }
    dst = output_dir / ".plugin" / "plugin.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _validate_output_dir(source_root: Path, output_dir: Path) -> tuple[bool, str]:
    """Refuse unsafe output dirs (mirrors build_claude_plugin/build_codex_plugin):
    the source root itself, any source-owned runtime path, or an ancestor of
    the source root. An output inside the source tree is allowed only under
    `hosts/` or `dist/` (the committed-package / release-zip homes)."""
    if output_dir == source_root:
        return False, "output directory must not be the source root"
    if source_root in output_dir.parents:
        source_owned_roots = {
            source_root / ".claude-plugin",
            source_root / ".codex-plugin",
            source_root / "agents",
            source_root / "hooks",
            source_root / "skills",
            source_root / "templates",
            source_root / "scripts",
            source_root / "docs",
            source_root / ".github",
        }
        if not (
            _is_relative_to(output_dir, source_root / "hosts")
            or _is_relative_to(output_dir, source_root / "dist")
        ):
            return (
                False,
                "output directory inside the source tree must be under "
                "hosts/ or dist/",
            )
        if output_dir in source_owned_roots or any(
            root in output_dir.parents for root in source_owned_roots
        ):
            return False, "output directory must not be a source-owned runtime path"
    if output_dir in source_root.parents:
        return False, "output directory must not be an ancestor of the source root"
    return True, ""


def build(source_root: Path, output_dir: Path, out=None) -> int:
    """Build the Copilot package at `output_dir` from `source_root`.

    Returns 0 on success, 1 on failure (missing manifest / unsafe output).
    Signature mirrors `build_claude_plugin.build` (`out=None` progress sink)."""
    if out is None:
        out = sys.stdout
    source_root = source_root.resolve()
    output_dir = output_dir.resolve()

    # The version source of truth is the SAME manifest build_claude_plugin
    # requires — jig's Claude and Codex manifests already carry the identical
    # version value (kept in lockstep by hand today); reusing it avoids a
    # THIRD parallel root-level source manifest for a walking-skeleton slice
    # whose only manifest fields are {name, version, description}.
    claude_manifest = source_root / ".claude-plugin" / "plugin.json"
    if not claude_manifest.is_file():
        out.write(f"ERROR: missing {claude_manifest}\n")
        return 1

    valid_output, reason = _validate_output_dir(source_root, output_dir)
    if not valid_output:
        out.write(f"ERROR: unsafe output directory: {reason}: {output_dir}\n")
        return 1

    try:
        version = json.loads(claude_manifest.read_text()).get("version", "")
    except json.JSONDecodeError as exc:
        out.write(f"ERROR: {claude_manifest} is not valid JSON: {exc}\n")
        return 1
    if not version:
        out.write(f"ERROR: {claude_manifest} has no non-empty 'version' field\n")
        return 1

    # Atomic-enough replace for a repeatable build: wipe a stale tree fully so
    # it is replaced, not merged (mirrors build_claude_plugin/build_codex_plugin).
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    _copy_skills(source_root, output_dir)
    _render_agents(source_root, output_dir)
    _write_manifest(output_dir, version)

    out.write(f"OK: built Copilot plugin at {output_dir}\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_copilot_plugin.py",
        description="materialize jig's Copilot CLI plugin package",
    )
    parser.add_argument(
        "--source-root",
        default=str(ROOT),
        help="path to jig's source root (default: repo root)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="output package directory (default: <source-root>/hosts/copilot)",
    )
    return parser


def main(argv: list[str]) -> int:
    ns = _build_parser().parse_args(argv[1:])
    source_root = Path(ns.source_root)
    output_dir = (
        Path(ns.output_dir)
        if ns.output_dir
        else source_root / "hosts" / "copilot"
    )
    return build(source_root=source_root, output_dir=output_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
