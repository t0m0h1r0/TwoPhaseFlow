# CHK-RA-CH14-RIESZ-VERIFY-001

## Scope

User request: verify the central closed-interface Riesz capillary law, not a
visual workaround.

The candidate law tested here is the implementation-facing theorem:

```text
T(u) = -D_f(psi_f u_f)
s    = -M_f^{-1} T^T d(sigma S_h)^T
B    =  M_f^{-1} T^T dV_h^T
```

where `S_h` is the fixed-stratum P1 marching-squares trace length, `V_h` is
the sharp P1 liquid area, `M_f` is the face mass/measure metric, and the Hodge
projection uses the exact dense diagnostic matrix for the same `D_f`.

This checkpoint intentionally does not alter production capillary physics.
It proves which theorem gates the current candidate passes and which one it
fails.

## Implementation

Added diagnostic source:

```text
src/twophase/coupling/closed_interface_riesz.py
src/twophase/tests/test_closed_interface_riesz.py
```

The module exposes:

```text
ClosedInterfaceRieszCochain
closed_interface_riesz_cochain
fixed_stratum_virtual_work_check
weighted_hodge_decomposition
component_reaction_hodge_gate
```

It constructs the face acceleration cochain from the actual transport adjoint,
checks fixed-stratum finite differences of `sigma S_h`, and projects the face
cochain with a dense `range(M_f^{-1}D_f^T)` Hodge solve.  This is deliberately
a proof tool, not a faster production path.

## Virtual-Work Gate

For an N12 periodic ellipse probe, using the constructed cochain itself as the
test face velocity:

```text
finite_difference      = -3.550367776828e+01
gradient_action        = -3.550367702084e+01
capillary_power        =  3.550367702084e+01
fd_gradient_residual   =  1.052614345697e-08
riesz_residual         =  0.000000000000e+00
```

This proves the algebraic Riesz statement for the selected discrete transport
map: `d(sigma S_h)[T(u)] + <s,u>_M = 0` on the fixed stratum.

## Static/Dynamic Hodge Gate

The same candidate then fails the static critical-point gate.  After best
component-volume reaction removal, the residual Hodge norm for a nearly round
circle does not approach roundoff:

| N | circle surface Hodge | circle component residual | ratio |
|---:|---:|---:|---:|
| 10 | `8.271914088111e-02` | `4.583342999469e-02` | `5.540849373734e-01` |
| 12 | `1.135141799258e-01` | `2.571383992489e-02` | `2.265253551733e-01` |
| 14 | `1.178302663551e-01` | `1.786111893948e-02` | `1.515834555245e-01` |
| 16 | `6.900992665271e-02` | `2.375661786592e-02` | `3.442492843889e-01` |
| 24 | `1.290759590706e-01` | `2.695700659712e-02` | `2.088460685570e-01` |

The Hodge residuals are divergence-free under the same dense `D_f` solve
(`~1e-12` Linf divergence), so this is not a pressure solve artifact.

The ellipse also has a strong nonzero Hodge drive, as required for dynamic
release:

| N | ellipse surface Hodge | ellipse component residual | ratio |
|---:|---:|---:|---:|
| 10 | `1.261464914683e-01` | `1.211537811598e-01` | `9.604213303881e-01` |
| 12 | `1.928367433359e-01` | `1.237050543443e-01` | `6.415014701260e-01` |
| 14 | `2.018196350715e-01` | `1.529367883682e-01` | `7.577894406263e-01` |
| 16 | `1.693413122495e-01` | `1.322183384260e-01` | `7.807801691720e-01` |
| 24 | `1.893565886632e-01` | `1.425394701014e-01` | `7.527568547138e-01` |

## Verdict

The core candidate passes the Riesz virtual-work identity but fails the
static Young-Laplace gate.  Therefore it must not be promoted to production
as the final capillary force.

The failure is mathematically informative: the conservative nodal indicator
transport map `T(u)=-D_f(psi_f u_f)` is not the correct fixed-stratum
transport differential for the sharp trace geometry.  It gives a valid Riesz
representative of its own discrete transport law, but that law does not make a
closed round interface a constrained critical point under the same Hodge
metric.  In short:

```text
Riesz identity:             PASS
static Young-Laplace gate:  FAIL
dynamic nonzero gate:       PASS
production acceptance:      FAIL
```

The next theorem-grade route is not damping, smoothing, CFL tuning, curvature
capping, or projection deletion.  It is to replace the transport differential
with the true fixed-stratum trace-vertex transport map, i.e. the VJP of the
zero-crossing polygon geometry under face velocities, then re-run the same
virtual-work and static/dynamic Hodge gates.

## Validation

Remote-first validation:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='twophase/tests/test_closed_interface_riesz.py -q'
```

The project wrapper expanded to the full CPU suite:

```text
602 passed, 32 skipped in 41.46s
```

[SOLID-X] Diagnostic/proof code only; production solver behavior and YAML
defaults unchanged.  No tested implementation deleted; no FD/WENO/PPE fallback,
damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket
`c -> Pi_R c`, or QP-as-physics path introduced.
