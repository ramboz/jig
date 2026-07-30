"""
AC verification tests for slice 008-01 (migrate-report).

Run from the repo root:
    python3 -m unittest skills.migrate.test_migrate
Or from the skill dir:
    python3 -m unittest test_migrate
"""

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_PY = REPO_ROOT / "skills" / "migrate" / "migrate.py"
WORKFLOW_PY = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
SKILL_MD = REPO_ROOT / "skills" / "migrate" / "SKILL.md"
FIXTURES = REPO_ROOT / "skills" / "migrate" / "fixtures"


def run_migrate(*args: str) -> subprocess.CompletedProcess:
    """Invoke migrate.py as a subprocess."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(MIGRATE_PY), *args],
        capture_output=True, text=True, env=env,
    )


# Load migrate.py as a module for direct-call tests. Mirrors the pattern in
# skills/spec-workflow/test_workflow.py and skills/slice-land/test_land.py:
# importlib bypasses the `from skills.migrate import migrate` import path
# that only works under `unittest discover`. Inbox 2026-05-13 follow-up.
import importlib.util as _ilu


def _load_migrate():
    # Register the module in sys.modules BEFORE exec_module so dataclass's
    # typing machinery can resolve `cls.__module__` (Python 3.9 with string
    # annotations and 3.14+ raise AttributeError otherwise).
    spec = _ilu.spec_from_file_location("_migrate_module", MIGRATE_PY)
    mod = _ilu.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_migrate = _load_migrate()


def _write_track_local_corpus(root: Path) -> Path:
    """CWV-shaped minimal corpus: artifacts live directly under ``root``."""
    spec_dir = root / "specs" / "001-example"
    spec_dir.mkdir(parents=True)
    spec = spec_dir / "spec.md"
    spec.write_text(
        "---\nstatus: DRAFT\nuse_cases: []\n---\n\n"
        "# Spec 001: Example\n\n## Overview\nExample.\n\n"
        "## Assumptions\n\nNone.\n\n## Slices\n"
        "- [001-01 — example](slice-01-example.md)\n"
    )
    (spec_dir / "slice-01-example.md").write_text(
        "---\nstatus: DRAFT\ndependencies: []\nlast_verified: 2026-07-15\n---\n\n"
        "## Slice 001-01 — example\n\n**Goal:** Example.\n\n"
        "**DoR:**\n- ✅ Ready.\n\n**Acceptance Criteria:**\n\n"
        "1. Example.\n\n**DoD:**\n- [ ] Example.\n\n"
        "**Anti-horizontal-phasing check:** Example.\n"
    )
    (root / "specs" / "README.md").write_text("# Spec status board\n")
    (root / "decisions").mkdir()
    (root / "decisions" / "adr-0001-example.md").write_text("# ADR-0001\n")
    (root / "workflow.md").write_text("# Workflow\n")
    (root / "architecture.md").write_text("# Architecture\n")
    return spec


class AdoptLayoutTests(unittest.TestCase):
    """Spec 092 — existing custom-root corpus adoption."""

    def setUp(self):
        import tempfile
        self.root = Path(tempfile.mkdtemp(prefix="jig-adopt-layout-"))
        self.spec = _write_track_local_corpus(self.root)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root)

    def test_report_under_dot_root_is_adoptable_and_uses_real_paths(self):
        r = run_migrate("report", str(self.root), "--docs-root", ".")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Verdict:** adoptable", r.stdout)
        self.assertIn("`specs/*/spec.md`", r.stdout)
        self.assertNotIn("`docs/specs/*/spec.md`", r.stdout)
        self.assertIn("adopt-layout", r.stdout)

    def test_report_scans_contract_surfaces_under_custom_root(self):
        (self.root / "architecture.md").write_text(
            "# Architecture\n\n## API\n\n| Method | Path |\n|---|---|\n"
            "| GET | /v1/example |\n\n```json\n{}\n```\n"
        )

        r = run_migrate("report", str(self.root), "--docs-root", ".")

        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Prose API contract", r.stdout)
        self.assertIn("`architecture.md` §API", r.stdout)

    def test_dry_run_writes_nothing(self):
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        r = run_migrate(
            "adopt-layout", str(self.root), "--docs-root", ".", "--dry-run",
            "--host", "codex",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run]", r.stdout)
        self.assertFalse((self.root / "scaffold.json").exists())
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_apply_preserves_corpus_and_enables_workflow_transition(self):
        before = {p.relative_to(self.root): p.read_bytes()
                  for p in self.root.rglob("*") if p.is_file()}
        r = run_migrate(
            "adopt-layout", str(self.root), "--docs-root", ".",
            "--host", "codex",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        manifest = __import__("json").loads(
            (self.root / "scaffold.json").read_text()
        )
        self.assertEqual(manifest["layout"]["docs_root"], ".")
        self.assertEqual(manifest["scaffold_mode"], "plugin-only")
        after = {p.relative_to(self.root): p.read_bytes()
                 for p in self.root.rglob("*")
                 if p.is_file() and p.name != "scaffold.json"}
        self.assertEqual(before, after)

        board = subprocess.run(
            [sys.executable, str(WORKFLOW_PY), "status-board", str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(board.returncode, 0, board.stderr)
        self.assertIn(
            "001-01 — example",
            (self.root / "specs" / "README.md").read_text(),
        )

        transition = subprocess.run(
            [sys.executable, str(WORKFLOW_PY), "transition", str(self.spec),
             "001-01", "READY_FOR_REVIEW"],
            capture_output=True, text=True,
        )
        self.assertEqual(transition.returncode, 0, transition.stderr)
        slice_text = (self.spec.parent / "slice-01-example.md").read_text()
        self.assertIn("status: READY_FOR_REVIEW", slice_text)

        reverse = subprocess.run(
            [sys.executable, str(WORKFLOW_PY), "transition", str(self.spec),
             "001-01", "DRAFT"],
            capture_output=True, text=True,
        )
        self.assertEqual(reverse.returncode, 0, reverse.stderr)

    def test_refuses_incomplete_or_escaping_layout_without_write(self):
        import tempfile
        incomplete = Path(tempfile.mkdtemp(prefix="jig-adopt-incomplete-"))
        try:
            bad = run_migrate(
                "adopt-layout", str(incomplete), "--docs-root", ".")
            self.assertEqual(bad.returncode, 2)
            self.assertFalse((incomplete / "scaffold.json").exists())
        finally:
            import shutil
            shutil.rmtree(incomplete)

        escaping = run_migrate(
            "adopt-layout", str(self.root), "--docs-root", "../escape")
        self.assertEqual(escaping.returncode, 2)
        self.assertFalse((self.root / "scaffold.json").exists())


# -------------------- InventoryTests --------------------


class InventoryTests(unittest.TestCase):
    """AC #1 — Inventory section lists detected artifacts."""

    def test_tiny_validator_inventory_has_expected_rows(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        self.assertEqual(r.returncode, 0,
                         f"exit {r.returncode}; stderr: {r.stderr}")
        out = r.stdout
        # Inventory section exists and includes expected rows
        self.assertIn("## Inventory", out)
        # Slice dir detected with count 2
        self.assertRegex(out, r"docs/slices/.*\b2\b")
        # Decisions dir detected with count 2
        self.assertRegex(out, r"docs/decisions/.*\b2\b")
        # Spike dir detected
        self.assertIn("docs/spikes/", out)
        # Doc landmarks
        self.assertIn("docs/workflow.md", out)
        self.assertIn("docs/architecture.md", out)
        # Custom skill in inventory
        self.assertIn("custom-skill.md", out)
        # CLAUDE.md size reported
        self.assertRegex(out, r"CLAUDE\.md.*\d+")

    def test_greenfield_inventory_minimal(self):
        r = run_migrate("report", str(FIXTURES / "greenfield"))
        # Even on greenfield, exit 0 (the report is the deliverable
        # regardless of verdict).
        self.assertEqual(r.returncode, 0)
        out = r.stdout
        self.assertIn("## Inventory", out)
        # No specs/slices/decisions/workflow/architecture rows expected.
        # The inventory section will either be empty-ish or only show
        # what's actually present.


# -------------------- VerdictTests --------------------


class VerdictTests(unittest.TestCase):
    """AC #2 + AC #3 — verdict logic + exit codes."""

    def test_tiny_validator_is_adoptable(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"(?i)\*\*Verdict:\*\*\s+adoptable")

    def test_partial_fixture_returns_one(self):
        r = run_migrate("report", str(FIXTURES / "partial"))
        # Partial = exit 1, informational, but report still emits
        self.assertEqual(r.returncode, 1, f"stderr: {r.stderr}")
        self.assertRegex(r.stdout, r"(?i)\*\*Verdict:\*\*\s+partial")

    def test_greenfield_returns_zero(self):
        r = run_migrate("report", str(FIXTURES / "greenfield"))
        # Greenfield = exit 0, report is still the deliverable
        self.assertEqual(r.returncode, 0)
        self.assertRegex(r.stdout, r"(?i)\*\*Verdict:\*\*\s+not-yet-spec-driven")


# -------------------- MappingTests --------------------


class MappingTests(unittest.TestCase):
    """AC #1 — Mapping section shows current → jig translations."""

    def test_decisions_dir_kept_when_already_aligned(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        self.assertIn("## Mapping", out)
        # decisions dir already matches ADR-0004 — should map to "kept"
        self.assertRegex(out, r"(?is)docs/decisions/.*(?:kept|already)")

    def test_3_digit_adr_filenames_pad_to_4(self):
        """ADR file `adr-001-foo.md` should map to `adr-0001-foo.md` (4-digit)."""
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        # Mapping row mentions the pad operation
        self.assertRegex(out, r"adr-001-foo\.md")
        self.assertRegex(out, r"adr-0001-foo\.md")

    def test_flat_slices_flagged_as_topology_question(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        # Flat slices noted as topology question / pointing to Ambiguities
        # or to 008-04 (future slice).
        self.assertRegex(out,
                         r"(?is)docs/slices/.*?(?:topology|008-04|ambigu)")


# -------------------- ConflictTests --------------------


class ConflictTests(unittest.TestCase):
    """AC #1 — Conflicts section flags blocking situations."""

    def test_both_adrs_and_decisions_present_flagged(self):
        r = run_migrate("report", str(FIXTURES / "conflict"))
        # Adoptable verdict (4 triggers present: decisions, adrs, workflow,
        # architecture — adrs is a decisions-dir variant, still counts).
        self.assertEqual(r.returncode, 0)
        out = r.stdout
        self.assertIn("## Conflicts", out)
        # Both dirs called out
        self.assertRegex(out,
                         r"(?is)docs/adrs/.*?docs/decisions/|"
                         r"docs/decisions/.*?docs/adrs/")

    def test_conflict_blocks_rename_in_operations(self):
        r = run_migrate("report", str(FIXTURES / "conflict"))
        out = r.stdout
        # Operations section either omits rename-decisions or marks it blocked
        self.assertIn("## Operations", out)
        # The rename suggestion should be flagged as blocked/refused given
        # the dual-dir presence.
        self.assertRegex(
            out,
            r"(?is)rename-decisions.*?(?:refus|conflict|block|not\s+available)"
            r"|(?:refus|conflict|block).*?rename-decisions",
        )


# -------------------- AmbiguityTests --------------------


class AmbiguityTests(unittest.TestCase):
    """AC #1 — Ambiguities section names judgment calls."""

    def test_flat_slices_with_milestones_named(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        self.assertIn("## Ambiguities", out)
        # The Ambiguities section must name the milestone-to-parent-spec
        # question (validator's M1–M6 → 6 specs) OR the flat-slice
        # topology issue. The fixture uses M1 references.
        self.assertRegex(out,
                         r"(?i)(?:milestone|parent\s+spec|topology)")

    def test_custom_skill_named_as_ambiguity_or_inventory(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        # Custom skills overlap question — either inventoried with caveat
        # or named in Ambiguities. Either is acceptable for 008-01.
        self.assertIn("custom-skill", out)

    def test_adr_status_readable_helper(self):
        """`_adr_status_readable` mirrors the `→ DONE` gate's *presence*
        check: frontmatter `status:` OR a prose `## Status` section is
        readable; a bare inline `**Status:** Accepted` line is not."""
        # Frontmatter status → readable.
        self.assertTrue(_migrate._adr_status_readable(
            "---\nstatus: Accepted\n---\n\n# ADR\n\nbody\n"))
        # Prose `## Status` section → readable.
        self.assertTrue(_migrate._adr_status_readable(
            "# ADR\n\n## Status\n\nAccepted (2026-01-01)\n"))
        # Frontmatter present but no status key, with a prose section → readable.
        self.assertTrue(_migrate._adr_status_readable(
            "---\ndependencies: []\n---\n\n# ADR\n\n## Status\n\nAccepted\n"))
        # Bare inline `**Status:**` line, no frontmatter, no section → NOT readable.
        self.assertFalse(_migrate._adr_status_readable(
            "# ADR\n\n- **Status:** Accepted\n- **Date:** 2026-01-01\n"))
        # A `status:` key inside the body (not the leading frontmatter block)
        # must NOT be mistaken for readable frontmatter.
        self.assertFalse(_migrate._adr_status_readable(
            "# ADR\n\nprose then a line\nstatus: Accepted\n"))

    def test_unreadable_adr_status_flagged_in_ambiguities(self):
        """Reported gap: the tiny-validator fixture's ADRs use a bare inline
        `**Status:** Accepted` line — a format the `→ DONE` gate can't read.
        `report` must surface this in Ambiguities so `adoptable` isn't
        misread as full lifecycle conformance."""
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        self.assertIn("## Ambiguities", out)
        self.assertRegex(out, r"(?i)status format the.*DONE.*gate can'?t read")
        self.assertIn("adr-001-foo.md", out)
        self.assertIn("adr-002-bar.md", out)

    def test_readable_adr_status_not_flagged(self):
        """An ADR whose status the gate CAN read (frontmatter or `## Status`)
        must not be flagged."""
        import shutil
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="jig-mig-adr-status-"))
        try:
            decisions = tmpdir / "docs" / "decisions"
            decisions.mkdir(parents=True)
            (decisions / "adr-0001-fm.md").write_text(
                "---\nstatus: Accepted\n---\n\n# ADR-0001\n\nbody\n")
            (decisions / "adr-0002-prose.md").write_text(
                "# ADR-0002\n\n## Status\n\nAccepted (2026-01-01)\n")
            (tmpdir / "docs" / "workflow.md").write_text("# wf")
            (tmpdir / "docs" / "architecture.md").write_text("# arch")
            r = run_migrate("report", str(tmpdir))
            self.assertNotRegex(
                r.stdout, r"status format the.*DONE.*gate can'?t read",
                f"readable ADRs wrongly flagged:\n{r.stdout}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_readme_excluded_from_slices_count(self):
        """Reviewer-flagged latent bug: prior version filtered README only
        for decisions/adrs/skills/agents; slices/spikes were unfiltered.
        A `docs/slices/README.md` would have been counted as a slice."""
        import shutil
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="jig-mig-slice-readme-"))
        try:
            slices = tmpdir / "docs" / "slices"
            slices.mkdir(parents=True)
            (slices / "README.md").write_text("# Slices readme")
            (slices / "slice-01-real.md").write_text(
                "# Slice 01 — Real\n**Milestone:** M1\n"
            )
            # Plus other triggers so verdict is adoptable
            (tmpdir / "docs" / "workflow.md").write_text("# wf")
            (tmpdir / "docs" / "architecture.md").write_text("# arch")
            r = run_migrate("report", str(tmpdir))
            out = r.stdout
            # Slices row must show count 1, not 2.
            self.assertRegex(out, r"docs/slices/.*?\b1\b",
                             f"Slices count includes README:\n{out}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_readme_excluded_from_spikes_count(self):
        """Same latent bug, spike side."""
        import shutil
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="jig-mig-spike-readme-"))
        try:
            spikes = tmpdir / "docs" / "spikes"
            spikes.mkdir(parents=True)
            (spikes / "README.md").write_text("# Spikes readme")
            (spikes / "spike-01-thing.md").write_text("# Spike 01")
            (tmpdir / "docs" / "workflow.md").write_text("# wf")
            (tmpdir / "docs" / "architecture.md").write_text("# arch")
            (tmpdir / "docs" / "decisions").mkdir()
            (tmpdir / "docs" / "decisions" / "adr-001-foo.md").write_text("# adr")
            r = run_migrate("report", str(tmpdir))
            out = r.stdout
            self.assertRegex(out, r"docs/spikes/.*?\b1\b",
                             f"Spikes count includes README:\n{out}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_readme_excluded_from_agents_listing(self):
        """Regression: dogfood against validator listed
        `.claude/agents/README.md` as a custom agent — that's a docs
        file, not an agent definition. README.md must be filtered out
        the same way it's filtered from decisions/adrs."""
        import shutil
        import tempfile
        tmpdir = Path(tempfile.mkdtemp(prefix="jig-mig-readme-"))
        try:
            agents = tmpdir / ".claude" / "agents"
            agents.mkdir(parents=True)
            (agents / "README.md").write_text("# Agents readme")
            (agents / "real-agent.md").write_text("# real agent")
            # Plus minimal triggers so the report runs without exiting 2
            (tmpdir / "docs").mkdir()
            (tmpdir / "docs" / "workflow.md").write_text("# wf")
            (tmpdir / "docs" / "architecture.md").write_text("# arch")
            r = run_migrate("report", str(tmpdir))
            out = r.stdout
            # README.md must NOT appear in the agents inventory listing.
            self.assertNotRegex(
                out, r"custom agents:[^|]*README\.md",
                f"README.md leaked into agents listing:\n{out}",
            )
            # The real agent should appear
            self.assertIn("real-agent.md", out)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# -------------------- OperationsTests --------------------


class OperationsTests(unittest.TestCase):
    """AC #1 — Operations section suggests next migrate.py subcommands."""

    def test_operations_section_present(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        self.assertIn("## Operations", r.stdout)

    def test_operations_flags_rename_as_future_slice(self):
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        # The mention of rename-decisions should indicate it's not yet
        # implemented (slice 008-02 deferred).
        self.assertRegex(r.stdout,
                         r"(?is)rename-decisions.*?(?:008-02|not yet|deferred|coming)")

    def test_operations_numbering_is_sequential(self):
        """Regression: dogfood against validator showed `1. ... 3. ...`
        (skipped 2) because the slice-to-spec branch's index math was
        off-by-one. Numbers must run 1, 2, 3, … with no gaps."""
        r = run_migrate("report", str(FIXTURES / "tiny-validator"))
        out = r.stdout
        ops_section_match = re.search(
            r"## Operations\s*\n(.*)", out, re.DOTALL,
        )
        self.assertIsNotNone(ops_section_match)
        ops_body = ops_section_match.group(1)
        # Find numbered lines like `1. **...**` or `1. ...`
        numbers = [int(m.group(1)) for m in
                   re.finditer(r"^(\d+)\.\s+\*\*", ops_body, re.MULTILINE)]
        if len(numbers) >= 2:
            self.assertEqual(
                numbers, list(range(1, len(numbers) + 1)),
                f"Operations numbering not sequential: {numbers}",
            )


# -------------------- SafetyTests --------------------


# Sentinel comment that partitions migrate.py into a read-only region (the
# `report` code path) and a mutator region (the `rename-decisions` code path).
# Slice 008-02 introduced this split — `report` must remain pure-read, but
# `rename-decisions` is the first mutating subcommand and necessarily calls
# os.replace + atomic-write helpers.
SAFETY_SENTINEL = (
    "# ---------- BEGIN MUTATING CODE PATH (rename-decisions) ----------"
)


def _read_only_region() -> str:
    """Return the source slice from start of file up to (but not including)
    the sentinel comment. Raises if the sentinel is missing."""
    src = MIGRATE_PY.read_text()
    idx = src.find(SAFETY_SENTINEL)
    if idx == -1:
        raise AssertionError(
            f"SAFETY_SENTINEL not found in {MIGRATE_PY}; the read-only "
            "region cannot be verified. Add the sentinel comment between "
            "the report code path and the rename-decisions code path."
        )
    return src[:idx]


class SafetyTests(unittest.TestCase):
    """AC #4 (008-01) + AC #10c (008-02) — no filesystem-mutating calls in
    the report code path. The rename-decisions code path is allowed to
    mutate; this test class verifies the read-only region only."""

    def setUp(self):
        self.source = _read_only_region()

    def test_no_path_write_text(self):
        self.assertNotRegex(self.source, r"\.write_text\s*\(")

    def test_no_path_rename(self):
        self.assertNotRegex(self.source, r"\.rename\s*\(")

    def test_no_os_replace(self):
        self.assertNotRegex(self.source, r"os\.replace\s*\(")

    def test_no_shutil_move(self):
        self.assertNotRegex(self.source, r"shutil\.move\s*\(")

    def test_no_path_unlink(self):
        self.assertNotRegex(self.source, r"\.unlink\s*\(")

    def test_no_path_mkdir(self):
        # No directory creation in the report path.
        self.assertNotRegex(self.source, r"\.mkdir\s*\(")

    def test_no_open_for_write(self):
        # `open(path, "w")` / `open(path, "a")` / `open(path, "x")` — forbidden.
        self.assertNotRegex(self.source,
                            r"open\s*\([^)]*,\s*[\'\"][wax]")


# -------------------- ErrorTests --------------------


class ErrorTests(unittest.TestCase):
    """AC #3 — exit 2 on user error."""

    def test_missing_dir_arg(self):
        r = run_migrate("report")
        self.assertEqual(r.returncode, 2)

    def test_nonexistent_dir(self):
        r = run_migrate("report", "/tmp/this-does-not-exist-jig-test-xyz")
        self.assertEqual(r.returncode, 2)

    def test_dir_is_file_not_directory(self):
        # Pass migrate.py itself as the "dir" arg — should refuse.
        r = run_migrate("report", str(MIGRATE_PY))
        self.assertEqual(r.returncode, 2)


# -------------------- SkillSurfaceTests --------------------


class SkillSurfaceTests(unittest.TestCase):
    """AC #5 — SKILL.md surface."""

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text()

    def test_frontmatter_active(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md must have YAML frontmatter")
        fm = m.group(1)
        self.assertNotIn("disable-model-invocation: true", fm,
                         "migrate must auto-trigger (frontmatter active)")

    def test_user_invocable(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        self.assertNotIn("user-invocable: false", fm)

    def test_description_has_all_five_trigger_phrases(self):
        """AC #5 enumerates five trigger phrases — all must appear in the
        description block of the frontmatter.

        Reviewer note: the description-extraction regex anchors on the
        closing `---` of the frontmatter rather than the next YAML key.
        Earlier brittle form `(?=\\n\\w+:|\\Z)` overran into
        `user-invocable:` because the folded `>` block is indented; the
        test passed only because the trigger phrases happened to sit
        before `user-invocable:`. Anchoring on `---` is unambiguous."""
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1)
        # Match `description:` value through the rest of the frontmatter,
        # but stop at any line that starts a new top-level YAML key
        # (zero-indent `<word>:` line). Folded `>` block content is
        # always indented, so a zero-indent key is unambiguously the
        # next field.
        desc_match = re.search(
            r"description:\s*>?\s*\n?(.*?)(?=^[A-Za-z][\w-]*:\s|\Z)",
            fm, re.DOTALL | re.MULTILINE,
        )
        self.assertIsNotNone(desc_match)
        desc = desc_match.group(1).lower()
        # Sanity: the description we extracted must NOT contain other
        # top-level keys (regression guard against the prior brittle
        # extraction).
        for stray_key in ("user-invocable:", "name:"):
            self.assertNotIn(stray_key, desc,
                             f"description regex leaked into `{stray_key}` "
                             f"— check the closing anchor")
        expected = [
            "migrate this project",
            "adopt jig",
            "already has specs",
            "scaffold-init refused",
            "introduce jig to an existing",
        ]
        for phrase in expected:
            self.assertIn(phrase, desc,
                          f"description missing trigger phrase: {phrase!r}")

    def test_body_references_migrate_py_report(self):
        self.assertIn("migrate.py report", self.skill)

    def test_body_mentions_future_subcommands(self):
        # Body should reference future subcommands as not-yet-available
        # (e.g. "rename-decisions" as Coming in slice 008-02).
        self.assertIn("rename-decisions", self.skill)


# -------------------- DogfoodTests --------------------


class DogfoodTests(unittest.TestCase):
    """AC #7 — gated dogfood against the real aso-shallow-validator path.

    Skipped when the validator dir doesn't exist (CI / clean machines)."""

    VALIDATOR = Path(
        "/Users/ramboz/Projects/misc/aso-shallow-validator"
    )

    @unittest.skipUnless(VALIDATOR.is_dir(),
                         "aso-shallow-validator path not present")
    def test_validator_reports_adoptable(self):
        r = run_migrate("report", str(self.VALIDATOR))
        self.assertEqual(r.returncode, 0,
                         f"exit {r.returncode}; stderr: {r.stderr}")
        self.assertRegex(r.stdout, r"(?i)\*\*Verdict:\*\*\s+adoptable")


# ==========================================================================
# Slice 008-02 — rename-decisions tests
# ==========================================================================

import hashlib
import shutil
import tempfile


def _make_tree(spec: dict, root: Path = None) -> Path:
    """Build a synthetic project tree under a tempdir.

    spec is a {relative_path: file_content} mapping. Parent dirs are created
    automatically. Empty-string content creates an empty file; None means
    "create as directory" (use `dir/` suffix). Returns the root."""
    if root is None:
        root = Path(tempfile.mkdtemp(prefix="jig-mig-rename-"))
    for rel, content in spec.items():
        target = root / rel
        if rel.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    return root


def _hash_tree(root: Path) -> str:
    """Stable hash of the tree's content (paths + bytes) for byte-identity
    assertions before/after dry-run."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            h.update(b"SYMLINK\0")
            h.update(str(p.relative_to(root)).encode())
            h.update(b"\0")
            h.update(os.readlink(p).encode())
            h.update(b"\0")
            continue
        if p.is_dir():
            h.update(b"DIR\0")
            h.update(str(p.relative_to(root)).encode())
            h.update(b"\0")
            continue
        h.update(b"FILE\0")
        h.update(str(p.relative_to(root)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


class RenamePlanTests(unittest.TestCase):
    """AC #1 / #2 — plan() returns the expected ordered list of operations."""

    def setUp(self):
        # Adrs-dir source with 3-digit padding; needs dir rename + file pads.
        self.tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# ADR-0001\n",
            "docs/adrs/0002-bar.md": "# ADR-0002\n",
            "docs/workflow.md": "# Workflow\n",
            "docs/architecture.md": "Refers to docs/adrs/0001-foo.md.\n",
        })

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_plan_includes_dir_rename(self):
        migrate = _migrate
        plan = migrate.plan_rename(self.tmpdir)
        self.assertIsNotNone(plan.dir_rename)
        self.assertEqual(plan.dir_rename.src.name, "adrs")
        self.assertEqual(plan.dir_rename.dst.name, "decisions")

    def test_plan_includes_file_renames(self):
        migrate = _migrate
        plan = migrate.plan_rename(self.tmpdir)
        new_names = [fr.dst.name for fr in plan.file_renames]
        self.assertIn("adr-0001-foo.md", new_names)
        self.assertIn("adr-0002-bar.md", new_names)

    def test_plan_includes_cross_ref_rewrites(self):
        migrate = _migrate
        plan = migrate.plan_rename(self.tmpdir)
        rewrite_paths = [r.path.name for r in plan.cross_ref_rewrites]
        self.assertIn("architecture.md", rewrite_paths)


class RenameDryRunTests(unittest.TestCase):
    """AC #2 / #7 — --dry-run emits plan, makes zero filesystem changes."""

    def setUp(self):
        self.tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# ADR-0001\n",
            "docs/adrs/0002-bar.md": "# ADR-0002\n",
            "docs/architecture.md": "See docs/adrs/0001-foo.md\n",
            "CLAUDE.md": "Project notes; refs docs/adrs/0002-bar.md inline.\n",
        })

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dry_run_does_not_mutate_tree(self):
        before = _hash_tree(self.tmpdir)
        r = run_migrate("rename-decisions", str(self.tmpdir), "--dry-run")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        after = _hash_tree(self.tmpdir)
        self.assertEqual(before, after,
                         "dry-run mutated the tree (hash changed)")

    def test_dry_run_output_has_prefix_on_every_line(self):
        r = run_migrate("rename-decisions", str(self.tmpdir), "--dry-run")
        op_lines = [line for line in r.stdout.splitlines()
                    if line.strip() and not line.startswith("#")]
        self.assertTrue(op_lines, f"no op lines: {r.stdout!r}")
        for line in op_lines:
            self.assertTrue(line.startswith("[dry-run]"),
                            f"line missing [dry-run] prefix: {line!r}")

    def test_dry_run_output_is_deterministic(self):
        r1 = run_migrate("rename-decisions", str(self.tmpdir), "--dry-run")
        r2 = run_migrate("rename-decisions", str(self.tmpdir), "--dry-run")
        self.assertEqual(r1.stdout, r2.stdout,
                         "dry-run output not byte-identical across runs")


class RenameApplyTests(unittest.TestCase):
    """AC #1 — apply renames the dir, files, and updates cross-refs."""

    def setUp(self):
        self.tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# ADR-0001 Foo\nSee 0002-bar.md.\n",
            "docs/adrs/0002-bar.md": "# ADR-0002 Bar\n",
            "docs/architecture.md": "Refs: docs/adrs/0001-foo.md and 0002-bar.md.\n",
            "CLAUDE.md": "Reads docs/adrs/0001-foo.md.\n",
        })

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_apply_renames_dir(self):
        r = run_migrate("rename-decisions", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse((self.tmpdir / "docs" / "adrs").exists(),
                         "docs/adrs/ should be gone after rename")
        self.assertTrue((self.tmpdir / "docs" / "decisions").is_dir(),
                        "docs/decisions/ should exist after rename")

    def test_apply_renames_files_with_pad_and_prefix(self):
        r = run_migrate("rename-decisions", str(self.tmpdir))
        self.assertEqual(r.returncode, 0)
        decisions = self.tmpdir / "docs" / "decisions"
        names = sorted(p.name for p in decisions.iterdir())
        self.assertEqual(names, ["adr-0001-foo.md", "adr-0002-bar.md"])

    def test_apply_rewrites_cross_references(self):
        r = run_migrate("rename-decisions", str(self.tmpdir))
        self.assertEqual(r.returncode, 0)
        arch = (self.tmpdir / "docs" / "architecture.md").read_text()
        self.assertIn("docs/decisions/adr-0001-foo.md", arch)
        self.assertNotIn("docs/adrs/", arch)
        # CLAUDE.md should also be rewritten
        claude = (self.tmpdir / "CLAUDE.md").read_text()
        self.assertIn("docs/decisions/adr-0001-foo.md", claude)
        self.assertNotIn("docs/adrs/", claude)


class RenamePadTests(unittest.TestCase):
    """AC #5 — 3-digit padding and adr- prefix handling."""

    def test_3_digit_padded_to_4(self):
        tmpdir = _make_tree({"docs/adrs/001-foo.md": "x\n"})
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            self.assertTrue(
                (tmpdir / "docs" / "decisions" / "adr-0001-foo.md").is_file()
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_existing_adr_prefix_pads_digits(self):
        tmpdir = _make_tree({"docs/adrs/adr-001-foo.md": "x\n"})
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0)
            self.assertTrue(
                (tmpdir / "docs" / "decisions" / "adr-0001-foo.md").is_file()
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_already_canonical_file_left_alone(self):
        tmpdir = _make_tree({"docs/decisions/adr-0001-foo.md": "x\n"})
        try:
            before = _hash_tree(tmpdir)
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0)
            after = _hash_tree(tmpdir)
            self.assertEqual(before, after,
                             "fully-canonical tree mutated unexpectedly")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_sub_3_digit_prefix_left_alone(self):
        """A `1-bar.md` (1-digit) is not normalized — too ambiguous."""
        tmpdir = _make_tree({
            "docs/adrs/1-bar.md": "x\n",
            "docs/adrs/0002-foo.md": "y\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            decisions = tmpdir / "docs" / "decisions"
            names = sorted(p.name for p in decisions.iterdir())
            # 0002-foo.md gets prefix; 1-bar.md is left untouched.
            self.assertIn("adr-0002-foo.md", names)
            self.assertIn("1-bar.md", names)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenamePrefixTests(unittest.TestCase):
    """AC #5 — adr- prefix added when missing."""

    def test_no_prefix_4_digit_gets_prefix(self):
        tmpdir = _make_tree({"docs/adrs/0042-thing.md": "x\n"})
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0)
            self.assertTrue(
                (tmpdir / "docs" / "decisions" / "adr-0042-thing.md").is_file()
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameIdempotencyTests(unittest.TestCase):
    """AC #5 — running twice leaves the tree unchanged after the first run."""

    def test_second_run_is_noop(self):
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# ADR-0001\n",
            "docs/architecture.md": "See docs/adrs/0001-foo.md\n",
        })
        try:
            r1 = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r1.returncode, 0)
            mid = _hash_tree(tmpdir)
            r2 = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r2.returncode, 0)
            end = _hash_tree(tmpdir)
            self.assertEqual(mid, end,
                             "second run mutated the tree (not idempotent)")
            # And the second run's stdout should signal "already aligned"
            # or be empty of operation lines.
            op_lines = [line for line in r2.stdout.splitlines()
                        if line.strip() and "renamed" in line.lower()]
            self.assertEqual(op_lines, [],
                             f"second run did rename ops: {r2.stdout!r}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameConflictTests(unittest.TestCase):
    """AC #3 — both docs/adrs/ and docs/decisions/ present → exit 2."""

    def test_conflict_exits_two(self):
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# foo\n",
            "docs/decisions/adr-0002-bar.md": "# bar\n",
        })
        try:
            before = _hash_tree(tmpdir)
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 2)
            self.assertRegex(r.stderr, r"(?i)conflict")
            after = _hash_tree(tmpdir)
            self.assertEqual(before, after,
                             "conflict refusal still mutated the tree")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameCollisionTests(unittest.TestCase):
    """AC #3 — two files map to the same target name → exit 2."""

    def test_collision_within_source_dir(self):
        # 0001-foo.md → adr-0001-foo.md AND adr-0001-foo.md → adr-0001-foo.md
        # (the canonical one already exists)
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# pre-canonical\n",
            "docs/adrs/adr-0001-foo.md": "# already canonical\n",
        })
        try:
            before = _hash_tree(tmpdir)
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 2)
            self.assertRegex(r.stderr, r"(?i)collision|exists")
            after = _hash_tree(tmpdir)
            self.assertEqual(before, after,
                             "collision refusal still mutated the tree")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameCrossRefTests(unittest.TestCase):
    """AC #6 — cross-reference rewriting scope and exclusions."""

    def test_helper_self_not_rewritten(self):
        """migrate.py and test_migrate.py must never be rewritten — they
        contain the canonical patterns and sample paths."""
        # We exercise this against an actual `docs/adrs/` mention placed in a
        # file colocated with the helper. But since the helper lives outside
        # tempdir, the simpler assertion is: after a real run, migrate.py's
        # content still contains literal `docs/adrs/` (the report subcommand
        # supports both layouts and the file talks about both).
        src_before = MIGRATE_PY.read_text()
        tmpdir = _make_tree({"docs/adrs/0001-foo.md": "x\n"})
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            src_after = MIGRATE_PY.read_text()
            self.assertEqual(src_before, src_after,
                             "migrate.py was rewritten by its own helper")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_binary_file_skipped(self):
        """A binary file under docs/ is not rewritten and not corrupted."""
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "x\n",
            "docs/architecture.md": "ref docs/adrs/0001-foo.md\n",
        })
        # Add a binary file
        bin_path = tmpdir / "docs" / "logo.png"
        bin_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100 + b"docs/adrs/foo"
        bin_path.write_bytes(bin_bytes)
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            self.assertEqual(bin_path.read_bytes(), bin_bytes,
                             "binary file was modified or corrupted")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_skipped_dirs_not_scanned(self):
        """`.git`, `node_modules`, `__pycache__` are skipped."""
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "x\n",
            ".git/HEAD": "docs/adrs/0001-foo.md\n",
            "docs/node_modules/foo.md": "docs/adrs/0001-foo.md\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            git_head = (tmpdir / ".git" / "HEAD").read_text()
            self.assertIn("docs/adrs/", git_head,
                          ".git was rewritten (should be skipped)")
            nm = (tmpdir / "docs" / "node_modules" / "foo.md").read_text()
            self.assertIn("docs/adrs/", nm,
                          "node_modules was rewritten (should be skipped)")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_mixed_canonical_and_legacy_refs_no_corruption(self):
        """Regression from reviewer: a file containing both a legacy
        reference (`docs/adrs/0001-foo.md`) AND an already-canonical
        reference (`docs/decisions/adr-0001-foo.md`) must produce a clean
        result — the canonical reference must NOT become
        `adr-adr-0001-foo.md` from greedy substring substitution.

        This covers the mixed-state tree case (partial prior migration,
        hand-edited references, or self-references in an ADR)."""
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "# ADR-0001\n",
            # Architecture doc mentions both legacy and canonical refs.
            "docs/architecture.md": (
                "Legacy ref: docs/adrs/0001-foo.md.\n"
                "Already canonical: docs/decisions/adr-0001-foo.md.\n"
                "Bare legacy: 0001-foo.md.\n"
                "Bare canonical: adr-0001-foo.md.\n"
            ),
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            arch = (tmpdir / "docs" / "architecture.md").read_text()
            # The canonical reference must NOT have been double-prefixed.
            self.assertNotIn("adr-adr-", arch,
                             f"greedy substitution corrupted canonical ref:\n{arch}")
            # All four references should end up as the canonical form.
            self.assertEqual(arch.count("docs/decisions/adr-0001-foo.md"), 2,
                             f"expected 2 path-prefixed canonical refs:\n{arch}")
            self.assertEqual(arch.count("adr-0001-foo.md"), 4,
                             f"expected 4 total canonical filename mentions:\n{arch}")
            self.assertNotIn("docs/adrs/", arch)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_claude_worktrees_skipped(self):
        """Regression from validator dogfood: `.claude/worktrees/<name>/` is
        a parallel git checkout, not project content. Scanning it would
        rewrite a sibling branch's working tree."""
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "x\n",
            "docs/architecture.md": "ref docs/adrs/0001-foo.md\n",
            ".claude/worktrees/some-branch/docs/architecture.md":
                "should not be touched: docs/adrs/0001-foo.md\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            sibling = (tmpdir / ".claude" / "worktrees" / "some-branch"
                       / "docs" / "architecture.md").read_text()
            self.assertIn("docs/adrs/0001-foo.md", sibling,
                          "worktree was rewritten (should be skipped)")
            # And the in-scope file IS rewritten
            arch = (tmpdir / "docs" / "architecture.md").read_text()
            self.assertIn("docs/decisions/", arch)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_codex_host_scans_agents_and_codex_runtime(self):
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "x\n",
            "docs/architecture.md": "doc ref docs/adrs/0001-foo.md\n",
            "AGENTS.md": "primer ref docs/adrs/0001-foo.md\n",
            ".codex/skills/jig-migrate/SKILL.md":
                "skill ref docs/adrs/0001-foo.md\n",
            ".codex/hooks.json": '{"note":"docs/adrs/0001-foo.md"}\n',
            "CLAUDE.md": "claude ref should remain docs/adrs/0001-foo.md\n",
            ".claude/skills/jig-migrate/SKILL.md":
                "claude skill should remain docs/adrs/0001-foo.md\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir), "--host", "codex")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / "AGENTS.md").read_text(),
            )
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / ".codex" / "skills" / "jig-migrate" / "SKILL.md")
                .read_text(),
            )
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / ".codex" / "hooks.json").read_text(),
            )
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / "docs" / "architecture.md").read_text(),
            )
            self.assertIn("docs/adrs/0001-foo.md",
                          (tmpdir / "CLAUDE.md").read_text())
            self.assertIn(
                "docs/adrs/0001-foo.md",
                (tmpdir / ".claude" / "skills" / "jig-migrate" / "SKILL.md")
                .read_text(),
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_claude_host_keeps_existing_scan_scope(self):
        tmpdir = _make_tree({
            "docs/adrs/0001-foo.md": "x\n",
            "CLAUDE.md": "claude ref docs/adrs/0001-foo.md\n",
            ".claude/skills/jig-migrate/SKILL.md":
                "claude skill ref docs/adrs/0001-foo.md\n",
            "AGENTS.md": "codex primer should remain docs/adrs/0001-foo.md\n",
            ".codex/hooks.json": '{"note":"docs/adrs/0001-foo.md"}\n',
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir), "--host", "claude")
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / "CLAUDE.md").read_text(),
            )
            self.assertIn(
                "docs/decisions/adr-0001-foo.md",
                (tmpdir / ".claude" / "skills" / "jig-migrate" / "SKILL.md")
                .read_text(),
            )
            self.assertIn("docs/adrs/0001-foo.md",
                          (tmpdir / "AGENTS.md").read_text())
            self.assertIn("docs/adrs/0001-foo.md",
                          (tmpdir / ".codex" / "hooks.json").read_text())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameContainmentTests(unittest.TestCase):
    """AC #6 — helper does not operate outside <project-dir>."""

    def test_sibling_dir_untouched(self):
        parent = Path(tempfile.mkdtemp(prefix="jig-mig-cont-"))
        project = _make_tree(
            {"docs/adrs/0001-foo.md": "ref docs/adrs/0001-foo.md\n"},
            root=parent / "project",
        )
        sibling = _make_tree(
            {"docs/adrs/0001-foo.md": "should not be touched\n"},
            root=parent / "sibling",
        )
        try:
            sibling_before = _hash_tree(sibling)
            r = run_migrate("rename-decisions", str(project))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            sibling_after = _hash_tree(sibling)
            self.assertEqual(sibling_before, sibling_after,
                             "sibling dir was touched outside project-dir")
        finally:
            shutil.rmtree(parent, ignore_errors=True)


class RenameAtomicityTests(unittest.TestCase):
    """AC #5 — every write goes through atomic-write or os.replace."""

    def test_no_bare_path_write_text_in_rename_path(self):
        """The mutator region uses _atomic_write (tmp + os.replace), never a
        bare Path.write_text. Read the full file source and check that
        `_atomic_write` is defined and used."""
        src = MIGRATE_PY.read_text()
        # _atomic_write helper must be defined.
        self.assertRegex(src, r"def\s+_atomic_write\s*\(")
        # And it must use os.replace (POSIX-atomic same-FS rename).
        self.assertRegex(src, r"os\.replace\s*\(")


class RenameErrorTests(unittest.TestCase):
    """AC #3 — exit 2 on user error for rename-decisions."""

    def test_missing_dir_arg(self):
        r = run_migrate("rename-decisions")
        self.assertEqual(r.returncode, 2)

    def test_nonexistent_dir(self):
        r = run_migrate("rename-decisions", "/tmp/jig-rename-nope-xyz-zzz")
        self.assertEqual(r.returncode, 2)

    def test_dir_is_file_not_directory(self):
        r = run_migrate("rename-decisions", str(MIGRATE_PY))
        self.assertEqual(r.returncode, 2)

    def test_no_adrs_or_decisions_dir_is_exit_zero(self):
        """A project with no ADR dir at all is exit 0 with 'already aligned'.

        Per AC #4: nothing-to-do is a no-op success, not an error."""
        tmpdir = _make_tree({"docs/workflow.md": "wf\n"})
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            self.assertRegex(r.stdout, r"(?i)already\s+aligned|nothing\s+to")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class RenameSkillSurfaceTests(unittest.TestCase):
    """AC #8 — SKILL.md updated for rename-decisions."""

    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL_MD.read_text()

    def test_skill_mentions_rename_decisions_as_available(self):
        self.assertIn("rename-decisions", self.skill)

    def test_skill_no_longer_says_rename_deferred(self):
        """The 008-01 SKILL.md text said 'rename-decisions (slice 008-02,
        not yet implemented)'. After 008-02 lands, that caveat must go."""
        # Tolerate any forward-looking mention of slice 008-02 (e.g., the
        # commit history reference) but disallow the "not yet implemented"
        # tag on rename-decisions specifically.
        self.assertNotRegex(
            self.skill,
            r"rename-decisions[^\n]*not\s+yet\s+implemented",
        )

    def test_skill_description_has_new_trigger_phrase(self):
        m = re.match(r"---\n(.*?)\n---", self.skill, re.DOTALL)
        fm = m.group(1).lower()
        # AC #8: "apply ADR-0004 to my project" — one of the new triggers
        self.assertIn("apply adr-0004", fm)


class BareIdPaddingTests(unittest.TestCase):
    """Slice 014-01: rename-decisions also pads bare `adr-NNN` ID tokens
    in frontmatter dependencies lists when the corresponding ADR file
    is renamed."""

    def test_flow_list_bare_id_padded(self):
        tmpdir = _make_tree({
            "docs/adrs/001-foo.md": "# ADR-0001 Foo\n",
            "docs/specs/100-spec/spec.md":
                "## Slice 100-01\n\n"
                "---\nstatus: DRAFT\ndependencies: [adr-001]\n---\n\nBody.\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            spec = (tmpdir / "docs/specs/100-spec/spec.md").read_text()
            self.assertIn("dependencies: [adr-0001]", spec)
            self.assertNotIn("adr-001]", spec)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_block_list_bare_id_padded(self):
        tmpdir = _make_tree({
            "docs/adrs/002-bar.md": "# ADR-0002 Bar\n",
            "docs/specs/200-spec/spec.md":
                "## Slice 200-01\n\n"
                "---\nstatus: DRAFT\ndependencies:\n  - adr-002\n---\n\nBody.\n",
        })
        try:
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
            spec = (tmpdir / "docs/specs/200-spec/spec.md").read_text()
            self.assertIn("- adr-0002", spec)
            self.assertNotIn("- adr-002\n", spec)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_already_canonical_id_unchanged(self):
        """`adr-0001` (already canonical) must not be touched when its
        file is not being renamed."""
        tmpdir = _make_tree({
            "docs/decisions/adr-0001-foo.md": "# ADR-0001 Foo\n",
            "docs/specs/300-spec/spec.md":
                "## Slice 300-01\n\n"
                "---\nstatus: DRAFT\ndependencies: [adr-0001]\n---\n\nBody.\n",
        })
        try:
            # Already canonical: should report "nothing to do"
            r = run_migrate("rename-decisions", str(tmpdir))
            self.assertEqual(r.returncode, 0)
            spec = (tmpdir / "docs/specs/300-spec/spec.md").read_text()
            self.assertIn("dependencies: [adr-0001]", spec)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


SPEC_MD_TWO_SLICES = """\
---
status: DRAFT
skill: spec-workflow
tier: 1
---

# Spec 999: demo

## Overview

Demo spec for split-slices tests.

## Decomposition

S — Spike: none.

### Slices

- 999-01 — alpha
- 999-02 — beta

---

## Slice 999-01 — alpha

---
status: DONE
dependencies: []
last_verified:
---

**Goal:** First slice body.

**DoD:**
- [x] Done.

---

## Slice 999-02 — beta

---
status: DRAFT
dependencies: [999-01]
last_verified:
---

**Goal:** Second slice body.
"""


SPEC_MD_NO_SLICES = """\
---
status: DRAFT
---

# Spec 998: no-slices

## Overview

This spec has no slices yet.

## Decomposition

_TBD_
"""


class SplitSlicesTests(unittest.TestCase):
    """Slice 018-04 ACs: `migrate.py split-slices <spec-dir>`."""

    def setUp(self):
        import tempfile
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-mig-split-"))
        self.spec_dir = self.tmpdir / "999-demo"
        self.spec_dir.mkdir()
        self.spec_md = self.spec_dir / "spec.md"
        self.spec_md.write_text(SPEC_MD_TWO_SLICES)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # AC #1, #2: subcommand exists; one file per slice.
    def test_split_writes_one_file_per_slice(self):
        r = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        files = sorted(p.name for p in self.spec_dir.glob("slice-*.md"))
        self.assertEqual(files, ["slice-01-alpha.md", "slice-02-beta.md"])

    # AC #2: slice file frontmatter at top, heading after.
    def test_slice_file_has_frontmatter_at_top(self):
        run_migrate("split-slices", str(self.spec_dir))
        text = (self.spec_dir / "slice-01-alpha.md").read_text()
        self.assertTrue(text.startswith("---\n"),
                        f"expected `---` at top, got: {text[:50]!r}")
        # Heading must follow the closing frontmatter
        fm_end = text.index("\n---\n", 4)
        self.assertIn("## Slice 999-01 — alpha", text[fm_end:])
        # Frontmatter preserved verbatim
        self.assertIn("status: DONE", text)
        self.assertIn("dependencies: []", text)

    # AC #3: spec.md drops `## Slice` sections, gets a `## Slices` link list.
    def test_spec_md_rewritten_drops_slices_adds_link_section(self):
        run_migrate("split-slices", str(self.spec_dir))
        text = self.spec_md.read_text()
        self.assertNotIn("## Slice 999-01", text)
        self.assertNotIn("## Slice 999-02", text)
        # `## Slices` link list at the bottom
        self.assertIn("## Slices", text)
        self.assertIn("[999-01 — alpha](slice-01-alpha.md)", text)
        self.assertIn("[999-02 — beta](slice-02-beta.md)", text)
        # Prefix preserved (header + overview + decomposition)
        self.assertIn("# Spec 999: demo", text)
        self.assertIn("## Overview", text)
        self.assertIn("## Decomposition", text)

    # AC #4: --dry-run writes nothing.
    def test_dry_run_writes_nothing(self):
        before = self.spec_md.read_text()
        r = run_migrate("split-slices", str(self.spec_dir), "--dry-run")
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertIn("[dry-run]", r.stdout)
        self.assertIn("slice-01-alpha.md", r.stdout)
        self.assertIn("slice-02-beta.md", r.stdout)
        # No slice files written
        self.assertEqual(sorted(p.name for p in self.spec_dir.glob("slice-*.md")), [])
        # spec.md unchanged
        self.assertEqual(self.spec_md.read_text(), before)

    # AC #5: refuses on conflict, no partial writes.
    def test_refuses_on_existing_target_file(self):
        # Pre-create a conflicting slice file
        (self.spec_dir / "slice-01-alpha.md").write_text("blocking content")
        r = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r.returncode, 2,
                         f"expected exit 2, got: stderr={r.stderr} stdout={r.stdout}")
        self.assertIn("refusing", r.stdout.lower())
        self.assertIn("slice-01-alpha.md", r.stdout)
        # No partial writes: slice-02-beta.md must NOT exist
        self.assertFalse((self.spec_dir / "slice-02-beta.md").exists())
        # spec.md UNTOUCHED — content is the original two-slice spec.
        self.assertEqual(self.spec_md.read_text(), SPEC_MD_TWO_SLICES)

    # AC #6: idempotent — no slices to split → exit 0 with no-op message.
    def test_idempotent_when_no_slices_in_spec_md(self):
        self.spec_md.write_text(SPEC_MD_NO_SLICES)
        r = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r.returncode, 0)
        self.assertIn("nothing to split", r.stdout)
        # No slice files emitted
        self.assertEqual(sorted(p.name for p in self.spec_dir.glob("slice-*.md")), [])

    # AC #8: label-to-filename derivation — special chars / hyphens.
    def test_slug_derivation_handles_punctuation_and_spaces(self):
        spec_dir = self.tmpdir / "777-tricky"
        spec_dir.mkdir()
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "# Spec 777\n\n## Decomposition\n\n_TBD_\n\n"
            "---\n\n## Slice 777-01 — Foo Bar/Baz!\n\n"
            "**Goal:** Tricky shortname.\n"
        )
        r = run_migrate("split-slices", str(spec_dir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        # `/` and `!` dropped, space → `-`, lowercased
        files = sorted(p.name for p in spec_dir.glob("slice-*.md"))
        self.assertEqual(files, ["slice-01-foo-barbaz.md"])

    # AC #8: heading-after-split is still resolvable via iter_slices.
    def test_iter_slices_after_split_yields_both_slice_files(self):
        run_migrate("split-slices", str(self.spec_dir))
        sys.path.insert(0, str(REPO_ROOT / "skills" / "_common"))
        from parsing import iter_slices
        locs = list(iter_slices(self.spec_md))
        labels = sorted(sl.label for sl in locs)
        self.assertEqual(labels, ["999-01 — alpha", "999-02 — beta"])
        # All come from slice files now, not spec.md
        self.assertTrue(all(sl.path.name.startswith("slice-")
                            for sl in locs),
                        f"expected all slice files, got: {[sl.path.name for sl in locs]}")

    # AC #7-ish: --dry-run writes nothing, exit 0
    def test_dry_run_exits_zero(self):
        r = run_migrate("split-slices", str(self.spec_dir), "--dry-run")
        self.assertEqual(r.returncode, 0)

    def test_missing_spec_md_returns_exit_two(self):
        empty = self.tmpdir / "empty"
        empty.mkdir()
        r = run_migrate("split-slices", str(empty))
        self.assertEqual(r.returncode, 2)
        self.assertIn("spec.md not found", r.stdout)

    # Reviewer §SPECIFIC ISSUES — legacy-shape (no frontmatter) split.
    def test_legacy_shape_slice_without_frontmatter(self):
        """Spec 017's slices predate per-slice frontmatter: heading is
        followed directly by prose `**STATUS: ...**` instead of a
        `---\\n...---\\n` block. The split must produce a slice file
        that starts with the heading on line 1 (no synthesized
        frontmatter), and `iter_slices` must still resolve it."""
        spec_dir = self.tmpdir / "888-legacy"
        spec_dir.mkdir()
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "# Spec 888\n\n## Overview\n\nOld-style.\n\n"
            "## Slice 888-01 — legacy-shape\n\n"
            "**STATUS: DONE**\n\n"
            "**Goal:** A slice authored before frontmatter conventions.\n"
        )
        r = run_migrate("split-slices", str(spec_dir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        target = spec_dir / "slice-01-legacy-shape.md"
        self.assertTrue(target.is_file())
        text = target.read_text()
        # File starts with the heading, NOT `---`.
        self.assertTrue(text.startswith("## Slice 888-01"),
                        f"legacy-shape slice should start with heading; "
                        f"got: {text[:50]!r}")
        # Body preserved verbatim
        self.assertIn("**STATUS: DONE**", text)
        self.assertIn("A slice authored before frontmatter conventions.", text)

    # Reviewer §SPECIFIC ISSUES — split twice is a no-op.
    def test_split_is_idempotent_on_rerun(self):
        """AC #6 idempotency: running split-slices on a spec.md that's
        already been split (no `## Slice` sections remain) is a no-op
        that exits 0 with the canonical message."""
        r1 = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r1.returncode, 0)
        r2 = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r2.returncode, 0)
        self.assertIn("nothing to split", r2.stdout)
        # Re-run did NOT modify the slice files
        slice1_first = (self.spec_dir / "slice-01-alpha.md").read_text()
        r3 = run_migrate("split-slices", str(self.spec_dir))
        self.assertEqual(r3.returncode, 0)
        self.assertEqual(
            (self.spec_dir / "slice-01-alpha.md").read_text(),
            slice1_first,
            "split-slices on already-split dir must not touch slice files",
        )

    # Reviewer §SPECIFIC ISSUES — horizontal rules in body don't break FM detection.
    def test_horizontal_rule_in_body_not_treated_as_frontmatter(self):
        """A slice body that opens with `\\n---\\n` (a horizontal rule
        separator) followed by prose then another `---` must NOT be
        misidentified as a YAML frontmatter block. The guard requires
        a `key:` line inside the captured `---...---` window."""
        spec_dir = self.tmpdir / "777-hr"
        spec_dir.mkdir()
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(
            "# Spec 777\n\n## Overview\n\nx.\n\n"
            "## Slice 777-01 — hr-body\n\n"
            "---\n\n"  # horizontal rule, no `key:` lines
            "Body paragraph one.\n\n"
            "---\n\n"  # another horizontal rule
            "Body paragraph two.\n"
        )
        r = run_migrate("split-slices", str(spec_dir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        text = (spec_dir / "slice-01-hr-body.md").read_text()
        # Must start with the heading — the `---\n...\n---\n` window
        # was correctly identified as hr-pair, not frontmatter.
        self.assertTrue(text.startswith("## Slice 777-01"))
        # Both horizontal rules + paragraphs preserved in body
        self.assertIn("Body paragraph one.", text)
        self.assertIn("Body paragraph two.", text)


WORKED_EXAMPLE = REPO_ROOT / "skills" / "migrate" / "worked-example-slice-to-spec.md"


class SliceToSpecSkillTests(unittest.TestCase):
    """Slice 020-01: surface-pinning tests for the agentic slice-to-spec
    workflow documented in SKILL.md + worked-example sibling. No
    `migrate.py` code is exercised — this slice ships markdown only."""

    @classmethod
    def setUpClass(cls):
        cls.skill_text = SKILL_MD.read_text()
        cls.worked_text = (WORKED_EXAMPLE.read_text()
                           if WORKED_EXAMPLE.is_file() else "")

    # AC #1: dedicated section heading.
    def test_skill_md_has_slice_to_spec_section(self):
        self.assertIn("## Agentic slice-to-spec migration",
                      self.skill_text,
                      "SKILL.md missing the agentic slice-to-spec section")

    # AC #2: state translation table.
    def test_skill_md_has_state_translation_table(self):
        # The table must mention the canonical 4-state vocabulary AND
        # the jig 7-state vocabulary together.
        for state_4 in ("Draft", "Ready", "In Progress", "Done"):
            self.assertIn(state_4, self.skill_text,
                          f"4-state token {state_4!r} missing from SKILL.md")
        for state_7 in ("DRAFT", "READY_FOR_IMPLEMENTATION",
                        "IN_PROGRESS", "DONE"):
            self.assertIn(state_7, self.skill_text,
                          f"jig-state token {state_7!r} missing from SKILL.md")
        # The "Ready → READY_FOR_IMPLEMENTATION" mapping is the
        # most lossy translation — its rationale must be explicit.
        # Check for the key phrase in any case.
        lower = self.skill_text.lower()
        self.assertTrue(
            "ready to start work" in lower or "not \"ready for spec review\"" in lower,
            "SKILL.md should explain why Ready maps past READY_FOR_REVIEW",
        )

    # AC #3: algorithm-as-steps with the canonical step list.
    def test_skill_md_has_algorithm_steps(self):
        # Spot-check each of the 6 canonical steps. Phrasing is flexible
        # but the concept must appear.
        for token in ("milestone summaries", "milestone → spec mapping",
                      "frontmatter", "originals", "iter_slices",
                      "spec_lint", "status-board"):
            self.assertIn(token, self.skill_text,
                          f"algorithm step token {token!r} missing")

    # AC #4: worked example file exists with key sections.
    def test_worked_example_file_present(self):
        self.assertTrue(WORKED_EXAMPLE.is_file(),
                        f"worked example missing at {WORKED_EXAMPLE}")
        self.assertGreater(len(self.worked_text), 1000,
                           "worked example suspiciously short")

    def test_worked_example_documents_m1_dogfood(self):
        # The dogfood was on shallow-validator M1 — that name should appear.
        self.assertIn("shallow-validator", self.worked_text)
        self.assertIn("M1", self.worked_text)
        # Before/after slice snippets must be present
        self.assertIn("# Slice 01", self.worked_text,
                      "worked example missing source-shape snippet")
        self.assertIn("## Slice 001-01", self.worked_text,
                      "worked example missing target-shape snippet")
        # The result must show iter_slices / spec_lint / status-board outputs
        self.assertIn("iter_slices", self.worked_text)
        self.assertIn("spec_lint", self.worked_text)
        self.assertIn("status-board", self.worked_text)

    # AC #5: skill description updated to mention the new workflow.
    def test_skill_description_mentions_slice_to_spec(self):
        # Frontmatter description block (between `---` lines at file top).
        m = re.match(r"---\n(.*?)\n---\n", self.skill_text, re.DOTALL)
        self.assertIsNotNone(m, "SKILL.md missing frontmatter block")
        fm = m.group(1).lower()
        self.assertTrue(
            "slice-to-spec" in fm or "flat slices into nested specs" in fm,
            "frontmatter description must mention the new agentic workflow",
        )

    # AC #6 sanity check: no `migrate.py slice-to-spec` subcommand exists.
    def test_no_slice_to_spec_subcommand_in_migrate_py(self):
        migrate_py = (REPO_ROOT / "skills" / "migrate" / "migrate.py").read_text()
        # The string `slice-to-spec` MAY appear in comments / docstrings
        # discussing the deferral, but NOT as an argparse subparser.
        self.assertNotIn('add_parser(\n        "slice-to-spec"', migrate_py)
        self.assertNotIn('add_parser("slice-to-spec"', migrate_py)


# ==========================================================================
# Slice 021-01 — copy-machinery subcommand
# ==========================================================================

import json as _json


def _seed_spec_driven_project(root: Path) -> None:
    """Build a tiny spec-driven project layout the way slice 008-05 expects
    it (so `report` returns `adoptable`). Used by CopyMachineryTests and
    CopyMachineryOperationsTests."""
    (root / "docs" / "specs" / "001-demo").mkdir(parents=True)
    (root / "docs" / "specs" / "001-demo" / "spec.md").write_text(
        "# Spec 001\n\n## Overview\n\nDemo.\n"
    )
    (root / "docs" / "decisions").mkdir(parents=True)
    (root / "docs" / "decisions" / "adr-0001-demo.md").write_text(
        "# ADR-0001 demo\n"
    )
    (root / "docs" / "workflow.md").write_text("# Workflow\n")
    (root / "docs" / "architecture.md").write_text("# Architecture\n")


class CopyMachineryTests(unittest.TestCase):
    """Slice 021-01 — `migrate.py copy-machinery <project-dir>` reuses
    scaffold-mode's machinery copy via the public `copy_machinery()`
    façade.

    Maps to AC #2 (subcommand registered), AC #3 (subcommand calls the
    façade), AC #4 (UnmanagedHooksError refuses cleanly), AC #5
    (idempotent re-run), AC #8 (a-e: skills + hooks + settings + refuse
    + idempotency)."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-021-copy-mach-"))
        _seed_spec_driven_project(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ----- AC #1 — public façade exists and is callable --------------------
    def test_public_facade_is_importable_from_scaffold(self):
        """AC #1 — `copy_machinery(plugin, target, *, force=False)` is
        importable from `skills/scaffold-init/scaffold.py`. The dir name
        has a hyphen, so dotted-package imports don't work — we mirror
        the same `spec_from_file_location` pattern migrate.py uses
        internally to load scaffold (inbox 2026-05-13 follow-up).
        """
        scaffold_py = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
        spec = _ilu.spec_from_file_location("_scaffold_for_test", scaffold_py)
        mod = _ilu.module_from_spec(spec)
        sys.modules[spec.name] = mod
        sys.modules.setdefault("_scaffold_for_test", mod)
        spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod, "copy_machinery", None)),
                        "copy_machinery is not callable on scaffold module")

    # ----- AC #2 — subcommand registered -----------------------------------
    def test_copy_machinery_subcommand_is_registered(self):
        """AC #2 — invoking `migrate.py copy-machinery --help` returns
        exit 0 with usage referencing project_dir + --force."""
        r = run_migrate("copy-machinery", "--help")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("project", r.stdout.lower())
        self.assertIn("--force", r.stdout)
        self.assertIn("hook configuration", r.stdout)
        self.assertNotIn("settings.json", r.stdout)

    # ----- AC #3 — subcommand exits 0 on success ---------------------------
    def test_subcommand_returns_zero_on_clean_target(self):
        """AC #3 — `copy-machinery <dir>` against a clean spec-driven
        project (no pre-existing `.claude/settings.json`) returns exit 0."""
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")

    # ----- AC #8 (a) — skills copied with rewritten SKILL.md ---------------
    def test_8a_skills_copied_with_rewritten_skill_md(self):
        """AC #8 (a) — `.claude/skills/jig-migrate/` exists with a
        SKILL.md whose `${CLAUDE_PLUGIN_ROOT}/skills/` path strings have
        been rewritten."""
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        copied = (self.tmpdir / ".claude" / "skills" / "jig-migrate"
                  / "SKILL.md")
        self.assertTrue(copied.is_file(), f"missing: {copied}")
        body = copied.read_text()
        # No raw plugin-root paths survive in the body
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}/skills/", body,
                         "SKILL.md still has plugin-root path strings")
        # Agents copied too
        agents_dir = self.tmpdir / ".claude" / "agents"
        agents = sorted(p.name for p in agents_dir.glob("jig-*.md"))
        self.assertTrue(agents,
                        f"no jig-prefixed agents copied: {list(agents_dir.iterdir())}")

    # ----- AC #8 (b) — hook scripts present with 0o755 perms ---------------
    def test_8b_hook_scripts_present_and_executable(self):
        """AC #8 (b) — `.claude/hooks/scripts/` has at least one
        `jig-*.sh` and every script has mode 0o755."""
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        scripts_dir = self.tmpdir / ".claude" / "hooks" / "scripts"
        self.assertTrue(scripts_dir.is_dir(),
                        f"missing scripts dir: {scripts_dir}")
        scripts = sorted(scripts_dir.glob("jig-*.sh"))
        self.assertTrue(scripts, f"no jig-*.sh scripts in {scripts_dir}")
        for s in scripts:
            mode = s.stat().st_mode & 0o777
            self.assertEqual(
                mode, 0o755,
                f"{s} has mode {oct(mode)}, expected 0o755",
            )

    # ----- AC #8 (c) — settings.json marker on every hook entry ------------
    def test_8c_settings_json_marks_every_hook_entry(self):
        """AC #8 (c) — `.claude/settings.json` exists and every hook
        entry under `hooks.<event>` has `metadata.managed_by_jig: true`."""
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        settings_path = self.tmpdir / ".claude" / "settings.json"
        self.assertTrue(settings_path.is_file(),
                        f"missing: {settings_path}")
        settings = _json.loads(settings_path.read_text())
        hooks = settings.get("hooks") or {}
        self.assertTrue(hooks, "settings.json has no hooks")
        for event, entries in hooks.items():
            self.assertTrue(entries, f"event {event} has no entries")
            for entry in entries:
                meta = entry.get("metadata") or {}
                self.assertTrue(
                    meta.get("managed_by_jig"),
                    f"entry under {event} missing managed_by_jig marker: "
                    f"{entry}",
                )

    # ----- AC #8 (d) — UnmanagedHooksError refusal exits 3 ----------------
    def test_8d_unmanaged_hooks_refusal_exits_three(self):
        """AC #8 (d) — pre-seed `.claude/settings.json` with a non-jig
        hook entry. Subcommand must exit 3, emit `--force` in the
        refuse-message on stderr, leave stdout empty."""
        settings_path = self.tmpdir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(_json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        }, indent=2) + "\n")
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(
            r.returncode, 3,
            f"expected exit 3 on unmanaged hooks; got {r.returncode} "
            f"(stdout={r.stdout!r} stderr={r.stderr!r})",
        )
        self.assertIn("--force", r.stderr,
                      f"refuse-message must mention --force: {r.stderr!r}")
        self.assertEqual(
            r.stdout, "",
            f"stdout must stay empty on refusal; got: {r.stdout!r}",
        )

    # ----- Inbox 2026-05-15 — no partial state when refusal fires ---------
    def test_unmanaged_hooks_refusal_leaves_no_partial_state(self):
        """Inbox 2026-05-15 (spec 016-03 deviation §7 carryover): the
        `copy_machinery()` façade ran `_copy_skills_and_agents` BEFORE the
        hooks safety check, leaving copied jig-* skill/agent files behind
        when the refusal fired. Pre-flight safety check now runs first,
        so a refused call must leave `.claude/skills/` and `.claude/agents/`
        untouched.
        """
        settings_path = self.tmpdir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(_json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        }, indent=2) + "\n")
        # No `.claude/skills/` or `.claude/agents/` exists yet
        skills_root = self.tmpdir / ".claude" / "skills"
        agents_root = self.tmpdir / ".claude" / "agents"
        hooks_scripts = self.tmpdir / ".claude" / "hooks" / "scripts"
        self.assertFalse(skills_root.exists())
        self.assertFalse(agents_root.exists())
        self.assertFalse(hooks_scripts.exists())

        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 3, f"stderr: {r.stderr}")

        # Nothing should have been written on the refusal path.
        self.assertFalse(
            skills_root.exists(),
            f"refusal left jig-* skills on disk: "
            f"{list(skills_root.iterdir()) if skills_root.exists() else None}",
        )
        self.assertFalse(
            agents_root.exists(),
            f"refusal left jig-* agents on disk: "
            f"{list(agents_root.iterdir()) if agents_root.exists() else None}",
        )
        self.assertFalse(
            hooks_scripts.exists(),
            f"refusal left hook scripts on disk: "
            f"{list(hooks_scripts.iterdir()) if hooks_scripts.exists() else None}",
        )
        # Settings.json must also be untouched (preserved verbatim).
        preserved = _json.loads(settings_path.read_text())
        self.assertEqual(
            preserved["hooks"]["PreToolUse"][0]["matcher"], "Edit",
            "user's settings.json was modified despite refusal",
        )

    # ----- AC #8 (e) — idempotent re-run -----------------------------------
    def test_8e_idempotent_rerun(self):
        """AC #8 (e) — running `copy-machinery` against a `.claude/`
        already populated by a prior run is a byte-stable no-op (modulo
        the in-place file overwrites which produce identical content).
        Hash the relevant subtree before/after the second run."""
        r1 = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r1.returncode, 0,
                         f"first run failed: {r1.stderr}")
        claude_dir = self.tmpdir / ".claude"
        before = _hash_tree(claude_dir)
        r2 = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r2.returncode, 0,
                         f"second run failed: {r2.stderr}")
        after = _hash_tree(claude_dir)
        self.assertEqual(
            before, after,
            "idempotent re-run mutated .claude/ tree (hash drift)",
        )

    # ----- AC #4 + AC #5 — force overrides unmanaged-hooks refusal ---------
    def test_force_flag_overrides_unmanaged_hooks(self):
        """AC #4 — `--force` is the documented escape. With the flag,
        the merge proceeds and the user's pre-existing entry survives."""
        settings_path = self.tmpdir / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(_json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Edit",
                     "hooks": [{"type": "command",
                                "command": "bash ./user-edit.sh",
                                "timeout": 5}]}
                ]
            }
        }, indent=2) + "\n")
        r = run_migrate("copy-machinery", str(self.tmpdir), "--force")
        self.assertEqual(r.returncode, 0,
                         f"--force should succeed; stderr: {r.stderr}")
        merged = _json.loads(settings_path.read_text())
        pre_tool_use = merged["hooks"]["PreToolUse"]
        user_present = any(
            entry.get("matcher") == "Edit"
            and entry.get("hooks", [{}])[0].get("command", "").endswith(
                "user-edit.sh"
            )
            for entry in pre_tool_use
        )
        self.assertTrue(
            user_present,
            "user's Edit-matcher hook was clobbered under --force",
        )


class CodexCopyMachineryTests(unittest.TestCase):
    """Slice 059-01 — host-aware `copy-machinery` for Codex scaffold mode."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-059-codex-copy-"))
        _seed_spec_driven_project(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_copy_machinery_host_codex_writes_codex_runtime_only(self):
        r = run_migrate("copy-machinery", str(self.tmpdir), "--host", "codex")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertIn(str(self.tmpdir / ".codex"), r.stdout)
        self.assertTrue(
            (self.tmpdir / ".codex" / "skills" / "jig-migrate" / "SKILL.md")
            .is_file(),
            "Codex migrate skill was not copied",
        )
        self.assertTrue(
            (self.tmpdir / ".codex" / "agents" / "jig-reviewer.toml").is_file(),
            "Codex TOML agents were not copied",
        )
        self.assertTrue(
            (self.tmpdir / ".codex" / "hooks.json").is_file(),
            "Codex hooks config was not written",
        )
        self.assertFalse(
            (self.tmpdir / ".claude").exists(),
            "Codex copy-machinery must not create Claude runtime files",
        )

    def test_copy_machinery_host_codex_renders_honest_migrate_skill(self):
        r = run_migrate("copy-machinery", str(self.tmpdir), "--host", "codex")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        body = (
            self.tmpdir / ".codex" / "skills" / "jig-migrate" / "SKILL.md"
        ).read_text()
        self.assertIn("--host codex", body)
        self.assertIn(".codex/", body)
        self.assertIn("AGENTS.md", body)
        self.assertIn(
            "Use `--host codex` when invoking from Codex-facing source "
            "or plugin docs.",
            body,
        )
        self.assertIn("Copies Codex agents into `.codex/agents/jig-*.toml`.", body)
        self.assertIn("copy-machinery <project-dir> --host codex --force", body)
        self.assertNotIn("copy-machinery` remains Claude-only", body)
        self.assertNotIn(".claude/settings.json", body)
        self.assertNotIn(".codex/settings.json", body)
        self.assertNotIn("`.codex/agents/jig-*.toml`.codex", body)
        self.assertNotIn("--host claude", body)
        self.assertNotIn("`--host claude` writes Codex", body)
        self.assertNotIn("all other invocations infer Codex", body)
        self.assertNotIn("Non-jig hooks in an existing settings.json survive", body)
        self.assertNotIn("read-only EXCEPT", body)
        self.assertNotIn("For Codex, this means .codex/settings.json", body)

    def test_copy_machinery_host_codex_refuses_unmanaged_hooks_json_cleanly(self):
        hooks_path = self.tmpdir / ".codex" / "hooks.json"
        hooks_path.parent.mkdir(parents=True, exist_ok=True)
        hooks_path.write_text('{"hooks": {"PreToolUse": []}}\n')
        r = run_migrate("copy-machinery", str(self.tmpdir), "--host", "codex")
        self.assertEqual(r.returncode, 3, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertIn("--force", r.stderr)
        self.assertFalse(
            (self.tmpdir / ".codex" / "skills").exists(),
            "refused Codex copy left partial skills on disk",
        )

    def test_copied_codex_helper_auto_rerun_does_not_jig_jig(self):
        r = run_migrate("copy-machinery", str(self.tmpdir), "--host", "codex")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        codex_root = self.tmpdir / ".codex"
        copied_helper = codex_root / "skills" / "jig-migrate" / "migrate.py"
        self.assertTrue(copied_helper.is_file(), copied_helper)
        before = _hash_tree(codex_root)

        env = os.environ.copy()
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        rerun = subprocess.run(
            [sys.executable, str(copied_helper), "copy-machinery", str(self.tmpdir)],
            cwd=self.tmpdir,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(
            rerun.returncode, 0,
            f"copied helper rerun failed: stdout={rerun.stdout!r} "
            f"stderr={rerun.stderr!r}",
        )
        self.assertEqual(
            _hash_tree(codex_root), before,
            "copied Codex helper rerun should be byte-stable",
        )
        bad = sorted((codex_root / "skills").glob("jig-jig-*"))
        self.assertEqual(bad, [], f"copied helper created double-prefixed dirs: {bad}")


class CopyMachinerySecurityFloorTests(unittest.TestCase):
    """Slice 052-04 AC1/AC2 — `migrate copy-machinery` brings the security
    floor to an existing jig project: the `.gitignore` secret block, the
    `permissions.deny` defaults, and the secret-scan hook registration all
    land, idempotently and without clobbering pre-existing user content.

    The floor is ungated infra (AC2): it lands regardless of the target's
    `installed_tiers` (these projects have no scaffold.json → copy-all)."""

    GITIGNORE_MARKER = "# >>> jig secret-ignore >>>"
    DENY_GLOBS = (
        "Bash(git push --force*)",
        "Bash(git reset --hard*)",
        "Bash(rm -rf*)",
    )

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-052-04-mig-"))
        _seed_spec_driven_project(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _read_settings(self) -> dict:
        return _json.loads(
            (self.tmpdir / ".claude" / "settings.json").read_text()
        )

    def _deny(self) -> list:
        return self._read_settings().get("permissions", {}).get("deny", [])

    def _secret_scan_registered(self) -> bool:
        pre = self._read_settings().get("hooks", {}).get("PreToolUse", [])
        for entry in pre:
            if entry.get("matcher") != "Edit|Write|MultiEdit":
                continue
            if not (entry.get("metadata") or {}).get("managed_by_jig"):
                continue
            for h in entry.get("hooks", []):
                if "jig-secret-scan.sh" in (h.get("command") or ""):
                    return True
        return False

    # ----- AC1 — the .gitignore floor lands -----
    def test_copy_machinery_writes_gitignore_secret_floor(self):
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}\nstdout: {r.stdout}")
        gi = self.tmpdir / ".gitignore"
        self.assertTrue(gi.is_file(),
                        "migrate copy-machinery must write .gitignore")
        text = gi.read_text()
        self.assertIn(self.GITIGNORE_MARKER, text)
        self.assertIn(".env", text)
        self.assertIn("*.pem", text)

    # ----- AC1 — permissions.deny defaults land -----
    def test_copy_machinery_merges_permissions_deny(self):
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        deny = self._deny()
        for glob in self.DENY_GLOBS:
            self.assertIn(glob, deny,
                          f"migrate copy-machinery missing deny glob: {glob}")

    # ----- AC1 — secret-scan hook registered -----
    def test_copy_machinery_registers_secret_scan_hook(self):
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(
            self._secret_scan_registered(),
            "migrate copy-machinery did not register the secret-scan hook",
        )

    # ----- AC1 — idempotent: no duplicate .gitignore block on re-run -----
    def test_copy_machinery_gitignore_idempotent(self):
        r1 = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r1.returncode, 0, f"stderr: {r1.stderr}")
        r2 = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r2.returncode, 0, f"stderr: {r2.stderr}")
        text = (self.tmpdir / ".gitignore").read_text()
        self.assertEqual(
            text.count(self.GITIGNORE_MARKER), 1,
            "re-run duplicated the jig secret-ignore block",
        )

    # ----- AC1 — pre-existing user .gitignore content survives -----
    def test_copy_machinery_preserves_user_gitignore_lines(self):
        gi = self.tmpdir / ".gitignore"
        gi.write_text("# my project\nnode_modules/\ndist/\n")
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        text = gi.read_text()
        self.assertIn("node_modules/", text)
        self.assertIn("dist/", text)
        self.assertIn("# my project", text)
        self.assertIn(self.GITIGNORE_MARKER, text)


class CopyMachineryOperationsTests(unittest.TestCase):
    """Slice 021-01 AC #6 + AC #9 — `migrate.py report` surfaces the new
    subcommand in its Operations section when the verdict is `adoptable`
    or `partial` AND the target's `.claude/skills/` has no pre-existing
    `jig-*` skill dir. Suppressed once the skills are in place."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-021-ops-"))
        _seed_spec_driven_project(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ----- AC #6 — operations section names copy-machinery -----------------
    def test_operations_section_suggests_copy_machinery_when_absent(self):
        """AC #6 / AC #9 — adoptable verdict + no `.claude/skills/jig-*`
        on disk → Operations section names `copy-machinery`."""
        r = run_migrate("report", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}")
        self.assertIn("## Operations", r.stdout)
        self.assertIn("copy-machinery", r.stdout)

    # ----- AC #9 — suppressed when jig-* skill dir already present --------
    def test_operations_section_suppresses_when_jig_skills_present(self):
        """AC #9 — same project, but with a COMPLETE jig install present
        (`.claude/skills/jig-*/` AND `.claude/templates/`), must NOT mention
        `copy-machinery` in Operations. The Inventory row may still
        reference `copy-machinery` as the refresh path; the suppression
        rule is scoped to the Operations section.

        Slice 095-01: templates are part of a complete install, so the
        fixture seeds them too — without a templates tree this is the
        pre-095 shape the backfill nudge (below) deliberately flags.
        """
        jig_dir = self.tmpdir / ".claude" / "skills" / "jig-migrate"
        jig_dir.mkdir(parents=True)
        (jig_dir / "SKILL.md").write_text("seed\n")
        templates = self.tmpdir / ".claude" / "templates" / "docs" / "decisions"
        templates.mkdir(parents=True)
        (templates / "lightweight-decisions.md.template").write_text("seed\n")
        r = run_migrate("report", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}")
        self.assertIn("## Operations", r.stdout)
        # Scope the check to the Operations section only.
        ops_marker = "## Operations"
        ops_section = r.stdout[r.stdout.index(ops_marker):]
        self.assertNotIn(
            "copy-machinery", ops_section,
            f"operations should suppress copy-machinery when "
            f"jig-* skills exist: {ops_section!r}",
        )

    # ----- Inbox 2026-05-15 — jig-managed skills row in Inventory ---------
    def test_inventory_surfaces_jig_managed_skills(self):
        """Inbox 2026-05-15 — without this row, AC #9's Operations
        suppression looked unexplained: the user sees agents listed but
        nothing for `.claude/skills/` even though 12 jig-* dirs are present.
        The fix adds a separate Inventory row that names them and points at
        `copy-machinery` for refresh.
        """
        # Drop two jig-* dirs into the seed project
        for name in ("jig-migrate", "jig-spec-workflow"):
            jig_dir = self.tmpdir / ".claude" / "skills" / name
            jig_dir.mkdir(parents=True)
            (jig_dir / "SKILL.md").write_text("seed\n")
        r = run_migrate("report", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}")
        self.assertIn("## Inventory", r.stdout)
        # New row exists and names the jig-managed skills
        self.assertIn("(jig-managed)", r.stdout)
        self.assertIn("jig-migrate", r.stdout)
        self.assertIn("jig-spec-workflow", r.stdout)
        # And points at the refresh path
        self.assertIn("copy-machinery", r.stdout)

    def test_inventory_omits_jig_row_when_no_jig_skills_present(self):
        """The new row appears only when jig_skill_dirs is non-empty.
        Same seed project, no jig-* dirs, so the row should be absent."""
        r = run_migrate("report", str(self.tmpdir))
        self.assertEqual(r.returncode, 0,
                         f"stderr: {r.stderr}")
        self.assertIn("## Inventory", r.stdout)
        self.assertNotIn("(jig-managed)", r.stdout)

    # ----- AC #6 — partial verdict branch also surfaces copy-machinery ----
    def test_operations_section_suggests_copy_machinery_on_partial_verdict(self):
        """AC #6 — verdict `partial` (exactly two triggers detected) ALSO
        surfaces `copy-machinery` in Operations. Reviewer noted the
        `adoptable` path was the only covered branch; this test closes
        the gap by seeding a project with specs + decisions only (no
        workflow.md / architecture.md), which produces exactly two
        triggers per `compute_verdict`."""
        partial_root = Path(tempfile.mkdtemp(prefix="jig-021-ops-partial-"))
        try:
            (partial_root / "docs" / "specs" / "001-demo").mkdir(parents=True)
            (partial_root / "docs" / "specs" / "001-demo" / "spec.md").write_text(
                "# Spec 001\n\n## Overview\n\nDemo.\n"
            )
            (partial_root / "docs" / "decisions").mkdir(parents=True)
            (partial_root / "docs" / "decisions" / "adr-0001-demo.md").write_text(
                "# ADR-0001 demo\n"
            )
            r = run_migrate("report", str(partial_root))
            self.assertEqual(r.returncode, 1,  # partial verdict → exit 1
                             f"stderr: {r.stderr}")
            self.assertIn("**Verdict:** partial", r.stdout)
            self.assertIn("## Operations", r.stdout)
            self.assertIn("copy-machinery", r.stdout)
        finally:
            shutil.rmtree(partial_root, ignore_errors=True)


class TemplatesBackfillOperationsTests(unittest.TestCase):
    """Slice 095-01 — `migrate.py report` flags a project that has jig
    machinery copied but no `.claude/templates/` (the shape of a project
    scaffolded before 095-01) and routes it to `copy-machinery` to backfill
    the tree. The retrofit itself already works — `copy-machinery` carries
    `templates/` since 095-01; this is the discoverability half, resolving
    ADR-0038's retrofit open question so an affected project learns about the
    gap before a record helper fails on it."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-095-backfill-"))
        _seed_spec_driven_project(self.tmpdir)
        # A project scaffolded before 095-01: machinery copied, but no
        # `.claude/templates/` tree beside it.
        jig_dir = self.tmpdir / ".claude" / "skills" / "jig-memory-sync"
        jig_dir.mkdir(parents=True)
        (jig_dir / "SKILL.md").write_text("seed\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _ops_section(self, stdout: str) -> str:
        self.assertIn("## Operations", stdout)
        return stdout[stdout.index("## Operations"):]

    def test_report_flags_missing_templates_and_routes_to_copy_machinery(self):
        """Machinery present + `.claude/templates/` absent → Operations names
        `copy-machinery` and the missing templates tree."""
        r = run_migrate("report", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        ops = self._ops_section(r.stdout)
        self.assertIn("copy-machinery", ops)
        self.assertIn(".claude/templates/", ops)

    def test_backfill_nudge_names_the_jig_install_caveat(self):
        """The nudge must say the retrofit runs from a jig install — a
        scaffolded project cannot repair itself from its own copied files
        (ADR-0038 Open questions)."""
        r = run_migrate("report", str(self.tmpdir))
        ops = self._ops_section(r.stdout)
        self.assertIn("jig install", ops)

    def test_report_stops_flagging_once_templates_present(self):
        """Backfill the templates tree → the nudge disappears."""
        templates = self.tmpdir / ".claude" / "templates" / "docs" / "decisions"
        templates.mkdir(parents=True)
        (templates / "lightweight-decisions.md.template").write_text("seed\n")
        r = run_migrate("report", str(self.tmpdir))
        ops = self._ops_section(r.stdout)
        self.assertNotIn(
            ".claude/templates/", ops,
            "templates present → the backfill nudge must be suppressed",
        )

    def test_no_backfill_nudge_without_jig_machinery(self):
        """A project with no `.claude/skills/jig-*` gets the full copy-machinery
        suggestion, not the templates-backfill variant — the backfill is
        scoped to projects that already have machinery."""
        plain = Path(tempfile.mkdtemp(prefix="jig-095-nomach-"))
        try:
            _seed_spec_driven_project(plain)
            r = run_migrate("report", str(plain))
            ops = self._ops_section(r.stdout)
            self.assertNotIn(
                "predates the templates copy", ops,
                "no machinery → no templates-backfill nudge (full copy instead)",
            )
        finally:
            shutil.rmtree(plain, ignore_errors=True)


class CopyMachinerySkillSurfaceTests(unittest.TestCase):
    """AC #7 — SKILL.md documents the new `copy-machinery` subcommand."""

    @classmethod
    def setUpClass(cls):
        cls.skill_text = SKILL_MD.read_text()

    def test_skill_md_has_copy_machinery_section(self):
        """AC #7 — `## Copying machinery into your project` (or
        equivalent prose) is documented."""
        # Accept any heading whose text contains "copy" + "machinery"
        # (case-insensitive). The slice spec names "Copying machinery into
        # your project" but we don't pin the exact wording.
        m = re.search(r"(?im)^##\s+.*copy.*machinery", self.skill_text)
        self.assertIsNotNone(
            m,
            "SKILL.md missing a `## ...copy...machinery...` heading",
        )

    def test_skill_md_documents_force_escape(self):
        """AC #7 — section names `--force` as the documented escape
        for the unmanaged-hooks refusal."""
        # The new section should reference --force somewhere near a
        # mention of unmanaged hooks. Loose constraint: both tokens
        # appear in the document.
        self.assertIn("--force", self.skill_text)


# ---------------------------------------------------------------------------
# Slice 022-02 — `## Contract surfaces detected` section in `report` output
# ---------------------------------------------------------------------------


CONTRACT_HEADING = "## Contract surfaces detected"


class ContractSurfacesReportTests(unittest.TestCase):
    """Slice 022-02 AC #3 — `migrate.py report` emits a 'Contract surfaces
    detected' section listing schema artifacts (a), prose API contracts (b),
    env-contract patterns (c), and hand-typed boundary types (d). Each
    detection type covered by at least one tmpdir fixture."""

    def setUp(self):
        import tempfile
        self.tmpdirs: list[Path] = []
        self._tempfile = tempfile

    def tearDown(self):
        import shutil
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make_project(self, files: dict) -> Path:
        """Build a tmpdir with the given relative-path → text mapping."""
        root = Path(self._tempfile.mkdtemp(prefix="jig-mig-csurf-"))
        self.tmpdirs.append(root)
        for relpath, content in files.items():
            target = root / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        return root

    def _report(self, root: Path) -> str:
        r = run_migrate("report", str(root))
        # exit may be 0 (adoptable / not-yet-spec-driven) or 1 (partial);
        # we only care that it ran cleanly and emitted the section.
        self.assertIn(r.returncode, (0, 1),
                      f"exit {r.returncode}; stderr: {r.stderr}")
        self.assertIn(CONTRACT_HEADING, r.stdout)
        return r.stdout

    # ---- empty case ----

    def test_empty_project_emits_no_surfaces_detected_prose(self):
        root = self._make_project({})
        out = self._report(root)
        self.assertIn("_No contract surfaces detected._", out)
        self.assertIn("/jig:vision-elicitation", out)
        self.assertIn("Section 13", out)

    # ---- (a) schema artifacts ----

    def test_detects_openapi_yaml(self):
        root = self._make_project({
            "openapi.yaml": "openapi: 3.0.3\ninfo:\n  title: x\n",
        })
        out = self._report(root)
        self.assertIn("**HTTP API artifact**", out)
        self.assertIn("openapi.yaml", out)
        self.assertIn("OpenAPI 3.x", out)
        self.assertIn("spectral", out)

    def test_detects_asyncapi_yaml(self):
        root = self._make_project({
            "asyncapi.yaml": "asyncapi: 2.6.0\n",
        })
        out = self._report(root)
        self.assertIn("**Event bus / async messaging artifact**", out)
        self.assertIn("AsyncAPI", out)

    def test_detects_dot_proto(self):
        root = self._make_project({
            "proto/foo.proto": "syntax = \"proto3\";\nmessage Foo {}\n",
        })
        out = self._report(root)
        self.assertIn("**RPC artifact**", out)
        self.assertIn("foo.proto", out)
        self.assertIn("buf lint", out)

    def test_detects_graphql_sdl(self):
        root = self._make_project({
            "schema.graphql": "type Query { hello: String }\n",
        })
        out = self._report(root)
        self.assertIn("**GraphQL artifact**", out)
        self.assertIn("schema.graphql", out)

    def test_detects_json_schema(self):
        root = self._make_project({
            "src/events/feedback.schema.json": '{"type":"object"}\n',
        })
        out = self._report(root)
        self.assertIn("**Internal data shape artifact**", out)
        self.assertIn("feedback.schema.json", out)
        self.assertIn("ajv", out)

    def test_skips_artifacts_inside_node_modules(self):
        # Skip-set must exclude node_modules; a fixture openapi.yaml inside
        # node_modules/some-pkg/ must NOT be reported.
        root = self._make_project({
            "node_modules/some-pkg/openapi.yaml": "openapi: 3.0.3\n",
        })
        out = self._report(root)
        # Section heading present, but the bullet must not surface.
        self.assertIn(CONTRACT_HEADING, out)
        self.assertNotIn("**HTTP API artifact**", out)

    # ---- (b) prose API contracts ----

    def test_detects_prose_api_in_architecture_md(self):
        root = self._make_project({
            "docs/architecture.md": (
                "# Architecture\n\n"
                "## 5. API contract\n\n"
                "### Endpoints\n\n"
                "| Method | Path | Purpose |\n"
                "|--------|------|---------|\n"
                "| `POST` | `/v1/foo` | submit |\n"
                "| `GET`  | `/v1/foo/{id}` | poll |\n\n"
                "### Request\n\n"
                "```jsonc\n"
                "{ \"requestId\": \"req_01\", \"customerId\": \"acme\" }\n"
                "```\n"
            ),
        })
        out = self._report(root)
        self.assertIn("**Prose API contract**", out)
        self.assertIn("§5. API contract", out)
        self.assertIn("worked-example-openapi-http.md", out)

    def test_detects_prose_api_in_api_contract_md_whole_doc(self):
        # Validator-shape: contract moved out of architecture.md into a
        # sibling docs/api-contract.md, with table in §1 and jsonc in §2.
        # Per the Tier-2 (whole-document) heuristic for dedicated contract
        # docs, both signals anywhere in the file is enough.
        root = self._make_project({
            "docs/api-contract.md": (
                "# API contract\n\n## 1 Endpoints\n\n"
                "| Method | Path |\n|--------|------|\n"
                "| `POST` | `/v1/validate` |\n\n"
                "## 2 Request\n\n```jsonc\n"
                "{ \"requestId\": \"req_01\" }\n```\n"
            ),
        })
        out = self._report(root)
        self.assertIn("**Prose API contract**", out)
        self.assertIn("api-contract.md", out)
        self.assertIn("whole document", out)

    def test_prose_api_requires_both_signals(self):
        # H2 with endpoint table but NO jsonc fence → no detection.
        root = self._make_project({
            "docs/architecture.md": (
                "## Endpoints\n\n"
                "| Method | Path |\n|--------|------|\n"
                "| GET | /health |\n"
            ),
        })
        out = self._report(root)
        self.assertNotIn("**Prose API contract**", out)

    def test_prose_detection_skips_contract_surfaces_section(self):
        # The wizard's own output declares surfaces in a `## Contract surfaces`
        # H2. That section may contain example endpoint-tables or jsonc — it
        # must not be flagged as a prose-API-to-migrate.
        root = self._make_project({
            "docs/architecture.md": (
                "## Contract surfaces\n\n"
                "- **HTTP API** (recommended: OpenAPI 3.x)\n\n"
                "| Method | Path |\n|--------|------|\n"
                "| `POST` | `/v1/foo` |\n\n"
                "```jsonc\n{ \"requestId\": \"x\" }\n```\n"
            ),
        })
        out = self._report(root)
        self.assertNotIn("**Prose API contract**", out)

    # ---- (c) env-contract patterns ----

    def test_detects_full_env_contract_triple(self):
        root = self._make_project({
            "docs/env-contract.md": "# Env contract\n",
            ".env.example": "FOO=bar\n",
            "tools/env-contract/check.mjs": "// checker\n",
        })
        out = self._report(root)
        self.assertIn("**env-contract pattern** detected", out)
        self.assertIn("full triple", out)

    def test_detects_partial_env_contract(self):
        # Only the doc + seed, no checker.
        root = self._make_project({
            "docs/env-contract.md": "# Env contract\n",
            ".env.example": "FOO=bar\n",
        })
        out = self._report(root)
        self.assertIn("**Partial env-contract pattern**", out)
        self.assertIn("2 of 3", out)
        self.assertIn("checker script", out)

    # ---- (d) hand-typed boundary types ----

    def test_detects_problem_details_ts(self):
        root = self._make_project({
            "src/problem-details.ts": "export type ProblemDetails = {};\n",
        })
        out = self._report(root)
        self.assertIn("**Hand-typed boundary type**", out)
        self.assertIn("problem-details.ts", out)
        self.assertIn("RFC 7807", out)

    def test_detects_problem_details_py(self):
        root = self._make_project({
            "app/problem_details.py": "class ProblemDetails: pass\n",
        })
        out = self._report(root)
        self.assertIn("**Hand-typed boundary type**", out)
        self.assertIn("problem_details.py", out)


# Slice 022-02 SafetyTests extension: the new contract-surface detection
# code lives in the read-only region. Verify it doesn't introduce write-
# shaped calls. (The existing SafetyTests class scans the whole region;
# this test just ensures the new function names are inside it.)


class ContractSurfaceCodeIsReadOnly(unittest.TestCase):
    """The contract-surface detection helpers must live ABOVE the SAFETY
    sentinel — they're part of the read-only `report` code path."""

    def test_render_contract_surfaces_is_read_only(self):
        src = MIGRATE_PY.read_text()
        idx = src.find(
            "# ---------- BEGIN MUTATING CODE PATH (rename-decisions) ----------"
        )
        self.assertGreater(idx, 0, "safety sentinel must exist")
        read_only = src[:idx]
        for fn in [
            "def render_contract_surfaces(",
            "def _detect_schema_artifacts(",
            "def _detect_prose_api_in_architecture(",
            "def _detect_env_contract_pattern(",
            "def _detect_handtyped_boundary_types(",
            "def _walk_for_files(",
        ]:
            self.assertIn(
                fn, read_only,
                f"{fn} must live in the read-only region "
                f"(above the MUTATING sentinel)",
            )


_SCAFFOLD_PY = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"


def run_scaffold(*args: str) -> subprocess.CompletedProcess:
    """Invoke scaffold.py as a subprocess (to build a real tier-0 base)."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(_SCAFFOLD_PY), *args],
        capture_output=True, text=True, env=env,
    )


class TierUpgradeTests(unittest.TestCase):
    """Slice 038-04 — `migrate.py copy-machinery --add-tier <tier>` upgrades
    an already-scaffolded project to a higher tier *additively* (copies only
    the newly-added tier's skills; leaves existing tiers untouched), without
    re-scaffolding. Plain `copy-machinery` resolves tiers from the target
    `scaffold.json` (no manifest → copy-all, preserving the spec-021
    migrate behavior)."""

    TIER0 = [
        "scaffold-init", "memory-sync", "spec-workflow", "independent-review",
        "migrate", "vision-elicitation", "contracts",
    ]
    TIER1 = [
        "adr-workflow", "tdd-loop", "slice-land", "pr-review", "arch-review",
        "clarify", "analyze", "security-review", "code-health", "explain",
        "bug-fix", "reframe", "orient",
    ]

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-038-04-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        # Real tier-0 base with machinery ON DISK: the tier-upgrade contract is
        # "manifest installed_skills == on-disk jig-* skill set", so this needs
        # in-repo mode (slice 099-01 / ADR-0041 flipped the default to plugin
        # mode, which copies no skills at all).
        r = run_scaffold("--in-repo", "--no-tests", str(self.target))
        self.assertEqual(r.returncode, 0, f"scaffold setup failed: {r.stderr}")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _on_disk(self):
        d = self.target / ".claude" / "skills"
        return {
            p.name[len("jig-"):]
            for p in d.iterdir()
            if p.is_dir() and p.name.startswith("jig-") and (p / "SKILL.md").is_file()
        }

    def _manifest(self):
        return _json.loads((self.target / "scaffold.json").read_text())

    def _manifest_skills(self):
        return {s.split("/", 1)[1] for s in self._manifest()["installed_skills"]}

    def test_baseline_is_tier0(self):
        self.assertEqual(self._on_disk(), set(self.TIER0))
        self.assertEqual(self._manifest()["installed_tiers"], ["tier-0"])

    def test_upgrade_adds_tier1(self):  # AC #1
        r = run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-1")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        on_disk = self._on_disk()
        self.assertTrue(
            set(self.TIER1) <= on_disk, f"tier-1 skills not added: {sorted(on_disk)}",
        )
        self.assertEqual(on_disk, set(self.TIER0) | set(self.TIER1))

    def test_upgrade_updates_manifest_and_holds_invariant(self):  # AC #2
        run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-1")
        self.assertEqual(self._manifest()["installed_tiers"], ["tier-0", "tier-1"])
        self.assertEqual(
            self._on_disk(), self._manifest_skills(),
            "manifest installed_skills must equal on-disk skill set after upgrade",
        )

    def test_upgrade_preserves_existing_tier0_and_user_files(self):  # AC #1
        # Additive: the upgrade copies only the tier-1 delta, so an edit to a
        # tier-0 jig skill file and a user doc both survive.
        edited = (
            self.target / ".claude" / "skills" / "jig-spec-workflow" / "SKILL.md"
        )
        edited.write_text("USER EDIT — must survive upgrade\n")
        notes = self.target / "docs" / "my-notes.md"
        notes.write_text("keep me\n")
        run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-1")
        self.assertEqual(
            edited.read_text(), "USER EDIT — must survive upgrade\n",
            "tier-0 skill file was re-copied — upgrade must touch only the delta tier",
        )
        self.assertEqual(notes.read_text(), "keep me\n")

    def test_upgrade_idempotent(self):  # AC #4
        run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-1")
        manifest_after_first = self._manifest()
        disk_after_first = self._on_disk()
        r = run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-1")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertEqual(
            self._manifest(), manifest_after_first,
            "manifest changed on idempotent re-add of an already-installed tier",
        )
        self.assertEqual(self._on_disk(), disk_after_first)

    def test_plain_copy_machinery_respects_manifest_tiers(self):  # AC #2
        # No --add-tier on a tier-0 project: reads the manifest and copies
        # only tier-0 (7), NOT all 15 — proving it is no longer copy-all.
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertEqual(self._on_disk(), set(self.TIER0))

    def test_add_tier_requires_scaffold_json(self):  # precondition (not AlreadyScaffoldedError)
        bare = self.tmpdir / "bare"
        bare.mkdir()
        r = run_migrate("copy-machinery", str(bare), "--add-tier", "tier-1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("scaffold.json", (r.stderr + r.stdout).lower())

    def test_add_tier_rejects_unknown_tier(self):
        r = run_migrate("copy-machinery", str(self.target), "--add-tier", "tier-9")
        self.assertNotEqual(r.returncode, 0)


class PluginModeConversionTests(unittest.TestCase):
    """Bug 018 — `copy-machinery` converts a plugin-mode project to in-repo,
    so the project's own records must stop describing plugin mode.

    A project's mode lives in three places: the files on disk, the
    `scaffold_mode` manifest field, and the helper paths its rendered docs
    cite. Before this fix only the first was updated.

    The split follows the maintainer's ruling on PR #145:
      - the manifest is mechanical and user-data-free -> flip it silently;
      - the rendered docs may carry real user content -> **name them, never
        rewrite them**, and let the session ask the user what to do.
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-bug018-"))
        self.target = self.tmpdir / "proj"
        self.target.mkdir()
        r = run_scaffold("--no-tests", "--plugin-only", str(self.target))
        self.assertEqual(r.returncode, 0, f"scaffold setup failed: {r.stderr}")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mode(self):
        return _json.loads((self.target / "scaffold.json").read_text()).get(
            "scaffold_mode"
        )

    # ----- the manifest half -------------------------------------------------
    def test_baseline_manifest_says_plugin_only(self):
        """Guard the premise: without this the conversion test proves nothing."""
        self.assertEqual(self._mode(), "plugin-only")

    def test_successful_copy_flips_scaffold_mode_to_in_repo(self):
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertEqual(
            self._mode(), "in-repo",
            "copy-machinery left scaffold_mode claiming plugin mode",
        )

    def test_summary_reports_the_mode_flip(self):
        r = run_migrate("copy-machinery", str(self.target))
        self.assertIn("plugin-only", r.stdout)
        self.assertIn("in-repo", r.stdout)

    def test_manifest_flip_preserves_other_fields(self):
        before = _json.loads((self.target / "scaffold.json").read_text())
        run_migrate("copy-machinery", str(self.target))
        after = _json.loads((self.target / "scaffold.json").read_text())
        for key, value in before.items():
            if key == "scaffold_mode":
                continue
            self.assertEqual(after.get(key), value, f"manifest field {key} changed")

    def test_flip_is_idempotent(self):
        run_migrate("copy-machinery", str(self.target))
        first = (self.target / "scaffold.json").read_text()
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertEqual(first, (self.target / "scaffold.json").read_text())
        # Nothing to convert on the second run, so no conversion line.
        self.assertNotIn("plugin-only -> in-repo", r.stdout)

    def test_already_in_repo_project_is_not_reflipped(self):
        other = self.tmpdir / "inrepo"
        other.mkdir()
        # `--in-repo` explicitly: since spec 099-01 / ADR-0041 plugin mode is
        # the DEFAULT, so a bare scaffold would build the wrong fixture here
        # and this test would pass by accident.
        r = run_scaffold("--no-tests", "--in-repo", str(other))
        self.assertEqual(r.returncode, 0, f"scaffold setup failed: {r.stderr}")
        r = run_migrate("copy-machinery", str(other))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        mode = _json.loads((other / "scaffold.json").read_text())["scaffold_mode"]
        self.assertEqual(mode, "in-repo")
        self.assertNotIn("plugin-only -> in-repo", r.stdout)

    def test_project_without_a_manifest_is_unaffected(self):
        """The spec-021 migrate-into-jig case: no scaffold.json, so there is no
        mode claim to contradict and none must be invented."""
        bare = self.tmpdir / "bare"
        bare.mkdir()
        _seed_spec_driven_project(bare)
        r = run_migrate("copy-machinery", str(bare))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertFalse(
            (bare / "scaffold.json").exists(),
            "copy-machinery must not invent a manifest for an unscaffolded project",
        )

    # ----- the docs half — warn, never rewrite -------------------------------
    def test_stale_doc_citations_are_named_in_the_summary(self):
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertIn("docs/workflow.md", r.stdout)
        self.assertIn("CLAUDE_PLUGIN_ROOT", r.stdout)

    def test_summary_states_the_replacement_path(self):
        r = run_migrate("copy-machinery", str(self.target))
        self.assertIn("${CLAUDE_PROJECT_DIR}/.claude/skills/jig-", r.stdout)

    def test_stale_docs_are_not_rewritten(self):
        """The whole reason this half is a warning: docs/workflow.md is a file
        the user is invited to edit, and by conversion time it may hold real
        project content. Hand-written prose must survive byte-for-byte."""
        wf = self.target / "docs" / "workflow.md"
        wf.write_text(
            "# Our workflow\n\nHouse rule: run\n"
            "`python3 ${CLAUDE_PLUGIN_ROOT}/skills/tdd-loop/tdd.py run` first.\n"
        )
        before = wf.read_bytes()
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        after = wf.read_text()
        self.assertIn("House rule: run", after)
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/skills/tdd-loop/", after,
                      "the stale citation was rewritten — it must only be reported")
        # The managed convention blocks still append (spec 065-04 / 067-03), so
        # the file grows; what must not happen is the user's prose being edited.
        self.assertTrue(after.startswith(before.decode()),
                        "user prose was modified rather than appended to")

    def test_warning_reaches_stdout_without_failing_the_run(self):
        """Advisory, not a gate: the copy succeeded, so the exit code stays 0."""
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0)

    def test_clean_docs_produce_no_warning(self):
        for md in (self.target / "docs").rglob("*.md"):
            md.write_text(md.read_text().replace("${CLAUDE_PLUGIN_ROOT}", "PLUGIN"))
        r = run_migrate("copy-machinery", str(self.target))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        self.assertNotIn("still cite", r.stdout)

    def test_copied_machinery_is_not_reported_as_stale_user_docs(self):
        """`.claude/skills/jig-*/` is jig-owned machinery, refreshed by this very
        command. Listing it would bury the two files the user actually owns."""
        r = run_migrate("copy-machinery", str(self.target))
        listed = [
            line.strip()[2:].split(" (")[0]
            for line in r.stdout.splitlines()
            if line.startswith("  - ")
        ]
        self.assertTrue(listed, f"expected stale files to be listed: {r.stdout}")
        for path in listed:
            self.assertFalse(
                path.startswith(".claude/") or path.startswith(".codex/"),
                f"host runtime machinery reported as a user doc: {path}",
            )

    def test_skill_documents_the_ask_before_editing_step(self):
        """The helper only reports. The decision belongs to the session, which
        must warn the user and let them choose — not silently pick for them."""
        # Whitespace-normalized: the source is hard-wrapped prose, so a raw
        # substring search would break on an innocuous re-wrap.
        body = " ".join(SKILL_MD.read_text().split())
        marker = "Stale plugin-root citations after conversion"
        self.assertIn(marker, body, "the conversion advisory is undocumented")
        section = body.split(marker, 1)[1][:2000].lower()
        self.assertIn("ask the user", section)
        self.assertIn("does not touch these files", section)
        self.assertIn("do not pick for them", section)

    def test_codex_render_keeps_the_ask_before_editing_step(self):
        """The Codex builder replaces whole named sections of this SKILL.md
        wholesale. A section written between two of its anchor points is
        deleted from the Codex package with no error and no diff — which is
        how the first draft of this advisory vanished. Guard the rendered
        artifact, not just the source."""
        rendered = (
            REPO_ROOT / "hosts" / "codex" / "plugins" / "jig" / "skills"
            / "migrate" / "SKILL.md"
        )
        if not rendered.is_file():          # package not built in this tree
            self.skipTest(f"no committed Codex package at {rendered}")
        body = " ".join(rendered.read_text().split())
        self.assertIn(
            "Stale plugin-root citations after conversion", body,
            "the Codex render dropped the conversion advisory",
        )
        self.assertIn("ask the user", body.lower())


class CopyMachinerySelfDefiningConventionTests(unittest.TestCase):
    """Spec 065-04 AC3 — `migrate copy-machinery` refreshes the self-defining-
    vocabulary convention block into an EXISTING project's docs/workflow.md
    (the only path that reaches an already-scaffolded project — copy-machinery
    does not otherwise touch docs/). Idempotent + non-clobbering, mirroring the
    .gitignore secret-floor merge."""

    BLOCK_BEGIN = "<!-- >>> jig self-defining-vocabulary >>> -->"

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-065-04-mig-"))
        _seed_spec_driven_project(self.tmpdir)
        # Give the seeded workflow.md some pre-existing custom content so we can
        # assert copy-machinery preserves it (append, not clobber).
        self.wf = self.tmpdir / "docs" / "workflow.md"
        self.wf.write_text("# Workflow\n\nOur own house rules.\n")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_copy_machinery_appends_convention_block(self):
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        text = self.wf.read_text()
        self.assertIn(self.BLOCK_BEGIN, text, "convention block not appended")
        self.assertIn("Self-defining vocabulary", text)
        # Pre-existing content preserved verbatim.
        self.assertIn("Our own house rules.", text)

    def test_copy_machinery_block_injection_is_idempotent(self):
        run_migrate("copy-machinery", str(self.tmpdir))
        once = self.wf.read_text()
        r = run_migrate("copy-machinery", str(self.tmpdir))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        twice = self.wf.read_text()
        self.assertEqual(once, twice, "second copy-machinery run must be a no-op")
        self.assertEqual(twice.count(self.BLOCK_BEGIN), 1, "no duplicate block")


_UNSET = object()  # "caller passed nothing", distinct from a falsy layout


class CopyMachineryTrackLocalDocsRootTests(unittest.TestCase):
    """Bug 022 — `copy-machinery` must write its two managed `workflow.md`
    blocks under the project's CONFIGURED `layout.docs_root` (spec 084 /
    ADR-0033), not a hardcoded `docs/`.

    `migrate.copy_machinery` forwarded `force` / `installed_tiers` / `host` to
    `scaffold.copy_machinery` but not `docs_root`, so the façade's
    `docs_root="docs"` default applied. On a track-local project
    (`docs_root: "."`) that put the blocks in a `docs/workflow.md` the project
    never asked for, and left the real root `workflow.md` untouched."""

    SELF_DEFINING_BEGIN = "<!-- >>> jig self-defining-vocabulary >>> -->"
    REFRAME_BEGIN = "<!-- >>> jig reframe-practice >>> -->"

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-022-docs-root-"))

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _seed(self, docs_root: str, *, raw_layout=_UNSET):
        """Seed a spec-driven project whose docs live under `docs_root`, with a
        scaffold.json recording that layout.

        Returns `(project_dir, workflow_path)` — both explicitly, so no test
        has to re-derive one from the other by `.parents[N]` index arithmetic
        (the depth coupling ADR-0033 removed elsewhere).

        `raw_layout` overrides what is written to scaffold.json's `layout`
        key, so a test can seed a MALFORMED config while still knowing where
        the correctly-configured workflow.md would be."""
        project = self.tmpdir / docs_root.replace("/", "-").replace(".", "root")
        base = project if docs_root == "." else project / docs_root
        (base / "specs" / "001-demo").mkdir(parents=True)
        (base / "specs" / "001-demo" / "spec.md").write_text(
            "# Spec 001\n\n## Overview\n\nDemo.\n"
        )
        (base / "decisions").mkdir(parents=True)
        (base / "decisions" / "adr-0001-demo.md").write_text("# ADR-0001 demo\n")
        (base / "architecture.md").write_text("# Architecture\n")
        workflow = base / "workflow.md"
        workflow.write_text("# Workflow\n\nOur own house rules.\n")
        layout = {"docs_root": docs_root} if raw_layout is _UNSET else raw_layout
        (project / "scaffold.json").write_text(_json.dumps(
            {"layout": layout, "installed_tiers": ["tier-0"]}
        ) + "\n")
        return project, workflow

    def test_convention_block_lands_at_configured_root(self):
        project, workflow = self._seed(".")
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}\nstdout: {r.stdout}")
        text = workflow.read_text()
        self.assertIn(
            self.SELF_DEFINING_BEGIN, text,
            f"convention block missing from {workflow} — copy-machinery wrote it "
            "to a hardcoded docs/ instead of the configured docs_root",
        )
        self.assertIn("Our own house rules.", text,
                      "pre-existing workflow content must survive the append")

    def test_no_spurious_docs_dir_is_created(self):
        project, _workflow = self._seed(".")
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(
            (project / "docs").exists(),
            "copy-machinery created a docs/ dir in a docs_root='.' project — "
            "collapsing that layer is the entire point of track-local adoption",
        )

    def test_reframe_block_lands_at_configured_root(self):
        project, workflow = self._seed(".")
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn(
            self.REFRAME_BEGIN, workflow.read_text(),
            f"reframe practice block missing from {workflow} — the second "
            "managed block must follow the same configured root",
        )

    def test_nested_docs_root_is_honoured(self):
        """Not `.`-special-cased: any non-default root must be honoured."""
        project, workflow = self._seed("docs/internal")
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn(
            self.SELF_DEFINING_BEGIN, workflow.read_text(),
            f"block missing from {workflow}",
        )
        # The invariant stated directly: nothing is written to the default
        # root at all. Unconditional, so it cannot degrade into a trivial
        # pass if the marker constant ever drifts.
        self.assertFalse(
            (project / "docs" / "workflow.md").exists(),
            "block leaked into docs/workflow.md instead of docs/internal/",
        )

    def test_default_docs_root_still_lands_in_docs(self):
        """Regression guard on the ordinary path — the fix must not move the
        blocks for a project that uses the default root."""
        project, workflow = self._seed("docs")
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn(self.SELF_DEFINING_BEGIN, workflow.read_text())

    def test_malformed_layout_degrades_instead_of_failing_the_copy(self):
        """The resolver choice this fix rests on, pinned.

        `_project_docs_root` swallows a bad config and returns `"docs"` rather
        than raising, so a malformed `scaffold.json` cannot fail a machinery
        copy that would otherwise succeed. That is the whole reason it is used
        here instead of the raising `_validated_docs_root`. Without this test
        someone could swap in a raising resolver and every other test in this
        class would stay green."""
        project, _workflow = self._seed(".", raw_layout={"docs_root": ["not", "a", "string"]})
        r = run_migrate("copy-machinery", str(project))
        self.assertEqual(
            r.returncode, 0,
            "a malformed layout.docs_root must not fail the copy — "
            f"stderr: {r.stderr}",
        )
        # Pin the degrade OUTCOME, not just the exit code: the fallback is
        # the literal "docs", so the blocks land there. Without this a copy
        # that exited 0 while writing no blocks at all would pass.
        self.assertTrue(
            (project / "docs" / "workflow.md").is_file(),
            "the degrade must fall back to the documented `docs` root, "
            "not skip the managed blocks entirely",
        )


# -------------------- SeedDecisionsTests --------------------


_LD_TEMPLATE = (
    REPO_ROOT / "templates" / "docs" / "decisions"
    / "lightweight-decisions.md.template"
)

_FOREIGN_TABLE = """# Lightweight Decisions

| ID | Date | Decision |
|----|------|----------|
| LD-1 | 2026-07-15 | Knob fill uses var(--surface) |
"""


class SeedDecisionsTests(unittest.TestCase):
    """Bug 012 / #109 finding 1 fix 1 — the backfill op. A project scaffolded
    before the lightweight-decisions feature landed never received the LD
    home, and no migrate subcommand could give it one; `scaffold-init` only
    seeds at init and cannot be re-run on a scaffolded project.
    """

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        # A project that is unambiguously spec-driven (4 verdict triggers →
        # 'adoptable' → report exits 0) but has no lightweight-decisions.md.
        (self.project / "docs" / "specs" / "001-foo").mkdir(parents=True)
        (self.project / "docs" / "specs" / "001-foo" / "spec.md").write_text(
            "# Spec 001\n")
        (self.project / "docs" / "decisions").mkdir(parents=True)
        (self.project / "docs" / "decisions" / "adr-0001-foo.md").write_text(
            "# ADR-0001\n")
        (self.project / "docs" / "workflow.md").write_text("# Workflow\n")
        (self.project / "docs" / "architecture.md").write_text("# Arch\n")
        self.ld = self.project / "docs" / "decisions" / "lightweight-decisions.md"

    def tearDown(self):
        self._tmp.cleanup()

    def test_seed_creates_the_ld_home(self):
        r = run_migrate("seed-decisions", str(self.project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertTrue(self.ld.is_file())
        self.assertIn("## Entries", self.ld.read_text())

    def test_seeded_file_is_the_shipped_template(self):
        run_migrate("seed-decisions", str(self.project))
        self.assertEqual(self.ld.read_text(), _LD_TEMPLATE.read_text())

    def test_seed_is_idempotent(self):
        first = run_migrate("seed-decisions", str(self.project))
        self.assertEqual(first.returncode, 0, f"stderr: {first.stderr}")
        once = self.ld.read_text()
        second = run_migrate("seed-decisions", str(self.project))
        self.assertEqual(second.returncode, 0, f"stderr: {second.stderr}")
        self.assertEqual(self.ld.read_text(), once,
                         "second seed-decisions run must not rewrite the file")

    def test_dry_run_writes_nothing(self):
        r = run_migrate("seed-decisions", str(self.project), "--dry-run")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertFalse(self.ld.exists(),
                         "--dry-run must not create the file")

    def test_refuses_to_clobber_a_foreign_format_file(self):
        self.ld.write_text(_FOREIGN_TABLE)
        r = run_migrate("seed-decisions", str(self.project))
        self.assertNotEqual(r.returncode, 0,
                            "a foreign-format LD home is an unresolved state "
                            "— seed must fail loud, not exit 0")
        self.assertEqual(self.ld.read_text(), _FOREIGN_TABLE,
                         "must never overwrite the owner's file")
        combined = r.stdout + r.stderr
        self.assertIn("## Entries", combined)

    def test_report_flags_the_missing_ld_home(self):
        r = run_migrate("report", str(self.project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertIn("seed-decisions", r.stdout)
        self.assertIn("lightweight-decisions.md", r.stdout)

    def test_seed_honours_track_local_docs_root(self):
        """spec 084 — `--docs-root .` puts decisions/ directly under the
        project root. The only docs_root with a distinct output path."""
        r = run_migrate("seed-decisions", str(self.project), "--docs-root", ".")
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        track_local = self.project / "decisions" / "lightweight-decisions.md"
        self.assertTrue(track_local.is_file(),
                        "--docs-root . must seed <project>/decisions/")
        self.assertIn("## Entries", track_local.read_text())

    def test_report_stops_flagging_once_seeded(self):
        run_migrate("seed-decisions", str(self.project))
        r = run_migrate("report", str(self.project))
        self.assertEqual(r.returncode, 0, f"stderr: {r.stderr}")
        self.assertNotIn("seed-decisions", r.stdout,
                         "suggestion must be suppressed once the home exists")


if __name__ == "__main__":
    unittest.main()
