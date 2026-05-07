# CHK-RA-CH14-GEOM-N32T1-001

## Scope

User request: validate the current ch14 static and oscillating droplets at
`N=32,T=1` after the first closed-interface geometry implementation slice.

The geometry slice does not change the production capillary cochain,
pressure projection, corrector, transport, or reinitialization.  This
checkpoint is therefore a regression/behavior validation of the current
component-Hodge production path, not proof that the final closed-interface
Riesz force is implemented.

## Commands

Temporary derived configs were used and removed after execution.

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_static_n32_t1_geom_impl'
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_osc_n32_t1_geom_impl'
```

Results were pulled to:

```text
experiment/ch14/results/_tmp_ch14_static_n32_t1_geom_impl/
experiment/ch14/results/_tmp_ch14_osc_n32_t1_geom_impl/
```

Both result directories contain `psi`, `velocity`, and `pressure` snapshot
PDFs through `t=1`.

## Metrics

| Quantity | Static N32/T1 | Oscillating N32/T1 |
|---|---:|---:|
| final time | `1.0` | `1.0` |
| steps | `102` | `100` |
| final volume drift | `2.030335957233e-15` | `2.428288862556e-15` |
| max volume drift | `2.918607938522e-15` | `2.428288862556e-15` |
| first KE | `2.680382538057e-12` | `2.246143054319e-09` |
| final KE | `5.284015367708e-09` | `3.643971286909e-04` |
| max KE | `5.284015367708e-09` | `3.643971286909e-04` |
| deformation | `0 -> 0` | `8.034730291014e-02 -> 6.838554894764e-02` |
| signed deformation | n/a | `7.617534118366e-02 -> 4.334636515834e-02` |
| max snapshot velocity component Linf | `1.852030317519e-05` | `9.417804979351e-03` |
| max snapshot speed Linf | `2.546460883371e-05` | `1.321312837017e-02` |
| final snapshot speed Linf | `2.492199895553e-05` | `1.321312837017e-02` |
| max pressure contrast | `2.959370916933e-01` | `4.733177571441e-01` |
| final pressure contrast | `2.958916635054e-01` | `3.966228025474e-01` |
| max pressure-acceleration face Linf | `9.449650451065e-05` | `1.417884072748e-02` |
| final pressure-acceleration face Linf | `5.663793271974e-05` | `1.417884072748e-02` |

## Verdict

The N32/T1 regression gate passes for execution, volume conservation, finite
fields, and visualization output.

The static droplet remains deformation-stationary with tiny but nonzero KE
and tiny pressure-acceleration faces.  This is consistent with the known
limitation of the scalar curvature-jump production cochain: the component
reaction projection strongly suppresses static drift but does not prove a
roundoff-level constrained critical point.

The oscillating droplet is no longer in the old algebraic zero-drive state:
the run develops nonzero face acceleration, velocity, and KE, with signed
deformation changing from `7.617534118366e-02` to
`4.334636515834e-02`.  This confirms that the current production path still
receives capillary drive after the geometry implementation slice.

The result must not be overinterpreted as final physics.  The mathematically
correct next implementation target remains the fixed-stratum transport-adjoint
Riesz cochain

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
```

with same-metric component reaction projection and a separate reinit energy
ledger.

[SOLID-X] Validation/artifact only; no solver, production YAML, pressure
projection, corrector, transport, or reinit behavior changed; no tested
implementation deleted; no FD/WENO/PPE fallback, damping/CFL workaround,
curvature cap, smoothing, benchmark branch, blanket `c -> Pi_R c`, or
QP-as-physics path introduced.
