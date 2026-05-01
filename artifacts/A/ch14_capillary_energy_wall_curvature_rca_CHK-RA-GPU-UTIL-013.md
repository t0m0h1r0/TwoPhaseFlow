# CHK-RA-GPU-UTIL-013 — Capillary energy instability RCA after wall topology fix

Date: 2026-05-01
Scope: `experiment/ch14/config/ch14_capillary_n32_t25.yaml`, `schedule=1`,
no-slip wall topology fixed, remaining capillary/curvature energy failure

## Conclusion

The remaining N=32, T=25 capillary-wave failure is not a wall-contact drift
problem.  The wall phase topology now remains fixed:

```text
side-wall crossing count max = 1
first extra crossing = None
pinned branch drift = 0.0
```

The failure is a capillary-energy instability.  The sharpest identified cause
is the wall-contact curvature closure on the non-uniform fitted grid:

```text
bulk graph curvature at t≈0        ≈ 1.50
expected mode-2 curvature amplitude ≈ 1.58
runtime nodal curvature near wall   ≈ O(10^2)
```

The huge curvature is localized at the side-wall contact neighborhoods.  It is
then clipped by `kappa_max=5` from the first step, converted into an affine
pressure-jump face source by nodal averaging, and inserted into the PPE/corrector
without a discrete surface-energy identity.  This creates a high-frequency
capillary pressure defect that eventually drives the balanced-force residual,
PPE RHS, divergence, and kinetic energy upward.

The theory-level root is therefore:

> the current capillary operator uses a bulk nodal curvature formula and
> nodal-band affine jump at no-slip wall contact points, but the correct
> continuum problem requires a wall-compatible interface/cut-face geometry
> closure whose work is the negative variation of the same discrete surface
> energy.

Lowering CFL, raising/lowering the curvature cap, adding smoothing, or relaxing
the wall topology would only mask this violation.

## Physical judges

For gravity-free capillary flow in a stationary no-slip box,

```math
{d\over dt}\left[
  \int_\Omega {1\over 2}\rho |u|^2\,dV
  + \sigma |\Gamma|
\right]
= -\int_\Omega 2\mu |D(u)|^2\,dV \le 0,
```

up to discretization error.  A no-slip wall performs no work because the wall
velocity is zero.  If a contact-line law is absent, the wall contact root is a
constraint and the wall reaction balances endpoint forces; it is not a source of
bulk capillary work.

For the small-amplitude mode `η=A cos(4πx)`, the correct first response is
restoring:

```text
ω = 0.3777640482251637
theory A'' ≈ -1.48e-3 for A≈0.01037
observed six-snapshot fit A'' = -1.043e-3
```

So the gross Young--Laplace sign is no longer reversed.  The failure is
high-frequency energy injection, not first-mode anti-surface-tension.

## Current T25 ordering

From `experiment/ch14/results/ch14_capillary_n32_t25/data.npz`:

| event | first step/time |
|---|---:|
| `bf_residual_max > 1e2` | step 2061, `t=16.282054` |
| `div_u_max > 1e-3` | step 2216, `t=17.809493` |
| `KE > 1e-2` | step 2589, `t=21.186098` |
| advective limiter active | step 2629, `t=21.533767` |
| `volume_drift > 1e-2` | step 3437, `t=22.467996` |
| BLOWUP | step 3801, `t=22.4868` |

Thus volume drift and advective CFL collapse are downstream.  The first clear
large defect is the capillary/BF residual.

Snapshot-derived capillary energy proxy:

| t | length proxy | `σ(L-L0)` | KE | proxy total |
|---:|---:|---:|---:|---:|
| 0.006 | 1.004345 | 0.000000e+00 | 1.57e-09 | 1.57e-09 |
| 7.505 | 1.018779 | 1.039245e-03 | 5.51e-04 | 1.59e-03 |
| 10.007 | 1.068375 | 4.610184e-03 | 1.32e-03 | 5.93e-03 |
| 12.506 | 1.205312 | 1.446968e-02 | 2.36e-03 | 1.68e-02 |
| 17.506 | 1.285464 | 2.024057e-02 | 3.43e-03 | 2.37e-02 |
| 22.001 | 1.095806 | 6.585227e-03 | 1.47e+01 | 1.47e+01 |

This violates the expected capillary-plus-kinetic non-increase well before the
final numerical blow-up.

## Decisive wall-curvature test

Initial-state local reconstruction, after the fitted non-uniform grid is built
and before long-time dynamics:

```text
alpha=2, ψ-direct filtered curvature:
  all interface-band nodes: max |κ| = 321.500154109521
  excluding 1 boundary layer: max |κ| = 9.362311357161484
  excluding 2 boundary layers: max |κ| = 1.753759757961492
  excluding 3 boundary layers: max |κ| = 1.5730556851906494

alpha=1, same initial field:
  all interface-band nodes: max |κ| = 1.5794215626819328
```

Legacy logit curvature shows the same pattern:

```text
alpha=2, legacy filtered curvature:
  all interface-band nodes: max |κ| = 340.18837766055856
  excluding 1 boundary layer: max |κ| = 9.633622958275087
  excluding 2 boundary layers: max |κ| = 1.789860301912876
```

The largest `ψ`-direct filtered values are at the side-wall contact
neighborhoods:

```text
x=0.0, y=0.4812539889495609, ψ=0.6482447511009488, κ=-321.500154109521
x=1.0, y=0.4812539889495609, ψ=0.6482447511009488, κ=-321.5001541095159
x=1.0, y=0.5380162790939310, ψ=0.3552154846890924, κ=-57.58877272501764
x=0.0, y=0.5380162790939310, ψ=0.3552154846890924, κ=-57.588772725014294
```

Therefore the curvature cap being saturated from the first output is not caused
by the physical capillary-wave curvature; it is caused by the non-uniform
wall/contact curvature closure.

## Code-path facts

- `experiment/ch14/config/ch14_capillary_n32_t25.yaml` declares
  `curvature.method: psi_direct_filtered`.
- The current runtime still instantiates `CurvatureCalculator`, the legacy
  logit/`φ` path, in `src/twophase/simulation/ns_scheme_bootstrap.py`.
- This is a fidelity mismatch and must be fixed, but it is not the primary
  energy-instability cause because both legacy and `ψ`-direct curvature produce
  the same wall-local non-uniform spike pattern.
- `pressure_jump` is not double-counting CSF: `PressureJumpSurfaceTension`
  inherits the null force path.
- `src/twophase/coupling/interface_stress_closure.py` builds the affine jump
  face source by:
  - detecting cut faces from nodal `ψ` signs,
  - averaging adjacent nodal pressure jumps,
  - dividing by the node-to-node face distance.

That static jump closure can pass sign and manufactured-jump tests, but it is
not a proof that the dynamic work equals `-σ Δ|Γ_h|`, especially when the
adjacent nodal curvature is a wall-boundary artifact.

## Hypothesis audit

| ID | Hypothesis | Verdict | Verification |
|---|---|---|---|
| H01 | Young--Laplace sign is still reversed. | Rejected | Initial signed mode has restoring `A''=-1.043e-3`, same sign as theory. |
| H02 | T25 failure is only a diagnostic artifact. | Rejected | Reconstructed length/energy proxy grows; KE reaches blow-up. |
| H03 | Surface tension is double-counted as CSF plus affine jump. | Rejected | `PressureJumpSurfaceTension` is a null body-force strategy. |
| H04 | Wall contact topology is still moving. | Rejected | Crossing count max `1`, no extra crossings, pinned drift `0.0`. |
| H05 | Wall topology fix itself injects energy by freezing a smooth trace. | Rejected as primary | Adopted invariant fixes only phase side/contact roots; same-phase wall values and interior remain free. |
| H06 | Volume drift is the first cause. | Rejected | `volume_drift > 1e-2` occurs at `t=22.468`, after BF/div/KE growth. |
| H07 | Advective CFL failure is the first cause. | Rejected | Advective limiter activates after `KE>1e-2` and long after BF residual growth. |
| H08 | PPE/DC low-order solver choice is primary. | Rejected | The earliest large defect is capillary/BF source; FD direct DC path is already factorized and stable in solver tests. |
| H09 | Curvature cap causes the failure alone. | Contributor | Cap is saturated from first output, but the cap is triggered by a prior wall-curvature spike. |
| H10 | Bulk curvature formula is globally wrong. | Rejected | Excluding two wall layers gives `max |κ|≈1.75`, close to expected `≈1.58`. |
| H11 | Runtime ignores `psi_direct_filtered`. | Confirmed secondary | YAML says `ψ`-direct; runtime uses legacy `CurvatureCalculator`. Both exhibit the wall spike, so not primary. |
| H12 | Non-uniform fitted grid is necessary for the initial curvature spike. | Supported | `alpha=1` all-band max `1.58`; `alpha=2` all-band max `321.5`. |
| H13 | No-slip wall-contact curvature closure is missing. | Accepted primary | Spikes localize at side-wall contact neighborhoods and vanish when boundary layers are excluded. |
| H14 | Affine jump uses nodal/band curvature instead of interface/cut-face quadrature. | Accepted structural cause | Face source averages adjacent nodal jumps; no discrete area variation identity exists. |
| H15 | Reinitialization is the sole source. | Rejected as sole cause | Initial spike appears before long-time reinit dynamics; older controls show reinit interacts but is not sufficient. |
| H16 | Dynamic grid/remap is irrelevant. | Rejected | `alpha=2` non-uniform initial grid creates wall spike; uniform grid does not. |
| H17 | Contact angle/wetting physics is implicitly handled. | Rejected | Current wall topology fixes roots but does not provide a wall-compatible curvature/contact-angle closure. |
| H18 | Density ratio/viscosity alone causes late KE growth. | Rejected as primary | Initial capillary mode scale is correct; BF residual grows before incompressibility failure. |
| H19 | Smaller time step would be a principled fix. | Rejected as root fix | It may delay high-mode growth, but cannot restore a missing energy identity. |
| H20 | Smoothing or changing `kappa_max` would be a principled fix. | Rejected | It treats the symptom and changes Young--Laplace law instead of fixing wall/interface geometry. |

## Root cause statement

The current capillary route has two connected mathematical defects:

1. **Wall-contact curvature defect.**  A bulk nodal curvature formula is used
   at a pinned no-slip wall contact on a non-uniform fitted grid without the
   required wall/contact-angle/contact-root geometry closure.  This produces
   `O(10^2)` curvature where the physical graph curvature is `O(1)`.
2. **Non-variational affine jump defect.**  The pressure-jump face source is
   assembled from adjacent nodal curvature values rather than from a shared
   interface/cut-face geometry state whose work equals the negative variation
   of discrete surface energy.

Together they explain the observed chain:

```text
non-uniform wall-contact curvature spike
  -> kappa cap active from first step
  -> capillary jump no longer equals physical Young--Laplace curvature
  -> affine face source has high-frequency, non-variational component
  -> BF residual growth
  -> PPE RHS and divergence growth
  -> kinetic-energy blow-up
```

## Theory-first design direction

Do not repair this by tuning `kappa_max`, smoothing, CFL, or allowing wall
topology changes.  The correct design target is:

1. Construct a `CapillaryGeometryState` from a single interface geometry:
   contact roots, wall phase topology, cut-face positions, normals, curvature,
   area measure, and pressure jump.
2. At no-slip walls, provide an explicit wall-compatible closure:
   pinned contact roots plus either a stated contact-angle/wetting condition or
   a neutral/mirrored ghost geometry.  Periodic boundaries remain separate.
3. Evaluate `κ_Γ` and `J_Γ=-σκ_Γ` on interface/cut-face quadrature, not as a
   raw nodal band field at wall boundary nodes.
4. Use the same face/cut geometry in PPE RHS and corrector so that
   `G_Γ` is the adjoint-consistent capillary work operator.
5. Add an energy audit gate:
   `KE + σ(|Γ_h|-|Γ_h(0)|)` must not grow beyond a stated time-discretization
   tolerance in the gravity-free capillary-wave case.
6. Restore algorithm fidelity by making the runtime curvature strategy match
   the declared `psi_direct_filtered` path, but only as part of the
   wall-compatible geometry design; switching the class alone is insufficient.

## Paper reflection

This CHK also updates the paper to state:

- no-slip wall contact is a phase-topology invariant, not a smooth wall-trace
  value clamp;
- periodic boundaries are excluded from wall-contact topology constraints;
- bulk curvature formulas are not sufficient at no-slip wall contact endpoints
  unless a wall-compatible geometry closure is supplied.

## SOLID audit

[SOLID-X] Analysis and paper-only changes.  No production module boundary is
changed in this CHK.  The proposed future fix should isolate wall/contact
geometry in a capillary geometry service rather than distributing special cases
across PPE, reinitialization, and solver orchestration.
