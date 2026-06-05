"""
jig stocktake — slice 001-04 (deferred-decisions)

Reports reconciled-slice count and lists deferred items from refinement-todo.md.
When ≥3 slices are RECONCILED or DONE, surfaces a "review for promotion" suggestion.

User invokes manually:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/scaffold-init/stocktake.py <target>

Per Spike 001a + slice 001-04 plan: "spec" is interpreted as "slice" here, since
slice-level completion is the practical pulse of the workflow.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Threshold below which we don't surface the promotion suggestion.
PROMOTION_THRESHOLD = 3

# Slice statuses that count as "reconciled" for the purposes of stocktake.
DONE_STATUSES = ("DONE", "RECONCILED")


@dataclass
class DeferredItem:
    name: str
    category: str
    reason: str
    trigger: str


def count_reconciled_slices(target: Path) -> int:
    """Count occurrences of **STATUS: DONE** or **STATUS: RECONCILED** across
    all docs/specs/*/spec.md files. Each occurrence = one slice."""
    specs_dir = target / "docs" / "specs"
    if not specs_dir.is_dir():
        return 0
    count = 0
    pattern = re.compile(
        rf"\*\*STATUS:\s+({'|'.join(DONE_STATUSES)})\*\*",
        re.IGNORECASE,
    )
    for spec_md in specs_dir.glob("*/spec.md"):
        try:
            count += len(pattern.findall(spec_md.read_text()))
        except Exception:
            continue
    return count


def parse_deferred_items(target: Path) -> list:
    """Parse `docs/refinement-todo.md` into a list of DeferredItem.
    Returns empty list if the file is missing or malformed."""
    todo_path = target / "docs" / "refinement-todo.md"
    if not todo_path.is_file():
        return []
    try:
        text = todo_path.read_text()
    except Exception:
        return []

    items: list[DeferredItem] = []
    # Walk top-level categories (## ...). Inside each, find ### Decision: blocks.
    cat_pattern = re.compile(r"(?ms)^##\s+(?P<cat>[^\n]+?)\n(?P<body>.*?)(?=^##\s|\Z)")
    dec_pattern = re.compile(
        r"(?ms)^###\s+Decision:\s+(?P<name>[^\n]+?)\n(?P<body>.*?)(?=^###\s|^##\s|\Z)"
    )
    for cm in cat_pattern.finditer(text):
        category = cm.group("cat").strip()
        # Skip the top-level title "# Refinement Todo" handled separately
        if category.lower().startswith("refinement todo"):
            continue
        for dm in dec_pattern.finditer(cm.group("body")):
            name = dm.group("name").strip()
            body = dm.group("body")
            reason = _extract_line(body, "**Deferred:**")
            trigger = _extract_line(body, "**Resolution trigger:**")
            items.append(DeferredItem(
                name=name, category=category, reason=reason, trigger=trigger,
            ))
    return items


def _extract_line(body: str, prefix: str) -> str:
    """Pull the inline content after a bold prefix marker on its own line."""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix):].strip()
    return ""


def render_report(reconciled_count: int, items: list) -> str:
    """Build a markdown report. Includes a promotion suggestion when threshold met."""
    out = ["# Stocktake", ""]
    out.append(f"- Reconciled slices: **{reconciled_count}**")
    out.append(f"- Deferred items: **{len(items)}**")
    out.append("")

    if items:
        out.append("## Deferred items")
        out.append("")
        # Group by category for readability
        by_cat: dict[str, list[DeferredItem]] = {}
        for item in items:
            by_cat.setdefault(item.category, []).append(item)
        for cat in sorted(by_cat):
            out.append(f"### {cat}")
            out.append("")
            for item in by_cat[cat]:
                out.append(f"- **Decision: {item.name}**")
                if item.trigger:
                    out.append(f"  - Resolution trigger: {item.trigger}")
            out.append("")
    else:
        out.append("_(0 deferred items found.)_")
        out.append("")

    if reconciled_count >= PROMOTION_THRESHOLD and items:
        out.append("## Suggestion")
        out.append("")
        out.append(
            f"With **{reconciled_count}** reconciled slices, several deferred decisions "
            "may now have signal. **Review the items above for promotion** to specs or "
            "ADRs:"
        )
        out.append("")
        for item in items:
            out.append(f"- promote `{item.name}` → consider writing an ADR or new spec")
        out.append("")

    return "\n".join(out) + "\n"


def main(argv: list) -> int:
    if len(argv) != 2:
        sys.stderr.write("usage: stocktake.py <target-dir>\n")
        return 2

    target = Path(argv[1]).resolve()
    if not target.is_dir():
        sys.stderr.write(f"not a directory: {target}\n")
        return 1

    count = count_reconciled_slices(target)
    items = parse_deferred_items(target)
    sys.stdout.write(render_report(count, items))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
