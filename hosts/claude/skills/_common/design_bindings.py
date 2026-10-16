"""Finite, trusted-local design attestation bindings; reads/hashes only."""

from __future__ import annotations

import hashlib
import json
import math
import re
import stat
import unicodedata
from pathlib import Path
from typing import Any

SCHEMA = "jig/design-freshness/1"
CONTRACTS = {
    "vellum_input": "vellum-design-input/0.1-pilot",
    "gate_result": 2,
    "required_component_result": 1,
    "command_result_artifacts": 1,
    "design_evidence": 1,
    "design_eval_config": 2,
}
FILE_ROLES = {
    "pre_result", "source_approval", "approved_target", "c0", "frozen_policy",
    "frozen_config", "installed_policy", "installed_config", "installed_gate",
    "checks", "full_oracle", "runtime_files",
}
TREE_ROLES = {"runtime", "candidate_inputs", "build_output", "delivery"}
MAX_JSON = 32 * 1024 * 1024
MAX_FILES = 100_000
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")
_PRIVATE = {".ssh", ".aws", ".gnupg", ".git", ".azure", ".kube"}


class BindingError(ValueError):
    """A named comparison cannot be established."""


def _require(ok: bool, label: str, reason: str) -> None:
    if not ok:
        raise BindingError(f"{label}: {reason}")


def _object(value: Any, label: str, keys: set[str] | None = None) -> dict:
    _require(isinstance(value, dict), label, "expected object")
    if keys is not None:
        missing = keys - value.keys()
        extra = value.keys() - keys
        _require(not missing and not extra, label,
                 f"keys mismatch (missing {', '.join(sorted(missing)) or 'none'}; "
                 f"unknown {', '.join(sorted(extra)) or 'none'})")
    return value


def _list(value: Any, label: str, *, empty: bool = False) -> list:
    _require(isinstance(value, list), label, "expected list")
    _require((empty or bool(value)) and len(value) <= MAX_FILES, label,
             "missing or oversized inventory")
    return value


def _string(value: Any, label: str) -> str:
    _require(isinstance(value, str) and bool(value), label, "expected nonempty string")
    return value


def _pairs(pairs: list) -> dict:
    result: dict = {}
    for key, value in pairs:
        _require(key not in result, "JSON", "duplicate key")
        result[key] = value
    return result


def _constant(_value: str) -> Any:
    raise BindingError("JSON: nonfinite number")


def _float(value: str) -> float:
    number = float(value)
    _require(math.isfinite(number), "JSON", "nonfinite number")
    return number


def _json(text: str, label: str) -> dict:
    _require(len(text.encode("utf-8")) <= MAX_JSON, label, "oversized JSON")
    try:
        value = json.loads(text, object_pairs_hook=_pairs,
                           parse_constant=_constant, parse_float=_float)
    except (ValueError, RecursionError) as exc:
        raise BindingError(f"{label}: malformed, duplicate or nonfinite JSON") from exc
    return _object(value, label)


def _block(text: str, name: str) -> dict | None:
    tag = f"jig-design-{name}"
    starts = re.findall(rf"(?m)^[ \t]*`{{3,}}{tag}\b[^\n]*", text)
    if not starts:
        return None
    _require(len(starts) == 1, name, "duplicate fenced block")
    found = re.search(rf"(?m)^```{tag}\n(.*?)\n```[ \t]*$", text, re.DOTALL)
    _require(found is not None and starts == [f"```{tag}"], name,
             "malformed fenced block")
    assert found is not None
    return _json(found.group(1), name)


def _relative(value: Any, label: str) -> str:
    text = _string(value, label)
    parts = text.split("/")
    _require(not text.startswith("/") and len(parts) <= 64
             and all(p not in {"", ".", ".."} for p in parts)
             and not any(p.casefold() in _PRIVATE for p in parts)
             and not any(c in text for c in ("\\", ":"))
             and not any(ord(c) < 32 or ord(c) == 127 for c in text)
             and unicodedata.normalize("NFC", text) == text,
             label, "unsafe or ambiguous relative path")
    return text


def _hash(value: Any, label: str) -> str:
    text = _string(value, label)
    _require(_HASH.fullmatch(text) is not None, label, "expected raw sha256 hash")
    return text


class _Reader:
    def __init__(self, value: Any):
        roots = _object(value, "selection roots")
        _require("project" in roots and 1 <= len(roots) <= 64,
                 "selection roots", "explicit project root required (at most 64 roots)")
        _require(all(isinstance(raw, str)
                     and not any(ord(c) < 32 or ord(c) == 127 for c in raw)
                     for raw in roots.values()),
                 "selection root", "expected root strings without control characters")
        self.roots: dict[str, Path] = {}
        self.count = 0
        for name, raw in roots.items():
            _require(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name) is not None,
                     "selection roots", "invalid root name")
            text = _string(raw, "selection root")
            root = Path(text)
            home = Path.home().resolve()
            try:
                canonical = root.resolve()
            except (OSError, RuntimeError) as exc:
                raise BindingError("selection root: inaccessible or symlink loop") from exc
            _require(root.is_absolute() and str(root) == text
                     and canonical == root and len(root.parts) >= 4
                     and root != home and root not in home.parents
                     and not any(p.casefold() in _PRIVATE for p in root.parts)
                     and root.parts[1] not in {
                         "etc", "dev", "proc", "sys", "System", "Library",
                         "usr", "bin", "sbin", "Applications",
                     } and not str(root).startswith("/private/etc"),
                     "selection root", "unsafe broad, private or aliased root")
            _require(root.is_dir(), "selection root", "inaccessible directory")
            for other in self.roots.values():
                a, b = str(root).casefold(), str(other).casefold()
                _require(a != b and not a.startswith(b + "/") and not b.startswith(a + "/"),
                         "selection roots", "overlapping or aliased roots")
            self.roots[name] = root

    def path(self, root_id: Any, relative: Any, label: str) -> Path:
        _require(isinstance(root_id, str) and root_id in self.roots, label,
                 "unknown reviewed root")
        name = _relative(relative, label)
        current = self.roots[root_id]
        for part in name.split("/"):
            try:
                aliases = [p.name for p in current.iterdir()
                           if p.name.casefold() == part.casefold()]
            except OSError as exc:
                raise BindingError(f"{label}: inaccessible comparison path") from exc
            _require(aliases == [part], label, "missing file or ambiguous case alias")
            current = current / part
            _require(not current.is_symlink(), label, "symlink reference refused")
        return current

    def ref(self, value: Any, label: str) -> Path:
        ref = _object(value, label, {"root", "path", "hash"})
        expected = _hash(ref["hash"], label)
        path = self.path(ref["root"], ref["path"], label)
        self.count += 1
        _require(self.count <= MAX_FILES, label, "comparison limit exceeded")
        try:
            _require(stat.S_ISREG(path.stat().st_mode), label, "not a regular file")
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
        except OSError as exc:
            raise BindingError(f"{label}: inaccessible comparison bytes") from exc
        _require("sha256:" + hasher.hexdigest() == expected, label,
                 "raw hash mismatch; changed binding")
        return path

    def document(self, value: Any, label: str) -> dict:
        path = self.ref(value, label)
        try:
            _require(path.stat().st_size <= MAX_JSON, label, "oversized JSON")
            return _json(path.read_text(encoding="utf-8"), label)
        except (OSError, UnicodeError) as exc:
            raise BindingError(f"{label}: inaccessible or non-UTF-8 JSON") from exc

    def tree(self, value: Any, label: str) -> dict[Path, str]:
        tree = _object(value, label, {"root", "path", "files"})
        directory = self.path(tree["root"], tree["path"], label)
        _require(directory.is_dir(), label, "missing closed directory")
        rows = _list(tree["files"], label)
        expected: dict[Path, str] = {}
        names: list[str] = []
        for row in rows:
            row = _object(row, label, {"path", "hash"})
            name = _relative(row["path"], label)
            names.append(name)
            path = self.ref({
                "root": tree["root"], "path": tree["path"] + "/" + name,
                "hash": row["hash"],
            }, label)
            expected[path] = row["hash"]
        _require(names == sorted(names) and len({n.casefold() for n in names}) == len(names),
                 label, "duplicate, aliased or unsorted inventory")
        actual: set[Path] = set()
        pending = [(directory, 0)]
        entries = 0
        while pending:
            parent, depth = pending.pop()
            _require(depth <= 64, label, "directory depth limit exceeded")
            children = list(parent.iterdir())
            _require(len({p.name.casefold() for p in children}) == len(children),
                     label, "ambiguous case aliases in directory")
            for child in children:
                entries += 1
                _require(entries <= MAX_FILES, label, "directory inventory limit exceeded")
                mode = child.lstat().st_mode
                _require(not stat.S_ISLNK(mode), label, "symlink in closed inventory")
                if stat.S_ISDIR(mode):
                    pending.append((child, depth + 1))
                else:
                    _require(stat.S_ISREG(mode), label, "nonregular file in inventory")
                    actual.add(child)
        _require(actual == set(expected), label, "partial closed inventory; added/missing files")
        return expected

    def producer_path(self, raw: Any, label: str) -> Path:
        """Resolve only the fixed producer link fields, never arbitrary JSON."""
        text = _string(raw, label)
        path = Path(text)
        _require(str(path) == text, label, "ambiguous producer path alias")
        if not path.is_absolute():
            return self.path("project", text, label)
        for root_id, root in self.roots.items():
            if root in path.parents:
                return self.path(root_id, path.relative_to(root).as_posix(), label)
        raise BindingError(f"{label}: link outside reviewed roots")


def _version(value: dict, kind: str, version: int, run: str, label: str) -> None:
    _require(value.get("kind") == kind
             and type(value.get("schema_version")) is int
             and value["schema_version"] == version,
             label, "unsupported record kind/version")
    _require(value.get("run_id") == run, label, "missing or foreign run_id")


def _validate(selection: dict, bindings: dict) -> None:
    selection = _object(selection, "selection", {"schema", "roots", "context"})
    bindings = _object(bindings, "bindings", {
        "schema", "context", "run_id", "records", "result_artifact", "output", "served",
    })
    _require(selection["schema"] == SCHEMA and bindings["schema"] == SCHEMA,
             "bindings/selection", "unsupported freshness contract")
    _require(bindings["context"] == selection["context"], "context",
             "comparison context differs from independent selection")
    reader = _Reader(selection["roots"])
    context = reader.document(selection["context"], "context")
    context = _object(context, "context", {"schema", "contracts", "files", "trees"})
    _require(context["schema"] == SCHEMA, "context", "unsupported freshness contract")
    contracts = _object(context["contracts"], "contracts", set(CONTRACTS))
    _require(all(type(contracts[k]) is type(v) and contracts[k] == v
                 for k, v in CONTRACTS.items()), "contracts", "unsupported namespaced contract")
    files = _object(context["files"], "context files", FILE_ROLES)
    for role, refs in files.items():
        seen: set[Path] = set()
        for ref in _list(refs, role, empty=role == "runtime_files"):
            path = reader.ref(ref, role)
            _require(path not in seen, role, "duplicate reference")
            seen.add(path)
    trees = _object(context["trees"], "context trees", TREE_ROLES)
    tree_sets: dict[str, dict[Path, str]] = {}
    for role, inventories in trees.items():
        combined: dict[Path, str] = {}
        for inventory in _list(inventories, role, empty=role == "runtime"):
            checked = reader.tree(inventory, role)
            _require(not combined.keys() & checked.keys(), role, "duplicate inventory")
            combined.update(checked)
        tree_sets[role] = combined
    _require(bool(files["runtime_files"] or tree_sets["runtime"]), "runtime",
             "missing complete runtime closure")
    run = _string(bindings["run_id"], "run_id")
    records = _object(bindings["records"], "records",
                      {"overall", "component", "envelope", "acquisition"})
    documents = {role: reader.document(ref, role) for role, ref in records.items()}
    for role, kind, version in (
        ("overall", "gate_result", 2), ("component", "required_component_result", 1),
        ("envelope", "design_evidence", 1),
    ):
        _version(documents[role], kind, version, run, role)
    acquisition = _object(documents["acquisition"], "acquisition",
                          {"run_id", "envelope_hash", "nonce"})
    _require(acquisition["run_id"] == run, "acquisition",
             "missing or foreign run_id")
    _require(acquisition["envelope_hash"] == records["envelope"]["hash"],
             "acquisition", "envelope digest mismatch")
    _require(_string(acquisition["nonce"], "acquisition nonce")
             == documents["envelope"].get("acquisition_nonce"),
             "acquisition", "envelope acquisition nonce mismatch")
    overall = documents["overall"]
    _require(overall.get("status") == "pass", "overall", "preserved verdict is not pass")
    component_path = reader.ref(records["component"], "component")
    links = []
    for component in _list(overall.get("components"), "overall components"):
        component = _object(component, "overall component")
        _require("result" in component, "overall component", "missing result link")
        if component["result"] is None:
            continue  # The producer's scalar-quality component has no result file.
        result = _object(component["result"], "overall component result", {"path", "hash"})
        # Other producer components are raw-pinned in the overall record, not followed.
        if result["hash"] == records["component"]["hash"]:
            links.append(reader.producer_path(result["path"], "component link"))
    _require(links == [component_path], "component", "missing/duplicate overall run/digest link")
    artifact = _object(bindings["result_artifact"], "result_artifact", {
        "kind", "schema_version", "run_id", "root", "manifest", "artifacts",
    })
    _version(artifact, "command_result_artifacts", 1, run, "result_artifact")
    for raw in _list(documents["component"].get("evidence"), "component evidence"):
        raw = _object(raw, "component raw result")
        _require(raw.get("result_artifact") == artifact, "component result_artifact",
                 "missing, partial or inconsistent raw result link")
    output = reader.tree(bindings["output"], "output")
    output_root = reader.path(bindings["output"]["root"], bindings["output"]["path"], "output")
    _require(reader.producer_path(artifact["root"], "result_artifact root") == output_root,
             "result_artifact", "output root mismatch")
    manifest = _object(artifact["manifest"], "result_artifact manifest", {"path", "hash"})
    manifest_name = _relative(manifest["path"], "result_artifact manifest")
    envelope_path = reader.ref(records["envelope"], "envelope")
    _require(output_root / manifest_name == envelope_path
             and manifest["hash"] == records["envelope"]["hash"],
             "result_artifact", "envelope manifest mismatch")
    rows = _list(artifact["artifacts"], "result_artifact artifacts")
    expected = {p.relative_to(output_root).as_posix(): h for p, h in output.items()}
    declared: dict[str, str] = {manifest_name: _hash(manifest["hash"], "manifest")}
    names = []
    for row in rows:
        row = _object(row, "result_artifact artifact", {"path", "hash"})
        name = _relative(row["path"], "result_artifact artifact")
        _require(name not in declared, "result_artifact", "duplicate artifact")
        names.append(name)
        declared[name] = _hash(row["hash"], "result_artifact")
    _require(names == sorted(names) and declared == expected, "result_artifact",
             "partial or inconsistent complete output inventory")
    seen_captures: set[Path] = set()
    for link in _list(bindings["served"], "served"):
        link = _object(link, "served", {"capture", "delivery", "resource_path"})
        capture = reader.ref(link["capture"], "served capture")
        delivery = reader.ref(link["delivery"], "served delivery")
        _require(capture in output and delivery in tree_sets["delivery"],
                 "served", "observation/delivery outside complete selected inventories")
        _require(capture not in seen_captures, "served", "duplicate capture link")
        seen_captures.add(capture)
        observation = _object(reader.document(link["capture"], "served observation"),
                              "served observation", {
                                  "acquisition_error", "acquisition_nonce", "capture_hash",
                                  "capture_id", "driver", "elements", "facts", "loaded_resources",
                                  "root", "run_id", "state", "state_error", "viewport",
                              })
        _require(observation["run_id"] == run, "served observation",
                 "missing or foreign run_id")
        resource_path = _relative(link["resource_path"], "served resource_path")
        selected: list[dict] = []
        seen_resources: set[str] = set()
        for row in _list(observation["loaded_resources"], "served loaded_resources"):
            row = _object(row, "served loaded resource",
                          {"path", "hash", "resource_type", "status"})
            name = _relative(row["path"], "served loaded resource")
            _hash(row["hash"], "served response")
            _require(name.casefold() not in seen_resources, "served loaded_resources",
                     "duplicate or aliased resource path")
            seen_resources.add(name.casefold())
            if name == resource_path:
                selected.append(row)
        _require(len(selected) == 1, "served", "missing exact response resource")
        response = selected[0]
        _require(response["resource_type"] == "document"
                 and type(response["status"]) is int and response["status"] == 200,
                 "served", "unsupported response resource_type/status")
        _require(response["hash"] == tree_sets["delivery"][delivery], "served",
                 "declared response hash differs from independently selected delivery bytes")


def freshness_problem(slice_text: str, review_body: str) -> str:
    """Empty iff unselected historical evidence or all selected bindings match."""
    try:
        selection = _block(slice_text, "selection")
        bindings = _block(review_body, "bindings")
        if selection is None and bindings is None:
            return ""
        _require(selection is not None, "selection", "missing explicit rich comparison context")
        _require(bindings is not None, "bindings", "missing complete attested comparisons")
        assert selection is not None and bindings is not None
        _validate(selection, bindings)
    except (BindingError, OSError, UnicodeError, RecursionError) as exc:
        # Filesystem errors can contain paths; never echo their contents or credentials.
        reason = str(exc) if isinstance(exc, BindingError) else "inaccessible comparison bytes"
        return (f"design-freshness: {reason}; obtain fresh producer evidence "
                "and independent attestation")
    return ""
