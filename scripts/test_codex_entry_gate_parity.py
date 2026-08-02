"""Codex host-parity tests for the lifecycle entry gate — slice 098-02.

Packaging parity (provable here) + host-transform correctness + a behavioral
spot-check on the SHIPPED Codex copy of the hook logic. Runtime payload/cadence
parity (AC2/AC5) needs the Codex runtime and is recorded honestly in the host
support matrix (docs/architecture.md), not asserted here.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEX_PKG = REPO_ROOT / "hosts" / "codex" / "plugins" / "jig"
CODEX_HOOKS_JSON = CODEX_PKG / "hooks" / "hooks.json"
CODEX_HOOK_SH = CODEX_PKG / "hooks" / "scripts" / "jig-entry-gate.sh"
CODEX_HOOK_LIB = CODEX_PKG / "hooks" / "scripts" / "lib" / "entry_gate.py"


def _codex_hook_commands() -> list:
    data = json.loads(CODEX_HOOKS_JSON.read_text())
    out = []
    for event, entries in data.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                out.append((event, entry.get("matcher", ""), hook.get("command", "")))
    return out


class CodexEntryGatePackagingTests(unittest.TestCase):
    """AC1 — the generated Codex package carries the gate, registered."""

    def test_hook_registered_in_posttooluse_matcher_with_plugin_root(self):
        rows = [
            (evt, m, c) for (evt, m, c) in _codex_hook_commands()
            if "jig-entry-gate.sh" in c
        ]
        self.assertEqual(len(rows), 1, rows)
        evt, matcher, command = rows[0]
        self.assertEqual(evt, "PostToolUse")
        self.assertEqual(matcher, "Edit|Write|MultiEdit")
        self.assertIn("${PLUGIN_ROOT}/hooks/scripts/jig-entry-gate.sh", command)

    def test_hook_script_and_lib_present_in_package(self):
        self.assertTrue(CODEX_HOOK_SH.is_file())
        self.assertTrue(CODEX_HOOK_LIB.is_file())
        # The helper's _common import target ships beside skills/ in the package.
        self.assertTrue((CODEX_PKG / "skills" / "_common" / "project_layout.py").is_file())


class CodexEntryGateTransformTests(unittest.TestCase):
    """AC3/host-transform — the Codex copy is the same logic with the Codex
    host substitutions applied, not a divergent implementation."""

    def test_wrapper_reads_codex_project_dir(self):
        text = CODEX_HOOK_SH.read_text()
        self.assertIn("CODEX_PROJECT_DIR", text)
        self.assertNotIn("CLAUDE_PROJECT_DIR", text)

    def test_infra_dirs_rewritten_to_codex(self):
        text = CODEX_HOOK_LIB.read_text()
        self.assertIn('".codex"', text)
        # The blind `.claude`→`.codex` rewrite must leave no `.claude` literal
        # in the Codex copy (mirror of the CODEX_PROJECT_DIR substitution check).
        self.assertNotIn('".claude"', text)
        # The host-agnostic marker dir must NOT be rewritten.
        self.assertIn('Path(".jig") / "spec-ref"', text)


class CodexEntryGateBehaviorTests(unittest.TestCase):
    """AC7/boundary — the SHIPPED Codex logic behaves: nudges on source,
    treats the Codex `.codex/` infra dir as non-source, honors the opt-out."""

    @classmethod
    def setUpClass(cls):
        # Load the Codex-shipped copy under a distinct module name. We add the
        # Codex package's skills/ to sys.path for its `from _common import
        # project_layout`; note that if a sibling suite already imported `_common`
        # in this process it stays cached (the two copies are byte-identical, so
        # this is harmless — the point of this suite is the SHIPPED entry_gate
        # logic + Codex substitutions, not _common isolation).
        cls._added_path = str(CODEX_PKG / "skills")
        sys.path.insert(0, cls._added_path)
        spec = importlib.util.spec_from_file_location(
            "codex_entry_gate", CODEX_HOOK_LIB)
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)

    @classmethod
    def tearDownClass(cls):
        try:
            sys.path.remove(cls._added_path)
        except ValueError:
            pass

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()
        self.state.cleanup()

    def _eval(self, file_path, session="c1", env=None):
        payload = {"tool_name": "Edit",
                   "tool_input": {"file_path": file_path},
                   "session_id": session}
        prior = dict(os.environ)
        os.environ["JIG_CLAIM_ID"] = "wt-codex"
        os.environ.pop("JIG_ENTRY_GATE", None)
        if env:
            os.environ.update(env)
        try:
            return self.mod.evaluate(payload, self.root, self.state.name)
        finally:
            os.environ.clear()
            os.environ.update(prior)

    def test_source_edit_nudges(self):
        self.assertIsNotNone(self._eval(str(self.root / "app.py")))

    def test_codex_infra_dir_is_silent(self):
        # The Codex-specific boundary: `.codex/` is infra, not source.
        self.assertIsNone(self._eval(str(self.root / ".codex" / "settings.json")))

    def test_lifecycle_artifact_is_silent(self):
        self.assertIsNone(self._eval(str(self.root / "docs" / "specs" / "098-x" / "spec.md")))

    def test_relocated_docs_root_artifacts_silent_source_nudges(self):
        # AC3 parity on a relocated docs root, resolved via the shipped copy's
        # project_layout (scaffold.json). Artifacts silent; source still nudges.
        (self.root / "scaffold.json").write_text(
            json.dumps({"layout": {"docs_root": "documentation"}}))
        self.assertIsNone(
            self._eval(str(self.root / "documentation" / "specs" / "098-x" / "spec.md")))
        self.assertIsNotNone(self._eval(str(self.root / "documentation" / "app.py"),
                                        session="reloc-src"))

    def test_gitignored_path_is_silent(self):
        # AC3 boundary (a): git check-ignore behaves identically on Codex (it is
        # git, not the host).
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / ".gitignore").write_text("build/\n")
        (self.root / "build").mkdir()
        self.assertIsNone(self._eval(str(self.root / "build" / "out.js")))
        self.assertIsNotNone(self._eval(str(self.root / "app.py"), session="git-src"))

    def test_opt_out_disables_full_token_set(self):
        for token in ("0", "false", "off", "no"):
            self.assertIsNone(
                self._eval(str(self.root / "app.py"), env={"JIG_ENTRY_GATE": token}),
                f"JIG_ENTRY_GATE={token} must disable the gate")

    def test_dual_host_claude_dir_nudges_on_codex_accepted_limit(self):
        # Accepted limit (frame review): the blind `.claude`→`.codex` build
        # rewrite means the Codex copy does NOT treat a `.claude/` dir as infra,
        # so a `.claude/` edit nudges on Codex. Pinned so the limit is explicit
        # and intentional (advisory, fail-open) — see architecture.md AC3 caveat.
        self.assertIsNotNone(self._eval(str(self.root / ".claude" / "settings.json")))


if __name__ == "__main__":
    unittest.main()
