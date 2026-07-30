"""
AC verification tests for slice 083-05 (routing rubric + decisions.py
add-lightweight) and the single-source drift guard co-owned with 083-06.

Run from the repo root:
    python3 skills/memory-sync/test_decisions.py
"""

import ast
import contextlib
import importlib.util
import io
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


# ---- CLI helpers ------------------------------------------------------

def _run_cli(argv):
    """Run `decisions.main(argv)`, capturing stderr. Returns (rc, stderr).
    Reused by the update / promote / lint subcommand tests."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        rc = decisions.main(argv)
    return rc, buf.getvalue()


# Pulls the false-positive corpus straight from the real file (AC3) rather
# than a hand-transcribed copy, so an edit to the illustrative entry can't
# leave this test silently exercising stale text.
_ILLUSTRATIVE_ENTRY_RE = re.compile(
    r"^### [^\n]+ — (?P<title>[^\n]+)\n\n"
    r"\*\*Decision:\*\* (?P<decision>.+?)\n\n"
    r"\*\*Context:\*\* (?P<context>.+?)\n\n"
    r"\*\*Scope:\*\* (?P<scope>.+?)\n\n",
    re.MULTILINE | re.DOTALL,
)


def _real_illustrative_entry():
    text = RUBRIC.read_text(encoding="utf-8")
    m = _ILLUSTRATIVE_ENTRY_RE.search(text)
    assert m, ("illustrative entry not found in %s — has the corpus moved?"
              % RUBRIC)
    return (m.group("title").strip(), m.group("decision").strip(),
            m.group("context").strip(), m.group("scope").strip())


# Fixtures for the two-signal rule (100-01 / ADR-0042). Each is checked by
# hand against every marker group below so the tests pin exactly one
# condition apiece rather than a coincidental combination.
_LOAD_BEARING_HALF = (
    "We are replacing the vendored library with our own native "
    "implementation.")
_ALTERNATIVES_HALF = (
    "We considered several alternatives and rejected them, choosing this "
    "instead of continuing to patch the old one.")
_BOUNDARY_ONLY = (
    "This changes the module boundary between the auth and billing "
    "services.")
_ALTERNATIVES_ONLY = (
    "We considered several alternatives and rejected them, choosing this "
    "instead of the others.")
_LOAD_BEARING_ONLY = (
    "This is a load-bearing decision about internal dependency coupling.")
_ALTERNATIVELY_TEXT = "We could alternatively use a different color for the icon."
_SCHEMATIC_TEXT = "We redrew the schematic in the onboarding illustration."
# A real lightweight decision of the class the rubric routes to this home by
# name ("UI string or translation choices") that happens to say "user
# interface". BOUNDARY flags on its own, so a bare `interface` marker would
# refuse this — see the marker table's note and ADR-0042's Option A.
_UI_COPY_WITH_INTERFACE = (
    "Settings label wording",
    "Use 'Preferences' over 'Settings' in the user interface",
    "Matches the platform convention users already know",
    "settings screen",
)


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


class UpdateTimeRoutingGuidanceTests(unittest.TestCase):
    """100-01 — the routing enforcement chosen in ADR-0042 is PROSE: the
    memory-sync prompt tells the assistant to re-judge a lightweight decision
    against the ADR trigger when revising it, and to promote rather than
    revise when it clears.

    Deliberately does NOT assert a second verbatim `ADR_TRIGGER` copy in this
    file. `SingleSourceDriftTests` already pins one copy here with a
    whole-file `assertIn`, so a second copy would be (a) redundant
    single-sourcing within one file and (b) untestable — the drift assertion
    would pass on the OLD copy no matter what the guidance said. The guidance
    references that one copy instead; what is worth pinning is the linkage
    itself, which is what these tests do."""

    def setUp(self):
        self.text = MEMORY_SYNC_SKILL.read_text(encoding="utf-8")

    def test_guidance_fires_at_the_revision_moment(self):
        self.assertIn("Revising an already-recorded entry", self.text)

    def test_guidance_points_at_the_canonical_trigger(self):
        # The reference is only valid while the verbatim quote it points at
        # is in this same file — SingleSourceDriftTests guarantees that.
        self.assertIn("canonical ADR trigger quoted above", self.text)
        self.assertIn(decisions.ADR_TRIGGER, self.text)

    def test_guidance_routes_a_cleared_decision_to_promote(self):
        self.assertIn("decisions.py\" promote", self.text)
        self.assertIn("--title \"<existing title>\"", self.text)

    def test_guidance_keeps_in_place_revision_for_bounded_decisions(self):
        self.assertIn("decisions.py\" update", self.text)

    def test_guidance_names_the_advisory_lint_as_advisory(self):
        self.assertIn("decisions.py lint", self.text)
        self.assertIn("advisory", self.text)

    def test_guidance_warns_against_the_vocabulary_over_fire(self):
        """ADR-0042 rejected keyword-matching because UI-copy decisions say
        "X instead of Y" and belong in the lightweight home. The prose must
        carry that distinction, or it recreates the over-fire in the model's
        judgement instead of in a regex."""
        self.assertIn("Judge meaning, not vocabulary", self.text)


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


class RoutingEvaluatorTests(unittest.TestCase):
    """The pure lexical evaluator that backs the advisory lint (100-04 /
    ADR-0042). No project dir, no filesystem, no env — text in, matches out.
    ADR-0042 confines this to the report-only lint; it must not gate a write,
    so these tests pin behaviour, not a refusal."""

    # AC8 — importable, pure, structured output.
    def test_evaluator_is_a_plain_function_returning_named_matches(self):
        matches = decisions.evaluate_routing_signals(
            "t", "load-bearing change", "", "")
        self.assertIsInstance(matches, list)
        self.assertTrue(matches)
        m = matches[0]
        self.assertEqual(m.group, "LOAD_BEARING")
        self.assertEqual(m.phrase, "load-bearing")

    def test_no_markers_returns_empty_list(self):
        self.assertEqual(
            decisions.evaluate_routing_signals("t", "d", "c", "s"), [])

    # Edge case — empty/None context+scope must not crash the scan.
    def test_empty_context_and_scope_do_not_crash(self):
        self.assertEqual(
            decisions.evaluate_routing_signals("t", "d", "", ""), [])

    def test_none_context_and_scope_do_not_crash(self):
        self.assertEqual(
            decisions.evaluate_routing_signals("t", "d", None, None), [])

    # AC4 — ALTERNATIVES alone does not flag.
    def test_alternatives_alone_does_not_flag(self):
        matches = decisions.evaluate_routing_signals(
            "t", _ALTERNATIVES_ONLY, "", "")
        groups = {m.group for m in matches}
        self.assertEqual(groups, {"ALTERNATIVES"})
        self.assertFalse(decisions.flags_adr_routing(matches))

    # AC4 — LOAD_BEARING alone does not flag.
    def test_load_bearing_alone_does_not_flag(self):
        matches = decisions.evaluate_routing_signals(
            "t", _LOAD_BEARING_ONLY, "", "")
        groups = {m.group for m in matches}
        self.assertEqual(groups, {"LOAD_BEARING"})
        self.assertFalse(decisions.flags_adr_routing(matches))

    # AC2 (evaluator half) — BOUNDARY alone DOES flag.
    def test_boundary_alone_flags(self):
        matches = decisions.evaluate_routing_signals(
            "t", _BOUNDARY_ONLY, "", "")
        groups = {m.group for m in matches}
        self.assertEqual(groups, {"BOUNDARY"})
        self.assertTrue(decisions.flags_adr_routing(matches))

    # AC1 (evaluator half) — ALTERNATIVES + LOAD_BEARING together DOES flag.
    def test_alternatives_and_load_bearing_together_flag(self):
        matches = decisions.evaluate_routing_signals(
            "t", _LOAD_BEARING_HALF, _ALTERNATIVES_HALF, "")
        groups = {m.group for m in matches}
        self.assertEqual(groups, {"LOAD_BEARING", "ALTERNATIVES"})
        self.assertTrue(decisions.flags_adr_routing(matches))

    # AC3 (evaluator half) — jig's own illustrative UI-copy entry, read from
    # the real file, must not flag under either criterion.
    def test_illustrative_entry_does_not_flag(self):
        title, decision, context, scope = _real_illustrative_entry()
        matches = decisions.evaluate_routing_signals(
            title, decision, context, scope)
        self.assertFalse(
            decisions.flags_adr_routing(matches),
            "false positive on jig's own illustrative entry: %r" % (matches,))

    # Edge case — a marker inside a larger word must not match.
    def test_alternatively_does_not_fire_alternative_marker(self):
        matches = decisions.evaluate_routing_signals(
            "t", _ALTERNATIVELY_TEXT, "", "")
        self.assertEqual(matches, [])

    def test_schematic_does_not_fire_schema_marker(self):
        matches = decisions.evaluate_routing_signals(
            "t", _SCHEMATIC_TEXT, "", "")
        self.assertEqual(matches, [])

    # AC3's second corpus — a UI-copy decision that says "user interface".
    # BOUNDARY flags alone, so a bare `interface` marker refuses a decision the
    # rubric names as belonging here. Guards the narrowing to `public
    # interface`; a later re-widening fails on this rather than on a report
    # from the field.
    def test_user_interface_in_ui_copy_does_not_flag(self):
        matches = decisions.evaluate_routing_signals(*_UI_COPY_WITH_INTERFACE)
        self.assertFalse(
            decisions.flags_adr_routing(matches),
            "false positive on an ordinary UI-copy decision: %r" % (matches,))

    # AC7 — case-insensitive and whitespace-tolerant.
    def test_matching_is_case_insensitive_and_whitespace_tolerant(self):
        matches = decisions.evaluate_routing_signals(
            "t", "This changes the   MODULE\n   BOUNDARY  here.", "", "")
        groups = {m.group for m in matches}
        self.assertIn("BOUNDARY", groups)

    # AC7 — all four fields are scanned, not just decision/context.
    def test_all_four_fields_are_scanned(self):
        field_names = ("title", "decision", "context", "scope")
        for idx in range(4):
            args = ["", "", "", ""]
            args[idx] = "module boundary change"
            matches = decisions.evaluate_routing_signals(*args)
            groups = {m.group for m in matches}
            self.assertIn(
                "BOUNDARY", groups,
                "field %r was not scanned" % (field_names[idx],))


# ---- 100-02: `update` subcommand --------------------------------------

# A plain, addressable, single-entry fixture — no illustrative marker, so
# every entry in it is REAL per the 100-02 "real entry" notion. The default
# fixture for tests that exercise a normal revision.
_PLAIN_SEED = """# Lightweight Decisions

Some intro prose.

## Entries

### 2026-06-26 — Button copy

**Decision:** Use 'Get started'.

**Context:** User testing showed it tested lower-friction.

**Scope:** Onboarding CTA.
"""

# Three real entries in a row, plus the routing-rubric / `## Template` fence
# sections a real project file carries above `## Entries` — AC1 requires
# those, and every entry but the one under test, to survive an update
# byte-identical.
_MULTI_SEED = """# Lightweight Decisions

Some intro prose.

## Routing rubric — where does this decision land?

Some rubric text here.

## Template

```markdown
### [Date] — [Short title]

**Decision:** _what was decided_
```

---

## Entries

### 2026-06-01 — First entry

**Decision:** First decision.

**Context:** First context.

**Scope:** First scope.

### 2026-06-15 — Target entry

**Decision:** Old decision.

**Context:** Old context.

**Scope:** Old scope.

**Commit:** old-sha

### 2026-06-26 — Third entry

**Decision:** Third decision.

**Context:** Third context.

**Scope:** Third scope.
"""

# Same title, two dates — the AC5/AC6 disambiguation fixture.
_RECURRING_TITLE_SEED = """# Lightweight Decisions

## Entries

### 2026-06-01 — Recurring title

**Decision:** First decision.

**Context:** c

**Scope:** s

### 2026-06-15 — Recurring title

**Decision:** Second decision.

**Context:** c

**Scope:** s
"""


class EntriesSectionBoundTests(unittest.TestCase):
    """The `## Entries` section must START at a real heading line and STOP at
    the next H2.

    Without the stop bound the last entry's `**Scope:**` absorbs everything
    that follows — and since `update`/`promote` rewrite exactly the span the
    parser reports, the absorbed section is then DELETED. Reachable for any
    adopter who keeps another section below their entries, which
    `_foreign_format_error`'s own remedy ("add an `## Entries` heading to the
    existing file") actively invites."""

    _WITH_TRAILING_SECTION = (
        "# Lightweight Decisions\n\n"
        "## Entries\n\n"
        "### 2026-07-01 — First\n\n"
        "**Decision:** d\n\n"
        "**Context:** c\n\n"
        "**Scope:** s\n\n"
        "## Archive\n\n"
        "Old decisions worth keeping.\n"
    )

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(self._WITH_TRAILING_SECTION, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_last_entry_does_not_absorb_the_following_section(self):
        entry = decisions._real_entries(self._WITH_TRAILING_SECTION)[0]
        self.assertEqual(entry.scope, "s")

    def test_update_does_not_delete_the_following_section(self):
        decisions.update_lightweight(self.project, "First", scope="new scope")
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("## Archive", text)
        self.assertIn("Old decisions worth keeping.", text)
        self.assertIn("**Scope:** new scope", text)

    def test_promote_does_not_delete_the_following_section(self):
        """`_replace_entry_with_stub` rewrites the same span, so the bound
        protects promote too — asserted separately because the two callers
        splice differently (stub vs re-render)."""
        entry = decisions._real_entries(self._WITH_TRAILING_SECTION)[0]
        adr = self.target.parent / "adr-0001-x.md"
        adr.write_text("# ADR-0001: X\n", encoding="utf-8")
        stubbed = decisions._replace_entry_with_stub(
            self._WITH_TRAILING_SECTION, entry, adr)
        self.assertIn("## Archive", stubbed)
        self.assertIn("Old decisions worth keeping.", stubbed)

    def test_lint_does_not_scan_the_following_section(self):
        """An unbounded section also feeds unrelated prose to the evaluator,
        so a trailing section could raise findings against text that is not a
        decision at all."""
        report = decisions.lint_lightweight(self.project)
        self.assertEqual(report.scanned, 1)

    def test_entries_heading_must_be_a_heading_line_not_a_mention(self):
        """A prose mention of `## Entries` above the real heading must not
        move the section start — that would pull the `## Template` fence into
        scope as a parseable entry."""
        text = (
            "# Lightweight Decisions\n\n"
            "Record one per line under `## Entries` below.\n\n"
            "## Template\n\n"
            "### [Date] — [Short title]\n\n"
            "**Decision:** _what_\n\n"
            "**Context:** _why_\n\n"
            "**Scope:** _where_\n\n"
            "## Entries\n\n"
            "### 2026-07-01 — Real\n\n"
            "**Decision:** d\n\n"
            "**Context:** c\n\n"
            "**Scope:** s\n"
        )
        self.assertEqual([e.title for e in decisions._real_entries(text)],
                         ["Real"])


class ParseRoundTripTests(unittest.TestCase):
    """AC3's stated guard: a round trip through `render_entry` then the
    parser must return exactly the fields that went in, or `update`'s
    merge-and-re-render can silently corrupt fields it was told to
    preserve (AC2)."""

    def test_round_trips_all_fields_including_commit(self):
        rendered = decisions.render_entry(
            "Some title", "Some decision", "Some context", "Some scope",
            commit="abc123", date="2026-07-20")
        text = "# X\n\n## Entries\n\n" + rendered
        entries = decisions._real_entries(text)
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e.date, "2026-07-20")
        self.assertEqual(e.title, "Some title")
        self.assertEqual(e.decision, "Some decision")
        self.assertEqual(e.context, "Some context")
        self.assertEqual(e.scope, "Some scope")
        self.assertEqual(e.commit, "abc123")

    def test_round_trips_without_commit(self):
        rendered = decisions.render_entry(
            "T", "D", "C", "S", date="2026-07-20")
        text = "# X\n\n## Entries\n\n" + rendered
        entries = decisions._real_entries(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].commit, "")

    def test_round_trips_multiple_entries_in_order(self):
        entries = decisions._real_entries(_MULTI_SEED)
        self.assertEqual([e.title for e in entries],
                         ["First entry", "Target entry", "Third entry"])
        self.assertEqual(entries[1].commit, "old-sha")
        self.assertEqual(entries[0].commit, "")

    def test_template_fence_heading_is_not_a_real_entry(self):
        """AC7 (fence half) — `## Template`'s `### [Date] — [Short title]`
        precedes `## Entries` in every shipped copy of this file, so a
        parser scoped to start AFTER `## Entries` never sees it."""
        entries = decisions._real_entries(_MULTI_SEED)
        self.assertNotIn("[Short title]", [e.title for e in entries])


class UpdateLightweightTests(unittest.TestCase):
    """100-02 `update_lightweight` — the Python API `_cmd_update` calls."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self, text):
        self.target.write_text(text, encoding="utf-8")

    def _text(self):
        return self.target.read_text(encoding="utf-8")

    # AC1 — fields are revised on the matching entry.
    def test_revises_supplied_fields(self):
        self._seed(_PLAIN_SEED)
        changed = decisions.update_lightweight(
            self.project, "Button copy", decision="Use 'Sign up' instead")
        self.assertTrue(changed)
        text = self._text()
        self.assertIn("**Decision:** Use 'Sign up' instead", text)
        self.assertIn("**Context:** User testing showed it tested "
                      "lower-friction.", text)

    # AC1 — every other entry is byte-identical, and the rubric / Template
    # fence sections are untouched.
    def test_other_entries_and_sections_are_byte_identical(self):
        self._seed(_MULTI_SEED)
        decisions.update_lightweight(
            self.project, "Target entry", decision="Revised decision")
        text = self._text()
        self.assertIn(
            "### 2026-06-01 — First entry\n\n**Decision:** First decision."
            "\n\n**Context:** First context.\n\n**Scope:** First scope.",
            text)
        self.assertIn(
            "### 2026-06-26 — Third entry\n\n**Decision:** Third decision."
            "\n\n**Context:** Third context.\n\n**Scope:** Third scope.",
            text)
        self.assertIn("## Routing rubric — where does this decision land?"
                      "\n\nSome rubric text here.", text)
        self.assertIn("### [Date] — [Short title]", text)
        self.assertIn("**Decision:** _what was decided_", text)

    # AC2 — omitted fields preserved, not blanked. The OQ2 case: only
    # --commit supplied.
    def test_omitted_fields_are_preserved(self):
        self._seed(_MULTI_SEED)
        decisions.update_lightweight(
            self.project, "First entry", commit="deadbeef")
        text = self._text()
        self.assertIn(
            "### 2026-06-01 — First entry\n\n**Decision:** First decision."
            "\n\n**Context:** First context.\n\n**Scope:** First scope."
            "\n\n**Commit:** deadbeef\n\n### 2026-06-15", text)

    # AC3 — the rewritten block is byte-identical to render_entry's output
    # for the merged fields.
    def test_rewrite_matches_render_entry_byte_for_byte(self):
        self._seed(_PLAIN_SEED)
        decisions.update_lightweight(
            self.project, "Button copy", context="Revised context",
            commit="cafef00d")
        text = self._text()
        expected = decisions.render_entry(
            "Button copy", "Use 'Get started'.", "Revised context",
            "Onboarding CTA.", commit="cafef00d", date="2026-06-26")
        self.assertIn(expected, text)

    # AC4 — a missing entry is a loud refusal, and writes nothing.
    def test_missing_entry_refuses_and_writes_nothing(self):
        self._seed(_PLAIN_SEED)
        before = self._text()
        with self.assertRaises(ValueError):
            decisions.update_lightweight(
                self.project, "No such title", decision="x")
        self.assertEqual(self._text(), before)

    def test_missing_file_refuses(self):
        # self.target was never written in this test.
        with self.assertRaises(ValueError):
            decisions.update_lightweight(self.project, "Anything",
                                         decision="x")

    # AC5 — matching is case/whitespace-insensitive, reusing `_normalize`.
    def test_matching_is_case_and_whitespace_insensitive(self):
        self._seed(_PLAIN_SEED)
        changed = decisions.update_lightweight(
            self.project, "  button   COPY  ", decision="Revised")
        self.assertTrue(changed)
        self.assertIn("**Decision:** Revised", self._text())

    # AC5 — --date disambiguates a recurring title.
    def test_date_disambiguates_recurring_title(self):
        self._seed(_RECURRING_TITLE_SEED)
        decisions.update_lightweight(
            self.project, "Recurring title", decision="Revised second",
            date="2026-06-15")
        text = self._text()
        self.assertIn("### 2026-06-01 — Recurring title\n\n**Decision:** "
                      "First decision.", text)
        self.assertIn("### 2026-06-15 — Recurring title\n\n**Decision:** "
                      "Revised second", text)

    # AC6 — ambiguous match refuses rather than guessing, listing dates.
    def test_ambiguous_title_without_date_refuses_and_lists_dates(self):
        self._seed(_RECURRING_TITLE_SEED)
        before = self._text()
        with self.assertRaises(ValueError) as ctx:
            decisions.update_lightweight(
                self.project, "Recurring title", decision="x")
        msg = str(ctx.exception)
        self.assertIn("2026-06-01", msg)
        self.assertIn("2026-06-15", msg)
        self.assertEqual(self._text(), before)

    # Edge case — an entry with no Commit line gains one cleanly.
    def test_commit_added_cleanly_when_absent(self):
        self._seed(_PLAIN_SEED)
        decisions.update_lightweight(
            self.project, "Button copy", commit="newsha")
        text = self._text()
        self.assertIn(
            "**Scope:** Onboarding CTA.\n\n**Commit:** newsha\n", text)
        self.assertEqual(text.count("**Commit:**"), 1)

    # Edge case — the last block in the file: the trailing newline must
    # survive, matching what add_lightweight itself would have produced.
    def test_last_entry_update_leaves_single_trailing_newline(self):
        self._seed(_PLAIN_SEED)
        decisions.update_lightweight(
            self.project, "Button copy", decision="Revised")
        text = self._text()
        self.assertTrue(text.endswith("Onboarding CTA.\n"))
        self.assertFalse(text.endswith("\n\n"))

    # Edge case — an entry followed by another: the rewrite must not
    # swallow the following `### ` heading.
    def test_entry_followed_by_another_entry_preserves_it(self):
        self._seed(_MULTI_SEED)
        decisions.update_lightweight(
            self.project, "First entry", decision="Revised first")
        text = self._text()
        self.assertIn("**Decision:** Revised first", text)
        self.assertIn(
            "First scope.\n\n### 2026-06-15 — Target entry", text)
        entries = decisions._real_entries(text)
        self.assertEqual([e.title for e in entries],
                         ["First entry", "Target entry", "Third entry"])

    # Edge case — markdown that looks like a heading inside --decision must
    # not corrupt the file's structure. INLINE `### ` is legal and preserved.
    def test_decision_with_inline_heading_like_text_is_preserved(self):
        self._seed(_MULTI_SEED)
        decisions.update_lightweight(
            self.project, "Target entry",
            decision="See ### Not A Heading for details")
        text = self._text()
        entries = decisions._real_entries(text)
        self.assertEqual([e.title for e in entries],
                         ["First entry", "Target entry", "Third entry"])
        self.assertEqual(entries[1].decision,
                         "See ### Not A Heading for details")

    # The case the inline test above CANNOT reach: a LINE-INITIAL `### ` is
    # what actually delimits an entry, so a value carrying one used to split
    # its own entry and orphan it — invisible to update/promote/lint, no
    # error. Refused at the write instead.
    def test_line_initial_heading_in_decision_is_refused(self):
        self._seed(_MULTI_SEED)
        before = self._text()
        with self.assertRaises(ValueError) as ctx:
            decisions.update_lightweight(
                self.project, "Target entry",
                decision="line1\n### 2020-01-01 — Ghost\nmore")
        self.assertIn("### ", str(ctx.exception))
        self.assertEqual(self._text(), before, "refused write must not touch "
                                               "the file")
        self.assertEqual(
            [e.title for e in decisions._real_entries(self._text())],
            ["First entry", "Target entry", "Third entry"])

    def test_line_initial_heading_is_refused_on_add_too(self):
        """The guard lives in `render_entry`, the shared emitter — so the
        append path is covered by the same check, not a second copy."""
        with self.assertRaises(ValueError):
            decisions.add_lightweight(
                self.project, "Injected", "ok",
                "ctx\n### 2020-01-01 — Ghost", "s", date="2026-08-01")

    # Edge case — every supplied field already matches: reported no-op, not
    # a rewrite.
    def test_unchanged_update_is_a_noop(self):
        self._seed(_PLAIN_SEED)
        before = self._text()
        changed = decisions.update_lightweight(
            self.project, "Button copy", decision="Use 'Get started'.",
            context="User testing showed it tested lower-friction.",
            scope="Onboarding CTA.")
        self.assertFalse(changed)
        self.assertEqual(self._text(), before)


class UpdateNotAddressableTests(unittest.TestCase):
    """AC7 — the illustrative example and the `## Template` fence are not
    addressable through `update`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    # Generic structural marker — a project's own illustrative note, not
    # jig's specific wording, must be excluded too.
    def test_generic_illustrative_marker_is_not_addressable(self):
        self.target.write_text(_SEED, encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.update_lightweight(
                self.project, "Example entry", decision="x")
        self.assertEqual(self.target.read_text(encoding="utf-8"), _SEED)

    # Grounded against the real corpus, not a hand-transcribed copy, so an
    # edit to the illustrative entry can't leave this silently stale.
    def test_real_illustrative_worked_example_is_not_addressable(self):
        rubric_text = RUBRIC.read_text(encoding="utf-8")
        self.target.write_text(rubric_text, encoding="utf-8")
        title, _, _, _ = _real_illustrative_entry()
        with self.assertRaises(ValueError):
            decisions.update_lightweight(self.project, title, decision="x")
        self.assertEqual(self.target.read_text(encoding="utf-8"), rubric_text)

    def test_template_fence_placeholder_is_not_addressable(self):
        template_text = TEMPLATE.read_text(encoding="utf-8")
        self.target.write_text(template_text, encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.update_lightweight(
                self.project, "[Short title]", decision="x")
        self.assertEqual(self.target.read_text(encoding="utf-8"),
                         template_text)


class UpdateRoutingGuardTests(unittest.TestCase):
    """AC8 — a guard against re-introducing the rejected write-gate
    (ADR-0042). `update` carries no `--confirm-lightweight` and refuses only
    on matching grounds, never on the decision's content."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PLAIN_SEED, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_confirm_lightweight_flag_on_update(self):
        with self.assertRaises(SystemExit):
            _run_cli(["update", "--title", "Button copy",
                     "--confirm-lightweight",
                     "--project-dir", str(self.project)])

    def test_content_that_flags_every_routing_marker_does_not_block_update(self):
        rc, err = _run_cli([
            "update", "--title", "Button copy",
            "--decision", _LOAD_BEARING_HALF + " " + _ALTERNATIVES_HALF
            + " " + _BOUNDARY_ONLY,
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 0, err)

    def test_module_source_imports_no_gate_machinery(self):
        # `--confirm-lightweight` deliberately is NOT asserted absent from
        # the source text here: the module carries an explanatory comment
        # naming it (documenting *why* it must not be added), which would
        # make an unconditional substring check self-defeating. The actual
        # structural absence — no such option registered on `update`'s
        # parser — is what `test_no_confirm_lightweight_flag_on_update`
        # exercises.
        src = DECISIONS_PY.read_text(encoding="utf-8")
        self.assertNotIn("gate_telemetry", src)
        self.assertNotIn("_common.parsing", src)

    def test_evaluator_is_reachable_only_from_lint(self):
        """ADR-0042's actual boundary: the lexical evaluator must not be
        wired into any write path. Asserted over the AST, not the source
        text — prose in docstrings names these functions, so a substring
        check reports matches that are not call sites."""
        tree = ast.parse(DECISIONS_PY.read_text(encoding="utf-8"))
        callers = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id == "evaluate_routing_signals"):
                    callers.append(node.name)
        self.assertEqual(
            sorted(set(callers)), ["lint_lightweight"],
            "the evaluator must be called only by the advisory lint; "
            "callers were %r" % (sorted(set(callers)),))

    def test_self_containment_imports(self):
        """The module docstring's standing rule: no cross-tree import of the
        scan lib, memory.py, or adr.py (the subprocess call to adr.py is the
        documented carve-out, and is not an import). Previously unguarded —
        the rule was prose only. AST-based, so the docstring that *describes*
        the rule does not trip it."""
        tree = ast.parse(DECISIONS_PY.read_text(encoding="utf-8"))
        forbidden = {"decision_scan", "memory", "adr"}
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertEqual(
            imported & forbidden, set(),
            "decisions.py must stay self-contained; forbidden import(s): %r"
            % (sorted(imported & forbidden),))


class UpdateCliTests(unittest.TestCase):
    """CLI-level (`decisions.main(["update", ...])`) smoke coverage — the
    Python-API tests above already pin the parsing/merge/rewrite behaviour
    in detail."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PLAIN_SEED, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_cli_updates_and_reports_success(self):
        rc, err = _run_cli([
            "update", "--title", "Button copy", "--commit", "abc123",
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 0, err)
        self.assertIn("**Commit:** abc123",
                      self.target.read_text(encoding="utf-8"))

    def test_cli_missing_entry_exits_nonzero_and_names_it(self):
        rc, err = _run_cli([
            "update", "--title", "No such title", "--decision", "x",
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 1)
        self.assertIn("no such title", err.lower())

    def test_cli_missing_title_is_a_required_argparse_error(self):
        with self.assertRaises(SystemExit):
            _run_cli(["update", "--decision", "x",
                     "--project-dir", str(self.project)])


# ---- 100-03: `promote` subcommand --------------------------------------

ADR_PY = REPO_ROOT / "skills" / "adr-workflow" / "adr.py"

# A single, addressable, plain entry with real Context/Scope text — the
# default fixture for tests that exercise a normal promotion.
_PROMOTABLE_SEED = "# Lightweight Decisions\n\n## Entries\n\n" + decisions.render_entry(
    "Button copy", "Use 'Get started'.",
    "User testing showed it tested lower-friction.", "Onboarding CTA.",
    date="2026-06-26")

# Context AND Scope both blank — both are optional at write time
# (`_require_entry_fields` only requires title + decision). Built through
# `render_entry` itself (not hand-typed) so the exact whitespace shape
# `_FIELD_RE` expects for an empty field is never guessed at.
_MINIMAL_ENTRY_SEED = "# Lightweight Decisions\n\n## Entries\n\n" + decisions.render_entry(
    "Minimal entry", "Do the thing.", "", "", date="2026-07-01")

# A pre-promoted stub, matching 100-03's own rendering — the AC8 fixture.
_ALREADY_PROMOTED_SEED = """# Lightweight Decisions

## Entries

### 2026-05-01 — Old decision

**Promoted:** moved to [ADR-0007: Old Decision](adr-0007-old-decision.md).
"""


class PromoteSlugDerivationTests(unittest.TestCase):
    """`_default_slug_from_title` — the pure kebab-casing + validation that
    backs AC1's default slug and the three edge cases (empty / leading
    digit / consecutive hyphens)."""

    def test_ordinary_title_kebab_cases_cleanly(self):
        self.assertEqual(
            decisions._default_slug_from_title("Button copy"),
            "button-copy")

    def test_title_with_existing_single_hyphen_is_fine(self):
        self.assertEqual(
            decisions._default_slug_from_title("Settings-label wording"),
            "settings-label-wording")

    # Edge case — empty (all-punctuation title).
    def test_all_punctuation_title_refuses(self):
        with self.assertRaises(ValueError) as ctx:
            decisions._default_slug_from_title("???")
        self.assertIn("--slug", str(ctx.exception))

    # Edge case — leading digit.
    def test_leading_digit_refuses(self):
        with self.assertRaises(ValueError) as ctx:
            decisions._default_slug_from_title("2026 upgrade")
        msg = str(ctx.exception)
        self.assertIn("digit", msg)
        self.assertIn("--slug", msg)

    # Edge case — consecutive hyphens (adjacent punctuation collides).
    def test_consecutive_hyphens_refuse(self):
        with self.assertRaises(ValueError) as ctx:
            decisions._default_slug_from_title("A -- B")
        msg = str(ctx.exception)
        self.assertIn("consecutive hyphens", msg)
        self.assertIn("--slug", msg)

    def test_does_not_silently_mangle(self):
        """The refusal must not have written a collapsed/stripped slug
        anywhere the caller could mistake for success — a raise, not a
        best-effort guess."""
        with self.assertRaises(ValueError):
            decisions._default_slug_from_title("2026 -- upgrade")


class PromoteAdrLocatorTests(unittest.TestCase):
    """`_adr_py_path` — sibling-skill resolution (100-03 design decision
    #2). Run against the REAL repo checkout, where decisions.py's sibling
    adr-workflow skill genuinely exists."""

    def test_finds_the_real_sibling_adr_py(self):
        found = decisions._adr_py_path()
        self.assertIsNotNone(found)
        self.assertEqual(found.resolve(), ADR_PY.resolve())

    def test_never_raises_when_absent(self):
        """Simulates a tier-0-only install with no adr-workflow sibling by
        monkeypatching the locator's own `__file__`-derived directory via a
        stand-in module attribute is impractical (the function reads
        `Path(__file__)` directly) — so this pins the documented CONTRACT
        (never raises, returns None) via the CLAUDE_PLUGIN_ROOT-fallback
        branch pointed at a directory with no `skills/adr-workflow/`, which
        cannot mask the always-present real sibling. Real absence is
        exercised behaviorally by PromoteAdrNotFoundTests below (which
        monkeypatches `decisions._adr_py_path` itself — the only seam that
        does not depend on decisions.py's own file location)."""
        saved = os.environ.get("CLAUDE_PLUGIN_ROOT")
        try:
            with tempfile.TemporaryDirectory() as td:
                os.environ["CLAUDE_PLUGIN_ROOT"] = td
                # The real sibling (own.parent/adr-workflow/adr.py) still
                # resolves regardless of CLAUDE_PLUGIN_ROOT — this just
                # pins that the function does not raise when the
                # plugin-root fallback candidate is unreachable.
                found = decisions._adr_py_path()
        finally:
            if saved is None:
                os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
            else:
                os.environ["CLAUDE_PLUGIN_ROOT"] = saved
        self.assertIsNotNone(found)


class RunAdrNewArgvTests(unittest.TestCase):
    """`_adr_new_argv` — pure argv construction, so AC5's flag-threading is
    pinned without a real subprocess for every combination."""

    def _argv(self, **kw):
        defaults = dict(adr_py=Path("/adr.py"), slug="slug", title="Title",
                        project_dir=Path("/proj"), no_push=False,
                        pr_mode=False)
        defaults.update(kw)
        return decisions._adr_new_argv(**defaults)

    def test_no_push_flag_appended(self):
        argv = self._argv(no_push=True)
        self.assertIn("--no-push", argv)
        self.assertNotIn("--pr", argv)

    def test_pr_flag_appended(self):
        argv = self._argv(pr_mode=True)
        self.assertIn("--pr", argv)
        self.assertNotIn("--no-push", argv)

    def test_neither_flag_by_default(self):
        argv = self._argv()
        self.assertNotIn("--no-push", argv)
        self.assertNotIn("--pr", argv)

    def test_project_dir_and_title_and_slug_present(self):
        argv = self._argv()
        self.assertIn("slug", argv)
        self.assertIn("--title", argv)
        self.assertIn("Title", argv)
        self.assertIn("--project-dir", argv)
        self.assertIn("/proj", argv)

    def test_invoked_with_sys_executable(self):
        argv = self._argv()
        self.assertEqual(argv[0], sys.executable)


class PromoteStubDetectionTests(unittest.TestCase):
    """`_find_promoted_stub` — the AC8 lookup, pure text-in/text-out."""

    def test_detects_a_promoted_stub_and_returns_its_filename(self):
        found = decisions._find_promoted_stub(
            _ALREADY_PROMOTED_SEED, "Old decision")
        self.assertEqual(found, "adr-0007-old-decision.md")

    def test_ordinary_real_entry_is_not_a_stub(self):
        self.assertIsNone(
            decisions._find_promoted_stub(_PROMOTABLE_SEED, "Button copy"))

    def test_no_match_returns_none(self):
        self.assertIsNone(
            decisions._find_promoted_stub(_ALREADY_PROMOTED_SEED,
                                          "No such title"))


class PromoteNotAddressableTests(unittest.TestCase):
    """AC9 — the illustrative example and the `## Template` fence are not
    promotable, same exclusion as `update`'s AC7. Mirrors
    UpdateNotAddressableTests. No subprocess is ever invoked here — the
    refusal happens before `promote_lightweight` reaches `adr.py`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_generic_illustrative_marker_is_not_promotable(self):
        self.target.write_text(_SEED, encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Example entry")
        self.assertEqual(self.target.read_text(encoding="utf-8"), _SEED)

    def test_real_illustrative_worked_example_is_not_promotable(self):
        rubric_text = RUBRIC.read_text(encoding="utf-8")
        self.target.write_text(rubric_text, encoding="utf-8")
        title, _, _, _ = _real_illustrative_entry()
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, title)
        self.assertEqual(self.target.read_text(encoding="utf-8"), rubric_text)

    def test_template_fence_placeholder_is_not_promotable(self):
        template_text = TEMPLATE.read_text(encoding="utf-8")
        self.target.write_text(template_text, encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "[Short title]")
        self.assertEqual(self.target.read_text(encoding="utf-8"),
                         template_text)


class PromoteMissingOrAmbiguousTests(unittest.TestCase):
    """AC7 — same matching rules and messages as `update`'s AC4-AC6."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_entry_refuses_and_writes_nothing(self):
        self.target.write_text(_PLAIN_SEED, encoding="utf-8")
        before = self.target.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "No such title")
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)

    def test_missing_file_refuses(self):
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Anything")

    def test_ambiguous_title_without_date_refuses_and_lists_dates(self):
        self.target.write_text(_RECURRING_TITLE_SEED, encoding="utf-8")
        before = self.target.read_text(encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(self.project, "Recurring title")
        msg = str(ctx.exception)
        self.assertIn("2026-06-01", msg)
        self.assertIn("2026-06-15", msg)
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)

    def test_foreign_format_refuses(self):
        self.target.write_text(_FOREIGN_TABLE, encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "t")


class PromoteAlreadyPromotedTests(unittest.TestCase):
    """AC8 — re-running promote on an already-promoted entry refuses,
    naming the ADR it already points to, and never invokes `adr.py`."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_ALREADY_PROMOTED_SEED, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_refuses_naming_the_existing_adr(self):
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(self.project, "Old decision")
        self.assertIn("adr-0007-old-decision.md", str(ctx.exception))

    def test_writes_nothing(self):
        before = self.target.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Old decision")
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)

    def test_never_invokes_adr_py(self):
        from unittest.mock import patch
        with patch.object(decisions, "_run_adr_new") as run_mock:
            with self.assertRaises(ValueError):
                decisions.promote_lightweight(self.project, "Old decision")
            run_mock.assert_not_called()


class PromoteAdrNotFoundTests(unittest.TestCase):
    """100-03 design decision #2 — when no adr-workflow sibling resolves,
    `promote` refuses cleanly (exit non-zero, write nothing) rather than
    raising an unhandled exception. Exercised via monkeypatching
    `decisions._adr_py_path` itself, the only seam that does not depend on
    decisions.py's own real file location (which always has a real
    sibling in this checkout)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PROMOTABLE_SEED, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_refuses_cleanly_and_names_the_missing_skill(self):
        from unittest.mock import patch
        before = self.target.read_text(encoding="utf-8")
        with patch.object(decisions, "_adr_py_path", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                decisions.promote_lightweight(self.project, "Button copy")
        msg = str(ctx.exception)
        self.assertIn("adr-workflow", msg)
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)


# ---- 100-03: real-subprocess end-to-end tests --------------------------
#
# `promote` invokes `adr.py new` as a REAL subprocess (100-03 design
# decision #1) — these tests run it for real, against a real git repo,
# mirroring adr-workflow/test_adr.py's `ReserveAdrCLITests`. `promote`'s
# own subprocess call carries no `env=` override (see `_run_adr_new`), so
# the child inherits THIS test process's environment — identity vars are
# set on `os.environ` itself (not just passed to the one-off `git init`
# calls) so the git commit nested two subprocess-hops down still succeeds
# on a CI runner with no global git identity.

_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def _git_init_off_main(repo_dir: Path) -> None:
    """A fresh git repo on a non-`main` branch (`work`), so `adr.py new`'s
    OFF-main routing (`_reserve_local_on_current_branch` for --no-push, or
    `_reserve_via_detached_worktree` otherwise) is what these tests
    exercise. The on-`main` path requires a CLEAN working tree (`adr.py`'s
    `_refuse_if_dirty`), which seeding lightweight-decisions.md AFTER init
    would violate — off-main + --no-push scopes its own commit to just the
    new ADR file (`git commit -- <adr-path>`), so the rest of the tree being
    "dirty" (our seeded lightweight file, scaffold.json) is a non-issue.
    Scaffold-classified as `scaffolded` (adr.py's `reserve_adr`
    precondition) via `scaffold.json` — not git-tracked; the classifier
    reads it straight off disk."""
    env = {**os.environ, **_GIT_IDENTITY}
    subprocess.run(["git", "init", "-q", "-b", "work", str(repo_dir)],
                   env=env, check=True, capture_output=True)
    (repo_dir / "scaffold.json").write_text("{}\n", encoding="utf-8")


class _PromoteE2ETestCase(unittest.TestCase):
    """Shared fixture for the real-subprocess promote tests below."""

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        _git_init_off_main(self.project)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self._saved_env = {k: os.environ.get(k) for k in _GIT_IDENTITY}
        os.environ.update(_GIT_IDENTITY)

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def _seed(self, text):
        self.target.write_text(text, encoding="utf-8")

    def _text(self):
        return self.target.read_text(encoding="utf-8")


class PromoteEndToEndTests(_PromoteE2ETestCase):
    """AC1-AC5 — the real `adr.py new` round trip."""

    # AC1 — creates the ADR through adr.py, default slug.
    def test_ac1_creates_adr_via_adr_new_default_slug(self):
        self._seed(_PROMOTABLE_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        self.assertTrue(adr_path.is_file())
        self.assertEqual(adr_path.name, "adr-0001-button-copy.md")

    # AC1 — --slug overrides the default.
    def test_ac1_slug_override(self):
        self._seed(_PROMOTABLE_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", slug="custom-slug", no_push=True)
        self.assertEqual(adr_path.name, "adr-0001-custom-slug.md")

    # AC2 — Decision/Context/Scope land in the ADR.
    def test_ac2_seeds_decision_context_scope(self):
        self._seed(_PROMOTABLE_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        text = adr_path.read_text(encoding="utf-8")
        self.assertIn("Use 'Get started'.", text)
        self.assertIn("User testing showed it tested lower-friction.", text)
        self.assertIn("Onboarding CTA.", text)

    # AC2 — the seeded sections keep the template's one-blank-line spacing.
    # A `\s*$` heading match swallows the newline, so the re-added spacing
    # renders `## Context` followed by TWO blank lines; caught by probing a
    # real promotion, invisible to a substring assertion.
    def test_ac2_seeded_sections_have_no_double_blank_line(self):
        self._seed(_PROMOTABLE_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        text = adr_path.read_text(encoding="utf-8")
        for heading in ("Context", "Recommended Decision"):
            self.assertNotIn(
                "## %s\n\n\n" % heading, text,
                "'## %s' rendered with a doubled blank line" % heading)
            self.assertIn("## %s\n\n" % heading, text)

    # Edge case — empty Context/Scope keep the template's own placeholder.
    def test_edge_empty_context_and_scope_keep_template_placeholder(self):
        self._seed(_MINIMAL_ENTRY_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Minimal entry", no_push=True)
        text = adr_path.read_text(encoding="utf-8")
        self.assertIn(
            "_TODO: describe the situation, forces, and constraints "
            "driving this decision._", text)
        self.assertIn(
            "_TODO: which screen / component / string / asset._", text)
        self.assertIn("Do the thing.", text)

    # AC3 — the entry becomes a forward-linking stub; heading preserved.
    def test_ac3_entry_replaced_by_stub_heading_preserved(self):
        self._seed(_PROMOTABLE_SEED)
        decisions.promote_lightweight(self.project, "Button copy",
                                      no_push=True)
        text = self._text()
        self.assertIn("### 2026-06-26 — Button copy", text)
        self.assertNotIn("**Decision:** Use 'Get started'.", text)
        self.assertIn("**Promoted:**", text)
        self.assertIn("adr-0001-button-copy.md", text)

    def test_ac3_entry_never_deleted_heading_count_unchanged(self):
        self._seed(_PROMOTABLE_SEED)
        before_headings = self._text().count("### ")
        decisions.promote_lightweight(self.project, "Button copy",
                                      no_push=True)
        after_headings = self._text().count("### ")
        self.assertEqual(before_headings, after_headings)

    # AC4 — the ADR back-links to the entry, naming the original date.
    def test_ac4_adr_back_links_to_entry_with_original_date(self):
        self._seed(_PROMOTABLE_SEED)
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        text = adr_path.read_text(encoding="utf-8")
        self.assertIn("2026-06-26", text)
        self.assertIn("lightweight-decisions.md", text)

    # AC5 — --no-push reaches adr.py new and suppresses the push.
    def test_ac5_no_push_creates_adr_without_touching_origin(self):
        self._seed(_PROMOTABLE_SEED)
        # No 'origin' remote was ever configured on this repo. If adr.py had
        # attempted a push it would fail loudly (no push destination), so a
        # successful return here proves --no-push suppressed it.
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        self.assertTrue(adr_path.is_file())

    def test_default_push_mode_fails_without_an_origin_remote(self):
        """Negative control for the AC5 test above: proves the fixture (no
        origin remote) actually WOULD surface a push attempt, so the
        --no-push test's success is meaningful rather than coincidental."""
        self._seed(_PROMOTABLE_SEED)
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Button copy")
        # And the lightweight file is untouched by the failed attempt.
        self.assertIn("Button copy", self._text())
        self.assertIn("**Decision:** Use 'Get started'.", self._text())


class PromoteDefaultPushModeTests(unittest.TestCase):
    """The DEFAULT push mode, end-to-end against a real `origin`.

    Regression guard for a defect that hid behind `--no-push`-only coverage:
    `promote` used to take `adr.py new`'s LAST stdout line as the created
    ADR's path. adr.py prints the path and then keeps printing — `reserved …
    on origin/main` after a successful push, the PR URL on the `--pr`
    fallback — so every mode except `--no-push` aborted with "reported a path
    that does not exist" AFTER the ADR had been created, committed and
    pushed: precisely the half-promoted state `promote_lightweight`'s
    ordering exists to prevent. Resolution is by slug now, not by position."""

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.origin = root / "origin.git"
        self.project = root / "work"
        env = {**os.environ, **_GIT_IDENTITY}
        self._saved_env = {k: os.environ.get(k) for k in _GIT_IDENTITY}
        os.environ.update(_GIT_IDENTITY)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main",
                        str(self.origin)], env=env, check=True,
                       capture_output=True)
        subprocess.run(["git", "clone", "-q", str(self.origin),
                        str(self.project)], env=env, check=True,
                       capture_output=True)
        (self.project / "scaffold.json").write_text("{}\n", encoding="utf-8")
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PROMOTABLE_SEED, encoding="utf-8")
        # adr.py's on-main path refuses a dirty tree, so commit the seed.
        for argv in (["git", "add", "-A"],
                     ["git", "commit", "-q", "-m", "seed"],
                     ["git", "push", "-q", "origin", "main"]):
            subprocess.run(argv, cwd=self.project, env=env, check=True,
                           capture_output=True)

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def test_default_push_mode_promotes_successfully(self):
        adr_path = decisions.promote_lightweight(self.project, "Button copy")
        self.assertTrue(adr_path.is_file())
        self.assertEqual(adr_path.name, "adr-0001-button-copy.md")
        text = self.target.read_text(encoding="utf-8")
        self.assertIn("**Promoted:**", text)
        self.assertIn("adr-0001-button-copy.md", text)

    def test_default_push_mode_actually_pushed(self):
        """Negative control: proves the fixture really is exercising the
        push path, so the test above is not passing on a silent fallback."""
        decisions.promote_lightweight(self.project, "Button copy")
        out = subprocess.run(
            ["git", "ls-tree", "--name-only", "-r", "main"],
            cwd=self.origin, capture_output=True, text=True, check=True).stdout
        self.assertIn("adr-0001-button-copy.md", out)


class PromotePushModeOffMainTests(unittest.TestCase):
    """Push-mode `promote` from anywhere but `main` refuses BEFORE creating
    anything.

    The defect this guards: `adr.py new` in push mode routes on the caller's
    branch. On `main` it writes/commits/pushes in the caller's own tree, so
    the ADR is on disk to seed. OFF `main` — jig's normal worktree-per-task
    mode — it builds the reservation in an EPHEMERAL DETACHED worktree at
    origin/main and pushes `HEAD:main`, so the ADR lands on the shared trunk
    and never in the caller's copy. `promote` then found nothing to seed and
    aborted AFTER the push, leaving an orphaned ADR on origin/main whose slug
    a re-run could not reuse (`adr.py` refuses on slug collision) — no
    self-service way forward.

    `PromoteDefaultPushModeTests` above covers push mode but clones fresh, so
    it runs on `main`; this class is the off-main half it could not see.

    Deliberately fixtured with a REAL bare origin the branch can reach, rather
    than reusing `_PromoteE2ETestCase`'s remote-less repo. Without a reachable
    origin the unguarded code fails anyway — `adr.py` cannot build its
    reservation worktree — and its refusal happens to quote `--no-push` too, so
    a remote-less fixture lets these tests pass for the wrong reason. With a
    live origin the unguarded path really does reserve, push, and only then
    abort, which is the defect being pinned; `test_..._pushes_nothing_to_origin`
    is what actually witnesses it.
    """

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not on PATH")
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.origin = root / "origin.git"
        self.project = root / "work"
        env = {**os.environ, **_GIT_IDENTITY}
        self._saved_env = {k: os.environ.get(k) for k in _GIT_IDENTITY}
        os.environ.update(_GIT_IDENTITY)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main",
                        str(self.origin)], env=env, check=True,
                       capture_output=True)
        subprocess.run(["git", "clone", "-q", str(self.origin),
                        str(self.project)], env=env, check=True,
                       capture_output=True)
        (self.project / "scaffold.json").write_text("{}\n", encoding="utf-8")
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PROMOTABLE_SEED, encoding="utf-8")
        for argv in (["git", "add", "-A"],
                     ["git", "commit", "-q", "-m", "seed"],
                     ["git", "push", "-q", "origin", "main"],
                     # The whole point: off `main`, on a real branch.
                     ["git", "checkout", "-q", "-b", "work"]):
            subprocess.run(argv, cwd=self.project, env=env, check=True,
                           capture_output=True)

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def _origin_adrs(self):
        out = subprocess.run(
            ["git", "ls-tree", "--name-only", "-r", "main"],
            cwd=self.origin, capture_output=True, text=True, check=True).stdout
        return [line for line in out.splitlines() if "/adr-" in line]

    def _text(self):
        return self.target.read_text(encoding="utf-8")

    def test_default_push_mode_off_main_refuses(self):
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(self.project, "Button copy")
        msg = str(ctx.exception)
        self.assertIn("needs --no-push", msg)
        self.assertIn("'work'", msg)

    def test_pr_mode_off_main_refuses(self):
        """`--pr` off main fails the same way (`_pr_fallback_from_worktree`
        pushes the reservation to a remote branch, equally out of tree), so the
        guard covers both push shapes — anything but `--no-push`."""
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(
                self.project, "Button copy", pr_mode=True)
        self.assertIn("needs --no-push", str(ctx.exception))

    def test_refusal_pushes_nothing_to_origin(self):
        """The load-bearing assertion. Unguarded, this reserved and PUSHED
        `adr-0001-button-copy.md` to origin/main and only then aborted,
        stranding a record whose slug no re-run could reuse. An empty origin
        is the proof the refusal happened first."""
        self.assertEqual(self._origin_adrs(), [])
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Button copy")
        self.assertEqual(self._origin_adrs(), [])

    def test_refusal_creates_no_local_adr_and_leaves_the_entry_untouched(self):
        before = self._text()
        with self.assertRaises(ValueError):
            decisions.promote_lightweight(self.project, "Button copy")
        self.assertEqual(self._text(), before)
        self.assertEqual(
            sorted(p.name for p in self.target.parent.glob("adr-*.md")), [])

    def test_detached_head_refuses(self):
        """A detached HEAD is not `main` either, and is exactly what jig's own
        ephemeral-worktree machinery leaves a caller sitting on."""
        subprocess.run(["git", "checkout", "-q", "--detach"],
                       cwd=self.project, check=True, capture_output=True)
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(self.project, "Button copy")
        self.assertIn("detached HEAD", str(ctx.exception))

    def test_no_push_off_main_still_promotes(self):
        """Control: the guard must not touch `--no-push`, which off main routes
        to `_reserve_local_on_current_branch` and DOES write into the caller's
        tree. Without this, the refusals above could pass by breaking promote
        outright."""
        adr_path = decisions.promote_lightweight(
            self.project, "Button copy", no_push=True)
        self.assertTrue(adr_path.is_file())
        self.assertIn("**Promoted:**", self._text())
        # Local-only: the reservation must not have reached the trunk.
        self.assertEqual(self._origin_adrs(), [])


class PromotedStubSectionBoundTests(unittest.TestCase):
    """`_find_promoted_stub` is scoped exactly as `_real_entries` is.

    `_real_entries` was bounded at the next H2 and anchored on a real
    `## Entries` heading line; its sibling still used a bare substring
    `.find()` with no bound, so a stub in a FOLLOWING section answered for a
    live entry. Because `promote_lightweight` consults it FIRST, that surfaced
    as a false "already promoted" refusing a legitimate promotion. The file
    shape is the one `_foreign_format_error`'s remedy 1 invites: `## Entries`
    added to an existing document whose own content stays below.
    """

    _WITH_ARCHIVE = """# Lightweight Decisions

## Entries

### 2026-07-01 — Button copy

**Decision:** Use "Save" over "Submit".

**Context:** User testing.

**Scope:** Settings form.

## Archive

### 2024-01-01 — Button copy

**Promoted:** moved to [ADR-0007: Old thing](adr-0007-old-thing.md).
"""

    def test_stub_in_a_following_section_is_not_found(self):
        self.assertIsNone(
            decisions._find_promoted_stub(self._WITH_ARCHIVE, "Button copy"))

    def test_the_live_entry_is_still_the_addressable_one(self):
        """Pins the two halves against each other: the same title resolves to
        the live entry, so the archived stub shadows nothing."""
        entries = decisions._real_entries(self._WITH_ARCHIVE)
        self.assertEqual([(e.date, e.title) for e in entries],
                         [("2026-07-01", "Button copy")])

    def test_prose_mentioning_the_heading_does_not_move_the_section(self):
        """The anchoring half: a passing mention of `## Entries` above the real
        heading must not pull earlier content into scope."""
        text = ("# Lightweight Decisions\n\nEntries live under the "
                "`## Entries` heading below.\n\n" + _ALREADY_PROMOTED_SEED
                .split("# Lightweight Decisions\n\n", 1)[1])
        self.assertEqual(
            decisions._find_promoted_stub(text, "Old decision"),
            "adr-0007-old-decision.md")

    def test_a_real_stub_inside_the_section_is_still_found(self):
        """Control: narrowing the scan must not blind it to the case it
        exists for (AC8's already-promoted refusal)."""
        self.assertEqual(
            decisions._find_promoted_stub(_ALREADY_PROMOTED_SEED,
                                          "Old decision"),
            "adr-0007-old-decision.md")


class PromoteCliTests(_PromoteE2ETestCase):
    """CLI-level (`decisions.main(["promote", ...])`) smoke coverage."""

    def test_cli_promotes_and_reports_success(self):
        self._seed(_PROMOTABLE_SEED)
        rc, err = _run_cli([
            "promote", "--title", "Button copy", "--no-push",
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 0, err)
        self.assertIn("**Promoted:**", self._text())

    def test_cli_missing_entry_exits_nonzero(self):
        self._seed(_PLAIN_SEED)
        rc, err = _run_cli([
            "promote", "--title", "No such title", "--no-push",
            "--project-dir", str(self.project)])
        self.assertEqual(rc, 1)
        self.assertIn("no such title", err.lower())

    def test_cli_missing_title_is_a_required_argparse_error(self):
        with self.assertRaises(SystemExit):
            _run_cli(["promote", "--no-push",
                     "--project-dir", str(self.project)])

    def test_cli_no_push_and_pr_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            _run_cli(["promote", "--title", "Button copy", "--no-push",
                     "--pr", "--project-dir", str(self.project)])


class PromoteAtomicityTests(unittest.TestCase):
    """AC6 — atomicity, proven by an INDUCED real `adr.py new` failure, not
    mock inspection. `CLAUDE_PLUGIN_ROOT` is pointed at a bare directory
    that carries no `templates/` tree — mirroring
    `UnreachableTemplateTests` above — so the nested `adr.py new` subprocess
    (which inherits this process's environment; `promote` passes no `env=`
    override) genuinely fails to find its template and exits non-zero. No
    git repo is needed: `--no-push` off the `main` branch (a bare tempdir
    has no branch at all) reaches the template check before any git call."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        (self.project / "scaffold.json").write_text("{}\n", encoding="utf-8")
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(_PROMOTABLE_SEED, encoding="utf-8")

        self._broken_root_tmp = tempfile.TemporaryDirectory()
        self._saved_plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        os.environ["CLAUDE_PLUGIN_ROOT"] = self._broken_root_tmp.name

    def tearDown(self):
        if self._saved_plugin_root is None:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        else:
            os.environ["CLAUDE_PLUGIN_ROOT"] = self._saved_plugin_root
        self._broken_root_tmp.cleanup()
        self._tmp.cleanup()

    def test_induced_adr_new_failure_leaves_lightweight_file_byte_identical(self):
        before = self.target.read_text(encoding="utf-8")
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(
                self.project, "Button copy", no_push=True)
        self.assertIn("adr.py new failed", str(ctx.exception))
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)

    def test_induced_adr_new_failure_is_a_real_template_not_found(self):
        """Confirms the induced failure is the specific one this test
        targets (template unreachable), not some unrelated refusal."""
        with self.assertRaises(ValueError) as ctx:
            decisions.promote_lightweight(
                self.project, "Button copy", no_push=True)
        self.assertIn("template not found", str(ctx.exception).lower())

    def test_cli_exits_nonzero_and_writes_nothing(self):
        before = self.target.read_text(encoding="utf-8")
        rc, err = _run_cli([
            "promote", "--title", "Button copy", "--no-push",
            "--project-dir", str(self.project)])
        self.assertNotEqual(rc, 0)
        self.assertEqual(self.target.read_text(encoding="utf-8"), before)


class PromotePostCreationFailureDisclosureTests(_PromoteE2ETestCase):
    """A failure AFTER `adr.py new` succeeded must name the orphaned ADR.

    `_cmd_promote` already catches `OSError` for this, on the reasoning that a
    traceback would leave the operator unaware a record was stranded. But
    `_seed_adr_from_entry` raises `ValueError` on a drifted ADR template ("ADR
    has no '## Context' section"), which fell to the generic `except
    ValueError` and reported the bare section-missing text — no hint that an
    ADR had been created, nor that its slug is now spent.

    The seeder is stubbed to raise rather than shipping a deliberately-broken
    ADR template: the behaviour under test is the WRAPPING, and the trigger it
    wraps is template drift, which by definition cannot be reproduced from the
    template this repo actually ships.
    """

    def _promote_with_failing_seeder(self):
        original = decisions._seed_adr_from_entry

        def boom(adr_path, entry):
            raise ValueError("ADR has no '## Context' section")

        decisions._seed_adr_from_entry = boom
        try:
            with self.assertRaises(ValueError) as ctx:
                decisions.promote_lightweight(
                    self.project, "Button copy", no_push=True)
            return str(ctx.exception)
        finally:
            decisions._seed_adr_from_entry = original

    def test_message_names_the_created_adr_and_the_underlying_cause(self):
        self._seed(_PROMOTABLE_SEED)
        msg = self._promote_with_failing_seeder()
        self.assertIn("adr-0001-button-copy.md", msg)
        self.assertIn("was created", msg)
        self.assertIn("'## Context'", msg)

    def test_message_warns_the_slug_is_spent(self):
        """The actionable half: a naive re-run allocates a NEW number and
        collides on the slug, so the operator has to be told to look first."""
        self._seed(_PROMOTABLE_SEED)
        msg = self._promote_with_failing_seeder()
        self.assertIn("slug is already taken", msg)

    def test_the_entry_is_left_unstubbed(self):
        """The ADR is orphaned, but the entry must still be promotable — the
        stub write is downstream of the seed and never ran."""
        self._seed(_PROMOTABLE_SEED)
        before = self._text()
        self._promote_with_failing_seeder()
        self.assertEqual(self._text(), before)
        self.assertNotIn("**Promoted:**", self._text())

    def test_no_push_omits_the_origin_claim_from_the_message(self):
        """`--no-push` reserved nothing on the trunk, so the message must not
        claim it did — the operator's cleanup is local only."""
        self._seed(_PROMOTABLE_SEED)
        msg = self._promote_with_failing_seeder()
        self.assertNotIn("origin/main", msg)


# ---- 100-04: `lint` subcommand -----------------------------------------
#
# Read-only advisory sweep over what is already on disk (ADR-0042). No
# subprocess, no seeding, no write path — every fixture below is built
# through `render_entry` itself (not hand-typed), matching the style the
# 100-03 promote fixtures already use.

# A single entry that trips the two-signal rule (LOAD_BEARING + ALTERNATIVES
# together, reusing the pinned marker halves from RoutingEvaluatorTests) —
# the AC1 "misfiled entry" fixture.
_LINT_FLAGGED_SEED = "# Lightweight Decisions\n\n## Entries\n\n" + decisions.render_entry(
    "Vendored library swap",
    _LOAD_BEARING_HALF + " " + _ALTERNATIVES_HALF,
    "Context text.", "Scope text.", date="2026-07-01")

# Same two-signal combination, but split across the Decision field's own two
# lines — pins that the scan reads a field WHOLE, not just its first line
# (100-04's stated multi-line edge case).
_LINT_MULTILINE_FIELD_SEED = (
    "# Lightweight Decisions\n\n## Entries\n\n"
    + decisions.render_entry(
        "Multi-line signal",
        "First line is unremarkable.\n" + _LOAD_BEARING_HALF,
        _ALTERNATIVES_HALF, "Scope.", date="2026-07-02"))

# Clean — no marker fires anywhere in any field.
_LINT_CLEAN_SEED = "# Lightweight Decisions\n\n## Entries\n\n" + decisions.render_entry(
    "Ordinary decision", "Use blue for the icon.", "Team preference.",
    "Icon only.", date="2026-07-03")

# `## Entries` present, zero REAL entries — just the template's own
# placeholder prose (mirrors the shipped template's empty state).
_LINT_EMPTY_ENTRIES_SEED = """# Lightweight Decisions

## Entries

_No entries yet._
"""

# An already-promoted stub (100-03 shape) whose HEADING TITLE itself would
# trip the BOUNDARY marker if it were scanned as an ordinary entry —
# demonstrates the stub is excluded structurally (its body never matches
# `_FIELD_RE`, so `_real_entries` never surfaces it), not by title-based
# special-casing.
_LINT_PROMOTED_STUB_SEED = """# Lightweight Decisions

## Entries

### 2026-07-01 — Module boundary change

**Promoted:** moved to [ADR-0012: Module Boundary Change](adr-0012-module-boundary-change.md).
"""


class LintTests(unittest.TestCase):
    """100-04 `lint` — advisory, read-only sweep (ADR-0042). The lexical
    evaluator (`evaluate_routing_signals` / `flags_adr_routing`) is defined
    elsewhere; this is the one place it is actually APPLIED."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name)
        self.target = decisions.lightweight_path(self.project)
        self.target.parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _seed(self, text):
        self.target.write_text(text, encoding="utf-8")

    def _text(self):
        return self.target.read_text(encoding="utf-8")

    def _stdout(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = decisions.main(argv)
        return rc, buf.getvalue()

    # AC1 — a misfiled entry is reported: date, title, and the matched
    # groups, via the Python API.
    def test_ac1_flagged_entry_reported_by_the_python_api(self):
        self._seed(_LINT_FLAGGED_SEED)
        report = decisions.lint_lightweight(self.project)
        self.assertEqual(len(report.findings), 1)
        finding = report.findings[0]
        self.assertEqual(finding.date, "2026-07-01")
        self.assertEqual(finding.title, "Vendored library swap")
        groups = {m.group for m in finding.matches}
        self.assertEqual(groups, {"LOAD_BEARING", "ALTERNATIVES"})

    # AC1 — the CLI names date, title, the matched groups/phrases, and the
    # promote remedy.
    def test_ac1_cli_names_date_title_matches_and_remedy(self):
        self._seed(_LINT_FLAGGED_SEED)
        rc, out = self._stdout(
            ["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 1)
        self.assertIn("2026-07-01", out)
        self.assertIn("Vendored library swap", out)
        self.assertIn("LOAD_BEARING", out)
        self.assertIn("ALTERNATIVES", out)
        # The matched PHRASES, not just the group names — the groups appear in
        # the summary line regardless, so asserting only those would still
        # pass if the evidence list were dropped, and an advisory finding the
        # reader cannot audit is one they can only trust blindly or ignore.
        self.assertIn("'vendored'", out)
        self.assertIn("'rejected'", out)
        self.assertIn(
            'decisions.py promote --title "Vendored library swap"', out)

    # AC2 — the defining constraint: nothing is ever written, including a
    # run that DOES produce findings (the case an accidental write would
    # hide).
    def test_ac2_run_with_findings_leaves_file_byte_identical(self):
        self._seed(_LINT_FLAGGED_SEED)
        before = self._text()
        self._stdout(["lint", "--project-dir", str(self.project)])
        self.assertEqual(self._text(), before)

    def test_ac2_clean_run_leaves_file_byte_identical(self):
        self._seed(_LINT_CLEAN_SEED)
        before = self._text()
        self._stdout(["lint", "--project-dir", str(self.project)])
        self.assertEqual(self._text(), before)

    # AC3 — jig's REAL shipped file, not a fixture: the illustrative worked
    # example and the `## Template` fence heading produce zero findings.
    def test_ac3_real_shipped_file_has_zero_findings(self):
        report = decisions.lint_lightweight(REPO_ROOT)
        self.assertIsNotNone(report)
        self.assertEqual(report.findings, [])

    # AC4 — exit code carries the verdict.
    def test_ac4_clean_exits_zero(self):
        self._seed(_LINT_CLEAN_SEED)
        rc = decisions.main(["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)

    def test_ac4_findings_exit_nonzero(self):
        self._seed(_LINT_FLAGGED_SEED)
        rc = decisions.main(["lint", "--project-dir", str(self.project)])
        self.assertNotEqual(rc, 0)

    def test_ac4_exit_zero_flag_reports_without_failing(self):
        self._seed(_LINT_FLAGGED_SEED)
        rc, out = self._stdout(
            ["lint", "--exit-zero", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertIn("Vendored library swap", out)

    # AC5 — a clean file says so: names the file and the entry count.
    def test_ac5_clean_line_names_file_and_scanned_count(self):
        self._seed(_LINT_CLEAN_SEED)
        rc, out = self._stdout(
            ["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertIn("docs/decisions/lightweight-decisions.md", out)
        # The count in context, not a bare "1" — a single character matches
        # almost any output, including a date or a path fragment.
        self.assertIn("1 entry scanned", out)
        self.assertIn("clean", out)

    # AC6 — a missing file reports "nothing to lint", exits 0, and does NOT
    # seed one (contrast add-lightweight, which does seed).
    def test_ac6_missing_file_reports_nothing_to_lint(self):
        rc, out = self._stdout(
            ["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertIn("nothing to lint", out)

    def test_ac6_missing_file_is_not_seeded(self):
        self._stdout(["lint", "--project-dir", str(self.project)])
        self.assertFalse(
            self.target.exists(), "lint must not seed a file (AC6)")

    def test_ac6_python_api_returns_none_for_missing_file(self):
        self.assertIsNone(decisions.lint_lightweight(self.project))

    # AC6 — a foreign-format file raises the existing `_foreign_format_error`,
    # unchanged.
    def test_ac6_foreign_format_raises_existing_error(self):
        self._seed(_FOREIGN_TABLE)
        with self.assertRaises(ValueError) as ctx:
            decisions.lint_lightweight(self.project)
        self.assertIn("## Entries", str(ctx.exception))

    def test_ac6_cli_foreign_format_exits_nonzero(self):
        self._seed(_FOREIGN_TABLE)
        rc, err = _run_cli(["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 1)
        self.assertIn("## Entries", err)

    # AC7 — `--project-dir` and `layout.docs_root` are honoured.
    def test_ac7_docs_root_dot_is_honoured(self):
        (self.project / "scaffold.json").write_text(
            '{"layout": {"docs_root": "."}}', encoding="utf-8")
        target = decisions.lightweight_path(self.project)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_LINT_CLEAN_SEED, encoding="utf-8")
        rc, out = self._stdout(
            ["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        self.assertIn("decisions/lightweight-decisions.md", out)
        self.assertNotIn("docs/decisions/lightweight-decisions.md", out)

    # Edge case — a 100-03 promotion stub produces no finding, even when its
    # heading title alone would trip a marker: it is excluded structurally
    # (never a REAL entry), not by re-checking its content.
    def test_edge_promoted_stub_produces_no_finding(self):
        self._seed(_LINT_PROMOTED_STUB_SEED)
        report = decisions.lint_lightweight(self.project)
        self.assertEqual(report.scanned, 0)
        self.assertEqual(report.findings, [])

    # Edge case — a multi-line field is scanned whole, not first-line-only.
    def test_edge_multiline_field_is_scanned_whole(self):
        self._seed(_LINT_MULTILINE_FIELD_SEED)
        report = decisions.lint_lightweight(self.project)
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0].title, "Multi-line signal")

    # Edge case — zero real entries (jig's own file, today) exits 0 with the
    # clean line.
    def test_edge_zero_real_entries_exits_clean(self):
        self._seed(_LINT_EMPTY_ENTRIES_SEED)
        rc, out = self._stdout(
            ["lint", "--project-dir", str(self.project)])
        self.assertEqual(rc, 0)
        report = decisions.lint_lightweight(self.project)
        self.assertEqual(report.scanned, 0)
        self.assertEqual(report.findings, [])

    def test_edge_jigs_own_file_has_zero_real_entries_today(self):
        report = decisions.lint_lightweight(REPO_ROOT)
        self.assertEqual(report.scanned, 0)


if __name__ == "__main__":
    unittest.main()
