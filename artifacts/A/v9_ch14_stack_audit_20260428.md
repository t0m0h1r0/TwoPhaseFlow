# CHK-RA-CH12-13-002 — V9 vs CH14 Stack Audit

## Verdict

V9 is not implemented according to the chapter 14 production stack.

The user's suspicion is correct for the pressure/interface operators: the current
`experiment/ch13/exp_V9_local_eps_nonuniform.py` is a reduced CCD/CSF probe, not
a §14-style FCCD/HFE/pressure-jump run.

## Evidence

- `paper/sections/14_benchmarks.tex` states that all §14 YAMLs share
  non-uniform interface-fitted grids, FCCD pressure gradients, HFE curvature,
  pressure-jump phase-separated PPE, UCCD6 convection, and IMEX-BDF2/implicit-BDF2
  time evolution.
- `experiment/ch14/config/ch14_capillary.yaml` and
  `experiment/ch14/config/ch14_rising_bubble.yaml` encode the same stack:
  `interface.transport.spatial: fccd`,
  `momentum.terms.convection.spatial: uccd6`,
  `momentum.terms.pressure.gradient: fccd`,
  `momentum.terms.surface_tension.formulation: pressure_jump`, and
  `projection.poisson.operator.discretization: fccd`.
- Current V9 constructs `CCDSolver`, computes curvature through
  `CurvatureCalculator`, applies surface tension as CSF `sigma*kappa*grad(psi)`,
  builds the PPE through `PPEBuilder`, and corrects velocity with `_ccd_grad(p)`.

## Operator Mismatch

| Role | CH14 stack | Current V9 | Assessment |
| --- | --- | --- | --- |
| Pressure gradient / projection | FCCD face-gradient + face-flux projection | nodal CCD gradient + FVM `PPEBuilder` | mismatch |
| Surface tension | pressure-jump in phase-separated PPE | CSF body force `sigma*kappa*grad(psi)` | mismatch |
| Curvature | HFE-filtered `psi_direct_hfe` path | legacy `CurvatureCalculator` without HFE filter | mismatch |
| Interface transport | FCCD/TVD-RK3 | no interface transport; static re-evaluation only | reduced probe |
| Momentum convection | UCCD6/IMEX-BDF2 | no convection term in the reduced static-droplet loop | not applicable unless V9 becomes a true dynamic NS run |

## Recommendation

Do not use the current V9 result as evidence for §14 local-thickness behavior.
It can only be described as a reduced CCD/CSF diagnostic.

For a §14-facing V9 replacement, use the config-driven `TwoPhaseNSSolver` stack
or an equivalent reduced script that explicitly uses:

- FCCD pressure gradient and face-flux projection;
- phase-separated FCCD PPE with `jump_decomposition`;
- HFE-filtered curvature;
- `surface_tension.formulation=pressure_jump`;
- UCCD6 only if the replacement includes a nonzero momentum-convection stage.

The key correction is not just "replace CCD with FCCD"; the pressure-jump
formulation and face-locus projection closure must be changed at the same time.

## SOLID / PR Assessment

- `[SOLID-X]` Audit artifact only; no production classes or module ownership changed.
- PR-5: Current V9 deviates from the §14 algorithmic stack, so its paper-facing
  interpretation must be corrected before it is used as §14 support evidence.
