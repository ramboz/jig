"""
Tests for release-please config files — slice 013-02 (release-please-scaffold).

Covers AC #9: (a) config parses as JSON; (b) contains `packages."."`;
(c) `release-type: "simple"`; (d) `extra-files` points at plugin.json with
`jsonpath: "$.version"`; (e) manifest parses + declares a version for ".".

Plus additional integrity checks: plugin manifests + manifest agree on the
checked-in version (so a contributor can't desync by editing one and not
the other), and `release-as` is consistent with the user-locked v1.0.0
decision until removed post-release.
"""

import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / ".github" / "release-please-config.json"
MANIFEST_PATH = REPO_ROOT / ".github" / ".release-please-manifest.json"
PLUGIN_JSON_PATH = REPO_ROOT / ".claude-plugin" / "plugin.json"
CODEX_PLUGIN_JSON_PATH = REPO_ROOT / ".codex-plugin" / "plugin.json"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
RELEASE_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"


# ---------------------------------------------------------------------------
# AC #9 (a)–(d): release-please-config.json
# ---------------------------------------------------------------------------


class ReleasePleaseConfigTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            CONFIG_PATH.is_file(),
            f"release-please-config.json missing at {CONFIG_PATH}",
        )
        self.config = json.loads(CONFIG_PATH.read_text())

    def test_config_parses_as_json(self):
        # Parsed in setUp; this is a no-op smoke test.
        self.assertIsInstance(self.config, dict)

    def test_config_contains_root_package(self):
        packages = self.config.get("packages", {})
        self.assertIn(
            ".", packages,
            f"release-please-config.json must declare packages.'.' (got {list(packages)!r})",
        )

    def test_config_uses_simple_release_type(self):
        self.assertEqual(
            self.config.get("release-type"),
            "simple",
            f"release-type must be 'simple' (got {self.config.get('release-type')!r})",
        )

    def test_extra_files_points_at_plugin_jsons(self):
        pkg = self.config["packages"]["."]
        extra = pkg.get("extra-files", [])
        paths = {
            e.get("path")
            for e in extra
            if isinstance(e, dict)
            and e.get("type") == "json"
            and e.get("jsonpath") == "$.version"
        }
        self.assertEqual(
            paths,
            {".claude-plugin/plugin.json", ".codex-plugin/plugin.json"},
            f"expected release-please to version both plugin manifests, got {extra!r}",
        )


# ---------------------------------------------------------------------------
# AC #9 (e): manifest
# ---------------------------------------------------------------------------


class ReleasePleaseManifestTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            MANIFEST_PATH.is_file(),
            f".release-please-manifest.json missing at {MANIFEST_PATH}",
        )
        self.manifest = json.loads(MANIFEST_PATH.read_text())

    def test_manifest_parses_as_json(self):
        self.assertIsInstance(self.manifest, dict)

    def test_manifest_declares_root_version(self):
        self.assertIn(
            ".", self.manifest,
            f"manifest must declare a version for '.' (got {list(self.manifest)!r})",
        )
        version = self.manifest["."]
        self.assertIsInstance(version, str)
        # Loose semver shape: N.N.N (no pre-release / build identifiers
        # expected during normal operation).
        parts = version.split(".")
        self.assertEqual(
            len(parts), 3,
            f"manifest version for '.' must be semver-shaped (got {version!r})",
        )
        for part in parts:
            self.assertTrue(
                part.isdigit(),
                f"manifest version components must be digits (got {version!r})",
            )

    def test_manifest_seed_below_release_as_target(self):
        # During the v1.0.0 bootstrap window, the manifest seed (the
        # "last released version" release-please tracks) MUST be below
        # the `release-as` target so release-please opens a release PR
        # for v1.0.0. If they're equal, release-please's "simple" type
        # treats v1.0.0 as already-released and declines to open a PR.
        # This regression test guards against that mistake.
        manifest_version = self.manifest["."]
        config = json.loads(CONFIG_PATH.read_text())
        release_as = config.get("packages", {}).get(".", {}).get("release-as")
        if release_as is None:
            # Post-v1.0.0: `release-as` has been removed per CONTRIBUTING.md
            # "After v1.0.0 lands" — no constraint applies anymore.
            return
        self.assertNotEqual(
            manifest_version, release_as,
            f"manifest seed {manifest_version!r} must differ from release-as "
            f"{release_as!r} or release-please will skip the first release PR",
        )


# ---------------------------------------------------------------------------
# Integrity: plugin.json must agree with the source of truth
# ---------------------------------------------------------------------------


class VersionLockstepTests(unittest.TestCase):
    """Plugin manifest versions must match what release-please will publish."""

    def test_plugin_json_versions_match_release_as_or_manifest(self):
        config = json.loads(CONFIG_PATH.read_text())
        manifest = json.loads(MANIFEST_PATH.read_text())

        pkg = config.get("packages", {}).get(".", {})
        release_as = pkg.get("release-as")
        manifest_version = manifest.get(".")

        # plugin.json should match either:
        #   - the `release-as` pin (during the v1.0.0 bootstrap window), OR
        #   - the manifest version (after release-as is removed)
        expected = release_as if release_as else manifest_version
        for path in (PLUGIN_JSON_PATH, CODEX_PLUGIN_JSON_PATH):
            plugin = json.loads(path.read_text())
            plugin_version = plugin.get("version")
            self.assertIsNotNone(
                plugin_version,
                f"{path.relative_to(REPO_ROOT)} must declare a version",
            )
            self.assertEqual(
                plugin_version, expected,
                f"{path.relative_to(REPO_ROOT)} version {plugin_version!r} must match "
                f"{'release-as' if release_as else 'manifest'} ({expected!r}) "
                "or release-please will produce a desync on its next run",
            )


# ---------------------------------------------------------------------------
# CHANGELOG seed (sanity)
# ---------------------------------------------------------------------------


class ChangelogSeedTests(unittest.TestCase):
    def test_changelog_exists(self):
        self.assertTrue(
            CHANGELOG_PATH.is_file(),
            f"CHANGELOG.md missing at {CHANGELOG_PATH}",
        )

    def test_changelog_has_changelog_heading(self):
        text = CHANGELOG_PATH.read_text()
        self.assertIn("# Changelog", text, "CHANGELOG.md must start with '# Changelog'")


# ---------------------------------------------------------------------------
# Slice 061-04 — release workflow builds, smoke-tests, and uploads BOTH
# host-explicit zips, keeps the legacy jig-vX.Y.Z.zip one cycle as a
# byte-identical Claude alias, and appends extract-then-add install notes.
# ---------------------------------------------------------------------------


class ReleaseWorkflowHostZipTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(
            RELEASE_WORKFLOW_PATH.is_file(),
            f"release.yml missing at {RELEASE_WORKFLOW_PATH}",
        )
        self.text = RELEASE_WORKFLOW_PATH.read_text()

    def test_builds_both_hosts(self):
        self.assertIn("--host claude", self.text)
        self.assertIn("--host codex", self.text)

    def test_smoke_tests_both_hosts(self):
        # Each host appears with its own --smoke-test invocation.
        self.assertIn("--smoke-test", self.text)
        self.assertIn("jig-claude-v", self.text)
        self.assertIn("jig-codex-v", self.text)

    def test_uploads_both_host_zips(self):
        self.assertIn("dist/jig-claude-v${{ needs.release-please.outputs.version }}.zip", self.text)
        self.assertIn("dist/jig-codex-v${{ needs.release-please.outputs.version }}.zip", self.text)

    def test_legacy_alias_copied_from_claude(self):
        # Legacy host-neutral zip kept one cycle as a byte-identical Claude alias.
        self.assertIn("jig-v${{ needs.release-please.outputs.version }}.zip", self.text)
        # The alias is a `cp` from the Claude zip to the legacy name (the two
        # paths may span continuation lines, so match across newlines).
        self.assertRegex(
            self.text,
            r"(?s)cp\s+.*jig-claude-v\$\{\{ needs\.release-please\.outputs\.version \}\}\.zip"
            r".*jig-v\$\{\{ needs\.release-please\.outputs\.version \}\}\.zip",
        )

    def test_release_notes_extract_then_add_language(self):
        self.assertIn("extract-then-add", self.text)
        # release-please notes must be appended, not overwritten.
        self.assertIn("gh release view", self.text)
        self.assertIn("gh release edit", self.text)

    def test_release_notes_legacy_deprecation(self):
        lowered = self.text.lower()
        self.assertIn("deprecated", lowered)
        # Codex zip must never be called a directly-installable plugin zip.
        self.assertNotIn("directly-installable", lowered)


if __name__ == "__main__":
    unittest.main()
