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

class NewTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-new-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_auto_number_starts_at_0001(self):
        """Empty docs/decisions/ → first ADR numbered 0001."""
        result = run_adr("new", "first-decision", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        adr_path = self.adrs_dir / "adr-0001-first-decision.md"
        self.assertTrue(adr_path.is_file(), f"expected file not created: {adr_path}")

    def test_auto_number_increments(self):
        """Existing 0001, 0002 → next is 0003."""
        write_sample_adr(self.adrs_dir / "adr-0001-foo.md", "0001", "foo", "Foo")
        write_sample_adr(self.adrs_dir / "adr-0002-bar.md", "0002", "bar", "Bar")
        result = run_adr("new", "baz", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.adrs_dir / "adr-0003-baz.md").is_file())

    def test_auto_number_skips_gap_uses_max_plus_one(self):
        """Gap (0001, 0003) → next is 0004 (max + 1, no gap filling)."""
        write_sample_adr(self.adrs_dir / "adr-0001-foo.md", "0001", "foo", "Foo")
        write_sample_adr(self.adrs_dir / "adr-0003-baz.md", "0003", "baz", "Baz")
        result = run_adr("new", "qux", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.adrs_dir / "adr-0004-qux.md").is_file())
        self.assertFalse((self.adrs_dir / "adr-0002-qux.md").is_file())

    def test_boundary_auto_number(self):
        """Last existing ADR 0099 → next is 0100 (per DoD)."""
        write_sample_adr(self.adrs_dir / "adr-0099-old.md", "0099", "old", "Old")
        result = run_adr("new", "centenary", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertTrue((self.adrs_dir / "adr-0100-centenary.md").is_file())

    def test_slug_collision_refused(self):
        """Existing NNNN-<slug>.md with any number → refuse new <slug> with exit 2."""
        write_sample_adr(self.adrs_dir / "adr-0001-taken.md", "0001", "taken", "Taken")
        result = run_adr("new", "taken", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout} stderr: {result.stderr}")
        self.assertIn("slug", result.stderr.lower())

    def test_readme_excluded_from_numbering(self):
        """README.md must NOT be counted as an ADR for numbering."""
        # README already exists from setUp
        result = run_adr("new", "first", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        # Must be 0001, not numbered by counting README.
        self.assertTrue((self.adrs_dir / "adr-0001-first.md").is_file())

    def test_default_title_title_cased_from_slug(self):
        """Slug `my-decision` → default title `My Decision`."""
        result = run_adr("new", "my-decision", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0001-my-decision.md").read_text()
        self.assertIn("# ADR-0001: My Decision", content)

    def test_explicit_title_used(self):
        """--title overrides the default title-cased slug."""
        result = run_adr("new", "thing", "--title", "Custom Title Here",
                         cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0001-thing.md").read_text()
        self.assertIn("# ADR-0001: Custom Title Here", content)

    def test_file_has_all_six_sections_in_order(self):
        """All six sections present, in the canonical order."""
        result = run_adr("new", "ordered", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
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
        result = run_adr("new", "dated", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        content = (self.adrs_dir / "adr-0001-dated.md").read_text()
        self.assertIn(f"Proposed ({TODAY})", content)

    def test_prints_created_path_to_stdout(self):
        """The created path is printed to stdout. Exit 0."""
        result = run_adr("new", "printable", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("adr-0001-printable.md", result.stdout)


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


if __name__ == "__main__":
    unittest.main()
