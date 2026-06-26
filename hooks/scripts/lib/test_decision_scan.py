"""Unit tests for hooks/scripts/lib/decision_scan.py (slice 083-04).

Pure-function scan over a Stop-hook `messages` payload. Hook-integration test
is a sibling at hooks/scripts/test_jig_decision_capture.py.

Run from the repo root:
    python3 hooks/scripts/lib/test_decision_scan.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from decision_scan import (  # noqa: E402
    Candidate,
    dedup,
    normalize_tokens,
    render_summary,
    scan,
)


def _user(text):
    return {"role": "user", "content": text}


def _agent(text):
    return {"role": "assistant", "content": text}


class TestTierDetection(unittest.TestCase):
    def test_tier1_askuserquestion_answer_is_high_and_user(self):
        messages = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "tu1", "name": "AskUserQuestion",
                 "input": {"questions": [
                     {"question": "Which auth method?", "header": "Auth"}]}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "tu1",
                 "content": "OAuth (Recommended)"},
            ]},
        ]
        t1 = [c for c in scan(messages) if c.tier == 1]
        self.assertEqual(len(t1), 1)
        self.assertEqual(t1[0].who, "user")
        self.assertEqual(t1[0].confidence, "high")
        self.assertIn("OAuth", t1[0].quote)

    def test_tier2_user_correction_should_not_default(self):
        t2 = [c for c in scan([_user("English should not be the default language.")])
              if c.tier == 2]
        self.assertEqual(len(t2), 1)
        self.assertEqual(t2[0].who, "user")
        self.assertEqual(t2[0].confidence, "high")

    def test_tier2_do_x_instead(self):
        cands = scan([_user("Don't use a modal here, do an inline banner instead.")])
        self.assertTrue(any(c.tier == 2 for c in cands))

    def test_tier2_actually_correction_marker(self):
        cands = scan([_user("Actually, the empty state should show a tip card.")])
        self.assertTrue(any(c.tier == 2 and c.who == "user" for c in cands))

    def test_tier3_agent_chose_over_is_low_confidence(self):
        t3 = [c for c in scan([_agent("I chose Postgres over SQLite for concurrency.")])
              if c.tier == 3]
        self.assertEqual(len(t3), 1)
        self.assertEqual(t3[0].who, "agent")
        self.assertEqual(t3[0].confidence, "low")


class TestProvenance(unittest.TestCase):
    def test_quote_and_turn_present(self):
        messages = [_agent("some filler reasoning"),
                    _user("Dark mode should not be the default.")]
        c = next(c for c in scan(messages) if c.tier == 2)
        self.assertIn("should not be the default", c.quote)
        self.assertEqual(c.turn, 1)

    def test_roles_not_flattened(self):
        # An agent settled-choice and a user correction must keep distinct `who`.
        messages = [_agent("I chose A over B."),
                    _user("Actually, use C instead.")]
        whos = {c.who for c in scan(messages)}
        self.assertEqual(whos, {"agent", "user"})


class TestEphemeraExcluded(unittest.TestCase):
    def test_ephemera_produce_no_candidates(self):
        for noise in ["Let me run the tests.", "Let me check the logs.",
                      "Running the build now.", "Let me look at the file."]:
            self.assertEqual(scan([_agent(noise)]), [],
                             "ephemera surfaced: %r" % noise)


class TestAdversarialMiss(unittest.TestCase):
    """AC4 — a load-bearing decision with NO trigger pattern is honestly missed.

    The scan must not surface it; it is owned by 083-06's reconciliation /
    memory-sync judgment prompt, not 083-04. This AC cannot be passed by
    writing regex-matching fixture lines.
    """

    def test_loadbearing_no_trigger_is_missed(self):
        load_bearing = _agent(
            "If we batch the writes we lose strict ordering, but throughput is "
            "the priority for this path, so we accept the weaker guarantee and "
            "document it.")
        self.assertEqual(
            scan([load_bearing]), [],
            "scan must NOT surface a trigger-phrase-free load-bearing decision; "
            "that case is owned by 083-06, not 083-04")


class TestDedup(unittest.TestCase):
    def test_dedup_suppresses_already_recorded(self):
        cands = scan([_user("English should not be the default language.")])
        self.assertTrue(cands)
        recorded = ["English is not the default language; users pick on first run."]
        self.assertEqual(dedup(cands, recorded), [],
                         "candidate already recorded must be suppressed")

    def test_dedup_keeps_novel(self):
        cands = scan([_user("Dark mode should not be the default.")])
        recorded = ["English is not the default language."]
        self.assertEqual(len(dedup(cands, recorded)), len(cands))

    def test_dedup_keeps_short_candidate_below_floor(self):
        # A 1-2 meaningful-token quote must not be deduped away just because a
        # recorded entry happens to share those tokens (over-suppression guard).
        short = Candidate(tier=2, who="user", quote="Use it.", turn=0,
                          confidence="high")
        self.assertEqual(
            dedup([short], ["we use it everywhere across the codebase"]), [short])


class TestNormalizeTokens(unittest.TestCase):
    def test_stopwords_and_punctuation_stripped(self):
        toks = normalize_tokens("English, should not be the DEFAULT language!")
        self.assertNotIn("the", toks)
        self.assertNotIn("be", toks)
        self.assertIn("english", toks)
        self.assertIn("default", toks)


class TestRenderSummary(unittest.TestCase):
    def test_summary_is_owner_gated_and_carries_provenance(self):
        summary = render_summary(scan([_user("X should not be the default.")]))
        self.assertIn("user", summary.lower())
        self.assertRegex(summary, r"(?i)triage|record|review")

    def test_empty_summary_for_no_candidates(self):
        self.assertEqual(render_summary([]), "")


if __name__ == "__main__":
    unittest.main()
