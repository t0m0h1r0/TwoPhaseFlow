# CHK-171: rising-bubble alpha=2 root-cause hypotheses and controls

Date: 2026-04-21
Branch: `worktree-rising-bubble`
Execution: remote GPU via `./remote.sh run`

## Theoretical framing

The projection step should satisfy the discrete identity

```text
D M^{-1} G p = D u* / dt + D f/rho
u^{n+1} = u* - dt M^{-1} G p + dt f/rho
D u^{n+1} = 0
```

For the alpha=2 wall-grid path, the current code mixes three spaces:

- PPE matrix: FVM face operator with harmonic face `1/rho`.
- PPE RHS before CHK-171 PoC: CCD nodal divergence of `u*` and `f/rho`.
- Corrector: FVM face-gradient averaged back to nodes, then multiplied by
  nodal `1/rho`.

This means the solved matrix is not the operator applied by the corrector:

```text
D_FVM (rho_node^-1 G_avg p) != A_FVM(rho_face^-1) p
```

At density ratio 833:1, a small projection mismatch is amplified at the
interface. Any nonzero force creates `u*` or `f/rho`; the projection then
injects divergence instead of removing it.

## Hypotheses

| ID | Hypothesis | Discriminator |
|---|---|---|
| H1 | Surface tension balanced-force residual is the sole trigger. | `sigma=0` should remove blowup. |
| H2 | Buoyancy/gravity is the sole trigger. | `g=0` should remove blowup. |
| H3 | Alpha=2 non-uniform projection inconsistency is the amplifier. | `alpha=1` should survive the same short run. |
| H4 | Grid/reinit path alone injects velocity. | `sigma=0, g=0` should still show nonzero KE. |
| H5 | PPE RHS divergence mismatch is one component. | Replacing CCD RHS divergence with FVM divergence should reduce residuals. |

## Remote GPU controls

All controls used the same gas bubble, density ratio, FCCD flux transport,
`ridge_eikonal`, and `consistent_gfm` setup unless noted.

| Case | Result | Key diagnostics |
|---|---|---|
| alpha=2 baseline | BLOWUP step 27, `t=0.007014` | max `bf_residual=1.52e12`, max `div_u=1.60e5` |
| alpha=2, `sigma=0` | BLOWUP step 28, `t=0.007308` | surface tension is not the sole trigger |
| alpha=2, `g=0` | BLOWUP step 27, `t=0.007127` | buoyancy is not the sole trigger |
| alpha=2, `sigma=0`, `g=0` | Stable to `T=0.02` | `KE=0`, `rhs=0`, `div_u=0` |
| alpha=1 baseline | Stable to `T=0.02` | `KE=2.59e-5`, max `div_u=7.23e-2` |

## CHK-171 PoC

Implemented a minimal strategy-layer PoC:

- `FVMDivergenceOperator` for non-uniform wall grids.
- `CCDDivergenceOperator` for the existing uniform/default path.
- PPE RHS now uses the paired divergence strategy for both `u*` and `f/rho`.

Targeted local verification:

- `py_compile` on `gradient_operator.py` and `ns_pipeline.py`
- `PYTHONPATH=src ... pytest src/twophase/tests/test_ns_pipeline_fccd.py -q`
- result: `6 passed`

Remote GPU result after PoC:

| Case | Result | Improvement |
|---|---|---|
| alpha=2 baseline | BLOWUP step 27, `t=0.007149` | max `bf_residual` reduced `1.52e12 -> 3.99e11`; not solved |
| alpha=2, `sigma=0` | BLOWUP step 27, `t=0.007367` | max `ppe_rhs` reduced `5.84e11 -> 1.28e11`; not solved |

## Identified cause

The dominant cause is not a pure surface-tension bug, not a pure buoyancy bug,
and not reinitialization alone. It is a non-uniform-grid projection closure bug:

```text
PPE solve:      face FVM, harmonic rho_face
velocity fix:   nodal correction, nodal rho_i, averaged pressure gradient
diagnostic D:   now FVM after PoC, previously CCD
```

The no-force alpha=2 run proves the grid/reinit path does not create velocity
by itself. The `sigma=0` and `g=0` controls prove either force family can excite
the same projection defect. The alpha=1 run proves the failure is tied to the
non-uniform metric/density projection rather than the bubble shape alone.

## Countermeasure

The production fix should move the projection update to face fluxes:

1. Build `u_face*` and `v_face*` from predictor velocities.
2. Solve the same FVM PPE already assembled by `PPEBuilder`.
3. Correct face fluxes with the same harmonic face coefficient used by the PPE:

```text
u_face^{n+1} = u_face* - dt * a_face * (p_R - p_L) / d_face
```

4. Include surface tension as a face force in the same face metric space:

```text
u_face^{n+1} += dt * (sigma kappa grad(psi))_face / rho_face
```

5. Reconstruct nodal velocities from corrected face fluxes using a conservative
   face-to-node operator, and use `D_FVM(u_face^{n+1})` as the divergence gate.

The CHK-171 PoC should be retained as a partial consistency improvement, but it
is not sufficient because it fixes only RHS divergence, not the nodal corrector
closure.
