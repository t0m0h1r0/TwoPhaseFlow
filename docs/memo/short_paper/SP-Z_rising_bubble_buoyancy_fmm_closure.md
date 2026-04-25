# SP-Z — Rising-Bubble Buoyancy/FMM Closure for ch13

- **Status**: ACTIVE
- **Compiled by**: Codex
- **Compiled at**: 2026-04-25
- **Scope**: `ch13_rising_bubble_water_air_alpha2_n128x256`
- **Code commits**: `90273da` (implementation), `a3bc8f2` (initial note)

## 1. Abstract

The clean worktree reproduces the last stable
`worktree-researcharchitect-src-refactor-plan` rising-bubble run only after
three theoretical constraints are enforced together:

1. **pressure-robust buoyancy placement** — the hydrostatic component of
   density-dependent gravity is kept in pressure space;
2. **projection-native predictor state** — the predictor/corrector carries the
   same face state used by the variable-density PPE operator;
3. **converged Ridge--Eikonal redistancing** — the level-set signed-distance
   reconstruction uses the non-uniform FMM Eikonal solve, not a fixed-sweep
   approximation.

These are algorithmic constraints, not tuning knobs. The ch13 blow-up is best
interpreted as an operator-compatibility failure: the predictor, projection,
balanced force, and reinitialisation each used a plausible local
discretisation, but the composed discrete identities did not close.

## 2. Production vocabulary

The user-facing YAML should name the *theoretical role*, not the internal
implementation detail. The accepted production vocabulary is therefore:

```yaml
numerics:
  momentum:
    predictor:
      assembly: balanced_buoyancy
    terms:
      convection:
        spatial: uccd6
        time_integrator: ab2
      viscosity:
        spatial: ccd
        time_integrator: crank_nicolson
        cn_mode: richardson
  projection:
    face_flux_projection: true
    canonical_face_state: true
    face_native_predictor_state: true
```

Backward-compatible aliases remain accepted:

- `balanced`, `well_balanced`, `well_balanced_buoyancy`, and `buoyancy_split`
  map to `balanced_buoyancy`;
- legacy `buoyancy_faceresidual_stagesplit_transversefullband` also maps to
  `balanced_buoyancy`;
- `cn_mode: richardson` maps internally to `richardson_picard`.

The long phrase `buoyancy_faceresidual_stagesplit_transversefullband` is useful
as an implementation diagnosis, but it is not suitable as a paper-facing or
experiment-facing abstraction.

## 3. A3 traceability chain

| Item | Paper-level equation/claim | Discretisation memo | Code implementation | Experiment gate |
|---|---|---|---|---|
| Buoyancy split | `rho' g = -grad(rho' Phi_g) + Phi_g grad(rho')` | SP-U, SP-V, this SP §4 | `src/twophase/simulation/ns_step_services.py` | ch13 rising bubble reaches `t=0.5` |
| Predictor assembly | gradient forces must not enter solenoidal velocity predictor | SP-Q--SP-X, this SP §5 | `src/twophase/simulation/ns_predictor_assembly.py` | no KE blow-up near `t≈0.38--0.46` |
| Face-canonical state | projection identity is `D_f A_f G_f`; predictor must live on same locus | SP-W, WIKI-L-032/033 | `src/twophase/simulation/ns_pipeline.py`, `ns_step_services.py` | `ppe_rhs`, `bf_res`, `div_u` finite to final time |
| Time integration | convective, viscous, pressure, and source stages have different stability character | SP-Y, this SP §6 | CN advance callbacks + AB2 convection | stable with `cfl=0.10` |
| Ridge--Eikonal | signed-distance field must satisfy `|grad(phi)|=1` on non-uniform grid | SP-B, SP-E, this SP §7 | `src/twophase/levelset/ridge_eikonal_reinitializer.py` | curvature remains bounded at final time |

## 4. Theoretical pillar I — pressure-robust buoyancy

Let gravity be vertical and let `Phi_g = -g y`. With `rho' = rho - rho_ref`,
the density-dependent body force can be written as

```text
rho' g = -grad(rho' Phi_g) + Phi_g grad(rho').
```

The first term is a gradient. In the incompressible projection setting, a pure
gradient force belongs in pressure space because the velocity after projection
is determined by the solenoidal component of the forcing. If this gradient
piece is advanced as an explicit velocity source, the predictor sees a large
non-solenoidal acceleration that the PPE then has to undo. In exact arithmetic
with perfectly compatible operators that cancellation may be benign; on a
non-uniform, phase-separated, face-projected grid it is precisely where a
large residual can be injected.

The production discretisation therefore forms a face residual acceleration:

```text
a_f^res = face(f_b / rho) + (1/rho)_f G_f(rho' Phi_g).
```

The `+` sign appears because the hydrostatic gradient has been moved to the
pressure side. In a well-balanced rest state, the projection pressure can
absorb `-grad(rho' Phi_g)` and the velocity predictor only receives the
non-hydrostatic residual `Phi_g grad(rho')`.

**Theoretical significance.** This is the two-phase analogue of
pressure-robust / well-balanced source treatment: gradient forces should not
drive the divergence-free velocity space. The key is not merely subtracting a
large number; the hydrostatic and non-hydrostatic parts must be represented on
the same discrete locus as the pressure operator.

## 5. Theoretical pillar II — same-locus face-state closure

The phase-separated FCCD projection solves a variable-density PPE whose
operator is, schematically,

```text
D_f A_f G_f p = D_f u*_f / dt + jump terms,
```

where `G_f` is the face pressure-gradient map, `A_f` is the face coefficient
`1/rho`, and `D_f` is the matching face divergence. This operator identity is
the discrete balanced-force contract. If the predictor is built only as nodal
velocity and then later remapped to faces, the remap introduces an additional
operator not present in the PPE. That breaks the identity being used to cancel
pressure-like forces.

The imported closure therefore introduces two state rules:

1. **canonical face state**: the projected face velocity is a primary state
   carried between steps;
2. **face-native predictor state**: predictor increments are assembled as
   face increments first, and nodal velocities are reconstructed only as the
   shape required by legacy term evaluators.

This is not "cache reuse" in the performance sense. It is an algorithmic state
variable required by the discrete proof: the object that appears in `D_f u*_f`
must be the same object whose correction is represented by `A_f G_f p`.

**Theoretical significance.** The implementation moves the predictor from a
node-centred convenience representation to the face-centred representation
where the projection theorem is actually stated. That is why the change is
more fundamental than storing an intermediate array.

## 6. Theoretical pillar III — time integration split

The selected time integration is deliberately not "one RK method for
everything." The terms have different stiffness and invariants:

- `u·grad u` is a transport-like term and is advanced explicitly with AB2;
- viscous stress is parabolic and uses Crank--Nicolson;
- the CN solve is refined by Richardson/Picard composition to recover the
  intended second-order predictor behaviour in the nonlinear pipeline;
- pressure is not a force stage but a constraint projection;
- buoyancy is split before entering the predictor, so the pressure-like part
  remains inside the projection solve.

TVD/SSP-RK3 remains appropriate for bounded hyperbolic interface transport,
where the SSP convex-combination argument is relevant. It is not the right
organising principle for the full variable-density NS momentum update because
the projection and pressure-like source cancellation are not represented as a
single explicit semidiscrete RHS.

**Theoretical significance.** The time update is term-aware. Stability is not
judged by a scalar RK stability region alone; it depends on whether each term
is advanced in the space where its continuous invariant is represented. For
this benchmark, the decisive invariant is the pressure/buoyancy balance, not
third-order explicit RK order.

## 7. Theoretical pillar IV — Ridge--Eikonal is required

The capillary and pressure-jump terms depend on interface geometry. In the CLS
pipeline, curvature quality depends on reconstructing a signed-distance field
`phi` satisfying

```text
|grad(phi)| = 1,
```

with the prescribed sign convention. The Ridge--Eikonal method has two roles:

1. it protects topology by extracting a ridge representation of the interface;
2. it restores metric quality by solving the Eikonal problem from accepted
   interface seeds on the non-uniform grid.

The second role is not optional for the rising-bubble benchmark. A fixed number
of pseudo-time/Godunov sweeps is not equivalent to the accepted-set FMM solve
unless one proves residual convergence and correct wall/non-uniform boundary
treatment. In the observed sequence, an approximate device sweep delayed the
instability but did not remove it; the non-uniform FMM path crossed the failing
region and completed `t=0.5`.

**Theoretical significance.** Ridge--Eikonal is not a visual smoothing tool.
It is the metric closure used by curvature, pressure jump, and balanced-force
operators. If the GPU implementation is changed, the replacement must be a
mathematically equivalent GPU FMM or a residual-converged non-uniform
fast-sweeping method.

## 8. Imported items and their meaning

| Imported item | Why it was imported | Theory it preserves | Why the old behaviour failed |
|---|---|---|---|
| `balanced_buoyancy` predictor | keep hydrostatic gravity in pressure space | pressure-robust gradient-force cancellation | full buoyancy in predictor created a large non-solenoidal stage |
| face residual acceleration | evaluate buoyancy residual with PPE face operators | same-locus `D_f A_f G_f` consistency | nodal residual and face projection used different maps |
| canonical face state | preserve projected face velocity across steps | projection state is the primary constrained state | recomputing faces from nodes lost the projection-native variable |
| face-native predictor state | assemble `u*_f` before PPE RHS | PPE RHS uses `D_f u*_f`, not arbitrary nodal `u*` | predictor/corrector did not close as a discrete identity |
| CN callback hooks | allow predictor assembly inside implicit viscous stage | source split and viscous solve must share the same stage state | applying the split outside CN changed the state seen by viscosity |
| Richardson/Picard CN mode | reduce splitting error in nonlinear CN path | second-order centred diffusion response | single Picard CN was too sensitive to intermediate-state mismatch |
| non-uniform FMM redistancing | solve `|grad(phi)|=1` with accepted upwind causality | signed-distance metric for curvature and jumps | fixed sweeps left enough metric error to trigger late blow-up |
| YAML vocabulary update | expose theory rather than implementation mechanics | reproducible experiment semantics | old value encoded debug implementation details |

## 9. Paper insertion material

Suggested paper paragraph:

> For buoyancy-driven two-phase runs we do not advance the full
> density-dependent gravity term in the explicit momentum predictor. Writing
> `rho' g = -grad(rho' Phi_g) + Phi_g grad(rho')`, the hydrostatic gradient is
> retained in pressure space while only the residual term is assembled in the
> velocity predictor. Discretely, this residual is constructed on the same
> face-centred coefficient-gradient-divergence chain used by the
> phase-separated PPE, so that the predictor state entering `D_f u*_f` and the
> corrector `A_f G_f p` share the same geometric locus. This is a
> pressure-robust, well-balanced source treatment rather than a post-hoc
> stabilisation.

Suggested Ridge--Eikonal paragraph:

> The reinitialisation step is required to recover a signed-distance field
> satisfying `|grad(phi)|=1` on the non-uniform interface-fitted grid. The
> accepted-set FMM update is retained in production because curvature and
> pressure-jump balance are sensitive to residual Eikonal error. GPU
> acceleration of this step is admissible only if it preserves the same
> non-uniform upwind Eikonal solve or supplies an explicit residual-convergence
> criterion.

Suggested time-integration paragraph:

> The final time integrator is term-aware: explicit AB2 for momentum
> convection, Crank--Nicolson with Richardson/Picard refinement for viscosity,
> pressure projection as a constraint solve, and SSP-RK3 only for bounded
> interface transport. This split follows the invariants of each operator
> rather than imposing one explicit Runge--Kutta stability region on the whole
> variable-density projection method.

## 10. Verification

Validation on 2026-04-25:

```text
make test
  559 passed, 3 skipped, 2 xfailed

make run EXP=experiment/ch13/run.py ARGS="ch13_rising_bubble_water_air_alpha2_n128x256"
  reached t = 0.5000 in 140 steps
  final KE = 9.494e-04
  final kappa_max = 3.528e+03
  final ppe_rhs = 6.719e+02
  final bf_res = 2.786e+02
```

The previous failing window near `t≈0.38--0.46` is crossed without kinetic
energy blow-up. Final field outputs include `psi`, velocity, and pressure at
`t=0.500`.

## 11. Literature anchors

The paper text should cite the local bibliography entries already used in the
SP series:

- Shu--Osher and Gottlieb--Shu--Tadmor for SSP/TVD RK theory;
- Brackbill--Kothe--Zemach and François et al. for continuum/balanced-force
  surface tension;
- Almgren et al. and Guermond--Salgado for variable-density projection and
  pressure splitting;
- Sethian and Osher--Sethian for accepted-set Eikonal/level-set foundations;
- the well-balanced source-term literature cited in SP-U for gradient-force
  preservation.

