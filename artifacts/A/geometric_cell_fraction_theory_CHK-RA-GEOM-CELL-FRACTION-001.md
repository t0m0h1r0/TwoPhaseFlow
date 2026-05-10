# CHK-RA-GEOM-CELL-FRACTION-001

## Purpose

User request:

> Establish the theory toward geometric cell fractions.  Clarify the root
> problem from physics and mathematics, generate many solution ideas, and
> verify them to choose a direction.  Theory first; no tactical patching.

This note treats "geometric cell fraction" as a reformulation of the
discrete phase space, not as an output-format or visualization change.

## Paper-Based Starting Point

The paper currently defines CLS through two roles:

```text
psi = H_eps(-phi) in [0,1]        conservative transported indicator
phi                               geometry gauge for normals/curvature
```

Chapter 3 states that the conserved quantity is

```text
V_CLS = integral_Omega psi dV,
psi_t + div(psi u) = 0.
```

This is a good answer to the classical non-conservative level-set mass-loss
problem.  It is not, however, the same object as the sharp physical liquid
volume

```text
V_sharp = |Omega_l|,
Omega_l = { x : phi(x) < 0 }.
```

For a smooth diffuse profile these two are asymptotically close, but they are
not identical at fixed grid resolution.  Reinitialization, capillary pressure
jumps, and common-flux momentum are sensitive to this distinction because each
uses the phase volume as a constraint or as a mass carrier.

## Root Problem

The present theoretical conflict is a mismatch of discrete measures:

```text
1. Sharp geometry measure:
   V_h^Gamma(phi_h) = |Omega_{l,h}(phi_h)|.

2. CLS diffuse/nodal measure:
   V_h^psi(psi_h) = sum_nodes psi_i W_i.

3. Conservative material measure needed by common-flux dynamics:
   V_h^mat(q_h) = sum_control q_i W_i, with rho(q), momentum, and checkpoints
                  built from q.
```

When these are treated as interchangeable, the numerical method is asked to
preserve two or three different volumes simultaneously.  That is not a
stability issue; it is a false constraint set.  The earlier
`sharp_phase_volume` Ridge--Eikonal fail-close is the cleanest symptom:

```text
fix sharp interface volume by moving phi,
then keep the sharp interface fixed while restoring nodal diffuse mass.
```

For a fixed zero set, changing only the diffuse profile width has a bounded
mass image.  If the old nodal mass lies outside that image, the constraint set
is empty.  Fail-close is therefore mathematically correct.

Geometric cell fractions are attractive because they can make the sharp
geometry measure and the conservative material measure the same discrete
functional:

```text
F_C(phi_h) = |C cap Omega_{l,h}(phi_h)| / |C|,
V_h^G(F)   = sum_C |C| F_C
           = |Omega_{l,h}(phi_h)|
           = V_h^Gamma(phi_h).
```

The target is not "better area estimation".  The target is a single physical
volume functional shared by phase transport, density, momentum, capillary
constraint, reinitialization/retraction, checkpoint/restart, and diagnostics.

## Manufactured Verification: Why Cell Fractions Matter

A paper-level manufactured probe was run independently of production code:

1. define an ellipse on a uniform square mesh;
2. reconstruct the P1/marching-squares liquid polygon in every cell;
3. compute `F_C = polygon_area / cell_area`;
4. compare `sum_C F_C |C|` with the sharp geometric area;
5. compare both against a nodal Heaviside control-volume mass.

Representative output:

```text
N   offset                geom_volume     cell_fraction_volume err_fraction nodal_volume    nodal-geom
16  +0,+0                 1.900094440e-01 1.900094440e-01      +0.000e+00   1.992187500e-01 +9.209e-03
32  +0,+0                 1.933617392e-01 1.933617392e-01      +0.000e+00   1.943359375e-01 +9.742e-04
64  +3.59e-3,-2.66e-3     1.941236187e-01 1.941236187e-01      +0.000e+00   1.950683594e-01 +9.447e-04
128 +3.20e-3,+2.42e-3     1.943205777e-01 1.943205777e-01      +0.000e+00   1.945800781e-01 +2.595e-04
```

Interpretation:

- geometric cell fractions satisfy the sharp-volume identity exactly, up to
  floating-point roundoff, because they are the local decomposition of the
  same reconstructed set;
- nodal Heaviside/control-volume mass is a different quadrature and can differ
  by translation-dependent errors even on the same grid;
- therefore a solver that constrains sharp volume but transports nodal `psi`
  is not enforcing a single volume law.

This verifies the central theorem:

```text
Geometric cell fractions are not an optional postprocess.  They are the
minimal representation that can make sharp geometry volume and conservative
finite-volume material volume identical.
```

## Physical and Mathematical Constraints to Preserve

Any admissible geometric-fraction scheme must preserve or explicitly account
for the following contracts.

### C1. Material Volume

For closed walls or periodic boundaries:

```text
sum_C |C| F_C^{n+1} = sum_C |C| F_C^n
```

except for declared phase-change/source terms.  This is the primary physical
law for incompressible immiscible phases.

### C2. Bound and Realizability

```text
0 <= F_C <= 1
```

and each mixed-cell value must correspond to a realizable subcell liquid set.
Clipping after the fact is not a proof of realizability because it can destroy
flux conservation and momentum consistency.

### C3. Shared Geometry for Volume and Surface Energy

The same reconstructed interface must define:

```text
V_h^G(F or phi),
S_h(interface),
dS_h, dV_h,
pressure-jump volume Lagrange multiplier.
```

If capillary force uses a surface different from the volume constraint, static
Young--Laplace balance cannot be exact in the discrete Hodge sense.

### C4. Common-Flux Material and Momentum Transport

For density ratio problems, phase mass and momentum must use the same phase
flux:

```text
F_m = rho_g F_V + (rho_l-rho_g) F_F,
F_p = F_m u_up.
```

The phase flux `F_F` must be the geometric liquid volume swept through a face,
not a separately interpolated smooth indicator if geometric fractions are the
physical carrier.

### C5. Pressure and Boundary Hodge Compatibility

The face mass metric and pressure projection must use densities derived from
the same cell fractions:

```text
rho_C = rho_g + (rho_l-rho_g) F_C,
M_f   = Q_f rho_f(F).
```

Wall/no-slip and periodic quotient constraints must be imposed on the same
face-state space that transports the geometric phase mass.

### C6. Reinitialization as Geometry Gauge, Not Mass Repair

Once `F_C` is the physical material volume, reinitialization of `phi` cannot
silently change `F_C`.  It may:

1. reconstruct a distance/gauge field from the interface geometry;
2. improve normals and curvature;
3. report geometric quality defects.

It must not become an unrecorded material remap.

### C7. Nonuniform Mesh Geometry

All cell volumes, polygon areas, face apertures, and swept volumes must be
computed in physical coordinates.  Uniform-grid formulas are not admissible on
fitted/nonuniform grids.

### C8. Topology and Ambiguity

Ambiguous cells, topology changes, wall-contact changes, and periodic cuts
need an explicit geometric contract.  If the chosen reconstruction cannot make
a unique physically admissible geometry, the solver should fail close or enter
a declared topology-handling route, not guess silently.

## Hypotheses and Verification Strategy

| Hypothesis | Broken law/contract if true | Efficient verification |
|---|---|---|
| H1: current volume failures come from measure mismatch | C1/C3 | manufactured P1 area vs nodal mass vs cell fraction identity |
| H2: sharp reinit fail-close is an empty constraint set | C1/C6 | fixed-zero-set feasible interval probe for profile mass |
| H3: cell fraction as diagnostic only will not fix dynamics | C4/C5 | one-step common-flux mass/momentum ledger using nodal q vs cell F |
| H4: cell fractions from phi after non-geometric transport are not conservative | C1 | translate/deform interface with known divergence-free velocity and check volume flux balance |
| H5: local PLIC can match any `F_C` but may break global surface continuity | C3/C8 | static circle Young--Laplace Hodge residual with per-cell PLIC surface |
| H6: using phi surface with transported F creates two geometries | C3 | compare `sum F_C |C|` and `V_h^Gamma(phi)` after transport/reinit |
| H7: face fluxes need swept geometry, not face interpolation | C1/C4 | one-cell and two-cell exact-translation tests |
| H8: nonuniform grid formulas can fake volume conservation | C7 | repeat manufactured cell-fraction identity on stretched physical cells |
| H9: periodic image planes can double-count fractions or face fluxes | C1/C5 | periodic quotient volume and face-flux cancellation probe |
| H10: wall-contact reconstruction can create forbidden contacts | C8 | no-slip wall contact trace invariant probe |
| H11: CCD/FCCD high-order derivatives should not differentiate discontinuous `F` | C3/C5 | smooth-field derivative tests separated from fraction transport tests |
| H12: capillary force must be the variational derivative of the same surface | C3 | static droplet zero Hodge residual, nonconstant-curvature release nonzero residual |

The cheapest decisive sequence is:

1. manufactured geometry identity: `sum F_C |C| = V_h^Gamma`;
2. exact translation advection: geometric flux preserves `sum F_C |C|`;
3. static circle: pressure jump balances the same `dS_h`/`dV_h`;
4. oscillating/curved interface: nonconstant curvature produces nonzero
   capillary drive;
5. high-density common-flux one-step: mass and momentum fluxes share `F_F`;
6. nonuniform/periodic/wall quotient probes.

Only after these pass should long chapter-14 runs be used.

## Candidate Ideas

### A. Geometric Fraction as a Diagnostic Only

Define `F_C = |C cap Omega(phi)|/|C|` for reporting, but keep transporting
nodal `psi`.

Verdict: reject as production.  It will make plots and diagnostics cleaner but
does not remove the two-volume problem.  It is useful as a probe and migration
aid only.

### B. Phi-Primary Geometry, Recompute `F_C = G(phi)` After Every Retraction

Use `phi` as the only state and define cell fractions from it whenever density
or volume is needed.

Strength: exact identity `sum F_C |C| = V_h^Gamma(phi)`.

Weakness: unless `phi` transport itself is conservative in the geometric sense,
mass conservation is not guaranteed.  This returns to the standard LS
weakness, merely with a better volume quadrature.

Verdict: admissible only if paired with a geometric conservative transport of
the interface.  Not enough by itself.

### C. Cell-Fraction-Primary Geometric VOF with Level-Set Gauge

Make `F_C` the material state.  Transport it by finite-volume geometric swept
fluxes.  Reconstruct a level-set gauge `phi` from the reconstructed interface
for normals, curvature, HFE, and visualization.

```text
primary:  F_C, m_C(F), p_C or face momentum state
geometry: interface R_h(F, optional phi normals)
gauge:    phi = signed_distance(R_h)
```

Strength:

- exact material volume conservation;
- natural common-flux mass/momentum coupling;
- compatible with pressure and gravity variational ledgers;
- reinitialization becomes gauge reconstruction, not mass repair.

Risk:

- reconstruction quality controls capillary accuracy;
- local PLIC surfaces may be discontinuous;
- needs a careful `F -> interface -> phi` map.

Verdict: strongest production direction.

### D. Coupled CLSVOF: Transport Both `F_C` and `phi`, Project to Compatibility

Transport `F_C` conservatively and `phi` with a high-order level-set method.
After each step, enforce compatibility:

```text
F_C is hard,
phi is adjusted/reconstructed so G(phi) matches F_C or matches the same
interface reconstruction.
```

Strength: keeps level-set smooth geometry while preserving volume.

Risk: compatibility projection is the core algorithm, not a small correction.
If it only enforces global volume, local cell fractions can still disagree.

Verdict: promising if the hard invariant is local/geometric, not merely global.
This is the most natural bridge from the current paper's CLS narrative.

### E. PLIC with Level-Set Normals

Use normals from `phi` or its filtered/CCD derivatives, then choose the line
intercept in each mixed cell so that the cut volume equals `F_C`.

Strength:

- any `F_C in [0,1]` is locally realizable;
- exact local volume;
- simple GPU table route in 2D.

Risk:

- cellwise segments need not form a continuous global curve;
- curvature from raw PLIC normals is noisy unless the level-set gauge is
  reconstructed consistently.

Verdict: likely the right first reconstruction primitive, but not the final
capillary geometry by itself.  Pair with a distance/gauge reconstruction.

### F. Moment-of-Fluid / Centroid-Enriched Fractions

Store `F_C` plus phase centroid or first moments.

Strength: better reconstruction uniqueness and curvature quality.

Risk: larger state, harder fluxing, more checkpoint/API impact.

Verdict: valuable later if PLIC+phi gauge is insufficient.  Too large for the
first theoretical migration.

### G. THINC/Algebraic Cell Fraction

Use an algebraic hyperbolic-tangent reconstruction per cell.

Strength: GPU-friendly and conservative.

Weakness: not a geometric cell-fraction method unless its integrated cell
volume is the actual conserved `F_C` and its surface/volume variations are used
consistently.  Otherwise it reintroduces a diffuse-volume measure.

Verdict: keep as separate candidate, not the base for geometric cell fraction.

### H. Global Normal-Offset Retraction

After reinitialization, solve one scalar offset so global volume is exact.

Strength: good theorem under current CLS state.

Weakness: only global volume; no cell-local geometric conservation; still not
a geometric VOF state.

Verdict: acceptable intermediate for current architecture, but not the target
of geometric cell fraction.

### I. Lagrangian Front Tracking plus Eulerian Fractions

Track an explicit interface and rasterize cell fractions.

Strength: accurate geometry and topology control when remeshing succeeds.

Risk: very large architectural change; topology changes and GPU data structure
complexity are high.

Verdict: not the near production route, but useful as a conceptual reference.

### J. Cut-Cell / Aperture State

Store not only cell fractions but also face apertures and interface lengths in
each cell.

Strength: pressure jump, fluxes, and capillary surface can use a shared
geometric complex.

Risk: more state and consistency constraints.

Verdict: likely necessary in mature form.  Start with cell fractions and derive
apertures from the same reconstruction.

## Extracted Direction

The mathematically correct target is:

```text
State:
  F_C        geometric liquid cell fraction
  m_C        material mass from F_C
  p or u_f   momentum/face velocity in the common-flux pressure-Hodge space
  phi        reconstructed distance/gauge, not the material volume carrier

Geometry operator:
  R_h(F_C, phi_gauge) -> interface complex I_h

Invariants:
  V_h(F) = sum_C |C| F_C
  S_h    = surface measure of I_h
  capillary/gravity/pressure work use the same F_C, I_h, M_f(F).
```

The first implementation-grade theoretical route should be a coupled
geometric CLSVOF route:

1. `F_C` is the hard conservative variable.
2. `phi` is a smooth gauge reconstructed from `F_C` and/or transported as a
   predictor.
3. PLIC/cut geometry with level-set normals reconstructs the per-cell
   interface and matches `F_C` exactly.
4. Face swept-volume fluxes update `F_C`.
5. Common-flux density and momentum use the same phase flux.
6. Capillary force is derived from the same reconstructed surface and volume
   constraint, not from a separate smoothed `psi` field.

This preserves the paper's motivation for CLS -- separate mass conservation
from geometric quality -- but changes the mass carrier from diffuse nodal
`psi` to geometric cell fraction `F_C`.  In paper language:

```text
old: psi is both conservative indicator and diffuse geometry profile;
new: F_C is conservative material volume, phi is geometry gauge.
```

## UX/YAML Implications

The YAML must make the representation explicit.  Silent switching between
diffuse and geometric volumes would recreate the bug.

Candidate contract:

```yaml
interface:
  representation:
    carrier: geometric_cell_fraction
    geometry_gauge: level_set
    reconstruction: plic_levelset_normal
    volume_measure: cell_fraction
    surface_measure: reconstructed_interface
  transport:
    phase_flux: geometric_swept_volume
    common_flux_momentum: true
  reinitialization:
    role: geometry_gauge_only
    hard_volume_constraint: cell_fraction
```

Rejected UX:

```yaml
volume_constraint: sharp_phase_volume
```

when the transported state is still nodal/diffuse `psi`.  That flag hides
which mass measure owns density and momentum.

## GPU-First Implementation Notes

The geometry route is GPU-suitable if expressed as table-driven cell-local
kernels:

- case-id per cell from corner signs or local PLIC state;
- branchless/table PLIC intercept and area formulas in 2D;
- face swept-volume formulas as vectorized per-face kernels;
- reductions only for diagnostics and global volume checks;
- no Python per-cell loops in production;
- periodic quotient and wall masks precomputed;
- host transfers reserved for fail-close diagnostics and output.

The smooth `phi` reconstruction can be more expensive, but it is a gauge
operation.  It should be scheduled and certified separately from conservative
transport.

## Negative Knowledge

The following must not be accepted as the geometric cell-fraction fix:

- making only plots use geometric fractions;
- adding a global mass correction after non-geometric transport;
- preserving sharp volume and diffuse nodal mass as independent hard
  constraints;
- clipping cell fractions without a conservative flux ledger;
- using geometric `F_C` for density but diffuse `psi` for capillary or gravity;
- differentiating discontinuous `F_C` with CCD/FCCD as if it were a smooth
  field;
- treating THINC or anti-diffusion CLS as geometric without a shared surface
  and volume functional;
- using long-run visual stability as proof before manufactured geometry,
  one-step flux, and static Hodge gates pass.

## Decision

Proceed toward geometric cell fractions as a state-space reformulation:

```text
Hard physical volume:
  V_h = sum_C |C| F_C.

Geometry:
  reconstructed cell/face interface complex I_h.

Gauge:
  level-set phi reconstructed from I_h for normals, curvature, HFE, and plots.

Transport:
  geometric finite-volume swept fluxes, shared by phase mass and momentum.

Capillarity:
  variational derivative of S_h(I_h) paired with the same V_h and pressure
  Hodge metric.
```

The immediate theoretical work before source implementation is to specify the
operator triple:

```text
G_h: phi or local PLIC state -> F_C, I_h
T_h: face velocity -> geometric swept-volume phase flux
R_h: F_C plus gauge normals -> compatible interface and phi gauge
```

and to prove the gates:

```text
sum F_C |C| equals interface volume,
geometric flux is conservative and bounded,
static Young--Laplace balance uses the same dS_h/dV_h pair,
common-flux momentum uses the same phase flux,
nonuniform/periodic/wall geometry is counted once in physical coordinates.
```
