# CHK-RA-CH14-CAPILLARY-AO-RUN-001 — ch14 capillary AO run

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: confirm `experiment/ch14/config/ch14_capillary.yaml` is configured to use the short-paper AO logic, then run the Chapter 14 capillary-wave experiment in a new worktree.

## YAML AO contract check

`experiment/ch14/config/ch14_capillary.yaml` matches the SP-AO front door:

- `interface.state_space.kind: geometric_cell_fraction`
- transported `q`, normalized `theta`, P1 gauge `phi`
- `compatibility.constraint: hard_cell_volume`
- `projection.implementation: active_cached`
- GPU contract requires SoA active storage, forbids inner host transfers, and forbids dense runtime fallback
- `solver.primary: active_pcg_newton`
- `fallback.policy: none`
- `interface.transport.variable: q`
- `interface.transport.spatial: geometric_swept_volume`
- `interface.tracking.primary: q`
- reinitialization disabled with `algorithm: none` and `every_steps: 0`
- capillary source uses `bundle_virtual_work`
- closed-interface endpoint is `geometric_cell_fraction`
- PPE capillary reaction projection is `pressure_component_hodge`

This is consistent with `docs/memo/short_paper/SP-AO_geometric_cell_fraction_state_space.md` §12 and the parser fail-close rules.

## Execution

Command:

```bash
make cycle EXP=experiment/run.py ARGS='--config ch14_capillary'
```

Remote execution reached the simulation start:

```text
==> ch14_capillary
config : /root/TwoPhaseFlow/experiment/ch14/config/ch14_capillary.yaml
outdir : /root/TwoPhaseFlow/experiment/ch14/results/ch14_capillary
[ch14_capillary] Running simulation...
[dynamic/1 non-uniform] grid built from IC, h_min=3.9638e-04
```

The run then failed closed at the GPU AO capillary boundary:

```text
ValueError: GPU AO capillary fail-close: diagonal active-Schur pressure solve violates Young-Laplace normal equations (9.806374e-07 > 1.000000e-11); a certified active PCG/Newton/DC solve is required before advancing; pressure_history_mode='pressure_coordinate' requires a scalar AO pressure coordinate, but this packet only provides face reaction increments; non-static packet has zero pressure-balanced drive (weighted_l2=0.000000e+00, max=0.000000e+00); the current approximation cancels the capillary force by construction
```

No local `experiment/ch14/results/ch14_capillary` directory was produced by the failed `cycle` because the remote command exited before the pull phase.

## Verdict

The YAML is configured for the short-paper AO logic. The experiment cannot currently advance under that contract: the runtime correctly rejects the admitted GPU packet because the current diagonal active-Schur approximation is not a certified active PCG/Newton/DC solve and has zero pressure-balanced drive for a non-static capillary wave.

This matches the existing admission finding in `docs/wiki/theory/WIKI-T-169.md`: a non-static AO packet with diagonal active-Schur residual and zero balanced drive must fail close; it must not switch to hidden PCG, DC, dense CPU, component-Hodge, damping, CFL, smoothing, or curvature-cap fallback.

[SOLID-X] Documentation/artifact/lock bookkeeping and remote experiment execution only; no production source, solver equation, YAML physical parameter, CFL, damping, smoothing, curvature cap, FD/WENO/PPE fallback, hidden dense fallback, benchmark-specific relaxation, or main merge was introduced.
