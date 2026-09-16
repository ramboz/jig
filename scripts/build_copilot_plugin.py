"""
build_copilot_plugin.py — slice 113-02 (renderer-and-skeleton).

Materializes jig's **Copilot CLI plugin package** at `hosts/copilot/` from
canonical source. Per ADR-0061 (extending ADR-0018's tri-host pattern to a
third committed host) the repository root stays canonical source and
`hosts/copilot/` is the clean, directly-installable payload:
`copilot plugin install ramboz/jig:hosts/copilot` — a repo-subdirectory
install, no build step and no separate marketplace (spike 113-01 AC1).

Scope note (113-02 shipped a **walking skeleton**; 113-03 grew it by custom
agents; 113-04 grows it by hook translation): skills, the plugin manifest,
`agents/*.md`, and now the 3 ADVISORY hooks (session git-freshness,
boundary-change-warn, entry-gate-nudge) ship here, rendered into
`.github/hooks/*.json` + their bash/python scripts under
`.github/hooks/scripts/`, fronted by `copilot_hook_adapter.py`.

Honest framing of what "hook translation" means at THIS slice (compliance
review fix, 113-04): the CONFIG-level translation is real and exercised —
`CLAUDE_TO_COPILOT_EVENTS` (Claude PascalCase -> Copilot camelCase event
keys), the hook-matcher tool-name map, and `build_hook_command`'s command
wrapping all run at BUILD TIME and shape what actually ships. The RUNTIME
INPUT adapter (`copilot_hook_adapter.py`) is also real and exercised — it
re-shapes Copilot's camelCase stdin JSON into what the unmodified jig
scripts read, at HOOK-FIRE TIME. `CopilotScaffoldRenderer.
translate_hook_protocol` (the RESPONSE-schema half) is NOT exercised by
either of those: it is the Copilot override of a seam that is unwired
repo-wide (Claude's and Codex's own `translate_hook_protocol` are equally
never called at runtime today — see `skills/scaffold-init/scaffold.py`'s
docstring). The adapter forwards each advisory hook's child stdout
VERBATIM; nothing currently post-processes it to drop `continue` or map
`block_reason` -> `permissionDecision`. Wiring `translate_hook_protocol`'s
RUNTIME application into the adapter is 113-05 scope, deferred there
because only 113-05's enforcing hooks (spec-gate, review-evidence,
bug-closure) actually need a `permissionDecision` deny path — the 3
advisory hooks this slice ships only ever emit `additionalContext`, which
already round-trips through the adapter unmodified (Copilot's schema
accepts it under that same key; the harmless, documented residual is that
`continue` also passes through un-stripped — see
`test_copilot_hook_adapter.py`'s `ShippedAdvisoryOutputThroughAdapterTests`).
The full mapped-or-unmappable inventory of every OTHER jig hook (telemetry,
skill-trace, …) and the release zip are still 113-05/06 scope. Skill bodies
now get the `${CLAUDE_PLUGIN_ROOT}` path rewrite too (113-04 AC4) — see
`scaffold.CopilotScaffoldRenderer.rewrite_skill_md_paths` for the
best-hypothesis, not-verified-live caveat. Agent prompt bodies still ship
Claude-native (no path rewriting) — none of the 3 canonical agents reference
`${CLAUDE_PLUGIN_ROOT}`, so there is nothing to rewrite there today; a
documented gap only if that ever changes.

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
                text = render_copilot_skill_md(entry.read_text(encoding="utf-8"))
                # Slice 113-04 AC4: rewrite any `${CLAUDE_PLUGIN_ROOT}/…`
                # runtime path to the plugin-root-relative Copilot spelling
                # (closes the gap 113-02 documented and deferred). A no-op
                # for the many skill bodies with no such reference.
                text = scaffold_mod.CopilotScaffoldRenderer.rewrite_skill_md_paths(text)
                dst.write_text(text, encoding="utf-8")
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


# Slice 113-04 (advisory-hooks) — the 3 hooks this slice renders: the
# `additionalContext`-emitting nudges (session git-freshness,
# boundary-change-warn, entry-gate-nudge), matching the slice's explicit
# scope (enforcing hooks — spec-gate/review-evidence/bug-closure — are
# 113-05's mapped-or-unmappable inventory, not this slice's). Each tuple is
# (Claude hook event, source script filename, output file stem); the stem
# becomes `.github/hooks/<stem>.json`.
_COPILOT_ADVISORY_HOOKS: tuple[tuple[str, str, str], ...] = (
    ("SessionStart", "jig-git-freshness.sh", "jig-git-freshness"),
    ("PostToolUse", "jig-boundary-change-warn.sh", "jig-boundary-change-warn"),
    ("PostToolUse", "jig-entry-gate.sh", "jig-entry-gate"),
)

# The scripts (and their `lib/` helpers) the 3 advisory hooks need, shipped
# VERBATIM — byte-identical, no rewriting — matching spike 113-01 AC5's
# design ("referencing the existing hooks/scripts/jig-*.sh bash scripts").
# ALL hook-schema translation lives in the emitted `.github/hooks/*.json`
# (event name, matcher, command path) — never in the script bodies
# themselves, so Claude/Codex's own copies of these same canonical files stay
# byte-for-byte unaffected by anything this builder does.
_COPILOT_HOOK_SCRIPT_FILES: tuple[str, ...] = (
    "jig-git-freshness.sh",
    "jig-boundary-change-warn.sh",
    "jig-entry-gate.sh",
)
_COPILOT_HOOK_LIB_FILES: tuple[str, ...] = (
    "lib/git_freshness.py",
    "lib/entry_gate.py",
    "lib/read_attribution.py",
    "lib/protected_paths.py",
)


def _write_copilot_hooks(source_root: Path, output_dir: Path) -> None:
    """Render the 3 advisory hooks into `.github/hooks/<stem>.json` (one file
    per hook — AC2). Silently does nothing for a hook whose source entry has
    gone missing (`render_copilot_hook_file` returns `None`) rather than
    writing an empty/garbage file; `hooks/hooks.json` itself missing (should
    never happen in this repo) is likewise a silent no-op, matching
    `_write_codex_hooks`'s own precedent for a missing source file."""
    source_hooks_path = source_root / "hooks" / "hooks.json"
    if not source_hooks_path.is_file():
        return
    source_hooks = json.loads(source_hooks_path.read_text())
    hooks_dst = output_dir / ".github" / "hooks"
    for claude_event, script_name, stem in _COPILOT_ADVISORY_HOOKS:
        payload = scaffold_mod.render_copilot_hook_file(
            source_hooks,
            claude_event,
            script_name,
            renderer_cls=scaffold_mod.CopilotScaffoldRenderer,
        )
        if payload is None:
            continue
        hooks_dst.mkdir(parents=True, exist_ok=True)
        (hooks_dst / f"{stem}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )


def _copy_copilot_hook_scripts(source_root: Path, output_dir: Path) -> None:
    """Copy the 3 advisory hooks' bash wrappers + their `lib/*.py` helpers
    into `.github/hooks/scripts/` verbatim, pinning each `.sh` to `0o755`
    (mirrors `_rewrite_codex_hook_scripts`'s mode-pinning, minus the body
    rewrite Codex needs and Copilot does not — see the module docstring).

    Placement note: nested under `.github/`, unlike Claude/Codex's
    plugin-root-level `hooks/scripts/`. This is deliberate, not
    inconsistent: `jig-entry-gate.sh` locates its sibling `_common` helpers
    via a `../../skills` climb relative to its OWN directory
    (`hooks/scripts/../../skills`); nesting Copilot's scripts under
    `.github/hooks/scripts/` keeps that SAME unmodified relative climb
    landing on `.github/skills` — exactly where `_copy_skills` already ships
    `_common` — with zero changes to the shared script.

    Also copies `copilot_hook_adapter.py` — the INPUT-payload half of the
    hook-protocol translation layer (AC1) — from `skills/scaffold-init/`
    (its canonical source location; it is Copilot-only and never touches
    `hooks/scripts/*.sh` / `lib/*.py`) into the SAME directory as the
    scripts it fronts, so `CopilotScaffoldRenderer.build_hook_command`'s
    relative command path (`.github/hooks/scripts/copilot_hook_adapter.py`)
    resolves."""
    scripts_src = source_root / "hooks" / "scripts"
    scripts_dst = output_dir / ".github" / "hooks" / "scripts"
    for rel_name in _COPILOT_HOOK_SCRIPT_FILES + _COPILOT_HOOK_LIB_FILES:
        src = scripts_src / rel_name
        if not src.is_file():
            continue
        dst = scripts_dst / rel_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        if rel_name.endswith(".sh"):
            dst.chmod(0o755)

    adapter_src = (
        source_root / "skills" / "scaffold-init"
        / scaffold_mod.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_FILENAME
    )
    if adapter_src.is_file():
        dst = scripts_dst / scaffold_mod.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_FILENAME
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(adapter_src.read_bytes())


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
    _write_copilot_hooks(source_root, output_dir)
    _copy_copilot_hook_scripts(source_root, output_dir)
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
