"""
AC verification tests for slice 083-05 (routing rubric + decisions.py
add-lightweight) and the single-source drift guard co-owned with 083-06.

Run from the repo root:
    python3 skills/memory-sync/test_decisions.py
"""

import contextlib
import importlib.util
import io
import os
import re
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


# Fixtures for the two-signal rule (096-01 / ADR-0039). Each is checked by
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
# refuse this — see the marker table's note and ADR-0039's Option A.
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
    """The pure lexical evaluator that backs the advisory lint (096-04 /
    ADR-0039). No project dir, no filesystem, no env — text in, matches out.
    ADR-0039 confines this to the report-only lint; it must not gate a write,
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


# ---- 096-02: `update` subcommand --------------------------------------

# A plain, addressable, single-entry fixture — no illustrative marker, so
# every entry in it is REAL per the 096-02 "real entry" notion. The default
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
    """096-02 `update_lightweight` — the Python API `_cmd_update` calls."""

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
    # not corrupt the file's structure.
    def test_decision_with_heading_like_text_does_not_corrupt_structure(self):
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
    (ADR-0039). `update` carries no `--confirm-lightweight` and refuses only
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


if __name__ == "__main__":
    unittest.main()
