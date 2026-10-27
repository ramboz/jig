"""Tests for slice 121-01 — genesis spec 000 seed + state-following pointers
(ADR-0067 decisions 1, 2, 4, 7).

Run: python3 skills/scaffold-init/test_scaffold_genesis.py
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

LEGACY_SPEC = (
    "---\nstatus: DONE\nskill: scaffold-init\n---\n\n# Spec 001: Adopt jig\n"
)
_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def run_scaffold(target: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), *args, str(target)],
        capture_output=True, text=True, env=env,
    )


def dangling_dir_links(md: Path, base: Path):
    """Markdown link targets in `md` (relative to `base`) whose path does not
    exist. Absolute URLs / mailto are skipped."""
    bad = []
    for m in _LINK.finditer(md.read_text()):
        tgt = m.group(1)
        if re.match(r"^[a-z]+:", tgt) or tgt.startswith("/"):
            continue
        if not (base / tgt).exists():
            bad.append(tgt)
    return bad


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-genesis-")
        self.target = Path(self.tmpdir) / "demo-project"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def scaffold(self, *args):
        r = run_scaffold(self.target, *args)
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr}\nstdout={r.stdout}")
        return r


class GenesisSeedShapeTests(_Tmp):
    def test_ac1_shape_and_no_other_spec_dirs(self):  # AC1
        self.scaffold()
        specs = self.target / "docs" / "specs"
        spec = (specs / "000-adopt-jig" / "spec.md").read_text()
        sl = (specs / "000-adopt-jig" / "slice-01-bootstrap.md").read_text()
        self.assertIn("# Spec 000: Adopt jig", spec)
        self.assertIn("## Slice 000-01 — bootstrap", sl)
        self.assertRegex(spec, r"(?m)^status:\s*DONE\s*$")
        self.assertRegex(sl, r"(?m)^status:\s*DONE\s*$")
        dirs = sorted(p.name for p in specs.iterdir() if p.is_dir())
        self.assertEqual(dirs, ["000-adopt-jig"])

    def test_ac1_non_default_docs_root_and_codex(self):  # AC1
        self.scaffold("--docs-root", "handbook", "--host", "codex", "--in-repo")
        specs = self.target / "handbook" / "specs"
        self.assertTrue((specs / "000-adopt-jig" / "spec.md").is_file())
        self.assertEqual(
            sorted(p.name for p in specs.iterdir() if p.is_dir()),
            ["000-adopt-jig"])

    def test_ac2_first_own_spec_is_001(self):  # AC2
        self.scaffold()
        subprocess.run(["git", "init", "-q"], cwd=self.target, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.target, check=True)
        subprocess.run(
            ["git", "-c", "user.email=a@b.c", "-c", "user.name=t",
             "commit", "-qm", "init"], cwd=self.target, check=True,
            capture_output=True)
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        # `new` commits the reservation; CI runners have no git identity.
        env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "a@b.c",
                    "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "a@b.c"})
        r = subprocess.run(
            [sys.executable, str(WORKFLOW), "new", "my-feature", "--no-push",
             "--project-dir", str(self.target)],
            capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("reserved 001-my-feature", r.stdout)
        self.assertTrue(
            (self.target / "docs/specs/001-my-feature/spec.md").is_file())

    def test_ac3_no_placeholder_or_legacy_names(self):  # AC3
        self.scaffold()
        banned = ("002-first-spec", "001-adopt-jig", "spec 002")
        for path in [self.target / "CLAUDE.md",
                     self.target / "docs/adoption-readiness.md",
                     *(self.target / "docs/specs").rglob("*.md")]:
            text = path.read_text()
            for b in banned:
                self.assertNotIn(b, text, f"{path.name} names {b!r}")
        spec = (self.target / "docs/specs/000-adopt-jig/spec.md").read_text()
        slice_ = (self.target
                  / "docs/specs/000-adopt-jig/slice-01-bootstrap.md").read_text()
        ready = (self.target / "docs/adoption-readiness.md").read_text()
        for text in (spec, ready):
            self.assertIn("/jig:spec-workflow new <slug>", text)
            self.assertIn("`001`", text)
        self.assertIn("/jig:spec-workflow new <slug>", slice_)
        self.assertIn("kept by default", spec)
        self.assertIn("workflow.py retire-genesis", spec)

    def test_ac4_board_one_row_and_check_board(self):  # AC4
        self.scaffold()
        board = (self.target / "docs/specs/README.md").read_text()
        rows = [ln for ln in board.splitlines()
                if ln.startswith("| [")]
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("000-adopt-jig", rows[0])
        self.assertIn("000-01 — bootstrap", rows[0])
        self.assertIn("**DONE**", rows[0])
        r = subprocess.run(
            [sys.executable, str(WORKFLOW), "check-board", str(self.target)],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_ac5_verify_seed_and_docs_pass(self):  # AC5
        import verify_install
        self.scaffold()
        ok, msg = verify_install.check_scaffold_seed_present(self.target)
        self.assertTrue(ok, msg)
        buf = io.StringIO()
        rc = verify_install.run_completion_summary(
            self.target, with_machinery=False, seed_expected=True, out=buf)
        self.assertEqual(rc, 0, buf.getvalue())
        (self.target / "docs/specs/000-adopt-jig/spec.md").unlink()
        ok, _ = verify_install.check_scaffold_seed_present(self.target)
        self.assertFalse(ok)


class SkillProseTests(unittest.TestCase):
    def test_ac6_spec_workflow_resolves_exemplar_by_state(self):  # AC6
        body = (REPO_ROOT / "skills/spec-workflow/SKILL.md").read_text()
        self.assertNotIn("002-first-spec", body)
        refs = [ln for ln in body.splitlines() if "adopt-jig" in ln]
        self.assertTrue(refs)
        # Every paragraph naming adopt-jig also names the genesis 000 form
        # and the DONE-slice fallback (state resolution, not a sole path).
        for para in body.split("\n\n"):
            if "adopt-jig" not in para:
                continue
            self.assertIn("000-adopt-jig", para)
            self.assertIn("DONE", para)

    def test_ac6_scaffold_init_next_steps(self):  # AC6
        body = (REPO_ROOT / "skills/scaffold-init/SKILL.md").read_text()
        a = body.index("## Immediate next steps")
        step = body[a:a + 1500]
        self.assertIn("`001`", step)
        self.assertIn("/jig:spec-workflow new <slug>", step)


class GenesisPointerTests(_Tmp):
    """AC7 — pointers name the genesis dir that is actually there."""

    def _rendered(self, docs_root="docs"):
        base = self.target if docs_root == "." else self.target / docs_root
        return [
            (self.target / "CLAUDE.md", self.target),
            (self.target / "AGENTS.md", self.target),
            (base / "adoption-readiness.md", base),
        ]

    def _assert_no_dangling(self, docs_root="docs"):
        seen = 0
        for md, base in self._rendered(docs_root):
            if not md.is_file():
                continue
            seen += 1
            self.assertEqual(dangling_dir_links(md, base), [],
                             f"{md.name} links a missing target")
        self.assertGreaterEqual(seen, 2)

    def test_greenfield_points_at_000_all_hosts_and_roots(self):
        for host, root in (("claude", "docs"), ("codex", "handbook"),
                           ("copilot", ".")):
            with self.subTest(host=host, root=root):
                shutil.rmtree(self.target)
                self.target.mkdir()
                mode = [] if host == "copilot" else ["--in-repo"]
                self.scaffold("--host", host, "--docs-root", root, *mode)
                primer = "CLAUDE.md" if host == "claude" else "AGENTS.md"
                text = (self.target / primer).read_text()
                self.assertIn("000-adopt-jig", text)
                for b in ("002-first-spec", "001-adopt-jig", "spec 002"):
                    self.assertNotIn(b, text, f"{primer} names {b!r}")
                self._assert_no_dangling(root)

    def _legacy_project(self):
        """A project scaffolded before spec 121: only `001-adopt-jig`."""
        legacy = self.target / "docs/specs/001-adopt-jig"
        legacy.mkdir(parents=True)
        (legacy / "spec.md").write_text(LEGACY_SPEC)

    def test_force_rescaffold_of_legacy_seed_points_at_001(self):
        for host, primer in (("claude", "CLAUDE.md"), ("codex", "AGENTS.md")):
            with self.subTest(host=host):
                self._legacy_project()
                self.scaffold("--force", "--host", host)
                text = (self.target / primer).read_text()
                ready = (self.target / "docs/adoption-readiness.md").read_text()
                for t in (text, ready):
                    self.assertIn("001-adopt-jig", t)
                    self.assertNotIn("000-adopt-jig", t)
                self.assertFalse(
                    (self.target / "docs/specs/000-adopt-jig").exists())
                self._assert_no_dangling()
                shutil.rmtree(self.target)
                self.target.mkdir()

    def test_force_rescaffold_no_genesis_but_own_spec_no_pointer(self):
        own = self.target / "docs/specs/007-my-spec"
        own.mkdir(parents=True)
        (own / "spec.md").write_text("# mine\n")
        self.scaffold("--force")
        self.scaffold("--force", "--host", "codex")
        for name in ("CLAUDE.md", "AGENTS.md"):
            text = (self.target / name).read_text()
            self.assertNotIn("adopt-jig", text)
        ready = (self.target / "docs/adoption-readiness.md").read_text()
        self.assertNotIn("adopt-jig", ready)
        self.assertFalse((self.target / "docs/specs/000-adopt-jig").exists())
        self._assert_no_dangling()

    def test_legacy_slug_without_scaffold_frontmatter_is_not_genesis(self):
        own = self.target / "docs/specs/001-adopt-jig"
        own.mkdir(parents=True)
        (own / "spec.md").write_text("---\nstatus: DONE\n---\n# user spec\n")
        self.scaffold("--force")
        self.assertNotIn("adopt-jig",
                         (self.target / "CLAUDE.md").read_text())

    def test_existing_000_is_pointed_at(self):
        g = self.target / "docs/specs/000-adopt-jig"
        g.mkdir(parents=True)
        (g / "spec.md").write_text(LEGACY_SPEC.replace("001", "000"))
        self.scaffold("--force")
        self.assertIn("000-adopt-jig",
                      (self.target / "CLAUDE.md").read_text())
        self._assert_no_dangling()


if __name__ == "__main__":
    unittest.main()
