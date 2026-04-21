# SP-F: GPU-Native FVM Projection — Face-Local Matrix-Free Operator and Variable-Batched PCR

**Status**: Short paper draft (research memo)  
**Date**: 2026-04-21  
**Related**: [WIKI-T-017](../../wiki/theory/WIKI-T-017.md), [WIKI-T-044](../../wiki/theory/WIKI-T-044.md), [WIKI-T-005](../../wiki/theory/WIKI-T-005.md), [WIKI-L-015](../../wiki/code/WIKI-L-015.md), [WIKI-L-022](../../wiki/code/WIKI-L-022.md), [WIKI-T-060](../../wiki/theory/WIKI-T-060.md), [WIKI-L-026](../../wiki/code/WIKI-L-026.md), [WIKI-X-018](../../wiki/cross-domain/WIKI-X-018.md)

---

## Abstract

The current non-uniform FVM projection path already contains three GPU-compatible ingredients: face-local pressure gradients (`_fvm_pressure_grad`), face-local Rhie-Chow flux divergence (`RhieChowInterpolator.face_velocity_divergence`), and device-native coefficient construction (`PPEBuilder.build_values`). The remaining performance wall is the **global sparse PPE solve**: `PPESolverFVMSpsolve.solve` still treats the operator as a CSR matrix consumed by a generic sparse direct solver, which either incurs host-device transfers on CPU fallback or routes the GPU through a coarse-grained sparse-solve kernel with poor arithmetic intensity. This note establishes a GPU-first reformulation of the same FVM method.

The key step is to stop thinking of the PPE as a pre-assembled sparse matrix and instead define it as a **face-local operator calculus**
$$
L_{\mathrm{FVM}}(\rho)\,p \;=\; \sum_{a=1}^{d} D_a\,A_a(\rho)\,G_a\,p,
$$
where $G_a$ is a face gradient, $A_a(\rho)$ is the harmonic face coefficient, and $D_a$ is the face-to-node divergence. Every constituent is slice-local and therefore naturally expressible in `backend.xp`. For a fixed transverse index, each axis contribution reduces to a tridiagonal line operator. Because the density field varies in both space and time, however, each line carries **different coefficients**. The correct GPU primitive is therefore not the existing “same matrix, many RHS” batched Thomas/PCR, but a **variable-batched tridiagonal solver** whose lower/main/upper diagonals are arrays of shape `(n, B)`.

This paper proposes a GPU-native PPE architecture built from four ideas. First, keep the FVM discretisation exactly as in the current code and evaluate $L_{\mathrm{FVM}}$ matrix-free via face-local kernels. Second, derive per-axis tridiagonal line operators from the existing `PPEBuilder` coefficients and solve all lines simultaneously with a variable-batched PCR/CR algorithm on the GPU. Third, use those line solves only as a **preconditioner** inside Krylov (FGMRES preferred), not as a standalone ADI solver; this avoids reintroducing splitting error into the fixed point. Fourth, enforce a strict D2H/H2D boundary: geometry is uploaded once, $\rho$-dependent coefficients are formed on device, and host transfers are allowed only at I/O boundaries.

The result is a theory-complete path to accelerate FVM on GPU without changing the paper-exact FVM equations. The global sparse matrix becomes an implementation detail that is no longer required in the hot loop.

---

## 1. Problem statement

The current code path splits naturally into two parts.

1. **Face-local operators already on the right abstraction.**
   - `src/twophase/simulation/ns_pipeline.py` `_fvm_pressure_grad` computes the face-average gradient by slice differences and averaging.
   - `src/twophase/spatial/rhie_chow.py` `face_velocity_divergence` forms face fluxes and takes a face-to-node divergence.
   - `src/twophase/ppe/ppe_builder.py` `build_values` constructs harmonic face coefficients directly in `backend.xp`.

2. **The PPE solve remains global and sparse-matrix-centric.**
   - `src/twophase/ppe/fvm_spsolve.py` `PPESolverFVMSpsolve.solve` builds the data vector, forms a CSR matrix, and delegates to `spsolve`.
   - On CPU this requires `to_host(rhs_vec)` before solve and `xp.asarray(...)` after solve.
   - On GPU it avoids an explicit host round-trip, but the algorithm is still formulated as a generic sparse direct solve rather than a device-native line-parallel operation.

The performance diagnosis is therefore **not** “FVM is inherently sequential”. The real diagnosis is:

> The current FVM algebra is local, but the current FVM solve is expressed through a global sparse-matrix abstraction that hides line parallelism and encourages host/device boundary crossings.

This distinction matters because it tells us what must change: the **operator representation**, not the PDE or the face coefficients.

---

## 2. Face-local operator calculus

Fix axis $a \in \{1,\ldots,d\}$. Let $E_a^{-}$ and $E_a^{+}$ denote the left and right face gathers:
$$
(E_a^- p)_f = p_L,\qquad (E_a^+ p)_f = p_R,
$$
with face spacing $H_{a,f} = x_{R} - x_{L}$ and nodal control volume $\Delta V_i$.

Define the harmonic face coefficient
$$
A_{a,f}(\rho) \;:=\; \frac{2}{\rho_L + \rho_R},
$$
the face gradient
$$
(G_a p)_f \;:=\; \frac{(E_a^+ p)_f - (E_a^- p)_f}{H_{a,f}},
$$
the face flux
$$
(F_a p)_f \;:=\; A_{a,f}(\rho)\,(G_a p)_f,
$$
and the face-to-node divergence
$$
(D_a q)_i \;:=\; \frac{q_{i+1/2} - q_{i-1/2}}{\Delta V_i}.
$$

Then the variable-density FVM PPE is
$$
L_{\mathrm{FVM}}(\rho)\,p
\;=\;
\sum_{a=1}^{d} D_a\,F_a p
\;=\;
\sum_{a=1}^{d} D_a\,A_a(\rho)\,G_a\,p.
$$

This is exactly the same algebra currently encoded implicitly in `PPEBuilder.build_values`. The difference is representational:

- **CSR view**: assemble all nonzeros, then multiply/solve.
- **Face-local view**: evaluate $G_a$, multiply by $A_a(\rho)$, then apply $D_a$.

The face-local view is GPU-native because every step is a batched slice operation over full arrays.

### 2.1 Matrix-free equivalence

For one axis in 1D, node $i$ receives contributions
$$
\frac{A_{i+1/2}}{H_{i+1/2}\,\Delta V_i}\,(p_{i+1}-p_i)
\;-\;
\frac{A_{i-1/2}}{H_{i-1/2}\,\Delta V_i}\,(p_i-p_{i-1}),
$$
which expands to
$$
c_i^-\,p_{i-1} + c_i^0\,p_i + c_i^+\,p_{i+1},
$$
with
$$
c_i^- = \frac{A_{i-1/2}}{H_{i-1/2}\,\Delta V_i},
\qquad
c_i^+ = \frac{A_{i+1/2}}{H_{i+1/2}\,\Delta V_i},
\qquad
c_i^0 = -(c_i^- + c_i^+).
$$

These are precisely the coefficients that `PPEBuilder.build_values` materialises into COO/CSR form. Therefore the matrix-free operator is **algebraically identical** to the current assembled operator.

---

## 3. Line decomposition and the missing GPU primitive

Fix axis $a$ and hold all transverse indices $\mathbf{m}$ constant. Along that line the axis contribution is tridiagonal:
$$
(\mathcal{T}_{a,\mathbf{m}} p)_k
\;=\;
c^-_{k,\mathbf{m}}\,p_{k-1,\mathbf{m}}
+ c^0_{k,\mathbf{m}}\,p_{k,\mathbf{m}}
+ c^+_{k,\mathbf{m}}\,p_{k+1,\mathbf{m}}.
$$

The important observation is:

> Every line is tridiagonal, but not every line has the same tridiagonal matrix.

This is the place where the current GPU infrastructure stops one step too early. `linalg_backend._pcr_solve_batched` already proves that a tridiagonal solve can be executed in parallel on GPU when the same matrix is shared across all batches. For variable-density FVM we need the generalisation
$$
\text{PCRVar}(a_{k,b}, d_{k,b}, c_{k,b}, r_{k,b}),
$$
where $b$ indexes the transverse line.

### 3.1 Why the generalisation is natural

PCR eliminates neighbours through pointwise arithmetic on the triples $(a,d,c)$ and RHS $r$. Nothing in the recurrence requires $a,d,c$ to be constant across batches; the current code simply broadcasts them from `(n,1)` because that is sufficient for compact-filter use. Replacing those arrays by full `(n,B)` arrays yields the variable-batched solver with the same algorithmic stages:

1. roll left/right by current stride,
2. compute elimination factors $\alpha,\beta$ pointwise,
3. update $(a,d,c,r)$ pointwise,
4. double the stride.

The result is still $\lceil \log_2 n \rceil$ stages, but now for **heterogeneous line systems**.

### 3.2 Consequence for FVM PPE

Once this primitive exists, axis-$a$ line solves become fully GPU-parallel:

- batch size $B = \prod_{b \neq a} (N_b+1)$ lines,
- each line length $n = N_a+1$,
- coefficients $a,d,c$ formed on device from $\rho$ and geometry,
- no CSR assembly, no sparse symbolic factorisation, no per-line Python loop.

This is the central theoretical bridge from current FVM code to GPU throughput.

---

## 4. Preconditioning, not standalone ADI

The project already contains negative evidence against using split line sweeps as a standalone multidimensional solver: ADI can converge slowly or inherit splitting artefacts. That history must not be repeated.

The correct role of the line solve is therefore:
$$
\text{solve } L_{\mathrm{FVM}}(\rho)\,p = b
\quad \text{with Krylov, using line solves only in } P^{-1}.
$$

One admissible additive preconditioner is
$$
P^{-1} r
\;:=\;
\sum_{a=1}^{d} \omega_a\,\mathcal{T}_a^{-1} r,
$$
where each $\mathcal{T}_a^{-1}$ is applied by variable-batched PCR on axis $a$ lines. A multiplicative or symmetric variant is equally possible.

This has two decisive consequences:

1. **No splitting error in the fixed point.** The exact operator seen by Krylov remains $L_{\mathrm{FVM}}$, not $\sum_a \mathcal{T}_a$.
2. **Line parallelism is still exploited.** The line solves influence convergence speed, not the PDE being solved.

In short:

> ADI as a solver changes the equation. Line-PCR as a preconditioner changes only the iteration path.

This is the correct theoretical resolution of the “sequential FVM” complaint.

---

## 5. D2H / H2D boundary discipline

The project’s GPU guidance already states that per-step host/device traffic destroys speedup. The present theory tightens that into a hot-loop rule:

### Proposition (zero-transfer hot loop)

If

1. geometry arrays $(H_{a,f}, \Delta V_i)$ are uploaded once at grid build time,
2. density-dependent coefficients $A_{a,f}(\rho)$ and line diagonals $(a,d,c)$ are formed in `backend.xp`,
3. matrix-free apply, line preconditioning, and Krylov residual norms remain in device arrays,

then the PPE hot loop performs **zero mandatory D2H/H2D transfers**. Host transfer is needed only at

- experiment I/O (`save_results`, plots),
- explicit diagnostics flush,
- inherently serial non-FVM modules outside the projection hot loop.

This proposition is not about numerical accuracy; it is the performance invariant required for any real GPU speedup.

---

## 6. A3 traceability

| Layer | Statement |
|---|---|
| Equation | $L_{\mathrm{FVM}}(\rho)\,p = \sum_a D_a A_a(\rho) G_a p$ |
| Discretisation | face-local gradient + harmonic face flux + node divergence + per-line tridiagonal restriction |
| Linear algebra | variable-batched PCR/CR line solves used as Krylov preconditioner |
| Code (existing) | `_fvm_pressure_grad`, `RhieChowInterpolator.face_velocity_divergence`, `PPEBuilder.build_values`, `linalg_backend._pcr_solve_batched` |
| Code (next) | `PPESolverFVMMatrixFree` + `solve_tridiagonal_variable_batched` |

The key design choice is conservative: the equations and coefficients are retained, while the operator representation and solve strategy change.

---

## 7. Implementation roadmap

### Phase 1 — New GPU primitive

Generalise `linalg_backend._pcr_solve_batched` from common-diagonal `(n,1)` broadcast to variable-diagonal `(n,B)` arrays. Expose it as a backend helper dedicated to heterogeneous line solves.

### Phase 2 — Matrix-free FVM operator

Add a new PPE solver class that

- evaluates $L_{\mathrm{FVM}}(\rho)\,p$ matrix-free,
- constructs line diagonals per axis directly from device $\rho$,
- runs FGMRES with the line-PCR preconditioner.

### Phase 3 — Additive integration

Register the solver under a new `ppe_solver_type` without changing defaults. `PPESolverFVMSpsolve` remains as the legacy fallback per C2.

### Phase 4 — Verification

1. matrix-free apply == CSR apply,
2. variable-batched PCR == CPU reference solve on random variable coefficients,
3. CPU/GPU parity,
4. no `.get()/.item()/float(device_array)/to_host()` inside the solve loop,
5. remote GPU wall-clock comparison against `fvm_spsolve`.

---

## 8. Connection to the existing H-01 / A-01 programme

H-01 and A-01 solved an **accuracy-locus** problem: pressure, capillary, and advection terms must live on the same face locus. SP-F solves a different problem: the **performance representation** of the same face-locus algebra.

The two tracks are complementary:

- H-01 / A-01: make the operator *correct*.
- SP-F: make the same operator *fast on GPU*.

Because SP-F preserves the face-local FVM equations exactly, it can accelerate the existing G^adj / Rhie-Chow / FVM PPE stack without reopening the correctness proofs.

---

## 9. One-line summary

FVM is not too sequential for GPU; only its current sparse-matrix representation is. Recast the PPE as the face-local operator $\sum_a D_a A_a G_a$, add a variable-batched PCR line solver, and use line solves as a Krylov preconditioner rather than as a standalone ADI solver.
