"""
jig migrate helper — slice 008-01 (migrate-report)

Read-only inventory + mapping report for an existing project considering
jig adoption. Mirrors the workflow.py / review.py / adr.py / tdd.py /
land.py shape: SKILL.md drives judgment; this script does filesystem
walk + report generation. NO filesystem mutations whatsoever.

One subcommand:
    python3 migrate.py report <project-dir>

The report has five sections in fixed order:
    Inventory   — what's present (paths + counts + shape notes)
    Mapping     — current path/name → jig path/name translations
    Conflicts   — situations that block migration
    Ambiguities — judgment calls the user must make
    Operations  — suggested next migrate.py subcommand invocations

Exit codes:
    0 — adoptable verdict OR not-yet-spec-driven (report is the deliverable)
    1 — partial verdict (informational; report still emits)
    2 — user error (missing dir, dir not readable, dir is not a directory)

Future subcommands (slice 008-02 and later):
    rename-decisions   — apply ADR-0004 rename
    slice-to-spec      — synthesize parent specs from milestones
"""

import argparse
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


# ---------- CLI plumbing ----------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="migrate.py",
        description="jig migrate helper (report)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    rp = sub.add_parser(
        "report",
        help="emit a read-only migration report for an existing project",
    )
    rp.add_argument("project_dir", help="path to the project to inventory")
    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    try:
        text, code = report(Path(ns.project_dir))
        sys.stdout.write(text)
        return code
    except MigrateError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2
    except Exception as exc:  # noqa: BLE001 — surface programming errors
        sys.stderr.write(f"migrate.py failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
