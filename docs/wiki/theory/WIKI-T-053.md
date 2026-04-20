---
ref_id: WIKI-T-053
title: "FCCD Calculation Equations via CCD Second-Derivative Closure"
domain: theory
status: PROPOSED  # ResearchArchitect review; PoC implementation pending
superseded_by: null
sources:
  - path: docs/wiki/theory/WIKI-T-046.md
    description: Uniform FCCD operator and H-01 motivation
  - path: docs/wiki/theory/WIKI-T-050.md
    description: Non-uniform FCCD Taylor coefficients mu/lambda/nu
  - path: paper/sections/04_ccd.tex
    description: Chu-Fan CCD derivation method used by the paper
  - path: paper/sections/appendix_ccd_coef_s1.tex
    description: Taylor matching for CCD Equation-I/II
  - path: src/twophase/ccd/ccd_solver.py
    description: Existing implementation returns d1 and d2, not d3
depends_on:
  - "[[WIKI-T-001]]: CCD Method: Design Rationale and O(h^6) Compactness"
  - "[[WIKI-T-046]]: FCCD operator definition"
  - "[[WIKI-T-050]]: FCCD non-uniform cancellation coefficients"
  - "[[WIKI-T-051]]: FCCD wall-face boundary handling"
  - "[[WIKI-T-052]]: R-1.5 zeroth-order face-gradient baseline"
consumers:
  - domain: code
    description: Future FCCDOperator implementation should use q = D_CCD^(2)u as the closure variable
  - domain: cross-domain
    description: WIKI-X-018 R-1 PoC equation set
tags: [ccd, fccd, face_gradient, second_derivative_closure, h01_remediation, research_proposal]
compiled_by: Codex GPT-5
compiled_at: "2026-04-20"
---

# FCCD Calculation Equations via CCD Second-Derivative Closure

## ResearchArchitect verdict

The FCCD Taylor coefficients in [WIKI-T-046](WIKI-T-046.md) and [WIKI-T-050](WIKI-T-050.md) are algebraically usable, but the phrase "obtain $\tilde u'''_f$ from Chu-Fan combined relations" is not yet an executable equation. The paper's CCD derivation solves a coupled system for $(u'_i, u''_i)$, not for $u'''_i$.

Therefore the first FCCD PoC should close the third-derivative correction through the existing CCD second derivative:

$$
q_i \;:=\; (D_{\mathrm{CCD}}^{(2)}u)_i \;\approx\; u''(x_i),
\qquad
\tilde u'''_f \;\leftarrow\; \frac{q_i-q_{i-1}}{H}.
$$

This preserves the Chu-Fan method used in the paper: introduce auxiliary derivatives, determine coefficients by Taylor cancellation, and eliminate auxiliary quantities into a compact computable operator.

## Equation chain

### 1. Paper CCD source equation

The paper's CCD system is

$$
\alpha_1 u'_{i-1} + u'_i + \alpha_1 u'_{i+1}
= \frac{a_1}{h}(u_{i+1}-u_{i-1})
  + b_1 h (u''_{i+1}-u''_{i-1}),
$$

$$
\beta_2 u''_{i-1} + u''_i + \beta_2 u''_{i+1}
= \frac{a_2}{h^2}(u_{i-1}-2u_i+u_{i+1})
  + \frac{b_2}{h}(u'_{i+1}-u'_{i-1}),
$$

with

$$
\alpha_1=\frac{7}{16},\quad a_1=\frac{15}{16},\quad b_1=\frac{1}{16},
\qquad
\beta_2=-\frac18,\quad a_2=3,\quad b_2=-\frac98 .
$$

Solving this system gives nodal $(u'_i,q_i)$ where $q_i=u''_i$.

### 2. Uniform-grid FCCD calculation

For a face $f=i-\tfrac12$ and $H=\Delta x$,

$$
\frac{u_i-u_{i-1}}{H}
= u'_f + \frac{H^2}{24}u'''_f + \mathcal{O}(H^4).
$$

Using the CCD second derivative,

$$
\tilde u'''_f
= \frac{q_i-q_{i-1}}{H}
= u'''_f + \mathcal{O}(H^2)
$$

on a uniform grid. The executable FCCD face gradient is therefore

$$
\boxed{\;
D^{\mathrm{FCCD}}u_f
= \frac{u_i-u_{i-1}}{H}
  - \frac{H}{24}(q_i-q_{i-1})
\;}
$$

and it satisfies

$$
D^{\mathrm{FCCD}}u_f = u'_f + \mathcal{O}(H^4).
$$

No new $u'''$ unknown is required.

### 3. Non-uniform FCCD calculation

Let

$$
h_L = x_f-x_{i-1},\qquad
h_R = x_i-x_f,\qquad
H=h_L+h_R,\qquad
\theta=\frac{h_R}{H}.
$$

[WIKI-T-050](WIKI-T-050.md) gives

$$
\mu(\theta)=\theta-\frac12,
\qquad
\lambda(\theta)=\frac{1-3\theta(1-\theta)}{6}.
$$

Close the two correction terms using the CCD second derivative:

$$
\tilde u''_f
= \theta q_{i-1} + (1-\theta)q_i,
\qquad
\tilde u'''_f
= \frac{q_i-q_{i-1}}{H}.
$$

The executable non-uniform FCCD face gradient is

$$
\boxed{\;
D^{\mathrm{FCCD,nu}}u_f
= \frac{u_i-u_{i-1}}{H}
  - \mu(\theta)H\left[\theta q_{i-1}+(1-\theta)q_i\right]
  - \lambda(\theta)H(q_i-q_{i-1})
\;}
$$

with expected local accuracy

$$
D^{\mathrm{FCCD,nu}}u_f
= u'_f + \mathcal{O}(H^3)
$$

for general non-uniform faces, recovering the uniform $\mathcal{O}(H^4)$ formula when $\theta=1/2$.

### 4. Zeroth-order reduction

Dropping the two CCD correction terms gives

$$
D^{(0)}u_f = \frac{u_i-u_{i-1}}{H},
$$

which is the [WIKI-T-052](WIKI-T-052.md) / $G^{\mathrm{adj}}$ baseline. Thus R-1.5 is the zeroth-order member of the same face-locus operator family.

## A3 traceability

| Layer | Decision |
|---|---|
| Equation | Use paper CCD Equation-I/II to compute $q_i=(D_{\mathrm{CCD}}^{(2)}u)_i$. |
| Discretization | Replace $\tilde u'''_f$ by $(q_i-q_{i-1})/H$ and $\tilde u''_f$ by a face interpolation of $q$. |
| Code | Call `CCDSolver.differentiate(u, axis)` and use the returned `d2` field as `q`. |
| Balanced-force | Apply the same FCCD face-gradient function to both $p$ and $\psi$. |

## Implementation implications

- **Native face-CCD is not needed for PoC-1.** The existing node CCD solve already supplies the required $q_i$.
- **The FCCD operator should return face arrays first.** Node-centred correction can be recovered by adjacent-face averaging only where the caller still requires nodal storage.
- **Use physical-space `d2` with physical face spacings.** If `apply_metric=False` is chosen, the entire FCCD formula must be written in $\xi$ space instead.
- **Wall handling follows WIKI-T-051.** For Neumann fields, wall-face gradients are prescribed as zero; interior faces use the formula above.
- **GPU path follows existing CCD rules.** Array operations must use `backend.xp`; face coefficients $\mu,\lambda,H,\theta$ should be precomputed per axis.

## Open checks

1. Verify the boxed equations by symbolic Taylor expansion in the PoC notebook or unit test.
2. Measure uniform-grid order for $u=\sin(2\pi x)$ using the existing `CCDSolver.differentiate` output.
3. Measure stretched-grid order using physical-space `d2`; if WIKI-T-039 metric error dominates, repeat in $\xi$ space to isolate FCCD algebra from metric conversion.
4. Compare BF residuals for node-CCD, R-1.5, and FCCD-unified on the WIKI-E-030 capillary case.

## Research note

The key correction to SP-A wording is interpretive, not algebraic: $u'''_f$ should be read as a derived face quantity from nodal CCD second derivatives, not as a new member of the Chu-Fan unknown vector. This keeps FCCD faithful to the paper's CCD derivation method and makes the R-1 PoC implementable without a new block system.
