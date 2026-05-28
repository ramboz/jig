"""
Tests for slice 036-02 (closed-spec drift sweep + reconciliation hook).

For each of the four sweep-target artifacts (drifts #1–#4 in spec 036's
Current state table), assert that:

- a level-2 `## Amendments` section exists
- at least one dated entry of the shape `### YYYY-MM-DD — <summary>` is present
- the entry body asserts the *corrected* claim (per AC slice DoD #2 — for
  prose-only edits, coverage means assert the corrected text, not the
  previous claim)

Also asserts:

- `README.md` does NOT carry a `## Amendments` section (drift #5 is
  deferred to spec 038 per AC #5 of the slice).
- `skills/spec-workflow/SKILL.md` carries a reconciliation-checklist
  gate naming "closed-spec drift" and linking to ADR-0008
  (`adr-0008-closed-spec-drift-policy`), and that gate sits between
  `## Reconciliation checklist` and the `**Commit**` gate (AC #6).
- Form consistency across the four amended artifacts (AC #7): all use
  the same `## Amendments` heading + at least one ISO-dated entry of
  the form `^### \\d{4}-\\d{2}-\\d{2} — ` (em dash).

Run:
    python3 scripts/test_closed_spec_drift_sweep.py
    # or from repo root:
    python3 -m unittest scripts.test_closed_spec_drift_sweep
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SPEC_016 = REPO_ROOT / "docs" / "specs" / "016-scaffold-mode" / "spec.md"
PR_REVIEW = REPO_ROOT / "skills" / "pr-review" / "SKILL.md"
MEMORY_SYNC = REPO_ROOT / "skills" / "memory-sync" / "SKILL.md"
WORKFLOW_MD = REPO_ROOT / "docs" / "workflow.md"
README = REPO_ROOT / "README.md"
SPEC_WORKFLOW_SKILL = REPO_ROOT / "skills" / "spec-workflow" / "SKILL.md"

# AC #7: every amendment date entry must match this regex (em dash).
DATE_HEADING_RE = re.compile(r"^### \d{4}-\d{2}-\d{2} — ", re.MULTILINE)
AMENDMENTS_HEADING_RE = re.compile(r"^## Amendments\s*$", re.MULTILINE)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _amendments_body(text: str) -> str:
    """Return the text after the `## Amendments` heading, or '' if missing."""
    m = AMENDMENTS_HEADING_RE.search(text)
    if not m:
        return ""
    return text[m.end():]


class DriftOneSpec016(unittest.TestCase):
    """AC #1 — spec 016 'five hooks' → seven hooks reality."""

    def setUp(self) -> None:
        self.text = _read(SPEC_016)
        self.body = _amendments_body(self.text)

    def test_has_amendments_section(self) -> None:
        self.assertRegex(self.text, AMENDMENTS_HEADING_RE,
                         "spec 016 must have a '## Amendments' section")

    def test_has_dated_entry(self) -> None:
        self.assertRegex(self.body, DATE_HEADING_RE,
                         "spec 016 amendments must include an ISO-dated entry")
        self.assertIn("2026-05-27", self.body)

    def test_body_asserts_seven_hooks(self) -> None:
        # Coverage = the corrected claim.
        # Body should mention "seven" hooks (or the explicit "five → seven"
        # transition).
        self.assertTrue(
            "seven" in self.body.lower() or "five → seven" in self.body,
            "spec 016 amendment must state corrected hook count (seven / five → seven)",
        )


class DriftTwoPrReview(unittest.TestCase):
    """AC #2 — pr-review SKILL.md claim that arch-review doesn't ship."""

    def setUp(self) -> None:
        self.text = _read(PR_REVIEW)
        self.body = _amendments_body(self.text)

    def test_has_amendments_section(self) -> None:
        self.assertRegex(self.text, AMENDMENTS_HEADING_RE,
                         "pr-review SKILL.md must have '## Amendments' section")

    def test_has_dated_entry(self) -> None:
        self.assertRegex(self.body, DATE_HEADING_RE)
        self.assertIn("2026-05-27", self.body)

    def test_body_mentions_arch_review_shipped(self) -> None:
        # Coverage: corrected claim — arch-review shipped (spec 014).
        lower = self.body.lower()
        self.assertIn("arch-review", lower)
        self.assertTrue(
            "014" in self.body or "ship" in lower,
            "amendment must record that arch-review shipped (spec 014)",
        )


class DriftThreeMemorySync(unittest.TestCase):
    """AC #3 — memory-sync SKILL.md claim that 002-03/04 are pending."""

    def setUp(self) -> None:
        self.text = _read(MEMORY_SYNC)
        self.body = _amendments_body(self.text)

    def test_has_amendments_section(self) -> None:
        self.assertRegex(self.text, AMENDMENTS_HEADING_RE)

    def test_has_dated_entry(self) -> None:
        self.assertRegex(self.body, DATE_HEADING_RE)
        self.assertIn("2026-05-27", self.body)

    def test_body_asserts_slices_done(self) -> None:
        # Coverage: corrected claim — both slices are DONE.
        self.assertIn("002-03", self.body)
        self.assertIn("002-04", self.body)
        self.assertIn("DONE", self.body)


class DriftFourWorkflow(unittest.TestCase):
    """AC #4 — workflow.md claim about disable-model-invocation stubs."""

    def setUp(self) -> None:
        self.text = _read(WORKFLOW_MD)
        self.body = _amendments_body(self.text)

    def test_has_amendments_section(self) -> None:
        self.assertRegex(self.text, AMENDMENTS_HEADING_RE)

    def test_has_dated_entry(self) -> None:
        self.assertRegex(self.body, DATE_HEADING_RE)
        self.assertIn("2026-05-27", self.body)

    def test_body_asserts_skills_auto_trigger(self) -> None:
        # Coverage: corrected claim — none of the three carry the flag,
        # all auto-trigger.
        lower = self.body.lower()
        self.assertIn("spec-workflow", lower)
        self.assertIn("independent-review", lower)
        self.assertIn("contracts", lower)
        self.assertTrue(
            "auto-trigger" in lower or "user-invocable" in lower
            or "no longer" in lower or "do not carry" in lower,
            "amendment must record that the three skills now auto-trigger / "
            "do not carry disable-model-invocation",
        )


class DriftFiveExcluded(unittest.TestCase):
    """AC #5 — README.md is explicitly NOT touched in this sweep."""

    def test_readme_has_no_amendments_section(self) -> None:
        text = _read(README)
        self.assertNotRegex(
            text,
            AMENDMENTS_HEADING_RE,
            "README.md must NOT carry a '## Amendments' section — drift #5 "
            "is deferred to spec 038's tier-reconciliation sweep.",
        )


class ReconciliationChecklistGate(unittest.TestCase):
    """AC #6 — closed-spec-drift gate wired into reconciliation checklist."""

    def setUp(self) -> None:
        self.text = _read(SPEC_WORKFLOW_SKILL)

    def test_checklist_section_exists(self) -> None:
        self.assertIn("## Reconciliation checklist", self.text)

    def test_gate_names_closed_spec_drift(self) -> None:
        # The gate must name "closed-spec drift" (or equivalent trigger).
        lower = self.text.lower()
        self.assertIn("closed-spec drift", lower,
                      "Reconciliation checklist must name the 'closed-spec drift' gate")

    def test_gate_links_adr_0008(self) -> None:
        # The gate must link to ADR-0008.
        self.assertIn("adr-0008-closed-spec-drift-policy", self.text)

    def test_gate_sits_before_commit(self) -> None:
        # Find positions in the reconciliation-checklist section.
        section_start = self.text.find("## Reconciliation checklist")
        self.assertNotEqual(section_start, -1)
        # The next `## ` heading marks end of the checklist proper.
        next_heading = self.text.find("\n## ", section_start + 1)
        section = self.text[section_start:next_heading if next_heading != -1 else len(self.text)]

        drift_pos = section.lower().find("closed-spec drift")
        commit_pos = section.find("**Commit**")
        self.assertGreater(drift_pos, 0,
                           "closed-spec drift gate not found in reconciliation checklist")
        self.assertGreater(commit_pos, 0,
                           "'**Commit**' gate must remain in reconciliation checklist")
        self.assertLess(drift_pos, commit_pos,
                        "closed-spec drift gate must precede the Commit gate")


class FormConsistencyAcrossArtifacts(unittest.TestCase):
    """AC #7 — same amendment-section shape across all four amended files."""

    AMENDED = (SPEC_016, PR_REVIEW, MEMORY_SYNC, WORKFLOW_MD)

    def test_each_has_amendments_heading(self) -> None:
        for p in self.AMENDED:
            with self.subTest(path=str(p)):
                self.assertRegex(_read(p), AMENDMENTS_HEADING_RE,
                                 f"{p} missing '## Amendments' heading")

    def test_each_has_iso_dated_entry(self) -> None:
        for p in self.AMENDED:
            with self.subTest(path=str(p)):
                body = _amendments_body(_read(p))
                self.assertRegex(
                    body, DATE_HEADING_RE,
                    f"{p} amendments must include at least one "
                    f"'### YYYY-MM-DD — ' entry (em dash)",
                )


if __name__ == "__main__":
    unittest.main()
