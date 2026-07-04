"""Memory-recall verification — the cheapest-first-cut mitigation named in
the refinement-todo "Memory-recall verification (claims-from-memory
linter)" entry.

Scans the most recent assistant turn for spec/slice/ADR references and
cross-checks each against the on-disk inventory, so a stale or
hallucinated claim ("spec 042 has slice X", "ADR-0099 says Y") gets
flagged before it goes unverified for the rest of the session.

Deliberately narrow — the "cheap first cut" the refinement-todo entry
names, not the full claims-from-memory linter it describes:
- Only the three canonical shapes the entry itself names — `spec NNN`,
  `slice NNN-NN`, `ADR-NNNN` — not arbitrary file paths or symbol names
  (the entry's open question 3 is left for a future, broader pass).
- Same-turn framing (open question 2): only the LAST assistant message is
  scanned, so a flagged claim surfaces once, right after the turn that
  made it, instead of re-nagging on every later Stop in the session.
- Fixed to jig's default layout (docs/specs/, docs/decisions/) — a
  project using a configurable docs_root (ADR-0033) is a known gap, not
  solved here.
- A reference to a not-yet-created spec/ADR number (a legitimate forward
  mention, e.g. proposing "spec 090" before reserving it) will also read
  as unresolved — an accepted false-positive for a first cut; the warning
  says "verify", not "this is wrong".

Python 3.9 compatible.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass

_SPEC_RE = re.compile(r"\bspec\s+(\d{1,3})\b", re.IGNORECASE)
_SLICE_RE = re.compile(r"\bslice\s+(\d{1,3})-(\d{1,3})\b", re.IGNORECASE)
_ADR_RE = re.compile(r"\badr-(\d{1,4})\b", re.IGNORECASE)


@dataclass
class Claim:
    kind: str      # "spec" | "slice" | "adr"
    label: str     # e.g. "spec 999", "slice 042-99", "ADR-0099"
    resolved: bool


def _extract_text(content):
    """Return only human-prose text from a message's content (mirrors
    lib/decision_scan.py's helper of the same name — tool_use/tool_result
    blocks are not prose and must not be scanned)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def last_assistant_text(messages) -> str:
    """Return the most recent assistant message's prose text, or ""."""
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            return _extract_text(msg.get("content"))
    return ""


def _spec_dir(project_dir, num: int):
    matches = glob.glob(os.path.join(project_dir, "docs", "specs", f"{num:03d}-*"))
    return matches[0] if matches else None


def _spec_exists(project_dir, num: int) -> bool:
    return _spec_dir(project_dir, num) is not None


def _slice_exists(project_dir, spec_num: int, slice_num: int) -> bool:
    spec_dir = _spec_dir(project_dir, spec_num)
    if spec_dir is None:
        return False
    if glob.glob(os.path.join(spec_dir, f"slice-{slice_num:02d}-*.md")):
        return True
    spec_md = os.path.join(spec_dir, "spec.md")
    if os.path.isfile(spec_md):
        try:
            with open(spec_md, encoding="utf-8", errors="replace") as f:
                body = f.read()
        except Exception:
            return False
        if re.search(rf"##\s+Slice\s+{spec_num:03d}-{slice_num:02d}\b", body):
            return True
    return False


def _adr_exists(project_dir, num: int) -> bool:
    matches = glob.glob(
        os.path.join(project_dir, "docs", "decisions", f"adr-{num:04d}-*.md"))
    return bool(matches)


def scan_claims(project_dir, text: str) -> list:
    """Extract spec/slice/ADR claims from `text` and check each against the
    on-disk inventory under `project_dir`. Returns a list of `Claim`, in
    first-appearance order, deduped by label."""
    seen = set()
    claims = []
    for m in _SPEC_RE.finditer(text or ""):
        num = int(m.group(1))
        label = f"spec {num}"
        if label in seen:
            continue
        seen.add(label)
        claims.append(Claim("spec", label, _spec_exists(project_dir, num)))
    for m in _SLICE_RE.finditer(text or ""):
        spec_num, slice_num = int(m.group(1)), int(m.group(2))
        label = f"slice {spec_num:03d}-{slice_num:02d}"
        if label in seen:
            continue
        seen.add(label)
        claims.append(Claim(
            "slice", label, _slice_exists(project_dir, spec_num, slice_num)))
    for m in _ADR_RE.finditer(text or ""):
        num = int(m.group(1))
        label = f"ADR-{num:04d}"
        if label in seen:
            continue
        seen.add(label)
        claims.append(Claim("adr", label, _adr_exists(project_dir, num)))
    return claims


def render_warning(claims: list) -> str:
    """additionalContext text naming the unresolved claims, or "" if all
    resolved (or none found)."""
    unresolved = [c for c in claims if not c.resolved]
    if not unresolved:
        return ""
    lines = "\n".join(f"- {c.label}" for c in unresolved)
    return (
        "Memory-recall check: the previous message referenced the "
        f"following, but no matching artifact was found on disk:\n{lines}\n\n"
        "Before relying on these, verify they exist (or were renamed / "
        "renumbered / not yet reserved) rather than assuming the "
        "reference is current."
    )
