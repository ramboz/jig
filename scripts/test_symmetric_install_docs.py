"""
Doc guards for the symmetric three-peer install story (spec 061-05).

Slice 061-05 rewrites README.md (and CONTRIBUTING.md) so the three-peer layout
— canonical source root, committed `hosts/claude`, committed `hosts/codex` —
reads symmetrically: each host gets its native remote one-command install, the
committed-and-drift-guarded nature of the host packages is stated (not implied),
scaffold examples run from the host packages (never the repo root), release-zip
docs use host-explicit names, and the docs point at per-host verification.

These guards lock the corrections in. Positive guards assert the corrected
prose is present (one+ per AC, plus the structural-asymmetry edge case); inverse
guards fail if the stale `dist/codex-plugin`-as-install-source wording or a
host-neutral-only release zip story returns, or if the repository-structure
block forgets the `hosts/` peers.

Run:
    python3 scripts/test_symmetric_install_docs.py
    # or from repo root:
    python3 -m unittest scripts.test_symmetric_install_docs
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class Ac1BothRemoteInstalls(unittest.TestCase):
    """AC1: README documents BOTH remote one-command installs."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_claude_marketplace_add(self) -> None:
        self.assertIn(
            "/plugin marketplace add ramboz/jig", self.text,
            "README must document the Claude remote one-command install "
            "(`/plugin marketplace add ramboz/jig`)",
        )

    def test_claude_plugin_install(self) -> None:
        self.assertIn(
            "/plugin install jig@jig", self.text,
            "README must document `/plugin install jig@jig` (Claude)",
        )

    def test_codex_marketplace_add(self) -> None:
        self.assertIn(
            "codex plugin marketplace add", self.text,
            "README must document the Codex remote install "
            "(`codex plugin marketplace add`)",
        )

    def test_codex_plugin_add(self) -> None:
        self.assertIn(
            "codex plugin add jig@jig", self.text,
            "README must document `codex plugin add jig@jig` (Codex)",
        )

    def test_codex_install_targets_committed_hosts_codex(self) -> None:
        # The Codex install points marketplace-add at the committed hosts/codex
        # package directly (its descriptor lives in the hosts/codex subtree,
        # not the repo root) — not a locally built dist dir.
        self.assertRegex(
            self.text,
            r"codex plugin marketplace add hosts/codex\b",
            "the Codex `marketplace add` command must point at the committed "
            "`hosts/codex` package directly",
        )

    def test_codex_install_does_not_claim_bare_repo_shorthand(self) -> None:
        # Honesty guard (jig design principle): there is NO repo-root Codex
        # marketplace descriptor, so `codex plugin marketplace add ramboz/jig`
        # would NOT resolve. Only Claude has the repo-root pointer that enables
        # the bare-repo one-liner. Re-introducing it is a doc-honesty regression.
        self.assertNotIn(
            "codex plugin marketplace add ramboz/jig", self.text,
            "README must NOT claim a bare-repo `codex plugin marketplace add "
            "ramboz/jig` one-liner — Codex has no repo-root marketplace pointer; "
            "point it at the committed `hosts/codex` package instead",
        )

    def test_keeps_hook_trust_caveat(self) -> None:
        # Spec 059 caveat must not regress.
        self.assertIn(
            "/hooks", self.text,
            "README must keep the Codex hook-trust caveat (the `/hooks` "
            "trust note from spec 059)",
        )

    def test_keeps_explicit_agent_install_caveat(self) -> None:
        self.assertIn(
            "--install-codex-agents", self.text,
            "README must keep the explicit Codex agent-install caveat "
            "(`--install-codex-agents`, spec 059)",
        )


class Ac2ThreePeerLayoutExplained(unittest.TestCase):
    """AC2: the three-peer layout is explained, not implied."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_names_hosts_claude_peer(self) -> None:
        self.assertIn(
            "hosts/claude", self.text,
            "README must name the committed `hosts/claude` peer",
        )

    def test_names_hosts_codex_peer(self) -> None:
        self.assertIn(
            "hosts/codex", self.text,
            "README must name the committed `hosts/codex` peer",
        )

    def test_states_committed(self) -> None:
        self.assertIn(
            "committed", self.text,
            "README must state the host packages are committed",
        )

    def test_states_drift_guard_kept_fresh(self) -> None:
        self.assertIn(
            "build_host_packages.py", self.text,
            "README must name the drift-guard builder "
            "(`scripts/build_host_packages.py [--check]`) that keeps the "
            "committed packages fresh",
        )
        self.assertIn(
            "drift", self.text,
            "README must frame the host packages as drift-guarded",
        )

    def test_states_not_hand_edited(self) -> None:
        # Allow either "not hand-edited" or "never hand-edited" phrasing.
        self.assertRegex(
            self.text,
            r"(not|never|n['’]t)\s+hand-?edit",
            "README must state the committed host packages are NOT "
            "hand-edited (they are source-derived build outputs)",
        )


class Ac3ScaffoldExamplesRunFromHostPackages(unittest.TestCase):
    """AC3: local scaffold examples run from the host packages, never the
    repo root."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_claude_scaffold_from_host_package(self) -> None:
        self.assertIn(
            "hosts/claude/skills/scaffold-init/scaffold.py", self.text,
            "README scaffold example must run the Claude scaffold from the "
            "committed package path "
            "(`hosts/claude/skills/scaffold-init/scaffold.py`)",
        )

    def test_codex_scaffold_from_host_package(self) -> None:
        self.assertIn(
            "hosts/codex/plugins/jig/skills/scaffold-init/scaffold.py",
            self.text,
            "README scaffold/agent-install example must run from the committed "
            "Codex package path "
            "(`hosts/codex/plugins/jig/skills/scaffold-init/scaffold.py`)",
        )

    def test_no_repo_root_scaffold_invocation(self) -> None:
        # A bare `skills/scaffold-init/scaffold.py` invocation (not prefixed by
        # a hosts/ or ${...}/ path) is the stale repo-root form AC3 forbids in
        # the local examples. Match `python3 skills/...` or `python3 "skills/...`.
        self.assertNotRegex(
            self.text,
            r"python3\s+\"?skills/scaffold-init/scaffold\.py",
            "README must NOT invoke the repo-root "
            "`skills/scaffold-init/scaffold.py` directly — local scaffold "
            "examples run from the committed host packages (AC3)",
        )


class Ac4HostExplicitReleaseZips(unittest.TestCase):
    """AC4: release-zip docs use host-explicit names + honest Codex story."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_claude_zip_name(self) -> None:
        self.assertIn(
            "jig-claude-vX.Y.Z.zip", self.text,
            "README must reference the Claude release zip "
            "`jig-claude-vX.Y.Z.zip`",
        )

    def test_codex_zip_name(self) -> None:
        self.assertIn(
            "jig-codex-vX.Y.Z.zip", self.text,
            "README must reference the Codex release zip "
            "`jig-codex-vX.Y.Z.zip`",
        )

    def test_codex_no_direct_zip_drop(self) -> None:
        # Honest: Codex has no drag-drop zip install — it's extract-then-add.
        self.assertRegex(
            self.text,
            r"(no direct zip[- ]drop|extract[- ]then[- ]add|unzip)",
            "README must be honest that the Codex zip is an extract-then-add "
            "marketplace bundle (no direct zip-drop install)",
        )


class Ac5HostSpecificVerification(unittest.TestCase):
    """AC5: docs leave room for host-specific verification."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_points_to_codex_verification(self) -> None:
        self.assertIn(
            "codex_install_smoke.py", self.text,
            "README must point at the Codex install verification "
            "(`scripts/codex_install_smoke.py`)",
        )

    def test_points_to_claude_verification(self) -> None:
        # Claude-side verification: verify_install and/or the claude smoke-test.
        self.assertRegex(
            self.text,
            r"(verify_install|build_release_zip\.py --host claude --smoke-test)",
            "README must point at the Claude install verification "
            "(`verify_install` / `build_release_zip.py --host claude "
            "--smoke-test`)",
        )


class EdgeCaseStructuralAsymmetry(unittest.TestCase):
    """Edge case: the flat-Claude vs marketplace-wrapped-Codex asymmetry is
    stated plainly."""

    def setUp(self) -> None:
        self.text = _read(README)

    def test_states_claude_is_flat(self) -> None:
        self.assertIn(
            "flat", self.text,
            "README must state the Claude package is a flat plugin "
            "(`.claude-plugin/plugin.json` at the package root)",
        )

    def test_states_codex_is_marketplace_wrapped(self) -> None:
        self.assertRegex(
            self.text,
            r"marketplace[- ]wrapped",
            "README must state the Codex package is marketplace-wrapped "
            "(`hosts/codex/.agents/plugins/marketplace.json` + "
            "`hosts/codex/plugins/jig/...`)",
        )

    def test_names_codex_marketplace_descriptor_path(self) -> None:
        self.assertIn(
            "hosts/codex/.agents/plugins/marketplace.json", self.text,
            "README must name the Codex marketplace descriptor path so the "
            "wrapped shape is concrete",
        )


class InverseRegressionGuards(unittest.TestCase):
    """Inverse guards: the stale install wording must not return."""

    def setUp(self) -> None:
        self.readme = _read(README)
        self.contributing = _read(CONTRIBUTING)

    def test_readme_no_install_from_dist_codex_plugin(self) -> None:
        # `dist/codex-plugin` is a local build dir, NOT the committed package.
        # No install/marketplace-add command may target it.
        self.assertNotRegex(
            self.readme,
            r"(marketplace add|plugin add)[^\n]*dist/codex-plugin",
            "README must NOT instruct installing from `dist/codex-plugin` — "
            "the committed package lives at `hosts/codex` (061-05)",
        )

    def test_contributing_no_install_from_dist_codex_plugin(self) -> None:
        self.assertNotRegex(
            self.contributing,
            r"(marketplace add|plugin add)[^\n]*dist/codex-plugin",
            "CONTRIBUTING must NOT instruct installing from "
            "`dist/codex-plugin` — the committed package lives at "
            "`hosts/codex` (061-05)",
        )

    def test_readme_no_host_neutral_zip_as_primary(self) -> None:
        # The host-neutral `jig-vX.Y.Z.zip` is at most a deprecated one-cycle
        # Claude alias; it must not be the documented download artifact.
        self.assertNotRegex(
            self.readme,
            r"Download\s+`?jig-vX\.Y\.Z\.zip`?",
            "README must NOT instruct downloading the host-neutral "
            "`jig-vX.Y.Z.zip` — use host-explicit names (061-04/05)",
        )

    def test_repository_structure_lists_hosts(self) -> None:
        # The "Repository structure (for contributors)" block must list the
        # hosts/ peers.
        m = re.search(
            r"## Repository structure.*?```(.*?)```",
            self.readme,
            re.DOTALL,
        )
        self.assertIsNotNone(
            m, "README must keep a `## Repository structure` code block",
        )
        block = m.group(1)
        self.assertIn(
            "hosts/", block,
            "the Repository-structure block must list the `hosts/` peers "
            "(committed Claude + Codex packages) (061-05 AC2)",
        )
        # Accept either the joined path form (`hosts/claude`) or the tree form
        # (`hosts/` followed by an indented `claude/` entry) — both name the peer.
        for peer, leaf in (("hosts/claude", "claude/"), ("hosts/codex", "codex/")):
            with self.subTest(peer=peer):
                self.assertTrue(
                    peer in block or leaf in block,
                    f"the Repository-structure block must name the `{peer}` "
                    f"peer (joined path or `{leaf}` tree entry under `hosts/`)",
                )


class ContributingMaintainerDocs(unittest.TestCase):
    """061-05: CONTRIBUTING's release-zip section uses host-explicit names and
    the `--host` flag (slice 061-04 made `--host` required), and frames the
    committed host packages as drift-guarded / not hand-edited."""

    def setUp(self) -> None:
        self.text = _read(CONTRIBUTING)

    def test_host_explicit_zip_names(self) -> None:
        for name in ("jig-claude-vX.Y.Z.zip", "jig-codex-vX.Y.Z.zip"):
            with self.subTest(name=name):
                self.assertIn(
                    name, self.text,
                    f"CONTRIBUTING must reference the host-explicit zip "
                    f"`{name}` (061-04/05)",
                )

    def test_build_release_zip_uses_host_flag(self) -> None:
        self.assertRegex(
            self.text,
            r"build_release_zip\.py --host (claude|codex)",
            "CONTRIBUTING must invoke `build_release_zip.py --host ...` "
            "(slice 061-04 made --host required)",
        )

    def test_no_hostless_build_release_zip_version(self) -> None:
        # The old `--version`-without-`--host` form is now broken.
        self.assertNotRegex(
            self.text,
            r"build_release_zip\.py --version",
            "CONTRIBUTING must NOT invoke `build_release_zip.py --version` "
            "without `--host` (it now errors; 061-04)",
        )

    def test_frames_drift_guard(self) -> None:
        self.assertIn(
            "build_host_packages.py", self.text,
            "CONTRIBUTING must name the drift-guard builder for the committed "
            "host packages",
        )


if __name__ == "__main__":
    unittest.main()
