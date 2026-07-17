"""Unit tests for hooks/scripts/lib/decision_scratch.py (slice 083-07).

In-flight decision scratch log. Hook-integration test is a sibling at
hooks/scripts/test_jig_decision_inflight.py.

Run from the repo root:
    python3 hooks/scripts/lib/test_decision_scratch.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decision_scratch as ds  # noqa: E402
from decision_scan import Candidate  # noqa: E402


class ScratchIOTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_and_read_roundtrip(self):
        ok = ds.append_stub(self.project, "sess-1", "user",
                            "Use Redis instead of Memcached", "user-override",
                            turn=4)
        self.assertTrue(ok)
        stubs = ds.read_stubs(self.project, "sess-1")
        self.assertEqual(len(stubs), 1)
        self.assertEqual(stubs[0]["who"], "user")
        self.assertEqual(stubs[0]["source"], "user-override")
        self.assertEqual(stubs[0]["turn"], 4)
        self.assertIn("Redis", stubs[0]["quote"])
        self.assertIn("timestamp", stubs[0])

    def test_blank_quote_writes_nothing(self):
        ok = ds.append_stub(self.project, "sess-1", "user", "   ",
                            "askuserquestion")
        self.assertFalse(ok)
        self.assertFalse(ds.scratch_path(self.project, "sess-1").exists())
        self.assertEqual(ds.read_stubs(self.project, "sess-1"), [])

    def test_multiple_appends_accumulate(self):
        ds.append_stub(self.project, "s", "user", "first decision", "askuserquestion")
        ds.append_stub(self.project, "s", "user", "second decision", "user-override")
        self.assertEqual(len(ds.read_stubs(self.project, "s")), 2)

    def test_read_tolerates_garbage_lines(self):
        path = ds.scratch_path(self.project, "s")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('not json\n{"quote": "real one", "who": "user"}\n{}\n',
                        encoding="utf-8")
        stubs = ds.read_stubs(self.project, "s")
        self.assertEqual(len(stubs), 1)  # garbage + the no-quote {} both dropped
        self.assertEqual(stubs[0]["quote"], "real one")

    def test_clear_removes_log(self):
        ds.append_stub(self.project, "s", "user", "x decision", "user-override")
        self.assertTrue(ds.scratch_path(self.project, "s").exists())
        ds.clear_scratch(self.project, "s")
        self.assertFalse(ds.scratch_path(self.project, "s").exists())
        ds.clear_scratch(self.project, "s")  # idempotent / no error when absent

    def test_session_id_sanitized_to_single_component(self):
        path = ds.scratch_path(self.project, "../../etc/passwd")
        self.assertEqual(path.parent.name, "decision-scratch")
        self.assertNotIn("/", path.name.replace(".log", ""))

    def test_read_missing_session_is_empty(self):
        self.assertEqual(ds.read_stubs(self.project, "never-written"), [])

    def test_write_stubs_rewrites_and_empties(self):
        ds.write_stubs(self.project, "s", [
            {"quote": "keep me around", "who": "user", "source": "user-override"}])
        self.assertEqual(len(ds.read_stubs(self.project, "s")), 1)
        ds.write_stubs(self.project, "s", [])  # empty -> file removed
        self.assertFalse(ds.scratch_path(self.project, "s").exists())


class FlagRecordedTests(unittest.TestCase):
    # Bug 011 / issue #109: this path mirrored the scan's containment rule (then
    # `decision_scan.dedup`, now `flag_duplicates`) and so carried the identical
    # defect — a stub that *reverses* a recorded decision was silently pruned.
    # Stubs are now flagged, never dropped, matching the scan path.

    def test_recorded_stub_flagged_unrecorded_untouched(self):
        stubs = [
            {"quote": "Use Postgres instead of MySQL for the store",
             "who": "user", "source": "user-override"},
            {"quote": "Adopt a hexagonal architecture at the edges",
             "who": "user", "source": "user-override"},
        ]
        recorded = ["### 2026-06-26 — Store\n**Decision:** Use Postgres instead "
                    "of MySQL for the store."]
        kept = ds.flag_recorded_stubs(stubs, recorded)
        self.assertEqual(len(kept), 2, "a stub is never dropped against recorded")
        by_quote = {s["quote"]: s for s in kept}
        self.assertTrue(
            by_quote["Use Postgres instead of MySQL for the store"]
            ["possible_duplicate"])
        self.assertFalse(
            by_quote["Adopt a hexagonal architecture at the edges"]
            .get("possible_duplicate", False))

    def test_stub_reversing_a_recorded_decision_survives(self):
        stubs = [{"quote": "actually use MySQL instead of Postgres for the store",
                  "who": "user", "source": "user-override"}]
        recorded = ["### 2026-06-26 — Store\n**Decision:** Use Postgres instead "
                    "of MySQL for the store."]
        kept = ds.flag_recorded_stubs(stubs, recorded)
        self.assertEqual(len(kept), 1,
                         "a reversal captured in-flight must reach the owner")
        self.assertTrue(kept[0]["possible_duplicate"])

    def test_no_recorded_flags_nothing(self):
        stubs = [{"quote": "some decision here", "who": "user",
                  "source": "user-override"}]
        kept = ds.flag_recorded_stubs(stubs, [])
        self.assertEqual(len(kept), 1)
        self.assertFalse(kept[0].get("possible_duplicate", False))


class StubCandidateTests(unittest.TestCase):
    def test_source_maps_to_tier(self):
        cands = ds.stubs_to_candidates([
            {"quote": "answer a", "who": "user", "source": "askuserquestion"},
            {"quote": "do b instead", "who": "user", "source": "user-override"},
            {"quote": "no source", "who": "user"},
        ])
        self.assertEqual([(c.tier, c.confidence) for c in cands],
                         [(1, "high"), (2, "high"), (2, "high")])

    def test_skips_quoteless_stub(self):
        self.assertEqual(ds.stubs_to_candidates([{"who": "user"}]), [])

    def test_possible_duplicate_flag_carries_onto_the_candidate(self):
        # The stub path's half of bug 011: flag_recorded_stubs marks the dict,
        # but the flag only reaches the owner if the Candidate carries it. An
        # unflagged stub must default to False, not to a missing attribute.
        flagged, plain = ds.stubs_to_candidates([
            {"quote": "use postgres for the store", "who": "user",
             "source": "user-override", "possible_duplicate": True},
            {"quote": "adopt hexagonal edges", "who": "user",
             "source": "user-override"},
        ])
        self.assertTrue(flagged.possible_duplicate)
        self.assertFalse(plain.possible_duplicate)


class DedupScanVsStubsTests(unittest.TestCase):
    def _scan(self, quote, tier=1):
        return Candidate(tier=tier, who="user", quote=quote, turn=2, confidence="high")

    def test_scan_candidate_covered_by_stub_is_dropped(self):
        stub_cands = ds.stubs_to_candidates([
            {"quote": "Use Redis instead of Memcached for the cache",
             "who": "user", "source": "user-override"}])
        scan_cands = [self._scan("Use Redis instead of Memcached for the cache")]
        kept = ds.dedup_scan_against_stubs(scan_cands, stub_cands)
        self.assertEqual(kept, [])

    def test_unrelated_scan_candidate_kept(self):
        stub_cands = ds.stubs_to_candidates([
            {"quote": "Use Redis for caching", "who": "user",
             "source": "user-override"}])
        scan_cands = [self._scan("Adopt a hexagonal architecture boundary")]
        kept = ds.dedup_scan_against_stubs(scan_cands, stub_cands)
        self.assertEqual(len(kept), 1)

    def test_no_stubs_keeps_all_scan(self):
        scan_cands = [self._scan("anything at all here")]
        self.assertEqual(ds.dedup_scan_against_stubs(scan_cands, []), scan_cands)

    def test_short_scan_candidate_below_floor_is_kept(self):
        # The terse-quote floor applies here too: a 1-2 token quote clears any
        # containment threshold against a stub sharing those tokens. Pinned when
        # the rule moved to decision_scan.is_contained (bug 011).
        scan_cands = [self._scan("Use it.")]
        stub_cands = ds.stubs_to_candidates([
            {"quote": "we use it everywhere across the codebase",
             "who": "user", "source": "user-override"}])
        self.assertEqual(ds.dedup_scan_against_stubs(scan_cands, stub_cands),
                         scan_cands)

    def test_none_scan_candidates_is_fail_open(self):
        # The module contracts fail-open throughout; None must not raise.
        self.assertEqual(ds.dedup_scan_against_stubs(None, []), [])


class AnswerExtractionTests(unittest.TestCase):
    def test_extracts_from_nested_response(self):
        resp = {"answers": [{"label": "Pair 05+06", "value": "together"}]}
        text = ds.extract_askuserquestion_answer(resp)
        self.assertIn("Pair 05+06", text)
        self.assertIn("together", text)

    def test_falls_back_to_input_when_response_empty(self):
        text = ds.extract_askuserquestion_answer({}, {"question": "Which DB?"})
        self.assertIn("Which DB?", text)

    def test_string_response(self):
        self.assertEqual(ds.extract_askuserquestion_answer("just a string"),
                         "just a string")

    def test_empty_everything(self):
        self.assertEqual(ds.extract_askuserquestion_answer(None, None), "")


class OverrideMatchTests(unittest.TestCase):
    def test_override_phrases_match(self):
        self.assertTrue(ds.is_override("X should not be the default"))
        self.assertTrue(ds.is_override("do A instead"))
        self.assertTrue(ds.is_override("actually, let's go the other way"))

    def test_plain_prose_does_not_match(self):
        self.assertFalse(ds.is_override("let me run the tests"))
        self.assertFalse(ds.is_override(""))


if __name__ == "__main__":
    unittest.main()
