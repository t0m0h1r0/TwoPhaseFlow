# CHK-RA-CAP-HODGE-PITFALL-001 - Pitfall Audit for Generic Variational-Hodge Capillarity

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`

## Executive Verdict

The generic variational-Hodge theory remains the right target, but it is easy
to implement a wrong version that looks mathematically similar.  The dangerous
mistake is to treat the slogan

```text
preserve the Hodge component of c_f
```

as sufficient.  It is not sufficient.  The correct statement is:

```text
build the physically weighted surface-energy force covector;
map it through the exact transport adjoint into the exact face space used by
the PPE/corrector;
then preserve its incompressible projection under the same mass inner product.
```

Any shortcut around those words can reintroduce either static spurious currents
or dynamic zero-drive.

## Critical Pitfalls

### P1 - Wrong Inner Product for `P_h`

The pressure range and Hodge complement are not Euclidean objects in the real
solver.  With variable density, nonuniform metrics, cut-face coefficients, and
face control volumes, pressure accelerations are orthogonal to divergence-free
velocities in the physical kinetic-energy pairing, not in a bare l2 norm.

For continuous variable-density projection:

```text
rho * (1/rho grad p) = grad p,
```

so orthogonality is with the `rho`-weighted velocity inner product.  In face
space this means the projection must use the same mass/metric pairing as the
velocity update and the same adjoint as the PPE/corrector.

Toy weighted model:

```text
D match corr/bad                         3.69e-15 / 3.01e-15
proj_bad_distance_to_correct_range_Wf    9.523e-01
range_component_difference_Wf            9.523e-01
```

The naive projection matched `D c` but lived outside the correct weighted
pressure range.  Thus `D h = 0` alone is not enough; the range itself must be
the weighted-adjoint pressure range.

Mitigation:

- Define the face mass matrix `M_f` and cell pairing before coding.
- Define `G_f` as the adjoint paired with `D_f` under those pairings.
- Define `P_h` only after those choices.

### P2 - Force Covector vs Acceleration Cochain

Virtual work pairs a force covector with velocity:

```text
<F_sigma, u_f>.
```

The velocity corrector applies acceleration:

```text
u_f^{n+1} = u_f^* + dt * M_f^{-1} F_sigma + ...
```

If `c_f` is sometimes a force and sometimes a mass-inverted acceleration, signs
and density factors can silently flip or double-count.  This is especially
dangerous at high density ratio.

Mitigation:

- Name two objects if needed: `force_covector_f` and `accel_cochain_f`.
- State which one enters `D_f A_f G_f p`.
- Unit-test density scaling by changing `rho_l/rho_g` with fixed geometry.

### P3 - Full Pressure vs Pressure Increment

In IPC/fractional-step schemes, the pressure unknown may be full pressure,
pressure increment, base pressure, or acceleration history.  A Young-Laplace
jump belongs to the same unknown.  If the solver unknown is an increment, the
jump must be an increment.  If the solver unknown is full pressure, the full
jump is appropriate.

Failure modes:

- full jump inserted into an increment solve: double-counting or force kill;
- previous capillary face history subtracted twice;
- Hodge diagnostic computed on full cochain but corrector uses increment
  cochain.

Mitigation:

- For each pressure stage, write the unknown explicitly:
  `p`, `delta p`, `p_base`, or `a_p,f`.
- Attach the capillary cochain to that unknown, not to a generic "pressure".

### P4 - Raw Curvature Jump Is Not Automatically Variational

The Hodge theory says to preserve the incompressible part of a *physical*
capillary cochain.  It does not say every raw curvature-derived jump is
physical.  A raw `face_implicit` curvature jump can contain numerical Hodge
content caused by chain-rule failure, trace mismatch, nonuniform metrics, or
support mismatch.

This is the biggest conceptual trap after zero-drive.  Setting
`capillary_range_projection:none` may restore motion, but it does not prove the
motion is the correct surface-energy force.

Mitigation:

- Build or verify `c_f` through a discrete surface-energy virtual-work gate:
  `<c_f, w_f> = - delta E_h[w_f]`.
- Treat static spurious current as failure of cochain construction, not as
  permission for blanket Hodge deletion.

### P5 - Reinitialization and Remap Are Not Surface Tension

Ridge-Eikonal, volume closure, and fitted-grid rebuilds alter the
representation.  They may alter moment diagnostics and surface proxies even
when velocity is zero.  They are not physical capillary relaxation unless they
are explicitly included in the transport map and energy accounting.

Mitigation:

- Split physical transport from representation repair.
- Record deformation changes under zero velocity.
- Exclude reinit/remap from the capillary virtual-work identity unless the
  identity explicitly includes their map.

### P6 - Boundary, Contact, Body-Force, and Multi-Component Constraints

The admissible velocity space changes with:

- periodic vs wall boundary conditions;
- no-penetration and contact-angle constraints;
- gravity or other body potentials;
- multiple disconnected components and per-component volume constraints;
- topology changes/coalescence.

The equilibrium condition is therefore not "constant curvature" in isolation.
It is the vanishing first variation of total constrained energy.

Mitigation:

- Define the admissible space before computing `P_h c_f`.
- For gravity, include potential energy.
- For walls/contact, include boundary energy or contact constraints.
- For multiple components, define the volume constraints and pressure gauges.

### P7 - Topology and Threshold Nonsmoothness

Marching-squares/P2 trace energies can be nonsmooth when the interface crosses a
vertex, changes topology, creates a tiny component, or has nearly zero
`|grad psi|`.  A discrete gradient may become ill-conditioned or undefined.

Mitigation:

- Fail closed near degenerate cuts.
- Report condition metrics for trace geometry.
- Do not smooth/cap as a hidden physics fix; if regularization is introduced,
  name the regularized energy functional.

### P8 - Face/Nodal Space Mismatch

The capillary work is a face-space statement.  If the corrected face velocity is
then reconstructed to nodes and a different nodal velocity is used for CLS
transport, kinetic diagnostics, or next-step history, the virtual-work identity
can be lost.

Mitigation:

- Use the canonical projected face state for interface transport.
- Compute capillary work in the same face state.
- Audit reconstruction as an output operation, not as the source of truth.

### P9 - Tangential or Non-Scalar Interface Stresses

A scalar Young-Laplace pressure jump represents normal capillarity with
constant surface tension.  Marangoni stresses, viscous stress jumps, contact-line
dissipation, and surfactant physics are not scalar pressure jumps.

Mitigation:

- Add separate stress cochains for those physics.
- Do not hide them in `h_f` or delete `h_f` because scalar pressure cannot
  represent them.

### P10 - Time Discretization Overclaim

An explicit variational cochain can be first-order consistent but not
unconditionally energy stable.  A discrete-gradient identity over a finite step
usually couples `psi^{n+1}` and velocity; making it explicit changes the
theorem.

Mitigation:

- State whether the method is explicit, semi-implicit, or fully discrete
  gradient.
- For explicit methods, keep the capillary CFL gate.
- For implicit methods, verify the finite-step energy identity.

### P11 - Gauge, Nullspace, and Solver Compatibility

Projection identities assume the Poisson problem is solved in the intended
range with the intended gauge.  Phase-separated systems can have extra null
spaces, pin constraints, or phase-mean compatibility corrections.

Mitigation:

- Verify `D_f A_f G_f` range, gauge, and compatibility after cut-face assembly.
- Do not let pinning or phase-mean repair change the capillary work identity.

### P12 - Verification Can Pass the Wrong Theorem

The previous finite-dimensional check verified the algebra of range deletion,
not the full production theorem.  A test can pass while using the wrong inner
product, wrong pressure unknown, or non-variational cochain.

Mitigation:

- Keep algebra tests, but label them algebra-only.
- Add virtual-work tests against `E_h`.
- Add density/metric/boundary variants for every gate.

## Minimum Safe Next Step

Before touching production logic, define the following in one place:

1. face velocity space and boundary constraints;
2. face mass/kinetic-energy inner product;
3. pressure unknown for the current stage;
4. surface-energy functional `E_h`;
5. transport map from face velocity to interface change;
6. adjoint map from `delta E_h` to face force;
7. conversion from force covector to acceleration cochain;
8. diagnostics: range part, Hodge part, virtual-work residual, static critical
   residual, dynamic release.

Only after those are explicit should implementation begin.

## Strongest Warning

The correct fix is not:

```text
capillary_range_projection: none
```

as a blind production setting.  That may revive oscillation, but it may also
revive non-variational static currents.  The correct fix is:

```text
construct a variational capillary cochain, then preserve its incompressible
projection.
```

[SOLID-X] pitfall/docs only; no solver/config production change; no tested
implementation deleted; no FD/WENO/PPE fallback or alternate route introduced.
