"""Tests for `_common/candidate_sidecar.py` — spec 096-03 (ADR-0040 D3 / OQ2).
Focus: the lifetime / absence / staleness contract (AC9) that makes 096-05's
`not-shown` signal honest."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# Make `skills/` importable so `from _common import ...` resolves regardless of
# test-discovery order (run_tests.py pins top_level_dir=skills/_common, so the
# `_common` package needs its parent on the path).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _common import candidate_sidecar as cs  # noqa: E402


def _cands():
    return [
        {"name": "review-pr-deep", "description": "d", "path": "/p",
         "tier": "high-confidence"},
        {"name": "morning-github", "description": "b", "path": "/q",
         "tier": "speculative"},
    ]


class CandidateSidecarTest(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        root = Path(self._tmp.name)
        self.spec = root / "docs" / "specs" / "099-x" / "spec.md"
        self.spec.parent.mkdir(parents=True)
        self.spec.write_text("x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_path_keyed_by_slice_and_pass(self):
        p = cs.sidecar_path(self.spec, "099-03 — enum", "craft")
        self.assertEqual(p.name, "slice-03-craft.json")
        self.assertEqual(p.parent.name, ".candidates")

    def test_write_then_read_roundtrips(self):
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        data = cs.read_sidecar(self.spec, "099-03", "craft")
        self.assertEqual(len(data["candidates"]), 2)
        self.assertIsNone(data["pick"])
        self.assertIn("run_id", data)
        self.assertIn("created_at", data)
        # tier membership retained (096-05 reads it)
        tiers = {c["name"]: c["tier"] for c in data["candidates"]}
        self.assertEqual(tiers["review-pr-deep"], "high-confidence")
        self.assertEqual(tiers["morning-github"], "speculative")

    def test_absent_sidecar_reads_none(self):
        self.assertIsNone(cs.read_sidecar(self.spec, "099-03", "craft"))
        self.assertFalse(cs.has_shown(self.spec, "099-03", "craft"))

    def test_record_pick_requires_existing_sidecar(self):
        with self.assertRaises(cs.SidecarError):
            cs.record_pick(self.spec, "099-03", "craft", "review-pr-deep", "/p")

    def test_record_pick_updates_pick(self):
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        cs.record_pick(self.spec, "099-03", "craft", "review-pr-deep", "/p/S.md")
        data = cs.read_sidecar(self.spec, "099-03", "craft")
        self.assertEqual(data["pick"], "review-pr-deep")
        self.assertEqual(data["applied_path"], "/p/S.md")
        self.assertIsNotNone(data["picked_at"])

    def test_write_overwrites_fresh_and_resets_pick(self):
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        cs.record_pick(self.spec, "099-03", "craft", "review-pr-deep", "/p")
        first = cs.read_sidecar(self.spec, "099-03", "craft")["run_id"]
        # re-running candidates overwrites: fresh run_id, pick reset to None
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        second = cs.read_sidecar(self.spec, "099-03", "craft")
        self.assertNotEqual(first, second["run_id"])
        self.assertIsNone(second["pick"])

    # -- AC9: consume makes staleness impossible ------------------------
    def test_consume_reads_then_deletes(self):
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        cs.record_pick(self.spec, "099-03", "craft", "review-pr-deep", "/p")
        got = cs.consume(self.spec, "099-03", "craft")
        self.assertEqual(got["pick"], "review-pr-deep")
        # After consume, the sidecar is ABSENT — a subsequent cycle that skips
        # `candidates` reads None (not-shown), never a stale `shown`.
        self.assertIsNone(cs.read_sidecar(self.spec, "099-03", "craft"))
        self.assertFalse(cs.has_shown(self.spec, "099-03", "craft"))

    def test_consume_absent_returns_none(self):
        self.assertIsNone(cs.consume(self.spec, "099-03", "craft"))

    def test_distinct_passes_do_not_collide(self):
        # craft and arch for the same slice are distinct keys.
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", _cands())
        cs.write_shown(self.spec, "099-03", "arch", "arch_review", [])
        self.assertTrue(cs.has_shown(self.spec, "099-03", "craft"))
        self.assertEqual(
            len(cs.read_sidecar(self.spec, "099-03", "arch")["candidates"]), 0)
        # consuming one leaves the other intact
        cs.consume(self.spec, "099-03", "craft")
        self.assertFalse(cs.has_shown(self.spec, "099-03", "craft"))
        self.assertTrue(cs.has_shown(self.spec, "099-03", "arch"))

    def test_empty_candidate_set_is_valid(self):
        cs.write_shown(self.spec, "099-03", "craft", "pr_review", [])
        data = cs.read_sidecar(self.spec, "099-03", "craft")
        self.assertEqual(data["candidates"], [])
        self.assertTrue(cs.has_shown(self.spec, "099-03", "craft"))

    def test_malformed_sidecar_reads_none(self):
        p = cs.sidecar_path(self.spec, "099-03", "craft")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{ not json")
        self.assertIsNone(cs.read_sidecar(self.spec, "099-03", "craft"))


if __name__ == "__main__":
    unittest.main()
