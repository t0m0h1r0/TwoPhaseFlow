# CHK-RA-OSC-N64-009 — N64 Static-Droplet Curvature Contract Audit

Date: 2026-05-03  
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

Continue the theory-first RCA for the N=64 pressure oscillation/blow-up path,
without damping/CFL/smoothing workarounds.  The key question is whether the
phase-separated PPE + affine pressure jump + defect-correction stack is failing
because of the PPE variable contract, or because the Young--Laplace curvature
input no longer satisfies the static-circle contract.

## Stack Check

The active N64 static control uses the intended pressure stack:

- `projection.poisson.operator.coefficient: phase_separated`
- `projection.poisson.operator.interface_coupling: affine_jump`
- `projection.poisson.solver.kind: defect_correction`
- `projection.poisson.solver.base_solver: fd/direct`
- `momentum.terms.surface_tension.formulation: pressure_jump`

The curvature route is `interface.geometry.curvature.method:
psi_direct_filtered`.  In the current config vocabulary this is the direct-psi
curvature route with the interface-limited filter; it is not a separate Hermite
field-extension operator.  The alias `psi_direct_hfe` maps to this same route.

## Hypotheses Tested

1. **Pressure variable mismatch** — physical pressure and base pressure are
   being confused between PPE solve, pressure increment, pressure history, and
   projection.
2. **Previous-pressure jump-gradient shortcut** — differentiating the stored
   pressure with the affine jump operator should cure the pressure oscillation.
3. **Curvature/Young--Laplace RHS defect** — the pressure jump is only as good
   as the cut-face curvature `κ_Γ`; if `κ_Γ` has high-frequency noise, the PPE
   receives a nonphysical pressure-jump source.
4. **Dynamic grid as root cause** — every-step fitted-grid rebuild is the
   primary source of the curvature noise.
5. **Reinitialization absence as root cause** — enabling ridge-eikonal
   reinitialization should restore the curvature contract.

## Diagnostics Added

- `experiment/ch14/diagnose_pressure_variable_contract_n64.py`
  records `pressure_increment - last_base_pressure`, accumulated physical/base
  pressure differences, and affine face-flux differences.
- `experiment/ch14/diagnose_curvature_contract_n64.py`
  records nodal interface-band curvature, the exact cut-face curvature used by
  `signed_pressure_jump_gradient()`, and cut-face radius Fourier amplitudes.
- `experiment/ch14/probe_pressure_history_gradient_n64.py`
  now includes base-pressure diagnostic controls:
  `base_corrector`, `base_history`, and `base_corrector_base_history`.

## Results

Pressure-variable contract diagnostic to `T=0.01`:

| metric | value |
|---|---:|
| `pressure_increment_minus_base_rms` | `0.0` |
| `pressure_total_minus_base_rms` | `0.0` |
| `previous_pressure_minus_base_rms` | `0.0` |
| `affine_increment_face_difference_rms` | `0.0` |

The stored pressure/base-pressure representation is not the immediate mismatch.
This also explains why `base_corrector_base_history` exactly matches the normal
baseline.

Short pressure probe to `T=0.40`:

| case | max KE | jump error | liquid RMS | gas RMS |
|---|---:|---:|---:|---:|
| baseline | `4.090994e-04` | `2.445409e-02` | `2.224346e-01` | `1.436939e-02` |
| exact `κ=4` | `6.484994e-05` | `1.282112e-02` | `1.723989e-01` | `4.762186e-03` |
| base corrector + base history | `4.090994e-04` | `2.445409e-02` | `2.224346e-01` | `1.436939e-02` |

Curvature contract diagnostic to `T=0.40`:

| case | final band `κ` std | final cut-face `κ` std | implied cut-face jump std | radius std | `m16` radius amplitude |
|---|---:|---:|---:|---:|---:|
| dynamic grid, no reinit | `2.164945e+01` | `1.066869e+01` | `7.681457e-01` | `5.540336e-04` | `2.238773e-04` |
| static grid | `1.690001e+01` | `7.716113e+00` | `5.555601e-01` | `4.004829e-04` | `1.497551e-04` |
| reinit every 20 | `7.856594e+00` | `1.167190e+01` | `8.403768e-01` | `1.050747e-03` | `9.601384e-04` |

The physical Young--Laplace jump for `R=0.25`, `sigma=0.072` is only `0.288`.
Therefore the computed cut-face curvature noise alone injects pressure-jump
fluctuations larger than the target static pressure jump.

## Inference

The closest root cause is not the PPE/DC stack selection and not a base-vs-
physical pressure storage mismatch.  It is the interface-geometry contract:
the pressure-jump RHS uses `j_gl = -sigma * κ_Γ`, but the current
`ψ`-differentiated, nodal-band curvature field produces large high-frequency
cut-face `κ_Γ` even while the visible radius error remains subcell-small.

Mathematically this is plausible: curvature is a second-derivative quantity, so
tiny grid-scale interface perturbations or profile errors are amplified roughly
like `m^2 * δr / R^2`.  A static circle can therefore have small deformation
and still receive a large oscillatory Young--Laplace pressure jump.

Dynamic fitted-grid rebuilds amplify the defect but do not cause it alone:
static-grid cut-face `κ` std remains `~7.7`.  Ridge-eikonal reinitialization at
`every_steps=20` improves broad-band `κ` but worsens cut-face `κ` and `m16`
radius amplitude; it is not a fix in this stack.

## Next Theory-Respecting Direction

Do not tune CFL, alpha, damping, or broad smoothing as a fix.  The next
implementation unit should enforce the actual GFM/PPE contract:

1. compute or reconstruct `κ_Γ` directly on cut faces,
2. use that single cut-face `κ_Γ` in the affine pressure-jump RHS and projection
   face flux,
3. verify the static Young--Laplace equilibrium by checking cut-face jump
   statistics before checking long-time kinetic energy.

[SOLID-X] Diagnostic scripts and artifact only; no production algorithm
boundary changed, no tested implementation deleted, and the falsified pressure
history implementation remains backed out.
