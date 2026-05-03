# CHK-RA-OSC-N64-013 — Problem Shortcut Hypothesis Map

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Theory Anchor

For a static circular droplet, the continuum equilibrium is

```text
u = 0,
p_l - p_g = sigma / R = 0.288,
kappa_lg = 1 / R = 4,
d_t psi = 0.
```

The discrete production path must therefore make the following loop neutral:

```text
Young-Laplace jump -> phase-separated affine PPE -> projected velocity
-> interface transport -> curvature at Gamma -> Young-Laplace jump.
```

Any nonzero discrete work around this loop is a root bug.  A smaller timestep,
stronger smoothing, or alpha tuning is not a root fix unless it restores one of
these mathematical contracts.

## Hypothesis Ledger

| ID | Hypothesis | Test / evidence | Verdict |
|---|---|---|---|
| H01 | Original N64 droplet is too small for period-one alpha-4 capillary physics | CHK-002: larger drops, lower sigma, alpha2, uniform grid, sigma0 controls | Supported for the initial small-ellipse blowup, not sufficient after resizing |
| H02 | Static-size ellipse removes the issue | CHK-003 reached `t=0.9495` but blew up before `T=1.5` | Falsified as complete fix |
| H03 | Elliptic Rayleigh-Lamb motion is the sole cause | CHK-004 static circle with same alpha4 route also blew up | Falsified |
| H04 | Alpha-4 fitted-grid concentration is a strong amplifier | CHK-004 alpha4 static failed; CHK-005 alpha2 static completed `T=1.5` | Supported as amplifier |
| H05 | Pressure oscillation is only gauge/color/plot artifact | CHK-006 phasewise residuals and jump reversal persisted in raw NPZ | Falsified |
| H06 | Volume drift or large deformation is primary | CHK-006/009: small radius/deformation errors while pressure/curvature residuals large | Falsified |
| H07 | Dynamic grid rebuild alone causes the pressure oscillation | CHK-009 static-grid improved but still had cut-face `kappa` std `7.716` | Falsified as sole cause |
| H08 | Missing ridge-eikonal reinit causes curvature noise | CHK-009 reinit every 20 worsened `m16`/cut-face `kappa` | Falsified for this route |
| H09 | Base-pressure vs physical-pressure storage mismatch drives PPE/projection | CHK-009 pressure-variable diagnostic differences were exactly `0.0` | Falsified |
| H10 | Plain previous-pressure gradient crossing the jump is the root fix | CHK-007 no-prev-gradient reduced KE but destroyed the pressure jump; CHK-008 retained-code retry worsened | Falsified as fix; still an injection path |
| H11 | Curvature denominator `|grad psi|` collapses at cut faces | CHK-010 final min cut-face `|grad psi|=8.284` while `kappa` std large | Falsified |
| H12 | Direct cut-face derivative `kappa_Gamma` reconstruction fixes noise | CHK-011 direct cut-face std `23.25` vs current `10.67` | Falsified |
| H13 | Naive ordered three-point geometric curvature fixes noise | CHK-011 geometric mean/std `15.33/10.80` | Falsified |
| H14 | Stronger curvature filter is a root fix | CHK-011 `C=0.10` reduced std but biased mean and grew `m32` radius noise | Falsified as root; partial symptom control |
| H15 | Curvature evaluator explodes even if `psi` is fixed | CHK-012 frozen interface kept cut-face mean/std `4.002/0.0166` | Falsified |
| H16 | Interface transport feedback is required for the instability | CHK-012 frozen interface removed growth | Strongly supported |
| H17 | Reconstructed nodal transport velocity breaks the projection-native face flux contract | CHK-013 face-native transport control reduced final cut-face `kappa` std from `10.67` to `1.86` and radius std from `5.54e-4` to `9.05e-5` | Leading root-cause shortcut |

## New Diagnostic

Extended `experiment/ch14/diagnose_curvature_contract_n64.py` with
`--face-native-transport`.  This diagnostic does not change production code.
It replaces the interface update by the projection-native conservative flux

```text
d_t psi = -D_f(psi_f u_f),
```

where `u_f` is the projected face velocity retained by the existing
`canonical_face_state` path.

Run:

```bash
make cycle EXP=experiment/ch14/diagnose_curvature_contract_n64.py ARGS="--face-native-transport"
```

## Final-Step Comparison at T=0.40

| case | band `kappa` std | cut-face `kappa` mean | cut-face `kappa` std | radius std | `m16` amp | `m32` amp | min `|grad psi|` |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline nodal transport | `2.164945e+01` | `3.231471e+00` | `1.066869e+01` | `5.540336e-04` | `2.238773e-04` | `1.075945e-04` | `8.284201e+00` |
| face-native transport | `4.626660e+00` | `4.185362e+00` | `1.855280e+00` | `9.048645e-05` | `2.447892e-05` | `3.323451e-05` | `1.010415e+01` |
| frozen interface | `1.019542e+00` | `4.002476e+00` | `1.659596e-02` | `2.320123e-05` | `6.396132e-06` | `5.227498e-06` | `1.048392e+01` |

## Inference

The fastest path to the root is not another curvature formula.  The evidence
points to a discrete transport/projection contract error:

1. the affine PPE/projection produces a nearly divergence-free face velocity;
2. the solver reconstructs that face velocity to nodes;
3. direct-psi FCCD transport builds a new flux from nodal velocities;
4. this regenerated flux is not the same projection-native flux, so static
   equilibrium acquires a small but persistent interface motion;
5. curvature amplifies that motion into an oscillatory Young-Laplace jump.

The face-native diagnostic fixes most of the growth without freezing the
interface, which means the transport velocity placement is a dominant causal
link.  Because face-native transport still leaves `kappa` std `1.86` rather than
the frozen-interface `0.0166`, the complete root fix must also audit remaining
sources: predictor history gradient, BDF/IPC temporal consistency, and grid
remap/history reset after dynamic rebuild.

## Next Root-Fix Unit

Implement and test a production-quality projection-native interface transport
contract, not as a damping workaround:

```text
Equation: d_t psi + div(psi u) = 0, div u = 0
Discretization: psi^{n+1} = TVD-RK3[-D_f(P_f psi * u_f^proj)]
Code: transport consumes retained projected face components directly
Verification: static Young-Laplace N64 alpha2 cut-face kappa/std and pressure
              residual stay near frozen-interface levels through T=0.40
```

[SOLID-X] Diagnostic extension only; no production solver/operator boundary
changed, no tested implementation deleted, and no damping/CFL/smoothing
workaround adopted as a fix.
