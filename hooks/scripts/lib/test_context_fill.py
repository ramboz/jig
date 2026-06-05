"""Unit tests for hooks/scripts/lib/context_fill.py.

These cover the pure-function estimator surface (no I/O beyond file reads
from a tempdir fixture). Hook-integration tests live as a sibling at
hooks/scripts/test_jig_context_check.py.

Run from the repo root:
    python3 hooks/scripts/lib/test_context_fill.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context_fill import (
    DEFAULT_COMPACT_THRESHOLD,
    DEFAULT_GROWTH_THRESHOLD,
    DEFAULT_READ_LEAN_BYTES,
    DEFAULT_THRESHOLD,
    DEFAULT_WINDOW_BYTES,
    GROWTH_BANDS,
    RATIO,
    _resolve_compact_threshold,
    _resolve_read_lean_bytes,
    compaction_nudge_text,
    duplicate_read_nudge_text,
    estimate,
    evaluate_growth,
    evaluate_read,
    growth_nudge_for_turn,
    growth_nudge_text,
    large_read_nudge_text,
    read_nudge_for_turn,
    read_tail_cache_read_tokens,
    token_window,
)


class EstimateBasicsTests(unittest.TestCase):
    """Pure-function behavior over a project-root tempdir."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ctx-")
        self.root = Path(self.tmpdir)
        # Clear env vars so tests are deterministic regardless of host env.
        for var in ("JIG_CONTEXT_WINDOW_BYTES", "JIG_CONTEXT_SOFT_WARN_PCT"):
            os.environ.pop(var, None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_repo_zero_bytes(self):
        """AC #6 edge case: empty repo (no CLAUDE.md, no docs/memory) →
        bytes == 0, ratio == 0, no threshold crossing."""
        result = estimate(self.root)
        self.assertEqual(result["bytes"], 0)
        self.assertEqual(result["est_tokens"], 0)
        self.assertEqual(result["ratio"], 0.0)
        self.assertEqual(result["breakdown"], {})
        self.assertLess(result["ratio"], result["threshold"])

    def test_claudemd_only(self):
        """AC #6: CLAUDE.md only → bytes equals len(CLAUDE.md content)."""
        body = "Hello jig.\n" * 50  # 550 bytes
        (self.root / "CLAUDE.md").write_text(body)
        result = estimate(self.root)
        self.assertEqual(result["bytes"], len(body.encode("utf-8")))
        self.assertEqual(result["est_tokens"], result["bytes"] // RATIO)
        self.assertIn("CLAUDE.md", result["breakdown"])
        self.assertEqual(result["breakdown"]["CLAUDE.md"], len(body.encode("utf-8")))

    def test_mixed_files_aggregate(self):
        """AC #6: CLAUDE.md + 2 memory files → bytes is the sum."""
        primer = "PRIMER\n" * 10
        glossary = "GLOSSARY\n" * 20
        learnings = "LEARNINGS\n" * 30
        (self.root / "CLAUDE.md").write_text(primer)
        memory = self.root / "docs" / "memory"
        memory.mkdir(parents=True)
        (memory / "glossary.md").write_text(glossary)
        (memory / "learnings.md").write_text(learnings)
        result = estimate(self.root)
        expected = (len(primer.encode("utf-8"))
                    + len(glossary.encode("utf-8"))
                    + len(learnings.encode("utf-8")))
        self.assertEqual(result["bytes"], expected)
        self.assertIn("CLAUDE.md", result["breakdown"])
        self.assertIn("docs/memory/glossary.md", result["breakdown"])
        self.assertIn("docs/memory/learnings.md", result["breakdown"])

    def test_missing_docs_memory_no_error(self):
        """AC #6 DoD edge case: missing docs/memory/ → no error, just no
        contribution. Same shape as the CLAUDE.md-only case."""
        body = "x" * 100
        (self.root / "CLAUDE.md").write_text(body)
        # No docs/memory/ dir at all.
        result = estimate(self.root)
        self.assertEqual(result["bytes"], 100)
        # Only CLAUDE.md in the breakdown.
        self.assertEqual(list(result["breakdown"].keys()), ["CLAUDE.md"])

    def test_empty_docs_memory_dir(self):
        """DoD edge case: empty docs/memory/ → no contribution, no error."""
        (self.root / "CLAUDE.md").write_text("a" * 50)
        (self.root / "docs" / "memory").mkdir(parents=True)
        result = estimate(self.root)
        self.assertEqual(result["bytes"], 50)
        # docs/memory/ exists but empty: no memory entries in breakdown.
        memory_entries = [k for k in result["breakdown"] if k.startswith("docs/memory/")]
        self.assertEqual(memory_entries, [])

    def test_docs_memory_skips_non_md(self):
        """docs/memory/ contribution is .md only — sibling .txt / .json
        files are not always-loaded primer content."""
        (self.root / "CLAUDE.md").write_text("primer\n")
        memory = self.root / "docs" / "memory"
        memory.mkdir(parents=True)
        (memory / "glossary.md").write_text("md-content\n")
        (memory / "notes.txt").write_text("txt-content\n")
        result = estimate(self.root)
        # .txt is excluded — only the .md counts.
        keys = list(result["breakdown"].keys())
        self.assertIn("docs/memory/glossary.md", keys)
        self.assertNotIn("docs/memory/notes.txt", keys)


class EstimateDefaultsTests(unittest.TestCase):
    """The 200K-token Opus-4.7-sized window and the 30% pin."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ctx-defaults-")
        self.root = Path(self.tmpdir)
        for var in ("JIG_CONTEXT_WINDOW_BYTES", "JIG_CONTEXT_SOFT_WARN_PCT"):
            os.environ.pop(var, None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_window_is_opus_47_sized(self):
        """200K tokens × 4 bytes/token = 800_000 bytes (Opus 4.7 sentinel)."""
        self.assertEqual(DEFAULT_WINDOW_BYTES, 800_000)

    def test_default_threshold_is_30_percent(self):
        """The 30% pin — pre-dumb-zone (40% per CLAUDE.md hot cache)."""
        self.assertEqual(DEFAULT_THRESHOLD, 0.30)

    def test_default_ratio_is_4_bytes_per_token(self):
        """RATIO = 4 bytes per token, the rough English-prose heuristic."""
        self.assertEqual(RATIO, 4)

    def test_ratio_uses_default_window(self):
        """ratio = bytes / DEFAULT_WINDOW_BYTES when no env override."""
        body = "x" * 80_000  # 10% of the 800_000 default
        (self.root / "CLAUDE.md").write_text(body)
        result = estimate(self.root)
        self.assertEqual(result["window_bytes"], DEFAULT_WINDOW_BYTES)
        self.assertAlmostEqual(result["ratio"], 0.10, places=4)
        self.assertEqual(result["threshold"], DEFAULT_THRESHOLD)


class EstimateEnvOverrideTests(unittest.TestCase):
    """Env-var overrides for window size + threshold."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ctx-env-")
        self.root = Path(self.tmpdir)
        self._saved_env = {}
        for var in ("JIG_CONTEXT_WINDOW_BYTES", "JIG_CONTEXT_SOFT_WARN_PCT"):
            self._saved_env[var] = os.environ.pop(var, None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        for var, val in self._saved_env.items():
            if val is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = val

    def test_window_bytes_env_override(self):
        """AC #2: JIG_CONTEXT_WINDOW_BYTES=1000 + bytes=400 → ratio=0.4."""
        (self.root / "CLAUDE.md").write_text("x" * 400)
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = "1000"
        result = estimate(self.root)
        self.assertEqual(result["window_bytes"], 1000)
        self.assertEqual(result["bytes"], 400)
        self.assertAlmostEqual(result["ratio"], 0.4, places=4)

    def test_threshold_env_override(self):
        """AC #2: JIG_CONTEXT_SOFT_WARN_PCT=0.5 overrides default 0.3."""
        os.environ["JIG_CONTEXT_SOFT_WARN_PCT"] = "0.5"
        result = estimate(self.root)
        self.assertEqual(result["threshold"], 0.5)

    def test_threshold_boundary_uses_gte(self):
        """DoD edge case: ratio == threshold → considered crossed (caller
        uses >=). The estimator just returns ratio + threshold; the policy
        is `ratio >= threshold` — pin it here so a regression is caught."""
        # 100 bytes vs 1000-byte window → ratio == 0.1. Threshold == 0.1
        # is exactly the boundary.
        (self.root / "CLAUDE.md").write_text("x" * 100)
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = "1000"
        os.environ["JIG_CONTEXT_SOFT_WARN_PCT"] = "0.1"
        result = estimate(self.root)
        self.assertAlmostEqual(result["ratio"], 0.1, places=4)
        self.assertEqual(result["threshold"], 0.1)
        # The boundary contract: caller treats >= as crossed.
        self.assertTrue(result["ratio"] >= result["threshold"])

    def test_invalid_window_env_falls_back_to_default(self):
        """Robustness: a malformed JIG_CONTEXT_WINDOW_BYTES falls back to
        the Opus 4.7 sentinel rather than crashing the hook."""
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = "not-an-int"
        result = estimate(self.root)
        self.assertEqual(result["window_bytes"], DEFAULT_WINDOW_BYTES)

    def test_invalid_threshold_env_falls_back_to_default(self):
        """Robustness: malformed JIG_CONTEXT_SOFT_WARN_PCT falls back."""
        os.environ["JIG_CONTEXT_SOFT_WARN_PCT"] = "fifty-percent"
        result = estimate(self.root)
        self.assertEqual(result["threshold"], DEFAULT_THRESHOLD)


class EstimatePurityTests(unittest.TestCase):
    """The function is pure (no printing, no mutation outside what the
    caller does with the return value). Goal #6 of spec 026: estimator
    importable in isolation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-ctx-pure-")
        self.root = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_does_not_print(self):
        """estimate() must not print to stdout/stderr — caller controls I/O."""
        import contextlib
        import io
        (self.root / "CLAUDE.md").write_text("payload")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            estimate(self.root)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_return_keys_present(self):
        """Spec 026 goal #6: stable interface. The contract is the dict
        keys; servo will subprocess-invoke for the same shape."""
        (self.root / "CLAUDE.md").write_text("payload")
        result = estimate(self.root)
        for key in ("bytes", "est_tokens", "ratio", "threshold",
                    "breakdown", "window_bytes"):
            self.assertIn(key, result, f"missing key: {key}")


# --------------------------------------------------------------------------
# Slice 055-02 — in-session context-growth nudge. Pure-function surface:
# token_window(), read_tail_cache_read_tokens(), evaluate_growth(), plus the
# new JIG_CONTEXT_GROWTH_WARN_PCT default + bands. The state-file I/O lives in
# the hook; these cover the testable math the hook delegates to.
# --------------------------------------------------------------------------


class GrowthDefaultsTests(unittest.TestCase):
    """AC #3 — the growth threshold defaults to 0.40 (the dumb-zone line)
    and the bands are 40 / 60 / 80%."""

    def test_default_growth_threshold_is_40_percent(self):
        self.assertEqual(DEFAULT_GROWTH_THRESHOLD, 0.40)

    def test_growth_bands_are_40_60_80(self):
        self.assertEqual(GROWTH_BANDS, (0.40, 0.60, 0.80))

    def test_token_window_is_window_bytes_over_ratio(self):
        """AC #3 — the token-window reuses JIG_CONTEXT_WINDOW_BYTES / RATIO,
        so bands are fractions of the configurable window, not hardcoded
        token counts."""
        os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)
        # Default: 800_000 bytes / 4 = 200_000 tokens.
        self.assertEqual(token_window(), DEFAULT_WINDOW_BYTES // RATIO)
        self.assertEqual(token_window(), 200_000)

    def test_token_window_honors_window_bytes_env(self):
        try:
            os.environ["JIG_CONTEXT_WINDOW_BYTES"] = "4000"
            self.assertEqual(token_window(), 1000)  # 4000 / 4
        finally:
            os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)


class GrowthThresholdEnvTests(unittest.TestCase):
    """AC #3 — JIG_CONTEXT_GROWTH_WARN_PCT mirrors the out-of-range fallback
    behavior of JIG_CONTEXT_SOFT_WARN_PCT (fallback 0.40)."""

    def setUp(self):
        self._saved = os.environ.pop("JIG_CONTEXT_GROWTH_WARN_PCT", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("JIG_CONTEXT_GROWTH_WARN_PCT", None)
        else:
            os.environ["JIG_CONTEXT_GROWTH_WARN_PCT"] = self._saved

    def _bands_for(self):
        """evaluate_growth reads the env each call; assert via the first
        band returned for a tokens value just over the threshold."""
        # window 100 tokens; tokens at the threshold → first band == threshold.
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        try:
            decision = evaluate_growth(
                cache_read_tokens=100, warned_bands=[],
            )
            return decision
        finally:
            os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)

    def test_env_override_changes_first_band(self):
        os.environ["JIG_CONTEXT_GROWTH_WARN_PCT"] = "0.50"
        # 100-token window, 49 tokens = 49% → below a 0.50 first band.
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        try:
            below = evaluate_growth(cache_read_tokens=49, warned_bands=[])
            self.assertFalse(below["nudge"])
            at = evaluate_growth(cache_read_tokens=50, warned_bands=[])
            self.assertTrue(at["nudge"])
        finally:
            os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)

    def test_out_of_range_env_falls_back_to_040(self):
        os.environ["JIG_CONTEXT_GROWTH_WARN_PCT"] = "40"  # percent, not fraction
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        try:
            # Falls back to 0.40 → 39 tokens silent, 40 tokens nudges.
            below = evaluate_growth(cache_read_tokens=39, warned_bands=[])
            self.assertFalse(below["nudge"])
            at = evaluate_growth(cache_read_tokens=40, warned_bands=[])
            self.assertTrue(at["nudge"])
        finally:
            os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)

    def test_non_numeric_env_falls_back_to_040(self):
        os.environ["JIG_CONTEXT_GROWTH_WARN_PCT"] = "lots"
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        try:
            at = evaluate_growth(cache_read_tokens=40, warned_bands=[])
            self.assertTrue(at["nudge"])
        finally:
            os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)


class EvaluateGrowthBandTests(unittest.TestCase):
    """AC #4 — at most one nudge per band, re-arm on drop. evaluate_growth is
    pure: it takes the current cache_read tokens + the prior warned-band list
    and returns {nudge, band, warned_bands} (the next state)."""

    def setUp(self):
        # Pin a tidy 100-token window so band fractions map to round numbers:
        # 40 tokens = 40%, 60 = 60%, 80 = 80%.
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        os.environ.pop("JIG_CONTEXT_GROWTH_WARN_PCT", None)

    def tearDown(self):
        os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)

    def test_below_first_band_is_silent(self):
        d = evaluate_growth(cache_read_tokens=39, warned_bands=[])
        self.assertFalse(d["nudge"])
        self.assertEqual(d["warned_bands"], [])

    def test_first_crossing_nudges_once(self):
        d = evaluate_growth(cache_read_tokens=45, warned_bands=[])
        self.assertTrue(d["nudge"])
        self.assertAlmostEqual(d["band"], 0.40, places=4)
        # 0.40 band now recorded as warned.
        self.assertIn(0.40, d["warned_bands"])

    def test_recrossing_same_band_is_silent(self):
        # Already warned the 0.40 band; still in [40, 60) → silent.
        d = evaluate_growth(cache_read_tokens=55, warned_bands=[0.40])
        self.assertFalse(d["nudge"])
        # Still recorded.
        self.assertIn(0.40, d["warned_bands"])

    def test_higher_band_nudges_again(self):
        # Warned 0.40; now at 60% → 0.60 band newly crossed.
        d = evaluate_growth(cache_read_tokens=65, warned_bands=[0.40])
        self.assertTrue(d["nudge"])
        self.assertAlmostEqual(d["band"], 0.60, places=4)
        self.assertIn(0.60, d["warned_bands"])
        self.assertIn(0.40, d["warned_bands"])

    def test_jump_straight_to_top_band_nudges(self):
        # No prior warnings; jump to 85% → nudges, reports the top band (0.80).
        d = evaluate_growth(cache_read_tokens=85, warned_bands=[])
        self.assertTrue(d["nudge"])
        self.assertAlmostEqual(d["band"], 0.80, places=4)
        # All crossed bands recorded so re-crossing stays silent.
        for b in (0.40, 0.60, 0.80):
            self.assertIn(b, d["warned_bands"])

    def test_drop_below_band_rearms(self):
        # Warned 0.40 + 0.60; estimate drops to 30% (e.g. after /compact).
        d = evaluate_growth(cache_read_tokens=30, warned_bands=[0.40, 0.60])
        self.assertFalse(d["nudge"])
        # Both bands re-armed (cleared), because 30% is below both.
        self.assertNotIn(0.40, d["warned_bands"])
        self.assertNotIn(0.60, d["warned_bands"])

    def test_drop_then_reclimb_nudges_again(self):
        # Step 1: climb to 45% → nudge, warned {0.40}.
        d1 = evaluate_growth(cache_read_tokens=45, warned_bands=[])
        self.assertTrue(d1["nudge"])
        # Step 2: drop to 30% (compact) → silent, re-arm.
        d2 = evaluate_growth(cache_read_tokens=30, warned_bands=d1["warned_bands"])
        self.assertFalse(d2["nudge"])
        # Step 3: reclimb to 45% → nudges AGAIN (band re-armed).
        d3 = evaluate_growth(cache_read_tokens=45, warned_bands=d2["warned_bands"])
        self.assertTrue(d3["nudge"])
        self.assertAlmostEqual(d3["band"], 0.40, places=4)

    def test_partial_drop_rearms_only_crossed_band(self):
        # Warned 0.40 + 0.60; drop to 50% → below 0.60 (re-arm) but still
        # at/above 0.40 (stays warned, no new nudge).
        d = evaluate_growth(cache_read_tokens=50, warned_bands=[0.40, 0.60])
        self.assertFalse(d["nudge"])
        self.assertIn(0.40, d["warned_bands"])
        self.assertNotIn(0.60, d["warned_bands"])

    def test_zero_tokens_is_silent(self):
        d = evaluate_growth(cache_read_tokens=0, warned_bands=[])
        self.assertFalse(d["nudge"])

    def test_none_tokens_is_silent(self):
        """No assistant turn yet → cache_read_tokens is None → silent."""
        d = evaluate_growth(cache_read_tokens=None, warned_bands=[])
        self.assertFalse(d["nudge"])
        self.assertEqual(d["warned_bands"], [])


class ReadTailTests(unittest.TestCase):
    """AC #2 / AC #5 — read_tail_cache_read_tokens reads the last assistant
    record's cache_read_input_tokens from the transcript tail, and returns
    None (never raises) for missing / empty / malformed inputs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-tail-")
        self.root = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_jsonl(self, name, records):
        import json as _json
        path = self.root / name
        path.write_text("\n".join(_json.dumps(r) for r in records) + "\n")
        return path

    def _assistant(self, cache_read):
        return {
            "type": "assistant",
            "message": {"usage": {"cache_read_input_tokens": cache_read}},
        }

    def test_reads_last_assistant_cache_read(self):
        path = self._write_jsonl("t.jsonl", [
            {"type": "user", "message": {"role": "user"}},
            self._assistant(1000),
            {"type": "user", "message": {"role": "user"}},
            self._assistant(50_000),
        ])
        self.assertEqual(read_tail_cache_read_tokens(path), 50_000)

    def test_skips_trailing_non_assistant_records(self):
        """The tail may end with user / tool-result records; the function
        walks back to the last assistant usage."""
        path = self._write_jsonl("t.jsonl", [
            self._assistant(77_000),
            {"type": "user", "message": {"role": "user"}},
            {"type": "system", "subtype": "info"},
        ])
        self.assertEqual(read_tail_cache_read_tokens(path), 77_000)

    def test_missing_file_returns_none(self):
        self.assertIsNone(
            read_tail_cache_read_tokens(self.root / "does-not-exist.jsonl")
        )

    def test_none_path_returns_none(self):
        self.assertIsNone(read_tail_cache_read_tokens(None))

    def test_empty_file_returns_none(self):
        path = self.root / "empty.jsonl"
        path.write_text("")
        self.assertIsNone(read_tail_cache_read_tokens(path))

    def test_no_assistant_record_returns_none(self):
        path = self._write_jsonl("t.jsonl", [
            {"type": "user", "message": {"role": "user"}},
            {"type": "user", "message": {"role": "user"}},
        ])
        self.assertIsNone(read_tail_cache_read_tokens(path))

    def test_malformed_lines_do_not_raise(self):
        path = self.root / "bad.jsonl"
        path.write_text("{not json\n" + "also not json\n")
        # No assistant record parseable → None, no exception.
        self.assertIsNone(read_tail_cache_read_tokens(path))

    def test_malformed_tail_then_valid_assistant(self):
        """A corrupt final line must not mask an earlier valid assistant
        record reachable from the tail."""
        import json as _json
        good = _json.dumps(self._assistant(42_000))
        path = self.root / "mixed.jsonl"
        path.write_text(good + "\n" + "{garbage\n")
        self.assertEqual(read_tail_cache_read_tokens(path), 42_000)

    def test_assistant_without_usage_is_skipped(self):
        path = self._write_jsonl("t.jsonl", [
            self._assistant(33_000),
            {"type": "assistant", "message": {}},  # no usage
        ])
        # Walks back past the usage-less record to the real one.
        self.assertEqual(read_tail_cache_read_tokens(path), 33_000)


class GrowthNudgeTextTests(unittest.TestCase):
    """AC #1 / AC #6 — the nudge body recommends /compact or delegation and
    points at the workflow.md discipline section."""

    def test_text_mentions_compact_and_delegation(self):
        text = growth_nudge_text(0.40, 0.45)
        self.assertIn("/compact", text)
        self.assertIn("delegat", text.lower())

    def test_text_references_workflow_section(self):
        text = growth_nudge_text(0.60, 0.65)
        self.assertIn("Context-cost discipline", text)
        self.assertIn("docs/workflow.md", text)


class GrowthNudgeForTurnTests(unittest.TestCase):
    """The hook's orchestration helper: tail-read → state → evaluate →
    persist. Pins the per-band rate-limit + re-arm via a real state dir,
    matching what the shell calls (slice 055-02)."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="jig-growth-turn-"))
        self.state = self.base / "state"
        self.state.mkdir()
        # 100-token window.
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        os.environ.pop("JIG_CONTEXT_GROWTH_WARN_PCT", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)
        os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)

    def _transcript(self, value, name="t.jsonl"):
        import json as _json
        path = self.base / name
        rec = {"type": "assistant",
               "message": {"usage": {"cache_read_input_tokens": value}}}
        path.write_text(_json.dumps(rec) + "\n")
        return path

    def test_below_threshold_returns_none(self):
        path = self._transcript(30)
        self.assertIsNone(
            growth_nudge_for_turn(path, "s", self.state)
        )

    def test_first_crossing_returns_text(self):
        path = self._transcript(45)
        out = growth_nudge_for_turn(path, "s", self.state)
        self.assertIsNotNone(out)
        self.assertIn("/compact", out)

    def test_second_call_same_band_returns_none(self):
        p1 = self._transcript(45, "a.jsonl")
        self.assertIsNotNone(growth_nudge_for_turn(p1, "sess", self.state))
        p2 = self._transcript(50, "b.jsonl")
        self.assertIsNone(growth_nudge_for_turn(p2, "sess", self.state),
                          "same band must stay silent across calls")

    def test_drop_then_reclimb_rearms(self):
        p1 = self._transcript(45, "a.jsonl")
        self.assertIsNotNone(growth_nudge_for_turn(p1, "sess", self.state))
        p2 = self._transcript(20, "b.jsonl")  # /compact
        self.assertIsNone(growth_nudge_for_turn(p2, "sess", self.state))
        p3 = self._transcript(45, "c.jsonl")  # re-climb
        self.assertIsNotNone(growth_nudge_for_turn(p3, "sess", self.state),
                             "re-armed band must nudge again")

    def test_state_isolated_per_session(self):
        # Session A warns; session B starts fresh and also warns.
        a = self._transcript(45, "a.jsonl")
        b = self._transcript(45, "b.jsonl")
        self.assertIsNotNone(growth_nudge_for_turn(a, "A", self.state))
        self.assertIsNotNone(growth_nudge_for_turn(b, "B", self.state))

    def test_missing_transcript_returns_none(self):
        self.assertIsNone(
            growth_nudge_for_turn(self.base / "nope.jsonl", "s", self.state)
        )

    def test_never_raises_on_bad_state_dir(self):
        # state_dir under a path component that is a file → write fails;
        # helper must still return the nudge (write is best-effort) and
        # never raise.
        blocker = self.base / "afile"
        blocker.write_text("x")
        bad_state = blocker / "subdir"  # parent is a file
        path = self._transcript(45)
        # Should not raise; returns the nudge (state just isn't persisted).
        out = growth_nudge_for_turn(path, "s", bad_state)
        self.assertIsNotNone(out)


# --------------------------------------------------------------------------
# Slice 057-02 — active-compaction trigger. The compaction band rides the
# SAME band machinery as the 055-02 warn bands (no duplicate state); only the
# message differs. Pure-function surface: DEFAULT_COMPACT_THRESHOLD,
# _resolve_compact_threshold(), compaction_nudge_text(), and the message
# selection in growth_nudge_for_turn().
# --------------------------------------------------------------------------


class CompactThresholdDefaultsTests(unittest.TestCase):
    """057-02 — the compaction band defaults to 0.75, above the warn bands,
    overridable via JIG_CONTEXT_COMPACT_PCT with the same out-of-range silent
    fallback as the other PCT knobs."""

    def setUp(self):
        self._saved = os.environ.pop("JIG_CONTEXT_COMPACT_PCT", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("JIG_CONTEXT_COMPACT_PCT", None)
        else:
            os.environ["JIG_CONTEXT_COMPACT_PCT"] = self._saved

    def test_default_compact_threshold_is_75_percent(self):
        self.assertEqual(DEFAULT_COMPACT_THRESHOLD, 0.75)

    def test_compact_band_is_above_warn_bands(self):
        """The compaction band must sit above the 40/60 warn bands so it is a
        distinct higher escalation (AC #2)."""
        self.assertGreater(DEFAULT_COMPACT_THRESHOLD, max(GROWTH_BANDS[:2]))

    def test_default_when_env_unset(self):
        os.environ.pop("JIG_CONTEXT_COMPACT_PCT", None)
        self.assertEqual(_resolve_compact_threshold(), DEFAULT_COMPACT_THRESHOLD)

    def test_valid_env_override(self):
        os.environ["JIG_CONTEXT_COMPACT_PCT"] = "0.90"
        self.assertEqual(_resolve_compact_threshold(), 0.90)

    def test_out_of_range_env_falls_back(self):
        os.environ["JIG_CONTEXT_COMPACT_PCT"] = "75"  # percent, not fraction
        self.assertEqual(_resolve_compact_threshold(), DEFAULT_COMPACT_THRESHOLD)

    def test_non_numeric_env_falls_back(self):
        os.environ["JIG_CONTEXT_COMPACT_PCT"] = "lots"
        self.assertEqual(_resolve_compact_threshold(), DEFAULT_COMPACT_THRESHOLD)


class CompactionNudgeTextTests(unittest.TestCase):
    """057-02 AC #1 — the compaction body is actionable (compact OR hand off)
    and names a concrete carry-over (spec path, current slice, open threads).
    Distinct from the warn message (AC #2)."""

    def test_text_is_actionable_compact_or_handoff(self):
        text = compaction_nudge_text(0.75, 0.78)
        self.assertIn("/compact", text)
        self.assertIn("hand off", text.lower())

    def test_text_names_concrete_carry_over(self):
        text = compaction_nudge_text(0.75, 0.78)
        lower = text.lower()
        self.assertIn("carry over", lower)
        self.assertIn("spec path", lower)
        self.assertIn("slice", lower)
        self.assertIn("open thread", lower)

    def test_text_references_workflow_section(self):
        text = compaction_nudge_text(0.75, 0.78)
        self.assertIn("Context-cost discipline", text)
        self.assertIn("docs/workflow.md", text)

    def test_text_is_distinct_from_warn_message(self):
        """AC #2 — the compaction message must not read as the plain growth
        warn nudge."""
        compaction = compaction_nudge_text(0.75, 0.78)
        warn = growth_nudge_text(0.40, 0.45)
        self.assertNotEqual(compaction, warn)
        self.assertNotIn("Active-compaction", warn)
        self.assertNotIn("carry over", warn.lower())


class CompactionGrowthForTurnTests(unittest.TestCase):
    """057-02 — message selection in growth_nudge_for_turn: below the
    compaction band → warn message; at/above → the actionable compaction
    message; reuses the once-per-band + re-arm-on-drop machinery (AC #3)."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="jig-compact-turn-"))
        self.state = self.base / "state"
        self.state.mkdir()
        # 100-token window: tokens map directly to percent.
        os.environ["JIG_CONTEXT_WINDOW_BYTES"] = str(100 * RATIO)
        os.environ.pop("JIG_CONTEXT_GROWTH_WARN_PCT", None)
        os.environ.pop("JIG_CONTEXT_COMPACT_PCT", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)
        os.environ.pop("JIG_CONTEXT_WINDOW_BYTES", None)
        os.environ.pop("JIG_CONTEXT_COMPACT_PCT", None)

    def _transcript(self, value, name="t.jsonl"):
        import json as _json
        path = self.base / name
        rec = {"type": "assistant",
               "message": {"usage": {"cache_read_input_tokens": value}}}
        path.write_text(_json.dumps(rec) + "\n")
        return path

    def test_warn_band_emits_warn_message_not_compaction(self):
        # 45% → 0.40 warn band, below the 0.75 compaction band.
        out = growth_nudge_for_turn(self._transcript(45), "s", self.state)
        self.assertIsNotNone(out)
        self.assertNotIn("Active-compaction", out)
        self.assertIn("Context-growth", out)

    def test_compaction_band_emits_compaction_message(self):
        # 78% → crosses the 0.75 compaction band.
        out = growth_nudge_for_turn(self._transcript(78), "s", self.state)
        self.assertIsNotNone(out)
        self.assertIn("Active-compaction", out)
        self.assertIn("carry over", out.lower())

    def test_compaction_band_fires_once(self):
        # First crossing nudges; staying above does not re-fire.
        first = growth_nudge_for_turn(self._transcript(78, "a.jsonl"), "sess", self.state)
        self.assertIn("Active-compaction", first)
        second = growth_nudge_for_turn(self._transcript(79, "b.jsonl"), "sess", self.state)
        self.assertIsNone(second, "staying above the band must not re-fire")

    def test_drop_then_recross_rearms_compaction(self):
        first = growth_nudge_for_turn(self._transcript(78, "a.jsonl"), "sess", self.state)
        self.assertIn("Active-compaction", first)
        # Drop below the compaction band (after a /compact) — silent re-arm.
        growth_nudge_for_turn(self._transcript(50, "b.jsonl"), "sess", self.state)
        # Re-cross → compaction message fires again.
        reclimb = growth_nudge_for_turn(self._transcript(78, "c.jsonl"), "sess", self.state)
        self.assertIsNotNone(reclimb)
        self.assertIn("Active-compaction", reclimb)

    def test_env_override_changes_compaction_band(self):
        os.environ["JIG_CONTEXT_COMPACT_PCT"] = "0.90"
        # 78% is now below the 0.90 compaction band but above 0.60 → warn msg.
        out = growth_nudge_for_turn(self._transcript(78), "s", self.state)
        self.assertIsNotNone(out)
        self.assertNotIn("Active-compaction", out)


# --------------------------------------------------------------------------
# Slice 055-03 — read-once / read-lean discipline. Pure-function surface:
# evaluate_read() (the duplicate-path + large-whole-file decision),
# read_nudge_for_turn() (the hook's orchestration: state read → evaluate →
# persist), and the two nudge-text builders. The PreToolUse(Read) hook owns
# only the state-file I/O; these cover the testable policy it delegates to.
# Read is the single biggest context source (~26%); e.g. spec.md was re-read
# 42× in the "$540 session" (spec 008's quizzical-moore worktree).
# --------------------------------------------------------------------------


class ReadLeanDefaultsTests(unittest.TestCase):
    """AC #3 — the read-lean byte threshold has a sensible default (64 KiB),
    overridable via JIG_READ_LEAN_BYTES, with the same out-of-range /
    non-numeric silent fallback as the other env knobs (slice 055-03
    reconciliation: pin the value + exercise the fallback branch directly)."""

    def setUp(self):
        self._saved = os.environ.pop("JIG_READ_LEAN_BYTES", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("JIG_READ_LEAN_BYTES", None)
        else:
            os.environ["JIG_READ_LEAN_BYTES"] = self._saved

    def test_default_read_lean_bytes_is_64_kib(self):
        self.assertEqual(DEFAULT_READ_LEAN_BYTES, 64 * 1024)

    def test_default_when_env_unset(self):
        os.environ.pop("JIG_READ_LEAN_BYTES", None)
        self.assertEqual(_resolve_read_lean_bytes(), DEFAULT_READ_LEAN_BYTES)

    def test_valid_env_override(self):
        os.environ["JIG_READ_LEAN_BYTES"] = "100000"
        self.assertEqual(_resolve_read_lean_bytes(), 100000)

    def test_out_of_range_env_falls_back_to_default(self):
        os.environ["JIG_READ_LEAN_BYTES"] = "-5"
        self.assertEqual(_resolve_read_lean_bytes(), DEFAULT_READ_LEAN_BYTES)

    def test_non_numeric_env_falls_back_to_default(self):
        os.environ["JIG_READ_LEAN_BYTES"] = "lots"
        self.assertEqual(_resolve_read_lean_bytes(), DEFAULT_READ_LEAN_BYTES)


class EvaluateReadDuplicateTests(unittest.TestCase):
    """AC #2 — evaluate_read flags a path Read more than once per session,
    at most once per path. Pure: takes the prior (seen, nudged) sets and
    returns {nudge, kind, text, seen_paths, nudged_paths} (the next state).
    """

    def test_first_read_is_silent(self):
        d = evaluate_read("/a/b.py", {"file_path": "/a/b.py"}, [], [])
        self.assertFalse(d["nudge"])
        # Path now recorded as seen, not yet nudged.
        self.assertIn("/a/b.py", d["seen_paths"])
        self.assertNotIn("/a/b.py", d["nudged_paths"])

    def test_second_read_same_path_nudges_once(self):
        # Path already seen on a prior turn → the second read nudges.
        d = evaluate_read("/a/b.py", {"file_path": "/a/b.py"},
                          ["/a/b.py"], [])
        self.assertTrue(d["nudge"])
        self.assertEqual(d["kind"], "duplicate")
        self.assertIn("/a/b.py", d["nudged_paths"])

    def test_third_read_same_path_is_silent(self):
        # Already seen AND already nudged → silent (at most once per path).
        d = evaluate_read("/a/b.py", {"file_path": "/a/b.py"},
                          ["/a/b.py"], ["/a/b.py"])
        self.assertFalse(d["nudge"])
        # Still recorded as nudged so further reads stay silent.
        self.assertIn("/a/b.py", d["nudged_paths"])

    def test_distinct_paths_are_silent(self):
        d = evaluate_read("/a/c.py", {"file_path": "/a/c.py"},
                          ["/a/b.py"], [])
        self.assertFalse(d["nudge"])
        self.assertIn("/a/c.py", d["seen_paths"])
        self.assertIn("/a/b.py", d["seen_paths"])

    def test_missing_file_path_is_silent(self):
        d = evaluate_read("", {}, [], [])
        self.assertFalse(d["nudge"])
        # No path → state unchanged.
        self.assertEqual(d["seen_paths"], [])

    def test_duplicate_text_names_the_path(self):
        d = evaluate_read("/a/b.py", {"file_path": "/a/b.py"},
                          ["/a/b.py"], [])
        self.assertIn("/a/b.py", d["text"])


class EvaluateReadLargeWholeFileTests(unittest.TestCase):
    """AC #3 — evaluate_read nudges on a whole-file Read (no offset/limit)
    of a file above the size threshold, suggesting offset/limit. A ranged
    Read (offset or limit present) is silent regardless of size."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-readlean-")
        self.root = Path(self.tmpdir)
        os.environ["JIG_READ_LEAN_BYTES"] = "100"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        os.environ.pop("JIG_READ_LEAN_BYTES", None)

    def _bigfile(self, name="big.py", size=500):
        path = self.root / name
        path.write_text("x" * size)
        return path

    def test_large_whole_file_read_nudges(self):
        path = self._bigfile()
        d = evaluate_read(str(path), {"file_path": str(path)}, [], [])
        self.assertTrue(d["nudge"])
        self.assertEqual(d["kind"], "large")
        # AC #3: the nudge suggests offset/limit.
        self.assertIn("offset", d["text"])
        self.assertIn("limit", d["text"])

    def test_ranged_read_is_silent_even_if_large(self):
        path = self._bigfile()
        d = evaluate_read(
            str(path),
            {"file_path": str(path), "offset": 1, "limit": 50},
            [], [],
        )
        self.assertFalse(d["nudge"])

    def test_limit_only_read_is_silent(self):
        path = self._bigfile()
        d = evaluate_read(
            str(path), {"file_path": str(path), "limit": 50}, [], [],
        )
        self.assertFalse(d["nudge"])

    def test_small_whole_file_read_is_silent(self):
        small = self.root / "small.py"
        small.write_text("x" * 10)  # below the 100-byte threshold
        d = evaluate_read(str(small), {"file_path": str(small)}, [], [])
        self.assertFalse(d["nudge"])

    def test_duplicate_takes_priority_over_large(self):
        """A second read of a large file fires the duplicate nudge (the
        in-context copy is the stronger advice), not the large-read one."""
        path = self._bigfile()
        d = evaluate_read(str(path), {"file_path": str(path)},
                          [str(path)], [])
        self.assertTrue(d["nudge"])
        self.assertEqual(d["kind"], "duplicate")

    def test_unreadable_path_does_not_crash(self):
        d = evaluate_read("/no/such/file.py",
                          {"file_path": "/no/such/file.py"}, [], [])
        # Can't stat → treat as not-large → silent first read.
        self.assertFalse(d["nudge"])


class ReadNudgeTextTests(unittest.TestCase):
    """AC #4 — both nudge bodies cite the motivating evidence (the 42×
    spec.md re-read in the "$540 session") and point at the workflow.md
    Context-cost discipline section."""

    def test_duplicate_text_cites_evidence_and_workflow(self):
        text = duplicate_read_nudge_text("/x/spec.md")
        self.assertIn("42", text)  # the 42× re-read
        self.assertIn("Context-cost discipline", text)
        self.assertIn("docs/workflow.md", text)

    def test_large_text_suggests_offset_limit_and_workflow(self):
        text = large_read_nudge_text("/x/big.py", 123456)
        self.assertIn("offset", text)
        self.assertIn("limit", text)
        self.assertIn("Context-cost discipline", text)


class ReadNudgeForTurnTests(unittest.TestCase):
    """The hook's orchestration helper: state read → evaluate → persist.
    Pins at-most-once-per-path across calls via a real per-session state
    dir, matching what the shell calls (slice 055-03)."""

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="jig-read-turn-"))
        self.state = self.base / "state"
        self.state.mkdir()
        os.environ.pop("JIG_READ_LEAN_BYTES", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.base, ignore_errors=True)
        os.environ.pop("JIG_READ_LEAN_BYTES", None)

    def test_first_read_returns_none(self):
        self.assertIsNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                "s", self.state)
        )

    def test_second_read_same_path_returns_text(self):
        self.assertIsNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                "sess", self.state)
        )
        out = read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                  "sess", self.state)
        self.assertIsNotNone(out)
        self.assertIn("/a/b.py", out)

    def test_third_read_same_path_returns_none(self):
        for _ in range(2):
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                "sess", self.state)
        # Third read: already nudged → silent.
        self.assertIsNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                "sess", self.state)
        )

    def test_distinct_paths_return_none(self):
        self.assertIsNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                "sess", self.state)
        )
        self.assertIsNone(
            read_nudge_for_turn("/a/c.py", {"file_path": "/a/c.py"},
                                "sess", self.state)
        )

    def test_state_isolated_per_session(self):
        # Session A sees /a/b.py twice (nudge on 2nd); session B's first
        # read of the same path is silent (independent state).
        read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"}, "A", self.state)
        self.assertIsNotNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"}, "A", self.state)
        )
        self.assertIsNone(
            read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"}, "B", self.state)
        )

    def test_missing_file_path_returns_none(self):
        self.assertIsNone(
            read_nudge_for_turn("", {}, "s", self.state)
        )

    def test_never_raises_on_bad_state_dir(self):
        # state_dir under a file → write fails; helper must still return the
        # nudge on the duplicate and never raise (write is best-effort).
        blocker = self.base / "afile"
        blocker.write_text("x")
        bad_state = blocker / "subdir"
        # First read can't persist, so the second read also can't see it →
        # it stays silent, but crucially nothing raises.
        out1 = read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                   "s", bad_state)
        self.assertIsNone(out1)
        out2 = read_nudge_for_turn("/a/b.py", {"file_path": "/a/b.py"},
                                   "s", bad_state)
        # No exception is the contract; with no persistence it stays silent.
        self.assertIsNone(out2)


if __name__ == "__main__":
    unittest.main()
