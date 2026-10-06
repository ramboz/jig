# Worked example: behavioral rules and runtime evidence

An illustrative progress-report slice, not an amendment to a closed spec.
Its ACs are **AC-1:** report one done slice out of two known slices, and
**AC-2:** preserve all fixture files without creating new files.

## Behavioral rules

| Rule | Operation/control | Actor | State/precondition | Outcome | Rationale | AC |
|------|-------------------|-------|--------------------|---------|-----------|----|
| BR-1 | Report progress | Developer | UC-1 cites a spec with DONE and DRAFT slices | Report 1/2 slices done | Count known work without hiding unfinished slices | AC-1 |
| BR-2 | Read project state | Developer | Run progress on the fixture | Leave fixture files unchanged | Progress is advisory, not a mutation | AC-2 |

IDs are trace links, not precedence. A conflicting reference must be resolved
against the owning ACs; this scenario is not a second requirements source.

## Verification scenario

**Preconditions:** Python 3, the Git executable (a Git checkout is optional),
and a jig payload with `workflow.py`; no network, Git security overrides,
accounts, or production data. The script creates and
removes only its own temporary fixture. Set `JIG_ROOT` to the installed jig
payload (or this source repository), not the consuming project's root.

**Invocation:** Run the following from any directory. It emits JSON containing
actual observations and outcomes, and exits nonzero on a failed observation.
Save that output as the scenario evidence; don't tick steps merely for writing
the script.

```bash
python3 - "$JIG_ROOT" <<'PY'
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

jig = Path(sys.argv[1]).resolve()
helper = jig / "skills/spec-workflow/workflow.py"
if not helper.is_file():
    print(json.dumps({"outcome": "environment-error", "reason": "workflow.py missing"}))
    raise SystemExit(2)

revision = subprocess.run(
    ["git", "-C", str(jig), "rev-parse", "HEAD"],
    capture_output=True, text=True,
)
code_revision = revision.stdout.strip() if revision.returncode == 0 else "installed payload"
runtime_files = [helper] + sorted(
    path for path in (jig / "skills/_common").rglob("*.py")
    if not path.name.startswith("test_")
)
runtime_manifest = {
    str(path.relative_to(jig)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in runtime_files
}
runtime_identity = "runtime-sha256:" + hashlib.sha256(
    json.dumps(runtime_manifest, sort_keys=True).encode("utf-8")
).hexdigest()

with tempfile.TemporaryDirectory(prefix="jig-behavioral-example-") as directory:
    project = Path(directory)
    files = {
        "scaffold.json": '{"project_name": "scenario-fixture"}\n',
        "docs/product-vision.md": "# Vision\n\n## Use cases\n\n- UC-1: A developer can inspect progress\n",
        "docs/specs/001-example/spec.md": "---\nstatus: DRAFT\nuse_cases: [UC-1]\n---\n\n# Example\n",
    }
    for number, status in ((1, "DONE"), (2, "DRAFT")):
        files[f"docs/specs/001-example/slice-{number:02d}-example.md"] = (
            f"---\nstatus: {status}\ndependencies: []\n---\n\n"
            f"## Slice 001-{number:02d} -- example\n\n**Goal:** fixture.\n"
        )
    for relative, text in files.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def snapshot():
        return {str(path.relative_to(project)): path.read_bytes()
                for path in project.rglob("*") if path.is_file()}

    before = snapshot()
    result = subprocess.run(
        [sys.executable, str(helper), "progress", "--project-dir", str(project)],
        capture_output=True, text=True, timeout=30,
    )
    report_ok = result.returncode == 0 and any(
        line.startswith("UC-1 ") and "1/2 slices done" in line
        for line in result.stdout.splitlines()
    )
    unchanged = before == snapshot()
    evidence = {
        "code_revision": code_revision,
        "dirty_change_identity": runtime_identity,
        "runtime_manifest": runtime_manifest,
        "python_version": sys.version,
        "coverage": "fixture CLI, not live host hooks",
        "steps": [
            {"step": 1, "ac": "AC-1", "outcome": "pass" if report_ok else "fail",
             "observed": result.stdout, "exit_code": result.returncode,
             "stderr": result.stderr},
            {"step": 2, "ac": "AC-2", "outcome": "pass" if unchanged else "fail",
             "observed": "Compared fixture file paths and bytes before/after",
             "unchanged": unchanged},
        ],
    }
    print(json.dumps(evidence, indent=2))
    raise SystemExit(0 if report_ok and unchanged else 1)
PY
```

**Expected observations:** step 1 names UC-1 with `1/2 slices done`; step 2
reports `unchanged: true`. Both outcomes must be `pass`.

**Preserved behavior:** file paths and bytes are compared, not inferred from an
exit code. A negative/refusal path in another slice needs its own expectation.

**Code revision / dirty-change identity:** the output names the source Git
revision when available and hashes the helper and its `_common` runtime module
tree, including dirty dependency edits, with a per-file manifest and Python
version. Installed payloads without Git are identified by that content digest,
not the descriptive "installed payload" label. For a larger application, record the build/commit and
identify all relevant dirty changes, such as a saved diff and digest; this
fixture runtime identity is not a general application attestation.

**Outcome discipline:** `not-run` or `environment-error` is not a pass. Missing
tools/access must remain unverified; a script that has not been executed is not
runtime evidence. This fixture proves CLI observations, not live hook firing,
an authenticated UI journey, or a reduction in escaped defects.
