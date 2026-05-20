"""
AC verification tests for slice 005-01 (adr-helper).

Run from the repo root:
    python3 skills/adr-workflow/test_adr.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_PY = REPO_ROOT / "skills" / "adr-workflow" / "adr.py"
SKILL_MD = REPO_ROOT / "skills" / "adr-workflow" / "SKILL.md"
TEMPLATE = (
    REPO_ROOT / "templates" / "docs" / "decisions" / "adr-0000-template.md"
)

TODAY = date.today().strftime("%Y-%m-%d")


def _import_adr_module():
    """Load adr.py as a module (the skill dir has a hyphen so we can't
    use plain `import`). Used by unit-level tests that need to call
    internal helpers directly.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("adr", ADR_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_adr(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(ADR_PY), *args],
        capture_output=True, text=True, env=env,
        cwd=str(cwd) if cwd else None,
    )


def write_sample_adr(path: Path, number: str, slug: str, title: str,
                     status: str = "Accepted",
                     context: str = "Sample context paragraph for the ADR.") -> None:
    """Write an ADR file with the standard skeleton at `path`."""
    path.write_text(
        f"# ADR-{number}: {title}\n\n"
        f"## Status\n\n{status} ({TODAY})\n\n"
        f"## Context\n\n{context}\n\n"
        f"## Decision Options Considered\n\n_TODO_\n\n"
        f"## Recommended Decision\n\n_TODO_\n\n"
        f"## Consequences\n\n_TODO_\n\n"
        f"## Open questions\n\nNone.\n"
    )


def write_sample_readme(path: Path) -> None:
    """Write a docs/decisions/README.md with the canonical jig sections."""
    path.write_text(
        "# Decisions\n\n"
        "> Architectural Decision Records. Nygard convention: immutable after acceptance.\n"
        "> New decisions supersede old ones — never edit an accepted ADR.\n\n"
        "## Index\n\n"
        "_No ADRs yet._\n\n"
        "## Format\n\n"
        "Each ADR lives at `docs/decisions/adr-NNNN-<slug>.md`. "
        "Title: `# ADR-NNNN: <Title>`.\n\n"
        "Required sections: Status, Context, Decision Options Considered, Recommended Decision, Consequences.\n\n"
        "## When to write an ADR\n\n"
        "- Hard-to-reverse decisions\n"
        "- Decisions that affect multiple modules or the public API\n"
    )


def write_refinement_todo(path: Path) -> None:
    """Sample refinement-todo.md mirroring the real one's shape, including a
    pre-resolved entry to exercise the 'already struck through' refusal."""
    path.write_text(
        "> Decisions the initial setup explicitly deferred.\n\n"
        "# Refinement Todo: sample\n\n"
        "## Architecture\n\n"
        "### Decision: Hook strictness profiles\n"
        "**Deferred:** Shipping an unread env var creates false expectations.\n"
        "**Resolution trigger:** First spec that touches hook enforcement.\n\n"
        "### Decision: SubagentStart hook event\n"
        "**Deferred:** Documented in changelog but absent from official docs.\n"
        "**Resolution trigger:** First time we need to react to subagent start.\n\n"
        "## Operations\n\n"
        "### ~~Decision: scaffold-stable ADR trigger~~ — RESOLVED 2026-05-12\n"
        "~~**Deferred:** The mechanism to flip docs from `Draft` to `Stable` is described but not implemented.~~\n"
        "**Resolved by:** [ADR-0001: scaffold-stable trigger]"
        "(decisions/adr-0001-scaffold-stable.md).\n\n"
        "### Decision: Scaffold.json manifest format\n"
        "**Deferred:** The schema is undefined.\n"
        "**Resolution trigger:** Slice 001-01 implementer defines schema.\n"
    )


# ---------- NewTests (AC #1, #6) ----------
#
# Slice 005-01 originally exercised `python adr.py new ...` as a real
# subprocess against a real temp git repo. Slice 028-01 added `git commit`
# inside `reserve_adr` — which broke this approach on CI runners with no
# global git identity. Migrated to the `_SubprocessRecorder` pattern
# (mirrors `ReserveAdrTests` below and `ReserveSpecTests` in
# spec-workflow), so no real git is ever invoked. File-shape contracts
# are still pinned; environmental coupling is gone.


def _git_init_on_main(repo_dir: Path) -> None:
    """Initialize a fresh git repo on branch `main` with one empty commit.

    Only used by `ReserveAdrCLITests` (the end-to-end CLI suite that does
    NOT mock subprocess). Identity is provided via env vars rather than
    relying on global `~/.gitconfig` so the helper works on CI runners
    with no global identity configured."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.invalid"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.invalid"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo_dir)],
                   env=env, check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo_dir), "commit",
                    "--allow-empty", "-q", "-m", "init"],
                   env=env, check=True, capture_output=True)


class NewTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-new-")
        self.target = Path(self.tmpdir)
        self.adrs_dir = self.target / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stub_preflight_ok(self, rec: "_SubprocessRecorder") -> None:
        """Stub the three git calls that `_preflight_branch_and_worktree`
        + the slug/preflight chain make: branch == main, clean worktree,
        origin URL on github.com. Mirrors `ReserveAdrTests._stub_preflight_ok`."""
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")

    def _reserve(self, slug: str, title: str = "") -> int:
        """Run `reserve_adr` in-process with all git calls stubbed. Returns
        the exit code; raises AdrError for refusals (collision, bad slug,
        preflight failures)."""
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            return _adr_mod.reserve_adr(
                slug, project_dir=self.target, title=title,
                no_push=True, pr_mode=False,
            )

    def test_auto_number_starts_at_0001(self):
        """Empty docs/decisions/ → first ADR numbered 0001."""
        code = self._reserve("first-decision")
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0001-first-decision.md").is_file())

    def test_auto_number_increments(self):
        """Existing 0001, 0002 → next is 0003."""
        write_sample_adr(self.adrs_dir / "adr-0001-foo.md", "0001", "foo", "Foo")
        write_sample_adr(self.adrs_dir / "adr-0002-bar.md", "0002", "bar", "Bar")
        code = self._reserve("baz")
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0003-baz.md").is_file())

    def test_auto_number_skips_gap_uses_max_plus_one(self):
        """Gap (0001, 0003) → next is 0004 (max + 1, no gap filling)."""
        write_sample_adr(self.adrs_dir / "adr-0001-foo.md", "0001", "foo", "Foo")
        write_sample_adr(self.adrs_dir / "adr-0003-baz.md", "0003", "baz", "Baz")
        code = self._reserve("qux")
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0004-qux.md").is_file())
        self.assertFalse((self.adrs_dir / "adr-0002-qux.md").is_file())

    def test_boundary_auto_number(self):
        """Last existing ADR 0099 → next is 0100 (per DoD)."""
        write_sample_adr(self.adrs_dir / "adr-0099-old.md", "0099", "old", "Old")
        code = self._reserve("centenary")
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0100-centenary.md").is_file())

    def test_slug_collision_refused(self):
        """Existing NNNN-<slug>.md with any number → AdrError (CLI: exit 2)."""
        write_sample_adr(self.adrs_dir / "adr-0001-taken.md", "0001", "taken", "Taken")
        with self.assertRaises(_adr_mod.AdrError) as ctx:
            self._reserve("taken")
        self.assertIn("slug", str(ctx.exception).lower())

    def test_readme_excluded_from_numbering(self):
        """README.md must NOT be counted as an ADR for numbering."""
        # README already exists from setUp
        code = self._reserve("first")
        self.assertEqual(code, 0)
        # Must be 0001, not numbered by counting README.
        self.assertTrue((self.adrs_dir / "adr-0001-first.md").is_file())

    def test_default_title_title_cased_from_slug(self):
        """Slug `my-decision` → default title `My Decision`."""
        code = self._reserve("my-decision")
        self.assertEqual(code, 0)
        content = (self.adrs_dir / "adr-0001-my-decision.md").read_text()
        self.assertIn("# ADR-0001: My Decision", content)

    def test_explicit_title_used(self):
        """--title overrides the default title-cased slug."""
        code = self._reserve("thing", title="Custom Title Here")
        self.assertEqual(code, 0)
        content = (self.adrs_dir / "adr-0001-thing.md").read_text()
        self.assertIn("# ADR-0001: Custom Title Here", content)

    def test_file_has_all_six_sections_in_order(self):
        """All six sections present, in the canonical order."""
        code = self._reserve("ordered")
        self.assertEqual(code, 0)
        content = (self.adrs_dir / "adr-0001-ordered.md").read_text()
        positions = [
            content.index("# ADR-0001:"),
            content.index("## Status"),
            content.index("## Context"),
            content.index("## Decision Options Considered"),
            content.index("## Recommended Decision"),
            content.index("## Consequences"),
            content.index("## Open questions"),
        ]
        self.assertEqual(positions, sorted(positions),
                         "sections must be in the canonical order")

    def test_status_body_is_proposed_today(self):
        """Status body is 'Proposed (YYYY-MM-DD)' with today's date."""
        code = self._reserve("dated")
        self.assertEqual(code, 0)
        content = (self.adrs_dir / "adr-0001-dated.md").read_text()
        self.assertIn(f"Proposed ({TODAY})", content)

    def test_prints_created_path_to_stdout(self):
        """The created path is printed to stdout."""
        import contextlib
        import io
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        buf = io.StringIO()
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with contextlib.redirect_stdout(buf):
                code = _adr_mod.reserve_adr(
                    "printable", project_dir=self.target, title="",
                    no_push=True, pr_mode=False,
                )
        self.assertEqual(code, 0)
        self.assertIn("adr-0001-printable.md", buf.getvalue())


# ---------- AcceptTests (AC #2) ----------

class AcceptTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-accept-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")
        # Proposed ADR seed.
        write_sample_adr(self.adrs_dir / "adr-0001-proposed-thing.md",
                         "0001", "proposed-thing", "Proposed Thing",
                         status="Proposed")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_accept_flips_status(self):
        """Happy path: Proposed → Accepted with today's date."""
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0001-proposed-thing.md").read_text()
        self.assertIn(f"Accepted ({TODAY})", content)
        self.assertNotIn(f"Proposed ({TODAY})", content)

    def test_accept_missing_adr_refused(self):
        """No ADR with that NNNN → exit 2."""
        result = run_adr("accept", "9999", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout}")
        self.assertIn("not found", result.stderr.lower())

    def test_accept_ambiguous_prefix_refused(self):
        """Multiple ADRs with the same NNNN-prefix is impossible by filename
        rules, but we still check the helper's defensive refusal: two files
        sharing the prefix bytes (extra-suffix copy) must produce exit 2."""
        # Create a second file with the same 0001 prefix; the prefix-match
        # scan should see both and refuse.
        write_sample_adr(self.adrs_dir / "adr-0001-duplicate-clone.md",
                         "0001", "duplicate-clone", "Dup Clone",
                         status="Proposed")
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambig", result.stderr.lower())

    def test_accept_already_accepted_refused(self):
        """Status is already Accepted → exit 2."""
        # First accept succeeds
        run_adr("accept", "0001", cwd=Path(self.tmpdir))
        # Second accept should refuse
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("proposed", result.stderr.lower())

    def test_accept_writes_atomically(self):
        """Accept leaves no stray .tmp file behind."""
        run_adr("accept", "0001", cwd=Path(self.tmpdir))
        stragglers = list(self.adrs_dir.glob("*.tmp"))
        self.assertEqual(stragglers, [], f"stray tmp files: {stragglers}")

    def test_accept_preserves_section_separator(self):
        """The blank line between Status and the next H2 must survive.
        Regression guard: a previous `\\s*$` regex ate the trailing newline
        and glued `Accepted (date)` directly to `## Decision Options...`."""
        run_adr("accept", "0001", cwd=Path(self.tmpdir))
        content = (self.adrs_dir / "adr-0001-proposed-thing.md").read_text()
        # Status body line must be on its own line; next section must follow a
        # blank line, not be glued.
        self.assertRegex(
            content,
            rf"Accepted \({TODAY}\)\n\n## Context",
        )

    def test_accept_prints_path_to_stdout(self):
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("adr-0001-proposed-thing.md", result.stdout)

    def test_accept_writes_last_verified_frontmatter(self):
        """Slice 014-01: accept stamps `last_verified: <today>` in frontmatter."""
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0001-proposed-thing.md").read_text()
        self.assertTrue(content.startswith("---\n"),
                        "frontmatter block must lead the file after accept")
        self.assertIn(f"last_verified: {TODAY}", content)
        # Title still intact below the block
        self.assertIn("# ADR-0001:", content)

    def test_accept_updates_existing_last_verified(self):
        """Re-accepting an ADR that already has stale last_verified updates it."""
        # Seed an existing frontmatter with old last_verified
        adr_path = self.adrs_dir / "adr-0001-proposed-thing.md"
        original = adr_path.read_text()
        adr_path.write_text(
            "---\nlast_verified: 2020-01-01\n---\n" + original
        )
        # Accept normally
        result = run_adr("accept", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = adr_path.read_text()
        self.assertIn(f"last_verified: {TODAY}", content)
        self.assertNotIn("last_verified: 2020-01-01", content)


# ---------- IndexTests (AC #3) ----------

class IndexTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-index-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_index_empty_when_no_adrs(self):
        """README has only its existing _No ADRs yet._ placeholder; index regen
        produces an empty index region (no entries) but does not crash."""
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "README.md").read_text()
        # No ADR bullet lines.
        self.assertNotRegex(content, r"-\s+\[ADR-\d{4}:")

    def test_index_regen_two_adrs_sorted(self):
        """Two ADRs → two entries, sorted ascending by NNNN."""
        write_sample_adr(self.adrs_dir / "adr-0002-beta.md", "0002", "beta", "Beta",
                         context="Beta does a thing.")
        write_sample_adr(self.adrs_dir / "adr-0001-alpha.md", "0001", "alpha", "Alpha",
                         context="Alpha does another thing.")
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "README.md").read_text()
        a = content.find("ADR-0001: Alpha")
        b = content.find("ADR-0002: Beta")
        self.assertGreater(a, 0)
        self.assertGreater(b, 0)
        self.assertLess(a, b, "ADRs must appear sorted by NNNN")

    def test_index_emits_canonical_bullet_format(self):
        """Bullet line: `- [ADR-NNNN: <Title>](NNNN-<slug>.md) — <desc> (<date>, <Status>)`."""
        write_sample_adr(self.adrs_dir / "adr-0001-alpha.md", "0001", "alpha", "Alpha",
                         status="Accepted", context="Alpha context one-liner.")
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        content = (self.adrs_dir / "README.md").read_text()
        self.assertIn(
            f"- [ADR-0001: Alpha](adr-0001-alpha.md) — Alpha context one-liner. ({TODAY}, Accepted)",
            content,
        )

    def test_index_idempotent(self):
        """Re-running on a current README produces byte-identical output."""
        write_sample_adr(self.adrs_dir / "adr-0001-alpha.md", "0001", "alpha", "Alpha",
                         context="Alpha context.")
        run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        first = (self.adrs_dir / "README.md").read_text()
        run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        second = (self.adrs_dir / "README.md").read_text()
        self.assertEqual(first, second, "index regen must be idempotent")

    def test_index_preserves_outside_content(self):
        """Header, Format, When-to-write sections must survive regen."""
        write_sample_adr(self.adrs_dir / "adr-0001-alpha.md", "0001", "alpha", "Alpha")
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        content = (self.adrs_dir / "README.md").read_text()
        self.assertIn("# Decisions", content)
        self.assertIn("## Format", content)
        self.assertIn("## When to write an ADR", content)
        self.assertIn("Hard-to-reverse decisions", content)

    def test_index_truncates_long_description(self):
        """First Context paragraph >120 chars or multi-line truncates at first
        sentence-ending punctuation."""
        long_ctx = (
            "ADR-0001's first sentence ends here. Then another sentence "
            "that should not appear in the index line because we truncate at the first period."
        )
        write_sample_adr(self.adrs_dir / "adr-0001-longctx.md", "0001", "longctx", "LongCtx",
                         context=long_ctx)
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        content = (self.adrs_dir / "README.md").read_text()
        self.assertIn("ADR-0001's first sentence ends here.", content)
        self.assertNotIn("another sentence that should not appear", content)

    def test_index_refuses_missing_index_heading(self):
        """README without `## Index` → exit 2."""
        bad = self.adrs_dir / "README.md"
        bad.write_text("# ADRs\n\nNo index heading.\n")
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("index", result.stderr.lower())

    def test_index_handles_real_adrs_in_repo(self):
        """Realism check: real jig ADRs (0001, 0002) produce a clean line each.
        Read them from the repo and synthesize a sandbox to regen against."""
        real_dir = REPO_ROOT / "docs" / "decisions"
        if not (real_dir / "adr-0001-scaffold-stable.md").is_file():
            self.skipTest("real ADR-0001 not present; skipping realism check")
        # Copy real ADRs + a synthesized README into sandbox.
        shutil.copy(real_dir / "adr-0001-scaffold-stable.md", self.adrs_dir)
        shutil.copy(real_dir / "adr-0002-contracts-stays-deferred.md",
                    self.adrs_dir)
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "README.md").read_text()
        # Two bullet lines, one per real ADR.
        bullets = [l for l in content.splitlines()
                   if re.match(r"^- \[ADR-\d{4}:", l)]
        self.assertEqual(len(bullets), 2,
                         f"expected exactly 2 bullets; got {bullets}")
        # Each bullet stays under a sane width.
        for b in bullets:
            self.assertLess(len(b), 400, f"bullet too long: {b}")


# ---------- ResolveTodoTests (AC #4) ----------

class ResolveTodoTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-resolve-")
        self.docs = Path(self.tmpdir) / "docs"
        self.adrs_dir = self.docs / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")
        # Accepted ADR for happy path.
        write_sample_adr(self.adrs_dir / "adr-0001-hooks.md", "0001", "hooks", "Hooks Decision",
                         status="Accepted")
        # Proposed ADR for not-accepted refusal.
        write_sample_adr(self.adrs_dir / "adr-0002-proposed.md", "0002", "proposed", "Proposed",
                         status="Proposed")
        self.todo = self.docs / "refinement-todo.md"
        write_refinement_todo(self.todo)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_resolve_strikes_heading_and_appends_resolved_by(self):
        """Heading wrapped in ~~~~ + ' — RESOLVED YYYY-MM-DD'; Resolved-by line appended."""
        result = run_adr("resolve-todo", "0001", "Hook strictness",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self.todo.read_text()
        self.assertIn(
            f"### ~~Decision: Hook strictness profiles~~ — RESOLVED {TODAY}",
            content,
        )
        self.assertIn(
            "**Resolved by:** [ADR-0001: Hooks Decision](decisions/adr-0001-hooks.md).",
            content,
        )

    def test_resolve_strikes_first_deferred_line(self):
        """The first **Deferred:** line in the section body is wrapped in ~~~~."""
        result = run_adr("resolve-todo", "0001", "Hook strictness",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        content = self.todo.read_text()
        # Look for the wrapped deferred line inside the Hook strictness section.
        section_pattern = re.compile(
            r"### ~~Decision: Hook strictness profiles.*?(?=\n###|\n##|\Z)",
            re.DOTALL,
        )
        m = section_pattern.search(content)
        self.assertIsNotNone(m, "wrapped section not found")
        self.assertIn("~~**Deferred:**", m.group(0))

    def test_resolve_substring_match(self):
        """Case-insensitive substring match against heading text."""
        result = run_adr("resolve-todo", "0001", "subagentstart",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = self.todo.read_text()
        self.assertIn("### ~~Decision: SubagentStart hook event~~", content)

    def test_resolve_zero_matches_refused(self):
        """No matching fragment → exit 2."""
        result = run_adr("resolve-todo", "0001", "nonexistent-thing",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_resolve_multiple_matches_refused(self):
        """Fragment matching multiple sections → exit 2."""
        # 'Decision' is in every heading
        result = run_adr("resolve-todo", "0001", "Decision",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambig", result.stderr.lower())

    def test_resolve_refuses_if_adr_not_accepted(self):
        """resolve-todo against an ADR still in Proposed state → exit 2."""
        result = run_adr("resolve-todo", "0002", "Hook strictness",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("accepted", result.stderr.lower())

    def test_resolve_refuses_already_struck_through(self):
        """Section heading already wrapped in ~~~~ → exit 2."""
        result = run_adr("resolve-todo", "0001", "scaffold-stable",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("struck", result.stderr.lower() + result.stdout.lower())

    def test_resolve_refuses_missing_todo_file(self):
        """No refinement-todo.md → exit 2."""
        self.todo.unlink()
        result = run_adr("resolve-todo", "0001", "Hook strictness",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("refinement-todo", result.stderr.lower())

    def test_resolve_writes_atomically(self):
        """No stray .tmp file behind."""
        run_adr("resolve-todo", "0001", "Hook strictness",
                cwd=Path(self.tmpdir))
        stragglers = list(self.docs.glob("*.tmp"))
        self.assertEqual(stragglers, [], f"stray tmp files: {stragglers}")

    def test_resolve_prints_path_to_stdout(self):
        result = run_adr("resolve-todo", "0001", "Hook strictness",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("refinement-todo.md", result.stdout)


# ---------- SkillSurfaceTests (AC #5, #6) ----------

class SkillSurfaceTests(unittest.TestCase):

    def setUp(self):
        self.assertTrue(SKILL_MD.is_file(), f"SKILL.md missing: {SKILL_MD}")
        self.skill = SKILL_MD.read_text()

    def test_skill_has_frontmatter(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have frontmatter")

    def test_skill_frontmatter_has_no_disable_invocation(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "adr-workflow must auto-trigger (frontmatter active)")

    def test_skill_is_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        self.assertNotIn("user-invocable: false", fm)

    def test_skill_description_has_trigger_phrases(self):
        """Description must include 'ADR', 'decision', 'resolve', 'supersede'."""
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1).lower()
        for phrase in ("adr", "decision", "resolve", "supersede"):
            self.assertIn(phrase, fm,
                          f"description must mention '{phrase}' to auto-trigger correctly")

    def test_skill_body_references_all_four_subcommands(self):
        body_lower = self.skill.lower()
        for sub in ("new", "accept", "index", "resolve-todo"):
            self.assertIn(sub, body_lower,
                          f"SKILL.md body must mention `{sub}` subcommand")

    def test_skill_body_has_gotchas_section(self):
        self.assertRegex(self.skill, r"(?im)^##\s+Gotchas",
                         "SKILL.md must have a Gotchas section")

    def test_skill_body_mentions_immutability(self):
        """Per AC #5: 'Immutability rule (no editing accepted ADRs — supersede instead)'."""
        self.assertRegex(
            self.skill,
            r"(?i)immutab|supersede",
            "SKILL.md must document the immutability rule",
        )

    def test_template_exists(self):
        self.assertTrue(TEMPLATE.is_file(), f"template missing: {TEMPLATE}")

    def test_template_has_placeholders(self):
        content = TEMPLATE.read_text()
        for ph in ("{{NUMBER}}", "{{TITLE}}", "{{DATE}}"):
            self.assertIn(ph, content, f"template missing placeholder {ph}")

    def test_template_has_all_six_sections(self):
        content = TEMPLATE.read_text()
        for header in (
            "# ADR-{{NUMBER}}: {{TITLE}}",
            "## Status",
            "## Context",
            "## Decision Options Considered",
            "## Recommended Decision",
            "## Consequences",
            "## Open questions",
        ):
            self.assertIn(header, content,
                          f"template missing section header: {header}")


# ---------- Inbox 2026-05-12: abbreviation handling in _extract_description ----

class ExtractDescriptionAbbreviationTests(unittest.TestCase):
    """The Context-paragraph sentence-end detector must skip common
    abbreviations (`e.g.`, `i.e.`, `etc.`, `Mr.`, …) so the index entry
    doesn't get cut mid-abbreviation. First hit: ADR-0004 produced
    `... files as NNNN-<slug>.md (e.g.` — truncated after the period in
    `e.g.`. Fix: explicit allowlist of abbreviations.
    """

    def setUp(self):
        self.adr = _import_adr_module()

    def _ctx(self, paragraph: str) -> str:
        # Wrap the paragraph in a minimal valid ADR so the detector runs
        # exactly the path it would for a real file.
        return (
            "# ADR-0099: Sample\n\n## Status\n\nAccepted\n\n"
            f"## Context\n\n{paragraph}\n\n## Decision Options Considered\n\n_TODO_\n"
        )

    def _force_truncate(self, paragraph: str) -> str:
        """The detector only kicks in when multi-line OR > 120 chars.
        Pad the paragraph so truncation is guaranteed."""
        if len(paragraph) <= 120:
            paragraph = paragraph + " " + ("X" * (130 - len(paragraph)))
        return self.adr._extract_description(self._ctx(paragraph))

    def test_eg_not_treated_as_sentence_boundary(self):
        """The ADR-0004 incident: a Context para that contains `e.g.` early
        on must NOT truncate at the period inside `e.g.`."""
        para = (
            "Decision records live at `docs/decisions/` with filenames like "
            "`adr-NNNN-<slug>.md` (e.g. `adr-0004-decisions-folder-naming.md`)."
        )
        # First force a multi-line scenario so the truncator runs.
        out = self.adr._extract_description(self._ctx(para + "\n\nMore here."))
        # The bug would cut at `(e.g.` — make sure we never see that.
        self.assertNotIn("(e.g.…", out, f"out={out!r}")
        self.assertFalse(out.endswith("(e.g."), f"out={out!r}")
        # And the full first real sentence should survive.
        self.assertTrue(
            out.endswith(".md`)."),
            f"expected the full first sentence; got {out!r}",
        )

    def test_ie_not_treated_as_sentence_boundary(self):
        para = (
            "We use semantic versioning, i.e. major.minor.patch, with strict "
            "rules about backwards compatibility for shipped APIs."
        )
        out = self._force_truncate(para)
        self.assertFalse(out.endswith("i.e."), f"out={out!r}")

    def test_etc_not_treated_as_sentence_boundary(self):
        para = (
            "Supported runners include pytest, vitest, jest, etc. The "
            "auto-detector picks one based on `package.json` and friends."
        )
        out = self._force_truncate(para)
        # Should NOT end at `etc.` — should continue to the next real boundary.
        self.assertFalse(out.endswith("etc."), f"out={out!r}")

    def test_real_sentence_after_abbreviation_still_terminates(self):
        """After an abbreviation, a real sentence boundary still wins."""
        para = (
            "Migrations sometimes touch packaging concerns, e.g. lockfiles "
            "and CI configs. Subsequent runs use the cached layout instead."
        )
        out = self._force_truncate(para)
        self.assertTrue(
            out.endswith("CI configs."),
            f"expected truncation at the real boundary; got {out!r}",
        )

    def test_normal_sentence_still_truncates(self):
        """Regression — sentences without abbreviations still cut at the
        first period that's followed by space."""
        para = (
            "Plain first sentence ends here. Then a second sentence that "
            "should NOT appear in the index line after truncation."
        )
        out = self._force_truncate(para)
        self.assertTrue(out.endswith("here."), f"out={out!r}")
        self.assertNotIn("second sentence", out)

    def test_abbreviation_at_paragraph_start_does_not_break(self):
        """An abbreviation as the very first token shouldn't crash the
        look-back (boundary safety on `before_idx < 0`)."""
        para = (
            "E.g. consider the case where every detector contradicts the "
            "headline rule and produces a divergent suggestion downstream."
        )
        # No crash + something sensible comes back.
        out = self._force_truncate(para)
        # The capitalized `E.g.` is the same shape as `e.g.` but starts the
        # paragraph; case-sensitive match means it WILL truncate after the
        # second period. That's acceptable — the test is just "no crash."
        self.assertIsInstance(out, str)

    def test_mr_and_dr_titles_not_sentence_boundaries(self):
        para = (
            "The migration was reviewed by Dr. Foo and Mr. Bar before the "
            "team reached consensus on the final shape of the helper."
        )
        out = self._force_truncate(para)
        self.assertFalse(out.endswith("Dr."), f"out={out!r}")
        self.assertFalse(out.endswith("Mr."), f"out={out!r}")


# ---------- ReserveAdrTests (slice 028-01) ----------
#
# These tests mirror the shape of skills/spec-workflow/test_workflow.py's
# ReserveSpecTests class (slice 003-03). The reserve-on-main flow inside
# adr.py is an inline-mirror of workflow.py's reserve_spec per ADR-0003
# (two callers; extract when a third caller emerges).

_adr_mod = _import_adr_module()


class _SubprocessRecorder:
    """Captures subprocess.run calls and returns canned results based on
    a sequence of (matcher, returncode, stdout, stderr) tuples.

    Mirrors the recorder in skills/spec-workflow/test_workflow.py. Each
    call consumes the first matching tuple (FIFO). Unmatched calls return
    a benign (rc=0, stdout="", stderr="") proc."""

    def __init__(self):
        self.calls = []
        self._responses = []

    def stub(self, matcher, returncode=0, stdout="", stderr=""):
        self._responses.append((matcher, returncode, stdout, stderr))
        return self

    def __call__(self, *args, **kwargs):
        argv = args[0] if args else kwargs.get("args")
        if isinstance(argv, str):
            argv_list = argv.split()
        else:
            argv_list = list(argv)
        self.calls.append(argv_list)
        for i, (matcher, rc, out, err) in enumerate(self._responses):
            if matcher(argv_list):
                self._responses.pop(i)
                return _make_proc(rc, out, err)
        return _make_proc(0, "", "")

    def argv_log(self):
        return [" ".join(a) for a in self.calls]


def _make_proc(returncode: int, stdout: str = "", stderr: str = ""):
    from unittest.mock import MagicMock
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def _matches(*prefix_tokens):
    def _m(argv):
        return tuple(argv[: len(prefix_tokens)]) == tuple(prefix_tokens)
    return _m


class ReserveAdrTests(unittest.TestCase):
    """Slice 028-01: `adr.py new <slug>` reserves the next free ADR
    number on origin/main, mirroring `workflow.py new`."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-reserve-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()
        # Scaffold the docs/decisions/ surface — the reserve flow refuses
        # if it's absent (parity with workflow.py docs/specs/ guard).
        self.adrs_dir = self.target / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed_adr(self, number: str, slug: str, title: str = None) -> None:
        title = title or _adr_mod._slug_to_title(slug)
        write_sample_adr(self.adrs_dir / f"adr-{number}-{slug}.md",
                         number, slug, title)

    def _stub_preflight_ok(self, rec: _SubprocessRecorder,
                           dirty: bool = False) -> None:
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0,
                 stdout=("M somefile\n" if dirty else ""))
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")

    # AC #1 + AC #3 + AC #5 — happy path with --no-push; verify
    # stub contents and commit semantics without any remote calls.
    def test_new_reserves_next_number_and_writes_stub(self):
        """AC #1: reserves next free NNNN; AC #3: --no-push skips remote."""
        self._seed_adr("0001", "first")
        self._seed_adr("0015", "another")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "new-decision", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        adr_path = self.adrs_dir / "adr-0016-new-decision.md"
        self.assertTrue(adr_path.is_file(), f"missing: {adr_path}")
        content = adr_path.read_text()
        # Title-cased default
        self.assertIn("# ADR-0016: New Decision", content)
        # Proposed status with today's date
        self.assertIn(f"Proposed ({TODAY})", content)
        # Canonical commit message
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("docs(decisions): reserve adr-0016-new-decision",
                      " ".join(commit_calls[0]))
        # --no-push: no fetch / push calls
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat)
        self.assertNotIn("git fetch", flat)

    # AC #1 — gap-tolerance: max + 1 across gaps.
    def test_new_uses_max_plus_one_across_gaps(self):
        self._seed_adr("0001", "x")
        self._seed_adr("0015", "y")
        self._seed_adr("0003", "z")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "newslot", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0016-newslot.md").is_file(),
                        f"expected 0016-newslot; got: "
                        f"{sorted(self.adrs_dir.iterdir())}")

    # AC #5 (pattern) — refuse on non-main branch.
    def test_new_refuses_on_non_main_branch(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/foo\n")
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "myslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("main", msg)
        # No file created
        self.assertFalse(any(self.adrs_dir.glob("*-myslug.md")))

    # AC #5 (pattern) — refuse on dirty worktree.
    def test_new_refuses_on_dirty_worktree(self):
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec, dirty=True)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "myslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertTrue("dirty" in msg or "uncommitted" in msg or "clean" in msg,
                        f"unexpected: {ctx.exception!r}")
        self.assertFalse(any(self.adrs_dir.glob("*-myslug.md")))

    # Bad slug refuses BEFORE any git invocation (parity with workflow.py).
    # Re-uses the existing adr.py slug regex which accepts a leading digit
    # (design note: don't tighten to workflow.py's stricter regex).
    def test_new_refuses_on_bad_slug_before_git(self):
        # NOTE: adr.py's slug regex (`^[a-z0-9][a-z0-9-]*$`) is
        # deliberately looser than workflow.py's stricter pattern: it
        # accepts a leading digit AND a trailing hyphen. Per the slice's
        # design notes, do NOT tighten — that would silently break any
        # existing ADR slug. Only test slugs that the existing regex
        # rejects.
        bad = ["BadSlug", "", "with space", "UPPER", "-leading"]
        for slug in bad:
            with self.subTest(slug=slug):
                rec = _SubprocessRecorder()
                from unittest.mock import patch
                with patch.object(_adr_mod, "subprocess") as sp_mod:
                    sp_mod.run = rec
                    with self.assertRaises(_adr_mod.AdrError) as ctx:
                        _adr_mod.reserve_adr(
                            slug, project_dir=self.target,
                            title="", no_push=True, pr_mode=False,
                        )
                msg = str(ctx.exception).lower()
                self.assertIn("slug", msg,
                              f"slug={slug!r}: error didn't name 'slug': "
                              f"{ctx.exception!r}")
                # No git was invoked
                self.assertEqual(rec.calls, [],
                                 f"slug={slug!r}: git invoked before slug check")

    def test_new_allows_slug_starting_with_digit(self):
        """adr.py's slug regex accepts a leading digit (don't tighten to
        workflow.py's stricter regex — would be a silent break)."""
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "2026-policy", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        self.assertTrue((self.adrs_dir / "adr-0001-2026-policy.md").is_file())

    # Refuse when docs/decisions/ absent (parity with workflow.py
    # missing-specs-dir refusal).
    def test_new_refuses_when_decisions_dir_absent(self):
        bare = Path(self.tmpdir) / "bare"
        bare.mkdir()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "validslug", project_dir=bare,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("docs/decisions", msg)

    # Slug-collision check fires AFTER fetch (so the collision view is
    # freshest) but BEFORE writing the new file.
    def test_new_refuses_on_slug_collision_post_fetch(self):
        self._seed_adr("0007", "taken")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "taken", project_dir=self.target,
                    title="", no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("slug", msg)
        # Fetch happened (proves the check is post-fetch)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git fetch", flat)
        # But no commit / push (collision short-circuits)
        self.assertNotIn("git commit", flat)
        self.assertNotIn("git push", flat)
        # No new file beyond the seed
        files = sorted(p.name for p in self.adrs_dir.glob("adr-*.md"))
        self.assertEqual(files, ["adr-0007-taken.md"])

    # AC #1 — default behavior: direct push to origin/main succeeds.
    def test_new_direct_push_succeeds(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "newslot", project_dir=self.target,
                title="", no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # No PR-fallback branches created
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # AC #2 — protected-branch stderr triggers PR fallback.
    def test_new_falls_back_on_protected_branch(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="remote: error: GH006: Protected branch update failed.\n")
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/99\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "newslot", project_dir=self.target,
                title="", no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git branch", flat)
        self.assertIn("git reset --hard origin/main", flat)
        self.assertIn("git checkout", flat)
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)
        # PR branch name follows the reserve/adr-NNNN-<slug> convention
        branch_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "branch"]
        self.assertTrue(any("reserve/adr-0002-newslot" in " ".join(c)
                            for c in branch_calls),
                        f"branch name: {branch_calls}")

    # AC #4 — non-fast-forward triggers race-detection (NOT PR fallback).
    def test_new_does_not_fall_back_on_non_fast_forward(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "newslot", project_dir=self.target,
                    title="", no_push=False, pr_mode=False,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("race", msg)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git reset --hard HEAD~1", flat)
        # No fallback branch / gh pr create
        self.assertNotIn("git branch reserve", flat)
        self.assertNotIn("gh pr create", flat)

    # Race recovery cleans up the stranded ADR file on disk so the
    # worktree stays tidy (parity with workflow.py's spec-dir cleanup).
    def test_new_race_recovery_removes_stranded_file(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "push", "origin", "main"),
                 returncode=1,
                 stderr="! [rejected]  main -> main (non-fast-forward)\n")
        # `git reset --hard HEAD~1` is mocked → worktree files NOT
        # rolled back; the helper must clean up its own write.
        rec.stub(_matches("git", "reset", "--hard", "HEAD~1"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError):
                _adr_mod.reserve_adr(
                    "newslot", project_dir=self.target,
                    title="", no_push=False, pr_mode=False,
                )
        stranded = self.adrs_dir / "adr-0002-newslot.md"
        self.assertFalse(
            stranded.exists(),
            f"race recovery left stranded ADR on disk: {stranded}",
        )

    # AC #3 — --pr skips direct push, goes straight to PR fallback.
    def test_new_pr_mode_skips_direct_push(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        rec.stub(_matches("git", "branch"), returncode=0)
        rec.stub(_matches("git", "reset", "--hard", "origin/main"),
                 returncode=0)
        rec.stub(_matches("git", "checkout"), returncode=0)
        rec.stub(_matches("git", "push", "-u", "origin"), returncode=0)
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/u/r/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "myslot", project_dir=self.target,
                title="", no_push=False, pr_mode=True,
            )
        self.assertEqual(code, 0)
        # No direct push to main
        push_main = [c for c in rec.calls
                     if tuple(c[:4]) == ("git", "push", "origin", "main")]
        self.assertEqual(push_main, [],
                         f"--pr should skip direct push; calls: "
                         f"{rec.argv_log()}")
        flat = " | ".join(rec.argv_log())
        self.assertIn("git push -u origin", flat)
        self.assertIn("gh pr create", flat)

    # AC #2 — PR fallback refuses without `gh` on PATH.
    def test_new_pr_mode_refuses_without_gh(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value=None):
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "myslot", project_dir=self.target,
                    title="", no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("gh", msg)

    # AC #2 — PR fallback refuses when origin isn't on github.com.
    def test_new_pr_mode_refuses_without_github_remote(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0,
                 stdout="git@gitlab.example.com:foo/bar.git\n")
        rec.stub(_matches("git", "fetch"), returncode=0)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/bin/gh"):
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "myslot", project_dir=self.target,
                    title="", no_push=False, pr_mode=True,
                )
        msg = str(ctx.exception).lower()
        self.assertIn("github.com", msg)

    # AC #3 — --no-push never calls fetch or push.
    def test_new_no_push_skips_remote_calls(self):
        self._seed_adr("0001", "existing")
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "soloslot", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git fetch", flat)
        self.assertNotIn("git push", flat)

    # AC #5 (CLI surface) — --no-push and --pr are mutually exclusive.
    def test_new_no_push_and_pr_are_mutually_exclusive(self):
        # argparse usage error → exit 2 from main()
        result = run_adr("new", "myslot", "--no-push", "--pr",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2,
                         f"stdout: {result.stdout} stderr: {result.stderr}")

    # --title override flows through reserve.
    def test_new_explicit_title_used_in_reserve(self):
        rec = _SubprocessRecorder()
        self._stub_preflight_ok(rec)
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "thing", project_dir=self.target,
                title="Custom Title Here", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        content = (self.adrs_dir / "adr-0001-thing.md").read_text()
        self.assertIn("# ADR-0001: Custom Title Here", content)


# ---------- ReserveAdrCLITests (CLI surface) ----------

class ReserveAdrCLITests(unittest.TestCase):
    """CLI surface tests for slice 028-01 — verify `--help` lists the new
    flags, and that the --no-push CLI path works end-to-end against a
    real git repo (no mocking)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-reserve-cli-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")
        _git_init_on_main(Path(self.tmpdir))
        env = {**os.environ,
               "GIT_AUTHOR_NAME": "Test",
               "GIT_AUTHOR_EMAIL": "test@example.invalid",
               "GIT_COMMITTER_NAME": "Test",
               "GIT_COMMITTER_EMAIL": "test@example.invalid"}
        subprocess.run(["git", "-C", self.tmpdir, "add", "-A"],
                       check=True, capture_output=True, env=env)
        subprocess.run(["git", "-C", self.tmpdir, "commit", "-q", "-m",
                        "scaffold"], check=True, capture_output=True,
                       env=env)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_help_shows_no_push_flag(self):
        result = run_adr("new", "--help")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("--no-push", result.stdout)

    def test_help_shows_pr_flag(self):
        result = run_adr("new", "--help")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("--pr", result.stdout)

    def test_help_shows_project_dir_flag(self):
        result = run_adr("new", "--help")
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("--project-dir", result.stdout)

    def test_cli_no_push_creates_file_and_commits(self):
        """End-to-end: --no-push commits locally, no remote interaction."""
        env = {**os.environ,
               "GIT_AUTHOR_NAME": "Test",
               "GIT_AUTHOR_EMAIL": "test@example.invalid",
               "GIT_COMMITTER_NAME": "Test",
               "GIT_COMMITTER_EMAIL": "test@example.invalid",
               "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)}
        result = subprocess.run(
            [sys.executable, str(ADR_PY), "new", "first", "--no-push"],
            capture_output=True, text=True, env=env, cwd=self.tmpdir,
        )
        self.assertEqual(result.returncode, 0,
                         f"stdout: {result.stdout} stderr: {result.stderr}")
        adr_path = self.adrs_dir / "adr-0001-first.md"
        self.assertTrue(adr_path.is_file())
        # The commit landed on local main with the canonical message.
        log = subprocess.run(
            ["git", "-C", self.tmpdir, "log", "-1", "--format=%s"],
            capture_output=True, text=True, env=env, check=True,
        )
        self.assertIn("docs(decisions): reserve adr-0001-first",
                      log.stdout)


if __name__ == "__main__":
    unittest.main()
