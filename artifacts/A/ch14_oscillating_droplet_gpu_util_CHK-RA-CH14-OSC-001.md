# CHK-RA-CH14-OSC-001: ch14 oscillating-droplet GPU-utilization rounds

Date: 2026-05-08
Branch: `codex/ra-ch14-osc-gpu-util-20260508`
Worktree: `.claude/worktrees/codex-ra-ch14-osc-gpu-util-20260508`

## Scope

Optimize the `experiment/ch14/` oscillating-droplet route for GPU utilization and
wall-clock behavior without changing the paper route:

- keep `closed_interface_riesz`, `pressure_component_hodge`,
  `variational_adjoint`, `variational_operator`, FCCD/UCCD6, and
  `ridge_eikonal`;
- no damping, CFL workaround, smoothing, curvature cap, benchmark branch,
  fallback PPE, or physics shortcut;
- keep the Rayleigh-Lamb phase metric `signed_deformation`.

## Rounds

1. Baseline 12-step remote probe, canonical numerical stack with output disabled:
   `real=15.171s`, GPU `avg=94.94%`, active `avg=94.94%`, `ge50=0.985`,
   `max_mem=593 MiB`. Profile top: PPE defect-correction and cuSPARSE
   `spSM_analysis`, closed-interface component saddle, ridge-eikonal
   sharp-volume projection.
2. Enabled static operator cache inside
   `capillary_external_component_saddle_projection` only during the temporary
   zero-jump saddle solve, with graph snapshot/restore. Probe was neutral
   (`real=15.211s`), but the change avoids repeated low-order factor rebuilds
   for multiple same-rho saddle solves and restores solver state after use.
3. Removed one duplicate residual evaluation per diffuse-mass bisection in
   `RidgeEikonalReinitializer._apply_diffuse_mass_profile_constraint`.
   Targeted ridge-eikonal tests passed. Probe improved to `real=14.449s`.
4. Reused the already-computed scale-1 diffuse residual and returned cached
   `psi_candidate` when a sample meets tolerance. Probe was noisy
   (`real=14.733s`) but avoids redundant sigmoid/materialization work.
5. Removed the unsigned `deformation` diagnostic from canonical
   `ch14_oscillating_droplet.yaml`, leaving `signed_deformation` as the plotted
   Rayleigh-Lamb phase metric. 12-step probe improved to `real=9.167s`,
   `max_mem=288 MiB`.
6. Side-effect audit for the user question "signed_deformationなくす副作用ない?":
   confirmed `signed_deformation` remains in diagnostics and figures, and added
   a config contract test. Removing `signed_deformation` would break the
   benchmark output, so it was not removed.
7. Longer 48-step probe after the diagnostic change to reduce startup noise:
   `real=34.061s`, final `step=48`, `t=0.4563`, route completed.
8. Audited derived ch14 oscillating controls and found
   `n64_oscillating_droplet(one_period=True)` re-added unsigned
   `deformation`; removed it and added a variant contract test.
9. Re-ran 48-step probe with a saved `nvidia-smi` monitor:
   `real=33.863s`, monitor `samples=115`, active `samples=67`,
   active GPU `avg=55.46%`, active `ge50=0.672`, `max_mem=288 MiB`.
   The lower average versus the baseline reflects less diagnostic/memory work;
   the remaining utilization waves come from small PPE/reinit/saddle kernels.
10. Final validation and cleanup: temporary probe YAML and pulled results were
    removed from the worktree. Local and remote targeted tests passed, and
    `git diff --check` passed.

## Adopted changes

- The oscillating-droplet canonical and N64 one-period variant now collect
  `signed_deformation` only, not both signed and unsigned deformation.
- The component saddle projection enables temporary static operator reuse inside
  its zero-jump solver graph, then restores the original graph state.
- Ridge-eikonal diffuse profile correction avoids repeated residual and
  materialization work in the scalar bracket/bisection.

## Validation

- Local targeted pytest:
  `5 passed in 0.49s`
- Remote targeted pytest after push:
  `5 passed in 0.42s`
- Remote 48-step route probe:
  `real=33.863s`
- `git diff --check`:
  pass

Note: a remote `make test PYTEST_ARGS='--gpu -k "a or b"'` attempt failed
because `remote.sh` drops the quoted `-k` expression and pytest treats `or` as
a file name. The same pushed code passed the exact target tests through direct
remote pytest.

## SOLID

[SOLID-X] [SOLID-D] [SOLID-P] The changes are scoped to GPU hot-path reuse,
diagnostic selection, and scalar reinitialization work reuse. No solver
equation, capillary model, pressure/PPE route, FCCD/UCCD6 route, reinit
physics, boundary condition, or benchmark physics was replaced or relaxed.
