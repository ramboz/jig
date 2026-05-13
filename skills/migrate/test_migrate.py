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

    def test_readme_excluded_from_slices_count(self):
        """Reviewer-flagged latent bug: prior version filtered README only
        for decisions/adrs/skills/agents; slices/spikes were unfiltered.
        A `docs/slices/README.md` would have been counted as a slice."""
        import tempfile, shutil
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
        import tempfile, shutil
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
        import tempfile, shutil
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


class SafetyTests(unittest.TestCase):
    """AC #4 — no filesystem-mutating calls in the report code path."""

    def setUp(self):
        self.source = MIGRATE_PY.read_text()

    def test_no_path_write_text(self):
        # `Path.write_text` would be a write — forbidden anywhere in this slice
        # (no subcommand mutates).
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
        # No directory creation either — pure read-only walk.
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


if __name__ == "__main__":
    unittest.main()
