"""
usage.py — on-demand per-spec token + cost report for jig (orchestrator +
subagent).

Reads Claude Code's local per-session transcripts directly (no capture hook,
no ledger), attributes sessions to a spec, sums the per-turn `message.usage`
token counts, and prints a token breakdown plus a `ccusage`-based $ estimate.

The report is split into two MEASURED dimensions plus their combined total
(spec 056):

  * ORCHESTRATOR (slice 056-01) — the flat session files
    ``<encoded-cwd>/<session>.jsonl``.
  * SUBAGENT (slice 056-02) — each delegated (``Agent``-tool) turn's full
    transcript, nested at ``<encoded-cwd>/<session>/subagents/agent-*.jsonl``
    (``isSidechain: true``, per-turn ``message.usage``, subagent type in the
    top-level ``attributionAgent`` field). Summed directly — measured, NOT the
    lossy ``toolUseResult`` final-turn proxy. Broken down by subagent type.

  * COMBINED — orchestrator + subagent = the true per-spec cost shape.

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
``--main-root`` for testing. Each attributed session's nested
``<session>/subagents/`` dir (if present) carries its delegated-turn
transcripts.

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
number for determinism. A session mentioning no spec is unattributed. When a
session's ``cwd`` carries a ``.jig/spec-ref`` marker (slice 056-03), that exact
attribution is preferred and this content heuristic is the fallback.

Cost via ccusage (pricing authority)
-------------------------------------
We never hard-code pricing. ``npx ccusage@latest --json`` reports per-model
token totals + cost under ``daily[].modelBreakdowns[]``; we derive each model's
effective ``$/token`` (cost / summed tokens) and multiply by *this spec's*
attributed per-model token totals — applied to the orchestrator, subagent, and
combined dimensions alike. If ``npx``/``ccusage`` is unavailable or errors, the
token breakdowns still print and the $ lines read "unavailable".

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


def find_subagent_files(session_path: Path) -> list:
    """Return the nested subagent transcripts for a flat session file.

    Claude Code writes each delegated (``Agent``-tool) turn's full transcript
    to ``<dir>/<session-uuid>/subagents/agent-*.jsonl`` — a sibling directory
    named for the session UUID (the flat session is ``<dir>/<uuid>.jsonl``).
    Given the flat session path, return the sorted ``agent-*.jsonl`` files in
    that nested dir, or an empty list if the dir is absent (a session that
    delegated nothing). Never raises.
    """
    nested = session_path.with_suffix("") / "subagents"
    if not nested.is_dir():
        return []
    try:
        return sorted(nested.glob("agent-*.jsonl"))
    except OSError:
        return []


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
# Exact attribution — the `.jig/spec-ref` marker (slice 056-03)
# ---------------------------------------------------------------------------
#
# `workflow.py transition ... IN_PROGRESS` stamps `<cwd>/.jig/spec-ref` with
# the spec being worked on. Format (line-oriented `key=value`, agreed with the
# writer in skills/spec-workflow/workflow.py):
#
#     spec=056
#     slice=056-03
#
# We read the `spec=` line and normalize it to a three-digit number — the same
# key the content heuristic produces, so the rest of the pipeline is identical
# whichever source attributed the session. Read-only and fail-soft: a missing /
# unreadable / spec-less marker simply returns None (caller falls back to the
# content heuristic).

_SPEC_REF_RE = re.compile(r"(?m)^\s*spec\s*=\s*(\d{1,3})\s*$")


def read_spec_ref_marker(cwd):
    """Return the three-digit spec number recorded in ``<cwd>/.jig/spec-ref``,
    or ``None`` when the marker is absent, unreadable, or has no ``spec=``
    line. Never raises (read-only, fail-soft).
    """
    if not cwd:
        return None
    try:
        marker = Path(cwd) / ".jig" / "spec-ref"
        text = marker.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None
    m = _SPEC_REF_RE.search(text)
    if not m:
        return None
    return f"{int(m.group(1)):03d}"


def session_cwd(records: list):
    """Return the working directory a session ran in (the ``cwd`` field carried
    on its records), or ``None`` if no record carries one. Used to locate the
    session's ``.jig/spec-ref`` marker.
    """
    for rec in records:
        if isinstance(rec, dict):
            cwd = rec.get("cwd")
            if cwd:
                return cwd
    return None


def attribute_session(records: list):
    """Resolve a session to ``(spec_number, method)``.

    Prefers the exact ``.jig/spec-ref`` marker in the session's ``cwd`` (method
    ``"marker"``); falls back to the dominant content-mention heuristic (method
    ``"heuristic"``). Returns ``(None, None)`` when neither attributes the
    session. The marker wins even when content dominantly mentions a different
    spec — the marker is the deliberate, authoritative signal (slice 056-03).
    """
    marked = read_spec_ref_marker(session_cwd(records))
    if marked is not None:
        return marked, "marker"
    guessed = dominant_spec(records)
    if guessed is not None:
        return guessed, "heuristic"
    return None, None


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


def sum_subagent_usage(records: list) -> dict:
    """Sum the four usage fields across nested-subagent assistant turns, and
    break the totals down by subagent type (the top-level ``attributionAgent``
    field on each record).

    Unlike :func:`sum_usage` (which counts the orchestrator's flat session),
    this reads the per-turn ``message.usage`` of an ``agent-*.jsonl`` nested
    transcript — measured, not a proxy (slice 056-02). Records without a
    ``message.usage`` block are skipped.

    Returns a dict with the four token fields, ``per_model`` (for ccusage
    costing) and ``by_type`` (``{attributionAgent: {<four fields>}}``).
    """
    totals = {f: 0 for f in _USAGE_FIELDS}
    per_model = {}
    by_type = {}
    for rec in records:
        if rec.get("type") not in (None, "assistant"):
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        model = msg.get("model") or "unknown"
        agent = rec.get("attributionAgent") or "unknown"
        mslot = per_model.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
        tslot = by_type.setdefault(agent, {f: 0 for f in _USAGE_FIELDS})
        for f in _USAGE_FIELDS:
            val = usage.get(f, 0)
            if not isinstance(val, (int, float)):
                continue
            totals[f] += int(val)
            mslot[f] += int(val)
            tslot[f] += int(val)
    totals["per_model"] = per_model
    totals["by_type"] = by_type
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
    # Orchestrator (flat session) totals -- slice 056-01, measured.
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    session_count: int = 0
    # Attribution-confidence split (slice 056-03): how many attributed
    # sessions came from the exact `.jig/spec-ref` marker vs. the content
    # heuristic. marker + heuristic == session_count.
    marker_session_count: int = 0
    heuristic_session_count: int = 0
    models: list = field(default_factory=list)
    per_model: dict = field(default_factory=dict)
    cost_usd: float = None
    cost_note: str = None
    # Subagent (nested transcript) totals -- slice 056-02, measured (not a
    # proxy): summed from each session's <uuid>/subagents/agent-*.jsonl.
    subagent_input_tokens: int = 0
    subagent_output_tokens: int = 0
    subagent_cache_read_tokens: int = 0
    subagent_cache_creation_tokens: int = 0
    subagent_per_model: dict = field(default_factory=dict)
    subagent_by_type: dict = field(default_factory=dict)
    subagent_cost_usd: float = None
    subagent_cost_note: str = None
    # Combined = orchestrator + subagent = the true per-spec cost.
    combined_cost_usd: float = None
    combined_cost_note: str = None

    @property
    def total_tokens(self) -> int:
        return (self.input_tokens + self.output_tokens
                + self.cache_read_tokens + self.cache_creation_tokens)

    @property
    def subagent_total_tokens(self) -> int:
        return (self.subagent_input_tokens + self.subagent_output_tokens
                + self.subagent_cache_read_tokens
                + self.subagent_cache_creation_tokens)

    @property
    def combined_total_tokens(self) -> int:
        return self.total_tokens + self.subagent_total_tokens


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
    """Build a per-spec usage report: measured orchestrator (flat sessions)
    + measured subagent (nested transcripts) token totals and $ costs, plus
    their combined total (= the true per-spec cost).

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

    # Attribute sessions, keeping the session PATH so we can locate each
    # session's nested subagent transcripts (slice 056-02). Slice 056-03:
    # prefer the exact `.jig/spec-ref` marker; fall back to the content
    # heuristic — and record which, so the report can flag confidence.
    attributed = []
    marker_count = 0
    heuristic_count = 0
    for session_path in find_sessions(projects_dir, encoded_prefix):
        records = read_session(session_path)
        if not records:
            continue
        spec_num, method = attribute_session(records)
        if spec_num == target:
            attributed.append((session_path, records))
            if method == "marker":
                marker_count += 1
            else:
                heuristic_count += 1

    # Orchestrator (flat session) totals — slice 056-01, unchanged.
    models = set()
    per_model = {}
    # Subagent (nested transcript) totals — slice 056-02, measured.
    sub_per_model = {}
    sub_by_type = {}
    for session_path, records in attributed:
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

        # Sum this session's nested subagent transcripts (if any). A session
        # that delegated nothing has no nested dir -> contributes zero,
        # silently. A malformed nested file is skipped by read_session.
        for agent_path in find_subagent_files(session_path):
            agent_records = read_session(agent_path)
            if not agent_records:
                continue
            asums = sum_subagent_usage(agent_records)
            rep.subagent_input_tokens += asums["input_tokens"]
            rep.subagent_output_tokens += asums["output_tokens"]
            rep.subagent_cache_read_tokens += asums["cache_read_input_tokens"]
            rep.subagent_cache_creation_tokens += \
                asums["cache_creation_input_tokens"]
            for model, slot in asums["per_model"].items():
                agg = sub_per_model.setdefault(
                    model, {f: 0 for f in _USAGE_FIELDS})
                for f in _USAGE_FIELDS:
                    agg[f] += slot[f]
            for agent, slot in asums["by_type"].items():
                agg = sub_by_type.setdefault(
                    agent, {f: 0 for f in _USAGE_FIELDS})
                for f in _USAGE_FIELDS:
                    agg[f] += slot[f]

    rep.session_count = len(attributed)
    rep.marker_session_count = marker_count
    rep.heuristic_session_count = heuristic_count
    rep.models = sorted(models)
    rep.per_model = per_model
    rep.subagent_per_model = sub_per_model
    rep.subagent_by_type = sub_by_type

    # Cost via ccusage (optional, fail-soft) — applied to BOTH the
    # orchestrator and subagent per-model totals using the SAME rates, with
    # the combined being their sum (= the true per-spec cost). Any ccusage
    # error degrades all three to unavailable (token breakdowns intact).
    if ccusage_runner is None:
        note = "ccusage not run"
        rep.cost_usd = None
        rep.cost_note = note
        rep.subagent_cost_usd = None
        rep.subagent_cost_note = note
        rep.combined_cost_usd = None
        rep.combined_cost_note = note
    else:
        try:
            payload = ccusage_runner()
            rates = ccusage_rates_from_json(payload)
            rep.cost_usd, rep.cost_note = apply_rates(per_model, rates)
            # No delegated turns -> a MEASURED subagent $0.0 (not "unavailable":
            # the absence of subagents is real data, distinct from a pricing
            # failure). With tokens present, price them like the orchestrator.
            if not sub_per_model:
                rep.subagent_cost_usd = 0.0
                rep.subagent_cost_note = "no subagent usage"
            else:
                rep.subagent_cost_usd, rep.subagent_cost_note = apply_rates(
                    sub_per_model, rates)
            rep.combined_cost_usd, rep.combined_cost_note = apply_rates(
                _merge_per_model(per_model, sub_per_model), rates)
        except Exception as exc:  # noqa: BLE001 — degrade on ANY ccusage error
            note = f"ccusage unavailable ({exc.__class__.__name__})"
            rep.cost_usd = None
            rep.cost_note = note
            rep.subagent_cost_usd = None
            rep.subagent_cost_note = note
            rep.combined_cost_usd = None
            rep.combined_cost_note = note

    return rep


def _merge_per_model(*maps) -> dict:
    """Sum several ``{model: {<usage fields>}}`` maps into one (for the
    combined orchestrator+subagent cost)."""
    merged = {}
    for m in maps:
        for model, slot in m.items():
            agg = merged.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
            for f in _USAGE_FIELDS:
                agg[f] += int(slot.get(f, 0))
    return merged


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _fmt(n: int) -> str:
    return f"{n:,}"


def _token_block(lines: list, inp: int, out: int, cr: int, cc: int,
                 total: int) -> None:
    """Render the four-field token breakdown + a total, in the established
    056-01 column layout."""
    lines.append(f"  input_tokens:           {_fmt(inp)}")
    lines.append(f"  output_tokens:          {_fmt(out)}")
    lines.append(f"  cache_read_tokens:      {_fmt(cr)}")
    lines.append(f"  cache_creation_tokens:  {_fmt(cc)}")
    lines.append("  ------------------------")
    lines.append(f"  total_tokens:           {_fmt(total)}")


def _cost_line(lines: list, cost, note, label="$ estimate (ccusage):") -> None:
    """Render a $ line — a figure (with optional note) or an 'unavailable'
    fallback — reusing 056-01's degradation wording."""
    if cost is not None:
        lines.append(f"  {label:<22}  ${cost:,.2f}")
        if note:
            lines.append(f"    note: {note}")
    else:
        reason = note or "ccusage not found"
        lines.append(f"  {'$ estimate:':<22}  unavailable ({reason})")


def render(rep: Report) -> str:
    lines = []
    lines.append(f"## Token usage — spec {rep.spec} "
                 f"(orchestrator + subagent)")
    lines.append("")
    if rep.session_count == 0:
        lines.append(
            f"No sessions attributed to spec {rep.spec} "
            f"(no spec-path mentions found in any transcript)."
        )
        lines.append("")
        lines.append("  Total tokens: 0")
        lines.append("  $ estimate:   n/a")
        lines.append("")
        _append_framing(lines, rep)
        return "\n".join(lines) + "\n"

    lines.append(f"  Sessions:               {rep.session_count}")
    lines.append(f"  Models:                 {', '.join(rep.models) or 'unknown'}")
    # Slice 056-03: surface attribution confidence — how many sessions were
    # mapped exactly (by the `.jig/spec-ref` marker) vs. heuristically (the
    # dominant content-mention guess). The lower-confidence caveat is shown
    # ONLY when heuristic sessions actually contributed.
    lines.append(
        f"  Attribution:            {rep.marker_session_count} by marker "
        f"(exact), {rep.heuristic_session_count} by heuristic"
    )
    if rep.heuristic_session_count:
        lines.append(
            f"    note: {rep.heuristic_session_count} session(s) had no "
            f".jig/spec-ref marker and fell back to the content heuristic "
            f"(lower confidence) — treat their share as approximate."
        )
    lines.append("")

    # --- Orchestrator (flat sessions, 056-01) -----------------------------
    lines.append("ORCHESTRATOR (flat sessions, measured)")
    _token_block(lines, rep.input_tokens, rep.output_tokens,
                 rep.cache_read_tokens, rep.cache_creation_tokens,
                 rep.total_tokens)
    _cost_line(lines, rep.cost_usd, rep.cost_note)
    lines.append("")

    # --- Subagent (nested transcripts, 056-02) ----------------------------
    lines.append("SUBAGENT (nested transcripts, measured)")
    _token_block(lines, rep.subagent_input_tokens, rep.subagent_output_tokens,
                 rep.subagent_cache_read_tokens,
                 rep.subagent_cache_creation_tokens,
                 rep.subagent_total_tokens)
    _cost_line(lines, rep.subagent_cost_usd, rep.subagent_cost_note)
    if rep.subagent_by_type:
        lines.append("  by subagent type:")
        for agent in sorted(rep.subagent_by_type):
            slot = rep.subagent_by_type[agent]
            sub_total = sum(int(slot.get(f, 0)) for f in _USAGE_FIELDS)
            lines.append(f"    {agent:<22} {_fmt(sub_total)} tokens")
    lines.append("")

    # --- Combined = the true per-spec cost --------------------------------
    lines.append("COMBINED (orchestrator + subagent = true per-spec cost)")
    lines.append(f"  total_tokens:           {_fmt(rep.combined_total_tokens)}")
    _cost_line(lines, rep.combined_cost_usd, rep.combined_cost_note)
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
        "Both the orchestrator (flat session files) and subagent (nested "
        "subagents/agent-*.jsonl transcripts) totals are MEASURED per-turn "
        "from message.usage — the combined figure is the true per-spec cost."
    )
    lines.append(
        "Attribution prefers the exact .jig/spec-ref marker (stamped by "
        "`workflow.py transition ... IN_PROGRESS`); sessions without a marker "
        "fall back to the content heuristic (dominant spec-path mention) and "
        "are flagged above as lower-confidence (slice 056-03)."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="usage.py",
        description="On-demand per-spec token + cost report "
                    "(orchestrator + subagent).",
    )
    sub = p.add_subparsers(dest="command")

    rep = sub.add_parser(
        "report",
        help="report orchestrator + subagent token usage + ccusage $ "
             "for a spec",
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
