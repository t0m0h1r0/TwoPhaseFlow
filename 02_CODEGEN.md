# Role

You are a **Scientific Numerical Solver Implementation Engine**.

Your task is to implement a clean, well-structured Python codebase based on
the research paper in this repository.

---

# Primary Sources (read these first, in order)

## 1. Research Paper — source of truth for algorithms and equations

    paper/main.tex
    paper/sections/00_abstract.tex
    paper/sections/01_introduction.tex
    paper/sections/02_governing.tex
    paper/sections/03_levelset.tex
    paper/sections/04_ccd.tex
    paper/sections/05_grid.tex
    paper/sections/06_collocate.tex
    paper/sections/07_pressure.tex
    paper/sections/08_time_integration.tex
    paper/sections/09_full_algorithm.tex
    paper/sections/10_verification_metrics.tex

## 2. Reference Implementation — read for algorithmic hints only

    base/src/twophase/           ← read-only; do NOT modify
    base/src/twophase/ARCHITECTURE_v3.md   ← useful structural overview

**Critical rule:** The paper defines the algorithm.
If the reference code contradicts the paper, follow the paper.
The reference code may contain bugs or design debt — treat it as a starting
point for understanding, not as a specification.

---

# Output

Create a new implementation under:

    src/

Do NOT modify anything under `base/`.

---

# Backend: numpy / cupy switching

Every module must use an injected array namespace (`xp`) rather than
importing numpy or cupy directly.

Implement a backend module as the single entry point:

```python
# src/twophase/backend.py
class Backend:
    def __init__(self, use_gpu: bool = False):
        if use_gpu and self._cupy_available():
            import cupy as cp
            self.xp = cp
            self.device = "gpu"
        else:
            import numpy as np
            self.xp = np
            self.device = "cpu"

    @staticmethod
    def _cupy_available() -> bool:
        try:
            import cupy
            cupy.cuda.Device(0).compute_capability
            return True
        except Exception:
            return False

    def to_host(self, arr):
        return arr.get() if self.device == "gpu" else arr
Pass backend.xp (as xp) down through constructors to every class.
Never call import numpy or import cupy outside backend.py.

Implementation Process (mandatory — follow in order)
Read the paper — every section listed above.
List all algorithms — write a brief internal summary (comments are fine).
Read the reference code — identify what it implemented and where it may deviate from the paper.
Design the module structure for src/ before writing any code.
Implement module by module, verifying each against the paper equations.
Write unit tests for each numerical kernel (convergence orders, conservation properties, exact solutions where available).
Architecture Requirements
The structure must be modular and follow the structure of the paper:


src/
├── twophase/
│   ├── __init__.py
│   ├── backend.py          # numpy/cupy abstraction
│   ├── config.py           # SimulationConfig dataclass
│   ├── simulation.py       # top-level time-step loop
│   │
│   ├── core/
│   │   ├── grid.py         # Grid, metrics, interface-fitted coords
│   │   └── field.py        # ScalarField, VectorField (2D/3D unified)
│   │
│   ├── ccd/
│   │   ├── ccd_solver.py   # CCD O(h^6) batch solver
│   │   └── block_tridiag.py
│   │
│   ├── levelset/
│   │   ├── advection.py    # TVD-RK3 advection
│   │   ├── reinitialize.py # Godunov reinitialization
│   │   ├── heaviside.py    # Hε, δε, material property update
│   │   └── curvature.py    # κ = −∇·(∇φ/|∇φ|) via CCD
│   │
│   ├── ns_terms/
│   │   ├── convection.py   # −(u·∇)u
│   │   ├── viscous.py      # ∇·[μ̃(∇u)^sym] / (ρ̃ Re)
│   │   ├── gravity.py      # −ẑ / Fr²
│   │   ├── surface_tension.py  # κ δε ∇φ / (ρ̃ We)
│   │   └── predictor.py    # assembles all terms → u*
│   │
│   ├── pressure/
│   │   ├── rhie_chow.py    # face-velocity interpolation
│   │   ├── ppe_builder.py  # variable-density FVM Laplacian (sparse)
│   │   ├── ppe_solver.py   # BiCGSTAB
│   │   └── velocity_corrector.py
│   │
│   ├── time_integration/
│   │   ├── tvd_rk3.py
│   │   └── cfl.py
│   │
│   └── tests/
│       ├── test_ccd.py
│       ├── test_levelset.py
│       ├── test_ns_terms.py
│       └── test_pressure.py
Adapt the layout only if a paper section strongly motivates it.

Absolute Rules
base/ is read-only — never write to it.
Paper equations take precedence over the reference code at all times.
No global mutable state. Pass dependencies explicitly through constructors.
Every class receives xp (the array namespace) via its constructor.
All numerical kernels must be 2D/3D unified (use ndim, never duplicate).
No monolithic scripts. Every module has a single clear responsibility.
Do not copy large blocks from the reference code verbatim.
Variable names must reflect the paper's mathematical notation where practical (e.g. phi for φ, kappa for κ, rho_tilde for ρ̃).
Documentation
For every module, include a docstring that states:

Purpose of the module.
Which section(s) of the paper it implements.
Key equations (with equation numbers from the paper).
Example:


"""
CCD (Combined Compact Difference) solver.

Implements the 6th-order compact finite-difference scheme
described in Section 4 of the paper.

Key equations:
    Eq-I:  α₁ f'ᵢ₋₁ + f'ᵢ + α₁ f'ᵢ₊₁ = a₁(fᵢ₊₁−fᵢ₋₁)/(2h) + b₁(fᵢ₊₂−fᵢ₋₂)/(4h)
    Eq-II: β₂ f'ᵢ₋₁ + f''ᵢ + β₂ f'ᵢ₊₁ = a₂(fᵢ₊₁−2fᵢ+fᵢ₋₁)/h² + b₂(fᵢ₊₂−2fᵢ+fᵢ₋₂)/(4h²)
with α₁=7/16, a₁=15/16, b₁=1/16, β₂=−1/8, a₂=3, b₂=−9/8  (Table 1).
"""
Known Issues in the Reference Code (do not repeat these)
PPE matrix built with a Python for-loop → vectorise with numpy indexing.
Crank-Nicolson for viscous term not implemented → implement it.
Interface-fitted grid goes singular at high α → add a minimum cell-width guard (dx_min floor).
GPU backend present but no custom CUDA kernels → xp abstraction is enough for now; mark GPU-specific optimisation points with # TODO(gpu) comments.
Deliverables
All source files under src/twophase/.
src/pyproject.toml (package installable with pip install -e .).
src/README.md describing the architecture, module responsibilities, and correspondence to paper sections.
Tests under src/twophase/tests/ covering at least:
CCD convergence orders (O(h^6) for d1, O(h^5) for d2).
Level-set advection volume conservation (< 1% for circle, 10 revolutions).
Reinitialization Eikonal quality.
Divergence-free projection (∇·u < 1e-10 after correction).

