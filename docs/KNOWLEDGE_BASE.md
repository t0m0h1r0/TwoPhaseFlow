# **ARCHITECTURE & DEVELOPMENT RULES**

## **1\. System Architecture (src/twophase/)**

* **backend:** Numpy/CuPy hardware abstraction via xp \= backend.xp. NEVER hardcode numpy.  
* **config:** Hierarchical pure data classes (SimulationConfig composed of GridConfig, FluidConfig, NumericsConfig, SolverConfig). Sub-configs are the single source of truth.  
* **interfaces:** Abstract Base Classes strictly enforce contracts (IPPESolver, IReinitializer, ICurvatureCalculator, etc.).  
* **simulation:** Coordination logic. TwoPhaseSimulation is the executor, SimulationBuilder is the constructor.

## **2\. SOLID Design & Construction Rules**

* **No Direct Instantiation of Simulation:** TwoPhaseSimulation.\_\_init\_\_ has been deprecated/deleted. The simulation MUST be built using SimulationBuilder(cfg).build().  
* **Dependency Injection:** Components (e.g., Reinitializer, CurvatureCalculator, RhieChowInterpolator) must be injected via constructors. SimulationBuilder orchestrates this injection.  
* **Open-Closed Principle (OCP):** Do not modify TwoPhaseSimulation to add new solvers. Create a new class extending IPPESolver and register it in ppe\_solver\_factory.py.  
* **Single Responsibility Principle (SRP):** Boundary conditions, diagnostics, and I/O (CheckpointManager) must remain completely decoupled from the core numerical solvers.  
* **No Global Mutable State:** State (rho, u, p, phi) must be passed explicitly to functions.

## **3\. Implementation Constraints**

* **Dimension Agnostic:** Code should support ndim \= 2 or 3 gracefully where possible.  
* **Vectorization:** Heavy preference for vectorized array operations. Avoid Python for loops over grid points.  
* **Testing:** Every new feature requires a pytest (preferably Method of Manufactured Solutions \- MMS validation) checking L1, L2, L∞ norms.

## **4\. LaTeX Authoring Constraints (paper/)**

* **NO Hard-coded References:** Never write "Section 3" or "Eq. (5)" manually. ALWAYS use cross-reference commands: \\ref{sec:...}, \\eqref{eq:...}, \\ref{fig:...}.  
* **Label Consistency:** Every section, equation, figure, and table must have a consistent and descriptive \\label{}.  
* **Pedagogy First:** Equations must be followed by physical meaning and algorithmic/implementation implications.