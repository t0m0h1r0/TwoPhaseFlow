# CHK-RA-CH14-VAR-007 — q-to-interface-manifold projection theory

## Claim

The next Ch14 capillary theory step should treat transported cell volume
`q_T` as a measured object that may have left the smooth-interface manifold,
not as an all-cell physical constraint that the next `phi` must satisfy
exactly.

The owned physical state remains the interface configuration `Gamma_h`.  The
new diagnostic decomposition is

```text
q_T = Q_h(Gamma*) + r,
```

where `Gamma*` is the closest admissible physical interface in the selected
chart and `r` is the non-geometric residual.  The residual is not a
force-producing state variable.  It is evidence about whether transport,
projection, or rebuild has pushed the computation off the admissible interface
manifold.

## Interface Manifold

For a chart family `C_h` of smooth discrete interfaces, define

```text
M_h(C_h) = { Q_h(Gamma_h) | Gamma_h in C_h and Gamma_h is regular }.
```

Examples:

```text
graph chart:        Gamma_h = {(x_i, eta_i)}
closed-curve chart: Gamma_h = {X_i}_{i=0}^{M-1}, X_M = X_0
```

`M_h` is a low-dimensional nonlinear manifold inside the cell-volume space.
A transported conservative `q_T` can be outside `M_h` even if it satisfies
global volume conservation.  This is the precise mathematical form of the
screened graph-q failure knowledge:

```text
all-cell q exactness != physical interface admissibility.
```

## Projection Problem

For the first diagnostic oracle, solve a chart-local projection:

```text
Gamma* = argmin_Gamma  1/2 || Q_h(Gamma) - q_T ||_W^2
                       + beta [ E_h(Gamma) - E_ref ]
subject to             C_h(Gamma) = C(q_T)
                       Gamma in regular chart stratum.
```

Interpretation:

- `Q_h(Gamma)` is the derived cell-volume measure.
- `W` is a declared measurement metric on cell volumes, preferably scaled by
  cell volume and optionally separated into low/high mode diagnostics.
- `C_h(Gamma)=C(q_T)` are physical exact constraints, initially total volume
  and later component volume, centroid, or selected low modes if physically
  justified.
- `E_h(Gamma)=sigma |Gamma|_h` is the physical surface energy.  `beta` is not
  a smoothing knob for production; in the oracle it is a diagnostic
  homotopy/selector that reveals whether exact q fitting demands
  nonphysical energy growth.
- `E_ref` can be the energy of the advected/predicted interface or the best
  zero-beta projection.  Only energy differences matter.

The key forbidden replacement is:

```text
find phi such that Q_h(phi)=q_T exactly,
then compute curvature from phi.
```

That route makes every cell component of `q_T` a hard physical constraint, so
grid-scale non-geometric residuals become curvature-producing interface
features.

## Residual Semantics

Once `Gamma*` is selected, define

```text
q_phys = Q_h(Gamma*)
r      = q_T - q_phys.
```

`r` should be classified, not hidden:

| Residual property | Meaning |
|---|---|
| small norm, high-frequency, zero total volume | likely numerical off-manifold transport residue; do not feed it into capillary force |
| low-mode content or nonzero constrained moments | the projection is erasing physical motion; chart or constraints are wrong |
| localized near topology change or wall contact | chart validity or boundary-state problem |
| grows step by step | transport/projection is not tangent to the interface manifold |
| correlated with curvature-force spikes | non-geometric q modes are being converted into capillary work |

The capillary force must be built from `Gamma*`, not from `r`.  The residual
can trigger fail-close or redesign if it exceeds a declared budget, but it is
not a hidden damping term.

## Constraint Ladder

Do not jump directly to all-cell `Q_h(Gamma)=q_T`.  Use this ladder:

| Level | Exact constraints | Purpose |
|---|---|---|
| L0 | total volume only | prove the chart and energy variation are coherent |
| L1 | component volumes | handle separated material components |
| L2 | volume + centroid/low modes | preserve physical large-scale motion when supported by diagnostics |
| L3 | selected interface modes | preserve validated wave/deformation modes |
| L4 | all-cell q | allowed only as a falsification probe, not as the default physics |

If L4 succeeds only by raising energy, roughness, or force high modes, the
correct conclusion is not "increase projection iterations."  It is
"`q_T` contains non-geometric components for this chart/metric."

## Graph-Chart Oracle Specification

The next implementation unit should extend the validated graph oracle with an
off-manifold `q_T` input.

Start from a smooth graph:

```text
eta_0(x) = h0 + A cos(kx)
q_0      = Q_h(eta_0)
```

Construct controlled perturbations:

```text
q_T = q_0 + eps_low r_low + eps_high r_high
```

where:

- `r_low` is representable by a graph mode, such as another cosine component;
- `r_high` is a zero-total-volume checkerboard or localized cell residual that
  is not expected to be graph-representable without roughness.

Then solve for `eta*` under the constraint ladder and report:

```text
q_phys = Q_h(eta*)
r      = q_T - q_phys
E[eta*]
mode amplitudes of eta*, q_phys, and r
force sign from delta E/delta eta*
roughness / high-mode indicator
```

Expected outcomes:

| Case | Expected result | Falsifies |
|---|---|---|
| clean `q_0` | `eta* ~= eta_0`, `r ~= 0`, force sign unchanged | oracle implementation or metric bug |
| low-mode `q_T` | `eta*` absorbs the physical low mode, `r` remains small | overly restrictive chart/constraint |
| high-mode `q_T` | `eta*` stays smooth, `r` captures high-frequency residue | all q modes are physical |
| forced all-cell q on high-mode `q_T` | energy/roughness/force high modes grow | exact q should be default |

Visualization is required: `eta_0`, `eta*`, `q_T`, `Q_h(eta*)`, `r`, energy
sweep, and mode spectra.

## Quick Graph-Chart Validation

Implemented:

```text
experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Remote-first validation command:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Result: PASS.  The run saved:

```text
experiment/ch14/results/diagnose_q_manifold_projection_oracle/data.npz
experiment/ch14/results/diagnose_q_manifold_projection_oracle/q_manifold_projection_oracle.pdf
```

This oracle uses a low-mode graph chart for `eta*`.  It projects `q_T` by
matching column-volume modes, then defines:

```text
r = q_T - Q_h(eta*).
```

The three synthetic cases behaved as the theory predicts:

| Case | `residual_l2` | `residual_column_linf` | `eta_delta_linf` | `force_sign_product` | Verdict |
|---|---:|---:|---:|---:|---|
| clean | `1.262190153575e-16` | `3.552713678801e-15` | `7.216449660064e-16` | `-2.312348084758e-01` | clean `Q_h(eta)` lies on `M_h` |
| low_mode | `1.578050209727e-16` | `3.552713678801e-15` | `4.440892098501e-16` | `-2.199623647695e-01` | representable low mode is absorbed into `eta*` |
| high_residual | `1.381067932005e-04` | `3.553364200104e-15` | `7.216449660064e-16` | `-2.312348084758e-01` | zero-column cell-scale residue remains in `r`, not in `eta*` |

The key point is that the high-residual case preserves column volume to
roundoff and leaves the smooth graph unchanged, while `r` remains visible in
the cell field.  This is exactly the desired separation:

```text
physical graph modes -> Gamma*
non-geometric cell modes -> r
```

This is still a graph-chart smoke test, not a production runtime admission.
The next required validation is the same residual classification in the
closed-curve chart.

## Closed-Curve Extension

After the graph projection oracle passes, repeat the same decomposition for
the mode-2 closed curve from `CHK-RA-CH14-VAR-005`:

```text
X(theta) = c + R(1 + eps cos(2 theta)) (cos theta, sin theta)
q_T      = Q_h(X) + r
X*       = projection of q_T onto M_h(closed curve)
```

The exact constraints start with area and component identity.  A successful
closed chart must show that the graph and closed-curve charts share the same
residual semantics:

```text
physical low modes -> interface motion
non-geometric cell modes -> residual r, not capillary force
```

## Runtime Implication

The eventual runtime step should not be:

```text
transport q
-> rebuild phi exactly matching q
-> compute force from phi
```

It should be:

```text
transport/predict Gamma_h or a chart-tangent measure
-> derive q_T
-> project q_T to Gamma* on M_h with physical constraints
-> record r = q_T - Q_h(Gamma*)
-> compute surface-energy variation from Gamma*
-> convert work to the same face/pressure metric
```

If `r` is large, the step is not physically admitted.  The response is to
redesign the transport or chart, not to weaken q/phi tolerance.

## Acceptance Before Any T/8 Run

The following must pass before a Ch14 T/8 oscillating-droplet run:

1. graph projection oracle distinguishes representable low modes from
   non-geometric high modes;
2. closed-curve projection oracle passes the same residual classification;
3. a short runtime probe records pre-projection `q_T`, projected
   `Q_h(Gamma*)`, residual `r`, surface energy, force mode/sign, pressure
   reaction, and face-space boundary residual;
4. no production route consumes `r` as curvature or force.

Until these are true, T/8 failure would not identify a physical capillary
problem; it would only mix transport, reconstruction, force, and projection
errors again.
