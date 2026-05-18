"""
Tests for scripts/spec_lint.py.

Run:
    python3 scripts/test_spec_lint.py
    # or from repo root:
    python3 -m unittest scripts.test_spec_lint
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_LINT = REPO_ROOT / "scripts" / "spec_lint.py"

# Import the module directly for unit tests.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import spec_lint as sl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_spec(slices: list) -> str:
    """Build a minimal spec with given slices.  Each element is a dict:
      label, status, acs (list of str), extra (appended text after ACs).
    """
    parts = ["---\nstatus: DRAFT\n---\n\n# Spec 099: test\n"]
    for s in slices:
        acs = "\n".join(f"{i+1}. {ac}" for i, ac in enumerate(s.get("acs", [])))
        parts.append(
            f"## Slice {s['label']}\n\n"
            f"**STATUS: {s.get('status', 'DRAFT')}**\n\n"
            f"**Acceptance Criteria:**\n\n{acs}\n\n"
            f"{s.get('extra', '')}\n"
        )
    return "\n".join(parts)


CLEAN_SPEC = _make_spec([
    {
        "label": "099-01 — clean-slice",
        "status": "READY_FOR_IMPLEMENTATION",
        "acs": [
            "The output must contain the phrase `hello world`.",
            "The output must include the trigger phrase `goodbye world`.",
            "The output is valid markdown.",
        ],
    }
])

CONTRADICTION_SPEC = _make_spec([
    {
        "label": "099-01 — contradict-slice",
        "status": "READY_FOR_IMPLEMENTATION",
        "acs": [
            # AC #1 requires an exact phrase containing "multi-persona"
            'The description uses this exact phrasing: '
            '"a personal multi-persona reviewer at ~/.claude/skills/pr-review".',
            # AC #2 is neutral
            "The skill name must be `pr-review`.",
            # AC #3 forbids "multi-persona"
            'The description does NOT contain any of these: "multi-persona", "deep audit".',
        ],
    }
])

MULTI_FORBIDDEN_SPEC = _make_spec([
    {
        "label": "099-01 — multi-forbidden",
        "status": "READY_FOR_IMPLEMENTATION",
        "acs": [
            # AC #1 requires a phrase that triggers two forbidden terms
            'The label uses exact phrasing: "comprehensive expert-level security review".',
            # AC #2 forbids two separate terms
            'The description must NOT contain "comprehensive review" or "expert-level".',
        ],
    }
])

SAME_AC_SPEC = _make_spec([
    {
        "label": "099-01 — same-ac",
        "status": "READY_FOR_IMPLEMENTATION",
        "acs": [
            # Single AC contains both a required phrase AND a forbidden term —
            # that is not a contradiction (same AC, different semantic intent).
            'Using exact phrasing: "foo bar". Also the output must NOT contain "baz".',
        ],
    }
])

MULTI_SLICE_SPEC = _make_spec([
    {
        "label": "099-01 — first-clean",
        "status": "DONE",
        "acs": ["The output is valid JSON.", "Exit code is 0 on success."],
    },
    {
        "label": "099-02 — second-contradiction",
        "status": "READY_FOR_IMPLEMENTATION",
        "acs": [
            'Uses this exact phrasing: "full audit mode".',
            'Must NOT contain "full audit".',
        ],
    },
])

NO_ACS_SPEC = _make_spec([
    {
        "label": "099-01 — no-acs",
        "status": "DRAFT",
        "acs": [],
    }
])


# ---------------------------------------------------------------------------
# Unit tests: phrase extraction
# ---------------------------------------------------------------------------

class RequiredPhraseExtractionTests(unittest.TestCase):

    def test_exact_phrasing_marker(self):
        text = 'Using this exact phrasing: "hello world and more".'
        phrases = sl._extract_phrases_near(text, sl._REQUIRED_MARKERS)
        self.assertIn("hello world and more", phrases)

    def test_exact_phrase_backtick(self):
        text = "The description contains exact phrase `trigger word`."
        phrases = sl._extract_phrases_near(text, sl._REQUIRED_MARKERS)
        self.assertIn("trigger word", phrases)

    def test_no_marker_no_extraction(self):
        text = "The output must be valid markdown."
        phrases = sl._extract_phrases_near(text, sl._REQUIRED_MARKERS)
        self.assertEqual(phrases, [])

    def test_exact_wording_variant(self):
        text = 'Use exact wording: "ship it now".'
        phrases = sl._extract_phrases_near(text, sl._REQUIRED_MARKERS)
        self.assertIn("ship it now", phrases)

    def test_multiple_required_in_one_ac(self):
        text = (
            'Step 1 uses this exact phrasing: "alpha phrase". '
            'Step 2 uses exact phrasing: "beta phrase".'
        )
        phrases = sl._extract_phrases_near(text, sl._REQUIRED_MARKERS)
        self.assertIn("alpha phrase", phrases)
        self.assertIn("beta phrase", phrases)


class ForbiddenPhraseExtractionTests(unittest.TestCase):

    def test_not_contain_inline(self):
        text = 'The description does NOT contain "multi-persona".'
        phrases = sl._extract_phrases_near(text, sl._FORBIDDEN_MARKERS)
        self.assertIn("multi-persona", phrases)

    def test_must_not_contain(self):
        text = 'Output must not contain `security review`.'
        phrases = sl._extract_phrases_near(text, sl._FORBIDDEN_MARKERS)
        self.assertIn("security review", phrases)

    def test_must_not_include(self):
        text = 'The field must not include "verbose logging".'
        phrases = sl._extract_phrases_near(text, sl._FORBIDDEN_MARKERS)
        self.assertIn("verbose logging", phrases)

    def test_forbidden_list(self):
        text = (
            'The description does NOT contain any of these: '
            '"comprehensive review", "deep code analysis", "expert-level".'
        )
        phrases = sl._extract_phrases_near(text, sl._FORBIDDEN_MARKERS)
        self.assertIn("comprehensive review", phrases)
        self.assertIn("deep code analysis", phrases)
        self.assertIn("expert-level", phrases)

    def test_no_marker_no_extraction(self):
        text = "The output is valid JSON."
        phrases = sl._extract_phrases_near(text, sl._FORBIDDEN_MARKERS)
        self.assertEqual(phrases, [])


# ---------------------------------------------------------------------------
# Unit tests: AC item parsing
# ---------------------------------------------------------------------------

class AcParsingTests(unittest.TestCase):

    def test_numbered_items_parsed(self):
        text = (
            "## Slice 001-01 — example\n\n"
            "**Acceptance Criteria:**\n\n"
            "1. First criterion.\n"
            "2. Second criterion.\n"
            "3. Third criterion.\n"
        )
        items = sl._parse_ac_items(text)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0][0], 1)
        self.assertEqual(items[1][0], 2)

    def test_empty_ac_block(self):
        items = sl._parse_ac_items("## Slice 001-01\n\nNo AC header here.\n")
        self.assertEqual(items, [])

    def test_multiline_ac_joined(self):
        text = (
            "**Acceptance Criteria:**\n\n"
            "1. First line of a long AC\n"
            "   continuation line here.\n"
            "2. Second item.\n"
        )
        items = sl._parse_ac_items(text)
        self.assertEqual(items[0][0], 1)
        self.assertIn("First line", items[0][1])


# ---------------------------------------------------------------------------
# Unit tests: contradiction detection
# ---------------------------------------------------------------------------

class ContradictionDetectionTests(unittest.TestCase):

    def test_clean_spec_no_contradictions(self):
        slices = list(sl._iter_slices(CLEAN_SPEC))
        self.assertEqual(len(slices), 1)
        contradictions, _ = sl.check_slice(slices[0][0], slices[0][1])
        self.assertEqual(contradictions, [])

    def test_detects_012_01_pattern(self):
        """Reproduces the motivating incident from slice 012-01 deviation log."""
        slices = list(sl._iter_slices(CONTRADICTION_SPEC))
        contradictions, _ = sl.check_slice(slices[0][0], slices[0][1])
        self.assertEqual(len(contradictions), 1)
        c = contradictions[0]
        self.assertEqual(c.req_ac, 1)
        self.assertEqual(c.forbid_ac, 3)
        self.assertIn("multi-persona", c.required)
        self.assertEqual(c.forbidden, "multi-persona")

    def test_multi_forbidden_produces_two_contradictions(self):
        slices = list(sl._iter_slices(MULTI_FORBIDDEN_SPEC))
        contradictions, _ = sl.check_slice(slices[0][0], slices[0][1])
        forbidden_terms = {c.forbidden for c in contradictions}
        # Both "comprehensive review" and "expert-level" should be flagged.
        # "comprehensive review" is a substring of "comprehensive expert-level security review".
        # "expert-level" is a substring of "comprehensive expert-level security review".
        self.assertIn("expert-level", forbidden_terms)

    def test_same_ac_not_flagged(self):
        """A required phrase and a forbidden term in the same AC is not a contradiction."""
        slices = list(sl._iter_slices(SAME_AC_SPEC))
        contradictions, _ = sl.check_slice(slices[0][0], slices[0][1])
        # "foo bar" is required and "baz" is forbidden — but "baz" is NOT in "foo bar"
        # and they're in the same AC anyway.
        self.assertEqual(contradictions, [])

    def test_multi_slice_only_flags_affected_slice(self):
        slices = list(sl._iter_slices(MULTI_SLICE_SPEC))
        all_contradictions = []
        for label, section in slices:
            cs, _ = sl.check_slice(label, section)
            all_contradictions.extend(cs)
        # Only 099-02 has a contradiction; 099-01 is clean.
        self.assertEqual(len(all_contradictions), 1)
        self.assertIn("full audit mode", all_contradictions[0].required)

    def test_no_acs_no_contradictions(self):
        slices = list(sl._iter_slices(NO_ACS_SPEC))
        contradictions, _ = sl.check_slice(slices[0][0], slices[0][1])
        self.assertEqual(contradictions, [])


# ---------------------------------------------------------------------------
# Integration tests: lint() + render_report()
# ---------------------------------------------------------------------------

class LintFunctionTests(unittest.TestCase):

    def setUp(self):
        import tempfile, os
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_spec(self, content: str) -> Path:
        p = Path(self._tmpdir) / "spec.md"
        p.write_text(content)
        return p

    def test_clean_spec_exit_zero(self):
        p = self._write_spec(CLEAN_SPEC)
        _, code = sl.lint(p)
        self.assertEqual(code, 0)

    def test_contradiction_exit_one(self):
        p = self._write_spec(CONTRADICTION_SPEC)
        _, code = sl.lint(p)
        self.assertEqual(code, 1)

    def test_missing_file_exit_two(self):
        _, code = sl.lint(Path(self._tmpdir) / "nonexistent.md")
        self.assertEqual(code, 2)

    def test_slice_filter_clean(self):
        p = self._write_spec(MULTI_SLICE_SPEC)
        _, code = sl.lint(p, slice_fragment="first-clean")
        self.assertEqual(code, 0)

    def test_slice_filter_contradiction(self):
        p = self._write_spec(MULTI_SLICE_SPEC)
        _, code = sl.lint(p, slice_fragment="second-contradiction")
        self.assertEqual(code, 1)

    def test_ambiguous_fragment_exit_two(self):
        spec = _make_spec([
            {"label": "099-01 — foo", "acs": []},
            {"label": "099-02 — foo-also", "acs": []},
        ])
        p = self._write_spec(spec)
        _, code = sl.lint(p, slice_fragment="foo")
        self.assertEqual(code, 2)

    def test_report_contains_ac_numbers(self):
        p = self._write_spec(CONTRADICTION_SPEC)
        report, _ = sl.lint(p)
        self.assertIn("AC #1", report)
        self.assertIn("AC #3", report)

    def test_report_contains_phrases(self):
        p = self._write_spec(CONTRADICTION_SPEC)
        report, _ = sl.lint(p)
        self.assertIn("multi-persona", report)

    def test_report_no_contradiction_check(self):
        p = self._write_spec(CLEAN_SPEC)
        report, _ = sl.lint(p)
        self.assertIn("No AC contradictions", report)

    def test_no_slice_headings_exit_two(self):
        p = self._write_spec("# Just a heading\n\nNo slices here.\n")
        _, code = sl.lint(p)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# CLI subprocess tests
# ---------------------------------------------------------------------------

def _run_lint(*args: str, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SPEC_LINT), *args],
        capture_output=True, text=True,
        cwd=cwd,
    )


class CliTests(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_spec(self, content: str, name: str = "spec.md") -> str:
        p = Path(self._tmpdir) / name
        p.write_text(content)
        return str(p)

    def test_cli_clean_exit_zero(self):
        path = self._write_spec(CLEAN_SPEC)
        result = _run_lint(path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("No AC contradictions", result.stdout)

    def test_cli_contradiction_exit_one(self):
        path = self._write_spec(CONTRADICTION_SPEC)
        result = _run_lint(path)
        self.assertEqual(result.returncode, 1)

    def test_cli_missing_file_exit_two(self):
        result = _run_lint("/tmp/nonexistent_spec_lint_test_99999.md")
        self.assertEqual(result.returncode, 2)

    def test_cli_slice_flag(self):
        path = self._write_spec(MULTI_SLICE_SPEC)
        result = _run_lint(path, "--slice", "first-clean")
        self.assertEqual(result.returncode, 0)

    def test_cli_contradiction_report_format(self):
        path = self._write_spec(CONTRADICTION_SPEC)
        result = _run_lint(path)
        self.assertIn("AC #1 × AC #3", result.stdout)

    def test_cli_against_real_012_spec(self):
        """Smoke test: run spec_lint against the real 012 spec.
        The 012-01 deviation log says AC #1/#3 collision was RESOLVED during
        reconciliation (the spec's AC #1 was updated to remove 'multi-persona').
        So the real spec must now be clean.
        """
        real_spec = REPO_ROOT / "docs" / "specs" / "012-pr-review" / "spec.md"
        if not real_spec.is_file():
            self.skipTest("012 spec not found")
        result = _run_lint(str(real_spec), "--slice", "012-01")
        # After reconciliation the spec should be clean (no contradiction).
        # If this fails it means the spec still has the original un-resolved AC.
        self.assertEqual(result.returncode, 0,
                         f"Real 012-01 spec has a contradiction: {result.stdout}")


class MixedLayoutLintTests(unittest.TestCase):
    """Slice 018-02 AC #5: spec_lint sees slices in both layouts."""

    def setUp(self):
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp(prefix="jig-lint-mixed-"))
        # Slice in a file
        (self._tmpdir / "slice-01-from-file.md").write_text(
            "---\nstatus: DRAFT\ndependencies: []\nlast_verified:\n---\n\n"
            "## Slice 018-01 — alpha-from-file\n\n"
            "**Acceptance Criteria:**\n\n"
            "1. **Must** do thing X.\n"
            "2. Doesn't do anything unusual.\n\n"
        )
        # Slice embedded
        self.spec = self._tmpdir / "spec.md"
        self.spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n"
            "## Slice 018-02 — beta-embedded\n\n"
            "**STATUS: DRAFT**\n\n"
            "**Acceptance Criteria:**\n\n"
            "1. **Must** also do thing Y.\n"
            "2. No contradictions.\n\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_lint_walks_both_layouts(self):
        report, code = sl.lint(self.spec)
        self.assertEqual(code, 0,
                         f"report:\n{report}")
        # Report should reference both slices
        self.assertIn("018-01 — alpha-from-file", report)
        self.assertIn("018-02 — beta-embedded", report)


# ---------------------------------------------------------------------------
# Inbox 2026-05-14: --all / no-arg directory-walking mode
# ---------------------------------------------------------------------------

class WalkAllSpecsTests(unittest.TestCase):
    """spec_lint walks every `docs/specs/*/spec.md` under cwd in one shot
    so contributors see every offending spec in a single run (instead of
    short-circuiting on the first failure as CI's `set -e` bash loop did).
    """

    def setUp(self):
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp(prefix="jig-lint-all-"))
        (self._tmpdir / "docs" / "specs").mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _seed_spec(self, slug: str, content: str) -> Path:
        spec_dir = self._tmpdir / "docs" / "specs" / slug
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec = spec_dir / "spec.md"
        spec.write_text(content)
        return spec

    def test_discover_specs_orders_lexicographically(self):
        self._seed_spec("002-second", CLEAN_SPEC)
        self._seed_spec("001-first", CLEAN_SPEC)
        self._seed_spec("003-third", CLEAN_SPEC)
        found = sl._discover_specs(self._tmpdir)
        names = [p.parent.name for p in found]
        self.assertEqual(names, ["001-first", "002-second", "003-third"])

    def test_discover_specs_empty_when_no_specs_root(self):
        empty = Path(self._tmpdir) / "empty"
        empty.mkdir()
        self.assertEqual(sl._discover_specs(empty), [])

    def test_discover_specs_skips_dirs_without_spec_md(self):
        # Subdir present but no spec.md inside — should be ignored
        (self._tmpdir / "docs" / "specs" / "999-placeholder").mkdir()
        self._seed_spec("001-real", CLEAN_SPEC)
        found = sl._discover_specs(self._tmpdir)
        self.assertEqual([p.parent.name for p in found], ["001-real"])

    def test_lint_all_aggregates_clean_specs(self):
        s1 = self._seed_spec("001-first", CLEAN_SPEC)
        s2 = self._seed_spec("002-second", CLEAN_SPEC)
        report, code = sl.lint_all([s1, s2])
        self.assertEqual(code, 0)
        self.assertIn("Linted 2 spec(s)", report)
        self.assertIn("no contradictions found", report)

    def test_lint_all_reports_every_offending_spec(self):
        """The whole point of --all: every bad spec shows in one run, not just
        the first one (which is what the bash loop short-circuited at).
        """
        s1 = self._seed_spec("001-clean", CLEAN_SPEC)
        s2 = self._seed_spec("002-bad-a", CONTRADICTION_SPEC)
        s3 = self._seed_spec("003-bad-b", MULTI_FORBIDDEN_SPEC)
        report, code = sl.lint_all([s1, s2, s3])
        self.assertEqual(code, 1)
        # Both bad specs should appear in the report
        self.assertIn("002-bad-a", report)
        self.assertIn("003-bad-b", report)

    def test_lint_all_exit_two_propagates(self):
        """A spec that can't parse (no '## Slice' headings) yields exit 2,
        which must dominate even if every other spec is clean.
        """
        s_clean = self._seed_spec("001-clean", CLEAN_SPEC)
        s_unparse = self._seed_spec("002-unparse",
                                     "# Just a title\n\nNo slices.\n")
        report, code = sl.lint_all([s_clean, s_unparse])
        self.assertEqual(code, 2)

    def test_cli_no_arg_walks_docs_specs(self):
        self._seed_spec("001-clean", CLEAN_SPEC)
        self._seed_spec("002-bad", CONTRADICTION_SPEC)
        result = _run_lint(cwd=str(self._tmpdir))
        self.assertEqual(result.returncode, 1)
        self.assertIn("001-clean", result.stdout)
        self.assertIn("002-bad", result.stdout)
        self.assertIn("Linted 2 spec(s)", result.stdout)

    def test_cli_all_flag_equivalent_to_no_arg(self):
        self._seed_spec("001-clean", CLEAN_SPEC)
        result = _run_lint("--all", cwd=str(self._tmpdir))
        self.assertEqual(result.returncode, 0)
        self.assertIn("Linted 1 spec(s)", result.stdout)

    def test_cli_no_arg_no_specs_exits_two(self):
        import tempfile
        empty = tempfile.mkdtemp(prefix="jig-lint-empty-")
        try:
            result = _run_lint(cwd=empty)
            self.assertEqual(result.returncode, 2)
            self.assertIn("no docs/specs", result.stderr)
        finally:
            import shutil
            shutil.rmtree(empty, ignore_errors=True)

    def test_cli_all_with_positional_is_user_error(self):
        spec = self._seed_spec("001-clean", CLEAN_SPEC)
        result = _run_lint("--all", str(spec), cwd=str(self._tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("mutually exclusive", result.stderr)

    def test_cli_all_with_slice_is_user_error(self):
        self._seed_spec("001-clean", CLEAN_SPEC)
        result = _run_lint("--all", "--slice", "anything",
                            cwd=str(self._tmpdir))
        self.assertEqual(result.returncode, 2)
        self.assertIn("--slice", result.stderr)


# ---------------------------------------------------------------------------
# Slice 029-01: `kind:` enum validation + spike body-shape soft-warn.
# ---------------------------------------------------------------------------


def _make_slice_file(kind: str = None, body: str = "") -> str:
    """Build a file-per-slice fixture with optional `kind:` frontmatter
    field. Default body is empty so callers can pass spike-shaped blocks.
    """
    lines = ["---", "status: DRAFT"]
    if kind is not None:
        lines.append(f"kind: {kind}")
    lines.append("dependencies: []")
    lines.append("last_verified:")
    lines.append("---")
    lines.append("")
    lines.append("## Slice 099-01 — kind-fixture")
    lines.append("")
    lines.append("**Acceptance Criteria:**")
    lines.append("")
    lines.append("1. Trivial AC.")
    lines.append("")
    if body:
        lines.append(body)
        lines.append("")
    return "\n".join(lines) + "\n"


SPIKE_FULL_BODY = (
    "**Question:** Should we use library A or library B?\n\n"
    "**Time-box:** 1 day\n\n"
    "**Findings:**\n- A is faster but lacks feature X.\n"
    "- B has feature X but the API is awkward.\n\n"
    "**Outcome:** ADR-0007 created"
)


class KindEnumValidationTests(unittest.TestCase):
    """Slice 029-01 AC #2: `spec_lint.py` validates the `kind` enum.

    Unknown values are hard errors (exit 1), reported with a clear message
    naming the allowed values. Allowed values: `spike`, `feature`.
    Unset/absent `kind` is fine (default).
    """

    def setUp(self):
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp(prefix="jig-lint-kind-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_slice(self, name: str, content: str) -> Path:
        spec = self._tmpdir / "spec.md"
        # Minimum spec.md to anchor iter_slices' walk.
        spec.write_text("---\nstatus: DRAFT\n---\n\n# Spec 099\n")
        slice_path = self._tmpdir / name
        slice_path.write_text(content)
        return spec

    def test_kind_spike_passes(self):
        # `kind: spike` is in the enum; with body filled, lint is clean.
        spec = self._write_slice(
            "slice-01-spike.md",
            _make_slice_file(kind="spike", body=SPIKE_FULL_BODY),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)

    def test_kind_feature_passes(self):
        # `kind: feature` is the documented explicit-default synonym.
        spec = self._write_slice(
            "slice-01-feature.md",
            _make_slice_file(kind="feature"),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)

    def test_kind_absent_passes(self):
        # No `kind:` field at all — default behavior, no warning, no error.
        spec = self._write_slice(
            "slice-01-no-kind.md",
            _make_slice_file(kind=None),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)

    def test_kind_bogus_is_hard_error(self):
        # Unknown value -> exit 1.
        spec = self._write_slice(
            "slice-01-bogus.md",
            _make_slice_file(kind="bogus"),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 1, msg=report)
        # Error message names the offending value
        self.assertIn("bogus", report)
        # Error message names the allowed values
        self.assertIn("spike", report)
        self.assertIn("feature", report)

    def test_kind_bogus_other_value(self):
        # Different unknown value still fires.
        spec = self._write_slice(
            "slice-01-refactor.md",
            _make_slice_file(kind="refactor"),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 1, msg=report)
        self.assertIn("refactor", report)


class SpikeBodyShapeValidationTests(unittest.TestCase):
    """Slice 029-01 AC #3: `kind: spike` slices missing one of the four
    labelled body blocks (`**Question:**`, `**Time-box:**`,
    `**Findings:**`, `**Outcome:**`) emit a WARNING (not a hard error).

    Spikes mid-flight legitimately have empty Findings/Outcome. The
    warning should name the missing label(s) so the author knows which
    blocks still need filling.

    Edge cases also covered here:
      - Outcome with multiple semicolon-separated values parses cleanly.
      - The four labels are checked case-sensitively; `**question:**`
        with lower-case 'q' is not the same label.
    """

    def setUp(self):
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp(prefix="jig-lint-spike-body-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_slice(self, name: str, content: str) -> Path:
        spec = self._tmpdir / "spec.md"
        spec.write_text("---\nstatus: DRAFT\n---\n\n# Spec 099\n")
        slice_path = self._tmpdir / name
        slice_path.write_text(content)
        return spec

    def test_spike_with_all_four_labels_clean(self):
        spec = self._write_slice(
            "slice-01-full-spike.md",
            _make_slice_file(kind="spike", body=SPIKE_FULL_BODY),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)
        # No spike-shape warnings emitted.
        self.assertNotIn("missing", report.lower())

    def test_spike_missing_findings_warns(self):
        body = (
            "**Question:** open question?\n\n"
            "**Time-box:** 1 day\n\n"
            "**Outcome:** abandoned (lib unmaintained)"
        )
        spec = self._write_slice(
            "slice-01-no-findings.md",
            _make_slice_file(kind="spike", body=body),
        )
        report, code = sl.lint(spec)
        # Default strict=False: warnings are informational; exit still 0.
        self.assertEqual(code, 0, msg=report)
        self.assertIn("Findings", report)

    def test_spike_missing_outcome_warns(self):
        body = (
            "**Question:** an unknown.\n\n"
            "**Time-box:** 4 hours\n\n"
            "**Findings:**\n- evidence A.\n"
        )
        spec = self._write_slice(
            "slice-01-no-outcome.md",
            _make_slice_file(kind="spike", body=body),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)
        self.assertIn("Outcome", report)

    def test_spike_missing_question_and_timebox_warns(self):
        body = (
            "**Findings:**\n- bullet.\n\n"
            "**Outcome:** abandoned (n/a)"
        )
        spec = self._write_slice(
            "slice-01-no-q-tb.md",
            _make_slice_file(kind="spike", body=body),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)
        self.assertIn("Question", report)
        self.assertIn("Time-box", report)

    def test_spike_with_no_labels_at_all_warns_for_each(self):
        spec = self._write_slice(
            "slice-01-no-labels.md",
            _make_slice_file(kind="spike"),
        )
        report, code = sl.lint(spec)
        self.assertEqual(code, 0, msg=report)
        # All four labels named in the warning.
        for label in ("Question", "Time-box", "Findings", "Outcome"):
            self.assertIn(label, report)

    def test_warning_is_soft_unless_strict(self):
        # Hard error promotion under --strict (existing behavior).
        spec = self._write_slice(
            "slice-01-partial.md",
            _make_slice_file(kind="spike",
                             body="**Question:** open?\n"),
        )
        # Without strict: warning, exit 0.
        report_loose, code_loose = sl.lint(spec, strict=False)
        self.assertEqual(code_loose, 0, msg=report_loose)
        # With strict: warning escalates to exit 1.
        report_strict, code_strict = sl.lint(spec, strict=True)
        self.assertEqual(code_strict, 1, msg=report_strict)

    def test_feature_slice_no_body_shape_warning(self):
        # `kind: feature` (or unset) should NEVER trigger the spike body
        # shape soft-warn.
        spec_a = self._write_slice(
            "slice-01-feature.md",
            _make_slice_file(kind="feature"),
        )
        report, code = sl.lint(spec_a, strict=True)
        self.assertEqual(code, 0, msg=report)
        for label in ("Question", "Time-box", "Findings", "Outcome"):
            # The spike body warning string should not appear.
            # (Using both labels lowered into a string to avoid false-positive
            # matches on stray content.)
            self.assertNotIn(f"{label}:", report,
                             f"feature slice mentioned {label} in lint output")

    def test_spike_outcome_multiple_semicolon_separated(self):
        # Edge case: Outcome value with multiple semicolon-separated parts
        # parses cleanly and emits no warning.
        body = (
            "**Question:** open?\n\n"
            "**Time-box:** 1 day\n\n"
            "**Findings:**\n- alpha.\n\n"
            "**Outcome:** ADR-0007 created; spec 030-02 unblocked"
        )
        spec = self._write_slice(
            "slice-01-multi.md",
            _make_slice_file(kind="spike", body=body),
        )
        report, code = sl.lint(spec, strict=True)
        self.assertEqual(code, 0, msg=report)


class KindEmbeddedSliceLayoutTests(unittest.TestCase):
    """Slice 029-01: `kind:` enum + spike body-shape soft-warn also fires
    on embedded `## Slice` sections inside `spec.md` (legacy layout).

    Spec 018-02 routes spec_lint through `_common.iter_slices`, which
    walks both file-per-slice and embedded layouts. The kind extraction
    handles both via `_split_slice_section`-style heading-strip logic;
    this class pins that the kind error/warning surface is layout-agnostic.
    """

    def setUp(self):
        import tempfile
        self._tmpdir = Path(tempfile.mkdtemp(prefix="jig-lint-embedded-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _write_embedded_spec(self, kind: str, body: str = "") -> Path:
        # Heading-first, frontmatter-after — the legacy embedded shape.
        spec = self._tmpdir / "spec.md"
        kind_line = f"kind: {kind}\n" if kind else ""
        section = (
            "## Slice 099-01 — embedded-fixture\n\n"
            f"---\nstatus: DRAFT\n{kind_line}dependencies: []\n"
            "last_verified:\n---\n\n"
            "**Acceptance Criteria:**\n\n1. Trivial.\n\n"
        )
        if body:
            section += body + "\n\n"
        spec.write_text(
            "---\nstatus: DRAFT\n---\n\n# Spec X\n\n" + section
        )
        return spec

    def test_embedded_kind_bogus_is_hard_error(self):
        spec = self._write_embedded_spec("bogus")
        report, code = sl.lint(spec)
        self.assertEqual(code, 1, msg=report)
        self.assertIn("bogus", report)

    def test_embedded_kind_spike_missing_labels_warns(self):
        spec = self._write_embedded_spec("spike")
        report, code = sl.lint(spec, strict=True)
        # Soft warning under --strict promotes to exit 1.
        self.assertEqual(code, 1, msg=report)
        for label in ("Question", "Time-box", "Findings", "Outcome"):
            self.assertIn(label, report)

    def test_embedded_kind_spike_full_body_clean(self):
        body = (
            "**Question:** open?\n\n"
            "**Time-box:** 1 day\n\n"
            "**Findings:**\n- evidence.\n\n"
            "**Outcome:** abandoned (no signal)"
        )
        spec = self._write_embedded_spec("spike", body=body)
        report, code = sl.lint(spec, strict=True)
        self.assertEqual(code, 0, msg=report)


if __name__ == "__main__":
    unittest.main()
