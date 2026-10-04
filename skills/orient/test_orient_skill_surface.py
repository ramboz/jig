"""Surface tests for skills/orient/SKILL.md.

Half of this skill ships prose, not code. These tests pin the *load-bearing
phrases* — the ones whose absence would reproduce a reported failure or drop
a core acceptance criterion — rather than re-reviewing wording.

Three provenances live here:
  - Slice 101-01 (AC5–AC8): the collaboration-survey + freshness additions.
    The failure they guard against — orientation surveys only local files,
    never the collaboration layer, and so reports a project as unblocked
    while an open PR sits asking the owner direct questions.
  - Slice 088-02 (AC4–AC5): the skill's own core prose contract — zero-write
    (writes no file) and the correct `jig:spec-workflow` handoff. Added at
    088-02 close-out to pin the two ACs the compliance pass found unguarded
    (a future edit deleting either would otherwise fail no test).
  - Slice 116-02 (AC2–AC5): the use-case progress survey source and the one
    conditional layout section, both fed by `workflow.py progress --summary`.
    The failure they guard against — the briefing silently dropping the
    section, or growing it into a full tree / percentage / on-goal verdict
    that ADR-0064 rules out.

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


class OrientOriginFreshnessSurfaceTests(unittest.TestCase):
    """Bug 031: the interactive path must refresh against origin, or it will
    narrate stale local boards as current. These pin the load-bearing phrases
    whose absence reproduces the reported failure."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def test_headline_command_passes_fetch(self):
        """The documented `orient` invocation must carry `--fetch`; without it
        the skill reads stale boards without checking origin."""
        self.assertRegex(
            self.text,
            r"workflow\.py\"?\s+orient\s+--project-dir\s+\.\s+--fetch",
        )

    def test_behind_reading_is_flagged_as_possibly_stale(self):
        """A `behind` reading must be tied to 'treat the boards as stale',
        not left as a bare number the reader can ignore."""
        lowered = self.text.lower()
        self.assertIn("freshness", lowered)
        self.assertRegex(lowered, r"behind")
        self.assertRegex(lowered, r"stale")

    def test_unreachable_origin_is_reported_not_assumed_fresh(self):
        self.assertRegex(self.text.lower(), r"could not reach origin")


class Orient088CoreContractTests(unittest.TestCase):
    """Slice 088-02 AC4/AC5: the skill's own core prose contract.

    These pin the two 088-02 ACs the compliance pass found unguarded —
    zero-write and the correct handoff. Both are scoped to a section *body*
    so a whole-file match can't satisfy them with the load-bearing prose
    deleted (the words 'writes'/'spec-workflow' recur elsewhere).
    """

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def _section(self, start_marker: str) -> str:
        start = self.text.index(start_marker)
        rest = self.text.find("\n## ", start + 1)
        return (self.text[start:] if rest == -1 else self.text[start:rest]).lower()

    def test_zero_write_contract_is_stated(self):
        """AC4: a dedicated section must state the skill writes no file.

        Anchored to the '## Orient writes nothing' section body; asserting a
        bare 'read-only' file-wide would pass with the whole contract gone
        (the Judgment section also says 'read-only')."""
        body = self._section("## Orient writes nothing")
        self.assertIn("read-only", body)
        self.assertRegex(
            body, r"no file|writes\s+\*\*no file|nothing under `docs/`|zero-write",
            "the zero-write section body must say it writes no file",
        )

    def test_handoff_routes_implement_through_spec_workflow_not_implementer(self):
        """AC5: 'implement a ready slice' routes through jig:spec-workflow, and
        the section names that there is no directly invocable jig:implementer.

        Scoped to the '## Handoff' section body — 'spec-workflow' appears in
        other bullets/prose, so a file-wide search would be tautological."""
        body = self._section("## Handoff")
        self.assertIn("implement a ready slice", body)
        self.assertIn("jig:spec-workflow", body)
        self.assertRegex(
            body, r"no directly invocable\s+`?jig:implementer",
            "the handoff must warn there is no invocable jig:implementer skill",
        )


class OrientUseCaseProgressTests(unittest.TestCase):
    """Slice 116-02 AC2-AC5: a named survey source plus one conditional layout
    section that copies `workflow.py progress --summary` (ADR-0064).

    Section assertions are scoped to the new section's body (not the whole
    file): 'percentage', 'unanchored' and 'workflow.py progress' would
    otherwise be satisfiable by prose elsewhere, or by the heading alone.
    """

    HEADING = r"^### \d+\. Use-case progress"

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text()

    def _survey(self) -> str:
        start = self.text.index("## What it reads (the survey)")
        end = self.text.index("## The output shape", start)
        return self.text[start:end]

    def _survey_bullet(self) -> str:
        """The survey bullet that names the progress command, lowercased."""
        chunks = re.split(r"\n(?=- \*\*)", self._survey())
        hits = [c for c in chunks if "progress --summary" in c]
        self.assertEqual(len(hits), 1, "exactly one survey bullet owns it")
        return re.sub(r"\s+", " ", hits[0]).lower()

    def _section(self) -> str:
        return re.sub(r"\s+", " ", section_body(self.text, self.HEADING))

    # ---- AC2: the named survey source ---------------------------------------

    def test_survey_names_the_summary_command(self):
        self.assertRegex(
            self._survey(),
            r"workflow\.py\"?\s+progress\s+--summary",
            "the survey must name the command orient reads",
        )

    def test_survey_reads_it_only_when_the_vision_has_a_use_cases_section(self):
        bullet = self._survey_bullet()
        self.assertIn("## use cases", bullet)
        self.assertIn("product-vision.md", bullet)
        self.assertRegex(bullet, r"\bonly when\b")

    # ---- AC5: the new source is described as read-only ----------------------

    def test_survey_describes_the_new_source_as_read_only(self):
        bullet = self._survey_bullet()
        self.assertIn("read-only", bullet)
        self.assertIn("writes nothing", bullet)

    # ---- AC3: one conditional section in the fixed layout -------------------

    def test_layout_has_a_use_case_progress_section_marked_conditional(self):
        self.assertRegex(
            self.text,
            re.compile(
                self.HEADING
                + r".*\(when the use-case layer is adopted\)\s*$",
                re.MULTILINE),
            "the section heading must carry the adoption condition",
        )

    def test_section_sits_in_the_fixed_order_before_the_recommendation(self):
        heading = re.search(self.HEADING, self.text, re.MULTILINE)
        self.assertTrue(heading)
        self.assertLess(
            heading.start(), self.text.index("My recommendation (always)"))
        self.assertLess(
            self.text.index("The one decision blocking the most (when"),
            heading.start(),
            "waiting-on-a-human items outrank the progress block",
        )

    def test_section_copies_the_summary_instead_of_rederiving_it(self):
        body = self._section()
        self.assertIn("progress --summary", body)
        self.assertRegex(body, r"\bcopy\b")
        self.assertRegex(body, r"re-?deriv|recount")

    def test_section_carries_exactly_the_three_summary_things(self):
        body = self._section()
        self.assertRegex(body, r"done/known")  # the totals line
        self.assertIn("no done slice or no spec", body)  # the untouched goals
        self.assertIn("unanchored", body)  # the untraced work, by name
        self.assertRegex(body, r"\bno more\b|\bnothing else\b")

    def test_section_points_at_the_full_listing_command(self):
        body = self._section()
        self.assertRegex(
            body, r"`workflow\.py progress`[^.]*full",
            "one line must name `workflow.py progress` for the full listing",
        )

    def test_section_never_reproduces_the_tree_or_states_a_percentage(self):
        body = self._section()
        self.assertRegex(body, r"never[^.]*full tree")
        self.assertRegex(body, r"never[^.]*percentage")

    def test_section_is_not_a_drift_or_on_goal_verdict(self):
        """ADR-0064 bound 5: a progress view, not a drift detector."""
        body = self._section()
        self.assertRegex(body, r"not a (verdict|check)[^.]*(on-goal|drift)")

    # ---- AC4: silent when not adopted ---------------------------------------

    def test_section_states_the_omission_rule(self):
        body = self._section()
        self.assertIn("## use cases", body)
        self.assertRegex(body, r"omit[^.]*(section|it)")
        self.assertRegex(
            body, r"no mention of use cases|nothing about use cases",
            "a non-adopting project's briefing must not mention use cases",
        )

    def test_section_renders_the_content_as_bullets(self):
        """The fixed layout's formatting rules (one bullet per item, no inline
        lists) apply to this section too — the output is copied as content,
        not pasted as a block."""
        self.assertRegex(self._section(), r"\bas bullets\b")

    # ---- AC7: an unelicited vision is omitted like an absent section --------

    def test_omission_covers_any_one_line_skipped_or_noop_note(self):
        """The survey bullet and the section both drop the section on the
        command's one-line `skipped` / `no-op` note — which now includes a
        `## Use cases` section that is present but not elicited yet."""
        for where, text in (("survey bullet", self._survey_bullet()),
                            ("section", self._section())):
            with self.subTest(where=where):
                self.assertIn("`skipped`", text)
                self.assertIn("`no-op`", text)
                self.assertIn("elicited", text)
                self.assertRegex(text, r"one-line")

    # ---- AC5: the write contract is untouched -------------------------------

    def test_zero_write_section_does_not_gain_a_progress_exception(self):
        start = self.text.index("## Orient writes nothing")
        end = self.text.index("\n## ", start + 1)
        body = self.text[start:end].lower()
        # Specific tokens, not a bare "progress": an unrelated IN_PROGRESS
        # mention added to this section later must not trip the guard.
        self.assertNotIn("use-case progress", body)
        self.assertNotIn("progress --summary", body)
        self.assertNotIn("workflow.py progress", body)
        self.assertNotIn("use case", body)


if __name__ == "__main__":
    unittest.main()
