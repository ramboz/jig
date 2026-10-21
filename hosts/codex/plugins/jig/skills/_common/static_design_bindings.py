"""Finite Vellum 0.2 / Servo static APP readback. No producer code is imported.

This checks identities and recorded conclusions, not CSS, source facts, scores,
host loader behavior or honest execution. Independent compliance still owns ACs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

from _common.design_bindings import (
    MAX_FILES,
    _hash,
    _list,
    _object,
    _Reader,
    _relative,
    _require,
    _string,
    _version,
)

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
DOCUMENTS = {
    "app_policy", "policy_review", "input", "approval", "request", "manifest",
    "checks", "required_policy", "build", "selection", "runtime_manifest", "browser_manifest",
}
TREES = {"source", "helpers", "candidate_inputs", "build_output", "delivery"}
RECORDS = {
    "overall", "oracle_result", "component", "invocation", "accepted", "claim",
    "receipt", "envelope",
}
RESULT_KEYS = {
    "overall": {
        "schema_version", "kind", "run_id", "status", "exit_code", "reason",
        "composite", "threshold", "threshold_override", "policy_hash", "required",
        "components", "missing",
    },
    "component": {
        "schema_version", "kind", "run_id", "component", "config_hash", "policy_hash",
        "evaluator_hash", "source_identity", "score", "required", "evidence",
    },
    "envelope": {
        "schema_version", "kind", "version", "run_id", "acquisition_nonce",
        "source", "policy", "evaluator", "runtime", "build", "current_delivery",
        "observations", "constraints", "summary", "measurement_diagnostic",
        "residuals", "artifacts",
    },
    "invocation": {"schema_version", "kind", "run_id"},
}
APP_NORMALIZERS = {
    "presence": "unique-scoped-visible-presence-app/1",
    "text": "text-content-exact-visible-app/1",
    "background-color": "rgba8-exact-v0", "color": "rgba8-exact-v0",
    "font-family": "css-computed-family-list/1", "font-size": "css-scalar-v0",
    "font-weight": "css-scalar-v0", "width": "dom-bounds-csspx-v0", "height": "dom-bounds-csspx-v0",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def identity(domain: str, value: Any) -> str:
    # Published serializations differ, not just their domain separators.
    if domain.startswith("vellum-"):
        def source_value(item: Any) -> None:
            if type(item) in (str, int, bool) or item is None:
                return
            if isinstance(item, list):
                for child in item:
                    source_value(child)
                return
            _require(isinstance(item, dict), "source JSON", "noninteger/unsupported value")
            for key, child in item.items():
                _require(isinstance(key, str) and key.isascii(), "source JSON", "non-ASCII key")
                source_value(child)
        source_value(value)
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        raw = domain.encode("ascii") + b"\0" + payload
    else:
        raw = domain.encode("ascii") + b"\n" + canonical(value)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def same(actual: Any, expected: Any, label: str) -> None:
    if isinstance(actual, Path):
        actual = str(actual)
    if isinstance(expected, Path):
        expected = str(expected)
    _require(canonical(actual) == canonical(expected), label, "inconsistent recorded binding")


def version(doc: dict, kind: str, number: int, label: str) -> None:
    _require(doc.get("kind") == kind and type(doc.get("schema_version")) is int
             and doc["schema_version"] == number, label, "unsupported record kind/version")


def number(value: Any, label: str) -> float:
    _require(type(value) in (int, float), label,
             "expected explicit finite number, not bool/null")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    _require(finite, label, "number outside finite native scalar range")
    return value


def browser_links(rows: list) -> None:
    """Resolve declared membership names lexically, never filesystem symlinks."""
    members = {r["path"]: r for r in rows}
    for row in rows:
        if row["kind"] != "symlink":
            continue
        pending = row["path"].split("/")
        resolved: list[str] = []
        expansions = 0
        while pending:
            part = pending.pop(0)
            if part in ("", "."):
                continue
            if part == "..":
                _require(bool(resolved), "browser symlink", "target escapes closed membership")
                resolved.pop()
                continue
            resolved.append(part)
            member = members.get("/".join(resolved))
            _require(member is not None, "browser symlink", "target outside declared membership")
            assert member is not None
            if member["kind"] == "symlink":
                expansions += 1
                _require(expansions <= 64, "browser symlink", "cyclic/oversized link chain")
                target = _string(member["target"], "browser symlink target")
                _require(not target.startswith("/") and "\\" not in target
                         and not any(ord(c) < 32 or ord(c) == 127 for c in target),
                         "browser symlink", "unsafe target")
                resolved.pop()
                pending = target.split("/") + pending
        _require(bool(resolved), "browser symlink", "target must be a declared member")


def entries(rows: Any, label: str, *, bare: bool = False) -> dict[str, str]:
    result = {}
    for row in _list(rows, label):
        row = _object(row, label, {"path", "hash"})
        name = _relative(row["path"], label)
        value = row["hash"]
        if bare:
            value = "sha256:" + _string(value, label)
        result[name] = _hash(value, label)
    names = [r["path"] for r in rows]
    _require(names == sorted(names) and len({n.casefold() for n in names}) == len(names),
             label, "duplicate, aliased or unsorted inventory")
    return result


def required(value: Any, ids: list[str], label: str, *, overall: bool = False) -> None:
    doc = _object(value, label, {
        "ids", "items", "counts", "passed", "failed", "unknown", "status",
    })
    same(doc["ids"], ids, label + " IDs")
    same({k: v for k, v in doc.items() if k not in {"ids", "items"}}, {
        "status": "pass", "counts": {"pass": len(ids), "fail": 0, "unknown": 0},
        "passed": ids, "failed": [], "unknown": [],
    }, label)
    rows = _list(doc["items"], label)
    _require(len(rows) == len(ids), label, "partial or duplicate required inventory")
    for i, (row, name) in enumerate(zip(rows, ids)):
        row = _object(row, label, {"id", "status", "reason", "evidence_index"}
                      | ({"component"} if overall else set()))
        _require(row["id"] == name and row["status"] == "pass"
                 and type(row["evidence_index"]) is int and row["evidence_index"] == i,
                 label, "missing, contradictory or foreign required row")
        _string(row["reason"], label + " producer reason")
        if overall:
            same(row["component"], "spec_oracle_static", label)


class StaticReadback:
    """One bounded selection; only explicitly owned link fields are resolved."""

    def __init__(self, selection: dict, bindings: dict):
        self.reader = _Reader(selection["roots"])
        self.bindings = bindings
        self.context = _object(self.reader.document(selection["context"], "context"),
                               "static context", {
                                   "schema", "contracts", "files", "trees", "browser", "aliases",
                               })
        same(self.context["schema"], SCHEMA, "static context")
        contracts = _object(self.context["contracts"], "contracts", set(CONTRACTS))
        _require(all(type(contracts[k]) is type(v) and contracts[k] == v
                     for k, v in CONTRACTS.items()), "contracts", "unsupported namespaced contract")
        self.refs = _object(self.context["files"], "static files",
                            DOCUMENTS | {"pre_result", "pins", "runtime_files"})
        self.pins: dict[Path, str] = {}
        self.docs: dict[str, Any] = {}
        self.trees: dict[str, dict[Path, str]] = {}
        self.directories: dict[str, Path] = {}

    def pin(self, ref: dict, label: str) -> Path:
        path = self.reader.ref(ref, label)
        if path in self.pins:
            same(self.pins[path], ref["hash"], label)
        self.pins[path] = ref["hash"]
        return path

    def link(self, row: Any, label: str) -> Path:
        row = _object(row, label, {"path", "hash"})
        text = _string(row["path"], label)
        path = Path(text)
        # Compare a fixed owned link with paths already traversed and rehashed in
        # THIS readback. No new filesystem authority or symlink traversal here.
        if path.is_absolute():
            _require(str(path) == text, label, "ambiguous producer path alias")
        else:
            path = self.reader.roots["project"] / _relative(text, label)
        _require(self.pins.get(path) == _hash(row["hash"], label), label,
                 "link not in independently pinned complete inventory")
        return path

    def directory(self, value: Any, label: str) -> Path:
        # Owned directory fields may name the reviewed root itself. This is
        # not a file Ref and does not relax the legacy producer-path grammar.
        for root in self.reader.roots.values():
            if value == str(root):
                return root
        path = self.reader.producer_path(value, label)
        _require(path.is_dir(), label, "expected selected directory")
        return path

    def load_context(self) -> None:
        for role in DOCUMENTS:
            self.pin(self.refs[role], role)
            self.docs[role] = self.reader.data(self.refs[role], role)
        for role in ("pre_result", "pins", "runtime_files"):
            paths = [self.pin(ref, role) for ref in _list(self.refs[role], role)]
            _require(len(paths) == len(set(paths)), role, "duplicate reference")
            if role == "runtime_files":
                self.runtime_files = {path: self.pins[path] for path in paths}
        trees = _object(self.context["trees"], "static trees", TREES)
        for role, tree in trees.items():
            checked = self.reader.tree(tree, role)
            self.trees[role] = checked
            self.directories[role] = self.reader.path(tree["root"], tree["path"], role)
            for path, value in checked.items():
                _require(path not in self.pins or self.pins[path] == value, role,
                         "conflicting inventory")
                self.pins[path] = value
        for role in DOCUMENTS - {"runtime_manifest", "browser_manifest"}:
            _object(self.docs[role], role)

    def tree_entries(self, role: str) -> dict[str, str]:
        return {p.relative_to(self.directories[role]).as_posix(): h
                for p, h in self.trees[role].items()}

    def source_policy(self) -> tuple[dict, list[str]]:
        policy = self.docs["app_policy"]
        _object(policy, "APP policy", {
            "schema_version", "kind", "version", "target", "producer", "source", "bindings",
            "normalizers", "constraints", "environment", "selection", "output_root", "runtime",
            "evaluator_files", "residuals", "approval",
        })
        version(policy, "static_source_contract_app_policy", 1, "APP policy")
        same(policy["version"], CONTRACTS["static_app_policy"], "APP policy namespace")
        same(policy["target"], str(self.reader.roots["project"]), "APP target")
        policy_hash = identity("servo-static-app-policy-v1",
                               {k: v for k, v in policy.items() if k != "approval"})
        approval = _object(policy["approval"], "APP approval", {
            "decision", "author", "reviewer", "policy_hash", "review_record_hash",
        })
        _string(approval["author"], "APP author")
        _string(approval["reviewer"], "APP reviewer")
        _require(approval["decision"] == "approved" and approval["author"] != approval["reviewer"],
                 "APP approval", "independent approval required")
        same(approval["policy_hash"], policy_hash, "APP policy domain")
        same(approval["review_record_hash"], self.refs["policy_review"]["hash"], "APP review hash")
        review = self.docs["policy_review"]
        for key, value in {"verdict": "pass", "policy_hash": policy_hash,
                           "author": approval["author"], "reviewer": approval["reviewer"]}.items():
            same(review.get(key), value, "APP independent review")
        source = _object(policy["source"], "source identity", {
            "root", "contract_version", "profile", "input_hash", "approval_hash",
            "target_revision", "request_hash",
        })
        same(self.directory(source["root"], "source root"),
             self.directories["source"], "source root")
        same(source["input_hash"], self.refs["input"]["hash"], "source input hash")
        same(source["approval_hash"], self.refs["approval"]["hash"], "source approval hash")
        for role, name in (("input", "input.json"), ("approval", "approval.json"),
                           ("request", "request.json"), ("manifest", "manifest.json")):
            same(self.reader.ref(self.refs[role], role), self.directories["source"] / name,
                 "source " + role)
        doc = _object(self.docs["input"], "source input", {
            "version", "profile", "kind", "core", "target_revision", "request", "artifacts",
        })
        core = _object(doc.get("core"), "source core")
        for part in (doc, core, self.docs["request"], self.docs["manifest"]):
            same(part.get("version"), CONTRACTS["vellum_input"], "source namespace")
            same(part.get("profile"), CONTRACTS["source_profile"], "source profile")
        same(source["contract_version"], CONTRACTS["vellum_input"], "source namespace")
        same(source["profile"], CONTRACTS["source_profile"], "source profile")
        same(doc.get("kind"), "approved", "source approval")
        same(core.get("manifest"), self.docs["manifest"], "source manifest")
        same(core.get("policy"), self.docs["manifest"].get("required"), "source policy")
        rows = _list(core.get("policy"), "source required")
        ids = [_string(_object(row, "source required").get("id"), "required ID") for row in rows]
        _require(ids == sorted(set(ids)), "source required", "duplicate or unsorted required IDs")
        same(core.get("inventory"), ids, "source inventory")
        target = identity("vellum-confirmed-target-core-v2", core)[7:]
        same(doc.get("target_revision"), target, "source target revision")
        same(source["target_revision"], target, "source target revision")
        request = {"version": CONTRACTS["vellum_input"], "profile": CONTRACTS["source_profile"],
                   "target_revision": target}
        for name, value in {
            "inventory": ids, "policy": core["policy"], "bindings": core.get("bindings"),
            "resources": core.get("resources"), "reference": core.get("reference"),
            "capture": core.get("capture"),
            "source": {"origin": core.get("origin"), "originals": core.get("originals")},
            "scope": self.docs["manifest"].get("view"),
            "coverage": self.docs["manifest"].get("coverage"), "manifest": self.docs["manifest"],
        }.items():
            request[name] = identity("vellum-confirmed-" + name + "-v2", value)[7:]
        same(doc.get("request"), request, "source request")
        same(self.docs["request"], request, "source request")
        request_hash = identity("vellum-confirmed-review-request-v2", request)[7:]
        same(source["request_hash"], request_hash, "source request domain")
        source_approval = self.docs["approval"]
        for key, value in {"version": CONTRACTS["vellum_input"], "request": request,
                           "request_hash": request_hash, "decision": "approve",
                           "independent": True}.items():
            same(source_approval.get(key), value, "source approval")
        _string(source_approval.get("reviewer"), "source independent reviewer")
        _string(source_approval.get("reason"), "source approval reason")
        same(entries(doc.get("artifacts"), "source artifacts", bare=True),
             {n: h for n, h in self.tree_entries("source").items() if n != "input.json"},
             "source complete artifacts")
        core_artifacts = entries(core.get("artifacts"), "source core artifacts", bare=True)
        for name, value in core_artifacts.items():
            same(self.tree_entries("source").get(name), value, "source core artifact")
        # The source API inspects current originals as well as its archived package.
        origin = self.directory(_object(core.get("origin"), "source origin").get("root"),
                                "source original root")
        for name, row in _object(core.get("originals"), "source originals").items():
            name = _relative(name, "source original")
            row = _object(row, "source original", {"path", "hash"})
            archive = _relative(row["path"], "source original archive")
            value = _hash("sha256:" + _string(row["hash"], "source original hash"),
                          "source original hash")
            same(self.tree_entries("source").get(archive), value, "source original archive")
            self.link({"path": str(origin / name), "hash": value},
                      "source current original")
        expected_constraints = []
        for row in rows:
            normalizer = APP_NORMALIZERS.get(row.get("property"))
            _require(normalizer is not None, "source policy", "unsupported static property")
            expected_constraints.append({**row, "app_normalizer": normalizer})
        same(policy["constraints"], expected_constraints, "APP/source constraints")
        same(policy["environment"], self.docs["manifest"].get("environment"), "APP environment")
        normalizers = _object(policy["normalizers"], "APP normalizers")
        same(normalizers.get("properties"), APP_NORMALIZERS, "APP property namespaces")
        same(normalizers.get("visibility"),
             "scoped-dom-text-ancestor-overflow-and-paint-intersection-app/3", "APP visibility")
        same(_object(normalizers.get("family"), "APP family").get("version"),
             "css-computed-family-list/1", "APP family namespace")
        residuals = [_string(r, "APP residual")
                     for r in _list(policy["residuals"], "APP residuals")]
        source_residuals = [
            _string(r, "source residual")
            for r in _list(self.docs["manifest"]["coverage"]["residuals"], "source residuals")]
        _require(set(source_residuals) <= set(residuals),
                 "APP residuals", "source residuals lost")
        helpers = self.directories["helpers"]
        same(self.directory(policy["producer"], "source helper root"), helpers / "producer",
             "source helper root")
        evaluator = {self.link(row, "APP evaluator"): row["hash"]
                     for row in _list(policy["evaluator_files"], "APP evaluator")}
        same({str(p): h for p, h in evaluator.items()},
             {str(p): h for p, h in self.trees["helpers"].items()}, "APP helper closure")
        _require(len(evaluator) == len(policy["evaluator_files"]), "APP evaluator", "duplicate pin")
        return policy, ids

    def runtime(self, policy: dict) -> None:
        runtime = _object(policy["runtime"], "runtime")
        same(self.link(runtime.get("manifest"), "runtime manifest"),
             self.reader.ref(self.refs["runtime_manifest"], "runtime manifest"), "runtime manifest")
        rows = _list(self.docs["runtime_manifest"], "runtime manifest")
        expected = {}
        names = []
        for row in rows:
            path = self.link(row, "runtime dependency")
            _require(path not in expected, "runtime", "duplicate manifest reference")
            expected[path] = row["hash"]
            names.append(path)
        _require(names == sorted(names), "runtime", "unsorted manifest")
        selected = self.runtime_files
        same({str(p): h for p, h in selected.items()},
             {str(p): h for p, h in expected.items()}, "runtime complete closure")
        for field in ("executable", "bash"):
            path = self.reader.producer_path(runtime.get(field), "runtime " + field)
            _require(path in selected, "runtime " + field, "missing canonical runtime pin")
        for raw in _object(runtime.get("module_origins"), "runtime module origins").values():
            _require(self.reader.producer_path(raw, "runtime module") in selected,
                     "runtime module", "origin outside runtime closure")
        for row in _list(runtime.get("native_resolutions"), "native resolutions", empty=True):
            row = _object(row, "native resolution", {"path", "resolved", "hash"})
            # Native loader labels are pinned provenance, NOT new traversal authority.
            _string(row["path"], "native loader label")
            path = self.link({"path": row["resolved"], "hash": row["hash"]}, "native runtime")
            _require(path in selected, "native runtime", "resolved file outside runtime closure")
        same(self.link(runtime.get("browser_membership"), "browser manifest"),
             self.reader.ref(self.refs["browser_manifest"], "browser manifest"), "browser manifest")
        browser = _object(self.context["browser"], "browser", {"root", "path"})
        root = self.reader.path(browser["root"], browser["path"], "browser root")
        same(str(root), runtime.get("browser_root"), "browser root")
        rows = _list(self.docs["browser_manifest"], "browser membership")
        actual = []
        pending = [(root, 0)]
        while pending:
            parent, depth = pending.pop()
            _require(depth <= 64, "browser", "membership depth exceeded")
            children = list(parent.iterdir())
            _require(len({p.name.casefold() for p in children}) == len(children),
                     "browser", "ambiguous case aliases")
            for path in children:
                _require(len(actual) < MAX_FILES, "browser", "membership limit exceeded")
                name = _relative(path.relative_to(root).as_posix(), "browser member")
                mode = path.lstat().st_mode
                row = {"path": name}
                if stat.S_ISLNK(mode):
                    row.update(kind="symlink", target=os.readlink(path))
                elif stat.S_ISDIR(mode):
                    row["kind"] = "directory"
                    pending.append((path, depth + 1))
                else:
                    _require(stat.S_ISREG(mode) and path in selected, "browser",
                             "nonregular or unpinned browser file")
                    row["kind"] = "file"
                actual.append(row)
        same(rows, sorted(actual, key=lambda r: r["path"]), "browser closed membership")
        browser_links(rows)
        _require(runtime.get("browser_hash") in {
            value for path, value in selected.items() if root in path.parents},
            "browser executable", "browser hash outside complete selected browser files")
        self.alias_paths = set()
        for row in _list(self.context["aliases"], "runtime aliases", empty=True):
            row = _object(row, "runtime alias", {"root", "path", "target"})
            name = _relative(row["path"], "runtime alias")
            parent, _, leaf = name.rpartition("/")
            _require(bool(parent), "runtime alias", "alias needs a narrow parent")
            directory = self.reader.path(row["root"], parent, "runtime alias parent")
            path = directory / leaf
            _require(path not in self.alias_paths, "runtime alias", "duplicate alias")
            _require([p.name for p in directory.iterdir() if p.name.casefold() == leaf.casefold()]
                     == [leaf], "runtime alias", "missing or ambiguous alias")
            _require(stat.S_ISLNK(path.lstat().st_mode), "runtime alias", "not a declared symlink")
            same(os.readlink(path), _string(row["target"], "runtime alias target"), "runtime alias")
            self.alias_paths.add(str(path))

    def grading(self, policy: dict, ids: list[str], component: dict) -> None:
        plan = self.docs["checks"]
        _require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1
                 and "kind" not in plan, "checks", "unsupported checks namespace/version")
        same(plan.get("approval_status"), "approved", "checks approval")
        same(plan.get("required_policy"), {"enabled": True, "schema_version": 1}, "checks policy")
        checks = _list(plan.get("checks"), "checks")
        same([_object(c, "check").get("id") for c in checks], ids, "checks inventory")
        for check in checks:
            _require(check.get("required") is True and check.get("family") == "command",
                     "checks", "all static checks must be required commands")
            same(check.get("refusal_exit_codes"), [2], "checks UNKNOWN refusal")
            same(check.get("result_artifact"), {
                "root": policy["output_root"], "manifest": "evidence.json",
                "kind": "static_source_contract_evidence", "schema_version": 1,
            }, "checks static artifact contract")
            command = _list(check.get("command"), "check command")
            _require(all(isinstance(s, str) and s for s in command),
                     "check command", "invalid argv")
            same(command[1:], ["-I", "-B", str(self.directories["helpers"] / "static_contract.py"),
                               "evaluate", "--policy",
                               str(self.reader.path(self.refs["app_policy"]["root"],
                                                    self.refs["app_policy"]["path"], "APP policy")),
                               "--constraint", check["id"]], "static command identity")
            _require(command[0] == policy["runtime"]["executable"]
                     or command[0] in self.alias_paths,
                     "command runtime", "unselected interpreter alias")
        content: dict[str, Any] = {"checks": [], "residual_judgment": []}
        for key in content:
            for row in _list(plan.get(key), "grading " + key, empty=key == "residual_judgment"):
                item = dict(_object(row, "grading row"))
                if "statement" in item:
                    item["statement"] = " ".join(_string(item["statement"], "statement").split())
                content[key].append(item)
            content[key].sort(key=lambda row: row.get("id", ""))
        content.update(required_policy=plan["required_policy"],
                       schema_version=1, kind="required_plan_content")
        grade = "sha256:" + hashlib.sha256(canonical(content)).hexdigest()
        same(plan.get("approved_content_hash"), grade, "effective grading hash")
        installed = self.docs["required_policy"]
        version(installed, "required_policy", 1, "installed required policy")
        components = _list(installed.get("components"), "installed components")
        _require(len(components) == 1, "installed policy", "only finite static component supported")
        binding = _object(components[0], "installed binding")
        version(binding, "approved_required_binding", 1, "installed binding")
        same(binding, plan.get("approved_required_binding"), "installed/frozen binding")
        for key, value in {"required_ids": ids, "component": "spec_oracle_static",
                           "enabled": True, "config_hash": grade}.items():
            same(binding.get(key), value, "installed " + key)
        same(self.link({"path": binding.get("checks_path"),
                        "hash": self.refs["checks"]["hash"]}, "installed checks"),
             self.reader.ref(self.refs["checks"], "checks"), "installed checks")
        same(binding.get("source_identity"), {
            "path": plan.get("source_spec_path"), "hash": plan.get("source_hash"),
        }, "grading source")
        self.link(binding.get("source_identity"), "grading source")
        self.link(binding.get("evaluator"), "grader")
        self.link(binding.get("required_runtime"), "component native runtime")
        for row in _list(binding.get("evaluator_artifacts"), "frozen evaluator artifacts"):
            self.link(row, "frozen evaluator artifact")
        same(binding["required_runtime"]["hash"], installed.get("runtime_hash"), "native runtime")
        self.link({"path": ".servo/required_runtime.py", "hash": installed.get("runtime_hash")},
                  "installed native runtime")
        # Driver internals are producer authority: pin the full installed bytes, not
        # a Jig reimplementation of the driver's extraction/normalization algorithm.
        driver = self.reader.roots["project"] / "oracle.sh"
        _require(driver in self.pins, "installed driver", "missing full oracle pin")
        for key, value in {
            "component": "spec_oracle_static", "config_hash": grade,
            "policy_hash": self.refs["required_policy"]["hash"],
            "evaluator_hash": binding["evaluator"]["hash"],
            "source_identity": binding["source_identity"],
        }.items():
            same(component.get(key), value, "component " + key)

    def current(self, policy: dict, envelope: dict) -> None:
        selection = _object(self.docs["selection"], "candidate selection", {"build", "delivery"})
        target = self.reader.roots["project"]
        same(policy["selection"], "candidate-selection.json", "selection location")
        same(self.reader.path(self.refs["selection"]["root"], self.refs["selection"]["path"],
                              "selection"), target / policy["selection"], "selection location")
        build_path = self.reader.path(
            self.refs["build"]["root"], self.refs["build"]["path"], "build")
        same(self.directory(selection["build"], "selected build"),
             build_path.parent, "selected build")
        same(build_path.name, "build.json", "build record")
        same(self.directory(selection["delivery"], "selected delivery"),
             self.directories["delivery"], "selected delivery")
        build = _object(self.docs["build"], "build", {
            "schema_version", "kind", "source", "inputs", "outputs", "configuration",
            "recipe", "input_hash", "output_hash",
        })
        version(build, "static_snapshot_build", 1, "build")
        same(self.directory(build["source"], "candidate inputs"),
             self.directories["candidate_inputs"],
             "candidate inputs")
        same(self.directories["build_output"], build_path.parent / "output", "build output")
        same(entries(build["inputs"], "build inputs"), self.tree_entries("candidate_inputs"),
             "candidate complete inputs")
        outputs = entries(build["outputs"], "build outputs")
        same(outputs, self.tree_entries("build_output"), "build complete outputs")
        same(outputs, self.tree_entries("delivery"), "delivery complete outputs")
        config_path = self.directories["candidate_inputs"] / "candidate.json"
        config_ref = next((r for r in self.context["trees"]["candidate_inputs"]["files"]
                           if r["path"] == "candidate.json"), None)
        _require(config_ref is not None, "candidate", "missing candidate configuration")
        tree = self.context["trees"]["candidate_inputs"]
        config = self.reader.document({
            "root": tree["root"], "path": tree["path"] + "/candidate.json",
            "hash": self.pins[config_path],
        }, "candidate configuration")
        _object(config, "candidate configuration",
                {"schema_version", "kind", "entry", "resources", "metadata"})
        version(config, "static_snapshot_candidate", 1, "candidate")
        same(config, build["configuration"], "candidate build configuration")
        resources = _list(config["resources"], "candidate resources")
        urls, paths = [], []
        for row in resources:
            row = _object(row, "candidate resource", {"url", "path", "content_type"})
            urls.append(_string(row["url"], "resource URL"))
            _require(re.fullmatch(r"/[A-Za-z0-9_./-]+", row["url"]) is not None,
                     "resource URL", "unsupported static URL")
            _relative(row["url"][1:], "resource URL")
            paths.append(_relative(row["path"], "resource path"))
            _require(row["content_type"] in {
                "text/html", "text/css", "text/javascript", "application/json",
                "text/html; charset=utf-8", "text/javascript; charset=utf-8",
                "application/json; charset=utf-8",
            }, "resource content type", "unsupported static content type")
        _require(urls == sorted(set(urls)) and len(set(paths)) == len(paths),
                 "candidate resources", "duplicate/unsorted resource inventory")
        _require(config["entry"] in urls, "candidate entry", "entry outside inventory")
        entry_mime = resources[urls.index(config["entry"])]["content_type"].split(";")[0]
        _require(entry_mime == "text/html",
                 "candidate entry", "entry must be HTML")
        metadata = _list(config["metadata"], "candidate metadata", empty=True)
        for name in metadata:
            _relative(name, "candidate metadata")
        _require(metadata == sorted(set(metadata)),
                 "candidate metadata", "duplicate/unsorted metadata")
        expected = sorted(["candidate.json", *paths, *metadata])
        _require(len(set(expected)) == len(expected), "candidate", "aliased input")
        same(sorted(self.tree_entries("candidate_inputs")), expected, "candidate input inventory")
        same(outputs, {n: self.tree_entries("candidate_inputs")[n] for n in sorted(paths)},
             "copy-only build")
        same(self.link(build["recipe"], "build recipe"),
             self.directories["helpers"] / "static_snapshot.py", "build recipe")
        same(build["input_hash"], identity("servo-static-snapshot-input-v1",
                                           {"files": build["inputs"], "recipe": build["recipe"]}),
             "build input domain")
        same(build["output_hash"], identity("servo-static-snapshot-output-v1", build["outputs"]),
             "build output domain")
        same(envelope.get("build"), build, "evaluated/current build")
        same(envelope.get("current_delivery"), {
            "path": str(self.directories["delivery"]), "output_hash": build["output_hash"],
            "selection_hash": self.refs["selection"]["hash"],
        }, "evaluated/current delivery")

    def results(self, policy: dict, ids: list[str], docs: dict, run: str) -> None:
        overall, component, envelope = (docs[k] for k in ("overall", "component", "envelope"))
        for role, keys in RESULT_KEYS.items():
            _object(docs[role], role, keys)
        for role, kind, schema_version in (
            ("oracle_result", "gate_result", 2), ("component", "required_component_result", 1),
            ("invocation", "gate_invocation", 1),
            ("envelope", "static_source_contract_evidence", 1),
        ):
            _version(docs[role], kind, schema_version, run, role)
        same(docs["oracle_result"], overall, "native oracle/overall")
        same(overall.get("policy_hash"), self.refs["required_policy"]["hash"], "overall policy")
        same(overall.get("missing"), [], "overall missing components")
        same(overall.get("reason"), None, "overall pass reason")
        components = _list(overall.get("components"), "overall components")
        _require(len(components) == 1, "overall components", "unsupported extra/missing component")
        row = _object(components[0], "overall component",
                      {"component", "exit_code", "result", "score", "weight"})
        same(row.get("component"), "spec_oracle_static", "overall component")
        same(row.get("exit_code"), 0, "overall component exit")
        composite = number(overall.get("composite"), "overall composite")
        threshold = number(overall.get("threshold"), "overall threshold")
        number(row.get("score"), "component diagnostic")
        number(component.get("score"), "component diagnostic")
        _require(number(row.get("weight"), "component weight") > 0,
                 "component weight", "nonpositive weight")
        _require(composite >= threshold, "overall", "PASS contradicts preserved threshold")
        override = _object(overall.get("threshold_override"), "threshold override",
                           {"source", "value"})
        _require(override["source"] in {"environment", "oracle_default"},
                 "threshold override", "unsupported provenance")
        value = _string(override["value"], "threshold override")
        _require(re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?",
                             value) is not None,
                 "threshold override", "not a finite numeric declaration")
        _require(number(float(value), "threshold override") == threshold,
                 "threshold override", "threshold identity mismatch")
        if override["source"] == "oracle_default":
            same(value, self.docs["checks"]["approved_required_binding"].get("threshold_default"),
                 "frozen threshold default")
        same(self.link(row.get("result"), "overall component link"),
             self.reader.ref(self.bindings["records"]["component"], "component"), "component link")
        same(row.get("score"), component.get("score"), "component diagnostic")
        required(overall.get("required"), ids, "overall required", overall=True)
        required(component.get("required"), ids, "component required")
        same(envelope.get("version"), CONTRACTS["static_app_policy"], "envelope namespace")
        same(envelope.get("source"), policy["source"], "envelope source")
        same(envelope.get("policy"),
             {"hash": policy["approval"]["policy_hash"], "required_ids": ids},
             "envelope policy")
        for key, expected in (("evaluator", policy["evaluator_files"]),
                              ("runtime", policy["runtime"]),
                              ("residuals", policy["residuals"])):
            same(envelope.get(key), expected, "envelope " + key)
        same(envelope.get("summary"), {
            "status": "pass", "required_status": "pass", "counts": {
                "pass": len(ids), "fail": 0, "unknown": 0},
            "passed": ids, "failed": [], "unknown": [],
        }, "envelope required summary")
        same(envelope.get("measurement_diagnostic"), {
            "passed": len(ids), "total": len(ids),
            "claim": "static-measurement-only-not-visual-quality",
        }, "envelope diagnostic scope")
        constraints = _list(envelope.get("constraints"), "envelope constraints")
        same([r.get("id") for r in constraints], ids, "envelope inventory")
        for row, expected in zip(constraints, policy["constraints"]):
            same({k: row.get(k) for k in expected}, expected, "envelope source constraint")
            _require(row.get("required") is True and row.get("status") == "pass",
                     "envelope", "nonpassing required constraint")
            _string(row.get("reason"), "envelope producer reason")
            same(row.get("observation"), {"path": "observations.json",
                                         "role": row["element"], "property": row["property"]},
                 "constraint observation")
        output = self.reader.tree(self.bindings["output"], "output")
        tree = self.bindings["output"]
        root = self.reader.path(tree["root"], tree["path"], "output")
        self.pins.update(output)
        same(self.reader.ref(self.bindings["records"]["envelope"], "envelope"),
             root / "evidence.json", "envelope output")
        template = _relative(policy["output_root"], "APP output root")
        _require(template.split("/").count("{run_id}") == 1,
                 "APP output root", "missing run segment")
        same(root, self.reader.roots["project"] / template.replace("{run_id}", run),
             "run output root")
        artifacts = entries(envelope.get("artifacts"), "output artifacts")
        same(artifacts, {p.relative_to(root).as_posix(): h for p, h in output.items()
                         if p != root / "evidence.json"}, "complete output artifacts")
        artifact = {
            "kind": "command_result_artifacts", "schema_version": 1, "run_id": run,
            "root": template.replace("{run_id}", run),
            "manifest": {"path": "evidence.json",
                         "hash": self.bindings["records"]["envelope"]["hash"]},
            "artifacts": envelope["artifacts"],
        }
        evidence = _list(component.get("evidence"), "component evidence")
        _require(len(evidence) == len(ids),
                 "component evidence", "partial/extra required inventory")
        for i, row in enumerate(evidence):
            version(row, "evidence", 1, "raw evidence")
            for key, expected in {
                "ac_id": ids[i], "check_id": ids[i], "family": "command",
                "status": "pass", "exit_code": 0,
                "command": self.docs["checks"]["checks"][i]["command"], "result_artifact": artifact,
            }.items():
                same(row.get(key), expected, "raw evidence " + key)
            same(row.get("message"), component["required"]["items"][i]["reason"], "required reason")
            same(row.get("message"), overall["required"]["items"][i]["reason"], "overall reason")
        same(docs["accepted"], {
            "path": str(self.reader.ref(self.bindings["records"]["overall"], "overall")),
            "hash": self.bindings["records"]["overall"]["hash"],
        }, "native consumer accepted")
        claim = _object(docs["claim"], "acquisition claim", {
            "run_id", "nonce", "policy_hash", "output_root",
        })
        nonce = _string(claim["nonce"], "acquisition nonce")
        same(claim, {"run_id": run, "nonce": nonce,
                     "policy_hash": policy["approval"]["policy_hash"],
                     "output_root": template.replace("{run_id}", run)}, "acquisition claim")
        same(envelope.get("acquisition_nonce"), nonce, "envelope nonce")
        same(docs["receipt"], {
            "run_id": run, "nonce": nonce,
            "envelope_hash": self.bindings["records"]["envelope"]["hash"],
        }, "acquisition receipt")
        claim_ref = {"root": tree["root"], "path": tree["path"] + "/claim.json",
                     "hash": self.pins.get(root / "claim.json")}
        same(self.reader.document(claim_ref, "output claim"), claim, "acquisition output claim")
        self.responses(policy, envelope, root, run, nonce)

    def responses(self, policy: dict, envelope: dict, root: Path, run: str, nonce: str) -> None:
        observation_path = self.link(
            {"path": str(root / "observations.json"),
             "hash": _object(envelope.get("observations"), "observation ref",
                             {"path", "hash"})["hash"]}, "observations")
        same(envelope["observations"]["path"], "observations.json", "observation path")
        tree = self.bindings["output"]
        obs = self.reader.document({
            "root": tree["root"], "path": tree["path"] + "/observations.json",
            "hash": self.pins[observation_path],
        }, "observations")
        _object(obs, "observations", {
            "run_id", "acquisition_nonce", "acquisition_error", "error", "environment",
            "capture_hash", "elements", "settlement", "loaded_resources",
        })
        for key, expected in {"run_id": run, "acquisition_nonce": nonce,
                               "acquisition_error": None, "error": None,
                               "environment": policy["environment"]}.items():
            same(obs[key], expected, "observation " + key)
        capture_hash = _hash(obs["capture_hash"], "observation screenshot")
        _require(any(row["path"] == "app.png" for row in self.bindings["output"]["files"]),
                 "observation screenshot", "missing required output witness")
        same(capture_hash, self.pins.get(root / "app.png"), "observation screenshot")
        settlement = _object(obs["settlement"], "settlement")
        same(settlement.get("error"), None, "settlement error")
        same(settlement.get("unstable_ids"), [], "settlement unstable IDs")
        rows = _list(obs["loaded_resources"], "served responses")
        resources = self.docs["build"]["configuration"]["resources"]
        _require(len(rows) == len(resources),
                 "served responses", "partial/extra response inventory")
        seen = set()
        for row, resource in zip(rows, resources):
            row = _object(row, "served response", {
                "url", "path", "content_type", "resource_type", "status", "hash", "artifact",
            })
            same({k: row[k] for k in resource}, resource, "served resource declaration")
            same(row["status"], 200, "served completed status")
            mime = resource["content_type"].split(";")[0]
            allowed = {"text/html": {"document"}, "text/css": {"stylesheet"},
                       "text/javascript": {"script"}, "application/json": {"fetch", "xhr"}}
            _require(row["resource_type"] in allowed[mime],
                     "served response", "wrong resource type")
            same(row["hash"], self.trees["delivery"].get(
                self.directories["delivery"] / resource["path"]), "served delivery body")
            name = _relative(row["artifact"], "served body artifact")
            _require(name not in seen, "served responses", "duplicate response body")
            seen.add(name)
            same(self.pins.get(root / name), row["hash"], "served retained response body")


def validate(selection: dict, bindings: dict) -> None:
    _object(selection, "selection", {"schema", "roots", "context"})
    _object(bindings, "bindings", {"schema", "context", "run_id", "records", "output"})
    same(selection["schema"], SCHEMA, "static selection")
    same(bindings["schema"], SCHEMA, "static bindings")
    same(bindings["context"], selection["context"], "independent context")
    run = _string(bindings["run_id"], "run_id")
    _require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", run) is not None,
             "run_id", "expected canonical UUID")
    _require(str(uuid.UUID(run)) == run, "run_id", "expected canonical UUID")
    readback = StaticReadback(selection, bindings)
    records = _object(bindings["records"], "records", RECORDS)
    # Native nonpass authority precedes current-candidate comparisons, so a genuine
    # historical FAIL/UNKNOWN retains its reason even after candidate restoration.
    overall = readback.reader.document(records["overall"], "overall")
    _version(overall, "gate_result", 2, run, "overall")
    if overall.get("status") != "pass" or type(overall.get("exit_code")) is not int \
            or overall["exit_code"] != 0:
        reason = overall.get("reason")
        required_result = overall.get("required")
        rows = required_result.get("items", []) if isinstance(required_result, dict) else []
        rows = rows if isinstance(rows, list) else []
        reasons = [f"{r.get('id')}: {r.get('status')} ({r.get('reason')})"
                   for r in rows if isinstance(r, dict) and r.get("status") != "pass"]
        _require(False, "overall native verdict",
                 f"{overall.get('status')} / exit {overall.get('exit_code')}; "
                 + str(reason or "; ".join(reasons) or "nonpassing or unsupported verdict")[:2000])
    readback.load_context()
    docs = {}
    for role, ref in records.items():
        readback.pin(ref, role)
        docs[role] = readback.reader.document(ref, role)
    same(docs["overall"], overall, "overall stable read")
    policy, ids = readback.source_policy()
    readback.runtime(policy)
    readback.grading(policy, ids, docs["component"])
    readback.current(policy, docs["envelope"])
    readback.results(policy, ids, docs, run)
