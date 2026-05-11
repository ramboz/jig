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
