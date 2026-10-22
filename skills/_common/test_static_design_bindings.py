"""120-01 TEST ONLY synthetic generic static records; no producer execution."""

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
from _common.test_design_bindings import GenericFixture, block, digest

# Lazy enough for baseline public-rail tests to witness the missing gate.
try:
    from _common import design_bindings as db
except ImportError:
    db = None

SCHEMA = "jig/static-design-freshness/1"
CONTRACTS = {
    "vellum_input": "vellum-confirmed-source/0.2",
    "source_profile": "static-css-subset/1",
    "gate_result": 2,
    "required_component_result": 1,
    "command_result_artifacts": 1,
    "static_source_contract_evidence": 1,
    "static_app_policy": "static-source-contract-app/1",
    "snapshot_candidate": 1,
    "snapshot_build": 1,
}


def identity(domain, value):
    separator = b"\0" if domain.startswith("vellum-") else b"\n"
    text = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=not domain.startswith("vellum-"), allow_nan=False)
    payload = (text + ("\n" if domain.startswith("vellum-") else "")).encode()
    return "sha256:" + hashlib.sha256(domain.encode() + separator + payload).hexdigest()


class StaticFixture(GenericFixture):
    def __init__(self, base, source_archive="SOURCE, not APP", extra_input=False,
                 variant="notice", revision=None):
        self.base = base.resolve()
        self.project = self.base / "project"
        self.evidence = self.base / "evidence"
        self.project.mkdir()
        self.evidence.mkdir()
        self.spec_dir = self.project / "docs/specs/999-synthetic"
        self.spec_dir.mkdir(parents=True)
        self.spec = self.spec_dir / "spec.md"
        self.spec.write_text("---\nstatus: IN_PROGRESS\n---\n# SYNTHETIC\n")
        self.slice = self.spec_dir / "slice-01-fixture.md"
        self.run = "41a3554e-8fd3-4d14-a59c-e7b8f2ec7593"
        self.ids = (["caption-text", "marker-width"] if variant == "notice"
                    else ["action-label", "editor-height", "heading-text"])
        self.nonce = "synthetic-nonce"
        self.put("project", "originals/direction.html", "SOURCE, not APP")
        if revision == "git":
            self.git("init", "-q")
            self.git("-c", "user.name=TEST ONLY", "-c", "user.email=test@example.invalid",
                     "commit", "-q", "--allow-empty", "-m", "TEST ONLY source epoch")
            revision = self.git("rev-parse", "HEAD").stdout.strip()
        self.put("project", "source/originals/direction.html", source_archive)
        self.put("project", "source/source.png", "synthetic image")
        facts = (
            (("caption-text", "caption", "text", "text-content-exact-v0", "text", "Caption"),
             ("marker-width", "marker", "width", "dom-bounds-csspx-v0", "CSSpx", "8"))
            if variant == "notice" else
            (("action-label", "submit", "text", "text-content-exact-v0", "text", "Send"),
             ("editor-height", "composer", "height", "dom-bounds-csspx-v0", "CSSpx", "160"),
             ("heading-text", "title", "text", "text-content-exact-v0", "text", "Compose"))
        )
        constraints = [
            {"id": name, "element": role, "property": prop, "normalizer": norm,
             "comparison": "exact", "units": units, "tolerance": "0",
             "direction": {"kind": "literal", "value": value, "rationale": "synthetic"}}
            for name, role, prop, norm, units, value in facts
        ]
        manifest = {
            "version": CONTRACTS["vellum_input"], "profile": CONTRACTS["source_profile"],
            "required": constraints, "environment": {"viewport": {"width": 800, "height": 600}},
            "view": {"root": "#source"},
            "elements": {role: {"selector": "#" + role} for _, role, *_ in facts},
            "coverage": {"residuals": ["No visual/fullAPP/JigDONE certification"]},
        }
        self.put("project", "source/manifest.json", manifest)
        core = {
            "version": CONTRACTS["vellum_input"], "profile": CONTRACTS["source_profile"],
            "manifest": manifest, "inventory": self.ids, "policy": constraints,
            "bindings": {"view": manifest["view"], "elements": manifest["elements"]},
            "origin": {"root": str(self.project / "originals"), "git_revision": revision},
            "originals": {"direction.html": {
                "path": "originals/direction.html",
                "hash": digest(self.project / "originals/direction.html")[7:]}},
            "resources": [], "reference": {}, "capture": {}, "artifacts": [
                {"path": r["path"], "hash": r["hash"][7:]}
                for r in self.tree("project", "source")["files"]],
        }
        request = {
            "version": CONTRACTS["vellum_input"], "profile": CONTRACTS["source_profile"],
            "target_revision": identity("vellum-confirmed-target-core-v2", core)[7:],
        }
        # The source API's finite review-request domains, not a call to inspect/verify.
        for name, value in {
            "inventory": core["inventory"], "policy": core["policy"],
            "bindings": core["bindings"], "resources": core["resources"],
            "source": {"origin": core["origin"], "originals": core["originals"]},
            "reference": core["reference"], "capture": core["capture"],
            "scope": manifest["view"], "coverage": manifest["coverage"], "manifest": manifest,
        }.items():
            request[name] = identity("vellum-confirmed-" + name + "-v2", value)[7:]
        self.put("project", "source/request.json", request)
        self.put("project", "source/approval.json", {
            "version": CONTRACTS["vellum_input"], "request": request,
            "request_hash": identity("vellum-confirmed-review-request-v2", request)[7:],
            "reviewer": "independent-synthetic", "independent": True,
            "decision": "approve", "reason": "SYNTHETIC SOURCE only",
        })
        self.put("project", "source/input.json", {
            **({"unknown_source_field": True} if extra_input else {}),
            "version": CONTRACTS["vellum_input"], "profile": CONTRACTS["source_profile"],
            "kind": "approved", "core": core, "request": request,
            "target_revision": request["target_revision"],
            "artifacts": [{"path": r["path"], "hash": r["hash"][7:]}
                          for r in self.tree("project", "source")["files"]],
        })
        for name in ("native.py", "grader.py", "oracle.sh", "fragment", "source.md"):
            self.put("project", "installed/" + name, "synthetic frozen " + name)
        self.put("project", ".servo/required_runtime.py", "synthetic frozen native.py")
        self.put("project", "oracle.sh", 'COMPONENTS=(\n  "spec_oracle_static:1"\n)\n')
        for name in (
            "static_contract.py", "static_snapshot.py", "evidence_io.py", "evidence_runtime.py",
            "producer/confirmed_source.py", "producer/capture_confirmed.py",
            "producer/design_input.py", "producer/redline_intake.py",
            "producer/resolve_redline.py", "producer/validate_redline.py",
        ):
            self.put("project", "helpers/" + name, "synthetic helper " + name)
        self.put("project", "runtime/bin/python-real", "synthetic interpreter")
        self.put("project", "runtime/dependency.data", "synthetic package metadata")
        self.put("project", "runtime/dependency/child", "synthetic package child")
        self.put("project", "runtime/browser/Versions/1/browser", "synthetic browser")
        (self.project / "runtime/browser/Current").symlink_to("Versions/1")
        (self.project / "runtime/bin/python").symlink_to("python-real")
        self.put("project", "helpers/runtime-files.json", [
            {"path": str(p), "hash": digest(p)}
            for p in sorted((self.project / "runtime").rglob("*"))
            if p.is_file() and not p.is_symlink()])
        self.members = [
            {"path": "Current", "kind": "symlink", "target": "Versions/1"},
            {"path": "Versions", "kind": "directory"},
            {"path": "Versions/1", "kind": "directory"},
            {"path": "Versions/1/browser", "kind": "file"},
        ]
        self.put("project", "helpers/browser-membership.json", self.members)
        runtime = {
            "manifest": self.raw("helpers/runtime-files.json"),
            "browser_membership": self.raw("helpers/browser-membership.json"),
            "browser_root": str(self.project / "runtime/browser"),
            "executable": str(self.project / "runtime/bin/python-real"),
            "bash": str(self.project / "runtime/bin/python-real"),
            "browser_hash": digest(self.project / "runtime/browser/Versions/1/browser"),
            "python": "3.13.1", "prefix": str(self.project / "runtime"),
            "os": "TEST ONLY synthetic OS", "browser_version": "TEST ONLY",
            "dependencies": {k: "TEST ONLY" for k in
                             ("playwright", "greenlet", "pyee", "typing_extensions")},
            "site_roots": [str(self.project / "runtime/dependency")],
            "module_origins": {
                k: str(self.project / "runtime/dependency.data") for k in
                ("playwright", "greenlet", "pyee", "typing_extensions")},
            "native_resolutions": [],
        }
        config = {
            "kind": "static_snapshot_candidate", "schema_version": 1, "entry": "/panel.html",
            "resources": [
                {"url": "/panel.css", "path": "panel.css", "content_type": "text/css"},
                {"url": "/panel.html", "path": "panel.html", "content_type": "text/html"},
            ], "metadata": ["preselection.json"],
        }
        if variant != "notice":
            config.update(entry="/compose/index.html", resources=[
                {"url": "/assets/composer.css", "path": "styles/editor.css",
                 "content_type": "text/css"},
                {"url": "/compose/index.html", "path": "views/compose.html",
                 "content_type": "text/html; charset=utf-8"},
                {"url": "/data/hints.json", "path": "data/hints.json",
                 "content_type": "application/json"},
            ], metadata=["notes/scope.txt", "notes/selection.json"])
        self.put("project", "candidate/candidate.json", config)
        for name in config["metadata"]:
            self.put("project", "candidate/" + name, "TEST ONLY independent selection")
        for name in (r["path"] for r in config["resources"]):
            for directory in ("candidate", "build/output", "delivery"):
                self.put("project", directory + "/" + name, "synthetic " + name)
        recipe = self.raw("helpers/static_snapshot.py")
        inputs = self.tree("project", "candidate")["files"]
        outputs = self.tree("project", "build/output")["files"]
        build = {
            "kind": "static_snapshot_build", "schema_version": 1,
            "source": str(self.project / "candidate"), "configuration": config,
            "inputs": inputs, "outputs": outputs, "recipe": recipe,
            "input_hash": identity("servo-static-snapshot-input-v1",
                                   {"files": inputs, "recipe": recipe}),
            "output_hash": identity("servo-static-snapshot-output-v1", outputs),
        }
        self.put("project", "build/build.json", build)
        self.put("project", "candidate-selection.json", {"build": "build", "delivery": "delivery"})
        self.policy = {
            "kind": "static_source_contract_app_policy", "schema_version": 1,
            "version": CONTRACTS["static_app_policy"], "target": str(self.project),
            "producer": str(self.project / "helpers/producer"),
            "source": {
                "root": str(self.project / "source"),
                "contract_version": CONTRACTS["vellum_input"],
                "profile": CONTRACTS["source_profile"],
                "input_hash": digest(self.project / "source/input.json"),
                "approval_hash": digest(self.project / "source/approval.json"),
                "target_revision": request["target_revision"],
                "request_hash": identity("vellum-confirmed-review-request-v2", request)[7:],
            },
            "constraints": [
                {**r, "app_normalizer": {"text": "text-content-exact-visible-app/1",
                                        "width": "dom-bounds-csspx-v0",
                                        "height": "dom-bounds-csspx-v0"}[r["property"]]}
                for r in constraints],
            "environment": manifest["environment"], "bindings": {"root": "#app"},
            "normalizers": {
                "properties": {
                    "presence": "unique-scoped-visible-presence-app/1",
                    "text": "text-content-exact-visible-app/1",
                    "background-color": "rgba8-exact-v0", "color": "rgba8-exact-v0",
                    "font-family": "css-computed-family-list/1", "font-size": "css-scalar-v0",
                    "font-weight": "css-scalar-v0", "width": "dom-bounds-csspx-v0",
                    "height": "dom-bounds-csspx-v0"},
                "visibility": "scoped-dom-text-ancestor-overflow-and-paint-intersection-app/3",
                "family": {"version": "css-computed-family-list/1"},
            },
            "selection": "candidate-selection.json",
            "output_root": "spec/oracle/static/runs/{run_id}/observed", "runtime": runtime,
            "evaluator_files": [self.raw("helpers/" + r["path"])
                                for r in self.tree("project", "helpers")["files"]],
            "residuals": manifest["coverage"]["residuals"],
        }
        policy_hash = identity("servo-static-app-policy-v1", self.policy)
        self.put("project", "policy-review.json", {
            "verdict": "pass", "author": "author", "reviewer": "independent",
            "policy_hash": policy_hash, "scope": "SYNTHETIC finite", "reason": "synthetic",
        })
        self.policy["approval"] = {
            "decision": "approved", "author": "author", "reviewer": "independent",
            "policy_hash": policy_hash,
            "review_record_hash": digest(self.project / "policy-review.json"),
        }
        self.put("project", "app-policy.json", self.policy)
        command = [str(self.project / "runtime/bin/python"), "-I", "-B",
                   str(self.project / "helpers/static_contract.py"), "evaluate", "--policy",
                   str(self.project / "app-policy.json"), "--constraint"]
        self.checks = {
            "schema_version": 1, "approval_status": "approved",
            "required_policy": {"schema_version": 1, "enabled": True},
            "source_spec_path": "installed/source.md",
            "source_hash": digest(self.project / "installed/source.md"),
            "residual_judgment": [], "checks": [
                {"id": name, "family": "command", "command": command + [name],
                 "required": True, "refusal_exit_codes": [2], "timeout": 180,
                 "result_artifact": {
                     "root": self.policy["output_root"], "manifest": "evidence.json",
                     "schema_version": 1, "kind": "static_source_contract_evidence"}}
                for name in self.ids],
        }
        content = {k: self.checks[k] for k in ("checks", "residual_judgment", "required_policy")}
        content.update(schema_version=1, kind="required_plan_content")
        grade = "sha256:" + hashlib.sha256(json.dumps(
            content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        binding = {
            "kind": "approved_required_binding", "schema_version": 1,
            "component": "spec_oracle_static", "enabled": True, "required_ids": self.ids,
            "checks_path": "checks.json", "config_hash": grade,
            "source_identity": self.raw("installed/source.md", absolute=False),
            "evaluator": self.raw("installed/grader.py", absolute=False),
            "required_runtime": self.raw("installed/native.py", absolute=False),
            "evaluator_artifacts": [self.raw("installed/oracle.sh", absolute=False)],
            "fragment_hash": digest(self.project / "installed/fragment"),
            "driver_hash": "sha256:" + "a" * 64, "threshold_default": "0.5",
        }
        self.checks.update(approved_content_hash=grade, approved_required_binding=binding)
        self.put("project", "checks.json", self.checks)
        self.put("project", "required-policy.json", {
            "kind": "required_policy", "schema_version": 1, "components": [binding],
            "runtime_hash": digest(self.project / "installed/native.py"),
            "driver_prefix_hash": "sha256:" + "b" * 64,
        })
        self.put("evidence", "pre-result.json", {"synthetic": "independent selection, not result"})
        roles = {
            "app_policy": "app-policy.json", "policy_review": "policy-review.json",
            "input": "source/input.json", "approval": "source/approval.json",
            "request": "source/request.json", "manifest": "source/manifest.json",
            "checks": "checks.json", "required_policy": "required-policy.json",
            "build": "build/build.json", "selection": "candidate-selection.json",
            "runtime_manifest": "helpers/runtime-files.json",
            "browser_manifest": "helpers/browser-membership.json",
        }
        self.context = {
            "schema": SCHEMA, "contracts": copy.deepcopy(CONTRACTS),
            "files": {k: self.ref("project", v) for k, v in roles.items()},
            "trees": {role: self.tree("project", directory) for role, directory in {
                "source": "source", "helpers": "helpers", "candidate_inputs": "candidate",
                "build_output": "build/output", "delivery": "delivery"}.items()},
            "browser": {"root": "project", "path": "runtime/browser"},
            "aliases": [{"root": "project", "path": "runtime/bin/python", "target": "python-real"}],
        }
        self.context["files"].update(
            pre_result=[self.ref("evidence", "pre-result.json")],
            pins=[self.ref("project", "installed/" + name) for name in
                  ("native.py", "grader.py", "oracle.sh", "fragment", "source.md")]
            + [self.ref("project", name) for name in
               ("originals/direction.html", ".servo/required_runtime.py", "oracle.sh")],
            runtime_files=[self.ref("project", p.relative_to(self.project).as_posix())
                           for p in sorted((self.project / "runtime").rglob("*"))
                           if p.is_file() and not p.is_symlink()],
        )
        self.write_context()
        self.make_run()
        self.select()
        for name in ("compliance", "craft", "reconciliation"):
            self.verdict(name, "SYNTHETIC unrelated lifecycle precondition.\n")
        self.verdict("design-review", self.body())

    def raw(self, name, absolute=True):
        return {"path": str(self.project / name) if absolute else name,
                "hash": digest(self.project / name)}

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.project / "originals"), *args],
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            capture_output=True, text=True, check=True, timeout=10,
        )

    def select(self, selection=None, status="IN_PROGRESS"):
        super().select(selection or {
            "schema": SCHEMA,
            "roots": {"project": str(self.project), "evidence": str(self.evidence)},
            "context": self.ref("evidence", "context.json")}, status)

    def make_run(self):
        out = self.policy["output_root"].replace("{run_id}", self.run)
        (self.project / out / "evidence.json").unlink(missing_ok=True)
        claim = {"run_id": self.run, "nonce": self.nonce,
                 "policy_hash": self.policy["approval"]["policy_hash"], "output_root": out}
        self.put("project", out + "/claim.json", claim)
        self.put("project", out + "/app.png", "synthetic screenshot")
        resources = []
        for resource in self.policy_build()["configuration"]["resources"]:
            path = resource["path"]
            self.put("project", out + "/responses/" + path + ".body",
                     (self.project / "delivery" / path).read_text())
            resources.append({
                **resource, "artifact": "responses/" + path + ".body",
                "hash": digest(self.project / "delivery" / path), "status": 200,
                "resource_type": {"text/html": "document", "text/css": "stylesheet",
                                  "application/json": "fetch"}[
                                      resource["content_type"].split(";")[0]],
            })
        self.put("project", out + "/observations.json", {
            "run_id": self.run, "acquisition_nonce": self.nonce, "acquisition_error": None,
            "error": None, "environment": self.policy["environment"],
            "capture_hash": digest(self.project / out / "app.png"),
            "loaded_resources": resources, "elements": {}, "settlement": {"unstable_ids": []},
        })
        envelope = {
            "kind": "static_source_contract_evidence", "schema_version": 1,
            "version": CONTRACTS["static_app_policy"], "run_id": self.run,
            "acquisition_nonce": self.nonce, "source": self.policy["source"],
            "policy": {"hash": claim["policy_hash"], "required_ids": self.ids},
            "evaluator": self.policy["evaluator_files"], "runtime": self.policy["runtime"],
            "build": self.policy_build(), "current_delivery": {
                "path": str(self.project / "delivery"),
                "selection_hash": digest(self.project / "candidate-selection.json"),
                "output_hash": self.policy_build()["output_hash"]},
            "observations": {"path": "observations.json",
                             "hash": digest(self.project / out / "observations.json")},
            "constraints": [{**r, "required": True, "status": "pass", "reason": "synthetic pass",
                             "observation": {"path": "observations.json", "role": r["element"],
                                             "property": r["property"]}}
                            for r in self.policy["constraints"]],
            "summary": {"status": "pass", "required_status": "pass", "passed": self.ids,
                        "failed": [], "unknown": [],
                        "counts": {"pass": len(self.ids), "fail": 0, "unknown": 0}},
            "measurement_diagnostic": {"passed": len(self.ids), "total": len(self.ids),
                                       "claim": "static-measurement-only-not-visual-quality"},
            "residuals": self.policy["residuals"],
            "artifacts": self.tree("project", out)["files"],
        }
        self.put("project", out + "/evidence.json", envelope)
        artifact = {
            "kind": "command_result_artifacts", "schema_version": 1, "run_id": self.run,
            "root": out, "manifest": {"path": "evidence.json",
                                    "hash": digest(self.project / out / "evidence.json")},
            "artifacts": envelope["artifacts"],
        }
        items = [{"id": name, "evidence_index": i, "status": "pass", "reason": "synthetic pass"}
                 for i, name in enumerate(self.ids)]
        required = {"ids": self.ids, "items": items, "failed": [], "unknown": [],
                    "passed": self.ids, "status": "pass",
                    "counts": {"pass": len(self.ids), "fail": 0, "unknown": 0}}
        self.put("project", "runs/" + self.run + "/result.json", {
            "kind": "required_component_result", "schema_version": 1, "run_id": self.run,
            "component": "spec_oracle_static",
            "config_hash": self.checks["approved_content_hash"],
            "policy_hash": digest(self.project / "required-policy.json"),
            "evaluator_hash": digest(self.project / "installed/grader.py"),
            "source_identity": self.checks["approved_required_binding"]["source_identity"],
            "required": required, "score": 1.0,
            "evidence": [
                {"kind": "evidence", "schema_version": 1, "family": "command",
                 "ac_id": name, "check_id": name, "status": "pass", "exit_code": 0,
                 "message": "synthetic pass", "command": self.checks["checks"][i]["command"],
                 "result_artifact": artifact} for i, name in enumerate(self.ids)],
        })
        self.put("project", "gate/overall.json", {
            "kind": "gate_result", "schema_version": 2, "run_id": self.run,
            "status": "pass", "exit_code": 0, "reason": None, "composite": 1.0, "threshold": 0.0,
            "threshold_override": {"source": "environment", "value": "0"},
            "policy_hash": digest(self.project / "required-policy.json"), "missing": [],
            "components": [{"component": "spec_oracle_static", "score": 1.0,
                            "exit_code": 0, "weight": 1.0,
                            "result": self.raw("runs/" + self.run + "/result.json")}],
            "required": {**required, "items": [{**r, "component": "spec_oracle_static"}
                                              for r in items]},
        })
        self.put("project", "gate/oracle-result.json",
                 json.loads((self.project / "gate/overall.json").read_text()))
        self.put("project", "gate/invocation.json", {
            "kind": "gate_invocation", "schema_version": 1, "run_id": self.run})
        self.put("project", "gate/accepted.json", self.raw("gate/overall.json"))
        self.put("project", "gate/claim.json", claim)
        self.put("project", "gate/receipt.json", {
            "run_id": self.run, "nonce": self.nonce,
            "envelope_hash": digest(self.project / out / "evidence.json")})
        self.bindings = {
            "schema": SCHEMA, "context": self.ref("evidence", "context.json"), "run_id": self.run,
            "records": {role: self.ref("project", path) for role, path in {
                "overall": "gate/overall.json", "oracle_result": "gate/oracle-result.json",
                "component": "runs/" + self.run + "/result.json",
                "invocation": "gate/invocation.json",
                "accepted": "gate/accepted.json", "claim": "gate/claim.json",
                "receipt": "gate/receipt.json", "envelope": out + "/evidence.json"}.items()},
            "output": self.tree("project", out),
        }

    def policy_build(self):
        return json.loads((self.project / "build/build.json").read_text())

    def problem(self):
        return db.freshness_problem(self.slice.read_text(), self.body())

    def repin_record(self, role, change):
        ref = self.bindings["records"][role]
        path = self.root(ref["root"]) / ref["path"]
        value = json.loads(path.read_text())
        change(value)
        self.put(ref["root"], ref["path"], value)
        self.bindings["records"][role] = self.ref(ref["root"], ref["path"])

    def sync_result_links(self):
        """Repin COPY-only synthetic links; never repairs altered semantic rows."""
        out = self.policy["output_root"].replace("{run_id}", self.run)
        envelope_path = self.project / out / "evidence.json"
        envelope = json.loads(envelope_path.read_text())
        envelope["artifacts"] = [r for r in self.tree("project", out)["files"]
                                 if r["path"] != "evidence.json"]
        envelope["observations"]["hash"] = digest(self.project / out / "observations.json")
        self.put("project", out + "/evidence.json", envelope)
        component_path = f"runs/{self.run}/result.json"
        component = json.loads((self.project / component_path).read_text())
        for row in component["evidence"]:
            row["result_artifact"]["manifest"]["hash"] = digest(envelope_path)
            row["result_artifact"]["artifacts"] = envelope["artifacts"]
        self.put("project", component_path, component)
        overall = json.loads((self.project / "gate/overall.json").read_text())
        overall["components"][0]["result"]["hash"] = digest(self.project / component_path)
        for name in ("overall", "oracle-result"):
            self.put("project", f"gate/{name}.json", overall)
        self.put("project", "gate/accepted.json", self.raw("gate/overall.json"))
        self.put("project", "gate/receipt.json", {
            "run_id": self.run, "nonce": self.nonce, "envelope_hash": digest(envelope_path)})
        for role, ref in self.bindings["records"].items():
            self.bindings["records"][role] = self.ref(ref["root"], ref["path"])
        self.bindings["output"] = self.tree("project", out)


class StaticBindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="jig-static-bindings-")
        self.addCleanup(self.tmp.cleanup)
        self.f = StaticFixture(Path(self.tmp.name))

    def test_ac1_vellum_and_servo_canonical_domains_are_not_interchangeable(self):
        from _common.static_design_bindings import identity
        value = {"a": "é"}
        source_bytes = b'vellum-confirmed-test-v2\0{"a":"\xc3\xa9"}\n'
        expected = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        self.assertEqual(identity("vellum-confirmed-test-v2", value), expected)
        static_bytes = b'servo-static-test-v1\n{"a":"\\u00e9"}'
        self.assertEqual(identity("servo-static-test-v1", value),
                         "sha256:" + hashlib.sha256(static_bytes).hexdigest())
        with self.assertRaises(db.BindingError):
            identity("vellum-confirmed-test-v2", {"not": 1.5})

    def test_ac1_public_record_and_check_accept_distinct_static_contract(self):
        self.assertEqual(self.f.problem(), "")
        recorded = self.f.record()
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        result = self.f.cli("independent-review/review.py", "check-reviews",
                            self.f.spec, "999-01", "--stage", "REVIEWED")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("static_source_contract_evidence", (
            self.f.project / self.f.bindings["records"]["envelope"]["path"]).read_text())

    def test_ac1_ac6_ac8_both_generic_profiles_cross_public_record_check_and_lifecycle(self):
        for variant in ("notice", "composer"):
            with self.subTest(profile=variant), tempfile.TemporaryDirectory() as tmp:
                f = StaticFixture(Path(tmp), variant=variant)
                prompt = f.cli("independent-review/review.py", "design-review",
                               f.spec, "999-01", f.project / "app-policy.json")
                self.assertEqual(prompt.returncode, 0, prompt.stderr)
                self.assertIn(SCHEMA, prompt.stdout)
                self.assertEqual(f.record().returncode, 0)
                for stage in ("REVIEWED", "RECONCILED"):
                    check = f.cli("independent-review/review.py", "check-reviews",
                                  f.spec, "999-01", "--stage", stage)
                    self.assertEqual(check.returncode, 0, check.stderr)
                for stage in ("REVIEWED", "RECONCILED", "DONE"):
                    result = f.cli("spec-workflow/workflow.py", "transition",
                                   f.spec, "999-01", stage)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac5_retired_record_refusal_is_atomic_and_transitions_do_not_change_state(self):
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        before = record.read_bytes()
        for schema in ("jig/design-freshness/1", "vellum-design-input/0.1-pilot"):
            for selection, binding in ((schema, schema), (SCHEMA, schema), (schema, SCHEMA)):
                self.f.select({**self.f.selection, "schema": selection})
                body = block("bindings", {**self.f.bindings, "schema": binding})
                result = self.f.record(body)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("retired", result.stderr)
                self.assertEqual(record.read_bytes(), before)
                # TEST ONLY injection exercises reuse of invalid evidence; the
                # public writer above correctly refused to write this body.
                self.f.verdict("design-review", body)
                for stage, status in (("REVIEWED", "IN_PROGRESS"), ("DONE", "RECONCILED")):
                    self.f.select({**self.f.selection, "schema": selection}, status=status)
                    old_state = self.f.slice.read_bytes()
                    result = self.f.cli("spec-workflow/workflow.py", "transition",
                                        self.f.spec, "999-01", stage)
                    self.assertEqual(result.returncode, 2, result.stdout)
                    self.assertEqual(self.f.slice.read_bytes(), old_state)
                record.write_bytes(before)

    def test_ac3_changed_git_head_with_identical_original_bytes_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = StaticFixture(Path(tmp), revision="git")
            self.assertEqual(f.record().returncode, 0)
            original = (f.project / "originals/direction.html").read_bytes()
            f.git("-c", "user.name=TEST ONLY", "-c", "user.email=test@example.invalid",
                  "commit", "-q", "--allow-empty", "-m", "TEST ONLY next source epoch")
            self.assertEqual((f.project / "originals/direction.html").read_bytes(), original)
            result = f.record()
            self.assertEqual(result.returncode, 2)
            self.assertIn("git", result.stderr)
            self.assertTrue(f.check())

    def test_ac3_helper_membership_and_module_origins_are_finite_successor_profile(self):
        from _common.static_design_bindings import StaticReadback
        for helper in ("card_evidence.py", "approved_card.py", "unknown.py"):
            path = self.f.put("project", "helpers/" + helper, "TEST ONLY unapproved helper")
            self.f.context["trees"]["helpers"] = self.f.tree("project", "helpers")
            self.f.write_context()
            self.f.select()
            self.f.bindings["context"] = self.f.selection["context"]
            checker = StaticReadback(self.f.selection, self.f.bindings)
            checker.load_context()
            with self.assertRaisesRegex(db.BindingError, "helper"):
                checker.source_policy()
            path.unlink()
        self.f.context["trees"]["helpers"] = self.f.tree("project", "helpers")
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        for origins in ({}, {**self.f.policy["runtime"]["module_origins"],
                            "producer": str(self.f.project / "runtime/dependency.data")}):
            checker = StaticReadback(self.f.selection, self.f.bindings)
            checker.load_context()
            policy = copy.deepcopy(self.f.policy)
            policy["runtime"]["module_origins"] = origins
            with self.assertRaisesRegex(db.BindingError, "module origins"):
                checker.runtime(policy)

    def test_ac3_execution_failure_is_explicit_nonclear_not_null_source_identity(self):
        with mock.patch("subprocess.run", side_effect=PermissionError("TEST ONLY denied")):
            self.assertIn("git", self.f.problem())

    def configure_aliases(self, targets, declared=None):
        """TEST ONLY symlink graph; aliases never become ordinary Ref authority."""
        directory = self.f.project / "runtime/bin"
        for name, target in targets.items():
            path = directory / name
            path.unlink(missing_ok=True)
            path.symlink_to(target)
        self.f.context["aliases"] = [
            {"root": "project", "path": "runtime/bin/" + name, "target": targets[name]}
            for name in (targets if declared is None else declared)]
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]

    def test_ac3_interpreter_alias_missing_hop_refuses_atomically_before_and_after_tamper(self):
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        before = record.read_bytes()
        self.configure_aliases({"python": "hop", "hop": "python-real"}, declared=["python"])
        for destination in ("python-real", "../dependency.data"):
            hop = self.f.project / "runtime/bin/hop"
            hop.unlink()
            hop.symlink_to(destination)
            result = self.f.record()
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("alias", result.stderr)
            self.assertEqual(record.read_bytes(), before)

    def test_ac3_complete_interpreter_alias_chain_passes_and_literal_tamper_refuses(self):
        self.configure_aliases({"python": "hop", "hop": "python-real"})
        self.assertEqual(self.f.problem(), "")
        result = self.f.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        hop = self.f.project / "runtime/bin/hop"
        hop.unlink()
        hop.symlink_to("../dependency.data")
        self.assertIn("alias", self.f.problem())
        self.assertEqual(self.f.record().returncode, 2)
        hop.unlink()
        hop.symlink_to("python-real")
        self.assertEqual(self.f.problem(), "")
        with self.assertRaises(db.BindingError):
            db._Reader(self.f.selection["roots"]).ref(
                self.f.ref("project", "runtime/bin/hop"), "no-follow alias Ref")

    def test_ac3_interpreter_alias_cycles_foreign_and_oversized_chains_refuse(self):
        cases = [
            {"python": "hop", "hop": "python"},
            {"python": "../dependency.data"},
            {"python": "/foreign/interpreter"},
            {"python": "unlisted"},
            {"python": "hop/../python-real", "hop": "../dependency"},
            {"python": "hop0", **{f"hop{i}": f"hop{i + 1}" for i in range(64)},
             "hop64": "python-real"},
        ]
        for targets in cases:
            with self.subTest(targets=targets):
                self.configure_aliases(targets)
                self.assertIn("alias", self.f.problem())
                self.assertEqual(self.f.record().returncode, 2)

    def test_ac3_interpreter_alias_absolute_and_parent_relative_targets_are_supported(self):
        canonical = self.f.project / "runtime/bin/python-real"
        for target in (str(canonical), "../bin/python-real"):
            self.configure_aliases({"python": target})
            self.assertEqual(self.f.problem(), "")

    def configure_directory_aliases(self):
        """TEST ONLY: venv -> version alias -> package directory -> binary alias."""
        labels = self.f.base / "metadata"
        labels.mkdir()
        binary = self.f.project / "runtime/package/bin/python3.14"
        binary.parent.mkdir(parents=True)
        binary.symlink_to("../../bin/python-real")
        (labels / "python").symlink_to("../project/runtime/package")
        self.configure_aliases({
            "python": "python3.14",
            "python3.14": str(labels / "python/bin/python3.14"),
        })
        self.f.context["aliases"].extend([
            {"root": "metadata", "path": "python", "target": "../project/runtime/package"},
            {"root": "project", "path": "runtime/package/bin/python3.14",
             "target": "../../bin/python-real"},
        ])
        self.f.write_context()
        selection = copy.deepcopy(self.f.selection)
        selection["roots"]["metadata"] = str(labels)
        selection["context"] = self.f.ref("evidence", "context.json")
        self.f.select(selection)
        self.f.bindings["context"] = selection["context"]
        return labels

    def test_ac3_four_hop_interpreter_and_directory_alias_chain_passes(self):
        self.configure_directory_aliases()
        self.assertEqual(self.f.problem(), "")
        result = self.f.record()
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(db.BindingError):
            db._Reader(self.f.selection["roots"]).path(
                "metadata", "python/bin/python3.14", "ordinary Ref still no-follow")

    def test_ac3_directory_alias_membership_and_literal_hops_remain_required(self):
        labels = self.configure_directory_aliases()
        self.assertEqual(self.f.problem(), "")
        original = copy.deepcopy(self.f.context["aliases"])
        for index in (1, 2, 3):
            self.f.context["aliases"] = [
                row for i, row in enumerate(original) if i != index]
            self.f.write_context()
            selection = copy.deepcopy(self.f.selection)
            selection["context"] = self.f.ref("evidence", "context.json")
            self.f.select(selection)
            self.f.bindings["context"] = selection["context"]
            self.assertIn("alias", self.f.problem())
        self.f.context["aliases"] = original
        self.f.write_context()
        selection["context"] = self.f.ref("evidence", "context.json")
        self.f.select(selection)
        self.f.bindings["context"] = selection["context"]
        for replacement in (str(self.f.project / "runtime/package"),
                            "../metadata/python", "../../foreign"):
            (labels / "python").unlink()
            (labels / "python").symlink_to(replacement)
            self.assertIn("alias", self.f.problem())
        (labels / "python").unlink()
        (labels / "python").symlink_to("../project/runtime/package")
        self.assertEqual(self.f.problem(), "")
        alias_root = self.f.base / "metadata-alias"
        alias_root.symlink_to(labels)
        bad_roots = {**selection["roots"], "metadata": str(alias_root)}
        with self.assertRaises(db.BindingError):
            db._Reader(bad_roots)

    def test_ac3_declared_directory_alias_cycle_escape_and_unknown_prefix_refuse(self):
        labels = self.configure_directory_aliases()
        original = copy.deepcopy(self.f.context["aliases"])
        for target in ("../metadata/python", "../../outside/python"):
            (labels / "python").unlink()
            (labels / "python").symlink_to(target)
            self.f.context["aliases"] = copy.deepcopy(original)
            self.f.context["aliases"][2]["target"] = target
            self.f.write_context()
            selection = copy.deepcopy(self.f.selection)
            selection["context"] = self.f.ref("evidence", "context.json")
            self.f.select(selection)
            self.f.bindings["context"] = selection["context"]
            self.assertIn("alias", self.f.problem())
        (labels / "python").unlink()
        (labels / "python").symlink_to("../project/runtime/package")
        (labels / "python-other").symlink_to("../project/runtime/package")
        version_alias = self.f.project / "runtime/bin/python3.14"
        version_alias.unlink()
        foreign = str(labels / "python-other/bin/python3.14")
        version_alias.symlink_to(foreign)
        self.f.context["aliases"] = copy.deepcopy(original)
        self.f.context["aliases"][1]["target"] = foreign
        self.f.write_context()
        selection["context"] = self.f.ref("evidence", "context.json")
        self.f.select(selection)
        self.f.bindings["context"] = selection["context"]
        self.assertIn("alias", self.f.problem())

    def configure_native_quality(self, static_weight=0, quality_weight=1,
                                 score=0.7, threshold=0.5):
        self.f.put("project", "oracle.sh", (
            'COMPONENTS=(\n'
            f'  "spec_oracle_static:{static_weight}"\n'
            f'  "quality:{quality_weight}"\n'
            '  # TEST ONLY native scalar quality; not visual approval.\n)\n'))
        self.f.context["files"]["pins"] = [
            self.f.ref("project", row["path"])
            if row["root"] == "project" and row["path"] == "oracle.sh" else row
            for row in self.f.context["files"]["pins"]]
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        self.f.make_run()

        def quality(doc):
            doc["components"][0]["weight"] = static_weight
            doc["components"].append({
                "component": "quality", "score": score, "weight": quality_weight,
                "exit_code": 0, "result": None})
            doc.update(composite=score, threshold=threshold,
                       threshold_override={"source": "environment", "value": str(threshold)})

        self.f.repin_record("overall", quality)
        self.f.sync_result_links()

    def test_ac2_declared_native_static_quality_composition_accepts_actual_numeric_policy(self):
        for static_weight, quality_weight, score, threshold in (
            (0, 2.5, 0.2, 0.1), (2, 0.5, 1.0, 0.5), (0, 0.1, 0, 0),
        ):
            with self.subTest(weights=(static_weight, quality_weight), score=score):
                self.configure_native_quality(static_weight, quality_weight, score, threshold)
                self.assertEqual(self.f.problem(), "")
                result = self.f.record()
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac2_native_quality_and_frozen_roster_cannot_override_required_or_overall(self):
        mutations = [
            lambda d: d["components"][1].update(exit_code=1),
            lambda d: d["components"][1].update(score=True),
            lambda d: d["components"][1].update(score=1.1),
            lambda d: d["components"][1].update(weight=-1),
            lambda d: d["components"][1].update(weight=2),
            lambda d: d["components"][1].update(result={"path": "foreign", "hash": "bad"}),
            lambda d: d["components"][1].update(component="unexpected"),
            lambda d: d["components"].append(dict(d["components"][1])),
            lambda d: d["components"].pop(),
            lambda d: d.update(status="fail", exit_code=1, reason="TEST ONLY quality cutoff"),
            lambda d: d.update(status="unknown", exit_code=2, reason="TEST ONLY unavailable"),
            lambda d: d["required"]["items"][0].update(status="unknown"),
        ]
        for mutate in mutations:
            self.configure_native_quality()
            self.f.repin_record("overall", mutate)
            self.f.sync_result_links()
            self.assertTrue(self.f.problem())
            self.assertEqual(self.f.record().returncode, 2)

    def test_ac2_native_roster_rejects_dynamic_duplicate_reassigned_and_augmented_forms(self):
        for change in (
            lambda s: s.replace('"quality:1"', '"quality:${WEIGHT}"'),
            lambda s: s.replace('"quality:1"', '"quality:$(weight)"'),
            lambda s: s.replace('"quality:1"', '"quality:1"\n  "quality:1"'),
            lambda s: s + '\nCOMPONENTS=("quality:1")\n',
            lambda s: s + '\ntrue; COMPONENTS+=("quality:1")\n',
            lambda s: s + '\nCOMPONENTS\\\n+=("quality:1")\n',
            lambda s: s + '\nCOMPON\\\nENTS=("quality:1")\n',
            lambda s: s + '\nCOMPONENTS+\\\n=("quality:1")\n',
            lambda s: s + '\nCOMPONENTS[0]="quality:1"\n',
            lambda s: s + '\nCOMPONENTS[$(\nprintf 1\n)]="quality:2"\n',
            lambda s: s.replace('"quality:1"', '"quality:1e999"'),
        ):
            self.configure_native_quality()
            path = self.f.project / "oracle.sh"
            path.write_text(change(path.read_text()))
            self.f.context["files"]["pins"] = [
                self.f.ref("project", row["path"])
                if row["root"] == "project" and row["path"] == "oracle.sh" else row
                for row in self.f.context["files"]["pins"]]
            self.f.write_context()
            self.f.select()
            self.f.bindings["context"] = self.f.selection["context"]
            self.assertIn("native", self.f.problem())
            self.assertEqual(self.f.record().returncode, 2)

    def test_ac4_foreign_owned_links_missing_run_nonce_and_unsafe_inventory_refuse(self):
        for role, change in (
            ("receipt", lambda d: d.pop("nonce")),
            ("claim", lambda d: d.pop("run_id")),
            ("invocation", lambda d: d.pop("run_id")),
            ("component", lambda d: d["evidence"][0]["result_artifact"].update(run_id="foreign")),
            ("overall", lambda d: d["components"][0]["result"].update(path="/foreign/result.json")),
            ("envelope", lambda d: d["artifacts"][0].update(path="../foreign")),
        ):
            with self.subTest(role=role):
                self.f.make_run()
                self.f.repin_record(role, change)
                result = self.f.record()
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_ac7_other_reviews_remain_independently_required(self):
        for name in ("compliance", "craft", "reconciliation"):
            record = self.f.spec_dir / f"reviews/slice-01-{name}.md"
            saved = record.read_bytes()
            record.unlink()
            stage = "RECONCILED" if name == "reconciliation" else "REVIEWED"
            result = self.f.cli("independent-review/review.py", "check-reviews",
                                self.f.spec, "999-01", "--stage", stage)
            self.assertEqual(result.returncode, 2)
            self.assertIn(name, result.stderr)
            record.write_bytes(saved)

    def test_ac1_namespaces_are_exact_and_never_boolean_or_scalar_fallback(self):
        self.assertEqual(self.f.problem(), "")
        for key, value in CONTRACTS.items():
            with self.subTest(namespace=key):
                self.f.context["contracts"][key] = True if type(value) is int else "design_evidence"
                self.f.write_context()
                self.f.select()
                self.f.bindings["context"] = self.f.selection["context"]
                self.assertIn("contracts", self.f.problem())
                self.f.context["contracts"][key] = value
        self.f.write_context()
        self.f.select()
        self.assertIn("bindings", db.freshness_problem(self.f.slice.read_text(), "plain PASS"))

    def test_ac1_finite_record_shapes_are_closed_not_just_name_allowlists(self):
        self.assertEqual(self.f.problem(), "")
        for role in ("overall", "component", "envelope", "invocation"):
            with self.subTest(role=role):
                self.f.make_run()
                self.f.repin_record(role, lambda d: d.update(unknown_record_field=True))
                self.f.sync_result_links()
                self.assertIn("keys", self.f.problem())
        with tempfile.TemporaryDirectory(prefix="jig-static-unknown-source-") as tmp:
            inconsistent = StaticFixture(Path(tmp), extra_input=True)
            self.assertIn("source input", inconsistent.problem())

    def test_ac2_native_fail_unknown_keep_authority_even_at_threshold_zero(self):
        for status, code, reason in (("fail", 1, "required contradiction"),
                                     ("env_error", 2, "required UNKNOWN")):
            self.f.make_run()
            self.f.repin_record("overall", lambda d, s=status, c=code, r=reason: d.update(
                status=s, exit_code=c, reason=r, composite=None if c == 2 else 1.0))
            self.assertIn(reason, self.f.problem())
            result = self.f.record()
            self.assertEqual(result.returncode, 2)
            self.assertIn(reason, result.stderr)

    def test_ac2_contradictory_closed_required_rows_and_foreign_runs_refuse(self):
        self.assertEqual(self.f.problem(), "")
        cases = [
            ("overall", lambda d: d.update(exit_code=True)),
            ("component", lambda d: d["required"]["items"].append(d["required"]["items"][0])),
            ("component", lambda d: d["required"]["ids"].pop()),
            ("overall", lambda d: d["required"]["items"][0].update(status="unknown")),
            ("component", lambda d: d["evidence"][0].update(check_id="foreign")),
            ("component", lambda d: d.update(run_id="foreign-run")),
            ("invocation", lambda d: d.update(schema_version=True)),
            ("envelope", lambda d: d["constraints"][0].update(tolerance="1")),
            ("envelope", lambda d: d["summary"].update(required_status="unknown")),
            ("envelope", lambda d: d.update(kind="design_evidence")),
        ]
        for role, change in cases:
            with self.subTest(role=role):
                self.f.make_run()
                self.f.repin_record(role, change)
                self.assertTrue(self.f.problem())

    def test_ac3_all_owned_bytes_runtime_and_closed_membership_restore(self):
        self.assertEqual(self.f.problem(), "")
        paths = [
            "source/input.json", "source/approval.json", "source/request.json",
            "originals/direction.html", "app-policy.json", "policy-review.json",
            "required-policy.json", "checks.json", "installed/native.py", "installed/grader.py",
            "installed/oracle.sh", "helpers/static_contract.py", "runtime/bin/python-real",
            "runtime/browser/Versions/1/browser", "candidate-selection.json",
        ]
        for name in paths:
            with self.subTest(path=name):
                path = self.f.project / name
                before = path.read_bytes()
                path.write_bytes(before + b" ")
                self.assertTrue(self.f.problem())
                path.write_bytes(before)
                self.assertEqual(self.f.problem(), "")
        for name in ("runtime/browser/extra", "runtime/browser/empty-directory"):
            path = self.f.project / name
            if name.endswith("directory"):
                path.mkdir()
                self.assertTrue(self.f.problem())
                path.rmdir()
            else:
                path.write_text("added")
                self.assertTrue(self.f.problem())
                path.unlink()
        alias = self.f.project / "runtime/bin/python"
        alias.unlink()
        alias.symlink_to("../elsewhere")
        self.assertTrue(self.f.problem())
        alias.unlink()
        alias.symlink_to("python-real")
        self.assertEqual(self.f.problem(), "")

    def test_ac3_partial_runtime_cannot_pin_only_outer_manifest(self):
        self.assertEqual(self.f.problem(), "")
        self.f.context["files"]["runtime_files"].pop()
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        self.assertIn("runtime", self.f.problem())

    def test_ac3_source_archive_and_current_original_identity_must_agree(self):
        self.assertEqual(self.f.problem(), "")
        with tempfile.TemporaryDirectory(prefix="jig-static-inconsistent-source-") as tmp:
            inconsistent = StaticFixture(Path(tmp), source_archive="inconsistent archive bytes")
            self.assertIn("source original archive", inconsistent.problem())

    def test_ac4_added_and_deleted_members_in_each_closed_tree_refuse_and_restore(self):
        self.assertEqual(self.f.problem(), "")
        for tree in (*self.f.context["trees"].values(), self.f.bindings["output"]):
            directory = self.f.root(tree["root"]) / tree["path"]
            addition = directory / "extra"
            addition.write_text("SYNTHETIC unexpected member")
            self.assertTrue(self.f.problem())
            addition.unlink()
            path = directory / tree["files"][0]["path"]
            before = path.read_bytes()
            path.unlink()
            self.assertTrue(self.f.problem())
            path.write_bytes(before)
            self.assertEqual(self.f.problem(), "")

    def test_ac3_runtime_manifest_keeps_native_path_component_order_not_string_order(self):
        self.assertEqual(self.f.problem(), "")
        rows = json.loads((self.f.project / "helpers/runtime-files.json").read_text())
        names = [r["path"] for r in rows]
        self.assertNotEqual(names, sorted(names))
        self.assertEqual([Path(n) for n in names], sorted(Path(n) for n in names))

    def test_ac3_repinned_unsorted_runtime_manifest_refuses(self):
        from _common.static_design_bindings import StaticReadback

        self.assertEqual(self.f.problem(), "")
        rows = json.loads((self.f.project / "helpers/runtime-files.json").read_text())
        self.f.put("project", "helpers/runtime-files.json", list(reversed(rows)))
        self.f.context["files"]["runtime_manifest"] = self.f.ref(
            "project", "helpers/runtime-files.json")
        self.f.context["trees"]["helpers"] = self.f.tree("project", "helpers")
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        checker = StaticReadback(self.f.selection, self.f.bindings)
        checker.load_context()
        policy = copy.deepcopy(self.f.policy)
        policy["runtime"]["manifest"] = self.f.raw("helpers/runtime-files.json")
        with self.assertRaisesRegex(db.BindingError, "unsorted manifest"):
            checker.runtime(policy)

    def test_ac4_missing_screenshot_cannot_clear_with_repinned_null_capture(self):
        self.assertEqual(self.f.problem(), "")
        out = self.f.policy["output_root"].replace("{run_id}", self.f.run)
        (self.f.project / out / "app.png").unlink()
        observation = json.loads((self.f.project / out / "observations.json").read_text())
        observation["capture_hash"] = None
        self.f.put("project", out + "/observations.json", observation)
        self.f.sync_result_links()
        self.assertIn("screenshot", self.f.problem())
        result = self.f.record()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("screenshot", result.stderr)

    def test_ac2_native_scalar_types_and_threshold_contradictions_refuse(self):
        self.assertEqual(self.f.problem(), "")
        for update in ({"composite": True}, {"threshold": True}, {"threshold": 2.0},
                       {"threshold_override": {"source": "environment", "value": "nan"}},
                       {"composite": None}, {"composite": 10 ** 1000}):
            self.f.make_run()
            self.f.repin_record("overall", lambda d, change=update: d.update(change))
            self.f.sync_result_links()
            self.assertTrue(self.f.problem(), update)

    def test_ac8_malformed_nested_static_data_refuses_without_traceback(self):
        self.assertEqual(self.f.problem(), "")
        policy = copy.deepcopy(self.f.policy)
        policy["residuals"] = [["not a string"]]
        policy_hash = identity("servo-static-app-policy-v1",
                               {k: v for k, v in policy.items() if k != "approval"})
        review = json.loads((self.f.project / "policy-review.json").read_text())
        review["policy_hash"] = policy_hash
        self.f.put("project", "policy-review.json", review)
        policy["approval"].update(
            policy_hash=policy_hash,
            review_record_hash=digest(self.f.project / "policy-review.json"))
        self.f.put("project", "app-policy.json", policy)
        self.f.context["files"]["app_policy"] = self.f.ref("project", "app-policy.json")
        self.f.context["files"]["policy_review"] = self.f.ref("project", "policy-review.json")
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        self.assertTrue(self.f.problem())
        result = self.f.record()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_ac3_declared_browser_escape_and_wrong_browser_hash_refuse(self):
        self.assertEqual(self.f.problem(), "")
        browser = self.f.project / "runtime/browser"
        (browser / "Current").unlink()
        (browser / "Current").symlink_to("../../../originals")
        members = copy.deepcopy(self.f.members)
        members[0]["target"] = "../../../originals"
        self.f.put("project", "helpers/browser-membership.json", members)
        self.f.context["files"]["browser_manifest"] = self.f.ref(
            "project", "helpers/browser-membership.json")
        self.f.context["trees"]["helpers"] = self.f.tree("project", "helpers")
        # Direct runtime check after valid independent context load isolates this
        # membership rule from policy/envelope hash tamper detection.
        from _common.static_design_bindings import StaticReadback
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        checker = StaticReadback(self.f.selection, self.f.bindings)
        checker.load_context()
        policy = copy.deepcopy(self.f.policy)
        policy["runtime"]["browser_membership"] = self.f.raw("helpers/browser-membership.json")
        with self.assertRaisesRegex(db.BindingError, "browser"):
            checker.runtime(policy)
        (browser / "Current").unlink()
        (browser / "Current").symlink_to("Versions/1")
        self.f.put("project", "helpers/browser-membership.json", self.f.members)
        policy["runtime"]["browser_membership"] = self.f.raw("helpers/browser-membership.json")
        self.f.context["files"]["browser_manifest"] = self.f.ref(
            "project", "helpers/browser-membership.json")
        self.f.context["trees"]["helpers"] = self.f.tree("project", "helpers")
        self.f.write_context()
        self.f.select()
        self.f.bindings["context"] = self.f.selection["context"]
        checker = StaticReadback(self.f.selection, self.f.bindings)
        checker.load_context()
        policy["runtime"]["browser_hash"] = "sha256:" + "e" * 64
        with self.assertRaisesRegex(db.BindingError, "browser"):
            checker.runtime(policy)

    def test_ac4_semantic_response_and_observation_tamper_with_all_links_repinned(self):
        self.assertEqual(self.f.problem(), "")
        obs_path = (self.f.policy["output_root"].replace("{run_id}", self.f.run)
                    + "/observations.json")
        mutations = [
            lambda d: d.update(run_id="foreign-run"),
            lambda d: d.update(acquisition_nonce="foreign-nonce"),
            lambda d: d.update(acquisition_error="not completed"),
            lambda d: d.update(capture_hash="sha256:" + "e" * 64),
            lambda d: d["settlement"].update(unstable_ids=["caption-text"]),
            lambda d: d["loaded_resources"].pop(),
            lambda d: d["loaded_resources"].append(d["loaded_resources"][0]),
        ]
        for index in (0, 1):
            mutations.extend([
                lambda d, i=index: d["loaded_resources"][i].update(status=True),
                lambda d, i=index: d["loaded_resources"][i].update(status=302),
                lambda d, i=index: d["loaded_resources"][i].update(content_type="text/plain"),
                lambda d, i=index: d["loaded_resources"][i].update(resource_type="image"),
                lambda d, i=index: d["loaded_resources"][i].update(hash="sha256:" + "e" * 64),
                lambda d, i=index: d["loaded_resources"][i].update(artifact="../outside"),
            ])
        for mutate in mutations:
            self.f.make_run()
            obs = json.loads((self.f.project / obs_path).read_text())
            mutate(obs)
            self.f.put("project", obs_path, obs)
            self.f.sync_result_links()
            self.assertTrue(self.f.problem())
        self.f.make_run()
        self.assertEqual(self.f.problem(), "")

    def test_ac2_closed_inventory_semantics_not_merely_component_digest(self):
        self.assertEqual(self.f.problem(), "")
        cases = [
            ("component", lambda d: d["required"]["items"].pop()),
            ("component", lambda d: d["required"]["items"][0].update(evidence_index=True)),
            ("component", lambda d: d["required"].update(status="unknown")),
            ("component", lambda d: d["required"]["counts"].update(fail=1)),
            ("component", lambda d: d["evidence"][0].update(status="unknown", exit_code=2)),
            ("component", lambda d: d["evidence"][0].update(check_id="extra")),
            ("overall", lambda d: d["required"]["items"][0].update(component="foreign")),
            ("overall", lambda d: d["required"]["ids"].append("extra")),
            ("envelope", lambda d: d["constraints"].pop()),
            ("envelope", lambda d: d["constraints"][0].update(tolerance="1")),
            ("envelope", lambda d: d["constraints"][0].update(status="unknown")),
            ("envelope", lambda d: d["source"].update(target_revision="e" * 64)),
            ("envelope", lambda d: d["runtime"].update(browser_version="foreign")),
        ]
        for role, change in cases:
            self.f.make_run()
            self.f.repin_record(role, change)
            self.f.sync_result_links()
            self.assertTrue(self.f.problem())
        self.f.make_run()
        self.assertEqual(self.f.problem(), "")

    def test_ac3_run_nonce_receipt_observations_and_output_links_refuse(self):
        self.assertEqual(self.f.problem(), "")
        for role, change in [
            ("receipt", lambda d: d.update(nonce="foreign")),
            ("claim", lambda d: d.update(policy_hash="sha256:" + "e" * 64)),
            ("accepted", lambda d: d.update(hash="sha256:" + "e" * 64)),
            ("envelope", lambda d: d.update(acquisition_nonce="foreign")),
        ]:
            self.f.make_run()
            self.f.repin_record(role, change)
            self.assertTrue(self.f.problem())

    def test_ac4_all_resources_inputs_outputs_delivery_record_reuse_done_restore(self):
        self.assertEqual(self.f.problem(), "")
        record = self.f.spec_dir / "reviews/slice-01-design-review.md"
        original_review = record.read_bytes()
        for name in ("candidate/panel.css", "candidate/preselection.json",
                     "build/output/panel.html", "delivery/panel.css",
                     self.f.policy["output_root"].replace("{run_id}", self.f.run)
                     + "/responses/panel.css.body"):
            path = self.f.project / name
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            self.assertEqual(self.f.record().returncode, 2)
            for stage in ("REVIEWED", "DONE"):
                self.f.select(status="IN_PROGRESS" if stage == "REVIEWED" else "RECONCILED")
                result = self.f.cli("spec-workflow/workflow.py", "transition",
                                    self.f.spec, "999-01", stage)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("design-freshness", result.stderr)
            self.assertEqual(record.read_bytes(), original_review)
            path.write_bytes(before)
            self.assertEqual(self.f.problem(), "")
        self.f.put("project", "docs/unrelated.md", "documentation-only change")
        self.assertEqual(self.f.problem(), "")

    def test_ac5_synthetic_lifecycle_positive_is_not_independent_real_attestation(self):
        self.assertEqual(self.f.problem(), "")
        for end in ("REVIEWED", "RECONCILED", "DONE"):
            # Unrelated ordinary prerequisites are synthetic, not real attestation.
            result = self.f.cli("spec-workflow/workflow.py", "transition",
                                self.f.spec, "999-01", end)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac7_unselected_scalar_behavior_unchanged(self):
        self.assertEqual(db.freshness_problem("ordinary slice", "ordinary review"), "")
        self.assertEqual(self.f.problem(), "")

    def test_ac6_no_arbitrary_source_commands_evaluator_browser_or_network(self):
        import subprocess
        real_run = subprocess.run

        def fixed_git_only(argv, **kwargs):
            self.assertEqual(argv, ["git", "--no-optional-locks", "-C",
                                   str(self.f.project / "originals"),
                                   "rev-parse", "--verify", "HEAD"])
            return real_run(argv, **kwargs)

        with mock.patch("subprocess.run", side_effect=fixed_git_only), \
                mock.patch("socket.socket", side_effect=AssertionError("network forbidden")):
            self.assertEqual(self.f.problem(), "")

    def test_ac7_prompt_and_guidance_name_finite_scope_and_independent_compliance(self):
        import importlib.util
        path = Path(__file__).resolve().parents[1] / "independent-review/review.py"
        spec = importlib.util.spec_from_file_location("static_review_prompt", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        prompt = module.build_design_review_prompt(self.f.spec, "999-01", [])
        for text in (prompt,):
            for required in ("jig/static-design-freshness/1", "static_source_contract_evidence",
                             "actual font faces", "arbitrary Jig", "compliance"):
                self.assertIn(required, text)

    def test_ac8_strict_roots_paths_json_limits_and_no_symlink_ref_relaxation(self):
        self.assertEqual(self.f.problem(), "")
        ref = self.f.context["files"]["runtime_files"][0]
        alias_ref = {**ref, "path": "runtime/bin/python"}
        with self.assertRaises(db.BindingError):
            db._Reader(self.f.selection["roots"]).ref(alias_ref, "ordinary Ref")
        for bad in ("../escape", "a//b", "a\\b", ".git/config", "/absolute"):
            with self.assertRaises(db.BindingError):
                db._relative(bad, "static path")
        for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e9999}'):
            with self.assertRaises(db.BindingError):
                db._json(text, "static JSON")
        with mock.patch.object(db, "MAX_JSON", 4):
            self.assertIn("oversized", self.f.problem())

    def test_ac3_owned_directory_field_can_name_exact_reviewed_narrow_root(self):
        from _common.static_design_bindings import StaticReadback
        reader = StaticReadback(self.f.selection, self.f.bindings)
        self.assertEqual(reader.directory(str(self.f.project), "owned directory"), self.f.project)
        with self.assertRaises(db.BindingError):
            reader.reader.producer_path(str(self.f.project), "ordinary producer Ref")


if __name__ == "__main__":
    unittest.main()
