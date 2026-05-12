# CHK-RA-CH14-AO-FASTVOL-005 - AO-Fast explicit fallback YAML/UX policy

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User correction: "DC failure then PCG" is not fail-close when it is implicit.
This checkpoint fixes the AO-Fast solver UX contract so that fallback is
opt-in, named, gated, and ledgered.  It remains a theory/specification
checkpoint.  No solver source is changed.

## Decision

AO-Fast has three separate UX concepts:

```text
primary solver   owns convergence for the configured projection,
accelerator      may propose candidates but cannot change solver family,
fallback         may change solver family only through a declared chain.
```

The default policy is `fallback.policy: none`.  Under that policy:

```text
DC proposal accepted by exact Q/S gates  -> commit candidate,
DC proposal rejected                     -> discard candidate,
primary solver succeeds                  -> commit primary solve,
primary solver fails                     -> fail close.
```

There is no implicit DC-to-PCG or PCG-to-Newton transition.

## YAML Shape

Default fail-close AO-Fast route:

```yaml
interface:
  state_space:
    kind: geometric_cell_fraction
    compatibility:
      projection:
        method: active_stratum_schur
        fail_close: true
        solver:
          primary: active_pcg_newton
          accelerators:
            dc_candidate:
              enabled: true
              role: proposal_only
              on_reject: discard_candidate
          fallback:
            policy: none
```

Explicit fallback route:

```yaml
interface:
  state_space:
    kind: geometric_cell_fraction
    compatibility:
      projection:
        method: active_stratum_schur
        fail_close: true
        solver:
          primary: residual_monotone_dc
          fallback:
            policy: explicit_chain
            chain:
              - from: residual_monotone_dc
                to: active_pcg_newton
                triggers:
                  - no_exact_residual_decrease
                  - trust_region_exhausted
                record_as: dc_to_pcg_declared_fallback
```

The second form is acceptable only because the fallback edge is visible in YAML.
It is not a hidden runtime rescue path.

## Parser And UX Rules

The parser must reject:

```text
fail_close=false,
fallback aliases such as auto, try_next, best_effort, or on_failure,
fallback.policy=explicit_chain without nonempty chain,
chain entries missing from, to, triggers, or record_as,
accelerator.on_reject values that switch the primary solver,
DC configured as both proposal_only accelerator and fallback source in the same edge,
fallback to a solver that is not an admissible AO active solver.
```

The UI should expose fallback as an advanced opt-in policy, not as a recovery
checkbox.  The default display should say `Fallback: none (fail close)`.  When
fallback is enabled, the UI should show every transition as `from -> to`, the
exact trigger list, and the ledger label that will be emitted.

## Ledger Contract

Every AO-Fast compatibility projection must record:

```text
solver.primary,
accelerator.name,
accelerator.accepted,
fallback.policy,
fallback.transition,
fallback.trigger,
fallback.record_as,
exact_residual_before,
exact_residual_after.
```

When `fallback.policy: none`, `fallback.transition` must be `none`; a nonempty
transition is a contract violation.  When an explicit fallback fires, exact
`Q_h/S_h` residual gates remain mandatory before commit.

## Completion Judgement

The AO-Fast design now preserves fail-close semantics.  PCG/Newton may be the
primary active solver, or it may be an explicitly declared fallback target, but
it is never an automatic consequence of DC failure.

## SOLID-X

Theory/specification artifact only.  No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, implicit fallback, or hidden DCCD/UCCD damper introduced.
