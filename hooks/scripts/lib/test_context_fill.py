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
from context_fill import estimate, DEFAULT_WINDOW_BYTES, DEFAULT_THRESHOLD, RATIO


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


if __name__ == "__main__":
    unittest.main()
