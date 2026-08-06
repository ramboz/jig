"""AC1/AC2/AC3/AC5 scaffold-output tests for slice 106-01 (ADR-0051).

Scaffolding a fixture repo must write the governance plane (CODEOWNERS, the
`jig-governance` CI workflow, and the governance doc) and record
`protected_paths` in `scaffold.json` — in BOTH plugin-only (default) and
`--in-repo` (with-machinery) modes.

Run from repo root:
    python3 -m unittest skills.scaffold-init.test_scaffold_governance
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
sys.path.insert(0, str(REPO_ROOT / "skills" / "scaffold-init"))
import governance  # noqa: E402


def run_scaffold(target: Path, *extra) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), str(target), *extra],
        capture_output=True, text=True, env=env,
    )


class _GovernancePlaneMixin:
    """Asserts the scaffolded governance plane, parametrized by scaffold mode."""

    EXTRA: tuple = ()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jig-gov-")
        self.target = Path(self.tmp) / "demo"
        self.target.mkdir()
        r = run_scaffold(self.target, *self.EXTRA)
        self.assertEqual(r.returncode, 0, f"scaffold failed: {r.stderr}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_codeowners_written(self):  # AC1
        codeowners = self.target / "CODEOWNERS"
        self.assertTrue(codeowners.is_file())
        text = codeowners.read_text()
        for glob in governance.PROTECTED_PATHS:
            self.assertIn(glob, text)
        self.assertIn("@OWNER", text)

    def test_ci_workflow_written(self):  # AC2
        wf = self.target / ".github" / "workflows" / "jig-governance.yml"
        self.assertTrue(wf.is_file())
        text = wf.read_text()
        self.assertIn("jig-governance", text)
        self.assertIn("inert", text.lower())

    def test_governance_doc_written(self):  # AC5
        doc = self.target / "docs" / "governance.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text().lower()
        self.assertIn("branch protection", text)
        self.assertIn("inert", text)
        self.assertIn("surface-and-stop", text)

    def test_protected_paths_in_manifest(self):  # AC3
        data = json.loads((self.target / "scaffold.json").read_text())
        self.assertEqual(
            data.get("protected_paths"), list(governance.PROTECTED_PATHS)
        )


class PluginOnlyGovernanceTests(_GovernancePlaneMixin, unittest.TestCase):
    EXTRA = ()  # default = plugin-only


class InRepoGovernanceTests(_GovernancePlaneMixin, unittest.TestCase):
    EXTRA = ("--in-repo",)


if __name__ == "__main__":
    unittest.main()
