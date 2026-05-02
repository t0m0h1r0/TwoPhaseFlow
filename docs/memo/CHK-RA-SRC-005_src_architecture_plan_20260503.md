# CHK-RA-SRC-005 src Architecture Plan

Date: 2026-05-03
Branch: `ra-src-architecture-gpu-20260503`

## Design Principle

`src/twophase/` should be organized around explicit numerical boundaries:

1. Backend boundary: all CPU/GPU namespace, host transfer, device detection,
   and Python scalar conversion lives in `twophase.backend`.
2. Operator boundary: CCD-family spatial operators remain the only production
   spatial discretization path in solver code.
3. Construction boundary: `SimulationBuilder` and config runtime builders own
   object construction; hot-path modules receive already-built dependencies.
4. Algorithm boundary: paper equations map to one implementation path; legacy
   alternatives stay registered and labeled, not silently selected.
5. Diagnostics boundary: diagnostics may end in host scalars, but reductions
   should stay device-side until an explicit final scalar/NumPy boundary.

## Completed Units

- Unit 1: centralized array namespace, host array, scalar, and device-array
  helpers in `twophase.backend`.
- Unit 2: batched hot scalar reductions in CFL, buoyancy-axis selection, and
  reinitialization monitors.

## Next Units

- Operator interface pass: make CCD/FCCD/UCCD/DCCD call sites consume a shared
  backend/operator context instead of ad hoc `xp`/grid pairs.
- Pressure solver boundary pass: separate production PPE policy, component-test
  PPE paths, and legacy solvers through explicit registry metadata.
- Diagnostics lifecycle pass: split device-resident metric accumulation from
  host serialization for long runs and plotting.
- Legacy quarantine pass: ensure C2-retained implementations are named,
  registered, and unreachable from production defaults unless explicitly chosen.

## SOLID Audit

[SOLID-X] No open violation in the completed units. The backend now owns array
boundary concerns, while diagnostics, time-step, level-set, and PPE modules no
longer duplicate CuPy dispatch/scalar extraction helpers. No tested
implementation was deleted, and no numerical algorithm or fallback policy was
changed.
