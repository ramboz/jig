"""
Tests for scripts/build_release_zip.py — slice 061-04 (host-explicit release zips).

The builder now produces ONE zip per host, archived from the committed
`hosts/<host>/` packages (slice 061-02/03), not from a host-neutral walk of
the source root:

  - `--host claude` -> a flat Claude plugin zip (`.claude-plugin/plugin.json`
    at the zip root, drag-droppable / `--plugin-dir`-loadable).
  - `--host codex`  -> the Codex marketplace bundle root
    (`.agents/plugins/marketplace.json` + `plugins/jig/.codex-plugin/plugin.json`),
    an extract-then-add bundle (NOT a directly-installable plugin zip).

Covers slice 061-04 ACs:
  AC1 — Claude zip is `hosts/claude/` flat at root.
  AC2 — Codex zip is the `hosts/codex/` marketplace root.
  AC3 — Codex language is exact (extract-then-add; never directly-installable).
  AC4 — version coherence vs the host's own committed manifest (exit 2).
  AC5 — per-host smoke names the host; release workflow uploads both.
"""

import io
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_release_zip  # noqa: E402
import install_contract  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_ROOT = REPO_ROOT / "hosts"
CLAUDE_PKG = HOSTS_ROOT / "claude"
CODEX_PKG = HOSTS_ROOT / "codex"

_CLAUDE_VERSION = json.loads(
    (CLAUDE_PKG / ".claude-plugin" / "plugin.json").read_text()
)["version"]
_CODEX_VERSION = json.loads(
    (CODEX_PKG / "plugins" / "jig" / ".codex-plugin" / "plugin.json").read_text()
)["version"]


def _build_once(host: str, version: str, hosts_root: Path = HOSTS_ROOT) -> tuple[Path, str]:
    """Build a host zip from the committed hosts/ tree into a tempdir.

    Returns (zip_path, builder_output). Raises on a non-zero build code so a
    test that expects success surfaces the builder log.
    """
    tmp = Path(tempfile.mkdtemp(prefix=f"jig-{host}-build-test-"))
    out = tmp / f"jig-{host}-v{version}.zip"
    sink = io.StringIO()
    code = build_release_zip.build(
        host=host,
        hosts_root=hosts_root,
        version=version,
        output_path=out,
        out=sink,
    )
    if code != 0:
        raise RuntimeError(
            f"builder exited {code} for host={host} version={version!r}: "
            f"{sink.getvalue()}"
        )
    return out, sink.getvalue()


# ---------------------------------------------------------------------------
# AC1 — Claude zip is hosts/claude/ flat at root.
# ---------------------------------------------------------------------------


class ClaudeZipShapeTests(unittest.TestCase):
    def setUp(self):
        self.zip_path, self.output = _build_once("claude", _CLAUDE_VERSION)
        self.addCleanup(shutil.rmtree, self.zip_path.parent, ignore_errors=True)
        with zipfile.ZipFile(self.zip_path) as zf:
            self.names = set(zf.namelist())

    def test_claude_plugin_json_at_root(self):
        self.assertIn(".claude-plugin/plugin.json", self.names)

    def test_no_wrapping_directory(self):
        wrapped = [n for n in self.names if n.startswith("jig/")]
        self.assertEqual(wrapped, [], f"Claude zip must be flat; found {wrapped!r}")

    def test_no_hosts_prefix(self):
        # arcnames are relative to hosts/claude/, not the repo root.
        leaked = [n for n in self.names if n.startswith("hosts/")]
        self.assertEqual(leaked, [], f"arcnames must be relative to hosts/claude/; got {leaked!r}")

    def test_runtime_dirs_present(self):
        self.assertIn("agents/reviewer.md", self.names)
        skill_files = [n for n in self.names if n.startswith("skills/")]
        self.assertGreater(len(skill_files), 0)
        self.assertIn("hooks/hooks.json", self.names)

    def test_every_registered_hook_script_present(self):
        """Every script registered by hooks.json is present in the host zip."""
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

    def test_dev_only_files_absent(self):
        # The committed Claude package is runtime-only: no docs/tests/CI.
        for prefix in ("docs/", ".github/", ".codex-plugin/"):
            offenders = [n for n in self.names if n.startswith(prefix)]
            self.assertEqual(
                offenders, [], f"Claude zip must exclude {prefix}; found {offenders!r}"
            )

    def test_scripts_are_the_runtime_allowlist_only(self):
        # `scripts/` is not wholesale-excluded: the allowlisted runtime modules
        # ship under it so `${CLAUDE_PLUGIN_ROOT}/scripts/…` resolves in an
        # installed plugin (bug 024/#167). Nothing else from dev-only scripts/
        # may leak.
        shipped_scripts = {n for n in self.names if n.startswith("scripts/")}
        self.assertEqual(
            shipped_scripts,
            set(install_contract.RELEASE_INCLUDE_SCRIPT_FILES),
            "Claude zip scripts/ must equal RELEASE_INCLUDE_SCRIPT_FILES; "
            f"got {sorted(shipped_scripts)!r}",
        )
        self.assertIn("scripts/spec_lint.py", shipped_scripts)

    def test_no_pycache_or_dsstore(self):
        junk = [n for n in self.names if "__pycache__" in n or n.endswith(".pyc")
                or Path(n).name == ".DS_Store"]
        self.assertEqual(junk, [])

    def test_claude_default_output_name(self):
        # default output path is dist/jig-<host>-v<version>.zip
        self.assertEqual(
            build_release_zip.default_output_path(REPO_ROOT, "claude", _CLAUDE_VERSION),
            REPO_ROOT / "dist" / f"jig-claude-v{_CLAUDE_VERSION}.zip",
        )

    def test_claude_message_may_be_drag_droppable(self):
        # Claude messaging keeps the drag-droppable phrasing (allowed, not required).
        self.assertIn("claude", self.output.lower())


# ---------------------------------------------------------------------------
# AC2 — Codex zip is the hosts/codex/ marketplace root.
# ---------------------------------------------------------------------------


class CodexZipShapeTests(unittest.TestCase):
    def setUp(self):
        self.zip_path, self.output = _build_once("codex", _CODEX_VERSION)
        self.addCleanup(shutil.rmtree, self.zip_path.parent, ignore_errors=True)
        with zipfile.ZipFile(self.zip_path) as zf:
            self.names = set(zf.namelist())

    def test_marketplace_json_at_root(self):
        self.assertIn(".agents/plugins/marketplace.json", self.names)

    def test_codex_plugin_json_present(self):
        self.assertIn("plugins/jig/.codex-plugin/plugin.json", self.names)

    def test_no_hosts_prefix(self):
        leaked = [n for n in self.names if n.startswith("hosts/")]
        self.assertEqual(leaked, [], f"arcnames must be relative to hosts/codex/; got {leaked!r}")

    def test_codex_default_output_name(self):
        self.assertEqual(
            build_release_zip.default_output_path(REPO_ROOT, "codex", _CODEX_VERSION),
            REPO_ROOT / "dist" / f"jig-codex-v{_CODEX_VERSION}.zip",
        )


# ---------------------------------------------------------------------------
# AC3 — Codex language is exact: extract-then-add, never directly-installable.
# ---------------------------------------------------------------------------


class CodexLanguageTests(unittest.TestCase):
    def test_codex_build_message_says_extract_then_add(self):
        _, output = _build_once("codex", _CODEX_VERSION)
        self.assertIn("extract-then-add", output)

    def test_codex_build_message_not_directly_installable(self):
        _, output = _build_once("codex", _CODEX_VERSION)
        lowered = output.lower()
        self.assertNotIn("drag-droppable", lowered)
        self.assertNotIn("directly-installable", lowered)
        self.assertNotIn("directly installable", lowered)

    @unittest.skipUnless(sys.version_info >= (3, 11),
                         "codex smoke validation needs tomllib (3.11+); jig is zero-dep")
    def test_codex_smoke_message_says_extract_then_add(self):
        zip_path, _ = _build_once("codex", _CODEX_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        sink = io.StringIO()
        code = build_release_zip.smoke_test("codex", zip_path, out=sink)
        self.assertEqual(code, 0, msg=sink.getvalue())
        self.assertIn("extract-then-add", sink.getvalue())

    @unittest.skipUnless(sys.version_info >= (3, 11),
                         "codex smoke validation needs tomllib (3.11+); jig is zero-dep")
    def test_codex_smoke_message_not_directly_installable(self):
        zip_path, _ = _build_once("codex", _CODEX_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        sink = io.StringIO()
        build_release_zip.smoke_test("codex", zip_path, out=sink)
        lowered = sink.getvalue().lower()
        self.assertNotIn("drag-droppable", lowered)
        self.assertNotIn("directly-installable", lowered)


# ---------------------------------------------------------------------------
# AC4 — version coherence vs the host's own committed manifest (exit 2).
# Edge case: a stale hosts/ (manifest != requested) must fail, not ship.
# ---------------------------------------------------------------------------


class VersionCoherenceTests(unittest.TestCase):
    def test_claude_version_mismatch_exits_2(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-claude-mismatch-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / "jig-claude-v9.9.9.zip"
        sink = io.StringIO()
        code = build_release_zip.build(
            host="claude",
            hosts_root=HOSTS_ROOT,
            version="9.9.9",
            output_path=out,
            out=sink,
        )
        self.assertEqual(code, 2)
        self.assertIn("9.9.9", sink.getvalue())
        self.assertIn("mislabeled", sink.getvalue())

    def test_codex_version_mismatch_exits_2(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-codex-mismatch-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / "jig-codex-v9.9.9.zip"
        sink = io.StringIO()
        code = build_release_zip.build(
            host="codex",
            hosts_root=HOSTS_ROOT,
            version="9.9.9",
            output_path=out,
            out=sink,
        )
        self.assertEqual(code, 2)
        self.assertIn("9.9.9", sink.getvalue())
        self.assertIn("mislabeled", sink.getvalue())

    def test_stale_hosts_tree_fails_coherence(self):
        # Edge case: a hosts/ tree whose manifest version differs from the
        # requested release version must refuse, not ship a stale package.
        # Build a tmp hosts tree by copying the committed Claude package and
        # bumping its manifest, then request the OLD version.
        tmp_hosts = Path(tempfile.mkdtemp(prefix="jig-stale-hosts-"))
        self.addCleanup(shutil.rmtree, tmp_hosts, ignore_errors=True)
        shutil.copytree(CLAUDE_PKG, tmp_hosts / "claude")
        manifest_path = tmp_hosts / "claude" / ".claude-plugin" / "plugin.json"
        data = json.loads(manifest_path.read_text())
        data["version"] = "9.9.9"  # deliberately different from requested version
        manifest_path.write_text(json.dumps(data))

        out = tmp_hosts / "out.zip"
        sink = io.StringIO()
        code = build_release_zip.build(
            host="claude",
            hosts_root=tmp_hosts,
            version=_CLAUDE_VERSION,  # request the (now stale) old version
            output_path=out,
            out=sink,
        )
        self.assertEqual(code, 2, msg=sink.getvalue())
        self.assertIn("mislabeled", sink.getvalue())
        self.assertFalse(out.is_file(), "must not produce a mislabeled artifact")


# ---------------------------------------------------------------------------
# Determinism — two builds -> identical bytes, per host.
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_claude_two_builds_identical(self):
        a, _ = _build_once("claude", _CLAUDE_VERSION)
        b, _ = _build_once("claude", _CLAUDE_VERSION)
        self.addCleanup(shutil.rmtree, a.parent, ignore_errors=True)
        self.addCleanup(shutil.rmtree, b.parent, ignore_errors=True)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_codex_two_builds_identical(self):
        a, _ = _build_once("codex", _CODEX_VERSION)
        b, _ = _build_once("codex", _CODEX_VERSION)
        self.addCleanup(shutil.rmtree, a.parent, ignore_errors=True)
        self.addCleanup(shutil.rmtree, b.parent, ignore_errors=True)
        self.assertEqual(a.read_bytes(), b.read_bytes())


# ---------------------------------------------------------------------------
# AC5 — per-host smoke tests name the host.
# ---------------------------------------------------------------------------


class SmokeTests(unittest.TestCase):
    def test_claude_smoke_passes_and_names_host(self):
        zip_path, _ = _build_once("claude", _CLAUDE_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        sink = io.StringIO()
        code = build_release_zip.smoke_test("claude", zip_path, out=sink)
        self.assertEqual(code, 0, msg=sink.getvalue())
        self.assertIn("claude", sink.getvalue().lower())

    @unittest.skipUnless(sys.version_info >= (3, 11),
                         "codex smoke validation needs tomllib (3.11+); jig is zero-dep")
    def test_codex_smoke_passes_and_names_host(self):
        zip_path, _ = _build_once("codex", _CODEX_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        sink = io.StringIO()
        code = build_release_zip.smoke_test("codex", zip_path, out=sink)
        self.assertEqual(code, 0, msg=sink.getvalue())
        self.assertIn("codex", sink.getvalue().lower())

    def test_smoke_fails_on_missing_zip_names_host(self):
        sink = io.StringIO()
        code = build_release_zip.smoke_test(
            "claude", Path("/nonexistent/jig-claude-v999.zip"), out=sink
        )
        self.assertNotEqual(code, 0)
        self.assertIn("not found", sink.getvalue())
        self.assertIn("claude", sink.getvalue().lower())


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


class CliTests(unittest.TestCase):
    def test_main_build_claude(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-cli-claude-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / f"jig-claude-v{_CLAUDE_VERSION}.zip"
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main([
                "build_release_zip.py", "--host", "claude",
                "--version", _CLAUDE_VERSION, "--output", str(out),
            ])
        finally:
            sys.stdout = original
        self.assertEqual(code, 0, msg=captured.getvalue())
        self.assertTrue(out.is_file())

    def test_main_build_codex(self):
        tmp = Path(tempfile.mkdtemp(prefix="jig-cli-codex-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        out = tmp / f"jig-codex-v{_CODEX_VERSION}.zip"
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main([
                "build_release_zip.py", "--host", "codex",
                "--version", _CODEX_VERSION, "--output", str(out),
            ])
        finally:
            sys.stdout = original
        self.assertEqual(code, 0, msg=captured.getvalue())
        self.assertTrue(out.is_file())

    def test_main_build_requires_host(self):
        # argparse should reject build mode without --host (required arg).
        original_err = sys.stderr
        sys.stderr = io.StringIO()
        try:
            with self.assertRaises(SystemExit):
                build_release_zip.main([
                    "build_release_zip.py", "--version", _CLAUDE_VERSION,
                ])
        finally:
            sys.stderr = original_err

    def test_main_smoke_requires_host(self):
        zip_path, _ = _build_once("claude", _CLAUDE_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        original_err = sys.stderr
        sys.stderr = io.StringIO()
        try:
            with self.assertRaises(SystemExit):
                build_release_zip.main([
                    "build_release_zip.py", "--smoke-test", str(zip_path),
                ])
        finally:
            sys.stderr = original_err

    def test_main_smoke_via_cli(self):
        zip_path, _ = _build_once("claude", _CLAUDE_VERSION)
        self.addCleanup(shutil.rmtree, zip_path.parent, ignore_errors=True)
        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = build_release_zip.main([
                "build_release_zip.py", "--host", "claude",
                "--smoke-test", str(zip_path),
            ])
        finally:
            sys.stdout = original
        self.assertEqual(code, 0, msg=captured.getvalue())


if __name__ == "__main__":
    unittest.main()
