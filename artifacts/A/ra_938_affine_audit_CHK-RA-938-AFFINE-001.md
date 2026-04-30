# CHK-RA-938-AFFINE-001 — §9.3.8 affine jump audit

- Worktree: `.claude/worktrees/ra-938-affine-audit-20260430`
- Branch: `ra-938-affine-audit-20260430`
- Trigger: user requested ResearchArchitect audit of whether the affine
  formulation introduced in §9.3.8 is physically and mathematically justified,
  and whether it contributes to the problem it is meant to solve.

## Verdict

The affine introduction in §9.3.8 is justified and should be kept, but only
with the explicit oriented pressure-jump contract now stated in the paper:

```text
psi = 1 liquid, psi = 0 gas
n_lg = liquid -> gas
kappa_lg = div_Gamma n_lg
j_gl = p_gas - p_liquid = -sigma kappa_lg
G_Gamma(p; j_gl) = G(p) - B(j_gl)
```

The key point is that affine jump is not a cosmetic implementation variant of
CSF.  It solves a real algebraic defect: a sharp Young--Laplace pressure jump
represented as a regular pressure field can be absorbed by the elliptic solve
as `p_base ~= -J`, leaving `p_total = p_base + J ~= 0`.  Moving the known jump
into the face-gradient operator prevents that cancellation and puts pressure
and surface tension on the same discrete operator locus.

This does not prove full long-time capillary-wave validity.  It fixes the
pressure-jump coupling layer.  Curvature caps, HFE extension quality,
resolution/CFL dependence, and geometry-energy stability remain separate
validation gates.

## Problem Solved

The target problem is not merely "avoid explicit CSF".  There are two concrete
failures:

1. Regular jump decomposition makes the interfacial jump a free pressure
   component.  In the initially stationary capillary-wave diagnostic, the old
   route measured `ptp(p_total) / ptp(J) = 9.022527e-04`, so the restoring
   pressure was almost completely cancelled before time-step or curvature
   issues could dominate.
2. Separate body-force CSF and pressure-gradient evaluation can miss the
   balanced-force requirement because the two terms live on different discrete
   loci.  The affine form applies the same face coefficient, divergence, and
   gradient path to both the unknown pressure and the known jump.

The affine form contributes exactly to these failures.  It turns the projection
equation from "solve a pressure field plus a removable add-on" into "solve a
pressure whose face gradient is constrained by the supplied jump".

## Mathematical Check

For a face from low index cell to high index cell,

```text
s_f = I_gas(high) - I_gas(low)
B_f(j_gl) = s_f j_gl / d_f
G_Gamma(p; j_gl)_f = G(p)_f - B_f(j_gl)
```

The local invariant is decisive:

```text
liquid-low / gas-high:
  p_high - p_low = p_g - p_l = j_gl
  s_f = 1
  G_Gamma = j_gl/d_f - j_gl/d_f = 0

gas-low / liquid-high:
  p_high - p_low = p_l - p_g = -j_gl
  s_f = -1
  G_Gamma = -j_gl/d_f - (-j_gl/d_f) = 0
```

Thus the sign in `G_Gamma = G - B` is mathematically fixed by the manufactured
two-cell identity.  For the PPE,

```text
D_f alpha_f G_Gamma(p; j_gl) = q
```

is equivalent to

```text
D_f alpha_f G(p) = q + D_f alpha_f B(j_gl).
```

So the implementation's `rhs + D alpha B(j_gl)` path is the correct affine
right-hand-side form.

## Physical Check

With `n_lg` oriented from liquid to gas, the normal traction jump gives

```text
p_liquid - p_gas = sigma kappa_lg
j_gl = p_gas - p_liquid = -sigma kappa_lg.
```

This convention gives the required signs without benchmark-specific branches:

| Case | `kappa_lg` | `j_gl` | Physical consequence |
|---|---:|---:|---|
| liquid droplet in gas | positive | negative | liquid pressure higher |
| gas bubble in liquid | negative | positive | gas pressure higher |
| capillary-wave crest | positive | negative | restoring acceleration |
| flat RT interface | zero | zero | no capillary pressure artifact |

This is why the current `pressure_jump_gas_minus_liquid` data contract is
physically safer than a raw `sigma*kappa` field.  A raw product cannot tell the
consumer whether it stores `p_l-p_g`, `p_g-p_l`, gasward curvature, or
liquidward curvature.

## A3 Traceability

| Layer | Evidence |
|---|---|
| Equation | Young--Laplace: `j_gl=p_g-p_l=-sigma*kappa_lg` |
| Discretization | `B_f=s_f*j_gl/d_f`, `G_Gamma=G-B`, `D alpha G = q + D alpha B` |
| Code | `InterfaceStressContext.pressure_jump_gas_minus_liquid`; affine PPE RHS in `PPESolverFCCDMatrixFree`; corrector forwarding in `correct_ns_velocity_stage` |
| Tests | two-cell orientation, droplet/bubble sign, nonzero affine RHS, corrector context forwarding, one-step no-NaN stack |
| Experiment | oriented affine N=32/T=10 capillary run completed, early `A''` restored with observed/theory ratios 0.8814, 1.0380, 1.0166 |

## Finding Fixed

The audit found one paper-level inconsistency outside the §9.3.8 block but in
the same split-PPE section.  The IPC pressure-increment paragraph still wrote

```text
J_p = sigma (kappa^{n+1} - kappa^n)
```

even though the paper-wide contract defines `J_p=j_gl=-sigma*kappa_lg`.  The
correct increment jump is

```text
delta j_gl = j_gl^{n+1} - j_gl^n
           = -sigma (kappa_lg^{n+1} - kappa_lg^n).
```

This was corrected in `paper/sections/09b_split_ppe.tex`.  The same patch also
made §9.3.8 state explicitly that affine jump solves regular-jump cancellation
and balanced-force operator placement, while leaving curvature/geometry
stability to §14 validation.

## Residual Risks

- The affine pressure-jump operator is pressure-only and constant-sigma in the
  current production path; full viscous normal-stress and Marangoni jumps are
  future extensions.
- Correctness depends on the supplied `kappa_lg` having the documented
  liquid-to-gas orientation.  The operator cannot repair upstream curvature
  sign mistakes.
- The current capillary benchmark validates the short-time restoring sign, not
  the full Prosperetti phase/period response.
- Rising-bubble and RT physical benchmark gates remain open in the paper.

## Validation

- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS,
  `main.pdf` generated with 234 pages.
- `make test PYTEST_ARGS="-k affine_jump -q"`: PASS, 8 selected tests passed.
- `git diff --check`: PASS.

[SOLID-X] Paper and audit artifact only; no production code boundary change.
