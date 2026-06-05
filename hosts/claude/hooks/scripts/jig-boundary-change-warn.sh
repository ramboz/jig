#!/bin/bash
# Boundary-change-warn: fires when Edit/Write/MultiEdit touches a canonical
# external-interface contract-artifact file (OpenAPI / AsyncAPI / .proto /
# GraphQL / *.schema.json). Emits a soft additionalContext nudge pointing
# the author at /jig:adr-workflow new and the surface-appropriate
# breaking-change ecosystem tool. Always exits 0 — never a gate.
#
# The canonical filename + tool list is sourced manually from
# skills/contracts/SKILL.md "Per-surface artifact recommendations". If the
# contracts skill grows the table later, this hook grows with it. The sync
# is manual and intentional (slice 005-03 AC #2).
#
# Mechanics (slice 005-03, mirrors 027-01):
#   - Edit / Write / MultiEdit fire identically — basename-only match.
#   - Case-insensitive basename match.
#   - Fires on both new-file Write and Edit of an existing artifact
#     (Clarification Q3 — don't gate on file-existed-before-edit).
#   - Crash posture: silent `except Exception: pass`. No stderr writes
#     (Clarification Q2).
#   - Opt-out: JIG_BOUNDARY_CHECK=0.
python3 -c "
import sys, json, os, fnmatch

# (pattern, tool-mention, surface-label) — order matters: more specific
# patterns first (e.g., *.schema.json before bare json fallbacks). All
# matches are case-insensitive.
PATTERNS = [
    ('openapi.yaml',   'redocly diff / spectral (OpenAPI breaking-change ruleset)', 'OpenAPI'),
    ('openapi.yml',    'redocly diff / spectral (OpenAPI breaking-change ruleset)', 'OpenAPI'),
    ('openapi.json',   'redocly diff / spectral (OpenAPI breaking-change ruleset)', 'OpenAPI'),
    ('asyncapi.yaml',  'AsyncAPI parser diff (asyncapi/parser)',                    'AsyncAPI'),
    ('asyncapi.yml',   'AsyncAPI parser diff (asyncapi/parser)',                    'AsyncAPI'),
    ('asyncapi.json',  'AsyncAPI parser diff (asyncapi/parser)',                    'AsyncAPI'),
    ('*.proto',        'buf breaking',                                              'Protocol Buffers'),
    ('*.graphql',      'graphql-inspector diff',                                    'GraphQL SDL'),
    ('*.graphqls',     'graphql-inspector diff',                                    'GraphQL SDL'),
    ('*.schema.json',  'JSON Schema diff against the base ref',                     'JSON Schema'),
]

def match_pattern(basename):
    '''Return (tool, surface) on match, or (None, None) if no pattern hits.

    Match is case-insensitive: lowercase the basename, lowercase each glob.
    Special case for *.schema.json: the .schema infix is load-bearing —
    package.json must not match. fnmatch handles this naturally with the
    *.schema.json glob; the * is greedy and would not match a bare .json.'''
    name = basename.lower()
    for pat, tool, surface in PATTERNS:
        if fnmatch.fnmatchcase(name, pat.lower()):
            return tool, surface
    return None, None

try:
    if os.environ.get('JIG_BOUNDARY_CHECK') == '0':
        sys.exit(0)

    data = json.load(sys.stdin)
    tool_name = data.get('tool_name', '')
    if tool_name not in ('Edit', 'Write', 'MultiEdit'):
        sys.exit(0)

    tool_input = data.get('tool_input', {}) or {}
    file_path = tool_input.get('file_path') or ''
    if not file_path:
        sys.exit(0)

    basename = os.path.basename(file_path)
    if not basename:
        sys.exit(0)

    tool, surface = match_pattern(basename)
    if tool is None:
        sys.exit(0)

    # Nudge text — AC #3 four parts: basename, ADR pointer, surface tool,
    # informational reminder.
    msg = (
        f'{basename} ({surface}) was just edited. '
        f'If this is a breaking change, consider capturing the rationale '
        f'with /jig:adr-workflow new <slug>, and confirm with the '
        f'surface-appropriate breaking-change tool: {tool}. '
        f'This nudge is informational, not a gate.'
    )
    print(json.dumps({'continue': True, 'additionalContext': msg}))
except SystemExit:
    raise
except Exception:
    pass
"
exit 0
