"""Spec 124-02 / ADR-0069: jig asks whether the owner wants to try a
UI-related slice — `owner-review-status`, the transition note, the
`session-plan` line, the authoring step and the slice template.

Run from the repo root:
    python3 skills/spec-workflow/test_owner_review_question.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO_ROOT / "skills" / "spec-workflow"
WORKFLOW = SKILL_DIR / "workflow.py"
SKILL_MD = SKILL_DIR / "SKILL.md"
TEMPLATE = REPO_ROOT / "templates" / "docs" / "specs" / "slice-template.md"

sys.path.insert(0, str(SKILL_DIR))
sys.path.insert(0, str(SKILL_DIR.parent))
import workflow  # noqa: E402

UI_BODY = ("**Goal:** a Save button replaces the confirmation dialog.\n\n"
           "**Acceptance Criteria:**\n\n1. Tapping Save stores the entry.\n")
PLAIN_BODY = ("**Goal:** the importer retries on a 503.\n\n"
              "**Acceptance Criteria:**\n\n1. Three retries, then exit 1.\n")


def run_workflow(*args):
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
           "JIG_REVIEW_EVIDENCE_GATE": "0", "JIG_CROSSREF_GATE": "0",
           "JIG_START_COLLISION_GATE": "0"}
    return subprocess.run([sys.executable, str(WORKFLOW), *args],
                          capture_output=True, text=True, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="jig-owner-q-"))
        self.spec_dir = self.tmp / "docs" / "specs" / "900-demo"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text("---\nstatus: DRAFT\n---\n\n# Spec\n")
        self.slice = self.spec_dir / "slice-01-thing.md"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_slice(self, body=UI_BODY, extra="", status="DRAFT",
                    frontmatter=True):
        fm = (f"---\nstatus: {status}\ndependencies: []\nlast_verified:\n"
              f"{extra}---\n\n") if frontmatter else ""
        marker = "" if frontmatter else f"**STATUS: {status}**\n\n"
        self.slice.write_text(
            fm + "## Slice 900-01 — thing\n\n" + marker + body)

    def status(self):
        r = run_workflow("owner-review-status", str(self.spec), "900-01")
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()


class StatusTests(Base):
    def test_truthy_flag_is_required(self):
        self.write_slice(PLAIN_BODY, "owner_review: true\n")
        self.assertEqual(self.status().split()[0], "required")

    def test_any_other_value_is_declined(self):
        for value in ("false", "no", "later"):
            self.write_slice(UI_BODY, f"owner_review: {value}\n")
            self.assertEqual(self.status().split()[0], "declined", value)

    def test_an_empty_value_counts_as_not_asked(self):
        self.write_slice(UI_BODY, "owner_review:\n")
        self.assertEqual(self.status().split()[0], "ask")

    def test_absent_flag_on_a_ui_slice_asks_and_gives_the_reason(self):
        self.write_slice(UI_BODY)
        out = self.status()
        self.assertEqual(out.split()[0], "ask")
        self.assertIn("button", out)
        self.assertIn("dialog", out)
        self.assertNotIn("recommended answer", out.lower())

    def test_absent_flag_on_a_non_ui_slice_is_not_applicable(self):
        self.write_slice(PLAIN_BODY)
        self.assertEqual(self.status().split()[0], "not-applicable")

    def test_design_review_makes_it_ui_and_recommends_yes(self):
        self.write_slice(PLAIN_BODY, "design_review: true\n")
        out = self.status()
        self.assertEqual(out.split()[0], "ask")
        self.assertIn("design_review", out)
        self.assertIn("recommended answer: yes", out.lower())
        # The recommendation comes after the question, not mid-sentence.
        self.assertNotIn("screen), and", out)

    def test_design_review_never_sets_the_flag(self):
        self.write_slice(PLAIN_BODY, "design_review: true\n")
        self.status()
        self.assertNotIn("owner_review", self.slice.read_text())
        r = run_workflow("owner-review-needed", str(self.spec), "900-01")
        self.assertEqual(r.stdout.strip(), "false")

    def test_unknown_slice_is_an_error(self):
        self.write_slice()
        r = run_workflow("owner-review-status", str(self.spec), "999-99")
        self.assertNotEqual(r.returncode, 0)


class UiRuleTests(unittest.TestCase):
    """AC2: one word list, whole words, case-insensitive, optional plural;
    frontmatter, comments and everything after the ACs are not scanned."""

    def signals(self, body, fm=""):
        text = (f"---\nstatus: DRAFT\n{fm}---\n\n## Slice 900-01 — t\n\n"
                + body)
        return workflow.owner_review_ui_signals(text)

    def test_terms_live_in_one_tuple(self):
        self.assertIsInstance(workflow.OWNER_REVIEW_UI_TERMS, tuple)
        self.assertIn("button", workflow.OWNER_REVIEW_UI_TERMS)

    def test_multi_word_terms_match_across_a_line_wrap(self):
        self.assertEqual(
            self.signals("**Goal:** a new user\ninterface with dark\nmode.\n"),
            ["user interface", "dark mode"])

    def test_whole_words_case_insensitive_with_plural(self):
        self.assertEqual(self.signals("**Goal:** Two BUTTONS.\n"), ["button"])
        self.assertEqual(self.signals("**Goal:** the UI.\n"), ["ui"])
        self.assertEqual(self.signals("**Goal:** dark mode.\n"), ["dark mode"])

    def test_substrings_do_not_match(self):
        for text in ("build the guide", "a screenshot diff", "quiet mode",
                     "clickhouse import", "tapestry", "touchscreen",
                     "scss", "Maui"):
            self.assertEqual(self.signals(f"**Goal:** {text}.\n"), [], text)

    def test_frontmatter_and_comments_are_not_scanned(self):
        self.assertEqual(
            self.signals("<!-- a button\nand a dialog -->\n**Goal:** x.\n",
                         fm="skill: ui\n"), [])

    def test_text_after_the_acceptance_criteria_is_not_scanned(self):
        body = ("**Goal:** x.\n\n**Acceptance Criteria:**\n\n1. y.\n\n"
                "### Verification scenario (optional)\n\nUI scenarios.\n\n"
                "**DoD:**\n- [ ] the button works\n")
        self.assertEqual(self.signals(body), [])
        body = "**Goal:** x.\n\n**DoD:**\n- [ ] the button works\n"
        self.assertEqual(self.signals(body), [])

    def test_the_untouched_slice_template_is_not_ui_related(self):
        self.assertEqual(workflow.owner_review_ui_signals(
            TEMPLATE.read_text()), [])


class TransitionNoteTests(Base):
    def move(self, target):
        return run_workflow("transition", str(self.spec), "900-01", target)

    def test_note_on_each_forward_transition_until_answered(self):
        for start, target in (("DRAFT", "READY_FOR_REVIEW"),
                              ("READY_FOR_REVIEW", "READY_FOR_IMPLEMENTATION"),
                              ("READY_FOR_IMPLEMENTATION", "IN_PROGRESS"),
                              ("IN_PROGRESS", "REVIEWED")):
            self.write_slice(UI_BODY, status=start)
            r = self.move(target)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(f"status: {target}", self.slice.read_text())
            note = r.stderr
            self.assertIn("900-01", note)
            self.assertIn("owner_review: true", note)
            self.assertIn("owner_review: false", note)
            self.assertIn("button", note)
            self.assertIn("Ask the owner", note)
            self.assertIn("Do not answer for them", note)

    def test_no_note_once_answered_or_when_not_ui(self):
        for body, extra in ((UI_BODY, "owner_review: true\n"),
                            (UI_BODY, "owner_review: false\n"),
                            (PLAIN_BODY, "")):
            self.write_slice(body, extra)
            r = self.move("READY_FOR_REVIEW")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("owner_review", r.stderr)

    def test_no_note_on_other_transitions(self):
        self.write_slice(UI_BODY, status="READY_FOR_REVIEW")
        r = self.move("DRAFT")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("owner_review", r.stderr)

    def test_no_note_for_a_slice_without_frontmatter(self):
        self.write_slice(UI_BODY, frontmatter=False)
        r = self.move("READY_FOR_REVIEW")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("owner_review", r.stderr)

    def test_design_review_note_recommends_yes(self):
        self.write_slice(PLAIN_BODY, "design_review: true\n")
        r = self.move("READY_FOR_REVIEW")
        self.assertIn("Recommended answer: yes", r.stderr)


class SessionPlanTests(Base):
    def plan(self):
        r = run_workflow("session-plan", str(self.spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_unanswered_ui_slice_gets_one_line(self):
        self.write_slice(UI_BODY)
        out = self.plan()
        lines = [ln for ln in out.splitlines() if "owner_review" in ln]
        self.assertEqual(len(lines), 1, out)
        self.assertIn("NOT ASKED YET", lines[0])
        self.assertIn("button", lines[0])
        self.assertEqual(
            re.findall(r"^\s+\d+\. ([a-z-]+) — ", out, re.MULTILINE),
            ["implement", "compliance", "craft", "reconcile", "land"])

    def test_design_review_line_recommends_yes(self):
        self.write_slice(PLAIN_BODY, "design_review: true\n")
        line = next(ln for ln in self.plan().splitlines()
                    if "NOT ASKED YET" in ln)
        self.assertIn("Recommended answer: yes", line)
        self.assertIn("Do not answer for them", line)

    def test_done_slices_get_no_line(self):
        self.write_slice(UI_BODY, status="DONE")
        self.assertNotIn("NOT ASKED YET", self.plan())

    def test_answered_or_non_ui_slices_get_no_line(self):
        for body, extra in ((UI_BODY, "owner_review: false\n"),
                            (PLAIN_BODY, "")):
            self.write_slice(body, extra)
            self.assertNotIn("NOT ASKED YET", self.plan())


class AuthoringSurfaceTests(unittest.TestCase):
    def test_skill_has_the_question_next_to_the_design_nudge(self):
        body = SKILL_MD.read_text()
        flow = body[body.index("### Creating a new spec"):
                    body.index("### Picking up a slice")]
        nudge = flow.index("5a. **Design-fidelity authoring nudge")
        question = flow.index("**Owner-review question")
        after = flow.index("5b. **Behavioral rules")
        self.assertTrue(nudge < question < after)
        step = re.sub(r"\s+", " ", flow[question:after])
        for needle in ("owner-review-status", "owner_review: true",
                       "owner_review: false", "ADR-0069", "`ask`",
                       "do not answer for the owner",
                       "recommended answer is yes",
                       "does not set the flag"):
            self.assertIn(needle, step, needle)
        low = step.lower()
        self.assertIn("before it is reconciled", low)

    def test_skill_prints_the_same_word_list(self):
        flat = re.sub(r"\s+", " ", SKILL_MD.read_text())
        start = flat.index("contain one of these terms")
        listed = flat[flat.index(":", start) + 1:flat.index(". A false", start)]
        self.assertEqual(
            re.findall(r"`([^`]+)`", listed),
            list(workflow.OWNER_REVIEW_UI_TERMS))

    def test_template_carries_the_commented_flag(self):
        text = TEMPLATE.read_text()
        fm = text[:text.index("\n---", 3)]
        self.assertRegex(fm, r"(?m)^#\s*owner_review: true")
        flat = re.sub(r"\s+", " ", fm.replace("#", " "))
        for needle in ("false", "review batch", "not in the DoD", "ADR-0069"):
            self.assertIn(needle, flat, needle)
        # Commented out = absent: a fresh slice is "not asked yet".
        self.assertNotRegex(fm, r"(?m)^owner_review:")


if __name__ == "__main__":
    unittest.main()
