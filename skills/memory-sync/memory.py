"""
jig memory-sync — slice 002-01 (explicit-sync)

Deterministic helper for persisting context to the memory layer. Claude makes
the decisions (what to persist where); this script does the file I/O,
idempotency, and self-healing of missing memory structure.

Usage:
    python3 memory.py <command> [args] <target-dir>

Commands:
    add-term <name> <definition>           → docs/memory/glossary.md
    add-learning <title> [--body=<text>]   → docs/memory/learnings.md
        (body from --body, or stdin if --body omitted)
    add-inbox <text>                       → docs/inbox.md (dated)
    add-refinement-todo <text>             → docs/refinement-todo.md (raw append)
    promote <term> <definition>            → CLAUDE.md Hot Cache → Key terms
    summary                                → counts of memory files
"""

import argparse
import contextlib
import fcntl
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _common import team_signal
from _common.atomic_io import atomic_write_text

# Heading marker used to find the Key terms list inside CLAUDE.md Hot Cache.
HOT_CACHE_KEY_TERMS_HEADING = "### Key terms"

# Placeholder line inserted by scaffold-init under Key terms; replaced on first promote.
HOT_CACHE_PLACEHOLDER = re.compile(
    r"^- \(populated as the project grows.*?\)\s*$", re.MULTILINE
)


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


# ---------- Slice 050-01/050-02: team-recheck (shared `_common` signal) ----------
# AC1 — re-check uses the EXACT detection the rest of jig uses; no
# re-implementation. The team-signal logic (contributor count, threshold,
# the `.jig/no-people-md` marker contract, `people_md_path`) lives in
# `_common.team_signal`, its single home since slice 050-02 tripped
# ADR-0002's rule-of-three (scaffold-init / memory-sync / workflow.py stale).
# memory.py imports it directly — the hyphenated-dir importlib loader the
# 050-01 reconciliation added is retired by the cleaner `_common` import.


def _bootstrap_people_md(target: Path) -> tuple:
    """Write `docs/memory/people.md` from the REAL scaffold-init template
    (AC5 — no embedded duplicate). Returns `(written: bool, message: str)`.

    Locates the template the same way scaffold-init does — under
    `plugin_root()/templates/` — and renders its `{{PROJECT_NAME}}`
    placeholder before an atomic write. If the template cannot be resolved
    (e.g. a scaffold-mode target whose `templates/` dir was not copied in),
    degrades gracefully: returns (False, <manual-create guidance>) and the
    caller exits 0."""
    people = team_signal.people_md_path(target)
    if people.exists():
        return (False, f"people.md already exists at {people} — leaving it untouched.")

    template = plugin_root() / "templates" / "docs" / "memory" / "people.md.template"
    if not template.is_file():
        return (
            False,
            "could not locate the people.md template at "
            f"{template} — create docs/memory/people.md manually "
            "(this is expected for a scaffold-mode target without a "
            "bundled templates/ dir).",
        )
    # Inline `{{PROJECT_NAME}}`-only substitution is byte-identical to
    # scaffold-init's `copy_template` for the CURRENT single-placeholder
    # template (it carries no other placeholder and no `${CLAUDE_PLUGIN_ROOT}`
    # path for scaffold's `render()` leftover-check / `_rewrite_skill_md_paths`
    # to act on). That identity (slice 050-01 AC5) is now an invariant of the
    # template's content; `test_memory.py::BootstrapTemplateParityTests` guards
    # it by rendering the real template through BOTH paths and asserting
    # byte-equality — if the template ever gains a second placeholder, that
    # cross-check fails loudly here instead of shipping unrendered drift.
    rendered = template.read_text().replace("{{PROJECT_NAME}}", target.name)
    people.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(people, rendered)
    return (True, f"bootstrapped {people} from the scaffold-init template.")


def team_check(target: Path, *, bootstrap: bool = False, never: bool = False,
               isatty: "bool | None" = None) -> int:
    """Re-run jig's team signal and nudge to bootstrap people.md when the
    project has grown (spec 050-01). Returns a process exit code (always 0 in
    normal operation — this is an advisory, never a blocker).

    Flow:
      - `--bootstrap`: write people.md from the template (refuse-on-exists).
      - `--never`: write the `.jig/no-people-md` opt-out marker.
      - otherwise: no-op when people.md exists (AC2), the marker exists
        (AC3), or the signal does not fire; else emit the structured nudge
        (AC4). When stdin is a TTY, prompt y/n/never and act; when NOT a TTY
        (CI / agent), print the advisory + follow-up commands and exit 0
        without blocking (AC7).
    """
    people = team_signal.people_md_path(target)
    marker = team_signal.no_people_md_marker_path(target)

    # Explicit actions first — they are how the agent relays a non-TTY user
    # choice back into the helper. By design these run BEFORE the signal-fires
    # check: the flags relay the user's explicit [y]/[never] decision, so they
    # act unconditionally (an explicit --bootstrap writes people.md even on a
    # solo repo); the signal was already gated at nudge time.
    if bootstrap:
        _written, msg = _bootstrap_people_md(target)
        print(f"team-check: {msg}")
        return 0
    if never:
        team_signal.write_no_people_md_marker(target)
        print(f"team-check: wrote opt-out marker {marker} — no further nudges.")
        return 0

    # No-op suppressors.
    if people.exists():
        print("team-check: people.md already present — no nudge.")
        return 0
    if marker.exists():
        print(f"team-check: opt-out marker {marker} present — no nudge.")
        return 0

    count = team_signal.count_team_contributors(target)
    if count < team_signal.TEAM_THRESHOLD:
        print(f"team-check: solo project ({count} contributor"
              f"{'' if count == 1 else 's'}) — no nudge.")
        return 0

    # Signal fires, people.md absent, marker absent → nudge (AC4).
    advisory = (
        f"team-check: this project now has {count} git contributors but "
        "docs/memory/people.md is absent.\n"
        "  people.md gives the agent per-person context (attribution, "
        "message framing, module ownership).\n"
        "  Options:\n"
        "    [y]     bootstrap docs/memory/people.md now (from the template)\n"
        "    [n]     skip this run (you'll be asked again next memory-sync)\n"
        "    [never] suppress future nudges (writes .jig/no-people-md)"
    )
    print(advisory)

    if isatty is None:
        isatty = sys.stdin.isatty()

    if not isatty:
        # AC7 — non-interactive: print the follow-up commands, do NOT block.
        rel = "docs/memory/people.md"
        print(
            "  Non-interactive run: not prompting. To act, re-run with the "
            "matching flag:\n"
            f"    memory.py team-check --bootstrap <target>   # create {rel}\n"
            "    memory.py team-check --never <target>       # suppress forever"
        )
        return 0

    # Interactive — prompt and act.
    try:
        answer = input("  Bootstrap people.md? [y/n/never]: ").strip().lower()
    except EOFError:
        answer = "n"
    if answer in ("y", "yes"):
        _written, msg = _bootstrap_people_md(target)
        print(f"team-check: {msg}")
    elif answer == "never":
        team_signal.write_no_people_md_marker(target)
        print(f"team-check: wrote opt-out marker {marker} — no further nudges.")
    else:
        print("team-check: skipped this run.")
    return 0


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _ensure_file(path: Path, default_content: str) -> None:
    """Create a file with default_content if it doesn't exist. Self-healing."""
    if path.exists():
        return
    _ensure_dir(path.parent)
    atomic_write_text(path, default_content)


def _glossary_path(target: Path) -> Path:
    path = target / "docs" / "memory" / "glossary.md"
    _ensure_file(path, "# Glossary\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _learnings_path(target: Path) -> Path:
    path = target / "docs" / "memory" / "learnings.md"
    _ensure_file(path, "# Learnings\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _inbox_path(target: Path) -> Path:
    path = target / "docs" / "inbox.md"
    _ensure_file(path, "# Inbox\n\n> Status: Draft (self-healed by memory-sync)\n\n")
    return path


def _refinement_todo_path(target: Path) -> Path:
    """Self-healing path for docs/refinement-todo.md (per slice 028-02)."""
    path = target / "docs" / "refinement-todo.md"
    _ensure_file(
        path,
        "# Refinement Todo\n\n> Status: Draft (self-healed by memory-sync)\n\n",
    )
    return path


def _claude_md_path(target: Path) -> Path:
    """Returns CLAUDE.md path; does not create. Callers handle absence."""
    return target / "CLAUDE.md"


# ---------- Slice 028-02: file-lock for inbox + refinement-todo appends ----------
# Lock scope: a single .git/jig-locks/ directory shared by every worktree of the
# same project. fcntl.flock is kernel-released on process exit (including
# crash / SIGKILL), so stale-lock recovery is trivial — no PID-reuse window.
# The PID written to the lock file is *diagnostic only*: it lets a user
# inspect "who's holding it" while the kernel decides what counts as "held."
#
# Per ADR-0002's three-callers rule, the helpers are inline in this module
# (two callers: add-inbox, add-refinement-todo). Extraction defers until
# slice 028-03 (or any third caller) needs them.

CLI_DEFAULT_LOCK_TIMEOUT = 5.0  # seconds; configurable via the Python API kwarg.


class LockTimeoutError(Exception):
    """Raised when `_file_lock` cannot acquire within its timeout. Surfaces
    as a non-zero exit + clear stderr error in the CLI path."""


def _resolve_lock_dir(target: Path) -> Path:
    """Resolve the lock directory for this target.

    Inside a git repo, returns `<git-common-dir>/jig-locks/`. Critical: multiple
    worktrees of the SAME project share a single `.git/` (the "common dir"),
    so this is the only filesystem location that serializes across worktrees.
    A `<target>/.jig/locks/` per-worktree path would only serialize within one
    worktree, which would miss the whole point.

    Outside a git repo (or when git isn't on PATH), falls back to
    `<target>/.jig/locks/` so the helper still works on bare directories.

    The result is `mkdir -p`'d.
    """
    lock_dir = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, cwd=str(target),
        )
        if result.returncode == 0:
            raw = result.stdout.strip()
            if raw:
                p = Path(raw)
                if not p.is_absolute():
                    p = (target / p).resolve()
                lock_dir = p / "jig-locks"
    except (FileNotFoundError, OSError):
        # git not on PATH or invocation failed — fall through to the
        # .jig/locks/ fallback.
        pass
    if lock_dir is None:
        lock_dir = target / ".jig" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir


@contextlib.contextmanager
def _file_lock(lock_path: Path, timeout: float):
    """Context manager that acquires an exclusive fcntl.flock on `lock_path`.

    Acquires non-blocking in a polled loop with a `time.monotonic()` deadline.
    Polling cadence is 50ms — that's not a race-manufacturing sleep, it's just
    how often we ask the kernel "is it free yet?". The total wait is bounded
    by `timeout`.

    On acquisition, truncates the file and writes the current PID as the
    body — purely diagnostic, so an inspecting user can see "who's holding
    this lock right now." The kernel — not the PID — is the source of truth:
    if the holder dies (crash, SIGKILL, normal exit), the OS releases the
    flock immediately. This means there is no PID-reuse window: a stale lock
    file on disk is never "held" once its owner has gone away.

    The lock file itself is left on disk after release. That's intentional —
    creating-and-removing a lock file races itself ("is this fresh or a
    leftover?"); leaving the file persistent and using fcntl as the held-bit
    sidesteps the question entirely.

    Raises `LockTimeoutError` if the deadline elapses without acquisition.
    """
    # `_resolve_lock_dir` already created `lock_path.parent`; no second mkdir
    # is required here.
    deadline = time.monotonic() + timeout
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise LockTimeoutError(
                        f"could not acquire lock on {lock_path} within "
                        f"{timeout}s (another process is holding it; "
                        f"see PID in {lock_path}). Re-run, or kill the "
                        f"stale holder if it has crashed."
                    ) from None
                time.sleep(0.05)
        # Lock acquired — record the holder PID for diagnostics.
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            os.ftruncate(fd, 0)
            os.write(fd, str(os.getpid()).encode())
        except OSError:
            # PID-write is purely advisory; never let it sabotage a successful
            # acquisition.
            pass
        try:
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        os.close(fd)
# ---------- end slice 028-02 ----------


def _append_section(path: Path, heading: str, body: str) -> bool:
    """Append `## <heading>\\n<body>` to `path` unless an exact `## <heading>\\n`
    already exists. Returns True if appended, False if skipped (idempotent)."""
    text = path.read_text()
    marker = f"\n## {heading}\n"
    if marker in text:
        return False
    if not text.endswith("\n"):
        text += "\n"
    text += marker + body
    if not text.endswith("\n"):
        text += "\n"
    atomic_write_text(path, text)
    return True


def add_term(target: Path, term: str, definition: str) -> bool:
    """Append a term to glossary.md. Idempotent on exact term name."""
    return _append_section(_glossary_path(target), term, definition + "\n")


def add_learning(target: Path, title: str, body: str) -> bool:
    """Append a learning to learnings.md. Idempotent on exact title."""
    return _append_section(_learnings_path(target), title, body + "\n")


def add_inbox(target: Path, item: str,
              timeout: float = CLI_DEFAULT_LOCK_TIMEOUT) -> bool:
    """Append a dated bullet to inbox.md. Always appends (no idempotency check
    — inbox is a stream, duplicate-ish entries are acceptable).

    Slice 028-02: acquires an fcntl.flock on
    `<git-common-dir>/jig-locks/inbox.md.lock` so parallel worktrees never
    silently overwrite each other on git merge. `timeout` is the bound on
    how long to wait for the lock; the CLI default is 5s but tests pass
    smaller values. Raises `LockTimeoutError` on deadline.

    The `_inbox_path` self-heal call is performed *inside* the lock so
    a concurrent first-write against a non-existent inbox.md doesn't
    let the two writers race `_ensure_file`'s `exists()`/`write_text`
    sequence and clobber each other's appended bullet."""
    lock_path = _resolve_lock_dir(target) / "inbox.md.lock"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = f"- [{date}] {item}\n"
    with _file_lock(lock_path, timeout=timeout):
        path = _inbox_path(target)
        with open(path, "a") as f:
            f.write(line)
    return True


def add_refinement_todo(target: Path, item: str,
                        timeout: float = CLI_DEFAULT_LOCK_TIMEOUT) -> bool:
    """Append raw text to docs/refinement-todo.md.

    The caller composes the markdown chunk (H2 categorization, deferred-/
    resolution-trigger structure, etc.); the helper just appends with a
    boundary-newline guarantee and the file lock. Mirrors `add_inbox`'s
    shape (lock surface, semantics) so the helper signature is uniform
    across the two append-locked artifacts per slice 028-02 AC #3.

    Self-heals the file with a minimal scaffold if absent. The self-heal
    runs *inside* the lock so concurrent first-writes against a
    non-existent file don't race `_ensure_file`'s `exists()`/`write_text`
    sequence and clobber each other. Raises `LockTimeoutError` if the
    lock cannot be acquired within `timeout`.
    """
    lock_path = _resolve_lock_dir(target) / "refinement-todo.md.lock"
    with _file_lock(lock_path, timeout=timeout):
        path = _refinement_todo_path(target)
        # Read existing content under the lock so the trailing-newline
        # check is consistent with the append.
        existing = path.read_text() if path.exists() else ""
        chunk = item
        if existing and not existing.endswith("\n"):
            chunk = "\n" + chunk
        if not chunk.endswith("\n"):
            chunk = chunk + "\n"
        with open(path, "a") as f:
            f.write(chunk)
    return True


def promote(target: Path, term: str, definition: str) -> bool:
    """Add a term to CLAUDE.md Hot Cache → Key terms.
    If CLAUDE.md is absent (pre-scaffold-init project), fall back to glossary
    and warn on stderr. Idempotent on exact `- **<term>**` presence."""
    claude_md = _claude_md_path(target)
    if not claude_md.exists():
        sys.stderr.write(
            "warning: CLAUDE.md not found at target root; "
            "falling back to glossary.md for term '%s'\n" % term
        )
        return add_term(target, term, definition)

    text = claude_md.read_text()
    if HOT_CACHE_KEY_TERMS_HEADING not in text:
        sys.stderr.write(
            "warning: CLAUDE.md missing Key terms section; "
            "falling back to glossary.md for term '%s'\n" % term
        )
        return add_term(target, term, definition)

    entry = f"- **{term}** — {definition}"
    # Idempotency: already promoted? Anchor to line start to avoid false positives
    # when the marker appears inside another bullet's prose.
    if re.search(rf"(?m)^- \*\*{re.escape(term)}\*\*", text):
        return False

    # Replace the placeholder line if present (first promotion);
    # otherwise insert the new bullet right after the heading.
    if HOT_CACHE_PLACEHOLDER.search(text):
        new_text = HOT_CACHE_PLACEHOLDER.sub(entry, text, count=1)
    else:
        # Insert after the Key terms heading and any existing bullets — find
        # the line right after the section heading and append within the section.
        heading_idx = text.index(HOT_CACHE_KEY_TERMS_HEADING)
        line_end = text.index("\n", heading_idx)
        # Insert after the heading line; will become first bullet, others shift.
        new_text = text[: line_end + 1] + entry + "\n" + text[line_end + 1 :]

    atomic_write_text(claude_md, new_text)
    return True


def _find_in_hot_cache(target: Path, term: str) -> str:
    """Search CLAUDE.md Hot Cache → Key terms section for `term`.
    Case-insensitive. Returns the matching bullet's definition (after the em-dash
    or first hyphen separator), or '' if not found."""
    claude_md = _claude_md_path(target)
    if not claude_md.exists():
        return ""
    text = claude_md.read_text()
    if HOT_CACHE_KEY_TERMS_HEADING not in text:
        return ""
    # Scope the search to the Key terms section
    heading_idx = text.index(HOT_CACHE_KEY_TERMS_HEADING)
    section = text[heading_idx:]
    # Next H3 or H2 bounds the section
    nxt = re.search(r"(?m)^(?:##|###)\s", section[len(HOT_CACHE_KEY_TERMS_HEADING):])
    section_body = section[: len(HOT_CACHE_KEY_TERMS_HEADING) + nxt.start()] if nxt else section
    # Line-anchored case-insensitive match: `- **<term>** — <definition>`
    pattern = rf"(?im)^- \*\*{re.escape(term)}\*\*\s*[—\-:]?\s*(.+?)\s*$"
    m = re.search(pattern, section_body)
    return m.group(1).strip() if m else ""


def _find_in_glossary(target: Path, term: str) -> str:
    """Search docs/memory/glossary.md for an H2 matching `term` (case-insensitive).
    Returns the body prose under the heading, or '' if not found."""
    path = target / "docs" / "memory" / "glossary.md"
    if not path.exists():
        return ""
    text = path.read_text()
    # Match `## <term>` heading then capture body until the next ## or end
    pattern = rf"(?ims)^##\s+{re.escape(term)}\s*$\n+(.*?)(?=^##\s|\Z)"
    m = re.search(pattern, text)
    if not m:
        return ""
    body = m.group(1).strip()
    return body


def lookup(target: Path, term: str) -> tuple:
    """Search hot cache then glossary for `term`. Returns (source, definition)
    on hit; ('', '') on miss. `source` is 'hot-cache' or 'glossary'."""
    hit = _find_in_hot_cache(target, term)
    if hit:
        return ("hot-cache", hit)
    hit = _find_in_glossary(target, term)
    if hit:
        return ("glossary", hit)
    return ("", "")


def summary(target: Path) -> str:
    """Return a one-line-per-file count summary of the memory layer state."""
    lines = ["# Memory Summary", ""]

    def count_sections(path: Path) -> int:
        if not path.exists():
            return 0
        return len(re.findall(r"(?m)^## ", path.read_text()))

    def count_bullets(path: Path) -> int:
        if not path.exists():
            return 0
        return len(re.findall(r"(?m)^- ", path.read_text()))

    g = count_sections(target / "docs/memory/glossary.md")
    le = count_sections(target / "docs/memory/learnings.md")
    inb = count_bullets(target / "docs/inbox.md")
    lines.append(f"- glossary entries: **{g}**")
    lines.append(f"- learnings entries: **{le}**")
    lines.append(f"- inbox items: **{inb}**")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="memory.py",
                                description="jig memory-sync helper")
    sub = p.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("add-term")
    pt.add_argument("term")
    pt.add_argument("definition")
    pt.add_argument("target")

    pl = sub.add_parser("add-learning")
    pl.add_argument("title")
    pl.add_argument("--body", default=None,
                    help="learning body; if omitted, read from stdin")
    pl.add_argument("target")

    pi = sub.add_parser("add-inbox")
    pi.add_argument("item")
    pi.add_argument("target")

    prt = sub.add_parser("add-refinement-todo")
    prt.add_argument("item")
    prt.add_argument("target")

    pp = sub.add_parser("promote")
    pp.add_argument("term")
    pp.add_argument("definition")
    pp.add_argument("target")

    pk = sub.add_parser("lookup")
    pk.add_argument("term")
    pk.add_argument("target")

    ps = sub.add_parser("summary")
    ps.add_argument("target")

    # Slice 050-01 — re-run scaffold-init's team signal at end of memory-sync.
    ptc = sub.add_parser(
        "team-check",
        help="re-evaluate the team signal; nudge to bootstrap people.md "
             "when the project has grown past solo (spec 050-01)",
    )
    tc_action = ptc.add_mutually_exclusive_group()
    tc_action.add_argument(
        "--bootstrap", action="store_true",
        help="write docs/memory/people.md from the template (refuses if it "
             "already exists)",
    )
    tc_action.add_argument(
        "--never", action="store_true",
        help="write the .jig/no-people-md opt-out marker (suppress nudges)",
    )
    ptc.add_argument("target")

    return p


def main(argv: list) -> int:
    parser = _build_parser()
    try:
        ns = parser.parse_args(argv[1:])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2

    target = Path(ns.target).resolve()
    if not target.exists():
        sys.stderr.write(f"target does not exist: {target}\n")
        return 1

    try:
        if ns.command == "add-term":
            added = add_term(target, ns.term, ns.definition)
            print(f"glossary: {'added' if added else 'already present'} '{ns.term}'")
        elif ns.command == "add-learning":
            body = ns.body if ns.body is not None else sys.stdin.read().rstrip()
            if not body.strip():
                sys.stderr.write(
                    "warning: add-learning called with empty body — entry "
                    f"'{ns.title}' will have no content; consider passing --body or piping text\n"
                )
            added = add_learning(target, ns.title, body)
            print(f"learnings: {'added' if added else 'already present'} '{ns.title}'")
        elif ns.command == "add-inbox":
            add_inbox(target, ns.item)
            print(f"inbox: parked '{ns.item}'")
        elif ns.command == "add-refinement-todo":
            add_refinement_todo(target, ns.item)
            print(f"refinement-todo: appended {len(ns.item)} chars")
        elif ns.command == "promote":
            added = promote(target, ns.term, ns.definition)
            print(f"hot cache: {'promoted' if added else 'already present'} '{ns.term}'")
        elif ns.command == "lookup":
            source, definition = lookup(target, ns.term)
            if not source:
                sys.stderr.write(f"not found: '{ns.term}'\n")
                return 2
            sys.stdout.write(f"{definition}\n")
            sys.stdout.write(f"source: {source}\n")
        elif ns.command == "summary":
            sys.stdout.write(summary(target))
        elif ns.command == "team-check":
            return team_check(
                target, bootstrap=ns.bootstrap, never=ns.never,
            )
    except Exception as exc:
        sys.stderr.write(f"memory-sync failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
