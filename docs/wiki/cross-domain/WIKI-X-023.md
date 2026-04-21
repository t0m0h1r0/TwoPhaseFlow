---
ref_id: WIKI-X-023
title: "UCCD6 Integration Design for Incompressible NS (Skew-Symmetric Advection + Selective Hyperviscosity)"
domain: cross-domain
status: PROPOSED  # Research memo; integration PoC pending
superseded_by: null
sources:
  - description: Internal research memo on NS-level UCCD6 design (2026-04-21)
depends_on:
  - "[[WIKI-T-001]]: CCD Method (baseline Chu & Fan operator)"
  - "[[WIKI-T-002]]: DCCD spectral filter"
  - "[[WIKI-T-046]]: FCCD face-centered upwind CCD"
  - "[[WIKI-T-061]]: Upwind⊕CCD pedagogical foundation"
  - "[[WIKI-T-062]]: UCCD6 sixth-order upwind CCD with order-preserving hyperviscosity"
consumers:
  - domain: future-impl
    description: NS pipeline integration of UCCD6 (skew-sym advection, flux-form viscous, PPE)
  - domain: theory
    description: Energy conservation proof (NS version), CFL constraint analysis, two-phase interface stability
tags: [ccd, uccd6, navier_stokes, skew_symmetric, flux_form, les_filter, two_phase, design_guide]
compiled_by: ResearchArchitect
compiled_at: "2026-04-21"
---

# UCCD6 Integration Design for Incompressible Navier–Stokes

## Thesis

> **UCCD6 is not a per-term replacement for the advection operator. It is the
> discrete realisation of the structural decomposition "skew-symmetric
> (energy-conserving) ⊕ positive-definite (high-wavenumber selective)
> dissipation", and should be designed at the NS-system level — not the
> advection-term level.**

This entry organises that insight and its implications for the project's
CLS + CCD + PPE + NS pipeline. The core scheme is defined in
[WIKI-T-062](../theory/WIKI-T-062.md); this note positions it inside the NS
equations.

## 1. Structural decomposition of incompressible NS

$$
\frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u}\cdot\nabla)\mathbf{u} = -\nabla p + \nu \nabla^2 \mathbf{u}, \qquad \nabla\cdot\mathbf{u} = 0.
$$

At the discrete level the three building blocks have distinct mathematical
character:

| Block | Form | Discrete character |
|---|---|---|
| (A) advection | $(\mathbf{u}\cdot\nabla)\mathbf{u}$ | **skew-symmetric / anti-Hermitian** (energy-conserving) |
| (B) diffusion | $\nu \nabla^2 \mathbf{u}$ | **symmetric / positive semi-definite** (physical dissipation) |
| (C) projection | $-\nabla p$ s.t. $\nabla\cdot\mathbf{u} = 0$ | **constraint** (null-space of div) |

UCCD6's fundamental pattern mirrors exactly this split:

$$
\partial_t u = -a D_1^{\text{CCD}} u - \sigma |a| h^7 (-D_2^{\text{CCD}})^4 u
$$

- first term: skew-Hermitian (energy-conserving dispersion)
- second term: positive semi-definite (selective high-wavenumber damping)

## 2. Recommended NS discretisation

### 2.1 Advection — skew-symmetric CCD form

Plain $(\mathbf{u}\cdot\nabla)\mathbf{u}$ is *not* discretely skew-symmetric
under CCD. Use the symmetrised "skew" form instead:

$$
\mathcal{A}_{\text{skew}}(\mathbf{u}) = \tfrac{1}{2}\bigl[(\mathbf{u}\cdot\nabla)\mathbf{u} + \nabla\cdot(\mathbf{u}\otimes\mathbf{u})\bigr]
$$

with each half discretised by $D_1^{\text{CCD}}$:

- convective: $(\mathbf{u}\cdot\nabla)u \;\to\; u \, D_x^{\text{CCD}} u + v \, D_y^{\text{CCD}} u$
- divergence: $\nabla\cdot(\mathbf{u}\otimes u) \;\to\; D_x^{\text{CCD}}(u^2) + D_y^{\text{CCD}}(uv)$

### 2.2 UCCD6 hyperviscosity — NS extension

Add the UCCD6 hyperviscosity as a vector-Laplacian-power term acting on
$\mathbf{u}$:

$$
\boxed{\;\mathcal{A}_{\text{UCCD6}}(\mathbf{u}) = \mathcal{A}_{\text{skew}}(\mathbf{u}) + \sigma h^7 (-\Delta_{\text{CCD}})^4 \mathbf{u}\;}
$$

where $\Delta_{\text{CCD}} = \sum_k (D_2^{\text{CCD}})_k$ is the tensor-product
CCD Laplacian. Operationally this is four successive applications of
$-\Delta_{\text{CCD}}$ per RHS evaluation, mirroring the 1-D UCCD6 recipe in
[WIKI-T-062](../theory/WIKI-T-062.md).

**Trade-off summary:**

| Choice | Stability | Accuracy | Verdict |
|---|---|---|---|
| Pure CCD advection | dispersion-only | $O(h^6)$ | **diverges** (Gibbs blows up) |
| 1st-order upwind | TVD | $O(h)$ | stable but low order |
| **CCD + UCCD6** | high-$k$ damped | $O(h^6)$ main | **ideal** (selective dissipation) |

### 2.3 Viscous term — flux form for $\mu$ jumps

For constant $\nu$: $\nu \nabla^2 \mathbf{u} \to \nu D_2^{\text{CCD}} \mathbf{u}$.

**⚠️ Two-phase warning.** In the project's CLS system the viscosity $\mu$
jumps at the interface and gradients are discontinuous. Plain CCD on
$\mu \nabla\mathbf{u}$ violates Chu & Fan's smoothness assumptions and
contaminates the balanced-force residual ([WIKI-T-044](../theory/WIKI-T-044.md)).
Two remediation paths:

- **Option 1 (recommended)** — flux-form discretisation
  $\nabla\cdot(\mu \nabla u) \to D_x^{\text{CCD}}\bigl(\mu (D_x^{\text{CCD}} u)\bigr) + \ldots$
  keeps CCD in the interior and the flux divergence stays consistent with
  the balanced-force operator.
- **Option 2 (high-order path)** — split-phase viscous solver + Radau IIA
  time integration. Higher implementation cost; reserved for
  high-Reynolds-number campaigns.

### 2.4 Pressure / PPE

Pressure gradient: $\nabla p \to D_1^{\text{CCD}} p$. Poisson solve:
$\nabla^2 p \to D_2^{\text{CCD}} p$.

**⚠️ Known issue (project-specific).** The CCD Laplacian with pure Neumann
BCs on $p$ has a rank-deficient nullspace; see [WIKI-X-004](WIKI-X-004.md),
[WIKI-T-016](../theory/WIKI-T-016.md), and the IIM-decomposition approach in
[WIKI-L-028](../code/WIKI-L-028.md) (CHK-177). UCCD6 does not alter this
diagnosis — the hyperviscosity term is local to $\mathbf{u}$ and does not
touch the PPE.

## 3. Complete NS+UCCD6 form

$$
\boxed{\;\frac{\partial \mathbf{u}}{\partial t} = -\mathcal{A}_{\text{skew}}^{\text{CCD}}(\mathbf{u}) - \sigma h^7 (-\Delta_{\text{CCD}})^4 \mathbf{u} + \nu D_2^{\text{CCD}} \mathbf{u} - \nabla^{\text{CCD}} p, \qquad \nabla\cdot\mathbf{u} = 0.\;}
$$

| Term | Scheme | Character |
|---|---|---|
| advection | CCD skew-symmetric | energy-conserving |
| stabilisation | UCCD6 hyperviscosity | high-$k$ selective damping |
| viscosity | CCD Laplacian (flux form for $\mu$ jumps) | physical dissipation |
| pressure gradient | $D_1^{\text{CCD}}$ | incompressibility constraint |
| Poisson solve | CCD elliptic + IIM decomposition | null-space aware |

## 4. The core insight — LES filter analogy

> **Upwind = low-order artificial viscosity (damps all wavenumbers).**
>
> **UCCD6 = high-order selective artificial viscosity (damps only the upper
> spectrum).**

The $(-\Delta_{\text{CCD}})^4$ symbol grows as $\theta^8$ near $\theta \to 0$,
so well-resolved scales see a $h^7 k^8$ damping rate — vanishing at the
convergence rate. At the Nyquist, the symbol saturates to
$\omega_2(\pi)^8 \approx 8.5\times 10^3$ per $h$, giving aggressive
near-Nyquist damping. This is essentially a **spectral LES filter**
embedded inside the discrete operator, not a post-hoc smoothing pass.

## 5. Two-phase (CLS) caveats

- **Do not apply CCD directly to $\psi$ (level-set) or to density jumps.**
  Use either the spectral filter ([WIKI-T-002](../theory/WIKI-T-002.md)),
  IIM / GFM, or FCCD ([WIKI-T-046](../theory/WIKI-T-046.md)) — whichever
  matches the variable class.
- Curvature computation must use the project's HFE smoothing
  ([WIKI-T-038](../theory/WIKI-T-038.md)); raw CCD on $\nabla^2\psi$ is
  under-resolved near the interface.
- The UCCD6 hyperviscosity term is applied to the *velocity* field, not to
  $\psi$. The velocity field is smooth away from the interface, so UCCD6
  is well-posed. Near the interface, the skew-sym advection operator uses
  the existing CLS surgical treatment.

## 6. Shortest implementation path

1. **Advection** — skew-symmetric form + $D_1^{\text{CCD}}$.
2. **Stabilisation** — UCCD6 hyperviscosity via four successive
   $D_2^{\text{CCD}}$ applications. For explicit RK3, $\sigma$ is CFL-limited
   to $\sigma \lesssim h / 8500$; for CN (matrix-free GMRES), $\sigma = O(1)$
   is unconditionally stable.
3. **Viscous** — flux-form $\mu$-weighted Laplacian; reuse project's
   `_fvm_pressure_grad` pattern.
4. **PPE** — existing CCD Poisson solver with IIM decomposition.

## 7. Open questions for follow-up research

- **Energy conservation proof (NS version).** Show that the CCD skew-sym
  advection operator is discretely skew-Hermitian in the project's
  $\ell^2$ inner product, so that energy balance at the NS level reduces
  to $\tfrac{1}{2}\mathrm{d}\|\mathbf{u}\|^2/\mathrm{d}t = -\sigma h^7 \|(-\Delta_{\text{CCD}})^2 \mathbf{u}\|^2 - \nu \|\nabla_{\text{CCD}} \mathbf{u}\|^2$.
- **CFL constraint (explicit RK3).** Quantify the joint advection +
  hyperviscosity stability polygon for TVD-RK3 on the NS-UCCD6 operator
  at realistic $\sigma$.
- **Two-phase interface stability.** Empirically measure whether UCCD6
  applied to $\mathbf{u}$ (not $\psi$) remains neutral to the
  balanced-force residual H-01 ([WIKI-E-030](../experiment/WIKI-E-030.md)).
  Theoretical expectation: neutral (UCCD6 is orthogonal to the
  face/node locus issue that FCCD addresses).

## References

- [WIKI-T-061](../theory/WIKI-T-061.md) / [SP-G](../../memo/short_paper/SP-G_upwind_ccd_pedagogical.md)
- [WIKI-T-062](../theory/WIKI-T-062.md) / [SP-H](../../memo/short_paper/SP-H_uccd6_hyperviscosity.md)
- [WIKI-T-001](../theory/WIKI-T-001.md), [WIKI-T-002](../theory/WIKI-T-002.md), [WIKI-T-046](../theory/WIKI-T-046.md)
- [WIKI-X-004](WIKI-X-004.md) (PPE instability survey), [WIKI-T-044](../theory/WIKI-T-044.md) (BF residual)
- [WIKI-X-024](WIKI-X-024.md): **Balanced-force design for two-phase UCCD6-NS** — the BF pair σκ∇ψ ↔ ∇p is the dominant residual source in two-phase flow; UCCD6 is orthogonal to it. Read alongside §2.3 and §5.
