# CHK-RA-CH14-GEOM-IMPL-001: closed-interface geometry implementation

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: implement and verify the first proof-sized code slice for
closed-interface Riesz capillarity: fixed-stratum geometry diagnostics.  This
does not change production capillary force, PPE, corrector, YAML defaults, or
ch14 runtime physics.

## Implemented

New modules:

```text
src/twophase/coupling/closed_interface_stratum.py
src/twophase/coupling/closed_interface_geometry.py
```

New tests:

```text
src/twophase/tests/test_closed_interface_geometry.py
```

The public coupling exports now include:

```text
ClosedInterfaceStratum
build_closed_interface_stratum
trace_surface_length_2d
trace_surface_length_gradient_2d
liquid_area_2d
liquid_area_gradient_2d
fixed_stratum_directional_derivative_check
```

## Mathematical Contract Covered

This slice covers only the geometry part of the selected diagram:

```text
K fixed,
S_h(q) = P1 marching-squares trace length,
V_h(q) = sharp area of psi >= threshold,
dS_h and dV_h valid only while K is unchanged.
```

`ClosedInterfaceStratum` records:

```text
cell sign cases,
edge crossing counts,
cut-cell count,
ambiguous-cell count,
threshold-touch count,
topology hash,
regular/irregular flag.
```

`TraceGeometryFunctional` currently provides:

```text
trace_surface_length_2d       P1 sharp trace length
trace_surface_length_gradient existing P1 marching-squares length gradient
liquid_area_2d                sharp P1 liquid area
liquid_area_gradient_2d       analytic nodal area derivative
fixed_stratum_directional_derivative_check
```

The area derivative is assembled from the oriented shoelace formula.  Original
cell corners have zero coordinate derivative; edge-crossing vertices carry the
chain rule from crossing fraction to the two endpoint `psi` values.  The
finite-difference checker fails closed if either `psi+eps*r` or `psi-eps*r`
changes the stratum hash.

## Tests Added

The tests verify:

```text
1. stratum hash remains stable under small same-pattern perturbations,
2. exact threshold touches are irregular and fail closed,
3. axis-aligned half-plane length and area are correct,
4. dS_h matches centered fixed-stratum finite differences,
5. dV_h matches centered fixed-stratum finite differences,
6. derivative checks reject irregular base strata.
```

## Validation

Remote-first command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_closed_interface_geometry.py -q'
```

The wrapper pushed the worktree and expanded to the CPU suite.  Final result:

```text
598 passed, 32 skipped in 43.43s
```

Whitespace validation:

```text
git diff --check
```

passed before this artifact row was written.

## What Remains

This is intentionally not the production capillary fix yet.  Remaining slices:

```text
1. TransportLinearization: actual pre-reinit transport VJP and dot-product gate.
2. CapillaryRieszCochain: s=-M_f^{-1}T^TdE and B=M_f^{-1}T^TdV.
3. AugmentedCapillaryHodgeProjector: multi-column pressure/component reaction
   projection.
4. CorrectorSignLock: energy-lowering sign in the existing pressure-flux
   convention.
5. YAML/runtime mode: explicit source=closed_interface_riesz after gates pass.
6. ch14 N=32/T=1 and T=10 validation with reinit-separated visuals.
```

[SOLID-X] First implementation slice only; no C1 violation found in the new
geometry/stratum boundary.  No production source/config/result change, no
tested implementation deleted, no FD/WENO/PPE fallback, damping, CFL
workaround, curvature cap, smoothing, blanket `c -> Pi_R c`, benchmark-name
branch, or QP-as-physics path introduced.
