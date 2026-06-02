"""Hook-integration tests for hooks/scripts/jig-secret-scan.sh
(spec 052, slice 052-02 — secret-prevention-floor).

The hook is a PreToolUse Edit|Write|MultiEdit *deliberateness* gate: on a
high-confidence secret pattern in the pending content it exits 2 (block)
with a structured stderr message (file + matched rule + how-to-override),
overridable by JIG_SECRET_SCAN_APPROVED=1. It fails OPEN on any internal
error so a buggy scanner never wedges the agent (mirrors jig-spec-gate.sh).

BOOTSTRAPPING HAZARD: jig-secret-scan.sh is a LIVE PreToolUse Edit|Write
hook in this very repo. To keep this test *source file* from tripping the
very hook it tests (and to avoid committing real-looking secrets), every
secret-shaped literal below is ASSEMBLED AT RUNTIME by string
concatenation — no contiguous secret-shaped match ever appears on disk.

Run from the repo root:
    python3 hooks/scripts/test_jig_secret_scan.py
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "scripts" / "jig-secret-scan.sh"


def run_hook(payload: dict, *, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Drop the override by default so tests pin the on-by-default block.
    env.pop("JIG_SECRET_SCAN_APPROVED", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    )


# ---- runtime-assembled secret-shaped literals (see module docstring) ----

def aws_key() -> str:
    """A real-looking AWS access key id (NOT the *EXAMPLE* canonical one —
    that contains 'EXAMPLE' and would be caught by the placeholder guard)."""
    return "AKIA" + "JKL4MNOP5QRS6TUV"


def aws_temp_key() -> str:
    """ASIA-prefixed temporary/session key."""
    return "ASIA" + "JKL4MNOP5QRS6TUV"


def pem_block() -> str:
    """A PEM private-key block, header/footer assembled from parts."""
    dashes = "-" * 5
    begin = dashes + "BEGIN RSA PRIVATE KEY" + dashes
    end = dashes + "END RSA PRIVATE KEY" + dashes
    return begin + "\nMIIEvQIBADANB...redacted-body...\n" + end + "\n"


def openssh_pem_block() -> str:
    dashes = "-" * 5
    begin = dashes + "BEGIN OPENSSH PRIVATE KEY" + dashes
    end = dashes + "END OPENSSH PRIVATE KEY" + dashes
    return begin + "\nb3BlbnNzaC1rZXktdjEAAA...\n" + end + "\n"


def env_real_secret() -> str:
    """A .env-style assignment of a secret-named key to a real-looking value."""
    return "AWS_SECRET_ACCESS_KEY=" + "wJalr" + "XUtnFEMI9K7MDENGbPxRfiCYEXAMPLEKEY".replace("EXAMPLE", "rEAL")


def bearer_token() -> str:
    """A real-looking 'sk-'-prefixed opaque API token, assembled at runtime so
    no contiguous secret-shaped literal lands on disk (see module docstring)."""
    return "sk-" + "live" + "9aZ" + "Q2w" + "8xE" + "7rT" + "5yU" + "3iO" + "1pB"


class BlockOnRealSecretTests(unittest.TestCase):
    """AC #2 / AC #3 — high-confidence patterns block (exit 2) with a
    structured message naming the file and the matched rule."""

    def _write_payload(self, content: str, file_path: str = "/tmp/app/config.py") -> dict:
        return {
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content},
        }

    def test_aws_access_key_blocks(self):
        path = "/tmp/app/aws_config.py"
        r = run_hook(self._write_payload(
            "AWS_ACCESS_KEY_ID = '" + aws_key() + "'\n", path,
        ))
        self.assertEqual(r.returncode, 2,
                         f"AWS key should block; stderr={r.stderr!r}")
        # Structured message: file + matched rule.
        self.assertIn(path, r.stderr)
        self.assertIn("AWS", r.stderr)

    def test_aws_temp_key_blocks(self):
        r = run_hook(self._write_payload(
            "session_key = '" + aws_temp_key() + "'\n",
        ))
        self.assertEqual(r.returncode, 2,
                         f"ASIA temp key should block; stderr={r.stderr!r}")

    def test_pem_private_key_block_blocks(self):
        path = "/tmp/app/id_rsa"
        r = run_hook(self._write_payload(pem_block(), path))
        self.assertEqual(r.returncode, 2,
                         f"PEM block should block; stderr={r.stderr!r}")
        self.assertIn(path, r.stderr)
        self.assertIn("private key", r.stderr.lower())

    def test_openssh_private_key_block_blocks(self):
        r = run_hook(self._write_payload(openssh_pem_block(), "/tmp/app/id_ed25519"))
        self.assertEqual(r.returncode, 2,
                         f"OPENSSH PEM block should block; stderr={r.stderr!r}")

    def test_env_assignment_real_value_blocks(self):
        path = "/tmp/app/.env"
        r = run_hook(self._write_payload(
            "DB_HOST=localhost\n" + env_real_secret() + "\n", path,
        ))
        self.assertEqual(r.returncode, 2,
                         f".env real-value assignment should block; stderr={r.stderr!r}")
        self.assertIn(path, r.stderr)

    def test_block_message_names_override_var(self):
        """AC #2 — the structured message tells the agent how to override."""
        r = run_hook(self._write_payload("key = '" + aws_key() + "'\n"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("JIG_SECRET_SCAN_APPROVED", r.stderr)

    def test_block_message_is_honest_about_scope(self):
        """AC #5 — the block message states the floor is agent-time /
        defense-in-depth, not a guarantee, and names an out-of-band channel."""
        r = run_hook(self._write_payload("key = '" + aws_key() + "'\n"))
        self.assertEqual(r.returncode, 2)
        low = r.stderr.lower()
        self.assertIn("defense-in-depth", low)
        self.assertTrue(
            "not a guarantee" in low or "does not guarantee" in low,
            f"block message must disclaim a guarantee; got: {r.stderr!r}",
        )
        # Names at least one out-of-band channel.
        self.assertTrue(
            any(ch in low for ch in ("ci", "server-side", "branch protection",
                                     "branch-protection")),
            f"block message must name an out-of-band channel; got: {r.stderr!r}",
        )

    def test_prefixed_bearer_token_blocks(self):
        """A secret-named key assigned a real 'sk-'-prefixed opaque token must
        still block (the tightened value-shape gate keeps genuine secrets)."""
        path = "/tmp/app/secrets.py"
        r = run_hook(self._write_payload(
            'API_TOKEN = "' + bearer_token() + '"\n', path,
        ))
        self.assertEqual(r.returncode, 2,
                         f"a real sk- token must still block; stderr={r.stderr!r}")
        self.assertIn(path, r.stderr)
        self.assertIn("secret-named", r.stderr)


class AllowOnPlaceholderTests(unittest.TestCase):
    """AC #3 — placeholder / example forms must NOT block (exit 0)."""

    def _write(self, content: str, file_path: str = "/tmp/app/config.py") -> subprocess.CompletedProcess:
        return run_hook({
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content},
        })

    def test_angle_bracket_placeholder_allowed(self):
        r = self._write("API_KEY=<your-key>\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_dollar_var_placeholder_allowed(self):
        r = self._write("API_KEY=${SOME_ENV_VAR}\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_bare_dollar_var_placeholder_allowed(self):
        r = self._write("token = $MY_TOKEN\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_run_of_x_placeholder_allowed(self):
        r = self._write("password = 'xxxxxxxxxxxx'\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_example_word_placeholder_allowed(self):
        r = self._write("client_secret = 'example-secret-value'\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_changeme_placeholder_allowed(self):
        r = self._write("API_KEY=changeme\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_empty_value_allowed(self):
        r = self._write("SECRET_TOKEN=\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_canonical_aws_example_key_allowed(self):
        """The canonical AWS docs key ends in EXAMPLE — the placeholder guard
        must treat it as a placeholder, not a real secret."""
        canonical = "AKIA" + "IOSFODNN7" + "EXAMPLE"
        r = self._write("AWS_ACCESS_KEY_ID = '" + canonical + "'\n")
        self.assertEqual(r.returncode, 0,
                         f"canonical *EXAMPLE key must be allowed; stderr={r.stderr!r}")

    def test_clean_content_allowed(self):
        r = self._write("def add(a, b):\n    return a + b\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")


class AllowOnExampleFileTests(unittest.TestCase):
    """AC #3 — files whose path legitimately holds placeholder secrets
    (.example / .sample / .template / .dist) are not scanned."""

    def _write(self, content: str, file_path: str) -> subprocess.CompletedProcess:
        return run_hook({
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content},
        })

    def test_dot_example_file_allowed_even_with_real_secret(self):
        # A real-looking key in a .env.example is the intended use of that file.
        r = self._write("AWS_ACCESS_KEY_ID=" + aws_key() + "\n", "/tmp/app/.env.example")
        self.assertEqual(r.returncode, 0,
                         f".example file must be skipped; stderr={r.stderr!r}")

    def test_dot_sample_file_allowed(self):
        r = self._write("key = '" + aws_key() + "'\n", "/tmp/app/config.sample")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_dot_template_file_allowed(self):
        r = self._write("key = '" + aws_key() + "'\n", "/tmp/app/secrets.template")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_dot_dist_file_allowed(self):
        r = self._write("key = '" + aws_key() + "'\n", "/tmp/app/.env.dist")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")


class OverrideTests(unittest.TestCase):
    """AC #2 — JIG_SECRET_SCAN_APPROVED=1 turns the block into an allow."""

    def test_override_allows_real_secret(self):
        r = run_hook(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/app/config.py",
                    "content": "key = '" + aws_key() + "'\n",
                },
            },
            env_overrides={"JIG_SECRET_SCAN_APPROVED": "1"},
        )
        self.assertEqual(r.returncode, 0,
                         f"override should allow; stderr={r.stderr!r}")

    def test_without_override_same_payload_blocks(self):
        """Symmetric assertion: unset override → the same payload blocks."""
        r = run_hook({
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/app/config.py",
                "content": "key = '" + aws_key() + "'\n",
            },
        })
        self.assertEqual(r.returncode, 2)


class ToolPayloadShapeTests(unittest.TestCase):
    """AC #2 — Write (content), Edit (new_string), MultiEdit
    (edits[].new_string) payload shapes are all scanned."""

    def test_edit_new_string_scanned(self):
        r = run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/app/config.py",
                "old_string": "placeholder",
                "new_string": "AWS_KEY = '" + aws_key() + "'",
            },
        })
        self.assertEqual(r.returncode, 2,
                         f"Edit new_string should be scanned; stderr={r.stderr!r}")

    def test_edit_clean_new_string_allowed(self):
        r = run_hook({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/tmp/app/config.py",
                "old_string": "x",
                "new_string": "y = 1",
            },
        })
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_multiedit_concatenates_new_strings(self):
        """The secret is split across two edits — neither alone is a match
        in this fixture, but the secret lives entirely in the second edit.
        Pin that every edit's new_string is scanned."""
        r = run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": "/tmp/app/config.py",
                "edits": [
                    {"old_string": "a", "new_string": "clean line one"},
                    {"old_string": "b", "new_string": "KEY = '" + aws_key() + "'"},
                ],
            },
        })
        self.assertEqual(r.returncode, 2,
                         f"MultiEdit edits should be scanned; stderr={r.stderr!r}")

    def test_multiedit_all_clean_allowed(self):
        r = run_hook({
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": "/tmp/app/config.py",
                "edits": [
                    {"old_string": "a", "new_string": "clean one"},
                    {"old_string": "b", "new_string": "clean two"},
                ],
            },
        })
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")


class FailOpenRobustnessTests(unittest.TestCase):
    """Mirrors jig-spec-gate.sh — the hook must fail OPEN (exit 0) on any
    malformed input so a buggy scanner never wedges the agent."""

    def test_invalid_json_exits_zero(self):
        env = os.environ.copy()
        env.pop("JIG_SECRET_SCAN_APPROVED", None)
        r = subprocess.run(
            ["bash", str(HOOK)],
            input="not even json",
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r.returncode, 0, "invalid JSON must not block")

    def test_garbage_payload_exits_zero(self):
        r = run_hook({"completely": "unexpected", "shape": True})
        self.assertEqual(r.returncode, 0)

    def test_unknown_tool_exits_zero(self):
        r = run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        self.assertEqual(r.returncode, 0)

    def test_missing_content_exits_zero(self):
        r = run_hook({"tool_name": "Write", "tool_input": {"file_path": "/tmp/x"}})
        self.assertEqual(r.returncode, 0)

    def test_empty_file_path_with_clean_content_exits_zero(self):
        r = run_hook({"tool_name": "Write", "tool_input": {"content": "clean"}})
        self.assertEqual(r.returncode, 0)


class AllowOnCodeAnnotationTests(unittest.TestCase):
    """Regression (056-02 fallout): the secret-named-.env-assignment rule must
    NOT fire on ordinary code — Python/TS type annotations, bare literals, and
    numeric defaults — even when the identifier contains a secret-y word like
    'token' or 'secret'. The value has to look like a real opaque credential."""

    def _write(self, content: str, file_path: str = "/tmp/app/models.py") -> subprocess.CompletedProcess:
        return run_hook({
            "tool_name": "Write",
            "tool_input": {"file_path": file_path, "content": content},
        })

    def test_token_named_int_annotation_allowed(self):
        # The exact shape that tripped the floor during slice 056-02.
        r = self._write("    subagent_input_tokens: int = 0\n")
        self.assertEqual(r.returncode, 0,
                         f"type annotation must not block; stderr={r.stderr!r}")

    def test_secret_named_optional_annotation_allowed(self):
        r = self._write("    client_secret: Optional[str] = None\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_apikey_named_str_default_allowed(self):
        r = self._write('    api_key: str = ""\n')
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_token_named_numeric_default_allowed(self):
        r = self._write("max_tokens = 100000\n")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_secret_named_bare_keyword_yaml_allowed(self):
        # YAML-ish 'key: value' with a bare keyword value.
        r = self._write("rotate_secret: true\n", "/tmp/app/config.yaml")
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")

    def test_dataclass_token_fields_allowed(self):
        r = self._write(
            "@dataclass\nclass Report:\n    subagent_output_tokens: int = 0\n"
            "    cache_read_tokens: int = 0\n",
            "/tmp/app/report.py",
        )
        self.assertEqual(r.returncode, 0, f"stderr={r.stderr!r}")


if __name__ == "__main__":
    unittest.main()
