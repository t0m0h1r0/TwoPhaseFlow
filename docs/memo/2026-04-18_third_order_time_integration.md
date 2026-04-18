# Third-Order Time Integration for Two-Phase CLS–Navier–Stokes

**Compiled by**: ResearchArchitect
**Date**: 2026-04-18
**Branch**: `worktree-research-third-order-time-evolution`
**Status**: Theory proposal (no code, no experiment)
**Compiled into**: [[WIKI-T-041]]

---

## 1. Introduction and Motivation

The current solver's global time-integration order is **$O(\Delta t^2)$**
([paper §5](../../paper/sections/05_time_integration.tex), [§12c](../../paper/sections/12c_time_accuracy.tex),
[§12h error budget](../../paper/sections/12h_error_budget.tex), [[WIKI-T-003]], [[WIKI-P-002]]).
The spatial budget, in contrast, is $O(h^6)$ for CCD differentiation ([[WIKI-T-001]]) and
realised as $O(h^{5.97})$ experimentally ([[WIKI-E-005]], [[WIKI-E-013]]). With $h$ refinement
already dropping spatial error $\sim 10^{-7}$ at $N=64$, **temporal error $O(\Delta t^2)$
becomes the dominant contribution** for any $\Delta t \gtrsim h^3$.

The CLS interface transport is already $O(\Delta t^3)$ via Shu–Osher TVD-RK3
([paper §5.1](../../paper/sections/05_time_integration.tex#L17-L42)). The paper explicitly notes
the asymmetry "CLS is $O(\Delta t^3)$ but overall is $O(\Delta t^2)$"
([§5, lines 153–172](../../paper/sections/05_time_integration.tex#L153-L172)) and attributes the
ceiling to three NS-side operators: AB2 convection, IPC pressure split, and CN viscous.
Cross-derivative viscous is additionally $O(\Delta t^1)$ near high-$\mu$-ratio interfaces
([§12h table, row 39](../../paper/sections/12h_error_budget.tex#L39)).

**Goal of this note**: establish a rigorous theory and design for raising the global NS+CLS
temporal order to $O(\Delta t^3)$, reusing existing project infrastructure where possible.

---

## 2. Rate-Limiter Taxonomy

Every time-integration operator in the solver, its current order, and what must change:

| # | Operator | Current order | Required upgrade | Mechanism |
|---|---|---|---|---|
| 1 | CLS advection | $O(\Delta t^3)$ | — | TVD-RK3 unchanged |
| 2 | CLS reinit compression | $O(\Delta t^1)$ (FE) | $O(\Delta t^3)$ | RK3 compression step |
| 3 | CLS reinit diffusion | $O(\Delta t^2)$ (CN-ADI) | $O(\Delta t^3)$ | Richardson-CN pseudo-time |
| 4 | NS convection | $O(\Delta t^2)$ (AB2) | $O(\Delta t^3)$ | **AB3** extrapolation |
| 5 | NS viscous diagonal | $O(\Delta t^2)$ (Picard-CN) | $O(\Delta t^3)$ | **Richardson(Picard-CN)** — already implemented ([[WIKI-T-033]]) |
| 6 | NS viscous cross-term | $O(\Delta t^1)$ explicit | $O(\Delta t^3)$ | **AB3 extrapolation** of $\mathcal{D}_{\mathrm{c}}$ |
| 7 | Pressure splitting | $O(\Delta t^2)$ (IPC, van Kan) | $O(\Delta t^{5/2})$ $p$ / $O(\Delta t^3)$ $\mathbf{u}$ | **Rotational IPC** (Guermond–Shen 2003) |
| 8 | ADI directional split | $O(\Delta t^2)$ (Peaceman–Rachford) | $O(\Delta t^2)$ (kept) | Absorbed into IPC error |

Operator 1 already meets target. Operators 2–3 (reinit pseudo-time) do not contaminate NS
temporal order because reinit is operator-split and operates on a pseudo-time $\tau$
decoupled from physical $t$; we leave them $O(\Delta t^2)$. The **four binding changes**
are operators 4, 5, 6, 7.

**Key insight**: operator 5 (Richardson-CN) is already implemented in the codebase
([`cn_advance/richardson_cn.py`](../../src/twophase/time_integration/cn_advance/richardson_cn.py),
selected via `config.numerics.cn_mode="richardson_picard"`) and verified at $O(\Delta t^3)$
([[WIKI-T-033]] §Richardson family). The remaining three changes are the new theoretical
content of this note.

---

## 3. Route Analysis

Three classical routes are compared on six axes.

### Route A — KIO stiffly-stable multistep (Karniadakis–Israeli–Orszag 1991)

Unified BDF3 time derivative + AB3 convection + fully implicit viscous + consistent
pressure BC:
$$
\frac{11\mathbf{u}^{n+1} - 18\mathbf{u}^n + 9\mathbf{u}^{n-1} - 2\mathbf{u}^{n-2}}{6\Delta t}
= 3\mathbf{N}^n - 3\mathbf{N}^{n-1} + \mathbf{N}^{n-2} + \nu\nabla^2\mathbf{u}^{n+1}
- \nabla p^{n+1} + \mathbf{f}^{n+1}
$$
with boundary condition $\partial p/\partial n|_{\mathrm{wall}} = \nu(\nabla\times\nabla\times\mathbf{u}^{n+1})\cdot\mathbf{n}$.

| Axis | Evaluation |
|---|---|
| Order chain | Clean $O(\Delta t^3)$ for all terms |
| Cross-term | Implicit — **destroys ADI tridiagonal structure** |
| Startup | BDF3 needs $n$, $n{-}1$, $n{-}2$; bootstrap ramp required |
| ADI compat | **Lost** unless cross-term treated explicitly |
| Effort | Large (new timestepper, pressure BC modification, block solver) |
| Risk | Known to work; well-tested in spectral element codes |

### Route B — Component-wise upgrade (recommended)

AB3 convection + Richardson(Picard-CN) viscous + AB3 cross-term + Rotational IPC pressure.

| Axis | Evaluation |
|---|---|
| Order chain | $O(\Delta t^3)$ velocity, $O(\Delta t^{5/2})$ pressure $L^2$ |
| Cross-term | Explicit AB3 extrapolation on RHS — **preserves ADI** |
| Startup | AB3 needs 3 history levels; natural extension of AB2 startup |
| ADI compat | **Fully preserved** — Thomas structure untouched |
| Effort | Small–Medium (~50 lines across 3 files; Richardson-CN already shipped) |
| Risk | AB3 imaginary-axis instability; rotational term at high $\mu$ ratio |

### Route C — SDIRK3 (Alexander 1977, 3-stage L-stable)

Single-step 3-stage DIRK with $\alpha \approx 0.4358665$ diagonal, PPE per stage:
$$
\mathbf{u}^{(i)} = \mathbf{u}^n + \Delta t\sum_{j=1}^{i} a_{ij}\,\bigl[\nu\nabla^2\mathbf{u}^{(j)} - \mathbf{N}^{(j)} - \nabla p^{(j)}\bigr], \quad i=1,2,3.
$$

| Axis | Evaluation |
|---|---|
| Order chain | Clean $O(\Delta t^3)$ all terms |
| Cross-term | Implicit per stage — couples $u$–$v$ |
| Startup | **Self-starting** from $\mathbf{u}^n$ alone |
| ADI compat | Lost unless cross-term explicit within each stage |
| Effort | Large (3 PPE solves/step = 3× cost; stage orchestration) |
| Risk | L-stability is conservative; IPC-per-stage consistency subtle |

### Recommendation: **Route B**

Decisive criteria:
1. **Richardson-CN already shipped** (operator 5 of §2) — free $O(\Delta t^3)$ for viscous diagonal.
2. **ADI tridiagonal preservation** — AB3 extrapolation of $\mathcal{D}_{\mathrm{c}}$ keeps cross-term on RHS.
3. **Minimal disruption** — AB3 is a 3-line coefficient change + one history buffer; rotational IPC is a 20-line pressure-update patch.
4. **Matches paper's existing footnote** ([§5 line 141](../../paper/sections/05_time_integration.tex#L141):
   "AB2 extrapolation of $\mathcal{D}_{\mathrm{c}}$ is recommended") — AB3 is the natural generalisation.

Route A and C both require dismantling ADI for the cross-term or accepting a residual
$O(\Delta t^1)$ floor that restores the current near-interface degradation.

---

## 4. Recommended Scheme (Route B) — Equation-Level Specification

### 4.1 CLS Step (unchanged)
$$
\psi^{n+1} = \mathrm{TVD\text{-}RK3}\bigl[-\nabla\!\cdot(\psi\mathbf{u}^n),\ \Delta t\bigr], \quad \mathcal{O}(\Delta t^3).
$$

### 4.2 NS Predictor — AB3 Convection + AB3 Cross-Viscous + Richardson-CN Diagonal

Define convection $\mathcal{C}^k := \mathbf{u}^k\!\cdot\!\nabla\mathbf{u}^k$ and
cross-viscous $\mathcal{D}_{\mathrm{c}}^k := \text{cross-}\partial(\mu^k, \mathbf{u}^k)$.
For $n \geq 2$:
$$
\begin{aligned}
\text{AB3 convection:}\quad
\mathbf{N}^{n+\frac{1}{2}} &\;:=\; \tfrac{23}{12}\mathcal{C}^n - \tfrac{16}{12}\mathcal{C}^{n-1} + \tfrac{5}{12}\mathcal{C}^{n-2},\\[2pt]
\text{AB3 cross-visc:}\quad
\mathbf{D_c}^{n+\frac{1}{2}} &\;:=\; \tfrac{23}{12}\mathcal{D}_{\mathrm{c}}^n - \tfrac{16}{12}\mathcal{D}_{\mathrm{c}}^{n-1} + \tfrac{5}{12}\mathcal{D}_{\mathrm{c}}^{n-2}.
\end{aligned}
$$

Explicit RHS:
$$
\mathbf{F}^n \;:=\; -\rho^{n+1}\mathbf{N}^{n+\frac{1}{2}} + \frac{1}{Re}\mathbf{D_c}^{n+\frac{1}{2}} - \nabla p^n + \mathbf{f}^{n+1}.
$$

Diagonal viscous is solved by Richardson(Picard-CN):
$$
\frac{\rho^{n+1}(\mathbf{u}^* - \mathbf{u}^n)}{\Delta t}
= \mathbf{F}^n + \frac{1}{2Re}\bigl[\mathcal{D}_{\mathrm{d}}(\mu^{n+1},\mathbf{u}^*) + \mathcal{D}_{\mathrm{d}}(\mu^n,\mathbf{u}^n)\bigr],
$$
computed via $\Phi_R = \bigl(4\,\Phi_{\Delta t/2}\circ\Phi_{\Delta t/2} - \Phi_{\Delta t}\bigr)/3$
where $\Phi_h$ is the Picard-CN (Heun) step of size $h$. This is the existing
`RichardsonCNAdvance` class.

### 4.3 PPE (IPC increment — unchanged structure)
$$
\nabla\!\cdot\!\left(\frac{1}{\rho^{n+1}}\nabla(\delta p)\right) = \frac{1}{\Delta t}\nabla\!\cdot\mathbf{u}^*.
$$

### 4.4 Corrector — Rotational IPC Pressure Update

Velocity correction (standard IPC):
$$
\mathbf{u}^{n+1} = \mathbf{u}^* - \frac{\Delta t}{\rho^{n+1}}\nabla(\delta p).
$$

Pressure update is **rotational** (Guermond–Shen 2003), replacing $p^{n+1} = p^n + \delta p$:
$$
\boxed{\ p^{n+1} \;=\; p^n + \delta p \;-\; \nu_{\mathrm{eff}}\,\nabla\!\cdot\mathbf{u}^*\ }, \qquad \nu_{\mathrm{eff}} := \mu^{n+1}/\rho^{n+1}.
$$

The rotational correction $-\nu_{\mathrm{eff}}\nabla\!\cdot\mathbf{u}^*$ removes the
artificial pressure boundary layer that limits standard IPC to $O(\Delta t^2)$.

### 4.5 Startup Ramp

| Step | Convection | Cross-visc | Viscous diag | Corrector |
|---|---|---|---|---|
| $n=0$ (FE) | $\mathcal{C}^0$ | $\mathcal{D}_{\mathrm{c}}^0$ | Picard-CN | IPC (standard) |
| $n=1$ (AB2) | $\tfrac{3}{2}\mathcal{C}^1-\tfrac{1}{2}\mathcal{C}^0$ | AB2 on $\mathcal{D}_{\mathrm{c}}$ | Richardson-CN | IPC (rotational) |
| $n\geq 2$ (AB3) | AB3 | AB3 | Richardson-CN | IPC (rotational) |

Startup introduces a local $O(\Delta t^2)$ error. AB3's parasitic roots satisfy the
Dahlquist root condition ($|\rho_j| < 1$ for $j=2,3$) so the error decays geometrically;
asymptotic order $O(\Delta t^3)$ is restored by step $\sim 5$.

### 4.6 History Buffers (new state)

| Buffer | Size | Purpose |
|---|---|---|
| $\mathcal{C}^{n-1}, \mathcal{C}^{n-2}$ | $2\,N_xN_y\,d$ | AB3 convection |
| $\mathcal{D}_{\mathrm{c}}^{n-1}, \mathcal{D}_{\mathrm{c}}^{n-2}$ | $2\,N_xN_y\,d$ | AB3 cross-viscous |

Total additional memory: **$4\,N_xN_y\,d$ reals** (e.g. $4\times 256^2\times 2\times 8\,\mathrm{B} = 4\,\mathrm{MB}$ at $N=256$ in 2D — negligible vs PPE matrix).

---

## 5. Theorems

**Theorem 1 (AB3 zero-stability and imaginary-axis restriction).**
Adams–Bashforth-3 with coefficients $(\beta_0,\beta_1,\beta_2)=(23/12,-16/12,5/12)$
has characteristic polynomial $\rho(z)=z^3-z^2$ and is zero-stable (Dahlquist root condition).
Its absolute stability region excludes the imaginary axis: for $\lambda\in i\mathbb{R}$,
$|z(\lambda\Delta t)|>1$ for any $\lambda\Delta t \neq 0$.
*Capillary implication*: modes with $\omega = \sqrt{\sigma k^3/(\rho_l+\rho_g)}$ require
numerical dissipation from the spatial operator. With DCCD filter $\varepsilon_d=1/4$,
the effective stability bound reduces $C_{\mathrm{CFL}}$ from AB2's $0.5$ to
approximately $0.275$ — *proposed operational value $C_{\mathrm{CFL}}=0.25$* for
$\sigma>0$ two-phase runs.

*Proof sketch*: Root-locus of $z^3 - z^2 - \Delta t(\beta_0 z^2 + \beta_1 z + \beta_2)\lambda = 0$
on $\lambda\Delta t\in i\mathbb{R}$, compared against the DCCD filter's symbol magnitude.
Standard; see Hairer–Wanner *Solving ODEs II* Ch. III.3. ∎

**Theorem 2 (Richardson lifting for non-symmetric CN base).**
Let $\Phi_{\Delta t}$ be the Picard-CN (Heun) step with asymptotic error expansion
$\mathbf{u}(\Delta t) = \mathbf{u}^* + C_2\Delta t^2 + C_3\Delta t^3 + \dots$
Then $\Phi_R := (4\Phi_{\Delta t/2}\!\circ\!\Phi_{\Delta t/2} - \Phi_{\Delta t})/3$ satisfies
$\mathbf{u}(\Delta t) - \Phi_R = O(\Delta t^4)$ only if $C_3 = 0$; otherwise $O(\Delta t^3)$.
For the *non-symmetric* Heun base, $C_3 \neq 0$ generically, so $\Phi_R$ is $O(\Delta t^3)$.

*Proof*: Direct Taylor expansion. See [[WIKI-T-033]] §Richardson-CN and
[`docs/memo/extended_cn_ccd_design.md`](extended_cn_ccd_design.md) §Richardson. ∎

**Theorem 3 (Rotational IPC velocity order, Guermond–Shen 2003).**
For the incompressible NS equations on a smooth domain with $\mathbf{u}\in H^3(\Omega)$,
the rotational pressure-correction scheme achieves
$$
\|\mathbf{u}(t^n) - \mathbf{u}^n\|_{L^2} \leq C\Delta t^3, \qquad
\|p(t^n) - p^n\|_{L^2} \leq C\Delta t^{5/2},
$$
provided convection and viscous terms are discretised to $O(\Delta t^3)$.

*Proof reference*: Guermond & Shen, *Math. Comp.* 73 (2003), Theorem 3.1;
see also Guermond, Minev, Shen, *CMAME* 195 (2006) §4.3 overview. ∎

**Theorem 4 (AB3 cross-term extrapolation).**
For $\mathcal{D}_{\mathrm{c}}(v(t),\mu(t))$ with $v,\mu\in C^3([0,T])$,
$$
\tfrac{23}{12}\mathcal{D}_{\mathrm{c}}^n - \tfrac{16}{12}\mathcal{D}_{\mathrm{c}}^{n-1} + \tfrac{5}{12}\mathcal{D}_{\mathrm{c}}^{n-2}
= \mathcal{D}_{\mathrm{c}}(t^{n+1}) + O(\Delta t^3).
$$
Near smoothed interfaces of width $\varepsilon$, $\mu\in C^{\infty}$ so the
extrapolation preserves $O(\Delta t^3)$; the coefficient of $\Delta t^3$ scales as
$\|\partial_t^3 \mathcal{D}_{\mathrm{c}}\| \sim (\mu_l/\mu_g)/\varepsilon^2 \cdot \|\partial_t^3 v\|$
but the order itself does not degrade (cf. [[WIKI-T-030]]).

*Proof*: Standard Taylor-series argument for AB3 extrapolation; the coefficient bound
follows from chain rule applied to $\mathcal{D}_{\mathrm{c}} = \partial(\mu\partial v)$
with $\|\partial_x\mu\| \lesssim (\mu_l-\mu_g)/\varepsilon$. ∎

---

## 6. ADI Compatibility

**Claim**: Route B preserves the Peaceman–Rachford block-tridiagonal ADI sweep structure
([`appD_predictor_adi.tex:49-64`](../../paper/sections/appD_predictor_adi.tex#L49-L64)).

**Argument**:
- AB3 convection: pure RHS assembly. No change to LHS tridiagonal operator.
- AB3 cross-viscous: pure RHS assembly (cross-term stays explicit).
  The existing recommendation ([§5 line 141](../../paper/sections/05_time_integration.tex#L141))
  already suggests AB2 extrapolation; we extend to AB3.
- Richardson-CN viscous diagonal: each of the three Picard-CN sub-solves uses the
  same tridiagonal operator $[\rho/\Delta t + \lambda^\pm]$; no structural change.
  The GPU-cached inverse `A_inv_dev` (CHK-119) is directly reusable.
- Rotational IPC: pointwise update of $p^{n+1}$ field after corrector. No additional
  linear solve.

The ADI Thomas sweep remains $\mathcal{O}(N)$ per row/column. ∎

---

## 7. Stability Budget Revision

AB3's absolute-stability region is smaller than AB2's. Quantitative comparison
(Hairer–Wanner §III.3, Tables 3.1–3.2):

| Scheme | Real-axis bound | Imaginary-axis | Advective CFL |
|---|---|---|---|
| AB2 | $[-1, 0]$ | $\{0\}$ only | $C_{\mathrm{CFL}} \leq 0.5$ |
| AB3 | $[-6/11, 0] \approx [-0.545, 0]$ | $\{0\}$ only | $C_{\mathrm{CFL}} \leq 0.275$ |

**Proposed operational CFL** for AB3 + DCCD: $C_{\mathrm{CFL}} = 0.25$
(factor $0.55$× reduction vs current $0.45$ from [§5 box warn:cross_cfl](../../paper/sections/05_time_integration.tex#L236)).

Capillary CFL $\Delta t_\sigma \propto \Delta x^{3/2}$ is a spatial-operator / surface-tension
constraint, unaffected by convection scheme. Cross-viscous CFL $\Delta t_{\mathrm{cross}} \le C_{\mathrm{cross}} h^2/\Delta\mu$
with $C_{\mathrm{cross}} \approx 0.22$ ([§12c tab 12.7](../../paper/sections/12c_time_accuracy.tex#L150-L165))
is unaffected: AB3 extrapolation of $\mathcal{D}_{\mathrm{c}}$ does not relax this bound
(extrapolation is explicit, inherits the explicit constraint).

**Summary**: AB3 tightens the advective CFL by ~0.55×, other CFL bounds unchanged.

---

## 8. Risk Register and Open Questions

### Risks (quantified where possible)

**R1 — AB3 capillary instability (High).** AB3 has zero stability on the imaginary axis.
Capillary waves produce imaginary-axis eigenvalues $\lambda = i\omega$. DCCD filter provides
$\varepsilon_d \kappa_{\max}^2$ dissipation. For water–air ($\sigma=0.072$, $\rho=1000$, $k=2\pi/h$)
at $h=1/256$, $\omega \sim 10^4\,\mathrm{s}^{-1}$; requires $\Delta t < C/\omega$ with
$C \approx 0.1$ for practical margin. Mitigation: $C_{\mathrm{CFL}}=0.25$ (Theorem 1); add
$\tfrac{1}{2}$-explicit damping if problematic.

**R2 — Rotational IPC amplification at high $\mu_l/\mu_g$ (Medium).** The term
$-\nu_{\mathrm{eff}}\nabla\!\cdot\mathbf{u}^*$ multiplies by $\nu_{\mathrm{eff}} = \mu/\rho$
which varies by $\sim 10^2$ across the interface for water–air. Near-interface $\nabla\!\cdot\mathbf{u}^*$
residual ($\sim 10^{-6}$ typical) becomes $\sim 10^{-4}$ pressure noise in the liquid phase.
Mitigation: use harmonic-mean $\nu_{\mathrm{eff}}$ across interface, or $\nu_g$-uniform
(as in original Guermond–Shen; gives $O(\Delta t^{5/2})$ velocity, $O(\Delta t^2)$ pressure
but stable).

**R3 — Richardson-CN substep freezing (Low).** Richardson calls the CN base three times per
step, all using $\mu^n$, $\rho^n$, $\kappa^n$ from the step start. Introduced error is
$O(\Delta t \cdot \partial_t\mu) = O(\Delta t^2)$, not contaminating the $O(\Delta t^3)$ order.

**R4 — $\mathcal{D}_{\mathrm{c}}$ history buffer startup (Low).** At step 1, $\mathcal{D}_{\mathrm{c}}^{n-2}$
unavailable. Use AB2 extrapolation; contributes $O(\Delta t^2)$ startup error that decays under
AB3 root condition.

**R5 — Interaction with DGR blowup mechanism (Known, [[WIKI-T-030]] Limitations).**
Route B operates on NS side only. Interface fold detection/repair is reinit-side.
**Must use hybrid reinit** (CHK-133 default) to avoid fold cascade. Route B does not alter
this constraint.

### Open questions

**Q1 — AB3 on CLS advection?** The paper already uses TVD-RK3 ($O(\Delta t^3)$, TVD-preserving,
Shu–Osher) for CLS. Multistep AB3 is not TVD-preserving and is inappropriate for the advection
operator that interacts with the positivity clamp ($\psi\in[0,1]$). **Keep TVD-RK3 for CLS.**

**Q2 — Rotational IPC pressure in $L^\infty$?** Guermond–Shen (2003) guarantees $O(\Delta t^{5/2})$
in $L^2$, but $L^\infty$ remains $O(\Delta t^2)$. Whether this matters depends on which
observables drive validation (e.g. Laplace pressure in static droplet is $L^\infty$-relevant).

**Q3 — Path to $O(\Delta t^4)$.** Upgrade Picard-CN to fully-implicit CN; then Richardson(Implicit-CN)
symmetrically extrapolates to $O(\Delta t^4)$ per [[WIKI-T-033]] §Padé-(2,2). Combined with
AB4 convection (coefficients $(55/24, -59/24, 37/24, -9/24)$) and rotational IPC with
exponential integrator for pressure split, a clean $O(\Delta t^4)$ is theoretically attainable
but requires ~3–4× the implementation effort of Route B.

**Q4 — Operator-split consistency between CLS ($O(\Delta t^3)$) and NS ($O(\Delta t^3)$).**
The coupling via $\rho^{n+1}$, $\mu^{n+1}$, $\kappa^{n+1}$ uses $\psi^{n+1}$ from Step 1.
The paper's current argument ([§5 lines 153–172](../../paper/sections/05_time_integration.tex#L153-L172))
that "operator-split coupling is $O(\Delta t^2)$" needs revisiting at $O(\Delta t^3)$:
does the density transport via Heaviside $H_\varepsilon(\phi^{n+1})$ introduce $O(\Delta t^2)$
contamination? Conjecture: no, provided TVD-RK3 is used for CLS and $\psi^{n+1}$ is updated
before $\rho^{n+1}$, $\mu^{n+1}$ are evaluated. Formal proof is an open question.

---

## 9. References to Add to `paper/bibliography.bib`

```bibtex
@article{Karniadakis1991,
  author = {Karniadakis, G. E. and Israeli, M. and Orszag, S. A.},
  title = {High-order splitting methods for the incompressible {N}avier--{S}tokes equations},
  journal = {Journal of Computational Physics},
  volume = {97},
  number = {2},
  pages = {414--443},
  year = {1991}
}

@article{Timmermans1996,
  author = {Timmermans, L. J. P. and Minev, P. D. and van de Vosse, F. N.},
  title = {An approximate projection scheme for incompressible flow
           using spectral elements},
  journal = {International Journal for Numerical Methods in Fluids},
  volume = {22},
  number = {7},
  pages = {673--688},
  year = {1996}
}

@article{GuermondShen2003,
  author = {Guermond, J.-L. and Shen, J.},
  title = {Velocity-correction projection methods for incompressible flows},
  journal = {SIAM Journal on Numerical Analysis},
  volume = {41},
  number = {1},
  pages = {112--134},
  year = {2003}
}

@article{Alexander1977,
  author = {Alexander, R.},
  title = {Diagonally implicit {R}unge--{K}utta methods for stiff ODE's},
  journal = {SIAM Journal on Numerical Analysis},
  volume = {14},
  number = {6},
  pages = {1006--1021},
  year = {1977}
}

@book{HundsdorferVerwer2003,
  author = {Hundsdorfer, W. and Verwer, J. G.},
  title = {Numerical Solution of Time-Dependent Advection-Diffusion-Reaction Equations},
  publisher = {Springer},
  series = {Springer Series in Computational Mathematics},
  volume = {33},
  year = {2003}
}
```

---

## 10. Implementation Roadmap (for future CHK)

This note is **theory only**. Implementation is a separate future effort with the following
scope (estimated):

1. `ab2_predictor.py` → AB3 extension: extend `_conv_prev` → `_conv_hist[2]`; add
   `_ab3_ready` flag; change coefficient tuple on the AB3 branch (~15 lines).
2. AB3 cross-viscous buffer: mirror the convection buffer for $\mathcal{D}_{\mathrm{c}}$
   (~20 lines).
3. Rotational IPC corrector: modify `velocity_corrector.py` pressure update line to include
   $-\nu_{\mathrm{eff}}\nabla\!\cdot\mathbf{u}^*$ term (~10 lines + $\nabla\!\cdot\mathbf{u}^*$
   pass-through from predictor).
4. Activate `cn_mode="richardson_picard"` as default when third-order is requested
   (~2 lines in config).
5. Verification experiments: extend [`experiment/ch11/exp11_15_ab2_convergence.py`] to AB3;
   add `exp11_30_rotational_ipc_convergence.py`; add `exp11_31_third_order_e2e_tgv.py`
   (Taylor–Green vortex at AB3 + Richardson-CN + Rotational-IPC, expect slope $3.00$).

Total: ~80 lines of library code + 3 new experiment files. Risk-mitigation work (capillary
CFL retune, rotational term blending) adds ~40 lines.

---

**End of note.** Compiled into [[WIKI-T-041]] on 2026-04-18.
