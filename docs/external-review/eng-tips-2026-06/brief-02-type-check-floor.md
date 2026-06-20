# Brief: Add a type-check floor to code-health (tighten jig's own contracts)

> EngTip #3 ("Tighten Contracts on Nullable Values With Optional Types")
> argues for making contracts *statically enforceable* rather than
> relying on authors being "careful enough." jig's whole thesis is
> contract-tightening, yet jig's own Python helpers have no type-checker
> in the loop — `code-health` runs ruff (`F,E,W,I,B`) only.

## Problem

`ruff.toml` selects `F,E,W,I,B` — lint and import hygiene, no type
analysis. There is **no mypy / pyright** anywhere in CI
(`scripts/run_tests.py`, `ruff.toml`, no type-check step). The helpers in
`skills/_common/` and the per-skill `*.py` files use type hints
*inconsistently*, and nothing enforces or checks them.

For a tool that preaches "tighten the contract so the compiler/linter
catches the null path" (EngTip #3) and "a test should affirmatively fail
when the contract changes" (EngTip #11), jig's own helper contracts are
unchecked. A function that starts returning `None` on a new path has
nothing flagging the unguarded callers.

`code-health` already has the exact mechanism for this: ADR-0017's
`AdvisoryProbe` — a report-but-never-gate signal (already used for
complexity and prettier). A type-checker fits that slot cleanly.

## Scope

1. **Decide advisory vs. gating** (the core question):
   - **(a) Advisory probe** — add a type-checker as an `AdvisoryProbe`
     in `health.py` (reported in the summary, never maps the 0/1/2 exit).
     Lowest friction; mirrors complexity/prettier. Recommended default.
   - **(b) Primary check, opt-in** — type errors gate exit 1, but only
     when a project opts in (a `.jig/typecheck` marker or `pyproject`
     config), so jig doesn't impose typing on every scaffolded project.
   - Whichever wins for *scaffolded projects*, decide separately what
     jig's **own repo** runs (jig can hold itself to the stricter bar).
2. **Pick the checker + invocation** consistent with code-health's
   "install nothing" rule: resolve on PATH, else run ephemerally
   (`uvx mypy` / `uvx pyright` / `pipx run`), degrade to "skipped (no
   type-checker)" — never crash. Mirror the ruff resolver chain.
3. **Add it to the `ECOSYSTEMS` table** as a Python probe (Node already
   has tsc as a natural future analog — note it, don't build it).
4. **Bring jig's own helpers up to a passing baseline** — add the
   missing hints, fix the real null-path findings the checker surfaces.
   This is the EngTip #3 payoff and likely the bulk of the work.

## Non-goals

- **No new dependency in the shipped plugin.** Type-checkers run
  ephemerally or off PATH, like every other code-health tool. jig stays
  stdlib-only.
- **No "100% typed" mandate** for scaffolded projects. The floor is a
  *signal*, gated behind opt-in if it gates at all (ADR-0011 spirit:
  jig recommends, the project decides).
- **No strict-mode crusade.** Start permissive (catch the obvious
  null/attr paths); strictness is a later dial.
- **No Node/tsc implementation** in this brief — Python only; leave the
  table extension point documented for a follow-on.

## Suggested SPIDR axis

**R (Rules)** primary — "what does the type floor check, and does it
gate?" is the core rule. **I (Interface)** secondary — the `health.py`
probe surface.

## Sketch of slices

1. **typecheck-probe** — add the type-checker as an `AdvisoryProbe` in
   `health.py` (resolver chain + summarizer + "skipped" degrade), with
   tests covering: found-on-PATH, ephemeral fallback, no-checker degrade,
   and findings-summary shape. Update ADR-0017's consequences (amendment
   or short note) to record the new probe.
2. **jig-self-baseline** — run the probe over jig's own helpers, add
   missing hints, fix real findings, and wire the check into
   `run_tests.py` / the local CI gate so jig holds *itself* to the
   stricter (gating) bar even if scaffolded projects only get advisory.

## Dependencies

- **None blocking.** `health.py` + `AdvisoryProbe` (spec 060 / ADR-0017)
  are DONE and are the foundation.
- Light coupling with the **code-health reviewer pass** (060-05): the
  reviewer already judges the injected health summary — type findings
  flow into that judgment for free once they're in the summary.

## Notes for clarify / SPIDR

- Likely clarify question: "mypy or pyright?" pyright is faster and has
  a better no-config experience; mypy is more conventional in stdlib-
  Python shops. Worth a one-line decision in the spec; either fits the
  resolver pattern.
- Likely clarify question: "Won't this be noisy on jig's `sys.path.insert`
  pattern?" `ruff.toml` already ignores `E402` for that reason; expect a
  similar small ignore-list for the type-checker. Capture the baseline
  ignores explicitly.
- Honest scoping note: the *probe* is small; the *self-baseline* (fixing
  real findings across all helpers) is the unknown — slice 2 may surface
  genuine latent null-path bugs, which is the point. Budget for it.
- This is the most directly "EngTip #3" of the bundle — the spec should
  cite it, and the deviation log should note any real contract bug the
  checker caught (evidence the floor earns its keep).
