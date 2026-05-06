# CHK-RA-CH14-GEOM-N32T4-001

## Scope

User request: try the current ch14 static and oscillating droplets at
`N=32,T=4`, continuing the `N=32,T=1` validation of the current production
path after the closed-interface geometry implementation slice.

The production capillary cochain, pressure projection, corrector, transport,
and reinitialization algorithms are unchanged.  This is a longer regression
and physical-behavior probe, not proof of the final fixed-stratum Riesz force.

## Commands

Temporary derived configs were generated from the canonical ch14 YAMLs, with
`grid.cells=[32,32]`, `run.time.final=4.0`, and snapshot interval `0.2`.
They were removed after execution.

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_static_n32_t4_geom_impl'
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_osc_n32_t4_geom_impl'
```

Results were pulled to:

```text
experiment/ch14/results/_tmp_ch14_static_n32_t4_geom_impl/
experiment/ch14/results/_tmp_ch14_osc_n32_t4_geom_impl/
```

Both result directories contain `psi`, `velocity`, and `pressure` snapshot
PDFs through `t=4`.

## Metrics

| Quantity | Static N32/T4 | Oscillating N32/T4 |
|---|---:|---:|
| final time | `4.0` | `4.0` |
| steps | `405` | `396` |
| final volume drift | `8.882719812894e-16` | `1.661460800696e-15` |
| max volume drift | `3.172399933176e-15` | `3.961944986275e-15` |
| first KE | `2.680382538057e-12` | `2.246143054319e-09` |
| final KE | `3.168855531975e-09` | `2.479811774672e-03` |
| max KE | `8.305994192533e-09` | `2.479811774672e-03` |
| deformation | `0 -> 0` | `8.034730291014e-02 -> 6.838554894764e-02` |
| signed deformation | n/a | `7.617534118366e-02 -> 2.894198501011e-02` |
| Rayleigh-Lamb reference at `t=4` | n/a | `7.838e-02` |
| signed deformation error at `t=4` | n/a | approximately `-4.944e-02` |
| max snapshot speed Linf | `3.240408584682e-05` | `2.333385447203e-02` |
| final snapshot speed Linf | `1.631759068061e-05` | `2.267173169021e-02` |
| max pressure contrast | `2.962676141588e-01` | `4.862082440709e-01` |
| final pressure contrast | `2.957473904514e-01` | `4.567399814025e-01` |
| max pressure-acceleration face Linf | `1.048475174367e-04` | `1.697013145264e-02` |
| final pressure-acceleration face Linf | `7.279326109840e-05` | `1.245365787171e-02` |

## Verdict

The longer `N=32,T=4` gate passes for execution, volume conservation, finite
fields, and visualization output.

The static droplet remains deformation-stationary and low-energy through
`t=4`; the nonzero face acceleration and KE stay small but are not roundoff
zero.  This remains consistent with the known limitation that the current
scalar curvature-jump cochain plus component reaction projection is not yet a
theorem-grade constrained critical-point proof.

The oscillating droplet keeps receiving nonzero capillary drive through `t=4`:
KE grows to `2.479811774672e-03`, max speed reaches
`2.333385447203e-02`, and the velocity/pressure snapshot fields remain finite.
This confirms that the old algebraic zero-drive pathology is absent.

Physically, the phase/amplitude are still not acceptable as final
Rayleigh-Lamb physics.  The canonical analytical overlay uses
`D_ref(t)=0.10 cos(0.167435 t)`, so `D_ref(4)≈7.838e-02`, while the simulated
signed deformation is `2.894198501011e-02`.  Because every-step Ridge-Eikonal
reinit is active in the oscillating run, this shape signal cannot be read as
pure capillary transport.  The next theorem-grade task remains the
fixed-stratum transport-adjoint Riesz force and reinit-separated energy ledger.

[SOLID-X] Validation/artifact only; no solver, production YAML, pressure
projection, corrector, transport, or reinit behavior changed; no tested
implementation deleted; no FD/WENO/PPE fallback, damping/CFL workaround,
curvature cap, smoothing, benchmark branch, blanket `c -> Pi_R c`, or
QP-as-physics path introduced.
