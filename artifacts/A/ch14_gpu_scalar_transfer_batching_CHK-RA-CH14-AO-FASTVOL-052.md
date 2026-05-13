# CHK-RA-CH14-AO-FASTVOL-052 - GPU Scalar Transfer Batching Guard

## Scope

- User directive: unavoidable synchronization and scalar transfers must be
  batched.
- Route: Chapter 14 capillary AO-Fast GPU runtime fail-close/reporting boundary.
- Contract: preserve nonuniform grids, interface-tracking grid rebuilds, active
  geometry algebra, and fail-close semantics.

## Change

- `_host_scalar_packet_float` remains the only usable scalar D2H helper in the
  AO GPU runtime and transfers all fail-close diagnostics in one host packet.
- `_host_scalar_float` now fails closed before touching the backend, preventing
  future code from reintroducing one-scalar-at-a-time synchronization.
- Added a regression proving packet scalar transfer uses exactly one host
  transfer for three diagnostics and the single-scalar helper performs zero
  host transfers before raising.

## Validation

```text
python3 -m py_compile \
  src/twophase/simulation/geometric_phase_runtime_gpu.py \
  src/twophase/tests/test_geometric_runtime_gpu_gates.py
PASS
```

```text
make test PYTEST_ARGS="twophase/tests/test_geometric_runtime_gpu_gates.py::test_gpu_scalar_packet_uses_one_host_transfer twophase/tests/test_geometric_runtime_gpu_gates.py::test_gpu_single_scalar_transfer_helper_fails_closed -q"
740 passed, 33 skipped
```

The remote pytest root expanded the nodeid command to the repository test suite;
the new scalar-transfer tests were included in
`test_geometric_runtime_gpu_gates.py`.

## SOLID / Fidelity Audit

- [SOLID-S] Scalar transfer policy stays in the GPU runtime boundary helper,
  not in the numerical kernels.
- [SOLID-X] No physical parameter change, CFL reduction, smoothing, damping,
  tolerance weakening, FD/WENO/PPE fallback, dense CPU fallback, hidden solver
  fallback, nonuniform-grid removal, interface-tracking rebuild removal, main
  merge, or branch deletion was introduced.
