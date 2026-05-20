"""Hook script tests for slice 005-03 (jig-boundary-change-warn.sh).

Tests the PostToolUse hook by piping mock hook payloads in via stdin and
asserting on stdout JSON, stderr, and exit code. Parallels the shape used
by `scripts/test_post_edit_verify.py` (slice 027-01).

Run from the repo root:
    python3 scripts/test_boundary_change_warn.py
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-boundary-change-warn.sh"


def run_hook(payload: dict, *, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Drop the opt-out by default so tests pin the on-by-default behavior.
    env.pop("JIG_BOUNDARY_CHECK", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


def parse(result: subprocess.CompletedProcess):
    """Assert exit 0, return parsed stdout dict or None if no output."""
    assert result.returncode == 0, (
        f"hook should never block (got {result.returncode}); "
        f"stderr={result.stderr!r}"
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)


class MatchMatrixTests(unittest.TestCase):
    """AC #2 + AC #6 match matrix — each canonical filename triggers a nudge
    containing both /jig:adr-workflow new AND the surface-specific tool name."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-match-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _edit_payload(self, basename: str) -> dict:
        f = Path(self.tmpdir) / basename
        f.write_text("placeholder content\n")
        return {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "placeholder",
                "new_string": "edited",
            },
        }

    def test_openapi_yaml_triggers_adr_pointer_and_redocly_or_spectral(self):
        out = parse(run_hook(self._edit_payload("openapi.yaml")))
        self.assertIsNotNone(out, "openapi.yaml should trigger nudge")
        ctx = out["additionalContext"]
        self.assertIn("/jig:adr-workflow new", ctx)
        self.assertIn("openapi.yaml", ctx)
        self.assertTrue("redocly" in ctx.lower() or "spectral" in ctx.lower(),
                        f"OpenAPI nudge must mention redocly or spectral: {ctx!r}")

    def test_openapi_yml_triggers_nudge(self):
        out = parse(run_hook(self._edit_payload("openapi.yml")))
        self.assertIsNotNone(out)
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])

    def test_openapi_json_triggers_nudge(self):
        out = parse(run_hook(self._edit_payload("openapi.json")))
        self.assertIsNotNone(out)
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])

    def test_proto_triggers_buf_breaking(self):
        out = parse(run_hook(self._edit_payload("foo.proto")))
        self.assertIsNotNone(out, "*.proto should trigger nudge")
        ctx = out["additionalContext"]
        self.assertIn("/jig:adr-workflow new", ctx)
        self.assertIn("foo.proto", ctx)
        self.assertIn("buf breaking", ctx,
                      f".proto nudge must mention `buf breaking`: {ctx!r}")

    def test_graphql_triggers_graphql_inspector(self):
        out = parse(run_hook(self._edit_payload("schema.graphql")))
        self.assertIsNotNone(out, "*.graphql should trigger nudge")
        ctx = out["additionalContext"]
        self.assertIn("/jig:adr-workflow new", ctx)
        self.assertIn("schema.graphql", ctx)
        self.assertIn("graphql-inspector", ctx,
                      f"*.graphql nudge must mention graphql-inspector: {ctx!r}")

    def test_graphqls_triggers_nudge(self):
        out = parse(run_hook(self._edit_payload("schema.graphqls")))
        self.assertIsNotNone(out, "*.graphqls should trigger nudge")
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])
        self.assertIn("graphql-inspector", out["additionalContext"])

    def test_schema_json_triggers_json_schema_diff(self):
        out = parse(run_hook(self._edit_payload("event.schema.json")))
        self.assertIsNotNone(out, "*.schema.json should trigger nudge")
        ctx = out["additionalContext"]
        self.assertIn("/jig:adr-workflow new", ctx)
        self.assertIn("event.schema.json", ctx)
        # JSON-Schema diff tool (mention "JSON Schema" + "diff" or similar)
        self.assertIn("schema", ctx.lower())
        self.assertIn("diff", ctx.lower(),
                      f"*.schema.json nudge must mention a diff tool: {ctx!r}")

    def test_asyncapi_yaml_triggers_parser_diff(self):
        out = parse(run_hook(self._edit_payload("asyncapi.yaml")))
        self.assertIsNotNone(out, "asyncapi.yaml should trigger nudge")
        ctx = out["additionalContext"]
        self.assertIn("/jig:adr-workflow new", ctx)
        self.assertIn("asyncapi.yaml", ctx)
        self.assertIn("asyncapi", ctx.lower())

    def test_asyncapi_yml_triggers_nudge(self):
        out = parse(run_hook(self._edit_payload("asyncapi.yml")))
        self.assertIsNotNone(out)
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])

    def test_asyncapi_json_triggers_nudge(self):
        out = parse(run_hook(self._edit_payload("asyncapi.json")))
        self.assertIsNotNone(out)
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])


class CaseInsensitiveTests(unittest.TestCase):
    """AC #2 — basename match is case-insensitive."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-case-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _edit_payload(self, basename: str) -> dict:
        f = Path(self.tmpdir) / basename
        f.write_text("placeholder\n")
        return {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "placeholder",
                "new_string": "edited",
            },
        }

    def test_uppercase_openapi_yaml_still_triggers(self):
        out = parse(run_hook(self._edit_payload("OpenAPI.YAML")))
        self.assertIsNotNone(out, "OpenAPI.YAML (case-mixed) should trigger")
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])

    def test_uppercase_proto_still_triggers(self):
        out = parse(run_hook(self._edit_payload("FOO.PROTO")))
        self.assertIsNotNone(out, "FOO.PROTO (uppercase) should trigger")
        self.assertIn("buf breaking", out["additionalContext"])


class NonMatchingFilesTests(unittest.TestCase):
    """AC #5 — files that don't match a canonical pattern exit silently."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-nonmatch-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _edit_payload(self, basename: str) -> dict:
        f = Path(self.tmpdir) / basename
        f.write_text("placeholder\n")
        return {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(f),
                "old_string": "placeholder",
                "new_string": "edited",
            },
        }

    def test_readme_md_is_silent(self):
        result = run_hook(self._edit_payload("README.md"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_python_source_is_silent(self):
        result = run_hook(self._edit_payload("foo.py"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_package_json_does_not_match_schema_json(self):
        """package.json must NOT match *.schema.json — the infix is load-bearing."""
        result = run_hook(self._edit_payload("package.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.strip(), "",
            f"package.json should NOT trigger schema.json nudge; got {result.stdout!r}",
        )

    def test_pyproject_toml_is_silent(self):
        result = run_hook(self._edit_payload("pyproject.toml"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_arbitrary_json_does_not_trigger(self):
        """Bare `.json` doesn't trigger — only `*.schema.json` matches."""
        result = run_hook(self._edit_payload("config.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class NonEditToolsTests(unittest.TestCase):
    """AC #5 — non-Edit|Write|MultiEdit tools produce no output."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-tools-")
        self.f = Path(self.tmpdir) / "openapi.yaml"
        self.f.write_text("openapi: 3.0.0\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_read_tool_is_silent(self):
        result = run_hook({
            "tool_name": "Read",
            "tool_input": {"file_path": str(self.f)},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "",
                         "Read on a matching file must not trigger")

    def test_bash_tool_is_silent(self):
        result = run_hook({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_glob_tool_is_silent(self):
        result = run_hook({
            "tool_name": "Glob",
            "tool_input": {"pattern": "*.yaml"},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_task_tool_is_silent(self):
        result = run_hook({
            "tool_name": "Task",
            "tool_input": {"description": "x", "prompt": "y"},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class WriteAndMultiEditTriggerTests(unittest.TestCase):
    """AC #2/#5 + Clarification Q3 — Write of a new artifact AND Edit
    of an existing artifact both trigger. MultiEdit also triggers."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-write-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_new_openapi_triggers(self):
        # Write payload for a new file (which may or may not exist at hook time)
        f = Path(self.tmpdir) / "openapi.yaml"
        out = parse(run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": str(f),
                "content": "openapi: 3.0.0\n",
            },
        }))
        self.assertIsNotNone(out,
                             "Write of new openapi.yaml must trigger (Clarif Q3)")
        self.assertIn("/jig:adr-workflow new", out["additionalContext"])

    def test_multiedit_proto_triggers(self):
        f = Path(self.tmpdir) / "foo.proto"
        f.write_text("syntax = \"proto3\";\n")
        out = parse(run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": str(f),
                "edits": [
                    {"old_string": "proto3", "new_string": "proto3"},
                ],
            },
        }))
        self.assertIsNotNone(out, "MultiEdit on .proto must trigger")
        self.assertIn("buf breaking", out["additionalContext"])


class OptOutTests(unittest.TestCase):
    """AC #4 — JIG_BOUNDARY_CHECK=0 disables the hook entirely."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-optout-")
        self.f = Path(self.tmpdir) / "openapi.yaml"
        self.f.write_text("openapi: 3.0.0\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_opt_out_silences_nudge(self):
        result = run_hook(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(self.f),
                    "old_string": "openapi",
                    "new_string": "openapi: 3.0.0\n# edit",
                },
            },
            env_overrides={"JIG_BOUNDARY_CHECK": "0"},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "",
                         "opt-out should produce no output")

    def test_default_on_still_nudges(self):
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.f),
                "old_string": "openapi",
                "new_string": "openapi: 3.0.0\n# edit",
            },
        }))
        self.assertIsNotNone(out, "default-on should nudge")


class NeverBlocksTests(unittest.TestCase):
    """AC #6 — when a nudge fires, output is valid JSON with continue:true,
    no block / permissionDecision field, exit code 0."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-shape-")
        self.f = Path(self.tmpdir) / "openapi.yaml"
        self.f.write_text("openapi: 3.0.0\n")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_nudge_payload_shape(self):
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.f),
                "old_string": "openapi",
                "new_string": "edited",
            },
        }))
        self.assertIsNotNone(out)
        self.assertIs(out.get("continue"), True,
                      "must never set continue:false — soft nudge only")
        self.assertNotIn("block", out,
                         "must not set 'block' — nudge only")
        self.assertNotIn("permissionDecision", out,
                         "must not set 'permissionDecision' — nudge only")
        self.assertIsInstance(out.get("additionalContext"), str)
        self.assertGreater(len(out["additionalContext"]), 0)

    def test_nudge_mentions_informational_not_gate(self):
        """AC #3 — nudge text includes a reminder that it's informational."""
        out = parse(run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(self.f),
                "old_string": "openapi",
                "new_string": "edited",
            },
        }))
        self.assertIsNotNone(out)
        ctx = out["additionalContext"].lower()
        # AC #3 part 4 — reminder this is informational, not a gate
        self.assertTrue(
            "informational" in ctx or "not a gate" in ctx
            or "non-blocking" in ctx or "nudge" in ctx,
            f"nudge text must signal informational/non-blocking intent: {ctx!r}",
        )


class RobustnessTests(unittest.TestCase):
    """AC #5 + general robustness: missing file_path, garbage payloads,
    crash posture (Clarification Q2 — silent except Exception: pass)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="jig-005-03-robust-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_missing_file_path_exits_silently(self):
        result = run_hook({
            "tool_name": "Edit",
            "tool_input": {"old_string": "x", "new_string": "y"},
        })
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_garbage_payload_exits_silently(self):
        result = run_hook({"completely": "unexpected", "shape": True})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_invalid_stdin_json_exits_zero(self):
        env = os.environ.copy()
        env.pop("JIG_BOUNDARY_CHECK", None)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="not even json",
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 0,
                         "invalid JSON must not block")
        # Clarification Q2 — crash posture is silent, no stderr writes.
        self.assertEqual(result.stderr.strip(), "",
                         "crash posture is silent — no stderr writes")

    def test_missing_tool_input_exits_silently(self):
        result = run_hook({"tool_name": "Edit"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")


class HookRegistrationTests(unittest.TestCase):
    """AC #1 — hook is registered in hooks/hooks.json under PostToolUse
    matcher Edit|Write|MultiEdit with timeout: 5."""

    def test_hook_script_exists(self):
        self.assertTrue(HOOK.is_file(),
                        f"hook script must exist at {HOOK}")

    def test_hook_script_is_executable_or_invokable_via_bash(self):
        # Hook scripts are invoked via `bash <script>`, so we don't strictly
        # require the executable bit, but a simple run should work.
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="{}",
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0,
                         f"hook should accept empty JSON; got {result.returncode}")

    def test_hooks_json_registers_boundary_change_warn(self):
        hooks_json = REPO_ROOT / "hooks" / "hooks.json"
        data = json.loads(hooks_json.read_text())
        post = data.get("hooks", {}).get("PostToolUse", [])
        # Find any entry whose matcher mentions Edit|Write|MultiEdit and whose
        # hooks list references jig-boundary-change-warn.sh.
        found = False
        for entry in post:
            matcher = entry.get("matcher", "")
            if matcher != "Edit|Write|MultiEdit":
                continue
            for h in entry.get("hooks", []) or []:
                cmd = h.get("command", "")
                if "jig-boundary-change-warn.sh" in cmd:
                    found = True
                    self.assertEqual(h.get("timeout"), 5,
                                     "timeout must be 5 (mirrors sibling hooks)")
        self.assertTrue(
            found,
            "hooks/hooks.json must register jig-boundary-change-warn.sh as a "
            "PostToolUse Edit|Write|MultiEdit hook",
        )


if __name__ == "__main__":
    unittest.main()
