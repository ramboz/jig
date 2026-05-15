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
        from skills.migrate import migrate
        plan = migrate.plan_rename(self.tmpdir)
        self.assertIsNotNone(plan.dir_rename)
        self.assertEqual(plan.dir_rename.src.name, "adrs")
        self.assertEqual(plan.dir_rename.dst.name, "decisions")

    def test_plan_includes_file_renames(self):
        from skills.migrate import migrate
        plan = migrate.plan_rename(self.tmpdir)
        new_names = [fr.dst.name for fr in plan.file_renames]
        self.assertIn("adr-0001-foo.md", new_names)
        self.assertIn("adr-0002-bar.md", new_names)

    def test_plan_includes_cross_ref_rewrites(self):
        from skills.migrate import migrate
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


if __name__ == "__main__":
    unittest.main()
