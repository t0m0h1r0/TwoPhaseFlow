# Architecture

Repository structure


src/
pyproject.toml
README.md

twophase/

backend.py
config.py
simulation.py

core/
ccd/
levelset/
ns_terms/
pressure/
time_integration/

tests/

Module roles

| Module | Purpose |
|------|------|
| backend | numpy/cupy switch |
| config | simulation parameters |
| simulation | main time loop |
| core | grid + fields |
| ccd | compact finite difference |
| levelset | interface tracking |
| ns_terms | Navier–Stokes terms |
| pressure | pressure Poisson equation |
| time_integration | time stepping |

---

# Solver Workflow

1. Compute NS predictor
2. Solve pressure Poisson equation
3. Velocity correction
4. Level set advection
5. Reinitialization