#!/bin/bash
# Spec gate (deliberateness gate — see Rationale): blocks Edit/Write to
# docs/conventions.md unless JIG_CONVENTIONS_APPROVED=1 is set in the environment.
#
# Fires on PreToolUse / Edit|Write|MultiEdit. Exit 2 to block; exit 0 to allow.
#
# Rationale (see ADR-0011): docs/conventions.md encodes project rules. This gate
# is a DELIBERATENESS check, not a human-only guarantee. The env var is
# satisfiable by anyone with a shell — including the agent itself, via Bash — so
# it does NOT enforce human approval. What it reliably catches is the ACCIDENTAL
# case: an agent editing conventions.md as a side effect of unrelated work won't
# have the flag set, so the stray edit is blocked. A deliberate actor sets the
# flag to proceed. True human-only enforcement is out of scope for an in-process
# hook (a hook runs inside the agent's trust boundary); enforce it out-of-band —
# CODEOWNERS on docs/conventions.md, a CI check on the PR diff, or branch
# protection.
#
# Layout note: this gate is jig-layout-specific — it matches docs/conventions.md
# only. A project using a different constitution path (e.g. root CONVENTIONS.md)
# gets no gate. A configurable gated set (JIG_GATED_FILES) is a deferred
# enhancement (ADR-0011 Scope).
#
# Spec 078-01: an approved edit emits a content-free `gate_bypassed` event to
# .claude/skill-usage.jsonl (gate name, env var, timestamp, best-effort
# spec-ref) via skills/_common/gate_telemetry.py, so the override leaves an
# auditable trail. Resolved relative to this script's own location (works
# whether jig runs as a plugin or a scaffolded install — same idiom as
# jig-memory-scan.sh's lexicon import). Fail-open: any telemetry error is
# swallowed and never turns an allowed edit into a block.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_DIR="$SCRIPT_DIR" python3 -c "
import sys, json, os

script_dir = os.environ.get('SCRIPT_DIR', '.')

try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path') or tool_input.get('path') or ''
    if not file_path:
        sys.exit(0)

    # Normalize to defeat path-traversal bypasses like
    # 'foo/docs/conventions.md/../conventions.md'. realpath resolves symlinks too.
    try:
        resolved = os.path.realpath(file_path) if os.path.isabs(file_path) else os.path.normpath(file_path)
    except Exception:
        sys.exit(0)

    # Gate the resolved path docs/conventions.md (absolute suffix or relative match)
    if not (resolved.endswith(os.sep + 'docs' + os.sep + 'conventions.md')
            or resolved == os.path.join('docs', 'conventions.md')):
        sys.exit(0)

    # Opt-in approval token. Mirrors _common/parsing.FRONTMATTER_TRUTHY
    # ({1,true,yes,on}) — kept inline (not imported) so this load-bearing gate
    # gains no _common-import failure mode; a source-inspection test pins the
    # two token sets in sync. Widened from a bare '1' for cross-gate
    # consistency; '1' still works (backward-compatible).
    if (os.environ.get('JIG_CONVENTIONS_APPROVED') or '').strip().lower() in ('1', 'true', 'yes', 'on'):
        try:
            common_dir = os.path.join(script_dir, '..', '..', 'skills', '_common')
            if common_dir not in sys.path:
                sys.path.insert(0, common_dir)
            from gate_telemetry import emit_gate_bypass, read_spec_ref
            project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '.')
            emit_gate_bypass(project_dir, 'conventions', 'JIG_CONVENTIONS_APPROVED',
                              spec_ref=read_spec_ref(project_dir))
        except Exception:
            pass
        sys.exit(0)

    sys.stderr.write(
        'Blocked: docs/conventions.md changes require deliberate approval.\n'
        'This gate catches accidental side-effect edits; it is not a human-only '
        'guarantee.\n'
        'If this change is intentional, set JIG_CONVENTIONS_APPROVED=1 in your '
        'shell session and retry.\n'
    )
    sys.exit(2)
except SystemExit:
    raise
except Exception as exc:
    sys.stderr.write(f'jig-spec-gate hook error: {exc}\n')
    sys.exit(0)
"
