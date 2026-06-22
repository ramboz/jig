"""
AC verification tests for slice 002-01 (memory-sync explicit-sync).

Run from the repo root:
    python3 skills/memory-sync/test_memory.py
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY = REPO_ROOT / "skills" / "memory-sync" / "memory.py"
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_memory(target: Path, *args: str, stdin: str = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(MEMORY), *args, str(target)],
        capture_output=True, text=True, env=env,
        input=stdin,
    )


def scaffold(target: Path) -> None:
    """Run scaffold-init to set up the target."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target)],
        capture_output=True, text=True, env=env, check=True,
    )


class MemoryHelperTests(unittest.TestCase):
    """Slice 002-01 — CLI helpers operate on a scaffolded target."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-mem-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _glossary(self) -> str:
        return (self.target / "docs/memory/glossary.md").read_text()

    def _learnings(self) -> str:
        return (self.target / "docs/memory/learnings.md").read_text()

    def _inbox(self) -> str:
        return (self.target / "docs/inbox.md").read_text()

    def _claude(self) -> str:
        return (self.target / "CLAUDE.md").read_text()

    # AC #2: new glossary terms
    def test_add_term_appends_to_glossary(self):
        result = run_memory(self.target, "add-term", "SPIDR",
                            "Five story-splitting techniques: Spike, Path, Interface, Data, Rules")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._glossary()
        self.assertRegex(content, r"(?m)^## SPIDR\b")
        self.assertIn("Five story-splitting techniques", content)

    def test_add_term_idempotent(self):
        run_memory(self.target, "add-term", "FOO", "the foo system")
        run_memory(self.target, "add-term", "FOO", "the foo system")
        # Only one ## FOO heading
        self.assertEqual(self._glossary().count("\n## FOO\n"), 1,
                         "duplicate term should not write twice")

    # AC #3: new learnings
    def test_add_learning_with_body_flag(self):
        result = run_memory(self.target, "add-learning", "Heredoc stdin bug",
                            "--body", "python3 - <<EOF consumes stdin; use python3 -c instead")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._learnings()
        self.assertIn("Heredoc stdin bug", content)
        self.assertIn("python3 -c instead", content)

    def test_add_learning_via_stdin(self):
        result = run_memory(self.target, "add-learning", "Title via stdin",
                            stdin="Body comes from stdin when --body omitted.\n")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("Title via stdin", self._learnings())
        self.assertIn("Body comes from stdin", self._learnings())

    def test_add_learning_idempotent_on_same_title(self):
        run_memory(self.target, "add-learning", "X", "--body", "y")
        run_memory(self.target, "add-learning", "X", "--body", "y")
        self.assertEqual(self._learnings().count("\n## X\n"), 1)

    # AC #5: unresolved → inbox.md
    def test_add_inbox_dates_entry(self):
        result = run_memory(self.target, "add-inbox", "explore jq alternative for hooks")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._inbox()
        self.assertRegex(content, r"- \[\d{4}-\d{2}-\d{2}\] explore jq alternative")

    def test_add_inbox_appends(self):
        run_memory(self.target, "add-inbox", "first")
        run_memory(self.target, "add-inbox", "second")
        # Both items present, in order
        c = self._inbox()
        self.assertLess(c.index("first"), c.index("second"))

    # AC #4: high-frequency terms promoted to hot cache
    def test_promote_writes_to_hot_cache(self):
        result = run_memory(self.target, "promote", "jig",
                            "the AI-native dev scaffold plugin")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self._claude()
        # Locate the Key terms section under Hot Cache
        idx = content.find("### Key terms")
        self.assertGreater(idx, 0, "missing Key terms section")
        next_heading = content.find("\n### ", idx + 1)
        section = content[idx:next_heading if next_heading != -1 else len(content)]
        self.assertIn("jig", section)
        self.assertIn("the AI-native dev scaffold plugin", section)

    def test_promote_idempotent(self):
        run_memory(self.target, "promote", "ABC", "alpha bravo charlie")
        run_memory(self.target, "promote", "ABC", "alpha bravo charlie")
        # Only one entry
        c = self._claude()
        self.assertEqual(c.count("alpha bravo charlie"), 1)

    def test_promote_not_fooled_by_prose_mention(self):
        """Regression (reviewer-flagged): if an existing entry's prose mentions
        `- **FOO**`, promoting FOO must still write a real entry — the
        idempotency check is line-anchored."""
        # Promote a term whose definition references another marker-shaped phrase
        run_memory(self.target, "promote", "BAZ",
                   "see also - **FOO** for related context")
        # Now promote FOO — should succeed, not be falsely treated as already-present
        result = run_memory(self.target, "promote", "FOO", "the foo system")
        self.assertEqual(result.returncode, 0)
        self.assertIn("promoted", result.stdout.lower())
        # And the actual FOO entry should be in the file
        self.assertIn("the foo system", self._claude())

    # AC #1: summary command lists what's in memory
    def test_summary_lists_counts(self):
        run_memory(self.target, "add-term", "AAA", "first")
        run_memory(self.target, "add-learning", "BBB", "--body", "second")
        run_memory(self.target, "add-inbox", "CCC")
        result = run_memory(self.target, "summary")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        out = result.stdout
        self.assertIn("glossary", out.lower())
        self.assertIn("learnings", out.lower())
        self.assertIn("inbox", out.lower())
        # The counts should reflect at least the items just added
        self.assertRegex(out, r"glossary.*?\b1\b|\b1\b.*?glossary")


class LookupTests(unittest.TestCase):
    """Slice 002-02 — lookup command: hot cache first, glossary fallback."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-lookup-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lookup_finds_glossary_term(self):
        run_memory(self.target, "add-term", "SPIDR", "Spike, Path, Interface, Data, Rules")
        result = run_memory(self.target, "lookup", "SPIDR")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("Spike, Path, Interface, Data, Rules", result.stdout)
        self.assertIn("glossary", result.stdout.lower())

    def test_lookup_finds_hot_cache_term(self):
        run_memory(self.target, "promote", "jig", "the AI-native dev scaffold plugin")
        result = run_memory(self.target, "lookup", "jig")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("the AI-native dev scaffold plugin", result.stdout)
        # Source should indicate hot cache (not glossary)
        self.assertRegex(result.stdout.lower(), r"hot[\s-]?cache")

    # AC #1: hot cache wins when term is in both
    def test_lookup_hot_cache_wins_when_both(self):
        run_memory(self.target, "add-term", "FOO", "glossary definition")
        run_memory(self.target, "promote", "FOO", "hot cache definition")
        result = run_memory(self.target, "lookup", "FOO")
        self.assertEqual(result.returncode, 0)
        self.assertIn("hot cache definition", result.stdout)
        self.assertNotIn("glossary definition", result.stdout)

    def test_lookup_returns_2_for_unknown(self):
        result = run_memory(self.target, "lookup", "NEVER_DEFINED")
        self.assertEqual(result.returncode, 2,
                         "lookup miss should exit 2; got %d" % result.returncode)
        self.assertEqual(result.stdout, "", "no stdout on miss")
        self.assertIn("not found", result.stderr.lower())

    def test_lookup_case_insensitive(self):
        run_memory(self.target, "add-term", "SPIDR", "definition")
        result = run_memory(self.target, "lookup", "spidr")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("definition", result.stdout)

    # AC #5: after add-term, subsequent lookup succeeds
    def test_lookup_after_add_term_round_trip(self):
        # First lookup misses
        miss = run_memory(self.target, "lookup", "BARQ")
        self.assertEqual(miss.returncode, 2)
        # Add the term (simulating "ask user, get answer, persist")
        run_memory(self.target, "add-term", "BARQ", "Bar Q definition")
        # Second lookup hits
        hit = run_memory(self.target, "lookup", "BARQ")
        self.assertEqual(hit.returncode, 0)
        self.assertIn("Bar Q definition", hit.stdout)


class LookupOnBareDirTests(unittest.TestCase):
    """Slice 002-02 — lookup graceful on un-scaffolded target."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-lookup-bare-")
        self.target = Path(self.tmpdir) / "bare-project"
        self.target.mkdir()
        # Do NOT scaffold

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lookup_on_bare_dir_returns_2(self):
        result = run_memory(self.target, "lookup", "ANYTHING")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())


class SelfHealingTests(unittest.TestCase):
    """AC #6: memory.py creates docs/memory/ and docs/inbox.md if absent."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-heal-")
        self.target = Path(self.tmpdir) / "bare-project"
        self.target.mkdir()
        # Do NOT scaffold — we want a bare directory

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_memory_dir_if_missing(self):
        result = run_memory(self.target, "add-term", "X", "y")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.target / "docs/memory/glossary.md").exists())

    def test_creates_inbox_md_if_missing(self):
        result = run_memory(self.target, "add-inbox", "first thing")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.target / "docs/inbox.md").exists())

    def test_promote_warns_when_no_claude_md(self):
        result = run_memory(self.target, "promote", "X", "y")
        # Should still succeed (writing X to glossary as fallback)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Stderr should mention the fallback
        combined = result.stderr.lower() + result.stdout.lower()
        self.assertTrue(
            "claude.md" in combined or "fallback" in combined,
            "expected a warning about missing CLAUDE.md",
        )


class IntegrationTests(unittest.TestCase):
    """Slice 002-04 — static-content checks for reconciliation-integration.

    These guard against future edits silently removing the memory-layer
    integration in the reviewer agent or spec-workflow skill stub."""

    def test_reviewer_agent_forbids_writing_to_memory(self):
        """AC #2: reviewer.md must explicitly prohibit writing to docs/memory/."""
        reviewer = (REPO_ROOT / "agents" / "reviewer.md").read_text()
        # Match either form of the prohibition: "docs/memory" or "memory/" path
        self.assertRegex(
            reviewer,
            r"(?i)do not\s+(?:write|modify|edit|update).*(?:docs/memory|memory layer|memory/)",
            "reviewer.md must prohibit writes to docs/memory/",
        )

    def test_spec_workflow_includes_memory_sync_in_reconciliation(self):
        """AC #1 + #3: spec-workflow's reconciliation checklist surfaces memory-sync
        — the memory-sync mention must be *inside* the reconciliation section,
        not just anywhere in the file."""
        spec_workflow = (REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md").read_text()
        # Locate the reconciliation H2 header
        header = re.search(r"(?im)^##\s+[^\n]*reconcil[^\n]*$", spec_workflow)
        self.assertIsNotNone(header,
                             "spec-workflow must have a Reconciliation-titled H2 section")
        # Section runs from end of header line to the next H2 (or EOF)
        rest = spec_workflow[header.end():]
        nxt = re.search(r"(?m)^##\s", rest)
        section = rest[: nxt.start()] if nxt else rest
        self.assertIn(
            "memory-sync", section,
            "memory-sync must be referenced INSIDE the reconciliation section, not just anywhere",
        )


# ---------- Slice 028-02: inbox-and-refinement-todo-append-lock ----------
# Tests for the file-lock pattern guarding concurrent appends from parallel
# worktrees. Uses threading.Barrier for deterministic ordering and subprocess
# for stale-lock-recovery (kernel auto-release on process exit).


def _import_memory_module():
    """Importlib-load memory.py as a module so tests can call helpers
    directly (for `_file_lock` and configurable-timeout coverage)."""
    spec = importlib.util.spec_from_file_location("_memory_under_test", MEMORY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class AppendLockTests(unittest.TestCase):
    """Slice 028-02 — file-lock on inbox + refinement-todo appends.

    ACs covered:
      - AC #2: `add-inbox` acquires the lock, appends, releases.
      - AC #3: `add-refinement-todo` mirrors `add-inbox`'s shape + lock.
      - AC #4: lock timeout surfaces a clear error (no silent hangs).
      - AC #5: stale-lock recovery via kernel auto-release.
      - AC #6: contention coverage with deterministic threading.Barrier.

    AC #1 (decision: file-lock over reserve-on-main) is recorded in the
    slice's deviation log; no test needed.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-locks-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Make `target` a git repo so the lock dir resolves to .git/jig-locks/
        # (the path that serializes across worktrees-of-the-same-project).
        subprocess.run(
            ["git", "init", "-q"], cwd=self.target, check=True,
        )
        # Self-healing creates inbox.md / refinement-todo.md on first call;
        # but seed CLAUDE.md + memory/ via scaffold so helpers don't warn.
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #2: inbox helper still works end-to-end (regression-protect old behavior).
    def test_add_inbox_appends_with_lock(self):
        result = run_memory(self.target, "add-inbox", "first parallel-locked append")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.target / "docs/inbox.md").read_text()
        self.assertRegex(
            content,
            r"- \[\d{4}-\d{2}-\d{2}\] first parallel-locked append",
        )

    # AC #3: refinement-todo helper exists and appends raw text + trailing newline.
    def test_add_refinement_todo_appends_raw_text(self):
        result = run_memory(
            self.target, "add-refinement-todo", "first deferred decision",
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        path = self.target / "docs/refinement-todo.md"
        self.assertTrue(path.exists(),
                        "refinement-todo.md should self-heal on first call")
        content = path.read_text()
        self.assertIn("first deferred decision", content)
        # Must end with a newline boundary (so the next append doesn't run-on).
        self.assertTrue(content.endswith("\n"),
                        "refinement-todo.md must end with a trailing newline")

    def test_add_refinement_todo_ensures_trailing_newline(self):
        """AC #3: even if the existing file lacks a trailing newline, the
        helper inserts one before appending. Prevents run-on lines."""
        path = self.target / "docs" / "refinement-todo.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Refinement Todo\n\nLast line no newline")
        result = run_memory(
            self.target, "add-refinement-todo", "next entry",
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = path.read_text()
        # The previous "no newline" line and the new entry must be on separate
        # lines (separator inserted by the helper).
        self.assertNotIn("no newlinenext entry", content)
        self.assertIn("Last line no newline", content)
        self.assertIn("next entry", content)
        self.assertTrue(content.endswith("\n"))

    # AC #2 + AC #6: concurrent inbox appends from two threads — both land.
    def test_add_inbox_concurrent_two_threads_both_land(self):
        barrier = threading.Barrier(2)
        results = [None, None]

        def writer(i, payload):
            barrier.wait()  # Deterministic simultaneous start — no time.sleep race.
            results[i] = run_memory(self.target, "add-inbox", payload)

        t1 = threading.Thread(target=writer, args=(0, "alpha-inbox"))
        t2 = threading.Thread(target=writer, args=(1, "bravo-inbox"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(results[0].returncode, 0,
                         f"thread 0 stderr: {results[0].stderr}")
        self.assertEqual(results[1].returncode, 0,
                         f"thread 1 stderr: {results[1].stderr}")
        content = (self.target / "docs/inbox.md").read_text()
        self.assertIn("alpha-inbox", content)
        self.assertIn("bravo-inbox", content)
        # Both bullet lines must be present and on their own lines.
        bullets = re.findall(r"^- \[\d{4}-\d{2}-\d{2}\] .+$", content, re.MULTILINE)
        self.assertGreaterEqual(
            len([b for b in bullets if "alpha-inbox" in b or "bravo-inbox" in b]),
            2,
            f"both bullets must land as distinct lines; got: {bullets}",
        )

    # AC #6: three concurrent writers; all three lines must appear.
    def test_add_inbox_three_concurrent_writers_all_land(self):
        barrier = threading.Barrier(3)
        results = [None, None, None]

        def writer(i, payload):
            barrier.wait()
            results[i] = run_memory(self.target, "add-inbox", payload)

        threads = [
            threading.Thread(target=writer, args=(i, f"writer-{i}-payload"))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for i, r in enumerate(results):
            self.assertEqual(r.returncode, 0, f"thread {i} stderr: {r.stderr}")
        content = (self.target / "docs/inbox.md").read_text()
        for i in range(3):
            self.assertIn(
                f"writer-{i}-payload", content,
                f"thread {i}'s line missing from inbox under contention",
            )

    # AC #3 + AC #6: concurrent refinement-todo appends — both land.
    def test_add_refinement_todo_concurrent_serialization(self):
        barrier = threading.Barrier(2)
        results = [None, None]

        def writer(i, payload):
            barrier.wait()
            results[i] = run_memory(self.target, "add-refinement-todo", payload)

        t1 = threading.Thread(target=writer, args=(0, "refinement-alpha"))
        t2 = threading.Thread(target=writer, args=(1, "refinement-bravo"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        self.assertEqual(results[0].returncode, 0)
        self.assertEqual(results[1].returncode, 0)
        content = (self.target / "docs/refinement-todo.md").read_text()
        self.assertIn("refinement-alpha", content)
        self.assertIn("refinement-bravo", content)

    # AC #4: lock timeout — pre-hold the lock; the next caller bails clearly.
    def test_lock_timeout_surfaces_clear_error(self):
        """A waiting writer that doesn't acquire within the timeout exits
        non-zero with an error message naming the lock. The Python helper
        accepts a configurable timeout (0.2s here) so the test stays fast."""
        memory = _import_memory_module()
        # Pre-hold the inbox lock from a background thread so a foreground
        # caller hits the timeout. The helper exposes _file_lock as a
        # context manager; we hold it via threading.Event coordination.
        acquired = threading.Event()
        release = threading.Event()

        def holder():
            lock_dir = memory._resolve_lock_dir(self.target)
            lock_path = lock_dir / "inbox.md.lock"
            with memory._file_lock(lock_path, timeout=5.0):
                acquired.set()
                release.wait(timeout=5.0)

        h = threading.Thread(target=holder)
        h.start()
        try:
            self.assertTrue(acquired.wait(timeout=5.0),
                            "holder thread never reported lock acquisition")
            # Now call add_inbox via the Python API with a short timeout.
            with self.assertRaises(memory.LockTimeoutError) as ctx:
                memory.add_inbox(self.target, "should-timeout", timeout=0.2)
            self.assertIn("inbox", str(ctx.exception).lower())
        finally:
            release.set()
            h.join(timeout=5.0)

    def test_lock_timeout_cli_default_5s_is_configurable(self):
        """The CLI's default timeout is 5s (spec) but the Python API takes
        a kwarg. Pin both the constant and the kwarg path."""
        memory = _import_memory_module()
        # Pin the CLI default — flipping this constant is a user-visible
        # contract change and should require an explicit test update.
        self.assertEqual(
            memory.CLI_DEFAULT_LOCK_TIMEOUT, 5.0,
            "CLI default lock timeout is the slice 028-02 AC #4 contract",
        )
        # And the Python API accepts a smaller value (used by the
        # contention timeout test) — lock acquired immediately when
        # no holder is contending.
        memory.add_inbox(self.target, "fast-path", timeout=0.2)
        content = (self.target / "docs/inbox.md").read_text()
        self.assertIn("fast-path", content)

    # AC #5: stale-lock recovery — subprocess acquires + exits; next call works.
    def test_stale_lock_recovery_after_subprocess_exit(self):
        """fcntl.flock is released by the kernel on process exit (including
        SIGKILL). A subprocess that acquires and exits leaves the lock file
        on disk but unheld; the next call must acquire cleanly."""
        memory = _import_memory_module()
        lock_dir = memory._resolve_lock_dir(self.target)
        lock_path = lock_dir / "inbox.md.lock"

        # Spawn a subprocess that acquires the lock then exits immediately.
        # We use a one-liner Python that imports the helper, opens the lock,
        # writes its PID, then exits — kernel auto-releases on exit.
        helper_src = (
            "import sys, fcntl, os; "
            f"sys.path.insert(0, {str(MEMORY.parent)!r}); "
            f"lock_path = {str(lock_path)!r}; "
            "os.makedirs(os.path.dirname(lock_path), exist_ok=True); "
            "fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644); "
            "fcntl.flock(fd, fcntl.LOCK_EX); "
            "os.write(fd, str(os.getpid()).encode()); "
            # Process exits here, kernel releases the lock.
        )
        rc = subprocess.run(
            [sys.executable, "-c", helper_src],
            capture_output=True, text=True,
        )
        self.assertEqual(rc.returncode, 0, f"holder exited non-zero: {rc.stderr}")
        # The lock file exists on disk; the lock itself is released.
        self.assertTrue(lock_path.exists(),
                        "lock file should persist on disk (only the lock releases)")
        # Subsequent add-inbox call must succeed.
        result = run_memory(self.target, "add-inbox", "after-stale-lock")
        self.assertEqual(result.returncode, 0,
                         f"post-stale call must succeed; stderr: {result.stderr}")
        self.assertIn(
            "after-stale-lock",
            (self.target / "docs/inbox.md").read_text(),
        )

    def test_lock_dir_resolves_to_git_common_dir(self):
        """The lock path must live under <git-common-dir>/jig-locks/, so all
        worktrees of the same project serialize against the SAME directory.
        (A `.jig/locks/` per-worktree path would only serialize within one
        worktree — wrong scope.)"""
        memory = _import_memory_module()
        lock_dir = memory._resolve_lock_dir(self.target)
        # Inside a git repo, must resolve under .git/ (the common dir).
        self.assertIn(
            ".git", str(lock_dir),
            f"lock_dir must be under .git/ for parallel-worktree safety; "
            f"got {lock_dir}",
        )
        self.assertTrue(
            str(lock_dir).endswith("jig-locks"),
            f"lock dir basename must be 'jig-locks'; got {lock_dir}",
        )

    def test_lock_dir_falls_back_outside_git_repo(self):
        """When `git rev-parse --git-common-dir` fails (no git, bare dir),
        the helper falls back to <target>/.jig/locks/ so the helper still
        works on un-scaffolded projects."""
        memory = _import_memory_module()
        non_git = Path(tempfile.mkdtemp(prefix="jig-nogit-"))
        try:
            lock_dir = memory._resolve_lock_dir(non_git)
            self.assertEqual(
                lock_dir, non_git / ".jig" / "locks",
                f"fallback path must be <target>/.jig/locks/; got {lock_dir}",
            )
        finally:
            import shutil
            shutil.rmtree(non_git, ignore_errors=True)

    def test_lock_file_records_holder_pid(self):
        """AC #5 (diagnostic): the lock file content is the holder's PID so
        an inspecting user can see who's blocking. Kernel — not the PID —
        is the source of truth for held-ness."""
        memory = _import_memory_module()
        lock_dir = memory._resolve_lock_dir(self.target)
        lock_path = lock_dir / "inbox.md.lock"
        acquired = threading.Event()
        release = threading.Event()
        recorded_pid_text = {}

        def holder():
            with memory._file_lock(lock_path, timeout=5.0):
                # Read the PID from the file while the lock is held BEFORE
                # signaling acquired — otherwise the main thread can race
                # ahead and read recorded_pid_text before it's populated.
                recorded_pid_text["text"] = lock_path.read_text().strip()
                acquired.set()
                release.wait(timeout=5.0)

        h = threading.Thread(target=holder)
        h.start()
        try:
            self.assertTrue(acquired.wait(timeout=5.0))
            self.assertEqual(
                recorded_pid_text["text"], str(os.getpid()),
                "lock file should contain the holder's PID",
            )
        finally:
            release.set()
            h.join(timeout=5.0)


class AppendLockFirstWriteRaceTests(unittest.TestCase):
    """Slice 028-02 — concurrent first-writes against a non-existent
    inbox.md/refinement-todo.md must still serialize. The self-heal
    `_inbox_path` / `_refinement_todo_path` runs inside the lock so the
    pre-existing TOCTOU in `_ensure_file` (`exists()`/`write_text`)
    cannot clobber a concurrent append.

    Regression for the compliance-pass reviewer note on
    `skills/memory-sync/memory.py:246, 269`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-locks-first-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Bare git init — do NOT run scaffold(), so inbox.md and
        # refinement-todo.md don't exist on the first call.
        subprocess.run(
            ["git", "init", "-q"], cwd=self.target, check=True,
        )
        # Sanity: neither artifact pre-exists.
        self.assertFalse((self.target / "docs/inbox.md").exists())
        self.assertFalse((self.target / "docs/refinement-todo.md").exists())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_concurrent_first_writes_to_inbox_both_land(self):
        """Two concurrent writers against a non-existent inbox.md — both
        bullets must land (the self-heal must be inside the lock)."""
        barrier = threading.Barrier(2)
        results = [None, None]

        def writer(i, payload):
            barrier.wait()
            results[i] = run_memory(self.target, "add-inbox", payload)

        t1 = threading.Thread(target=writer, args=(0, "first-write-alpha"))
        t2 = threading.Thread(target=writer, args=(1, "first-write-bravo"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        for i, r in enumerate(results):
            self.assertEqual(r.returncode, 0, f"writer {i} stderr: {r.stderr}")
        content = (self.target / "docs/inbox.md").read_text()
        self.assertIn("first-write-alpha", content)
        self.assertIn("first-write-bravo", content)

    def test_concurrent_first_writes_to_refinement_todo_both_land(self):
        """Same shape, refinement-todo flavour."""
        barrier = threading.Barrier(2)
        results = [None, None]

        def writer(i, payload):
            barrier.wait()
            results[i] = run_memory(
                self.target, "add-refinement-todo", payload,
            )

        t1 = threading.Thread(target=writer, args=(0, "rt-first-alpha"))
        t2 = threading.Thread(target=writer, args=(1, "rt-first-bravo"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        for i, r in enumerate(results):
            self.assertEqual(r.returncode, 0, f"writer {i} stderr: {r.stderr}")
        content = (self.target / "docs/refinement-todo.md").read_text()
        self.assertIn("rt-first-alpha", content)
        self.assertIn("rt-first-bravo", content)


class AppendLockSkillDocsTests(unittest.TestCase):
    """Slice 028-02 — SKILL.md must document the new add-refinement-todo command."""

    def test_skill_md_mentions_add_refinement_todo(self):
        skill = (REPO_ROOT / "skills" / "memory-sync" / "SKILL.md").read_text()
        self.assertIn(
            "add-refinement-todo", skill,
            "SKILL.md must document the new add-refinement-todo command",
        )


def _git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, timeout=3
        ).returncode == 0
    except Exception:
        return False


@unittest.skipUnless(_git_available(), "git not available")
class TeamCheckTests(unittest.TestCase):
    """Slice 050-01 — `memory.py team-check` re-runs scaffold-init's team
    signal and nudges to bootstrap people.md when the project has grown."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-teamcheck-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        scaffold(self.target)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- git fixture helpers (mirror test_scaffold.py's pattern) ---
    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git", "-C", str(self.target), *args],
            capture_output=True, text=True, env=env, check=True,
        )

    def _commit_as(self, name: str, email: str, filename: str):
        (self.target / filename).write_text("seed")
        self._git("add", filename)
        env = {
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", f"add {filename}", env_extra=env)

    def _make_team_repo(self):
        """≥2 distinct authors → signal fires."""
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Bob", "bob@example.com", "b.txt")

    def _make_solo_repo(self):
        """1 author → signal does not fire."""
        self._git("init", "-q")
        self._commit_as("Alice", "alice@example.com", "a.txt")
        self._commit_as("Alice", "alice@example.com", "b.txt")

    def _people(self) -> Path:
        return self.target / "docs/memory/people.md"

    def _marker(self) -> Path:
        return self.target / ".jig" / "no-people-md"

    # AC4 — signal fires AND people.md absent AND marker absent → nudge.
    # Non-TTY (subprocess has no tty) so it must NOT block.
    def test_nudge_when_signal_fires_and_people_absent(self):
        self._make_team_repo()
        # scaffold ran on a bare dir (solo) so people.md is absent
        self.assertFalse(self._people().exists())
        result = run_memory(self.target, "team-check")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        out = result.stdout
        # names the contributor count
        self.assertIn("2", out, "advisory should name N=2 contributors")
        # three labeled options present
        self.assertIn("[y]", out)
        self.assertIn("[n]", out)
        self.assertIn("[never]", out)

    # AC7 — non-TTY mode prints the advisory + follow-up commands, exits 0,
    # does NOT prompt/block, does NOT write anything.
    def test_non_tty_prints_followup_commands_and_does_not_block(self):
        self._make_team_repo()
        result = run_memory(self.target, "team-check")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("--bootstrap", result.stdout)
        self.assertIn("--never", result.stdout)
        # nothing written: no people.md, no marker
        self.assertFalse(self._people().exists())
        self.assertFalse(self._marker().exists())

    # AC2 — people.md exists → no-op regardless of signal.
    def test_no_nudge_when_people_md_exists(self):
        self._make_team_repo()
        self._people().parent.mkdir(parents=True, exist_ok=True)
        self._people().write_text("# People\n\nhand-written\n")
        result = run_memory(self.target, "team-check")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertNotIn("[never]", result.stdout,
                         "no nudge options when people.md already exists")
        # file untouched
        self.assertIn("hand-written", self._people().read_text())

    # AC3 — marker exists → no-op (suppressed forever).
    def test_no_nudge_when_marker_exists(self):
        self._make_team_repo()
        self._marker().parent.mkdir(parents=True, exist_ok=True)
        self._marker().write_text("# opt out\n")
        result = run_memory(self.target, "team-check")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertNotIn("[never]", result.stdout,
                         "marker must suppress the nudge")
        self.assertFalse(self._people().exists())

    # Signal does not fire (solo) → no-op.
    def test_no_nudge_on_solo_repo(self):
        self._make_solo_repo()
        result = run_memory(self.target, "team-check")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertNotIn("[never]", result.stdout)
        self.assertFalse(self._people().exists())

    # AC5 — --bootstrap writes people.md from the real template.
    def test_bootstrap_writes_people_md_from_template(self):
        self._make_team_repo()
        result = run_memory(self.target, "team-check", "--bootstrap")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(self._people().exists(),
                        "--bootstrap must create people.md")
        body = self._people().read_text()
        # Same shape as scaffold-init's output (template watermark + project name)
        self.assertIn("Status: Draft (wizard-generated)", body)
        self.assertIn(self.target.name, body,
                      "{{PROJECT_NAME}} should be substituted")
        # No unrendered placeholders leaked
        self.assertNotIn("{{PROJECT_NAME}}", body)

    # AC5 — --bootstrap refuses to overwrite an existing people.md.
    def test_bootstrap_refuses_overwrite(self):
        self._make_team_repo()
        self._people().parent.mkdir(parents=True, exist_ok=True)
        self._people().write_text("# People\n\nhand-written\n")
        result = run_memory(self.target, "team-check", "--bootstrap")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # existing content preserved
        self.assertIn("hand-written", self._people().read_text())

    # --never writes the opt-out marker.
    def test_never_writes_marker(self):
        self._make_team_repo()
        result = run_memory(self.target, "team-check", "--never")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue(self._marker().exists(),
                        "--never must write .jig/no-people-md")

    # SKILL.md documents the new step.
    def test_skill_md_documents_team_check(self):
        skill = (REPO_ROOT / "skills" / "memory-sync" / "SKILL.md").read_text()
        self.assertIn("team-check", skill,
                      "SKILL.md must document the team-check step")


def _load_memory_module():
    """Load memory.py as a module for in-process interactive-path tests
    (the dir name has a hyphen, so a plain `import` won't work)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("jig_memory_for_test", MEMORY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_scaffold_module():
    """Load scaffold.py as a module so the cross-check test can render the
    people.md template through scaffold-init's OWN `copy_template`/`render`
    (the dir name has a hyphen, so a plain `import` won't work)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("jig_scaffold_for_test", SCAFFOLD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BootstrapTemplateParityTests(unittest.TestCase):
    """Slice 050-02 reconciliation (craft nit 1) — enforce AC5's byte-identity.

    Slice 050-02 retired the importlib loader, so `memory.py
    _bootstrap_people_md` now renders the people.md template via an inline
    `.read_text().replace("{{PROJECT_NAME}}", ...)` instead of calling
    scaffold-init's `copy_template`/`render`. Today the two outputs are
    byte-identical (the template carries only `{{PROJECT_NAME}}` and no
    plugin-root path), so slice 050-01's AC5 ("no drift, mirrors scaffold
    output") still holds — but that identity is now an IMPLICIT invariant of
    the template's content, not enforced by shared code. Both 050-02 reviewers
    flagged it.

    This test renders the REAL `templates/docs/memory/people.md.template`
    through BOTH paths into equivalent targets and asserts byte-identity. If
    the template ever gains a second placeholder or a `${CLAUDE_PLUGIN_ROOT}`
    path, memory-sync's bootstrap (which only substitutes `{{PROJECT_NAME}}`
    and applies no `render()` leftover-check / `_rewrite_skill_md_paths`
    post_render) would diverge from scaffold's `copy_template` — and this
    assertion fails loudly here rather than silently shipping the drift."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-bootstrap-parity-")
        # SAME project-name input for both paths so the comparison is fair:
        # `_bootstrap_people_md` derives `{{PROJECT_NAME}}` from `target.name`,
        # exactly as scaffold's `subs["PROJECT_NAME"] = target.name` does.
        self.project_name = "demo-project"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_bootstrap_render_matches_scaffold_copy_template_byte_for_byte(self):
        memory = _load_memory_module()
        scaffold_mod = _load_scaffold_module()

        os.environ["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        template = (
            REPO_ROOT / "templates" / "docs" / "memory" / "people.md.template"
        )
        self.assertTrue(template.is_file(),
                        f"real people.md template must exist at {template}")

        # --- Path A: memory-sync's bootstrap (the inline-render production code).
        mem_target = Path(self.tmpdir) / self.project_name
        mem_target.mkdir()
        written, _msg = memory._bootstrap_people_md(mem_target)
        self.assertTrue(written, "bootstrap should have written people.md")
        mem_people = mem_target / "docs" / "memory" / "people.md"
        mem_bytes = mem_people.read_bytes()

        # --- Path B: scaffold-init's own copy_template, with the EXACT
        # substitutions and post_render scaffold uses for people.md (full subs
        # dict + the machinery-mode `_rewrite_skill_md_paths` doc-rewrite). If
        # the template later gains a `{{JIG_VERSION}}`/`{{TIMESTAMP}}`
        # placeholder or a plugin-root path, this path renders it while Path A
        # leaves it raw — and the byte comparison below diverges.
        scaffold_dst = Path(self.tmpdir) / "scaffold-out" / "people.md"
        subs = {
            "PROJECT_NAME": self.project_name,
            "JIG_VERSION": "0.0.0-test",
            "TIMESTAMP": "2026-01-01T00:00:00Z",
        }
        scaffold_mod.copy_template(
            template, scaffold_dst, subs,
            post_render=scaffold_mod._rewrite_skill_md_paths,
        )
        scaffold_bytes = scaffold_dst.read_bytes()

        self.assertEqual(
            mem_bytes, scaffold_bytes,
            "memory-sync bootstrap and scaffold-init copy_template must render "
            "the people.md template byte-identically (AC5). They diverged — the "
            "template likely gained a placeholder or plugin-root path that "
            "scaffold's render() handles but memory-sync's inline "
            "`{{PROJECT_NAME}}`-only substitution does not. Route the bootstrap "
            "through scaffold's render path (or re-pin this invariant).",
        )


@unittest.skipUnless(_git_available(), "git not available")
class TeamCheckInteractiveTests(unittest.TestCase):
    """Slice 050-01 AC4 (interactive arm) — when stdin is a TTY the nudge
    prompts and acts. Driven in-process via team_check(isatty=True) with a
    patched input(), since a subprocess can't present a real TTY."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-teamint-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        subprocess.run([sys.executable, str(SCAFFOLD), str(self.target)],
                       capture_output=True, text=True, env=env, check=True)
        # team repo so the signal fires
        self._git("init", "-q")
        for name, email, fn in [("Alice", "alice@x.com", "a.txt"),
                                 ("Bob", "bob@x.com", "b.txt")]:
            self._commit_as(name, email, fn)
        self.mod = _load_memory_module()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args, env_extra=None):
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        return subprocess.run(["git", "-C", str(self.target), *args],
                              capture_output=True, text=True, env=env, check=True)

    def _commit_as(self, name, email, fn):
        (self.target / fn).write_text("seed")
        self._git("add", fn)
        self._git("commit", "-m", fn, env_extra={
            "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email,
        })

    def _run_with_answer(self, answer):
        import builtins
        orig = builtins.input
        builtins.input = lambda *a, **k: answer
        try:
            os.environ["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
            return self.mod.team_check(self.target, isatty=True)
        finally:
            builtins.input = orig

    def test_interactive_yes_bootstraps(self):
        rc = self._run_with_answer("y")
        self.assertEqual(rc, 0)
        self.assertTrue((self.target / "docs/memory/people.md").exists(),
                        "interactive [y] must bootstrap people.md")

    def test_interactive_never_writes_marker(self):
        rc = self._run_with_answer("never")
        self.assertEqual(rc, 0)
        self.assertTrue((self.target / ".jig" / "no-people-md").exists(),
                        "interactive [never] must write the opt-out marker")
        self.assertFalse((self.target / "docs/memory/people.md").exists())

    def test_interactive_no_does_nothing(self):
        rc = self._run_with_answer("n")
        self.assertEqual(rc, 0)
        self.assertFalse((self.target / "docs/memory/people.md").exists())
        self.assertFalse((self.target / ".jig" / "no-people-md").exists())

    # Scaffold-mode fallback: when the people.md template can't be resolved
    # (a scaffolded target has no bundled templates/ dir), --bootstrap must
    # degrade gracefully — no people.md written, a manual-create message,
    # and a non-fatal outcome (caller exits 0).
    def test_bootstrap_degrades_when_template_missing(self):
        fake_root = Path(self.tmpdir) / "no-templates-root"
        (fake_root / "skills").mkdir(parents=True)
        orig = os.environ.get("CLAUDE_PLUGIN_ROOT")
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(fake_root)
        try:
            written, msg = self.mod._bootstrap_people_md(self.target)
        finally:
            if orig is not None:
                os.environ["CLAUDE_PLUGIN_ROOT"] = orig
            else:
                os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        self.assertFalse(written, "no people.md should be written without a template")
        self.assertIn("manually", msg.lower())
        self.assertFalse((self.target / "docs/memory/people.md").exists())


if __name__ == "__main__":
    unittest.main()
