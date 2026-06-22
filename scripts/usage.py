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
    python3 scripts/usage.py top [options]
    python3 scripts/usage.py compact-thresholds <spec> [<spec> ...] [options]
    python3 scripts/usage.py read-attribution [options]
    python3 scripts/usage.py semantic-index [options]

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
    --require-marker      Include only exact ``.jig/spec-ref`` attributions;
                          useful for future A/B comparisons.
    compact-thresholds    Read-only what-if: count historical orchestrator
                          turns crossing alternate ``cache_read`` thresholds
                          (default 0.60, 0.65, 0.75 of a 200k-token window).
    read-attribution      Summarize `.claude/context-growth-read-events.jsonl`
                          by spec/session for read events and by
                          hook/spec/session for `additionalContext`
                          injections.
    semantic-index        Summarize `.jig/semantic-index-events.jsonl`
                          activation telemetry alongside content-free
                          transcript/read fallback proxies.

Read-only: this tool never writes or deletes anything. The only network access
is the optional ``npx ccusage`` call (suppressed by --ccusage-json/--no-ccusage).
It never raises on a malformed or missing transcript — bad lines are skipped.
"""

import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
import sys
import time
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


READ_ATTRIBUTION_LOG = "context-growth-read-events.jsonl"
READ_ATTRIBUTION_BYTES_PER_TOKEN = 4
SEMANTIC_INDEX_TELEMETRY_LOG = Path(".jig") / "semantic-index-events.jsonl"


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

DEFAULT_TOKEN_WINDOW_TOKENS = 200_000


def _usage_token_values(usage: dict) -> dict:
    """Return normalized integer token values for the usage fields."""
    values = {}
    for f in _USAGE_FIELDS:
        raw = usage.get(f, 0)
        if isinstance(raw, bool):
            values[f] = 0
        elif isinstance(raw, (int, float)):
            values[f] = int(raw)
        else:
            values[f] = 0
    return values


def _usage_total(values: dict) -> int:
    return sum(int(values.get(f, 0)) for f in _USAGE_FIELDS)


def _iter_positive_usage(records: list):
    """Yield ``(record, message, token_values)`` for assistant usage turns
    with at least one positive token. Synthetic zero-token turns are ignored
    consistently by summing, turn counts, peaks, and threshold reports.
    """
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("type") not in (None, "assistant"):
            # Only assistant turns carry message.usage we count. User/system/
            # summary records have no billable usage.
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        token_values = _usage_token_values(usage)
        if _usage_total(token_values) <= 0:
            continue
        yield rec, msg, token_values


def sum_usage(records: list) -> dict:
    """Sum the four orchestrator usage fields across assistant records that
    carry a ``message.usage`` block. Also collects the set of models seen.

    Returns a dict with the four token fields, ``models`` (sorted list), and a
    ``per_model`` map. Records without ``usage`` are skipped.
    """
    totals = {f: 0 for f in _USAGE_FIELDS}
    per_model = {}
    models = set()
    for _rec, msg, token_values in _iter_positive_usage(records):
        model = msg.get("model") or "unknown"
        models.add(model)
        slot = per_model.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
        for f in _USAGE_FIELDS:
            val = token_values[f]
            totals[f] += val
            slot[f] += val
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
    for rec, msg, token_values in _iter_positive_usage(records):
        model = msg.get("model") or "unknown"
        agent = rec.get("attributionAgent") or "unknown"
        mslot = per_model.setdefault(model, {f: 0 for f in _USAGE_FIELDS})
        tslot = by_type.setdefault(agent, {f: 0 for f in _USAGE_FIELDS})
        for f in _USAGE_FIELDS:
            val = token_values[f]
            totals[f] += val
            mslot[f] += val
            tslot[f] += val
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
        model_tokens = sum(int(toks.get(f, 0)) for f in _USAGE_FIELDS)
        if model_tokens <= 0:
            continue
        rate = rates.get(model)
        if rate is None:
            unmatched.append(model)
            continue
        matched = True
        total += rate * model_tokens
    if not matched:
        if not unmatched:
            return 0.0, "no token usage"
        return None, (
            "ccusage has no rate for "
            + (", ".join(sorted(unmatched)) or "the attributed model(s)")
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
    orchestrator_turns: int = 0
    peak_cache_read_tokens: int = 0
    # Attribution-confidence split (slice 056-03): how many attributed
    # sessions came from the exact `.jig/spec-ref` marker vs. the content
    # heuristic. marker + heuristic == session_count.
    marker_session_count: int = 0
    heuristic_session_count: int = 0
    marker_required: bool = False
    skipped_heuristic_session_count: int = 0
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
    subagent_turns: int = 0
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


@dataclass
class TopRow:
    spec: str
    session_count: int = 0
    marker_session_count: int = 0
    heuristic_session_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    subagent_input_tokens: int = 0
    subagent_output_tokens: int = 0
    subagent_cache_read_tokens: int = 0
    subagent_cache_creation_tokens: int = 0
    orchestrator_turns: int = 0
    subagent_turns: int = 0
    peak_cache_read_tokens: int = 0
    models: set = field(default_factory=set)
    subagent_by_type: dict = field(default_factory=dict)

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

    @property
    def combined_cache_read_tokens(self) -> int:
        return self.cache_read_tokens + self.subagent_cache_read_tokens

    @property
    def combined_output_tokens(self) -> int:
        return self.output_tokens + self.subagent_output_tokens

    @property
    def combined_cache_creation_tokens(self) -> int:
        return (self.cache_creation_tokens
                + self.subagent_cache_creation_tokens)

    @property
    def combined_input_tokens(self) -> int:
        return self.input_tokens + self.subagent_input_tokens


@dataclass
class TopReport:
    rows: list
    session_count: int = 0
    attributed_session_count: int = 0
    unattributed_session_count: int = 0
    empty_session_count: int = 0
    marker_required: bool = False
    skipped_heuristic_session_count: int = 0

    @property
    def input_tokens(self) -> int:
        return sum(r.combined_input_tokens for r in self.rows)

    @property
    def output_tokens(self) -> int:
        return sum(r.combined_output_tokens for r in self.rows)

    @property
    def cache_read_tokens(self) -> int:
        return sum(r.combined_cache_read_tokens for r in self.rows)

    @property
    def cache_creation_tokens(self) -> int:
        return sum(r.combined_cache_creation_tokens for r in self.rows)

    @property
    def orchestrator_tokens(self) -> int:
        return sum(r.total_tokens for r in self.rows)

    @property
    def subagent_tokens(self) -> int:
        return sum(r.subagent_total_tokens for r in self.rows)

    @property
    def combined_total_tokens(self) -> int:
        return self.orchestrator_tokens + self.subagent_tokens


@dataclass
class CompactThresholdRow:
    threshold: float
    crossing_turns: int = 0
    sessions_crossed: int = 0
    first_crossing_turn: int = None


@dataclass
class CompactThresholdSpecReport:
    spec: str
    window_tokens: int
    thresholds: list
    session_count: int = 0
    marker_session_count: int = 0
    heuristic_session_count: int = 0
    marker_required: bool = False
    skipped_heuristic_session_count: int = 0
    orchestrator_turns: int = 0
    orchestrator_tokens: int = 0
    peak_cache_read_tokens: int = 0

    @property
    def peak_ratio(self) -> float:
        if self.window_tokens <= 0:
            return 0.0
        return self.peak_cache_read_tokens / self.window_tokens


@dataclass
class ReadPathSummary:
    file_path: str
    count: int = 0
    total_known_size_bytes: int = 0


@dataclass
class ReadAttributionRow:
    spec: str
    session_id: str
    counts: dict = field(default_factory=lambda: {"large": 0, "duplicate": 0})
    total_known_size_bytes: int = 0
    top_paths: list = field(default_factory=list)
    _path_stats: dict = field(default_factory=dict, repr=False)

    @property
    def event_count(self) -> int:
        return int(self.counts.get("large", 0)) + int(
            self.counts.get("duplicate", 0))

    @property
    def estimated_tokens(self) -> int:
        return self.total_known_size_bytes // READ_ATTRIBUTION_BYTES_PER_TOKEN


@dataclass
class HookInjectionAttributionRow:
    spec: str
    session_id: str
    source_hook: str
    kind_counts: dict = field(default_factory=dict)
    total_bytes: int = 0
    estimated_tokens: int = 0
    hook_event_names: list = field(default_factory=list)
    _hook_event_name_set: set = field(default_factory=set, repr=False)
    share: float = 0.0

    @property
    def event_count(self) -> int:
        return sum(int(v) for v in self.kind_counts.values())


@dataclass
class ReadAttributionReport:
    log_path: Path
    rows: list = field(default_factory=list)
    hook_injection_rows: list = field(default_factory=list)
    scanned_event_count: int = 0
    included_event_count: int = 0
    hook_injection_event_count: int = 0
    included_hook_injection_event_count: int = 0
    malformed_line_count: int = 0
    skipped_unattributed_event_count: int = 0
    total_context_growth_bytes: int = 0
    require_marker: bool = False


@dataclass
class SemanticIndexActivationRow:
    bucket: str
    provider: str
    provider_profile: str
    outcome: str
    repo_root_class: str
    host: str
    count: int = 0


@dataclass
class SemanticIndexDigest:
    telemetry_log: Path
    read_log: Path
    since_seconds: int = None
    window_tokens: int = DEFAULT_TOKEN_WINDOW_TOKENS
    activation_event_count: int = 0
    malformed_activation_line_count: int = 0
    filtered_activation_event_count: int = 0
    activation_rows: list = field(default_factory=list)
    session_count: int = 0
    usage_session_count: int = 0
    raw_read_tool_calls: int = 0
    broad_grep_tool_calls: int = 0
    broad_search_tool_calls: int = 0
    cache_read_bands: dict = field(default_factory=dict)
    read_large_events: int = 0
    read_duplicate_events: int = 0
    read_malformed_line_count: int = 0
    read_filtered_event_count: int = 0
    missing_transcript_count: int = 0


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
                 ccusage_runner=run_ccusage_npx,
                 require_marker: bool = False) -> Report:
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
    rep.marker_required = require_marker

    # Attribute sessions, keeping the session PATH so we can locate each
    # session's nested subagent transcripts (slice 056-02). Slice 056-03:
    # prefer the exact `.jig/spec-ref` marker; fall back to the content
    # heuristic — and record which, so the report can flag confidence.
    attributed = []
    marker_count = 0
    heuristic_count = 0
    skipped_heuristic = 0
    for session_path in find_sessions(projects_dir, encoded_prefix):
        records = read_session(session_path)
        if not records:
            continue
        spec_num, method = attribute_session(records)
        if spec_num == target:
            if require_marker and method != "marker":
                skipped_heuristic += 1
                continue
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
        turns, peak = _usage_turns_and_peak(records)
        rep.orchestrator_turns += turns
        rep.peak_cache_read_tokens = max(rep.peak_cache_read_tokens, peak)
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
            turns, _peak = _usage_turns_and_peak(agent_records)
            rep.subagent_turns += turns
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
    rep.skipped_heuristic_session_count = skipped_heuristic
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


def _usage_turns_and_peak(records: list) -> tuple:
    """Return ``(turn_count, peak_cache_read_tokens)`` for assistant records
    carrying positive ``message.usage``. Used by report/top/threshold rollups
    to expose spec 057's measured levers (turn count + peak context) without
    letting zero-token synthetic records inflate the counters.
    """
    turns = 0
    peak = 0
    for _rec, _msg, token_values in _iter_positive_usage(records):
        turns += 1
        peak = max(peak, token_values["cache_read_input_tokens"])
    return turns, peak


def build_top_report(projects_dir: Path, encoded_prefix: str,
                     require_marker: bool = False) -> TopReport:
    """Build a read-only all-spec rollup from the same transcript substrate as
    ``report``. The rows are sorted by combined orchestrator+subagent tokens,
    descending, with spec number as the deterministic tie-breaker.
    """
    rows = {}
    summary = TopReport(rows=[], marker_required=require_marker)

    for session_path in find_sessions(projects_dir, encoded_prefix):
        summary.session_count += 1
        records = read_session(session_path)
        if not records:
            summary.empty_session_count += 1
            continue
        spec_num, method = attribute_session(records)
        if spec_num is None:
            summary.unattributed_session_count += 1
            continue
        if require_marker and method != "marker":
            summary.skipped_heuristic_session_count += 1
            continue

        summary.attributed_session_count += 1
        row = rows.setdefault(spec_num, TopRow(spec=spec_num))
        row.session_count += 1
        if method == "marker":
            row.marker_session_count += 1
        else:
            row.heuristic_session_count += 1

        sums = sum_usage(records)
        row.input_tokens += sums["input_tokens"]
        row.output_tokens += sums["output_tokens"]
        row.cache_read_tokens += sums["cache_read_input_tokens"]
        row.cache_creation_tokens += sums["cache_creation_input_tokens"]
        row.models.update(sums["models"])
        turns, peak = _usage_turns_and_peak(records)
        row.orchestrator_turns += turns
        row.peak_cache_read_tokens = max(row.peak_cache_read_tokens, peak)

        for agent_path in find_subagent_files(session_path):
            agent_records = read_session(agent_path)
            if not agent_records:
                continue
            asums = sum_subagent_usage(agent_records)
            row.subagent_input_tokens += asums["input_tokens"]
            row.subagent_output_tokens += asums["output_tokens"]
            row.subagent_cache_read_tokens += asums["cache_read_input_tokens"]
            row.subagent_cache_creation_tokens += \
                asums["cache_creation_input_tokens"]
            turns, _peak = _usage_turns_and_peak(agent_records)
            row.subagent_turns += turns
            for agent, slot in asums["by_type"].items():
                prior = row.subagent_by_type.setdefault(
                    agent, {f: 0 for f in _USAGE_FIELDS})
                for f in _USAGE_FIELDS:
                    prior[f] += int(slot.get(f, 0))

    summary.rows = sorted(
        rows.values(),
        key=lambda r: (-r.combined_total_tokens, r.spec),
    )
    return summary


def build_compact_threshold_reports(specs: list, projects_dir: Path,
                                    encoded_prefix: str, thresholds: list,
                                    window_tokens: int =
                                    DEFAULT_TOKEN_WINDOW_TOKENS,
                                    require_marker: bool = False) -> list:
    """Build read-only what-if reports for alternate active-compaction bands.

    Each row answers: for this spec's attributed orchestrator turns, how many
    turns had ``cache_read_input_tokens`` at or above ``threshold * window``?
    This does not simulate post-/compact cache drops; it measures historical
    crossings from the transcript facts, which is enough to pick candidate
    thresholds for a controlled A/B run.
    """
    normalized = [_spec_number(s) for s in specs]
    reports = {
        spec: CompactThresholdSpecReport(
            spec=spec,
            window_tokens=window_tokens,
            thresholds=[CompactThresholdRow(t) for t in thresholds],
            marker_required=require_marker,
        )
        for spec in normalized
    }

    for session_path in find_sessions(projects_dir, encoded_prefix):
        records = read_session(session_path)
        if not records:
            continue
        spec_num, method = attribute_session(records)
        if spec_num not in reports:
            continue
        rep = reports[spec_num]
        if require_marker and method != "marker":
            rep.skipped_heuristic_session_count += 1
            continue

        rep.session_count += 1
        if method == "marker":
            rep.marker_session_count += 1
        else:
            rep.heuristic_session_count += 1

        sums = sum_usage(records)
        rep.orchestrator_tokens += sum(int(sums.get(f, 0))
                                       for f in _USAGE_FIELDS)

        turn_index = 0
        crossed_in_session = {row.threshold: False
                              for row in rep.thresholds}
        for _rec, _msg, token_values in _iter_positive_usage(records):
            turn_index += 1
            rep.orchestrator_turns += 1
            cache_read = token_values["cache_read_input_tokens"]
            rep.peak_cache_read_tokens = max(
                rep.peak_cache_read_tokens, cache_read)
            ratio = cache_read / window_tokens if window_tokens > 0 else 0
            for row in rep.thresholds:
                if ratio >= row.threshold:
                    row.crossing_turns += 1
                    crossed_in_session[row.threshold] = True
                    if (row.first_crossing_turn is None
                            or turn_index < row.first_crossing_turn):
                        row.first_crossing_turn = turn_index

        for row in rep.thresholds:
            if crossed_in_session[row.threshold]:
                row.sessions_crossed += 1

    return [reports[spec] for spec in normalized]


def _read_known_size(event: dict):
    size = event.get("size_bytes")
    if isinstance(size, bool):
        return None
    if isinstance(size, (int, float)) and size >= 0:
        return int(size)
    return None


def _nonnegative_int_or_none(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return int(value)
    return None


def _read_attribution_sort_key(row: ReadAttributionRow):
    # Attributed specs first, then the empty/unattributed bucket.
    spec_key = row.spec if row.spec else "zzz-unattributed"
    return (spec_key, row.session_id)


def _hook_injection_sort_key(row: HookInjectionAttributionRow):
    spec_key = row.spec if row.spec else "zzz-unattributed"
    return (spec_key, row.session_id, row.source_hook)


def build_read_attribution_report(log_path: Path,
                                  require_marker: bool = False
                                  ) -> ReadAttributionReport:
    """Build a read-only report from the context-growth attribution log.

    Hooks write metadata-only read-nudge and additionalContext events under
    `.claude/`. This parser is deliberately tolerant: malformed lines are
    counted and skipped, missing files simply produce an empty report, and
    unknown event shapes are ignored.
    """
    log_path = Path(log_path)
    report = ReadAttributionReport(
        log_path=log_path,
        require_marker=require_marker,
    )
    rows = {}
    hook_rows = {}

    try:
        fh = log_path.open("r", encoding="utf-8", errors="replace")
    except OSError:
        return report

    with fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                report.malformed_line_count += 1
                continue
            if not isinstance(event, dict):
                report.malformed_line_count += 1
                continue
            event_name = event.get("event")
            if event_name == "read_nudge":
                kind = event.get("kind")
                if kind not in ("large", "duplicate"):
                    continue

                report.scanned_event_count += 1
                spec = str(event.get("spec") or "")
                if require_marker and not spec:
                    report.skipped_unattributed_event_count += 1
                    continue

                session_id = str(event.get("session_id") or "unknown")
                row = rows.setdefault(
                    (spec, session_id),
                    ReadAttributionRow(spec=spec, session_id=session_id),
                )
                row.counts[kind] = int(row.counts.get(kind, 0)) + 1

                size = _read_known_size(event)
                if size is not None:
                    row.total_known_size_bytes += size
                    report.total_context_growth_bytes += size

                file_path = str(event.get("file_path") or "")
                if file_path:
                    path_summary = row._path_stats.setdefault(
                        file_path, ReadPathSummary(file_path=file_path))
                    path_summary.count += 1
                    if size is not None:
                        path_summary.total_known_size_bytes += size
                report.included_event_count += 1
                continue

            if event_name == "additional_context":
                report.hook_injection_event_count += 1
                spec = str(event.get("spec") or "")
                if require_marker and not spec:
                    report.skipped_unattributed_event_count += 1
                    continue

                session_id = str(event.get("session_id") or "unknown")
                source_hook = str(event.get("source_hook") or "unknown")
                row = hook_rows.setdefault(
                    (spec, session_id, source_hook),
                    HookInjectionAttributionRow(
                        spec=spec,
                        session_id=session_id,
                        source_hook=source_hook,
                    ),
                )
                kind = str(event.get("kind") or "unknown")
                row.kind_counts[kind] = int(row.kind_counts.get(kind, 0)) + 1
                hook_event_name = str(event.get("hook_event_name") or "")
                if (hook_event_name
                        and hook_event_name not in row._hook_event_name_set):
                    row._hook_event_name_set.add(hook_event_name)
                    row.hook_event_names.append(hook_event_name)

                byte_count = _nonnegative_int_or_none(event.get("bytes")) or 0
                row.total_bytes += byte_count
                report.total_context_growth_bytes += byte_count
                est = _nonnegative_int_or_none(event.get("estimated_tokens"))
                row.estimated_tokens += (
                    est if est is not None
                    else byte_count // READ_ATTRIBUTION_BYTES_PER_TOKEN
                )
                report.included_hook_injection_event_count += 1
                continue

    for row in rows.values():
        row.top_paths = sorted(
            row._path_stats.values(),
            key=lambda p: (-p.count, -p.total_known_size_bytes, p.file_path),
        )
    report.rows = sorted(rows.values(), key=_read_attribution_sort_key)
    if report.total_context_growth_bytes > 0:
        for row in hook_rows.values():
            row.share = row.total_bytes / report.total_context_growth_bytes
    report.hook_injection_rows = sorted(
        hook_rows.values(), key=_hook_injection_sort_key)
    return report


def _timestamp_seconds(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            pass
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    return None


def _in_window(timestamp, cutoff):
    if cutoff is None:
        return True
    # Rows without timestamps are retained. Older schemas and synthetic
    # fixtures should stay visible rather than disappearing silently.
    if timestamp is None:
        return True
    return timestamp >= cutoff


def _activation_bucket(event: dict) -> str:
    outcome = str(event.get("outcome") or "unknown")
    action = str(event.get("action") or "")
    if outcome in ("ready", "attach_started"):
        return "index-ready"
    if outcome == "not_opted_in" or action == "recommend":
        return "recommended-but-not-opted-in"
    if outcome == "provider_missing":
        return "provider-missing"
    if outcome == "overlay_disabled":
        return "overlay-disabled"
    return "activation-failed"


def _cache_read_band(peak_cache_read: int, window_tokens: int) -> str:
    if peak_cache_read <= 0:
        return "0"
    if window_tokens <= 0:
        return "unknown-window"
    ratio = peak_cache_read / window_tokens
    if ratio < 0.25:
        return "0-25%"
    if ratio < 0.50:
        return "25-50%"
    if ratio < 0.75:
        return "50-75%"
    return "75%+"


def _iter_tool_uses(records: list):
    for rec in records:
        if not isinstance(rec, dict):
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield str(block.get("name") or "")


def _session_timestamp(records: list):
    for rec in records:
        if isinstance(rec, dict):
            ts = _timestamp_seconds(rec.get("timestamp"))
            if ts is not None:
                return ts
    return None


def _read_proxy_counts(log_path: Path, cutoff):
    counts = {
        "large": 0,
        "duplicate": 0,
        "malformed": 0,
        "filtered": 0,
    }
    try:
        fh = Path(log_path).open("r", encoding="utf-8", errors="replace")
    except OSError:
        return counts
    with fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                counts["malformed"] += 1
                continue
            if not isinstance(event, dict):
                counts["malformed"] += 1
                continue
            if not _in_window(_timestamp_seconds(event.get("timestamp")), cutoff):
                counts["filtered"] += 1
                continue
            if event.get("event") != "read_nudge":
                continue
            kind = event.get("kind")
            if kind in ("large", "duplicate"):
                counts[kind] += 1
    return counts


def build_semantic_index_digest(
        telemetry_log: Path,
        projects_dir: Path,
        encoded_prefix: str,
        *,
        read_log: Path = None,
        since_seconds: int = None,
        window_tokens: int = DEFAULT_TOKEN_WINDOW_TOKENS,
        now=time.time) -> SemanticIndexDigest:
    """Build a metadata-only semantic-index activation digest.

    Activation telemetry has no session id by design, so this digest keeps the
    activation buckets and transcript/read proxies adjacent but aggregated over
    the same time window rather than pretending they join one-to-one.
    """
    telemetry_log = Path(telemetry_log)
    read_log = (
        Path(read_log) if read_log is not None
        else telemetry_log.parent / READ_ATTRIBUTION_LOG
    )
    cutoff = None
    if since_seconds is not None:
        cutoff = float(now()) - max(0, int(since_seconds))
    digest = SemanticIndexDigest(
        telemetry_log=telemetry_log,
        read_log=read_log,
        since_seconds=since_seconds,
        window_tokens=window_tokens,
    )

    activation_rows = {}
    try:
        fh = telemetry_log.open("r", encoding="utf-8", errors="replace")
    except OSError:
        fh = None
    if fh is not None:
        with fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except (ValueError, TypeError):
                    digest.malformed_activation_line_count += 1
                    continue
                if not isinstance(event, dict):
                    digest.malformed_activation_line_count += 1
                    continue
                if not _in_window(_timestamp_seconds(event.get("timestamp")), cutoff):
                    digest.filtered_activation_event_count += 1
                    continue
                bucket = _activation_bucket(event)
                key = (
                    bucket,
                    str(event.get("provider") or "unknown"),
                    str(event.get("provider_profile") or "unknown"),
                    str(event.get("outcome") or "unknown"),
                    str(event.get("repo_root_class") or "unknown"),
                    str(event.get("host") or "unknown"),
                )
                row = activation_rows.setdefault(
                    key,
                    SemanticIndexActivationRow(
                        bucket=key[0],
                        provider=key[1],
                        provider_profile=key[2],
                        outcome=key[3],
                        repo_root_class=key[4],
                        host=key[5],
                    ),
                )
                row.count += 1
                digest.activation_event_count += 1
    digest.activation_rows = sorted(
        activation_rows.values(),
        key=lambda r: (r.bucket, r.provider_profile, r.provider, r.outcome,
                       r.repo_root_class, r.host),
    )

    bands = {"0": 0, "0-25%": 0, "25-50%": 0, "50-75%": 0, "75%+": 0}
    for session_path in find_sessions(projects_dir, encoded_prefix):
        records = read_session(session_path)
        if not records:
            digest.missing_transcript_count += 1
            continue
        if not _in_window(_session_timestamp(records), cutoff):
            continue
        digest.session_count += 1
        turns, peak = _usage_turns_and_peak(records)
        if turns:
            digest.usage_session_count += 1
        band = _cache_read_band(peak, window_tokens)
        bands[band] = bands.get(band, 0) + 1
        for tool_name in _iter_tool_uses(records):
            lowered = tool_name.lower()
            if lowered == "read":
                digest.raw_read_tool_calls += 1
            elif lowered == "grep":
                digest.broad_grep_tool_calls += 1
            elif lowered == "search":
                digest.broad_search_tool_calls += 1
    digest.cache_read_bands = {k: v for k, v in bands.items() if v}

    read_counts = _read_proxy_counts(read_log, cutoff)
    digest.read_large_events = read_counts["large"]
    digest.read_duplicate_events = read_counts["duplicate"]
    digest.read_malformed_line_count = read_counts["malformed"]
    digest.read_filtered_event_count = read_counts["filtered"]
    return digest


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
        if rep.marker_required:
            lines.append(
                f"No marker-attributed sessions found for spec {rep.spec}."
            )
            if rep.skipped_heuristic_session_count:
                lines.append(
                    f"  Heuristic sessions skipped: "
                    f"{rep.skipped_heuristic_session_count}"
                )
        else:
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
    if rep.marker_required:
        lines.append("  Marker required:        yes")
        lines.append(
            f"  Heuristic skipped:      {rep.skipped_heuristic_session_count}"
        )
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
    lines.append(f"  turns:                  {_fmt(rep.orchestrator_turns)}")
    lines.append(
        f"  peak_cache_read_tokens: {_fmt(rep.peak_cache_read_tokens)}"
    )
    _token_block(lines, rep.input_tokens, rep.output_tokens,
                 rep.cache_read_tokens, rep.cache_creation_tokens,
                 rep.total_tokens)
    _cost_line(lines, rep.cost_usd, rep.cost_note)
    lines.append("")

    # --- Subagent (nested transcripts, 056-02) ----------------------------
    lines.append("SUBAGENT (nested transcripts, measured)")
    lines.append(f"  turns:                  {_fmt(rep.subagent_turns)}")
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


def _pct(part: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def render_top(rep: TopReport, limit: int = 10) -> str:
    lines = []
    lines.append("## Token usage top specs")
    lines.append("")
    lines.append(f"  Sessions scanned:       {_fmt(rep.session_count)}")
    lines.append(f"  Attributed sessions:    {_fmt(rep.attributed_session_count)}")
    lines.append(f"  Unattributed sessions:  {_fmt(rep.unattributed_session_count)}")
    lines.append(f"  Empty sessions:         {_fmt(rep.empty_session_count)}")
    if rep.marker_required:
        lines.append("  Marker required:        yes")
        lines.append(
            f"  Heuristic skipped:      "
            f"{_fmt(rep.skipped_heuristic_session_count)}"
        )
    lines.append(f"  Specs attributed:       {_fmt(len(rep.rows))}")
    lines.append("")

    lines.append("CATEGORY TOTALS (attributed sessions)")
    total = rep.combined_total_tokens
    lines.append(
        f"  input_tokens:           {_fmt(rep.input_tokens)} "
        f"({_pct(rep.input_tokens, total)})"
    )
    lines.append(
        f"  output_tokens:          {_fmt(rep.output_tokens)} "
        f"({_pct(rep.output_tokens, total)})"
    )
    lines.append(
        f"  cache_read_tokens:      {_fmt(rep.cache_read_tokens)} "
        f"({_pct(rep.cache_read_tokens, total)})"
    )
    lines.append(
        f"  cache_creation_tokens:  {_fmt(rep.cache_creation_tokens)} "
        f"({_pct(rep.cache_creation_tokens, total)})"
    )
    lines.append("  ------------------------")
    lines.append(f"  combined_total_tokens:  {_fmt(total)}")
    lines.append("")

    lines.append("DIMENSION TOTALS")
    lines.append(
        f"  orchestrator_tokens:    {_fmt(rep.orchestrator_tokens)} "
        f"({_pct(rep.orchestrator_tokens, total)})"
    )
    lines.append(
        f"  subagent_tokens:        {_fmt(rep.subagent_tokens)} "
        f"({_pct(rep.subagent_tokens, total)})"
    )
    lines.append("")

    rows = rep.rows[:max(0, limit)]
    lines.append(f"TOP SPECS (by combined tokens, limit {len(rows)})")
    if not rep.rows:
        lines.append("  No attributed specs with token usage.")
        return "\n".join(lines) + "\n"
    if not rows:
        lines.append("  No rows shown (limit 0).")
        return "\n".join(lines) + "\n"
    header = (
        "  spec  sessions  attribution  combined     orch         sub"
        "          cache_read   output       orch_turns  sub_turns  peak_cR"
    )
    lines.append(header)
    for row in rows:
        attr = f"{row.marker_session_count}m/{row.heuristic_session_count}h"
        lines.append(
            f"  {row.spec:<4}  {row.session_count:>8}  {attr:>11}  "
            f"{_fmt(row.combined_total_tokens):>11}  "
            f"{_fmt(row.total_tokens):>11}  "
            f"{_fmt(row.subagent_total_tokens):>11}  "
            f"{_fmt(row.combined_cache_read_tokens):>11}  "
            f"{_fmt(row.combined_output_tokens):>10}  "
            f"{_fmt(row.orchestrator_turns):>10}  "
            f"{_fmt(row.subagent_turns):>9}  "
            f"{_fmt(row.peak_cache_read_tokens):>7}"
        )
    lines.append("")
    lines.append(
        "Note: top is token-only; run `usage.py report <spec>` for ccusage "
        "$ estimates. Attribution is marker count / heuristic count."
    )
    return "\n".join(lines) + "\n"


def render_compact_thresholds(reports: list) -> str:
    lines = []
    lines.append("## Compaction threshold comparison")
    lines.append("")
    for idx, rep in enumerate(reports):
        if idx:
            lines.append("")
        lines.append(f"SPEC {rep.spec}")
        lines.append(f"  Sessions:               {_fmt(rep.session_count)}")
        if rep.marker_required:
            lines.append("  Marker required:        yes")
            lines.append(
                f"  Heuristic skipped:      "
                f"{_fmt(rep.skipped_heuristic_session_count)}"
            )
        lines.append(
            f"  Attribution:            {rep.marker_session_count} by marker "
            f"(exact), {rep.heuristic_session_count} by heuristic"
        )
        lines.append(f"  Window tokens:          {_fmt(rep.window_tokens)}")
        lines.append(f"  Orchestrator turns:     {_fmt(rep.orchestrator_turns)}")
        lines.append(f"  Orchestrator tokens:    {_fmt(rep.orchestrator_tokens)}")
        lines.append(
            f"  Peak cache_read:        "
            f"{_fmt(rep.peak_cache_read_tokens)} "
            f"({_pct(rep.peak_cache_read_tokens, rep.window_tokens)})"
        )
        if rep.session_count == 0:
            lines.append("  No attributed sessions to compare.")
            continue
        lines.append("")
        lines.append(
            "  threshold  turns_at_or_above  sessions_crossed  first_turn"
        )
        for row in rep.thresholds:
            first = (str(row.first_crossing_turn)
                     if row.first_crossing_turn is not None else "-")
            lines.append(
                f"  {row.threshold:>8.2f}  "
                f"{_fmt(row.crossing_turns):>17}  "
                f"{_fmt(row.sessions_crossed):>16}  "
                f"{first:>10}"
            )
    lines.append("")
    lines.append(
        "Note: this is a read-only what-if over historical orchestrator turns. "
        "It counts positive-token turns whose cache_read_input_tokens crossed "
        "threshold * window_tokens; it does not simulate cache drops after "
        "/compact."
    )
    return "\n".join(lines) + "\n"


def render_read_attribution(rep: ReadAttributionReport, limit: int = 50) -> str:
    lines = []
    lines.append("## Read attribution")
    lines.append("")
    lines.append(f"  Log:                    {rep.log_path}")
    lines.append(f"  Events scanned:         {_fmt(rep.scanned_event_count)}")
    lines.append(f"  Events included:        {_fmt(rep.included_event_count)}")
    lines.append(
        f"  Hook injections scanned: {_fmt(rep.hook_injection_event_count)}"
    )
    lines.append(
        f"  Hook injections incl.:  "
        f"{_fmt(rep.included_hook_injection_event_count)}"
    )
    lines.append(
        f"  Context-growth bytes:   "
        f"{_fmt(rep.total_context_growth_bytes)}"
    )
    if rep.require_marker:
        lines.append("  Marker required:        yes")
        lines.append(
            f"  Skipped unattributed:   "
            f"{_fmt(rep.skipped_unattributed_event_count)}"
        )
    if rep.malformed_line_count:
        lines.append(
            f"  Malformed lines:        {_fmt(rep.malformed_line_count)}"
        )
    lines.append("")

    rows = rep.rows[:max(0, limit)]
    lines.append(f"BY SPEC / SESSION (limit {len(rows)})")
    if not rep.rows:
        lines.append("  No read-attribution events found.")
    elif not rows:
        lines.append("  No rows shown (limit 0).")
    else:
        header = (
            "  spec            session  events  counts               known_bytes"
            "  est_tokens  top_paths"
        )
        lines.append(header)
        for row in rows:
            spec = row.spec or "(unattributed)"
            counts = (
                f"large={int(row.counts.get('large', 0))} "
                f"duplicate={int(row.counts.get('duplicate', 0))}"
            )
            top = ", ".join(
                f"{p.file_path} ({p.count})" for p in row.top_paths[:3]
            ) or "-"
            lines.append(
                f"  {spec:<15} {row.session_id:<8} "
                f"{_fmt(row.event_count):>6}  {counts:<20} "
                f"{_fmt(row.total_known_size_bytes):>11}  "
                f"{_fmt(row.estimated_tokens):>10}  {top}"
            )

    lines.append("")
    hook_rows = rep.hook_injection_rows[:max(0, limit)]
    lines.append(f"HOOK INJECTIONS BY HOOK / SPEC / SESSION (limit {len(hook_rows)})")
    if not rep.hook_injection_rows:
        lines.append("  No Hook injections found.")
    elif not hook_rows:
        lines.append("  No rows shown (limit 0).")
    else:
        header = (
            "  source_hook                spec            session  events"
            "  kinds                 bytes  est_tokens  share  hook_events"
        )
        lines.append(header)
        for row in hook_rows:
            spec = row.spec or "(unattributed)"
            kinds = " ".join(
                f"{kind}={int(count)}"
                for kind, count in sorted(row.kind_counts.items())
            ) or "-"
            hook_events = ",".join(row.hook_event_names) or "-"
            lines.append(
                f"  {row.source_hook:<26} {spec:<15} {row.session_id:<8} "
                f"{_fmt(row.event_count):>6}  {kinds:<20} "
                f"{_fmt(row.total_bytes):>7}  "
                f"{_fmt(row.estimated_tokens):>10}  "
                f"{row.share * 100:>5.1f}%  {hook_events}"
            )
    lines.append("")
    lines.append(
        f"Note: estimated tokens use "
        f"{READ_ATTRIBUTION_BYTES_PER_TOKEN} bytes/token. The log is "
        "metadata-only: file paths, sizes, thresholds, injected-context "
        "byte counts, and attribution fields."
    )
    return "\n".join(lines) + "\n"


def render_semantic_index_digest(rep: SemanticIndexDigest,
                                 limit: int = 50) -> str:
    lines = []
    lines.append("## Semantic-index activation digest")
    lines.append("")
    lines.append(f"  Telemetry log:          {rep.telemetry_log}")
    lines.append(f"  Read proxy log:         {rep.read_log}")
    window = (f"last {_fmt(rep.since_seconds)}s"
              if rep.since_seconds is not None else "all time")
    lines.append(f"  Window:                 {window}")
    lines.append(f"  Activation events:      {_fmt(rep.activation_event_count)}")
    if rep.filtered_activation_event_count:
        lines.append(
            f"  Activation filtered:    {_fmt(rep.filtered_activation_event_count)}"
        )
    if rep.malformed_activation_line_count:
        lines.append(
            f"  Malformed activation:   "
            f"{_fmt(rep.malformed_activation_line_count)}"
        )
    lines.append("")

    rows = rep.activation_rows[:max(0, limit)]
    lines.append(f"ACTIVATION BUCKETS (limit {len(rows)})")
    if not rep.activation_rows:
        lines.append("  No semantic-index activation telemetry found.")
    elif not rows:
        lines.append("  No rows shown (limit 0).")
    else:
        lines.append(
            "  bucket                          provider       profile"
            "           outcome                 repo_root  host     count"
        )
        for row in rows:
            lines.append(
                f"  {row.bucket:<31} {row.provider:<14} "
                f"{row.provider_profile:<17} {row.outcome:<22} "
                f"{row.repo_root_class:<10} {row.host:<8} "
                f"{_fmt(row.count):>5}"
            )
    lines.append("")

    lines.append("TRANSCRIPT PROXIES")
    lines.append(f"  Sessions scanned:       {_fmt(rep.session_count)}")
    lines.append(f"  Sessions with usage:    {_fmt(rep.usage_session_count)}")
    lines.append(f"  Raw Read tool calls:    {_fmt(rep.raw_read_tool_calls)}")
    lines.append(f"  Broad Grep calls:       {_fmt(rep.broad_grep_tool_calls)}")
    lines.append(f"  Broad Search calls:     {_fmt(rep.broad_search_tool_calls)}")
    if rep.missing_transcript_count:
        lines.append(
            f"  Empty/malformed files:   {_fmt(rep.missing_transcript_count)}"
        )
    if rep.cache_read_bands:
        lines.append("  Cache-read peak bands:")
        for band in ("0", "0-25%", "25-50%", "50-75%", "75%+",
                     "unknown-window"):
            if band in rep.cache_read_bands:
                lines.append(
                    f"    {band:<14} {_fmt(rep.cache_read_bands[band])}"
                )
    else:
        lines.append("  Cache-read peak bands:  none")
    lines.append("")

    lines.append("READ-GROWTH PROXIES")
    lines.append(f"  Large read nudges:      {_fmt(rep.read_large_events)}")
    lines.append(f"  Duplicate read nudges:  {_fmt(rep.read_duplicate_events)}")
    if rep.read_filtered_event_count:
        lines.append(
            f"  Read events filtered:   {_fmt(rep.read_filtered_event_count)}"
        )
    if rep.read_malformed_line_count:
        lines.append(
            f"  Malformed read lines:   {_fmt(rep.read_malformed_line_count)}"
        )
    lines.append("")
    lines.append(
        "Note: activation telemetry has no session id, so activation buckets "
        "and transcript/read proxies are compared as aggregate counts over "
        "the same window. Output is metadata-only: no queries, file bodies, "
        "diffs, provider command output, or read paths are printed."
    )
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
    rep.add_argument(
        "--require-marker", action="store_true",
        help="only include sessions attributed by exact .jig/spec-ref marker",
    )

    top = sub.add_parser(
        "top",
        help="rank attributed specs by combined orchestrator+subagent tokens",
    )
    top.add_argument(
        "--limit", type=int, default=10, metavar="N",
        help="number of specs to show (default: 10)",
    )
    top.add_argument(
        "--projects-dir", default=None, metavar="PATH",
        help="override the ~/.claude/projects root (testing seam)",
    )
    top.add_argument(
        "--main-root", default=None, metavar="PATH",
        help="override the repo main root used to derive the encoded prefix",
    )
    top.add_argument(
        "--require-marker", action="store_true",
        help="only include sessions attributed by exact .jig/spec-ref marker",
    )

    compact = sub.add_parser(
        "compact-thresholds",
        help="compare what-if active-compaction thresholds for one or more "
             "specs",
    )
    compact.add_argument(
        "specs", nargs="+",
        help="spec number(s) or slug(s), e.g. 055 057-token-budget",
    )
    compact.add_argument(
        "--thresholds", default="0.60,0.65,0.75",
        help="comma-separated threshold fractions (default: 0.60,0.65,0.75)",
    )
    compact.add_argument(
        "--window-tokens", type=int, default=DEFAULT_TOKEN_WINDOW_TOKENS,
        metavar="N",
        help=f"context window token budget (default: "
             f"{DEFAULT_TOKEN_WINDOW_TOKENS})",
    )
    compact.add_argument(
        "--projects-dir", default=None, metavar="PATH",
        help="override the ~/.claude/projects root (testing seam)",
    )
    compact.add_argument(
        "--main-root", default=None, metavar="PATH",
        help="override the repo main root used to derive the encoded prefix",
    )
    compact.add_argument(
        "--require-marker", action="store_true",
        help="only include sessions attributed by exact .jig/spec-ref marker",
    )

    read_attr = sub.add_parser(
        "read-attribution",
        help="summarize context-growth read-nudge and additionalContext "
             "telemetry",
    )
    read_attr.add_argument(
        "--log", default=None, metavar="PATH",
        help="override the read-attribution JSONL log path",
    )
    read_attr.add_argument(
        "--main-root", default=None, metavar="PATH",
        help="override the repo main root used to locate the default log",
    )
    read_attr.add_argument(
        "--require-marker", action="store_true",
        help="only include events attributed by exact .jig/spec-ref marker",
    )
    read_attr.add_argument(
        "--limit", type=int, default=50, metavar="N",
        help="number of spec/session rows to show (default: 50)",
    )

    semantic = sub.add_parser(
        "semantic-index",
        help="summarize semantic-index activation telemetry alongside "
             "read/search fallback proxies",
    )
    semantic.add_argument(
        "--telemetry-log", default=None, metavar="PATH",
        help="override the semantic-index telemetry JSONL path",
    )
    semantic.add_argument(
        "--read-log", default=None, metavar="PATH",
        help="override the read-attribution JSONL log path",
    )
    semantic.add_argument(
        "--projects-dir", default=None, metavar="PATH",
        help="override the ~/.claude/projects root (testing seam)",
    )
    semantic.add_argument(
        "--main-root", default=None, metavar="PATH",
        help="override the repo main root used to derive the encoded prefix",
    )
    semantic.add_argument(
        "--since-seconds", type=int, default=None, metavar="N",
        help="only count timestamped events from the last N seconds",
    )
    semantic.add_argument(
        "--window-tokens", type=int, default=DEFAULT_TOKEN_WINDOW_TOKENS,
        metavar="N",
        help=f"context window token budget for cache-read bands (default: "
             f"{DEFAULT_TOKEN_WINDOW_TOKENS})",
    )
    semantic.add_argument(
        "--limit", type=int, default=50, metavar="N",
        help="number of activation bucket rows to show (default: 50)",
    )
    return p


def _parse_thresholds(raw: str) -> list:
    thresholds = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            val = float(part)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid threshold {part!r}") from exc
        if not 0 < val <= 1:
            raise argparse.ArgumentTypeError(
                f"threshold must be in (0, 1], got {part!r}")
        thresholds.append(val)
    if not thresholds:
        raise argparse.ArgumentTypeError("at least one threshold is required")
    return sorted(set(thresholds))


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

    if ns.command not in ("report", "top", "compact-thresholds",
                          "read-attribution", "semantic-index"):
        parser.print_help(sys.stderr)
        return 2

    root = ns.main_root if ns.main_root else main_root()
    encoded_prefix = encode_cwd(root)

    if ns.command == "read-attribution":
        log_path = (Path(ns.log) if ns.log
                    else Path(root) / ".claude" / READ_ATTRIBUTION_LOG)
        rep = build_read_attribution_report(
            log_path,
            require_marker=ns.require_marker,
        )
        sys.stdout.write(render_read_attribution(rep, limit=ns.limit))
        return 0

    projects_dir = (Path(ns.projects_dir) if ns.projects_dir
                    else default_projects_dir())

    if ns.command == "semantic-index":
        if ns.window_tokens <= 0:
            sys.stderr.write("usage.py: error: --window-tokens must be > 0\n")
            return 2
        telemetry_log = (Path(ns.telemetry_log) if ns.telemetry_log
                         else Path(root) / SEMANTIC_INDEX_TELEMETRY_LOG)
        read_log = (Path(ns.read_log) if ns.read_log
                    else Path(root) / ".claude" / READ_ATTRIBUTION_LOG)
        digest = build_semantic_index_digest(
            telemetry_log,
            projects_dir,
            encoded_prefix,
            read_log=read_log,
            since_seconds=ns.since_seconds,
            window_tokens=ns.window_tokens,
        )
        sys.stdout.write(render_semantic_index_digest(
            digest, limit=ns.limit))
        return 0

    if ns.command == "top":
        top = build_top_report(projects_dir, encoded_prefix,
                               require_marker=ns.require_marker)
        sys.stdout.write(render_top(top, limit=ns.limit))
        return 0

    if ns.command == "compact-thresholds":
        if ns.window_tokens <= 0:
            sys.stderr.write("usage.py: error: --window-tokens must be > 0\n")
            return 2
        try:
            thresholds = _parse_thresholds(ns.thresholds)
        except argparse.ArgumentTypeError as exc:
            sys.stderr.write(f"usage.py: error: {exc}\n")
            return 2
        reports = build_compact_threshold_reports(
            specs=ns.specs,
            projects_dir=projects_dir,
            encoded_prefix=encoded_prefix,
            thresholds=thresholds,
            window_tokens=ns.window_tokens,
            require_marker=ns.require_marker,
        )
        sys.stdout.write(render_compact_thresholds(reports))
        return 0

    runner = _make_ccusage_runner(ns)

    rep = build_report(
        spec=ns.spec,
        projects_dir=projects_dir,
        encoded_prefix=encoded_prefix,
        ccusage_runner=runner,
        require_marker=ns.require_marker,
    )
    sys.stdout.write(render(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
