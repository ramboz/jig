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
        rows.append(f"| `docs/workflow.md` | 1 | workflow doc present |")
    if inv.architecture is not None:
        rows.append(f"| `docs/architecture.md` | 1 | architecture doc present |")
    if inv.product_vision is not None:
        rows.append(f"| `docs/product-vision.md` | 1 | product-vision doc present |")
    if inv.custom_skills:
        names = ", ".join(f"`{p.name}`" for p in inv.custom_skills)
        rows.append(f"| `.claude/skills/` | {len(inv.custom_skills)} | "
                    f"custom skills: {names} (out of 008-01 scope) |")
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
    parts.append(render_operations(inv, verdict))
    parts.append("")
    return "\n".join(parts)


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


def _walk_text_files(project_dir: Path) -> list:
    """Yield text files under `project_dir/docs/`, `project_dir/CLAUDE.md`,
    and `project_dir/.claude/`. Honors `_SKIP_PATH_NAMES`."""
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

    _walk(project_dir / "docs")
    claude_md = project_dir / "CLAUDE.md"
    if claude_md.is_file() and _is_text_path(claude_md):
        out.append(claude_md)
    _walk(project_dir / ".claude")
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


def plan_rename(project_dir: Path) -> RenamePlan:
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
        project_dir, old_dir_str, new_dir_str, name_map,
    )

    return RenamePlan(
        dir_rename=dir_rename,
        file_renames=tuple(file_renames),
        cross_ref_rewrites=tuple(cross_ref_rewrites),
    )


def _plan_cross_refs(project_dir: Path, old_dir: str, new_dir: str,
                     name_map: dict) -> list:
    """Scan text files under in-scope roots and identify which need
    rewriting. Returns a sorted list of CrossRefRewrite entries."""
    rewrites = []
    for path in _walk_text_files(project_dir):
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


def rename_decisions(project_dir: Path, dry_run: bool = False) -> tuple:
    """Top-level entry for the rename-decisions subcommand.

    Returns `(summary_text, exit_code)`."""
    plan = plan_rename(project_dir)
    if plan.is_empty():
        return ("already aligned: nothing to do\n", 0)
    lines = apply_rename(plan, project_dir, dry_run=dry_run)
    return ("\n".join(lines) + "\n", 0)


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="migrate.py",
        description="jig migrate helper (report + rename-decisions)",
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
                Path(ns.project_dir), dry_run=ns.dry_run,
            )
            sys.stdout.write(text)
            return code
        # argparse `required=True` should make this unreachable.
        sys.stderr.write(f"unknown subcommand: {ns.cmd}\n")
        return 2
    except MigrateError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors
        sys.stderr.write(f"migrate.py failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
