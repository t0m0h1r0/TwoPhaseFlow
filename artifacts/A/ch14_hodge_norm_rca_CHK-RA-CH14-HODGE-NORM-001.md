# CHK-RA-CH14-HODGE-NORM-001

## Scope

User request: investigate the remaining nonzero capillary Hodge norm from
physics and mathematics first, generate many hypotheses, verify them, identify
the problem, design a theoretical remedy, and verify whether the remedy solves
the identified problem.  Symptom-hiding fixes such as damping, CFL tuning,
curvature caps, smoothing, fallback solvers, benchmark branches, blanket range
projection, or QP-as-physics are forbidden.

## Theorem Contract

The finite-dimensional statement is shape-free.  A closed component is static
only when the chosen discrete surface-energy covector lies in the span of the
chosen component-volume covectors:

```text
d_z(sigma S_h) = sum_m lambda_m d_z V_m .
```

The capillary drive is then the component-constrained pressure-Hodge quotient
of the corresponding face-space Riesz representative.  Therefore a sampled
analytic circle is not a finite-grid oracle.  It is static only if it is a
critical point of the selected discrete geometry and transport map.

## Hypotheses

| ID | Hypothesis | Test | Verdict |
|---|---|---|---|
| H01 | Hodge normal-equation solver leaves algebraic residue | manufactured pure-range cochain and `D_f h` gate from prior fix | falsified; pure range recovers roundoff |
| H02 | wall/periodic boundary handling creates the residual | periodic vs wall N16/32/64 sweep | falsified; values are identical away from walls |
| H03 | affine-jump inverse-density weights are missing | arithmetic face mass vs affine cut-face mass | falsified as main cause; ratios unchanged |
| H04 | one component reaction is missing | component-reaction Hodge projection and orthogonality | falsified as algebra; component direction is included |
| H05 | sign of the volume reaction is wrong | best-fit coefficient remains physical positive in vertex criticality | falsified |
| H06 | sampled circle is assumed to be discrete static | vertex `dS_h - lambda dV_h` residual | supported |
| H07 | ellipse/circle classification is contaminating the logic | criticality uses only covector span, no shape label | falsified by construction |
| H08 | trace-Riesz cochain is not adjoint to the actual conservative psi transport endpoint | finite difference of `S_h(psi + eps T_f u)` vs face power | supported |
| H09 | residual is reinit work | all probes are fixed-stratum, no-reinit geometry probes | falsified for this residual |
| H10 | residual is just a visualization/diagnostic norm artifact | divergence and component-orthogonality gates | falsified; the quotient component is real |
| H11 | density ratio alone creates static current | constant and variable metrics compared qualitatively | falsified as direct cause |
| H12 | P1 trace geometry is too low-order for sampled analytic circles to be exact | finite-grid criticality residual | supported |

## Key Measurements

Static criticality and Hodge projection, using `sigma=0.072`:

| case | N | bc | vertex criticality ratio | trace Hodge ratio | trace Hodge L2 | conservative-transport Hodge ratio |
|---|---:|---|---:|---:|---:|---:|
| circle | 16 | periodic | `6.096979e-02` | `2.299902e-02` | `2.309683e-02` | `3.442493e-01` |
| circle | 32 | periodic | `1.568664e-01` | `3.611950e-02` | `5.240871e-02` | `2.700926e-01` |
| circle | 64 | periodic | `2.110791e-01` | `5.270868e-02` | `1.078979e-01` | `4.003813e-01` |
| ellipse | 32 | periodic | `3.164826e-01` | `1.035021e-01` | `1.518272e-01` | `7.190677e-01` |
| circle | 32 | wall | `1.568664e-01` | `3.611950e-02` | `5.240871e-02` | `2.700929e-01` |
| ellipse | 32 | wall | `3.164826e-01` | `1.035021e-01` | `1.518272e-01` | `7.190672e-01` |

Affine metric check for the static circle:

| N | arithmetic-metric Hodge ratio | affine-metric Hodge ratio | max relative weight change |
|---:|---:|---:|---:|
| 16 | `2.450469e-02` | `2.452716e-02` | `1.267890e-01` |
| 32 | `3.732547e-02` | `3.736686e-02` | `1.150124e-01` |
| 64 | `5.479642e-02` | `5.526277e-02` | `1.312640e-01` |

Actual-transport adjoint check at N32 static circle, using the trace surface
cochain as the probe velocity:

| quantity | value |
|---|---:|
| finite difference of `S_h` under actual conservative `T_f u` | `-1.286553e+00` |
| conservative-transport Riesz face power | `+1.286553e+00` |
| conservative actual-transport residual | `5.761773e-09` |
| trace-vertex face power | `+2.105346e+00` |
| trace actual-transport residual | `2.413967e-01` |
| trace self-Riesz residual under its own `C_K` | `1.054671e-16` |

The trace cochain is mathematically self-consistent for its declared trace map,
but it is not the adjoint of the conservative `psi` transport endpoint
currently used by the solver.  Separately, the sampled circle is not a
discrete constrained critical trace for the selected P1 geometry.  These are
the two supported causes of the remaining nonzero Hodge norm.

## Remedy Implemented

The remedy in this checkpoint is fail-close diagnostic structure, not force
clipping:

```text
TraceStaticCriticality:
  residual = d_z(sigma S_h) - projection_span{d_z V_m} d_z(sigma S_h)
```

Code changes:

- `src/twophase/coupling/closed_interface_trace_riesz.py`
  adds `TraceStaticCriticality`, `trace_static_criticality`, and
  `trace_vertex_static_criticality`.
- `TraceComponentHodgeProjection` now carries the static-criticality result.
- `src/twophase/simulation/interface_projection_diagnostics.py` and
  `src/twophase/simulation/step_diagnostics.py` export
  `capillary_static_critical_*` diagnostics.

This solves the identified diagnostic problem: a nonzero Hodge norm can now be
separated from projection algebra and read against the discrete
Euler--Lagrange static condition.  It intentionally does not erase the force.

The remaining physics implementation decision is explicit:

```text
If production transport remains conservative face-psi transport,
  the accepted capillary cochain must be the VJP of that endpoint.
If production adopts trace-vertex transport as the physical endpoint,
  the interface transport update must be made consistent with C_K.
In both cases, a sampled analytic circle is convergence data;
  roundoff staticity requires a constructed discrete critical trace.
```

## Verification

Local targeted tests:

```text
PYTHONPATH=src /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python -m pytest \
  src/twophase/tests/test_closed_interface_trace_riesz.py \
  src/twophase/tests/test_interface_projection_diagnostics.py -q
```

Result:

```text
16 passed in 0.79s
```

Remote-first validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_closed_interface_trace_riesz.py twophase/tests/test_interface_projection_diagnostics.py -q'
```

The project wrapper ran the full CPU suite:

```text
614 passed, 33 skipped in 43.77s
```

Targeted theorem gates added:

- manufactured component-reaction covector gives static-critical residual
  ratio `< 1e-14`;
- sampled N32 circle gives residual ratio `> 1e-2`, proving it is not treated
  as a finite-grid static oracle;
- capillary diagnostics report the static-criticality scalars without changing
  pressure, corrector, transport, reinit, or production force behavior.

## Verdict

The remaining nonzero Hodge norm is not a Hodge solver bug, not a boundary
artifact, not an affine-weight artifact, and not something to zero out.  The
direct causes are:

1. the sampled analytic circle is not an exact constrained critical point of
   the selected finite-dimensional trace geometry;
2. the trace-vertex cochain is self-adjoint for `C_K`, but the solver currently
   transports `psi` through a different conservative face endpoint.

The implemented diagnostic remedy solves the interpretation and fail-close
problem.  A production force-law change must choose one endpoint theorem and
make force and transport share that same VJP; otherwise the nonzero norm is
real evidence of a theorem mismatch, not a tunable numerical nuisance.

[SOLID-X] Diagnostic/theory gate only; no tested implementation deleted; no
FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing,
benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics path introduced.
