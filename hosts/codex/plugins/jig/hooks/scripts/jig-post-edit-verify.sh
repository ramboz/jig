#!/bin/bash
# Post-edit verify: re-reads the file region that Edit/Write/MultiEdit just
# touched and emits a soft warning if the claimed write isn't in the file.
#
# Fires on PostToolUse / Edit|Write|MultiEdit. Always exits 0 — this is a
# same-turn signal, not a gate. Reviewer subagents still catch semantic drift;
# this only catches mechanical "the edit silently didn't take" cases.
#
# Mechanics (slice 027-01):
#   - Edit: new_string is present in file (or, if new_string is empty,
#     old_string is no longer present).
#   - Write: first 200 bytes of file match first 200 bytes of requested content.
#   - MultiEdit: each edit checked individually.
#   - Bounded to 64KB total read per file (10MB files don't full-file-read).
#   - Opt-out: JIG_POST_EDIT_VERIFY=0.
python3 -c "
import sys, json, os

MAX_READ = 65536
WRITE_PREFIX = 200

def check_edit(content_bytes, fully_read, new_string, old_string, file_path):
    '''Return warning text on a confirmed mismatch, None otherwise.

    Best-effort: if the file is larger than MAX_READ and we did not find
    new_string in the head, we return None (cannot confirm a mismatch).'''
    if new_string == '':
        # Deletion: old_string should no longer be present.
        if old_string and old_string.encode() in content_bytes:
            preview = old_string[:60].replace('\n', ' ')
            return (
                f'{file_path} post-edit check failed: deletion did not take '
                f'(old_string {preview!r} still present). Re-read and retry.'
            )
        return None
    if new_string.encode() in content_bytes:
        return None
    if fully_read:
        preview = new_string[:60].replace('\n', ' ')
        return (
            f'{file_path} post-edit check failed: new_string {preview!r} '
            'not found in file. Re-read and retry.'
        )
    return None  # file larger than read budget — cannot confirm mismatch

try:
    if os.environ.get('JIG_POST_EDIT_VERIFY') == '0':
        sys.exit(0)

    data = json.load(sys.stdin)
    tool_name = data.get('tool_name', '')
    if tool_name not in ('Edit', 'Write', 'MultiEdit'):
        sys.exit(0)

    tool_input = data.get('tool_input', {}) or {}
    file_path = tool_input.get('file_path') or ''
    if not file_path or not os.path.exists(file_path):
        sys.exit(0)  # AC 8: missing file → silent

    try:
        size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            content_bytes = f.read(MAX_READ)
    except Exception:
        sys.exit(0)
    fully_read = size <= MAX_READ

    warnings = []

    if tool_name == 'Edit':
        w = check_edit(
            content_bytes, fully_read,
            tool_input.get('new_string', '') or '',
            tool_input.get('old_string', '') or '',
            file_path,
        )
        if w:
            warnings.append(w)
    elif tool_name == 'Write':
        content = tool_input.get('content', '') or ''
        expected = content.encode()[:WRITE_PREFIX]
        actual = content_bytes[:WRITE_PREFIX]
        if expected != actual:
            warnings.append(
                f'{file_path} post-write check failed: first {WRITE_PREFIX} '
                'bytes of file do not match requested content. Re-read and retry.'
            )
    elif tool_name == 'MultiEdit':
        edits = tool_input.get('edits', []) or []
        total = len(edits)
        for i, edit in enumerate(edits):
            w = check_edit(
                content_bytes, fully_read,
                edit.get('new_string', '') or '',
                edit.get('old_string', '') or '',
                file_path,
            )
            if w:
                warnings.append(f'(edit {i+1}/{total}) ' + w)

    if warnings:
        msg = ' | '.join(warnings)
        print(json.dumps({'continue': True, 'additionalContext': msg}))
except SystemExit:
    raise
except Exception:
    pass
"
exit 0
