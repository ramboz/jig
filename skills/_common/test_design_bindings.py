"""119-02 synthetic consistency fixtures, NOT producer/judge execution claims."""

import copy
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
SCHEMA = "jig/design-freshness/1"
CONTRACTS = {
    "vellum_input": "vellum-design-input/0.1-pilot",
    "gate_result": 2,
    "required_component_result": 1,
    "command_result_artifacts": 1,
    "design_evidence": 1,
    "design_eval_config": 2,
}
FILE_ROLES = (
    "pre_result", "source_approval", "approved_target", "c0", "frozen_policy",
    "frozen_config", "installed_policy", "installed_config", "installed_gate",
    "checks", "full_oracle",
)


def digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def block(name, value):
    return f"```jig-design-{name}\n{json.dumps(value, sort_keys=True)}\n```\n"


class FreshnessFixture:
    def __init__(self, base):
        self.base = base.resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        self.evidence = self.base / "evidence"
        self.evidence.mkdir()
        self.spec_dir = self.project / "docs/specs/999-synthetic"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text("---\nstatus: IN_PROGRESS\n---\n# Synthetic fixture\n")
        self.slice = self.spec_dir / "slice-01-fixture.md"
        self.context = {
            "schema": SCHEMA, "contracts": CONTRACTS,
            "files": {"runtime_files": []}, "trees": {},
        }
        for role in FILE_ROLES:
            self.put("evidence", f"pins/{role}", role)
            self.context["files"][role] = [self.ref("evidence", f"pins/{role}")]
        for role in ("runtime", "candidate_inputs", "build_output", "delivery"):
            self.put("project", f"{role}/index.html", "synthetic build A")
            self.context["trees"][role] = [self.tree("project", role)]
        self.put("project", "runtime/nested/dependency.bin", "nested runtime")
        self.context["trees"]["runtime"] = [self.tree("project", "runtime")]
        self.write_context()
        self.run = "synthetic-run-A"
        self.make_run()
        self.select()
        for name in ("compliance", "craft", "reconciliation"):
            self.verdict(name, "Synthetic unrelated prerequisites only.\n")
        self.verdict("design-review", self.body())

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

    def make_run(self, observation_overrides=None):
        response_hash = digest(self.project / "delivery/index.html")
        for state in ("normal", "open"):
            observation = {
                "run_id": self.run, "loaded_resources": [{
                    "hash": response_hash, "path": "index.html",
                    "resource_type": "document", "status": 200,
                }],
                "acquisition_nonce": "synthetic-nonce", "acquisition_error": None,
                "capture_hash": "synthetic-capture-not-a-response-body",
                "capture_id": f"synthetic-{state}", "driver": {},
                "elements": {}, "facts": {}, "root": {}, "state": state,
                "state_error": None, "viewport": {},
            }
            if state == "normal" and observation_overrides is not None:
                observation.update(observation_overrides)
            self.put("evidence", f"output/{state}.observations.json", observation)
        self.put("evidence", "output/evidence.json", {
            "kind": "design_evidence", "schema_version": 1, "run_id": self.run,
            "acquisition_nonce": "synthetic-nonce",
        })
        manifest = self.ref("evidence", "output/evidence.json")
        artifact = {
            "kind": "command_result_artifacts", "schema_version": 1,
            "run_id": self.run, "root": str(self.evidence / "output"),
            "manifest": {"path": "evidence.json", "hash": manifest["hash"]},
            "artifacts": [
                {"path": f"{state}.observations.json",
                 "hash": digest(self.evidence / f"output/{state}.observations.json")}
                for state in ("normal", "open")
            ],
        }
        self.put("evidence", "component.json", {
            "kind": "required_component_result", "schema_version": 1,
            "run_id": self.run, "evidence": [{"result_artifact": artifact}],
        })
        component = self.ref("evidence", "component.json")
        self.put("evidence", "overall.json", {
            "kind": "gate_result", "schema_version": 2, "run_id": self.run,
            "status": "pass",
            "components": [{"result": {
                "path": str(self.evidence / "component.json"),
                "hash": component["hash"],
            }}],
        })
        self.put("evidence", "acquisition.json", {
            "run_id": self.run, "envelope_hash": manifest["hash"],
            "nonce": "synthetic-nonce",
        })
        self.bindings = {
            "schema": SCHEMA, "context": self.ref("evidence", "context.json"),
            "run_id": self.run,
            "records": {
                "overall": self.ref("evidence", "overall.json"),
                "component": component, "envelope": manifest,
                "acquisition": self.ref("evidence", "acquisition.json"),
            },
            "result_artifact": artifact,
            "output": self.tree("evidence", "output"),
            "served": [{
                "capture": self.ref("evidence", f"output/{state}.observations.json"),
                "delivery": self.ref("project", "delivery/index.html"),
                "resource_path": "index.html",
            } for state in ("normal", "open")],
        }

    def select(self, selection=None, status="IN_PROGRESS"):
        self.selection = selection or {
            "schema": SCHEMA,
            "roots": {"project": str(self.project), "evidence": str(self.evidence)},
            "context": self.ref("evidence", "context.json"),
        }
        self.slice.write_text(
            f"---\nstatus: {status}\ndependencies: []\ndesign_review: true\n---\n"
            "\n## Slice 999-01 fixture\n\n"
            + block("selection", self.selection)
            + "\n### Deviation log\nSynthetic lifecycle preconditions.\n"
            "\n### Reconciliation sweep\nSynthetic fixture; no product claims.\n"
        )

    def body(self):
        return "SYNTHETIC attestation, not a genuine producer PASS.\n" + block(
            "bindings", self.bindings)

    def verdict(self, name, body):
        target = self.spec_dir / f"reviews/slice-01-{name}.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text(
            "---\nslice: 999-01 fixture\n"
            f"pass: {name}\nverdict: pass\nreviewer: synthetic\n"
            "reviewed_at: 2026-10-15T00:00:00Z\nprompt_source: synthetic\n---\n"
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
            "--reviewer", "synthetic", "--prompt-source", "synthetic",
            "--summary-file", "-", body=self.body() if body is None else body,
        )


class DesignFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="jig-design-bindings-")
        self.addCleanup(self.tmp.cleanup)
        self.f = FreshnessFixture(Path(self.tmp.name))

    def assert_refuses(self, name):
        problems = "\n".join(self.f.check())
        self.assertIn("design-freshness", problems)
        self.assertIn(name, problems)
        self.assertIn("fresh producer evidence", problems)

    def test_ac1_three_way_closed_context_required_even_for_existing_pass(self):
        self.assertEqual(self.f.check(), [])
        for role in ("approved_target", "frozen_config"):
            p = self.f.evidence / f"pins/{role}"
            original = p.read_bytes()
            p.write_text("changed")
            self.assert_refuses(role)
            p.write_bytes(original)
        self.f.verdict("design-review", "Historical plain PASS cannot downgrade selection.")
        self.assert_refuses("bindings")

    def test_ac2_unchanged_pass_refuses_changed_bytes_at_reviewed_and_done(self):
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        old_record = record.read_bytes()
        for role in ("candidate_inputs", "build_output", "delivery"):
            p = self.f.project / role / "index.html"
            original = p.read_bytes()
            p.write_text("synthetic build B")
            self.assert_refuses(role)
            new_review = self.f.record()
            self.assertEqual(new_review.returncode, 2, new_review.stdout)
            for stage, status in (("REVIEWED", "IN_PROGRESS"), ("DONE", "RECONCILED")):
                self.f.select(status=status)
                result = self.f.cli("spec-workflow/workflow.py", "transition",
                                    self.f.spec, "999-01", stage)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(role, result.stderr)
            self.assertEqual(record.read_bytes(), old_record)
            p.write_bytes(original)
            self.assertEqual(self.f.check(), [])

    def test_ac3_every_pin_runtime_capture_and_run_is_rechecked(self):
        paths = [(role, self.f.evidence / f"pins/{role}") for role in FILE_ROLES]
        paths += [
            ("runtime", self.f.project / "runtime/nested/dependency.bin"),
            ("overall", self.f.evidence / "overall.json"),
            ("component", self.f.evidence / "component.json"),
            ("envelope", self.f.evidence / "output/evidence.json"),
            ("acquisition", self.f.evidence / "acquisition.json"),
            ("output", self.f.evidence / "output/normal.observations.json"),
        ]
        for name, p in paths:
            with self.subTest(binding=name):
                original = p.read_bytes()
                p.write_bytes(original + b" ")
                self.assert_refuses(name)
                p.write_bytes(original)
                self.assertEqual(self.f.check(), [])

    def test_ac4_guard_performs_no_execution_or_network_and_missing_ref_refuses(self):
        with mock.patch("subprocess.run", side_effect=AssertionError("no execution")), \
                mock.patch("socket.socket", side_effect=AssertionError("no network")):
            self.assertEqual(self.f.check(), [])
            (self.f.project / "candidate_inputs/index.html").unlink()
            self.assert_refuses("candidate_inputs")

    def test_ac5_renewal_clears_and_outside_closure_documentation_preserves(self):
        self.f.put("project", "docs/new.md", "documentation-only, unrelated to app")
        self.assertEqual(self.f.check(), [])
        for role in ("candidate_inputs", "build_output", "delivery"):
            self.f.put("project", f"{role}/index.html", "synthetic build B")
            self.f.context["trees"][role] = [self.f.tree("project", role)]
        self.f.write_context()
        self.f.run = "synthetic-run-B"
        self.f.make_run()
        self.f.select()
        result = self.f.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        for stage in ("REVIEWED", "RECONCILED", "DONE"):
            result = self.f.cli("spec-workflow/workflow.py", "transition",
                                self.f.spec, "999-01", stage)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac6_prompt_and_live_guidance_bound_the_local_consistency_claim(self):
        result = self.f.cli("independent-review/review.py", "design-review",
                            self.f.spec, "999-01", self.f.evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        guidance = (REPO / "skills/independent-review/SKILL.md").read_text()
        for text in (result.stdout, guidance):
            self.assertIn("jig-design-bindings", text)
            self.assertIn("jig-design-selection", text)
            self.assertIn("forgery-proof", text)
            self.assertIn("sealed local bundle", text)

    def test_prompt_locates_grammar_beside_actual_helper_not_adopter_project(self):
        result = self.f.cli("independent-review/review.py", "design-review",
                            self.f.spec, "999-01", self.f.evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        grammar = REPO / "skills/independent-review/design-bindings.md"
        self.assertTrue(f"grammar documented in `{grammar}`" in result.stdout,
                        "prompt must name the installed helper's grammar path")

    def test_complete_tree_rejects_added_deleted_and_case_alias_files(self):
        p = self.f.project / "runtime/nested/extra.bin"
        p.write_text("not inventoried")
        self.assert_refuses("runtime")
        p.unlink()
        self.f.context["trees"]["runtime"][0]["files"].append(
            {"path": "INDEX.html", "hash": digest(self.f.project / "runtime/index.html")})
        self.f.write_context()
        self.f.bindings["context"] = self.f.ref("evidence", "context.json")
        self.f.select()
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("runtime")

    def test_unknown_partial_duplicate_and_nonfinite_grammar_refuses(self):
        original = copy.deepcopy(self.f.bindings)
        variants = []
        for key in ("context", "records", "result_artifact", "output", "served"):
            value = copy.deepcopy(original)
            del value[key]
            variants.append((key, value))
        value = copy.deepcopy(original)
        value["schema"] = "jig/design-freshness/99"
        variants.append(("unsupported", value))
        value = copy.deepcopy(original)
        value["unexpected"] = True
        variants.append(("keys", value))
        value = copy.deepcopy(original)
        value["output"]["files"] *= 2
        variants.append(("output", value))
        for name, value in variants:
            with self.subTest(name=name):
                self.f.verdict("design-review", block("bindings", value))
                self.assert_refuses(name)
        for raw in (
            '{"schema":NaN}', '{"schema":1e999}', '{"schema":1,"schema":2}',
            '{"schema":true}', '{}', '[]',
        ):
            self.f.verdict("design-review", f"```jig-design-bindings\n{raw}\n```\n")
            self.assert_refuses("bindings")

    def test_explicit_selection_cannot_downgrade_when_malformed_or_duplicated(self):
        original = self.f.slice.read_text()
        for selection in ("```jig-design-selection\n{}\n```\n",
                          "```jig-design-selection\n", block("selection", self.f.selection) * 2):
            self.f.slice.write_text(original.split("```jig-design-selection")[0] + selection)
            self.assert_refuses("selection")

    def test_run_links_refuse_foreign_run_and_missing_or_partial_output(self):
        component_path = self.f.evidence / "component.json"
        original = json.loads(component_path.read_text())
        overall = json.loads((self.f.evidence / "overall.json").read_text())
        for change, diagnostic in (
            ({"run_id": "foreign-run"}, "component"),
            ({"evidence": []}, "component evidence"),
            ({"evidence": [{"result_artifact": {}}]}, "component result_artifact"),
        ):
            component = {**original, **change}
            self.f.put("evidence", "component.json", component)
            self.f.bindings["records"]["component"] = self.f.ref("evidence", "component.json")
            overall["components"][0]["result"]["hash"] = digest(component_path)
            self.f.put("evidence", "overall.json", overall)
            self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
            self.f.verdict("design-review", self.f.body())
            self.assert_refuses(diagnostic)
        self.f.put("evidence", "component.json", original)
        self.f.bindings["records"]["component"] = self.f.ref("evidence", "component.json")
        overall["components"][0]["result"]["hash"] = digest(component_path)
        self.f.put("evidence", "overall.json", overall)
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.bindings["result_artifact"]["artifacts"] = []
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("result_artifact")

    def test_unsafe_roots_traversal_symlinks_and_aliases_refuse_without_reading(self):
        original = copy.deepcopy(self.f.selection)
        selections = []
        for root in ("/", str(Path.home()), str(self.f.project.parent),
                     str(self.f.project / ".." / "project")):
            selection = copy.deepcopy(original)
            selection["roots"]["project"] = root
            selections.append(selection)
        for selection in selections:
            self.f.select(selection)
            self.assert_refuses("root")
        self.f.select(original)
        self.f.bindings["records"]["overall"]["path"] = "../outside"
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("overall")
        self.f.make_run()
        p = self.f.project / "candidate_inputs/index.html"
        p.unlink()
        p.symlink_to(self.f.evidence / "pins/c0")
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("candidate_inputs")

    def test_control_character_path_is_not_a_supported_file_reference(self):
        content = (self.f.evidence / "overall.json").read_bytes()
        p = self.f.evidence / "overall\t.json"
        p.write_bytes(content)
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", p.name)
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("overall")

    def test_control_root_recording_refuses_without_overwriting_existing_pass(self):
        result = self.f.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        original = record.read_bytes()
        selection = copy.deepcopy(self.f.selection)
        for control in ("\0", "\t", "\n", "\r", "\x1f", "\x7f"):
            with self.subTest(control=repr(control)):
                selection["roots"]["project"] = str(self.f.project) + control
                self.f.select(selection)
                result = self.f.record()
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("design-freshness", result.stderr)
                self.assertIn("selection root", result.stderr)
                self.assertIn("fresh producer evidence", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("internal error", result.stderr.lower())
                self.assertEqual(record.read_bytes(), original)

    def test_control_root_reuse_refuses_before_resolution_at_reviewed_and_done(self):
        self.assertEqual(self.f.check(), [])
        selection = copy.deepcopy(self.f.selection)
        selection["roots"]["project"] = str(self.f.project) + "\0"
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        original = record.read_bytes()
        self.f.select(selection)
        results = [self.f.cli("independent-review/review.py", "check-reviews",
                              self.f.spec, "999-01", "--stage", "REVIEWED")]
        for stage, status in (("REVIEWED", "IN_PROGRESS"), ("DONE", "RECONCILED")):
            self.f.select(selection, status=status)
            results.append(self.f.cli("spec-workflow/workflow.py", "transition",
                                      self.f.spec, "999-01", stage))
        for result in results:
            with self.subTest(command=result.args):
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("design-freshness", result.stderr)
                self.assertIn("selection root", result.stderr)
                self.assertIn("fresh producer evidence", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn("internal error", result.stderr.lower())
        self.assertEqual(record.read_bytes(), original)
        with mock.patch("pathlib.Path.resolve",
                        side_effect=AssertionError("no filesystem resolve")):
            for control in ("\0", "\t", "\n", "\r", "\x1f", "\x7f"):
                selection["roots"]["project"] = str(self.f.project) + control
                problem = ev.freshness_problem(block("selection", selection), self.f.body())
                self.assertIn("design-freshness", problem)
                self.assertIn("selection root", problem)

    def test_historical_unselected_and_unflagged_behavior_unchanged(self):
        self.f.slice.write_text(self.f.slice.read_text().split("```jig-design-selection")[0])
        self.f.verdict("design-review", "Historical plain design review.")
        self.assertEqual(self.f.check(), [])
        self.f.slice.write_text(self.f.slice.read_text().replace("design_review: true", ""))
        (self.f.spec_dir / "reviews/slice-01-design-review.md").unlink()
        self.assertEqual(self.f.check(), [])

    def test_record_refuses_invalid_pass_but_preserves_nonpass_reasons(self):
        old = (self.f.spec_dir / "reviews/slice-01-design-review.md").read_bytes()
        result = self.f.record("Explicitly missing bindings; cannot pass.")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("design-freshness", result.stderr)
        self.assertEqual((self.f.spec_dir / "reviews/slice-01-design-review.md").read_bytes(), old)
        result = self.f.record("Cannot attest: closure unknown.", verdict="needs-changes")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_acquisition_requires_complete_matching_receipt_not_just_run_id(self):
        original = json.loads((self.f.evidence / "acquisition.json").read_text())
        variants = [
            {"run_id": self.f.run},
            {**original, "nonce": "foreign-nonce"},
            {**original, "kind": "unsupported-receipt"},
        ]
        for receipt in variants:
            with self.subTest(receipt=receipt):
                self.f.put("evidence", "acquisition.json", receipt)
                self.f.bindings["records"]["acquisition"] = self.f.ref(
                    "evidence", "acquisition.json")
                self.f.verdict("design-review", self.f.body())
                self.assert_refuses("acquisition")

    def test_invalid_json_bytes_refuse_with_named_role_without_echoing_content(self):
        self.f.put("evidence", "overall.json", "SYNTHETIC_PRIVATE_MARKER")
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("overall")
        self.assertNotIn("SYNTHETIC_PRIVATE_MARKER", str(self.f.check()))
        (self.f.evidence / "overall.json").write_bytes(b"\xff")
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("overall")

    def test_runtime_single_file_refs_do_not_enumerate_unrelated_versions(self):
        self.f.put("project", "versions/runtime-v1", "reviewed binary")
        self.f.context["files"]["runtime_files"] = [self.f.ref("project", "versions/runtime-v1")]
        self.f.context["trees"]["runtime"] = []
        self.f.write_context()
        self.f.bindings["context"] = self.f.ref("evidence", "context.json")
        self.f.select()
        self.f.verdict("design-review", self.f.body())
        self.f.put("project", "versions/unrelated-v2", "not part of this runtime")
        self.assertEqual(self.f.check(), [])
        self.f.put("project", "versions/runtime-v1", "changed binary")
        self.assert_refuses("runtime_files")

    def test_runtime_tree_symlink_loop_and_noncanonical_producer_link_refuse(self):
        p = self.f.project / "runtime/loop"
        p.symlink_to(p)
        self.assert_refuses("runtime")
        p.unlink()
        overall = json.loads((self.f.evidence / "overall.json").read_text())
        overall["components"][0]["result"]["path"] = str(
            self.f.evidence) + "//component.json"
        self.f.put("evidence", "overall.json", overall)
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("component")

    def test_producer_scalar_component_null_link_keeps_pinned_overall_authority(self):
        overall = json.loads((self.f.evidence / "overall.json").read_text())
        overall["components"].append({
            "component": "design_fidelity", "result": None,
            "score": 0.99, "exit_code": 0, "weight": 1,
        })
        self.f.put("evidence", "overall.json", overall)
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.verdict("design-review", self.f.body())
        self.assertEqual(self.f.check(), [])
        overall["components"] = overall["components"][1:]
        self.f.put("evidence", "overall.json", overall)
        self.f.bindings["records"]["overall"] = self.f.ref("evidence", "overall.json")
        self.f.verdict("design-review", self.f.body())
        self.assert_refuses("component")

    def test_actual_shape_observation_declares_response_hash_not_capture_file_hash(self):
        self.assertFalse((self.f.evidence / "output/response.html").exists())
        self.assertNotEqual(
            digest(self.f.evidence / "output/normal.observations.json"),
            digest(self.f.project / "delivery/index.html"),
        )
        self.assertEqual(self.f.check(), [])
        result = self.f.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        original = (self.f.project / "delivery/index.html").read_bytes()
        self.f.put("project", "delivery/index.html", "same URL, changed served bundle")
        self.assert_refuses("delivery")
        (self.f.project / "delivery/index.html").write_bytes(original)
        self.assertEqual(self.f.check(), [])

    def test_observation_links_refuse_partial_foreign_duplicate_and_unsupported_records(self):
        row = {
            "hash": digest(self.f.project / "delivery/index.html"),
            "path": "index.html", "resource_type": "document", "status": 200,
        }
        variants = [
            {"run_id": "foreign-run"},
            {"kind": "unsupported-observation"},
            {"loaded_resources": None},
            {"loaded_resources": []},
            {"loaded_resources": [row, row]},
            {"loaded_resources": [{**row, "path": "other.html"}]},
            {"loaded_resources": [{k: v for k, v in row.items() if k != "hash"}]},
            {"loaded_resources": [{**row, "hash": "not-a-raw-sha256"}]},
            {"loaded_resources": [{**row, "hash": "sha256:" + "0" * 64}]},
            {"loaded_resources": [{**row, "resource_type": "image"}]},
            {"loaded_resources": [{**row, "status": 201}]},
            {"loaded_resources": [{**row, "status": "200"}]},
            {"loaded_resources": [{**row, "unexpected": True}]},
        ]
        for override in variants:
            with self.subTest(override=override):
                # Re-pin synthetic containers to exercise the link, not an outer hash failure.
                self.f.make_run(override)
                self.f.verdict("design-review", self.f.body())
                self.assert_refuses("served")

    def test_observation_selection_requires_exact_safe_resource_and_output_membership(self):
        self.f.make_run()
        original = copy.deepcopy(self.f.bindings["served"])
        variants = []
        for path in ("other.html", "../index.html", "/index.html"):
            link = copy.deepcopy(original[0])
            link["resource_path"] = path
            variants.append([link])
        variants.append([{k: v for k, v in original[0].items() if k != "resource_path"}])
        variants.append([original[0], original[0]])
        self.f.put("evidence", "outside.observations.json",
                   (self.f.evidence / "output/normal.observations.json").read_text())
        outside = copy.deepcopy(original[0])
        outside["capture"] = self.f.ref("evidence", "outside.observations.json")
        variants.append([outside])
        for links in variants:
            with self.subTest(links=links):
                self.f.bindings["served"] = links
                self.f.verdict("design-review", self.f.body())
                self.assert_refuses("served")


if __name__ == "__main__":
    unittest.main()
