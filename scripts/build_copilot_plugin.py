"""
build_copilot_plugin.py — slice 113-02 (renderer-and-skeleton).

Materializes jig's **Copilot CLI plugin package** at `hosts/copilot/` from
canonical source. Per ADR-0061 (extending ADR-0018's tri-host pattern to a
third committed host) the repository root stays canonical source and
`hosts/copilot/` is the clean, directly-installable payload:
`copilot plugin install ramboz/jig:hosts/copilot` — a repo-subdirectory
install, no build step and no separate marketplace (spike 113-01 AC1).

Scope note (113-02 shipped a **walking skeleton**; 113-03 grew it by custom
agents; 113-04 grew it by ADVISORY hook translation; 113-05 grows it by
ENFORCING hooks + the permissions floor + a hook-schema correction): skills,
the plugin manifest, `agents/*.md`, the advisory hooks (session
git-freshness, boundary-change-warn, entry-gate-nudge) AND now the 3
ENFORCING hooks (spec-gate, secret-scan, and the permissions-floor
destructive-command guard) ship here, rendered into `.github/hooks/*.json` +
their bash/python scripts under `.github/hooks/scripts/`, fronted by
`copilot_hook_adapter.py`.

PERMISSIONS FLOOR RESHAPE (113-05, owner-directed correction): an EARLIER
version of this slice rendered the floor as `.github/copilot/settings.json`
(`deniedTools`, translated via Copilot's `--allow-tool`/`--deny-tool`
CLI-flag pattern syntax) — the owner corrected this after confirming
(authoritative GitHub docs + a live probe) that Copilot has NO persistent,
repo-committable tool-deny mechanism at all: `copilot help config`'s own
authored list of PERSISTED settings.json keys has no tool-allow/deny entry
(only `allowedUrls`/`deniedUrls`, plus `hooks`); `--deny-tool` is
SESSION-scoped only. A `deniedTools` settings.json key would have been a
DEAD FILE. The floor now ships as `.github/hooks/jig-permissions-floor.json`
— a real ENFORCING `preToolUse` hook fronting `copilot_permissions_floor.py`
(a standalone Python module, mirroring `copilot_hook_adapter.py`'s own
design) that pattern-matches the shell command against ALL 8 of
`_PERMISSIONS_DENY_DEFAULTS` (a superset of what Copilot's OWN `shell()`
permission-pattern syntax could faithfully express — see
`scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook`'s and
`copilot_permissions_floor.py`'s own docstrings for the full history and
evidence trail) and denies (`exit 2`) a match.

SCHEMA CORRECTION (113-05): 113-04 rendered `.github/hooks/*.json` in
Claude's OWN nested shape (`{event: [{matcher?, hooks:[{type, command,
timeout}]}]}`), which is NOT what Copilot's loader reads. The AUTHORITATIVE
on-disk schema (GitHub's own hooks reference, re-verified against the
installed CLI 1.0.86-0's `copilot help` output) is `{"version": 1, "hooks":
{"<camelCaseEvent>": [<flat entry: matcher?, type, bash, timeoutSec?>]}}` —
see `scaffold.render_copilot_hook_file`'s docstring. Fixed here for every
hook this builder renders, advisory and enforcing alike, since the bug
would otherwise have made NONE of them loadable.

Honest framing of what "hook translation" means (compliance review fix,
113-04; RE-CONFIRMED 113-05): the CONFIG-level translation is real and
exercised — `CLAUDE_TO_COPILOT_EVENTS` (Claude PascalCase -> Copilot
camelCase event keys), the hook-matcher tool-name map, and
`build_hook_command`'s command wrapping all run at BUILD TIME and shape
what actually ships. The RUNTIME INPUT adapter (`copilot_hook_adapter.py`)
is also real and exercised — it re-shapes Copilot's camelCase stdin JSON
into what the unmodified jig scripts read, at HOOK-FIRE TIME. As of 113-05,
the adapter's ENFORCING mode (`--enforce`) also preserves the target
script's exit code and emits a `permissionDecision: deny` body on a
non-zero one — but via a mapping the adapter DUPLICATES (drift-guarded by a
test), not by calling `CopilotScaffoldRenderer.translate_hook_protocol` at
runtime; that method remains unwired repo-wide (Claude's and Codex's own
copies are equally never called — see `skills/scaffold-init/scaffold.py`'s
docstring, and the adapter's own module docstring for why it stays
standalone rather than importing `scaffold.py`). The 3 advisory hooks still
only ever emit `additionalContext`, which round-trips through the adapter
unmodified; the harmless, documented residual that `continue` also passes
through un-stripped remains — see `test_copilot_hook_adapter.py`'s
`ShippedAdvisoryOutputThroughAdapterTests`. `build_copilot_plugin._JIG_HOOK_INVENTORY`
is the mapped-or-unmappable inventory (AC2) for every OTHER jig hook
(telemetry, skill-trace, …); most remain MAPPABLE-but-not-yet-shipped,
rendered in 113-06 (AC6 — remaining-advisory-hook parity), and 2 (telemetry's `Task` matcher,
skill-trace's `Skill` matcher) are recorded UNMAPPABLE (no confirmed
Copilot tool-call analogue). Skill bodies get the `${CLAUDE_PLUGIN_ROOT}`
path rewrite too (113-04 AC4) — see
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

# Slice 113-05 (enforcing-hooks-and-permissions) — the 2 ENFORCING hooks
# (jig's blocking, `exit 2`-on-block PreToolUse gates): spec-gate and
# secret-scan. Same tuple shape as `_COPILOT_ADVISORY_HOOKS`; rendered
# through `render_copilot_hook_file(..., enforcing=True)` (below) so the
# adapter invocation preserves the target script's exit code instead of
# masking it to 0.
_COPILOT_ENFORCING_HOOKS: tuple[tuple[str, str, str], ...] = (
    ("PreToolUse", "jig-spec-gate.sh", "jig-spec-gate"),
    ("PreToolUse", "jig-secret-scan.sh", "jig-secret-scan"),
)

# The 2 enforcing hooks' bash wrappers, shipped VERBATIM (same rationale as
# `_COPILOT_HOOK_SCRIPT_FILES`). Neither needs a `lib/` helper of its own:
# `jig-secret-scan.sh` is self-contained inline Python; `jig-spec-gate.sh`
# imports `gate_telemetry` from `skills/_common/` (already shipped by
# `_copy_skills`, reached via the SAME `../../skills` climb
# `_copy_copilot_hook_scripts`'s docstring already establishes for
# `jig-entry-gate.sh`) — no NEW lib file to copy.
_COPILOT_ENFORCING_HOOK_SCRIPT_FILES: tuple[str, ...] = (
    "jig-spec-gate.sh",
    "jig-secret-scan.sh",
)


def _write_copilot_hooks(source_root: Path, output_dir: Path) -> None:
    """Render the advisory + enforcing hooks into `.github/hooks/<stem>.json`
    (one file per hook — AC2). Silently does nothing for a hook whose source
    entry has gone missing (`render_copilot_hook_file` returns `None`)
    rather than writing an empty/garbage file; `hooks/hooks.json` itself
    missing (should never happen in this repo) is likewise a silent no-op,
    matching `_write_codex_hooks`'s own precedent for a missing source
    file."""
    source_hooks_path = source_root / "hooks" / "hooks.json"
    if not source_hooks_path.is_file():
        return
    source_hooks = json.loads(source_hooks_path.read_text())
    hooks_dst = output_dir / ".github" / "hooks"

    def _render(claude_event: str, script_name: str, stem: str, *, enforcing: bool) -> None:
        payload = scaffold_mod.render_copilot_hook_file(
            source_hooks,
            claude_event,
            script_name,
            renderer_cls=scaffold_mod.CopilotScaffoldRenderer,
            enforcing=enforcing,
        )
        if payload is None:
            return
        hooks_dst.mkdir(parents=True, exist_ok=True)
        (hooks_dst / f"{stem}.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    for claude_event, script_name, stem in _COPILOT_ADVISORY_HOOKS:
        _render(claude_event, script_name, stem, enforcing=False)
    for claude_event, script_name, stem in _COPILOT_ENFORCING_HOOKS:
        _render(claude_event, script_name, stem, enforcing=True)


def _copy_copilot_hook_scripts(source_root: Path, output_dir: Path) -> None:
    """Copy the advisory + enforcing hooks' bash wrappers + their `lib/*.py`
    helpers into `.github/hooks/scripts/` verbatim, pinning each `.sh` to
    `0o755` (mirrors `_rewrite_codex_hook_scripts`'s mode-pinning, minus the
    body rewrite Codex needs and Copilot does not — see the module
    docstring).

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
    all_files = (
        _COPILOT_HOOK_SCRIPT_FILES
        + _COPILOT_ENFORCING_HOOK_SCRIPT_FILES
        + _COPILOT_HOOK_LIB_FILES
    )
    for rel_name in all_files:
        src = scripts_src / rel_name
        if not src.is_file():
            continue
        dst = scripts_dst / rel_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        if rel_name.endswith(".sh"):
            dst.chmod(0o755)

    # `copilot_hook_adapter.py` (113-04) and `copilot_permissions_floor.py`
    # (113-05) both ship the SAME way: standalone Python modules copied
    # verbatim from `skills/scaffold-init/` (their canonical source
    # location; each is Copilot-only and never touches
    # `hooks/scripts/*.sh` / `lib/*.py`) into this SAME scripts directory,
    # so their rendered relative command paths resolve.
    for standalone_filename in (
        scaffold_mod.CopilotScaffoldRenderer.COPILOT_HOOK_ADAPTER_FILENAME,
        scaffold_mod.CopilotScaffoldRenderer.COPILOT_PERMISSIONS_FLOOR_FILENAME,
    ):
        src = source_root / "skills" / "scaffold-init" / standalone_filename
        if not src.is_file():
            continue
        dst = scripts_dst / standalone_filename
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def _write_permissions_floor_hook(output_dir: Path) -> None:
    """Slice 113-05 AC3 (owner reshape) — render the destructive-command
    permissions FLOOR as an ENFORCING `preToolUse` hook,
    `.github/hooks/jig-permissions-floor.json`, REPLACING an earlier
    (dead — Copilot cannot persist a tool-deny setting) `.github/copilot/
    settings.json` attempt this same slice tried. See
    `scaffold.CopilotScaffoldRenderer.render_permissions_floor_hook`'s own
    docstring for the schema and matcher, and
    `copilot_permissions_floor.py`'s module docstring for the guard
    script's own design."""
    payload = scaffold_mod.CopilotScaffoldRenderer.render_permissions_floor_hook()
    hooks_dst = output_dir / ".github" / "hooks"
    hooks_dst.mkdir(parents=True, exist_ok=True)
    (hooks_dst / "jig-permissions-floor.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


# Slice 113-05 AC2 — the mapped-or-unmappable inventory (ADR-0061: "every
# jig hook is either mapped to a Copilot event with equivalent enforcement,
# or explicitly recorded as unmappable with the residual documented"). One
# record per (event, matcher, script) registration in the REAL
# `hooks/hooks.json` — a script registered under more than one
# event/matcher gets one record per registration (e.g.
# `jig-decision-inflight.sh` is both a PostToolUse/AskUserQuestion
# registration, UNMAPPABLE, and a UserPromptSubmit registration, MAPPABLE
# — the SAME script degrades differently depending on which trigger fires).
#
# `source` is one of:
#   "hooks.json"    — a real (event, matcher, script) registration in the
#                     canonical `hooks/hooks.json`; `HookInventoryCoverageTests`
#                     cross-checks these against that file both ways (no
#                     undocumented registration, no stale inventory entry).
#   "copilot-only"  — a hook that exists ONLY in the Copilot package, with
#                     no Claude-format `hooks/hooks.json` entry to translate
#                     FROM (currently: the permissions-floor deny-hook,
#                     whose Claude-side equivalent is its native
#                     `permissions.deny` engine, not a jig hook script).
#                     Exempt from the hooks.json cross-check for the
#                     obvious reason there is nothing in hooks.json to
#                     cross-check it against — but still required to carry
#                     a known `status` and `notes`, same as every other
#                     entry.
#
# `status` is one of:
#   SHIPPED     — rendered + shipped in THIS package; verified by
#                 `HookInventoryCoverageTests.test_every_shipped_entry_is_actually_built`
#                 (scripts/test_build_copilot_plugin.py) against the
#                 build's own output, not just asserted here.
#   MAPPABLE    — a Copilot event (and matcher, if any) exist to render
#                 this hook the SAME way SHIPPED ones are, but it is not
#                 yet built into this package — an advisory nudge, not a
#                 gate, rendered in 113-06 (AC6 — remaining-advisory-hook parity).
#   UNMAPPABLE  — no confirmed Copilot analogue exists for the matcher/tool
#                 this hook keys on; `notes` documents the residual. The
#                 hook's nudge/telemetry does not fire under Copilot — a
#                 DOCUMENTED gap, never a silent one.
#
# `HookInventoryCoverageTests` reads the REAL `hooks/hooks.json` and asserts
# every (event, matcher, script) triple found there is represented among the
# `source == "hooks.json"` entries here (and vice versa) — so a hook added
# to `hooks.json` later without a matching inventory entry fails a test
# rather than silently falling through.
_JIG_HOOK_INVENTORY: tuple[dict, ...] = (
    {
        "source": "hooks.json",
        "event": "PreToolUse", "matcher": "Task", "script": "jig-telemetry.sh",
        "status": "UNMAPPABLE",
        "notes": (
            "no confirmed Copilot tool literally named \"Task\" fires under "
            "preToolUse; Copilot's own subagentStart/subagentStop HookType "
            "members (confirmed enum values) are a plausible future remap "
            "target for this telemetry's INTENT, but that would change "
            "which EVENT the hook fires under, not just translate its "
            "matcher spelling — a bigger step than this slice's render-layer "
            "translation scope, not attempted here"
        ),
    },
    {
        "source": "hooks.json",
        "event": "PreToolUse", "matcher": "Skill", "script": "jig-skill-trace.sh",
        "status": "UNMAPPABLE",
        "notes": (
            "no confirmed Copilot tool literally named \"Skill\" fires under "
            "preToolUse; Copilot's skill invocation is loader-driven, not a "
            "discrete hookable tool call"
        ),
    },
    {
        "source": "hooks.json",
        "event": "PreToolUse", "matcher": "Edit|Write|MultiEdit",
        "script": "jig-spec-gate.sh", "status": "SHIPPED",
        "notes": "enforcing (exit 2 blocks); 113-05",
    },
    {
        "source": "hooks.json",
        "event": "PreToolUse", "matcher": "Edit|Write|MultiEdit",
        "script": "jig-secret-scan.sh", "status": "SHIPPED",
        "notes": "enforcing (exit 2 blocks); 113-05",
    },
    {
        "source": "hooks.json",
        "event": "PreToolUse", "matcher": "Read", "script": "jig-context-check.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "PostToolUse", "matcher": "Edit|Write|MultiEdit",
        "script": "jig-post-edit-verify.sh", "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "PostToolUse", "matcher": "Edit|Write|MultiEdit",
        "script": "jig-boundary-change-warn.sh", "status": "SHIPPED",
        "notes": "advisory; 113-04",
    },
    {
        "source": "hooks.json",
        "event": "PostToolUse", "matcher": "Edit|Write|MultiEdit",
        "script": "jig-entry-gate.sh", "status": "SHIPPED",
        "notes": "advisory; 113-04",
    },
    {
        "source": "hooks.json",
        "event": "PostToolUse", "matcher": "AskUserQuestion",
        "script": "jig-decision-inflight.sh", "status": "UNMAPPABLE",
        "notes": (
            "no confirmed Copilot tool literally named \"AskUserQuestion\" "
            "fires under postToolUse; see this SAME script's "
            "UserPromptSubmit registration below, which IS mappable — this "
            "one trigger of the two is the degraded one, not the whole hook"
        ),
    },
    {
        "source": "hooks.json",
        "event": "SessionStart", "matcher": None, "script": "jig-context-check.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "SessionStart", "matcher": None, "script": "jig-project-orient.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "SessionStart", "matcher": None, "script": "jig-semantic-index.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "SessionStart", "matcher": None, "script": "jig-git-freshness.sh",
        "status": "SHIPPED", "notes": "advisory; 113-04",
    },
    {
        "source": "hooks.json",
        "event": "UserPromptSubmit", "matcher": None, "script": "jig-memory-scan.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "UserPromptSubmit", "matcher": None, "script": "jig-context-check.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "UserPromptSubmit", "matcher": None,
        "script": "jig-decision-inflight.sh", "status": "MAPPABLE",
        "notes": (
            "advisory; rendered in 113-06 (AC6 remaining-advisory-hook parity) — "
            "THIS registration IS mappable "
            "(userPromptSubmitted is a confirmed event, no matcher needed), "
            "unlike the PostToolUse/AskUserQuestion registration of the "
            "same script above"
        ),
    },
    {
        "source": "hooks.json",
        "event": "Stop", "matcher": None, "script": "jig-task-capture.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "Stop", "matcher": None, "script": "jig-decision-capture.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "hooks.json",
        "event": "Stop", "matcher": None, "script": "jig-claim-check.sh",
        "status": "MAPPABLE",
        "notes": "advisory; rendered in 113-06 (AC6 — remaining-advisory-hook parity)",
    },
    {
        "source": "copilot-only",
        "event": "PreToolUse", "matcher": "bash",
        "script": "copilot_permissions_floor.py", "status": "SHIPPED",
        "notes": (
            "enforcing (exit 2 blocks); 113-05 owner reshape of AC3 — NOT a "
            "translation of a hooks.json entry (Claude's equivalent is its "
            "native permissions.deny engine, not a jig hook script); "
            "replaces an earlier, dead .github/copilot/settings.json "
            "attempt (Copilot has no persistent, repo-committable tool-deny "
            "mechanism) with a real enforcing preToolUse hook that covers "
            "all 8 of _PERMISSIONS_DENY_DEFAULTS, including the 2 "
            "mid-string-wildcard force-push variants Copilot's own "
            "shell() permission-pattern syntax could not express"
        ),
    },
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
    _write_copilot_hooks(source_root, output_dir)
    _copy_copilot_hook_scripts(source_root, output_dir)
    _write_permissions_floor_hook(output_dir)
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
