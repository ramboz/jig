# ruff: noqa: E501  (verbatim legacy-template fixtures are long lines)
"""Tests for slice 121-02 — `workflow.py retire-genesis` + the first-done hint
(ADR-0067 decisions 3, 5, 7).

Run: python3 skills/spec-workflow/test_retire_genesis.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAFFOLD = REPO_ROOT / "skills" / "scaffold-init" / "scaffold.py"
WORKFLOW = REPO_ROOT / "skills" / "spec-workflow" / "workflow.py"
sys.path.insert(0, str(REPO_ROOT / "skills"))
sys.path.insert(0, str(WORKFLOW.parent))

import workflow  # noqa: E402

# Verbatim pre-121 seed stub (git 3383e59c:templates/docs/specs/seed/002-first-spec).
LEGACY_STUB = "---\nstatus: DRAFT\n# use_cases: the UC-N id(s) from docs/product-vision.md's `## Use cases`\n# section that this spec serves (spec 068-02 / ADR-0025), e.g. [UC-1, UC-3].\n# Soft/advisory — leave [] when this spec serves no captured behavior, or\n# when the project hasn't adopted the use-case layer. Empty is fine.\nuse_cases: []\n---\n\n# Spec 002: First spec — replace me\n\n## Overview\n\n**Replace this with your first real spec.** Run `/jig:spec-workflow` to\nauthor it, or edit this file by hand. Spec\n[001-adopt-jig](../001-adopt-jig/spec.md) above is a complete `DONE`\nworked example — copy its shape: an overview, a SPIDR decomposition, and\none or more vertical slices in sibling `slice-NN-<short>.md` files.\n\nThis stub is intentionally `DRAFT`, **not**\n`READY_FOR_IMPLEMENTATION`: an empty placeholder is not ready to build,\nand marking it ready would be dishonest. Move it to\n`READY_FOR_IMPLEMENTATION` only once it describes real, testable work.\n\n## Decomposition\n\n**SPIDR axis: _TODO — pick the axis that best splits your work._**\n\n### Slices\n\n1. **`002-01 <name>`** — _TODO: describe the first vertical slice._\n\n## Slice 002-01 — replace-me\n\n**Goal:** _TODO: one sentence stating the end-to-end value this slice\ndelivers. Replace this entire spec with your first real unit of work._\n\n**DoR:**\n- ✅ _TODO: prerequisites that must hold before this becomes\n  `READY_FOR_IMPLEMENTATION`._\n\n**Acceptance Criteria:**\n\n1. **_TODO: first AC._** Sharp, testable, observable from outside.\n\n**DoD:**\n- [ ] All ACs pass; full test suite green (no regressions).\n- [ ] Implementer test coverage exercises each AC with at least one\n      fixture.\n- [ ] Reviewed by `reviewer` subagent. Reviewer prompt built by\n      `review.py`.\n- [ ] Implementation review passed.\n- [ ] Deviation log produced under this slice heading.\n- [ ] Reconciliation review passed.\n\n**Anti-horizontal-phasing check:** _TODO: describe the end-to-end\nobservable value a user gets after this slice lands._\n"

# Verbatim pre-121 primer bullet and adoption-readiness item.
LEGACY_PRIMER_BULLET = '- [001-adopt-jig](docs/specs/001-adopt-jig/spec.md) - DONE worked example to imitate; see [docs/specs/README.md](docs/specs/README.md) for the status board.'
LEGACY_READINESS_ITEM = '1. **Read the worked example** — your scaffold seeded a `DONE` reference\n   spec, [001-adopt-jig](specs/001-adopt-jig/spec.md). Skim it to see the\n   shape of a finished slice, then check the\n   [status board](specs/README.md).\n'

LEGACY_SEED_SPEC = (
    "---\nstatus: DONE\nskill: scaffold-init\n---\n\n# Spec 001: Adopt jig\n"
)
GENESIS_SPEC = (
    "---\nstatus: DONE\nskill: scaffold-init\n---\n\n# Spec 000: Adopt jig\n"
)


EDITED_STUB = LEGACY_STUB.replace(
    "_TODO: describe the first vertical slice._", "Build the thing.")


def user_spec(name: str, status: str = "DRAFT", body: str = "") -> str:
    return (
        f"---\nstatus: {status}\n---\n\n# Spec {name}\n\n{body}\n"
        f"## Slice {name[:3]}-01 — one\n\n**Goal:** x\n"
    )


def user_slice(num: str, status: str) -> str:
    return f"---\nstatus: {status}\n---\n\n## Slice {num}-01 — one\n\n**Goal:** x\n"


PRIMER_NEW = (
    "### Active specs\n"
    "- [000-adopt-jig](docs/specs/000-adopt-jig/spec.md) - DONE worked example "
    "to imitate; see [docs/specs/README.md](docs/specs/README.md) for the "
    "status board.\n\n### Deferred decisions\n- See x.\n"
)
READINESS_NEW = (
    "## Your first 30 minutes\n\n"
    "1. **Read the worked example** — your scaffold seeded a `DONE` reference\n"
    "   spec, [000-adopt-jig](specs/000-adopt-jig/spec.md). Skim it to see the\n"
    "   shape of a finished slice, then check the\n"
    "   [status board](specs/README.md).\n"
    "2. **Set your vision** — go.\n"
)


BOARD = "# Spec Status Board\n\n| Spec | Slice | Status | Notes |\n|------|-------|--------|-------|\n"


def run_wf(*args, cwd=None, env=None):
    e = os.environ.copy()
    e.update(env or {})
    return subprocess.run(
        [sys.executable, str(WORKFLOW), *args],
        capture_output=True, text=True, env=e, cwd=cwd,
    )


class _Proj(unittest.TestCase):
    docs_root = "docs"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jig-retire-")
        self.root = Path(self.tmp) / "proj"
        self.root.mkdir()
        if self.docs_root != "docs":
            (self.root / "scaffold.json").write_text(json.dumps(
                {"layout": {"docs_root": self.docs_root}}))
        self.base = self.root if self.docs_root == "." else self.root / self.docs_root
        self.specs = self.base / "specs"
        self.specs.mkdir(parents=True)
        (self.specs / "README.md").write_text(BOARD)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def w(self, rel: str, text: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def spec(self, name: str, spec_text: str, slices=None):
        self.w(self.specs.relative_to(self.root) / name / "spec.md", spec_text)
        for fn, txt in (slices or {}).items():
            self.w(self.specs.relative_to(self.root) / name / fn, txt)

    def new_genesis(self):
        self.spec("000-adopt-jig", GENESIS_SPEC,
                  {"slice-01-bootstrap.md": user_slice("000", "DONE")})

    def legacy(self, stub: str = LEGACY_STUB):
        self.spec("001-adopt-jig", LEGACY_SEED_SPEC)
        self.spec("002-first-spec", stub)

    def user(self, name="003-mine", status="DRAFT", body=""):
        self.spec(name, user_spec(name, status, body),
                  {"slice-01-one.md": user_slice(name[:3], status)})

    def retire(self, *extra):
        return run_wf("retire-genesis", "--project-dir", str(self.root), *extra)

    def snapshot(self):
        out = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                out[str(p.relative_to(self.root))] = p.read_bytes()
        return out


class RetireNewShapeTests(_Proj):
    def test_ac1_removes_dir_and_board_row(self):
        self.new_genesis()
        self.user()
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.specs / "000-adopt-jig").exists())
        self.assertIn("000-adopt-jig", r.stdout)
        board = (self.specs / "README.md").read_text()
        self.assertNotIn("000-adopt-jig", board)
        self.assertIn("003-mine", board)


class RetireLegacyShapeTests(_Proj):
    def test_ac2_untouched_stub_removed_with_seed(self):
        self.legacy()
        self.user("003-mine")
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.specs / "001-adopt-jig").exists())
        self.assertFalse((self.specs / "002-first-spec").exists())

    def test_ac2_edited_but_draft_heading_intact_stub_kept(self):
        self.legacy(EDITED_STUB)
        self.user("003-mine")
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.specs / "001-adopt-jig").exists())
        self.assertTrue((self.specs / "002-first-spec").exists())
        self.assertIn("002-first-spec", r.stdout)

    def test_ac2_each_marker_edit_keeps_stub(self):
        for marker in ("status: DRAFT", "# Spec 002: First spec — replace me",
                       "**Replace this with your first real spec.**",
                       "## Slice 002-01 — replace-me",
                       "_TODO: describe the first vertical slice._"):
            with self.subTest(marker=marker):
                self.tearDown()
                self.setUp()
                self.legacy(LEGACY_STUB.replace(marker, "changed", 1))
                self.user("003-mine")
                self.assertEqual(self.retire().returncode, 0)
                self.assertTrue((self.specs / "002-first-spec").exists())

    def test_ac2_stub_dir_with_extra_slice_file_kept(self):
        self.legacy()
        self.w(self.specs.relative_to(self.root) / "002-first-spec" / "slice-01-x.md", "x")
        self.user("003-mine")
        self.assertEqual(self.retire().returncode, 0)
        self.assertTrue((self.specs / "002-first-spec" / "slice-01-x.md").exists())
        self.assertFalse((self.specs / "001-adopt-jig").exists())

    def test_ac2_unrecognised_001_reported_and_left(self):
        self.spec("001-adopt-jig", "---\nstatus: DONE\n---\n\n# mine\n")
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.specs / "001-adopt-jig").exists())
        self.assertIn("001-adopt-jig", r.stdout)
        self.assertIn("not recognised as the jig seed; left in place", r.stdout)

    def test_ac2_detection_is_by_slug_not_number(self):
        self.spec("001-other", "---\nstatus: DONE\nskill: scaffold-init\n---\n")
        self.new_genesis()
        self.user()
        self.assertEqual(self.retire().returncode, 0)
        self.assertTrue((self.specs / "001-other").exists())


class RewriteTests(_Proj):
    def seed_pointers(self, primer, readiness):
        self.w("CLAUDE.md", "# P\n\n" + primer)
        self.w("AGENTS.md", "# A\n\n" + primer)
        self.w(self.base.relative_to(self.root) / "adoption-readiness.md"
               if self.docs_root != "." else "adoption-readiness.md", readiness)

    def primer(self, text):
        return text if self.docs_root == "docs" else text.replace(
            "docs/specs/", "specs/" if self.docs_root == "." else self.docs_root + "/specs/")

    def check_new(self):
        self.new_genesis()
        self.user()
        primer = self.primer(PRIMER_NEW)
        readiness = READINESS_NEW
        self.seed_pointers(primer, readiness)
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in ("CLAUDE.md", "AGENTS.md"):
            t = (self.root / f).read_text()
            self.assertNotIn("adopt-jig", t, f)
            self.assertIn("### Active specs", t)
            self.assertIn("### Deferred decisions", t)
        rd = (self.base / "adoption-readiness.md").read_text()
        self.assertNotIn("adopt-jig", rd)
        self.assertNotIn("worked example", rd)
        self.assertNotIn("shape of a finished slice", rd)
        self.assertNotIn("[status board]", rd)
        self.assertTrue(rd.rstrip().endswith("2. **Set your vision** — go."))

    def test_ac3_new_shape_default_root(self):  # AC3
        self.check_new()

    def test_ac3_legacy_primer_bullet_and_readiness_item(self):  # AC3
        self.legacy()
        self.user()
        self.seed_pointers(
            self.primer("### Active specs\n" + LEGACY_PRIMER_BULLET + "\n\n### Deferred decisions\n- x\n"),
            "## Your first 30 minutes\n\n" + LEGACY_READINESS_ITEM + "2. **Set your vision** — go.\n")
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in ("CLAUDE.md", "AGENTS.md"):
            t = (self.root / f).read_text()
            self.assertNotIn("001-adopt-jig", t)
            self.assertNotIn("imitate", t)
            self.assertIn("### Deferred decisions", t)
        rd = (self.base / "adoption-readiness.md").read_text()
        self.assertNotIn("001-adopt-jig", rd)
        self.assertNotIn("worked example", rd)
        self.assertNotIn("shape of a finished", rd)
        self.assertIn("2. **Set your vision**", rd)

    def test_ac3_kept_legacy_stub_link_unlinked(self):  # AC3
        self.legacy(EDITED_STUB)
        self.user()
        self.assertEqual(self.retire().returncode, 0)
        t = (self.specs / "002-first-spec" / "spec.md").read_text()
        self.assertNotIn("](../001-adopt-jig/spec.md)", t)
        self.assertIn("`001-adopt-jig`", t)
        self.assertIn("Build the thing.", t)

    def test_ac3_user_spec_link_reported_not_rewritten(self):  # AC3
        self.new_genesis()
        self.user("003-mine", body="See [the seed](../000-adopt-jig/spec.md).")
        before = (self.specs / "003-mine" / "spec.md").read_text()
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.specs / "003-mine" / "spec.md").read_text(), before)
        self.assertIn("003-mine", r.stdout)
        self.assertIn("000-adopt-jig", r.stdout)
        self.assertIn("not rewritten", r.stdout)

    def test_ac3_other_links_and_items_untouched(self):  # AC3
        self.new_genesis()
        self.user()
        self.w("CLAUDE.md", self.primer("- [a](docs/foo.md) keep\n- [000-adopt-jig](docs/specs/000-adopt-jig/spec.md) x\n  cont\n- b\n"))
        self.assertEqual(self.retire().returncode, 0)
        self.assertEqual((self.root / "CLAUDE.md").read_text(),
                         self.primer("- [a](docs/foo.md) keep\n- b\n"))

    def test_ac3_inline_link_becomes_backticked_text(self):  # AC3
        self.new_genesis()
        self.user()
        self.w("AGENTS.md", self.primer("See [seed](docs/specs/000-adopt-jig/spec.md#x) now.\n"))
        self.assertEqual(self.retire().returncode, 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "See `seed` now.\n")


class RewriteDotRootTests(RewriteTests):
    docs_root = "."

    def test_ac3_new_shape_default_root(self):  # AC3 (dot root)
        self.check_new()


class RewriteCustomRootTests(RewriteTests):
    docs_root = "handbook"

    def test_ac3_new_shape_default_root(self):  # AC3 (custom root)
        self.check_new()


class NoopRefuseDryRunTests(_Proj):
    def test_ac4_no_genesis_noop(self):
        self.user()
        before = self.snapshot()
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing to retire", r.stdout.lower())
        self.assertEqual(self.snapshot(), before)

    def test_ac4_refuses_when_only_genesis(self):
        self.new_genesis()
        self.w("CLAUDE.md", PRIMER_NEW)
        before = self.snapshot()
        r = self.retire()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("first spec", r.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_ac4_refuses_when_only_legacy_seed_and_untouched_stub(self):
        self.legacy()
        before = self.snapshot()
        r = self.retire()
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_ac4_dry_run_writes_nothing(self):
        self.new_genesis()
        self.user()
        self.w("CLAUDE.md", PRIMER_NEW)
        before = self.snapshot()
        r = self.retire("--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("000-adopt-jig", r.stdout)
        self.assertIn("CLAUDE.md", r.stdout)
        self.assertEqual(self.snapshot(), before)


class FirstDoneHintTests(_Proj):
    HINT = "retire-genesis"

    def finish(self, name):
        spec_md = self.specs / name / "spec.md"
        # walk the slice to DONE with the evidence/dep gates bypassed
        env = {"JIG_REVIEW_EVIDENCE_GATE": "0", "JIG_CROSSREF_GATE": "0"}
        for st in ("READY_FOR_IMPLEMENTATION", "IN_PROGRESS", "REVIEWED",
                   "RECONCILED", "DONE"):
            last = run_wf("transition", str(spec_md), f"{name[:3]}-01", st, env=env)
        return last

    def prep(self, name, status="IN_PROGRESS"):
        self.spec(name, user_spec(name, status),
                  {"slice-01-one.md": user_slice(name[:3], status)})

    def test_ac5_hint_fires_once_on_first_non_genesis_done(self):
        self.new_genesis()
        self.prep("003-a", "DRAFT")
        self.prep("004-b", "DRAFT")
        a = self.finish("003-a")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual((a.stdout + a.stderr).count(self.HINT), 1, a.stdout + a.stderr)
        b = self.finish("004-b")
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertNotIn(self.HINT, b.stdout + b.stderr)
        self.assertTrue((self.specs / "000-adopt-jig").exists())

    def test_ac5_no_hint_when_no_genesis(self):
        self.prep("003-a", "DRAFT")
        a = self.finish("003-a")
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertNotIn(self.HINT, a.stdout + a.stderr)

    def test_ac5_no_hint_for_non_final_transitions(self):
        self.new_genesis()
        self.prep("003-a", "DRAFT")
        env = {"JIG_REVIEW_EVIDENCE_GATE": "0", "JIG_CROSSREF_GATE": "0"}
        r = run_wf("transition", str(self.specs / "003-a" / "spec.md"), "003-01",
                   "READY_FOR_IMPLEMENTATION", env=env)
        self.assertNotIn(self.HINT, r.stdout + r.stderr)

    def test_ac5_hint_failure_does_not_change_exit(self):
        self.new_genesis()
        self.prep("003-a", "DRAFT")
        orig = workflow._genesis_first_done_hint
        workflow._genesis_first_done_hint = lambda *a, **k: 1 / 0
        try:
            spec_md = self.specs / "003-a" / "spec.md"
            os.environ["JIG_REVIEW_EVIDENCE_GATE"] = "0"
            os.environ["JIG_CROSSREF_GATE"] = "0"
            for st in ("READY_FOR_IMPLEMENTATION", "IN_PROGRESS", "REVIEWED",
                       "RECONCILED", "DONE"):
                out = workflow.transition(spec_md, "003-01", st)
            self.assertIn("DONE", out)
        finally:
            workflow._genesis_first_done_hint = orig
            os.environ.pop("JIG_REVIEW_EVIDENCE_GATE", None)
            os.environ.pop("JIG_CROSSREF_GATE", None)


class RescaffoldTests(unittest.TestCase):
    def test_ac6_retired_stays_retired(self):
        for host, primer in (("claude", "CLAUDE.md"), ("codex", "AGENTS.md")):
            with self.subTest(host=host):
                self._check(host, primer)

    def _check(self, host, primer):
        tmp = tempfile.mkdtemp(prefix="jig-retire-rescaf-")
        try:
            target = Path(tmp) / "demo"
            target.mkdir()
            env = os.environ.copy()
            env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)

            def scaffold(*a):
                r = subprocess.run(
                    [sys.executable, str(SCAFFOLD), "--host", host, *a, str(target)],
                    capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, r.stderr + r.stdout)

            scaffold("--in-repo") if host == "codex" else scaffold()
            specs = target / "docs" / "specs"
            (specs / "001-mine").mkdir()
            (specs / "001-mine" / "spec.md").write_text(user_spec("001-mine"))
            r = run_wf("retire-genesis", "--project-dir", str(target))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("reported", r.stdout)
            self.assertFalse((specs / "000-adopt-jig").exists())
            files = (primer, "docs/adoption-readiness.md")
            for f in files:
                self.assertNotIn("adopt-jig", (target / f).read_text(), f)
            scaffold("--force", "--in-repo") if host == "codex" else scaffold("--force")
            self.assertFalse((specs / "000-adopt-jig").exists())
            for f in files:
                self.assertNotIn("adopt-jig", (target / f).read_text(), f)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


BOARD_WITH_GENESIS = BOARD + (
    "| [000-adopt-jig](000-adopt-jig/spec.md) | 000-01 — bootstrap | **DONE** |  |\n"
    "| [003-mine](003-mine/spec.md) | 003-01 — one | DRAFT |  |\n")


class ReviewRegressionTests(_Proj):
    """Slice 121-02 compliance/craft review findings."""

    def test_status_board_row_is_not_reported(self):
        self.new_genesis()
        self.user()
        (self.specs / "README.md").write_text(BOARD_WITH_GENESIS)
        for extra in ((), ("--dry-run",)):
            with self.subTest(extra=extra):
                r = self.retire(*extra)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertNotIn("reported", r.stdout)

    def test_nested_child_link_does_not_delete_parent_or_siblings(self):
        self.new_genesis()
        self.user()
        self.w("CLAUDE.md",
               "## Specs\n"
               "- Specs:\n"
               "  - [000-adopt-jig](docs/specs/000-adopt-jig/spec.md) - example\n"
               "  - [other](https://example.com) - keep me\n"
               "- [board](docs/specs/README.md)\n")
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.root / "CLAUDE.md").read_text()
        self.assertNotIn("adopt-jig", text)
        self.assertIn("- Specs:", text)
        self.assertIn("[other](https://example.com) - keep me", text)
        self.assertIn("[board](docs/specs/README.md)", text)

    def test_default_project_dir_is_cwd(self):
        self.new_genesis()
        self.user()
        self.w("CLAUDE.md", PRIMER_NEW)
        r = run_wf("retire-genesis", cwd=str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.specs / "000-adopt-jig").exists())
        self.assertNotIn("adopt-jig", (self.root / "CLAUDE.md").read_text())

    def test_unrecognised_000_without_seed_frontmatter_is_kept(self):
        self.spec("000-adopt-jig", "---\nstatus: DONE\n---\n\n# Mine\n")
        self.user()
        r = self.retire()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.specs / "000-adopt-jig").is_dir())
        self.assertIn("000-adopt-jig: not recognised as the jig seed", r.stdout)


if __name__ == "__main__":
    unittest.main()
