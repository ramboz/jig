"""
jig code-health helper — detect-and-drive static analysis.

Deterministic linter detection + subprocess-driven invocation, with
normalized exit codes so Claude can branch deterministically on the result.
The static-analysis sibling of `tdd.py`: detect the ecosystem → drive its
installed linter → normalize → print a tight summary → degrade to a
recommendation when no tool is available.

Two subcommands (mirroring tdd.py's `detect` / `run` shape):
  - `detect [target]`: print the resolved primary linter name (or exit 2).
  - `check [target]` : resolve + invoke the ecosystem's linter, parse the
                       result, exit 0 (clean) / 1 (findings) / 2 (no runner /
                       no recognized ecosystem / env error).

Ecosystem detection is **table-driven** (AC1): each ecosystem is described by
an `Ecosystem` descriptor (name, marker `detect`, primary-lint resolver,
advisory probe resolvers, and a stdout→(count, top_codes) summarizer).
Adding a third ecosystem is appending a descriptor to `ECOSYSTEMS` — no new
`if/elif` branch in the control flow.

Per ADR-0002 + tdd.py's own deviation note: the `_read_text_safe` /
`_read_json_safe` / `_pkg_deps` / `_custom_command_file` /
`_parse_custom_command` idioms here intentionally **duplicate** the
equivalents in `skills/tdd-loop/tdd.py` rather than extracting a shared
`_common` module. This is only the 2nd detect-and-drive helper of its kind
(tests + lint); the two have independent lifecycles (test runner vs. linter)
and diverge in detail (ephemeral-runner resolution is lint-specific).
ADR-0002's extract-trigger is the *third* caller — inline mirror until then,
exactly as tdd.py documents its duplication of scaffold.py.

Scope: Python (ruff, + advisory C901/PLR09xx complexity and pyright type
findings) and Node (eslint primary, + advisory prettier --check), plus a
cross-ecosystem advisory **duplication** dimension (native-first → ephemeral
`npx jscpd` fallback → `skipped (no detector)` line; reported, never
gating). The dedicated code-health reviewer pass (060-05) judges the summary.
"""

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

# How many distinct rule codes to surface in the tight summary (spec 057 —
# a count + the top codes, not the raw tool dump).
TOP_CODES = 5

# Recommendation printed when no Python linter is resolvable in a Python-only
# project (preserved verbatim from slice 060-01).
NO_LINTER_MSG = (
    "no Python linter found — install ruff or run via pipx "
    "(e.g. `pipx run ruff check .` / `uvx ruff check .`)"
)

# Recommendation printed when no Node linter is resolvable in a Node project.
NO_NODE_LINTER_MSG = (
    "no Node linter found — install eslint or run via npx "
    "(e.g. `npx eslint --format json .`)"
)

# Recommendation printed when no ecosystem markers match (and no override).
NO_ECOSYSTEM_MSG = (
    "no recognized ecosystem (Python/Node) found — "
    "set .jig/lint-command to run your linter"
)

# Python complexity rules surfaced by the advisory probe (AC3).
COMPLEXITY_RULES = ["C901", "PLR0911", "PLR0912", "PLR0913", "PLR0915"]

# How many top clones (file:line) to surface in the duplication summary
# (spec 057 — a percentage + a few clones, not the full jscpd dump).
TOP_CLONES = 3

# Filename jscpd writes its JSON report under when given `--output <dir>`.
JSCPD_REPORT_NAME = "jscpd-report.json"

# The advisory duplication skip line (AC3): emitted when neither a native
# duplication tool nor `npx jscpd` is available, so the dimension is honestly
# reported as unavailable rather than silently dropped.
DUPLICATION_SKIP_MSG = (
    "duplication: skipped (no detector) — install a duplication tool or "
    "Node (npx jscpd) to enable"
)

# The advisory pyright skip line (spec 077-01): emitted when a Python project
# can run its primary linter but no type checker is resolvable.
PYRIGHT_SKIP_MSG = (
    "pyright: skipped (no type-checker) — install pyright or run via "
    "pipx/uvx to enable"
)


# -------------------- shared file idioms (inline-mirror tdd.py) --------------------


def _read_text_safe(path: Path) -> str:
    """Read text, swallowing all errors and returning "". Same as tdd.py."""
    try:
        return path.read_text()
    except Exception:
        return ""


def _read_json_safe(path: Path) -> dict:
    """Read JSON, swallowing all errors and returning {}. Same as tdd.py."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _custom_command_file(target: Path):
    """Return <target>/.jig/lint-command if it exists, else None.

    Mirrors tdd.py's `_custom_command_file` (which reads `.jig/test-command`)
    — same semantics, lint-command path."""
    p = target / ".jig" / "lint-command"
    return p if p.is_file() else None


def _parse_custom_command(cmd_file) -> str:
    """Return the first non-blank, non-comment line from cmd_file, or None.

    Identical parsing semantics to tdd.py's `_parse_custom_command`."""
    for line in _read_text_safe(cmd_file).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


# -------------------- ecosystem marker detection --------------------


def _has_py_files_shallow(target: Path) -> bool:
    """Look for any `*.py` at root OR in any DIRECT subdir (shallow scan,
    max depth 2 — mirrors tdd.py's `_has_test_files_shallow` spirit)."""
    try:
        for entry in target.iterdir():
            if entry.is_file() and entry.name.endswith(".py"):
                return True
            if entry.is_dir():
                try:
                    for sub in entry.iterdir():
                        if sub.is_file() and sub.name.endswith(".py"):
                            return True
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError, FileNotFoundError):
        return False
    return False


def _detect_python(target: Path) -> bool:
    """Python marker: pyproject.toml present OR any *.py (shallow)."""
    if (target / "pyproject.toml").is_file():
        return True
    return _has_py_files_shallow(target)


def _detect_node(target: Path) -> bool:
    """Node marker: package.json present (the same file tdd.py keys off via
    `_pkg_deps`; here we only need its presence, not its parsed contents)."""
    return (target / "package.json").is_file()


# -------------------- primary-lint resolvers (PATH → ephemeral) --------------------


def _ruff_launcher(args: list) -> Optional[list]:
    """Prefix `args` (a ruff sub-invocation, e.g. `["check", ...]`) with the
    first available ruff launcher: PATH `ruff` → `uvx ruff` → `pipx run ruff`,
    else None. Shared by the primary-lint resolver and the complexity probe so
    the launcher chain lives in one place."""
    if shutil.which("ruff"):
        return ["ruff", *args]
    if shutil.which("uvx"):
        return ["uvx", "ruff", *args]
    if shutil.which("pipx"):
        return ["pipx", "run", "ruff", *args]
    return None


def _resolve_ruff(target: Path) -> Optional[list]:
    """Resolve ruff's primary-lint argv: PATH → uvx → pipx, else None."""
    return _ruff_launcher(["check", "--output-format=json", str(target)])


def _resolve_eslint(target: Path) -> Optional[list]:
    """Resolve eslint's primary-lint argv: PATH → npx (ephemeral), else None."""
    args = ["--format", "json", str(target)]
    if shutil.which("eslint"):
        return ["eslint", *args]
    if shutil.which("npx"):
        return ["npx", "eslint", *args]
    return None


# -------------------- advisory probe resolvers --------------------


def _resolve_ruff_complexity(target: Path, workdir: Optional[Path] = None) -> Optional[list]:
    """Resolve the ruff complexity probe argv (same launcher chain as ruff).
    `workdir` is part of the uniform probe-resolver signature; ruff writes to
    stdout, so it is unused here."""
    return _ruff_launcher([
        "check",
        "--select",
        ",".join(COMPLEXITY_RULES),
        "--output-format=json",
        str(target),
    ])


def _resolve_prettier(target: Path, workdir: Optional[Path] = None) -> Optional[list]:
    """Resolve the prettier --check probe argv: PATH → npx (ephemeral).
    `workdir` is part of the uniform probe-resolver signature; prettier writes
    to stdout, so it is unused here."""
    args = ["--check", str(target)]
    if shutil.which("prettier"):
        return ["prettier", *args]
    if shutil.which("npx"):
        return ["npx", "prettier", *args]
    return None


def _resolve_pyright(target: Path, workdir: Optional[Path] = None) -> Optional[list]:
    """Resolve pyright's advisory type-check argv: PATH → uvx → pipx.
    `workdir` is part of the uniform probe-resolver signature; pyright writes
    JSON to stdout, so it is unused here."""
    args = ["--outputjson", str(target)]
    if shutil.which("pyright"):
        return ["pyright", *args]
    if shutil.which("uvx"):
        return ["uvx", "pyright", *args]
    if shutil.which("pipx"):
        return ["pipx", "run", "pyright", *args]
    return None


def _resolve_duplication(target: Path, workdir: Optional[Path]) -> Optional[list]:
    """Resolve the cross-ecosystem duplication probe argv (AC1/AC2).

    Order:
      1. (native, per-ecosystem) — the extension point for a future native
         duplication tool. **No ecosystem in jig's tool set currently ships a
         distinct native duplication detector** (ruff has none; jscpd is the
         language-agnostic tool), so this branch is intentionally empty — a
         future native tool is a one-line addition here, mirroring the
         table-driven extensibility of 060-03. We deliberately do NOT shoehorn
         in a flaky native tool (e.g. pylint's duplicate-code) just to populate
         it (see the deviation log).
      2. `npx jscpd` (ephemeral, when `npx` is on PATH) — the Node analogue of
         `pipx run`, works on ANY language. The real detector in practice.
      3. else None → the AdvisoryProbe.skip_summary line (AC3).

    jscpd writes its JSON report to a file (not stdout); we point `--output` at
    `workdir` — a temp dir OUTSIDE the project that the advisory-probe runner
    creates and tears down (so cleanup is guaranteed on every exit path,
    including a subprocess failure). The summarizer reads the report back from
    the same `workdir`. `--silent` keeps progress chatter off the console; no
    `--threshold` so jscpd never exits non-zero (duplication is advisory — it
    must not gate)."""
    # 1. native, per-ecosystem — intentionally empty (extension point).

    # 2. npx jscpd (ephemeral, language-agnostic). `workdir` is always provided
    #    for this probe (needs_workdir=True), but guard defensively.
    if workdir is not None and shutil.which("npx"):
        return [
            "npx", "jscpd",
            "--reporters", "json",
            "--output", str(workdir),
            "--silent",
            str(target),
        ]

    # 3. nothing resolvable.
    return None


# -------------------- per-ecosystem summarizers --------------------


def _summarize_ruff(stdout: str) -> Tuple[Optional[int], list]:
    """Parse ruff's JSON (a flat list of finding dicts) into (count, top_codes).
    Robust to non-JSON — returns (None, []) then, so callers fall back to a
    generic line rather than crashing."""
    try:
        findings = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None, []
    if not isinstance(findings, list):
        return None, []
    codes = Counter(
        f.get("code") for f in findings
        if isinstance(f, dict) and f.get("code")
    )
    top = [code for code, _ in codes.most_common(TOP_CODES)]
    return len(findings), top


def _summarize_eslint(stdout: str) -> Tuple[Optional[int], list]:
    """Parse eslint's JSON (array of {filePath, messages:[{ruleId,...}], ...})
    into (count, top_rule_ids). count = total messages across files. Robust
    to non-JSON — returns (None, [])."""
    try:
        files = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None, []
    if not isinstance(files, list):
        return None, []
    total = 0
    codes = Counter()
    for f in files:
        if not isinstance(f, dict):
            continue
        msgs = f.get("messages") or []
        if not isinstance(msgs, list):
            continue
        for m in msgs:
            if not isinstance(m, dict):
                continue
            total += 1
            rid = m.get("ruleId")
            if rid:
                codes[rid] += 1
    top = [code for code, _ in codes.most_common(TOP_CODES)]
    return total, top


# -------------------- advisory probe descriptors --------------------


@dataclass
class AdvisoryProbe:
    """An advisory dimension (complexity / formatting / duplication). Reported
    in the summary; NEVER changes the exit code (AC3). Best-effort: a failure
    to start or unparseable output is swallowed and reported as nothing.

    `skip_summary` (060-04): when set, a probe whose `resolve()` returns None
    (no tool available) emits this line instead of staying silent — so the
    duplication probe can report `skipped (no detector)`. Probes WITHOUT a
    `skip_summary` (complexity / prettier) keep the 060-03 behavior of staying
    silent when their tool is unavailable.

    `needs_workdir` (060-04): when True, the runner creates a fresh temp dir
    (via `TemporaryDirectory`, so cleanup is guaranteed on EVERY exit path,
    including a subprocess failure) and threads it as `workdir` into both
    `resolve` and `summarize`. Probes that write a report file (jscpd) use it;
    stdout-only probes (complexity / prettier) leave it False and ignore the
    `workdir` argument."""

    name: str
    # resolve(target, workdir) -> argv, or None when no tool is available.
    resolve: Callable[[Path, Optional[Path]], Optional[list]]
    # summarize(returncode, stdout, stderr, workdir) -> a summary line, or None
    # to report nothing for this probe.
    summarize: Callable[[int, str, str, Optional[Path]], Optional[str]]
    # When the resolver returns None, emit this line (else stay silent).
    skip_summary: Optional[str] = None
    # When True, the runner owns a temp dir threaded in as `workdir`.
    needs_workdir: bool = False


def _summarize_complexity_probe(returncode: int, stdout: str, stderr: str,
                                workdir: Optional[Path] = None) -> Optional[str]:
    """Surface a per-function complexity signal from the ruff complexity probe.
    Best-effort — unparseable output → None (report nothing). `workdir` is part
    of the uniform probe-summarizer signature; unused (ruff reports on stdout)."""
    count, top = _summarize_ruff(stdout)
    if count is None or count == 0:
        return None
    codes = ", ".join(top) if top else "(no rule codes)"
    return f"complexity: {count} function(s) over threshold; top: {codes}"


def _summarize_prettier_probe(returncode: int, stdout: str, stderr: str,
                              workdir: Optional[Path] = None) -> Optional[str]:
    """Surface a formatting signal from `prettier --check`. prettier exits
    non-zero and lists the files that would be reformatted on stdout; exit 0
    means everything is formatted. Best-effort. `workdir` is part of the
    uniform probe-summarizer signature; unused (prettier reports on stdout)."""
    if returncode == 0:
        return None
    # prettier prints one path per line (plus a header/footer). Count the
    # non-blank lines that look like file paths — but be forgiving: any
    # non-zero exit with output means "some file(s) need formatting".
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    # Drop prettier's own banner lines (they start with "Checking" / "[warn]"
    # / "All matched files"); count the rest as candidate files.
    candidates = [
        ln for ln in lines
        if not ln.strip().lower().startswith(("checking", "all matched", "[warn]", "[error]"))
    ]
    n = len(candidates) if candidates else len(lines)
    if n == 0:
        return "prettier: some file(s) need formatting"
    return f"prettier: {n} file(s) need formatting"


def _summarize_pyright_probe(returncode: int, stdout: str, stderr: str,
                             workdir: Optional[Path] = None) -> Optional[str]:
    """Surface pyright diagnostics as a tight advisory line. Pyright exits
    non-zero for type findings, but this probe never changes health.py's exit
    code; it only contributes a count + representative diagnostic rules."""
    try:
        report = json.loads(stdout)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(report, dict):
        return None

    diagnostics = report.get("generalDiagnostics")
    if not isinstance(diagnostics, list):
        diagnostics = []

    summary = report.get("summary")
    count = len(diagnostics)
    if count == 0 and isinstance(summary, dict):
        counts = [
            summary.get("errorCount", 0),
            summary.get("warningCount", 0),
            summary.get("informationCount", 0),
        ]
        try:
            count = sum(int(c or 0) for c in counts)
        except (TypeError, ValueError):
            count = 0

    if count <= 0:
        return None

    rules = Counter()
    for diag in diagnostics:
        if not isinstance(diag, dict):
            continue
        rule = diag.get("rule")
        if rule:
            rules[rule] += 1
            continue
        severity = diag.get("severity")
        if severity:
            rules[severity] += 1

    top = [rule for rule, _ in rules.most_common(TOP_CODES)]
    if top:
        return f"pyright: {count} type diagnostic(s); top: {', '.join(top)}"
    return f"pyright: {count} type diagnostic(s)"


def _summarize_jscpd_report(report_text: str) -> Optional[str]:
    """Parse a jscpd JSON report into a tight duplication summary line (AC4):
    a percentage + the top clones as `file:line`. Returns None on missing /
    unparseable / shapeless input so the probe reports nothing useful rather
    than crashing or emitting junk (best-effort).

    Real jscpd report shape (verified against `npx jscpd --reporters json`):
      {"statistics": {"total": {"percentage": <num>, "clones": <int>, ...}},
       "duplicates": [{"firstFile": {"name": "...", "startLoc": {"line": N}},
                       "secondFile": {...}}, ...]}
    """
    try:
        report = json.loads(report_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(report, dict):
        return None
    total = (report.get("statistics") or {}).get("total")
    if not isinstance(total, dict) or "percentage" not in total:
        return None
    pct = total.get("percentage")
    try:
        pct_str = f"{float(pct):.1f}%"
    except (TypeError, ValueError):
        return None
    clones = total.get("clones", 0)

    # Top clones as file:line (the firstFile of each duplicate).
    tops: List[str] = []
    dups = report.get("duplicates")
    if isinstance(dups, list):
        for dup in dups[:TOP_CLONES]:
            if not isinstance(dup, dict):
                continue
            ff = dup.get("firstFile")
            if not isinstance(ff, dict):
                continue
            name = ff.get("name")
            line = (ff.get("startLoc") or {}).get("line")
            if name and line is not None:
                tops.append(f"{name}:{line}")
            elif name:
                tops.append(str(name))

    head = f"duplication: {pct_str} ({clones} clones)"
    if tops:
        return f"{head}; top: {', '.join(tops)}"
    return head


def _summarize_duplication_probe(returncode: int, stdout: str, stderr: str,
                                 workdir: Optional[Path] = None) -> Optional[str]:
    """AdvisoryProbe summarize for duplication. jscpd writes its report to a
    file (not stdout), so we read it back from `workdir` — the temp dir the
    advisory-probe runner created for this probe and will tear down itself
    (guaranteeing cleanup on every exit path). Best-effort — any failure →
    None (report nothing)."""
    if workdir is None:
        return None
    return _summarize_jscpd_report(_read_text_safe(workdir / JSCPD_REPORT_NAME))


# -------------------- ecosystem descriptors (the AC1 table) --------------------


@dataclass
class Ecosystem:
    """A code-health ecosystem descriptor. Adding a language = appending one
    of these to ECOSYSTEMS — no control-flow fork (AC1)."""

    name: str
    detect: Callable[[Path], bool]
    resolve_primary: Callable[[Path], Optional[list]]
    summarize_primary: Callable[[str], Tuple[Optional[int], list]]
    no_linter_msg: str
    advisory_probes: List[AdvisoryProbe] = field(default_factory=list)


# The duplication probe (060-04) is cross-ecosystem and language-agnostic
# (native-first → `npx jscpd` fallback → skip line), so a SINGLE shared
# instance is referenced by BOTH ecosystems' advisory_probes lists. Unlike
# complexity/prettier it carries a `skip_summary`, so it reports
# `skipped (no detector)` when nothing resolves rather than staying silent.
DUPLICATION_PROBE = AdvisoryProbe(
    name="duplication",
    resolve=_resolve_duplication,
    summarize=_summarize_duplication_probe,
    skip_summary=DUPLICATION_SKIP_MSG,
    needs_workdir=True,
)


ECOSYSTEMS: List[Ecosystem] = [
    Ecosystem(
        name="python",
        detect=_detect_python,
        resolve_primary=_resolve_ruff,
        summarize_primary=_summarize_ruff,
        no_linter_msg=NO_LINTER_MSG,
        advisory_probes=[
            AdvisoryProbe(
                name="complexity",
                resolve=_resolve_ruff_complexity,
                summarize=_summarize_complexity_probe,
            ),
            AdvisoryProbe(
                name="pyright",
                resolve=_resolve_pyright,
                summarize=_summarize_pyright_probe,
                skip_summary=PYRIGHT_SKIP_MSG,
            ),
            DUPLICATION_PROBE,
        ],
    ),
    Ecosystem(
        name="node",
        detect=_detect_node,
        resolve_primary=_resolve_eslint,
        summarize_primary=_summarize_eslint,
        no_linter_msg=NO_NODE_LINTER_MSG,
        advisory_probes=[
            AdvisoryProbe(
                name="prettier",
                resolve=_resolve_prettier,
                summarize=_summarize_prettier_probe,
            ),
            DUPLICATION_PROBE,
        ],
    ),
]


def _detect_ecosystems(target: Path) -> List[Ecosystem]:
    """Return every ecosystem whose marker fires on target (table iteration —
    no if/elif fork)."""
    return [eco for eco in ECOSYSTEMS if eco.detect(target)]


# -------------------- resolution (override > table) --------------------


def _override_argv(target: Path):
    """Return the `.jig/lint-command` override argv, or None.

    The override is honored verbatim and **bypasses ecosystem detection
    entirely** (preserves 060-01 semantics). An empty / comment-only file
    falls through (returns None)."""
    cmd_file = _custom_command_file(target)
    if cmd_file is None:
        return None
    cmd_str = _parse_custom_command(cmd_file)
    if cmd_str is None:
        return None
    return shlex.split(cmd_str)


def resolve_lint_command(target: Path):
    """Resolve the primary-lint argv to run, or None if nothing is available.

    Resolution order:
      1. `.jig/lint-command` override (verbatim; bypasses detection — AC2-override).
      2. The single matching ecosystem's primary-lint resolver.

    Returns None when: the override is empty AND (0, 2+, or 1-but-unresolvable)
    ecosystems match. The richer degradation messaging lives in cmd_check;
    this helper preserves the 060-01 "argv or None" contract for callers/tests.
    """
    override = _override_argv(target)
    if override is not None:
        return override

    matches = _detect_ecosystems(target)
    if len(matches) != 1:
        return None
    return matches[0].resolve_primary(target)


def _resolved_name(argv: list) -> str:
    """Human-readable name of a resolved command (for `detect` + summaries)."""
    if not argv:
        return "?"
    if argv[0] == "uvx":
        return " ".join(argv[:2])
    if argv[0] == "pipx":
        return " ".join(argv[:3])
    if argv[0] == "npx":
        return " ".join(argv[:2])
    return argv[0]


# -------------------- advisory probe runner --------------------


def _run_one_probe(probe: AdvisoryProbe, target: Path,
                   workdir: Optional[Path]) -> Optional[str]:
    """Run a single advisory probe best-effort; return its summary line, its
    skip line, or None. NEVER raises — any failure (FileNotFoundError, OSError,
    parse errors, anything) is swallowed and contributes nothing (AC3)."""
    try:
        argv = probe.resolve(target, workdir)
        if argv is None:
            # No tool resolved. A probe with a skip_summary (duplication)
            # reports it; one without (complexity / prettier) stays silent.
            return probe.skip_summary
        result = subprocess.run(
            argv, cwd=str(target), capture_output=True, text=True
        )
        return probe.summarize(
            result.returncode, result.stdout, result.stderr, workdir
        )
    except Exception:
        return None


def _run_advisory_probes(probes: List[AdvisoryProbe], target: Path) -> List[str]:
    """Run each advisory probe best-effort; collect the non-empty summary
    lines. NEVER raises (AC3: advisory, reported-not-gating, never crash).

    For a probe with `needs_workdir`, the runner OWNS a fresh `TemporaryDirectory`
    threaded in as `workdir` — so the temp dir is torn down on EVERY exit path,
    including a subprocess failure (the leak the 060-04 craft review caught: a
    summarizer-owned `finally` is skipped when the subprocess raises)."""
    lines: List[str] = []
    for probe in probes:
        if probe.needs_workdir:
            with tempfile.TemporaryDirectory(prefix="jig-jscpd-") as wd:
                line = _run_one_probe(probe, target, Path(wd))
        else:
            line = _run_one_probe(probe, target, None)
        if line:
            lines.append(line)
    return lines


# -------------------- subcommands --------------------


def _degradation_message(target: Path) -> str:
    """Pick the right one-line recommendation for a no-runnable-linter case
    (AC4): unknown (0 matches) / mixed (2+ matches) / single-but-unresolvable."""
    matches = _detect_ecosystems(target)
    if len(matches) == 0:
        return NO_ECOSYSTEM_MSG
    if len(matches) >= 2:
        names = "/".join(eco.name for eco in matches)
        return (
            f"multiple ecosystems detected ({names}) — "
            "set .jig/lint-command to disambiguate which linter to run"
        )
    # Exactly one matched but its primary linter did not resolve.
    return matches[0].no_linter_msg


def cmd_detect(target: Path) -> int:
    """`detect` subcommand. Prints the resolved primary linter name; exit 2
    on miss (with an ecosystem-appropriate recommendation)."""
    argv = resolve_lint_command(target)
    if argv is None:
        sys.stderr.write(_degradation_message(target) + "\n")
        return 2
    sys.stdout.write(_resolved_name(argv) + "\n")
    return 0


def _summarize_for(target: Path, argv: list) -> Callable[[str], Tuple[Optional[int], list]]:
    """Pick the primary summarizer for a resolved argv. The override path has
    no ecosystem, so default to the ruff summarizer (back-compat with 060-01,
    where an override that emitted ruff JSON was summarized; non-JSON falls to
    the generic line either way)."""
    override = _override_argv(target)
    if override is not None and argv == override:
        return _summarize_ruff
    matches = _detect_ecosystems(target)
    if len(matches) == 1:
        return matches[0].summarize_primary
    return _summarize_ruff


def _advisory_probes_for(target: Path, argv: list) -> List[AdvisoryProbe]:
    """The advisory probes to run alongside the resolved primary. The override
    path runs no advisory probes (we don't know the ecosystem)."""
    override = _override_argv(target)
    if override is not None and argv == override:
        return []
    matches = _detect_ecosystems(target)
    if len(matches) == 1:
        return matches[0].advisory_probes
    return []


def cmd_check(target: Path) -> int:
    """`check` subcommand. Resolve + invoke the primary linter, parse the
    result, normalize the exit code (0 clean / 1 findings / 2 no-runner /
    no-recognized-ecosystem / env error), and append advisory probe lines
    (complexity / prettier) to the summary WITHOUT changing the exit code.

    The primary tool's native exit code is 0 (clean) / 1 (has findings); we
    map it through, but a FileNotFoundError / OSError when launching the
    process means the binary/module is genuinely unavailable → 2 (the exact
    lesson tdd.py encodes: distinguish "tool absent" from "tool ran and found
    issues")."""
    argv = resolve_lint_command(target)
    if argv is None:
        # AC4 — graceful degradation: one-line recommendation, no trace.
        sys.stderr.write(_degradation_message(target) + "\n")
        return 2

    name = _resolved_name(argv)
    summarize = _summarize_for(target, argv)
    probes = _advisory_probes_for(target, argv)

    try:
        result = subprocess.run(argv, cwd=str(target),
                                capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        sys.stderr.write(
            f"{argv[0]}: linter failed to start (is it installed?)\n"
        )
        return 2

    count, top = summarize(result.stdout)

    # Advisory probes run regardless of the primary outcome; they only ever
    # add summary lines (AC3 — reported, not gating).
    advisory_lines = _run_advisory_probes(probes, target)

    def _emit_advisory():
        for line in advisory_lines:
            sys.stdout.write(line + "\n")

    if result.returncode == 0:
        sys.stdout.write(f"{name}: clean — no findings\n")
        _emit_advisory()
        return 0

    # Non-zero: findings (the common case) — print a tight summary.
    if count is None:
        # Tool emitted non-JSON; we can't count, so report generically.
        sys.stdout.write(f"{name}: findings reported (non-zero exit)\n")
    elif count == 0:
        # Non-zero exit but no parseable findings — surface the stderr tail.
        tail = (result.stderr or "").strip().splitlines()
        hint = tail[-1] if tail else f"{name} exited non-zero with no findings"
        sys.stdout.write(f"{name}: {hint}\n")
    else:
        codes = ", ".join(top) if top else "(no rule codes)"
        sys.stdout.write(
            f"{name}: {count} finding(s); top rules: {codes}\n"
        )
    _emit_advisory()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="health.py",
        description="jig code-health helper (detect / check)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("detect",
                        help="print the resolved linter name")
    pd.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")

    pc = sub.add_parser("check",
                        help="run the resolved linter against target")
    pc.add_argument("target", nargs="?", default=".",
                    help="target directory (default: .)")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    target = Path(ns.target).resolve()
    if not target.is_dir():
        sys.stderr.write(f"target is not a directory: {target}\n")
        return 2

    try:
        if ns.cmd == "detect":
            return cmd_detect(target)
        if ns.cmd == "check":
            return cmd_check(target)
    except Exception as exc:  # noqa: BLE001 — surface programming errors clearly.
        sys.stderr.write(f"health.py failed: {exc}\n")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
