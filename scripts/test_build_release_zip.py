"""
Tests for scripts/build_release_zip.py — slice 013-03 (release-zip-artifact).

Covers AC #5 (zip shape, exclusion rules, version-mismatch fail, idempotency)
and AC #4 (output validation gate).
"""

import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_release_zip  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent


def _build_once(version: str = "1.0.0") -> Path:
    """Build a zip using the real repo as source, into a tempdir.

    Builder log output is captured to a sink so the test runner's
    output stays clean (CI logs would otherwise be polluted with one
    `OK: built ...` line per test).

    Returns the zip path. Caller is responsible for cleanup if it
    creates artifacts outside the tempdir.
    """
    tmp = Path(tempfile.mkdtemp(prefix="jig-build-test-"))
    out = tmp / f"jig-v{version}.zip"
    sink = io.StringIO()
    code = build_release_zip.build(
        source_root=REPO_ROOT,
        version=version,
        output_path=out,
        out=sink,
    )
    if code != 0:
        raise RuntimeError(
            f"builder exited {code} for version {version!r}: {sink.getvalue()}"
        )
    return out


# ---------------------------------------------------------------------------
# AC #5 (a): produces a non-empty zip at the expected path
# ---------------------------------------------------------------------------


class BuildOutputTests(unittest.TestCase):
    def test_zip_exists_and_nonempty(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        self.assertTrue(zip_path.is_file())
        self.assertGreater(zip_path.stat().st_size, 0)


# ---------------------------------------------------------------------------
# AC #5 (b)–(d): contains the right files
# ---------------------------------------------------------------------------


class InclusionTests(unittest.TestCase):
    def setUp(self):
        self.zip_path = _build_once()
        self.addCleanup(self.zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(self.zip_path) as zf:
            self.names = set(zf.namelist())

    def test_plugin_json_at_root(self):
        self.assertIn(".claude-plugin/plugin.json", self.names)

    def test_marketplace_json_at_root(self):
        self.assertIn(".claude-plugin/marketplace.json", self.names)

    def test_reviewer_agent_present(self):
        self.assertIn("agents/reviewer.md", self.names)

    def test_implementer_agent_present(self):
        self.assertIn("agents/implementer.md", self.names)

    def test_architect_agent_present(self):
        self.assertIn("agents/architect.md", self.names)

    def test_skill_md_present(self):
        skill_mds = [n for n in self.names if n.startswith("skills/") and n.endswith("/SKILL.md")]
        self.assertGreater(
            len(skill_mds), 0,
            f"expected at least one skill SKILL.md under skills/; got {sorted(self.names)[:20]!r}...",
        )

    def test_templates_directory_present(self):
        template_files = [n for n in self.names if n.startswith("templates/")]
        self.assertGreater(len(template_files), 0)

    def test_hooks_json_present(self):
        self.assertIn("hooks/hooks.json", self.names)

    def test_hook_scripts_present(self):
        """Regression: `hooks/scripts/*.sh` must be in the zip.

        `hooks/hooks.json` invokes `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-*.sh`
        at runtime — excluding them silently breaks every hook event.
        Bug from first 013-03 build: a too-broad `scripts` directory
        exclusion swallowed these files.
        """
        hook_scripts = [
            n for n in self.names
            if n.startswith("hooks/scripts/") and n.endswith(".sh")
        ]
        self.assertGreater(
            len(hook_scripts), 0,
            f"expected at least one hooks/scripts/*.sh in zip; got "
            f"{sorted(n for n in self.names if n.startswith('hooks/'))!r}",
        )

    def test_readme_present(self):
        self.assertIn("README.md", self.names)


# ---------------------------------------------------------------------------
# AC #5 (e)–(f): explicit exclusions
# ---------------------------------------------------------------------------


class ExclusionTests(unittest.TestCase):
    def setUp(self):
        self.zip_path = _build_once()
        self.addCleanup(self.zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(self.zip_path) as zf:
            self.names = set(zf.namelist())

    def test_no_test_files(self):
        test_files = [n for n in self.names if Path(n).name.startswith("test_") and n.endswith(".py")]
        self.assertEqual(
            test_files, [],
            f"zip must not contain test_*.py files; found {test_files!r}",
        )

    def test_no_scripts_dir(self):
        scripts_entries = [n for n in self.names if n.startswith("scripts/")]
        self.assertEqual(scripts_entries, [])

    def test_no_docs_dir(self):
        docs_entries = [n for n in self.names if n.startswith("docs/")]
        self.assertEqual(docs_entries, [])

    def test_no_github_dir(self):
        gh_entries = [n for n in self.names if n.startswith(".github/")]
        self.assertEqual(gh_entries, [])

    def test_no_claude_md(self):
        self.assertNotIn("CLAUDE.md", self.names)

    def test_no_contributing_md(self):
        self.assertNotIn("CONTRIBUTING.md", self.names)

    def test_no_settings_json(self):
        self.assertNotIn("settings.json", self.names)

    def test_no_jig_dir(self):
        entries = [n for n in self.names if n.startswith(".jig/")]
        self.assertEqual(entries, [])

    def test_no_pycache(self):
        entries = [n for n in self.names if "__pycache__" in n or n.endswith(".pyc")]
        self.assertEqual(entries, [])

    def test_no_wrapping_directory(self):
        """Per the AC: contents must be flat at root, NOT wrapped in `jig/`."""
        wrapped = [n for n in self.names if n.startswith("jig/")]
        self.assertEqual(
            wrapped, [],
            f"zip must not nest contents in a 'jig/' wrapping dir; found {wrapped!r}",
        )


# ---------------------------------------------------------------------------
# AC #4: version-mismatch case exits non-zero with clear message
# ---------------------------------------------------------------------------


class VersionMismatchTests(unittest.TestCase):
    def test_mismatched_version_exits_nonzero(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-mismatch-"))
        out = tmp / "jig-v9.9.9.zip"
        # The real repo's plugin.json says 1.0.0; passing 9.9.9 must fail.
        captured = io.StringIO()
        code = build_release_zip.build(
            source_root=REPO_ROOT,
            version="9.9.9",
            output_path=out,
            out=captured,
        )
        self.assertNotEqual(code, 0)
        text = captured.getvalue()
        self.assertIn("9.9.9", text)
        # Cleanup any partial artifact.
        out.unlink(missing_ok=True)
        tmp.rmdir()


# ---------------------------------------------------------------------------
# AC #5 (g): idempotency — running twice produces a bit-identical zip
# ---------------------------------------------------------------------------


class IdempotencyTests(unittest.TestCase):
    def test_two_builds_produce_identical_bytes(self):
        zip_a = _build_once()
        zip_b = _build_once()
        self.addCleanup(zip_a.unlink, missing_ok=True)
        self.addCleanup(zip_b.unlink, missing_ok=True)
        self.assertEqual(
            zip_a.read_bytes(),
            zip_b.read_bytes(),
            "idempotency: two builds with the same --version must yield bit-identical bytes",
        )


# ---------------------------------------------------------------------------
# Plugin-manifest content is correct (version is what we asked for)
# ---------------------------------------------------------------------------


class ManifestContentTests(unittest.TestCase):
    def test_plugin_json_version_matches_requested(self):
        zip_path = _build_once(version="1.0.0")
        self.addCleanup(zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(".claude-plugin/plugin.json") as f:
                data = json.loads(f.read())
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["name"], "jig")


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def test_main_with_version_creates_zip(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-cli-"))
        out = tmp / "jig-v1.0.0.zip"
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main(
                ["build_release_zip.py", "--version", "1.0.0", "--output", str(out)]
            )
        finally:
            sys.stdout = original
        try:
            self.assertEqual(code, 0, msg=captured.getvalue())
            self.assertTrue(out.is_file())
        finally:
            out.unlink(missing_ok=True)
            tmp.rmdir()

    def test_main_without_version_or_smoketest_errors(self):
        original_err = sys.stderr
        sys.stderr = io.StringIO()
        try:
            code = build_release_zip.main(["build_release_zip.py"])
        finally:
            sys.stderr = original_err
        self.assertNotEqual(code, 0)


class SmokeTestTests(unittest.TestCase):
    """AC #7: `--smoke-test <zip>` extracts the zip and runs verify_install."""

    def test_smoke_test_passes_on_valid_zip(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        sink = io.StringIO()
        code = build_release_zip.smoke_test(zip_path, out=sink)
        self.assertEqual(code, 0, msg=sink.getvalue())

    def test_smoke_test_fails_on_missing_zip(self):
        sink = io.StringIO()
        code = build_release_zip.smoke_test(Path("/nonexistent/jig-v999.zip"), out=sink)
        self.assertNotEqual(code, 0)
        self.assertIn("not found", sink.getvalue())

    def test_smoke_test_via_main(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main(
                ["build_release_zip.py", "--smoke-test", str(zip_path)]
            )
        finally:
            sys.stdout = original
        self.assertEqual(code, 0, msg=captured.getvalue())


class MissingLicenseWarningTests(unittest.TestCase):
    """AC #2: builder warns (not fails) when LICENSE is absent at build time."""

    def test_missing_license_emits_warning(self):
        # Build against the real repo, which currently has no LICENSE
        # (013-04 adds it). The builder should still succeed AND emit
        # a warning line so the missing file is visible to the operator.
        tmp = Path(tempfile.mkdtemp(prefix="jig-license-"))
        out = tmp / "jig-v1.0.0.zip"
        sink = io.StringIO()
        code = build_release_zip.build(
            source_root=Path(__file__).resolve().parent.parent,
            version="1.0.0",
            output_path=out,
            out=sink,
        )
        try:
            license_exists = (Path(__file__).resolve().parent.parent / "LICENSE").is_file()
            if license_exists:
                # If LICENSE is present (post-013-04), no warning expected.
                self.assertNotIn("WARN: optional file 'LICENSE'", sink.getvalue())
            else:
                self.assertEqual(code, 0, msg=sink.getvalue())
                self.assertIn(
                    "WARN: optional file 'LICENSE'", sink.getvalue(),
                    f"expected LICENSE-missing warning; got: {sink.getvalue()!r}",
                )
        finally:
            out.unlink(missing_ok=True)
            tmp.rmdir()


if __name__ == "__main__":
    unittest.main()
