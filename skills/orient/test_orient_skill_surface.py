"""Surface tests for skills/orient/SKILL.md (slice 096-01, AC5–AC8).

Half of this slice ships prose, not code. These tests pin the *load-bearing
phrases* — the ones whose absence reproduces the reported failure — rather
than re-reviewing wording. The failure they guard against: orientation
surveys only local files, never the collaboration layer, and so reports a
project as unblocked while an open PR sits asking the owner direct questions.

Run from the repo root:
    python3 skills/orient/test_orient_skill_surface.py
"""

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
SKILL = SKILL_DIR / "SKILL.md"


def section_body(text: str, heading_pattern: str) -> str:
    """Body of the `###` section whose heading matches, lowercased.

    Anchored on the *heading*, not on a phrase that may also occur in prose,
    and starting after the heading line so words in the heading itself cannot
    satisfy an assertion about the body.
    """
    match = re.search(heading_pattern, text, re.MULTILINE)
    assert match, f"no heading matched {heading_pattern!r}"
    start = text.index("\n", match.start()) + 1
    end = text.find("\n### ", start)
    return (text[start:] if end == -1 else text[start:end]).lower()


class OrientCollaborationSurveyTests(unittest.TestCase):
    """AC5: the survey reaches the collaboration layer, and does it first."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def _survey(self) -> str:
        """The body of `## What it reads (the survey)`."""
        start = self.text.index("## What it reads (the survey)")
        end = self.text.index("## The output shape", start)
        return self.text[start:end]

    def test_survey_names_both_gh_commands(self):
        survey = self._survey()
        self.assertIn("gh pr list", survey)
        self.assertIn("gh pr view", survey)

    def test_survey_says_to_read_the_pr_body(self):
        """Listing PR titles is not enough — the owner's questions live in
        the description, which is exactly what the field incident missed."""
        survey = self._survey().lower()
        self.assertIn("body", survey)
        self.assertRegex(survey, r"unattended|overnight|night|cron")

    def test_pull_requests_are_the_first_survey_bullet(self):
        survey = self._survey()
        bullets = [
            line for line in survey.splitlines()
            if line.startswith("- **")
        ]
        self.assertTrue(bullets, "survey has no bullets")
        self.assertRegex(
            bullets[0].lower(), r"pull request",
            "the PR bullet must come first — it is the one most often skipped",
        )

    def test_missing_gh_is_reported_not_silently_skipped(self):
        survey = self._survey().lower()
        self.assertIn("gh", survey)
        self.assertRegex(
            survey,
            r"(unavailable|absent|not installed|no remote)",
            "the skill must say when it could not check, not omit silently",
        )


class OrientOutputLayoutTests(unittest.TestCase):
    """AC6/AC7: there is a place to render it, ahead of the decision section."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def test_waiting_on_you_section_exists(self):
        # NB: assertRegex's third argument is `msg`, not flags — compile the
        # pattern so MULTILINE actually applies.
        self.assertRegex(
            self.text, re.compile(r"^### \d+\. Waiting on you", re.MULTILINE))

    def test_waiting_on_you_precedes_the_one_decision_section(self):
        waiting = self.text.index("Waiting on you")
        decision = self.text.index("The one decision blocking the most")
        self.assertLess(
            waiting, decision,
            "finished work awaiting a human outranks work not yet started",
        )

    def test_layout_section_numbers_are_unique_and_sequential(self):
        numbers = [
            int(m.group(1))
            for m in re.finditer(r"^### (\d+)\. ", self.text, re.MULTILINE)
        ]
        self.assertEqual(
            numbers, sorted(numbers), "layout sections must stay in order")
        self.assertEqual(
            len(numbers), len(set(numbers)),
            f"duplicate section numbers in the fixed layout: {numbers}",
        )

    def test_the_three_misleading_states_are_named_in_the_section(self):
        """Scoped to the section *body* on purpose.

        Each of these three words also occurs elsewhere in the file
        ('Accepted/Superseded' in the ADR bullet, 'stale'/'unmerged' in Recent
        work) — and 'unmerged' appears in this very section's own heading — so
        a whole-file or heading-inclusive search would pass with the entire
        three-state list deleted.
        """
        section = section_body(self.text, r"^### \d+\. Waiting on you")
        for token in ("stale", "unmerged", "superseded"):
            self.assertIn(
                token, section,
                f"the Waiting-on-you section body must flag the '{token}' "
                "case — each misleads the reader in a different way",
            )

    def test_decision_section_cross_checks_open_prs(self):
        """The reported failure: re-deriving questions a PR already asked.

        Asserting a bare 'pr' here would be tautological — 'Proposed' and
        'prominently' both contain it and both predate this slice. Pin the
        actual instruction instead.
        """
        section = section_body(
            self.text, r"^### \d+\. The one decision blocking the most")
        self.assertIn("cross-check", section)
        self.assertIn("open prs", section)


class OrientJudgmentRuleTests(unittest.TestCase):
    """AC8: the generalising rule is stated where judgment lives."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def _judgment(self) -> str:
        start = self.text.index("## Judgment")
        rest = self.text.find("\n## ", start + 1)
        return self.text[start:] if rest == -1 else self.text[start:rest]

    def test_blocked_on_a_human_rule_is_present(self):
        judgment = self._judgment().lower()
        self.assertIn("blocked on a human", judgment)

    def test_re_ask_within_a_session_is_covered(self):
        """The second miss in the field incident: answering a later re-ask
        from context already in hand instead of re-checking."""
        judgment = self._judgment().lower()
        self.assertRegex(judgment, r"re-?ask|again|same session")


if __name__ == "__main__":
    unittest.main()
