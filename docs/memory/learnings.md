# Learnings

> Dead ends, failed approaches, "we tried X and here's why it didn't work."
> The institutional memory that ADRs don't capture because they're not decisions —
> they're anti-patterns and gotchas discovered in practice.
>
> Update via `/jig:memory-sync` during reconciliation.

## Hook PATH injection does not apply to hook commands

`bin/` scripts are added to PATH for the **Bash tool only**, not for hook `command` fields.
Hook commands must use `bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.sh`.
Discovered: plan review (rev 2). Would have caused silent failures at runtime.

## jq is not safe as a hook script dependency

`jq` is not installed by default on macOS. Hook scripts that depend on it will fail
silently on fresh installs. Use Python 3 (reliably present) for JSON parsing.
Discovered: plan review (rev 2). Rule: all hook scripts use `python3 - <<'EOF'`.

## The bootstrap paradox for self-enforcing hooks

A spec-gate hook for `docs/conventions.md` cannot enforce itself during scaffold creation —
the hook only activates after scaffold-init completes. This is fine: the gate starts
working from the second session onward. Don't fight the paradox; document it.
Discovered: plan review (rev 2), issue #3.

## `python3 - <<'EOF'` consumes stdin — fatal for hook scripts

The pattern `python3 - <<'EOF' ... EOF` runs Python with `-` (script from stdin)
where stdin is the heredoc. Python reads the script, leaving `sys.stdin` at EOF.
So `json.load(sys.stdin)` returns "Expecting value: line 1 column 1" — there is
no JSON to read. This silently broke ALL 5 hook scripts in the initial commit.

**Fix:** Use `python3 -c "<script>"` instead. The script is a command-line argument,
and stdin remains available for the hook payload. `docs/memory/tooling.md` was
updated to reflect this.

Discovered: slice 001-01 TDD, while running `test_conventions_gate_blocks`. The
test failed with "Expecting value: line 1 column 1 (char 0)" — the smoking gun.
Caught only because the spec-gate hook had a deterministic test; the other hooks
appeared to "work" because they only ran the silent telemetry/scan paths and
exited 0.

**Generalizable lesson:** If a hook is async and exits 0 on errors (telemetry pattern),
you cannot tell whether it works without a deterministic test that asserts a
specific output. Every new hook needs a unit test that pipes mock stdin and
checks behavior.
