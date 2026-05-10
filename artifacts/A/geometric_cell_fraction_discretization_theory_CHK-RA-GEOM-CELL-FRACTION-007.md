# CHK-RA-GEOM-CELL-FRACTION-007

## Purpose

User request:

> Establish the theory of the discretization.

This note turns the geometric cell-fraction direction into a discrete
state-space theory.  The target is not a tactical implementation recipe.  The
target is a set of discrete spaces, maps, adjoints, invariants, and fail-close
conditions that preserve the physical laws already identified:

```text
material volume is a sharp geometric finite-volume measure,
capillary force is the virtual work derivative of the same geometry,
pressure projection is a Hodge projection in the same face/cell complex,
CCD/FCCD/UCCD act on smooth fields and must not differentiate discontinuous
cell fractions as if they were smooth profiles.
```

## 1. Central Discretization Theorem

The primary phase unknown should be the cell liquid volume

```text
q_C = |C| theta_C,
```

not the normalized fraction alone.  The fraction remains the user-facing and
state-inspection variable:

```text
theta_C = q_C / |C|,       0 <= theta_C <= 1.
```

The reason is mathematical, not cosmetic.  On a nonuniform grid, equal changes
in `theta_C` do not represent equal physical volumes.  Conservation,
projection residuals, and adjoint work must therefore be written in the
integrated variable `q_C`.

The discrete phase theorem is:

```text
q_C is the material-volume 2-form.
Gamma_h is the sharp interface complex.
phi is a continuous gauge used to represent Gamma_h.

Compatibility:
  q_C = Q_h(phi)_C := |C cap Omega_l(Gamma(phi))|.
```

Equivalently:

```text
theta_C = A_h(Gamma(phi))_C = Q_h(phi)_C / |C|.
```

The equality in `q` units is the production constraint.  The equality in
`theta` units is only the normalized view.

## 2. Mesh as a Metric Cell Complex

Let the physical mesh be an oriented finite-volume cell complex:

```text
C_h      cells C
F_h      oriented faces f
N_h      gauge nodes v
|C|      physical cell area/volume
|f|      physical face length/area
B        cell-face incidence matrix
```

`B_{C,f}` is `+1` when face `f` enters cell `C` with its orientation, `-1`
when it leaves, and `0` otherwise.  Periodic boundaries are represented by
quotienting the topology before forming `B`; a periodic pair is one oriented
face degree of freedom, not two unrelated boundary fluxes.  Impermeable wall
faces are either absent from the transport complex or have identically zero
normal flux.

The topological identity is:

```text
1_C^T B = boundary functional.
```

For periodic and wall-closed phase transport:

```text
1_C^T B Phi_l = 0.
```

This identity must hold before any metric weighting.  Metrics enter through
Hodge matrices:

```text
H_C = diag(|C|)
M_f = face kinetic/mass Hodge
W_v = nodal gauge Hodge
```

The cell divergence of a face volume flux `U_f` is:

```text
D_h U = H_C^{-1} B U.
```

The conservative cell-volume update is written in integrated form:

```text
q^{n+1} = q^n - Delta t B Phi_l.
```

Here `Phi_l` is liquid volume flux per time through faces.  The normalized
fraction is then:

```text
theta^{n+1} = H_C^{-1} q^{n+1}.
```

## 3. Discrete Spaces and Ownership

The proposed discrete state is:

```text
q_C        liquid volume 2-form, hard material carrier
theta_C    normalized view q_C/|C|
u_f        face velocity or face flux variable
p_C        cell pressure multiplier
phi_v      continuous nodal gauge
Gamma_h    zero trace of phi on the cell complex
```

Ownership is strict:

```text
q owns material volume and density.
Gamma_h owns sharp surface geometry.
phi owns the continuous gauge representation of Gamma_h.
psi, if present, is derived visualization/legacy bridge state.
```

Density must be built from the same volume owner:

```text
rho_C(q) = rho_g + (rho_l - rho_g) q_C/|C|.
```

Any route that computes density from `q` while computing capillary force from
an incompatible `psi` or independent `phi` returns to a two-measure
formulation and is rejected.

## 4. Geometry Map on a Fixed Stratum

Use a continuous P1/Q1 gauge `phi` on nodes and define:

```text
Omega_l(phi) = { x : phi_h(x) < 0 },
Gamma(phi)   = { x : phi_h(x) = 0 }.
```

On a fixed regular stratum `S`, the sign pattern and edge-crossing pattern are
fixed.  The cut polygons inside each cell are then algebraic functions of the
nodal values.  Define:

```text
Q_h^S(phi)_C = |C cap Omega_l(Gamma(phi))|,
A_h^S(phi)_C = Q_h^S(phi)_C / |C|,
S_h^S(phi)   = length/area of Gamma(phi).
```

All geometry is measured in physical coordinates.  Reference-cell fractions
are allowed only if the Jacobian map to physical coordinates is included
exactly in `|C|`, cut areas, face apertures, and surface lengths.

The fixed-stratum derivative of the volume map is:

```text
J_q(phi) = d Q_h^S(phi) / d phi.
```

Shape-calculus form for `Omega_l={phi<0}`:

```text
delta q_C
  = - integral_{Gamma(phi) cap C} delta phi / |grad phi| dS.
```

For P1 segments this integral is exact on the segment because `delta phi` is
linear and `grad phi` is constant per subcell.  Thus each mixed-cell row of
`J_q` touches only the local trace nodes.  This is the sparse operator that
belongs in the compatibility projection.

The normalized Jacobian is:

```text
J_A = H_C^{-1} J_q.
```

`J_A` is useful for reporting fractions.  `J_q` is the correct constraint row
for conservation, nonuniform grids, and physical work.

## 5. Conservative Geometric Transport

The material law is the finite-volume transport of `q`:

```text
q^{n+1} = q^n - Delta t B Phi_l(Gamma_h,u).
```

`Phi_l` must be a geometric swept-volume flux of the same liquid set
represented by `Gamma_h`, not a product of a smooth indicator sample and a
velocity.  For every internal face, the same oriented flux is used by both
neighboring cells.

Global conservation follows immediately:

```text
1^T q^{n+1}
  = 1^T q^n - Delta t 1^T B Phi_l
  = 1^T q^n
```

under wall/periodic closure.

Boundedness is also geometric.  A flux construction is admissible only if it
can certify:

```text
0 <= q_C^{n+1} <= |C|
```

without after-the-fact clipping.  A CFL condition may be part of the theorem
if it states the domain in which swept subregions are disjoint and contained.
It is not an empirical stability knob.

The common mass flux must be derived from the same phase flux:

```text
Phi_m = rho_g Phi_V + (rho_l - rho_g) Phi_l,
```

where `Phi_V` is the total volume flux.  Momentum remap and any common-flux
ledger must use this same `Phi_l`.  Otherwise mass and momentum are transported
by different phase geometries.

## 6. Compatibility Projection After Transport

After transport there are two predicted objects:

```text
q^-      conservative transported material volume
phi^-    transported/predicted smooth gauge
```

The projection is:

```text
min_phi  1/2 ||phi - phi^-||_{W_eta}^2

subject to
  Q_h^S(phi)_C = q^-_C          active mixed cells,
  phi satisfies full/empty sign inequalities,
  periodic node identifications and wall constraints hold.
```

with

```text
W_eta = W_v + eta L^T H_L L.
```

The smoothness/eikonal term is a gauge metric, not a physical force.  Its work
must be recorded separately if it changes surface energy.

Linearized constrained step:

```text
r_q   = q^- - Q_h^S(phi_k),
J_q   = d Q_h^S(phi_k) / d phi,

min_delta  1/2 ||delta - delta_pred||_{W_eta}^2
subject to J_q delta = r_q.
```

KKT system:

```text
[ W_eta   J_q^T ][ delta ] = [ W_eta delta_pred ]
[ J_q       0   ][ lambda]   [ r_q              ].
```

Schur form:

```text
S_q lambda = J_q delta_pred - r_q,
S_q = J_q W_eta^{-1} J_q^T,
delta = delta_pred - W_eta^{-1} J_q^T lambda.
```

This is the correct row scaling for nonuniform meshes.  Solving with `J_A`
instead of `J_q` changes the metric of the constraints and can make small
cells and large cells compete incorrectly.

Mandatory gates:

```text
rank(J_q),
condition estimate of S_q,
maximum admissible line-search step before sign/case change,
hard residual ||Q_h(phi^+) - q^-||,
boundedness 0 <= q_C <= |C|,
Delta S_Pi ledger.
```

If any gate fails, the method must fail close or enter a declared topology
route.  It must not silently clip `q`, relax the hard constraint, or fall back
to a diffuse mass correction.

## 7. Pressure Projection and Hodge Adjoint

Let `u_f` be the face velocity/flux variable with kinetic inner product:

```text
<u,v>_M = u^T M_f v.
```

For cell pressure `p_C`, the pressure gradient must be the negative adjoint of
the finite-volume divergence:

```text
<G_h p, u>_M = - p^T B u.
```

Therefore:

```text
G_h p = - M_f^{-1} B^T p.
```

The incompressibility projection has the algebraic form:

```text
B (u^* - Delta t M_f^{-1} B^T p) = 0,
```

up to the sign convention used for `p`.  This is the same Hodge structure that
must be used when capillary virtual work is converted into face acceleration.

The key compatibility rule is:

```text
phase transport uses B,
pressure projection uses B and M_f,
capillary work returns a face covector paired with the same M_f.
```

If these three use different metrics or different phase geometries, the
discrete Hodge residual has no physical meaning.

## 8. Capillary Virtual Work Discretization

At a compatible state:

```text
q = Q_h(phi),       Gamma_h = Gamma(phi),
E_sigma(phi) = sigma S_h(phi).
```

A virtual face motion `w_f` changes material volume through the geometric
transport tangent:

```text
delta q = T_q(Gamma_h) w.
```

The lifted gauge variation is:

```text
L_B(w)
  = argmin_delta_phi ||delta_phi - delta_phi_pred(w)||_{W_eta}^2
    subject to J_q delta_phi = T_q(Gamma_h) w.
```

The capillary covector is defined by virtual work:

```text
r_sigma(w) = - sigma dS_h(phi)[ L_B(w) ].
```

The face acceleration is the Riesz representative:

```text
a_sigma = M_f^{-1} r_sigma.
```

This is the discrete replacement for a hand-built curvature force.  The
surface derivative `dS_h` must be the exact derivative of the same polyline or
surface complex used by `Q_h`.  It is not allowed to compute `Q_h` from
geometric fractions and `dS_h` from an unrelated smoothed profile.

### Discrete Young--Laplace Test

A static equilibrium is discrete Young--Laplace if there exists a pressure
multiplier `pi_C` such that, on admissible bundle variations,

```text
sigma dS_h(delta_phi) + pi^T J_q delta_phi = 0.
```

Equivalently, the capillary covector lies in the pressure-gradient range after
the same bundle lift.  Then the projected face acceleration is zero.  A
nonconstant-curvature interface should not satisfy this range condition, and
must produce a nonzero projected drive.

This replaces "circle vs ellipse" logic.  The criterion is not shape name.  It
is whether `dS_h` is a pressure-exact covector on the compatible discrete
bundle.

## 9. CCD/FCCD/UCCD Orthogonality

The geometric phase carrier `q` is discontinuous by design.  It is a cell
2-form.  It should not be differentiated by CCD, FCCD, UCCD, or DCCD as if it
were a smooth scalar field.

The CCD-family role remains:

```text
smooth velocity/pressure/gauge derivatives,
gauge prediction for phi,
elliptic/compact smooth-field components,
smooth diagnostics and manufactured probes.
```

The geometric finite-volume role is:

```text
phase material transport,
cell volume conservation,
boundedness,
common mass flux,
compatibility constraints.
```

This is not a fallback from CCD.  It is a de Rham-style split:

```text
smooth fields live in CCD-compatible nodal/face spaces,
material phase lives as a conservative finite-volume cochain,
the two communicate only through declared maps Q_h, J_q, T_q, and L_B.
```

## 10. Boundary, Periodic, and Nonuniform Rules

### Periodic boundaries

Periodic domains are quotient complexes:

```text
periodic nodes are identified in phi,
periodic faces are single oriented flux degrees of freedom,
Gamma_h wraps through the quotient without duplicate volume.
```

Volume and surface must not be counted twice at the seam.

### Wall boundaries

For impermeable walls:

```text
Phi_l = 0 on wall faces,
B has no open phase boundary contribution,
compatibility projection enforces wall sign/contact constraints.
```

If a contact-angle model is introduced, it is a boundary term in `dS_h`, not a
post-hoc correction to curvature.

### Nonuniform grids

All measures are physical:

```text
q_C, |C|, |f|, swept volumes, cut areas, and surface lengths
```

are computed after the mesh mapping.  Normalized fractions are never summed
without `|C|`.

## 11. Restart State

A restart that claims bitwise or mathematical continuation must store enough
state to reconstruct the same discrete problem:

```text
q or theta plus cell volumes,
phi and any multistep/history gauge state,
velocity/momentum and pressure-stage data required by the time integrator,
current stratum/case identifiers if used for fail-close diagnostics,
projection ledger terms Delta S_Pi and compatibility residual history,
phase-flux/common-flux stage data when the next step depends on it.
```

Storing only `theta` and the latest `phi` is not sufficient for a multistage or
restart-sensitive solver if prior-stage fluxes, predictor states, or previous
time levels enter the next update.

## 12. Algebraic Manufactured Checks

A minimal incidence/Hodge probe on a `4 x 3` grid with periodic `x` and wall
`y` topology produced:

```text
Nc=12, Nf=20, rank(B)=11
global_volume_residual = 0.000e+00
pressure_adjoint_residual = 0.000e+00
```

The check verifies two algebraic identities of the proposed discretization:

```text
1^T B Phi = 0
< -M_f^{-1} B^T p, u >_{M_f} + p^T B u = 0.
```

This does not validate the full geometry solver.  It validates the cell/face
complex and pressure Hodge skeleton that the geometry solver must plug into.

## 13. Negative Knowledge

Reject as production theory:

- treating `theta_C` as the primary hard variable in unweighted residual norms
  on nonuniform meshes;
- solving compatibility with `J_A` when the physical hard constraint is
  `q=Q_h(phi)`;
- differentiating discontinuous `theta` with CCD/FCCD/UCCD/DCCD;
- computing capillary `dS_h` from a surface different from the one used by
  `Q_h`;
- clipping `q` after transport instead of proving bounded geometric flux;
- using global mass correction in place of local compatibility;
- hiding projection surface work inside physical capillary work;
- counting periodic seam geometry twice;
- introducing damping, CFL tuning, curvature caps, smoothing, FD/WENO/PPE
  fallbacks, benchmark-name branches, or case-specific quiet fixes.

## 14. Established Direction

The discretization theory is now:

```text
1. Use q_C=|C|theta_C as the conserved phase 2-form.
2. Use a physical metric cell complex with incidence B.
3. Transport q by a bounded geometric swept-volume flux Phi_l.
4. Derive common mass/momentum fluxes from the same Phi_l.
5. Represent the capillary surface by a continuous gauge phi and Gamma(phi).
6. Enforce compatibility as Q_h(phi)=q in q-units.
7. Use J_q=dQ_h/dphi, not only J_A, in projection and capillary lifts.
8. Convert pressure and capillary covectors through the same face Hodge M_f.
9. Keep CCD-family derivatives on smooth fields; do not use them as phase
   fraction differentiators.
10. Fail close on infeasible stratum, rank loss, sign-margin loss, or hidden
    projection work.
```

The remaining implementation-proof gates are precise:

```text
G1: exact Q_h and J_q on uniform/nonuniform physical cells,
G2: bounded conservative Phi_l with common-flux ledger,
G3: constrained projection residual in q-units,
G4: static Young--Laplace range test in the same Hodge metric,
G5: nonconstant-curvature drive test on the same bundle,
G6: periodic/wall quotient geometry test,
G7: restart equivalence with saved stage state.
```

[SOLID-X] Theory/artifact only.  No solver source was changed, no tested code
was deleted, and no tactical stabilization, fallback, benchmark branch, or
case-specific correction was introduced.
