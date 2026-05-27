"""
Tests for the tdd-loop test-quality preflight (quality.py).

Run from the repo root:
    python3 -m unittest discover -s skills/tdd-loop -p 'test_quality.py'

Coverage matrix (per spec 043-01):
    - ClassifyPathTests / ApplicabilityTests / CountingTests / SignalTests:
      original smoke suite — path classification + applicable gating +
      basic counting + assertion-thin gate.
    - PerFileFloodSignalTests (AC1): both the max-per-file and the
      tests-per-code-file ratio paths into per-file-flood, with
      threshold-minus-one negatives.
    - MockHeavySignalTests (AC2): mock-density threshold crossing plus
      the min-test-count gate.
    - ParametrizeWalkerTests (AC3): trailing comma, nested tuples,
      string-with-comma, 80-line-lookahead boundary.
    - PytestRaisesAssertionTests (AC4): both `pytest.raises(X)` and
      `with pytest.raises(X):` forms.
    - MalformedDiffTests (AC5): binary headers, pure renames, mode-only
      changes — parse without crashing, contribute zero to counters.
    - YamlShapeTests (AC6): schema-version, applicable, signal keys,
      metrics key ordering — parsed with a minimal stdlib walker since
      PyYAML is off-limits.
    - AgainstRefTests (AC7): `--against HEAD` in a tmp git repo matches
      the `--diff-file` snapshot.
"""

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
QUALITY_PY = REPO_ROOT / "skills" / "tdd-loop" / "quality.py"


def _load_quality():
    spec = importlib.util.spec_from_file_location("quality", QUALITY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_quality_with_diff(diff_text: str) -> subprocess.CompletedProcess:
    """Write `diff_text` to a tmp file, invoke quality.py --diff-file, return result."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".diff", delete=False, encoding="utf-8",
    ) as fh:
        fh.write(diff_text)
        path = fh.name
    try:
        return subprocess.run(
            [sys.executable, str(QUALITY_PY), "--diff-file", path],
            capture_output=True, text=True,
        )
    finally:
        os.unlink(path)


# -------------------- Path classification --------------------


class ClassifyPathTests(unittest.TestCase):
    """Path classifier picks the right kind for Python test conventions."""

    def setUp(self):
        self.mod = _load_quality()

    def test_test_underscore_prefix(self):
        self.assertEqual(self.mod.classify_path("tests/test_foo.py"), "test")

    def test_underscore_test_suffix(self):
        self.assertEqual(self.mod.classify_path("pkg/foo_test.py"), "test")

    def test_under_tests_dir(self):
        self.assertEqual(self.mod.classify_path("tests/helpers.py"), "test")

    def test_plain_python_source(self):
        self.assertEqual(self.mod.classify_path("pkg/foo.py"), "code")

    def test_markdown_docs(self):
        self.assertEqual(self.mod.classify_path("README.md"), "other")

    def test_under_docs_dir(self):
        self.assertEqual(self.mod.classify_path("docs/foo.md"), "other")

    def test_non_python_source(self):
        self.assertEqual(self.mod.classify_path("static/style.css"), "other")


# -------------------- Applicable / not-applicable --------------------


class ApplicabilityTests(unittest.TestCase):

    def test_empty_diff_not_applicable(self):
        result = run_quality_with_diff("")
        self.assertEqual(result.returncode, 0)
        self.assertIn("applicable: false", result.stdout)
        self.assertIn("empty-or-unreadable-diff", result.stdout)

    def test_docs_only_not_applicable(self):
        diff = """\
diff --git a/README.md b/README.md
index 0000..1111 100644
--- a/README.md
+++ b/README.md
@@ -1,1 +1,1 @@
-old
+new
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0)
        self.assertIn("applicable: false", result.stdout)
        self.assertIn("docs-only", result.stdout)


# -------------------- Test + assertion counting --------------------


class CountingTests(unittest.TestCase):

    def test_counts_pytest_function_and_assertion(self):
        diff = """\
diff --git a/tests/test_foo.py b/tests/test_foo.py
index 0000..1111 100644
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -0,0 +1,5 @@
+def test_alpha():
+    x = 1 + 1
+    assert x == 2
+
+def test_beta():
+    assert True
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applicable: true", result.stdout)
        self.assertIn("new-it-blocks: 2", result.stdout)
        self.assertIn("new-assertions: 2", result.stdout)
        self.assertIn("new-mocks: 0", result.stdout)

    def test_counts_unittest_assert_methods(self):
        diff = """\
diff --git a/tests/test_bar.py b/tests/test_bar.py
index 0000..1111 100644
--- a/tests/test_bar.py
+++ b/tests/test_bar.py
@@ -0,0 +1,5 @@
+class TestBar(unittest.TestCase):
+    def test_alpha(self):
+        self.assertEqual(1, 1)
+        self.assertTrue(True)
+        self.assertIn("a", "abc")
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new-it-blocks: 1", result.stdout)
        self.assertIn("new-assertions: 3", result.stdout)

    def test_counts_parametrize_cases(self):
        diff = """\
diff --git a/tests/test_p.py b/tests/test_p.py
index 0000..1111 100644
--- a/tests/test_p.py
+++ b/tests/test_p.py
@@ -0,0 +1,7 @@
+@pytest.mark.parametrize("x,y", [
+    (1, 2),
+    (3, 4),
+    (5, 6),
+])
+def test_pair(x, y):
+    assert x + 1 == y or x + 1 != y
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Three cases under the decorator — should expand from 1 def to 3.
        self.assertIn("new-it-blocks: 3", result.stdout)

    def test_counts_unittest_mock_patterns(self):
        diff = """\
diff --git a/tests/test_m.py b/tests/test_m.py
index 0000..1111 100644
--- a/tests/test_m.py
+++ b/tests/test_m.py
@@ -0,0 +1,5 @@
+def test_with_mock():
+    m = MagicMock()
+    with patch.object(foo, "bar") as p:
+        m.return_value = 1
+    assert True
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        # MagicMock( and patch.object( both count.
        self.assertIn("new-mocks: 2", result.stdout)


# -------------------- Signal firing --------------------


class SignalTests(unittest.TestCase):
    """Minimum-test-count gates suppress signals on tiny diffs; threshold
    crossings fire signals as designed."""

    def test_assertion_thin_requires_min_tests(self):
        # 10 tests, 9 assertions → density 0.9, below the 1.0 threshold,
        # BUT under the 20-test minimum so the signal stays quiet. Picked
        # to couple to BOTH gates: a future regression that drops the
        # threshold to 0.5 would still find this test passing only
        # because of the min-test gate, not because of either-gate-only.
        chunks = []
        for i in range(10):
            chunks.append(f"+def test_{i}():\n")
            if i < 9:
                chunks.append("+    assert True\n")
            else:
                chunks.append("+    pass\n")
            chunks.append("+\n")
        body = "".join(chunks)
        diff = f"""\
diff --git a/tests/test_thin.py b/tests/test_thin.py
index 0000..1111 100644
--- a/tests/test_thin.py
+++ b/tests/test_thin.py
@@ -0,0 +1,30 @@
{body}"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("assertion-thin: false", result.stdout)

    def test_assertion_thin_fires_at_threshold(self):
        # 25 tests, ~22 assertions → density 0.88, below the 1.0
        # threshold; > 20 tests so the signal fires. (Three tests have
        # no assertion — the case the threshold is meant to catch.)
        chunks = []
        for i in range(25):
            chunks.append(f"+def test_{i}():\n")
            if i < 22:
                chunks.append("+    assert True\n")
            else:
                chunks.append("+    pass\n")
            chunks.append("+\n")
        body = "".join(chunks)
        diff = f"""\
diff --git a/tests/test_thin.py b/tests/test_thin.py
index 0000..1111 100644
--- a/tests/test_thin.py
+++ b/tests/test_thin.py
@@ -0,0 +1,75 @@
{body}"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("assertion-thin: true", result.stdout)


# -------------------- AC1: per-file-flood signal --------------------


def _diff_with_n_test_functions(path: str, n: int, hunk_size: int = None) -> str:
    """Build a unified diff that adds `n` pytest test functions to `path`."""
    body = "".join(
        f"+def test_f{i}():\n+    assert True\n+\n" for i in range(n)
    )
    size = hunk_size if hunk_size is not None else (3 * n)
    return (
        f"diff --git a/{path} b/{path}\n"
        f"index 0000..1111 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{size} @@\n"
        f"{body}"
    )


def _diff_add_code_file(path: str, lines: int = 5) -> str:
    body = "".join(f"+x = {i}\n" for i in range(lines))
    return (
        f"diff --git a/{path} b/{path}\n"
        f"index 0000..1111 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{lines} @@\n"
        f"{body}"
    )


class PerFileFloodSignalTests(unittest.TestCase):
    """AC1: per-file-flood fires on >100 tests in one file OR
    tests-per-new-code-file ratio above 50."""

    def test_max_per_file_over_100_fires(self):
        diff = _diff_with_n_test_functions("tests/test_flood.py", 101)
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("per-file-flood: true", result.stdout)

    def test_max_per_file_at_100_quiet(self):
        # Threshold is strictly > 100. Exactly 100 should NOT fire.
        diff = _diff_with_n_test_functions("tests/test_flood.py", 100)
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("per-file-flood: false", result.stdout)

    def test_ratio_51_over_1_code_fires(self):
        # 51 tests for 1 new code file → ratio 51 > 50 threshold.
        diff = (
            _diff_with_n_test_functions("tests/test_ratio.py", 51)
            + _diff_add_code_file("pkg/mod.py", lines=5)
        )
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("per-file-flood: true", result.stdout)
        # Disambiguate the branch: max-it-per-file is 51, well below the
        # 100 max-per-file threshold, so the signal must have fired via
        # the tests-per-new-code-file ratio path.
        self.assertIn("max-it-per-file: 51", result.stdout)

    def test_ratio_50_over_1_code_quiet(self):
        # 50 tests for 1 new code file → ratio 50 == threshold (strictly >).
        diff = (
            _diff_with_n_test_functions("tests/test_ratio.py", 50)
            + _diff_add_code_file("pkg/mod.py", lines=5)
        )
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("per-file-flood: false", result.stdout)


# -------------------- AC2: mock-heavy signal --------------------


class MockHeavySignalTests(unittest.TestCase):
    """AC2: mock-heavy fires when mock-density > 5.0 AND new-tests >= 10."""

    def _mock_heavy_diff(self, n_tests: int, mocks_per_test: int = 6) -> str:
        # Each test function body has `mocks_per_test` MagicMock() calls.
        chunks = []
        for i in range(n_tests):
            chunks.append(f"+def test_m{i}():\n")
            for j in range(mocks_per_test):
                chunks.append(f"+    m{j} = MagicMock()\n")
            chunks.append("+    assert True\n+\n")
        body = "".join(chunks)
        size = (3 + mocks_per_test) * n_tests
        return (
            "diff --git a/tests/test_mocks.py b/tests/test_mocks.py\n"
            "index 0000..1111 100644\n"
            "--- a/tests/test_mocks.py\n"
            "+++ b/tests/test_mocks.py\n"
            f"@@ -0,0 +1,{size} @@\n"
            f"{body}"
        )

    def test_mock_heavy_fires_above_threshold(self):
        # 10 tests, 6 mocks each → density 6.0 > 5.0, AND >= 10 tests.
        diff = self._mock_heavy_diff(10, mocks_per_test=6)
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mock-heavy: true", result.stdout)

    def test_mock_heavy_silenced_by_min_test_gate(self):
        # 9 tests, 6 mocks each → same density 6.0, but < 10 tests so
        # the gate suppresses the signal.
        diff = self._mock_heavy_diff(9, mocks_per_test=6)
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mock-heavy: false", result.stdout)


# -------------------- AC3: parametrize walker edge cases --------------------


class ParametrizeWalkerTests(unittest.TestCase):
    """AC3: count_parametrize_cases handles non-trivial argvalues."""

    def setUp(self):
        self.mod = _load_quality()

    def _count_from_lines(self, source_lines):
        """Given a list of source lines (no leading +), build the
        added-lines list the walker expects and call it. The decorator
        is at index 0."""
        added = ["+" + line for line in source_lines]
        return self.mod.count_parametrize_cases(added, 0)

    def test_trailing_comma_after_last_case(self):
        # Trailing comma after last tuple should NOT inflate the count.
        lines = [
            '@pytest.mark.parametrize("x,y", [',
            "    (1, 2),",
            "    (3, 4),",
            "    (5, 6),",
            "])",
        ]
        self.assertEqual(self._count_from_lines(lines), 3)

    def test_nested_tuples(self):
        # Nested tuples — inner commas at depth > 1 must not count.
        lines = [
            '@pytest.mark.parametrize("x,y", [',
            "    (1, (2, 3)),",
            "    (4, (5, 6)),",
            "])",
        ]
        self.assertEqual(self._count_from_lines(lines), 2)

    def test_string_literal_with_comma(self):
        # Comma inside a string literal must not count as a separator.
        lines = [
            '@pytest.mark.parametrize("s,n", [',
            '    ("a,b", 1),',
            '    ("c", 2),',
            "])",
        ]
        self.assertEqual(self._count_from_lines(lines), 2)

    def test_eighty_line_lookahead_boundary(self):
        # Argvalues longer than the 80-line lookahead window should not
        # crash — the walker returns a sensible value (>= 1). The current
        # implementation effectively truncates at the lookahead, but the
        # AC only requires a non-crashing fallback.
        lines = ['@pytest.mark.parametrize("x", [']
        for i in range(200):
            lines.append(f"    ({i},),")
        lines.append("])")
        # Should not raise.
        cases = self._count_from_lines(lines)
        # Sensible fallback: counts at least *some* of the cases that fit
        # within the lookahead window (not just the no-decorator fallback
        # of 1), and stays at or below the total number of declared cases.
        # The 80-line lookahead covers ~78 case lines plus the opening
        # bracket and a slack line.
        self.assertGreater(cases, 1)
        self.assertLessEqual(cases, 200)


# -------------------- AC4: pytest.raises as assertions --------------------


class PytestRaisesAssertionTests(unittest.TestCase):
    """AC4: both `pytest.raises(X)` and `with pytest.raises(X):` increment
    new-assertions."""

    def test_bare_pytest_raises_counts(self):
        diff = """\
diff --git a/tests/test_r.py b/tests/test_r.py
index 0000..1111 100644
--- a/tests/test_r.py
+++ b/tests/test_r.py
@@ -0,0 +1,3 @@
+def test_bare():
+    pytest.raises(ValueError, lambda: int("x"))
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new-assertions: 1", result.stdout)

    def test_with_pytest_raises_counts(self):
        diff = """\
diff --git a/tests/test_r.py b/tests/test_r.py
index 0000..1111 100644
--- a/tests/test_r.py
+++ b/tests/test_r.py
@@ -0,0 +1,4 @@
+def test_with_form():
+    with pytest.raises(ValueError):
+        int("x")
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new-assertions: 1", result.stdout)


# -------------------- AC5: malformed diff variants --------------------


class MalformedDiffTests(unittest.TestCase):
    """AC5: binary headers, pure renames, and mode-only changes parse
    without exception and contribute zero to test/code counters."""

    def test_binary_file_header_no_crash(self):
        # Binary diff should classify the file as 'other' and produce a
        # not-applicable result (no test/code changes), no exception.
        diff = """\
diff --git a/assets/logo.png b/assets/logo.png
index 0000..1111 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applicable: false", result.stdout)

    def test_pure_rename_no_crash(self):
        # Pure rename: no +/- content lines. Should not crash.
        diff = """\
diff --git a/pkg/old_name.py b/pkg/new_name.py
similarity index 100%
rename from pkg/old_name.py
rename to pkg/new_name.py
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Pure rename has no +/- content lines, so the file is reclassified
        # as 'other' and the diff becomes not-applicable.
        self.assertIn("applicable: false", result.stdout)

    def test_mode_only_change_no_crash(self):
        # Mode-only change: only mode metadata, no content lines.
        diff = """\
diff --git a/scripts/run.sh b/scripts/run.sh
old mode 100644
new mode 100755
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applicable: false", result.stdout)

    def test_mixed_binary_and_real_test_diff(self):
        # A real test file added alongside a binary asset — binary entry
        # should contribute zero, real test entry should drive counters.
        binary = """\
diff --git a/assets/logo.png b/assets/logo.png
index 0000..1111 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""
        real = """\
diff --git a/tests/test_real.py b/tests/test_real.py
index 0000..1111 100644
--- a/tests/test_real.py
+++ b/tests/test_real.py
@@ -0,0 +1,3 @@
+def test_alpha():
+    assert True
"""
        result = run_quality_with_diff(binary + real)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applicable: true", result.stdout)
        self.assertIn("new-it-blocks: 1", result.stdout)
        # The binary file should NOT count as a test or code file.
        self.assertIn("new-test-files: 1", result.stdout)
        self.assertIn("new-code-files: 0", result.stdout)


# -------------------- AC6: YAML shape --------------------


def _parse_minimal_yaml(text: str):
    """Parse the quality.py YAML emission into a nested-dict structure
    plus a list of (key, path-tuple) entries preserving emission order.

    Stdlib-only: a small regex walk is sufficient because quality.py's
    output is a fixed two/three-level tree with no list-of-dicts. The
    path-tuple lets callers ask for the keys of a specific subtree in
    emission order (e.g. just `metrics`, not `signals`).

    Returns (tree, ordered_entries) where each entry is (key, path)
    and `path` is the tuple of ancestor keys (root key first).
    """
    tree = {}
    ordered_entries = []
    # Stack of (container, indent, path-to-container).
    stack = [(tree, -1, ())]
    line_re = re.compile(r"^(\s*)([A-Za-z0-9_-]+):\s*(.*)$")
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = line_re.match(raw)
        if not m:
            continue
        indent = len(m.group(1))
        key = m.group(2)
        value = m.group(3)
        # Pop stack to the right parent.
        while stack and stack[-1][1] >= indent:
            stack.pop()
        parent, _, parent_path = stack[-1]
        ordered_entries.append((key, parent_path))
        if value == "":
            child = {}
            parent[key] = child
            stack.append((child, indent, parent_path + (key,)))
        else:
            # Strip surrounding double-quotes if present.
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            parent[key] = value
    return tree, ordered_entries


class YamlShapeTests(unittest.TestCase):
    """AC6: emitted YAML has the right schema-version, signals, and
    metrics-key ordering."""

    def test_yaml_schema_version_and_applicable(self):
        diff = """\
diff --git a/tests/test_y.py b/tests/test_y.py
index 0000..1111 100644
--- a/tests/test_y.py
+++ b/tests/test_y.py
@@ -0,0 +1,3 @@
+def test_alpha():
+    assert True
"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        tree, _ = _parse_minimal_yaml(result.stdout)
        self.assertIn("test-quality-snapshot", tree)
        snap = tree["test-quality-snapshot"]
        self.assertEqual(snap["schema-version"], "1")
        self.assertEqual(snap["applicable"], "true")

    def test_yaml_signals_keys_present(self):
        diff = """\
diff --git a/tests/test_y.py b/tests/test_y.py
index 0000..1111 100644
--- a/tests/test_y.py
+++ b/tests/test_y.py
@@ -0,0 +1,3 @@
+def test_alpha():
+    assert True
"""
        result = run_quality_with_diff(diff)
        tree, _ = _parse_minimal_yaml(result.stdout)
        signals = tree["test-quality-snapshot"]["signals"]
        for key in ("per-file-flood", "assertion-thin", "mock-heavy"):
            self.assertIn(key, signals, f"missing signal key {key!r}")
            self.assertIn(signals[key], ("true", "false"))

    def test_yaml_metrics_key_order(self):
        diff = """\
diff --git a/tests/test_y.py b/tests/test_y.py
index 0000..1111 100644
--- a/tests/test_y.py
+++ b/tests/test_y.py
@@ -0,0 +1,4 @@
+def test_alpha():
+    m = MagicMock()
+    assert True
"""
        # Also include a code file so test-to-code-ratio shows up.
        code = _diff_add_code_file("pkg/mod.py", lines=3)
        result = run_quality_with_diff(diff + code)
        self.assertEqual(result.returncode, 0, result.stderr)
        _, ordered = _parse_minimal_yaml(result.stdout)
        # Filter to keys whose parent path is (snapshot, metrics).
        metrics_path = ("test-quality-snapshot", "metrics")
        metric_keys = [k for k, path in ordered if path == metrics_path]
        # The declared order in quality.py emit_yaml.
        declared = [
            "new-test-files", "new-code-files", "new-test-loc", "new-code-loc",
            "new-it-blocks", "removed-it-blocks", "net-it-blocks",
            "new-assertions", "new-mocks",
            "max-it-per-file", "largest-test-file",
            "assertion-density", "mock-density", "test-to-code-ratio",
        ]
        # Keep only the subset of declared keys that actually appear in
        # this run's output, in their declared order.
        expected = [k for k in declared if k in metric_keys]
        self.assertEqual(metric_keys, expected)


# -------------------- AC7: --against ref code path --------------------


class AgainstRefTests(unittest.TestCase):
    """AC7: `--against HEAD` inside a tmp git repo produces the same
    snapshot as a `--diff-file` invocation against the equivalent diff."""

    def _run_git(self, cwd, *args):
        return subprocess.run(
            ["git", *args],
            cwd=cwd, capture_output=True, text=True, check=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
            },
        )

    def test_against_head_matches_diff_file_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Initialize git repo with a baseline commit so HEAD exists.
            self._run_git(tmp, "init", "-q", "-b", "main")
            self._run_git(tmp, "config", "user.email", "test@example.com")
            self._run_git(tmp, "config", "user.name", "Test")
            # Baseline file so we have a HEAD to diff against.
            baseline = Path(tmp) / "README.md"
            baseline.write_text("hi\n")
            self._run_git(tmp, "add", "README.md")
            self._run_git(tmp, "commit", "-q", "-m", "init")

            # Add a test file in the working tree (not committed).
            tests_dir = Path(tmp) / "tests"
            tests_dir.mkdir()
            test_file = tests_dir / "test_alpha.py"
            test_file.write_text(
                "def test_alpha():\n    assert True\n"
            )
            self._run_git(tmp, "add", "tests/test_alpha.py")

            # `git diff HEAD` only diffs tracked changes; staged additions
            # are visible to it.
            git_diff = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=tmp, capture_output=True, text=True, check=True,
            ).stdout
            self.assertTrue(git_diff, "expected non-empty git diff HEAD")

            # Invoke quality.py with --against HEAD inside the tmp repo.
            against_result = subprocess.run(
                [sys.executable, str(QUALITY_PY), "--against", "HEAD"],
                cwd=tmp, capture_output=True, text=True,
            )
            self.assertEqual(against_result.returncode, 0, against_result.stderr)

            # And with --diff-file pointed at the equivalent diff.
            diff_file_result = run_quality_with_diff(git_diff)
            self.assertEqual(diff_file_result.returncode, 0, diff_file_result.stderr)

            self.assertEqual(against_result.stdout, diff_file_result.stdout)
            self.assertIn("applicable: true", against_result.stdout)
            self.assertIn("new-it-blocks: 1", against_result.stdout)


if __name__ == "__main__":
    unittest.main()
