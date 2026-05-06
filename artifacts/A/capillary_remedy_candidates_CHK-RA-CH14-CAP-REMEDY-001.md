# CHK-RA-CH14-CAP-REMEDY-001 - Remedy Candidates for Closed-Interface Capillary Cochain Mismatch

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Problem Restatement

Previous RCA established:

```text
local cut-face B_Gamma(j) notin range(A_f G_f)
```

for curved closed interfaces.  The current affine jump/FCCD complex is exact
for compatible flat jumps, but a static circular Young--Laplace jump leaves an
O(4-5%) weighted Hodge residual.  Production `range_projected` then removes
that residual by replacing the whole cochain with its range part, but this also
removes the true oscillating-ellipse capillary drive.

The remedy must satisfy:

```text
G1 static circle:        P_h c = 0 for constant Young-Laplace jump
G2 dynamic ellipse:      P_h c != 0 for nonconstant constrained curvature mode
G3 energy contract:      face work equals -delta(sigma S_h - lambda V_h)
G4 same complex:         same D_f, A_f, G_f as PPE/corrector
G5 no shortcuts:         no damping/CFL/caps/smoothing/FD/WENO/PPE fallback
G6 reinit separation:    do not mix Pi_h reinitialization work with capillary work
```

## Key Theorem For Selection

For a closed incompressible droplet, the pressure can absorb only the
component-wise Young--Laplace Lagrange multiplier:

```text
lambda_m = sigma * kappa_bar_m,
delta(sigma S - lambda_m V) = 0   for a static circular component.
```

Therefore a valid production cochain must make the constant component exact
without deleting the nonconstant shape modes.  This is the narrow path between
the two known failures:

```text
full raw local jump      -> moves, but static circle has parasitic Hodge work
blanket range projection -> static, but dynamic ellipse is killed
```

## Candidate List And Theory Verdicts

| ID | Idea | Theory verdict |
|---|---|---|
| R01 | Set `capillary_range_projection:none`. | Reject. Restores motion but applies the static-circle parasitic Hodge residual. |
| R02 | Keep `range_projected` only for static droplet YAMLs and `none` for oscillating YAMLs. | Reject. Benchmark-name branch, not physics. |
| R03 | Damping, smaller CFL, curvature cap, or smoothing. | Reject. These hide energy/cochain errors and violate the problem contract. |
| R04 | FD/WENO/PPE fallback. | Reject. Violates project algorithm fidelity and does not repair the cochain complex. |
| R05 | Use current `transport_variational_p2` with a volume multiplier. | Reject. RCA showed relative Hodge about 1 for static circle even with `lambda`; it fails before dynamics. |
| R06 | Use diffuse nodal pressure `q ~ psi` or phase-step `q ~ 1_phase` as the exact jump lifting. | Reject as exact fix. Best phase-step mismatch is about 20%; diffuse candidates are O(1). |
| R07 | Make every capillary jump exact by defining `c = A_f G_f q_lift(j)`. | Reject. If all nonconstant jumps are range, dynamic capillary drive is killed. |
| R08 | Subtract the component-wise mean curvature from curvature before building the affine jump: `kappa' = kappa - kappa_bar`. | Promising but incomplete. It enforces the continuum constrained force and zeros a static circle, but loses pressure-contrast representation unless mean jump is recorded separately. |
| R09 | Build `c_dyn = B_Gamma(sigma(kappa-kappa_bar))` and store `lambda=sigma*kappa_bar` as diagnostic pressure contrast only. | Promising for velocity dynamics, weaker for pressure diagnostics. Good first diagnostic branch, not final pressure law. |
| R10 | Range-calibrated Young--Laplace null mode: `c = Pi_R c_bar + (c_raw(kappa) - c_raw(kappa_bar))`. | Strongly promising. Static circle gives exact range cochain; nonconstant modes are preserved. Uses range projection only for the physically pressure-like scalar null mode, not the whole capillary force. |
| R11 | Hodge-null calibration form: `c = c_raw(kappa) - H(c_raw(kappa_bar))`, where `H=I-Pi_R`. | Strongly promising and equivalent to R10 algebraically. It removes only the known spurious closed-interface residual of the constant mode. |
| R12 | Choose `kappa_bar_h` by interface quadrature mean curvature. | Promising as first definition, but must pass discrete static gates. |
| R13 | Choose `kappa_bar_h` by discrete constrained variation `delta S_h / delta V_h`. | Stronger than R12. Best theoretical definition because it matches the energy constraint. |
| R14 | Choose `kappa_bar_h` as scalar minimizing `||P_h B_Gamma(kappa-kappa_bar)||_{A^-1}`. | Conditionally promising. Scalar-only minimization cannot erase nonconstant modes, but it must be proven equivalent or close to discrete `delta S_h/delta V_h`, not used as arbitrary tuning. |
| R15 | Component-wise version for multiple droplets: one `kappa_bar_m` per connected interface component. | Required for generality. A single global mean is physically wrong for multiple radii. |
| R16 | Use a harmonic/cohomology basis and remove only the constant Young--Laplace harmonic residue per component. | Promising theoretical framing for R10/R11; useful if the residual is a closed-interface harmonic artifact. |
| R17 | Enrich the pressure space with one Heaviside/jump DOF per connected component. | Strongly promising but heavier. Constant jumps become exact operator DOFs; nonconstant modes still drive. |
| R18 | Full GFM/HFE pressure-jump lifting with a component jump unknown and variable residual along interface. | Strongly promising, medium/high effort. This is an operator-level exactness fix. |
| R19 | Interface-fitted/cut-cell pressure operator where constant closed-interface jumps are exact by construction. | Promising long-term, high implementation cost and larger blast radius. |
| R20 | Build capillarity as a discrete surface-stress divergence rather than scalar pressure jump. | Promising only if derived as `T_h^* dS_h` in the same face space; otherwise it risks becoming CSF fallback. |
| R21 | Polygonal interface virtual-work cochain: define `S_h` and `V_h` from the reconstructed closed curve and differentiate them with respect to face-normal transport. | Gold-standard theory. High effort but cleanest energy proof. |
| R22 | Finite-step Gonzalez/discrete-gradient version of R21 for time integration. | Strong long-term companion to R21; needed for energy ledger over finite steps. |
| R23 | Use `range_projected` as a static-equilibrium gate only, failing production if the static null mode residual exceeds tolerance. | Required diagnostic, not a remedy alone. |
| R24 | Let reinitialization absorb residual geometry errors. | Reject. Reinit is a representation projection, not capillary work. |
| R25 | Hybrid safe rollout: first implement R10/R11 as diagnostic-only cochain variant, then gate static circle and ellipse before enabling corrector. | Strongly promising as process. It avoids silently replacing physics. |

## Theoretical Screening

### Gate G1 - Static Circle Exactness

R08/R09 pass by construction if `kappa_bar` equals the constant circle
curvature, because `kappa-kappa_bar=0`.  However, they remove the mean jump
from the velocity cochain entirely.  That is physically acceptable for velocity
because the mean jump is a pressure Lagrange multiplier, but pressure contrast
must be reconstructed separately.

R10/R11 pass more completely:

```text
c_raw(kappa_bar) = Pi_R c_raw(kappa_bar) + H c_raw(kappa_bar)
c = c_raw(kappa_bar) - H c_raw(kappa_bar)
  = Pi_R c_raw(kappa_bar)
```

The corrector then yields zero acceleration for a zero-predictor static
circle because the cochain is exactly pressure-range.  Unlike blanket range
projection, this replacement is restricted to the constant Young--Laplace
null mode.

R17/R18/R19 also pass by adding pressure-space structure so a constant
closed-interface jump is exact by construction.

### Gate G2 - Dynamic Ellipse Release

The continuum capillary drive for a fixed-area closed curve is controlled by
the nonconstant curvature mode:

```text
delta E = -sigma integral_Gamma (kappa - kappa_bar) u_n ds.
```

R08/R09/R10/R11 preserve `B_Gamma(kappa-kappa_bar)`.  Therefore an ellipse,
whose curvature is not constant, retains nonzero admissible capillary work.
They do not delete the dynamic Hodge component unless `kappa` is constant.

R17/R18/R19 preserve dynamics if the enriched pressure handles only the
component jump scalar exactly and leaves variable jump content to the same
PPE/corrector residual mechanism.

R07 fails here: exact-lifting all jump content makes all capillarity pressure
range and kills release.

### Gate G3 - Energy Contract

R10/R11 are acceptable only if `kappa_bar_h` is chosen from a discrete
constrained energy relation, not from visual tuning:

```text
kappa_bar_h = (delta S_h / delta V_h)_component.
```

For a circle this recovers `1/R`; for general closed shapes it removes only
the component-wise pressure multiplier.  R13 is therefore preferred over R12.

R21 is strongest because it derives the whole cochain from

```text
T_h^* d(sigma S_h - lambda_h V_h)
```

directly, rather than correcting a local jump after the fact.

### Gate G4 - Same PPE Complex

R10/R11 explicitly use the same `Pi_R` and weighted Hodge split already
computed from `(D_f,A_f,G_f)`, so their static calibration is in the correct
complex.  This is why they are more credible than ad hoc curvature smoothing.

R17/R18/R19 also satisfy G4 only if the PPE/corrector both consume the same
augmented operator.  A diagnostic-only pressure enrichment that is not used by
the corrector would fail.

### Gate G5 - No Shortcut Policy

R01-R07, R24 fail or are incomplete because they either erase dynamic physics,
hide the symptom, or do not repair the cochain contract.

R10/R11/R13/R15/R17/R18/R21/R22/R23/R25 are compatible with the no-shortcut
policy because they state verifiable mathematical invariants.

## Extracted Promising Set

### A. Range-Calibrated Young--Laplace Null Mode

Definition:

```text
c_bar = B_Gamma(sigma kappa_bar_h)
c_dyn = B_Gamma(sigma (kappa - kappa_bar_h))
c_prod = Pi_R(c_bar) + c_dyn
       = c_raw(kappa) - H(c_bar)
```

Why it is promising:

- exact static circle by construction;
- preserves nonconstant curvature modes;
- uses range projection only for the physically pressure-like scalar
  Lagrange multiplier;
- minimal blast radius because it can sit inside the existing affine-jump
  diagnostics/corrector path;
- supports component-wise multiple droplets.

Required proof/tests:

```text
static circle:        ||P_h c_prod||_w / ||c_prod||_w -> roundoff/small tolerance
oscillating ellipse:  ||P_h c_prod||_w remains clearly nonzero
flat wall jump:       unchanged exactness
constant square:      no regression
```

This is the best near-term candidate.

### B. Discrete Constrained Curvature Mean

Definition:

```text
kappa_bar_h = (delta S_h / delta V_h)_component
```

or, as a controlled first approximation, an interface-quadrature mean that
must be shown to agree with the discrete constrained variation on static
circles.

Why it is promising:

- gives R10/R11 a physical scalar, not a tuning parameter;
- handles different droplet radii component-wise;
- ties the correction to the same area/volume constraint as Rayleigh--Lamb.

Required proof/tests:

```text
circle radius R:      kappa_bar_h -> 1/R
ellipse same area:    kappa_bar_h is scalar pressure multiplier only
multiple droplets:    one scalar per component, not global mean
```

This is a necessary companion to A.

### C. Enriched Pressure-Jump DOF Per Interface Component

Definition:

Augment the pressure solve with a component jump scalar so that constant
Young--Laplace jumps are in the pressure space exactly, while variable
curvature content remains a residual drive.

Why it is promising:

- repairs the operator rather than correcting the cochain afterward;
- matches GFM/XFEM intuition without FD/WENO fallback;
- pressure contrast becomes native rather than diagnostic-only.

Cost/risk:

- larger implementation surface: PPE operator, corrector, pressure history,
  gauge, and HFE representatives must all share the augmented complex.

This is a strong medium-term candidate.

### D. Polygonal Surface-Energy Virtual-Work Cochain

Definition:

Use the reconstructed closed interface polygon to define `S_h` and `V_h`;
differentiate `sigma S_h - lambda_h V_h` through the actual face transport map
to obtain the face covector.

Why it is promising:

- cleanest variational proof;
- static and dynamic behavior come from one energy;
- compatible with finite-step energy ledgers if extended by a Gonzalez
  discrete gradient.

Cost/risk:

- highest implementation cost;
- must handle topology, component labeling, cut-point derivatives, and reinit
  separation carefully.

This is the gold-standard long-term candidate.

### E. Gate-First Rollout

Before any production corrector change, add an experimental/diagnostic route
that computes A/B candidates and reports:

```text
raw_static_rel
nullmode_calibrated_static_rel
ellipse_dynamic_rel
flat_exact_rel
component_count
kappa_bar_h
```

Why it is promising:

- prevents another silent `range_projected`-style overgeneralization;
- makes the theory falsifiable before enabling motion;
- keeps reinit and capillary work separated.

This is required process, not optional polish.

## Recommended Order

1. Implement diagnostic-only R10/R11 with component-wise `kappa_bar_h`.
2. Define `kappa_bar_h` first by robust interface quadrature, then compare to
   discrete `delta S_h/delta V_h` on circles and ellipses.
3. Run gates: flat wall, static circle, canonical oscillating ellipse, square
   negative/positive controls.
4. Only if gates pass, enable full `c_prod` in the corrector for a temporary
   experiment config.
5. In parallel or next phase, design enriched pressure-jump DOF or polygonal
   virtual-work cochain for a theorem-grade production route.

## Final Selection

Most promising near-term path:

```text
Range-Calibrated Young--Laplace Null Mode
  + component-wise discrete kappa_bar_h
  + diagnostic-first gates
```

Most rigorous long-term path:

```text
Polygonal closed-interface virtual-work cochain
  or augmented pressure-jump DOF per component
```

Rejected explicitly:

```text
blanket range projection,
none-only production,
damping/CFL/caps/smoothing,
FD/WENO/PPE fallback,
QP/range projection as physical capillarity,
current P2 route with only lambda patched in.
```

[SOLID-X] Theory/design artifact only; no production solver/config/YAML
behavior changed; no tested implementation deleted; no FD/WENO/PPE fallback
introduced.
