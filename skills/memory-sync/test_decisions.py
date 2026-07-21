"""
AC verification tests for slice 083-05 (routing rubric + decisions.py
add-lightweight) and the single-source drift guard co-owned with 083-06.

Run from the repo root:
    python3 skills/memory-sync/test_decisions.py
"""

import importlib.util
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISIONS_PY = REPO_ROOT / "skills" / "memory-sync" / "decisions.py"
TEMPLATE = (
    REPO_ROOT / "templates" / "docs" / "decisions"
    / "lightweight-decisions.md.template"
)
TODAY = date.today().isoformat()

# The four consumer sites that must quote the canonical ADR-trigger sentence
# verbatim, plus ADR-0031 (the human-readable canonical source).
RUBRIC = REPO_ROOT / "docs" / "decisions" / "lightweight-decisions.md"
WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"
MEMORY_SYNC_SKILL = REPO_ROOT / "skills" / "memory-sync" / "SKILL.md"
ADR_0031 = (
    REPO_ROOT / "docs" / "decisions"
    / "adr-0031-load-bearing-decision-adr-trigger.md"
)

_SEED = """# Lightweight Decisions

Some intro prose.

## Entries

> _Illustrative only._

### 2026-01-15 — Example entry

**Decision:** something.
"""


def _import_decisions():
    spec = importlib.util.spec_from_file_location("decisions", DECISIONS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


decisions = _import_decisions()


class AddLightweightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        target = decisions.lightweight_path(self.project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_SEED, encoding="utf-8")
        self.target = target

    def tearDown(self):
        self._tmp.cleanup()

    # AC1 — appends a well-formed entry
    def test_append_wellformed_entry(self):
        appended = decisions.add_lightweight(
            self.project, "Button copy", "Use 'Get started'",
            "User testing", "Onboarding CTA", commit="abc123", date="2026-06-26")
        self.assertTrue(appended)
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("### 2026-06-26 — Button copy", text)
        self.assertIn("**Decision:** Use 'Get started'", text)
        self.assertIn("**Context:** User testing", text)
        self.assertIn("**Scope:** Onboarding CTA", text)
        self.assertIn("**Commit:** abc123", text)
        # the seeded example entry is preserved
        self.assertIn("### 2026-01-15 — Example entry", text)

    def test_date_defaults_to_today(self):
        decisions.add_lightweight(
            self.project, "No date given", "decided", "ctx", "scope")
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("### %s — No date given" % TODAY, text)

    def test_commit_optional(self):
        decisions.add_lightweight(
            self.project, "No commit", "decided", "ctx", "scope",
            date="2026-06-26")
        text = self.target.read_text(encoding="utf-8")
        self.assertNotIn("**Commit:**", text.split("No commit", 1)[1])

    # AC2 — idempotent
    def test_idempotent_same_title_date(self):
        first = decisions.add_lightweight(
            self.project, "Dupe", "d", "c", "s", date="2026-06-26")
        before = self.target.read_text(encoding="utf-8")
        second = decisions.add_lightweight(
            self.project, "  dupe  ", "d2", "c2", "s2", date="2026-06-26")
        after = self.target.read_text(encoding="utf-8")
        self.assertTrue(first)
        self.assertFalse(second)  # normalized title match → no-op
        self.assertEqual(before, after)

    def test_same_title_different_date_appends(self):
        decisions.add_lightweight(
            self.project, "Recur", "d", "c", "s", date="2026-06-26")
        appended = decisions.add_lightweight(
            self.project, "Recur", "d", "c", "s", date="2026-06-27")
        self.assertTrue(appended)

    # AC1/AC2 — malformed input
    def test_missing_title_raises(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "", "d", "c", "s")

    def test_missing_decision_raises(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "", "c", "s")

    # An absent file is no longer an error — it is seeded from the template.
    # See SeedFromTemplateTests (bug 012 deliberately inverts the old
    # `test_no_file_raises` contract).

    def test_missing_entries_heading_raises(self):
        self.target.write_text("# Lightweight Decisions\n\nNo entries heading.\n",
                               encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "d", "c", "s")


_FOREIGN_TABLE = """# Lightweight Decisions

Small shipped decisions that carry durable rationale.

| ID | Date | Decision |
|----|------|----------|
| LD-1 | 2026-07-15 | Knob fill uses var(--surface), not the mockup hex |
"""


class SeedFromTemplateTests(unittest.TestCase):
    """Bug 012 / #109 finding 1 — a project scaffolded before the
    lightweight-decisions feature landed never received the file, and the
    helper's refusal-to-create made the documented recording path
    permanently dead. The helper now seeds it from the template instead.

    Note these deliberately start from a bare project dir with NO
    docs/decisions/ — that is the reported state, not an edge case.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_is_seeded_and_entry_appended(self):
        appended = decisions.add_lightweight(
            self.project, "First decision", "Use X", "because Y",
            "Home screen", date="2026-07-16")
        self.assertTrue(appended)
        self.assertTrue(self.target.is_file())
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("## Entries", text)
        self.assertIn("### 2026-07-16 — First decision", text)
        self.assertIn("**Decision:** Use X", text)

    def test_seed_creates_missing_parent_directories(self):
        self.assertFalse(self.target.parent.exists())
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        self.assertTrue(self.target.is_file())

    def test_seeded_body_is_the_real_template_not_a_stub(self):
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        text = self.target.read_text(encoding="utf-8")
        # The routing rubric is the template's reason for existing — a
        # hand-rolled minimal stub would pass the ## Entries check but lose it.
        self.assertIn(decisions.ADR_TRIGGER, text)
        self.assertIn("# Lightweight Decisions", text)

    def test_seed_matches_the_shipped_template_verbatim(self):
        decisions.seed_lightweight(self.project)
        self.assertEqual(
            self.target.read_text(encoding="utf-8"),
            TEMPLATE.read_text(encoding="utf-8"),
            "seeded file must be the shipped template, or scaffold-init and "
            "the backfill path would produce different homes")

    def test_second_call_appends_without_reseeding(self):
        decisions.add_lightweight(self.project, "One", "d", "c", "s",
                                  date="2026-07-16")
        decisions.add_lightweight(self.project, "Two", "d", "c", "s",
                                  date="2026-07-16")
        text = self.target.read_text(encoding="utf-8")
        self.assertEqual(text.count("# Lightweight Decisions"), 1)
        self.assertIn("### 2026-07-16 — One", text)
        self.assertIn("### 2026-07-16 — Two", text)

    def test_seed_lightweight_reports_created_then_noop(self):
        self.assertTrue(decisions.seed_lightweight(self.project))
        self.assertFalse(decisions.seed_lightweight(self.project))

    def test_seed_then_append_round_trip(self):
        """The round trip the bug is about: a freshly seeded home must not
        then fail its own `## Entries` gate."""
        decisions.seed_lightweight(self.project)
        self.assertTrue(
            decisions.add_lightweight(self.project, "T", "d", "c", "s"))


class ForeignFormatTests(unittest.TestCase):
    """Bug 012 / #109 finding 1 fix 2 — when the file exists but is NOT in
    jig's format (the hand-rolled LD table an unguided agent writes), fail
    loud with the remedy in the message, and never touch the file.

    Deliberately NOT fix #4 (degrade + append under a created heading):
    grafting jig entries onto a foreign document the owner wrote would split
    the record across two formats silently — the same failure this bug is
    about, moved one step later.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_FOREIGN_TABLE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_foreign_format_raises(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "d", "c", "s")

    def test_error_names_the_expected_shape(self):
        with self.assertRaises(ValueError) as ctx:
            decisions.add_lightweight(self.project, "t", "d", "c", "s")
        msg = str(ctx.exception)
        self.assertIn("## Entries", msg)
        self.assertIn("###", msg)
        self.assertIn("**Decision:**", msg)

    def test_error_names_the_migrate_remedy(self):
        with self.assertRaises(ValueError) as ctx:
            decisions.add_lightweight(self.project, "t", "d", "c", "s")
        self.assertIn("seed-decisions", str(ctx.exception))

    def test_error_names_the_real_path_under_track_local_docs_root(self):
        """spec 084 — a `layout.docs_root: "."` corpus keeps decisions/ at the
        project root. The refusal must name where the offending file actually
        is, not the hardcoded default (review follow-up)."""
        (self.project / "scaffold.json").write_text(
            '{"layout": {"docs_root": "."}}', encoding="utf-8")
        target = decisions.lightweight_path(self.project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_FOREIGN_TABLE, encoding="utf-8")
        self.assertEqual(target, self.project / "decisions"
                         / "lightweight-decisions.md",
                         "precondition: docs_root '.' must move the file")
        with self.assertRaises(ValueError) as ctx:
            decisions.add_lightweight(self.project, "t", "d", "c", "s")
        msg = str(ctx.exception)
        self.assertIn("decisions/lightweight-decisions.md", msg)
        self.assertNotIn("docs/decisions/lightweight-decisions.md", msg,
                         "must not name the default path for a '.' corpus")

    def test_foreign_file_is_never_rewritten(self):
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "t", "d", "c", "s")
        self.assertEqual(self.target.read_text(encoding="utf-8"), _FOREIGN_TABLE)

    def test_seed_lightweight_refuses_to_clobber(self):
        self.assertFalse(decisions.seed_lightweight(self.project))
        self.assertEqual(self.target.read_text(encoding="utf-8"), _FOREIGN_TABLE)

    def test_foreign_format_fails_loud_even_when_title_looks_recorded(self):
        """The format gate must precede the idempotency no-op. Otherwise a
        foreign file carrying a matching `### <date> — <title>` heading
        returns a silent 'already recorded' and the divergence is never
        surfaced — which is the bug, not a no-op."""
        self.target.write_text(
            _FOREIGN_TABLE + "\n### 2026-07-16 — Probe\n\nsome prose\n",
            encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.add_lightweight(self.project, "Probe", "d", "c", "s",
                                      date="2026-07-16")


class UnreachableTemplateTests(unittest.TestCase):
    """Bug 012, review follow-up — re-premised by slice 095-01.

    Originally this pinned the *expected* Claude scaffold-mode failure: that
    mode copied `skills/` but not `templates/` (only Codex had
    `_copy_codex_templates`), so a copied helper resolved `parents[2]` to
    `<project>/.claude`, where no template existed. Bug 012 could not fix that
    mode and settled for failing with remedies that work.

    Slice 095-01 closed it — `copy_machinery` now copies `templates/` too
    (ADR-0038), and `ClaudeScaffoldTemplatesTests` in
    `skills/scaffold-init/test_scaffold_mode.py` pins the copied helper
    seeding for real. So no install mode is *expected* to land here any more,
    and these tests now guard the **broken-install** path: a copy predating
    095-01, a partial tree, or `CLAUDE_PLUGIN_ROOT` aimed at a non-jig root.
    The invariant is unchanged and still the point — a bare 'not found' would
    be the original bug in a new costume.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self._saved = os.environ.get("CLAUDE_PLUGIN_ROOT")
        # Point the plugin root at a dir with no templates/ tree — an install
        # whose template home is missing, however it got that way.
        os.environ["CLAUDE_PLUGIN_ROOT"] = str(self.project)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = self._saved
        self._tmp.cleanup()

    def _target_exists(self) -> bool:
        return decisions.lightweight_path(self.project).exists()

    def test_unreachable_template_names_working_remedies(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            decisions.seed_lightweight(self.project)
        msg = str(ctx.exception)
        self.assertIn("copy-machinery", msg,
                      "must name the remedy that repairs the install rather "
                      "than working around it — slice 095-01 made "
                      "copy-machinery bring templates/ with it")
        self.assertIn("CLAUDE_PLUGIN_ROOT", msg,
                      "must name the env-var remedy — it demonstrably works "
                      "from copied machinery")
        self.assertIn("seed-decisions", msg)

    def test_unreachable_template_writes_nothing(self):
        with self.assertRaises(FileNotFoundError):
            decisions.seed_lightweight(self.project)
        self.assertFalse(self._target_exists())


class CliOrderingTests(unittest.TestCase):
    """Bug 012, review follow-up — the CLI must not create the record home as
    a side effect of a call it then rejects. A file appearing with no signal
    is the silence this bug is about."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)

    def tearDown(self):
        self._tmp.cleanup()

    def test_invalid_input_does_not_seed(self):
        rc = decisions.main([
            "add-lightweight", "--title", "", "--decision", "d",
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 1)
        self.assertFalse(
            self.target.exists(),
            "rejected call must not leave a seeded file behind")


class SingleSourceDriftTests(unittest.TestCase):
    """083-05 AC4 / 083-06 AC3 — the canonical ADR_TRIGGER sentence must appear
    verbatim in all four consumer sites (and in ADR-0031's prose)."""

    def _assert_contains_trigger(self, path: Path):
        self.assertTrue(path.exists(), "missing consumer site: %s" % path)
        self.assertIn(
            decisions.ADR_TRIGGER, path.read_text(encoding="utf-8"),
            "canonical ADR_TRIGGER sentence not found verbatim in %s" % path.name)

    def test_rubric_site(self):
        self._assert_contains_trigger(RUBRIC)

    def test_workflow_reconcile_checklist_site(self):
        self._assert_contains_trigger(WORKFLOW_MD)

    def test_spec_workflow_reconcile_checklist_site(self):
        self._assert_contains_trigger(SPEC_WORKFLOW_SKILL)

    def test_memory_sync_prompt_site(self):
        self._assert_contains_trigger(MEMORY_SYNC_SKILL)

    def test_adr0031_canonical_source(self):
        self._assert_contains_trigger(ADR_0031)


class EntriesPlaceholderTests(unittest.TestCase):
    """The template seeds `## Entries` with a "_No entries yet._" placeholder,
    and `add_lightweight` appends at end-of-file without clearing it — so the
    moment a real decision is recorded, the file says "No entries yet"
    directly above the entries it lists. Affects every jig project, since
    scaffold-init seeds this same template.

    These start from the shipped template verbatim, which is exactly what a
    scaffolded project's file looks like before its first entry.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(TEMPLATE.read_text(encoding="utf-8"),
                               encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _text(self) -> str:
        return self.target.read_text(encoding="utf-8")

    def test_placeholder_is_dropped_when_the_first_entry_lands(self):
        decisions.add_lightweight(self.project, "Knob fill", "Use var(--surface)",
                                  "mockup hex rejected", "Home settings",
                                  date="2026-07-16")
        text = self._text()
        self.assertNotIn("_No entries yet.", text)
        self.assertIn("### 2026-07-16 — Knob fill", text)

    def test_entries_heading_survives_the_drop(self):
        """Strip the placeholder, not the section it sits in."""
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        self.assertEqual(self._text().count("## Entries"), 1)

    def test_placeholder_kept_while_the_file_has_no_entries(self):
        """It is useful copy for an empty file — the defect is only that it
        outlives the first entry. A no-op append must not strip it either."""
        self.assertIn("_No entries yet.", self._text())
        decisions.add_lightweight(self.project, "Dupe", "d", "c", "s",
                                  date="2026-07-16")
        before = self._text()
        appended = decisions.add_lightweight(self.project, "Dupe", "d2", "c2",
                                             "s2", date="2026-07-16")
        self.assertFalse(appended)
        self.assertEqual(self._text(), before, "no-op must not rewrite")

    def test_second_entry_appends_normally(self):
        decisions.add_lightweight(self.project, "One", "d", "c", "s",
                                  date="2026-07-16")
        decisions.add_lightweight(self.project, "Two", "d", "c", "s",
                                  date="2026-07-17")
        text = self._text()
        self.assertIn("### 2026-07-16 — One", text)
        self.assertIn("### 2026-07-17 — Two", text)
        self.assertNotIn("_No entries yet.", text)
        self.assertEqual(text.count("## Entries"), 1)

    def test_template_fence_example_heading_survives(self):
        """`_existing_keys` deliberately scans every `### ` heading, including
        the `### [Date] — [Short title]` line inside the `## Template` fence.
        Stripping the placeholder must not disturb it."""
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        self.assertIn("### [Date] — [Short title]", self._text())

    def test_unrelated_italics_are_not_stripped(self):
        """Only the placeholder goes — not any italic line that happens to sit
        under `## Entries` (e.g. a project's own illustrative note)."""
        self.target.write_text(_SEED, encoding="utf-8")
        decisions.add_lightweight(self.project, "T", "d", "c", "s")
        text = self._text()
        self.assertIn("> _Illustrative only._", text)
        self.assertIn("### 2026-01-15 — Example entry", text)

    def test_template_still_ships_the_placeholder_we_strip(self):
        """Drift guard: the matcher keys off the template's own wording. If the
        template's copy is reworded, the strip silently stops working and the
        defect returns with no test failing anywhere else."""
        self.assertRegex(TEMPLATE.read_text(encoding="utf-8"),
                         decisions._ENTRIES_PLACEHOLDER_RE)


if __name__ == "__main__":
    unittest.main()
