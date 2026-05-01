# CHK-RA-WALL-RIDGE-001 — Wall-Closure Ridge–Eikonal Theory

Date: 2026-05-01
Status: theory/design memo
Scope: Ridge–Eikonal reinitialization, Gaussian grid fitting, wall-contact interfaces

## 1. Conclusion

The observed wall detachment should not be treated as a cosmetic boundary
patch.  A two-phase interface that touches a solid wall is a manifold on the
closed domain,

```math
\overline{\Gamma}(t)=\Gamma(t)\cup C(t),\qquad
C(t)=\overline{\Gamma}(t)\cap\partial\Omega ,
```

where `C(t)` is the contact-line set.  Ridge extraction, FMM redistancing,
mass correction, and interface-fitted grid monitors must therefore preserve
the zero set on `\overline{\Omega}`, not merely inside `\Omega`.

The wall velocity/pressure boundary condition should not be changed first.
The required change is in the geometric reconstruction contract near walls:
Ridge–Eikonal and Gaussian fitting need a wall-compatible closure extension
and explicit contact-line seeds.

## 2. Failure Mechanism

The current free-domain geometry pipeline can open a hole at a wall through
four mathematically distinct mechanisms.

### 2.1 Truncated Gaussian support

The Ridge–Eikonal auxiliary field is built from Gaussian contributions,

```math
\xi_{\rm ridge}(x)=\sum_k \exp\left(-{|x-c_k|^2\over\sigma_k^2}\right).
```

Near a wall, the physical Gaussian support is cut in half if it is evaluated
only in `\Omega`.  This biases the ridge inward and can remove the maximum
that should lie on `\partial\Omega`.  A boundary contact then looks like an
interior ridge with a small gap.

### 2.2 Interior-only ridge admissibility

The current ridge local-maximum test is interior-biased: a maximum on the wall
is not the same object as a maximum with two neighbours across the wall.  On a
closed domain the correct condition is a constrained maximum on
`\overline{\Omega}`.  For inward wall normal `\nu`, wall tangent `\tau`, and
ridge field `\xi`,

```math
\partial_\tau \xi = 0,\qquad
\partial_\nu \xi \le 0,\qquad
\partial_{\tau\tau}\xi < 0
```

is the boundary analogue of the interior local-ridge test.

### 2.3 Incomplete FMM boundary data

The Eikonal solve is a boundary-value problem,

```math
|\nabla_x \phi| = 1,\qquad \phi=0\quad\text{on the seed set}.
```

If the seed set omits `C(t)`, the viscosity solution is allowed to choose a
zero contour that does not touch the wall.  Sign-change seeds in cell interiors
are not sufficient: exact-zero, saturated-Heaviside, or one-sided wall traces
can lose the sign change even when the geometric contact remains.

### 2.4 Global mass correction can move contact endpoints

The current scalar correction has the form

```math
\phi \leftarrow \phi+\delta\phi .
```

For a closed interior curve this is a uniform normal displacement.  For an
interface with a boundary endpoint, however, the endpoint is a constrained
Dirichlet seed.  A nonzero shift at the contact line can detach the zero set
from the wall unless the correction is pinned there.

## 3. Wall-Compatible Closure Extension

For the current capillary-wave setup the graph is `y=\eta(x)` and the relevant
wall contact is at the vertical walls.  The benchmark endpoints are intended
to behave as neutral wall contacts, so the signed-distance extension should
satisfy

```math
\partial_{n_w}\phi=0
```

at the wall, equivalently a mirror-even extension across the wall.  More
general contact-angle physics would replace this by an oblique contact-angle
condition, but that is a new physical model and should not be smuggled into a
numerical repair.

Let `R_w` denote reflection across a solid wall.  The wall-compatible Gaussian
ridge field is

```math
\xi_{\rm ridge}^{W}(x)
=\sum_{c_k\in S_\Gamma}\sum_{R\in\mathcal{R}_W}
  \exp\left(-{|x-Rc_k|^2\over\sigma_k^2}\right),
```

where `S_\Gamma` is the tracked interface crossing set and `\mathcal{R}_W`
contains the identity, relevant wall reflections, and corner reflections
within the Gaussian support band.  For a neutral wall this enforces
`\partial_{n_w}\xi_{\rm ridge}^{W}=0` at `\partial\Omega` and prevents the
half-Gaussian bias.

## 4. Contact-Line Seed Contract

Before reinitialization or grid fitting, construct a closure seed set

```math
S_h = S_{\rm interior}\cup S_{\rm wall}.
```

`S_{\rm interior}` contains the usual sub-cell sign-change crossings.
`S_{\rm wall}` contains sign changes and exact-zero contacts on wall traces.
For each wall segment with endpoint values `\phi_a,\phi_b`, include

```math
x_c=x_a+
{|\phi_a|\over |\phi_a|+|\phi_b|}(x_b-x_a)
```

when the wall trace changes sign, and include the endpoint itself when
`|\phi|` is below the interface tolerance.  The FMM then solves

```math
|\nabla_x\phi|=1 \quad\text{in }\Omega,\qquad
\phi=0\quad\text{on }S_h ,
```

with the sign copied from the pre-reinitialized phase field.  This makes wall
contact part of the Dirichlet data, not an emergent property of Gaussian
post-processing.

## 5. Contact-Preserving Mass Correction

Mass correction must be constrained so that it cannot move contact-line seeds.
Use a pinned correction

```math
\phi \leftarrow \phi+\lambda\,\chi_{\rm free}(x),
\qquad
\chi_{\rm free}=0\;\text{on a contact-line band},
\qquad
\chi_{\rm free}=1\;\text{away from the wall-contact band},
```

with `\lambda` chosen from the same volume constraint as the current scalar
correction.  In CLS variables this is equivalent to weighting the correction by

```math
w_{\rm pinned}(x)
= {\psi(1-\psi)\over\varepsilon_{\rm local}(x)}\chi_{\rm free}(x).
```

If the total free weight is too small, the correct response is to skip mass
correction for that step and report a diagnostic, not to shift the pinned
contact line.

## 6. Grid-Fitting Monitor Without Wall Holes

The interface-fitted grid monitor should be based on the projection of the
closed tracked interface, not only on `min |\phi|` over interior nodes.
For axis `a`,

```math
P_a(\overline{\Gamma})=\{x_a:\;x\in S_h\},
```

and a no-hole monitor can be written as

```math
\omega_a(s)
=1+(\alpha_a-1)\max_{c\in S_h}
\exp\left(-{(s-c_a)^2\over\varepsilon_{g,a}^2}\right).
```

For the capillary-wave benchmark with y-only fitting, this means the y-monitor
must include the vertical-wall endpoint projections as well as interior
crossings.  The x-axis should remain uniform.

## 7. No-Hole Invariant

The discrete geometric pipeline should satisfy:

> If `S_h` is an `O(h)` sampling of `\overline{\Gamma}` and the contact-line
> seeds are pinned during redistancing and mass correction, then no geometry
> operator may transform a wall-attached interface into an interface whose
> zero set has a finite gap from the wall.

Proof sketch:

1. `S_h` is imposed as FMM Dirichlet data, so the redistanced field has
   `\phi=0` on all contact seeds.
2. The mirror Gaussian makes the ridge field a closure-compatible smooth
   extension, so boundary ridges are not weakened by missing support outside
   the domain.
3. Boundary ridge admissibility uses the constrained maximum condition on
   `\overline{\Omega}` and therefore accepts wall ridges as first-class
   geometric features.
4. The pinned mass correction has `\chi_{\rm free}=0` on the contact-line band,
   so it cannot change `\phi=0` at the wall seeds.
5. The grid monitor is built from `S_h`, so grid rebuilding cannot erase the
   wall-contact projection before the next reconstruction step.

Thus any remaining wall detachment is either physical contact-line motion or a
failed advection/contact-angle model, not an artefact of Ridge–Eikonal
Gaussian processing.

## 8. Implementation Implications

Required production changes should be staged in this order:

1. Add a wall-contact extractor from current `\phi`/`\psi` traces.
2. Feed `S_wall` as explicit FMM seeds on CPU and GPU.
3. Mirror interface crossing points in `RidgeExtractor.compute_xi_ridge` within
   a finite Gaussian support band.
4. Add boundary ridge admissibility for one-sided wall maxima.
5. Replace scalar mass correction by contact-pinned mass correction when
   wall-contact seeds exist.
6. Build Gaussian grid-fitting monitors from the tracked closure seed set for
   active axes.

Validation should include:

- a static wall-attached graph that remains attached after repeated
  Ridge–Eikonal reinitialization;
- a y-only capillary-wave grid rebuild where vertical-wall endpoint
  projections remain in the y-monitor;
- a mass-correction case proving pinned seeds retain `\phi=0`;
- CPU/GPU parity for contact-line FMM seeds.

## 9. Answer to the Wall-Handling Question

Yes, wall-neighbourhood geometry processing should change.  No, the first
change should not be the Navier–Stokes wall boundary condition.  The immediate
bug class is geometric: a free-space Gaussian/Ridge–Eikonal pipeline is being
applied to a closed-domain interface.  The correct fix is to make
Ridge–Eikonal, mass correction, and grid fitting wall-closure aware.
