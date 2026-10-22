"""TEST ONLY generic reader/rail support; no producer approval or app claims."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import review_evidence as ev

REPO = Path(__file__).resolve().parents[2]
STATIC = "jig/static-design-freshness/1"
RETIRED = ("jig/design-freshness/1", "vellum-design-input/0.1-pilot")


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def block(name, value):
    return f"```jig-design-{name}\n{json.dumps(value, sort_keys=True)}\n```\n"


class GenericFixture:
    """Small file/CLI support only; no legacy producer or positive fixture."""

    def root(self, name):
        return getattr(self, name)

    def put(self, root, path, value):
        p = self.root(root) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value if isinstance(value, str) else json.dumps(value))
        return p

    def ref(self, root, path):
        return {"root": root, "path": path, "hash": digest(self.root(root) / path)}

    def tree(self, root, path):
        directory = self.root(root) / path
        return {
            "root": root, "path": path,
            "files": [
                {"path": p.relative_to(directory).as_posix(), "hash": digest(p)}
                for p in sorted(directory.rglob("*")) if p.is_file()
            ],
        }

    def write_context(self):
        self.put("evidence", "context.json", self.context)

    def select(self, selection, status="IN_PROGRESS"):
        self.selection = selection
        self.slice.write_text(
            f"---\nstatus: {status}\ndependencies: []\ndesign_review: true\n---\n"
            "\n## Slice 999-01 fixture\n\n"
            + block("selection", selection)
            + "\n### Deviation log\nTEST ONLY synthetic lifecycle preconditions.\n"
            "\n### Reconciliation sweep\nTEST ONLY; no product claims.\n"
        )

    def body(self):
        return "TEST ONLY SYNTHETIC; not genuine producer approval.\n" + block(
            "bindings", self.bindings)

    def verdict(self, name, body):
        target = self.spec_dir / f"reviews/slice-01-{name}.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text(
            "---\nslice: 999-01 fixture\n"
            f"pass: {name}\nverdict: pass\nreviewer: TEST ONLY synthetic\n"
            "reviewed_at: 2026-10-22T00:00:00Z\nprompt_source: TEST ONLY\n---\n"
            + body
        )
        return target

    def check(self):
        return ev.validate_evidence(self.spec, "999-01", "REVIEWED")

    def cli(self, helper, *args, body=None):
        return subprocess.run(
            [sys.executable, str(REPO / f"skills/{helper}"), *map(str, args)],
            input=body, capture_output=True, text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO),
                 "JIG_REVIEW_EVIDENCE_GATE": "1"},
        )

    def record(self, body=None, verdict="pass"):
        return self.cli(
            "independent-review/review.py", "record-review", self.spec, "999-01",
            "--pass", "design-review", "--verdict", verdict,
            "--reviewer", "TEST ONLY", "--prompt-source", "TEST ONLY",
            "--summary-file", "-", body=self.body() if body is None else body,
        )


class SelectionTests(unittest.TestCase):
    def test_ac5_retired_selected_namespaces_never_fall_back(self):
        from _common.design_bindings import freshness_problem
        for schema in RETIRED:
            for selection, bindings in (
                ({"schema": schema}, {"schema": schema}),
                ({"schema": STATIC}, {"schema": schema}),
                ({"schema": schema}, {"schema": STATIC}),
                ({"schema": schema}, None),
                (None, {"schema": schema}),
                ({"schema": STATIC, "contracts": {"vellum_input": schema}},
                 {"schema": STATIC}),
            ):
                with self.subTest(schema=schema, selection=selection, bindings=bindings):
                    problem = freshness_problem(
                        block("selection", selection) if selection else "ordinary",
                        block("bindings", bindings) if bindings else "ordinary")
                    self.assertIn("retired", problem)
                    self.assertIn("fresh producer evidence", problem)

    def test_ac5_malformed_duplicate_missing_and_unknown_selection_refuse(self):
        from _common.design_bindings import freshness_problem
        selection = block("selection", {"schema": STATIC})
        bindings = block("bindings", {"schema": STATIC})
        for left, right in (
            (selection, "plain PASS"), ("ordinary", bindings),
            (selection + selection, bindings),
            ("```jig-design-selection\n{bad}\n```", bindings),
            (selection.replace("```jig-", " ````jig-"), bindings),
            (block("selection", {"schema": "unknown/1"}), bindings),
        ):
            self.assertTrue(freshness_problem(left, right))

    def test_ac7_no_selection_is_unchanged_scalar_behavior(self):
        from _common.design_bindings import freshness_problem
        self.assertEqual(freshness_problem("ordinary slice", "scalar PASS"), "")

    def test_ac6_bounded_strict_reader_has_no_pilot_validator(self):
        from _common import design_bindings as db
        for value in ("../escape", ".git/config", "a//b", "a\\b", "/absolute",
                      "a:b", "a/\x00", "e\u0301"):
            with self.assertRaises(db.BindingError):
                db._relative(value, "test")
        for value in ('{"a":1,"a":2}', '{"n":NaN}', '{"n":1e9999}'):
            with self.assertRaises(db.BindingError):
                db._json(value, "test")
        self.assertFalse(hasattr(db, "CONTRACTS"), "no pilot contract runtime")


class GitIdentityTests(unittest.TestCase):
    def test_ac3_git_probe_is_fixed_local_and_removes_inherited_git_environment(self):
        from _common.static_design_bindings import git_revision
        completed = subprocess.CompletedProcess([], 0, "a" * 40 + "\n", "")
        poison = {
            "GIT_DIR": "/foreign", "GIT_WORK_TREE": "/foreign",
            "GIT_COMMON_DIR": "/foreign", "GIT_CONFIG_GLOBAL": "/foreign",
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.worktree",
            "GIT_CONFIG_VALUE_0": "/foreign", "GIT_OBJECT_DIRECTORY": "/foreign",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/foreign",
            "GIT_CEILING_DIRECTORIES": "/", "GIT_EXEC_PATH": "/foreign",
        }
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, poison), \
                mock.patch("subprocess.run", return_value=completed) as run:
            root = Path(tmp).resolve()
            self.assertEqual(git_revision(root), "a" * 40)
            args, kwargs = run.call_args
            self.assertEqual(args[0], [
                "git", "--no-optional-locks", "-C", str(root),
                "rev-parse", "--verify", "HEAD"])
            self.assertFalse(kwargs.get("shell", False))
            self.assertLessEqual(kwargs["timeout"], 10)
            self.assertTrue(all(k not in kwargs["env"] for k in poison
                                if k != "GIT_CONFIG_GLOBAL"))
            self.assertEqual(kwargs["env"]["GIT_CONFIG_NOSYSTEM"], "1")
            self.assertEqual(kwargs["env"]["GIT_CONFIG_GLOBAL"], os.devnull)

    def test_ac3_non_git_is_null_but_execution_errors_are_not_null(self):
        from _common.design_bindings import BindingError
        from _common.static_design_bindings import git_revision
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            self.assertIsNone(git_revision(root))
            for error in (PermissionError("denied"), FileNotFoundError("missing"),
                          subprocess.TimeoutExpired("git", 5)):
                with mock.patch("subprocess.run", side_effect=error):
                    with self.assertRaisesRegex(BindingError, "git"):
                        git_revision(root)
            for result in (
                subprocess.CompletedProcess([], 128, "", "fatal: permission denied"),
                subprocess.CompletedProcess([], 0, "not-a-revision", ""),
            ):
                with mock.patch("subprocess.run", return_value=result):
                    with self.assertRaisesRegex(BindingError, "git"):
                        git_revision(root)


if __name__ == "__main__":
    unittest.main()
