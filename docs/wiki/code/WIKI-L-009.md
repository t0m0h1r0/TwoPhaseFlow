---
id: WIKI-L-009
title: "Interface Contracts: 6 Abstractions Enabling DIP Throughout the Library"
status: ACTIVE
created: 2026-04-10
depends_on: [WIKI-L-008, WIKI-X-002]
---

# Interface Contracts Reference

Interfaces live in the owning subpackages, including `src/twophase/ppe/interfaces.py`,
`src/twophase/levelset/interfaces.py`, `src/twophase/field_extension/interfaces.py`,
and `src/twophase/ns_terms/interfaces.py`. They enable Dependency Inversion:
simulation components depend on abstractions, not on concrete implementations.

## 1. IPPESolver (`src/twophase/ppe/interfaces.py`)

```python
class IPPESolver(ABC):
    @abstractmethod
    def solve(self, rhs, rho, dt: float, p_init=None) -> "array":
```

| Param | Shape | Description |
|-------|-------|-------------|
| rhs | grid.shape | (1/dt) div(u*_RC) |
| rho | grid.shape | density field rho_tilde^{n+1} |
| dt | float | time step |
| p_init | grid.shape or None | warm-start (IPC: p^n) |

**Implementations (active)**: PPESolverCCDLU, PPESolverIIM, PPESolverIterative
**Implementations (legacy)**: PPESolverPseudoTime, PPESolverSweep, PPESolverDCOmega, PPESolver, PPESolverLU

## 2. ILevelSetAdvection (`src/twophase/levelset/interfaces.py`)

```python
class ILevelSetAdvection(ABC):
    @abstractmethod
    def advance(self, psi, velocity_components: List, dt: float) -> "array":
```

**Implementations**: FCCDLevelSetAdvection (paper-current), DissipativeCCDAdvection (legacy/reference), LevelSetAdvection (WENO5 reference)

## 3. IReinitializer (`src/twophase/levelset/interfaces.py`)

```python
class IReinitializer(ABC):
    @abstractmethod
    def reinitialize(self, psi) -> "array":
```

**Implementations**: Reinitializer (facade), SplitReinitializer, UnifiedDCCDReinitializer, DGRReinitializer, HybridReinitializer, ReinitializerWENO5 (legacy)

## 4. ICurvatureCalculator (`src/twophase/levelset/interfaces.py`)

```python
class ICurvatureCalculator(ABC):
    @abstractmethod
    def compute(self, psi) -> "array":
```

**Implementations**: CurvatureCalculatorPsi (active, psi-direct), CurvatureCalculator (legacy, phi-inversion)

## 5. IFieldExtension (`src/twophase/field_extension/interfaces.py`)

```python
class IFieldExtension(ABC):
    @abstractmethod
    def extend(self, field_data, phi, n_hat=None) -> "array":
```

| Param | Description |
|-------|-------------|
| field_data | scalar field to extend (e.g. pressure) |
| phi | signed-distance function |
| n_hat | pre-computed normals or None (compute internally) |

**Implementations**: FieldExtender (upwind FD), ClosestPointExtender (Hermite), HermiteFieldExtension (HFE), NullFieldExtender (no-op)

## 6. INSTerm (`src/twophase/ns_terms/interfaces.py`) — Marker Interface

```python
class INSTerm(ABC):
    pass  # no enforced methods
```

**Design rationale**: NS terms have domain-specific signatures (ConvectionTerm needs velocity+CCD, GravityTerm needs rho+shape, etc.). A unified `compute()` would force unnecessary parameters on each term. The marker enables type-safe injection without signature coupling.

**Implementations**: ConvectionTerm, ViscousTerm, GravityTerm, SurfaceTensionTerm

## Implementation Count by Interface

| Interface | Active | Legacy | Total |
|-----------|--------|--------|-------|
| IPPESolver | 3 | 5 | 8 |
| ILevelSetAdvection | 2 | 0 | 2 |
| IReinitializer | 5 | 2 | 7 |
| ICurvatureCalculator | 1 | 1 | 2 |
| IFieldExtension | 3+1 null | 0 | 4 |
| INSTerm | 4 | 0 | 4 |
