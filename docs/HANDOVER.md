# HANDOVER

Last update: 2026-03-15  
Status: Implementation complete

---

# Current State

Two-phase flow solver implemented from scratch.

All tests pass.


pytest src/twophase/tests
→ 25 passed


Python ≥ 3.9

---

# Important

Previous `base/` directory has been removed.

Do not reference it.

---

# TODO

- GPU optimization (CuPy kernels)
- Non-uniform grid tests
- 3D verification
- Periodic boundary support
- Output writers (VTK / HDF5)

---

# Possible Next Tasks

1. Rising bubble benchmark
2. Zalesak disk test
3. GPU backend verification
4. 3D test case