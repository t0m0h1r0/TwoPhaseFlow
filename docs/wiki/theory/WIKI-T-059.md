---
ref_id: WIKI-T-059
title: "Non-Uniform Fast Marching Method (Physical-Space Eikonal Quadratic + Seeding)"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md
    description: "SP-E §6 (D3) — physical-space Eikonal quadratic, seeding, caustic fallback"
  - path: src/twophase/levelset/ridge_eikonal.py
    description: "NonUniformFMM.solve"
  - path: src/twophase/levelset/reinit_eikonal.py
    description: "Stock _fmm_phi (uniform-grid baseline; line 312-404)"
depends_on:
  - "[[WIKI-T-048]]: Eikonal Reconstruction — Uniqueness (SP-B §5/§6)"
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation"
consumers:
  - domain: code
    description: "WIKI-L-025 (RidgeEikonalReinitializer library card)"
  - domain: theory
    description: "Deferred 3D extension"
tags: [fmm, eikonal, non_uniform, quadratic_update, caustic_fallback, seeding, chk_159]
compiled_by: Claude Opus 4.7
chk: CHK-159
---

# Non-Uniform Fast Marching Method

## Context

The stock FMM implements the Sethian quadratic $d=\tfrac{1}{2}(a_{x}+a_{y}+\sqrt{2-(a_{x}-a_{y})^{2}})$, which implicitly assumes $h_{x}=h_{y}=1$. On interface-fitted grids this violates the Eikonal equation $|\nabla_{x}\phi|=1$.

## Physical-space Eikonal

For an updating neighbour at node $(i,j)$ with accepted-neighbour distances $a_{x}=d_{i\pm1,j},\,a_{y}=d_{i,j\pm1}$ and physical step sizes $h_{x},h_{y}$ (forward-difference distances from the selected neighbour),
$$\frac{(d-a_{x})^{2}}{h_{x}^{2}}+\frac{(d-a_{y})^{2}}{h_{y}^{2}}=1.$$

**Closed form (physical-space quadratic, larger root).**
$$d=\frac{a_{x}/h_{x}^{2}+a_{y}/h_{y}^{2}+\sqrt{D}}{1/h_{x}^{2}+1/h_{y}^{2}},\qquad D=\left(\frac{1}{h_{x}^{2}}+\frac{1}{h_{y}^{2}}\right)-\frac{(a_{x}-a_{y})^{2}}{h_{x}^{2}h_{y}^{2}}.$$

**Caustic fallback.** When $D<0$ the wavefront is caustic; fall back to the monotone one-dimensional update
$$d=\min(a_{x}+h_{x},\,a_{y}+h_{y}).$$

## Physical-coordinate seeding

Sub-cell sign-change crossings are seeded with physical distances (not index fractions):
$$d_\text{seed}^{i}=\frac{|\phi_{i}|}{|\phi_{i}|+|\phi_{i+1}|}\,h_\text{fwd}(i),\qquad d_\text{seed}^{i+1}=\frac{|\phi_{i+1}|}{|\phi_{i}|+|\phi_{i+1}|}\,h_\text{fwd}(i),$$
where $h_\text{fwd}(i)=x_{i+1}-x_{i}$ is the physical forward spacing. The smaller of any two competing seed candidates wins via the Dijkstra heap.

## Ridge-seed augmentation

Optional extra seeds $\{(i,j,d)\}$ are injected into the heap. The `RidgeEikonalReinitializer` pipeline supplies ridge cells that coincide with sign-change crossings as zero-distance anchors, preserving topology when the Ridge step has created new disconnected components.

## Viscosity-uniqueness extension

The Eikonal equation is physical-space native; the SP-B §6 viscosity-solution argument (semi-concavity plus boundary data) extends by direct substitution. No additional hypotheses are required on the non-uniformity of the grid.

## Accuracy

The FMM is first-order accurate in physical space (consistent with the stock Sethian algorithm). The CHK-159 verification V3 asserts a 99th-percentile residual $\max_{ij}||\nabla_{x}\phi_\text{fmm}|-1|<0.35$ and mean residual $<0.1$ across $\alpha\in\{1,2,3\}$ on $64^{2}$ grids.

## Equation → Discretization → Code

  - Equation: $(d-a_{x})^{2}/h_{x}^{2}+(d-a_{y})^{2}/h_{y}^{2}=1$
  - Discretization: closed-form larger root + caustic fallback
  - Code: `NonUniformFMM.solve` in [`src/twophase/levelset/ridge_eikonal.py`](../../../src/twophase/levelset/ridge_eikonal.py) (CPU-serial by design)
  - D2H / H2D boundary handled by the calling `RidgeEikonalReinitializer`
  - Verification: `test_ridge_eikonal.py::test_fmm_eikonal_residual` (α=1,2,3), `test_fmm_physical_coord_seeding` (axis-aligned interface)

## References

  - SP-E, `docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md` §6
  - WIKI-T-047, WIKI-T-048 (viscosity uniqueness)
