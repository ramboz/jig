"""
scaffold_contract.py — slice 047-02 (scaffold-contract-validator).

The single validator-facing description of jig's **scaffold-target**
install contract: the `.claude/` tree (plus `scaffold.json` and the docs)
a project gets when jig is installed via `scaffold-init --with-machinery`.

This is the parallel of slice 047-01's `install_contract.py` (the
plugin/release contract). The two contracts genuinely differ — the
scaffold target carries a *tier-gated subset* of the skills under a
`.claude/skills/jig-*` layout, references its helpers by **local**
`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<helper>` paths (spec
046-01), registers hooks against `${CLAUDE_PROJECT_DIR}/.claude/hooks/...`
in `settings.json`, and records install state in `scaffold.json` — so the
scaffold-specific helpers live here rather than being bolted onto the
plugin contract. The shared, mode-agnostic plumbing (hook-command
iteration) is reused from `install_contract`, not duplicated.

Design constraints (mirror `install_contract.py`):

- **stdlib-only.** No third-party imports, no network, fast enough for CI
  and the local TDD loop. Does NOT import `scaffold.py` (which pulls in
  `_common.atomic_io` and is not on `scripts/`'s import path); the one
  source of truth it mirrors — the tier tables — is restated here and
  pinned equal by `test_scaffold_contract.py` (the restate-plus-
  consistency-test convention 047-01 established).
- **Pure.** The helpers take a project-root `Path` (or already-parsed
  data) and return a list of diagnostics — they never print, never exit.
  Callers (`verify_install.py` scaffold mode) own I/O and exit codes.
- **Actionable diagnostics (AC #4 / DoD).** Every failure names the
  offending path (skill dir / helper / hook script / manifest field /
  doc + missing link target) AND the violated rule, so a reader can fix
  it without reading the validator source.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

# Shared, mode-agnostic plumbing from the plugin/release contract (047-01):
# the hooks.json / settings.json inner shape is identical, so command
# iteration is reused rather than re-implemented.
import install_contract

# ---------------------------------------------------------------------------
# Tier tables (restated — source of truth: scaffold._TIER_SKILLS)
# ---------------------------------------------------------------------------
#
# scaffold.py (skills/scaffold-init/scaffold.py) is the source of truth for
# the per-tier skill inventory (ADR-0007). This module is stdlib-only and
# does NOT import scaffold.py, so the table is restated here and pinned equal
# to scaffold._TIER_SKILLS by test_scaffold_contract.py::
# TierTableConsistencyTests — the same restate-plus-consistency-test
# convention install_contract.EXPECTED_SKILLS / verify_install.
# _EXPECTED_HOOK_SCRIPTS already use.
_TIER_SKILLS: dict[str, list[str]] = {
    "tier-0": [
        "scaffold-init",
        "memory-sync",
        "spec-workflow",
        "independent-review",
        "migrate",
        "vision-elicitation",
        "contracts",
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
        "code-health",
    ],
    "tier-2": [],
}


def expected_scaffold_skills(scaffold_json_data: dict) -> set[str]:
    """Return the set of `jig-<skill>` directory names a scaffolded target is
    expected to carry, derived from its `scaffold.json` (AC #1, tier-gated).

    Preference order:
      1. `installed_tiers` → every skill in `_TIER_SKILLS[tier]` for each
         installed tier (the canonical derivation, ADR-0007);
      2. fallback to `installed_skills` (the `<tier>/<skill>` list) when
         `installed_tiers` is absent — still tracks the manifest.

    An unknown tier contributes nothing (a forward-compat tolerance — a
    manifest naming a tier this validator hasn't heard of shouldn't crash
    the expectation; the skill-presence diagnostics still cover what we do
    know about)."""
    tiers = scaffold_json_data.get("installed_tiers")
    if isinstance(tiers, list) and tiers:
        out: set[str] = set()
        for tier in tiers:
            for skill in _TIER_SKILLS.get(tier, []):
                out.add(f"jig-{skill}")
        return out
    # Fallback: derive from the per-skill list (`<tier>/<skill>`).
    out = set()
    for entry in scaffold_json_data.get("installed_skills") or []:
        if isinstance(entry, str) and "/" in entry:
            out.add(f"jig-{entry.split('/', 1)[1]}")
    return out


# ---------------------------------------------------------------------------
# Local helper-path contract (spec 046-01)
# ---------------------------------------------------------------------------
#
# In a scaffolded target, a SKILL.md references its helpers by the LOCAL path
#     ${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<helper>
# because the machinery is copied under .claude/ (the env var
# ${CLAUDE_PLUGIN_ROOT} is unset in a scaffolded project). spec 046-01
# rewrites every `${CLAUDE_PLUGIN_ROOT}/skills/<name>/` helper path to that
# local form. A surviving `${CLAUDE_PLUGIN_ROOT}/skills/...` path in a copied
# SKILL.md therefore means the rewrite was missed — it is a stale, broken
# helper path and must fail verification (AC #1).
#
# NOTE the precision: only the `.../skills/...` *helper path* is stale. A
# bare `${CLAUDE_PLUGIN_ROOT}` prose mention (e.g. "in plugin-only mode the
# machinery lives under ${CLAUDE_PLUGIN_ROOT}") is legitimate and must NOT
# false-fail — real scaffolded jig SKILL.md bodies (jig-migrate,
# jig-scaffold-init) carry exactly such prose. So the marker is the
# path-shaped prefix, not the bare token.

# A stale plugin-root *helper path* in a copied SKILL.md (the thing 046-01
# rewrites away).
_STALE_PLUGIN_SKILL_PATH_RE = re.compile(
    r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/[A-Za-z0-9_-]+/"
)

# A LOCAL helper reference (the post-046-01 shape). Captures the
# `jig-<name>/<...>.py` tail so the closure check can resolve it on disk.
# Both quoted and unquoted forms appear in SKILL.md bash recipes.
_LOCAL_HELPER_REF_RE = re.compile(
    r"\$\{CLAUDE_PROJECT_DIR\}/\.claude/skills/(jig-[A-Za-z0-9_-]+/"
    r"[A-Za-z0-9_./-]+?\.py)"
)


def _iter_skill_dirs(skills_dir: Path) -> Iterable[Path]:
    """Yield each copied user-facing skill dir (`jig-*`) under `skills_dir`,
    sorted for deterministic diagnostics."""
    for child in sorted(skills_dir.iterdir()):
        if child.is_dir() and child.name.startswith("jig-"):
            yield child


def scaffold_skill_problems(project_root: Path) -> list[str]:
    """Validate the copied-skill helper closure for a scaffolded target
    (AC #1). Returns diagnostics (empty == valid).

    Three rules, each naming the offending path + the rule (AC #4):

    1. **Expected-skill presence.** Every `jig-<skill>` the target's
       `scaffold.json` says should be installed (tier-gated via
       `expected_scaffold_skills`) has a `SKILL.md` under
       `.claude/skills/`. A missing one is named.
    2. **Helper closure.** Every local helper path a copied SKILL.md
       references (`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<x>.py`)
       resolves to a file on disk — including cross-skill references (one
       skill pointing at another skill's helper). A dangling reference names
       the referencing skill + the missing helper.
    3. **No stale plugin-root helper path.** A copied SKILL.md must not still
       carry a `${CLAUDE_PLUGIN_ROOT}/skills/...` helper path — spec 046-01
       rewrites those to local paths in scaffold mode. A survivor is named
       (a bare `${CLAUDE_PLUGIN_ROOT}` prose mention is deliberately
       tolerated — only the path-shaped form is stale)."""
    skills_dir = project_root / ".claude" / "skills"
    if not skills_dir.is_dir():
        return [
            f".claude/skills/ dir missing at {skills_dir} "
            "(scaffold-mode skills not copied)"
        ]

    problems: list[str] = []

    # Rule 1 — expected (tier-gated) skill set is present.
    manifest = _read_scaffold_manifest(project_root)
    for expected in sorted(expected_scaffold_skills(manifest)):
        if not (skills_dir / expected / "SKILL.md").is_file():
            problems.append(
                f".claude/skills/{expected}: missing SKILL.md "
                "(expected per scaffold.json installed tiers/skills)"
            )

    # Rules 2 + 3 — per copied skill, closure + stale-path.
    for skill_dir in _iter_skill_dirs(skills_dir):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        body = skill_md.read_text()

        # Rule 3 — stale plugin-root helper path.
        if _STALE_PLUGIN_SKILL_PATH_RE.search(body):
            problems.append(
                f".claude/skills/{skill_dir.name}/SKILL.md: references a "
                "stale '${CLAUDE_PLUGIN_ROOT}/skills/<name>/' helper path; "
                "scaffold-mode SKILL.md must use the local "
                "'${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/' path "
                "(spec 046-01)"
            )

        # Rule 2 — local helper references resolve on disk.
        for rel in sorted(set(_LOCAL_HELPER_REF_RE.findall(body))):
            # `rel` is `jig-<name>/<...>.py`; resolve under .claude/skills/.
            if not (skills_dir / rel).is_file():
                problems.append(
                    f".claude/skills/{skill_dir.name}/SKILL.md: referenced "
                    f"helper '.claude/skills/{rel}' does not exist "
                    "(broken local helper path — copied-skill helper closure)"
                )
    return problems


# ---------------------------------------------------------------------------
# Generated settings.json contract (AC #2)
# ---------------------------------------------------------------------------
#
# In scaffold mode every jig-managed hook command MUST be of the exact shape
#     bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/<name>
# (the plugin-mode `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>` rewritten by
# scaffold._rewrite_hook_command), and `<name>` must exist as a copied script
# under `.claude/hooks/scripts/`.

_SCAFFOLD_HOOK_COMMAND_PREFIX = (
    "bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/"
)


def _is_jig_managed(entry: dict) -> bool:
    """An entry counts as jig-managed iff its `metadata.managed_by_jig` is
    truthy (mirrors scaffold._is_jig_managed)."""
    return bool((entry.get("metadata") or {}).get("managed_by_jig"))


def validate_scaffold_settings(project_root: Path) -> list[str]:
    """Validate `.claude/settings.json` coherence for a scaffolded target
    (AC #2). Returns diagnostics (empty == valid).

    Stronger than "at least one jig-managed entry exists" (the pre-047-02
    check). It requires:

    - settings.json present + parseable;
    - at least one jig-managed (`metadata.managed_by_jig`) hook entry — a
      scaffold with no jig registration didn't install its hooks;
    - every jig-managed hook command uses the scaffold-mode invocation shape
      `bash ${CLAUDE_PROJECT_DIR}/.claude/hooks/scripts/<name>` (no bare
      name, no leftover `${CLAUDE_PLUGIN_ROOT}` prefix);
    - every referenced `<name>` script exists under `.claude/hooks/scripts/`
      (a dangling hook-script reference is named).

    Each diagnostic names the offending entry/script + the rule (AC #4)."""
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.is_file():
        return [f"settings.json missing at {settings_path}"]
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"settings.json is not valid JSON: {exc}"]

    scripts_dir = project_root / ".claude" / "hooks" / "scripts"
    problems: list[str] = []

    # Build a jig-managed-only view of the hooks block, then reuse
    # install_contract._iter_hook_commands (047-01) to walk its commands —
    # settings.json and hooks.json share the same `{hooks: {event: [{hooks:
    # [{command}]}]}}` inner shape, so the iteration plumbing is reused, not
    # re-implemented. Non-jig entries are the user's / a third party's and are
    # out of scope for the scaffold contract (a scaffold only owns its own
    # registration).
    hooks = data.get("hooks") or {}
    jig_only_hooks: dict = {}
    have_jig_entry = False
    for event, entries in hooks.items():
        kept = [
            entry
            for entry in (entries or [])
            if isinstance(entry, dict) and _is_jig_managed(entry)
        ]
        if kept:
            have_jig_entry = True
            jig_only_hooks[event] = kept
    if not have_jig_entry:
        problems.append(
            "settings.json has no jig-managed hook entries "
            "(metadata.managed_by_jig marker missing on every entry) — "
            "scaffold-mode hooks were not registered"
        )

    for event, command in install_contract._iter_hook_commands(
        {"hooks": jig_only_hooks}
    ):
        if not command.startswith(_SCAFFOLD_HOOK_COMMAND_PREFIX):
            problems.append(
                f"settings.json {event} jig-managed hook command "
                f"{command!r}: must invoke "
                f"'{_SCAFFOLD_HOOK_COMMAND_PREFIX}<name>' "
                "(scaffold-mode shape — no bare names, no "
                "${CLAUDE_PLUGIN_ROOT} prefix)"
            )
            continue
        name = command[len(_SCAFFOLD_HOOK_COMMAND_PREFIX):].strip()
        if not name or "/" in name or " " in name:
            problems.append(
                f"settings.json {event} jig-managed hook command "
                f"{command!r}: expected a single "
                f"'{_SCAFFOLD_HOOK_COMMAND_PREFIX}<name>' basename"
            )
            continue
        if not (scripts_dir / name).is_file():
            problems.append(
                f"settings.json {event} jig-managed hook {name!r}: "
                f"references a hook script that does not exist at "
                f"{scripts_dir / name} (dangling scaffold hook-script "
                "reference)"
            )
    return problems


# ---------------------------------------------------------------------------
# scaffold.json metadata contract (AC #3)
# ---------------------------------------------------------------------------
#
# Fields scaffold-mode consumers rely on. `jig_version` is the one spec
# 046-02 fixed (derived from the plugin manifest — the single source of
# truth); the others (`installed_tiers` / `installed_skills` / `scaffold_mode`
# / `project_name`) gate the tier-aware copy and the migrate upgrade path.

SCAFFOLD_MANIFEST_REQUIRED_FIELDS: tuple[str, ...] = (
    "jig_version",
    "project_name",
    "scaffold_mode",
)

# A `jig_version` that is still the unrendered template placeholder is a
# stale value, not a real version — reject it explicitly (spec 046-02).
_UNRENDERED_PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


def validate_scaffold_manifest(data: dict) -> list[str]:
    """Validate a parsed `scaffold.json` (AC #3). Returns diagnostics
    (empty == valid). Mirrors install_contract.validate_plugin_manifest's
    shape — required-field + value sanity, every diagnostic naming the field
    and the file (AC #4).

    Rules:
    - non-empty `jig_version` (spec 046-02), and not an unrendered
      `{{...}}` placeholder (a leaked template token == a stale value);
    - non-empty `project_name`, `scaffold_mode`;
    - `installed_tiers` present and a list;
    - `installed_skills`, if present, must be a list whose every entry's
      tier prefix (`<tier>/<skill>`) is in `installed_tiers` (the ADR-0007
      manifest invariant)."""
    if not isinstance(data, dict):
        return ["scaffold.json: top-level value must be a JSON object"]

    problems: list[str] = []
    for field in SCAFFOLD_MANIFEST_REQUIRED_FIELDS:
        value = data.get(field)
        if field not in data or value is None or value == "":
            problems.append(
                f"scaffold.json: missing/empty required field {field!r}"
            )
        elif isinstance(value, str) and _UNRENDERED_PLACEHOLDER_RE.search(value):
            problems.append(
                f"scaffold.json: field {field!r} carries an unrendered "
                f"template placeholder {value!r} (stale value)"
            )

    tiers = data.get("installed_tiers")
    if "installed_tiers" not in data:
        problems.append(
            "scaffold.json: missing required field 'installed_tiers'"
        )
    elif not isinstance(tiers, list):
        problems.append(
            "scaffold.json: 'installed_tiers' must be a list "
            f"(got {type(tiers).__name__})"
        )

    skills = data.get("installed_skills")
    if skills is not None:
        if not isinstance(skills, list):
            problems.append(
                "scaffold.json: 'installed_skills' must be a list "
                f"(got {type(skills).__name__})"
            )
        elif isinstance(tiers, list):
            # ADR-0007 invariant: every installed skill's tier is installed.
            tier_set = set(tiers)
            for entry in skills:
                if not isinstance(entry, str) or "/" not in entry:
                    problems.append(
                        f"scaffold.json: installed_skills entry {entry!r} is "
                        "not in the expected '<tier>/<skill>' form"
                    )
                    continue
                tier = entry.split("/", 1)[0]
                if tier not in tier_set:
                    problems.append(
                        f"scaffold.json: installed_skills entry {entry!r} "
                        f"names tier {tier!r} not in installed_tiers "
                        f"{sorted(tier_set)} (ADR-0007 invariant)"
                    )
    return problems


def _read_scaffold_manifest(project_root: Path) -> dict:
    """Read + parse `project_root/scaffold.json`, returning {} on any
    absence/parse error. Used by the skill-closure check to learn the
    tier-gated expected skill set; a missing/broken manifest is reported by
    the dedicated manifest check, so here it degrades to an empty
    expectation rather than raising."""
    manifest = project_root / "scaffold.json"
    if not manifest.is_file():
        return {}
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------------------
# Local command / link smoke checks (AC #4)
# ---------------------------------------------------------------------------
#
# Run against a scaffolded target, scan its docs + copied SKILL.md bodies for
#   (a) broken LOCAL helper commands — a referenced
#       ${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<x>.py that doesn't
#       exist on disk;
#   (b) dangling LOCAL markdown links — a relative `[text](path)` whose
#       target file is absent.
# External (http/https/mailto) links and pure #anchors are out of scope (we
# can't resolve a network URL offline, and an in-page anchor isn't a file).

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _iter_project_doc_files(project_root: Path) -> Iterable[Path]:
    """Yield the markdown docs a scaffolded target *owns and renders for
    itself*: every `*.md` under `docs/` and the top-level `CLAUDE.md`.
    Deterministic order for stable diagnostics.

    Copied `SKILL.md` bodies are deliberately NOT in this set for the
    *markdown-link* check: their relative `[text](../../docs/...)` links
    point at the source-plugin layout and spec 046-01 rewrote only the
    `${CLAUDE_PLUGIN_ROOT}/skills/` *helper bash paths*, not markdown doc
    links — so a SKILL.md doc-link to source `docs/` is a known, deliberate
    non-rewrite (a possible spec-046 follow-up), NOT a scaffold-contract
    violation. SKILL.md bodies ARE scanned for broken local helper *commands*
    (see `_iter_helper_command_files`), which 046-01 DID rewrite and which
    are load-bearing in the scaffolded target."""
    docs = project_root / "docs"
    if docs.is_dir():
        for md in sorted(docs.rglob("*.md")):
            yield md
    claude_md = project_root / "CLAUDE.md"
    if claude_md.is_file():
        yield claude_md


def _iter_helper_command_files(project_root: Path) -> Iterable[Path]:
    """Yield every file whose local helper *commands* must resolve: the
    project docs (`docs/**/*.md`, `CLAUDE.md`) plus the copied
    `.claude/skills/jig-*/SKILL.md` bodies. The local helper-command path
    (`${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<x>.py`) is rewritten by
    spec 046-01 and is load-bearing wherever it appears — a dangling one is a
    broken copied command (the anti-horizontal-phasing target)."""
    yield from _iter_project_doc_files(project_root)
    skills_dir = project_root / ".claude" / "skills"
    if skills_dir.is_dir():
        for skill_dir in _iter_skill_dirs(skills_dir):
            sk = skill_dir / "SKILL.md"
            if sk.is_file():
                yield sk


def _rel(project_root: Path, path: Path) -> str:
    """Best-effort project-relative display path for a diagnostic."""
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


def scaffold_doc_problems(project_root: Path) -> list[str]:
    """Smoke-check a scaffolded target's docs + copied SKILL.md bodies for
    broken local helper commands and dangling local markdown links (AC #4).
    Returns diagnostics (empty == clean); each names the offending doc, the
    missing target, and the rule.

    - **Broken local helper command** (project docs + copied SKILL.md
      bodies): a `${CLAUDE_PROJECT_DIR}/.claude/skills/jig-<name>/<x>.py`
      reference whose file is absent under `.claude/skills/`.
    - **Dangling local markdown link** (project docs only — see
      `_iter_project_doc_files` for why SKILL.md doc-links are out of scope):
      a relative `[text](path)` whose target file (anchor stripped) does not
      resolve on disk, relative to the doc's own directory. http/https/mailto
      links and pure `#anchor` links are ignored."""
    skills_dir = project_root / ".claude" / "skills"
    problems: list[str] = []

    # (a) broken local helper commands — project docs + copied SKILL.md.
    for doc in _iter_helper_command_files(project_root):
        text = doc.read_text()
        doc_rel = _rel(project_root, doc)
        for ref in sorted(set(_LOCAL_HELPER_REF_RE.findall(text))):
            # `ref` is `jig-<name>/<...>.py`.
            if not (skills_dir / ref).is_file():
                problems.append(
                    f"{doc_rel}: references local helper command "
                    f"'.claude/skills/{ref}' which does not exist on disk "
                    "(broken local helper command)"
                )

    # (b) dangling local markdown links — project docs the target owns.
    for doc in _iter_project_doc_files(project_root):
        text = doc.read_text()
        doc_rel = _rel(project_root, doc)
        for href in _MD_LINK_RE.findall(text):
            target = href.split("#", 1)[0].strip()
            if not target:
                continue  # pure #anchor — not a file
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = (doc.parent / target).resolve()
            if not resolved.exists():
                problems.append(
                    f"{doc_rel}: dangling local Markdown link to {target!r} "
                    f"(target file missing at {_rel(project_root, resolved)})"
                )
    return problems
