# Extended CN — Implementation Design Note

**Date**: 2026-04-12
**Status**: DESIGN (not implemented)
**Scope**: Library architecture for implementing Richardson-CN and Padé-(2,2) CN on top of the existing viscous predictor path
**Source**: [[docs/memo/extended_cn_ccd_design.md]], [[WIKI-T-033]]
**Target files**: `src/twophase/ns_terms/viscous.py`, new `src/twophase/ns_terms/cn_advance/`
**Consumers**: `ns_terms/predictor.py` (IPC+AB2+CN viscous predictor), `configs/*`, `simulation/builder.py`

---

## 1. Audit of the current viscous path (prerequisite finding)

### 1.1 `ViscousTerm.apply_cn_predictor` is not a true implicit CN

Current implementation (`src/twophase/ns_terms/viscous.py:86-134`):

```python
u_pred = u^n + dt*(explicit + V(u^n))                    # forward Euler
visc_star = V(u_pred)
u_cn   = u^n + dt*(explicit + 0.5*V(u^n) + 0.5*V(u_pred)) # explicit trapezoid
```

This is a **1-step Picard iteration on the CN equation** — algebraically identical to Heun's
predictor–corrector:
- Temporal accuracy: $O(\Delta t^2)$ (same as true CN on linear diffusion)
- Stability: **purely explicit** — no implicit solve, so viscous CFL
  $\Delta t \lesssim h^2\,\nu^{-1}/2$ is implicitly reintroduced
- A-stability: **no**
- Docstring claim *"converges in 1–2 iterations for moderate Δt"* is true only
  in the sense that a Picard on a contractive fixed-point converges — but the
  scheme here is Heun, not Picard-converged CN

### 1.2 CFL bookkeeping mismatch

[`src/twophase/time_integration/cfl.py:44`](../../src/twophase/time_integration/cfl.py#L44)
skips the viscous CFL check when `cn_viscous=True`:

> "CN is unconditionally stable"

This is inconsistent with §1.1 — the current scheme is not CN and is not unconditionally stable.
In practice the coupled convective/capillary CFL dominates for our Re regime, so no one has
hit the underlying explicit-viscous instability, but this is a latent PR-5 and A3 issue.

### 1.3 Dead parameter

[`predictor.py:187-189`](../../src/twophase/ns_terms/predictor.py#L187-L189) calls
`apply_cn_predictor(vel_n, None, explicit_rhs, ...)` — the second positional `u_star` is never
used in the method body. Legacy signature leftover.

### 1.4 Design consequence

Any Extended CN implementation must **first** decide whether to inherit the existing Heun-based
baseline (Option A) or rebuild on a true implicit CN (Option B). This note recommends
**both, layered** (§6).

---

## 2. Design principles

1. **SRP + DIP (C1 SOLID audit)**. `ViscousTerm` owns the stress-divergence operator $V(u)$.
   Time-stepping strategy is a separate concern. Extract `CNAdvance` as an injectable strategy.
2. **C2 preservation**. Keep the current 1-step Picard / Heun as `PicardCNAdvance` (tested,
   shipping), register in `docs/01_PROJECT_MAP.md §8` legacy table.
3. **DIP**. `ViscousTerm.apply_cn_predictor` delegates to the injected strategy. Builder chooses.
4. **Matrix-free on GPU**. Padé-(2,2) uses a `LinearOperator` that calls back into `V_lin`
   twice per matvec; no sparse assembly, reuses CHK-119 `A_inv_dev` through CCD.
5. **PR-5 Algorithm Fidelity**. Padé-(2,2) must reduce to exact CN as $\beta\to 0$; Richardson
   must reduce to plain CN when not activated. Default path must remain bit-exact to current
   production (CHK-120 baseline).
6. **Cross-term order trap**. Off-diagonal cross-stress terms
   $\sum_{\beta\ne\alpha}\partial_\beta(\mu\,\partial_\alpha u_\beta)$ are evaluated
   **explicitly** in the current code. If Padé-(2,2) only raises the *diagonal* part,
   the global temporal order is capped at $O(\Delta t^2)$ by the cross-term splitting.
   See §5.2 for the fix.

---

## 3. Proposed module layout

```
src/twophase/ns_terms/
  viscous.py                         # unchanged V(u) operator; apply_cn_predictor delegates
  cn_advance/
    __init__.py                      # factory
    base.py                          # ICNAdvance protocol
    picard_cn.py                     # PicardCNAdvance (current behaviour, C2 legacy)
    richardson_cn.py                 # RichardsonCNAdvance (wraps a base advance, Δt/2 extrapolation)
    pade22_cn.py                     # Pade22CNAdvance (true implicit, matrix-free, BiCGSTAB)
    implicit_cn.py                   # ImplicitCNAdvance (true linear CN, built as a dep of Pade22)
```

Zero edits under `src/twophase/ns_terms/viscous.py` except delegation; all new code lives
in `cn_advance/` subpackage. This bounds PR-5 blast radius.

---

## 4. Interface — `ICNAdvance`

```python
# cn_advance/base.py
from typing import Protocol, List
from ..interfaces.ns_terms import INSTerm  # circular-safe forward refs

class ICNAdvance(Protocol):
    """Time-advance strategy for the viscous predictor step.

    Given u^n, explicit RHS at time n, and the viscous operator V, return u*
    (the velocity field after the viscous predictor) such that

        rho * (u* - u^n) / dt  ==  explicit_rhs
                              + temporal_discretization(V, u^n, u*, dt)

    where `temporal_discretization` is the strategy-specific part (Heun,
    Richardson, Padé-(2,2), ...).
    """

    def advance(
        self,
        u_old:  List["array"],
        explicit_rhs: List["array"],
        mu:  "array",
        rho: "array",
        viscous_op: "ViscousTerm",      # provides V(u) via _evaluate
        ccd: "CCDSolver",
        dt: float,
    ) -> List["array"]: ...
```

Note: `viscous_op` is passed as a collaborator (not `self`) so that Richardson can call
it recursively with sub-strategies. `ViscousTerm` holds no mutable state across calls,
so reuse is safe.

---

## 5. Strategy implementations

### 5.1 `PicardCNAdvance` — legacy extraction (C2)

**Goal**: byte-identical to current `apply_cn_predictor` body. Move the code, don't change it.

```python
class PicardCNAdvance:
    def advance(self, u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt):
        visc_n = viscous_op._evaluate(u_old, mu, rho, ccd)
        u_pred = [u_old[c] + dt*(explicit_rhs[c]/rho + visc_n[c])
                  for c in range(len(u_old))]
        visc_star = viscous_op._evaluate(u_pred, mu, rho, ccd)
        return [u_old[c] + dt*(explicit_rhs[c]/rho
                               + 0.5*visc_n[c] + 0.5*visc_star[c])
                for c in range(len(u_old))]
```

**Verification**: CHK-120 baseline reproduction — `pytest tests/test_ns_terms.py`
must pass with `cn_viscous=True` path bit-identical. Every existing experiment
(exp11_25 viscous temporal, whatever ns_pipeline integration tests exist) must
pass bit-exact.

### 5.2 `RichardsonCNAdvance` — cheap $O(\Delta t^4)$ (ships first)

**Key insight**: Richardson extrapolation is *external* to the base scheme. If the base
scheme is a function $\Phi(\Delta t)$ of $\Delta t$ with expansion
$u(\Delta t) = u^\star + C_p\Delta t^p + C_{p+1}\Delta t^{p+1} + \dots$,
then $(4\Phi(\Delta t/2)\circ\Phi(\Delta t/2) - \Phi(\Delta t))/3$ annihilates the leading
$C_p\Delta t^p$ term, but what remains depends on the base:

| Base | Error expansion | Richardson lift |
|---|---|---|
| non-symmetric (Heun, general RK) | all powers $\Delta t^2, \Delta t^3, \Delta t^4,\dots$ | **+1 only** → $O(\Delta t^{p+1})$ |
| symmetric (trapezoidal, midpoint, Padé-(2,2)) | only *even* powers $\Delta t^2, \Delta t^4,\dots$ | **+2** → $O(\Delta t^{p+2})$ |

This is the classical symmetry/parity result. The **PicardCNAdvance base is Heun, not
symmetric**, so `Richardson(Picard)` is `O(Δt³)`, *not* `O(Δt⁴)` as initially anticipated.
Verified in Phase 2 by a self-similarity refinement test
(`src/twophase/tests/test_ns_terms.py::test_richardson_cn_lifts_order_on_pure_diffusion`):
measured order **3.01** for `RichardsonCNAdvance(PicardCNAdvance)` on pure diffusion.

Concrete orders for the planned strategy family:

| Wrapper × base | Order | Notes |
|---|---|---|
| `RichardsonCNAdvance(PicardCNAdvance)` | $O(\Delta t^3)$ | Phase 2 — this ship, one-step order lift only |
| `RichardsonCNAdvance(ImplicitCNAdvance)` | $O(\Delta t^4)$ | Phase 3+ — true trapezoidal is symmetric, full +2 |
| `RichardsonCNAdvance(Pade22CNAdvance)` | $O(\Delta t^6)$ | Phase 6 — Padé is symmetric, full +2 from the Padé base at order 4 |

The cross-term order-cap trap (§2 point 6) is still addressed by Richardson — because
the extrapolation operates on whole-scheme output, explicit cross-terms and
`explicit_rhs` are lifted along with the diagonal. Phase 2's `Richardson(Picard)`
gives `O(Δt³)` on *everything* (cross-terms, rhs, diagonal). True $O(\Delta t^4)$ requires
the symmetric-base path (Phase 3).

```python
class RichardsonCNAdvance:
    def __init__(self, base: ICNAdvance):
        self.base = base  # PicardCNAdvance or ImplicitCNAdvance

    def advance(self, u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt):
        # Big step
        u1 = self.base.advance(u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt)
        # Two half steps — explicit_rhs frozen at time n (same as current AB2 path)
        u_half = self.base.advance(u_old, explicit_rhs, mu, rho, viscous_op, ccd, 0.5*dt)
        u2     = self.base.advance(u_half, explicit_rhs, mu, rho, viscous_op, ccd, 0.5*dt)
        return [(4.0*u2[c] - u1[c]) / 3.0 for c in range(len(u_old))]
```

**Cost**: ~3× base (1 big + 2 half solves)
**Order**: $O(\Delta t^3)$ with the Picard (Heun) base — see table above; upgrade to $O(\Delta t^4)$ requires the symmetric ImplicitCNAdvance base (Phase 3)
**Stability**: inherits from base (same CFL regime as current Picard, not improved)
**Risk**: `explicit_rhs` is evaluated at time $n$ and held constant across the
substeps — this is consistent with how the current IPC+AB2 assembles it and
matches standard Richardson-on-sub-step practice. The AB2 convective contribution
inside `explicit_rhs` is already $O(\Delta t^2)$ accurate and does not benefit from
the viscous substep refinement, which sets a ceiling — see §7.

**Ship first**: minimal risk, no new operator, 4th-order viscous diagonal immediately.

### 5.3 `ImplicitCNAdvance` — true linear CN (dep of Pade22)

Build a matrix-free BiCGSTAB solve for

$$(I - \tfrac{\Delta t}{2}\,V_{\text{lin}})\,u^{n+1}_\alpha \;=\; u^n_\alpha + \Delta t\,(\text{explicit\_rhs}_\alpha/\rho + \tfrac{1}{2}V_{\text{lin}}(u^n)_\alpha + V_{\text{cross}}(u^n)_\alpha)$$

where $V_{\text{lin}}(u)_\alpha = (1/(Re\,\rho))\,\partial_\beta(\mu\,\partial_\beta u_\alpha)$
(diagonal part, $\beta$ summed) and $V_{\text{cross}}$ the off-diagonal part.

```python
class ImplicitCNAdvance:
    def __init__(self, backend, tol=1e-10, maxiter=50, precond="fd_lu"):
        self.xp = backend.xp
        self.backend = backend
        self.tol = tol
        self.maxiter = maxiter
        self.precond = precond

    def advance(self, u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt):
        # Build rhs (explicit half of CN + explicit cross-terms + explicit_rhs at time n)
        V_diag_n  = self._V_diag(u_old, mu, rho, viscous_op, ccd)
        V_cross_n = self._V_cross(u_old, mu, rho, viscous_op, ccd)
        rhs = [u_old[c] + dt*(explicit_rhs[c]/rho
                              + 0.5*V_diag_n[c]
                              + V_cross_n[c])
               for c in range(len(u_old))]

        # Matrix-free LinearOperator for (I - (dt/2) V_diag) applied component-wise
        u_new = []
        for c in range(len(u_old)):
            A = self._make_linop(mu, rho, viscous_op, ccd, dt, component=c)
            M = self._make_precond(mu, rho, dt, component=c) if self.precond else None
            x, info = bicgstab(A, rhs[c].ravel(), x0=u_old[c].ravel(),
                                tol=self.tol, maxiter=self.maxiter, M=M)
            u_new.append(x.reshape(u_old[c].shape))
        return u_new
```

- Needs a **split of `_evaluate`** into `_V_diag` / `_V_cross`. This is a 20-line
  refactor inside `ViscousTerm._stress_divergence_component` — split the $\beta=\alpha$
  term (diagonal) from the $\beta\ne\alpha$ terms (cross).
- Preconditioner: start with **no preconditioner** for correctness proof; add
  FD Helmholtz-LU from `src/twophase/ccd/fd_ppe_matrix.py` pattern (built with
  $\mu,\rho$ evaluated as scalar averages for cheapness).
- Solver choice: BiCGSTAB by default (variable $\mu/\rho$ breaks symmetry);
  CG when $\mu,\rho$ are constant.
- A-stability: exact (that's why we build this).

### 5.4 `Pade22CNAdvance` — $O(\Delta t^4)$ A-stable (ships second)

Same matrix-free framework as `ImplicitCNAdvance`, but the operator is

$$\mathcal{A} = I - \tfrac{\Delta t}{2}V_{\text{lin}} + \tfrac{\Delta t^2}{12}V_{\text{lin}}\!\circ\!V_{\text{lin}}$$

and the RHS uses the mirror polynomial. Matvec:

```python
def matvec(u_flat):
    u = u_flat.reshape(shape)
    w  = V_lin_apply(u)                      # CCD pass 1 (cached A_inv_dev)
    w2 = V_lin_apply(w)                      # CCD pass 2
    return (u - 0.5*dt*w + (dt*dt/12.0)*w2).ravel()
```

- `V_lin_apply(u)` applies the diagonal viscous operator to a **single scalar field**
  (one velocity component). Component-uncoupled at the diagonal level, so solve each
  component independently in the linear outer loop.
- Cross-terms stay explicit at time $n$ (same as ImplicitCN). To raise the global
  order to $O(\Delta t^4)$, wrap `Pade22CNAdvance` in `RichardsonCNAdvance` — the
  resulting scheme is *Padé-(2,2) per substep + Richardson extrapolation over cross-terms*,
  which is still $O(\Delta t^4)$ global and *A-stable on the diagonal* (Richardson
  on Padé-(2,2) is still A-stable because each base call is A-stable).

**This layered composition is the most important design decision in this note.**

### 5.5 `NullCNAdvance` — explicit baseline

Keeps `cn_viscous=False` working through the same strategy interface:

```python
class NullCNAdvance:
    def advance(self, u_old, explicit_rhs, mu, rho, viscous_op, ccd, dt):
        visc = viscous_op._evaluate(u_old, mu, rho, ccd)
        return [u_old[c] + dt*(explicit_rhs[c]/rho + visc[c])
                for c in range(len(u_old))]
```

Replaces the branch at `predictor.py:190-195`.

---

## 6. Phased implementation plan

Each phase is a separate commit on its own worktree branch with independent PR-5 verification.

### Phase 0 — **Audit fix** (1 CHK, no API change)

- Rename `apply_cn_predictor` docstring to reflect the actual 1-step Picard / Heun behaviour;
  update [`cfl.py:44`](../../src/twophase/time_integration/cfl.py#L44) comment to reflect
  conditional stability; drop the unused `u_star=None` parameter at `predictor.py:188`.
- **No numerical change**. Regression: `pytest` bit-exact.
- Register the legacy behaviour for the upcoming C2 preservation.

### Phase 1 — **Strategy extraction** (1 CHK)

- Create `cn_advance/` package with `base.py` + `picard_cn.py` + `__init__.py`.
- Refactor `ViscousTerm.apply_cn_predictor` to delegate:
  ```python
  def apply_cn_predictor(self, u_old, explicit_rhs, mu, rho, ccd, dt, strategy=None):
      strategy = strategy or self._default_strategy
      return strategy.advance(u_old, explicit_rhs, mu, rho, self, ccd, dt)
  ```
- Builder injects `PicardCNAdvance` by default ([`simulation/builder.py:212`](../../src/twophase/simulation/builder.py#L212)).
- **No numerical change**. Regression: bit-exact CHK-120 baseline + full pytest.
- C2 registration in `docs/01_PROJECT_MAP.md §8`.

### Phase 2 — **RichardsonCNAdvance** (1 CHK, ships 4th order)

- Implement `richardson_cn.py` as in §5.2.
- Config flag: `numerics.cn_richardson: bool = False` + `numerics.cn_viscous: bool = True`.
- Builder: if `cn_richardson`, wrap the base strategy.
- **Verification experiment**: `exp11_30_extended_cn_convergence` — manufactured viscous
  problem $u = e^{-\nu k^2 t}\sin(kx)\sin(ky)$, $\nu=0.01$, $N\in\{32,64,128\}$,
  $\Delta t$ sweep. Report:
  - temporal order of Picard-CN (expect 2)
  - temporal order of Richardson-Picard-CN (expect 4)
  - long-time energy drift over $T=10$
- **Risk**: the AB2 convective term has its own $O(\Delta t^2)$ floor, so the *global*
  ns_pipeline order stays at 2 even with Richardson viscous. The viscous-term order
  win only materializes on viscous-dominated cases. Document this in the experiment report.

### Phase 3 — **ImplicitCNAdvance** (1 CHK)

- Split `_evaluate` into `_V_diag` + `_V_cross` (20-line refactor inside `viscous.py`).
- Implement `implicit_cn.py` with BiCGSTAB, no preconditioner (correctness first).
- Config flag: `numerics.cn_implicit: bool = False`.
- **Verification**: (a) `exp11_30` ImplicitCN vs PicardCN — both should give $O(\Delta t^2)$
  but ImplicitCN should be A-stable at $\Delta t$ far above the explicit CFL
  (test with $\Delta t = 10\,\Delta t_{\text{CFL,visc}}$). (b) bit-exact fallback: with
  `cn_implicit=False` the default path is PicardCN, CHK-120 baseline preserved.
- Add FD-LU preconditioner in a second commit once BiCGSTAB correctness is proven.

### Phase 4 — **Pade22CNAdvance** (1 CHK)

- Implement `pade22_cn.py` with the matvec in §5.4, built on the `ImplicitCNAdvance`
  machinery (same solver, different operator polynomial).
- Config flag: `numerics.cn_pade22: bool = False`.
- **Verification**:
  - (a) Consistency: `Pade22CN` with $\beta=0$ must bit-match `ImplicitCN`.
  - (b) `exp11_30`: Pade22 alone → $O(\Delta t^4)$ on viscous diagonal.
  - (c) Energy drift measurement vs Richardson-Picard-CN baseline.
  - (d) High-$k$ wiggle check: single-mode initial condition at $k=N/2$, $\Delta t$ large,
       verify no exponential amplification (Padé-(2,2) is A-stable so this should pass;
       L-stable variants added in Phase 5 if needed).

### Phase 5 — **Wiggle mitigation** (optional, 1 CHK)

- Hook the existing dissipative CCD filter ([[WIKI-T-002]]) into the Pade22 output
  as an opt-in post-process; or implement the spectrally-optimized $\beta^\star < \Delta t^2/12$
  variant if the wiggle is physical.
- Only if Phase 4 (d) shows measurable wiggle on realistic two-phase cases.

### Phase 6 — **Richardson on Pade22** (composition, 1 CHK)

- No new class. Just verify that `RichardsonCNAdvance(base=Pade22CNAdvance())` works
  and delivers $O(\Delta t^4)$ *global* (viscous diagonal + cross-terms both raised).
- Document as the production target for viscous-dominated regimes.

---

## 7. Known limitations and non-goals

1. **AB2 convective term is not raised**. The global NS pipeline temporal order stays
   at $O(\Delta t^2)$ unless the predictor's AB2 is also upgraded (out of scope).
   Extended CN matters specifically for viscous-dominated cases and for the viscous
   piece of manufactured-solution verification.
2. **Variable $\mu, \rho$**: the diagonal operator $V_{\text{lin}}(u) = (1/(Re\,\rho))\,\nabla\cdot(\mu\,\nabla u)$
   is still linear in $u$ but the coefficients are fields. The matrix-free matvec sees
   $\mu, \rho$ as frozen at time $n$; this is the standard semi-implicit convention and
   does not affect temporal order on the *linear* subproblem.
3. **GFM interaction**: WIKI-T-033 open question — sequential $D_2(D_2 u)$ through a
   density/viscosity jump may lose jump-order consistency. Add a dedicated test case
   once Phase 4 is in.
4. **3D**: all strategies are dimension-agnostic through `range(ndim)`. BiCGSTAB scales
   as $O(N^d)$ per matvec, same memory profile as the existing CCD PPE solver.
5. **GPU**: `bicgstab` from `scipy.sparse.linalg` is CPU-only. The GPU path must use
   `cupyx.scipy.sparse.linalg.bicgstab` (or CG for symmetric cases). The `V_lin_apply`
   callback stays on device through the existing CCD `A_inv_dev` cache
   (CHK-119, [[WIKI-L-015]]). Dispatch at strategy construction time via `backend.is_gpu()`.

---

## 8. Files touched (summary)

### New
- `src/twophase/ns_terms/cn_advance/__init__.py` (factory)
- `src/twophase/ns_terms/cn_advance/base.py` (protocol)
- `src/twophase/ns_terms/cn_advance/picard_cn.py` (legacy extraction, C2)
- `src/twophase/ns_terms/cn_advance/richardson_cn.py` (Phase 2)
- `src/twophase/ns_terms/cn_advance/implicit_cn.py` (Phase 3)
- `src/twophase/ns_terms/cn_advance/pade22_cn.py` (Phase 4)
- `experiment/ch11/exp11_30_extended_cn_convergence.py` (verification)
- `src/twophase/tests/test_cn_advance.py` (unit tests per strategy)

### Modified (small diffs only)
- `src/twophase/ns_terms/viscous.py` (delegate + split `_evaluate`)
- `src/twophase/ns_terms/predictor.py` (remove dead `u_star=None` positional)
- `src/twophase/configs/config_loader.py` (new flags)
- `src/twophase/config.py` (new `NumericsConfig` fields)
- `src/twophase/simulation/builder.py` (strategy injection)
- `src/twophase/time_integration/cfl.py` (comment fix, Phase 0)
- `docs/01_PROJECT_MAP.md §8` (C2 legacy registration for PicardCNAdvance)

### Untouched
- `ns_terms/ipc.py`, `ns_terms/ab2.py`, `ns_terms/pressure.py`, all CCD internals,
  all level-set / reinit / curvature code.

---

## 9. A3 Traceability (Equation → Discretization → Code)

| Layer | Artifact |
|---|---|
| Equation | $\partial_t u = \nu L u + \text{cross}(u) + \text{explicit}$ ([[WIKI-T-003]] §10) |
| Discretization | Padé-(2,2): $(I - \alpha V_{\text{lin}} + \beta V_{\text{lin}}^2)u^{n+1} = \text{rhs}$, $\alpha=\Delta t/2$, $\beta=\Delta t^2/12$ ([[WIKI-T-033]]) |
| Operator | $V_{\text{lin}}(u)_\alpha = \partial_\beta(\mu\,\partial_\beta u_\alpha)/(Re\,\rho)$ via two CCD $D_2$ passes (sequential route, Route A of [[WIKI-T-033]]) |
| Solver | matrix-free BiCGSTAB over `LinearOperator`, CHK-119 `A_inv_dev` cache reused |
| Code | `cn_advance/pade22_cn.py` (new, Phase 4) |
| Verification | `exp11_30_extended_cn_convergence` (new, Phase 4) |

---

## 10. Recommendation

**Sequence**: Phase 0 → Phase 1 → Phase 2 → (Phase 3 ∥ Phase 4) → Phase 6. Skip Phase 5
unless Phase 4 (d) shows measurable wiggle. Phase 3 and Phase 4 can proceed in parallel
after Phase 1 lands (independent worktrees, different strategy files, no shared library edits
after the `_V_diag/_V_cross` split).

**Minimum viable deliverable**: Phase 0 + 1 + 2. Gives a 4th-order viscous diagonal via
Richardson, no new solver, minimal PR-5 risk, ships in ~3 CHKs.

**Production target**: Phase 0 + 1 + 2 + 4 + 6. True $O(\Delta t^4)$ A-stable viscous
predictor with cross-terms lifted by Richardson composition.

---

## 11. Open questions for the user

1. **Scope**: ship the minimum viable (Phase 0-2) first, or go straight to the
   production target (add 3-4-6)?
2. **Config API**: single enum `numerics.cn_mode ∈ {explicit, picard, richardson, implicit, pade22, richardson_pade22}` vs three booleans? Enum is cleaner but breaks the existing
   `cn_viscous: bool` flag. Boolean-compatible default: keep `cn_viscous` as the explicit/non-explicit
   toggle, add `cn_mode` as a secondary selector that defaults to `picard` (current behaviour).
3. **Phase 0 scope**: include the `cfl.py:44` comment fix and the dead-parameter cleanup,
   or treat those as separate housekeeping CHKs?
4. **GPU priority**: CPU-first for Phase 3-4 with `cupyx` BiCGSTAB as a follow-up, or GPU
   from day one?

---

## Source

- Design rationale: [[WIKI-T-033]], `docs/memo/extended_cn_ccd_design.md`
- Current viscous path audit: `src/twophase/ns_terms/viscous.py`, `src/twophase/ns_terms/predictor.py`,
  `src/twophase/time_integration/cfl.py`
- CCD `A_inv_dev` matrix-free floor: CHK-119, [[WIKI-L-015]]
- Projection method baseline: [[WIKI-T-003]]
- Filter hook for wiggle mitigation: [[WIKI-T-002]], [[WIKI-T-019]]
