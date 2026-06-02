"""
usage.py — on-demand per-spec orchestrator token + cost report for jig.

Reads Claude Code's local per-session transcripts directly (no capture hook,
no ledger), attributes sessions to a spec, sums the **orchestrator**
`message.usage` token counts, and prints a token breakdown plus a
`ccusage`-based $ estimate.

This is the MVP (spec 056, slice 056-01). It counts orchestrator usage only —
subagent (`Agent`-tool) consumption lands in the parent transcript's
`toolUseResult` as a final-turn-only summary and is OUT OF SCOPE here; it
arrives in slice 056-02. The report says so, in the output.

Where transcripts live
-----------------------
Claude Code writes one JSONL file per session under
``~/.claude/projects/<encoded-cwd>/<session-id>.jsonl``, where the directory
name is the session's working directory with every ``/`` and ``.`` replaced by
``-``. A repo's main root and all its git worktrees share the main root's
encoded prefix, e.g.::

    -Users-me-Projects-demo                              (main root)
    -Users-me-Projects-demo--claude-worktrees-foo        (a worktree)

So a single prefix glob over ``~/.claude/projects/<prefix>*/*.jsonl`` spans the
repo and every worktree. The prefix is derived from the repo's **main** git
root (``git rev-parse --git-common-dir`` -> its parent), overridable with
``--main-root`` for testing.

Attribution heuristic (MVP)
---------------------------
Branch names are random codenames, so attribution is by **spec-path mentions in
the transcript content**. A session is attributed to the spec it mentions most:
the dominant of three anchored signals counted across all of the session's
text/tool content —

  * ``specs/NNN-``           (a spec-dir path)
  * ``NNN-NN``               (a slice id like ``055-01``)
  * ``spec NNN``             (prose reference)

The dominant (most-mentioned) spec number wins; ties break to the lowest
number for determinism. A session mentioning no spec is unattributed. Slice
056-03 will replace this heuristic with an exact ``.jig/spec-ref`` marker.

Cost via ccusage (pricing authority)
-------------------------------------
We never hard-code pricing. ``npx ccusage@latest --json`` reports per-model
token totals + cost under ``daily[].modelBreakdowns[]``; we derive each model's
effective ``$/token`` (cost / summed tokens) and multiply by *this spec's*
attributed per-model token totals. If ``npx``/``ccusage`` is unavailable or
errors, the token breakdown still prints and the $ line reads "unavailable".

Usage
-----
    python3 scripts/usage.py report <spec> [options]

    <spec>                A spec number (e.g. ``055``) or slug
                          (e.g. ``055-token-usage-tracking``).

Options
-------
    --projects-dir PATH   Override the ~/.claude/projects root (testability).
    --main-root PATH      Override the repo main root used to derive the
                          encoded-cwd prefix (default: the current git repo).
    --ccusage-json PATH   Read a pre-captured ``ccusage --json`` payload from a
                          file instead of shelling out (offline / testing).
    --no-ccusage          Skip ccusage entirely; print "$: unavailable".

Read-only: this tool never writes or deletes anything. The only network access
is the optional ``npx ccusage`` call (suppressed by --ccusage-json/--no-ccusage).
It never raises on a malformed or missing transcript — bad lines are skipped.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Encoded-cwd prefix derivation
# ---------------------------------------------------------------------------

def encode_cwd(path: str) -> str:
    """Encode an absolute cwd the way Claude Code names its project dirs:
    every ``/`` and ``.`` becomes ``-``.
    """
    return path.replace("/", "-").replace(".", "-")


def main_root() -> str:
    """Return the repo's main git root (worktree-agnostic), or the cwd if not
    in a git repo. ``git rev-parse --git-common-dir`` points at the shared
    ``.git`` for the main checkout even from inside a worktree; its parent is
    the main root.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return str(Path.cwd())
    common = Path(out)
    if not common.is_absolute():
        common = (Path.cwd() / common).resolve()
    # Parent of the .git common dir is the main worktree root.
    return str(common.parent)


def default_projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


# ---------------------------------------------------------------------------
# Session discovery
# ---------------------------------------------------------------------------

def find_sessions(projects_dir: Path, encoded_prefix: str) -> list:
    """Return every ``*.jsonl`` under ``projects_dir`` whose parent dir name
    starts with ``encoded_prefix`` (i.e. the repo main root + all worktrees).

    Never raises if ``projects_dir`` is missing — returns an empty list.
    """
    if not projects_dir.is_dir():
        return []
    sessions = []
    for child in sorted(projects_dir.iterdir()):
        if not child.is_dir():
            continue
        if not child.name.startswith(encoded_prefix):
            continue
        sessions.extend(sorted(child.glob("*.jsonl")))
    return sessions


# ---------------------------------------------------------------------------
# Transcript reading (robust — never throws on bad input)
# ---------------------------------------------------------------------------

def read_session(path: Path) -> list:
    """Parse a session JSONL into a list of records. Malformed lines and
    unreadable files are skipped silently (read-only, fail-soft).
    """
    records = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except (ValueError, TypeError):
                    continue
    except OSError:
        return []
    return records


def _record_texts(record: dict):
    """Yield every text fragment carried by a record's ``message.content`` —
    plain text, tool-use inputs (serialized), and tool-result text. Used for
    spec-path mention counting.
    """
    msg = record.get("message")
    if not isinstance(msg, dict):
        return
    content = msg.get("content")
    if isinstance(content, str):
        yield content
        return
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        if btype == "text":
            yield block.get("text", "") or ""
        elif btype == "tool_use":
            try:
                yield json.dumps(block.get("input", {}))
            except (TypeError, ValueError):
                pass
        elif btype == "tool_result":
            c = block.get("content")
            if isinstance(c, str):
                yield c
            elif isinstance(c, list):
                for cb in c:
                    if isinstance(cb, dict) and cb.get("type") == "text":
                        yield cb.get("text", "") or ""


# ---------------------------------------------------------------------------
# Attribution — dominant spec-path mention
# ---------------------------------------------------------------------------

# Three anchored signals. Each captures a three-digit spec number.
_SPEC_PATTERNS = (
    re.compile(r"specs/(\d{3})-"),        # a spec-dir path
    re.compile(r"\b(\d{3})-\d{2}\b"),     # a slice id, e.g. 055-01
    re.compile(r"\bspec\s+(\d{3})\b", re.IGNORECASE),  # prose "spec 055"
)


def count_spec_mentions(records: list) -> dict:
    """Return ``{spec_number: count}`` of anchored spec-path mentions across a
    session's content.
    """
    counts = {}
    for rec in records:
        for text in _record_texts(rec):
            if not text:
                continue
            for pat in _SPEC_PATTERNS:
                for m in pat.finditer(text):
                    n = m.group(1)
                    counts[n] = counts.get(n, 0) + 1
    return counts


def dominant_spec(records: list):
    """Return the most-mentioned spec number in a session, or ``None`` if the
    session mentions no spec. Ties break to the lowest number (deterministic).
    """
    counts = count_spec_mentions(records)
    if not counts:
        return None
    # Highest count wins; tie -> lowest spec number.
    return min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]


# ---------------------------------------------------------------------------
# Token summing (orchestrator message.usage)
# ---------------------------------------------------------------------------

_USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def sum_usage(records: list) -> dict:
    """Sum the four orchestrator usage fields across assistant records that
    carry a ``message.usage`` block. Also collects the set of models seen.

    Returns a dict with the four token fields, ``models`` (sorted list), and a
    ``per_model`` map. Records without ``usage`` are skipped.
    """
    totals = {f: 0 for f in _USAGE_FIELDS}
    per_model = {}
    models = set()
    for rec in records:
        if rec.get("type") not in (None, "assistant"):
            # Only orchestrator assistant turns carry message.usage we count.
            # (User/system/summary records have no usage.)
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        model = msg.get("model") or "unknown"
        models.add(model)
        slot = per_model.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
        for f in _USAGE_FIELDS:
            val = usage.get(f, 0)
            if not isinstance(val, (int, float)):
                continue
            totals[f] += int(val)
            slot[f] += int(val)
    totals["models"] = sorted(models)
    totals["per_model"] = per_model
    return totals


# ---------------------------------------------------------------------------
# ccusage — derive per-model effective $/token, apply to attributed totals
# ---------------------------------------------------------------------------

_CCUSAGE_TOKEN_KEYS = (
    "inputTokens",
    "outputTokens",
    "cacheReadTokens",
    "cacheCreationTokens",
)


def ccusage_rates_from_json(payload: dict) -> dict:
    """Derive ``{model_name: effective_$_per_token}`` from a ``ccusage --json``
    payload by aggregating cost and token counts across every
    ``daily[].modelBreakdowns[]`` entry. Models with zero summed tokens are
    skipped (no defined rate).
    """
    cost_by_model = {}
    tokens_by_model = {}
    daily = payload.get("daily") if isinstance(payload, dict) else None
    if not isinstance(daily, list):
        return {}
    for day in daily:
        if not isinstance(day, dict):
            continue
        for mb in day.get("modelBreakdowns", []) or []:
            if not isinstance(mb, dict):
                continue
            name = mb.get("modelName")
            if not name:
                continue
            cost = mb.get("cost", 0) or 0
            toks = sum(int(mb.get(k, 0) or 0) for k in _CCUSAGE_TOKEN_KEYS)
            cost_by_model[name] = cost_by_model.get(name, 0.0) + float(cost)
            tokens_by_model[name] = tokens_by_model.get(name, 0) + toks
    rates = {}
    for name, toks in tokens_by_model.items():
        if toks > 0:
            rates[name] = cost_by_model[name] / toks
    return rates


# Wall-clock ceiling for the ``npx ccusage@latest`` call. ``npx`` may fetch the
# package on first run, so a stalled network must not hang ``report``
# indefinitely — on timeout ``subprocess.run`` raises ``TimeoutExpired``, which
# (like any other ccusage failure) degrades to "$ unavailable" with the token
# breakdown intact.
_CCUSAGE_TIMEOUT_S = 60


def run_ccusage_npx() -> dict:
    """Invoke ``npx ccusage@latest --json`` and return the parsed payload.

    Raises on failure (missing npx, non-zero exit, bad JSON, or a
    ``TimeoutExpired`` if the call exceeds ``_CCUSAGE_TIMEOUT_S``) so the caller
    can catch and degrade. This is the default runner; tests inject their own.
    """
    proc = subprocess.run(
        ["npx", "ccusage@latest", "--json"],
        capture_output=True, text=True, check=True,
        timeout=_CCUSAGE_TIMEOUT_S,
    )
    return json.loads(proc.stdout)


def apply_rates(per_model: dict, rates: dict):
    """Apply per-model effective rates to attributed per-model token totals.

    Returns ``(cost_usd, note)``. If no attributed model has a known rate,
    returns ``(None, <reason>)`` so the caller can show "unavailable".
    """
    if not rates:
        return None, "ccusage returned no usable rates"
    total = 0.0
    matched = False
    unmatched = []
    for model, toks in per_model.items():
        rate = rates.get(model)
        if rate is None:
            unmatched.append(model)
            continue
        matched = True
        total += rate * sum(int(toks.get(f, 0)) for f in _USAGE_FIELDS)
    if not matched:
        return None, (
            "ccusage has no rate for "
            + (", ".join(sorted(per_model)) or "the attributed model(s)")
        )
    return total, ("partial: no rate for " + ", ".join(unmatched)) if unmatched else None


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

@dataclass
class Report:
    spec: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    session_count: int = 0
    models: list = field(default_factory=list)
    per_model: dict = field(default_factory=dict)
    cost_usd: float = None
    cost_note: str = None

    @property
    def total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens
                + self.cache_read_tokens + self.cache_creation_tokens)


def _spec_number(spec: str) -> str:
    """Normalize a spec argument (number or slug) to a three-digit number.

    ``055`` -> ``055``; ``055-token-usage-tracking`` -> ``055``;
    ``55`` -> ``055`` (zero-padded). Returns the leading numeric run if it
    can't fully normalize, so attribution still has something to match.
    """
    m = re.match(r"\s*0*(\d+)", spec)
    if not m:
        return spec.strip()
    return f"{int(m.group(1)):03d}"


def build_report(spec: str, projects_dir: Path, encoded_prefix: str,
                 ccusage_runner=run_ccusage_npx) -> Report:
    """Build a per-spec orchestrator usage report.

    Parameters
    ----------
    spec : str
        Spec number or slug; normalized to a number for attribution.
    projects_dir : Path
        Root of the ~/.claude/projects tree (override for testing).
    encoded_prefix : str
        Encoded main-root prefix; sessions under dirs starting with this are
        scanned (spans worktrees).
    ccusage_runner : callable | None
        Zero-arg callable returning a parsed ``ccusage --json`` payload, or
        ``None`` to skip ccusage. Raising is fine — it degrades to
        "unavailable". This is the injection seam keeping tests offline.

    Read-only: reads transcripts (+ optionally runs ccusage); never writes.
    """
    target = _spec_number(spec)
    rep = Report(spec=target)

    attributed = []
    for session_path in find_sessions(projects_dir, encoded_prefix):
        records = read_session(session_path)
        if not records:
            continue
        if dominant_spec(records) == target:
            attributed.append(records)

    models = set()
    per_model = {}
    for records in attributed:
        sums = sum_usage(records)
        rep.input_tokens += sums["input_tokens"]
        rep.output_tokens += sums["output_tokens"]
        rep.cache_read_tokens += sums["cache_read_input_tokens"]
        rep.cache_creation_tokens += sums["cache_creation_input_tokens"]
        models.update(sums["models"])
        for model, slot in sums["per_model"].items():
            agg = per_model.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
            for f in _USAGE_FIELDS:
                agg[f] += slot[f]
    rep.session_count = len(attributed)
    rep.models = sorted(models)
    rep.per_model = per_model

    # Cost via ccusage (optional, fail-soft).
    if ccusage_runner is None:
        rep.cost_usd = None
        rep.cost_note = "ccusage not run"
    else:
        try:
            payload = ccusage_runner()
            rates = ccusage_rates_from_json(payload)
            cost, note = apply_rates(per_model, rates)
            rep.cost_usd = cost
            rep.cost_note = note
        except Exception as exc:  # noqa: BLE001 — degrade on ANY ccusage error
            rep.cost_usd = None
            rep.cost_note = f"ccusage unavailable ({exc.__class__.__name__})"

    return rep


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def render(rep: Report) -> str:
    lines = []
    lines.append(f"## Token usage — spec {rep.spec} (orchestrator)")
    lines.append("")
    if rep.session_count == 0:
        lines.append(
            f"No sessions attributed to spec {rep.spec} "
            f"(no spec-path mentions found in any transcript)."
        )
        lines.append("")
        lines.append(f"  Total tokens: 0")
        lines.append(f"  $ estimate:   n/a")
        lines.append("")
        _append_framing(lines, rep)
        return "\n".join(lines) + "\n"

    lines.append(f"  Sessions:               {rep.session_count}")
    lines.append(f"  Models:                 {', '.join(rep.models) or 'unknown'}")
    lines.append("")
    lines.append(f"  input_tokens:           {_fmt(rep.input_tokens)}")
    lines.append(f"  output_tokens:          {_fmt(rep.output_tokens)}")
    lines.append(f"  cache_read_tokens:      {_fmt(rep.cache_read_tokens)}")
    lines.append(f"  cache_creation_tokens:  {_fmt(rep.cache_creation_tokens)}")
    lines.append(f"  ------------------------")
    lines.append(f"  total_tokens:           {_fmt(rep.total_tokens)}")
    lines.append("")
    if rep.cost_usd is not None:
        lines.append(f"  $ estimate (ccusage):   ${rep.cost_usd:,.2f}")
        if rep.cost_note:
            lines.append(f"    note: {rep.cost_note}")
    else:
        reason = rep.cost_note or "ccusage not found"
        lines.append(f"  $ estimate:             unavailable ({reason})")
    lines.append("")
    _append_framing(lines, rep)
    return "\n".join(lines) + "\n"


def _append_framing(lines: list, rep: Report) -> None:
    lines.append(
        "Note: the $ figure is an ESTIMATE — notional under subscription "
        "billing (ccusage applies per-model API rates to the attributed "
        "token totals)."
    )
    lines.append(
        "This MVP counts ORCHESTRATOR usage only; subagent (delegated) usage "
        "is not yet included — it arrives in slice 056-02."
    )
    lines.append(
        "Attribution is a content heuristic (dominant spec-path mention); an "
        "exact .jig/spec-ref marker arrives in slice 056-03."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="usage.py",
        description="On-demand per-spec orchestrator token + cost report.",
    )
    sub = p.add_subparsers(dest="command")

    rep = sub.add_parser(
        "report",
        help="report orchestrator token usage + ccusage $ for a spec",
    )
    rep.add_argument("spec", help="spec number (e.g. 055) or slug")
    rep.add_argument(
        "--projects-dir", default=None, metavar="PATH",
        help="override the ~/.claude/projects root (testing seam)",
    )
    rep.add_argument(
        "--main-root", default=None, metavar="PATH",
        help="override the repo main root used to derive the encoded prefix",
    )
    rep.add_argument(
        "--ccusage-json", default=None, metavar="PATH",
        help="read a pre-captured ccusage --json payload from a file "
             "instead of shelling out (offline)",
    )
    rep.add_argument(
        "--no-ccusage", action="store_true",
        help="skip ccusage entirely; show '$: unavailable'",
    )
    return p


def _make_ccusage_runner(ns):
    """Resolve the ccusage seam from CLI flags into a runner callable (or
    None). --no-ccusage wins; then --ccusage-json (read a file); else the
    real npx runner.
    """
    if ns.no_ccusage:
        return None
    if ns.ccusage_json:
        path = Path(ns.ccusage_json)

        def _from_file():
            return json.loads(path.read_text())

        return _from_file
    return run_ccusage_npx


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    if ns.command != "report":
        parser.print_help(sys.stderr)
        return 2

    projects_dir = (Path(ns.projects_dir) if ns.projects_dir
                    else default_projects_dir())
    root = ns.main_root if ns.main_root else main_root()
    encoded_prefix = encode_cwd(root)
    runner = _make_ccusage_runner(ns)

    rep = build_report(
        spec=ns.spec,
        projects_dir=projects_dir,
        encoded_prefix=encoded_prefix,
        ccusage_runner=runner,
    )
    sys.stdout.write(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
