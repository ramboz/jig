"""
Smoke tests for the tdd-loop test-quality preflight (quality.py).

Run from the repo root:
    python3 -m unittest discover -s skills/tdd-loop -p 'test_quality.py'

This is an intentionally tight smoke suite, not a full AC matrix — when
this lands as a formal slice, deeper coverage (flood / assertion-thin /
mock-heavy threshold edges, malformed diff variants, gh fallback) should
be added.
"""

import importlib.util
import os
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
        # 3 tests, 1 assertion each → density 1.0, below 1.5, BUT under
        # the 20-test minimum so the signal stays quiet.
        body = "".join(
            f"+def test_{i}():\n+    assert True\n+\n" for i in range(3)
        )
        diff = f"""\
diff --git a/tests/test_thin.py b/tests/test_thin.py
index 0000..1111 100644
--- a/tests/test_thin.py
+++ b/tests/test_thin.py
@@ -0,0 +1,9 @@
{body}"""
        result = run_quality_with_diff(diff)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("assertion-thin: false", result.stdout)

    def test_assertion_thin_fires_at_threshold(self):
        # 25 tests, 25 assertions → density 1.0, below 1.5; > 20 tests so
        # the signal fires.
        body = "".join(
            f"+def test_{i}():\n+    assert True\n+\n" for i in range(25)
        )
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


if __name__ == "__main__":
    unittest.main()
