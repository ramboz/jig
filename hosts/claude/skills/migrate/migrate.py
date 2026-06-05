"""
jig migrate helper — slices 008-01 (report) and 008-02 (rename-decisions)

`report` is read-only. `rename-decisions` is the first mutating subcommand;
its code path is partitioned below `SAFETY_SENTINEL` so the safety regex
sweep in `test_migrate.py` can verify the report path stays pure-read.

Subcommands:
    python3 migrate.py report <project-dir>
    python3 migrate.py rename-decisions <project-dir> [--dry-run]

Report exit codes:
    0 — adoptable verdict OR not-yet-spec-driven (report is the deliverable)
    1 — partial verdict (informational; report still emits)
    2 — user error (missing dir, dir not readable, dir is not a directory)

Rename-decisions exit codes:
    0 — applied OR nothing-to-do (already aligned)
    2 — user error (missing dir, conflict, collision)

Future subcommands (008-04 and later):
    slice-to-spec      — synthesize parent specs from milestones
"""

import argparse
import dataclasses
import os
import re
import sys
from pathlib import Path


class MigrateError(RuntimeError):
    """User-facing CLI error — caller exits 2."""


class MigrateMachineryRefusalError(RuntimeError):
    """Raised by `copy_machinery` when the scaffold-mode helper refuses
    (currently: unmanaged hooks in the target host configuration without
    --force). Caller exits 3, mirroring `LooksAlreadySpecDrivenError`
    precedent from 008-05."""


_VALID_HOSTS = frozenset({"claude", "codex"})


def _infer_host_from_runtime() -> str:
    """Infer the host from the copied helper path.

    Source-checkout and Claude plugin/scaffold invocations default to Claude.
    A helper copied under `.codex/skills/...` defaults to Codex so Codex
    scaffold users do not need to remember a flag for ordinary reruns.
    """
    parts = [part.lower() for part in Path(__file__).resolve().parts]
    for i in range(len(parts) - 1):
        if parts[i] == ".codex" and parts[i + 1] == "skills":
            return "codex"
    return "claude"


def _resolve_host(host: 'str | None') -> str:
    if host in (None, "", "auto"):
        return _infer_host_from_runtime()
    if host not in _VALID_HOSTS:
        raise MigrateError(
            f"unsupported host: {host!r}; expected one of "
            f"{', '.join(sorted(_VALID_HOSTS))}"
        )
    return host


# ---------- Inventory model ----------


class Inventory:
    """Aggregated read-only observations about <project-dir>."""

    def __init__(self):
        self.slices = []          # list of Path under docs/slices/
        self.specs = []           # list of Path under docs/specs/*/spec.md
        self.decisions = []       # list of Path under docs/decisions/
        self.adrs = []            # list of Path under docs/adrs/
        self.spikes = []          # list of Path under docs/spikes/
        self.workflow = None      # Path | None
        self.architecture = None  # Path | None
        self.product_vision = None  # Path | None
        self.custom_skills = []   # list of Path under .claude/skills/
        self.custom_agents = []   # list of Path under .claude/agents/
        self.jig_skill_dirs = []  # list of Path under .claude/skills/jig-*/
                                  # (slice 021-01 — used by report's
                                  # operations section to suppress the
                                  # `copy-machinery` suggestion when
                                  # the machinery is already in place).
        self.claude_md_size = None  # int | None — bytes
        self.milestones_referenced = set()  # set of strings like "M1"


def _safe_iterdir(p: Path) -> list:
    """Read-only directory listing; returns [] if dir doesn't exist."""
    if not p.is_dir():
        return []
    try:
        return sorted(p.iterdir())
    except (OSError, PermissionError):
        return []


def _is_content_md(entry: Path) -> bool:
    """True iff `entry` is a regular `.md` file that is NOT a README.

    Used uniformly across every `.md`-listing scan (decisions, adrs,
    slices, specs, spikes, skills, agents). Reviewer-flagged latent
    bug: prior versions filtered README only for decisions/adrs/skills/
    agents, leaving `docs/slices/README.md` and `docs/spikes/README.md`
    as potential leak points. The validator doesn't currently have
    those files, but a future project might."""
    return (entry.is_file()
            and entry.suffix == ".md"
            and entry.name.lower() != "readme.md")


def _safe_read_text(p: Path, max_bytes: int = 200_000) -> str:
    """Read up to max_bytes from p. Returns '' on error."""
    if not p.is_file():
        return ""
    try:
        with p.open("rb") as fh:
            data = fh.read(max_bytes)
        return data.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return ""


def _safe_stat_size(p: Path) -> int:
    """Return file size in bytes, or 0 on error."""
    try:
        return p.stat().st_size
    except (OSError, PermissionError):
        return 0


MILESTONE_RE = re.compile(r"\*\*Milestone:\*\*\s*(M\d+)")


def scan(project_dir: Path) -> Inventory:
    """Build the inventory by reading <project-dir>. No mutations."""
    inv = Inventory()

    docs = project_dir / "docs"

    # Slices (flat) — docs/slices/slice-*.md
    slices_dir = docs / "slices"
    for entry in _safe_iterdir(slices_dir):
        if _is_content_md(entry):
            inv.slices.append(entry)

    # Specs (nested) — docs/specs/*/spec.md
    specs_dir = docs / "specs"
    for entry in _safe_iterdir(specs_dir):
        if entry.is_dir():
            spec_md = entry / "spec.md"
            if spec_md.is_file():
                inv.specs.append(spec_md)

    # Decisions — docs/decisions/*.md
    decisions_dir = docs / "decisions"
    for entry in _safe_iterdir(decisions_dir):
        if _is_content_md(entry):
            inv.decisions.append(entry)

    # ADRs (legacy/jig-pre-ADR-0004) — docs/adrs/*.md
    adrs_dir = docs / "adrs"
    for entry in _safe_iterdir(adrs_dir):
        if _is_content_md(entry):
            inv.adrs.append(entry)

    # Spikes — docs/spikes/*.md (subdirs allowed but only top-level .md counted)
    spikes_dir = docs / "spikes"
    for entry in _safe_iterdir(spikes_dir):
        if _is_content_md(entry):
            inv.spikes.append(entry)

    # Doc landmarks
    wf = docs / "workflow.md"
    if wf.is_file():
        inv.workflow = wf
    arch = docs / "architecture.md"
    if arch.is_file():
        inv.architecture = arch
    pv = docs / "product-vision.md"
    if pv.is_file():
        inv.product_vision = pv

    # Custom assets — exclude README.md (docs, not a skill/agent definition)
    claude_skills_dir = project_dir / ".claude" / "skills"
    for entry in _safe_iterdir(claude_skills_dir):
        if _is_content_md(entry):
            inv.custom_skills.append(entry)
        # Slice 021-01 — detect `jig-*` skill directories (the shape
        # scaffold-mode produces) so `report`'s Operations section can
        # decide whether to suggest `copy-machinery`.
        elif entry.is_dir() and entry.name.startswith("jig-"):
            inv.jig_skill_dirs.append(entry)
    claude_agents_dir = project_dir / ".claude" / "agents"
    for entry in _safe_iterdir(claude_agents_dir):
        if _is_content_md(entry):
            inv.custom_agents.append(entry)

    # CLAUDE.md size
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.is_file():
        inv.claude_md_size = _safe_stat_size(claude_md)

    # Milestone references in slices (heuristic — scan slice frontmatter
    # for `**Milestone:** M\d+` patterns)
    for slice_path in inv.slices:
        text = _safe_read_text(slice_path)
        for m in MILESTONE_RE.finditer(text):
            inv.milestones_referenced.add(m.group(1))

    return inv


# ---------- Verdict ----------


def compute_verdict(inv: Inventory) -> str:
    """Return one of: 'adoptable' | 'partial' | 'not-yet-spec-driven'."""
    triggers = 0
    # 1. spec-or-slice dir
    if inv.slices or inv.specs:
        triggers += 1
    # 2. decision-or-adr dir
    if inv.decisions or inv.adrs:
        triggers += 1
    # 3. workflow doc
    if inv.workflow is not None:
        triggers += 1
    # 4. architecture doc
    if inv.architecture is not None:
        triggers += 1
    if triggers >= 3:
        return "adoptable"
    if triggers == 2:
        return "partial"
    return "not-yet-spec-driven"


# ---------- Section renderers ----------


def render_inventory(inv: Inventory, project_dir: Path) -> str:
    """Render the Inventory section as a markdown table."""
    rows = []
    rows.append("| Path | Count | Note |")
    rows.append("|------|-------|------|")
    if inv.slices:
        rows.append(f"| `docs/slices/` | {len(inv.slices)} | "
                    f"flat slice files (validator-style) |")
    if inv.specs:
        rows.append(f"| `docs/specs/*/spec.md` | {len(inv.specs)} | "
                    f"nested specs (jig-style) |")
    if inv.decisions:
        rows.append(f"| `docs/decisions/` | {len(inv.decisions)} | "
                    f"decision records (ADR-0004 aligned) |")
    if inv.adrs:
        rows.append(f"| `docs/adrs/` | {len(inv.adrs)} | "
                    f"ADRs (pre-ADR-0004 layout — will be renamed) |")
    if inv.spikes:
        rows.append(f"| `docs/spikes/` | {len(inv.spikes)} | "
                    f"spike memos (inventoried only; spike workflow is a "
                    f"separate jig gap) |")
    if inv.workflow is not None:
        rows.append("| `docs/workflow.md` | 1 | workflow doc present |")
    if inv.architecture is not None:
        rows.append("| `docs/architecture.md` | 1 | architecture doc present |")
    if inv.product_vision is not None:
        rows.append("| `docs/product-vision.md` | 1 | product-vision doc present |")
    if inv.custom_skills:
        names = ", ".join(f"`{p.name}`" for p in inv.custom_skills)
        rows.append(f"| `.claude/skills/` | {len(inv.custom_skills)} | "
                    f"custom skills: {names} (out of 008-01 scope) |")
    if inv.jig_skill_dirs:
        # Inbox 2026-05-15: surface jig-managed skills so the user sees why
        # the Operations section suppresses `copy-machinery` (AC #9). Without
        # this row, a project with 12 jig-* skills shows nothing under
        # `.claude/skills/` and the silence is unexplained.
        names = ", ".join(f"`{p.name}`" for p in inv.jig_skill_dirs)
        rows.append(f"| `.claude/skills/` (jig-managed) | "
                    f"{len(inv.jig_skill_dirs)} | "
                    f"jig skills installed: {names} — refresh via "
                    f"`migrate.py copy-machinery` |")
    if inv.custom_agents:
        names = ", ".join(f"`{p.name}`" for p in inv.custom_agents)
        rows.append(f"| `.claude/agents/` | {len(inv.custom_agents)} | "
                    f"custom agents: {names} (out of 008-01 scope) |")
    if inv.claude_md_size is not None:
        rows.append(f"| `CLAUDE.md` | 1 | {inv.claude_md_size} bytes "
                    f"(jig template baseline ~6KB; larger = sprint-log "
                    f"content the user must port manually) |")
    if len(rows) == 2:
        # Only header rows — no detected artifacts
        rows.append("| _none_ | — | no spec-driven artifacts detected |")
    body = "\n".join(rows)
    return "## Inventory\n\n" + body


PAD_RE = re.compile(r"^(adr-)?(\d{3,4})(-.+)$")


def _map_adr_filename(name: str) -> str:
    """Return the jig-target filename for an ADR file (handles 3→4-digit
    pad, adr- prefix add).

    Number-width support: only 3-digit and 4-digit ADR numbers are
    normalized. 5+ digit numbers are passed through unchanged (the
    `\\d{3,4}` capture matches the first 3-4 digits and the rest is
    absorbed into the trailing `-.+` group). jig itself targets 4-digit
    numbers per ADR-0004; if a project uses >9999 ADRs the migration
    helper will leave them on the source layout and the user can decide
    whether to rename further by hand."""
    stem = name[:-3] if name.endswith(".md") else name
    m = PAD_RE.match(stem)
    if not m:
        # Unknown shape — keep as-is but ensure adr- prefix
        return f"adr-{stem}.md" if not stem.startswith("adr-") else f"{stem}.md"
    prefix, digits, rest = m.groups()
    padded = digits.zfill(4)
    return f"adr-{padded}{rest}.md"


def render_mapping(inv: Inventory) -> str:
    """Render the Mapping section as a markdown table."""
    rows = []
    rows.append("| Current | jig target | Note |")
    rows.append("|---------|------------|------|")

    # Decision dir mapping
    if inv.adrs and not inv.decisions:
        rows.append("| `docs/adrs/` | `docs/decisions/` | "
                    "directory rename per ADR-0004 |")
    elif inv.decisions and not inv.adrs:
        rows.append("| `docs/decisions/` | `docs/decisions/` | "
                    "kept (already matches ADR-0004) |")
    elif inv.adrs and inv.decisions:
        rows.append("| `docs/adrs/` + `docs/decisions/` | `docs/decisions/` | "
                    "**CONFLICT** — see Conflicts section |")

    # ADR file renames
    for adr_path in inv.adrs + inv.decisions:
        current_name = adr_path.name
        target_name = _map_adr_filename(current_name)
        if current_name == target_name:
            continue
        current_dir = "docs/adrs" if adr_path in inv.adrs else "docs/decisions"
        rows.append(f"| `{current_dir}/{current_name}` | "
                    f"`docs/decisions/{target_name}` | "
                    f"pad to 4-digit + ensure `adr-` prefix |")

    # Slice topology
    if inv.slices:
        rows.append(f"| `docs/slices/slice-NN-*.md` ({len(inv.slices)} files) | "
                    "topology question — see Ambiguities (slice 008-04) | "
                    "no automated mapping in 008-01 |")
    if inv.specs:
        rows.append("| `docs/specs/NNN-*/spec.md` | "
                    "kept (already nested) | no change required |")

    # Other landmarks
    if inv.workflow is not None:
        rows.append("| `docs/workflow.md` | `docs/workflow.md` | "
                    "kept — manual review against jig's template recommended |")
    if inv.architecture is not None:
        rows.append("| `docs/architecture.md` | `docs/architecture.md` | "
                    "kept — manual review against jig's template recommended |")

    if len(rows) == 2:
        rows.append("| _none_ | — | no mappings required |")

    return "## Mapping\n\n" + "\n".join(rows)


def render_conflicts(inv: Inventory) -> str:
    """Render the Conflicts section. Empty if no conflicts."""
    conflicts = []

    # Dual decisions/adrs dirs
    if inv.adrs and inv.decisions:
        conflicts.append(
            "- **Both `docs/adrs/` and `docs/decisions/` exist.** "
            "Migration would need to merge them, but `migrate.py "
            "rename-decisions` (slice 008-02) refuses on this "
            "configuration. Resolve manually: pick one canonical "
            "location, move files, update cross-references."
        )
        # Filename collisions after target normalization
        adr_targets = {_map_adr_filename(p.name) for p in inv.adrs}
        dec_targets = {_map_adr_filename(p.name) for p in inv.decisions}
        collisions = sorted(adr_targets & dec_targets)
        if collisions:
            conflicts.append(
                f"- **Filename collision after rename:** {len(collisions)} "
                f"file(s) in both directories map to the same target name: "
                + ", ".join(f"`{c}`" for c in collisions) + "."
            )

    if not conflicts:
        return "## Conflicts\n\n_None detected._"
    return "## Conflicts\n\n" + "\n".join(conflicts)


def render_ambiguities(inv: Inventory) -> str:
    """Render the Ambiguities section."""
    ambiguities = []

    # Flat slices + milestones
    if inv.slices:
        if inv.milestones_referenced:
            milestones = sorted(inv.milestones_referenced)
            ambiguities.append(
                f"- **Flat slices reference {len(milestones)} milestone(s) "
                f"({', '.join(milestones)}).** Under jig's nested model "
                f"(`docs/specs/NNN-name/spec.md`), each milestone could "
                f"become a parent spec. The user must decide the milestone-"
                f"to-parent-spec mapping; `migrate.py slice-to-spec` (slice "
                f"008-04, deferred) will accept that mapping as input."
            )
        else:
            ambiguities.append(
                f"- **{len(inv.slices)} flat slice file(s) detected with "
                f"no milestone references.** Under jig's nested model, "
                f"slices live under a parent spec — the user must group "
                f"these into parent specs manually before slice 008-04 "
                f"can map them."
            )

    # Custom skills / agents
    if inv.custom_skills:
        names = ", ".join(f"`{p.stem}`" for p in inv.custom_skills)
        ambiguities.append(
            f"- **Custom skills present:** {names}. These are out of "
            f"008-01's automated scope. The user must decide for each: "
            f"replace with a jig stock skill (if behavior overlaps), "
            f"keep both as parallel layers, or leave the custom version "
            f"in place."
        )
    if inv.custom_agents:
        names = ", ".join(f"`{p.stem}`" for p in inv.custom_agents)
        ambiguities.append(
            f"- **Custom agents present:** {names}. Same judgment call "
            f"as custom skills — out of 008-01's automated scope."
        )

    # Large CLAUDE.md
    if inv.claude_md_size is not None and inv.claude_md_size > 10_000:
        ambiguities.append(
            f"- **CLAUDE.md is large** ({inv.claude_md_size} bytes — jig's "
            f"template baseline is ~6KB). Likely contains sprint-log or "
            f"project-state content jig's Hot Cache doesn't model. The "
            f"user must decide what to port verbatim, what to summarize "
            f"into the Hot Cache, and what to archive elsewhere."
        )

    # Spikes (separate jig gap)
    if inv.spikes:
        ambiguities.append(
            f"- **{len(inv.spikes)} spike file(s) present** under "
            f"`docs/spikes/`. jig does not yet have a spike-workflow "
            f"skill — spikes are inventoried but not migrated by any "
            f"008 slice. Keep as-is; revisit when jig adds the skill."
        )

    if not ambiguities:
        return "## Ambiguities\n\n_None — migration can proceed without judgment calls._"
    return "## Ambiguities\n\n" + "\n".join(ambiguities)


def render_operations(inv: Inventory, verdict: str) -> str:
    """Render the Operations section — suggested next migrate.py calls."""
    if verdict == "not-yet-spec-driven":
        return (
            "## Operations\n\n"
            "Project is not yet spec-driven. Run `/jig:scaffold-init` "
            "to scaffold from scratch instead of migrating."
        )

    header = "Suggested order (each operation is `--dry-run` first):\n"
    items = []  # list of body strings; numbered at render time

    # rename-decisions
    if inv.adrs:
        if inv.decisions:
            items.append(
                "**`migrate.py rename-decisions`** — **not available** "
                "(see Conflicts: `docs/adrs/` and `docs/decisions/` both "
                "present). Resolve manually first."
            )
        else:
            items.append(
                "**`migrate.py rename-decisions <project-dir>`** "
                "(slice 008-02, **not yet implemented**) — apply ADR-0004 "
                "rename: `docs/adrs/` → `docs/decisions/`, files prefixed "
                "with `adr-` and padded to 4-digit numbers."
            )
    elif any(_map_adr_filename(p.name) != p.name for p in inv.decisions):
        # decisions dir present but files need renaming
        items.append(
            "**`migrate.py rename-decisions <project-dir>`** "
            "(slice 008-02, **not yet implemented**) — normalize "
            "filenames in `docs/decisions/` to `adr-NNNN-` shape "
            "(4-digit pad + `adr-` prefix where missing)."
        )

    # slice-to-spec
    if inv.slices:
        items.append(
            "**`migrate.py slice-to-spec <project-dir>`** "
            "(slice 008-04, **not yet implemented**) — interactively map "
            "flat slices into nested parent specs. Likely needs a "
            "milestone-to-spec manifest from the user."
        )

    # Slice 021-01 — copy-machinery (scaffold-mode parity for migrated
    # projects). Surfaces when the verdict is adoptable OR partial AND
    # the target's `.claude/skills/` has no pre-existing `jig-*` skill
    # dir (the marker scaffold-mode leaves behind). Suppressed once the
    # machinery is in place, otherwise the suggestion is redundant.
    if verdict in {"adoptable", "partial"} and not inv.jig_skill_dirs:
        items.append(
            "**`migrate.py copy-machinery <project-dir>`** — copy "
            "jig's hooks / agents / skill helpers into the target's "
            "`.claude/` (scaffold-mode parity). Mirrors what "
            "`scaffold-init` does by default for greenfield projects."
        )

    if not items:
        # Reviewer-flagged: omit the "Suggested order" header when there's
        # nothing to order. The empty-state message stands alone.
        return (
            "## Operations\n\n"
            "_No automated operations apply to this project's current "
            "shape. All detected artifacts are either already jig-aligned "
            "or out of 008-01's scope._"
        )

    numbered = [f"{i + 1}. {body}" for i, body in enumerate(items)]
    return "## Operations\n\n" + header + "\n" + "\n".join(numbered)


# ---------- Top-level report ----------


def render_report(inv: Inventory, verdict: str, project_dir: Path) -> str:
    """Assemble the full report."""
    parts = [
        f"# Migration report — `{project_dir}`",
        "",
        f"**Verdict:** {verdict}",
        "",
    ]
    if verdict == "adoptable":
        parts.append("_Three or more migration triggers detected. "
                     "Proceed with the operations below._\n")
    elif verdict == "partial":
        parts.append("_Two migration triggers detected — borderline. "
                     "`/jig:scaffold-init` may be a better fit; the "
                     "report below documents what would be migrated "
                     "if you choose to adopt jig anyway._\n")
    else:  # not-yet-spec-driven
        parts.append("_Fewer than two migration triggers detected. "
                     "Recommend `/jig:scaffold-init` instead — see "
                     "Operations._\n")

    parts.append(render_inventory(inv, project_dir))
    parts.append("")
    parts.append(render_mapping(inv))
    parts.append("")
    parts.append(render_conflicts(inv))
    parts.append("")
    parts.append(render_ambiguities(inv))
    parts.append("")
    parts.append(render_contract_surfaces(project_dir))
    parts.append("")
    parts.append(render_operations(inv, verdict))
    parts.append("")
    return "\n".join(parts)


# ---------- Contract-surface detection (slice 022-02) ----------
#
# Read-only detection for the `## Contract surfaces detected` section.
# Each helper returns a list of bullet strings; the renderer dedupes
# and joins. Detection scope per slice 022-02 AC #3:
#   (a) existing schema artifacts on disk
#   (b) prose API contracts in docs/architecture.md
#   (c) env-contract-style patterns
#   (d) hand-typed boundary types (RFC 7807-style)
#
# All file operations here are READS only — SafetyTests scans this
# region for write-shaped calls and refuses any.

# Skip-set for directory traversal. Mirrors the post-sentinel
# `_SKIP_PATH_NAMES` (which is defined alongside the mutating code path)
# but lives above the sentinel so SafetyTests sees it as part of the
# read-only region. Both sets stay in sync; if one grows, grow the other.
_CSURFACE_SKIP_DIRS = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".tox", "dist", "build",
    ".next", ".cache", "worktrees", ".claude",
})

# Filename patterns for schema artifacts (case-insensitive).
_SCHEMA_FILENAME_RES = (
    (re.compile(r"^openapi\.(ya?ml|json)$", re.IGNORECASE), "HTTP API",
     "OpenAPI 3.x", "spectral lint + openapi-typescript"),
    (re.compile(r"^asyncapi\.(ya?ml|json)$", re.IGNORECASE), "Event bus / async messaging",
     "AsyncAPI", "asyncapi/parser + asyncapi/generator"),
    (re.compile(r"^.+\.proto$", re.IGNORECASE), "RPC",
     "Protocol Buffers", "buf lint + buf generate"),
    (re.compile(r"^schema\.graphqls?$", re.IGNORECASE), "GraphQL",
     "GraphQL SDL", "graphql-inspector + graphql-codegen"),
    (re.compile(r"^.+\.schema\.json$", re.IGNORECASE), "Internal data shape",
     "JSON Schema", "ajv validate + quicktype"),
)

# Filename patterns for hand-typed boundary types (the drift symptom —
# a file whose name suggests an inline schema reimplementation).
_HANDTYPED_BOUNDARY_RES = (
    re.compile(r"^problem[-_]?details?\.(ts|tsx|js|jsx|mjs|py|go|rb|java|kt|rs)$",
               re.IGNORECASE),
)


def _walk_for_files(project_dir: Path, max_depth: int = 8):
    """Yield every file under `project_dir`, honoring _CSURFACE_SKIP_DIRS.
    Depth-bounded (default 8) to keep large monorepos tractable.

    READ-ONLY: only `Path.iterdir` and `Path.is_file` are used. No
    mutating operations.
    """
    if not project_dir.is_dir():
        return

    def _walk(root: Path, depth: int):
        if depth > max_depth:
            return
        try:
            entries = sorted(root.iterdir())
        except (OSError, PermissionError):
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in _CSURFACE_SKIP_DIRS:
                    continue
                yield from _walk(entry, depth + 1)
                continue
            if entry.is_file():
                yield entry

    yield from _walk(project_dir, 0)


def _detect_schema_artifacts(project_dir: Path) -> list:
    """AC #3(a) — flag existing OpenAPI / AsyncAPI / .proto / GraphQL SDL /
    JSON Schema files. One bullet per match, with surface classification +
    recommended tooling (mirrors the contracts skill's per-surface table)."""
    hits = []
    for fp in _walk_for_files(project_dir):
        name = fp.name
        for pattern, surface, artifact, tooling in _SCHEMA_FILENAME_RES:
            if pattern.match(name):
                rel = fp.relative_to(project_dir).as_posix()
                hits.append(
                    f"- **{surface} artifact**: `{rel}` ({artifact}) — "
                    f"matches `/jig:contracts` recommendation; wire `{tooling}` "
                    f"in CI if not already."
                )
                break
    return hits


# Match a prose API "endpoint table row": a Markdown table cell containing
# one of the HTTP verbs (GET / POST / PUT / DELETE / PATCH / HEAD / OPTIONS)
# possibly wrapped in backticks. Used as one signal that an architecture.md
# H2 section is prose-API-shaped.
_HTTP_VERB_ROW_RE = re.compile(
    r"\|\s*`?(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)`?\s*\|",
    re.IGNORECASE,
)

# Match a fenced jsonc / json code block — the second prose-API signal.
_JSONC_FENCE_RE = re.compile(r"```(?:jsonc|json)\b")


def _detect_prose_api_in_architecture(project_dir: Path) -> list:
    """AC #3(b) — flag prose API contracts in canonical doc files.

    Two-tier heuristic:

    1. For `docs/architecture.md` — per-section detection (both signals
       must appear in the SAME H2 section). High precision: architecture
       docs are broad and a section-scoped match avoids false positives
       from unrelated tables / examples.
    2. For dedicated contract-shaped docs (`api-contract.md`,
       `api-spec.md`, `api.md`, `contracts.md` under `docs/`) — document-
       level detection (both signals anywhere in the file). These files
       are *named* as contracts; a per-section gate misses the common
       shape where the endpoint table is in §1 and the jsonc bodies are
       in §2..§N (the aso-shallow-validator shape).

    For per-section matches, the bullet cites the matching §<heading>;
    for whole-doc matches, the bullet cites just the file.
    """
    docs_dir = project_dir / "docs"
    hits = []

    # Tier 1: per-section detection for architecture.md
    arch_path = docs_dir / "architecture.md"
    try:
        arch_text = arch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, FileNotFoundError):
        arch_text = None
    if arch_text:
        rel = arch_path.relative_to(project_dir).as_posix()
        h2_matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", arch_text))
        for i, hm in enumerate(h2_matches):
            section_start = hm.end()
            section_end = (h2_matches[i + 1].start()
                           if i + 1 < len(h2_matches) else len(arch_text))
            body = arch_text[section_start:section_end]
            # Skip the wizard-declared "Contract surfaces" section itself.
            if hm.group(1).strip().lower() == "contract surfaces":
                continue
            if _HTTP_VERB_ROW_RE.search(body) and _JSONC_FENCE_RE.search(body):
                heading = hm.group(1).strip()
                hits.append(
                    f"- **Prose API contract** in `{rel}` §{heading}: "
                    f"candidate for OpenAPI 3.x extraction (endpoint "
                    f"table + jsonc bodies present). See "
                    f"`skills/contracts/worked-example-openapi-http.md` "
                    f"for the recommended migration path."
                )

    # Tier 2: whole-doc detection for dedicated contract files
    contract_candidates = [
        docs_dir / "api-contract.md",
        docs_dir / "api-spec.md",
        docs_dir / "api.md",
        docs_dir / "contracts.md",
    ]
    for path in contract_candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, FileNotFoundError):
            continue
        if _HTTP_VERB_ROW_RE.search(text) and _JSONC_FENCE_RE.search(text):
            rel = path.relative_to(project_dir).as_posix()
            hits.append(
                f"- **Prose API contract** in `{rel}` (whole document): "
                f"candidate for OpenAPI 3.x extraction (endpoint table + "
                f"jsonc bodies present). See "
                f"`skills/contracts/worked-example-openapi-http.md` for "
                f"the recommended migration path."
            )
    return hits


def _detect_env_contract_pattern(project_dir: Path) -> list:
    """AC #3(c) — flag the bespoke env-contract triple (markdown doc +
    .env.example seed + checker). Emit one line summarizing which parts
    of the triple are present and what's missing."""
    doc = (project_dir / "docs" / "env-contract.md").is_file()
    seed = (project_dir / ".env.example").is_file()
    # Checker heuristic, layered:
    #   1. ANY file inside `tools/env-contract/` — the directory name
    #      carries the semantic (this is the aso-shallow-validator shape:
    #      `tools/env-contract/check.mjs` — file name is short, dir name
    #      is the contract).
    #   2. Files under `tools/`, `scripts/`, or repo root whose NAME
    #      contains `env-contract` / `env_contract` (e.g.
    #      `check-env-contract.sh`, `env_contract_check.py`).
    checker = False
    contract_dir = project_dir / "tools" / "env-contract"
    if contract_dir.is_dir():
        try:
            for fp in contract_dir.iterdir():
                if fp.is_file():
                    checker = True
                    break
        except (OSError, PermissionError):
            pass
    if not checker:
        for cand_dir in [project_dir / "scripts",
                         project_dir / "tools",
                         project_dir]:
            if not cand_dir.is_dir():
                continue
            try:
                entries = list(cand_dir.iterdir())
            except (OSError, PermissionError):
                continue
            for fp in entries:
                if not fp.is_file():
                    continue
                n = fp.name.lower()
                if "env-contract" in n or "env_contract" in n:
                    checker = True
                    break
            if checker:
                break

    present = sum([doc, seed, checker])
    if present == 0:
        return []
    if present == 3:
        return [
            "- **env-contract pattern** detected (full triple: "
            "`docs/env-contract.md` + `.env.example` + checker script). "
            "Bespoke alternative to JSON Schema for env vars; well-shaped, "
            "no migration recommended. See `skills/contracts/SKILL.md` "
            "Config / env vars row for the rationale."
        ]
    # Partial — name what's missing.
    missing = []
    if not doc:
        missing.append("`docs/env-contract.md`")
    if not seed:
        missing.append("`.env.example`")
    if not checker:
        missing.append("checker script (under `tools/env-contract/` or `scripts/`)")
    return [
        f"- **Partial env-contract pattern** ({present} of 3): missing "
        f"{', '.join(missing)}. Either complete the triple, migrate to "
        f"per-config JSON Schema, or document the partial state."
    ]


def _detect_handtyped_boundary_types(project_dir: Path) -> list:
    """AC #3(d) — flag files whose name suggests an inline schema
    reimplementation (e.g., `problem-details.ts`). Heuristic — high
    precision; modest recall (only the canonical RFC 7807-style names)."""
    hits = []
    for fp in _walk_for_files(project_dir):
        for pattern in _HANDTYPED_BOUNDARY_RES:
            if pattern.match(fp.name):
                rel = fp.relative_to(project_dir).as_posix()
                hits.append(
                    f"- **Hand-typed boundary type**: `{rel}` — name "
                    f"suggests an inline RFC 7807 (Problem Details) "
                    f"schema reimplementation. Candidate for codegen "
                    f"from the project's OpenAPI / JSON Schema artifact "
                    f"once it exists. See "
                    f"`skills/contracts/worked-example-openapi-http.md` "
                    f"§After for the typed-codegen pattern."
                )
                break
    return hits


def render_contract_surfaces(project_dir: Path) -> str:
    """AC #3 of slice 022-02 — `## Contract surfaces detected` section."""
    bullets = []
    bullets.extend(_detect_schema_artifacts(project_dir))
    bullets.extend(_detect_prose_api_in_architecture(project_dir))
    bullets.extend(_detect_env_contract_pattern(project_dir))
    bullets.extend(_detect_handtyped_boundary_types(project_dir))

    if not bullets:
        return (
            "## Contract surfaces detected\n\n"
            "_No contract surfaces detected._ This project does not appear "
            "to expose schema-shaped external interfaces. If this is "
            "wrong (e.g., a prose API contract lives in an unscanned "
            "doc, or a schema artifact uses a non-canonical name), "
            "declare the surface via `/jig:vision-elicitation` Section 13 "
            "(Contract surfaces). The `/jig:contracts` skill's per-surface "
            "recommendation table covers HTTP / events / RPC / GraphQL / "
            "internal data shapes / config / CLI output."
        )

    intro = (
        "Detected via file-and-pattern heuristics. Each line is a "
        "*recommendation*, not a migration order — the dev decides per "
        "surface (per `/jig:contracts`'s nudge-don't-mandate ethos). See "
        "`skills/contracts/SKILL.md` for the per-surface recommendation "
        "table."
    )
    return (
        "## Contract surfaces detected\n\n"
        f"{intro}\n\n" + "\n".join(bullets)
    )


def report(project_dir: Path) -> tuple:
    """Run the inventory, compute the verdict, render the report.

    Returns (report_text, exit_code)."""
    if not project_dir.exists():
        raise MigrateError(f"project directory not found: {project_dir}")
    if not project_dir.is_dir():
        raise MigrateError(f"not a directory: {project_dir}")

    inv = scan(project_dir)
    verdict = compute_verdict(inv)
    text = render_report(inv, verdict, project_dir)

    if verdict == "partial":
        return text, 1
    return text, 0


# ---------- BEGIN MUTATING CODE PATH (rename-decisions) ----------
#
# Everything below this sentinel is allowed to mutate the filesystem.
# test_migrate.py's SafetyTests scan only the region above this line for
# write/rename/replace/unlink/mkdir/open-for-write calls. The report
# subcommand stays read-only; rename-decisions necessarily writes.


# Text-file extensions in scope for cross-reference rewriting. Files
# without an extension are heuristically scanned via UTF-8 decode of the
# first 4KB; binary files are skipped.
_TEXT_EXTENSIONS = frozenset({
    ".md", ".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg",
    ".ini", ".sh", ".html", ".css", ".js", ".ts",
})

# Path components and substrings that are skipped during cross-reference
# scanning. Skipping `.git` is critical — git's loose-object store
# routinely contains bytes that decode as text and would otherwise be
# corrupted by a substitution. `worktrees` is here because both jig and
# the validator use `.claude/worktrees/<name>/` for parallel git
# checkouts; treating a worktree as in-scope would rewrite a sibling
# branch's working tree, which is never what the user wants.
_SKIP_PATH_NAMES = frozenset({
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".tox", "dist", "build",
    ".next", ".cache", "worktrees",
})

# Max bytes to read when sniffing an extension-less file for textness.
_TEXT_SNIFF_BYTES = 4096

# Recognize ADR filenames. `(adr-)?` captures whether the file already has
# the canonical prefix; `(\d{3,4})` captures the number (3 or 4 digit
# only — sub-3-digit / 5+ digit are left untouched per AC #5).
_ADR_NAME_RE = re.compile(r"^(adr-)?(\d{3,4})(-[^/]+)\.md$")


@dataclasses.dataclass(frozen=True)
class DirRename:
    """Rename of `<project>/docs/adrs/` → `<project>/docs/decisions/`."""
    src: Path
    dst: Path


@dataclasses.dataclass(frozen=True)
class FileRename:
    """Rename of one ADR file. Source path is given relative to the
    POST-dir-rename location (i.e. `<project>/docs/decisions/...`)
    so a stale `docs/adrs/...` Path never escapes the planner."""
    src: Path
    dst: Path


@dataclasses.dataclass(frozen=True)
class CrossRefRewrite:
    """One file whose content will be rewritten. `count` is the number of
    substitutions found at plan time (cosmetic — used for the summary
    line). The actual write re-reads at apply time."""
    path: Path
    count: int


@dataclasses.dataclass(frozen=True)
class RenamePlan:
    dir_rename: 'DirRename | None'
    file_renames: tuple  # tuple[FileRename, ...]
    cross_ref_rewrites: tuple  # tuple[CrossRefRewrite, ...]

    def is_empty(self) -> bool:
        return (self.dir_rename is None
                and not self.file_renames
                and not self.cross_ref_rewrites)


def _normalize_adr_filename(name: str) -> 'str | None':
    """Return the canonical `adr-NNNN-<slug>.md` form for `name`, or
    None if `name` cannot be normalized (sub-3-digit prefix, 5+ digit
    prefix, or a non-ADR filename like a quarterly review log).

    Returns the input unchanged if it is already canonical."""
    m = _ADR_NAME_RE.match(name)
    if not m:
        return None
    _, digits, rest = m.groups()
    padded = digits.zfill(4)
    return f"adr-{padded}{rest}.md"


def _atomic_write(path: Path, content: str) -> None:
    """POSIX-atomic write via `<path>.tmp` + `os.replace`. Same shape as
    `adr.py`'s helper."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, path)


def _is_text_path(path: Path) -> bool:
    """Decide whether `path` should be scanned for cross-references."""
    if path.suffix.lower() in _TEXT_EXTENSIONS:
        return True
    # Extension-less / unknown — sniff first chunk for textness.
    try:
        with path.open("rb") as fh:
            head = fh.read(_TEXT_SNIFF_BYTES)
    except (OSError, PermissionError):
        return False
    if not head:
        return True  # Empty file — treat as text (no harm).
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _should_skip_dir(path: Path) -> bool:
    """True iff `path` (a directory) is on the skip list."""
    return path.name in _SKIP_PATH_NAMES


def _walk_text_files(project_dir: Path, host: str = "claude") -> list:
    """Yield text files under host-appropriate cross-reference roots.

    Shared docs are always in scope. Claude scans `CLAUDE.md` and
    `.claude/`; Codex scans `AGENTS.md` and `.codex/`. Both honor
    `_SKIP_PATH_NAMES`, including nested `worktrees/` directories.
    """
    out = []

    def _walk(root: Path):
        if not root.is_dir():
            return
        for entry in sorted(root.iterdir()):
            if entry.is_dir():
                if _should_skip_dir(entry):
                    continue
                _walk(entry)
                continue
            if not entry.is_file():
                continue
            if not _is_text_path(entry):
                continue
            out.append(entry)

    resolved_host = _resolve_host(host)
    if resolved_host == "codex":
        primer = project_dir / "AGENTS.md"
        runtime_dir = project_dir / ".codex"
    else:
        primer = project_dir / "CLAUDE.md"
        runtime_dir = project_dir / ".claude"

    _walk(project_dir / "docs")
    if primer.is_file() and _is_text_path(primer):
        out.append(primer)
    _walk(runtime_dir)
    return out


def _is_helper_or_fixture(path: Path) -> bool:
    """True iff `path` is migrate.py / test_migrate.py / a fixture file.
    These must never be rewritten by the helper itself — they contain the
    canonical patterns and sample paths.

    The check is by absolute path comparison against this module's own
    location. If the helper is being run on its own repo, the check
    excludes the helper's own files."""
    helper_root = Path(__file__).resolve().parent
    try:
        path.resolve().relative_to(helper_root)
        return True
    except ValueError:
        return False


def _apply_substitutions(text: str, old_dir: str, new_dir: str,
                         name_map: dict) -> 'tuple[str, int]':
    """Two-step substitution per AC #6.

    (a) `old_dir` → `new_dir` (literal). Skipped when they're identical
        (i.e. the source dir is already `docs/decisions/`).
    (b) For each renamed file, its old name → new name, but only when
        the match is NOT already preceded by `adr-`. The negative
        lookbehind is the fix for the greedy-substring bug surfaced in
        review: a file containing both legacy (`docs/adrs/0001-foo.md`)
        and already-canonical (`docs/decisions/adr-0001-foo.md`)
        references would otherwise produce `adr-adr-0001-foo.md` on
        the canonical occurrence — silent content corruption.

    Additionally (slice 014-01): bare ADR ID tokens in frontmatter
    `dependencies:` lists — e.g. `adr-001` or `adr-1` — are padded to
    `adr-NNNN` shape when the corresponding ADR file was renamed.
    A bare-ID token is only padded when not already followed by
    another digit or a dash-letter (so `adr-001-foo.md` is left to
    the filename branch).

    Returns `(new_text, count)` where `count` is the number of actual
    substitutions performed. The count is cosmetic — used only for the
    summary line — and is NOT load-bearing for correctness."""
    count = 0
    out = text
    if old_dir != new_dir:
        count += out.count(old_dir)
        out = out.replace(old_dir, new_dir)
    for old_name, new_name in name_map.items():
        if old_name == new_name:
            continue
        pattern = re.compile(r"(?<!adr-)" + re.escape(old_name))
        out, n = pattern.subn(new_name, out)
        count += n

    # Slice 014-01: bare ADR ID padding (e.g. `adr-001` → `adr-0001`)
    # for frontmatter `dependencies:` list entries. Derive an ID-level
    # map by extracting the numeric portion from both old and new
    # filenames. Tolerates `001-foo.md` (unprefixed) and `adr-001-foo.md`
    # (prefixed) on the old side; the new side is always `adr-NNNN-`
    # post-rename. References in deps are written with the `adr-` prefix
    # by convention, so the canonical mapping is `adr-<old>` → `adr-<new>`.
    id_map = {}
    _num_re = re.compile(r"^(?:adr-)?(\d{1,4})-")
    for old_name, new_name in name_map.items():
        om = _num_re.match(old_name)
        nm = _num_re.match(new_name)
        if not (om and nm) or om.group(1) == nm.group(1):
            continue
        id_map[f"adr-{om.group(1)}"] = f"adr-{nm.group(1)}"
    for old_id, new_id in id_map.items():
        # Match the bare ID only when NOT followed by another digit
        # (avoids partial matches inside longer IDs) and NOT followed by
        # `-` (avoids `adr-001-foo.md` which is handled by the filename
        # branch above).
        pattern = re.compile(re.escape(old_id) + r"(?![\d\-])")
        out, n = pattern.subn(new_id, out)
        count += n

    return out, count


def plan_rename(project_dir: Path, host: str = "claude") -> RenamePlan:
    """Build (but do not apply) the rename plan. Raises MigrateError on
    conflict or collision (preserving the no-partial-writes invariant)."""
    if not project_dir.exists():
        raise MigrateError(f"project directory not found: {project_dir}")
    if not project_dir.is_dir():
        raise MigrateError(f"not a directory: {project_dir}")

    adrs_dir = project_dir / "docs" / "adrs"
    decisions_dir = project_dir / "docs" / "decisions"

    has_adrs = adrs_dir.is_dir()
    has_decisions = decisions_dir.is_dir()

    if has_adrs and has_decisions:
        raise MigrateError(
            f"conflict: both `docs/adrs/` and `docs/decisions/` are present "
            f"in {project_dir}. Resolve manually (merge files into one "
            f"directory, then re-run rename-decisions)."
        )

    if not has_adrs and not has_decisions:
        # Nothing to do.
        return RenamePlan(dir_rename=None, file_renames=(), cross_ref_rewrites=())

    # Determine source dir and whether we rename it.
    if has_adrs:
        dir_rename = DirRename(src=adrs_dir, dst=decisions_dir)
        source_dir = adrs_dir
        old_dir_str = "docs/adrs/"
    else:
        dir_rename = None
        source_dir = decisions_dir
        old_dir_str = "docs/decisions/"
    new_dir_str = "docs/decisions/"

    # Build file renames + name map. All file_rename paths refer to the
    # POST-dir-rename location so apply_rename never has to rewrite paths
    # mid-flight.
    name_map = {}
    file_renames = []
    canonical_present = set()
    for entry in sorted(source_dir.iterdir()):
        if not _is_content_md(entry):
            continue
        normalized = _normalize_adr_filename(entry.name)
        if normalized is None:
            # Unnormalizable (e.g. quarterly review log, sub-3-digit prefix).
            # Leave alone.
            continue
        if normalized == entry.name:
            # Already canonical.
            canonical_present.add(entry.name)
            continue
        name_map[entry.name] = normalized
        post_src = decisions_dir / entry.name
        post_dst = decisions_dir / normalized
        file_renames.append(FileRename(src=post_src, dst=post_dst))

    # Collision detection — before any write.
    target_names = [fr.dst.name for fr in file_renames]
    seen = set()
    duplicates = []
    for tname in target_names:
        if tname in seen:
            duplicates.append(tname)
        seen.add(tname)
    if duplicates:
        raise MigrateError(
            f"collision: multiple files in {source_dir} normalize to the "
            f"same target name(s): {sorted(set(duplicates))}. Resolve "
            f"manually before re-running."
        )
    overlap = sorted(seen & canonical_present)
    if overlap:
        raise MigrateError(
            f"collision: target name(s) already exist in {source_dir}: "
            f"{overlap}. Resolve manually before re-running."
        )

    # Cross-reference rewrites — scan all in-scope text files and count
    # substitutions. The actual rewrite is deferred to apply_rename.
    cross_ref_rewrites = _plan_cross_refs(
        project_dir, old_dir_str, new_dir_str, name_map, host=host,
    )

    return RenamePlan(
        dir_rename=dir_rename,
        file_renames=tuple(file_renames),
        cross_ref_rewrites=tuple(cross_ref_rewrites),
    )


def _plan_cross_refs(project_dir: Path, old_dir: str, new_dir: str,
                     name_map: dict, host: str = "claude") -> list:
    """Scan text files under in-scope roots and identify which need
    rewriting. Returns a sorted list of CrossRefRewrite entries."""
    rewrites = []
    for path in _walk_text_files(project_dir, host=host):
        if _is_helper_or_fixture(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        _, count = _apply_substitutions(text, old_dir, new_dir, name_map)
        if count > 0:
            rewrites.append(CrossRefRewrite(path=path, count=count))
    rewrites.sort(key=lambda r: str(r.path))
    return rewrites


def _format_op_lines(plan: RenamePlan, project_dir: Path,
                     dry_run: bool) -> list:
    """Render the operation summary lines for `plan`. Always returns the
    same lines for the same plan (order-stable per AC #7)."""
    prefix = "[dry-run] " if dry_run else ""
    lines = []
    if plan.dir_rename:
        lines.append(
            f"{prefix}renamed docs/adrs/ → docs/decisions/"
        )
    for fr in plan.file_renames:
        try:
            src_rel = fr.src.relative_to(project_dir)
            dst_rel = fr.dst.relative_to(project_dir)
        except ValueError:
            src_rel = fr.src
            dst_rel = fr.dst
        lines.append(f"{prefix}renamed {src_rel} → {dst_rel}")
    for ref in plan.cross_ref_rewrites:
        try:
            rel = ref.path.relative_to(project_dir)
        except ValueError:
            rel = ref.path
        plural = "s" if ref.count != 1 else ""
        lines.append(
            f"{prefix}rewrote {ref.count} cross-reference{plural} in {rel}"
        )
    return lines


def apply_rename(plan: RenamePlan, project_dir: Path,
                 dry_run: bool = False) -> list:
    """Apply `plan` to `project_dir`. Returns the operation summary lines.

    Execution order (independent of display order):
      1. Cross-reference rewrites on the ORIGINAL paths (before any
         rename moves files out from under us).
      2. Directory rename (if applicable).
      3. File renames (in the post-dir-rename location).

    Display order (per AC #7) is fixed: dir → files → cross-refs."""
    op_lines = _format_op_lines(plan, project_dir, dry_run)

    if dry_run or plan.is_empty():
        return op_lines

    # Step 1 — cross-reference rewrites. The rewrites operate on text
    # content; the file's location may differ after step 2, but the
    # content rewrite is identical either way. Doing this BEFORE the
    # rename keeps the recorded paths valid at apply time.
    old_dir_str, new_dir_str, name_map = _replay_substitution_params(plan)
    for ref in plan.cross_ref_rewrites:
        try:
            text = ref.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new_text, _ = _apply_substitutions(
            text, old_dir_str, new_dir_str, name_map,
        )
        if new_text != text:
            _atomic_write(ref.path, new_text)

    # Step 2 — directory rename.
    if plan.dir_rename:
        os.replace(plan.dir_rename.src, plan.dir_rename.dst)

    # Step 3 — file renames (now in the post-dir-rename location).
    for fr in plan.file_renames:
        os.replace(fr.src, fr.dst)

    return op_lines


def _replay_substitution_params(plan: RenamePlan) -> tuple:
    """Recover the (old_dir, new_dir, name_map) tuple used by the planner
    so apply_rename can re-run substitutions identically."""
    if plan.dir_rename:
        old_dir = "docs/adrs/"
    else:
        old_dir = "docs/decisions/"
    new_dir = "docs/decisions/"
    name_map = {fr.src.name: fr.dst.name for fr in plan.file_renames}
    return old_dir, new_dir, name_map


def rename_decisions(project_dir: Path, dry_run: bool = False,
                     host: str = "claude") -> tuple:
    """Top-level entry for the rename-decisions subcommand.

    Returns `(summary_text, exit_code)`."""
    plan = plan_rename(project_dir, host=host)
    if plan.is_empty():
        return ("already aligned: nothing to do\n", 0)
    lines = apply_rename(plan, project_dir, dry_run=dry_run)
    return ("\n".join(lines) + "\n", 0)


# ---------- CLI plumbing ----------


# ---------- split-slices (slice 018-04) ----------


_SLICE_H2_RE = re.compile(
    r"(?m)^##\s+Slice\s+(\d{3})-(\d{2})\s+—\s+([^\n]+?)\s*$"
)
_FM_AFTER_HEADING_RE = re.compile(
    r"\A(\s*\n)?(---\n.*?\n---\n)", re.DOTALL,
)
# Reviewer §SPECIFIC ISSUES (slice 018-04): a body that opens with
# `\n---\n` (horizontal rule) and later contains another `---` would be
# misread by `_FM_AFTER_HEADING_RE` as a YAML frontmatter block. Guard
# by requiring the captured block to contain at least one `key:` line
# (column 0, before the first whitespace). Real frontmatter always has
# at least one such line; a hr-pair never does.
_FM_KV_LINE_RE = re.compile(r"(?m)^[A-Za-z_][A-Za-z0-9_\-]*\s*:")


def _looks_like_frontmatter_block(block: str) -> bool:
    """True iff the captured `---\\n...---\\n` block contains at least
    one `key:` line — distinguishes a real YAML-lite frontmatter
    from a horizontal-rule pair around prose."""
    return bool(_FM_KV_LINE_RE.search(block))


def _shortname_to_slug(shortname: str) -> str:
    """Map a slice's heading shortname (free text after `— `) to a
    filename-safe slug. Lowercase, runs of whitespace collapse to `-`,
    non `[a-z0-9-]` chars dropped, leading/trailing `-` stripped."""
    slug = shortname.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "slice"


def _plan_split_slices(spec_md: Path):
    """Build the split-slices plan for `spec_md`. Returns a list of
    `(target_path, slice_file_content, source_start, source_end,
    spec_num, slice_num, shortname)` tuples in document order, or
    an empty list if no slice sections are present."""
    text = spec_md.read_text()
    spec_dir = spec_md.parent
    headings = list(_SLICE_H2_RE.finditer(text))
    plan = []
    for m in headings:
        spec_num = m.group(1)
        slice_num = m.group(2)
        shortname = m.group(3).strip()
        slug = _shortname_to_slug(shortname)
        target = spec_dir / f"slice-{slice_num}-{slug}.md"

        start = m.start()
        # End: next `## ` heading of any kind (slice OR non-slice section),
        # or EOF. Reviewer §SPECIFIC ISSUES (018-04): the original
        # implementation stopped intermediate slices at the next `## Slice`
        # only — meaning a non-slice `## Foo` H2 between two slice headings
        # would get absorbed by the preceding slice. Uniform "next `## `"
        # bound matches AC #1's spirit ("up to the next slice heading"
        # read as "up to the next major section") and avoids the latent
        # surprise.
        rest = text[m.end():]
        nxt = re.search(r"(?m)^##\s", rest)
        end = m.end() + (nxt.start() if nxt else len(rest))

        body_after_heading = text[m.end():end]
        fm_m = _FM_AFTER_HEADING_RE.match(body_after_heading)
        # Reviewer guard: require the captured block to actually look
        # like frontmatter (at least one `key:` line). A horizontal-rule
        # pair around prose has none.
        if fm_m and _looks_like_frontmatter_block(fm_m.group(2)):
            fm_block = fm_m.group(2)
            rest_body = body_after_heading[fm_m.end():]
            slice_content = (
                f"{fm_block}\n## Slice {spec_num}-{slice_num} — "
                f"{shortname}\n{rest_body}"
            )
        else:
            slice_content = (
                f"## Slice {spec_num}-{slice_num} — "
                f"{shortname}\n{body_after_heading}"
            )
        plan.append((target, slice_content, start, end, spec_num,
                     slice_num, shortname))
    return plan


def split_slices(spec_dir: Path, dry_run: bool = False) -> tuple:
    """Split each `## Slice` section out of `<spec_dir>/spec.md` into
    its own `slice-NN-<slug>.md` file. Returns `(report_text, exit_code)`.

    - Atomic: writes go via `_atomic_write`; spec.md is rewritten last.
    - Idempotent: if no `## Slice` sections remain in spec.md, exits 0
      with "nothing to split".
    - Refuses on conflict (exit 2): any target `slice-*.md` already
      exists in `spec_dir`. No partial writes — the conflict check runs
      before any I/O.
    - Cross-references unchanged: slice fragments (`NNN-MM`) still
      resolve via 018-01's dual-read parser.

    spec.md after the split:
    - Prefix preserved through the first `## Slice` heading (frontmatter,
      `# Spec ...` title, `## Overview`, `## Decomposition`, etc.).
    - All `## Slice` sections removed.
    - A `## Slices` link list appended pointing at each extracted file.
    - Any trailing content after the last `## Slice` (rare) is kept.
    """
    spec_dir = Path(spec_dir)
    spec_md = spec_dir / "spec.md"
    if not spec_md.is_file():
        return f"spec.md not found in {spec_dir}\n", 2

    plan = _plan_split_slices(spec_md)
    if not plan:
        return f"nothing to split: no `## Slice` sections in {spec_md}\n", 0

    # Conflict check: refuse if any target file already exists.
    conflicts = [str(t.relative_to(spec_dir)) for t, *_ in plan if t.exists()]
    if conflicts:
        return (
            "refusing: target slice file(s) already exist:\n  "
            + "\n  ".join(conflicts) + "\n",
            2,
        )

    if dry_run:
        lines = ["[dry-run] split-slices plan:"]
        for target, *_ in plan:
            lines.append(f"  → write {target.relative_to(spec_dir)}")
        lines.append(f"  → rewrite {spec_md.name}")
        return "\n".join(lines) + "\n", 0

    # Apply: write slice files first (recoverable on partial failure),
    # then rewrite spec.md last.
    for target, content, *_ in plan:
        _atomic_write(target, content)

    # Build the new spec.md content:
    #   prefix (everything before the first slice heading)
    # + `## Slices` link section
    # + any trailing content (after the last slice section)
    text = spec_md.read_text()
    first_start = plan[0][2]
    last_end = plan[-1][3]
    prefix = text[:first_start].rstrip() + "\n\n"
    trailing = text[last_end:].lstrip("\n")

    link_lines = ["## Slices", ""]
    for target, _content, _s, _e, spec_num, slice_num, shortname in plan:
        link_lines.append(
            f"- [{spec_num}-{slice_num} — {shortname}]({target.name})"
        )
    link_lines.append("")  # trailing newline before any further content

    new_spec = prefix + "\n".join(link_lines) + "\n"
    if trailing:
        new_spec += "\n" + trailing
    _atomic_write(spec_md, new_spec)

    summary = []
    for target, *_ in plan:
        summary.append(f"wrote {target.relative_to(spec_dir)}")
    summary.append(f"rewrote {spec_md.name}")
    return "\n".join(summary) + "\n", 0


# ---------- end split-slices ----------


# ---------- copy-machinery (slice 021-01) ----------
#
# Reuses scaffold-mode's `copy_machinery()` façade from
# skills/scaffold-init/scaffold.py. Imports are local to the function so
# the migrate.py module stays cheap to import for the read-only `report`
# path (which is the hot path for `/jig:migrate` skill autoload).


def _load_scaffold_module(plugin: Path):
    """Load `skills/scaffold-init/scaffold.py` from the plugin root and
    return the module object.

    Why not `from skills.scaffold-init.scaffold import copy_machinery`?
    Two reasons:
      1. The directory name `scaffold-init` contains a hyphen, which is
         not a valid Python identifier — the namespace-package import
         path only works when the caller is itself loaded as part of the
         `skills` package (e.g. via `python3 -m unittest`).
      2. When `migrate.py` is run as a top-level script
         (`python3 migrate.py ...`), `skills` is not on `sys.path` and
         the namespace package is unavailable.

    File-path loading via `importlib.util` works uniformly across both
    invocation shapes."""
    import importlib.util
    scaffold_py = plugin / "skills" / "scaffold-init" / "scaffold.py"
    if not scaffold_py.is_file():
        raise MigrateError(
            f"cannot locate scaffold.py at {scaffold_py}. "
            "Check that CLAUDE_PLUGIN_ROOT points at a valid jig install."
        )
    spec = importlib.util.spec_from_file_location(
        "jig_scaffold_for_migrate", scaffold_py,
    )
    if spec is None or spec.loader is None:
        raise MigrateError(
            f"importlib failed to build a module spec for {scaffold_py}"
        )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_plugin_root() -> Path:
    """Locate the jig plugin root. Mirrors scaffold.py's `plugin_root()`
    fallback shape:
      1. `CLAUDE_PLUGIN_ROOT` env var if set;
      2. otherwise this module's parents[2] (the repo root in a
         scaffolded / plugin install).

    Kept local to migrate.py (rather than importing scaffold.py's helper)
    so that the migrate module's import surface stays minimal. The fallback
    matches the same parents[N] depth because both helpers live at
    `<plugin-root>/skills/<name>/<file>.py`."""
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def copy_machinery(
    project_dir: Path, *, force: bool = False, add_tiers: list = None,
    host: str = "claude",
) -> tuple:
    """Top-level entry for the `copy-machinery` subcommand.

    Returns `(summary_text, exit_code)`. Raises `MigrateError` on user
    error (missing dir, not a directory, or an `--add-tier` precondition
    failure). `UnmanagedHooksError` bubbles out to `main()` where it is
    converted to exit code 3 (matching `LooksAlreadySpecDrivenError`
    precedent from 008-05).

    Delegates the work to `scaffold.copy_machinery()` — slice 021-01's
    public façade over `_copy_skills_and_agents` +
    `_copy_hooks_and_register`. The two helpers each carry their own
    safety guarantees (executable-bit pinning, marker-based merge, refuse
    before mutation).

    Tier resolution (slice 038-04, ADR-0012):
    - **Plain run** (`add_tiers` falsy): the on-disk skill set is gated to
      the tiers recorded in the target's `scaffold.json`. A project never
      scaffold-init'd has no manifest → tiers unknown → copy-all (the
      spec-021 migrate default, unchanged).
    - **`--add-tier` run**: additively *upgrade* an already-scaffolded
      project. The manifest's `installed_tiers`/`installed_skills` are
      raised to include the new tier(s); only the **newly-added** tier's
      skills are copied, so existing tiers (and any local edits to their
      files) are untouched. Idempotent. Reuses copy-machinery's existing
      non-greenfield entry — the `AlreadyScaffoldedError` guard is neither
      re-implemented nor tripped."""
    if not project_dir.exists():
        raise MigrateError(f"project directory not found: {project_dir}")
    if not project_dir.is_dir():
        raise MigrateError(f"not a directory: {project_dir}")

    # Local import: keep the scaffold dependency out of the report-path
    # module load (matches the comment in `_resolve_plugin_root`). The
    # `skills/scaffold-init/` directory contains a hyphen, so the
    # namespace-package import path `skills.scaffold-init.scaffold` only
    # works when migrate.py was loaded via the same parent package. When
    # migrate.py is run as a script (`python3 migrate.py ...`), `skills`
    # is not importable. Load by file path via `importlib.util` so both
    # modes work uniformly.
    resolved_host = _resolve_host(host)
    plugin = _resolve_plugin_root()
    scaffold_mod = _load_scaffold_module(plugin)

    upgrade_note = ""
    commit_tiers = None  # set on the --add-tier path; written AFTER the copy
    if add_tiers:
        # Upgrade path: plan the new tier set (validate, no write), copy only
        # the delta, then commit the manifest — so a copy failure never
        # leaves scaffold.json claiming tiers whose skills never landed.
        try:
            old, new, added = scaffold_mod.plan_installed_tiers(
                project_dir, add_tiers,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise MigrateError(str(exc)) from exc
        copy_tiers = added  # [] when already installed → copies no new skills
        if added:
            commit_tiers = new
            upgrade_note = (
                f"upgraded tiers {old} -> {new} (added: {', '.join(added)})\n"
            )
        else:
            upgrade_note = (
                f"tiers already at {old}; nothing to add (idempotent)\n"
            )
    else:
        # Plain refresh: gate to the tiers the manifest already records;
        # None (no manifest) means copy-all.
        copy_tiers = scaffold_mod.read_installed_tiers(project_dir)

    try:
        scaffold_mod.copy_machinery(
            plugin, project_dir, force=force, installed_tiers=copy_tiers,
            host=resolved_host,
        )
    except scaffold_mod.UnmanagedHooksError as exc:
        # Re-raise as a migrate-side typed exception so main()'s
        # exception chain can route to exit 3 via isinstance, not a
        # class-name string match (reviewer-flagged at slice 021-01
        # implementation review). The manifest is NOT yet committed on the
        # upgrade path, so a refusal here leaves scaffold.json unchanged.
        raise MigrateMachineryRefusalError(str(exc)) from exc

    # Commit the raised tier set only after the delta skills copied cleanly.
    if commit_tiers is not None:
        scaffold_mod.write_installed_tiers(project_dir, commit_tiers)

    runtime_dir = ".codex" if resolved_host == "codex" else ".claude"
    return (
        f"{upgrade_note}copied machinery into {project_dir / runtime_dir}\n",
        0,
    )


# ---------- end copy-machinery ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="migrate.py",
        description="jig migrate helper (report + rename-decisions + split-slices)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser(
        "report",
        help="emit a read-only migration report for an existing project",
    )
    rp.add_argument("project_dir", help="path to the project to inventory")

    rd = sub.add_parser(
        "rename-decisions",
        help="apply ADR-0004 rename (docs/adrs/ → docs/decisions/, "
             "adr-NNNN-<slug>.md filename shape)",
    )
    rd.add_argument("project_dir", help="path to the project to migrate")
    rd.add_argument(
        "--dry-run", action="store_true",
        help="emit the operations plan to stdout without writing anything",
    )
    rd.add_argument(
        "--host", choices=("auto", "claude", "codex"), default="auto",
        help="host runtime whose primer and machinery paths should be scanned "
             "(default: auto; copied .codex helpers infer codex)",
    )

    ss = sub.add_parser(
        "split-slices",
        help="split each `## Slice` section out of <spec-dir>/spec.md "
             "into its own slice-NN-<slug>.md file (slice 018-04)",
    )
    ss.add_argument("spec_dir",
                    help="path to a spec directory (containing spec.md)")
    ss.add_argument(
        "--dry-run", action="store_true",
        help="emit the operations plan to stdout without writing anything",
    )

    cm = sub.add_parser(
        "copy-machinery",
        help="copy jig's skills, agents, hooks, and hook configuration "
             "into the target's host-local runtime (scaffold-mode parity)",
    )
    cm.add_argument("project_dir",
                    help="path to the project to receive jig's machinery")
    cm.add_argument(
        "--force", action="store_true",
        help="override the unmanaged-hooks safety check when "
             "the host hook configuration already has unmanaged entries "
             "(same escape hatch as scaffold-init's --force)",
    )
    cm.add_argument(
        "--host", choices=("auto", "claude", "codex"), default="auto",
        help="host runtime to copy into: claude => .claude/, codex => .codex/ "
             "(default: auto; copied .codex helpers infer codex)",
    )
    cm.add_argument(
        "--add-tier", dest="add_tier", action="append", metavar="TIER",
        help="additively upgrade an already-scaffolded project to include "
             "TIER (e.g. tier-1): raises scaffold.json's installed_tiers and "
             "copies only the newly-added tier's skills, leaving existing "
             "tiers untouched (repeatable; slice 038-04)",
    )
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        if ns.cmd == "report":
            text, code = report(Path(ns.project_dir))
            sys.stdout.write(text)
            return code
        if ns.cmd == "rename-decisions":
            text, code = rename_decisions(
                Path(ns.project_dir), dry_run=ns.dry_run, host=ns.host,
            )
            sys.stdout.write(text)
            return code
        if ns.cmd == "split-slices":
            text, code = split_slices(
                Path(ns.spec_dir), dry_run=ns.dry_run,
            )
            sys.stdout.write(text)
            return code
        if ns.cmd == "copy-machinery":
            text, code = copy_machinery(
                Path(ns.project_dir), force=ns.force, add_tiers=ns.add_tier,
                host=ns.host,
            )
            sys.stdout.write(text)
            return code
        # argparse `required=True` should make this unreachable.
        sys.stderr.write(f"unknown subcommand: {ns.cmd}\n")
        return 2
    except MigrateMachineryRefusalError as exc:
        sys.stderr.write(f"{exc}\n")
        return 3
    except MigrateError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors
        sys.stderr.write(f"migrate.py failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
