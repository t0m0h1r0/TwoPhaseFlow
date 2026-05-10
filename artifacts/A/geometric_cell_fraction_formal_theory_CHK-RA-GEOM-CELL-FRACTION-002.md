# CHK-RA-GEOM-CELL-FRACTION-002

## Purpose

User request:

> First build the theory.  Whether to adopt it can be decided later.

This artifact therefore does **not** decide production adoption.  It constructs
the mathematical objects, invariants, maps, compatibility conditions, and
verification obligations required for a geometric cell-fraction formulation.

## Non-Decision Boundary

This note is a theory layer only.

It does not claim:

- that the solver should be migrated now;
- that PLIC is the final reconstruction method;
- that geometric cell fractions automatically solve capillarity;
- that the current CLS route is invalid for all purposes.

It claims only this:

```text
If geometric cell fractions are introduced as a physical volume carrier, then
the surrounding theory must be rebuilt around a single geometric finite-volume
measure.  Otherwise the old multi-measure contradiction returns.
```

## 1. Continuous Reference Problem

For an immiscible incompressible two-phase flow, let

```text
Omega_l(t)     liquid region,
Gamma(t)       boundary of Omega_l,
chi_l(x,t)     characteristic function of Omega_l,
u(x,t)         incompressible velocity,
n              interface normal.
```

With no phase change and no normal flow through physical walls,

```text
d/dt |Omega_l(t)| = 0.
```

The material law is not "a smoothed profile is preserved."  It is that the
indicator of the material region is transported:

```text
partial_t chi_l + div(chi_l u) = 0
```

in the distributional sense.  A smoothed CLS profile can approximate this, but
the physical invariant is still the sharp material volume.

Surface tension is variational:

```text
E_sigma(Gamma) = sigma |Gamma|.
```

For any admissible virtual interface displacement with normal speed `w_n`,

```text
delta E_sigma = - integral_Gamma sigma kappa w_n dS
delta V       =   integral_Gamma w_n dS.
```

Static Young--Laplace equilibrium is the stationarity of

```text
E_sigma + p0 V
```

under volume-constrained variations.  Thus the same geometric interface must
define both surface energy and volume.  This is the continuous reason the
discrete method must not mix unrelated volume and surface measures.

## 2. Discrete Geometry Primitives

Let the physical mesh be a finite-volume cell complex:

```text
C_h   cells C,
F_h   oriented faces f,
|C|   physical cell volume/area,
|f|   physical face area/length,
D_h   oriented finite-volume divergence from face fluxes to cells.
```

The discrete liquid geometry is an interface complex `I_h` that partitions
each cell:

```text
Omega_{l,h}(I_h) cap C,
Gamma_h(I_h) cap C.
```

In 2D this can be a cut segment/polygon per mixed cell.  In 3D it becomes a
cut polygon/polyhedron complex.  The exact choice is not decided here.

Define the geometric cell fraction map:

```text
A_h(I_h)_C = |C cap Omega_{l,h}(I_h)| / |C|.
```

Then

```text
0 <= A_h(I_h)_C <= 1,
V_h(I_h) = sum_C |C| A_h(I_h)_C = |Omega_{l,h}(I_h)|.
```

This identity is the key theorem.  It is true by construction if `A_h` is the
cellwise measure of the same reconstructed liquid set.

## 3. State-Space Split

The theory must separate physical state from geometry gauge.

### Physical carrier

```text
F_C in [0,1]       geometric liquid cell fraction
rho_C(F)           rho_g + (rho_l-rho_g) F_C
m_C(F)             |C| rho_C(F)
```

`F_C` is the material volume carrier.  Any solver using geometric cell
fractions must treat `sum_C |C|F_C` as the physical liquid volume.

### Gauge fields

```text
phi                signed-distance or level-set gauge
psi                optional smoothed profile for visualization or legacy bridges
```

Gauge fields may support normals, curvature, HFE, visualization, and
diagnostics.  They are not independent material-volume carriers unless a
separate theorem proves equivalence to `F_C`.

### Interface reconstruction

Because `F_C` alone does not uniquely determine a subcell interface, a
reconstruction map is needed:

```text
R_h : (F_C, g_C) -> I_h,
```

where `g_C` denotes additional geometric information: for example a level-set
normal, a transported gauge `phi`, neighborhood moments, or a chosen topology
rule.

The minimum admissibility conditions are:

```text
A_h(R_h(F,g))_C = F_C                 local volume exactness,
0 <= F_C <= 1                         realizability,
R_h respects periodic quotient        periodic consistency,
R_h respects wall-contact contract    wall consistency,
R_h is declared fail-close on ambiguity.
```

The non-uniqueness of `R_h` is not a minor detail.  It is the central
difference between "having volume fractions" and "having a capillary-ready
interface."

## 4. Geometry Gauge Compatibility

If a level-set gauge is retained, the cleanest abstract structure is:

```text
R_h(F, phi_pred) -> I_h,
Phi_h(I_h)      -> phi_gauge.
```

Here `phi_pred` can provide normals or orientation; `I_h` is the reconstructed
geometry; and `Phi_h` constructs a signed-distance or smooth gauge from `I_h`.

The compatibility condition is not merely global volume:

```text
sum_C |C|F_C = V_h(phi).
```

That is too weak.  The stronger local condition is:

```text
A_h(I_h)_C = F_C for every cell.
```

If `phi_gauge` is later used to compute a sharp volume, it should be understood
as the gauge of `I_h`, not as an independent volume owner.  Otherwise `phi` and
`F` can drift into two separate geometries.

## 5. Conservative Geometric Transport

The finite-volume update must be written in liquid volume, not in nodal
samples:

```text
|C| F_C^{n+1}
= |C| F_C^n - Delta t sum_{f in boundary C} s_{C,f} Phi_f^l.
```

`Phi_f^l` is the liquid volume flux through face `f` per unit time.  In a
geometric method it is the measure of a swept liquid region, not the product of
a face-interpolated smooth indicator with a velocity.

For an internal face shared by two cells, the same oriented flux must be used
with opposite sign.  Therefore

```text
sum_C |C| F_C^{n+1}
= sum_C |C| F_C^n
  - Delta t sum_boundary Phi_f^l.
```

Under periodic boundaries or impermeable walls, the boundary contribution is
zero.  This proves global volume conservation.

Boundedness requires more than global conservation.  A sufficient geometric
CFL-style condition is that the swept subregions used to remove liquid from a
cell are mutually disjoint subsets of the original liquid part of that cell,
and incoming swept regions fit inside the target cell.  Algebraically:

```text
0 <= outgoing_liquid_volume(C) <= |C|F_C^n,
0 <= incoming_liquid_volume(C) <= |C|(1-F_C^n) + outgoing_gas_volume(C).
```

High-order or unsplit fluxing must prove an equivalent bound.  Clipping after
the update is not the theorem; clipping is a sign that the flux construction
failed to preserve realizability.

## 6. Common-Flux Mass and Momentum

For density-ratio flows, the transported mass flux must be derived from the
same geometric phase flux:

```text
Phi_f^V     total volume flux through face f,
Phi_f^l     liquid volume flux,
Phi_f^m     rho_g Phi_f^V + (rho_l-rho_g) Phi_f^l.
```

Then a conservative momentum flux can be defined by the same mass flux:

```text
Phi_f^p = Phi_f^m u_up,f.
```

The state update is:

```text
m_C^{n+1} = m_C^n - Delta t D_h Phi^m,
p_C^{n+1} = p_C^n - Delta t D_h Phi^p,
m_C^{n+1} = |C| (rho_g + (rho_l-rho_g) F_C^{n+1}).
```

This is not optional bookkeeping.  If `F_C` updates phase mass but momentum is
updated with a different flux, the scheme creates or destroys kinetic energy
through a representation mismatch.

## 7. Pressure Hodge Compatibility

Let the pressure projection live in a face space with metric:

```text
M_f(F) = Q_f rho_f(F),
```

where `Q_f` is the face volume/area metric and `rho_f(F)` is a face density
derived from the same cell fractions and the same boundary quotient.

The projection should be an `M_f(F)`-orthogonal Hodge projection:

```text
u^{n+1} = u^* - M_f(F)^{-1} G_h p,
D_h u^{n+1} = 0,
boundary constraints.
```

For wall-bounded flows, this must be interpreted in the constrained face-state
space already developed in WIKI-T-168.  Geometric cell fractions must not
introduce a second pressure metric or a second divergence.

## 8. Capillary Variational Closure

Define the discrete surface energy from the same reconstructed interface:

```text
S_h(I_h) = |Gamma_h(I_h)|,
E_sigma(I_h) = sigma S_h(I_h).
```

The capillary covector must be the virtual work of this energy under the same
transport/reconstruction map that moves `F_C`:

```text
delta F = T_h(I_h) w_f,
delta E_sigma = <g_sigma, delta F>_C
              = <T_h(I_h)^* g_sigma, w_f>_F.
```

Then the capillary face acceleration is the Riesz representative:

```text
a_sigma = - M_f(F)^{-1} T_h(I_h)^* g_sigma.
```

The actual algebra may be implemented through interface vertices, cut segments,
or a level-set gauge.  But the theorem must remain:

```text
surface energy, volume constraint, pressure metric, and transport work all
refer to the same I_h/F_C geometry.
```

### Static Young--Laplace gate

For a discrete circle/sphere whose reconstructed interface has constant
discrete curvature in the chosen geometry, the constrained stationarity
condition is:

```text
dS_h + lambda dV_h = 0.
```

If this fails, the capillary force is not balanced by the pressure jump in the
chosen Hodge metric.  The failure cannot be patched by damping or smoothing.

### Dynamic nonconstant-curvature gate

For any nonconstant-curvature closed interface,

```text
projection of dS_h outside the pressure-volume range != 0.
```

This is the capillary drive.  A formulation that removes it by range
projection or by overconstraining volume has destroyed physical oscillation.

## 9. Reinitialization as Gauge Retraction

Under geometric cell fractions, reinitialization must be reclassified.

Old CLS view:

```text
reinit repairs psi profile, with mass correction.
```

Geometric-fraction view:

```text
F_C is the physical material volume and must not change silently.
reinit repairs only phi/psi gauge quality.
```

An admissible gauge retraction has the form:

```text
I_h       = R_h(F_C, phi_pred),
phi_new   = Phi_h(I_h),
psi_new   = H_eps(-phi_new) only if needed as a derived field.
```

The retraction must record, but not hide:

```text
A_h(I_h)-F_C local residual,
surface-energy change from gauge reconstruction,
normal/curvature quality,
topology or wall-contact changes,
kinetic lift defects if state variables are remapped.
```

Thus the earlier impossible task "preserve sharp volume and restore diffuse
nodal mass while keeping the zero set fixed" disappears because diffuse nodal
mass is no longer an independent physical invariant.

## 10. CCD/FCCD Orthogonality

Geometric cell fraction is discontinuous across the interface.  It should not
be differentiated by CCD/FCCD as a smooth scalar.

The division of labor should be:

```text
F_C              finite-volume/geometric transport and density carrier,
phi_gauge        smooth geometric derivatives, normals, HFE support,
u,p              CCD/FCCD pressure and velocity operators,
I_h              capillary surface and volume geometry.
```

This keeps CCD/FCCD valuable without asking high-order smooth operators to
differentiate a discontinuous indicator.

## 11. Nonuniform, Periodic, and Wall Geometry

### Nonuniform grid

All measures are physical:

```text
|C|, |f|, polygon areas, swept volumes, interface lengths.
```

Computational-coordinate formulas are valid only if multiplied by the correct
metric Jacobians and if the reconstruction is defined in physical space or in
a provably equivalent mapped space.

### Periodic boundary

The cell complex is a quotient.  Interface pieces and face fluxes crossing the
periodic seam must be represented once.  Image nodes/faces are implementation
devices, not additional physical cells.

### Wall boundary

No normal volume flux:

```text
Phi_f^V = Phi_f^l = 0 on impermeable walls.
```

If no slip/contact-line model is present, retraction and reconstruction must
not create new wall contact sets.  If contact-line physics is introduced, it
must enter as an explicit boundary law.

## 12. Main Risks

| Risk | Why it matters | Theoretical response |
|---|---|---|
| R1: `F_C`, `psi`, and `phi` all treated as physical phase | recreates multi-measure contradiction | declare `F_C` as material carrier; `phi/psi` are gauges unless proven equivalent |
| R2: PLIC gives local volume but discontinuous global interface | capillary curvature may be noisy/inconsistent | separate volume exactness from capillary-ready geometry; require static Hodge gate |
| R3: geometric flux not bounded | cell fractions leave [0,1] | prove swept-volume realizability before clipping |
| R4: common-flux momentum uses different mass flux | energy/momentum defects | derive `Phi_m` and `Phi_p` from same `Phi_l` |
| R5: pressure metric reads different density than transport | projection is not the Hodge projection of transported mass | define `M_f(F)` from the same `F_C` state |
| R6: reinit changes `F_C` through derived `psi` | hidden material remap | reinit is gauge-only; any `F_C` change is explicit transport/remap |
| R7: nonuniform geometry uses uniform formulas | fake conservation | all measures in physical coordinates |
| R8: periodic seam double-counts geometry | volume and flux errors | quotient-space counting and seam flux tests |
| R9: wall reconstruction creates contacts | violates boundary physics | wall-contact invariant or explicit contact model |
| R10: long-run visual stability used as proof | hides broken laws | manufactured and one-step gates first |

## 13. Verification Ladder

The theory should be validated in this order before any production adoption.

### V1. Geometry identity

Given an analytic interface and a mesh, compute `I_h` and `F_C`.

```text
sum_C |C|F_C = |Omega_{l,h}(I_h)|
0 <= F_C <= 1
```

### V2. Reconstruction inverse

Given realizable `F_C` and normals, reconstruct `I_h`:

```text
A_h(R_h(F,n))_C = F_C
```

for empty, full, and mixed cells, including near-0/near-1 fractions.

### V3. Exact translation

Move a shape by a constant velocity over a fraction of a cell:

```text
F^{n+1} from geometric flux == cell fractions of translated geometry
```

within the designed order.

### V4. Internal-face cancellation

On a closed or periodic domain:

```text
sum_C |C|(F_C^{n+1}-F_C^n) = 0
```

to roundoff for the discrete flux update.

### V5. Common-flux consistency

For density contrast:

```text
m_C(F^{n+1}) equals mass update from Phi_m,
momentum update uses the same Phi_m.
```

### V6. Static capillary Hodge balance

For static constant-curvature geometry:

```text
||P_Hodge capillary_covector|| = 0
```

within discretization tolerance.

### V7. Dynamic capillary drive

For nonconstant-curvature geometry:

```text
||P_Hodge capillary_covector|| != 0.
```

### V8. Gauge retraction no-mass-change

Reconstruct `phi` from `F_C`:

```text
F_C unchanged,
derived psi mass not used as physical invariant,
surface/gauge defects recorded.
```

### V9. Nonuniform/periodic/wall probes

Repeat V1--V5 on:

```text
stretched physical cells,
periodic seam crossings,
wall-adjacent cells with impermeable boundaries.
```

## 14. Theoretical Status

The formal structure is plausible and internally coherent if the following
single-owner rule is obeyed:

```text
F_C owns material volume and density.
I_h owns sharp surface and volume geometry.
phi/psi are derived gauges unless explicitly promoted with an equivalence proof.
```

The largest unresolved theoretical problem is not volume conservation.  It is
the capillary-ready reconstruction:

```text
How should R_h(F, gauge) construct an interface that is both locally
volume-exact and smooth/consistent enough for variational surface tension?
```

This question must be solved before adoption.  A local PLIC reconstruction is
a strong first mathematical primitive for volume and flux, but it is not by
itself a full capillary theory.

## 15. Open Theory Questions

1. What is the minimum extra gauge information beyond `F_C` needed for a
   capillary-ready `R_h`?
2. Should `phi` be transported as a predictor, reconstructed entirely from
   `F_C`, or both?
3. Can `S_h(I_h)` be chosen so that `dS_h` has a stable Hodge pairing while
   preserving exact local fractions?
4. What is the correct discrete topology rule for ambiguous cells?
5. How should wall contact be represented without a contact-angle model?
6. How should grid rebuild/remap transfer `F_C` exactly between nonmatching
   fitted grids?
7. Which variables need checkpointing to make restart bitwise/dynamically
   equivalent?

These are adoption blockers, not implementation details.
