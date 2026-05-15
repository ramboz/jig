"""
Tests for scripts/validate_manifests.py — slice 013-01 (ci-baseline).

Covers AC #7: (a) all-valid exits 0; (b) plugin.json missing `name` exits
non-zero with a clear message naming the missing field; (c) marketplace.json
missing `name` exits non-zero; (d) malformed JSON in any file exits non-zero
with the offending file path in the error message. Also a smoke test that
the real checked-in manifests in this repo pass validation.
"""

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_manifests  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_VALID_PLUGIN_JSON = {
    "name": "jig",
    "version": "0.1.0",
    "description": "test",
}

_VALID_MARKETPLACE_JSON = {
    "name": "jig",
    "owner": {"name": "ramboz"},
    "plugins": [{"name": "jig", "source": ".."}],
}

_VALID_HOOKS_JSON = {
    "hooks": {
        "PreToolUse": [],
    }
}


def _seed_valid_repo(root: Path) -> None:
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(_VALID_PLUGIN_JSON)
    )
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(_VALID_MARKETPLACE_JSON)
    )
    (root / "hooks").mkdir()
    (root / "hooks" / "hooks.json").write_text(json.dumps(_VALID_HOOKS_JSON))


# ---------------------------------------------------------------------------
# AC #7 (a) — all-valid: exits 0
# ---------------------------------------------------------------------------


class AllValidTests(unittest.TestCase):
    def test_all_valid_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertEqual(code, 0, msg=out.getvalue())

    def test_all_valid_summary_mentions_three_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            out = io.StringIO()
            validate_manifests.run(root, out=out)
            text = out.getvalue()
            self.assertIn("plugin.json", text)
            self.assertIn("marketplace.json", text)
            self.assertIn("hooks.json", text)


# ---------------------------------------------------------------------------
# AC #7 (b) — plugin.json missing `name` exits non-zero with clear message
# ---------------------------------------------------------------------------


class PluginJsonMissingNameTests(unittest.TestCase):
    def test_missing_name_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"version": "0.1.0"})
            )
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)

    def test_missing_name_message_names_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"version": "0.1.0"})
            )
            out = io.StringIO()
            validate_manifests.run(root, out=out)
            text = out.getvalue()
            self.assertIn("name", text)
            self.assertIn("plugin.json", text)


# ---------------------------------------------------------------------------
# AC #7 (c) — marketplace.json missing `name` exits non-zero
# ---------------------------------------------------------------------------


class MarketplaceJsonMissingNameTests(unittest.TestCase):
    def test_missing_name_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            broken = dict(_VALID_MARKETPLACE_JSON)
            broken.pop("name")
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(broken)
            )
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)

    def test_missing_name_message_names_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            broken = dict(_VALID_MARKETPLACE_JSON)
            broken.pop("name")
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps(broken)
            )
            out = io.StringIO()
            validate_manifests.run(root, out=out)
            text = out.getvalue()
            self.assertIn("name", text)
            self.assertIn("marketplace.json", text)


# ---------------------------------------------------------------------------
# AC #7 (d) — malformed JSON exits non-zero with offending path in message
# ---------------------------------------------------------------------------


class MalformedJsonTests(unittest.TestCase):
    def test_malformed_plugin_json_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / ".claude-plugin" / "plugin.json").write_text("{not json")
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)
            self.assertIn("plugin.json", out.getvalue())

    def test_malformed_marketplace_json_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / ".claude-plugin" / "marketplace.json").write_text("not json")
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)
            self.assertIn("marketplace.json", out.getvalue())

    def test_malformed_hooks_json_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / "hooks" / "hooks.json").write_text("[broken,")
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)
            self.assertIn("hooks.json", out.getvalue())


# ---------------------------------------------------------------------------
# Missing-file handling
# ---------------------------------------------------------------------------


class MissingFileTests(unittest.TestCase):
    def test_missing_plugin_json_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / ".claude-plugin" / "plugin.json").unlink()
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)
            self.assertIn("plugin.json", out.getvalue())

    def test_missing_hooks_json_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            (root / "hooks" / "hooks.json").unlink()
            out = io.StringIO()
            code = validate_manifests.run(root, out=out)
            self.assertNotEqual(code, 0)
            self.assertIn("hooks.json", out.getvalue())


# ---------------------------------------------------------------------------
# Integration: the real checked-in manifests validate cleanly
# ---------------------------------------------------------------------------


class RealRepoIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent

    def test_real_repo_validates(self):
        out = io.StringIO()
        code = validate_manifests.run(self.repo_root, out=out)
        self.assertEqual(
            code, 0,
            msg=f"the real repo's manifests should validate; got:\n{out.getvalue()}",
        )

    def test_marketplace_name_is_jig(self):
        """Pins the slice 013-04 rename: marketplace must be `jig`, not `jig-dev`.

        The public install command is `/plugin install jig@jig`. Reverting to
        `jig-dev` would invalidate the README install path documented in
        slice 013-04 AC #2.
        """
        data = json.loads(
            (self.repo_root / ".claude-plugin" / "marketplace.json").read_text()
        )
        self.assertEqual(
            data.get("name"), "jig",
            f"marketplace.json `name` must be 'jig' (post-013-04); got {data.get('name')!r}",
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


class GeneratorIterableTests(unittest.TestCase):
    """Regression: passing a generator instead of a tuple must not exhaust early."""

    def test_generator_manifests_summary_counts_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            out = io.StringIO()
            gen = (m for m in validate_manifests._MANIFESTS)
            code = validate_manifests.run(root, out=out, manifests=gen)
            self.assertEqual(code, 0)
            self.assertIn("3/3", out.getvalue())


class CliTests(unittest.TestCase):
    def test_main_with_no_args_uses_repo_root(self):
        # main() should default to the script's repo root and return 0 on the
        # real repo. Captures stdout to avoid noise during test runs.
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = validate_manifests.main(["validate_manifests.py"])
        finally:
            sys.stdout = original
        self.assertEqual(code, 0, msg=captured.getvalue())

    def test_main_with_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_valid_repo(root)
            captured = io.StringIO()
            original = sys.stdout
            sys.stdout = captured
            try:
                code = validate_manifests.main(
                    ["validate_manifests.py", "--root", str(root)]
                )
            finally:
                sys.stdout = original
            self.assertEqual(code, 0, msg=captured.getvalue())


if __name__ == "__main__":
    unittest.main()
