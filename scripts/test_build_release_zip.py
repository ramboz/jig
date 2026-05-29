"""
Tests for scripts/build_release_zip.py — slice 013-03 (release-zip-artifact).

Covers AC #5 (zip shape, exclusion rules, version-mismatch fail, idempotency)
and AC #4 (output validation gate).
"""

import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_release_zip  # noqa: E402
import install_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_VERSION = json.loads(
    (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
)["version"]


def _build_once(version: str = _PLUGIN_VERSION) -> Path:
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

    def test_codex_plugin_json_at_root(self):
        self.assertIn(".codex-plugin/plugin.json", self.names)

    def test_marketplace_json_at_root(self):
        self.assertIn(".claude-plugin/marketplace.json", self.names)

    def test_reviewer_agent_present(self):
        self.assertIn("agents/reviewer.md", self.names)

    def test_implementer_agent_present(self):
        self.assertIn("agents/implementer.md", self.names)

    def test_architect_agent_present(self):
        self.assertIn("agents/architect.md", self.names)

    def test_every_expected_skill_present(self):
        """Slice 047-01 (AC #3): the zip carries EVERY skill in the install
        contract — not just 'at least one'. A skill dropped from the build
        is named explicitly (AC #4)."""
        missing = [
            skill
            for skill in install_contract.EXPECTED_SKILLS
            if f"skills/{skill}/SKILL.md" not in self.names
        ]
        self.assertEqual(
            missing, [],
            f"release zip is missing SKILL.md for expected skill(s): {missing!r}",
        )

    def test_templates_directory_present(self):
        template_files = [n for n in self.names if n.startswith("templates/")]
        self.assertGreater(len(template_files), 0)

    def test_hooks_json_present(self):
        self.assertIn("hooks/hooks.json", self.names)

    def test_every_registered_hook_script_present(self):
        """Slice 047-01 (AC #3): every script hooks.json registers is in the
        zip. `hooks/hooks.json` invokes
        `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/jig-*.sh` at runtime, so a
        missing script silently breaks that hook event (the original 013-03
        build regression). Derived from the zip's own hooks.json so the test
        tracks the registration source of truth (AC #4 names any missing
        script)."""
        with zipfile.ZipFile(self.zip_path) as zf:
            hooks_data = json.loads(zf.read("hooks/hooks.json"))
        registered = install_contract.parse_hook_script_names(hooks_data)
        self.assertTrue(registered, "hooks.json registered no scripts")
        missing = [
            name
            for name in registered
            if f"hooks/scripts/{name}" not in self.names
        ]
        self.assertEqual(
            missing, [],
            f"release zip is missing registered hook script(s): {missing!r}",
        )

    def test_readme_present(self):
        self.assertIn("README.md", self.names)

    def test_spec_lint_shipped(self):
        """Slice 075-01 (AC #1 / AC #2): the dev-only spec-lint validator is
        re-included in the release so the shipped migrate/analyze references
        to it resolve in a consuming project (the original leak: skills told
        the agent to run a script the plugin never shipped). Removing
        `scripts/spec_lint.py` from `RELEASE_INCLUDE_SCRIPT_FILES` turns this
        red."""
        self.assertIn(
            "scripts/spec_lint.py", self.names,
            "release zip must ship scripts/spec_lint.py so the migrate/"
            "analyze skill references to it resolve in a consuming project",
        )


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
        test_files = [n for n in self.names
                      if Path(n).name.startswith("test_") and n.endswith(".py")]
        self.assertEqual(
            test_files, [],
            f"zip must not contain test_*.py files; found {test_files!r}",
        )

    def test_runtime_scripts_only(self):
        """`scripts/` is dev-only EXCEPT for the allowlisted modules: the
        three runtime modules scaffold-init imports at install time
        (verify_install + install_contract + scaffold_contract) plus the
        pure-stdlib spec_lint validator the migrate/analyze skills tell the
        agent to run (slice 075-01). The zip must carry exactly the
        `RELEASE_INCLUDE_SCRIPT_FILES` set under `scripts/` and none of the
        dev/CI tooling (build_release_zip, run_tests, usage,
        validate_manifests).
        Pins the `install_contract.RELEASE_INCLUDE_SCRIPT_FILES` allowlist
        (spec 069-01 re-homed it from build_release_zip) so a future dev
        script can't silently leak into the plugin install, and so the
        allowlisted modules can't silently drop back out (the regression that
        crashed scaffold-init's completion self-check on every packaged
        install — it shipped no `scripts/` at all)."""
        scripts_entries = {n for n in self.names if n.startswith("scripts/")}
        expected = set(install_contract.RELEASE_INCLUDE_SCRIPT_FILES)
        self.assertEqual(
            scripts_entries, expected,
            "zip's scripts/ entries must equal exactly the RELEASE_INCLUDE_SCRIPT_FILES allowlist; "
            f"got {sorted(scripts_entries)!r}, expected {sorted(expected)!r}",
        )

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
# Slice 047-01 (AC #3 / AC #4) — explicit release-zip contract inventory.
# The smoke test verifies the FULL declared install surface against a built
# zip (every expected skill + all three agents + every registered hook
# script + both manifests) and scans for any excluded test-only path that
# leaked in, rather than asserting only "at least one" artifact exists.
# ---------------------------------------------------------------------------


class ReleaseZipContractInventoryTests(unittest.TestCase):
    def setUp(self):
        self.zip_path = _build_once()
        self.addCleanup(self.zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(self.zip_path) as zf:
            self.names = set(zf.namelist())

    def test_all_three_agents_present(self):
        missing = [
            agent
            for agent in install_contract.REQUIRED_AGENTS
            if f"agents/{agent}.md" not in self.names
        ]
        self.assertEqual(
            missing, [], f"release zip missing agent file(s): {missing!r}"
        )

    def test_both_manifests_present(self):
        for manifest in (
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
        ):
            self.assertIn(
                manifest, self.names,
                f"release zip missing manifest {manifest!r}",
            )

    def test_no_excluded_path_leaked(self):
        """No path the release contract excludes (fixtures/, test_*.py,
        __pycache__, *.pyc, .DS_Store) leaked into the built zip. Uses the
        contract's own predicate, so the build's exclusion rules and the
        check agree (AC #3 / AC #4 names the leaked path)."""
        leaked = sorted(
            n for n in self.names if install_contract.is_excluded_release_path(n)
        )
        self.assertEqual(
            leaked, [],
            f"release zip contains excluded test-only/junk path(s): {leaked!r}",
        )

    def test_no_fixtures_directory_leaked(self):
        offenders = sorted(n for n in self.names if "fixtures" in Path(n).parts)
        self.assertEqual(
            offenders, [],
            f"release zip must exclude all fixtures/ paths; found {offenders!r}",
        )

    def test_no_test_py_leaked(self):
        offenders = sorted(
            n
            for n in self.names
            if Path(n).name.startswith("test_") and n.endswith(".py")
        )
        self.assertEqual(
            offenders, [],
            f"release zip must exclude test_*.py; found {offenders!r}",
        )


# ---------------------------------------------------------------------------
# AC #4: version-mismatch case exits non-zero with clear message
# ---------------------------------------------------------------------------


class VersionMismatchTests(unittest.TestCase):
    def test_mismatched_version_exits_nonzero(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-mismatch-"))
        out = tmp / "jig-v9.9.9.zip"
        # Passing a deliberately wrong version must fail regardless of current plugin.json.
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
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(".claude-plugin/plugin.json") as f:
                data = json.loads(f.read())
        self.assertEqual(data["version"], _PLUGIN_VERSION)
        self.assertEqual(data["name"], "jig")

    def test_codex_plugin_json_version_matches_requested(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(".codex-plugin/plugin.json") as f:
                data = json.loads(f.read())
        self.assertEqual(data["version"], _PLUGIN_VERSION)
        self.assertEqual(data["name"], "jig")

    def test_codex_plugin_manifest_uses_shared_runtime_roots(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(".codex-plugin/plugin.json") as f:
                data = json.loads(f.read())
        self.assertEqual(data["skills"], "./skills/")
        self.assertNotIn("codexSkills", data)
        self.assertNotIn("agents", data)


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def test_main_with_version_creates_zip(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-cli-"))
        out = tmp / f"jig-v{_PLUGIN_VERSION}.zip"
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main(
                ["build_release_zip.py", "--version", _PLUGIN_VERSION, "--output", str(out)]
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


class PackagedVerifierImportTests(unittest.TestCase):
    """The scaffold-completion self-check (slice 048-06) imports
    `verify_install` (which pulls in `install_contract` +
    `scaffold_contract`) from `<plugin-root>/scripts/` at install time.
    Before the runtime-scripts-allowlist fix the release zip carried no
    `scripts/` at all, so that import crashed on every packaged plugin
    install. The existing `smoke_test` imports the verifier from the SOURCE
    repo, not the extracted tree, so it never exercised this path.

    This test extracts the built zip, asserts every allowlisted
    `scripts/` module is present, and imports the verifier from the
    EXTRACTED tree in a clean subprocess (no repo `scripts/` on `sys.path`),
    reproducing exactly what scaffold.py does on a real plugin install."""

    def test_verifier_imports_from_extracted_tree(self):
        import subprocess

        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix="jig-pkg-verify-"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        for rel in install_contract.RELEASE_INCLUDE_SCRIPT_FILES:
            self.assertTrue(
                (tmp / rel).is_file(),
                f"runtime module {rel} missing from extracted plugin tree",
            )

        # Import in a subprocess with ONLY the extracted scripts/ dir on the
        # path — mirrors scaffold.py inserting `<plugin-root>/scripts/` and
        # importing verify_install on a packaged install. `-S`/clean env keep
        # the repo's own modules off the path.
        scripts_dir = tmp / "scripts"
        snippet = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "import verify_install; "
            "assert callable(verify_install.run_completion_summary)"
        )
        result = subprocess.run(
            [sys.executable, "-c", snippet, str(scripts_dir)],
            cwd=str(tmp),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode, 0,
            f"verifier failed to import from packaged tree:\n{result.stderr}",
        )


class MissingLicenseWarningTests(unittest.TestCase):
    """AC #2: builder warns (not fails) when LICENSE is absent at build time."""

    def test_missing_license_emits_warning(self):
        # Build against the real repo, which currently has no LICENSE
        # (013-04 adds it). The builder should still succeed AND emit
        # a warning line so the missing file is visible to the operator.
        tmp = Path(tempfile.mkdtemp(prefix="jig-license-"))
        out = tmp / f"jig-v{_PLUGIN_VERSION}.zip"
        sink = io.StringIO()
        code = build_release_zip.build(
            source_root=Path(__file__).resolve().parent.parent,
            version=_PLUGIN_VERSION,
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


# ---------------------------------------------------------------------------
# Slice 035-01 — exclude-fixtures-from-installs. The release-file enumerator
# (`install_contract.iter_release_files`, re-homed from build_release_zip in
# spec 069-01) must skip any directory named `fixtures` at any depth under
# the included roots (matches the `__pycache__` semantics already in place).
# Test data lives at `skills/migrate/fixtures/` today; the rule generalizes
# for any future skill that grows a fixtures tree.
# ---------------------------------------------------------------------------


class FixturesExclusionAgainstRealSourceTests(unittest.TestCase):
    """AC #2 — built zip against the real source tree contains no entry
    whose path includes a `fixtures` component anywhere under
    `skills/`. Pins the regression against the live `skills/migrate/
    fixtures/` test corpus."""

    def test_no_fixtures_entries_in_real_zip(self):
        zip_path = _build_once()
        self.addCleanup(zip_path.unlink, missing_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        offenders = [n for n in names if "fixtures" in Path(n).parts]
        self.assertEqual(
            offenders, [],
            "zip must not contain any `fixtures/` path components under "
            f"any included root; found {offenders!r}",
        )


class FixturesExclusionAtAnyDepthTests(unittest.TestCase):
    """AC #3 — `install_contract.iter_release_files` skips `fixtures/`
    directories nested below the skill root, not just at the top of a skill
    subtree. Uses a synthesized source tree so the test does not depend on
    the repo's current skill layout."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="jig-035-01-zip-"))
        # Minimum surface that the enumerator walks: one of the included
        # roots populated with a skill-shaped subtree. We use `skills/`
        # since the real bug is on that root.
        skill = self.tmpdir / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: demo\n---\nbody\n")
        (skill / "runtime.py").write_text("# kept\n")

        # Root-level fixtures dir under the skill.
        root_fixtures = skill / "fixtures"
        root_fixtures.mkdir()
        (root_fixtures / "case.txt").write_text("must not ship\n")

        # Nested fixtures dir — deeper than the skill root.
        nested_fixtures = skill / "sub" / "deeper" / "fixtures"
        nested_fixtures.mkdir(parents=True)
        (nested_fixtures / "nested.txt").write_text("must not ship\n")
        # Non-fixtures sibling to prove the filter is selective.
        (skill / "sub" / "deeper" / "kept.txt").write_text("kept\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_iter_files_skips_fixtures_at_any_depth(self):
        rels = [
            p.as_posix()
            for p in install_contract.iter_release_files(self.tmpdir)
        ]
        offenders = [r for r in rels if "fixtures" in Path(r).parts]
        self.assertEqual(
            offenders, [],
            "iter_release_files must skip every `fixtures/` dir at any depth "
            f"under the skill subtree; found {offenders!r}",
        )
        # Sanity — non-fixtures siblings still flow through.
        self.assertIn("skills/demo-skill/SKILL.md", rels)
        self.assertIn("skills/demo-skill/sub/deeper/kept.txt", rels)


if __name__ == "__main__":
    unittest.main()
