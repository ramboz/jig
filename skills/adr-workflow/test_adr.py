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
        "Required sections: Status, Context, Decision Options Considered, "
        "Recommended Decision, Consequences.\n\n"
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
        "~~**Deferred:** The mechanism to flip docs from `Draft` to `Stable` "
        "is described but not implemented.~~\n"
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
        # Spec 066-01: the reserve path classifies scaffold-state. Drop the
        # completion sentinel so these fixtures classify as `scaffolded` and
        # proceed through the legacy reserve flow unchanged.
        (self.target / "scaffold.json").write_text("{}\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stub_preflight_ok(self, rec: "_SubprocessRecorder") -> None:
        """Stub the three git calls that `_current_branch` / `_refuse_if_dirty`
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


# ---------- Slice 064-05: frame-critique stamp + accept gate ----------


def _write_proposed_adr_064(path: Path, number: str, slug: str, title: str,
                            *, frame_review: bool = False) -> None:
    """Proposed ADR seed for the gate tests. When `frame_review` is set, a
    leading frontmatter block carries `frame_review: true` (mirroring what
    `cmd_new` stamps); otherwise the file is markerless (legacy grace path)."""
    body = (
        f"# ADR-{number}: {title}\n\n"
        f"## Status\n\nProposed ({TODAY})\n\n"
        f"## Context\n\nSample.\n\n"
        f"## Decision Options Considered\n\n_TODO_\n\n"
        f"## Recommended Decision\n\n_TODO_\n\n"
        f"## Consequences\n\n_TODO_\n\n"
        f"## Open questions\n\nNone.\n"
    )
    if frame_review:
        body = "---\nframe_review: true\n---\n" + body
    path.write_text(body)


def _write_adr_frame_verdict(adrs_dir: Path, number: str,
                             verdict: str = "pass") -> None:
    reviews = adrs_dir / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    (reviews / f"adr-{number}-frame-critique.md").write_text(
        "---\n"
        f"adr: {number}\n"
        "pass: frame-critique\n"
        f"verdict: {verdict}\n"
        "reviewer: jig:reviewer\n"
        "reviewed_at: 2026-06-08T00:00:00Z\n"
        "prompt_source: review.py frame-critique x\n"
        "---\n\n## VERDICT\n" + verdict + "\n"
    )


class NewStampsFrameReviewTests(unittest.TestCase):
    """Slice 064-05 (OQ3 — ADRs always-on): cmd_new / reserve_adr stamp
    `frame_review: true` into the new ADR's frontmatter at creation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-stamp-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cmd_new_stamps_frame_review_true(self):
        mod = _import_adr_module()
        target = mod.cmd_new(self.adrs_dir, "stamped-decision", "")
        content = target.read_text()
        self.assertTrue(content.startswith("---\n"),
                        "frame_review must be stamped in a leading "
                        "frontmatter block")
        self.assertIn("frame_review: true", content)
        # Body intact below the block.
        self.assertIn("# ADR-", content)


class AcceptGateTests(unittest.TestCase):
    """Slice 064-05 AC #2/#3: `adr.py accept` gates the Proposed→Accepted
    flip on a passing frame-critique verdict for `frame_review: true` ADRs;
    bypassable via JIG_REVIEW_EVIDENCE_GATE=0; legacy markerless ADRs are
    not gated (grace path)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-gate-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _env_no_gate(self) -> dict:
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["JIG_REVIEW_EVIDENCE_GATE"] = "0"
        return env

    def test_gated_accept_refused_without_verdict(self):
        _write_proposed_adr_064(self.adrs_dir / "adr-0020-gated.md",
                                "0020", "gated", "Gated", frame_review=True)
        result = run_adr("accept", "0020", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout}")
        self.assertIn("adr-0020-frame-critique.md", result.stderr)
        self.assertIn("record-review", result.stderr)
        self.assertIn("--adr", result.stderr)
        # Status untouched — refusal happens before the flip.
        content = (self.adrs_dir / "adr-0020-gated.md").read_text()
        self.assertIn(f"Proposed ({TODAY})", content)

    def test_gated_accept_clears_with_passing_verdict(self):
        _write_proposed_adr_064(self.adrs_dir / "adr-0020-gated.md",
                                "0020", "gated", "Gated", frame_review=True)
        _write_adr_frame_verdict(self.adrs_dir, "0020", "pass")
        result = run_adr("accept", "0020", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0020-gated.md").read_text()
        self.assertIn(f"Accepted ({TODAY})", content)

    def test_gated_accept_refused_with_failing_verdict(self):
        _write_proposed_adr_064(self.adrs_dir / "adr-0020-gated.md",
                                "0020", "gated", "Gated", frame_review=True)
        _write_adr_frame_verdict(self.adrs_dir, "0020", "fail")
        result = run_adr("accept", "0020", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2, f"stdout: {result.stdout}")

    def test_bypass_via_env_var(self):
        _write_proposed_adr_064(self.adrs_dir / "adr-0020-gated.md",
                                "0020", "gated", "Gated", frame_review=True)
        result = subprocess.run(
            [sys.executable, str(ADR_PY), "accept", "0020"],
            capture_output=True, text=True, env=self._env_no_gate(),
            cwd=str(self.tmpdir),
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0020-gated.md").read_text()
        self.assertIn(f"Accepted ({TODAY})", content)

    def test_legacy_markerless_adr_accepts_freely(self):
        """Grace path: a pre-existing Proposed ADR WITHOUT frame_review is
        not gated — no false refusal."""
        _write_proposed_adr_064(self.adrs_dir / "adr-0007-legacy.md",
                                "0007", "legacy", "Legacy", frame_review=False)
        result = run_adr("accept", "0007", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "adr-0007-legacy.md").read_text()
        self.assertIn(f"Accepted ({TODAY})", content)


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
            f"- [ADR-0001: Alpha](adr-0001-alpha.md) — Alpha context one-liner. "
            f"({TODAY}, Accepted)",
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
        bullets = [ln for ln in content.splitlines()
                   if re.match(r"^- \[ADR-\d{4}:", ln)]
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


# ---------- SupersedeTests (slice 005-02 AC #1, #2) ----------


def _write_accepted_adr(path: Path, number: str, slug: str, title: str,
                        accepted_date: str = TODAY,
                        context: str = "Sample context paragraph for the ADR.") -> None:
    """Write a minimally-valid Accepted-state ADR for use in SupersedeTests.
    `write_sample_adr` defaults to `status="Accepted"` already, but spelling
    the intent out makes the test fixtures self-documenting."""
    path.write_text(
        f"# ADR-{number}: {title}\n\n"
        f"## Status\n\nAccepted ({accepted_date})\n\n"
        f"## Context\n\n{context}\n\n"
        f"## Decision Options Considered\n\n_TODO_\n\n"
        f"## Recommended Decision\n\n_TODO_\n\n"
        f"## Consequences\n\n_TODO_\n\n"
        f"## Open questions\n\nNone.\n"
    )


def _write_proposed_adr(path: Path, number: str, slug: str, title: str) -> None:
    """Write a Proposed-state ADR."""
    write_sample_adr(path, number, slug, title, status="Proposed")


def _write_superseded_adr(path: Path, number: str, slug: str, title: str,
                          new_number: str, new_slug: str,
                          accepted_date: str = "2026-01-01",
                          super_date: str = TODAY) -> None:
    """Write an ADR whose Status block has BOTH `Accepted (date)` and
    `Superseded by [ADR-NNNN](./adr-NNNN-<slug>.md) (date)` lines."""
    path.write_text(
        f"# ADR-{number}: {title}\n\n"
        f"## Status\n\n"
        f"Accepted ({accepted_date})\n"
        f"Superseded by [ADR-{new_number}]"
        f"(./adr-{new_number}-{new_slug}.md) ({super_date})\n\n"
        f"## Context\n\nSample context.\n\n"
        f"## Decision Options Considered\n\n_TODO_\n\n"
        f"## Recommended Decision\n\n_TODO_\n\n"
        f"## Consequences\n\n_TODO_\n\n"
        f"## Open questions\n\nNone.\n"
    )


class SupersedeTests(unittest.TestCase):
    """Slice 005-02 ACs #1 + #2: append supersession lines to both ADRs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-supersede-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")
        # Two Accepted ADRs by default.
        _write_accepted_adr(self.adrs_dir / "adr-0001-old.md",
                            "0001", "old", "Old Decision",
                            accepted_date="2026-01-01")
        _write_accepted_adr(self.adrs_dir / "adr-0002-new.md",
                            "0002", "new", "New Decision",
                            accepted_date=TODAY)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ---- AC #1: happy path ----

    def test_supersede_appends_to_old_status_with_link_and_today_date(self):
        """Old ADR's Status block gains:
        `Superseded by [ADR-NNNN](./adr-NNNN-<slug>.md) (TODAY)`."""
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        old = (self.adrs_dir / "adr-0001-old.md").read_text()
        self.assertIn(
            f"Superseded by [ADR-0002](./adr-0002-new.md) ({TODAY})",
            old,
        )

    def test_supersede_appends_to_new_status_plain_text(self):
        """New ADR's Status block gains: `Supersedes ADR-NNNN` (no link, no date)."""
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        new = (self.adrs_dir / "adr-0002-new.md").read_text()
        self.assertIn("Supersedes ADR-0001", new)
        # The text must NOT be a link or include a date.
        self.assertNotIn("Supersedes [ADR-0001]", new)
        self.assertNotIn(f"Supersedes ADR-0001 ({TODAY})", new)

    def test_supersede_preserves_old_accepted_line(self):
        """Old ADR keeps its `Accepted (date)` line."""
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        old = (self.adrs_dir / "adr-0001-old.md").read_text()
        self.assertIn("Accepted (2026-01-01)", old)

    def test_supersede_preserves_new_accepted_line(self):
        """New ADR keeps its `Accepted (date)` line."""
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        new = (self.adrs_dir / "adr-0002-new.md").read_text()
        self.assertIn(f"Accepted ({TODAY})", new)

    def test_supersede_preserves_section_separator(self):
        """The blank line between Status and the next H2 must survive.
        Regression guard mirroring AcceptTests.test_accept_preserves_section_separator."""
        run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        old = (self.adrs_dir / "adr-0001-old.md").read_text()
        # Old ADR's Status block must NOT be glued to ## Context.
        self.assertRegex(
            old,
            rf"Superseded by \[ADR-0002\]\(\./adr-0002-new\.md\) \({TODAY}\)\n\n## Context",
        )
        new = (self.adrs_dir / "adr-0002-new.md").read_text()
        self.assertRegex(
            new,
            r"Supersedes ADR-0001\n\n## Context",
        )

    def test_supersede_supersession_line_immediately_after_accepted_line(self):
        """Old ADR: the Superseded-by line comes right after Accepted (date)."""
        run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        old = (self.adrs_dir / "adr-0001-old.md").read_text()
        self.assertRegex(
            old,
            r"Accepted \(2026-01-01\)\nSuperseded by \[ADR-0002\]",
        )

    def test_supersede_prints_both_paths_to_stdout(self):
        """Both modified paths are printed to stdout (one per line)."""
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        self.assertIn("adr-0001-old.md", result.stdout)
        self.assertIn("adr-0002-new.md", result.stdout)

    def test_supersede_atomic_write_no_tmp_stragglers(self):
        """No stray .tmp file behind for either ADR."""
        run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        stragglers = list(self.adrs_dir.glob("*.tmp"))
        self.assertEqual(stragglers, [], f"stray tmp files: {stragglers}")

    # ---- AC #1: NNNN validation ----

    def test_supersede_refuses_malformed_old_number(self):
        """Old NNNN not 4-digit zero-padded → exit 2."""
        result = run_adr("supersede", "1", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("4-digit", result.stderr.lower())

    def test_supersede_refuses_malformed_new_number(self):
        """New NNNN not 4-digit zero-padded → exit 2."""
        result = run_adr("supersede", "0001", "abc", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("4-digit", result.stderr.lower())

    # ---- AC #2: refusal matrix ----

    def test_supersede_refuses_missing_old(self):
        """No ADR with the old NNNN → exit 2."""
        result = run_adr("supersede", "9999", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_supersede_refuses_missing_new(self):
        """No ADR with the new NNNN → exit 2."""
        result = run_adr("supersede", "0001", "9999", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr.lower())

    def test_supersede_refuses_proposed_old(self):
        """Old ADR's Status is Proposed → exit 2, distinguishing message."""
        _write_proposed_adr(self.adrs_dir / "adr-0001-old.md",
                            "0001", "old", "Old Decision")
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        msg = result.stderr.lower()
        # The message should mention "accept the old" (or proposed).
        self.assertIn("old", msg)
        self.assertTrue("accept" in msg or "proposed" in msg,
                        f"Proposed-old refusal must mention accept/proposed; got: {msg!r}")

    def test_supersede_refuses_proposed_new(self):
        """New ADR's Status is Proposed → exit 2, distinguishing message."""
        _write_proposed_adr(self.adrs_dir / "adr-0002-new.md",
                            "0002", "new", "New Decision")
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        msg = result.stderr.lower()
        self.assertIn("new", msg)
        self.assertTrue("accept" in msg or "proposed" in msg,
                        f"Proposed-new refusal must mention accept/proposed; got: {msg!r}")

    def test_supersede_refuses_already_superseded_old(self):
        """Old ADR is already Superseded → exit 2 with distinguishing message."""
        # Add a third ADR that will be the prior superseder.
        _write_accepted_adr(self.adrs_dir / "adr-0003-prior.md",
                            "0003", "prior", "Prior Replacement",
                            accepted_date="2026-02-01")
        # Now mark 0001 as Superseded by 0003.
        _write_superseded_adr(self.adrs_dir / "adr-0001-old.md",
                              "0001", "old", "Old Decision",
                              "0003", "prior",
                              accepted_date="2026-01-01",
                              super_date="2026-02-01")
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        msg = result.stderr.lower()
        # Distinguishing wording per AC #2: "double-supersede"
        self.assertIn("superseded", msg)

    def test_supersede_refuses_already_superseded_new(self):
        """New ADR is itself Superseded → exit 2 with distinguishing message."""
        # Add a third ADR that supersedes 0002.
        _write_accepted_adr(self.adrs_dir / "adr-0003-later.md",
                            "0003", "later", "Later Decision",
                            accepted_date="2026-03-01")
        _write_superseded_adr(self.adrs_dir / "adr-0002-new.md",
                              "0002", "new", "New Decision",
                              "0003", "later",
                              accepted_date=TODAY,
                              super_date="2026-03-01")
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        msg = result.stderr.lower()
        self.assertIn("superseded", msg)

    def test_supersede_refuses_self_supersession(self):
        """<old-NNNN> == <new-NNNN> → exit 2 BEFORE any file reads."""
        result = run_adr("supersede", "0001", "0001", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        msg = result.stderr.lower()
        self.assertTrue("same" in msg or "self" in msg or "identical" in msg,
                        f"self-supersession refusal must say so; got: {msg!r}")

    def test_supersede_refusal_does_not_mutate_either_file(self):
        """If supersession refuses, neither ADR is partially-modified."""
        new_before = (self.adrs_dir / "adr-0002-new.md").read_text()
        # Trigger the Proposed-old refusal
        _write_proposed_adr(self.adrs_dir / "adr-0001-old.md",
                            "0001", "old", "Old Decision")
        proposed_old = (self.adrs_dir / "adr-0001-old.md").read_text()
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 2)
        # New ADR untouched.
        self.assertEqual((self.adrs_dir / "adr-0002-new.md").read_text(),
                         new_before)
        # Old ADR exactly the Proposed version we wrote — no partial mutation.
        self.assertEqual((self.adrs_dir / "adr-0001-old.md").read_text(),
                         proposed_old)

    # ---- AC #6: dogfood-shape test ----

    def test_supersede_dogfood_byte_for_byte_shape(self):
        """Reproduce the ADR-0002 / ADR-0005 canonical shape byte-for-byte
        (modulo today's date for the supersede event)."""
        # Re-seed with dates and titles matching the real 0002/0005 fixture.
        _write_accepted_adr(self.adrs_dir / "adr-0001-old.md",
                            "0001", "old",
                            "`contracts` skill stays a deliberate stub",
                            accepted_date="2026-05-12")
        _write_accepted_adr(self.adrs_dir / "adr-0002-new.md",
                            "0002", "new",
                            "contracts skill is a judgment-skill nudging "
                            "toward standard external-interface artifacts",
                            accepted_date="2026-05-15")
        result = run_adr("supersede", "0001", "0002", cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        old = (self.adrs_dir / "adr-0001-old.md").read_text()
        # Match the canonical old-Status block shape verbatim.
        self.assertIn(
            f"## Status\n\n"
            f"Accepted (2026-05-12)\n"
            f"Superseded by [ADR-0002](./adr-0002-new.md) ({TODAY})\n",
            old,
        )

        new = (self.adrs_dir / "adr-0002-new.md").read_text()
        self.assertIn(
            "## Status\n\n"
            "Accepted (2026-05-15)\n"
            "Supersedes ADR-0001\n",
            new,
        )


# ---------- ExtractStatusAndDateTests (slice 005-02 AC #3) ----------


class ExtractStatusAndDateTests(unittest.TestCase):
    """Slice 005-02 AC #3: `_extract_status_and_date` recognizes the
    Superseded shape and (when both lines are present) prefers the
    Superseded tuple. Backward-compatible for Proposed / Accepted."""

    def setUp(self):
        self.adr = _import_adr_module()

    def _adr_with_status(self, status_body: str) -> str:
        return (
            "# ADR-0099: Sample\n\n"
            f"## Status\n\n{status_body}\n\n"
            "## Context\n\nSample.\n"
        )

    def test_proposed_returns_proposed_and_date(self):
        text = self._adr_with_status("Proposed (2026-01-01)")
        status, date_str = self.adr._extract_status_and_date(text)
        self.assertEqual(status, "Proposed")
        self.assertEqual(date_str, "2026-01-01")

    def test_accepted_returns_accepted_and_date(self):
        text = self._adr_with_status("Accepted (2026-01-15)")
        status, date_str = self.adr._extract_status_and_date(text)
        self.assertEqual(status, "Accepted")
        self.assertEqual(date_str, "2026-01-15")

    def test_superseded_only_returns_superseded_and_date(self):
        """A `Superseded by ... (date)` line on its own returns the date."""
        text = self._adr_with_status(
            "Superseded by [ADR-0099](./adr-0099-replacement.md) (2026-05-15)"
        )
        status, date_str = self.adr._extract_status_and_date(text)
        self.assertEqual(status, "Superseded")
        self.assertEqual(date_str, "2026-05-15")

    def test_accepted_then_superseded_returns_superseded(self):
        """Both `Accepted (date)` and `Superseded by ... (date)` present →
        Superseded wins (most recent state)."""
        text = self._adr_with_status(
            "Accepted (2026-01-01)\n"
            "Superseded by [ADR-0099](./adr-0099-replacement.md) (2026-05-15)"
        )
        status, date_str = self.adr._extract_status_and_date(text)
        self.assertEqual(status, "Superseded")
        self.assertEqual(date_str, "2026-05-15")

    def test_no_status_block_returns_unknown(self):
        """ADR text without a `## Status` block → ('(unknown)', '')."""
        text = "# ADR-0099: Sample\n\n## Context\n\nNo Status here.\n"
        status, date_str = self.adr._extract_status_and_date(text)
        self.assertEqual(status, "(unknown)")
        self.assertEqual(date_str, "")


# ---------- IndexTests for Superseded ADRs (slice 005-02 AC #4) ----------


class IndexSupersededTests(unittest.TestCase):
    """Slice 005-02 AC #4: `adr.py index` produces `(<date>, Superseded)`,
    NOT `(Superseded)` with no date, for a Superseded ADR."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-adr-index-super-")
        self.adrs_dir = Path(self.tmpdir) / "docs" / "decisions"
        self.adrs_dir.mkdir(parents=True)
        write_sample_readme(self.adrs_dir / "README.md")
        # Seed: an Accepted ADR (the new one) plus a Superseded one (the old).
        # Use _write_superseded_adr from SupersedeTests (same module).
        _write_accepted_adr(self.adrs_dir / "adr-0002-new.md",
                            "0002", "new", "New Decision",
                            accepted_date="2026-05-15")
        _write_superseded_adr(self.adrs_dir / "adr-0001-old.md",
                              "0001", "old", "Old Decision",
                              "0002", "new",
                              accepted_date="2026-01-01",
                              super_date="2026-05-15")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_index_bullet_for_superseded_carries_date(self):
        """Superseded bullet ends in `(<supersede-date>, Superseded)`."""
        result = run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        content = (self.adrs_dir / "README.md").read_text()
        self.assertIn("(2026-05-15, Superseded)", content)
        # The bare `(Superseded)` with no date is the old buggy shape.
        self.assertNotRegex(content, r"— [^()]*\(Superseded\)")

    def test_index_idempotent_after_supersede(self):
        """Re-running `index` after `supersede` produces identical bytes."""
        run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        first = (self.adrs_dir / "README.md").read_text()
        run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        second = (self.adrs_dir / "README.md").read_text()
        self.assertEqual(first, second, "index regen must be idempotent")

    def test_index_bullet_for_superseded_still_links_to_old_file(self):
        """The Superseded ADR remains historical record; its bullet must
        still link to the old file."""
        run_adr("index", str(self.adrs_dir), cwd=Path(self.tmpdir))
        content = (self.adrs_dir / "README.md").read_text()
        self.assertIn("(adr-0001-old.md)", content)


# ---------- Supersede SKILL.md surface (slice 005-02 AC #5) ----------


class SupersedeSkillSurfaceTests(unittest.TestCase):
    """Slice 005-02 AC #5: SKILL.md documents the new subcommand."""

    def setUp(self):
        self.skill = SKILL_MD.read_text()

    def test_skill_body_mentions_supersede_subcommand(self):
        """SKILL.md How-to-use section mentions `supersede`."""
        self.assertIn("supersede", self.skill.lower())

    def test_skill_documents_supersede_as_the_one_allowed_edit(self):
        """The immutability rule is reworded — supersede is now the recommended path."""
        # Some wording like "one edit allowed" or pointing at `adr.py supersede`
        # should appear in the immutability section.
        immut = self.skill.lower()
        self.assertIn("supersede", immut)
        # The skill must include the `supersede` bash invocation somewhere.
        self.assertRegex(
            self.skill,
            r"adr\.py\s+supersede",
            "SKILL.md must include the bash invocation `adr.py supersede`",
        )


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
        # Spec 066-01: the reserve path classifies scaffold-state. Drop the
        # completion sentinel so these fixtures classify as `scaffolded` and
        # run the existing 028-01 reserve flow with identical observable
        # output (AC4 no-regression).
        (self.target / "scaffold.json").write_text("{}\n")

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

    # Worktree-aware reservation (prototype): off-main no longer refuses.
    # With --no-push it commits a provisional reservation to the CURRENT
    # branch (the push path is exercised by the detached-worktree tests).
    def test_new_off_main_no_push_reserves_on_current_branch(self):
        self._seed_adr("0001", "first")
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/foo\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "myslug", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # Provisional stub created locally (0002 = max(0001) + 1).
        self.assertTrue((self.adrs_dir / "adr-0002-myslug.md").is_file())
        # Pathspec-limited commit so unrelated staged work can't leak in.
        commit_calls = [c for c in rec.calls
                        if len(c) >= 2 and c[0] == "git" and c[1] == "commit"]
        self.assertEqual(len(commit_calls), 1)
        self.assertIn("--", commit_calls[0])
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git push", flat)
        self.assertNotIn("git fetch", flat)

    # Worktree-aware reservation — default (push) from off-main claims the
    # number on origin/main via an ephemeral DETACHED worktree.
    def test_new_off_main_push_uses_detached_worktree(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/foo\n")
        # Reservation commit is pushed BY SHA, so rev-parse must be non-empty.
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "fromtree", project_dir=self.target,
                title="", no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertIn("git worktree add --detach", flat)
        self.assertIn("origin/main", flat)
        self.assertIn("git push origin 0a1b2c3d:refs/heads/main", flat)
        self.assertIn("git worktree remove --force", flat)
        self.assertNotIn("git checkout main", flat)
        self.assertNotIn("git reset --hard", flat)

    # Worktree path race recovery: teardown only, no `git reset --hard HEAD~1`.
    def test_new_off_main_race_cleans_up_worktree(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/foo\n")
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        # Push argv now starts with the SHA refspec, so match on the prefix.
        rec.stub(_matches("git", "push", "origin"),
                 returncode=1,
                 stderr="! [rejected] HEAD -> main (non-fast-forward)\n")
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "raced", project_dir=self.target,
                    title="", no_push=False, pr_mode=False,
                )
        self.assertIn("race", str(ctx.exception).lower())
        flat = " | ".join(rec.argv_log())
        self.assertIn("git worktree remove --force", flat)
        self.assertNotIn("git reset --hard HEAD~1", flat)

    # Worktree path protected-branch fallback: push to a reserve/ branch + PR.
    def test_new_off_main_protected_falls_back_to_pr(self):
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="feature/foo\n")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:user/repo.git\n")
        rec.stub(_matches("git", "rev-parse", "HEAD"),
                 returncode=0, stdout="0a1b2c3d\n")
        # First push (direct to main, by SHA) is refused by branch protection;
        # the one-shot stub fires on it, the later PR-fallback push to the
        # reserve/ branch falls through to the recorder's rc=0 default.
        rec.stub(_matches("git", "push", "origin"),
                 returncode=1,
                 stderr="remote: error: GH006: Protected branch update failed.\n")
        rec.stub(_matches("gh", "pr", "create"), returncode=0,
                 stdout="https://github.com/user/repo/pull/7\n")
        import shutil as _shutil
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod, \
             patch.object(_shutil, "which", return_value="/usr/local/bin/gh"):
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "protd", project_dir=self.target,
                title="", no_push=False, pr_mode=False,
            )
        self.assertEqual(code, 0)
        flat = " | ".join(rec.argv_log())
        self.assertIn(":refs/heads/reserve/adr-", flat)
        self.assertIn("gh pr create", flat)
        self.assertIn("--head", flat)
        self.assertIn("--base", flat)
        self.assertIn("git worktree remove --force", flat)

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
    def test_new_refuses_when_unscaffolded(self):
        # Spec 066-01: an empty (no scaffold.json, no spec-driven layout)
        # project classifies as `greenfield` and is ROUTED to scaffold-init,
        # replacing the old dead-end "docs/decisions/ not found" refusal.
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
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)
        # No ADR file / reservation commit created on the refusal.
        self.assertFalse(
            (bare / "docs" / "decisions" / "adr-0001-validslug.md").exists())
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

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


# ---------- ReserveAdrPreconditionRoutingTests (slice 066-01) ----------

class ReserveAdrPreconditionRoutingTests(unittest.TestCase):
    """Spec 066-01: `reserve_adr` (the `adr.py new` reserve path) replaces the
    weak `docs/decisions/`-presence check with a three-way scaffold-state
    classification that ROUTES — an `adoptable` project to /jig:migrate, a
    `greenfield` one to /jig:scaffold-init — while a `scaffolded` project
    (scaffold.json present) proceeds to the legacy reserve flow unchanged.
    `JIG_SCAFFOLD_PRECONDITION` bypasses the classification entirely (ADR-0011
    deliberateness gate). Mirrors ReserveSpecPreconditionRoutingTests in
    test_workflow.py."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-adr-066-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        self.adrs_dir = self.target / "docs" / "decisions"
        self._saved = os.environ.pop("JIG_SCAFFOLD_PRECONDITION", None)
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

        def _restore():
            if self._saved is not None:
                os.environ["JIG_SCAFFOLD_PRECONDITION"] = self._saved
            else:
                os.environ.pop("JIG_SCAFFOLD_PRECONDITION", None)
        self.addCleanup(_restore)

    def _make_greenfield(self):
        # Empty project: no scaffold.json, no spec-driven layout, no
        # docs/decisions/.
        pass

    def _make_adoptable(self):
        # >=3 triggers, no scaffold.json, no jig watermark.
        (self.target / "docs" / "specs").mkdir(parents=True)
        (self.target / "docs" / "decisions").mkdir(parents=True)
        (self.target / "docs" / "workflow.md").write_text("# wf\n")

    def _make_scaffolded(self):
        (self.target / "docs" / "decisions").mkdir(parents=True)
        (self.target / "scaffold.json").write_text("{}\n")

    # AC1 — adoptable → /jig:migrate, no ADR file, no reservation commit.
    def test_adoptable_routes_to_migrate(self):
        self._make_adoptable()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "validslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("adoptable", msg.lower())
        self.assertIn("/jig:migrate", msg)
        # No ADR file created, no reservation commit.
        self.assertFalse(
            (self.adrs_dir / "adr-0001-validslug.md").exists())
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

    # AC1 — greenfield → /jig:scaffold-init, no ADR file, no reservation commit.
    def test_greenfield_routes_to_scaffold_init(self):
        self._make_greenfield()
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "validslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)
        self.assertFalse((self.target / "docs" / "decisions").exists())
        flat = " | ".join(rec.argv_log())
        self.assertNotIn("git commit", flat)

    # Interrupted scaffold (jig watermark, no scaffold.json) → greenfield
    # routing (scaffold-init recovery), even with >=3 triggers present.
    def test_interrupted_scaffold_routes_to_scaffold_init(self):
        (self.target / "CLAUDE.md").write_text(
            "# Proj\n\n<!-- Generated by [jig] -->\n")
        (self.target / "docs" / "specs").mkdir(parents=True)
        (self.target / "docs" / "decisions").mkdir(parents=True)
        (self.target / "docs" / "workflow.md").write_text("# wf\n")
        (self.target / "docs" / "architecture.md").write_text("# arch\n")
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "validslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        self.assertIn("greenfield", msg.lower())
        self.assertIn("/jig:scaffold-init", msg)

    # AC4 — scaffolded → proceeds through the legacy reserve flow.
    def test_scaffolded_proceeds_to_reserve(self):
        self._make_scaffolded()
        rec = _SubprocessRecorder()
        # Stub the legacy preflight + commit path (branch==main, clean tree,
        # github origin, add/commit succeed) — no remote calls for --no-push.
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "validslug", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        # The legacy flow created the reservation stub ADR.
        self.assertTrue(
            (self.adrs_dir / "adr-0001-validslug.md").is_file())

    # AC3 — bypass: JIG_SCAFFOLD_PRECONDITION=0 skips classification and
    # runs the legacy flow even on a greenfield project (with docs/decisions/
    # present so the legacy weak check passes).
    def test_bypass_runs_legacy_flow_on_greenfield(self):
        # Greenfield-ish but the legacy flow still needs docs/decisions/ to
        # exist (the bypass restores *today's* behavior, including its own
        # weak docs/decisions/ check). Provide docs/decisions/ — but NOT
        # scaffold.json — so the legacy path runs without classification.
        (self.target / "docs" / "decisions").mkdir(parents=True)
        os.environ["JIG_SCAFFOLD_PRECONDITION"] = "0"
        rec = _SubprocessRecorder()
        rec.stub(_matches("git", "symbolic-ref", "--short", "HEAD"),
                 returncode=0, stdout="main\n")
        rec.stub(_matches("git", "status", "--porcelain"),
                 returncode=0, stdout="")
        rec.stub(_matches("git", "config", "--get", "remote.origin.url"),
                 returncode=0, stdout="git@github.com:u/r.git\n")
        rec.stub(_matches("git", "add"), returncode=0)
        rec.stub(_matches("git", "commit"), returncode=0)
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            code = _adr_mod.reserve_adr(
                "validslug", project_dir=self.target,
                title="", no_push=True, pr_mode=False,
            )
        self.assertEqual(code, 0)
        self.assertTrue(
            (self.adrs_dir / "adr-0001-validslug.md").is_file())

    # AC3 — bypass with the legacy weak check still firing: docs/decisions/
    # absent under bypass → the OLD dead-end refusal (preserves today's
    # behavior exactly, no scaffold-state routing).
    def test_bypass_preserves_legacy_weak_refusal(self):
        os.environ["JIG_SCAFFOLD_PRECONDITION"] = "false"
        rec = _SubprocessRecorder()
        from unittest.mock import patch
        with patch.object(_adr_mod, "subprocess") as sp_mod:
            sp_mod.run = rec
            with self.assertRaises(_adr_mod.AdrError) as ctx:
                _adr_mod.reserve_adr(
                    "validslug", project_dir=self.target,
                    title="", no_push=True, pr_mode=False,
                )
        msg = str(ctx.exception)
        # Legacy message (not the scaffold-state routing message).
        self.assertIn("docs/decisions", msg)
        self.assertNotIn("/jig:scaffold-init", msg)
        self.assertNotIn("/jig:migrate", msg)


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
        # Spec 066-01: the reserve path classifies scaffold-state; the
        # completion sentinel makes this CLI fixture classify as `scaffolded`.
        (Path(self.tmpdir) / "scaffold.json").write_text("{}\n")
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


class ReserveAdrFromLinkedWorktreeE2E(unittest.TestCase):
    """Real-git end-to-end proof of the worktree-aware ADR reservation fix.
    Reserves from a linked worktree (where `git checkout main` is impossible)
    and asserts it lands on origin/main with the feature branch untouched.
    Mirrors ReserveSpecFromLinkedWorktreeE2E in test_workflow.py."""

    def _git(self, *args, cwd):
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        )

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-adr-wt-e2e-"))
        self.work = self.tmp / "work"
        self._git("init", str(self.work), cwd=self.tmp)
        self._git("symbolic-ref", "HEAD", "refs/heads/main", cwd=self.work)
        for k, v in (("user.email", "t@e.x"), ("user.name", "T"),
                     ("commit.gpgsign", "false")):
            self._git("config", k, v, cwd=self.work)
        dec = self.work / "docs" / "decisions"
        dec.mkdir(parents=True)
        for name in ("adr-0001-alpha.md", "adr-0002-beta.md"):
            (dec / name).write_text(f"# {name}\n")
        # Spec 066-01: the reserve path classifies scaffold-state. Seed the
        # completion sentinel so the checked-out `self.feat` worktree (which
        # is what `reserve_adr` classifies) reads as `scaffolded`.
        (self.work / "scaffold.json").write_text("{}\n")
        self._git("add", "-A", cwd=self.work)
        self._git("commit", "-m", "seed adrs", cwd=self.work)
        self.origin = self.tmp / "origin.git"
        self._git("init", "--bare", str(self.origin), cwd=self.tmp)
        self._git("remote", "add", "origin", str(self.origin), cwd=self.work)
        push = self._git("push", "-u", "origin", "main", cwd=self.work)
        self.assertEqual(push.returncode, 0, f"seed push failed: {push.stderr}")
        self.feat = self.tmp / "feat"
        add = self._git("worktree", "add", "-b", "feature", str(self.feat),
                        cwd=self.work)
        self.assertEqual(add.returncode, 0, f"worktree add failed: {add.stderr}")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_reserve_from_linked_worktree_lands_on_origin_main(self):
        co = self._git("checkout", "main", cwd=self.feat)
        self.assertNotEqual(co.returncode, 0)
        self.assertIn("already used by worktree", co.stderr)

        feat_head_before = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()

        code = _adr_mod.reserve_adr(
            "gamma", project_dir=self.feat, title="", no_push=False,
            pr_mode=False,
        )
        self.assertEqual(code, 0)

        # Landed on origin/main as adr-0003-gamma (max + 1).
        ls = self._git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        self.assertIn("docs/decisions/adr-0003-gamma.md", ls.stdout)

        # Ephemeral reservation worktree cleaned up — only work + feat remain.
        wl = self._git("worktree", "list", cwd=self.work).stdout
        self.assertNotIn("jig-reserve-adr", wl)
        self.assertEqual(len(wl.strip().splitlines()), 2, wl)

        # Caller's branch tip and working tree untouched.
        feat_head_after = self._git(
            "rev-parse", "HEAD", cwd=self.feat).stdout.strip()
        self.assertEqual(feat_head_before, feat_head_after)
        self.assertFalse(
            (self.feat / "docs/decisions/adr-0003-gamma.md").exists())

    def test_reserve_from_linked_worktree_with_relative_origin_url(self):
        # B1 regression lock: with a RELATIVE origin URL, the old code (push
        # from the ephemeral temp worktree under $TMPDIR) resolved the URL
        # against the wrong base and died late. Pushing the commit BY SHA from
        # `project_dir` resolves it correctly. FAILS before the fix, PASSES
        # after. Mirrors ReserveSpecFromLinkedWorktreeE2E.
        rel = self._git("remote", "set-url", "origin", "../origin.git",
                        cwd=self.work)
        self.assertEqual(rel.returncode, 0, f"set-url failed: {rel.stderr}")
        url = self._git("remote", "get-url", "origin", cwd=self.feat)
        self.assertEqual(url.stdout.strip(), "../origin.git")

        code = _adr_mod.reserve_adr(
            "gamma", project_dir=self.feat, title="", no_push=False,
            pr_mode=False,
        )
        self.assertEqual(code, 0)

        # The ref REALLY moved on origin.
        ls = self._git("ls-tree", "-r", "--name-only", "main", cwd=self.origin)
        self.assertIn("docs/decisions/adr-0003-gamma.md", ls.stdout)

        wl = self._git("worktree", "list", cwd=self.work).stdout
        self.assertNotIn("jig-reserve-adr", wl)

    def test_reserve_no_push_does_not_sweep_unrelated_staged_file(self):
        # M1 regression lock: --no-push commits ONLY the stub ADR file via a
        # pathspec-limited commit, even when the caller has unrelated work
        # already staged. The staged file must survive uncommitted. (ADR
        # reservation writes a single stub file, vs. the spec path's two.)
        (self.feat / "unrelated.txt").write_text("do not commit me\n")
        add = self._git("add", "unrelated.txt", cwd=self.feat)
        self.assertEqual(add.returncode, 0, f"git add failed: {add.stderr}")

        code = _adr_mod.reserve_adr(
            "delta", project_dir=self.feat, title="", no_push=True,
            pr_mode=False,
        )
        self.assertEqual(code, 0)

        # (a) The reservation commit contains ONLY the stub ADR file.
        names = self._git(
            "show", "--name-only", "--pretty=format:", "HEAD", cwd=self.feat
        ).stdout.split()
        self.assertEqual(
            sorted(names), ["docs/decisions/adr-0003-delta.md"],
            f"commit swept extra files: {names}",
        )

        # (b) The unrelated file is still staged/uncommitted (not swept in).
        self.assertNotIn("unrelated.txt", names)
        staged = self._git(
            "diff", "--cached", "--name-only", cwd=self.feat).stdout
        self.assertIn("unrelated.txt", staged)


if __name__ == "__main__":
    unittest.main()
