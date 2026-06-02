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
    estimate,
    DEFAULT_WINDOW_BYTES,
    DEFAULT_THRESHOLD,
    RATIO,
    DEFAULT_GROWTH_THRESHOLD,
    GROWTH_BANDS,
    token_window,
    read_tail_cache_read_tokens,
    evaluate_growth,
    growth_nudge_for_turn,
    growth_nudge_text,
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
        import io
        import contextlib
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


if __name__ == "__main__":
    unittest.main()
