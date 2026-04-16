---
ref_id: WIKI-T-035
title: "Non-Uniform Grid Error Decomposition: 5-Component Taxonomy and DCCD Rescue Limits"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/理論_非一様格子でのCCD劣化機構とDCCD救済限界.md"
    description: "Theory short-paper: CCD degradation mechanism on non-uniform grids and DCCD rescue scope"
  - path: "experiment/ch12/exp12_19_gfm_nonuniform_ablation.py"
    description: "GPU A/B ablation: CSF vs GFM × uniform vs non-uniform — all 4 cases FAIL <10 steps"
  - path: "experiment/ch11/exp11_33_metric_dccd_ablation.py"
    description: "Metric-DCCD filter experiment: Jacobian smoothing effect on derivative accuracy"
consumers:
  - domain: E
    usage: "exp12_19 result interpretation; future non-uniform verification experiments"
  - domain: X
    usage: "WIKI-X-012 theoretical companion; WIKI-X-014 stability budget"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-031]]"
  - "[[WIKI-X-012]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Non-Uniform Grid Error Decomposition

**Relation to [[WIKI-X-012]]:** WIKI-X-012 documents the phenomenological instability
modes (Mode 1: rebuild metric discontinuity, Mode 2: static CCD amplification).
This entry provides the mathematical root-cause decomposition explaining *why*
those modes arise and what DCCD can/cannot fix.

---

## 1. Coordinate Transform and Metric Sensitivity

On a non-uniform grid the physical-space derivatives are:

$$
\frac{\partial f}{\partial x} = J_x \frac{\partial f}{\partial \xi}, \qquad
\frac{\partial^2 f}{\partial x^2} = J_x^2 \frac{\partial^2 f}{\partial \xi^2}
  + J_x \frac{\partial J_x}{\partial \xi} \frac{\partial f}{\partial \xi}
$$

The cross-term $J_x (\partial_\xi J_x) f_\xi$ makes the second derivative
accuracy jointly dependent on the metric quantities $J_x$, $\partial_\xi J_x$
and the computational-space derivatives $f_\xi$, $f_{\xi\xi}$.

---

## 2. The 5-Component Error Taxonomy

$$
E_{\text{total}} = E_{\text{metric}} + E_{\text{operator}} + E_{\text{reinit/geometry}} + E_{\text{time-coupling}} + E_{\text{HF-noise}}
$$

### $E_{\text{metric}}$ — Metric Evaluation Error

With discrete error orders $\delta(f_\xi) = O(h^p)$, $\delta(J_x) = O(h^q)$,
$\delta(\partial_\xi J_x) = O(h^r)$, the $f_{xx}$ error expands as:

$$
\delta(f_{xx}) \sim 2 J_x \,\delta J_x \, f_{\xi\xi}
  + J_x^2 \,\delta(f_{\xi\xi})
  + \delta J_x (\partial_\xi J_x) f_\xi
  + J_x \,\delta(\partial_\xi J_x) f_\xi
  + J_x (\partial_\xi J_x) \delta(f_\xi)
$$

If $q$ or $r$ is lower than $p$, the metric terms dominate.

### $E_{\text{operator}}$ — Pre-Asymptotic Regime

CCD is nominally $O(h^6)$ but requires sufficient resolution to exit the
pre-asymptotic regime. At $N \le 128$ with $\alpha = 2$, empirical convergence
order oscillates between 3.4 and 7.9 (exp11_04).

### $E_{\text{reinit/geometry}}$ — Reinitialization Width Mismatch

The reinitializer's uniform-grid-width assumption causes local CFL violation
on coarse cells. Quantified: mass error 23% before DGR, recovered to $2.6\times10^{-4}$
after DGR ([[WIKI-T-030]]).

### $E_{\text{time-coupling}}$ — Geometric–Temporal Resonance

Grid rebuild at step $k$ creates a metric discontinuity that is amplified by
all subsequent CCD solves. Repeated rebuild/interpolate/reinitialize/CSF cycles
can produce resonant error growth.

### $E_{\text{HF-noise}}$ — High-Frequency Oscillation

Grid-scale noise from CCD stencil edge effects and interpolation aliasing.
**This is the only component DCCD directly addresses.**

---

## 3. DCCD Rescue Scope

DCCD 3-point filter transfer function:

$$
H(\xi; \varepsilon_d) = 1 - 4\varepsilon_d \sin^2(\xi/2)
$$

At $\varepsilon_d = 1/4$ the Nyquist mode is zeroed.

| Error Component | DCCD Addressable? | Fix Path |
|---|---|---|
| $E_{\text{metric}}$ | No | Evaluate $J_x$, $\partial_\xi J_x$ at CCD operator order |
| $E_{\text{operator}}$ | No | Increase $N$ beyond pre-asymptotic threshold (~256) |
| $E_{\text{reinit/geometry}}$ | No | DGR with local grid width ([[WIKI-T-030]]) |
| $E_{\text{time-coupling}}$ | No | Reduce `rebuild_freq`, calibrate to interface velocity |
| $E_{\text{HF-noise}}$ | **Yes** | DCCD filter (high-frequency stabilizer) |

---

## 4. GCL Pass $\ne$ High-Order Accuracy

The Geometric Conservation Law guarantees no spurious conservation violation for
constant fields, but does **not** guarantee $f_{xx}$ accuracy. Machine-precision
GCL satisfaction can coexist with order oscillation $p = 3.4 \ldots 7.9$ at
$N \le 128$.

---

## 5. Grid Generation Error Floor

If the coordinate mapping $x(\xi)$ is built by trapezoidal quadrature of a
spacing function, the map itself has $O(\Delta\xi^2)$ error. This imposes an
accuracy floor independent of the CCD operator order and explains why ideal
high-order theory cannot be applied directly to the discrete map.

---

## 6. Experimental Evidence (exp12_19)

GPU A/B ablation — CSF vs GFM $\times$ uniform vs non-uniform on a static
droplet ($N=64$, 20 steps, $\text{Re}=100$, $\text{We}=10$):

| Case | step_fail | Implication |
|---|---|---|
| uniform_csf | 8 | Uniform grid also fails |
| uniform_gfm | 9 | GFM delays by 1 step |
| nonuniform_csf | 9 | Non-uniform is not sole cause |
| nonuniform_gfm | 10 | GFM delays by 1 step |

All 4 cases blow up within 10 steps. GFM delays but does not stabilize.
Non-uniform grid alone is not the dominant factor — $E_{\text{reinit/geometry}}$
and $E_{\text{time-coupling}}$ are the primary contributors.

---

## 7. Implementation Requirements (Minimum)

1. $J_x$ and $\partial_\xi J_x$ must be evaluated at the same order as the CCD operator.
2. Reinitialization on non-uniform grids must use local grid-width (DGR).
3. DCCD is a high-frequency stabilizer, not a substitute for metric correction.
4. Verification must go beyond GCL pass/fail — use MMS with 2nd-order transform terms.

---

## One-Line Summary

Non-uniform grid degradation decomposes into 5 error components; DCCD addresses
only high-frequency noise — metric, reinit, and time-coupling fixes are prerequisites.
